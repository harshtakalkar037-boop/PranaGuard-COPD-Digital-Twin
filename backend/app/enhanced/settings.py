"""Backend-only configuration. Never expose credentials in API status, URLs or logs."""
import os
from dataclasses import dataclass,field
from datetime import datetime, timezone

CITIES = {
    'Pune': {'latitude':18.5204,'longitude':73.8567,'state':'Maharashtra'},
    'Mumbai': {'latitude':19.0760,'longitude':72.8777,'state':'Maharashtra'},
    'Delhi': {'latitude':28.6139,'longitude':77.2090,'state':'Delhi'},
    'Bengaluru': {'latitude':12.9716,'longitude':77.5946,'state':'Karnataka'},
}
METRICS = {
    'spo2': {'label':'SpO₂','unit':'%','minimum':50,'maximum':100},
    'heart_rate': {'label':'Heart rate','unit':'bpm','minimum':25,'maximum':240},
    'resp_rate': {'label':'Respiratory rate','unit':'breaths/min','minimum':5,'maximum':60},
    'steps': {'label':'Steps in sample interval','unit':'steps','minimum':0,'maximum':1000},
    'fev1': {'label':'FEV₁','unit':'L','minimum':0.1,'maximum':8},
    'fvc': {'label':'FVC','unit':'L','minimum':0.1,'maximum':10},
}
DEVICE_CATALOG = [
    {'kind':'pulse_oximeter','label':'Generic pulse oximeter','metrics':['spo2','heart_rate']},
    {'kind':'smartwatch','label':'Generic smartwatch','metrics':['heart_rate','resp_rate','steps']},
    {'kind':'fitness_band','label':'Generic fitness band','metrics':['heart_rate','steps']},
    {'kind':'portable_spirometer','label':'Generic portable spirometer','metrics':['fev1','fvc']},
]
def utcnow():return datetime.now(timezone.utc)
def stamp():return utcnow().isoformat()
def parse_stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
def env_bool(key,default=False):return os.getenv(key,str(default)).lower() in ('true','1','yes')

@dataclass
class Settings:
    environment_enabled:bool=False
    cache_ttl_seconds:int=900
    retry_seconds:int=300
    provider_timeout_seconds:float=8
    provider_key:str=field(default='',repr=False)
    device_secret:str=field(default='',repr=False)
    email_mode:str='disabled'
    smtp_host:str=''
    smtp_port:int=587
    smtp_user:str=field(default='',repr=False)
    smtp_password:str=field(default='',repr=False)
    smtp_from:str=field(default='',repr=False)
    demo_recipient:str=field(default='',repr=False)
    smtp_starttls:bool=True
    smtp_ssl:bool=False
    allow_insecure_local:bool=False

    @classmethod
    def from_env(cls):
        return cls(
            environment_enabled=env_bool('PRANAGUARD_LIVE_ENV_ENABLED'),
            cache_ttl_seconds=max(300,int(os.getenv('PRANAGUARD_ENV_TTL_SECONDS','900'))),
            retry_seconds=max(300,int(os.getenv('PRANAGUARD_ENV_RETRY_SECONDS','300'))),
            provider_timeout_seconds=min(20,max(1,float(os.getenv('PRANAGUARD_ENV_TIMEOUT_SECONDS','8')))),
            provider_key=os.getenv('OPEN_METEO_API_KEY',''),device_secret=os.getenv('PRANAGUARD_DEVICE_SECRET',''),
            email_mode=os.getenv('PRANAGUARD_EMAIL_MODE','disabled'),
            smtp_host=os.getenv('PRANAGUARD_SMTP_HOST',''),smtp_port=int(os.getenv('PRANAGUARD_SMTP_PORT','587')),
            smtp_user=os.getenv('PRANAGUARD_SMTP_USER',''),smtp_password=os.getenv('PRANAGUARD_SMTP_PASSWORD',''),
            smtp_from=os.getenv('PRANAGUARD_SMTP_FROM',''),demo_recipient=os.getenv('PRANAGUARD_DEMO_RECIPIENT',''),
            smtp_starttls=env_bool('PRANAGUARD_SMTP_STARTTLS',True),smtp_ssl=env_bool('PRANAGUARD_SMTP_SSL'),
            allow_insecure_local=env_bool('PRANAGUARD_SMTP_ALLOW_INSECURE_LOCAL'),
        )
