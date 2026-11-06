"""Recompute main metrics from saved TEST predictions; fail if reported numbers drift."""
import json
import numpy as np
import pandas as pd
from backend.app.config import ARTIFACTS
from scripts.train import metrics

def evaluate():
    report=json.loads((ARTIFACTS/'evaluation.json').read_text());preds=pd.read_csv(ARTIFACTS/'test_predictions.csv.gz');checks=[]
    for h in [24,48,72]:
        actual=metrics(preds[f'label_{h}'].astype(int).to_numpy(),preds[f'risk_{h}'].to_numpy());saved=report['diagnostics'][str(h)]['metrics']
        for key in ['auroc','auprc','brier','precision','recall','specificity','prevalence']:
            assert np.isclose(actual[key],saved[key],atol=1e-12),(h,key,actual[key],saved[key])
        assert actual['confusion_matrix']==saved['confusion_matrix'];checks.append({'horizon':h,'verified':True,'metrics':actual})
    (ARTIFACTS/'evaluation_verification.json').write_text(json.dumps({'source':'recomputed from test_predictions.csv.gz','checks':checks},indent=2))
    print(json.dumps(checks,indent=2))
if __name__=='__main__':evaluate()
