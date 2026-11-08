"""Research model services — model registry, cough inference, TOLIFE longitudinal research data.

All external research models are reference artifacts evaluated by the separate research repository
pipeline. The production Digital Twin model in this same repository remains untouched:
these services never retrain, reload, merge or resample it.

Audio inference: only when soundfile + the trained joblib artifact are present; otherwise
explicitly reports inference unavailable (never returns fake predictions).
"""
import csv, gzip, hashlib, io, json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ART_DIR = Path(__file__).parent/'artifacts'

MODEL_ID_COUGH = 'cough-copd-rf-calibrated'
MODEL_ID_TOLIFE = 'tolife-longitudinal-probe-v2'
N_MEL, N_MFCC = 26, 13

def _hz_to_mel(hz): return 2595.0*np.log10(1.0+hz/700.0)
def _mel_to_hz(mel): return 700.0*(10.0**(mel/2595.0)-1.0)

def utc_now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')

class ResearchError(RuntimeError):
    pass

def _dct_ii_ortho(x):
    """DCT-II along axis 1 with 'ortho' scaling (matches scipy.fftpack.dct(type=2, norm='ortho'))."""
    n = x.shape[1]
    k = np.arange(n)[None, :]
    i = np.arange(n)[:, None]
    basis = np.cos(np.pi*(2*k+1)*i/(2.0*n))
    out = x@basis.T
    out[:, 0] *= np.sqrt(1.0/(4.0*n))
    out[:, 1:] *= np.sqrt(1.0/(2.0*n))
    return out*2.0

