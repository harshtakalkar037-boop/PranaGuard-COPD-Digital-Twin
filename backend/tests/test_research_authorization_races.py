"""Patient-scoped research access is authorized with its database snapshot."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import json

import pytest

from backend.app import main, portal
from backend.app.main import create_app
from backend.tests.test_portal import PASSWORD, auth
from fastapi.testclient import TestClient


@pytest.fixture(scope='module')
def research_app(tmp_path_factory):
    db = tmp_path_factory.mktemp('research-races') / 'db.sqlite'
    with TestClient(create_app(db, background_tasks=False, legacy_demo=False)) as client:
        with client.app.state.engine.store.connect() as c:
            c.execute("INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,'doctor',?)", ('doctor', portal.hash_password(PASSWORD), portal.timestamp()))
            doctor_id = c.execute("SELECT id FROM portal_users WHERE username='doctor'").fetchone()[0]
        yield client, {'doctor': doctor_id}, None


@pytest.fixture
def care(research_app):
    client, ids, _ = research_app
    with client.app.state.engine.store.connect() as c:
        c.execute('DELETE FROM portal_sessions')
        c.execute('DELETE FROM scenarios')
        c.execute('DELETE FROM interventions')
        c.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'], 'PG-0001'))
        state = c.execute("SELECT version,state FROM states WHERE patient_id='PG-0001' ORDER BY version DESC LIMIT 1").fetchone()
        version, original = state['version'], state['state']
    yield research_app
    with client.app.state.engine.store.connect() as c:
        c.execute("UPDATE states SET state=? WHERE patient_id='PG-0001' AND version=?", (original, version))


RESEARCH_CALLS = [
    ('get', '/api/patients/PG-0001', {}),
    ('get', '/api/patients/PG-0001/history', {}),
    ('get', '/api/patients/PG-0001/versions', {}),
    ('get', '/api/patients/PG-0001/explanation', {}),
    ('get', '/api/patients/PG-0001/scenarios', {}),
    ('post', '/api/patients/PG-0001/scenarios', {'json': {}}),
    ('get', '/api/patients/PG-0001/interventions', {}),
    ('get', '/api/portal/patients/PG-0001/explanation', {}),
    ('post', '/api/portal/patients/PG-0001/scenarios', {'json': {}}),
]


@pytest.mark.parametrize(('change', 'status'), [('unassign', 404), ('revoke', 401)])
def test_each_research_handler_rechecks_after_initial_auth(care, monkeypatch, change, status):
    client, ids, _ = care
    store = client.app.state.engine.store
    original = portal.authorize_patient
    def change_before_snapshot(c, request, user, pid):
        # Middleware/current() has already succeeded, but the read snapshot has
        # not yet been established by its first SELECT.
        with store.connect() as admin:
            if change == 'unassign':
                admin.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?', (ids['doctor'], pid))
            else:
                admin.execute('DELETE FROM portal_sessions WHERE token_hash=?', (request.state.portal_session_hash,))
        return original(c, request, user, pid)
    with monkeypatch.context() as patch:
        patch.setattr(main, 'authorize_patient', change_before_snapshot)
        patch.setattr(portal, 'authorize_patient', change_before_snapshot)
        for method, path, kwargs in RESEARCH_CALLS:
            with store.connect() as admin:
                admin.execute('INSERT OR IGNORE INTO doctor_patient_assignments VALUES (?,?)', (ids['doctor'], 'PG-0001'))
                before = (admin.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0], admin.execute('SELECT COUNT(*) FROM interventions').fetchone()[0])
            headers = auth(client, 'doctor')
            result = getattr(client, method)(path, headers=headers, **kwargs)
            assert result.status_code == status, (path, result.status_code, result.text)
            with store.connect() as admin:
                assert (admin.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0], admin.execute('SELECT COUNT(*) FROM interventions').fetchone()[0]) == before


@pytest.mark.parametrize(('change', 'status'), [('unassign', 404), ('revoke', 401)])
def test_intervention_rechecks_before_locked_write(care, monkeypatch, change, status):
    client, ids, _ = care
    headers = auth(client, 'doctor')
    engine = client.app.state.engine
    original_lock = engine.lock
    class ChangeBeforeEngineLock:
        def __enter__(self):
            import hashlib
            with engine.store.connect() as admin:
                if change == 'unassign':
                    admin.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?', (ids['doctor'], 'PG-0001'))
                else:
                    digest = hashlib.sha256(headers['Authorization'][7:].encode()).hexdigest()
                    admin.execute('DELETE FROM portal_sessions WHERE token_hash=?', (digest,))
            original_lock.acquire()
        def __exit__(self, *args):
            original_lock.release()
    with monkeypatch.context() as patch:
        patch.setattr(engine, 'lock', ChangeBeforeEngineLock())
        result = client.post('/api/patients/PG-0001/interventions', headers=headers, json={'kind': 'other', 'note': 'research only'})
    assert result.status_code == status, result.text
    with engine.store.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM interventions').fetchone()[0] == 0


@pytest.mark.parametrize('path', ['/api/patients/PG-0001/scenarios', '/api/portal/patients/PG-0001/scenarios'])
@pytest.mark.parametrize(('change', 'status'), [('unassign', 404), ('revoke', 401)])
def test_scenario_rechecks_before_commit_after_model_computation(care, monkeypatch, path, change, status):
    client, ids, _ = care
    headers = auth(client, 'doctor')
    engine = client.app.state.engine
    model = engine.models[24]
    predict = model.predict
    changed = []
    def change_during_prediction(features):
        if not changed:
            with engine.store.connect() as admin:
                if change == 'unassign':
                    admin.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?', (ids['doctor'], 'PG-0001'))
                else:
                    import hashlib
                    digest = hashlib.sha256(headers['Authorization'][7:].encode()).hexdigest()
                    admin.execute('DELETE FROM portal_sessions WHERE token_hash=?', (digest,))
            changed.append(True)
        return predict(features)
    with engine.store.connect() as c:
        before = c.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0]
        state_before = engine.patient('PG-0001')
    with monkeypatch.context() as patch:
        patch.setattr(model, 'predict', change_during_prediction)
        result = client.post(path, headers=headers, json={})
    assert changed
    assert result.status_code == status, result.text
    with engine.store.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0] == before
    assert engine.patient('PG-0001') == state_before
    assert 'trajectory' not in result.json()


def test_scoped_read_is_consistent_if_assignment_changes_after_snapshot(care, monkeypatch):
    client, ids, _ = care
    headers = auth(client, 'doctor')
    engine = client.app.state.engine
    original_state = engine.patient('PG-0001')
    original = engine.store.latest
    entered, release = Event(), Event()
    def wait_before_state(pid, version=None, conn=None):
        if conn is not None:
            entered.set()
            assert release.wait(10)
        return original(pid, version, conn=conn)
    with monkeypatch.context() as patch:
        patch.setattr(engine.store, 'latest', wait_before_state)
        with ThreadPoolExecutor(max_workers=1) as executor:
            read = executor.submit(client.get, '/api/patients/PG-0001', headers=headers)
            try:
                assert entered.wait(10)
                with engine.store.connect() as admin:
                    admin.execute('DELETE FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?', (ids['doctor'], 'PG-0001'))
                    changed = {**original_state, 'model_version': 'changed-after-snapshot'}
                    admin.execute('UPDATE states SET state=? WHERE patient_id=? AND version=?', (json.dumps(changed), 'PG-0001', original_state['version']))
            finally:
                release.set()
            result = read.result(timeout=10)
    assert result.status_code == 200
    assert result.json() == original_state
    assert engine.patient('PG-0001')['model_version'] == 'changed-after-snapshot'
    assert client.get('/api/patients/PG-0001', headers=headers).status_code == 404


def test_authorized_scenario_and_intervention_preserve_twin_state(care):
    client, _, _ = care
    headers = auth(client, 'doctor')
    engine = client.app.state.engine
    before = engine.patient('PG-0001')
    portal_result = client.post('/api/portal/patients/PG-0001/scenarios', headers=headers, json={})
    legacy_result = client.post('/api/patients/PG-0001/scenarios', headers=headers, json={})
    assert portal_result.status_code == legacy_result.status_code == 200
    portal_body, legacy_body = portal_result.json(), legacy_result.json()
    assert portal_body.pop('scenario_id') != legacy_body.pop('scenario_id')
    assert portal_body == legacy_body
    intervention = client.post('/api/patients/PG-0001/interventions', headers=headers, json={'kind': 'other', 'note': 'synthetic test'})
    assert intervention.status_code == 200
    assert intervention.json()['intervention']['patient_id'] == 'PG-0001'
    assert engine.patient('PG-0001') == before
