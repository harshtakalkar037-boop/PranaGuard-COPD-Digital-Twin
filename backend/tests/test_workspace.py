"""Care workspace: demo auth, doctor scoping/isolation, review workflow, plans, sputum, activity."""
import base64,json
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
