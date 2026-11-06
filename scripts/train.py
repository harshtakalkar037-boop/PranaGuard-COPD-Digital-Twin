"""Execute all experiments. Fixed protocol; no metric or threshold selection on test data."""
import argparse, hashlib, json, warnings
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (roc_auc_score, average_precision_score, brier_score_loss,
    log_loss, confusion_matrix, precision_score, recall_score, roc_curve, precision_recall_curve)
from sklearn.calibration import calibration_curve
from backend.app.config import DATA, ARTIFACTS, HORIZONS, MODEL_VERSION
from backend.app.features import add_features, FEATURES, GROUPS
from backend.app.ml import fit_model
warnings.filterwarnings('ignore',message='X does not have valid feature names')

def split_masks(df):
    ids=sorted(df.patient_id.unique()); n=len(ids); hours=int(df.hour.max()+1)
    ntrain=int(n*.6); ncal=int(n*.2)
    train_ids=ids[:ntrain]; cal_ids=ids[ntrain:ntrain+ncal]; test_ids=ids[ntrain+ncal:]
    ends={'train_end_exclusive':int(hours*.52),'cal_start':int(hours*.59),'cal_end_exclusive':int(hours*.73),'test_start':int(hours*.80),'test_end_exclusive':hours-72}
    eligible=df.eligible.astype(bool)
    train=eligible & df.patient_id.isin(train_ids)&(df.hour>=72)&(df.hour<ends['train_end_exclusive'])
    cal=eligible & df.patient_id.isin(cal_ids)&(df.hour>=ends['cal_start'])&(df.hour<ends['cal_end_exclusive'])
    test=eligible & df.patient_id.isin(test_ids)&(df.hour>=ends['test_start'])&(df.hour<ends['test_end_exclusive'])
    # Event-label windows cannot touch the next partition's feature window.
    assert ends['train_end_exclusive']+72<=ends['cal_start']
    assert ends['cal_end_exclusive']+72<=ends['test_start']
    assert not (set(train_ids)&set(cal_ids)|set(train_ids)&set(test_ids)|set(cal_ids)&set(test_ids))
    return train,cal,test,{'patient_ids':{'train':train_ids,'calibration':cal_ids,'test':test_ids},'hour_bounds':ends,
                         'protocol':'Patient-disjoint and calendar-time disjoint; >=72h purge between partitions; first72h baseline only.',
                         'fit_stride':3,'threshold':.35,'feature_names':FEATURES,'labels':'New synthetic onset in (t,t+h]; active episodes excluded; full 72h follow-up required.'}

def metrics(y,p):
    pred=p>=.35; matrix=confusion_matrix(y,pred,labels=[0,1]); tn,fp,fn,tp=matrix.ravel()
    return {'auroc':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
            'auprc':float(average_precision_score(y,p)), 'brier':float(brier_score_loss(y,p)),
            'log_loss':float(log_loss(y,p,labels=[0,1])), 'precision':float(precision_score(y,pred,zero_division=0)),
            'recall':float(recall_score(y,pred,zero_division=0)), 'specificity':float(tn/(tn+fp)),
            'threshold':.35,'confusion_matrix':matrix.tolist(),'n':int(len(y)),'positive_hours':int(np.sum(y)),
            'prevalence':float(np.mean(y))}

def thin(xs,ys,limit=75):
    ix=np.unique(np.linspace(0,len(xs)-1,min(limit,len(xs))).astype(int))
    return [{'x':float(xs[i]),'y':float(ys[i])} for i in ix]

def bootstrap(y,p,ids,seed=2026):
    rng=np.random.default_rng(seed); unique=np.unique(ids); vals=[]
    for _ in range(150):
        sample=rng.choice(unique,len(unique),replace=True); ix=np.concatenate([np.flatnonzero(ids==pid) for pid in sample])
        if len(np.unique(y[ix]))<2: continue
        vals.append([roc_auc_score(y[ix],p[ix]),average_precision_score(y[ix],p[ix])])
    if not vals:return {}
    a=np.array(vals)
    return {'method':'150 patient-cluster bootstrap resamples; descriptive, small synthetic sample',
            'auroc_95ci':np.quantile(a[:,0],[.025,.975]).tolist(),'auprc_95ci':np.quantile(a[:,1],[.025,.975]).tolist(),'valid_resamples':len(vals)}

