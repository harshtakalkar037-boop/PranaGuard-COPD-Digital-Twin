"""Shared fitted-model operations. Never return a handcrafted risk score."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


def logit(p):
    p=np.clip(np.asarray(p),1e-6,1-1e-6)
    return np.log(p/(1-p)).reshape(-1,1)

@dataclass
class HorizonModel:
    pipeline: Pipeline
    calibrator: LogisticRegression
    features: list
    horizon: int
    algorithm: str
    reference: dict

    def predict(self, frame):
        raw=self.pipeline.predict_proba(frame[self.features])[:,1]
        return self.calibrator.predict_proba(logit(raw))[:,1]

    def explain(self, frame):
        x=frame[self.features]
        if self.algorithm=='LightGBM':
            arr=self.pipeline.named_steps['imputer'].transform(x)
            # Native LightGBM TreeSHAP, exact additive contributions in raw log-odds.
            v=self.pipeline.named_steps['model'].booster_.predict(arr,pred_contrib=True)[0]
            return {'method':'LightGBM native TreeSHAP','units':'uncalibrated raw log-odds',
                    'base_value':float(v[-1]),'raw_margin':float(v.sum()),
                    'drivers':[{'feature':f,'value':None if pd.isna(x.iloc[0][f]) else float(x.iloc[0][f]),'contribution':float(c)} for f,c in zip(self.features,v[:-1])],
                    'caveat':'Contributions explain the uncalibrated tree score, not the final calibrated probability. Association, not causation.'}
        probability=float(self.predict(frame)[0]); drivers=[]
        for f in self.features:
            altered=frame.copy(); altered[f]=self.reference[f]
            drivers.append({'feature':f,'value':None if pd.isna(frame.iloc[0][f]) else float(frame.iloc[0][f]),
                            'contribution':probability-float(self.predict(altered)[0])})
        return {'method':'one-feature reference perturbation (fallback)','units':'probability difference, not additive',
                'base_value':None,'raw_margin':None,'drivers':drivers,
                'caveat':'Correlated features remain fixed; perturbations are not causal or additive SHAP values.'}


def make_pipeline(algorithm, seed=2026):
    if algorithm=='LightGBM':
        from lightgbm import LGBMClassifier
        model=LGBMClassifier(n_estimators=160,learning_rate=.045,num_leaves=15,max_depth=5,
                            min_child_samples=65,reg_lambda=3,subsample=.85,colsample_bytree=.85,
                            verbosity=-1,random_state=seed,n_jobs=2,deterministic=True,force_col_wise=True)
        return Pipeline([('imputer',SimpleImputer(strategy='median')),('model',model)])
    return Pipeline([('imputer',SimpleImputer(strategy='median')),('scale',StandardScaler()),
                     ('model',LogisticRegression(max_iter=1200,C=.3,random_state=seed))])


def fit_model(train,cal,features,horizon,algorithm):
    p=make_pipeline(algorithm)
    p.fit(train[features],train[f'label_{horizon}'].astype(int))
    raw=p.predict_proba(cal[features])[:,1]
    calibrator=LogisticRegression(C=1,max_iter=500).fit(logit(raw),cal[f'label_{horizon}'].astype(int))
    return HorizonModel(p,calibrator,features,horizon,algorithm,train[features].median().to_dict())
