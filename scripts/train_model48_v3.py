"""Fixed multi-seed48h development. Fresh seed31006 is forbidden until freeze."""
import json,gc
from datetime import datetime,timezone
import joblib,numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score
from backend.app.config import ROOT
from backend.app.model48 import calibrate_positive,margin
from backend.app.model48_v3 import CANDIDATES,make_pipeline,Model48V3,VERSION
from scripts.train_model48 import choose_threshold
from scripts.model48_v3_data import CACHE,sha,partition
OUT=ROOT/'artifacts/model48_v3'
def run():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'FROZEN.json').exists():raise RuntimeError('v3 already frozen; no audit-driven refit permitted.')
    protocol=json.loads((ROOT/'docs/model-v3/PROTOCOL.json').read_text());assert not (CACHE/'31006').exists(),'Audit seed must remain unopened.'
    train,train_meta=partition('train',protocol['development']['train']);val,val_meta=partition('selection',protocol['development']['selection']);assert not set(train['patient_id'])&set(val['patient_id']);assert train['hour'].max()+72<val['hour'].min()
    assert [s['name'] for s in CANDIDATES]==protocol['candidates']
    scores=[];best=None;best_ap=-1
    for spec in CANDIDATES:
        pipeline=make_pipeline(spec);pipeline.fit(train['x'][spec['features']],train['y']);pred=margin(pipeline,val['x'],spec['features']);ap=float(average_precision_score(val['y'],pred));record={'candidate':spec['name'],'specification':spec,'selection_auprc':ap,'selection_auroc':float(roc_auc_score(val['y'],pred))};scores.append(record);print(json.dumps({k:v for k,v in record.items() if k!='specification'}),flush=True)
        if ap>best_ap:best_ap=ap;best=(spec,pipeline)
        gc.collect()
    spec,pipeline=best;del train,val;gc.collect()
    cal,cal_meta=partition('calibration',protocol['development']['calibration']);calibration=calibrate_positive(margin(pipeline,cal['x'],spec['features']),cal['y']);del cal;gc.collect()
    model=Model48V3(pipeline,list(spec['features']),calibration,spec['name'],spec['kind'],VERSION)
    threshold,threshold_meta=partition('threshold',protocol['development']['threshold']);operating=choose_threshold(threshold['y'],model.predict(threshold['x']));assert operating is not None
    joblib.dump(model,OUT/'model.joblib',compress=3)
    report={'created_at':datetime.now(timezone.utc).isoformat(),'version':VERSION,'protocol_sha256':sha(ROOT/'docs/model-v3/PROTOCOL.json'),'model_sha256':sha(OUT/'model.joblib'),'generator_sha256':sha(ROOT/'scripts/generate_data.py'),'source_files_sha256':{name:sha(ROOT/name) for name in ['backend/app/model48_v3.py','scripts/model48_v3_data.py','scripts/train_model48_v3.py']},'selected_candidate':spec['name'],'features':model.features,'candidates':scores,'calibration':calibration,'operating_point':operating,'partitions':{'train':train_meta,'selection':val_meta,'calibration':cal_meta,'threshold':threshold_meta},'fresh_audit_not_generated':True,'original_or_v2_test_used_for_selection':False,'previous_v2_failure_disclosed':True}
    (OUT/'FROZEN.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['candidates','partitions','features']},indent=2))
if __name__=='__main__':run()