def train():
    ARTIFACTS.mkdir(exist_ok=True)
    raw=pd.read_csv(DATA/'synthetic_longitudinal.csv.gz')
    df=add_features(raw);tm,cm,em,protocol=split_masks(df)
    tr=df[tm & (df.hour%3==0)];ca=df[cm & (df.hour%3==0)];te=df[em]
    if len(te)==0:raise ValueError('Empty test split')
    protocol['rows']={'train_sampled':len(tr),'calibration_sampled':len(ca),'test_hourly':len(te)}
    protocol['timestamps']={k:{'min':part.timestamp.min(),'max':part.timestamp.max()} for k,part in [('train',tr),('calibration',ca),('test',te)]}
    results=[];diagnostics={}; bundles={}; testpred=te[['patient_id','hour','timestamp','label_24','label_48','label_72']].copy()
    primary='LightGBM'
    try: import lightgbm
    except ImportError: primary='LogisticRegression'
    experiments=[('LogisticRegression','personalized')]+[(primary,g) for g in GROUPS]
    for algorithm,group in experiments:
        for h in HORIZONS:
            fitted=fit_model(tr,ca,GROUPS[group],h,algorithm);p=fitted.predict(te);y=te[f'label_{h}'].to_numpy().astype(int)
            m=metrics(y,p);m.update({'algorithm':algorithm,'ablation':group,'horizon':h})
            results.append(m);print(f'{algorithm:20s} {group:18s} {h}h ROC={m["auroc"]:.4f} AP={m["auprc"]:.4f} Brier={m["brier"]:.4f}',flush=True)
            if algorithm==primary and group=='personalized':
                bundles[h]=fitted
                fpr,tpr,_=roc_curve(y,p);prec,rec,_=precision_recall_curve(y,p)
                frac,mean=calibration_curve(y,p,n_bins=10,strategy='uniform')
                m.update(bootstrap(y,p,te.patient_id.to_numpy()))
                diagnostics[str(h)]={'roc':thin(fpr,tpr),'pr':thin(rec,prec),
                                     'calibration':[{'predicted':float(a),'observed':float(b)} for a,b in zip(mean,frac)],
                                     'metrics':m}
                testpred[f'risk_{h}']=p
    # Evaluation-derived demonstration selection, never used for fitting or model selection.
    testpred.to_csv(ARTIFACTS/'test_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    e=protocol['hour_bounds']; leads=[];events=0;cases=[]
    for pid in protocol['patient_ids']['test']:
        onsets=raw[(raw.patient_id==pid)&(raw.event_onset==1)&(raw.hour>=e['test_start'])&(raw.hour<e['test_end_exclusive'])].hour
        ppart=testpred[testpred.patient_id==pid]
        for onset in onsets:
            events+=1;window=ppart[(ppart.hour<onset)&(ppart.hour>=onset-72)]
            hits=window[window.risk_72>=.35]
            if len(hits):
                lead=int(onset-hits.hour.min());leads.append(lead)
                cases.append({'patient_id':pid,'start_hour':int(max(e['test_start'],hits.hour.min()-12)),
                              'onset_hour':int(onset),'lead_hours':lead,'selection':'Retrospectively chosen from held-out synthetic events for a deterministic demonstration, not prospective validation.'})
    demo=max(cases,key=lambda x:x['lead_hours']) if cases else {'patient_id':protocol['patient_ids']['test'][0],'start_hour':e['test_start'],'onset_hour':None,'selection':'First held-out patient; no high-risk event selected.'}
    primary_rows=[r for r in results if r['algorithm']==primary and r['ablation']=='personalized']
    report={'created_at':datetime.now(timezone.utc).isoformat(),'model_version':MODEL_VERSION,'primary_algorithm':primary,
            'dataset_sha256':hashlib.sha256((DATA/'synthetic_longitudinal.csv.gz').read_bytes()).hexdigest(),
            'protocol':protocol,'results':results,'diagnostics':diagnostics,
            'lead_time':{'test_onsets':events,'detected_onsets':len(leads),'median_hours_detected':float(np.median(leads)) if leads else None,
                         'rule':'Earliest 72h risk >=0.35 in the prior72h among eligible TEST rows only. Undetected events excluded from median; boundary-truncated windows possible. Descriptive synthetic result.'},
            'warning':'ALL patient data and outcomes are synthetic. Row-wise metrics use correlated hourly windows. No clinical validation; generator learnability is not clinical performance.',
            'calibration_audit':{str(h):{'slope':float(bundles[h].calibrator.coef_[0,0]),'intercept':float(bundles[h].calibrator.intercept_[0]),'direction_preserving':bool(bundles[h].calibrator.coef_[0,0]>=0)} for h in HORIZONS},
            'frozen_choices':'No hyperparameter search. Threshold .35 fixed a priori. Platt calibration fitted only on calibration patients/time. Baseline first72h available before any fitted row.'}
    joblib.dump({'models':bundles,'version':MODEL_VERSION,'algorithm':primary,'feature_order':FEATURES,'data_hash':report['dataset_sha256']},ARTIFACTS/'models.joblib',compress=3)
    (ARTIFACTS/'evaluation.json').write_text(json.dumps(report,indent=2))
    (ARTIFACTS/'demo_case.json').write_text(json.dumps(demo,indent=2))
    (ARTIFACTS/'split_manifest.json').write_text(json.dumps(protocol,indent=2))
    pd.DataFrame(results).drop(columns=['confusion_matrix'],errors='ignore').to_csv(ARTIFACTS/'metrics.csv',index=False)
    summary=['# Executed model evaluation','',report['warning'],'','| Model / ablation | Horizon | AUROC | AUPRC | Brier | Positive hours / test hours |','|---|---:|---:|---:|---:|---:|']
    for r in results:summary.append(f'| {r["algorithm"]} / {r["ablation"]} | {r["horizon"]}h | {r["auroc"]:.4f} | {r["auprc"]:.4f} | {r["brier"]:.4f} | {r["positive_hours"]} / {r["n"]} |')
    summary+=['',f'Lead-time audit: `{json.dumps(report["lead_time"])}`','',f'Protocol: `{json.dumps(protocol)}`']
    (ARTIFACTS/'evaluation.md').write_text('\n'.join(summary))
    print('Saved all experiments, models, calibration/ROC/PR curves and reproducible demo case.',flush=True)

if __name__=='__main__':train()
