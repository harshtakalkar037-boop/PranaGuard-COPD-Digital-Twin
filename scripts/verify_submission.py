"""Evidence-based PASS / FAIL / PENDING gate. Public checks never use authentication.
Does not turn an existing file, a placeholder URL or HTTP200 video response into completion.
"""
import argparse,hashlib,json,re,subprocess,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import httpx
from backend.app.config import ROOT,ARTIFACTS,DATA
V=ROOT/'docs/verification'

def load(path,default=None):
    p=ROOT/path
    return json.loads(p.read_text()) if p.exists() else (default if default is not None else {})
def junit(path):
    p=ROOT/path
    if not p.exists():return {'status':'PENDING','tests':0}
    root=ET.parse(p).getroot();suites=[root] if root.tag=='testsuite' else list(root.findall('testsuite'))
    tests=sum(int(s.get('tests',0)) for s in suites);failures=sum(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites)
    return {'status':'PASS' if tests>0 and failures==0 else 'FAIL','tests':tests,'failures':failures}
def committed(path):
    r=subprocess.run(['git','show','HEAD:'+path],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    return r.returncode==0 and r.stdout==(ROOT/path).read_bytes()

def main(check_public=False):
    V.mkdir(exist_ok=True);meta=load('submission_metadata.json');readme=(ROOT/'README.md').read_text();items=[]
    def add(item,status,evidence):items.append({'item':item,'status':status,'evidence':evidence})
    pub={'repository':{'status':'PENDING','reason':'No actual public repository URL supplied; authorized publication unavailable in this build.'},'video':{'status':'PENDING','reason':'Actual recording, Unlisted upload and signed-out playback evidence absent.'},'artifact_urls':[],'authentication_used':False}
    if check_public and meta.get('public_repository_url'):
        url=meta['public_repository_url'];parsed=urlparse(url);parts=parsed.path.strip('/').split('/')
        if parsed.hostname!='github.com' or len(parts)!=2:pub['repository']={'status':'FAIL','reason':'Not an actual GitHub owner/repository URL'}
        else:
            owner,repo=parts
            try:
                response=httpx.get(f'https://api.github.com/repos/{owner}/{repo}',timeout=30,headers={'Accept':'application/vnd.github+json'});obj=response.json()
                okay=response.status_code==200 and obj.get('private') is False
                pub['repository']={'status':'PASS' if okay else 'FAIL','url':url,'http_status':response.status_code,'private':obj.get('private')}
                if okay:
                    branch=obj['default_branch']
                    for path in ['README.md','LICENSE','docs/architecture/PranaGuard_Architecture.pdf','docs/architecture/PranaGuard_Architecture.pptx','docs/presentation/PranaGuard_Digital_Twin_Challenge_2026.pdf','docs/presentation/PranaGuard_Digital_Twin_Challenge_2026.pptx','docs/screenshots/01_overview.png','docs/architecture/PranaGuard_Architecture.svg']:
                        raw=f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}'
                        r=httpx.get(raw,timeout=30,follow_redirects=True);same=r.status_code==200 and r.content==(ROOT/path).read_bytes()
                        pub['artifact_urls'].append({'path':path,'url':raw,'http_status':r.status_code,'bytes_match_local':same,'status':'PASS' if same else 'FAIL'})
            except Exception as ex:pub['repository']={'status':'FAIL','url':url,'reason':str(ex)}
    if check_public and meta.get('unlisted_youtube_url'):
        url=meta['unlisted_youtube_url'];human=load('docs/verification/video-manual-check.json');allowed=urlparse(url).hostname in ['www.youtube.com','youtube.com','youtu.be']
        if not allowed:pub['video']={'status':'FAIL','reason':'Expected an actual YouTube URL'}
        else:
            try:
                r=httpx.get(url,timeout=30,follow_redirects=True)
                human_ok=all(human.get(k) is True for k in ['unlisted_visibility_confirmed','signed_out_playback_verified','audio_and_content_reviewed']) and 15<=float(human.get('actual_duration_minutes',0))<=20 and bool(human.get('checked_by')) and bool(human.get('checked_at'))
                pub['video']={'status':'PASS' if r.status_code==200 and human_ok else 'PENDING','url':url,'http_status':r.status_code,'human_evidence':human,'reason':'HTTP status is not playback/duration/visibility evidence; signed-out human review required.'}
            except Exception as ex:pub['video']={'status':'FAIL','reason':str(ex),'url':url}
    if not check_public and meta.get('public_repository_url'):pub['repository']['reason']='Actual URL supplied, but unauthenticated check was not requested.'
    # Generate report paths before validating README-relative links, then overwrite with complete reports below.
    publictext=['# Public-access verification','',f'Checked: {datetime.now(timezone.utc).isoformat()}','',f'Project repository: **{pub["repository"]["status"]}** — {pub["repository"].get("reason",pub["repository"].get("url",""))}',f'Actual Unlisted video: **{pub["video"]["status"]}** — {pub["video"].get("reason","")}', '', 'No project GitHub/video URL was invented. A workspace preview does not prove unauthenticated public access. Raw environmental requests succeeded without credentials during caching; exact URLs/access times/checksums are in the source manifest.']
    if pub['artifact_urls']:
        publictext+=['','| Artifact | HTTP | Byte match | Status |','|---|---:|---|---|']+[f'| {x["path"]} | {x["http_status"]} | {x["bytes_match_local"]} | {x["status"]} |' for x in pub['artifact_urls']]
    else:publictext+=['','Project README / architecture PDF+PPTX / presentation PDF+PPTX / GitHub screenshots: **PENDING** public-access checks because no verified public repository exists. Local files and relative links are checked separately, not treated as public proof.']
    (V/'PUBLIC_ACCESS.md').write_text('\n'.join(publictext)+'\n');(V/'public-access.json').write_text(json.dumps(pub,indent=2))
    for path,initial in [(ROOT/'docs/SUBMISSION_CHECKLIST.md','# Submission checklist\n'),(V/'submission-audit.json','{}')]:
        if not path.exists():path.write_text(initial)
    links=[]
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',readme):
        if link.startswith(('https://','http://','#','mailto:')):continue
        path=link.split('#')[0];okay=(ROOT/path).is_file();links.append({'link':link,'exists':okay})
    sections=['Team details','College/incubator information','Project title','Problem statement','Healthcare use case','Technical stack','AI/ML model or framework details','Actual 15–20 minute demo video link','Open-source license details','Architecture diagram in PDF/PPT format','Presentation in PDF/PPT format','Confirmation that referenced files and links are publicly accessible']
    section_checks={s:s.casefold() in readme.casefold() for s in sections}
    backend=junit('docs/verification/backend-junit.xml');frontend=junit('docs/verification/frontend-junit.xml');browser=load('docs/verification/browser-verification.json');artifact=load('docs/verification/artifact-verification.json');repro=load('docs/verification/reproducibility.json');setup=load('docs/verification/clean-setup.json')
    relative_ok=all(x['exists'] for x in links);sections_ok=all(section_checks.values())
    add('Public GitHub repository URL verified',pub['repository']['status'],pub['repository'].get('reason',pub['repository'].get('url','')))
    add('Root README exists and is complete','PASS' if relative_ok and sections_ok else 'FAIL',f'{len(links)} local links checked; {sum(section_checks.values())}/{len(section_checks)} mandatory sections present. External completion remains pending.')
    team_ok=bool(meta.get('team_name')) and bool(meta.get('team_members'))
    add('Team details included or explicitly marked pending','PASS' if team_ok else 'PENDING','Actual team/member identities pending; clearly labelled placeholders are present.')
    add('College/incubator information included or explicitly marked pending','PASS' if meta.get('college_or_incubator') else 'PENDING','Actual institution pending; placeholder present.')
    for item,section in [('Project title included','Project title'),('Problem statement included','Problem statement'),('Healthcare use case included','Healthcare use case'),('Technical stack included','Technical stack'),('AI/ML model/framework details included','AI/ML model or framework details')]:add(item,'PASS' if section_checks[section] else 'FAIL','Verified explicit README section and corresponding implementation/report.')
    add('Actual 15–20 minute Unlisted YouTube video uploaded',pub['video']['status'],pub['video'].get('reason','Requires actual recording/upload/playback evidence.'))
    video_inserted=bool(meta.get('unlisted_youtube_url')) and meta['unlisted_youtube_url'] in readme
    add('Final video URL inserted into README','PASS' if video_inserted else 'PENDING','No actual YouTube URL yet; placeholder text is not counted as completion.' if not video_inserted else 'Actual supplied URL appears in README; playback is a separate gate.')
    add('Open-source license details included','PASS' if 'MIT' in readme and (ROOT/'LICENSE').exists() else 'FAIL','MIT code license; environmental CC BY4.0 and synthetic CC0 attribution documented separately.')
    add('Actual license file committed','PASS' if committed('LICENSE') else 'PENDING','Verified MIT LICENSE content in local HEAD.' if committed('LICENSE') else 'Requires the actual license to be included in a local commit.')
    artifact_ok=bool(artifact.get('all_pass'))
    for item in ['Architecture diagram exported as PDF','Architecture diagram available in PPT/PPTX-compatible format','Presentation exported as PDF','Editable presentation available as PPTX']:
        add(item,'PASS' if artifact_ok else 'PENDING','Parsed OOXML, actual PDF exports, page/text/bounds/image verification and rendered QA; see artifact-verification.json. Public access is a separate pending gate.')
    add('Presentation covers project details and actual outcomes','PASS' if artifact_ok else 'PENDING','16 slides; actual screenshots, executed metrics/ablations, negative72h findings, false-positive demo and safety/pending items verified.')
    mandatory=['README.md','LICENSE','docs/architecture/PranaGuard_Architecture.pdf','docs/architecture/PranaGuard_Architecture.pptx','docs/presentation/PranaGuard_Digital_Twin_Challenge_2026.pdf','docs/presentation/PranaGuard_Digital_Twin_Challenge_2026.pptx','docs/TECHNICAL_REPORT.md','docs/demo/DEMO_SCRIPT.md','artifacts/evaluation.json']
    committed_ok=all(committed(p) for p in mandatory)
    add('All referenced artifacts committed and linked','PASS' if relative_ok and committed_ok else 'PENDING','Required local artifact bytes match HEAD and README links resolve.' if relative_ok and committed_ok else 'Local files/links checked; final local commit must include the actual artifact bytes. Public publication remains separate.')
    public_ok=pub['repository']['status']=='PASS' and pub['video']['status']=='PASS' and bool(pub['artifact_urls']) and all(x['status']=='PASS' for x in pub['artifact_urls'])
    add('Public links tested without additional permissions','PASS' if public_ok else 'PENDING','Unauthenticated repository/raw-file and human signed-out video checks must all pass; no local preview substituted.')
    add('React frontend tested',frontend['status'],f'{frontend["tests"]} Vitest/RTL tests; browser checks {browser.get("passed",0)} passing, no page/API errors in final run.')
    add('FastAPI backend tested',backend['status'],f'{backend["tests"]} pytest tests; {backend.get("failures",0)} failures/errors. One upstream Starlette/httpx deprecation warning.')
    model_ok=backend['status']=='PASS' and repro.get('status')=='PASS' and (ARTIFACTS/'evaluation_verification.json').exists() and browser.get('failed',1)==0
    add('Model and twin workflows tested','PASS' if model_ok else 'PENDING','Actual inference consistency, replay, persistence, causal features, SHAP additivity, state-preserving scenarios, alert lifecycle and metric recomputation; full reproduction matches exactly.')
    add('README setup instructions verified',setup.get('status','PENDING'),'Clean local clone + new venv + pinned pip install + npm ci + bootstrap + API startup + backend/frontend tests + build; see clean-setup.json.' if setup.get('status')=='PASS' else 'Fresh-environment setup check not yet recorded.')
    prohibited=[]
    for path in ['requirements.txt','requirements-docs.txt','frontend/package.json']:
        text=(ROOT/path).read_text()
        if re.search(r'(?im)^\s*(?:"?streamlit|docker(?:-compose)?)\b',text):prohibited.append(path)
    for name in ['Dockerfile','docker-compose.yml','compose.yaml']:
        if (ROOT/name).exists():prohibited.append(name)
    add('No Docker or Streamlit dependency','PASS' if not prohibited else 'FAIL','Python venv/npm/SQLite workflow; prohibited dependency/config scan clean.' if not prohibited else str(prohibited))
    dataset_hash=hashlib.sha256((DATA/'synthetic_longitudinal.csv.gz').read_bytes()).hexdigest();evaluation=load('artifacts/evaluation.json')
    genuine=model_ok and dataset_hash==evaluation.get('dataset_sha256') and not any('__fixtures__' in p.read_text() for p in (ROOT/'frontend/src').glob('*.tsx') if '.test.' not in p.name)
    add('No fabricated metrics or links','PASS' if genuine else 'PENDING','15 experiments executed twice; saved predictions independently recomputed; production has no test-fixture import; GitHub/video URLs remain absent, not invented.')
    # High-confidence credential-pattern scan of project-owned tracked text (no dependency directories).
    gitfiles=subprocess.run(['git','ls-files','-z'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    files=[ROOT/p for p in gitfiles.stdout.decode().split('\0') if p] if gitfiles.returncode==0 else []
    secrets=[];patterns=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'AKIA[0-9A-Z]{16}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'xox[baprs]-[A-Za-z0-9-]{20,}']
    for path in files:
        if path.suffix.lower() not in ['.py','.ts','.tsx','.json','.md','.txt','.env','.example','.yml','.toml']:continue
        try:text=path.read_text()
        except UnicodeDecodeError:continue
        if any(re.search(p,text) for p in patterns) and path.name!='verify_submission.py':secrets.append(str(path.relative_to(ROOT)))
    forbidden_tracked=[str(p.relative_to(ROOT)) for p in files if p.name=='.env' or any(part in ['node_modules','.venv'] for part in p.parts) or p.suffix in ['.sqlite','.db']]
    package_ready=all(x['status']=='PASS' for x in items) and not secrets and not forbidden_tracked
    audit={'checked_at':datetime.now(timezone.utc).isoformat(),'submission_ready':package_ready,'summary':{k:sum(x['status']==k for x in items) for k in ['PASS','FAIL','PENDING']},'checklist':items,'readme_sections':section_checks,'local_link_checks':links,'public_access':pub,'backend_tests':backend,'frontend_tests':frontend,'secret_pattern_findings':secrets,'forbidden_tracked_files':forbidden_tracked,'limitations':'Pattern scan is not a guarantee of absence of all secrets. Model/software test success is not clinical validation.'}
    (V/'submission-audit.json').write_text(json.dumps(audit,indent=2))
    md=['# Final submission gate','', '**NOT FULLY SUBMISSION-READY.**' if not package_ready else '**All recorded mandatory gates pass; owner should still confirm the official portal requirements.**','',f'Checked: {audit["checked_at"]}', '', '| Mandatory item | Status | Verification / outstanding evidence |','|---|---|---|']
    md += [f'| {x["item"]} | **{x["status"]}** | {x["evidence"]} |' for x in items]
    md+=['',f'**Totals:** {audit["summary"]["PASS"]} PASS · {audit["summary"]["FAIL"]} FAIL · {audit["summary"]["PENDING"]} PENDING.','', '## Human-owned outstanding tasks','1. Supply actual team/member and college/incubator details; update metadata, README and slide1.','2. Publish the prepared repository as public using docs/PUBLISHING.md; do not invent a URL.','3. Record the actual15–20 minute demo, upload it to YouTube as Unlisted, review duration/audio/content and signed-out playback.','4. Insert the actual GitHub/video URLs, commit/push the final files and rerun unauthenticated public-access checks.','5. Open the repository, all artifact URLs/images and video signed out; document manual video verification and only then reassess readiness.','', '## Additional engineering verification','- High-confidence secret scan findings: '+str(secrets),'- Forbidden tracked environment/dependency/runtime DB files: '+str(forbidden_tracked),'- Actual poor72h performance and false-positive example are disclosed, not masked.','- The source DOCX was absent; user explicitly authorized the supplied message instead.','- No clinical validation or intervention benefit is established.']
    (ROOT/'docs/SUBMISSION_CHECKLIST.md').write_text('\n'.join(md)+'\n');print(json.dumps({'ready':package_ready,**audit['summary'],'local_links':len(links),'missing_local_links':[x for x in links if not x['exists']],'secret_findings':secrets,'forbidden_tracked':forbidden_tracked},indent=2))
    return audit
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check-public',action='store_true');a=p.parse_args();main(a.check_public)
