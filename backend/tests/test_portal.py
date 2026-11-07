import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.portal import hash_password, timestamp
from backend.app.store import Store

PASSWORD='a-strong-test-password'
@pytest.fixture(scope='module')
def portal(tmp_path_factory, monkeypatch_module=None):
    db=tmp_path_factory.mktemp('portal')/'db.sqlite'
    with TestClient(create_app(db,background_tasks=False,legacy_demo=False)) as c:
        with c.app.state.engine.store.connect() as con:
            for name,role in [('doc','doctor'),('otherdoc','doctor'),('alice','patient'),('bob','patient')]:
                con.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',(name,hash_password(PASSWORD),role,timestamp()))
            ids={r['username']:r['id'] for r in con.execute('SELECT id,username FROM portal_users')}
            con.execute('INSERT INTO patient_user_links VALUES (?,?)',(ids['alice'],'PG-0001'))
            con.execute('INSERT INTO patient_user_links VALUES (?,?)',(ids['bob'],'PG-0002'))
            con.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(ids['doc'],'PG-0001'))
            con.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(ids['otherdoc'],'PG-0002'))
        yield c

def auth(c,name):
    r=c.post('/api/portal/login',json={'username':name,'password':PASSWORD});assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def test_legacy_isolation_and_auth(portal):
    assert portal.get('/api/overview').status_code==401
    assert portal.get('/api/enhanced/registry/patients').status_code==401
    assert portal.get('/api/portal/me').status_code==401
    assert portal.post('/api/portal/login',json={'username':'doc','password':'incorrect-password'}).status_code==401
    assert portal.post('/api/portal/register',json={'username':'newdoctor','password':PASSWORD,'role':'doctor'}).status_code==422
    h=auth(portal,'alice');assert portal.post('/api/portal/logout',headers=h).status_code==200
    assert portal.get('/api/portal/me',headers=h).status_code==401

def test_permissions_and_checkins(portal):
    a=auth(portal,'alice'); b=auth(portal,'bob');doc=auth(portal,'doc')
    assert portal.get('/api/portal/patients/PG-0002',headers=a).status_code==404
    assert portal.get('/api/portal/patients/PG-0002',headers=doc).status_code==404
    assert portal.get('/api/portal/patients',headers=a).status_code==403
    assert [p['patient_id'] for p in portal.get('/api/portal/patients',headers=doc).json()['patients']]==['PG-0001']
    body={'breathlessness':'mild','cough':'none','sputum_amount':'usual','sputum_colour':'clear','wheezing':'no','fatigue':'mild','fever':'no','comments':'test'}
    assert portal.post('/api/portal/checkins',json={**body,'patient_id':'PG-0002'},headers=a).status_code==422
    check=portal.post('/api/portal/checkins',json=body,headers=a);assert check.status_code==201,check.text
    cid=check.json()['id'];assert portal.get('/api/portal/patients/PG-0001',headers=doc).json()['checkins'][0]['id']==cid
    assert portal.get('/api/portal/patients/PG-0002',headers=b).json()['checkins']==[]
    notice=portal.get('/api/portal/notifications',headers=doc).json()['notifications'][0]
    assert notice['read_at'] is None
    assert portal.post(f"/api/portal/notifications/{notice['id']}/read",headers=a).status_code==404
    assert portal.post(f"/api/portal/notifications/{notice['id']}/read",headers=doc).status_code==200
    assert portal.get('/api/portal/notifications',headers=doc).json()['notifications'][0]['read_at']
    review={'status':'Follow-up Required','notes':'Reviewed observations','follow_up':'Please contact the team','follow_up_date':'2030-01-01','checkin_id':cid,'shared':True}
    assert portal.post('/api/portal/patients/PG-0001/reviews',json=review,headers=a).status_code==403
    assert portal.post('/api/portal/patients/PG-0001/reviews',json=review,headers=doc).status_code==201
    assert portal.get('/api/portal/patients/PG-0001',headers=a).json()['reviews'][0]['follow_up']==review['follow_up']
    assert portal.get('/api/portal/notifications',headers=a).json()['notifications'][0]['title']=='A doctor shared an update'
    assert portal.post('/api/portal/patients/PG-0002/reviews',json=review,headers=doc).status_code==404

def test_upload_permissions_and_validation(portal,tmp_path,monkeypatch):
    monkeypatch.setenv('PRANAGUARD_UPLOAD_DIR',str(tmp_path/'private'))
    a=auth(portal,'alice');b=auth(portal,'bob');doc=auth(portal,'doc');other=auth(portal,'otherdoc')
    def upload(name,data,kind='care_plan'):
        return portal.post('/api/portal/uploads',headers=a,data={'kind':kind},files={'file':(name,data,'application/octet-stream')})
    assert upload('bad.txt',b'hello').status_code==415
    assert upload('bad.pdf',b'not a pdf').status_code==415
    assert upload('big.pdf',b'%PDF-'+b'x'*(10*1024*1024)).status_code==413
    assert upload('photo.pdf',b'%PDF-example','photo').status_code==415
    result=upload('plan.pdf',b'%PDF-example');assert result.status_code==201,result.text
    path='/api/portal/uploads/'+str(result.json()['id'])
    assert portal.get(path,headers=b).status_code==404
    assert portal.get(path,headers=other).status_code==404
    assert portal.get(path,headers=doc).content==b'%PDF-example'
    assert portal.get(path).status_code==401
    assert portal.get('/private_uploads/plan.pdf').status_code==404
    assert portal.get('/api/portal/patients/PG-0001',headers=a).json()['uploads'][0].get('stored_name') is None

def test_repeatable_migration(portal):
    s=Store(portal.app.state.engine.store.path);s.apply_migrations()
    with s.connect() as c:
        assert [r[0] for r in c.execute('SELECT version FROM schema_migrations ORDER BY version')]==[1,2,3,4,5,6,7,8]
        assert not c.execute('PRAGMA foreign_key_check').fetchall()

def test_scoped_research_tools(portal):
    doc=auth(portal,'doc');patient=auth(portal,'alice')
    assert portal.get('/api/portal/validation',headers=doc).status_code==403
    assert portal.get('/api/portal/validation',headers=patient).status_code==403
    assert portal.get('/api/portal/patients/PG-0002/explanation?horizon=24',headers=doc).status_code==404
    result=portal.get('/api/portal/patients/PG-0001/explanation?horizon=24',headers=doc)
    assert result.status_code==200,result.text
    assert result.json()['horizon']==24
    scenario=portal.post('/api/portal/patients/PG-0001/scenarios',headers=doc,json={'pm25_change_pct':-30,'adherence':.95,'activity_multiplier':1})
    assert scenario.status_code==200,scenario.text
    assert scenario.json()['original_state_preserved']
    assert portal.post('/api/portal/patients/PG-0002/scenarios',headers=doc,json={}).status_code==404

