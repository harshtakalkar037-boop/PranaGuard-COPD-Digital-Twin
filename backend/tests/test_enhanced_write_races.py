"""Secure enhanced mutations recheck identity and assignment under their write lock."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from backend.app import main, portal
from backend.app.main import create_app
from backend.tests.test_portal import PASSWORD, auth

REG={'request_id':'enhanced-race-key-1234','fictional_identity_confirmed':True,'demo_alias':'Synthetic Example','age':58,'city':'Pune'}
OBS={'fictional_data_confirmed':True,'symptom_score':8,'adherence':0.4,'note':'Synthetic observation'}
REV={'kind':'contact','note':'Synthetic review'}


@pytest.fixture(scope='module')
def write_app(tmp_path_factory):
    db=tmp_path_factory.mktemp('enhanced-write-races')/'db.sqlite'
    with TestClient(create_app(db,background_tasks=False,legacy_demo=False)) as client:
        with client.app.state.engine.store.connect() as c:
            c.execute("INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,'doctor',?)",('doctor',portal.hash_password(PASSWORD),portal.timestamp()))
            did=c.execute("SELECT id FROM portal_users WHERE username='doctor'").fetchone()[0]
            c.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)',(did,'PG-0001'))
            aid=c.execute("INSERT INTO alerts(patient_id,state_version,created_at,risk,horizon,status) VALUES ('PG-0001',1,?,.4,72,'new')",(portal.timestamp(),)).lastrowid
            nid=client.app.state.enhanced.notifications.create(category='patient_monitoring',title='test',reason='synthetic test',source='test',source_type='system_demo',patient_id='PG-0001',dedupe_key='race-notification',conn=c)
        yield client,did,aid,nid


@pytest.fixture
def writes(write_app):
    client,did,aid,nid=write_app
    with client.app.state.engine.store.connect() as c:
        c.execute('DELETE FROM portal_sessions')
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(did,'PG-0001'))
        c.execute("UPDATE alerts SET status='new',note='',updated_at=NULL WHERE id=?",(aid,))
        c.execute("UPDATE notifications SET status='active',read_at=NULL WHERE id=?",(nid,))
    yield write_app


def snapshot(client):
    tables=('patients','registrations','demo_observations','interventions','portal_audit','enhanced_audit','notifications','notification_history','alerts')
    with client.app.state.engine.store.connect() as c:
        return {t:[tuple(r) for r in c.execute(f'SELECT * FROM {t} ORDER BY rowid')] for t in tables}


def revoke(store,headers):
    digest=hashlib.sha256(headers['Authorization'][7:].encode()).hexdigest()
    with store.connect() as c:c.execute('DELETE FROM portal_sessions WHERE token_hash=?',(digest,))


def test_revoked_session_cannot_mutate_enhanced_registry_alerts_or_notifications(writes,monkeypatch):
    client,_,aid,nid=writes;store=client.app.state.engine.store
    registry=client.app.state.enhanced.registry;notices=client.app.state.enhanced.notifications
    calls=[('register','post','/api/enhanced/registry/patients',REG),('observation','post','/api/enhanced/registry/patients/PG-0001/observations',OBS),
           ('review','post','/api/enhanced/registry/patients/PG-0001/reviews',REV),('notification','patch',f'/api/enhanced/notifications/{nid}',{'status':'acknowledged','note':'test'}),
           ('alert','patch',f'/api/alerts/{aid}',{'status':'acknowledged','note':'test'})]
    for name,method,path,body in calls:
        headers=auth(client,'doctor');before=snapshot(client)
        with monkeypatch.context() as patch:
            if name=='alert':
                original=main.begin_authorized_write
                def changed(c,request,user):
                    revoke(store,headers)
                    return original(c,request,user)
                patch.setattr(main,'begin_authorized_write',changed)
            else:
                obj=notices if name=='notification' else registry;attr='update' if name=='notification' else name
                original=getattr(obj,attr)
                def changed(*args,**kwargs):
                    revoke(store,headers)
                    return original(*args,**kwargs)
                patch.setattr(obj,attr,changed)
            result=getattr(client,method)(path,headers=headers,json=body)
        assert result.status_code==401,(path,result.status_code,result.text)
        assert snapshot(client)==before,path


def test_unassignment_after_auth_denies_registry_and_alert_mutations(writes,monkeypatch):
    client,did,aid,nid=writes;store=client.app.state.engine.store
    registry=client.app.state.enhanced.registry;notices=client.app.state.enhanced.notifications
    calls=[('observation','post','/api/enhanced/registry/patients/PG-0001/observations',OBS),
           ('review','post','/api/enhanced/registry/patients/PG-0001/reviews',REV),
           ('notification','patch',f'/api/enhanced/notifications/{nid}',{'status':'acknowledged','note':'test'}),
           ('alert','patch',f'/api/alerts/{aid}',{'status':'acknowledged','note':'test'})]
    for name,method,path,body in calls:
        with store.connect() as c:c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)',(did,'PG-0001'))
        headers=auth(client,'doctor');before=snapshot(client)
        def unassign():
            with store.connect() as c:c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(did,'PG-0001'))
        with monkeypatch.context() as patch:
            if name=='alert':
                original=main.begin_authorized_write
                def changed(c,request,user):
                    unassign()
                    return original(c,request,user)
                patch.setattr(main,'begin_authorized_write',changed)
            else:
                obj=notices if name=='notification' else registry;attr='update' if name=='notification' else name
                original=getattr(obj,attr)
                def changed(*args,**kwargs):
                    unassign()
                    return original(*args,**kwargs)
                patch.setattr(obj,attr,changed)
            response=getattr(client,method)(path,headers=headers,json=body)
        assert response.status_code==404,(path,response.status_code,response.text)
        assert snapshot(client)==before,path


def test_registration_retry_requires_current_assignment_and_session(writes,monkeypatch):
    client,did,_,_=writes;store=client.app.state.engine.store
    headers=auth(client,'doctor');url='/api/enhanced/registry/patients'
    made=client.post(url,headers=headers,json=REG);assert made.status_code==200
    pid=made.json()['patient_id'];before=snapshot(client)
    registry=client.app.state.enhanced.registry;original=registry.register
    def unassign_first(*args,**kwargs):
        with store.connect() as c:c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(did,pid))
        return original(*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(registry,'register',unassign_first)
        response=client.post(url,headers=headers,json={**REG,'demo_alias':'Different Example'})
    assert response.status_code==404
    assert snapshot(client)==before


def test_observation_write_lock_orders_revocation_and_atomic_notice(writes,monkeypatch):
    client,did,_,_=writes;store=client.app.state.engine.store
    headers=auth(client,'doctor');registry=client.app.state.enhanced.registry
    locked,release,revoker_started,revoked=Event(),Event(),Event(),Event();original=registry.require
    def hold_lock(pid,conn=None):
        result=original(pid,conn=conn);locked.set();assert release.wait(10);return result
    def remove_assignment():
        revoker_started.set()
        with store.connect() as c:c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(did,'PG-0001'))
        revoked.set()
    with monkeypatch.context() as patch:
        patch.setattr(registry,'require',hold_lock)
        with ThreadPoolExecutor(max_workers=2) as executor:
            pending=executor.submit(client.post,'/api/enhanced/registry/patients/PG-0001/observations',headers=headers,json=OBS)
            try:
                assert locked.wait(10)
                revoker=executor.submit(remove_assignment);assert revoker_started.wait(10)
                assert not revoked.wait(.2)
            finally:release.set()
            result=pending.result(timeout=10);revoker.result(timeout=10)
    assert result.status_code==200 and revoked.is_set()
    oid=result.json()['id']
    with store.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM demo_observations WHERE id=?',(oid,)).fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM notifications WHERE dedupe_key=?',(f'observation:{oid}',)).fetchone()[0]==1
    assert client.post('/api/enhanced/registry/patients/PG-0001/observations',headers=headers,json=OBS).status_code==404


def test_valid_enhanced_review_and_notification_are_consistent(writes):
    client,_,aid,nid=writes;headers=auth(client,'doctor');store=client.app.state.engine.store
    review=client.post('/api/enhanced/registry/patients/PG-0001/reviews',headers=headers,json=REV)
    assert review.status_code==200,review.text
    with store.connect() as c:
        row=c.execute('SELECT * FROM interventions WHERE id=?',(review.json()['id'],)).fetchone()
        event=c.execute("SELECT * FROM enhanced_audit WHERE category='review_created' AND patient_id='PG-0001' ORDER BY id DESC LIMIT 1").fetchone()
        assert row['state_version']==review.json()['state_version'] and json.loads(event['detail'])['intervention_id']==row['id']
    result=client.patch(f'/api/enhanced/notifications/{nid}',headers=headers,json={'status':'acknowledged','note':'test'})
    assert result.status_code==200 and result.json()['status']=='acknowledged'
    assert result.json()['history'][-1]['note']=='test'
    result=client.patch(f'/api/alerts/{aid}',headers=headers,json={'status':'acknowledged','note':'test'})
    assert result.status_code==200 and result.json()['alert']['status']=='acknowledged'


@pytest.mark.parametrize(('path','body','trigger_table'),[
    ('/api/enhanced/registry/patients', {**REG,'request_id':'rollback-test-reg'}, 'enhanced_audit'),
    ('/api/enhanced/registry/patients/PG-0001/observations', OBS, 'notification_history'),
    ('/api/enhanced/registry/patients/PG-0001/reviews', REV, 'enhanced_audit'),
])
def test_secondary_failure_rolls_back_registry_mutation_and_side_effects(writes,path,body,trigger_table):
    import sqlite3
    client,_,_,_=writes;store=client.app.state.engine.store
    headers=auth(client,'doctor');before=snapshot(client)
    with store.connect() as c:
        c.execute(f"CREATE TRIGGER test_failure BEFORE INSERT ON {trigger_table} BEGIN SELECT RAISE(ABORT,'synthetic test failure'); END")
    try:
        with pytest.raises(sqlite3.IntegrityError,match='synthetic test failure'):
            client.post(path,headers=headers,json=body)
    finally:
        with store.connect() as c:c.execute('DROP TRIGGER test_failure')
    assert snapshot(client)==before


def test_synthetic_marker_rechecked_for_each_patient_mutation(writes,monkeypatch):
    client,_,aid,nid=writes;store=client.app.state.engine.store
    registry=client.app.state.enhanced.registry;notices=client.app.state.enhanced.notifications
    calls=[('observation','post','/api/enhanced/registry/patients/PG-0001/observations',OBS),
           ('review','post','/api/enhanced/registry/patients/PG-0001/reviews',REV),
           ('notification','patch',f'/api/enhanced/notifications/{nid}',{'status':'acknowledged'}),
           ('alert','patch',f'/api/alerts/{aid}',{'status':'acknowledged'})]
    with store.connect() as c:profile=c.execute("SELECT profile FROM patients WHERE patient_id='PG-0001'").fetchone()[0]
    for name,method,path,body in calls:
        headers=auth(client,'doctor');before=snapshot(client)
        def unset_synthetic():
            with store.connect() as c:c.execute("UPDATE patients SET profile=json_set(profile,'$.synthetic',json('false')) WHERE patient_id='PG-0001'")
        with monkeypatch.context() as patch:
            if name=='alert':
                original=main.begin_authorized_write
                def changed(c,request,user):
                    unset_synthetic()
                    return original(c,request,user)
                patch.setattr(main,'begin_authorized_write',changed)
            else:
                obj=notices if name=='notification' else registry;attr='update' if name=='notification' else name
                original=getattr(obj,attr)
                def changed(*args,**kwargs):
                    unset_synthetic()
                    return original(*args,**kwargs)
                patch.setattr(obj,attr,changed)
            response=getattr(client,method)(path,headers=headers,json=body)
        assert response.status_code==404,(path,response.status_code,response.text)
        with store.connect() as c:c.execute("UPDATE patients SET profile=? WHERE patient_id='PG-0001'",(profile,))
        assert snapshot(client)==before
