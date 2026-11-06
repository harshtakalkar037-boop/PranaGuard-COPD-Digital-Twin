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
    assert portal.get('/api/overview').status_code==403
    assert portal.get('/api/enhanced/registry/patients').status_code==403
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
        assert [r[0] for r in c.execute('SELECT version FROM schema_migrations ORDER BY version')]==[1,2,3,4,5]
        assert not c.execute('PRAGMA foreign_key_check').fetchall()

def test_scoped_research_tools(portal):
    doc=auth(portal,'doc');patient=auth(portal,'alice')
    assert portal.get('/api/portal/validation',headers=doc).status_code==200
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
    temporary=result.json()['temporary_password'];assert temporary=='PG-0003@123'
    assert portal.post(path,headers=doc).status_code==409
    with portal.app.state.engine.store.connect() as c:
        row=c.execute("SELECT password_hash,must_change_password FROM portal_users WHERE username='PG-0003'").fetchone()
        assert temporary not in row['password_hash'] and row['must_change_password']==1
    login=portal.post('/api/portal/login',json={'username':'PG-0003','password':temporary});assert login.status_code==200 and login.json()['must_change_password']
    h={'Authorization':'Bearer '+login.json()['token']}
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