def test_daily_care_sputum_and_plans(portal,tmp_path,monkeypatch):
    monkeypatch.setenv('PRANAGUARD_UPLOAD_DIR',str(tmp_path/'uploads'))
    a=auth(portal,'alice');b=auth(portal,'bob');doc=auth(portal,'doc');other=auth(portal,'otherdoc')
    plan={'title':'Wellness plan','start_date':'2026-01-01','food_guidance':'Individual plan','breakfast':'Breakfast guidance','hydration_target_ml':1200,'hydration_instructions':'Follow restriction','activities':'Walking','activity_schedule':'As agreed','activity_restrictions':'Follow clinical advice'}
    path='/api/portal/patients/PG-0001/care-plan'
    assert portal.post(path,headers=a,json=plan).status_code==403
    assert portal.post(path,headers=other,json=plan).status_code==404
    assert portal.post(path,headers=doc,json=plan).status_code==201
    assert portal.get(path,headers=a).json()['current']['hydration_target_ml']==1200
    assert portal.get('/api/portal/patients/PG-0002/care-plan',headers=b).json()['current'] is None
    assert portal.post(path,headers=doc,json={**plan,'hydration_target_ml':1300}).status_code==201
    assert len(portal.get(path,headers=doc).json()['history'])==2
    assert portal.get(path,headers=a).json()['history']==[]
    sputum={'observed_at':'2026-11-01T12:00:00+05:30','colour':'yellow','amount':'moderate','consistency':'thick','cough':'mild','description':'Reported observation'}
    created=portal.post('/api/portal/sputum',headers=a,json=sputum);assert created.status_code==201,created.text
    sid=created.json()['id']; assert portal.put(f'/api/portal/sputum/{sid}',headers=b,json=sputum).status_code==404
    upload=portal.post('/api/portal/uploads',headers=a,data={'kind':'photo','sputum_entry_id':str(sid)},files={'file':('diary.png',b'\x89PNG\r\n\x1a\nsynthetic','image/png')});assert upload.status_code==201,upload.text
    uid=upload.json()['id']; assert portal.get(f'/api/portal/uploads/{uid}',headers=other).status_code==404
    entry=portal.get('/api/portal/patients/PG-0001/sputum',headers=doc).json()['entries'][0]
    assert entry['photos'][0]['id']==uid and entry['colour']=='yellow'
    assert portal.get('/api/portal/patients/PG-0001/sputum',headers=other).status_code==404
    review={'notes':'Reviewed diary','follow_up':'Please share updates','shared':True}
    assert portal.post(f'/api/portal/patients/PG-0001/sputum/{sid}/reviews',headers=other,json=review).status_code==404
    assert portal.post(f'/api/portal/patients/PG-0001/sputum/{sid}/reviews',headers=doc,json=review).status_code==201
    entry=portal.get('/api/portal/patients/PG-0001/sputum',headers=a).json()['entries'][0]
    assert entry['review_status']=='Reviewed' and entry['reviews'][0]['follow_up']==review['follow_up']
    assert portal.put(f'/api/portal/sputum/{sid}',headers=a,json={**sputum,'colour':'clear'}).status_code==200
    entry=portal.get('/api/portal/patients/PG-0001/sputum',headers=doc).json()['entries'][0]
    assert entry['review_status']=='Pending Review' and 'yellow' in entry['edit_history'][0]['snapshot']
    for i,(kind,item,extra) in enumerate([('meal','Breakfast',{}),('meal','Lunch',{}),('meal','Dinner',{}),('hydration','Water',{'amount_ml':200}),('activity','Walking',{'duration_minutes':10,'effort':'light'})]):
        body={'kind':kind,'item':item,'occurred_at':'2026-11-02T10:00:00Z','status':'Completed','comments':'Patient reported', 'client_key':f'client-key-{i:010d}',**extra}
        result=portal.post('/api/portal/daily-care',headers=a,json=body);assert result.status_code==201,result.text
        duplicate=portal.post('/api/portal/daily-care',headers=a,json=body);assert duplicate.json()['duplicate']
        assert portal.post('/api/portal/daily-care',json={**body,'comments':'changed'}).status_code==401
        assert portal.post('/api/portal/daily-care',headers=a,json={**body,'comments':'changed'}).status_code==409
    logs=portal.get('/api/portal/patients/PG-0001/daily-care?kind=hydration&start=2026-11-02&end=2026-11-02',headers=doc).json()['logs']
    assert len(logs)==1 and logs[0]['amount_ml']==200
    assert portal.get('/api/portal/patients/PG-0001/daily-care',headers=other).status_code==404
    lid=logs[0]['id']
    assert portal.post(f'/api/portal/patients/PG-0001/daily-care/{lid}/reviews',headers=doc,json={'notes':'Reviewed intake','shared':True}).status_code==201
    assert portal.get('/api/portal/patients/PG-0001/daily-care?review_status=Reviewed',headers=a).json()['logs'][0]['reviews'][0]['notes']=='Reviewed intake'
    notices=portal.get('/api/portal/notifications',headers=doc).json()['notifications']
    assert any(n['title']=='New sputum diary entry' for n in notices)
    assert sum(n['title']=='New daily care activity' for n in notices)==5
    patient_notices=portal.get('/api/portal/notifications',headers=a).json()['notifications']
    assert any(n['title']=='Care plan updated' for n in patient_notices)
    assert any(n['title']=='Sputum diary reviewed' for n in patient_notices)
    assert portal.post(path,headers=doc,json={**plan,'active':False}).status_code==201
    assert portal.get(path,headers=a).json()['current'] is None

def test_demo_provisioning_and_password_change(portal,monkeypatch):
    doc=auth(portal,'doc');patient=auth(portal,'alice')
    with portal.app.state.engine.store.connect() as c:
        doc_id=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()[0]
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(doc_id,'PG-0003'))
    path='/api/portal/patients/PG-0003/provision-demo'
    assert portal.post(path,headers=doc).status_code==403
    monkeypatch.setenv('PRANAGUARD_SYNTHETIC_DEMO_PROVISIONING','1')
    assert portal.post(path,headers=patient).status_code==403
    result=portal.post(path,headers=doc);assert result.status_code==201,result.text
    temporary=result.json()['temporary_password'];assert len(temporary)>=20 and temporary!='PG-0003@123'
    assert portal.post(path,headers=doc).status_code==409
    with portal.app.state.engine.store.connect() as c:
        row=c.execute("SELECT password_hash,must_change_password FROM portal_users WHERE username='PG-0003'").fetchone()
        assert temporary not in row['password_hash'] and row['must_change_password']==1
    login=portal.post('/api/portal/login',json={'username':'PG-0003','password':temporary});assert login.status_code==200 and login.json()['must_change_password']
    h={'Authorization':'Bearer '+login.json()['token']}
    assert portal.post('/api/portal/login',json={'username':'PG-0003','password':temporary}).status_code==401
    assert portal.get('/api/portal/patients/PG-0003',headers=h).status_code==403
    assert portal.get('/api/portal/me',headers=h).json()['patient_id']=='PG-0003'
    assert portal.post('/api/portal/password',headers=h,json={'current_password':temporary,'new_password':temporary}).status_code==422
    changed=portal.post('/api/portal/password',headers=h,json={'current_password':temporary,'new_password':'new-unique-password-456'});assert changed.status_code==200
    assert portal.get('/api/portal/me',headers=h).status_code==401
    assert portal.post('/api/portal/login',json={'username':'PG-0003','password':temporary}).status_code==401
    fresh=portal.post('/api/portal/login',json={'username':'PG-0003','password':'new-unique-password-456'});assert fresh.status_code==200 and not fresh.json()['must_change_password']


def test_local_admin_reset_revokes_sessions(portal,monkeypatch,capsys):
    import sys
    from backend.app import portal_admin
    with portal.app.state.engine.store.connect() as c:
        c.execute("INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)",('reset_test',hash_password(PASSWORD),'patient',timestamp()))
    old=auth(portal,'reset_test')
    for _ in range(5):assert portal.post('/api/portal/login',json={'username':'reset_test','password':'incorrect'}).status_code==401
    assert portal.post('/api/portal/login',json={'username':'reset_test','password':PASSWORD}).status_code==429
    monkeypatch.setattr(portal_admin,'DB_PATH',portal.app.state.engine.store.path)
    monkeypatch.setattr(sys,'argv',['portal_admin','reset-password','reset_test'])
    portal_admin.main()
    output=capsys.readouterr().out.strip()
    temporary=output.split(': ',1)[1]
    assert len(temporary)>=12 and temporary!=PASSWORD
    assert portal.get('/api/portal/me',headers=old).status_code==401
    login=portal.post('/api/portal/login',json={'username':'reset_test','password':temporary})
    assert login.status_code==200 and login.json()['must_change_password']
    with portal.app.state.engine.store.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM portal_admin_audit WHERE action='password_reset' AND username='reset_test'").fetchone()[0]==1

def test_research_overview_supports_partial_assignment_and_validation_requires_full_cohort(portal):
    doc=auth(portal,'doc'); patient=auth(portal,'alice')
    assert portal.get('/api/overview',headers=patient).status_code==403
    assert portal.get('/api/overview',headers=doc).status_code==200
    assert portal.get('/api/validation',headers=doc).status_code==403
    engine=portal.app.state.engine
    with engine.store.connect() as c:
        doctor=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()['id']
        for pid in engine.profiles:
            c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(doctor,pid))
    overview=portal.get('/api/overview',headers=doc)
    assert overview.status_code==200
    assert len(overview.json()['patients'])==len(engine.profiles)==120
    assert portal.get('/api/portal/validation',headers=doc).status_code==200
    assert portal.get('/api/enhanced/registry/patients',headers=doc).status_code==200
    with engine.store.connect() as c:
        c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(doctor,'PG-0002'))
    assert portal.get('/api/patients/PG-0002',headers=doc).status_code==404


def test_bootstrap_does_not_overwrite_passwords(portal,monkeypatch):
    import json
    from backend.app.main import bootstrap_demo_portal
    from backend.app.portal import hash_password,verify_password
    engine=portal.app.state.engine
    cfg={'doctor':{'username':'doc','password_hash':hash_password('different-doctor-secret')},
         'patients':[{'username':f'bootstrap_{i}','patient_id':f'PG-{i:04d}',
                      'password_hash':hash_password('bootstrap-secret-123')}
                     for i in range(30,35)]}
    monkeypatch.setenv('PRANAGUARD_DEMO_BOOTSTRAP',json.dumps(cfg))
    bootstrap_demo_portal(engine)
    with engine.store.connect() as c:
        doctor=c.execute("SELECT password_hash FROM portal_users WHERE username='doc'").fetchone()
        user=c.execute("SELECT password_hash FROM portal_users WHERE username='bootstrap_30'").fetchone()
        assert verify_password(PASSWORD,doctor['password_hash'])
        c.execute("UPDATE portal_users SET password_hash=? WHERE username='bootstrap_30'",(hash_password('changed-password-123'),))
    bootstrap_demo_portal(engine)
    with engine.store.connect() as c:
        assert verify_password('changed-password-123',c.execute("SELECT password_hash FROM portal_users WHERE username='bootstrap_30'").fetchone()['password_hash'])


def test_assign_cohort_command_assigns_only_existing_cohort(portal,monkeypatch,capsys):
    import sys
    from backend.app import portal_admin
    engine=portal.app.state.engine
    monkeypatch.setattr(portal_admin,'DB_PATH',engine.store.path)
    monkeypatch.setattr(sys,'argv',['portal_admin','assign-cohort','otherdoc'])
    portal_admin.main()
    with engine.store.connect() as c:
        doc_id=c.execute("SELECT id FROM portal_users WHERE username='otherdoc'").fetchone()['id']
        assigned={r['patient_id'] for r in c.execute('SELECT patient_id FROM doctor_patient_assignments WHERE doctor_id=?',(doc_id,))}
        assert set(engine.profiles).issubset(assigned)
        assert c.execute("SELECT COUNT(*) FROM portal_admin_audit WHERE action='assign_synthetic_cohort'").fetchone()[0]==1
    assert '120 existing synthetic cohort records' in capsys.readouterr().out


