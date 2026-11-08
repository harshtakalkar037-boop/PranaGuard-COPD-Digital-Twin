"""One predeclared fresh synthetic audit AFTER freezing revised48h development."""
import hashlib,json
from datetime import datetime,timezone
import joblib,numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,log_loss,confusion_matrix,roc_curve,precision_recall_curve
from sklearn.calibration import calibration_curve
from backend.app.config import ROOT
from backend.app.model48 import research_features
from scripts.train_model48 import OUT,sha

def metrics(y,p,threshold):
    y=np.asarray(y).astype(int);p=np.asarray(p);tn,fp,fn,tp=confusion_matrix(y,p>=threshold,labels=[0,1]).ravel()
    return {'auroc':float(roc_auc_score(y,p)),'auprc':float(average_precision_score(y,p)),'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p)),'threshold':float(threshold),'recall':float(tp/(tp+fn)),'precision':float(tp/(tp+fp)) if tp+fp else 0.,'false_positive_rate':float(fp/(fp+tn)),'confusion_matrix':[[int(tn),int(fp)],[int(fn),int(tp)]],'n':len(y),'positive_rows':int(y.sum()),'prevalence':float(y.mean()),'mean_probability':float(p.mean())}

def curves(y,p):
    fpr,tpr,_=roc_curve(y,p);precision,recall,_=precision_recall_curve(y,p);observed,predicted=calibration_curve(y,p,n_bins=10,strategy='quantile')
    def thin(x,y):
        ix=np.unique(np.linspace(0,len(x)-1,min(80,len(x))).astype(int));return [{'x':float(x[i]),'y':float(y[i])} for i in ix]
    return {'roc':thin(fpr,tpr),'pr':thin(recall,precision),'calibration':[{'x':float(a),'y':float(b)} for a,b in zip(predicted,observed)]}

def cluster_intervals(y,old,new,ids):
    unique=np.unique(ids);indices={pid:np.flatnonzero(ids==pid) for pid in unique};rng=np.random.default_rng(20261106);rows=[]
    for _ in range(300):
        ix=np.concatenate([indices[pid] for pid in rng.choice(unique,len(unique),replace=True)])
        if len(np.unique(y[ix]))<2:continue
        old_metrics=[roc_auc_score(y[ix],old[ix]),average_precision_score(y[ix],old[ix]),brier_score_loss(y[ix],old[ix])]
        new_metrics=[roc_auc_score(y[ix],new[ix]),average_precision_score(y[ix],new[ix]),brier_score_loss(y[ix],new[ix])]
        rows.append(old_metrics+new_metrics+list(np.array(new_metrics)-np.array(old_metrics)))
    a=np.asarray(rows);keys=['old_auroc','old_auprc','old_brier','revised_auroc','revised_auprc','revised_brier','difference_auroc','difference_auprc','difference_brier']
    return {'method':'300 paired patient-cluster bootstrap resamples; descriptive synthetic intervals, not clinical validation','seed':20261106,'valid_resamples':len(rows),'ci95':{k:np.quantile(a[:,i],[.025,.975]).tolist() for i,k in enumerate(keys)}}

def run():
    report_path=OUT/'AUDIT_EVALUATION.json'
    if report_path.exists():raise RuntimeError('Audit already completed; do not select/tune on its results.')
    frozen=json.loads((OUT/'FROZEN_DEVELOPMENT.json').read_text());protocol=json.loads((ROOT/'docs/model-upgrade/PROTOCOL.json').read_text())
    assert sha(OUT/'model.joblib')==frozen['model_sha256'] and sha(ROOT/'docs/model-upgrade/PROTOCOL.json')==frozen['protocol_sha256']
    assert sha(ROOT/'scripts/generate_data.py')==frozen['original_generator_sha256']
    audit_dir=ROOT/'data/model48_audit';assert not audit_dir.exists();audit_dir.mkdir()
    # Run the UNMODIFIED generator into a dedicated directory, sourcing the same protected caches.
    from scripts import generate_data as generator
    base_data=ROOT/'data';original_environment=generator.environment
    def environment(city,hours,rng,offline):
        save=generator.DATA;generator.DATA=base_data
        try:return original_environment(city,hours,rng,offline)
        finally:generator.DATA=save
    generator.environment=environment;generator.DATA=audit_dir
    audit=protocol['fresh_audit'];generator.generate(seed=audit['seed'],patients=audit['patients'],days=audit['days'])
    path=audit_dir/'synthetic_longitudinal.csv.gz';raw=pd.read_csv(path);raw['patient_id']=raw.patient_id.str.replace('PG-','AUD48-',regex=False)
    raw.to_csv(path,index=False,compression={'method':'gzip','mtime':0})
    patients=json.loads((audit_dir/'patients.json').read_text())
    for patient in patients:patient['patient_id']=patient['patient_id'].replace('PG-','AUD48-');patient['display_name']='Independent audit '+patient['patient_id']
    (audit_dir/'patients.json').write_text(json.dumps(patients,indent=2));manifest=json.loads((audit_dir/'generation_manifest.json').read_text());manifest.update({'sha256':sha(path),'patient_id_namespace':'AUD48-','original_generator_sha256':frozen['original_generator_sha256'],'frozen_model_before_generation':frozen['model_sha256'],'shared_historical_environment':True,'clinical_validity':'NONE; independent synthetic patients, same generator and weather; not external clinical validation'});(audit_dir/'generation_manifest.json').write_text(json.dumps(manifest,indent=2))
    frame=research_features(raw);test=frame[frame.eligible.astype(bool)&frame.hour.between(*audit['evaluation_hours'])].copy();del frame,raw
    model=joblib.load(OUT/'model.joblib');baseline=joblib.load(ROOT/'artifacts/models.joblib')['models'][48]
    y=test.label_48.to_numpy().astype(int);old=baseline.predict(test);new=model.predict(test);operating=frozen['operating_point'];threshold=operating['threshold'] if operating else .35
    original=metrics(y,old,.35);revised=metrics(y,new,threshold)
    checks={'auprc_10_percent_relative_improvement':revised['auprc']>=1.10*original['auprc'],'auroc_not_worse':revised['auroc']>=original['auroc'],'brier_not_worse_with_0_0001_tolerance':revised['brier']<=original['brier']+.0001,'nonzero_recall_at_validation_selected_threshold':bool(operating) and revised['recall']>0,'false_positive_rate_at_most_15_percent':revised['false_positive_rate']<=.15}
    predictions=test[['patient_id','hour','timestamp','label_48']].copy();predictions['original_risk48']=old;predictions['revised_risk48']=new;predictions.to_csv(OUT/'audit_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    confidence=cluster_intervals(y,old,new,test.patient_id.to_numpy())
    # Previously disclosed original test: secondary historical benchmark, NOT untouched validation.
    from scripts.train import split_masks
    historical=research_features(pd.read_csv(ROOT/'data/synthetic_longitudinal.csv.gz'));_,_,mask,_=split_masks(historical);known=historical[mask];ky=known.label_48.astype(int);ko=baseline.predict(known);kn=model.predict(known)
    secondary={'warning':'Original test metrics were disclosed before this study. No candidate/threshold selection used these rows. This is a historical comparison, not a fresh holdout.','original':metrics(ky,ko,.35),'revised':metrics(ky,kn,threshold)}
    saved=known[['patient_id','hour','timestamp','label_48']].copy();saved['original_risk48']=ko;saved['revised_risk48']=kn;saved.to_csv(OUT/'historical_comparison.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    assert sha(OUT/'model.joblib')==frozen['model_sha256']
    report={'created_at':datetime.now(timezone.utc).isoformat(),'version':model.version,'selected_candidate':model.candidate,'status':'EXPERIMENTAL_GATE_PASS' if all(checks.values()) else 'GATE_NOT_PASSED','experimental_available':all(checks.values()),'gate_checks':checks,'fresh_audit':{'seed':audit['seed'],'patients':audit['patients'],'evaluated_patients':test.patient_id.nunique(),'hours':audit['evaluation_hours'],'original':original,'revised':revised,'revised_at_original_0_35':metrics(y,new,.35),'original_at_same_revised_cutoff':metrics(y,old,threshold),'curves':{'original':curves(y,old),'revised':curves(y,new)},'uncertainty':confidence,'dataset_sha256':sha(path),'predictions_sha256':sha(OUT/'audit_predictions.csv.gz')},'historical_benchmark':secondary,'development':{'mean_validation_auprc':next(r['mean_validation_auprc'] for r in frozen['candidates'] if r['candidate']==model.candidate),'calibration':frozen['calibration'],'operating_point':operating,'rows':frozen['development_rows']},'frozen_model_sha256':frozen['model_sha256'],'protocol_sha256':frozen['protocol_sha256'],'clinical_validation':False,'limitations':['All patients and outcomes synthetic; same generator and historical weather as development.','Hourly forecast windows overlap; effective sample is much smaller than row count.','The original24h/48h/72h artifacts and stored replay risks are retained, not silently replaced.','48h calibration/threshold are not clinically validated; metrics need not improve on every cohort or every patient.','72h model remains below chance in the original study; no benefit or emergency response is established.']}
    report_path.write_text(json.dumps(report,indent=2,allow_nan=False));print(json.dumps({k:v for k,v in report.items() if k not in ('fresh_audit','limitations')},indent=2));print('FRESH AUDIT',json.dumps({'original':original,'revised':revised,'uncertainty':confidence},indent=2))
if __name__=='__main__':run()
