"""Versioned experimental48h pipeline. Original features/models are not modified."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from backend.app.features import add_features,FEATURES

VERSION='pg48-research-v2-20261105'
CORE=['fev1_pct','pg48_spo2_delta24','pg48_hr_delta24','pg48_rr_delta24','pg48_symptom_delta24','pg48_sleep_delta24','adherence_mean24','pm25_mean24']
TREND=CORE+['prior_exacerbations','pg48_spo2_delta6','pg48_hr_delta6','pg48_rr_delta6','pg48_symptom_delta6','pg48_steps_ratio24','pg48_spo2_slope24','pg48_hr_slope24','pg48_symptom_slope24','pg48_adherence_mean72','pg48_pm25_mean72','pg48_symptom_std24','pg48_spo2_std24']
CANDIDATES=[
 {'name':'baseline_tree_35','kind':'tree','features':list(FEATURES),'regularized':False},
 {'name':'original_linear_35','kind':'linear','features':list(FEATURES),'C':.3},
 {'name':'core_linear_C0.03','kind':'linear','features':CORE,'C':.03},
 {'name':'core_linear_C0.3','kind':'linear','features':CORE,'C':.3},
 {'name':'trend_linear_C0.03','kind':'linear','features':TREND,'C':.03},
 {'name':'trend_linear_C0.3','kind':'linear','features':TREND,'C':.3},
 {'name':'trend_linear_C3','kind':'linear','features':TREND,'C':3.},
 {'name':'trend_tree_regularized','kind':'tree','features':TREND,'regularized':True}]

def research_features(raw):
    """Only baseline hours0..71, trailing windows and past shifts. No event/label input."""
    df=add_features(raw);groups=df.groupby('patient_id',sort=False)
    mapping={'spo2':'spo2_baseline','heart_rate':'hr_baseline','resp_rate':'rr_baseline','symptom_score':'symptom_baseline'}
    keys={'spo2':'spo2','heart_rate':'hr','resp_rate':'rr','symptom_score':'symptom'}
    for source,baseline in mapping.items():
        for window in (6,24):
            df[f'pg48_{keys[source]}_delta{window}']=groups[source].transform(lambda s:s.rolling(window,min_periods=1).mean())-df[baseline]
        if source in ('spo2','heart_rate','symptom_score'):
            column=f'pg48_{keys[source]}_delta6';df[f'pg48_{keys[source]}_slope24']=df[column]-df.groupby('patient_id',sort=False)[column].shift(24)
    sleep_base=df[df.hour<72].groupby('patient_id').sleep_hours.median()
    df['pg48_sleep_delta24']=groups.sleep_hours.transform(lambda s:s.rolling(24,min_periods=1).mean())-df.patient_id.map(sleep_base)
    df['pg48_steps_ratio24']=groups.steps.transform(lambda s:s.rolling(24,min_periods=1).mean())/df.steps_baseline.clip(lower=10)
    for source,target in [('adherence','adherence'),('pm25','pm25')]:df[f'pg48_{target}_mean72']=groups[source].transform(lambda s:s.rolling(72,min_periods=1).mean())
    for source,target in [('symptom_score','symptom'),('spo2','spo2')]:df[f'pg48_{target}_std24']=groups[source].transform(lambda s:s.rolling(24,min_periods=2).std())
    return df

def make_candidate(spec):
    if spec['kind']=='linear':return Pipeline([('imputer',SimpleImputer(strategy='median')),('scale',StandardScaler()),('model',LogisticRegression(C=spec['C'],max_iter=2000,random_state=20261105))])
    from lightgbm import LGBMClassifier
    options=dict(n_estimators=160,learning_rate=.045,num_leaves=15,max_depth=5,min_child_samples=65,reg_lambda=3,subsample=.85,colsample_bytree=.85)
    if spec['regularized']:options.update(n_estimators=180,num_leaves=7,max_depth=3,min_child_samples=120,reg_lambda=15,subsample=1.,colsample_bytree=1.)
    return Pipeline([('imputer',SimpleImputer(strategy='median')),('model',LGBMClassifier(**options,verbosity=-1,random_state=20261105,n_jobs=2,deterministic=True,force_col_wise=True))])

def margin(pipeline,frame,features):
    x=frame[features]
    if 'scale' in pipeline.named_steps:return pipeline.decision_function(x)
    arr=pipeline.named_steps['imputer'].transform(x)
    return pipeline.named_steps['model'].booster_.predict(arr,raw_score=True,num_threads=2)

def calibrate_positive(scores,labels):
    scores=np.asarray(scores,dtype=float);labels=np.asarray(labels,dtype=float)
    if len(np.unique(labels))!=2:raise ValueError('Separate calibration set must contain both classes.')
    def loss(theta):
        a,b=theta;z=a*scores+b;r=expit(z)-labels
        return float(np.sum(np.logaddexp(0,z)-labels*z)+.5*(a-1)**2),np.array([np.sum(r*scores)+(a-1),np.sum(r)])
    result=minimize(loss,[1.,0.],jac=True,bounds=[(0,None),(None,None)],method='L-BFGS-B',options={'maxiter':2000,'ftol':1e-12,'gtol':1e-8})
    if not result.success:raise RuntimeError('Constrained calibration did not converge.')
    return {'slope':float(result.x[0]),'intercept':float(result.x[1]),'direction_preserving':True,'objective':'Summed calibration log-loss +0.5*(slope-1)^2; slope>=0.'}

@dataclass
class Research48Model:
    pipeline:Pipeline
    features:list
    calibration:dict
    candidate:str
    kind:str
    version:str=VERSION
    def raw_margin(self,frame):return margin(self.pipeline,frame,self.features)
    def predict(self,frame):return expit(self.calibration['slope']*self.raw_margin(frame)+self.calibration['intercept'])
    def explain(self,frame):
        x=frame[self.features];arr=self.pipeline.named_steps['imputer'].transform(x)
        if self.kind=='linear':
            arr=self.pipeline.named_steps['scale'].transform(arr);model=self.pipeline.named_steps['model'];values=arr[0]*model.coef_[0];base=float(model.intercept_[0]);method='Exact logistic log-odds contributions'
        else:
            values_all=self.pipeline.named_steps['model'].booster_.predict(arr,pred_contrib=True,num_threads=2)[0];values=values_all[:-1];base=float(values_all[-1]);method='LightGBM native TreeSHAP, affine calibration-rescaled'
        a=self.calibration['slope'];b=self.calibration['intercept'];drivers=[{'feature':f,'value':None if pd.isna(x.iloc[0][f]) else float(x.iloc[0][f]),'contribution':float(a*v)} for f,v in zip(self.features,values)]
        calibrated_base=float(a*base+b);total=float(calibrated_base+sum(d['contribution'] for d in drivers))
        return {'method':method,'units':'calibrated log-odds, not probability differences','base_value':calibrated_base,'raw_margin':float(base+np.sum(values)),'calibrated_margin':total,'probability':float(expit(total)),'drivers':drivers,'model_version':self.version,'caveat':'Associational model explanation, not causation or clinical advice. Sigmoid(base + contributions) equals the revised probability.'}
