"""Additive read-only v3 inference. Never rewrites legacy states/alerts/scenarios."""
import hashlib,json,re
from functools import lru_cache
from typing import Literal
import joblib,pandas as pd
from fastapi import APIRouter,HTTPException,Query,Request
from pydantic import BaseModel,ConfigDict,Field
from backend.app.config import ROOT
from backend.app.engine import now
from backend.app.model48_v3 import VERSION,features_v3

class Driver(BaseModel):
    feature:str;label:str;value:float|None;contribution:float;imputed:bool
class ExplanationV3(BaseModel):
    method:str;units:str;base_value:float;raw_margin:float;calibrated_margin:float;probability:float;drivers:list[Driver];model_version:str;caveat:str
class PredictionV3(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    patient_id:str;state_version:int;hour:int;timestamp:str;computed_at:str
    model_version:Literal['pg48-v3-multiseed'];original_model_version:str
    synthetic:Literal[True]=True;input_source:Literal['original_synthetic_replay']='original_synthetic_replay'
    probability:float|None=Field(ge=0,le=1);original_risk48:float=Field(ge=0,le=1)
    prediction_supported:bool;demo_cutoff:float;above_demo_cutoff:bool|None
    persisted:Literal[False]=False;explanation:ExplanationV3|None;warnings:list[str]

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def evidence():
    try:
        folder=ROOT/'artifacts/model48_v3';frozen=json.loads((folder/'FROZEN.json').read_text());audit=json.loads((folder/'AUDIT.json').read_text())
        if digest(folder/'model.joblib')!=frozen['model_sha256'] or audit['model_sha256']!=frozen['model_sha256'] or digest(ROOT/'docs/model-v3/PROTOCOL.json')!=frozen['protocol_sha256'] or audit['protocol_sha256']!=frozen['protocol_sha256']:raise ValueError('Artifact fingerprint mismatch')
        for name,sha in frozen['source_files_sha256'].items():
            if digest(ROOT/name)!=sha:raise ValueError('Fitted source fingerprint mismatch')
        return frozen,audit
    except (OSError,ValueError,KeyError,TypeError):raise HTTPException(503,'v3 evidence is unavailable or inconsistent. Legacy stored predictions are unchanged.') from None

def report_v3():
    frozen,audit=evidence()
    return {'model_version':VERSION,'experimental_available':audit['experimental_available'],'legacy_endpoint_model':'pg-synthetic-v1','legacy_states_rewritten':False,'study':audit,'candidates':frozen['candidates'],'development':{'partitions':{k:{'patients':v['patients'],'rows':v['rows'],'positive_rows':v['positive_rows']} for k,v in frozen['partitions'].items()},'calibration':frozen['calibration'],'operating_point':frozen['operating_point']},'notice':'Experimental synthetic48h display, not a clinical prediction.24h/72h, stored histories, scenarios and alerts remain original v1. Prior failed v2 study is retained separately.'}

NAMES={'fev1_pct':'FEV₁ percent predicted','prior_exacerbations':'Prior synthetic exacerbations','adherence_mean24':'Adherence · past24h','pg48_adherence_mean72':'Adherence · past72h','pg48_steps_ratio24':'Activity vs72h personal baseline','pm25_mean24':'Historical ambient PM2.5 · past24h','pg48_pm25_mean72':'Historical ambient PM2.5 · past72h','pm25_change6':'Historical ambient PM2.5 change ·6h','temperature':'Historical ambient temperature','humidity':'Historical ambient humidity','no2':'Historical ambient NO₂','ozone':'Historical ambient ozone','v3_body_index6':'Mean standardized body deviation ·6h','v3_body_index24':'Mean standardized body deviation ·24h','v3_peak72_minus_now':'72h peak minus current body deviation','v3_peak144_minus_now':'144h peak minus current body deviation','v3_now_minus_min72':'Current minus72h minimum body deviation','v3_body_range72':'Range of body deviations ·72h'}
SIGNAL_NAMES={'spo2':'SpO₂','heart_rate':'Heart rate','resp_rate':'Respiratory rate','symptom_score':'Symptoms','sleep_hours':'Sleep'}
def feature_label(feature):
    if feature in NAMES:return NAMES[feature]
    match=re.fullmatch(r'v3_(.+)_(z|slope)(\d+)',feature)
    if match:
        key,kind,window=match.groups();signal=SIGNAL_NAMES.get(key,key)
        return f'{signal} · past{window}h deviation (baseline SD)' if kind=='z' else f'{signal}6h deviation · change over{window}h'
    return feature.replace('_',' ')

class Service48V3:
    def __init__(self,engine):
        self.engine=engine;self.frozen,self.audit=evidence()
        if not self.audit['experimental_available'] or not all(self.audit['gate_checks'].values()):raise HTTPException(503,'v3 failed its gates; only the original model may be used.')
        self.model=joblib.load(ROOT/'artifacts/model48_v3/model.joblib')
    @lru_cache(maxsize=16)
    def frame(self,pid,hour):
        # Physically truncate before feature extraction as well as using causal windows.
        raw=self.engine.raw[(self.engine.raw.patient_id==pid)&(self.engine.raw.hour<=hour)]
        frame=features_v3(raw);return frame[frame.hour==hour].copy()
    def predict(self,pid,version=None):
        with self.engine.lock:
            if pid not in self.engine.profiles:raise HTTPException(404,'v3 supports the original fictional replay cohort only; no manual/device/new-registration inference.')
            state=self.engine.patient(pid,version);hour=state['hour'];supported=bool(state['prediction_supported'] and hour>=72)
            probability=None;explanation=None;cutoff=self.frozen['operating_point']['threshold']
            if supported:
                row=self.frame(pid,hour);probability=float(self.model.predict(row)[0]);explanation=self.model.explain(row)
                explanation['drivers']=[{**d,'label':feature_label(d['feature']),'imputed':bool(pd.isna(row.iloc[0][d['feature']]))} for d in explanation['drivers']]
                explanation['drivers'].sort(key=lambda d:abs(d['contribution']),reverse=True)
            return {'patient_id':pid,'state_version':state['version'],'hour':hour,'timestamp':state['timestamp'],'computed_at':now(),'model_version':VERSION,'original_model_version':state['model_version'],'synthetic':True,'input_source':'original_synthetic_replay','probability':probability,'original_risk48':state['risks']['48'],'prediction_supported':supported,'demo_cutoff':cutoff,'above_demo_cutoff':None if probability is None else probability>=cutoff,'persisted':False,'explanation':explanation,'warnings':(['No supported v3 forecast: current episode, missing follow-up or baseline requirement not met.'] if not supported else [])+['Experimental synthetic model; low sensitivity. Not a diagnosis, emergency alert or clinical threshold.','Recomputed for this saved replay state. Old history,24h/72h, alerts and scenarios remain v1; no v3 history was backfilled.','Only original synthetic physiology and historical ambient caches are inputs; optional live context/manual/device records are excluded.']}

def make_v3_router():
    router=APIRouter(prefix='/api/model48/v3',tags=['Experimental synthetic48h v3'])
    @router.get('/study')
    def study():return report_v3()
    @router.get('/patients/{pid}',response_model=PredictionV3)
    def prediction(pid:str,request:Request,version:int|None=Query(default=None,ge=1)):
        engine=request.app.state.engine
        _,current_audit=evidence()  # Fail closed even after a service was cached.
        if not current_audit['experimental_available'] or not all(current_audit['gate_checks'].values()):raise HTTPException(503,'v3 gates unavailable or not passed; legacy predictions remain unchanged.')
        with engine.lock:
            if not hasattr(request.app.state,'model48_v3'):request.app.state.model48_v3=Service48V3(engine)
            service=request.app.state.model48_v3
        return service.predict(pid,version)
    return router
