"""Non-destructive ZIP-style setup in a separate source copy with fresh dependencies.
Never invokes research generation, training, replay reset, or either original Git tree.
"""
import hashlib,json,os,shutil,sqlite3,subprocess,sys,time
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from backend.app.config import ROOT

EXCLUDED={'.git','.venv','venv','node_modules','__pycache__','.pytest_cache','.cache','.mypy_cache','.ruff_cache','dist','build','coverage','playwright-report'}
def excluded(name):return name in EXCLUDED or (name.startswith('.env') and name!='.env.example') or name.endswith(('.pyc','.pyo','.tsbuildinfo','.sqlite','.sqlite-wal','.sqlite-shm','.sqlite-journal','.db','.log'))
def application_manifest(root):
    result={}
    for base in ('backend','frontend','scripts'):
        for folder,dirs,files in os.walk(root/base):
            dirs[:]=sorted(d for d in dirs if not excluded(d))
            for name in sorted(files):
                if not excluded(name):
                    path=Path(folder)/name;assert not path.is_symlink();result[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ['requirements.txt','pyproject.toml','.env.example','README.md']:
        result[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    return result

def run():
    out=ROOT/'docs/enhanced/verification';out.mkdir(parents=True,exist_ok=True)
    dest=ROOT.parent/'.cache/pranaguard-enhanced-clean-setup';sentinel=dest/'.enhanced-clean-setup-sentinel'
    assert dest!=ROOT and dest not in ROOT.parents and ROOT not in dest.parents
    if dest.exists():
        assert sentinel.is_file() and sentinel.read_text()==str(ROOT),'Refusing to remove a directory not created by this verifier.'
        shutil.rmtree(dest)
    source=application_manifest(ROOT);commands=[];report={};started=time.monotonic()
    env={k:v for k,v in os.environ.items() if not k.startswith(('PRANAGUARD_','OPEN_METEO_','VITE_')) and k not in ('API_PROXY_TARGET','PYTHONPATH')}
    env.update({'PRANAGUARD_LIVE_ENV_ENABLED':'false','PRANAGUARD_EMAIL_MODE':'disabled','PIP_DISABLE_PIP_VERSION_CHECK':'1'})
    logpath=out/'clean-setup.txt'
    with logpath.open('w') as log:
        def cmd(args,cwd=dest):
            args=list(map(str,args));print('$ '+' '.join(args),flush=True);t=time.monotonic()
            result=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=600)
            log.write('$ '+' '.join(args)+'\n'+result.stdout+'\n');log.flush();commands.append({'command':args,'exit_code':result.returncode,'seconds':round(time.monotonic()-t,3)})
            if result.returncode:raise RuntimeError('Clean setup command failed; inspect clean-setup.txt: '+' '.join(args))
            return result.stdout
        try:
            shutil.copytree(ROOT,dest,ignore=lambda folder,names:[name for name in names if excluded(name)])
            sentinel.write_text(str(ROOT))
            with sqlite3.connect('file:'+str(ROOT/'data/pranaguard.sqlite')+'?mode=ro',uri=True) as src,sqlite3.connect(dest/'data/pranaguard.sqlite') as target:src.backup(target)
            assert application_manifest(dest)==source
            shutil.copyfile(dest/'.env.example',dest/'.env')
            cmd([sys.executable,'-m','venv',dest/'.venv']);py=dest/'.venv/bin/python'
            python_version=cmd([py,'--version']).strip();node_version=cmd(['node','--version']).strip();npm_version=cmd(['npm','--version']).strip()
            cmd([py,'-m','pip','install','-r','requirements.txt']);cmd([py,'-m','pip','check'])
            cmd(['npm','--prefix','frontend','ci','--no-audit','--no-fund'])
            cmd([py,'-m','scripts.bootstrap'])
            smoke="""import hashlib,json,sqlite3
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import ROOT,DB_PATH
baseline=json.loads((ROOT/'docs/enhanced/BASELINE_MANIFEST.json').read_text())
def verify():
 with sqlite3.connect('file:'+str(DB_PATH)+'?mode=ro',uri=True) as db:
  for t,expected in baseline['database_before'].items():
   rows=[tuple(r) for r in db.execute(f'SELECT * FROM {t} ORDER BY rowid')]
   assert {'rows':len(rows),'content_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()}==expected
  assert not db.execute('PRAGMA foreign_key_check').fetchall()
verify()
with TestClient(app) as c:
 for url in ['/api/health','/api/overview','/api/patients/PG-0071','/api/validation','/api/enhanced/status','/api/enhanced/registry/patients','/api/enhanced/devices','/api/enhanced/notifications','/api/enhanced/email','/api/enhanced/provenance']:
  r=c.get(url);assert r.status_code==200,(url,r.status_code);print(url,'200')
 assert c.get('/api/overview').json()['summary']['total']==120
 assert c.get('/api/enhanced/registry/patients').json()['total']==120
 twin=c.get('/api/patients/PG-0071').json();assert twin['synthetic'] and len(twin['risks'])==3
 for city in ['Pune','Mumbai','Delhi','Bengaluru']:
  r=c.get('/api/enhanced/environment/'+city);assert r.status_code==200
  data=r.json();assert not data['live_requests_enabled'];assert all(part['status']=='historical_fallback' for part in data['components'].values())
 assert c.get('/api/enhanced/email').json()['mode']=='disabled'
verify()
print('PASS: actual ASGI lifespan, bundled predictions, 120/3000 preserved, additive migrations, enhanced reads, 4-city offline fallback; no reset or external email.')
"""
            cmd([py,'-c',smoke])
            cmd([py,'-m','pytest','--junitxml='+str(out/'clean-backend-tests.xml')])
            cmd(['npm','--prefix','frontend','test','--','--reporter=default','--reporter=json','--outputFile='+str(out/'clean-frontend-tests.json')])
            cmd(['npm','--prefix','frontend','run','build'])
            assert application_manifest(dest)==application_manifest(ROOT)==source,'Application source changed during verification.'
            suites=ET.parse(out/'clean-backend-tests.xml').getroot().iter('testsuite');backend_count=sum(int(s.get('tests','0'))-int(s.get('failures','0'))-int(s.get('errors','0'))-int(s.get('skipped','0')) for s in suites)
            frontend=json.loads((out/'clean-frontend-tests.json').read_text());assert frontend['success'] and frontend['numFailedTests']==0
            report={'status':'PASS','executed_at':datetime.now(timezone.utc).isoformat(),'source':'Actual isolated ZIP-style source copy, not a Git clone of the unmodified base commit. Application file hashes recorded below.','base_commit':json.loads((ROOT/'docs/enhanced/BASELINE_MANIFEST.json').read_text())['base_commit'],'fresh_virtual_environment':True,'pip_check':True,'npm_ci':True,'python':python_version,'node':node_version,'npm':npm_version,'bootstrap_without_reset':True,'asgi_startup_and_frozen_predictions':True,'original_cohort_and_states_unchanged':True,'offline_cities_verified':4,'backend_tests_passed':backend_count,'frontend_tests_passed':frontend['numPassedTests'],'production_frontend_build':True,'application_source_files':source,'application_source_count':len(source),'commands':commands,'total_seconds':round(time.monotonic()-started,3),'not_claimed':['Fresh external provider calls in this clean check','Physical hardware','External inbox delivery','Enhanced deployment']}
        except Exception as exc:
            report={'status':'FAIL','executed_at':datetime.now(timezone.utc).isoformat(),'error':str(exc),'commands':commands}
    (out/'CLEAN_SETUP_VERIFICATION.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('commands','application_source_files')},indent=2));assert report['status']=='PASS'
if __name__=='__main__':run()
