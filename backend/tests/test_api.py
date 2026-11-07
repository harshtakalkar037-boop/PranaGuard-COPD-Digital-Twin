import json
import numpy as np
import pandas as pd
import pytest
from backend.app.features import add_features,FEATURES,risk_category
from backend.app.engine import TwinEngine
from scripts.train import split_masks

@pytest.mark.parametrize('path',['/api/health','/api/overview','/api/patients','/api/status','/api/validation','/api/replay','/openapi.json'])
def test_read_endpoints(client,path):
    r=client.get(path);assert r.status_code==200;assert r.json()

def test_patient_label_and_predictions(client,engine):
    pid=engine.demo['patient_id'];r=client.get(f'/api/patients/{pid}');assert r.status_code==200
    d=r.json();assert d['synthetic'] and d['profile']['synthetic'];assert set(d['risks'])=={'24','48','72'}
    for h in [24,48,72]:
        actual=engine.models[h].predict(pd.DataFrame([d['features']]))[0]
        assert d['risks'][str(h)]==pytest.approx(actual)
        assert 0<=actual<=1
    assert not any(k in d['features'] for k in ['patient_id','hour','timestamp','event_onset','active_episode','label_24','label_48','label_72'])

def test_patient_search(client,engine):
    result=client.get('/api/patients?q=PG-0071').json()['patients'];assert len(result)==1
    assert client.get('/api/patients?q=DOES_NOT_EXIST').json()['patients']==[]
    assert all(p['risk_category']=='elevated' for p in client.get('/api/patients?risk=elevated').json()['patients'])

def test_not_found(client):
    assert client.get('/api/patients/no-such-id').status_code==404
    assert client.get('/api/patients/PG-0001?version=999999').status_code==404
    assert client.patch('/api/alerts/999999',json={'status':'resolved'}).status_code==404

def test_deterministic_replay(client,engine):
    pid=engine.demo['patient_id'];first=engine.patient(pid)
    engine.step(3);after=engine.patient(pid);assert after['version']==first['version']+3
    engine.reset(first['hour']);engine.step(3);assert engine.patient(pid)==after
    history=client.get(f'/api/patients/{pid}/history').json();assert len(history['versions'])==4
    observed=history['observations'];assert sum(x['risk_72'] is not None for x in observed)==4
    assert client.get(f'/api/patients/{pid}?version=1').json()==first

def test_state_persists_restart(client,engine):
    pid=engine.demo['patient_id'];engine.step();before=engine.patient(pid)
    # New store instance simulates reopening the connection after process restart.
    from backend.app.store import Store
    reopened=Store(engine.store.path)
    assert reopened.latest(pid)==before;assert reopened.meta('cursor')==engine.cursor

def test_shap_additivity(client,engine):
    pid=engine.demo['patient_id'];e=client.get(f'/api/patients/{pid}/explanation?horizon=72')
    assert e.status_code==200,e.text;d=e.json()
    assert 'TreeSHAP' in d['method'];assert len(d['drivers'])==len(FEATURES)
    assert d['base_value']+sum(x['contribution'] for x in d['drivers'])==pytest.approx(d['raw_margin'])
    engine.step();next_e=client.get(f'/api/patients/{pid}/explanation?horizon=24').json()
    assert next_e['risk_change'] is not None;assert any(x['contribution_change'] is not None for x in next_e['drivers'])

def test_scenario_preserves_state_and_has_real_outputs(client,engine):
    pid=engine.demo['patient_id'];before=engine.patient(pid);versions=engine.store.versions(pid)
    r=client.post(f'/api/patients/{pid}/scenarios',json={'pm25_change_pct':-40,'adherence':.95,'activity_multiplier':1.1})
    assert r.status_code==200,r.text;d=r.json();assert d['original_state_preserved']
    assert engine.patient(pid)==before;assert engine.store.versions(pid)==versions
    assert len(d['trajectory'])==8 and set(d['baseline_risks'])=={'24','48','72'}
    assert d['trajectory'][0]['baseline_72']==before['risks']['72']
    assert any(abs(x['baseline_24']-x['scenario_24'])>1e-9 for x in d['trajectory'][1:])
    assert len(client.get(f'/api/patients/{pid}/scenarios').json()['scenarios'])==1

