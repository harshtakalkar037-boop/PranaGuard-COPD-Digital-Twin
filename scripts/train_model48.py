"""Predeclared bounded48h development; never reads test labels or audit cohort."""
import hashlib,json,time
from datetime import datetime,timezone
import joblib,numpy as np,pandas as pd
from sklearn.metrics import average_precision_score,roc_auc_score,precision_recall_curve,confusion_matrix
from backend.app.config import ROOT
from backend.app.model48 import CANDIDATES,Research48Model,research_features,make_candidate,margin,calibrate_positive
OUT=ROOT/'artifacts/model48_v2'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def patient_ids(lo,hi):return [f'PG-{i:04d}' for i in range(lo,hi+1)]
def choose_threshold(y,p):
    # Evaluate unique validation score cutoffs only. No test/audit access.
    y=np.asarray(y).astype(int);p=np.asarray(p);options=[]
    if not y.any() or y.all():return None
    for threshold in np.unique(p):
        tn,fp,fn,tp=confusion_matrix(y,p>=threshold,labels=[0,1]).ravel();fpr=fp/(fp+tn);f1=2*tp/(2*tp+fp+fn) if tp else 0
        if tp>0 and fpr<=.10:options.append((f1,float(threshold),{'threshold':float(threshold),'f1':float(f1),'recall':float(tp/(tp+fn)),'precision':float(tp/(tp+fp)),'false_positive_rate':float(fpr),'confusion_matrix':[[int(tn),int(fp)],[int(fn),int(tp)]],'validated_clinical_cutoff':False}))
    return max(options,key=lambda x:(x[0],x[1]))[2] if options else None

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'FROZEN_DEVELOPMENT.json').exists():raise RuntimeError('Development already frozen; do not retune after audit. Use a separate explicitly versioned study.')
    protocol_path=ROOT/'docs/model-upgrade/PROTOCOL.json';protocol=json.loads(protocol_path.read_text());raw=pd.read_csv(ROOT/'data/synthetic_longitudinal.csv.gz')
    # Remove all nondevelopment patients and future hours before deriving development features.
    source=raw[raw.patient_id.isin(patient_ids(1,96))&(raw.hour<=1050)].copy();del raw
    frame=research_features(source);eligible=frame.eligible.astype(bool);results=[]
    assert [c['name'] for c in CANDIDATES]==protocol['candidates']
    for spec in CANDIDATES:
        scores=[]
        for fold in protocol['selection_folds']:
            tr=frame[eligible&frame.patient_id.isin(patient_ids(*fold['train_patient_numbers']))&frame.hour.between(*fold['train_hours'])&(frame.hour%3==0)]
            va=frame[eligible&frame.patient_id.isin(patient_ids(*fold['validation_patient_numbers']))&frame.hour.between(*fold['validation_hours'])]
            assert not set(tr.patient_id)&set(va.patient_id) and tr.hour.max()+72<va.hour.min()
            fitted=make_candidate(spec);fitted.fit(tr[spec['features']],tr.label_48.astype(int));p=margin(fitted,va,spec['features']);y=va.label_48.astype(int)
            scores.append({'auprc':float(average_precision_score(y,p)),'auroc':float(roc_auc_score(y,p)),'train_rows':len(tr),'validation_rows':len(va),'validation_positive_rows':int(y.sum())})
        result={'candidate':spec['name'],'features':spec['features'],'folds':scores,'mean_validation_auprc':float(np.mean([s['auprc'] for s in scores]))};results.append(result);print(spec['name'],result['mean_validation_auprc'],flush=True)
    selected=max(results,key=lambda r:r['mean_validation_auprc']);spec=next(s for s in CANDIDATES if s['name']==selected['candidate'])
    tr=frame[eligible&frame.patient_id.isin(patient_ids(1,72))&frame.hour.between(72,747)&(frame.hour%3==0)]
    ca=frame[eligible&frame.patient_id.isin(patient_ids(73,84))&frame.hour.between(849,1050)&(frame.hour%3==0)]
    threshold_set=frame[eligible&frame.patient_id.isin(patient_ids(85,96))&frame.hour.between(849,1050)&(frame.hour%3==0)]
    assert not set(tr.patient_id)&set(ca.patient_id)|set(ca.patient_id)&set(threshold_set.patient_id)|set(tr.patient_id)&set(threshold_set.patient_id)
    fitted=make_candidate(spec);fitted.fit(tr[spec['features']],tr.label_48.astype(int));cal=calibrate_positive(margin(fitted,ca,spec['features']),ca.label_48)
    model=Research48Model(fitted,list(spec['features']),cal,spec['name'],spec['kind']);operating=choose_threshold(threshold_set.label_48,model.predict(threshold_set))
    joblib.dump(model,OUT/'model.joblib',compress=3)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'version':model.version,'protocol_sha256':sha(protocol_path),'source_data_sha256':sha(ROOT/'data/synthetic_longitudinal.csv.gz'),'original_generator_sha256':sha(ROOT/'scripts/generate_data.py'),'candidates':results,'selected_candidate':model.candidate,'selected_features':model.features,'calibration':cal,'operating_point':operating,'development_rows':{'training':len(tr),'calibration':len(ca),'threshold':len(threshold_set)},'model_sha256':sha(OUT/'model.joblib'),'audit_not_yet_generated_or_evaluated':True,'original_test_used_for_selection':False,'warning':'Synthetic engineering study; no clinical validation.'}
    (OUT/'FROZEN_DEVELOPMENT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='candidates'},indent=2))
if __name__=='__main__':run()
