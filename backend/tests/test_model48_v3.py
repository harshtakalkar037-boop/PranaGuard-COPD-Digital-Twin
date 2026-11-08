"""Causality, frozen science and additive versioned48h inference contracts."""
import hashlib,json
from datetime import datetime
import joblib,numpy as np,pandas as pd,pytest
from scipy.special import expit
from fastapi import HTTPException
from backend.app.config import ROOT
from backend.app.features import FEATURES,add_features
from backend.app.model48_v3 import ALL,CANDIDATES,features_v3,VERSION
from scripts.audit_model48 import metrics

@pytest.fixture(scope='module')
def raw3():return pd.read_csv(ROOT/'data/synthetic_longitudinal.csv.gz',nrows=1440)
@pytest.fixture(scope='module')
def model3():return joblib.load(ROOT/'artifacts/model48_v3/model.joblib')

def test_v3_features_are_strictly_causal(raw3):
    full=features_v3(raw3);past=features_v3(raw3[raw3.hour<=200]);np.testing.assert_allclose(full.loc[full.hour==200,ALL],past.loc[past.hour==200,ALL],equal_nan=True)

def test_v3_future_measurements_cannot_change_risk(raw3,model3):
    changed=raw3.copy();changed.loc[changed.hour>200,['spo2','heart_rate','resp_rate','symptom_score','sleep_hours','steps','adherence','pm25','temperature','humidity']]=9999
    a=features_v3(raw3);b=features_v3(changed);np.testing.assert_allclose(model3.predict(a[a.hour==200]),model3.predict(b[b.hour==200]),rtol=0,atol=0)

def test_v3_hidden_truth_and_identifiers_not_predictors(raw3):
    changed=raw3.copy()
    for key in ['event_onset','active_episode','eligible','label_24','label_48','label_72','latent_load']:changed[key]=999
    a=features_v3(raw3);b=features_v3(changed);np.testing.assert_allclose(a[ALL],b[ALL],equal_nan=True)
    assert not set(ALL)&{'patient_id','hour','timestamp','event_onset','active_episode','eligible','label_24','label_48','label_72','latent_load'}

def test_v3_does_not_modify_original_features(raw3):pd.testing.assert_frame_equal(add_features(raw3)[FEATURES],features_v3(raw3)[FEATURES])

def test_v3_baseline_sd_and_recovery_calculations(raw3):
    frame=features_v3(raw3);row=frame[frame.hour==200].iloc[0];baseline=raw3[raw3.hour<72].spo2
    expected=-(raw3[raw3.hour.between(177,200)].spo2.mean()-baseline.median())/max(.05,baseline.std())
    assert row.v3_spo2_z24==pytest.approx(expected)
    expected_peak=frame[frame.hour.between(57,200)].v3_body_index6.max()-row.v3_body_index6;assert row.v3_peak144_minus_now==pytest.approx(expected_peak)

def test_v3_exact_calibrated_treeshap(raw3,model3):
    frame=features_v3(raw3);row=frame[frame.hour==200];e=model3.explain(row)
    assert 'TreeSHAP' in e['method'] and 'not probability' in e['units']
    assert e['base_value']+sum(d['contribution'] for d in e['drivers'])==pytest.approx(e['calibrated_margin'],abs=1e-12)
    assert expit(e['calibrated_margin'])==pytest.approx(model3.predict(row)[0],abs=1e-12)
    assert 0<=e['probability']<=1 and model3.calibration['slope']>0

def test_v3_missing_inputs_use_fitted_training_imputation(raw3,model3):
    frame=features_v3(raw3);row=frame[frame.hour==200].copy();row[model3.features]=np.nan
    p=model3.predict(row)[0];assert np.isfinite(p) and 0<=p<=1
    assert model3.explain(row)['probability']==pytest.approx(p)

def test_v3_protocol_seeds_separation_and_candidate_selection():
    p=json.loads((ROOT/'docs/model-v3/PROTOCOL.json').read_text());f=json.loads((ROOT/'artifacts/model48_v3/FROZEN.json').read_text());parts=list(p['development'].values())+[p['audit']];seeds=[seed for spec in parts for seed in spec['seeds']]
    assert len(seeds)==len(set(seeds))==6
    assert p['development']['train']['hours'][1]+72<p['development']['selection']['hours'][0]
    assert p['development']['threshold']['hours'][1]+72<p['audit']['hours'][0]
    assert sum(part['patients'] for part in f['partitions'].values())==1120 and f['partitions']['train']['patients']==640
    assert [c['name'] for c in CANDIDATES]==p['candidates']
    assert max(f['candidates'],key=lambda c:c['selection_auprc'])['candidate']==f['selected_candidate']
    assert not f['original_or_v2_test_used_for_selection'] and f['previous_v2_failure_disclosed']

def test_v3_artifact_and_source_frozen_before_audit():
    folder=ROOT/'artifacts/model48_v3';f=json.loads((folder/'FROZEN.json').read_text());a=json.loads((folder/'AUDIT.json').read_text());p=json.loads((ROOT/'docs/model-v3/PROTOCOL.json').read_text())
    assert datetime.fromisoformat(f['created_at'])<datetime.fromisoformat(a['created_at'])
    assert f['fresh_audit_not_generated'] and a['model_sha256']==f['model_sha256']==hashlib.sha256((folder/'model.joblib').read_bytes()).hexdigest()
    assert f['protocol_sha256']==hashlib.sha256((ROOT/'docs/model-v3/PROTOCOL.json').read_bytes()).hexdigest()
    for name,sha in {**p['all_source_code_before_fit'],**f['source_files_sha256']}.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha

