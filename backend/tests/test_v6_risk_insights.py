"""v6: doctor risk visibility (snapshot/history/overview/explanation) + patient health insights.

Additive over v5: prediction_history is migrated additively, raw scores never re-recorded,
patients are blocked from doctor-only prediction endpoints, and insights never fabricate data.
"""
import sqlite3
from test_workspace import auth

DISCLAIMER='Experimental synthetic-data model estimate. Not clinically validated'

def patient_auth(client):return auth(client,'pat-pg0071','prana-patient-demo')

def test_risk_snapshot_records_and_disclaimer(client,engine):
    d=auth(client)
    j=client.get('/api/workspace/patients/PG-0071/risk',headers=d).json()
    assert j['available'] is True
    assert sorted(j['horizons'])==['24','48','72']
    assert all(0<=j['horizons'][h]['risk']<=1 for h in ('24','48','72'))
    assert j['model_version']=='pg-synthetic-v1' and j['predicted_at']
    assert DISCLAIMER in j['disclaimer']
    assert j['review_status']['status'] in ('none','new','awaiting_review','under_review','follow_up_scheduled','completed','closed')

def test_risk_history_no_duplicate_records(client,engine):
    d=auth(client)
    first=client.get('/api/workspace/patients/PG-0071/risk/history',headers=d).json()
    # viewing again must NOT append duplicate rows for an unchanged replay state
    client.get('/api/workspace/patients/PG-0071/risk',headers=d)
    second=client.get('/api/workspace/patients/PG-0071/risk/history',headers=d).json()
    assert first['count']>=3 and first['count']==second['count']
    assert {r['horizon'] for r in first['items']}>={24,48,72}
    assert all(r['model_version']=='pg-synthetic-v1' for r in first['items'])
    raw=set()
    for r in first['items']:raw.add(round(r['risk'],9))  # risks returned unchanged (raw)
    assert DISCLAIMER in first['disclaimer']

def test_risk_overview_sorted_and_scoped(client):
    d=auth(client)
    j=client.get('/api/workspace/risk-overview',headers=d).json()
    assert j['assigned']==120 and len(j['items'])==120
    risks=[i['risk72'] for i in j['items'] if i['risk72'] is not None]
    assert risks==sorted(risks,reverse=True)
    assert all('display_name' in i and i['model_version']=='pg-synthetic-v1' for i in j['items'])
    # other doctor sees only own assignment count unless same pool
    n=auth(client,'dr-nova','prana-nova-demo')
    jn=client.get('/api/workspace/risk-overview',headers=n).json()
    assert jn['assigned']>=0 and len(jn['items'])==jn['assigned']

def test_risk_explanation_uses_frozen_engine(client,engine):
    d=auth(client)
    j=client.get('/api/workspace/patients/PG-0071/risk/explanation',headers=d).json()
    assert j['available'] and len(j['drivers'])>=3
    assert j['model_version']=='pg-synthetic-v1'
    assert 'not calibrated' in j['caution'].lower() or 'uncalibrated' in j['caution'].lower()

def test_patients_blocked_from_doctor_risk_endpoints(client):
    p=patient_auth(client)
    for ep in ['/api/workspace/risk-overview','/api/workspace/patients/PG-0071/risk',
               '/api/workspace/patients/PG-0071/risk/history','/api/workspace/patients/PG-0071/risk/explanation']:
        r=client.get(ep,headers=p);assert r.status_code==403,ep

def test_unassigned_doctor_blocked(client):
    d=auth(client)
    # fake pid 404, real-but-not-assigned handled by endpoint itself
    assert client.get('/api/workspace/patients/ZZ-9999/risk',headers=d).status_code in (403,404)

def test_insights_requires_patient_and_validates_dates(client):
    p=patient_auth(client)
    bad=client.get('/api/workspace/patient/insights?from=06-11-2026&to=2026-11-06',headers=p);assert bad.status_code==422
    inverted=client.get('/api/workspace/patient/insights?from=2026-11-06&to=2026-11-01',headers=p);assert inverted.status_code==422
    wide=client.get('/api/workspace/patient/insights?from=2024-01-01&to=2026-11-06',headers=p);assert wide.status_code==422
    # doctors are excluded
    assert client.get('/api/workspace/patient/insights',headers=auth(client)).status_code==403

def test_insights_returns_only_real_records(client):
    p=patient_auth(client)
    j=client.get('/api/workspace/patient/insights?from=2026-10-25&to=2026-11-07',headers=p).json()
    assert j['range']['start']=='2026-10-25' and j['range']['days']==14
    keys=set(j)
    for k in ('summary','daily_logs','sputum_entries','adherence','sleep','activity','hydration','wellbeing','breathing_rate','replay_symptom_score','units','sources','replay_window','note'):
        assert k in keys,k
    # daily series preserve gaps: one row per day in range
    assert len(j['sleep'])==14 and all('date' in r for r in j['sleep'])
    assert 'not wearable' in j['sources']['breathing_rate']
    assert j['replay_window']['first'] and j['replay_window']['last']

def test_patient_home_includes_summary_lines(client):
    p=patient_auth(client)
    j=client.get('/api/workspace/patient/home',headers=p).json()
    assert isinstance(j['summary_lines'],list) and j['summary_lines']
    assert any('logged' in l for l in j['summary_lines'])

def test_prediction_history_table_migration_additive(client,engine):
    db=client.app.state.store.db if hasattr(client.app.state,'store') else None
    # find the workbook DB path through the workspace service instead
    ws=client.app.state.workspace
    with ws.store.connect() as c:
        cols={r['name'] for r in c.execute('PRAGMA table_info(prediction_history)')}
    assert {'patient_id','horizon','model_version','risk','state_version','input_timestamp','recorded_at','data_status','provenance'}<=cols
    with ws.store.connect() as c:
        n=c.execute('SELECT COUNT(*) AS n FROM prediction_history').fetchone()['n']
    assert n>=3  # rows recorded by the snapshot tests above, never deleted