def test_review_queue_is_scoped_and_not_a_clinical_score(portal):
    patient=auth(portal,'alice'); doctor=auth(portal,'doc'); other=auth(portal,'otherdoc')
    assert portal.get('/api/portal/care-queue',headers=patient).status_code==403
    body={'breathlessness':'mild','cough':'none','sputum_amount':'usual','sputum_colour':'clear','wheezing':'no','fatigue':'mild','fever':'no','comments':'queue-test'}
    submitted=portal.post('/api/portal/checkins',headers=patient,json=body)
    assert submitted.status_code==201
    doc_queue=portal.get('/api/portal/care-queue',headers=doctor).json()
    assert any(x['kind']=='checkin' and x['id']==submitted.json()['id'] and x['patient_id']=='PG-0001' for x in doc_queue['items'])
    with portal.app.state.engine.store.connect() as c:
        oid=c.execute("SELECT id FROM portal_users WHERE username='otherdoc'").fetchone()['id']
        c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(oid,'PG-0001'))
    assert all(x['patient_id']!='PG-0001' for x in portal.get('/api/portal/care-queue',headers=other).json()['items'])
    assert 'not a measure of clinical urgency' in doc_queue['notice']


def test_registration_atomically_assigns_registering_doctor(portal):
    doctor=auth(portal,'doc');other=auth(portal,'otherdoc')
    with portal.app.state.engine.store.connect() as c:
        doc_id=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()['id']
        other_id=c.execute("SELECT id FROM portal_users WHERE username='otherdoc'").fetchone()['id']
        for pid in portal.app.state.engine.profiles:
            c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(doc_id,pid))
            c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(other_id,pid))
    body={'request_id':'atomic-reg-0001','fictional_identity_confirmed':True,'demo_alias':'Integration Demo','age':58,'city':'Pune','sex':'Female'}
    created=portal.post('/api/enhanced/registry/patients',headers=doctor,json=body)
    assert created.status_code==200,created.text
    pid=created.json()['patient_id']
    with portal.app.state.engine.store.connect() as c:
        assert c.execute('SELECT 1 FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(doc_id,pid)).fetchone()
        assert not c.execute('SELECT 1 FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(other_id,pid)).fetchone()
        assert c.execute("SELECT 1 FROM portal_audit WHERE actor_id=? AND patient_id=? AND action='synthetic_registration_assigned'",(doc_id,pid)).fetchone()
    assert portal.get('/api/overview',headers=doctor).status_code==200
    assert len(portal.get('/api/overview',headers=doctor).json()['patients'])==120
    assert portal.get('/api/enhanced/registry/patients/'+pid,headers=doctor).status_code==200
    details=portal.get('/api/portal/patients/'+pid,headers=doctor)
    assert details.status_code==200 and details.json()['profile']['city']=='Pune' and details.json()['twin'] is None
    env=portal.get('/api/portal/patients/'+pid+'/environment',headers=doctor)
    assert env.status_code==200 and env.json()['city']=='Pune'
    assert 'not station observation or personal exposure' in env.json()['scope']
    assert portal.get('/api/portal/patients/'+pid+'/environment',headers=other).status_code==404
    assert portal.get('/api/overview',headers=other).status_code==200
    assert portal.get('/api/enhanced/registry/patients/'+pid,headers=other).status_code==404
    assert portal.post('/api/enhanced/registry/patients',headers=other,json=body).status_code==404
    assert portal.post('/api/enhanced/registry/patients',headers=other,json={**body,'demo_alias':'Changed Alias'}).status_code==404
    duplicate=portal.post('/api/enhanced/registry/patients',headers=doctor,json=body)
    assert duplicate.status_code==200 and duplicate.json()['patient_id']==pid and duplicate.json()['duplicate']


def test_registration_rolls_back_if_doctor_assignment_fails(portal):
    import sqlite3
    from backend.app.enhanced.schemas import Registration
    with portal.app.state.engine.store.connect() as c:
        c.execute("CREATE TRIGGER reject_demo_assignment BEFORE INSERT ON doctor_patient_assignments WHEN NEW.patient_id LIKE 'PG-DEMO-%' BEGIN SELECT RAISE(ABORT,'test assignment failure'); END")
        doc_id=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()['id']
    body=Registration(request_id='rollback-test-0001',fictional_identity_confirmed=True,demo_alias='Rollback Test',age=58,city='Pune')
    try:
        with pytest.raises(sqlite3.IntegrityError,match='test assignment failure'):
            portal.app.state.enhanced.registry.register(body,doc_id)
        with portal.app.state.engine.store.connect() as c:
            assert not c.execute('SELECT 1 FROM registrations WHERE request_id=?',(body.request_id,)).fetchone()
            assert not c.execute("SELECT 1 FROM patients WHERE json_extract(profile,'$.display_name')='Fictional demo · Rollback Test'").fetchone()
    finally:
        with portal.app.state.engine.store.connect() as c:c.execute('DROP TRIGGER reject_demo_assignment')


def test_temporary_credential_expiry_and_legacy_fail_closed(portal):
    from datetime import datetime, timezone, timedelta
    from backend.app.portal import temporary_password_expiration
    now=datetime.now(timezone.utc)
    secret='expiry-test-password-random'
    with portal.app.state.engine.store.connect() as c:
        for name,expires in [('expired_temp',(now-timedelta(seconds=1)).isoformat()),('legacy_temp',None),('active_temp',temporary_password_expiration())]:
            c.execute("INSERT INTO portal_users(username,password_hash,role,created_at,must_change_password,temporary_password_expires_at) VALUES (?,?,'patient',?,1,?)",(name,hash_password(secret),timestamp(),expires))
    for name in ('expired_temp','legacy_temp'):
        assert portal.post('/api/portal/login',json={'username':name,'password':secret}).status_code==401
    login=portal.post('/api/portal/login',json={'username':'active_temp','password':secret});assert login.status_code==200
    h={'Authorization':'Bearer '+login.json()['token']}
    with portal.app.state.engine.store.connect() as c:
        c.execute("UPDATE portal_users SET temporary_password_expires_at=? WHERE username='active_temp'",((now-timedelta(seconds=1)).isoformat(),))
    assert portal.get('/api/portal/me',headers=h).status_code==401
    assert portal.post('/api/portal/password',headers=h,json={'current_password':secret,'new_password':'another-unique-password'}).status_code==401


def test_temporary_credential_atomic_single_use(portal):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from backend.app.portal import temporary_password_expiration
    secret='concurrent-password-random'
    with portal.app.state.engine.store.connect() as c:
        c.execute("INSERT INTO portal_users(username,password_hash,role,created_at,must_change_password,temporary_password_expires_at) VALUES (?,?,'patient',?,1,?)",('race_temp',hash_password(secret),timestamp(),temporary_password_expiration()))
    barrier=Barrier(2)
    def login(_):
        barrier.wait()
        return portal.post('/api/portal/login',json={'username':'race_temp','password':secret}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(login,range(2)))
    assert sorted(statuses)==[200,401]
    with portal.app.state.engine.store.connect() as c:
        row=c.execute("SELECT u.temporary_password_expires_at,u.temporary_password_used_at,s.expires_at AS session_expires FROM portal_users u JOIN portal_sessions s ON s.user_id=u.id WHERE u.username='race_temp'").fetchone()
        assert row['temporary_password_used_at'] and row['session_expires']<=row['temporary_password_expires_at']


def test_upgrade_from_version_five_preserves_existing_accounts(tmp_path):
    db=tmp_path/'old.sqlite';s=Store(db);encoded=hash_password('old-password-for-migration')
    # Create a version-five-shaped database with existing linked users and data.
    with s.connect() as c:
        c.execute('DELETE FROM schema_migrations WHERE version=6')
        c.execute('ALTER TABLE portal_users DROP COLUMN temporary_password_expires_at')
        c.execute('ALTER TABLE portal_users DROP COLUMN temporary_password_used_at')
        c.execute("INSERT INTO patients VALUES (?,?)",('PG-OLD','{"synthetic":true}'))
        c.execute("INSERT INTO portal_users(username,password_hash,role,created_at,must_change_password) VALUES (?,?,'patient',?,1)",('olduser',encoded,timestamp()))
        uid=c.execute("SELECT id FROM portal_users WHERE username='olduser'").fetchone()[0]
        c.execute('INSERT INTO patient_user_links VALUES (?,?)',(uid,'PG-OLD'))
        c.execute('INSERT INTO portal_sessions VALUES (?,?,?)',('existing-token-hash',uid,'2099-01-01T00:00:00+00:00'))
    upgraded=Store(db);upgraded.apply_migrations()
    with upgraded.connect() as c:
        row=c.execute("SELECT * FROM portal_users WHERE username='olduser'").fetchone()
        assert row['password_hash']==encoded and row['must_change_password']==1
        assert row['temporary_password_expires_at'] is None and row['temporary_password_used_at'] is None
        assert c.execute('SELECT patient_id FROM patient_user_links WHERE user_id=?',(uid,)).fetchone()[0]=='PG-OLD'
        assert c.execute('SELECT token_hash FROM portal_sessions WHERE user_id=?',(uid,)).fetchone()[0]=='existing-token-hash'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()


def test_every_protected_http_route_rejects_missing_expired_and_revoked_sessions(portal):
    import hashlib
    expired=auth(portal,'alice');revoked=auth(portal,'bob')
    expired_hash=hashlib.sha256(expired['Authorization'][7:].encode()).hexdigest()
    revoked_hash=hashlib.sha256(revoked['Authorization'][7:].encode()).hexdigest()
    with portal.app.state.engine.store.connect() as c:
        c.execute('UPDATE portal_sessions SET expires_at=? WHERE token_hash=?',('2000-01-01T00:00:00+00:00',expired_hash))
        c.execute('DELETE FROM portal_sessions WHERE token_hash=?',(revoked_hash,))
    public={('POST','/api/portal/register'),('POST','/api/portal/login'),('GET','/api/health')}
    routes=[]
    for path,methods in portal.app.openapi()['paths'].items():
        for method in methods:
            method=method.upper()
            if (method,path) in public:continue
            concrete=path
            for name,value in {'pid':'PG-0002','upload_id':'1','notification_id':'1','review_id':'1','entry_id':'1','log_id':'1','did':'not-a-device','city':'Pune','nid':'1','alert_id':'1'}.items():
                concrete=concrete.replace('{'+name+'}',value)
            assert '{' not in concrete,(method,path)
            routes.append((method,concrete))
    assert len(routes)>=65
    for method,path in routes:
        for headers in ({},expired,revoked):
            response=portal.request(method,path,headers=headers,json={})
            assert response.status_code==401,(method,path,response.status_code,response.text)


def test_every_legacy_http_route_rejects_patient_session(portal):
    patient=auth(portal,'alice')
    routes=0
    for path,methods in portal.app.openapi()['paths'].items():
        if not path.startswith('/api/') or path.startswith('/api/portal/') or path=='/api/health':continue
        for method in methods:
            concrete=path
            for name,value in {'pid':'PG-0002','did':'not-a-device','city':'Pune','nid':'1','alert_id':'1'}.items():concrete=concrete.replace('{'+name+'}',value)
            assert '{' not in concrete,(method,path)
            response=portal.request(method.upper(),concrete,headers=patient,json={})
            assert response.status_code==403,(method,path,response.status_code,response.text)
            routes+=1
    assert routes>=40


def test_scoped_original_twin_methods_do_not_require_global_access(portal):
    doc=auth(portal,'doc');other=auth(portal,'otherdoc');patient=auth(portal,'alice')
    with portal.app.state.engine.store.connect() as c:
        doc_id=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()[0]
        other_id=c.execute("SELECT id FROM portal_users WHERE username='otherdoc'").fetchone()[0]
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(doc_id,'PG-0001'))
        c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(doc_id,'PG-0002'))
        c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(other_id,'PG-0001'))
    # The unassigned doctor and modified patient ID are denied before body handling.
    cases=[('GET','',None),('GET','history',None),('GET','versions',None),('GET','explanation',None),('GET','scenarios',None),('POST','scenarios',{}),('GET','interventions',None),('POST','interventions',{'kind':'other','note':'test only'})]
    for method,suffix,body in cases:
        path='/api/patients/PG-0001'+('/'+suffix if suffix else '')
        denied=portal.request(method,path,headers=other,json=body)
        assert denied.status_code==404,(method,path,denied.text)
        assert portal.request(method,path,headers=patient,json=body).status_code==403
        modified=path.replace('PG-0001','PG-0002')
        assert portal.request(method,modified,headers=doc,json=body).status_code==404
        response=portal.request(method,path,headers=doc,json=body)
        assert response.status_code==200,(method,path,response.text)
    # Overview now scopes to assigned historical twins, while validation stays restricted.
    assert 'PG-0001' in [p['patient_id'] for p in portal.get('/api/overview',headers=doc).json()['patients']]
    assert portal.get('/api/validation',headers=doc).status_code==403