def test_scenario_does_not_use_future_records(client,engine):
    pid=engine.demo['patient_id'];args={'pm25_change_pct':-30,'adherence':.9,'activity_multiplier':1.0}
    one=engine.scenario(pid,args)['trajectory'];saved=engine.raw.copy()
    try:
        mask=(engine.raw.patient_id==pid)&(engine.raw.hour>engine.cursor)
        engine.raw.loc[mask,['pm25','spo2','heart_rate']]=99999
        assert engine.scenario(pid,args)['trajectory']==one
    finally:engine.raw=saved

def test_no_change_assumptions_match_baseline(client,engine):
    pid=engine.demo['patient_id'];current=engine.patient(pid)['current']
    d=engine.scenario(pid,{'pm25_change_pct':0,'adherence':current['adherence'],'activity_multiplier':1})
    assert d['baseline_risks']==d['scenario_risks']

@pytest.mark.parametrize('body',[{'pm25_change_pct':-90},{'adherence':1.1},{'activity_multiplier':2},{'unknown':1},{'pm25_change_pct':'not-a-number'}])
def test_scenario_validation(client,engine,body):
    assert client.post(f'/api/patients/{engine.demo["patient_id"]}/scenarios',json=body).status_code==422

def test_real_model_alert_lifecycle(client,engine):
    engine.reset(engine.demo['focus_hour']);alerts=engine.store.alerts(engine.demo['patient_id']);assert alerts
    alert=alerts[0];assert alert['risk']>=.35
    assert alert['risk']==engine.patient(alert['patient_id'])['risks']['72']
    iid=alert['id'];assert client.patch(f'/api/alerts/{iid}',json={'status':'acknowledged','note':'Synthetic review'}).status_code==200
    assert client.patch(f'/api/alerts/{iid}',json={'status':'resolved'}).status_code==200
    assert client.patch(f'/api/alerts/{iid}',json={'status':'acknowledged'}).status_code==409
    assert any(a['id']==iid and a['status']=='resolved' for a in engine.store.alerts())

def test_intervention_persistence(client,engine):
    pid=engine.demo['patient_id'];before=engine.patient(pid)
    r=client.post(f'/api/patients/{pid}/interventions',json={'kind':'clinical_review','note':'Reviewed synthetic risk; no clinical recommendation.'});assert r.status_code==200
    items=client.get(f'/api/patients/{pid}/interventions').json()['interventions'];assert len(items)==1
    assert items[0]['state_version']==before['version'];assert engine.patient(pid)==before
    assert client.post(f'/api/patients/{pid}/interventions',json={'kind':'dose','note':'x'}).status_code==422

def test_replay_endpoints_and_bounds(client,engine):
    old=engine.cursor;assert client.post('/api/replay/step',json={'hours':2}).status_code==200;assert engine.cursor==old+2
    assert client.post('/api/replay/step',json={'hours':0}).status_code==422
    assert client.post('/api/replay/start').json()['running'];assert not client.post('/api/replay/pause').json()['running']
    assert client.post('/api/replay/reset',json={'prime_hours':3}).json()['version']==4
    assert client.post('/api/replay/reset',json={'hour':73,'prime_hours':24}).status_code==422
    engine.reset(engine.max_hour);assert client.post('/api/replay/step',json={'hours':1}).status_code==422

def test_websocket(client):
    with client.websocket_connect('/api/ws') as ws:
        assert ws.receive_json()['type']=='connected';ws.send_text('ping');assert ws.receive_json()['type']=='pong'

def test_optional_write_authorization(client,engine,monkeypatch):
    monkeypatch.setenv('PRANAGUARD_ADMIN_TOKEN','unit-test-only-token')
    assert client.post('/api/replay/step',json={'hours':1}).status_code==401
    assert client.post('/api/replay/step',json={'hours':1},headers={'X-Demo-Token':'unit-test-only-token'}).status_code==200

