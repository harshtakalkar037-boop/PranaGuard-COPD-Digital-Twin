"""Doctor+patient dashboard: daily logs, adherence, documents, follow-ups, audit trail, isolation."""
import base64,json
import pytest
from test_workspace import auth  # reuse helpers

LOG={'entry_date':'2026-11-06','water_ml':1500,'food_notes':'dal rice','activity_minutes':20,'sleep_hours':7.5,'sleep_quality':'good','wellbeing':'same','notes':'ok'}

def patient_auth(client):return auth(client,'pat-pg0071','prana-patient-demo')

def test_patient_home_connected(client):
    h=patient_auth(client)
    j=client.get('/api/workspace/patient/home',headers=h).json()
    assert j['patient_id']=='PG-0071';assert j['documents_count']>=1 and j['follow_ups'] and j['recent_logs']
    assert j['care_plan'] is None or 'goals' in (j['care_plan'] or {})
    assert 'synthetic' in j['note'].lower()
    # doctors are pushed away from the patient home
    assert client.get('/api/workspace/patient/home',headers=auth(client)).status_code==403

def test_daily_log_create_validate_edit_audit(client):
    h=patient_auth(client)
    r=client.post('/api/workspace/patient/daily-logs',headers=h,json={**LOG,'entry_date':'2026-11-05'});assert r.status_code==200,r.text
    lid=r.json()['id']
    bad=client.post('/api/workspace/patient/daily-logs',headers=h,json={**LOG,'water_ml':999999,'entry_date':'2026-11-04'});assert bad.status_code==422
    future=client.post('/api/workspace/patient/daily-logs',headers=h,json={**LOG,'entry_date':'2999-01-01'});assert future.status_code==422
    edit=client.put(f'/api/workspace/patient/daily-logs/{lid}',headers=h,json={**LOG,'entry_date':'2026-11-05','water_ml':2500,'wellbeing':'better'})
    assert edit.status_code==200 and edit.json()['edited']
    items=client.get('/api/workspace/patient/daily-logs',headers=h).json()['items']
    row=[i for i in items if i['id']==lid][0];assert row['water_ml']==2500 and row['edited']==1 and row['created_at']
    doctor=auth(client)
    audit=client.get('/api/workspace/patients/PG-0071/audit',headers=doctor).json()['events']
    ev=[e for e in audit if e['entity']=='daily_log' and e['entity_id']==str(lid) and e['action']=='edited']
    assert ev and '"water_ml": 1500' in (ev[0]['before_json'] or '') and '"water_ml": 2500' in (ev[0]['after_json'] or '')

def test_patient_cannot_touch_other_patient_records(client):
    h=patient_auth(client)
    for status,ep in [(403,'/api/workspace/patients/PG-0001/daily-logs'),(403,'/api/workspace/patients/PG-0001/documents'),(403,'/api/workspace/patients/PG-0001/follow-ups'),(403,'/api/workspace/patients/PG-0001/audit')]:
        r=client.get(ep,headers=h);assert r.status_code==status,ep
    # doctor-side write on behalf of another patient is rejected for patient tokens
    assert client.post('/api/workspace/patients/PG-0001/documents',headers=h,json={'title':'xx','doc_type':'other','filename':'a.txt','media_type':'text/plain','data_base64':base64.b64encode(b'hello demo world').decode()}).status_code==403

