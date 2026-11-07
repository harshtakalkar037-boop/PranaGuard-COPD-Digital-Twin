"""Care workspace: demo auth, doctor scoping/isolation, review workflow, plans, sputum, activity."""
import base64,json,hashlib
import pytest

def login(client,username,password):return client.post('/api/workspace/login',json={'username':username,'password':password})
def auth(client,username='dr-atlas',password='prana-atlas-demo'):
    r=login(client,username,password);assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def test_login_logout_and_me(client):
    h=auth(client);me=client.get('/api/workspace/me',headers=h);assert me.status_code==200
    u=me.json()['user'];assert u['username']=='dr-atlas' and u['role']=='doctor' and u['assigned_patients']==120
    assert client.post('/api/workspace/logout',headers=h).status_code==200
    assert client.get('/api/workspace/me',headers=h).status_code==401

def test_wrong_password_and_no_token(client):
    assert login(client,'dr-atlas','wrong-password').status_code==401
    assert client.get('/api/workspace/me').status_code==401
    assert client.get('/api/workspace/patients').status_code==401
    assert 'token_hash' not in client.get('/openapi.json').text  # no raw token/hash exposure anywhere

def test_directory_search_filter_paginate_sort(client):
    h=auth(client);r=client.get('/api/workspace/patients?page=1&page_size=10',headers=h).json()
    assert r['total']==120 and len(r['items'])==10 and r['assigned']==120
    match=[p for p in client.get('/api/workspace/patients?q=PG-0071',headers=h).json()['items']]
    assert len(match)==1 and match[0]['patient_id']=='PG-0071' and match[0]['origin']=='historical_twin'
    assert client.get('/api/workspace/patients?q=NOPE',headers=h).json()['total']==0
    pune=client.get('/api/workspace/patients?city=Pune',headers=h).json();assert pune['total']>0 and all(p['city']=='Pune' for p in pune['items'])
    byrisk=client.get('/api/workspace/patients?sort=risk&page_size=50',headers=h).json()['items']
    vals=[p['risk72'] for p in byrisk if p['risk72'] is not None];assert vals==sorted(vals,reverse=True)
    demo=client.post('/api/enhanced/registry/patients',json={'request_id':'WS-DEMO-0001','fictional_identity_confirmed':True,'demo_alias':'Mira Testcase','age':61,'city':'Pune'})
    if demo.status_code in (401,403):
        # Admin token not configured or configured: retry with header absent-token failure expected only when configured.
        assert demo.status_code==200 or demo.status_code==401

def test_two_doctor_isolation(client):
    atlas=auth(client);nova=auth(client,'dr-nova','prana-nova-demo')
    d=client.get('/api/workspace/patients',headers=nova).json();assert d['total']==0 and d['items']==[]
    assert client.get('/api/workspace/patients/PG-0071',headers=nova).status_code==403
    assert client.get('/api/workspace/patients/PG-0071',headers=atlas).status_code==200
    o=client.get('/api/workspace/overview',headers=nova).json();assert o['summary']['total']==0 and o['trend']==[]
    o2=client.get('/api/workspace/overview',headers=atlas).json();assert o2['summary']['total']==120 and o2['scope']['excluded_from_view']==0
    # Doctor B cannot act on Doctor A's patient anywhere.
    assert client.post('/api/workspace/care/reviews',headers=nova,json={'patient_id':'PG-0071','note':'should fail'}).status_code==403
    assert client.put('/api/workspace/patients/PG-0071/plan',headers=nova,json={'goals':'x'*5}).status_code==403

def test_patient_role_scoping(client):
    p=auth(client,'pat-pg0071','prana-patient-demo');me=client.get('/api/workspace/me',headers=p).json()['user']
    assert me['role']=='patient' and me['patient_id']=='PG-0071'
    d=client.get('/api/workspace/patients',headers=p).json();assert d['total']==1
    assert client.get('/api/workspace/patients/PG-0072',headers=p).status_code==403