def test_portal_per_record_methods_reject_cross_patient_and_child_ids(portal):
    a=auth(portal,'alice');b=auth(portal,'bob');doc=auth(portal,'doc');other=auth(portal,'otherdoc')
    with portal.app.state.engine.store.connect() as c:
        ids={r['username']:r['id'] for r in c.execute("SELECT id,username FROM portal_users WHERE username IN ('doc','otherdoc')")}
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(ids['doc'],'PG-0001'))
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(ids['doc'],'PG-0002'))
        c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(ids['otherdoc'],'PG-0001'))
    for suffix in ('','/environment','/sputum','/care-plan','/daily-care'):
        path='/api/portal/patients/PG-0001'+suffix
        assert portal.get(path,headers=b).status_code==404,(path,'other patient')
        assert portal.get(path,headers=other).status_code==404,(path,'unassigned doctor')
        assert portal.get(path,headers=a).status_code==200,(path,'own patient')
        assert portal.get(path,headers=doc).status_code==200,(path,'assigned doctor')
    for method,suffix,body in [('GET','/explanation',None),('POST','/scenarios',{}),('POST','/care-plan',{'title':'Example','start_date':'2026-01-01'}),('POST','/reviews',{'status':'Reviewed','notes':'Example'})]:
        path='/api/portal/patients/PG-0001'+suffix
        assert portal.request(method,path,headers=a,json=body).status_code==403,(method,path,'patient')
        assert portal.request(method,path,headers=other,json=body).status_code==404,(method,path,'unassigned doctor')
    sputum={'observed_at':'2026-11-01T12:00:00Z','colour':'clear','amount':'small','consistency':'thin','cough':'mild'}
    sid=portal.post('/api/portal/sputum',headers=a,json=sputum).json()['id']
    daily={'kind':'meal','item':'Breakfast','occurred_at':'2026-11-01T12:00:00Z','status':'Completed','client_key':'cross-child-key-0001'}
    lid=portal.post('/api/portal/daily-care',headers=a,json=daily).json()['id']
    assert portal.put(f'/api/portal/sputum/{sid}',headers=b,json=sputum).status_code==404
    assert portal.post(f'/api/portal/patients/PG-0002/sputum/{sid}/reviews',headers=doc,json={'notes':'wrong patient'}).status_code==404
    assert portal.post(f'/api/portal/patients/PG-0002/daily-care/{lid}/reviews',headers=doc,json={'notes':'wrong patient'}).status_code==404


def test_historical_cohort_is_scoped_before_aggregation_and_alert_limit(portal):
    import json
    doctor=auth(portal,'doc');patient=auth(portal,'alice');engine=portal.app.state.engine
    fake_id='PG-OTHER-SCOPED-TEST';marker='Unassigned fictional marker'
    with engine.store.connect() as c:
        doc_id=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()[0]
        for pid in engine.profiles:c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(doc_id,pid))
    before=portal.get('/api/overview',headers=doctor);assert before.status_code==200
    baseline=before.json();assert len(baseline['patients'])==120
    with engine.store.connect() as c:
        profile={'patient_id':fake_id,'display_name':marker,'city':'Pune','synthetic':True}
        source=c.execute('SELECT version,hour,timestamp,state FROM states WHERE patient_id=? ORDER BY version DESC LIMIT 1',('PG-0001',)).fetchone()
        state=json.loads(source['state']);state.update(patient_id=fake_id,profile=profile,risks={'24':.99,'48':.99,'72':.99},risk_category='high')
        c.execute('INSERT INTO patients VALUES (?,?)',(fake_id,json.dumps(profile)))
        c.execute('INSERT INTO states VALUES (?,?,?,?,?)',(fake_id,source['version'],source['hour'],source['timestamp'],json.dumps(state)))
        # More than the legacy 500-alert limit must not displace authorized alerts.
        c.executemany('INSERT INTO alerts(patient_id,state_version,created_at,risk,horizon,status) VALUES (?,?,?,?,?,?)',[(fake_id,source['version'],timestamp(),.99,72,'new') for _ in range(501)])
    try:
        result=portal.get('/api/overview',headers=doctor);assert result.status_code==200
        current=result.json()
        assert current['summary']==baseline['summary'] and current['trend']==baseline['trend']
        assert current['patients']==baseline['patients'] and marker not in result.text and fake_id not in result.text
        assert portal.get('/api/patients',headers=doctor,params={'q':marker}).json()['patients']==[]
        assert len(portal.get('/api/patients',headers=doctor).json()['patients'])==120
        assert portal.get('/api/overview',headers=patient).status_code==403
        # Still-unscoped routes remain locked when another record is unassigned.
        registry=portal.get('/api/enhanced/registry/patients',headers=doctor)
        assert registry.status_code==200 and fake_id not in registry.text and marker not in registry.text
        assert registry.json()['original_cohort_count']==120
        assert portal.get('/api/enhanced/registry/patients/'+fake_id,headers=doctor).status_code==404
        scoped_alerts=portal.get('/api/alerts',headers=doctor);assert scoped_alerts.status_code==200 and fake_id not in scoped_alerts.text
        assert portal.get('/api/alerts',headers=doctor,params={'patient_id':fake_id}).status_code==404
        validation=portal.get('/api/validation',headers=doctor);assert validation.status_code==200 and fake_id not in validation.text
        city=portal.get('/api/enhanced/environment/Pune',headers=doctor);assert city.status_code==200 and fake_id not in city.text
        assert portal.get('/api/enhanced/environment/Pune',headers=patient).status_code==403
        with engine.store.connect() as c:c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(doc_id,'PG-0001'))
        partial=portal.get('/api/overview',headers=doctor);assert partial.status_code==200
        assert len(partial.json()['patients'])==119 and partial.json()['replay']['demo'] is None
        assert all(p['patient_id']!='PG-0001' for p in portal.get('/api/patients',headers=doctor).json()['patients'])
        assert portal.get('/api/validation',headers=doctor).status_code==403
    finally:
        with engine.store.connect() as c:
            c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(doc_id,'PG-0001'))
            c.execute('DELETE FROM alerts WHERE patient_id=?',(fake_id,))
            c.execute('DELETE FROM states WHERE patient_id=?',(fake_id,))
            c.execute('DELETE FROM patients WHERE patient_id=?',(fake_id,))