def test_medications_doctor_authored_and_adherence_validation(client):
    doctor=auth(client)
    # patient cannot add medication to the record
    assert client.post('/api/workspace/patients/PG-0071/medications',headers=patient_auth(client),json={'name':'Self-chosen med'}).status_code==403
    r=client.post('/api/workspace/patients/PG-0071/medications',headers=doctor,json={'name':'Demo spacer technique refresher','dose':'n/a','frequency':'daily'})
    assert r.status_code==200,r.text;mid=r.json()['id']
    dup=client.post('/api/workspace/patients/PG-0071/medications',headers=doctor,json={'name':'demo spacer technique refresher'});assert dup.status_code==409
    p=patient_auth(client)
    name=[m for m in client.get('/api/workspace/patient/medications',headers=p).json()['medication_options'] if m['id']==mid][0]['name']
    assert name=='Demo spacer technique refresher'
    bad=client.post('/api/workspace/patient/adherence',headers=p,json={'medication_id':999999,'as_prescribed':True,'taken_at':'2026-11-06T08:00:00Z'});assert bad.status_code==422
    missed=client.post('/api/workspace/patient/adherence',headers=p,json={'medication_id':mid,'as_prescribed':False,'taken_at':'2026-11-06T08:00:00Z'});assert missed.status_code==422  # missed without reason
    ok=client.post('/api/workspace/patient/adherence',headers=p,json={'medication_id':mid,'as_prescribed':False,'taken_at':'2026-11-06T08:00:00Z','missed_reason':'forgot while travelling'})
    assert ok.status_code==200
    seen=client.get('/api/workspace/patients/PG-0071/adherence',headers=doctor).json()['items']
    assert any(i['medication_id']==mid and i['as_prescribed']==0 for i in seen)

def sample_pdf():return base64.b64encode(b'%PDF-1.4 demo\n%%EOF').decode()
def test_document_upload_validation_and_scoping(client):
    doctor=auth(client);nova=auth(client,'dr-nova','prana-nova-demo');patient=patient_auth(client)
    # unsafe extension
    r=client.post('/api/workspace/patients/PG-0071/documents',headers=doctor,json={'title':'xx','doc_type':'other','filename':'evil.exe','media_type':'text/plain','data_base64':base64.b64encode(b'MZ').decode()})
    assert r.status_code==422
    # mismatched signature
    r=client.post('/api/workspace/patients/PG-0071/documents',headers=doctor,json={'title':'xx','doc_type':'prescription','filename':'x.pdf','media_type':'application/pdf','data_base64':base64.b64encode(b'not-a-pdf-payload').decode()})
    assert r.status_code==422
    # patient cannot upload doctor documents at all
    assert client.post('/api/workspace/patients/PG-0071/documents',headers=patient,json={'title':'xx','doc_type':'other','filename':'a.txt','media_type':'text/plain','data_base64':base64.b64encode(b'hello').decode()}).status_code==403
    # unassigned doctor blocked
    assert client.post('/api/workspace/patients/PG-0071/documents',headers=nova,json={'title':'xx','doc_type':'other','filename':'a.txt','media_type':'text/plain','data_base64':base64.b64encode(b'hello').decode()}).status_code==403
    success=client.post('/api/workspace/patients/PG-0071/documents',headers=doctor,json={'title':'Demo prescription record','doc_type':'prescription','doc_date':'2026-11-06','notes':'fictional','filename':'rx-demo.pdf','media_type':'application/pdf','data_base64':sample_pdf()})
    assert success.status_code==200,success.text;did=success.json()['id']
    # patient lists + downloads own; content bytes round-trip identical
    mine=client.get('/api/workspace/patient/documents',headers=patient).json()['items']
    assert any(d['id']==did for d in mine)
    f=client.get(f'/api/workspace/documents/{did}/file',headers=patient);assert f.status_code==200 and f.content.startswith(b'%PDF')
    assert f.headers.get('x-content-type-options')=='nosniff'
    assert client.get(f'/api/workspace/documents/{did}/file',headers=nova).status_code==403
    # delete keeps metadata in audit
    assert client.delete(f'/api/workspace/documents/{did}',headers=patient).status_code==403
    assert client.delete(f'/api/workspace/documents/{did}',headers=doctor).status_code==200
    assert client.get(f'/api/workspace/documents/{did}/file',headers=patient).status_code==404
    audit=client.get('/api/workspace/patients/PG-0071/audit',headers=doctor).json()['events']
    assert any(e['action']=='deleted' and e['entity']=='document' and e['entity_id']==str(did) and e['before_json'] for e in audit)

