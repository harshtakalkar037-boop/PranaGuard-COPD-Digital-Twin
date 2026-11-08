"""External research models (v7) — registry integrity, honest metrics, inference contracts, isolation from the twin."""
import io, json, math, struct, wave

import pytest


def _wav_bytes(seconds=1.0, sr=16000, hz=200):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        frames = b''.join(struct.pack('<h', int(8000*math.sin(2*math.pi*hz*i/sr)*math.sin(2*math.pi*6*i/sr))) for i in range(int(sr*seconds)))
        w.writeframes(frames)
    return buf.getvalue()

# ---------- registry ----------
def test_registry_lists_only_external_research_models(client):
    r = client.get('/api/models/registry'); assert r.status_code == 200
    models = r.json()['models']
    ids = {m['model_id'] for m in models}
    assert ids == {'cough-copd-rf-calibrated', 'tolife-longitudinal-probe-v2'}
    assert all('pg-synthetic' not in m['model_id'] for m in models), 'production twin must not appear in the external registry'

def test_registry_rows_are_complete(client):
    for m in client.get('/api/models/registry').json()['models']:
        for field in ('model_id', 'model_display_name', 'model_kind', 'version', 'dataset_source', 'task_type',
                      'feature_schema', 'preprocessing', 'evaluation', 'limitations', 'provenance_evidence_class'):
            assert m[field] not in (None, '', [], {}), f'{m["model_id"]}.{field} missing'
        assert m['limitations'], 'limitations must not be hidden'

# ---------- model B: cough ----------
def test_cough_info_reports_real_executed_metrics(client):
    info = client.get('/api/models/cough/info').json()
    t = info['test_metrics']
    assert round(t['auroc'], 4) == 0.9316 and round(t['auprc'], 4) == 0.8293
    assert t['prevalence_copd'] > 0, 'AUPRC must always be shown with its prevalence baseline'
    assert round(t['sensitivity_copd'], 3) == 0.578, 'low COPD sensitivity must be disclosed, not hidden'
    assert any('participant' in l.lower() for l in info['limitations'])
    assert any(('diagnos' in l.lower() or 'screening' in l.lower()) for l in info['limitations'])
    assert info['train']['n'] + info['test']['n'] == 853

def test_cough_info_never_calls_itself_diagnostic(client):
    info = client.get('/api/models/cough/info').json()
    blob = json.dumps({k: v for k, v in info.items() if k != 'limitations'}).lower()
    for banned in ('screening tool', 'diagnostic accuracy', 'clinical triage'):
        assert banned not in blob

def test_cough_inference_real_artifact_and_persisted(client):
    r = client.post('/api/models/cough/infer', files={'file': ('c.wav', _wav_bytes(), 'audio/wav')})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out['class_label'] in ('COPD', 'Healthy')
    assert 0.0 <= out['p_copd'] <= 1.0 and abs(out['p_copd'] + out['p_healthy'] - 1) < 1e-3
    assert 'NOT a diagnosis' in out['disclaimer'] or 'not a diagnosis' in out['disclaimer'].lower()
    hist = client.get('/api/models/cough/history').json()
    assert hist['count'] >= 1 and hist['predictions'][0]['input_hash'] == out['input_hash']

def test_cough_inference_rejects_garbage_without_faking(client):
    r = client.post('/api/models/cough/infer', files={'file': ('x.bin', b'not audio at all', 'application/octet-stream')})
    assert r.status_code in (400, 503), 'garbage input must error, never produce an invented prediction'
    r = client.post('/api/models/cough/infer', files={'file': ('short.wav', _wav_bytes(0.005), 'audio/wav')})
    assert r.status_code in (400, 503)

def test_cough_attribution_is_own_importance_not_shap(client):
    r = client.get('/api/models/cough/attribution'); assert r.status_code == 200
    body = r.json()
    assert 'shap' not in json.dumps(body).lower(), 'external model explainability must not reuse the twin SHAP implementation'
    assert len(body['global_feature_importance']) == 20
    imp = body['global_feature_importance'][0]
    assert imp['feature'] == 'logmel3_mean' and abs(imp['importance'] - 0.04009) < 2e-4

# ---------- model C: TOLIFE ----------
def test_tolife_overview_reconciled_counts_and_weak_horizons(client):
    ov = client.get('/api/models/tolife/overview').json()
    a = ov['event_audit']
    assert a['total_entries'] == 80 and a['unique_participants'] == 42 and a['missing_dates'] == 0
    assert a['observed_frame']['inside'] == 42 and a['observed_frame']['inside'] + a['observed_frame']['outside'] == 80
    assert a['events_with_valid_measurements_in_prior_7d'] == 32
    assert a['in_frame_events_with_prior_7d_measurements'] == 30
    hs = ov['horizons']
    for h, auroc in (('24', 0.355), ('48', 0.389), ('72', 0.393)):
        assert round(hs[h]['auroc'], 3) == auroc
        lo, hi = hs[h]['auroc_ci']
        assert lo < 0.5 and hi <= 0.6, 'CIs must stay visible and honest (at or below chance; 72h upper 0.523)'
        assert hs[h]['auprc'] > 0 and hs[h]['prevalence'] is not None

def test_tolife_corrected_experiment_note_and_no_symptom_channel_leak(client):
    ov = client.get('/api/models/tolife/overview').json()
    assert 'corrected' in ov['corrected_experiment_note'].lower() or 'leakage' in ov['corrected_experiment_note'].lower()
    series = client.get('/api/models/tolife/series').json()
    assert series['n_in_frame_events'] == 42
    assert 'CAT/CCQ/mMRC' in series['channels_note'] and 'EXCLUDED' in series['channels_note']
    channels = set(series['series'])
    assert not channels & {'cat_score', 'ccq_score', 'mmrc_grade'}, 'study-model-estimated symptom classes must not render as observed channels'

def test_tolife_participants_coded_identities_only(client):
    p = client.get('/api/models/tolife/participants').json()
    assert p['count'] == 86
    assert all(pt['participant_id'].startswith('tolife:') for pt in p['participants'])
    assert all('PG-' not in pt['participant_id'] for pt in p['participants']), 'no identity merging with platform patients'

# ---------- isolation & migration ----------
def test_twin_untouched_by_research_init(client):
    h = client.get('/api/health').json()
    assert h['status'] == 'ok' and h['model_version'].startswith('pg-synthetic')
    ov = client.get('/api/overview').json()
    assert ov['summary']['total'] == 120

def test_migration_006_tables_seeded(client):
    store = client.app.state.engine.store
    with store.connect() as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'model_registry', 'model_predictions', 'experiment_runs', 'research_cough_recordings',
                'research_tolife_participants', 'research_tolife_events', 'research_evaluation_metrics'} <= tables
        assert c.execute('SELECT COUNT(*) FROM research_cough_recordings').fetchone()[0] == 853
        assert c.execute('SELECT COUNT(*) FROM research_tolife_events').fetchone()[0] == 80
        assert c.execute('SELECT COUNT(*) FROM research_tolife_participants').fetchone()[0] == 86
        assert c.execute("SELECT COUNT(*) FROM experiment_runs WHERE status='complete'").fetchone()[0] >= 2
        assert c.execute('SELECT DISTINCT version FROM schema_migrations').fetchall(), 'migration ledger intact'