def test_related_submission_ids_cannot_be_rebound_to_an_assigned_patient(portal,tmp_path,monkeypatch):
    monkeypatch.setenv('PRANAGUARD_UPLOAD_DIR',str(tmp_path/'private'))
    alice=auth(portal,'alice');bob=auth(portal,'bob');doc=auth(portal,'doc')
    with portal.app.state.engine.store.connect() as c:
        uid=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()[0]
        for pid in ('PG-0001','PG-0002'):c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(uid,pid))
    checkin={'breathlessness':'mild','cough':'none','sputum_amount':'usual','sputum_colour':'clear','wheezing':'no','fatigue':'mild','fever':'no'}
    cid=portal.post('/api/portal/checkins',headers=alice,json=checkin).json()['id']
    photo=('observation.png',b'\x89PNG\r\n\x1a\nsynthetic','image/png')
    upload=portal.post('/api/portal/uploads',headers=alice,data={'kind':'photo'},files={'file':photo});assert upload.status_code==201
    upload_id=upload.json()['id']
    review={'status':'Reviewed','notes':'Synthetic test'}
    path='/api/portal/patients/PG-0002/reviews'
    assert portal.post(path,headers=doc,json={**review,'checkin_id':cid}).status_code==404
    assert portal.post(path,headers=doc,json={**review,'upload_id':upload_id}).status_code==404
    assert portal.get(f'/api/portal/uploads/{upload_id}',headers=bob).status_code==404
    sputum={'observed_at':'2026-11-01T12:00:00Z','colour':'clear','amount':'small','consistency':'thin','cough':'mild'}
    sid=portal.post('/api/portal/sputum',headers=alice,json=sputum).json()['id']
    assert portal.post('/api/portal/uploads',headers=bob,data={'kind':'photo','sputum_entry_id':str(sid)},files={'file':photo}).status_code==404


def test_scoped_registry_with_partial_assignments_and_foreign_mutations(portal):
    """Lists, filters, totals, related actions and retries cannot reveal another doctor's fiction."""
    import uuid
    first=auth(portal,'doc');other=auth(portal,'otherdoc');patient=auth(portal,'alice')
    body={'request_id':'scope-'+uuid.uuid4().hex,'fictional_identity_confirmed':True,'demo_alias':'Private Fiction','age':55,'city':'Pune'}
    with portal.app.state.engine.store.connect() as c:
        oid=c.execute("SELECT id FROM portal_users WHERE username='otherdoc'").fetchone()[0]
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments SELECT ?,patient_id FROM patients',(oid,))
    made=portal.post('/api/enhanced/registry/patients',headers=other,json=body)
    assert made.status_code==200, made.text
    pid=made.json()['patient_id']
    try:
        mine=portal.get('/api/enhanced/registry/patients',headers=other).json()
        foreign=portal.get('/api/enhanced/registry/patients',headers=first).json()
        assert pid in [p['patient_id'] for p in mine['patients']]
        assert pid not in [p['patient_id'] for p in foreign['patients']]
        assert foreign['total']==len(foreign['patients'])
        assert portal.get('/api/enhanced/registry/patients',headers=first,params={'q':pid}).json()['total']==0
        assert portal.get('/api/enhanced/registry/patients/'+pid,headers=first).status_code==404
        assert portal.get('/api/enhanced/registry/patients/'+pid,headers=other).status_code==200
        obs={'fictional_data_confirmed':True,'symptom_score':2,'adherence':.8,'note':'Test'}
        review={'kind':'contact','note':'Test review'}
        for suffix,payload in [('observations',obs),('reviews',review)]:
            assert portal.post(f'/api/enhanced/registry/patients/{pid}/{suffix}',headers=first,json=payload).status_code==404
            assert portal.post(f'/api/enhanced/registry/patients/{pid}/{suffix}',headers=patient,json=payload).status_code==403
            assert portal.post(f'/api/enhanced/registry/patients/{pid}/{suffix}',headers=other,json=payload).status_code==200
        assert portal.get('/api/enhanced/registry/patients',headers=patient).status_code==403
        assert portal.get('/api/enhanced/registry/patients').status_code==401
        assert portal.post('/api/enhanced/registry/patients',headers=first,json=body).status_code==404
        from fastapi import HTTPException
        from backend.app.enhanced.schemas import Registration
        with portal.app.state.engine.store.connect() as c: first_id=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()[0]
        with pytest.raises(HTTPException) as denied:portal.app.state.enhanced.registry.register(Registration(**body),first_id)
        assert denied.value.status_code==404
        assert portal.post('/api/enhanced/registry/patients',headers=other,json=body).json()['patient_id']==pid
    finally:
        # This test fixture is isolated and disposable; clean only its own records.
        with portal.app.state.engine.store.connect() as c:
            nids=[r[0] for r in c.execute('SELECT id FROM notifications WHERE patient_id=?',(pid,))]
            for nid in nids:c.execute('DELETE FROM notification_history WHERE notification_id=?',(nid,))
            for table in ('notifications','enhanced_audit','portal_audit','interventions','demo_observations','registrations','doctor_patient_assignments','patients'):
                c.execute('DELETE FROM '+table+' WHERE patient_id=?',(pid,))


def test_secure_websocket_rejects_all_sessions(portal):
    from starlette.websockets import WebSocketDisconnect
    import hashlib
    doctor=auth(portal,'doc');patient=auth(portal,'alice');expired=auth(portal,'alice');revoked=auth(portal,'bob')
    with portal.app.state.engine.store.connect() as c:
        c.execute('UPDATE portal_sessions SET expires_at=? WHERE token_hash=?',('2000-01-01T00:00:00+00:00',hashlib.sha256(expired['Authorization'][7:].encode()).hexdigest()))
        c.execute('DELETE FROM portal_sessions WHERE token_hash=?',(hashlib.sha256(revoked['Authorization'][7:].encode()).hexdigest(),))
    for headers in ({},doctor,patient,expired,revoked):
        with pytest.raises(WebSocketDisconnect) as exc:
            with portal.websocket_connect('/api/ws',headers=headers):
                pass
        assert exc.value.code==1008


def test_disposable_database_accounts_submissions_and_upload_survive_restart(tmp_path,monkeypatch):
    """Restart a local application, not evidence of production persistence."""
    import secrets
    db=tmp_path/'persist.sqlite';monkeypatch.setenv('PRANAGUARD_UPLOAD_DIR',str(tmp_path/'uploads'))
    password=secrets.token_urlsafe(24)
    with TestClient(create_app(db,background_tasks=False,legacy_demo=False)) as first:
        s=first.app.state.engine.store
        with s.connect() as c:
            c.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',('restartdoc',hash_password(password),'doctor',timestamp()))
            doctor=c.execute("SELECT id FROM portal_users WHERE username='restartdoc'").fetchone()[0]
            for n in range(1,6):
                pid=f'PG-{n:04d}'
                c.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',(f'restartpatient{n}',hash_password(password),'patient',timestamp()))
                uid=c.execute('SELECT id FROM portal_users WHERE username=?',(f'restartpatient{n}',)).fetchone()[0]
                c.execute('INSERT INTO patient_user_links VALUES (?,?)',(uid,pid))
                c.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(doctor,pid))
            profiles={r['patient_id']:r['profile'] for r in c.execute('SELECT patient_id,profile FROM patients')}
            original_state=c.execute("SELECT state FROM states WHERE patient_id='PG-0001' ORDER BY version DESC LIMIT 1").fetchone()[0]
            migrations=list(c.execute('SELECT version,sha256 FROM schema_migrations ORDER BY version'))
        def signin(client,name):
            r=client.post('/api/portal/login',json={'username':name,'password':password});assert r.status_code==200
            return {'Authorization':'Bearer '+r.json()['token']}
        h=signin(first,'restartpatient1')
        check=first.post('/api/portal/checkins',headers=h,json={'breathlessness':'mild','cough':'none','sputum_amount':'usual','sputum_colour':'clear','wheezing':'no','fatigue':'mild','fever':'no','comments':'persisted synthetic submission'})
        assert check.status_code==201
        up=first.post('/api/portal/uploads',headers=h,data={'kind':'care_plan'},files={'file':('plan.pdf',b'%PDF-restart-test','application/pdf')})
        assert up.status_code==201; upload_id=up.json()['id']; check_id=check.json()['id']
    with TestClient(create_app(db,background_tasks=False,legacy_demo=False)) as second:
        s=second.app.state.engine.store
        with s.connect() as c:
            assert {r['patient_id']:r['profile'] for r in c.execute('SELECT patient_id,profile FROM patients')}==profiles
            assert len(profiles)==120
            assert c.execute("SELECT state FROM states WHERE patient_id='PG-0001' ORDER BY version DESC LIMIT 1").fetchone()[0]==original_state
            assert [tuple(r) for r in c.execute('SELECT version,sha256 FROM schema_migrations ORDER BY version')]==[tuple(r) for r in migrations]
            assert not c.execute('PRAGMA foreign_key_check').fetchall()
        doc=signin(second,'restartdoc')
        for n in range(1,6):
            p=signin(second,f'restartpatient{n}')
            assert second.get('/api/portal/me',headers=p).json()['patient_id']==f'PG-{n:04d}'
        details=second.get('/api/portal/patients/PG-0001',headers=doc).json()
        assert any(item['id']==check_id and item['comments']=='persisted synthetic submission' for item in details['checkins'])
        assert any(item['id']==upload_id for item in details['uploads'])
        assert second.get(f'/api/portal/uploads/{upload_id}',headers=doc).content==b'%PDF-restart-test'