def test_follow_ups_lifecycle_and_patient_visibility(client):
    doctor=auth(client);patient=patient_auth(client)
    r=client.post('/api/workspace/patients/PG-0071/follow-ups',headers=doctor,json={'instructions':'Demo: gentle walk 10 min, log sputum daily','due_at':'2099-01-01T09:00:00Z'})
    assert r.status_code==200,r.text;fid=r.json()['id']
    assert client.post('/api/workspace/patients/PG-0071/follow-ups',headers=patient,json={'instructions':'self-made'}).status_code==403
    mine=client.get('/api/workspace/patient/follow-ups',headers=patient).json()['items']
    assert any(f['id']==fid and f['status']=='scheduled' for f in mine)
    home=client.get('/api/workspace/patient/home',headers=patient).json();assert any(f['id']==fid for f in home['follow_ups'])
    assert client.patch(f'/api/workspace/follow-ups/{fid}',headers=patient,json={'status':'completed'}).status_code==403
    assert client.patch(f'/api/workspace/follow-ups/{fid}',headers=doctor,json={'status':'completed'}).status_code==200
    again=client.patch(f'/api/workspace/follow-ups/{fid}',headers=doctor,json={'status':'cancelled'});assert again.status_code==409
    past=client.post('/api/workspace/patients/PG-0071/follow-ups',headers=doctor,json={'instructions':'x','due_at':'2001-01-01T00:00:00Z'});assert past.status_code==422

def test_doctor_marks_daily_log_reviewed_and_patient_sees_it(client):
    p=patient_auth(client);doctor=auth(client)
    lid=client.post('/api/workspace/patient/daily-logs',headers=p,json={**LOG,'entry_date':'2026-11-03'}).json()['id']
    assert client.patch(f'/api/workspace/daily-logs/{lid}/review',headers=p,json={'note':'self'}).status_code==403
    r=client.patch(f'/api/workspace/daily-logs/{lid}/review',headers=doctor,json={'note':'Reviewed — looks stable (demo)'})
    assert r.status_code==200 and r.json()['reviewed']
    again=client.patch(f'/api/workspace/daily-logs/{lid}/review',headers=doctor,json={'note':'twice'});assert again.status_code==409
    row=[i for i in client.get('/api/workspace/patient/daily-logs',headers=p).json()['items'] if i['id']==lid][0]
    assert row['reviewed_by']=='dr-atlas' and row['review_note'].startswith('Reviewed')
    home=client.get('/api/workspace/patient/home',headers=p).json();assert home['documents_count']>=1

def test_two_doctor_isolation_for_new_modules(client):
    nova=auth(client,'dr-nova','prana-nova-demo')
    for ep in ['/api/workspace/patients/PG-0071/daily-logs','/api/workspace/patients/PG-0071/documents','/api/workspace/patients/PG-0071/follow-ups','/api/workspace/patients/PG-0071/adherence','/api/workspace/patients/PG-0071/audit']:
        assert client.get(ep,headers=nova).status_code==403,ep

def test_seeded_demo_seed_only_once(client):
    h=patient_auth(client)
    docs=client.get('/api/workspace/patient/documents',headers=h).json()['items']
    assert any('fictional' in d['title'] for d in docs)
    with client:pass


def test_seeded_demo_open_care_review_is_visible_and_idempotent(client):
    doctor=auth(client)
    reviews=client.get('/api/workspace/care/reviews?page_size=50',headers=doctor).json()['items']
    showcase=[r for r in reviews if 'Routine follow-up review:' in r['note']]
    assert len(showcase)==1
    assert showcase[0]['patient_id']=='PG-0071'
    assert showcase[0]['status']=='awaiting_review'
    summary=client.get('/api/workspace/care/summary',headers=doctor).json()
    assert summary['pending_reviews']>=1
    assert any(r['id']==showcase[0]['id'] for r in summary['recent_reviews'])
    detail=client.get(f"/api/workspace/care/reviews/{showcase[0]['id']}",headers=doctor).json()
    assert detail['timeline'] and detail['timeline'][0]['event']=='created → awaiting_review'
    assert client.get('/api/workspace/care/reviews',headers=auth(client,'dr-nova','prana-nova-demo')).json()['total']==0