def test_v3_saved_audit_metrics_and_gates_are_reproducible():
    folder=ROOT/'artifacts/model48_v3';a=json.loads((folder/'AUDIT.json').read_text());saved=pd.read_csv(folder/'audit_predictions.csv.gz');old=metrics(saved.label_48,saved.original_risk48,.35);new=metrics(saved.label_48,saved.revised_risk48,a['fresh_audit']['revised']['threshold'])
    for key,m in [('original',old),('revised',new)]:
        for score in ['auroc','auprc','brier','recall','precision','false_positive_rate']:assert m[score]==pytest.approx(a['fresh_audit'][key][score],abs=1e-12)
    assert new['auprc']>=1.1*old['auprc'] and new['auroc']>=old['auroc'] and new['brier']<=old['brier']+.0001 and new['recall']>0 and new['false_positive_rate']<=.15
    assert a['experimental_available'] and all(a['gate_checks'].values()) and a['status']=='EXPERIMENTAL_GATE_PASS'
    assert saved.patient_id.nunique()==240 and len(saved)==45941 and not a['clinical_validation']
    assert a['fresh_audit']['uncertainty']['ci95']['difference_auroc'][0]<0

def test_v3_prior_failed_study_is_not_relabelled():
    a=json.loads((ROOT/'artifacts/model48_v2/AUDIT_EVALUATION.json').read_text());assert a['status']=='GATE_NOT_PASSED' and not a['experimental_available']
    prior=json.loads((ROOT/'docs/model-v3/BASE_V2_PROTECTED.json').read_text())
    for name,sha in prior.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha

def test_v3_readonly_api_preserves_legacy_states_and_history(client,engine):
    pid=engine.demo['patient_id'];before=engine.patient(pid);history=engine.history(pid);alerts=engine.store.alerts(pid)
    r=client.get('/api/model48/v3/patients/'+pid);assert r.status_code==200,r.text;d=r.json()
    assert d['model_version']==VERSION and d['state_version']==before['version'] and d['hour']==before['hour'] and d['original_risk48']==before['risks']['48'] and d['persisted'] is False
    assert d['explanation']['probability']==pytest.approx(d['probability'])
    assert engine.patient(pid)==before and engine.history(pid)==history and engine.store.alerts(pid)==alerts
    assert client.get('/api/health').json()['model_version']=='pg-synthetic-v1'
    assert client.post('/api/model48/v3/patients/'+pid,json={}).status_code==405

def test_v3_saved_version_not_latest_version_is_explained(client,engine):
    pid=engine.demo['patient_id'];first=engine.patient(pid);engine.step()
    d=client.get(f'/api/model48/v3/patients/{pid}?version={first["version"]}').json();assert d['state_version']==first['version'] and d['hour']==first['hour'] and d['original_risk48']==first['risks']['48']
    assert client.get('/api/model48/v3/patients/'+pid).json()['state_version']==first['version']+1

def test_v3_query_and_new_patient_bounds(client):
    assert client.get('/api/model48/v3/patients/PG-0071?version=0').status_code==422
    assert client.get('/api/model48/v3/patients/PG-0071?version=999999').status_code==404
    for pid in ['fictional-new-registration','not-found','DEMO-MANUAL']:
        assert client.get('/api/model48/v3/patients/'+pid).status_code==404

def test_v3_unsupported_episode_withholds_risk_and_explanation(client,engine):
    pid=engine.demo['patient_id'];source=engine.raw[(engine.raw.patient_id==pid)&(engine.raw.hour>=72)&(engine.raw.active_episode==1)];assert len(source)
    engine.reset(int(source.hour.iloc[0]));d=client.get('/api/model48/v3/patients/'+pid).json()
    assert not d['prediction_supported'] and d['probability'] is None and d['explanation'] is None and d['above_demo_cutoff'] is None

def test_v3_missing_evidence_fails_closed_without_breaking_legacy(client,tmp_path,monkeypatch):
    import backend.app.model48_v3_api as service
    monkeypatch.setattr(service,'ROOT',tmp_path)
    assert client.get('/api/model48/v3/study').status_code==503 and client.get('/api/model48/v3/patients/PG-0071').status_code==503
    assert client.get('/api/health').status_code==200 and len(client.get('/api/patients/PG-0071').json()['risks'])==3

def test_v3_report_is_versioned_and_read_only(client):
    d=client.get('/api/model48/v3/study').json();assert d['model_version']==VERSION and d['experimental_available'] and not d['legacy_states_rewritten']
    assert len(d['candidates'])==6 and d['legacy_endpoint_model']=='pg-synthetic-v1'
    assert client.post('/api/model48/v3/study',json={'activate':True}).status_code==405


def test_v3_gate_failure_refuses_inference_even_after_service_cached(client,monkeypatch):
    import backend.app.model48_v3_api as service
    frozen,audit=service.evidence()
    client.app.state.model48_v3=service.Service48V3(client.app.state.engine)
    monkeypatch.setattr(service,'evidence',lambda:(frozen,{**audit,'experimental_available':False}))
    assert client.get('/api/model48/v3/patients/PG-0071').status_code==503
    assert client.get('/api/patients/PG-0071').status_code==200
