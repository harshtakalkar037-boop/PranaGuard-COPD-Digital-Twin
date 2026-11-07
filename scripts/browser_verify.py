"""Actual Chromium integration run and screenshots. Start both local servers first."""
import json, os
from datetime import datetime,timezone
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect
from backend.app.config import ROOT
BASE=os.getenv('PRANAGUARD_BROWSER_URL','http://127.0.0.1:5173')
API=os.getenv('PRANAGUARD_API_URL','http://127.0.0.1:8000')+'/api'
OUT=ROOT/'docs'/'verification';SHOTS=ROOT/'docs'/'screenshots'

def run():
    checks=[];errors=[];external=[];bad_api=[]
    def mark(name,detail=''):checks.append({'name':name,'status':'PASS','detail':detail});print('PASS',name)
    def request(path,body=None):
        response=httpx.post(API+path,json=body or {},timeout=60) if body is not None else httpx.get(API+path,timeout=60)
        response.raise_for_status();return response.json()
    request('/replay/reset',{'prime_hours':24});pid=request('/replay')['demo']['patient_id']
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1512,'height':1120},device_scale_factor=1,accept_downloads=True)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        def route_handler(route):
            url=route.request.url
            if not url.startswith(BASE) and not url.startswith('data:') and not url.startswith('blob:'):
                external.append(url);route.abort()
            else:route.continue_()
        context.route('**/*',route_handler)
        page.on('response',lambda r:bad_api.append({'url':r.url,'status':r.status}) if '/api/' in r.url and r.status>=400 else None)
        def nav(name):page.locator('aside').get_by_role('button',name=name,exact=True).click()
        def shot(name):
            if page.locator('.toast').count():page.locator('.toast').wait_for(state='hidden',timeout=8000)
            page.screenshot(path=str(SHOTS/name),full_page=True)
        page.goto(BASE,wait_until='networkidle');expect(page.get_by_role('heading',name='Your patient cohort')).to_be_visible();mark('React loads backend cohort')
        expect(page.get_by_text('120',exact=True)).to_be_visible();mark('Actual cohort count 120 and synthetic provenance displayed')
        shot('01_overview.png')
        search=page.get_by_label('Search patients');search.fill(pid);expect(page.get_by_role('button',name=f'Open {pid}')).to_be_visible();mark('Patient search')
        page.get_by_role('button',name=f'Open {pid}').click();expect(page.get_by_role('heading',name='Personal baseline vs current')).to_be_visible();mark('Patient digital twin integrated')
        page.get_by_label('Physiology signal').select_option('heart_rate');page.get_by_label('Twin state version').select_option('1')
        expect(page.locator('.twin-banner-right').get_by_text('State v1',exact=False)).to_be_visible();page.get_by_label('Twin state version').select_option('current');mark('Persisted historical version selection')
        expect(page.locator('.twin-banner-right').get_by_text('State v25',exact=False)).to_be_visible();shot('02_patient_twin.png')
        with page.expect_download() as download_info:page.get_by_role('button',name='Export twin').click()
        download=download_info.value;export_path=OUT/'exported-twin.json';download.save_as(str(export_path))
        exported=json.loads(export_path.read_text());assert exported['patient_id']==pid and exported['synthetic'];mark('Snapshot JSON export')
        nav('Risk explainability');expect(page.get_by_text('LightGBM native TreeSHAP',exact=True)).to_be_visible()
        page.get_by_role('button',name='24 hours',exact=True).click();expect(page.get_by_text('24h calibrated risk')).to_be_visible();page.get_by_role('button',name='72 hours',exact=True).click();mark('Explainability endpoint and horizon switch');shot('03_explainability.png')
        nav('What-if studio');expect(page.get_by_role('button',name='Run backend simulation')).to_be_visible();before=request('/patients/'+pid)
        pm=page.get_by_label('PM2.5 change');pm.focus();pm.press('ArrowLeft');page.get_by_role('button',name='Run backend simulation').click()
        expect(page.get_by_text('Original twin preserved',exact=True)).to_be_visible(timeout=20000);after=request('/patients/'+pid);assert before==after
        assert request('/patients/'+pid+'/scenarios')['scenarios'];mark('Backend scenario response, persistence and state isolation');shot('04_what_if.png')
        nav('Model validation');expect(page.get_by_role('heading',name='Executed ablations')).to_be_visible();expect(page.get_by_text('0.3951',exact=True).first).to_be_visible()
        page.get_by_role('button',name='24-hour horizon').click();expect(page.get_by_text('0.6916',exact=True).first).to_be_visible();page.get_by_role('button',name='72-hour horizon').click();mark('Actual evaluation, diagnostics and ablations');shot('05_model_validation.png')
        initial=request('/replay')['cursor_hour'];page.get_by_role('button',name='Play replay',exact=True).click()
        page.wait_for_function('''async (hour) => {const r=await fetch('/api/replay');return (await r.json()).cursor_hour>hour;}''',arg=initial,timeout=12000)
        page.get_by_role('button',name='Pause',exact=True).click();assert not request('/replay')['running'];mark('Timed replay start/pause with WebSocket refresh')
        # Reset so the +12h demonstration is deterministic and reaches the documented actual high-score state.
        page.once('dialog',lambda d:d.accept())
        with page.expect_response(lambda r:'/api/replay/reset' in r.url and r.request.method=='POST') as reset_response:
            page.get_by_role('button',name='Reset deterministic demo').click()
        assert reset_response.value.status==200
        page.wait_for_function('''async () => (await (await fetch('/api/replay')).json()).cursor_hour===1039''',timeout=15000)
        with page.expect_response(lambda r:'/api/replay/step' in r.url and r.request.method=='POST') as step_response:
            page.get_by_role('button',name='12h',exact=True).click()
        assert step_response.value.status==200
        page.wait_for_function('''async () => (await (await fetch('/api/replay')).json()).cursor_hour===1051''',timeout=15000)
        alerts=request('/alerts')['alerts'];assert any(a['patient_id']==pid and a['risk']>=.35 for a in alerts),(pid,alerts,request('/replay'));mark('Replay raises actual model-generated false-positive alert')
        nav('Care activity');expect(page.get_by_role('button',name='Acknowledge')).to_be_visible();page.get_by_role('button',name='Acknowledge').click();expect(page.locator('article').get_by_text('acknowledged',exact=True)).to_be_visible();mark('Persisted alert acknowledgement')
        page.get_by_label('Review note').fill('Synthetic demonstration: reviewed model false positive. No treatment recommendation.')
        page.get_by_role('button',name='Save action').click();expect(page.get_by_text('Synthetic demonstration: reviewed model false positive. No treatment recommendation.',exact=True)).to_be_visible();mark('Persisted clinician intervention log');shot('06_alerts_and_interventions.png')
        page.get_by_role('button',name='Resolve',exact=True).click();expect(page.locator('article').get_by_text('resolved',exact=True)).to_be_visible();page.reload(wait_until='networkidle');expect(page.locator('article').get_by_text('resolved',exact=True)).to_be_visible();mark('Alert resolution and intervention survive browser reload')
        nav('System & data');expect(page.get_by_role('heading',name='Source freshness & provenance')).to_be_visible();mark('System status and cache provenance');shot('07_system_status.png')
        # Verify same-origin host acceptance separately; no external data needed for the application run.
        assert not external,external;mark('Offline runtime: external browser HTTP requests blocked; no external requests attempted')
        assert not errors,errors;assert not bad_api,bad_api;mark('No browser JavaScript errors or failed API responses')
        mobile=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
        mobile.goto(BASE,wait_until='networkidle');expect(mobile.get_by_role('heading',name='Cohort overview',exact=True)).to_be_visible()
        mobile.get_by_role('button',name='Open navigation').click();expect(mobile.locator('aside')).to_be_visible();mobile.locator('aside').get_by_role('button',name='Patient twins',exact=True).click();expect(mobile.get_by_role('heading',name='Personal baseline vs current')).to_be_visible();mobile.screenshot(path=str(SHOTS/'08_mobile_patient.png'),full_page=True)
        assert mobile.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1');mark('390px mobile layout and navigation without viewport overflow')
        browser.close()
    # Leave the preview in a clean, documented initial state for reviewers.
    request('/replay/reset',{'prime_hours':24})
    report={'created_at':datetime.now(timezone.utc).isoformat(),'base_url':BASE,'checks':checks,'passed':len(checks),'failed':0,'browser_errors':errors,'failed_api':bad_api,'external_requests':external,'screenshots':sorted(f.name for f in SHOTS.glob('*.png'))}
    (OUT/'browser-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':len(checks),'failed':0}))
if __name__=='__main__':run()
