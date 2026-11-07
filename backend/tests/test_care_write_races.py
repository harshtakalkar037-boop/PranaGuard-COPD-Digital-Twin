"""Authorization is checked again at the serialized care-write boundary."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import hashlib

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app import portal as routes
from backend.tests.test_portal import PASSWORD, auth


@pytest.fixture
def care(tmp_path, monkeypatch):
    monkeypatch.setenv('PRANAGUARD_UPLOAD_DIR', str(tmp_path / 'uploads'))
    monkeypatch.setenv('PRANAGUARD_SYNTHETIC_DEMO_PROVISIONING', '1')
    with TestClient(create_app(tmp_path / 'db.sqlite', background_tasks=False, legacy_demo=False)) as client:
        with client.app.state.engine.store.connect() as c:
            for name, role in [('doctor', 'doctor'), ('patient', 'patient')]:
                c.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',
                          (name, routes.hash_password(PASSWORD), role, routes.timestamp()))
            ids = {r['username']: r['id'] for r in c.execute('SELECT id,username FROM portal_users')}
            c.execute('INSERT INTO patient_user_links VALUES (?,?)', (ids['patient'], 'PG-0001'))
            c.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'], 'PG-0001'))
            c.execute('INSERT INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'], 'PG-0002'))
        yield client, ids, tmp_path / 'uploads'


CHECKIN = {'breathlessness': 'mild', 'cough': 'none', 'sputum_amount': 'usual', 'sputum_colour': 'clear', 'wheezing': 'no', 'fatigue': 'mild', 'fever': 'no'}
SPUTUM = {'observed_at': '2026-11-01T12:00:00Z', 'colour': 'clear', 'amount': 'small', 'consistency': 'thin', 'cough': 'mild'}
DAILY = {'kind': 'meal', 'occurred_at': '2026-11-01T12:00:00Z', 'item': 'Breakfast', 'status': 'Completed', 'client_key': 'race-test-key-12345'}


def snapshot(client):
    tables = ('symptom_checkins', 'patient_uploads', 'doctor_reviews', 'portal_notifications',
              'sputum_entries', 'sputum_entry_history', 'sputum_reviews', 'care_plan_versions',
              'daily_care_logs', 'daily_care_reviews', 'portal_audit', 'followup_completions',
              'patient_user_links', 'portal_users')
    with client.app.state.engine.store.connect() as c:
        return {t: [tuple(r) for r in c.execute(f'SELECT * FROM {t} ORDER BY rowid')] for t in tables}


def test_session_revocation_at_write_boundary_covers_every_care_mutation(care, monkeypatch):
    client, _, directory = care
    patient, doctor = auth(client, 'patient'), auth(client, 'doctor')
    entry = client.post('/api/portal/sputum', headers=patient, json=SPUTUM).json()['id']
    log = client.post('/api/portal/daily-care', headers=patient, json=DAILY).json()['id']
    review = client.post('/api/portal/patients/PG-0001/reviews', headers=doctor, json={
        'status': 'Follow-up Required', 'notes': 'follow up', 'follow_up_date': '2030-01-01'}).json()['id']
    notice = client.get('/api/portal/notifications', headers=doctor).json()['notifications'][0]['id']
    original = routes.begin_authorized_write
    def revoke_then_begin(c, request, user):
        # Different connection commits after current() but before the protected transaction.
        with client.app.state.engine.store.connect() as revoker:
            revoker.execute('DELETE FROM portal_sessions WHERE token_hash=?', (request.state.portal_session_hash,))
        return original(c, request, user)
    calls = [
        ('patient', 'post', '/api/portal/checkins', {'json': CHECKIN}),
        ('patient', 'post', '/api/portal/sputum', {'json': SPUTUM}),
        ('patient', 'put', f'/api/portal/sputum/{entry}', {'json': SPUTUM}),
        ('patient', 'post', '/api/portal/daily-care', {'json': DAILY}),
        ('patient', 'post', '/api/portal/uploads', {'data': {'kind': 'photo', 'sputum_entry_id': str(entry)}, 'files': {'file': ('sample.png', b'\x89PNG\r\n\x1a\nsynthetic', 'image/png')}}),
        ('doctor', 'post', '/api/portal/patients/PG-0001/reviews', {'json': {'status': 'Reviewed', 'notes': 'test', 'shared': True}}),
        ('doctor', 'post', f'/api/portal/patients/PG-0001/sputum/{entry}/reviews', {'json': {'notes': 'test', 'shared': True}}),
        ('doctor', 'post', '/api/portal/patients/PG-0001/care-plan', {'json': {'title': 'plan', 'start_date': '2026-01-01'}}),
        ('doctor', 'post', f'/api/portal/patients/PG-0001/daily-care/{log}/reviews', {'json': {'notes': 'test', 'shared': True}}),
        ('doctor', 'post', '/api/portal/patients/PG-0002/provision-demo', {}),
        ('doctor', 'post', f'/api/portal/patients/PG-0001/reviews/{review}/complete-followup', {'json': {'notes': 'completed'}}),
        ('doctor', 'post', f'/api/portal/notifications/{notice}/read', {}),
    ]
    before = snapshot(client)
    with monkeypatch.context() as patch:
        patch.setattr(routes, 'begin_authorized_write', revoke_then_begin)
        for name, method, path, kwargs in calls:
            headers = auth(client, name)
            response = getattr(client, method)(path, headers=headers, **kwargs)
            assert response.status_code == 401, (path, response.status_code, response.text)
            assert snapshot(client) == before, path
            assert not directory.exists() or list(directory.iterdir()) == []


def test_assignment_removal_and_patient_relink_before_transaction(care, monkeypatch):
    client, ids, _ = care
    doctor, patient = auth(client, 'doctor'), auth(client, 'patient')
    original = routes.begin_authorized_write
    def unassign(c, request, user):
        with client.app.state.engine.store.connect() as admin:
            admin.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?', (ids['doctor'], 'PG-0001'))
        return original(c, request, user)
    before = snapshot(client)
    with monkeypatch.context() as patch:
        patch.setattr(routes, 'begin_authorized_write', unassign)
        result = client.post('/api/portal/patients/PG-0001/reviews', headers=doctor, json={'status': 'Reviewed', 'notes': 'test', 'shared': True})
    assert result.status_code == 404
    assert snapshot(client) == before
    def relink(c, request, user):
        with client.app.state.engine.store.connect() as admin:
            admin.execute('UPDATE patient_user_links SET patient_id=? WHERE user_id=?', ('PG-0002', ids['patient']))
        return original(c, request, user)
    with monkeypatch.context() as patch:
        patch.setattr(routes, 'begin_authorized_write', relink)
        result = client.post('/api/portal/checkins', headers=patient, json=CHECKIN)
    assert result.status_code == 409
    after = snapshot(client)
    assert after['symptom_checkins'] == before['symptom_checkins']
    assert after['portal_notifications'] == before['portal_notifications']


def test_upload_rechecks_link_and_diary_after_staging_and_removes_orphan(care, monkeypatch):
    client, ids, directory = care
    patient = auth(client, 'patient')
    entry = client.post('/api/portal/sputum', headers=patient, json=SPUTUM).json()['id']
    before = snapshot(client)
    original = routes.begin_authorized_write
    def relink_after_file_written(c, request, user):
        assert len(list(directory.iterdir())) == 1  # read and staging completed
        with client.app.state.engine.store.connect() as admin:
            admin.execute('UPDATE patient_user_links SET patient_id=? WHERE user_id=?', ('PG-0002', ids['patient']))
        return original(c, request, user)
    with monkeypatch.context() as patch:
        patch.setattr(routes, 'begin_authorized_write', relink_after_file_written)
        result = client.post('/api/portal/uploads', headers=patient, data={'kind': 'photo', 'sputum_entry_id': str(entry)}, files={'file': ('sample.png', b'\x89PNG\r\n\x1a\nsynthetic', 'image/png')})
    assert result.status_code == 409
    assert list(directory.iterdir()) == []
    after = snapshot(client)
    for table in ('patient_uploads', 'sputum_entries', 'portal_notifications'):
        assert after[table] == before[table]
    # Even without a link change, an attachment removed after the first check fails closed.
    with client.app.state.engine.store.connect() as admin:
        admin.execute('UPDATE patient_user_links SET patient_id=? WHERE user_id=?', ('PG-0001', ids['patient']))
    def remove_diary(c, request, user):
        with client.app.state.engine.store.connect() as admin:
            admin.execute('DELETE FROM sputum_entries WHERE id=?', (entry,))
        return original(c, request, user)
    with monkeypatch.context() as patch:
        patch.setattr(routes, 'begin_authorized_write', remove_diary)
        result = client.post('/api/portal/uploads', headers=patient, data={'kind': 'photo', 'sputum_entry_id': str(entry)}, files={'file': ('sample.png', b'\x89PNG\r\n\x1a\nsynthetic', 'image/png')})
    assert result.status_code == 404
    assert list(directory.iterdir()) == []
    assert snapshot(client)['patient_uploads'] == before['patient_uploads']


def test_existing_idempotency_key_does_not_cross_patient_relink(care):
    client, ids, _ = care
    patient = auth(client, 'patient')
    assert client.post('/api/portal/daily-care', headers=patient, json=DAILY).status_code == 201
    with client.app.state.engine.store.connect() as c:
        c.execute('UPDATE patient_user_links SET patient_id=? WHERE user_id=?', ('PG-0002', ids['patient']))
    duplicate = client.post('/api/portal/daily-care', headers=patient, json=DAILY)
    assert duplicate.status_code == 409 and 'id' not in duplicate.json()


def test_revocation_waits_for_already_locked_write(care, monkeypatch):
    client, _, _ = care
    patient = auth(client, 'patient')
    token_hash = hashlib.sha256(patient['Authorization'][7:].encode()).hexdigest()
    locked, release, revoker_started, revoked = Event(), Event(), Event(), Event()
    original = routes.begin_authorized_write
    def hold_lock(c, request, user):
        original(c, request, user)
        locked.set()
        assert release.wait(10)
    def revoke():
        revoker_started.set()
        with client.app.state.engine.store.connect() as c:
            c.execute('DELETE FROM portal_sessions WHERE token_hash=?', (token_hash,))
        revoked.set()
    with monkeypatch.context() as patch:
        patch.setattr(routes, 'begin_authorized_write', hold_lock)
        with ThreadPoolExecutor(max_workers=2) as executor:
            write = executor.submit(client.post, '/api/portal/checkins', headers=patient, json=CHECKIN)
            try:
                assert locked.wait(10)
                revoke_task = executor.submit(revoke)
                assert revoker_started.wait(10)
                assert not revoked.wait(0.2)
            finally:
                release.set()
            assert write.result(timeout=10).status_code == 201
            revoke_task.result(timeout=10)
    assert revoked.is_set()
    assert client.post('/api/portal/checkins', headers=patient, json=CHECKIN).status_code == 401
    with client.app.state.engine.store.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM symptom_checkins').fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM portal_notifications WHERE title='New symptom check-in'").fetchone()[0] == 1


@pytest.mark.parametrize(('change', 'expected'), [('expire', 401), ('role', 401), ('password', 403), ('unlink', 409), ('non_synthetic', 409)])
def test_account_link_and_synthetic_status_rechecked_under_lock(care, monkeypatch, change, expected):
    client, ids, _ = care
    patient = auth(client, 'patient')
    before = snapshot(client)
    original = routes.begin_authorized_write
    def mutate_before_lock(c, request, user):
        with client.app.state.engine.store.connect() as admin:
            if change == 'expire':
                admin.execute("UPDATE portal_sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE token_hash=?", (request.state.portal_session_hash,))
            elif change == 'role':
                admin.execute("UPDATE portal_users SET role='doctor' WHERE id=?", (ids['patient'],))
            elif change == 'password':
                admin.execute('UPDATE portal_users SET must_change_password=1 WHERE id=?', (ids['patient'],))
            elif change == 'unlink':
                admin.execute('DELETE FROM patient_user_links WHERE user_id=?', (ids['patient'],))
            else:
                admin.execute("UPDATE patients SET profile=json_set(profile,'$.synthetic',json('false')) WHERE patient_id='PG-0001'")
        return original(c, request, user)
    with monkeypatch.context() as patch:
        patch.setattr(routes, 'begin_authorized_write', mutate_before_lock)
        result = client.post('/api/portal/checkins', headers=patient, json=CHECKIN)
    assert result.status_code == expected, result.text
    after = snapshot(client)
    assert after['symptom_checkins'] == before['symptom_checkins']
    assert after['portal_notifications'] == before['portal_notifications']
