"""Causal features shared by training, replay and scenario inference; no label inputs."""
import numpy as np
import pandas as pd
STATIC = ['age','fev1_pct','prior_exacerbations','smoking_pack_years','bmi']
BODY = ['spo2','heart_rate','resp_rate','symptom_score','adherence','steps','sleep_hours',
        'spo2_mean6','hr_mean6','rr_mean6','symptom_mean6','spo2_change6','hr_change6','adherence_mean24']
ENV = ['pm25','pm10','no2','ozone','temperature','humidity','pm25_mean24','pm25_change6']
PERSONAL = ['spo2_delta','hr_delta','rr_delta','symptom_delta','steps_ratio','spo2_baseline','hr_baseline','rr_baseline']
FEATURES = STATIC + BODY + ENV + PERSONAL
GROUPS = {'static_only':STATIC, 'body_stream':STATIC+BODY, 'full_environment':STATIC+BODY+ENV, 'personalized':FEATURES}
MEASURES = ['spo2','heart_rate','resp_rate','symptom_score','steps','sleep_hours','adherence','pm25','pm10','no2','ozone','temperature','humidity']
BASE_MAP={'spo2':'spo2_baseline','heart_rate':'hr_baseline','resp_rate':'rr_baseline','symptom_score':'symptom_baseline','steps':'steps_baseline'}

def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Input must contain one patient sorted by hour, or a sorted multi-patient frame.
    Calibration is first 72 hours only; these rows are never eligible for fitting/evaluation.
    No backward fill, centered rolling windows, future exposure or label-derived values.
    """
    df=frame.sort_values(['patient_id','hour']).copy()
    groups=df.groupby('patient_id',sort=False)
    for source,target in BASE_MAP.items():
        bases=df[df.hour<72].groupby('patient_id')[source].median()
        df[target]=df.patient_id.map(bases)
    for source,target in [('spo2','spo2_mean6'),('heart_rate','hr_mean6'),('resp_rate','rr_mean6'),('symptom_score','symptom_mean6')]:
        df[target]=groups[source].transform(lambda x:x.rolling(6,min_periods=1).mean())
    for source,target in [('spo2','spo2_change6'),('heart_rate','hr_change6'),('pm25','pm25_change6')]:
        df[target]=df[source]-groups[source].shift(6)
    df['pm25_mean24']=groups.pm25.transform(lambda x:x.rolling(24,min_periods=1).mean())
    df['adherence_mean24']=groups.adherence.transform(lambda x:x.rolling(24,min_periods=1).mean())
    df['spo2_delta']=df.spo2-df.spo2_baseline
    df['hr_delta']=df.heart_rate-df.hr_baseline
    df['rr_delta']=df.resp_rate-df.rr_baseline
    df['symptom_delta']=df.symptom_score-df.symptom_baseline
    df['steps_ratio']=df.steps/(df.steps_baseline.clip(lower=10))
    return df


def risk_category(p: float) -> str:
    return 'high' if p>=0.35 else 'elevated' if p>=0.15 else 'low'

DISPLAY = {'spo2':'Oxygen saturation','heart_rate':'Heart rate','resp_rate':'Respiratory rate',
           'symptom_score':'Symptom burden','pm25':'Ambient PM2.5','pm25_mean24':'24h PM2.5 exposure',
           'adherence':'Adherence assumption','adherence_mean24':'24h adherence',
           'spo2_delta':'SpO₂ vs personal baseline','hr_delta':'Heart rate vs baseline','rr_delta':'Respiratory rate vs baseline',
           'symptom_delta':'Symptoms vs baseline','steps_ratio':'Activity vs baseline'}