def test_review_workflow_persists_and_validates_transitions(client):
    h=auth(client)
    r=client.post('/api/workspace/care/reviews',headers=h,json={'patient_id':'PG-0071','note':'Initial synthetic review'}).json()['review']
    assert r['status']=='awaiting_review'
    rid=r['id']
    assert client.patch(f'/api/workspace/care/reviews/{rid}',headers=h,json={'status':'completed'}).status_code==409  # no skip
    assert client.patch(f'/api/workspace/care/reviews/{rid}',headers=h,json={'status':'under_review','note':'taking it'}).status_code==200
    assert client.patch(f'/api/workspace/care/reviews/{rid}',headers=h,json={'status':'follow_up_scheduled'}).status_code==422  # needs date
    from datetime import datetime,timezone,timedelta
    later=(datetime.now(timezone.utc)+timedelta(days=3)).isoformat()
    assert client.patch(f'/api/workspace/care/reviews/{rid}',headers=h,json={'status':'follow_up_scheduled','follow_up_at':later}).status_code==200
    assert client.patch(f'/api/workspace/care/reviews/{rid}',headers=h,json={'status':'completed'}).status_code==200
    assert client.patch(f'/api/workspace/care/reviews/{rid}',headers=h,json={'status':'under_review'}).status_code==409
    detail=client.get(f'/api/workspace/care/reviews/{rid}',headers=h).json()
    assert len(detail['timeline'])>=4 and 'Initial synthetic review' in detail['review']['note']
    listed=client.get('/api/workspace/care/reviews?patient_id=PG-0071',headers=h).json();assert any(x['id']==rid for x in listed['items'])
    # persisted for the same doctor after a fresh read (survives refresh/reopen)
    assert client.get(f'/api/workspace/care/reviews/{rid}',headers=auth(client)).json()['review']['status']=='completed'
    # other doctor never sees it
    assert client.get(f'/api/workspace/care/reviews/{rid}',headers=auth(client,'dr-nova','prana-nova-demo')).status_code==403

def test_care_summary_counts_match_records(client):
    h=auth(client);before=client.get('/api/workspace/care/summary',headers=h).json()
    r=client.post('/api/workspace/care/reviews',headers=h,json={'patient_id':'PG-0072','note':'Summary counter check'})
    assert r.status_code==200
    after=client.get('/api/workspace/care/summary',headers=h).json()
    assert after['pending_reviews']==before['pending_reviews']+1 and after['assigned_patients']==120
    empty=client.get('/api/workspace/care/summary',headers=auth(client,'dr-nova','prana-nova-demo')).json()
    assert empty=={'assigned_patients':0,'pending_reviews':0,'reviews_in_progress':0,'completed_reviews':0,'follow_ups_due':0,'open_notifications':0,'recent_reviews':[],'note':empty['note']}

def test_care_plan_save_reopen_revision(client):
    h=auth(client);pid='PG-0073'
    p=client.put(f'/api/workspace/patients/{pid}/plan',headers=h,json={'goals':'Walk 20 minutes daily as tolerated (documentation only).','status':'active','review_date':'2099-01-01'})
    assert p.status_code==200 and p.json()['plan']['status']=='active'
    reopen=client.get(f'/api/workspace/patients/{pid}/plan',headers=h).json();assert reopen['plan']['goals'].startswith('Walk')
    p2=client.put(f'/api/workspace/patients/{pid}/plan',headers=h,json={'goals':'Updated demo plan goals.','status':'active','change_note':'Adjusted after demo review'})
    assert p2.status_code==200
    again=client.get(f'/api/workspace/patients/{pid}/plan',headers=h).json()
    assert again['plan']['goals']=='Updated demo plan goals.' and len(again['revisions'])==1 and again['revisions'][0]['change_note']=='Adjusted after demo review'
    assert client.get(f'/api/workspace/patients/{pid}',headers=h).json()['care_plan']['status']=='active'
    assert client.put(f'/api/workspace/patients/{pid}/plan',headers=h,json={'goals':'xx','status':'draft'}).status_code==422

