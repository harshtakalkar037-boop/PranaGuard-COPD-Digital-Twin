"""Retrospective score-selected replay example; never alters training or test metrics."""
import json
import joblib,numpy as np,pandas as pd
from backend.app.config import DATA,ARTIFACTS
from backend.app.features import add_features

def select():
    current=json.loads((ARTIFACTS/'demo_case.json').read_text())
    if current.get('onset_hour') is not None:return current
    b=joblib.load(ARTIFACTS/'models.joblib');x=add_features(pd.read_csv(DATA/'synthetic_longitudinal.csv.gz'))
    candidate=x[x.eligible & (x.hour>=120)];p=b['models'][72].predict(candidate)
    ix=int(np.argmax(p));r=candidate.iloc[ix];peak=int(r.hour)
    result={'patient_id':r.patient_id,'start_hour':peak-12,'focus_hour':peak,'onset_hour':None,
            'selected_risk_72':float(p[ix]),'selected_label_72':int(r.label_72),
            'selection':'Retrospective maximum 72h model score across the synthetic cohort (not a held-out prospective case). Chosen to demonstrate a real model-generated alert, not detection performance. This example is a false positive when selected_label_72=0.'}
    (ARTIFACTS/'demo_case.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':print(json.dumps(select(),indent=2))
