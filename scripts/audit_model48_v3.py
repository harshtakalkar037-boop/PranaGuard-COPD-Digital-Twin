"""Single fresh audit after the multi-seed model/cutoff is frozen. Refuses overwrite."""
import json,gc
from datetime import datetime,timezone
import joblib,numpy as np,pandas as pd
from backend.app.config import ROOT
from backend.app.model48_v3 import features_v3
from scripts.model48_v3_data import sha,generate_seed
from scripts.audit_model48 import metrics,curves,cluster_intervals
OUT=ROOT/'artifacts/model48_v3'

def predict_raw(rawfile,model,baseline,hours,namespace=None,stride=1,original_test=False):
    predictions=[]
    for raw in pd.read_csv(rawfile,chunksize=1440):
        assert raw.patient_id.nunique()==1
        if original_test and int(raw.patient_id.iloc[0].split('-')[-1])<97:continue
        raw=raw[raw.hour<=hours[1]].copy()
        if namespace:raw['patient_id']=namespace+'-'+raw.patient_id
        frame=features_v3(raw);test=frame[frame.eligible.astype(bool)&frame.hour.between(*hours)&(frame.hour%stride==0)].copy()
        if not len(test):continue
        rows=test[['patient_id','hour','timestamp','label_48']].copy();rows['original_risk48']=baseline.predict(test);rows['revised_risk48']=model.predict(test);predictions.append(rows)
    return pd.concat(predictions,ignore_index=True)

def score(predictions,threshold):
    y=predictions.label_48.to_numpy().astype(int);old=predictions.original_risk48.to_numpy();new=predictions.revised_risk48.to_numpy()
    return {'original':metrics(y,old,.35),'revised':metrics(y,new,threshold),'revised_at_original_0_35':metrics(y,new,.35),'original_at_same_revised_cutoff':metrics(y,old,threshold)}

def run():
    report_path=OUT/'AUDIT.json'
    if report_path.exists():raise RuntimeError('v3 audit already completed. No seed/gate retries or audit-driven tuning.')
    frozen=json.loads((OUT/'FROZEN.json').read_text());protocol=json.loads((ROOT/'docs/model-v3/PROTOCOL.json').read_text());assert frozen['fresh_audit_not_generated']
    assert sha(OUT/'model.joblib')==frozen['model_sha256'] and sha(ROOT/'docs/model-v3/PROTOCOL.json')==frozen['protocol_sha256'] and sha(ROOT/'scripts/generate_data.py')==frozen['generator_sha256']
    for name,digest in frozen['source_files_sha256'].items():assert sha(ROOT/name)==digest
    audit=protocol['audit'];seed=audit['seeds'][0];rawfile,manifest=generate_seed(seed,audit['patients_per_seed'])
    model=joblib.load(OUT/'model.joblib');baseline=joblib.load(ROOT/'artifacts/models.joblib')['models'][48];threshold=frozen['operating_point']['threshold']
    pred=predict_raw(rawfile,model,baseline,audit['hours'],f'V3-{seed}',audit['stride']);scores=score(pred,threshold);old=scores['original'];new=scores['revised'];print('FRESH AUDIT POINT ESTIMATES',json.dumps(scores,indent=2),flush=True)
    checks={'auprc_10_percent_relative_improvement':new['auprc']>=1.10*old['auprc'],'auroc_not_worse':new['auroc']>=old['auroc'],'brier_not_worse_with_0_0001_tolerance':new['brier']<=old['brier']+.0001,'nonzero_recall_at_validation_selected_threshold':new['recall']>0,'false_positive_rate_at_most_15_percent':new['false_positive_rate']<=.15}
    pred.to_csv(OUT/'audit_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0});uncertainty=cluster_intervals(pred.label_48.to_numpy(),pred.original_risk48.to_numpy(),pred.revised_risk48.to_numpy(),pred.patient_id.to_numpy())
    known=predict_raw(ROOT/'data/synthetic_longitudinal.csv.gz',model,baseline,[1152,1367],original_test=True);secondary=score(known,threshold);known.to_csv(OUT/'historical_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    report={'created_at':datetime.now(timezone.utc).isoformat(),'version':model.version,'selected_candidate':model.candidate,'status':'EXPERIMENTAL_GATE_PASS' if all(checks.values()) else 'GATE_NOT_PASSED','experimental_available':all(checks.values()),'gate_checks':checks,'fresh_audit':{'seed':seed,'patients':audit['patients_per_seed'],'evaluated_patients':pred.patient_id.nunique(),'hours':audit['hours'],'stride':audit['stride'],**scores,'uncertainty':uncertainty,'curves':{'original':curves(pred.label_48,pred.original_risk48),'revised':curves(pred.label_48,pred.revised_risk48)},'raw_sha256':manifest['sha256'],'raw_rows':manifest['rows'],'synthetic_events':manifest['synthetic_events'],'predictions_sha256':sha(OUT/'audit_predictions.csv.gz')},'historical_benchmark':{'warning':'Previously disclosed original test, not a pristine holdout. Not used for development.',**secondary,'predictions_sha256':sha(OUT/'historical_predictions.csv.gz')},'frozen_at':frozen['created_at'],'model_sha256':frozen['model_sha256'],'protocol_sha256':frozen['protocol_sha256'],'original24_72_unchanged':True,'prior_v2_status':'GATE_NOT_PASSED; preserved','clinical_validation':False,'limitations':['All patients, physiological streams and labels are synthetic. Independent patients share the same generator and four-city historical environmental caches. This is not external/clinical validation.','This is a separate second improvement attempt after the disclosed v2 failure. Descriptive bootstrap intervals do not correct for all model/research-attempt selection.','Overlapping hourly labels are correlated; patient-cluster resampling is used. Row counts are not independent clinical sample sizes.','Original24h/72h models, stored replay probabilities and their limitations remain. Original72h AUROC below chance; original0.35 cutoffs all had zero sensitivity.','New48h calibration and operating point are synthetic-development choices, not clinical thresholds. No emergency, diagnostic, prevention or causal-benefit claim.','Live context, manual records, device sessions and newly registered patients do not receive these predictions.72h baseline requirement retained.']}
    assert sha(OUT/'model.joblib')==frozen['model_sha256']
    report_path.write_text(json.dumps(report,indent=2,allow_nan=False));print('FINAL v3',json.dumps({'status':report['status'],'gate_checks':checks,'uncertainty':uncertainty,'historical_benchmark':secondary},indent=2))
if __name__=='__main__':run()