def test_sputum_diary_with_attachment_and_review(client):
    h=auth(client);pid='PG-0074'
    png=base64.b64encode(bytes.fromhex('89504e470d0a1a0a')+b'\x00'*64).decode()
    body={'occurred_at':'2026-11-06T08:30:00+00:00','colour':'yellow','volume':'moderate','consistency':'thick','cough':6,'breathlessness':4,'note':'Demo diary entry','attachment':{'filename':'note.png','media_type':'image/png','data_base64':png}}
    r=client.post(f'/api/workspace/patients/{pid}/sputum',headers=h,json=body);assert r.status_code==200,r.text
    eid=r.json()['id'];assert r.json()['attachment_sha256_12']
    listed=client.get(f'/api/workspace/patients/{pid}/sputum',headers=h).json()
    assert listed['total']==1 and listed['items'][0]['attachment']['media_type']=='image/png'
    img=client.get(f"/api/workspace/attachments/{listed['items'][0]['attachment']['id']}",headers=h)
    assert img.status_code==200 and img.headers['content-type']=='image/png' and img.content[:4]==bytes.fromhex('89504e47')
    ok=client.patch(f'/api/workspace/sputum/{eid}/review',headers=h,json={'note':'Reviewed demo entry'});assert ok.status_code==200
    assert client.patch(f'/api/workspace/sputum/{eid}/review',headers=h,json={'note':'again'}).status_code==409
    assert 'documentation only' in client.post(f'/api/workspace/patients/{pid}/sputum',headers=h,json={**body,'attachment':None}).json()['notice']
    bad={**body,'breathlessness':11,'attachment':None};assert client.post(f'/api/workspace/patients/{pid}/sputum',headers=h,json=bad).status_code==422

def test_activity_aggregates_real_records_only(client):
    h=auth(client);pid='PG-0075'
    client.post(f'/api/enhanced/registry/patients/{pid}/observations',json={'fictional_data_confirmed':True,'symptom_score':2,'adherence':.8,'note':'baseline day'})
    a=client.get(f'/api/workspace/patients/{pid}/activity',headers=h).json()
    assert a['manual_entries']>=1 and a['series'] and 'simulated device' in a['sources'] 

def test_profile_aggregate_and_boundaries(client):
    h=auth(client);p=client.get('/api/workspace/patients/PG-0071',headers=h).json()
    assert p['model_state']['version'] and set(p['model_state']['risks'])=={'24','48','72'}
    assert p['baseline']['complete'] and p['notifications']['counts'] is not None
    assert p['model_state']['prediction_supported'] in (True,False)
    assert client.get('/api/workspace/patients/UNKNOWN',headers=h).status_code==403  # not assigned ⇒ forbidden, no existence leak
    assert 'not diagnoses' in p['caution']

def test_original_routes_untouched_by_workspace(client):
    # Research/original API behaves exactly as before (no auth added to them).
    assert client.get('/api/overview').json()['summary']['total']==120
    assert client.get('/api/patients/PG-0071').status_code==200
    assert client.get('/api/validation').status_code==200

def test_no_fake_activation(client):
    h=auth(client);assert client.post('/api/workspace/activate-model',headers=h).status_code==404


def test_workspace_me_authorization_cors_preflight(client):
    response = client.options(
        '/api/workspace/me',
        headers={
            'Origin': 'https://prana-guard-copd-digital-twin.vercel.app',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'authorization,content-type',
        },
    )
    assert response.status_code == 200, response.text
    assert response.headers.get('access-control-allow-origin') in (
        'https://prana-guard-copd-digital-twin.vercel.app', '*'
    )
    allowed = response.headers.get('access-control-allow-headers', '').lower()
    assert 'authorization' in allowed
    assert 'content-type' in allowed


def test_legacy_research_api_uses_workspace_scope_when_enabled(client, monkeypatch):
    monkeypatch.setenv('PRANAGUARD_REQUIRE_WORKSPACE_AUTH', '1')
    assert client.get('/api/overview').status_code == 401

    doctor = auth(client)
    overview = client.get('/api/overview', headers=doctor)
    assert overview.status_code == 200
    assert overview.json()['summary']['total'] == 120

    empty_doctor = auth(client, 'dr-nova', 'prana-nova-demo')
    assert client.get('/api/overview', headers=empty_doctor).json()['summary']['total'] == 0
    assert client.get('/api/patients/PG-0071', headers=empty_doctor).status_code == 404
    assert client.get('/api/enhanced/notifications', headers=empty_doctor).status_code == 403
    assert client.get('/api/validation', headers=empty_doctor).status_code == 403

    patient = auth(client, 'pat-pg0071', 'prana-patient-demo')
    assert client.post(
        '/api/patients/PG-0071/interventions',
        headers=patient,
        json={'kind': 'clinical_review', 'note': 'Should be blocked for patient role'},
    ).status_code == 403

    preflight = client.options(
        '/api/overview',
        headers={
            'Origin': 'https://prana-guard-copd-digital-twin.vercel.app',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'authorization,content-type',
        },
    )
    assert preflight.status_code == 200
    assert 'authorization' in preflight.headers.get('access-control-allow-headers', '').lower()


