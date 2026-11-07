"""Read-only completed research evidence. Never promotes or loads a candidate for care."""
import hashlib,json
from fastapi import HTTPException
from backend.app.config import ROOT

def study_report():
    folder=ROOT/'artifacts/model48_v2'
    try:
        study=json.loads((folder/'AUDIT_EVALUATION.json').read_text());frozen=json.loads((folder/'FROZEN_DEVELOPMENT.json').read_text())
        if hashlib.sha256((folder/'model.joblib').read_bytes()).hexdigest()!=frozen['model_sha256'] or study['frozen_model_sha256']!=frozen['model_sha256']:raise ValueError('Study fingerprint mismatch.')
        return {'decision':'retain_original','candidate_active':False,'active_model_version':'pg-synthetic-v1','reason':'The selected48h candidate failed the predeclared fresh synthetic audit. No live model, cutoff, stored risk, scenario or alert was replaced.','study':study,'candidates':frozen['candidates']}
    except (OSError,ValueError,KeyError,TypeError):raise HTTPException(503,'Completed48h study evidence is unavailable or inconsistent. Original model remains unchanged.') from None
