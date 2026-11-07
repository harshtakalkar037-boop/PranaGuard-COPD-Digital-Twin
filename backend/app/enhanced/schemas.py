"""Strict, bounded demo-only contracts. No arbitrary source, ID, URL or recipient overrides."""
from datetime import datetime, timezone, timedelta
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from backend.app.enhanced.settings import CITIES, METRICS

class Strict(BaseModel):model_config=ConfigDict(extra='forbid',allow_inf_nan=False,str_strip_whitespace=True)

class Registration(Strict):
    request_id:str=Field(min_length=8,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    fictional_identity_confirmed:Literal[True]
    demo_alias:str=Field(min_length=2,max_length=50,pattern=r'^[A-Za-z][A-Za-z0-9 -]*$')
    age:int=Field(ge=18,le=100)
    sex:Literal['Female','Male','Other','Not specified']='Not specified'
    city:str
    copd_history:str=Field(default='Fictional COPD history, not a clinical record.',max_length=1000)
    diagnosis_info:str=Field(default='Demo diagnosis information only.',max_length=1000)
    medications:str=Field(default='No demo medication plan recorded.',max_length=1000)
    clinician_alias:str=Field(default='Atlas',min_length=2,max_length=50,pattern=r'^[A-Za-z][A-Za-z0-9 -]*$')
    baseline_spo2:float|None=Field(default=None,ge=50,le=100)
    baseline_heart_rate:float|None=Field(default=None,ge=25,le=240)
    baseline_resp_rate:float|None=Field(default=None,ge=5,le=60)
    fev1_pct:float|None=Field(default=None,ge=10,le=120)
    bmi:float|None=Field(default=None,ge=12,le=50)
    smoking_pack_years:float|None=Field(default=None,ge=0,le=150)
    prior_exacerbations:int|None=Field(default=None,ge=0,le=15)
    source_type:Literal['manual_demo']='manual_demo'
    @field_validator('city')
    @classmethod
    def city_allowed(cls,v):
        if v not in CITIES:raise ValueError('Select a registered demo city.')
        return v

class AssociateDevice(Strict):
    patient_id:str=Field(min_length=1,max_length=100)
    kind:Literal['pulse_oximeter','smartwatch','fitness_band','portable_spirometer']
    label:str=Field(default='',max_length=60)
    interval_seconds:int=Field(default=5,ge=2,le=300)
class SimulationControl(Strict):interval_seconds:int=Field(default=5,ge=2,le=300)
class Reading(Strict):
    metric:str
    value:float
    unit:str=Field(max_length=30)
    @model_validator(mode='after')
    def bounds(self):
        spec=METRICS.get(self.metric)
        if not spec:raise ValueError('Unsupported metric.')
        if self.unit!=spec['unit']:raise ValueError(f"Expected unit {spec['unit']} for {self.metric}.")
        if not spec['minimum']<=self.value<=spec['maximum']:raise ValueError('Measurement outside demo plausibility bounds.')
        if self.metric=='steps' and not self.value.is_integer():raise ValueError('Steps must be a whole count.')
        return self
class Ingestion(Strict):
    patient_id:str=Field(min_length=1,max_length=100)
    device_id:str=Field(min_length=1,max_length=100)
    event_id:str=Field(min_length=1,max_length=120,pattern=r'^[A-Za-z0-9_:\-]+$')
    observed_at:datetime
    source_type:Literal['simulated_device']='simulated_device'
    readings:list[Reading]=Field(min_length=1,max_length=6)
    @field_validator('observed_at')
    @classmethod
    def timestamp(cls,v):
        if v.tzinfo is None or v.utcoffset() is None:raise ValueError('An explicit timezone is required.')
        v=v.astimezone(timezone.utc)
        if v>datetime.now(timezone.utc)+timedelta(minutes=2):raise ValueError('Future observations are not accepted.')
        return v
    @model_validator(mode='after')
    def unique_metrics(self):
        if len({r.metric for r in self.readings})!=len(self.readings):raise ValueError('Duplicate metrics in one event.')
        return self
class Observation(Strict):
    fictional_data_confirmed:Literal[True]
    symptom_score:int=Field(ge=0,le=10)
    adherence:float=Field(ge=0,le=1)
    note:str=Field(default='',max_length=1000)
class NotificationUpdate(Strict):
    status:Literal['active','acknowledged','under_review','resolved','closed']|None=None
    read:bool|None=None
    note:str=Field(default='',max_length=2000)
    @model_validator(mode='after')
    def not_empty(self):
        if self.status is None and self.read is None:raise ValueError('Specify a read state or review status.')
        return self
class Review(Strict):
    kind:Literal['clinical_review','contact','adherence_review','exposure_review','other']='clinical_review'
    note:str=Field(min_length=3,max_length=2000)
class EmptyBody(Strict):pass
