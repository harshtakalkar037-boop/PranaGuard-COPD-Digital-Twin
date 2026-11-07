"""Vectorized ingestion validation before any baseline/feature calculation."""
import numpy as np
import pandas as pd
BOUNDS={'age':(18,100),'fev1_pct':(10,100),'spo2':(75,100),'heart_rate':(35,160),
        'resp_rate':(8,45),'symptom_score':(0,10),'steps':(0,1000),'sleep_hours':(0,14),
        'adherence':(0,1),'pm25':(0,1500),'pm10':(0,2000),'no2':(0,2000),'ozone':(0,1000),
        'temperature':(-30,60),'humidity':(0,100)}
MISSING_ALLOWED={'spo2','heart_rate','resp_rate','steps'}
def validate_longitudinal(df):
    required={'patient_id','hour','timestamp'}|set(BOUNDS)
    if not required.issubset(df.columns):raise ValueError('Missing required longitudinal columns')
    if df.duplicated(['patient_id','hour']).any():raise ValueError('Duplicate patient-hour observations')
    stamps=pd.to_datetime(df.timestamp,utc=True,errors='coerce')
    if stamps.isna().any():raise ValueError('Invalid timestamps')
    if (df.hour<0).any() or not np.equal(df.hour,np.floor(df.hour)).all():raise ValueError('Hour must be a nonnegative integer')
    delta=stamps-pd.to_timedelta(df.hour,unit='h')
    if delta.nunique()!=1:raise ValueError('Timestamp/hour alignment is inconsistent')
    for col,(lo,hi) in BOUNDS.items():
        values=df[col]
        if np.isinf(values).any() or ((values<lo)|(values>hi)).any():raise ValueError(f'{col} outside supported ingestion range')
        if col not in MISSING_ALLOWED and values.isna().any():raise ValueError(f'{col} may not be missing')
    baseline=df[df.hour<72]
    if baseline.groupby('patient_id').size().min()!=72:raise ValueError('Incomplete first-72h calibration observations')
    return {'rows':len(df),'patients':df.patient_id.nunique(),'validated':True}
