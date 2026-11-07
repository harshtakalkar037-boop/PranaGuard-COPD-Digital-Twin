"""Portal read authorization and SQLite result snapshots share an ordering."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app import portal
from backend.app.main import create_app
from backend.tests.test_portal import PASSWORD, auth
from backend.tests.test_care_write_races import CHECKIN, DAILY, SPUTUM


@pytest.fixture(scope='module')
def read_app(tmp_path_factory):
    temp = tmp_path_factory.mktemp('portal-read-races')
    patch = pytest.MonkeyPatch()
    patch.setenv('PRANAGUARD_UPLOAD_DIR', str(temp / 'uploads'))
    try:
        with TestClient(create_app(temp/'db.sqlite', background_tasks=False, legacy_demo=False)) as client:
            with client.app.state.engine.store.connect() as c:
                for name, role in [('doctor', 'doctor'), ('patient', 'patient')]:
                    c.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)', (name, portal.hash_password(PASSWORD), role, portal.timestamp()))
                ids = {r['username']:r['id'] for r in c.execute('SELECT id,username FROM portal_users')}
                c.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'], 'PG-0001'))
                c.execute('INSERT INTO patient_user_links VALUES (?,?)', (ids['patient'], 'PG-0001'))
            patient, doctor = auth(client, 'patient'), auth(client, 'doctor')
            checkin = client.post('/api/portal/checkins', headers=patient, json=CHECKIN); assert checkin.status_code == 201
            sputum = client.post('/api/portal/sputum', headers=patient, json=SPUTUM); assert sputum.status_code == 201
            daily = client.post('/api/portal/daily-care', headers=patient, json=DAILY); assert daily.status_code == 201
            upload = client.post('/api/portal/uploads', headers=patient, data={'kind':'care_plan'}, files={'file':('sample.pdf',b'%PDF-synthetic','application/pdf')}); assert upload.status_code == 201
            plan = client.post('/api/portal/patients/PG-0001/care-plan', headers=doctor, json={'title':'Synthetic plan','start_date':'2026-01-01'}); assert plan.status_code == 201
            yield client, ids, {'checkin':checkin.json()['id'], 'upload':upload.json()['id']}
    finally:
        patch.undo()


@pytest.fixture
def reads(read_app):
    client, ids, _ = read_app
    with client.app.state.engine.store.connect() as c:
        c.execute('DELETE FROM portal_sessions')
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'], 'PG-0001'))
        c.execute('INSERT INTO patient_user_links(user_id,patient_id) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET patient_id=excluded.patient_id', (ids['patient'], 'PG-0001'))
    yield read_app


def paths(record):
    return [
        '/api/portal/me', '/api/portal/patients', '/api/portal/patients/PG-0001',
        f"/api/portal/patients/PG-0001/queue-items/checkin/{record['checkin']}",
        '/api/portal/patients/PG-0001/history/checkins', '/api/portal/patients/PG-0001/history/plans',
        '/api/portal/patients/PG-0001/sputum', '/api/portal/patients/PG-0001/care-plan',
        '/api/portal/patients/PG-0001/daily-care',
        '/api/portal/patients/PG-0001/daily-summary?start=2026-11-01T00:00:00Z&end=2026-11-02T00:00:00Z',
        '/api/portal/patients/PG-0001/environment', f"/api/portal/uploads/{record['upload']}",
        '/api/portal/notifications', '/api/portal/care-queue', '/api/portal/doctor-summary', '/api/portal/validation',
    ]


def test_revocation_after_auth_before_every_portal_read(reads, monkeypatch):
    client, _, record = reads
    store = client.app.state.engine.store
    original = portal.begin_authorized_read
    def revoke_before_read(c, request, user, **kwargs):
        with store.connect() as admin:
            admin.execute('DELETE FROM portal_sessions WHERE token_hash=?', (request.state.portal_session_hash,))
        return original(c, request, user, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(portal, 'begin_authorized_read', revoke_before_read)
        for path in paths(record):
            result = client.get(path, headers=auth(client, 'doctor'))
            assert result.status_code == 401, (path, result.status_code, result.text)


def test_unassign_and_unlink_after_auth_before_portal_read(reads, monkeypatch):
    client, ids, record = reads
    store = client.app.state.engine.store
    original = portal.begin_authorized_read
    def unassign(c, request, user):
        with store.connect() as admin:
            admin.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?', (ids['doctor'], 'PG-0001'))
        return original(c, request, user)
    individual = [p for p in paths(record) if '/patients/PG-0001' in p or '/uploads/' in p]
    with monkeypatch.context() as patch:
        patch.setattr(portal, 'begin_authorized_read', unassign)
        for path in individual:
            with store.connect() as c:
                c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'], 'PG-0001'))
            result = client.get(path, headers=auth(client, 'doctor'))
            assert result.status_code == 404, (path, result.status_code, result.text)
        # Collection endpoints stay available, but do not include the unassigned patient.
        for path in ['/api/portal/patients','/api/portal/notifications','/api/portal/care-queue','/api/portal/doctor-summary']:
            with store.connect() as c:
                c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'], 'PG-0001'))
            result = client.get(path, headers=auth(client, 'doctor'))
            assert result.status_code == 200
            assert 'PG-0001' not in result.text
            if path.endswith('doctor-summary'): assert result.json()['assigned'] == 0
    def unlink(c, request, user):
        with store.connect() as admin:
            admin.execute('DELETE FROM patient_user_links WHERE user_id=?', (ids['patient'],))
        return original(c, request, user)
    patient_paths = [p for p in individual if '/queue-items/' not in p and '/history/plans' not in p]
    with monkeypatch.context() as patch:
        patch.setattr(portal, 'begin_authorized_read', unlink)
        for path in patient_paths:
            with store.connect() as c:
                c.execute('INSERT OR IGNORE INTO patient_user_links VALUES (?,?)', (ids['patient'], 'PG-0001'))
            result = client.get(path, headers=auth(client, 'patient'))
            assert result.status_code == 409, (path, result.status_code, result.text)


def test_portal_detail_uses_one_snapshot_for_access_care_and_twin(reads, monkeypatch):
    client, ids, record = reads
    engine = client.app.state.engine
    doctor = auth(client, 'doctor')
    before = client.get('/api/portal/patients/PG-0001', headers=doctor).json()
    entered, release = Event(), Event()
    original = portal.access
    def pause_after_session_snapshot(c, user, pid):
        entered.set()
        assert release.wait(10)
        return original(c, user, pid)
    with monkeypatch.context() as patch:
        patch.setattr(portal, 'access', pause_after_session_snapshot)
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(client.get, '/api/portal/patients/PG-0001', headers=doctor)
            try:
                assert entered.wait(10)
                with engine.store.connect() as admin:
                    admin.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?', (ids['doctor'],'PG-0001'))
                    admin.execute("UPDATE symptom_checkins SET comments='changed-after-snapshot' WHERE id=?", (record['checkin'],))
                    state = admin.execute("SELECT version,state FROM states WHERE patient_id='PG-0001' ORDER BY version DESC LIMIT 1").fetchone()
                    changed = json.loads(state['state']);changed['model_version']='changed-after-snapshot'
                    admin.execute("UPDATE states SET state=? WHERE patient_id='PG-0001' AND version=?", (json.dumps(changed),state['version']))
            finally:
                release.set()
            response = pending.result(timeout=10)
    assert response.status_code == 200
    assert response.json() == before
    assert client.get('/api/portal/patients/PG-0001', headers=doctor).status_code == 404
    with engine.store.connect() as admin:
        admin.execute('UPDATE symptom_checkins SET comments=? WHERE id=?', (before['checkins'][0]['comments'],record['checkin']))
        admin.execute("UPDATE states SET state=? WHERE patient_id='PG-0001' AND version=?", (json.dumps(before['twin']),before['twin']['version']))


@pytest.mark.parametrize(('change','status'), [('revoke',401),('unassign',404),('unlink',409),('city',409)])
def test_environment_rechecks_after_provider_response(reads, monkeypatch, change, status):
    client, ids, _ = reads
    store = client.app.state.engine.store
    if change == 'unlink':
        headers = auth(client, 'patient'); pid='PG-0001'
    else:
        headers = auth(client, 'doctor'); pid='PG-0001'
    if change == 'city':
        pid='PG-MANUAL'
        with store.connect() as c:
            c.execute('INSERT INTO patients(patient_id,profile) VALUES (?,?)', (pid,json.dumps({'patient_id':pid,'synthetic':True,'city':'Pune'})))
            c.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'],pid))
    seen=[]
    async def get_and_change(city):
        seen.append(city)
        with store.connect() as c:
            if change == 'revoke':
                digest=hashlib.sha256(headers['Authorization'][7:].encode()).hexdigest()
                c.execute('DELETE FROM portal_sessions WHERE token_hash=?', (digest,))
            elif change == 'unassign': c.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(ids['doctor'],pid))
            elif change == 'unlink': c.execute('DELETE FROM patient_user_links WHERE user_id=?',(ids['patient'],))
            else: c.execute("UPDATE patients SET profile=json_set(profile,'$.city','Delhi') WHERE patient_id=?",(pid,))
        return {'city':city, 'test':'provider response'}
    with monkeypatch.context() as patch:
        patch.setattr(client.app.state.enhanced.environment, 'get', get_and_change)
        response=client.get(f'/api/portal/patients/{pid}/environment',headers=headers)
    assert seen
    assert response.status_code == status, response.text
    assert 'test' not in response.json()
    if change == 'city':
        with store.connect() as c:
            c.execute('DELETE FROM doctor_patient_assignments WHERE patient_id=?',(pid,))
            c.execute('DELETE FROM patients WHERE patient_id=?',(pid,))


def test_download_uses_snapshot_and_can_complete_after_revocation(reads, monkeypatch):
    client, ids, record = reads
    doctor = auth(client, 'doctor')
    engine = client.app.state.engine
    entered, release = Event(), Event()
    original = portal.access
    def pause_after_download_metadata(c,user,pid):
        entered.set()
        assert release.wait(10)
        return original(c,user,pid)
    with monkeypatch.context() as patch:
        patch.setattr(portal, 'access', pause_after_download_metadata)
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending=executor.submit(client.get,f"/api/portal/uploads/{record['upload']}",headers=doctor)
            try:
                assert entered.wait(10)
                with engine.store.connect() as admin:
                    admin.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(ids['doctor'],'PG-0001'))
            finally:
                release.set()
            response=pending.result(timeout=10)
    assert response.status_code == 200 and response.content == b'%PDF-synthetic'
    assert client.get(f"/api/portal/uploads/{record['upload']}",headers=doctor).status_code == 404


def test_me_rechecks_patient_link_and_temporary_password_expiry(reads, monkeypatch):
    client, ids, _ = reads
    store=client.app.state.engine.store
    patient=auth(client,'patient')
    original=portal.begin_authorized_read
    def unlink_before_me(c,request,user,**kwargs):
        with store.connect() as admin:
            admin.execute('DELETE FROM patient_user_links WHERE user_id=?',(ids['patient'],))
        return original(c,request,user,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(portal,'begin_authorized_read',unlink_before_me)
        response=client.get('/api/portal/me',headers=patient)
    assert response.status_code==409
    with store.connect() as c:
        c.execute('INSERT INTO patient_user_links VALUES (?,?)',(ids['patient'],'PG-0001'))
        c.execute('UPDATE portal_users SET must_change_password=1,temporary_password_expires_at=?,temporary_password_used_at=? WHERE id=?',(portal.temporary_password_expiration(),portal.timestamp(),ids['patient']))
    try:
        assert client.get('/api/portal/me',headers=patient).json()['must_change_password'] == 1
        def expire_before_me(c,request,user,**kwargs):
            with store.connect() as admin:
                admin.execute("UPDATE portal_users SET temporary_password_expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",(ids['patient'],))
            return original(c,request,user,**kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(portal,'begin_authorized_read',expire_before_me)
            response=client.get('/api/portal/me',headers=patient)
        assert response.status_code==401
    finally:
        with store.connect() as c:
            c.execute('UPDATE portal_users SET must_change_password=0,temporary_password_expires_at=NULL,temporary_password_used_at=NULL WHERE id=?',(ids['patient'],))
