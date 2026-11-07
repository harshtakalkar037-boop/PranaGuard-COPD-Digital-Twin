"""Execute generation/training again and compare actual outputs to the delivered experiment."""
import hashlib,json,subprocess,sys
import pandas as pd
import numpy as np
from backend.app.config import ROOT,ARTIFACTS,DATA

def run():
    before=pd.read_csv(ARTIFACTS/'metrics.csv');pred_before=pd.read_csv(ARTIFACTS/'test_predictions.csv.gz')
    sha_before=hashlib.sha256((DATA/'synthetic_longitudinal.csv.gz').read_bytes()).hexdigest()
    before.to_csv(ROOT/'docs/verification/first-run-metrics.csv',index=False)
    for mod in ['scripts.generate_data','scripts.train','scripts.select_demo','scripts.evaluate']:
        subprocess.run([sys.executable,'-m',mod],cwd=ROOT,check=True)
    after=pd.read_csv(ARTIFACTS/'metrics.csv');pred_after=pd.read_csv(ARTIFACTS/'test_predictions.csv.gz')
    sha_after=hashlib.sha256((DATA/'synthetic_longitudinal.csv.gz').read_bytes()).hexdigest()
    cols=['auroc','auprc','brier','precision','recall','specificity']
    delta=float(np.max(np.abs(before[cols].to_numpy()-after[cols].to_numpy())))
    pcols=['risk_24','risk_48','risk_72'];pdelta=float(np.max(np.abs(pred_before[pcols].to_numpy()-pred_after[pcols].to_numpy())))
    assert sha_before==sha_after;assert delta<1e-12;assert pdelta<1e-12
    report={'status':'PASS','dataset_bytes_identical':True,'sha256':sha_after,'experiments':len(after),'max_metric_absolute_difference':delta,'max_test_prediction_absolute_difference':pdelta,'seed':2026}
    (ROOT/'docs/verification/reproducibility.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':run()