def test_unscoped_routes_fail_closed_for_multiple_doctors_even_with_full_assignment(portal):
    doctor=auth(portal,'doc');other=auth(portal,'otherdoc');engine=portal.app.state.engine
    with engine.store.connect() as c:
        dids=[r[0] for r in c.execute("SELECT id FROM portal_users WHERE role='doctor'")]
        for did in dids:c.execute('INSERT OR IGNORE INTO doctor_patient_assignments SELECT ?,patient_id FROM patients',(did,))
    # The whole-workspace pre-check alone is vulnerable to a registration by
    # another doctor between authorization and the unscoped handler's read.
    for h in (doctor,other):
        for path in ('/api/status','/api/replay','/api/enhanced/devices','/api/enhanced/provenance'):
            assert portal.get(path,headers=h).status_code==403,path
        assert portal.get('/api/overview',headers=h).status_code==200
        assert portal.get('/api/enhanced/registry/patients',headers=h).status_code==200


def test_unscoped_routes_remain_available_in_fully_assigned_single_doctor_demo(tmp_path):
    with TestClient(create_app(tmp_path/'single.sqlite',background_tasks=False,legacy_demo=False)) as c:
        with c.app.state.engine.store.connect() as db:
            db.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',('single-doc',hash_password(PASSWORD),'doctor',timestamp()))
            did=db.execute("SELECT id FROM portal_users WHERE username='single-doc'").fetchone()[0]
            db.execute('INSERT INTO doctor_patient_assignments SELECT ?,patient_id FROM patients',(did,))
        h=auth(c,'single-doc')
        assert c.get('/api/alerts',headers=h).status_code==200
        assert c.get('/api/replay',headers=h).status_code==200
        assert c.get('/api/enhanced/devices',headers=h).status_code==200
        notice=c.post('/api/enhanced/notifications/test',headers=h,json={});assert notice.status_code==200
        nid=notice.json()['id']
        assert any(n['id']==nid for n in c.get('/api/enhanced/notifications',headers=h).json()['notifications'])
        assert c.get(f'/api/enhanced/notifications/{nid}',headers=h).status_code==200
        assert c.patch(f'/api/enhanced/notifications/{nid}',headers=h,json={'read':True}).status_code==200


def test_explanation_horizons_enforced_for_authorized_doctor(portal):
    doctor=auth(portal,'doc')
    for prefix in ('/api/patients/PG-0001/explanation','/api/portal/patients/PG-0001/explanation'):
        for horizon in (24,48,72):
            r=portal.get(prefix,params={'horizon':horizon},headers=doctor)
            assert r.status_code==200 and r.json()['horizon']==horizon
        for horizon in (0,25,96,-1):
            assert portal.get(prefix,params={'horizon':horizon},headers=doctor).status_code==422


def test_legacy_alerts_are_scoped_before_limit_and_update(tmp_path):
    import json
    with TestClient(create_app(tmp_path/'scoped-alerts.sqlite',background_tasks=False,legacy_demo=False)) as c:
        with c.app.state.engine.store.connect() as db:
            ids={}
            for name,role in [('alertdoctor1','doctor'),('alertdoctor2','doctor'),('alertpatient','patient')]:
                db.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',(name,hash_password(PASSWORD),role,timestamp()))
                ids[name]=db.execute('SELECT id FROM portal_users WHERE username=?',(name,)).fetchone()[0]
            db.execute('INSERT INTO patient_user_links VALUES (?,?)',(ids['alertpatient'],'PG-0001'))
            db.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(ids['alertdoctor1'],'PG-0001'))
            db.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(ids['alertdoctor2'],'PG-0002'))
            db.execute('INSERT INTO patients VALUES (?,?)',('PRIVATE-REAL',json.dumps({'patient_id':'PRIVATE-REAL','display_name':'Not synthetic','synthetic':False})))
            db.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(ids['alertdoctor1'],'PRIVATE-REAL'))
            def insert(pid):return db.execute('INSERT INTO alerts(patient_id,state_version,created_at,risk,horizon,status) VALUES (?,?,?,?,?,?)',(pid,1,timestamp(),.4,72,'new')).lastrowid
            own=insert('PG-0001');foreign=insert('PG-0002');real=insert('PRIVATE-REAL')
            for _ in range(501):insert('PG-0002')
        first=auth(c,'alertdoctor1');second=auth(c,'alertdoctor2');patient=auth(c,'alertpatient')
        r=c.get('/api/alerts',headers=first);assert r.status_code==200
        assert [a['id'] for a in r.json()['alerts']]==[own]
        assert c.get('/api/alerts',headers=first,params={'patient_id':'PG-0002'}).status_code==404
        assert c.get('/api/alerts',headers=first,params={'patient_id':'PRIVATE-REAL'}).status_code==404
        assert c.get('/api/alerts',headers=first,params={'patient_id':'NOT-FOUND'}).status_code==404
        assert c.get('/api/alerts',headers=patient).status_code==403
        assert c.get('/api/alerts').status_code==401
        for denied in (foreign,real,999999999):
            assert c.patch(f'/api/alerts/{denied}',headers=first,json={'status':'acknowledged','note':'not allowed'}).status_code==404
        assert c.patch(f'/api/alerts/{own}',headers=second,json={'status':'resolved'}).status_code==404
        assert c.patch(f'/api/alerts/{own}',headers=patient,json={'status':'resolved'}).status_code==403
        # Updating an older authorized ID must not depend on the 500-row list cap.
        with c.app.state.engine.store.connect() as db:
            db.executemany('INSERT INTO alerts(patient_id,state_version,created_at,risk,horizon,status) VALUES (?,?,?,?,?,?)',[('PG-0001',1,timestamp(),.4,72,'new') for _ in range(501)])
        assert own not in [a['id'] for a in c.get('/api/alerts',headers=first).json()['alerts']]
        ok=c.patch(f'/api/alerts/{own}',headers=first,json={'status':'resolved','note':'Synthetic review'})
        assert ok.status_code==200 and ok.json()['alert']['patient_id']=='PG-0001' and ok.json()['alert']['status']=='resolved'
        assert c.patch(f'/api/alerts/{own}',headers=first,json={'status':'acknowledged'}).status_code==409
        with c.app.state.engine.store.connect() as db:
            assert db.execute('SELECT status FROM alerts WHERE id=?',(foreign,)).fetchone()[0]=='new'
            assert db.execute('SELECT status FROM alerts WHERE id=?',(real,)).fetchone()[0]=='new'


def test_secure_demo_device_simulation_ingests_without_weakening_http_auth(tmp_path,monkeypatch):
    monkeypatch.setenv('PRANAGUARD_ADMIN_TOKEN','test-only-write-token')
    with TestClient(create_app(tmp_path/'secure-simulation.sqlite',background_tasks=True,legacy_demo=False)) as c:
        with c.app.state.engine.store.connect() as db:
            db.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',('simdoctor',hash_password(PASSWORD),'doctor',timestamp()))
            did=db.execute("SELECT id FROM portal_users WHERE username='simdoctor'").fetchone()[0]
            db.execute('INSERT INTO doctor_patient_assignments SELECT ?,patient_id FROM patients',(did,))
        doctor=auth(c,'simdoctor');write={**doctor,'X-Demo-Token':'test-only-write-token'}
        made=c.post('/api/enhanced/devices',headers=write,json={'patient_id':'PG-0001','kind':'pulse_oximeter','interval_seconds':2});assert made.status_code==200,made.text
        device=made.json();path='/api/enhanced/devices/'+device['id']
        assert c.post(path+'/start',headers=write,json={'interval_seconds':2}).status_code==200
        payload=c.app.state.enhanced.devices.sample(c.app.state.enhanced.devices.require(device['id']))
        assert c.post('/api/enhanced/ingestion',json=payload).status_code==401
        assert c.post('/api/enhanced/ingestion',headers=write,json=payload).status_code==401 # no device token
        assert c.post('/api/enhanced/ingestion',headers={'X-Device-Token':c.app.state.enhanced.devices.token_for(device['id']),'X-Demo-Token':'test-only-write-token'},json=payload).status_code==401 # no portal session
        import time
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            readings=c.get(path+'/readings',headers=doctor);assert readings.status_code==200
            if len(readings.json()['readings'])>=2:break
            time.sleep(.1)
        assert len(readings.json()['readings'])==2
        assert c.post(path+'/stop',headers=write,json={}).status_code==200
        c.portal.call(c.app.state.enhanced.devices.tick,c.app)
        assert len(c.get(path+'/readings',headers=doctor).json()['readings'])==2


