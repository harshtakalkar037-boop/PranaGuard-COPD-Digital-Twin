"""Research-model API routes (v7) — additive; never clashes with existing twin/clinical routes."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from .service import ResearchError, ResearchService

router = APIRouter(prefix='/api/models', tags=['research-models'])

_service = None

def bind_service(store):
    """Instantiate the ResearchService against the platform store (called once from main)."""
    global _service
    _service = ResearchService(store)
    return _service

def get_service() -> ResearchService:
    if _service is None:
        raise HTTPException(503, detail='research service not initialised')
    return _service

@router.get('/registry')
def model_registry(svc: ResearchService = Depends(get_service)):
    return svc.registry()

# ---- Model B: cough ----
@router.get('/cough/info')
def cough_info(svc: ResearchService = Depends(get_service)):
    try:
        return svc.cough_info()
    except ResearchError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.post('/cough/infer')
async def cough_infer(file: UploadFile = File(...), svc: ResearchService = Depends(get_service)):
    data = await file.read()
    if not data:
        raise HTTPException(400, 'empty file')
    if len(data) > 40*1024*1024:
        raise HTTPException(413, 'file too large (max 40 MB)')
    try:
        return svc.cough_predict(data, filename=file.filename or 'uploaded.wav')
    except ResearchError as exc:
        raise HTTPException(503, str(exc)) from exc

@router.get('/cough/attribution')
def cough_attribution(svc: ResearchService = Depends(get_service)):
    try:
        return {'model_id': 'cough-copd-rf-calibrated', 'global_feature_importance': svc.cough_attribution(),
                'note': 'Dataset-level feature attribution (LightGBM split importance), not a causal effect.'}
    except ResearchError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.get('/cough/history')
def cough_history(limit: int = 20, svc: ResearchService = Depends(get_service)):
    return svc.cough_history(limit=max(1, min(int(limit), 100)))

# ---- Model C: TOLIFE ----
@router.get('/tolife/overview')
def tolife_overview(svc: ResearchService = Depends(get_service)):
    try:
        return svc.tolife_overview()
    except ResearchError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.get('/tolife/series')
def tolife_series(svc: ResearchService = Depends(get_service)):
    try:
        return svc.tolife_series()
    except ResearchError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.get('/tolife/participants')
def tolife_participants(svc: ResearchService = Depends(get_service)):
    try:
        return svc.tolife_participants()
    except ResearchError as exc:
        raise HTTPException(404, str(exc)) from exc
