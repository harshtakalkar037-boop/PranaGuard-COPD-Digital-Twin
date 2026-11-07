"""Read-only reproduction of saved48h predictions/metrics and original preservation.
No model fitting, threshold changes, new audit seed, reset, or promotion.
"""
import hashlib,json,sqlite3,gc
from datetime import datetime,timezone
import joblib,numpy as np,pandas as pd
from backend.app.config import ROOT
from backend.app.model48 import research_features
from scripts.audit_model48 import metrics

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run():
    out=ROOT/'docs/model-upgrade/verification';folder=ROOT/'artifacts/model48_v2';frozen=json.loads((folder/'FROZEN_DEVELOPMENT.json').read_text());audit=json.loads((folder/'AUDIT_EVALUATION.json').read_text());baseline=json.loads((ROOT/'docs/enhanced/BASELINE_MANIFEST.json').read_text())
    for name,expected in baseline['protected_files'].items():assert sha(ROOT/name)==expected,name
    assert sha(folder/'model.joblib')==frozen['model_sha256']==audit['frozen_model_sha256']
    assert sha(ROOT/'docs/model-upgrade/PROTOCOL.json')==frozen['protocol_sha256']
    assert sha(ROOT/'scripts/generate_data.py')==frozen['original_generator_sha256']
    assert sha(ROOT/'data/model48_audit/synthetic_longitudinal.csv.gz')==audit['fresh_audit']['dataset_sha256']
    assert sha(folder/'audit_predictions.csv.gz')==audit['fresh_audit']['predictions_sha256']
    model=joblib.load(folder/'model.joblib');old=joblib.load(ROOT/'artifacts/models.joblib')['models'][48];results={}
    for name,dataset,saved_path,comparison in [('fresh_audit','data/model48_audit/synthetic_longitudinal.csv.gz','audit_predictions.csv.gz',audit['fresh_audit']),('historical','data/synthetic_longitudinal.csv.gz','historical_comparison.csv.gz',audit['historical_benchmark'])]:
        raw=pd.read_csv(ROOT/dataset);frame=research_features(raw)
        if name=='fresh_audit':mask=frame.eligible.astype(bool)&frame.hour.between(1152,1367);assert all(pid.startswith('AUD48-') for pid in frame.patient_id.unique())
        else:
            from scripts.train import split_masks
            _,_,mask,_=split_masks(frame)
        test=frame[mask];saved=pd.read_csv(folder/saved_path)
        assert list(zip(test.patient_id,test.hour))==list(zip(saved.patient_id,saved.hour))
        assert np.array_equal(test.label_48.astype(int),saved.label_48.astype(int))
        original=old.predict(test);revised=model.predict(test);np.testing.assert_allclose(original,saved.original_risk48,rtol=0,atol=1e-14);np.testing.assert_allclose(revised,saved.revised_risk48,rtol=0,atol=1e-14)
        for key,p in [('original',original),('revised',revised)]:
            recomputed=metrics(test.label_48,p,comparison[key]['threshold'])
            for metric in ['auroc','auprc','brier','log_loss','recall','precision','false_positive_rate']:assert abs(recomputed[metric]-comparison[key][metric])<1e-12,(name,key,metric)
        results[name]={'rows':len(test),'patients':test.patient_id.nunique(),'maximum_prediction_error':float(max(np.max(np.abs(original-saved.original_risk48)),np.max(np.abs(revised-saved.revised_risk48)))),'metrics_reproduced':True}
        del raw,frame,test,saved;gc.collect()
    with sqlite3.connect('file:'+str(ROOT/'data/pranaguard.sqlite')+'?mode=ro',uri=True) as db:
        original_tables={t:{'rows':len(rows),'content_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()} for t in baseline['database_before'] for rows in [[tuple(r) for r in db.execute(f'SELECT * FROM {t} ORDER BY rowid')]]}
        assert original_tables==baseline['database_before'] and not db.execute('PRAGMA foreign_key_check').fetchall()
    assert audit['status']=='GATE_NOT_PASSED' and not audit['experimental_available']
    result={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'software_verification_not_model_promotion':True,'model_decision':'REJECT_CANDIDATE_RETAIN_ORIGINAL','protected_files':len(baseline['protected_files']),'predictions_and_metrics':results,'database_original_tables':original_tables,'model_sha256':frozen['model_sha256'],'protocol_sha256':frozen['protocol_sha256'],'original_dataset_and_evaluation_unmodified':True,'no_training_new_audit_or_reset':True}
    (out/'REPRODUCTION_AND_PRESERVATION.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':run()
