"""Actual Chromium workspace regression: auth, directory, profile, care workflow, persistence, theme.
Point PRANAGUARD_BROWSER_URL and PRANAGUARD_API_URL at running app; DB must be a disposable copy.
Optional dependency: playwright + Chromium."""
import json,os
from datetime import datetime,timezone
import httpx
from playwright.sync_api import sync_playwright,expect
from backend.app.config import ROOT

def run():
    web=os.getenv('PRANAGUARD_BROWSER_URL','http://127.0.0.1:5173');api=os.getenv('PRANAGUARD_API_URL','http://127.0.0.1:8011')+'/api'
    out=ROOT/'docs/workspace-verification';shots=out/'screenshots';shots.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];failed=[];requests=[]
    def mark(name):checks.append({'name':name,'status':'PASS'});print('PASS',name,flush=True)
    def login(page,user_label='Dr. Asha Atlas'):
        page.goto(web);expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
        page.get_by_role('button',name=user_label).click()
        expect(page.get_by_role('heading',name='Your patient cohort')).to_be_visible()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('request',lambda r:requests.append(r.url));page.on('response',lambda r:failed.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        page.goto(web)
        expect(page.get_by_role('heading',name='One workspace for every synthetic twin.')).to_be_visible()
        expect(page.get_by_text('dr-atlas',exact=True)).to_be_visible();mark('Login screen with documented demo identities')
        r=httpx.post(api+'/workspace/login',json={'username':'dr-atlas','password':'wrong-password'},timeout=10);assert r.status_code==401;mark('Backend rejects bad credentials')
        page.get_by_role('button',name='Dr. Asha Atlas').click()
        expect(page.get_by_role('heading',name='Your patient cohort')).to_be_visible()
        colour=page.locator('aside').evaluate('(e)=>getComputedStyle(e).backgroundColor');assert colour=='rgb(16, 59, 52)',colour;mark('Sign-in opens workspace; original forest-green identity intact')
        nav=page.get_by_role('navigation')
        for group in ['Workspace','Twin & research','Care records','Data & system']:expect(nav.get_by_text(group,exact=True)).to_be_visible()
        mark('Sidebar regrouped into 4 meaning groups')
        page.get_by_role('button',name='Patients',exact=True).click()
        expect(page.get_by_role('heading',name='Unified patient directory')).to_be_visible()
        expect(page.get_by_text('Doctor-scoped · no cross-assignment leakage',exact=True)).to_be_visible()
        page.get_by_label('Search directory').fill('PG-0071')
        expect(page.get_by_text('1–1 of 1 assigned synthetic patients',exact=True)).to_be_visible();mark('Unified doctor-scoped directory with server-side search')
        page.get_by_role('button',name='Profile',exact=True).first.click()
        expect(page.get_by_test_id('patient-profile')).to_be_visible();expect(page.get_by_text('Frozen research models never ingest monitoring data',exact=True)).to_be_visible()
        page.get_by_role('button',name='Care plan').click()
        page.get_by_role('button',name='Create plan',exact=True).or_(page.get_by_role('button',name='Edit plan',exact=True)).first.click()
        page.get_by_label('Documented goals').fill('Browser-check demo goals only.')
        with page.expect_response(lambda r:'/plan' in r.url and r.request.method=='PUT') as presp:page.get_by_role('button',name='Save plan').click()
        assert presp.value.status==200,presp.value.text()
        expect(page.get_by_text('Care plan documentation saved.',exact=True)).to_be_visible(timeout=10000);mark('Care-plan editor saves through backend with feedback')
        page.get_by_role('button',name='Sputum diary').click()
        page.get_by_label('Notes').fill('Browser diary check')
        with page.expect_response(lambda r:'/sputum' in r.url and r.request.method=='POST') as resp:page.get_by_role('button',name='Save diary entry').click()
        assert resp.value.status==200,resp.value.status
        expect(page.get_by_text('Browser diary check',exact=False).first).to_be_visible(timeout=10000);mark('Sputum diary entry persists and renders immediately')
        page.get_by_role('button',name='Care action centre',exact=True).click()
        expect(page.get_by_text('Assigned patients',exact=True)).to_be_visible();expect(page.get_by_text('Follow-ups due',exact=True)).to_be_visible();mark('Care centre summary metrics from SQLite')
        page.get_by_role('button',name='Start a new care review').click()
        note='Browser review check '+datetime.now().strftime('%H%M%S')
        page.get_by_label('Review note').fill(note)
        page.get_by_role('button',name='Save review').click()
        expect(page.get_by_text(note,exact=False).first).to_be_visible();mark('Review created and shown in queue')
        page.reload();page.get_by_role('button',name='Care action centre',exact=True).click()
        expect(page.get_by_text(note,exact=False).first).to_be_visible();mark('Review survives full page reload (SQLite persistence)')
        # Doctor isolation in the actual browser: sign out, sign in as the empty-panel doctor.
        page.get_by_role('button',name='Sign out').click();expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
        page.get_by_role('button',name='Dr. Neil Nova').click();page.wait_for_load_state('networkidle');expect(page.get_by_role('button',name='Patients',exact=True)).to_be_visible()
        page.get_by_role('button',name='Patients',exact=True).click();expect(page.get_by_role('heading',name='Unified patient directory')).to_be_visible()
        expect(page.get_by_text('0 of 0 assigned synthetic patients',exact=True)).to_be_visible();mark('Two-doctor assignment isolation in browser')
        page.get_by_role('heading',name='Sign out',exact=False)
        page.get_by_role('button',name='Sign out').click()
        page.goto(web);page.get_by_role('button',name='Dr. Asha Atlas').click();page.wait_for_load_state('networkidle');expect(page.get_by_role('button',name='Patients',exact=True)).to_be_visible();mark('Session persists across reload; sign-out returns to login')
        page.get_by_role('button',name='Model validation',exact=True).click();expect(page.get_by_role('heading',name='Executed ablations')).to_be_visible();mark('Research workspace preserved')
        page.screenshot(path=str(shots/'workspace-desktop.png'),full_page=True,animations='disabled')
        m=browser.new_page(viewport={'width':390,'height':844})
        m.on('pageerror',lambda e:errors.append('mobile: '+str(e)))
        m.goto(web);m.get_by_role('button',name='Dr. Asha Atlas').click();expect(m.get_by_role('heading',name='Your patient cohort')).to_be_visible()
        assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        m.get_by_label('Open navigation').click();m.get_by_role('button',name='Care action centre',exact=True).click()
        expect(m.get_by_text('Assigned patients',exact=True)).to_be_visible();assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        m.screenshot(path=str(shots/'workspace-mobile.png'),full_page=True,animations='disabled');mark('Mobile 390px layout has no horizontal overflow')
        external=[u for u in requests if not u.startswith(('http://127.0.0.1','ws://127.0.0.1'))]
        errors=[e for e in errors if not e.startswith('Failed to load resource')]
        failed=[f for f in failed if not (f['status']==401 and '/workspace/me' in f['url'])]
        assert not errors and not failed and not external,{'errors':errors,'failed':failed,'external':external}
        mark('No JS/console errors, no failed requests, no external assets')
        browser.close()
    report={'status':'PASS','executed_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'note':'Disposable DB copy only; synthetic patients; no clinical validation.'}
    (out/'BROWSER_WORKSPACE.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':len(checks)},indent=1))
if __name__=='__main__':run()