def test_enhanced_notifications_are_scoped_for_lists_counts_and_atomic_review(tmp_path):
    import json
    with TestClient(create_app(tmp_path/'notifications.sqlite',background_tasks=False,legacy_demo=False)) as c:
        svc=c.app.state.enhanced.notifications
        with c.app.state.engine.store.connect() as db:
            for name,pid in [('notedoc1','PG-0001'),('notedoc2','PG-0002')]:
                db.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',(name,hash_password(PASSWORD),'doctor',timestamp()))
                did=db.execute('SELECT id FROM portal_users WHERE username=?',(name,)).fetchone()[0]
                db.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(did,pid))
            p=json.loads(db.execute("SELECT profile FROM patients WHERE patient_id='PG-0003'").fetchone()[0]);p['synthetic']=False
            db.execute("UPDATE patients SET profile=? WHERE patient_id='PG-0003'",(json.dumps(p),))
            db.execute("INSERT INTO doctor_patient_assignments SELECT id,'PG-0003' FROM portal_users WHERE username='notedoc1'")
            db.execute("INSERT INTO alerts(patient_id,horizon,risk,status,created_at,updated_at,state_version) VALUES ('PG-0002',72,.5,'new',?,?,1)",(timestamp(),timestamp()))
            foreign_alert=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            def add(pid,key,legacy=None):
                return svc.create(category='patient_monitoring',title=key,reason='synthetic test',source='test',source_type='system_demo',patient_id=pid,dedupe_key=key,legacy_alert_id=legacy,conn=db)
            own=add('PG-0001','own');foreign=add('PG-0002','foreign');nonsynthetic=add('PG-0003','nonsynthetic')
            mismatched=add('PG-0001','mismatched',foreign_alert)
            shared=add(None,'shared')
            for i in range(501):add('PG-0002',f'foreign-{i}')
        one=auth(c,'notedoc1');two=auth(c,'notedoc2')
        listed=c.get('/api/enhanced/notifications',headers=one,params={'limit':500});assert listed.status_code==200,listed.text
        assert [n['id'] for n in listed.json()['notifications']]==[own]
        assert listed.json()['counts']=={'unread':1,'total':1,'open':1}
        assert c.get('/api/enhanced/notifications/counts',headers=one).json()==listed.json()['counts']
        with c.app.state.engine.store.connect() as db:
            assert db.execute('SELECT COUNT(*) FROM notifications WHERE legacy_alert_id=?',(foreign_alert,)).fetchone()[0]==1 # only the deliberately mismatched fixture; not bridged
        assert c.get('/api/enhanced/notifications',headers=one,params={'patient_id':'PG-0002'}).status_code==404
        for nid in (foreign,nonsynthetic,mismatched,shared):
            assert c.get(f'/api/enhanced/notifications/{nid}',headers=one).status_code==404
            assert c.patch(f'/api/enhanced/notifications/{nid}',headers=one,json={'status':'resolved'}).status_code==404
        assert c.get(f'/api/enhanced/notifications/{foreign}',headers=two).status_code==200
        assert c.patch(f'/api/enhanced/notifications/{own}',headers=one,json={'status':'acknowledged'}).status_code==200
        with c.app.state.engine.store.connect() as db:
            assert db.execute('SELECT status FROM alerts WHERE id=?',(foreign_alert,)).fetchone()[0]=='new'
            # Doctor 1's list must not bridge another doctor's alert.
            # Doctor 2's later list can legitimately bridge it.
            db.execute("DELETE FROM doctor_patient_assignments WHERE doctor_id=(SELECT id FROM portal_users WHERE username='notedoc1') AND patient_id='PG-0001'")
        assert c.get(f'/api/enhanced/notifications/{own}',headers=one).status_code==404
        assert c.patch(f'/api/enhanced/notifications/{own}',headers=one,json={'read':True}).status_code==404
        assert c.get('/api/enhanced/notifications').status_code==401


def test_partial_cohort_isolation_empty_synthetic_and_aggregates(tmp_path):
    import json
    with TestClient(create_app(tmp_path/'partial.sqlite',background_tasks=False,legacy_demo=False)) as c:
        e=c.app.state.engine
        with e.store.connect() as db:
            for name in ('scope_a','scope_b','scope_empty'):
                db.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',(name,hash_password(PASSWORD),'doctor',timestamp()))
            ids={r['username']:r['id'] for r in db.execute("SELECT id,username FROM portal_users")}
            db.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(ids['scope_a'],'PG-0001'))
            db.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(ids['scope_b'],'PG-0002'))
            db.execute("INSERT INTO alerts(patient_id,state_version,created_at,risk,horizon,status) VALUES ('PG-0001',1,?,.5,72,'new')",(timestamp(),))
            db.executemany("INSERT INTO alerts(patient_id,state_version,created_at,risk,horizon,status) VALUES ('PG-0002',1,?,.9,72,'new')",[(timestamp(),)]*501)
        a=auth(c,'scope_a');b=auth(c,'scope_b');empty=auth(c,'scope_empty')
        one=c.get('/api/overview',headers=a);assert one.status_code==200
        assert [p['patient_id'] for p in one.json()['patients']]==['PG-0001']
        expected=e.cohort(['PG-0001'])
        assert one.json()['summary']==expected['summary'] and one.json()['trend']==expected['trend']
        assert one.json()['summary']['open_alerts']==1
        assert one.json()['replay']['demo'] is None
        assert 'PG-0002' not in one.text and c.get('/api/patients/PG-0002',headers=a).status_code==404
        assert [p['patient_id'] for p in c.get('/api/patients',headers=b).json()['patients']]==['PG-0002']
        assert c.get('/api/overview',headers=b).json()['summary']['open_alerts']==501
        assert c.get('/api/patients',headers=a,params={'q':'PG-0002'}).json()['patients']==[]
        assert c.get('/api/validation',headers=a).status_code==403
        assert c.get('/api/portal/validation',headers=a).status_code==403
        no=c.get('/api/overview',headers=empty).json()
        assert no['patients']==[] and no['trend']==[] and all(v==0 for v in no['summary'].values())
        assert no['replay']['demo'] is None and c.get('/api/patients',headers=empty).json()['patients']==[]
        with e.store.connect() as db:
            profile=json.loads(db.execute("SELECT profile FROM patients WHERE patient_id='PG-0001'").fetchone()[0]);profile['synthetic']=False
            db.execute("UPDATE patients SET profile=? WHERE patient_id='PG-0001'",(json.dumps(profile),))
        assert c.get('/api/overview',headers=a).json()['patients']==[]
        assert c.get('/api/patients/PG-0001',headers=a).status_code==404
        with e.store.connect() as db:
            profile['synthetic']='true'
            db.execute("UPDATE patients SET profile=? WHERE patient_id='PG-0001'",(json.dumps(profile),))
        assert c.get('/api/overview',headers=a).json()['patients']==[]
        assert c.get('/api/patients/PG-0001',headers=a).status_code==404


def test_followup_completion_is_scoped_audited_and_preserves_review(portal):
    doc=auth(portal,'doc');patient=auth(portal,'alice')
    with portal.app.state.engine.store.connect() as c:
        c.execute("INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,'doctor',?)",('scope_followup_doc',hash_password(PASSWORD),timestamp()))
        other_id=c.execute("SELECT id FROM portal_users WHERE username='scope_followup_doc'").fetchone()[0]
        c.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(other_id,'PG-0002'))
    other=auth(portal,'scope_followup_doc')
    review={'status':'Follow-up Required','notes':'Original review remains intact','follow_up':'Check back','follow_up_date':'2000-01-01','shared':True}
    created=portal.post('/api/portal/patients/PG-0001/reviews',headers=doc,json=review)
    assert created.status_code==201
    rid=created.json()['id'];path=f'/api/portal/patients/PG-0001/reviews/{rid}/complete-followup'
    before=portal.get('/api/portal/doctor-summary',headers=doc).json()['followups_due']
    assert any(i['kind']=='followup' and i['id']==rid for i in portal.get('/api/portal/care-queue',headers=doc).json()['items'])
    assert portal.post(path,headers=patient,json={'notes':'done'}).status_code==403
    assert portal.post(path,headers=other,json={'notes':'done'}).status_code==404
    assert portal.post(path.replace('PG-0001','PG-0002'),headers=other,json={'notes':'done'}).status_code==404
    assert portal.post(path,headers=doc,json={'notes':'  '}).status_code==422
    missing=portal.post('/api/portal/patients/PG-0001/reviews',headers=doc,json={'status':'Reviewed','notes':'No dated follow-up'}).json()['id']
    done=portal.post('/api/portal/patients/PG-0001/reviews',headers=doc,json={'status':'Completed','notes':'Already complete','follow_up_date':'2000-01-01'}).json()['id']
    for closed_id in (missing,done):
        assert portal.post(f'/api/portal/patients/PG-0001/reviews/{closed_id}/complete-followup',headers=doc,json={'notes':'done'}).status_code==409
    result=portal.post(path,headers=doc,json={'notes':'Documented completion'})
    assert result.status_code==201,result.text
    assert portal.post(path,headers=doc,json={'notes':'again'}).status_code==409
    assert portal.get('/api/portal/doctor-summary',headers=doc).json()['followups_due']==before-1
    assert not any(i['kind']=='followup' and i['id']==rid for i in portal.get('/api/portal/care-queue',headers=doc).json()['items'])
    doctor_review=next(r for r in portal.get('/api/portal/patients/PG-0001',headers=doc).json()['reviews'] if r['id']==rid)
    assert doctor_review['notes']==review['notes'] and doctor_review['status']==review['status']
    assert doctor_review['followup_completion_notes']=='Documented completion'
    patient_review=next(r for r in portal.get('/api/portal/patients/PG-0001',headers=patient).json()['reviews'] if r['id']==rid)
    assert 'followup_completion_notes' not in patient_review
    with portal.app.state.engine.store.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM portal_audit WHERE action='followup_completed' AND record_id=?",(rid,)).fetchone()[0]==1