class ResearchService:
    """Read-only registry + WAV cough inference + TOLIFE research views.

    Constructs with the platform Store; registry rows persist via additive migration
    006_research_models.sql (existing data untouched)."""

    def __init__(self, store):
        self.store = store
        self._cough_artifact = None
        self._cough_load_error = None
        self._register_models()

    # ---------- registry ----------
    def _upsert_registry(self, row):
        with self.store.connect() as c:
            existing = c.execute('SELECT version FROM model_registry WHERE model_id=?', (row['model_id'],)).fetchone()
            if existing:
                return  # registry rows immutable after creation; update via new version
            cols = list(row.keys())
            c.execute(
                f"INSERT INTO model_registry({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
                [row[k] for k in cols])

    def load_json(self, name):
        p = ART_DIR/name
        if not p.exists():
            raise ResearchError(f'artifact missing: {name}')
        return json.loads(p.read_text())

    def _register_models(self):
        try:
            cough_eval = self.load_json('cough_model_eval.json')
        except ResearchError:
            cough_eval = None
        try:
            horizons = self.load_json('tolife_horizon_results.json')
        except ResearchError:
            horizons = None
        now = utc_now()
        if cough_eval:
            self._upsert_registry({
                'model_id': MODEL_ID_COUGH, 'model_display_name': 'Cough Analysis',
                'model_kind': 'cough_research', 'version': cough_eval['version'],
                'dataset_source': cough_eval['dataset'],
                'task_type': 'binary file-level study-cough classification (COPD vs Healthy controls)',
                'feature_schema_json': json.dumps({'features': cough_eval['features'],
                                                   'feature_version': cough_eval['feature_version']}),
                'preprocessing_json': json.dumps({'mono': 'stereo-mean', 'frame_ms': 25, 'hop_ms': 10,
                                                  'window': 'hamming', 'nfft': 2048, 'n_mel': N_MEL, 'n_mfcc': N_MFCC}),
                'artifact_path': 'research/artifacts/cough_model.joblib' if (ART_DIR/'cough_model.joblib').exists() else None,
                'inference_method': 'joblib_calibrated_rf' if self._cough_ready() else 'none',
                'supported_outputs_json': json.dumps(['class_label', 'calibrated_probability', 'global_feature_importance']),
                'evaluation_json': json.dumps(cough_eval['test_metrics']),
                'limitations_json': json.dumps(cough_eval['limitations']),
                'provenance_evidence_class': 'REAL_DERIVED',
                'registered_at': now, 'updated_at': now})
        if horizons:
            self._upsert_registry({
                'model_id': MODEL_ID_TOLIFE, 'model_display_name': 'Longitudinal COPD Research',
                'model_kind': 'tolife_research', 'version': '2.0.0-leakage-corrected',
                'dataset_source': 'TOLIFE Clinical Study A (Zenodo 23263785 v2.0, CC-BY-4.0)',
                'task_type': 'feasibility probe: 24/48/72h exacerbation-onset risk, day-cadence',
                'feature_schema_json': json.dumps({'features': 'prior-day-only deltas vs trailing 7d personal baseline + missingness counts; model-estimated symptom classes excluded'}),
                'preprocessing_json': json.dumps({'frame': 'validity-filtered participant-day',
                                                  'horizons_evaluated': [24, 48, 72]}),
                'artifact_path': None,
                'inference_method': 'report_only',
                'supported_outputs_json': json.dumps(['horizon_metrics', 'event_audit', 'longitudinal_series']),
                'evaluation_json': json.dumps(horizons['results']),
                'limitations_json': json.dumps([
                    '72h prevalence 0.78%; 17 informative participants; CIs span both sides of chance',
                    'Feasibility probe only. Not a clinical risk predictor.',
                    'Corrected (v2) to remove study-model-estimated symptom predictor channels and same-day leakage']),
                'provenance_evidence_class': 'REAL_DERIVED',
                'registered_at': now, 'updated_at': now})
        self._seed_research_tables()

    def _seed_research_tables(self):
        """One-time, additive seeding of research dataset index tables from bundled artifacts."""
        if self.store.meta('research_seed_v7'):
            return
        now = utc_now()
        with self.store.connect() as c:
            try:
                idx = self.load_json('cough_dataset_index.json')
                for r in idx['recordings']:
                    c.execute('INSERT OR IGNORE INTO research_cough_recordings(filename,class_label,publisher_split,duration_s,samplerate_hz,channels,participant_id,evidence_class,provenance_json) VALUES (?,?,?,?,?,?,?,?,?)',
                              (r['filename'], r['class_label'], r['publisher_split'], None, None, None, None,
                               'REAL_OBSERVED', json.dumps({'dataset': idx['dataset'], 'source': r['filename']})))
            except ResearchError:
                pass
            try:
                parts = self.load_json('tolife_participants_research.json')
                for p in parts['participants']:
                    c.execute('INSERT OR IGNORE INTO research_tolife_participants(coded_participant_id,country,monitoring_days,first_day,last_day,evidence_class,provenance_json) VALUES (?,?,?,?,?,?,?)',
                              (p['participant_id'], p['country'], p['monitoring_days'], p['first_day'], p['last_day'],
                               'REAL_OBSERVED', json.dumps({'dataset': 'TOLIFE Zenodo 23263785 v2.0', 'kit': p['participant_id']})))
            except ResearchError:
                pass
            try:
                audit = self.load_json('event_register_audit.json')
                for e in audit['events']:
                    c.execute('INSERT INTO research_tolife_events(coded_participant_id,event_date,severity,in_observed_frame,valid_days_prior_7d,evidence_class,provenance_json) VALUES (?,?,?,?,?,?,?)',
                              (e['participant_id'], e['event_date'], None, int(e['in_observed_frame']),
                               int(e['valid_days_in_prior_7d']), 'REAL_OBSERVED',
                               json.dumps({'dataset': 'TOLIFE Zenodo 23263785 v2.0', 'register': 'exacerbations_all.csv'})))
            except ResearchError:
                pass
            try:
                horizons = self.load_json('tolife_horizon_results.json')
                c.execute('INSERT OR IGNORE INTO experiment_runs(id,model_id,started_at,finished_at,protocol_json,metrics_json,status,notes) VALUES (?,?,?,?,?,?,?,?)',
                          ('tolife-horizons-v2-20261108', MODEL_ID_TOLIFE, now, now,
                           json.dumps({'protocol': horizons['protocol']}), json.dumps(horizons['results']),
                           'complete', 'Leakage-corrected feasibility probe; weak/below-chance results reported honestly.'))
                for h, res in horizons['results'].items():
                    for metric in ('auroc', 'auprc', 'brier'):
                        c.execute('INSERT INTO research_evaluation_metrics(model_id,experiment_id,metric,horizon_hours,value,ci_low,ci_high,note,recorded_at) VALUES (?,?,?,?,?,?,?,?,?)',
                                  (MODEL_ID_TOLIFE, 'tolife-horizons-v2-20261108', metric, int(h), res.get(metric),
                                   (res.get(metric+'_ci') or [None, None])[0], (res.get(metric+'_ci') or [None, None])[1],
                                   'LOGO patient-level split; prelude to any future model tier decision', now))
            except ResearchError:
                pass
            try:
                ce = self.load_json('cough_model_eval.json')
                c.execute('INSERT OR IGNORE INTO experiment_runs(id,model_id,started_at,finished_at,protocol_json,metrics_json,status,notes) VALUES (?,?,?,?,?,?,?,?)',
                          ('cough-eval-v1-20261108', MODEL_ID_COUGH, now, now,
                           json.dumps({'protocol': ce['protocol']}), json.dumps(ce['test_metrics']),
                           'complete', 'Publisher train/test split; file-level evaluation; participant independence unverified.'))
                for metric, val in ce['test_metrics'].items():
                    if isinstance(val, (int, float)):
                        c.execute('INSERT INTO research_evaluation_metrics(model_id,experiment_id,metric,horizon_hours,value,ci_low,ci_high,note,recorded_at) VALUES (?,?,?,?,?,?,?,?,?)',
                                  (MODEL_ID_COUGH, 'cough-eval-v1-20261108', metric, None, float(val), None, None,
                                   'file-level test split', now))
            except ResearchError:
                pass
        self.store.set_meta('research_seed_v7', now)

    def registry(self):
        with self.store.connect() as c:
            rows = [dict(r) for r in c.execute('SELECT * FROM model_registry ORDER BY model_id')]
        for r in rows:
            for k in ('feature_schema_json', 'preprocessing_json', 'supported_outputs_json', 'evaluation_json', 'limitations_json'):
                r[k.replace('_json', '')] = json.loads(r.pop(k))
        return {'models': rows, 'count': len(rows)}

    # ---------- cough ----------
    def cough_info(self):
        d = self.load_json('cough_model_eval.json')
        d['inference_available'] = self._cough_ready()
        if not d['inference_available']:
            d['inference_note'] = self._cough_load_error or 'model artifact not bundled'
        return d

    def _cough_ready(self):
        if self._cough_artifact is not None:
            return True
        if self._cough_load_error:
            return False
        path = ART_DIR/'cough_model.joblib'
        if not path.exists():
            self._cough_load_error = 'cough_model.joblib not present'
            return False
        try:
            import joblib
            self._cough_artifact = joblib.load(path)
            return True
        except Exception as exc:
            self._cough_load_error = f'{type(exc).__name__}: {exc}'
            return False

    def _mel_filterbank(self, sr, nfft):
        mels = np.linspace(_hz_to_mel(0.0), _hz_to_mel(sr/2.0), N_MEL+2)
        freqs = _mel_to_hz(mels)
        bins = np.floor((nfft+1)*freqs/sr).astype(int)
        fb = np.zeros((N_MEL, nfft//2+1))
        for m in range(1, N_MEL+1):
            l, c, r = bins[m-1], bins[m], bins[m+1]
            fb[m-1, l:c] = (np.arange(l, c)-l+1)/(max(c-l, 1.0))
            fb[m-1, c:r] = (r-np.arange(c, r))/(max(r-c, 1.0))
        return fb

    def extract_features(self, wav_bytes):
        """MFCC/log-Mel/ZCR/RMS/centroid — features v1, matching the bundled research artifact."""
        try:
            import soundfile as sf
        except ImportError as exc:
            raise ResearchError('soundfile is not installed in this runtime; audio inference unavailable') from exc
        try:
            y, sr = sf.read(io.BytesIO(wav_bytes), always_2d=True)
        except Exception as exc:
            raise ResearchError(f'could not decode audio ({type(exc).__name__}); provide WAV/FLAC/OGG') from exc
        y = y.mean(axis=1).astype('float32')
        frame_len, hop = int(0.025*sr), int(0.010*sr)
        if len(y) < frame_len:
            raise ResearchError('audio too short (<25 ms of samples)')
        nframes = 1+(len(y)-frame_len)//hop
        starts = np.arange(nframes)*hop
        idx = np.clip(starts[:, None]+np.arange(frame_len)[None, :], 0, len(y)-1)
        frames = y[idx]*np.hamming(frame_len).astype('float32')
        frames = frames-np.concatenate([np.zeros((nframes, 1), 'float32'), 0.97*frames[:, :-1]], axis=1)
        nfft = 2048
        mag = np.abs(np.fft.rfft(frames, n=nfft))
        power = (1.0/nfft)*(mag*mag)
        fb = self._mel_filterbank(sr, nfft)
        mel = np.maximum(power@fb.T, 1e-10)
        logmel = np.log(mel)
        mfcc = _dct_ii_ortho(logmel)[:, :N_MFCC]
        zcr = ((frames[:, 1:]*frames[:, :-1] < 0).sum(axis=1)/frame_len).astype('float64')
        rms = np.sqrt((frames**2).mean(axis=1)+1e-12).astype('float64')
        centroid = (mag*(np.arange(mag.shape[1])*sr/nfft)).sum(axis=1)/(mag.sum(axis=1)+1e-12)
        feats = {}
        for k in range(N_MFCC):
            feats[f'mfcc{k+1}_mean'] = float(mfcc[:, k].mean()); feats[f'mfcc{k+1}_std'] = float(mfcc[:, k].std())
        for k in range(0, N_MEL, 2):
            feats[f'logmel{k+1}_mean'] = float(logmel[:, k].mean()); feats[f'logmel{k+1}_std'] = float(logmel[:, k].std())
        feats.update({'zcr_mean': float(zcr.mean()), 'zcr_std': float(zcr.std()),
                      'rms_mean': float(rms.mean()), 'rms_std': float(rms.std()),
                      'spectral_centroid_mean_hz': float(centroid.mean()),
                      'spectral_centroid_std_hz': float(centroid.std())})
        return feats, {'duration_s': round(float(len(y)/sr), 3), 'samplerate_hz': int(sr)}

    def cough_predict(self, wav_bytes, filename='uploaded.wav'):
        if not self._cough_ready():
            raise ResearchError(f'cough inference unavailable: {self._cough_load_error}')
        feats, meta = self.extract_features(wav_bytes)
        names = self._cough_artifact['features']
        X = np.array([[feats[n] for n in names]])
        proba = self._cough_artifact['model'].predict_proba(X)[0]
        pred = int(proba[1] >= 0.5)
        ih = hashlib.sha256(wav_bytes).hexdigest()[:16]
        out = {
            'model_id': MODEL_ID_COUGH, 'model_version': self._cough_artifact['meta']['version'],
            'class_label': 'COPD' if pred == 1 else 'Healthy',
            'p_copd': round(float(proba[1]), 4), 'p_healthy': round(float(proba[0]), 4),
            'threshold': 0.5, 'audio': meta, 'input_hash': ih,
            'evidence': 'the uploaded recording is REAL_OBSERVED input processed through a REAL_DERIVED research classifier',
            'disclaimer': ('Experimental cough-classification research model. NOT a diagnosis or screening result. '
                           'Participants in the published dataset were not independently validated; file-level counts include multiple recordings per participant.'),
        }
        with self.store.connect() as c:
            c.execute('INSERT INTO model_predictions(model_id,version,input_hash,input_summary_json,output_json,evidence_class,created_at) VALUES (?,?,?,?,?,?,?)',
                      (out['model_id'], out['model_version'], ih, json.dumps({'audio': meta, 'filename': filename}),
                       json.dumps({'class_label': out['class_label'], 'p_copd': out['p_copd']}), 'REAL_OBSERVED', utc_now()))
        return out

    def cough_attribution(self):
        return self.load_json('cough_model_eval.json').get('global_feature_importance', [])

    def cough_history(self, limit=20):
        with self.store.connect() as c:
            rows = [dict(r) for r in c.execute(
                'SELECT id,model_id,version,input_hash,input_summary_json,output_json,evidence_class,created_at FROM model_predictions WHERE model_id=? ORDER BY id DESC LIMIT ?',
                (MODEL_ID_COUGH, limit))]
        for r in rows:
            r['input_summary'] = json.loads(r.pop('input_summary_json'))
            r['output'] = json.loads(r.pop('output_json'))
        return {'predictions': rows, 'count': len(rows)}

    # ---------- tolife ----------
    def tolife_overview(self):
        audit = self.load_json('event_register_audit.json')
        horizons = self.load_json('tolife_horizon_results.json')
        return {
            'model_id': MODEL_ID_TOLIFE,
            'dataset': 'TOLIFE Clinical Study A (Zenodo 23263785 v2.0, CC-BY-4.0)',
            'event_audit': audit['summary'],
            'horizons': horizons['results'],
            'corrected_experiment_note': horizons.get('note', 'Leakage-corrected v2 protocol: prior-day-only features, strict in-frame events, model-estimated symptom classes excluded.'),
            'framing': 'Research view of an external clinical study. Participants are shown under coded identities only.',
        }

    def tolife_series(self):
        return self.load_json('tolife_research_series.json')

    def tolife_participants(self):
        return self.load_json('tolife_participants_research.json')
