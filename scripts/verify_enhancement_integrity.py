"""Read-only scientific/design regression. Writes evidence only under docs/enhanced.
Does not regenerate data, retrain, reselect a case or modify historical artifacts.
"""
import hashlib,json,re,subprocess,sqlite3
from datetime import datetime,timezone
from pathlib import Path
import joblib,numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,confusion_matrix
from backend.app.config import ROOT
from backend.app.features import add_features

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def run():
    manifest=json.loads((ROOT/'docs/enhanced/BASELINE_MANIFEST.json').read_text())
    files={name:{'expected':sha,'actual':digest(ROOT/name)} for name,sha in manifest['protected_files'].items()}
    assert all(x['expected']==x['actual'] for x in files.values()),'A protected scientific/design file changed.'
    base_colors=set(re.findall(r'#[a-fA-F0-9]{3,8}\b',(ROOT/'frontend/src/styles.css').read_text()))
    new_colors=set(re.findall(r'#[a-fA-F0-9]{3,8}\b',(ROOT/'frontend/src/enhanced/enhanced.css').read_text()))
    assert new_colors<=base_colors,new_colors-base_colors
    saved=pd.read_csv(ROOT/'artifacts/test_predictions.csv.gz');frame=add_features(pd.read_csv(ROOT/'data/synthetic_longitudinal.csv.gz'))
    x=saved[['patient_id','hour']].merge(frame,on=['patient_id','hour'],how='left',validate='one_to_one',sort=False)
    bundle=joblib.load(ROOT/'artifacts/models.joblib');evaluation=json.loads((ROOT/'artifacts/evaluation.json').read_text());horizons={}
    for h in (24,48,72):
        p=bundle['models'][h].predict(x);expected=saved[f'risk_{h}'].to_numpy();error=float(np.max(np.abs(p-expected)));assert error<1e-14,error
        y=saved[f'label_{h}'].astype(int);target=next(r for r in evaluation['results'] if r['algorithm']=='LightGBM' and r['ablation']=='personalized' and r['horizon']==h)
        recomputed={'auroc':float(roc_auc_score(y,p)),'auprc':float(average_precision_score(y,p)),'brier':float(brier_score_loss(y,p))}
        for key,value in recomputed.items():assert abs(value-target[key])<1e-12,(h,key,value,target[key])
        matrix=confusion_matrix(y,p>=.35).tolist();assert matrix==evaluation['diagnostics'][str(h)]['metrics']['confusion_matrix']
        horizons[str(h)]={'saved_predictions':len(expected),'max_absolute_difference':error,'metrics':recomputed,'confusion_matrix_at_0_35':matrix,'unchanged':True}
    # The delivered preservation DB, never the browser's throwaway verification.sqlite.
    after={}
    with sqlite3.connect('file:'+str(ROOT/'data/pranaguard.sqlite')+'?mode=ro',uri=True) as c:
        c.row_factory=sqlite3.Row
        for t in manifest['database_before']:
            rows=[tuple(r) for r in c.execute(f'SELECT * FROM {t} ORDER BY rowid')]
            after[t]={'rows':len(rows),'content_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()}
        assert after==manifest['database_before'],'Original preserved DB rows were changed.'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        migrations=[dict(r) for r in c.execute('SELECT version,name,applied_at FROM schema_migrations ORDER BY version')]
    original=ROOT.parent/'PranaGuard-COPD-Digital-Twin/data/pranaguard.sqlite'
    source_unchanged=(digest(original)==manifest['source_workspace_db_sha256']) if original.exists() else None
    if source_unchanged is not None:assert source_unchanged
    historical=[]
    if (ROOT/'.git').exists():
        # Historical slides, PDFs, screenshots, old reports and original scripts stay byte-identical.
        paths=subprocess.check_output(['git','ls-tree','-r','--name-only',manifest['base_commit']],cwd=ROOT,text=True).splitlines()
        allowed={'docs/API.md','docs/DATA_PROVENANCE.md'}
        for name in paths:
            if (name.startswith('docs/') and name not in allowed) or name.startswith('scripts/'):
                before=subprocess.check_output(['git','show',manifest['base_commit']+':'+name],cwd=ROOT)
                assert (ROOT/name).read_bytes()==before,'Historical file changed: '+name
                historical.append(name)
    result={'executed_at':datetime.now(timezone.utc).isoformat(),'status':'PASS','protected_files':files,'protected_count':len(files),'new_css_colors_are_existing_palette':True,'historical_files_checked':historical,'held_out_prediction_regression':horizons,'preserved_database_original_tables':after,'migrations':migrations,'original_workspace_database_unchanged':source_unchanged,'no_training_or_historical_evaluation_write':True}
    out=ROOT/'docs/enhanced/verification/INTEGRITY_VERIFICATION.json';out.write_text(json.dumps(result,indent=2));print(json.dumps({'status':'PASS','protected_files':len(files),'held_out_rows':len(saved),'horizons':horizons,'preserved_original_states':after['states']['rows'],'historical_files_checked':len(historical)},indent=2))

if __name__=='__main__':run()