def test_causal_features_and_calibration(client,engine):
    raw=engine.raw[engine.raw.patient_id=='PG-0001'].copy()
    a=add_features(raw);b=add_features(raw[raw.hour<=200])
    np.testing.assert_allclose(a[a.hour==200][FEATURES],b[b.hour==200][FEATURES],equal_nan=True)
    changed=raw.copy();changed.loc[changed.hour>200,['spo2','heart_rate','pm25']]=1000
    c=add_features(changed);np.testing.assert_allclose(a[a.hour==200][FEATURES],c[c.hour==200][FEATURES],equal_nan=True)
    assert a.loc[a.hour==200,'spo2_baseline'].iloc[0]==raw[raw.hour<72].spo2.median()

def test_split_leakage_guards(client,engine):
    x=engine.frame.reset_index(drop=True);tm,cm,em,info=split_masks(x)
    t=x[tm];c=x[cm];e=x[em]
    assert not set(t.patient_id)&set(c.patient_id);assert not set(t.patient_id)&set(e.patient_id)
    assert t.hour.max()+72<c.hour.min();assert c.hour.max()+72<e.hour.min()
    assert t.hour.min()>=72;assert all(col not in FEATURES for col in ['patient_id','hour','label_24','event_onset','city'])

def test_metrics_are_recomputed_from_predictions(client,engine):
    from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss
    from backend.app.config import ARTIFACTS
    preds=pd.read_csv(ARTIFACTS/'test_predictions.csv.gz')
    for h in [24,48,72]:
        d=engine.evaluation['diagnostics'][str(h)]['metrics'];y=preds[f'label_{h}'];p=preds[f'risk_{h}']
        assert d['auroc']==pytest.approx(roc_auc_score(y,p));assert d['auprc']==pytest.approx(average_precision_score(y,p));assert d['brier']==pytest.approx(brier_score_loss(y,p))

def test_database_transaction_rollback(client,engine):
    before=engine.store.meta('cursor')
    with pytest.raises(RuntimeError):
        with engine.store.connect() as c:
            c.execute('UPDATE meta SET value=? WHERE key=?',('999','cursor'));raise RuntimeError('forced rollback')
    assert engine.store.meta('cursor')==before

def test_missingness_and_freshness_reported(client,engine):
    status=client.get('/api/status').json();assert status['network_required'] is False
    assert status['live_patient_feed'] is False;assert len(status['environment_sources'])==8
    assert status['database']['counts']['patients']>=30
    co=client.get('/api/overview').json();assert len(co['trend'])>=1 and co['synthetic']
    assert sum(co['summary'][k] for k in ['low','elevated','high'])==co['summary']['total']

@pytest.mark.parametrize('p,category',[(0,'low'),(.149,'low'),(.15,'elevated'),(.349,'elevated'),(.35,'high'),(1,'high')])
def test_risk_categories(p,category):assert risk_category(p)==category

def test_ingestion_validated_before_features(client,engine):
    from backend.app.validation import validate_longitudinal
    assert validate_longitudinal(engine.raw)['validated']
    bad=engine.raw.iloc[:1440].copy();bad.loc[0,'spo2']=150
    with pytest.raises(ValueError,match='spo2'):validate_longitudinal(bad)

def test_ingestion_rejects_duplicate_hours(client,engine):
    from backend.app.validation import validate_longitudinal
    bad=pd.concat([engine.raw.iloc[:1440],engine.raw.iloc[:1]])
    with pytest.raises(ValueError,match='Duplicate'):validate_longitudinal(bad)

def test_ingestion_rejects_misaligned_time(client,engine):
    from backend.app.validation import validate_longitudinal
    bad=engine.raw.iloc[:1440].copy();bad.loc[0,'hour']=1500
    with pytest.raises(ValueError,match='alignment'):validate_longitudinal(bad)

def test_ingestion_rejects_missing_environment(client,engine):
    from backend.app.validation import validate_longitudinal
    bad=engine.raw.iloc[:1440].copy();bad.loc[0,'pm25']=np.nan
    with pytest.raises(ValueError,match='missing'):validate_longitudinal(bad)
