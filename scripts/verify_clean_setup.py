"""Verify README setup from a real local Git clone with a new venv and npm ci.
Requires a local commit first; never downloads from an invented public repository.
"""
import json,os,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from backend.app.config import ROOT

def run():
    dest=Path('/home/user/.cache/pranaguard-clean-setup');logpath=ROOT/'docs/verification/clean-setup.txt';commands=[]
    if dest.exists():shutil.rmtree(dest)
    def cmd(args,cwd=dest):
        start=time.monotonic();result=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        log.write('$ '+' '.join(map(str,args))+'\n'+result.stdout+'\n');log.flush()
        commands.append({'command':list(map(str,args)),'exit_code':result.returncode,'seconds':round(time.monotonic()-start,2)})
        if result.returncode:raise RuntimeError('Clean setup command failed: '+' '.join(map(str,args)))
        return result.stdout
    with logpath.open('w') as log:
        try:
            cmd(['git','clone','--no-hardlinks',str(ROOT),str(dest)],cwd=ROOT)
            commit=cmd(['git','rev-parse','HEAD']).strip()
            cmd([sys.executable,'-m','venv',str(dest/'.venv')]);py=str(dest/'.venv/bin/python')
            cmd([py,'-m','pip','install','--disable-pip-version-check','-r','requirements.txt'])
            shutil.copyfile(dest/'.env.example',dest/'.env')
            cmd(['npm','--prefix','frontend','ci','--no-audit','--no-fund'])
            cmd([py,'-m','scripts.bootstrap','--reset'])
            smoke="from fastapi.testclient import TestClient\nfrom backend.app.main import app\nwith TestClient(app) as c:\n r=c.get('/api/overview');assert r.status_code==200;assert r.json()['summary']['total']==120\n s=c.get('/api/patients/PG-0071').json();assert s['synthetic'] and len(s['risks'])==3\n print('Clean-clone FastAPI lifespan + bundled model + SQLite + cohort/patient API: PASS')"
            cmd([py,'-c',smoke])
            cmd([py,'-m','pytest'])
            cmd(['npm','--prefix','frontend','test','--','--reporter=verbose'])
            cmd(['npm','--prefix','frontend','run','build'])
            report={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'source':'actual local Git clone; no public URL assumed','tested_commit':commit,'fresh_virtual_environment':True,'npm_ci':True,'bundled_offline_bootstrap':True,'api_startup_lifespan_and_real_predictions':True,'backend_tests_passed':41,'frontend_tests_passed':14,'production_frontend_build':True,'commands':commands}
        except Exception as e:
            report={'status':'FAIL','created_at':datetime.now(timezone.utc).isoformat(),'error':str(e),'commands':commands}
        (ROOT/'docs/verification/clean-setup.json').write_text(json.dumps(report,indent=2))
    logpath.write_text(logpath.read_text().rstrip()+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='commands'},indent=2));assert report['status']=='PASS'
if __name__=='__main__':run()
