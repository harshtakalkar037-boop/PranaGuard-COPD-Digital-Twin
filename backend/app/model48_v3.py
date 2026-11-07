"""Larger-cohort causal48h model; original features/models remain immutable."""
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from backend.app.features import FEATURES
from backend.app.model48 import research_features,Research48Model,margin,CORE
VERSION='pg48-v3-multiseed'
SIGNALS={'spo2':-1,'heart_rate':1,'resp_rate':1,'symptom_score':1,'sleep_hours':-1}
ZCOLS=[f'v3_{key}_z{window}' for key in SIGNALS for window in (6,24,72,120)]
SLOPES=[f'v3_{key}_slope{lag}' for key in SIGNALS for lag in (24,72)]
RECOVERY=['v3_body_index6','v3_body_index24','v3_peak72_minus_now','v3_peak144_minus_now','v3_now_minus_min72','v3_body_range72']
BODY=['fev1_pct','prior_exacerbations','adherence_mean24','pg48_adherence_mean72','pg48_steps_ratio24']+ZCOLS+SLOPES+RECOVERY
CONTEXT=BODY+['pm25_mean24','pg48_pm25_mean72','pm25_change6','temperature','humidity','no2','ozone']
ALL=list(dict.fromkeys(list(FEATURES)+list(CORE)+CONTEXT))
CANDIDATES=[
 {'name':'tree_original35','kind':'tree','features':list(FEATURES),'trees':300,'leaves':15,'depth':5,'minimum':160,'l2':10},
 {'name':'linear_core8','kind':'linear','features':list(CORE),'C':.3},
 {'name':'tree_body15','kind':'tree','features':BODY,'trees':350,'leaves':15,'depth':5,'minimum':180,'l2':15},
 {'name':'tree_context15','kind':'tree','features':CONTEXT,'trees':350,'leaves':15,'depth':5,'minimum':180,'l2':15},
 {'name':'tree_context31','kind':'tree','features':CONTEXT,'trees':450,'leaves':31,'depth':6,'minimum':120,'l2':20},
 {'name':'tree_body7','kind':'tree','features':BODY,'trees':500,'leaves':7,'depth':3,'minimum':250,'l2':25}]

def features_v3(raw):
    # Baselines are each patient's first72h. No labels or event history is read.
    df=research_features(raw);groups=df.groupby('patient_id',sort=False);zs=[]
    for key,sign in SIGNALS.items():
        base=df[df.hour<72].groupby('patient_id')[key].agg(['median','std']);center=df.patient_id.map(base['median']);scale=df.patient_id.map(base['std'].clip(lower=.05))
        for window in (6,24,72,120):df[f'v3_{key}_z{window}']=sign*(groups[key].transform(lambda s:s.rolling(window,min_periods=1).mean())-center)/scale
        z=f'v3_{key}_z6';zs.append(z)
        for lag in (24,72):df[f'v3_{key}_slope{lag}']=df[z]-df.groupby('patient_id',sort=False)[z].shift(lag)
    # Descriptive multi-signal standardized deviation, NOT a handcrafted risk score.
    df['v3_body_index6']=df[zs].mean(axis=1);df['v3_body_index24']=df[[f'v3_{key}_z24' for key in SIGNALS]].mean(axis=1)
    g=df.groupby('patient_id',sort=False)['v3_body_index6'];peak72=g.transform(lambda s:s.rolling(72,min_periods=1).max());peak144=g.transform(lambda s:s.rolling(144,min_periods=1).max());low72=g.transform(lambda s:s.rolling(72,min_periods=1).min())
    df['v3_peak72_minus_now']=peak72-df.v3_body_index6;df['v3_peak144_minus_now']=peak144-df.v3_body_index6;df['v3_now_minus_min72']=df.v3_body_index6-low72;df['v3_body_range72']=peak72-low72
    return df

def make_pipeline(spec):
    if spec['kind']=='linear':return Pipeline([('imputer',SimpleImputer(strategy='median')),('scale',StandardScaler()),('model',LogisticRegression(C=spec['C'],max_iter=1500,random_state=31000))])
    from lightgbm import LGBMClassifier
    model=LGBMClassifier(n_estimators=spec['trees'],learning_rate=.04,num_leaves=spec['leaves'],max_depth=spec['depth'],min_child_samples=spec['minimum'],reg_lambda=spec['l2'],verbosity=-1,random_state=31000,n_jobs=2,deterministic=True,force_col_wise=True,colsample_bytree=1.,subsample=1.)
    return Pipeline([('imputer',SimpleImputer(strategy='median')),('model',model)])

class Model48V3(Research48Model):
    def raw_margin(self,frame):return margin(self.pipeline,frame[self.features].astype(np.float32),self.features)
    def explain(self,frame):return super().explain(frame[self.features].astype(np.float32))
