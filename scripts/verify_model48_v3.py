"""Read-only v3 metric/source/DB verification, with optional exact raw inference replay.
--full-audit uses the existing seed31006 cache. Add --regenerate-audit on a fresh
ZIP extraction to regenerate the SAME recorded synthetic cohort, not a new test.
No fitting, threshold changes, seed search, activation or replay reset occurs.
"""
import argparse,hashlib,json,sqlite3
from datetime import datetime,timezone
import joblib,numpy as np,pandas as pd
from backend.app.config import ROOT
from scripts.audit_model48 import metrics,cluster_intervals
from scripts.audit_model48_v3 import predict_raw
from scripts import model48_v3_data as data

def run(full=False,regenerate=False,bootstrap=False):
    folder=ROOT/'artifacts/model48_v3';out=ROOT/'docs/model-v3/verification';out.mkdir(parents=True,exist_ok=True)
    frozen=json.loads((folder/'FROZEN.json').read_text());audit=json.loads((folder/'AUDIT.json').read_text());protocol=json.loads((ROOT/'docs/model-v3/PROTOCOL.json').read_text());base=json.loads((ROOT/'docs/enhanced/BASELINE_MANIFEST.json').read_text());prior=json.loads((ROOT/'docs/model-v3/BASE_V2_PROTECTED.json').read_text())
    for name,digest in {**base['protected_files'],**prior,**protocol['all_source_code_before_fit'],**frozen['source_files_sha256']}.items():assert data.sha(ROOT/name)==digest,name
    assert data.sha(folder/'model.joblib')==frozen['model_sha256']==audit['model_sha256'] and data.sha(ROOT/'docs/model-v3/PROTOCOL.json')==frozen['protocol_sha256']==audit['protocol_sha256']
    assert frozen['created_at']==audit['frozen_at'] and datetime.fromisoformat(frozen['created_at'])<datetime.fromisoformat(audit['created_at'])
    results={};frames={}
    for name,file,expected in [('fresh_audit','audit_predictions.csv.gz',audit['fresh_audit']),('historical_benchmark','historical_predictions.csv.gz',audit['historical_benchmark'])]:
        assert data.sha(folder/file)==expected['predictions_sha256'];saved=pd.read_csv(folder/file);frames[name]=saved
        for key,column in [('original','original_risk48'),('revised','revised_risk48')]:
            m=metrics(saved.label_48,saved[column],expected[key]['threshold'])
            for metric in ['auroc','auprc','brier','log_loss','recall','precision','false_positive_rate','prevalence','mean_probability']:assert abs(m[metric]-expected[key][metric])<1e-12,(name,key,metric)
            assert m['confusion_matrix']==expected[key]['confusion_matrix'] and m['n']==expected[key]['n']
        results[name]={'rows':len(saved),'patients':saved.patient_id.nunique(),'saved_metrics_reproduced':True}
    old=audit['fresh_audit']['original'];new=audit['fresh_audit']['revised'];checks=[new['auprc']>=1.10*old['auprc'],new['auroc']>=old['auroc'],new['brier']<=old['brier']+.0001,new['recall']>0,new['false_positive_rate']<=.15];assert checks==list(audit['gate_checks'].values()) and all(checks)==audit['experimental_available']
    assert len(set(seed for p in [*protocol['development'].values(),protocol['audit']] for seed in p['seeds']))==6
    if bootstrap:
        saved=frames['fresh_audit'];actual=cluster_intervals(saved.label_48.to_numpy(),saved.original_risk48.to_numpy(),saved.revised_risk48.to_numpy(),saved.patient_id.to_numpy())
        for key,interval in actual['ci95'].items():np.testing.assert_allclose(interval,audit['fresh_audit']['uncertainty']['ci95'][key],rtol=0,atol=1e-12)
    if full or regenerate:
        model=joblib.load(folder/'model.joblib');baseline=joblib.load(ROOT/'artifacts/models.joblib')['models'][48];seed=protocol['audit']['seeds'][0];rawfile=data.CACHE/str(seed)/'synthetic_longitudinal.csv.gz'
        if not rawfile.exists():
            if not regenerate:raise RuntimeError('Recorded raw audit not included in compact ZIP. Use --full-audit --regenerate-audit to regenerate exactly seed31006; no new audit or fit.')
            data.CACHE=ROOT/'.cache/model48-v3-reproduction';rawfile,_=data.generate_seed(seed,protocol['audit']['patients_per_seed'])
        assert data.sha(rawfile)==audit['fresh_audit']['raw_sha256']
        for name,path,hours,namespace,is_original in [('fresh_audit',rawfile,protocol['audit']['hours'],f'V3-{seed}',False),('historical_benchmark',ROOT/'data/synthetic_longitudinal.csv.gz',[1152,1367],None,True)]:
            actual=predict_raw(path,model,baseline,hours,namespace,original_test=is_original);saved=frames[name]
            assert list(zip(actual.patient_id,actual.hour))==list(zip(saved.patient_id,saved.hour)) and np.array_equal(actual.label_48,saved.label_48)
            delta=max(float(np.max(np.abs(actual[column]-saved[column]))) for column in ['original_risk48','revised_risk48']);assert delta<1e-14
            results[name].update({'raw_model_inference_reproduced':True,'maximum_probability_error':delta})
    with sqlite3.connect('file:'+str(ROOT/'data/pranaguard.sqlite')+'?mode=ro',uri=True) as db:
        tables={t:{'rows':len(rows),'content_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()} for t in base['database_before'] for rows in [[tuple(r) for r in db.execute(f'SELECT * FROM {t} ORDER BY rowid')]]};assert tables==base['database_before'] and db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
    assert json.loads((ROOT/'artifacts/model48_v2/AUDIT_EVALUATION.json').read_text())['status']=='GATE_NOT_PASSED'
    report={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'original_protected_files':len(base['protected_files']),'prior_v2_protected_files':len(prior),'frozen_prefit_source_files':len(protocol['all_source_code_before_fit']),'predictions':results,'bootstrap_reproduced':bootstrap,'original_database_tables':tables,'v3_status':audit['status'],'prior_v2_still_rejected':True,'no_training_cutoff_change_new_seed_or_reset':True,'not_clinical_validation':True}
    (out/'REPRODUCTION.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--full-audit',action='store_true');p.add_argument('--regenerate-audit',action='store_true');p.add_argument('--bootstrap',action='store_true');args=p.parse_args();run(args.full_audit,args.regenerate_audit,args.bootstrap)
