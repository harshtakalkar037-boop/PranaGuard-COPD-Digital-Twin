"""48h research software checks; passing these does NOT mean the candidate is better."""
import hashlib,json
from pathlib import Path
import joblib,numpy as np,pandas as pd,pytest
from scipy.special import expit
from backend.app.config import ROOT
from backend.app.features import FEATURES,add_features
from backend.app.model48 import CORE,TREND,CANDIDATES,research_features,calibrate_positive
from scripts.train_model48 import choose_threshold

@pytest.fixture(scope='module')
def raw():
    return pd.read_csv(ROOT/'data/synthetic_longitudinal.csv.gz',nrows=1440)
@pytest.fixture(scope='module')
def model():return joblib.load(ROOT/'artifacts/model48_v2/model.joblib')

def test_research_features_are_past_only(raw):
    full=research_features(raw);past=research_features(raw[raw.hour<=200]);cols=list(set(TREND+FEATURES))
    np.testing.assert_allclose(full.loc[full.hour==200,cols],past.loc[past.hour==200,cols],equal_nan=True)

def test_future_mutations_do_not_change_prediction(raw,model):
    original=research_features(raw);changed=raw.copy();changed.loc[changed.hour>200,['spo2','heart_rate','resp_rate','symptom_score','sleep_hours','steps','pm25','adherence']]=999
    altered=research_features(changed)
    np.testing.assert_allclose(model.predict(original[original.hour==200]),model.predict(altered[altered.hour==200]))

def test_labels_onsets_and_eligibility_are_not_predictors(raw,model):
    a=research_features(raw);changed=raw.copy()
    for key in ['label_24','label_48','label_72','event_onset','active_episode','eligible']:changed[key]=1
    b=research_features(changed);np.testing.assert_allclose(a[model.features],b[model.features],equal_nan=True)
    assert not set(model.features)&{'patient_id','hour','timestamp','event_onset','active_episode','eligible','label_24','label_48','label_72'}

def test_original_feature_values_unchanged(raw):
    pd.testing.assert_frame_equal(add_features(raw)[FEATURES],research_features(raw)[FEATURES])

def test_first72_baseline_and_trailing_means(raw):
    df=research_features(raw);row=df[df.hour==200].iloc[0]
    expected=raw[(raw.hour>=177)&(raw.hour<=200)].spo2.mean()-raw[raw.hour<72].spo2.median()
    assert row.pg48_spo2_delta24==pytest.approx(expected)

def test_positive_calibrator_cannot_invert_ranking():
    x=np.linspace(-3,3,80);y=(x<0).astype(int);cal=calibrate_positive(x,y)
    assert cal['slope']>=0
    assert np.all(np.diff(expit(cal['slope']*x+cal['intercept']))>=0)

def test_calibration_requires_two_classes():
    with pytest.raises(ValueError):calibrate_positive([1,2,3],[0,0,0])

def test_candidate_probabilities_finite_and_exact_explanation(raw,model):
    frame=research_features(raw);frame=frame[frame.hour==200];explanation=model.explain(frame)
    assert 0<=model.predict(frame)[0]<=1 and np.isfinite(model.predict(frame)[0])
    assert explanation['base_value']+sum(d['contribution'] for d in explanation['drivers'])==pytest.approx(explanation['calibrated_margin'])
    assert expit(explanation['calibrated_margin'])==pytest.approx(model.predict(frame)[0])
    assert 'not probability' in explanation['units'] and 'Exact logistic' in explanation['method']

def test_threshold_constraint_and_no_positive_degeneracy():
    y=np.array([0,0,0,0,1,1]);p=np.array([.01,.02,.03,.04,.8,.9]);r=choose_threshold(y,p)
    assert r['false_positive_rate']<=.10 and r['recall']==1 and not r['validated_clinical_cutoff']
    assert choose_threshold([0,0],[.1,.2]) is None

def test_predeclared_fold_separation_and_candidate_selection():
    protocol=json.loads((ROOT/'docs/model-upgrade/PROTOCOL.json').read_text());frozen=json.loads((ROOT/'artifacts/model48_v2/FROZEN_DEVELOPMENT.json').read_text())
    for fold in protocol['selection_folds']:
        assert fold['train_patient_numbers'][1]<fold['validation_patient_numbers'][0]<=72
        assert fold['train_hours'][1]+72<fold['validation_hours'][0] and fold['validation_hours'][1]<=747
    assert [c['name'] for c in CANDIDATES]==protocol['candidates']
    assert max(frozen['candidates'],key=lambda r:r['mean_validation_auprc'])['candidate']==frozen['selected_candidate']
    assert frozen['original_test_used_for_selection'] is False
    assert frozen['protocol_sha256']==hashlib.sha256((ROOT/'docs/model-upgrade/PROTOCOL.json').read_bytes()).hexdigest()

def test_audit_was_frozen_and_failure_not_hidden():
    folder=ROOT/'artifacts/model48_v2';frozen=json.loads((folder/'FROZEN_DEVELOPMENT.json').read_text());report=json.loads((folder/'AUDIT_EVALUATION.json').read_text());manifest=json.loads((ROOT/'data/model48_audit/generation_manifest.json').read_text())
    sha=hashlib.sha256((folder/'model.joblib').read_bytes()).hexdigest()
    assert sha==frozen['model_sha256']==report['frozen_model_sha256']==manifest['frozen_model_before_generation']
    assert not report['experimental_available'] and report['status']=='GATE_NOT_PASSED'
    assert report['fresh_audit']['revised']['auprc']<report['fresh_audit']['original']['auprc']
    assert report['fresh_audit']['revised']['brier']>report['fresh_audit']['original']['brier']
    assert report['fresh_audit']['uncertainty']['valid_resamples']==300

def test_research_api_is_read_only_and_retains_old_outputs(client):
    before=client.get('/api/patients/PG-0071').json();study=client.get('/api/model48/study')
    assert study.status_code==200 and not study.json()['candidate_active']
    assert study.json()['decision']=='retain_original' and len(study.json()['candidates'])==8
    assert client.get('/api/patients/PG-0071').json()==before
    assert client.post('/api/model48/study',json={'activate':True}).status_code==405
    assert client.post('/api/model48/activate',json={}).status_code==404

def test_missing_study_never_breaks_original_model(client,tmp_path,monkeypatch):
    import backend.app.model48_study as study
    monkeypatch.setattr(study,'ROOT',tmp_path)
    assert client.get('/api/model48/study').status_code==503
    assert client.get('/api/health').status_code==200
    assert len(client.get('/api/patients/PG-0071').json()['risks'])==3

def test_original_scientific_design_and_generator_files_protected():
    baseline=json.loads((ROOT/'docs/enhanced/BASELINE_MANIFEST.json').read_text())
    for name,sha in baseline['protected_files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    frozen=json.loads((ROOT/'artifacts/model48_v2/FROZEN_DEVELOPMENT.json').read_text())
    assert hashlib.sha256((ROOT/'scripts/generate_data.py').read_bytes()).hexdigest()==frozen['original_generator_sha256']