def test_workspace_login_throttle_persists_and_expires(client, engine):
    for attempt in range(4):
        assert login(client, 'dr-atlas', 'wrong-password').status_code == 401
    assert login(client, 'dr-atlas', 'wrong-password').status_code == 429
    assert login(client, 'dr-atlas', 'prana-atlas-demo').status_code == 429
    assert login(client, 'dr-nova', 'prana-nova-demo').status_code == 200

    username_hash=hashlib.sha256(b'dr-atlas').hexdigest()
    with engine.store.connect() as c:
        c.execute('UPDATE care_login_failures SET window_expires_at=? WHERE username_hash=?',
                  ('2000-01-01T00:00:00+00:00', username_hash))
    assert login(client, 'dr-atlas', 'prana-atlas-demo').status_code == 200


def test_alert_id_and_websocket_are_scoped_in_unified_mode(client, engine, monkeypatch):
    from backend.app.engine import now
    with engine.store.connect() as c:
        alert_id=c.execute(
            "INSERT INTO alerts(patient_id,state_version,created_at,risk,horizon,status) VALUES ('PG-0071',1,?,.4,24,'new')",
            (now(),),
        ).lastrowid
    monkeypatch.setenv('PRANAGUARD_REQUIRE_WORKSPACE_AUTH', '1')
    empty_doctor=auth(client, 'dr-nova', 'prana-nova-demo')
    assert client.patch(
        f'/api/alerts/{alert_id}', headers=empty_doctor,
        json={'status':'acknowledged','note':'out of scope'},
    ).status_code == 404
    full_doctor=auth(client)
    assert client.patch(
        f'/api/alerts/{alert_id}', headers=full_doctor,
        json={'status':'acknowledged','note':'assigned synthetic alert review'},
    ).status_code == 200
    with client.websocket_connect('/api/ws') as ws:
        ws.send_text('auth:'+full_doctor['Authorization'][7:])
        assert ws.receive_json()['type'] == 'connected'
    with pytest.raises(Exception):
        with client.websocket_connect('/api/ws') as ws:
            ws.send_text('auth:'+empty_doctor['Authorization'][7:])
            ws.receive_json()


def test_followup_completion_ledger_is_scoped_and_idempotent(client, engine):
    doctor=auth(client)
    patient=auth(client,'pat-pg0071','prana-patient-demo')
    review=client.post('/api/workspace/care/reviews',headers=doctor,json={
        'patient_id':'PG-0071','note':'Synthetic follow-up ledger test'
    }).json()['review']
    rid=review['id']
    assert client.patch(f'/api/workspace/care/reviews/{rid}',headers=doctor,json={'status':'awaiting_review'}).status_code==200
    assert client.patch(f'/api/workspace/care/reviews/{rid}',headers=doctor,json={'status':'under_review'}).status_code==200
    scheduled=client.patch(f'/api/workspace/care/reviews/{rid}',headers=doctor,json={
        'status':'follow_up_scheduled','follow_up_at':'2099-01-01T10:00:00+00:00'
    })
    assert scheduled.status_code==200
    assert client.post(f'/api/workspace/care/reviews/{rid}/complete-follow-up',headers=patient,json={'note':'patient cannot close clinician follow-up'}).status_code==403
    completed=client.post(f'/api/workspace/care/reviews/{rid}/complete-follow-up',headers=doctor,json={'note':'Synthetic follow-up completed'})
    assert completed.status_code==200,completed.text
    assert completed.json()['review']['status']=='completed'
    assert completed.json()['completion']['scheduled_for'].startswith('2099-01-01')
    assert client.post(f'/api/workspace/care/reviews/{rid}/complete-follow-up',headers=doctor,json={}).status_code==409
    ledger=client.get('/api/workspace/patients/PG-0071/follow-up-ledger',headers=doctor).json()
    assert ledger['total']==1 and ledger['items'][0]['review_id']==rid
    assert client.get('/api/workspace/patients/PG-0071/follow-up-ledger',headers=auth(client,'dr-nova','prana-nova-demo')).status_code==403