def test_provisioning_rejects_truthy_non_boolean_synthetic_marker(portal,monkeypatch):
    import json
    doc=auth(portal,'doc');monkeypatch.setenv('PRANAGUARD_SYNTHETIC_DEMO_PROVISIONING','1')
    engine=portal.app.state.engine
    with engine.store.connect() as c:
        doc_id=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()[0]
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(doc_id,'PG-0004'))
        original=c.execute("SELECT profile FROM patients WHERE patient_id='PG-0004'").fetchone()[0]
        altered=json.loads(original);altered['synthetic']='true'
        c.execute("UPDATE patients SET profile=? WHERE patient_id='PG-0004'",(json.dumps(altered),))
    try:
        assert portal.post('/api/portal/patients/PG-0004/provision-demo',headers=doc).status_code==404
        with engine.store.connect() as c:assert not c.execute("SELECT 1 FROM portal_users WHERE username='PG-0004'").fetchone()
    finally:
        with engine.store.connect() as c:c.execute("UPDATE patients SET profile=? WHERE patient_id='PG-0004'",(original,))


def test_portal_notification_revocation_and_strict_synthetic_filter(portal):
    import json
    doc=auth(portal,'doc');patient=auth(portal,'alice');engine=portal.app.state.engine
    with engine.store.connect() as c:
        doc_id=c.execute("SELECT id FROM portal_users WHERE username='doc'").fetchone()[0]
        note_id=c.execute("INSERT INTO portal_notifications(user_id,patient_id,title,description,link,created_at) VALUES (?,?,'Scope test','Private','',?)",(doc_id,'PG-0001',timestamp())).lastrowid
        original=c.execute("SELECT profile FROM patients WHERE patient_id='PG-0001'").fetchone()[0]
    def visible():return [n['id'] for n in portal.get('/api/portal/notifications',headers=doc).json()['notifications']]
    assert note_id in visible()
    try:
        with engine.store.connect() as c:c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(doc_id,'PG-0001'))
        assert note_id not in visible()
        assert portal.post(f'/api/portal/notifications/{note_id}/read',headers=doc).status_code==404
        with engine.store.connect() as c:
            c.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(doc_id,'PG-0001'))
            profile=json.loads(original);profile['synthetic']=1
            c.execute("UPDATE patients SET profile=? WHERE patient_id='PG-0001'",(json.dumps(profile),))
        assert note_id not in visible()
        assert portal.get('/api/portal/patients/PG-0001',headers=doc).status_code==404
        assert portal.get('/api/portal/patients/PG-0001',headers=patient).status_code==404
        assert 'PG-0001' not in [p['patient_id'] for p in portal.get('/api/portal/patients',headers=doc).json()['patients']]
        assert all(i['patient_id']!='PG-0001' for i in portal.get('/api/portal/care-queue',headers=doc).json()['items'])
        assert all(p['patient_id']!='PG-0001' for p in portal.get('/api/enhanced/registry/patients',headers=doc).json()['patients'])
    finally:
        with engine.store.connect() as c:
            c.execute("UPDATE patients SET profile=? WHERE patient_id='PG-0001'",(original,))
            c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(doc_id,'PG-0001'))
    assert note_id in visible()


def test_upgrade_from_six_preserves_review_and_applies_followup_completion(tmp_path):
    db=tmp_path/'v6.sqlite';s=Store(db)
    with s.connect() as c:
        c.execute('DROP TABLE followup_completions')
        c.execute('DELETE FROM schema_migrations WHERE version=7')
        c.execute('INSERT INTO patients VALUES (?,?)',('PG-UPGRADE','{"synthetic":true}'))
        c.execute("INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,'doctor',?)",('upgrade_doc',hash_password(PASSWORD),timestamp()))
        uid=c.execute("SELECT id FROM portal_users WHERE username='upgrade_doc'").fetchone()[0]
        c.execute("INSERT INTO doctor_reviews(patient_id,doctor_id,status,notes,follow_up,follow_up_date,shared,created_at) VALUES (?,?,'Follow-up Required','keep review','keep follow-up','2000-01-01',0,?)",('PG-UPGRADE',uid,timestamp()))
    Store(db).apply_migrations()
    with s.connect() as c:
        row=c.execute('SELECT notes,follow_up FROM doctor_reviews WHERE patient_id=?',('PG-UPGRADE',)).fetchone()
        assert tuple(row)==('keep review','keep follow-up')
        assert c.execute('SELECT COUNT(*) FROM followup_completions').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM schema_migrations WHERE version=7').fetchone()[0]==1
        assert not c.execute('PRAGMA foreign_key_check').fetchall()


def test_concurrent_followup_completion_is_single_and_audited(portal):
    from concurrent.futures import ThreadPoolExecutor
    doctor=auth(portal,'doc')
    review=portal.post('/api/portal/patients/PG-0001/reviews',headers=doctor,json={'status':'Follow-up Required','notes':'Concurrent test','follow_up_date':'2000-01-01'}).json()
    path=f"/api/portal/patients/PG-0001/reviews/{review['id']}/complete-followup"
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(lambda _:portal.post(path,headers=doctor,json={'notes':'Recorded once'}).status_code,range(2)))
    assert sorted(statuses)==[201,409]
    with portal.app.state.engine.store.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM followup_completions WHERE review_id=?',(review['id'],)).fetchone()[0]==1
        assert c.execute("SELECT COUNT(*) FROM portal_audit WHERE action='followup_completed' AND record_id=?",(review['id'],)).fetchone()[0]==1


def test_login_throttle_is_persistent_case_insensitive_and_fail_closed(portal):
    from backend.app.portal import login_identifier
    from backend.app.store import Store
    name='rate_test_user'
    with portal.app.state.engine.store.connect() as c:
        c.execute("INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,'patient',?)",(name,hash_password(PASSWORD),timestamp()))
    def login(username,password):return portal.post('/api/portal/login',json={'username':username,'password':password})
    for _ in range(2):assert login(name,'wrong-password').status_code==401
    assert login(name,PASSWORD).status_code==200  # successful authentication clears failures
    for _ in range(5):assert login(name.upper(),'wrong-password').status_code==401
    denied=login(name,PASSWORD)
    assert denied.status_code==429 and int(denied.headers['retry-after'])>0
    with portal.app.state.engine.store.connect() as c:
        row=c.execute('SELECT * FROM portal_login_failures WHERE username_hash=?',(login_identifier(name),)).fetchone()
        assert row['failure_count']==5 and name not in row['username_hash']
    Store(portal.app.state.engine.store.path)  # idempotent restart preserves the active window
    assert login(name,PASSWORD).status_code==429
    with portal.app.state.engine.store.connect() as c:
        c.execute('UPDATE portal_login_failures SET window_expires_at=? WHERE username_hash=?',('2000-01-01T00:00:00+00:00',login_identifier(name)))
    assert login(name,PASSWORD).status_code==200
    with portal.app.state.engine.store.connect() as c:
        assert not c.execute('SELECT 1 FROM portal_login_failures WHERE username_hash=?',(login_identifier(name),)).fetchone()


def test_login_throttle_treats_unknown_accounts_identically_and_serializes_attempts(portal):
    from concurrent.futures import ThreadPoolExecutor
    name='unknown_throttle_account'
    def fail(_):return portal.post('/api/portal/login',json={'username':name,'password':'wrong-password'}).status_code
    with ThreadPoolExecutor(max_workers=8) as pool:statuses=list(pool.map(fail,range(8)))
    assert sorted(statuses)==[401]*5+[429]*3
    with portal.app.state.engine.store.connect() as c:
        assert c.execute('SELECT MAX(failure_count) FROM portal_login_failures').fetchone()[0]==5


def test_upgrade_from_seven_adds_login_throttle_without_losing_review(tmp_path):
    db=tmp_path/'v7.sqlite';s=Store(db)
    with s.connect() as c:
        c.execute('DROP TABLE portal_login_failures')
        c.execute('DELETE FROM schema_migrations WHERE version=8')
        c.execute('INSERT INTO patients VALUES (?,?)',('PG-UPGRADE-8','{"synthetic":true}'))
        c.execute("INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,'doctor',?)",('upgrade_eight',hash_password(PASSWORD),timestamp()))
        uid=c.execute("SELECT id FROM portal_users WHERE username='upgrade_eight'").fetchone()[0]
        c.execute("INSERT INTO doctor_reviews(patient_id,doctor_id,status,notes,follow_up,shared,created_at) VALUES (?,?,'Reviewed','preserve review','',0,?)",('PG-UPGRADE-8',uid,timestamp()))
    Store(db).apply_migrations()
    with s.connect() as c:
        assert c.execute('SELECT notes FROM doctor_reviews WHERE patient_id=?',('PG-UPGRADE-8',)).fetchone()[0]=='preserve review'
        assert c.execute('SELECT COUNT(*) FROM portal_login_failures').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM schema_migrations WHERE version=8').fetchone()[0]==1
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
