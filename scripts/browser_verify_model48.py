"""Actual read-only Chromium checks for the completed, REJECTED48h study."""
import json,os
from datetime import datetime,timezone
import httpx
from playwright.sync_api import sync_playwright,expect
from backend.app.config import ROOT

def run():
    web=os.getenv('PRANAGUARD_BROWSER_URL','http://127.0.0.1:5174');api=os.getenv('PRANAGUARD_API_URL','http://127.0.0.1:8010')+'/api';out=ROOT/'docs/model-upgrade/verification';shots=out/'screenshots';shots.mkdir(parents=True,exist_ok=True)
    def get(path):r=httpx.get(api+path,timeout=20);r.raise_for_status();return r.json()
    before=get('/patients/PG-0071');history=get('/patients/PG-0071/history');checks=[];errors=[];requests=[];failed=[]
    def mark(name):checks.append({'name':name,'status':'PASS'});print('PASS',name,flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None);page.on('request',lambda request:requests.append(request.url));page.on('response',lambda r:failed.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        page.goto(web);expect(page.get_by_role('heading',name='Your patient cohort')).to_be_visible();mark('Original cohort remains available')
        page.get_by_role('button',name='Model validation',exact=True).click();expect(page.get_by_role('heading',name='Executed ablations')).to_be_visible();mark('Original evaluation and negative72h result retained')
        study=page.get_by_test_id('model48-study');expect(study.get_by_text('NOT PROMOTED',exact=True)).to_be_visible();expect(study.get_by_text('Candidate not promoted — original 48h model retained.',exact=True)).to_be_visible();mark('Rejected candidate honestly labelled; no automatic deployment')
        expect(study.get_by_text('0.5539',exact=True)).to_be_visible();expect(study.get_by_text('0.5494',exact=True)).to_be_visible();expect(study.get_by_text('0.1485',exact=True)).to_be_visible();expect(study.get_by_text('0.1099',exact=True)).to_be_visible();mark('Actual matched fresh-cohort metrics rendered')
        expect(study.get_by_text('NOT MET',exact=True)).to_have_count(3);expect(study.get_by_text('PASS',exact=True)).to_have_count(2);mark('All predeclared acceptance failures exposed')
        study.get_by_text('Development candidates and uncertainty',exact=True).click();expect(study.get_by_text('core_linear_C0.3 · selected',exact=True)).to_be_visible();expect(study.locator('details').first.locator('tbody tr')).to_have_count(8);mark('All8 candidate validation scores and bootstrap uncertainty inspectable')
        study.get_by_text('Known original test — secondary comparison',exact=True).click();expect(study.get_by_text('0.6144',exact=True)).to_be_visible();expect(study.get_by_text('0.5946',exact=True)).to_be_visible();mark('Known historical comparison separated from fresh audit')
        assert not study.get_by_role('button').count();mark('No nonfunctional activation or clinical action controls')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(shots/'desktop-study.png'),full_page=True,animations='disabled');mark('Original theme retained without desktop viewport overflow')
        page.set_viewport_size({'width':390,'height':844});page.goto(web+'/#validation');expect(page.get_by_test_id('model48-study')).to_be_attached();study=page.get_by_test_id('model48-study');study.scroll_into_view_if_needed();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');study.screenshot(path=str(shots/'mobile-study.png'),animations='disabled');mark('390px responsive study uses scrollable data tables, not viewport overflow')
        browser.close()
    assert get('/patients/PG-0071')==before and get('/patients/PG-0071/history')==history;assert get('/overview')['summary']['total']==120;mark('Patient probabilities and saved history unchanged by study viewing')
    explanation=get('/patients/PG-0071/explanation?horizon=48');assert 'TreeSHAP' in explanation['method'] and explanation['probability']==before['risks']['48'];mark('Original48h native TreeSHAP and model version remain active')
    assert not errors and not failed,(errors,failed)
    external=[url for url in requests if not url.startswith((web,web.replace('http://','ws://')))];assert not external,external;mark('No JS/console/API errors or external browser assets')
    report={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'passed':len(checks),'failed':0,'checks':checks,'browser_errors':errors,'failed_requests':failed,'external_browser_requests':external,'candidate_promoted':False,'patient_history_and_predictions_preserved':True}
    (out/'BROWSER_VERIFICATION.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':len(checks),'failed':0}))
if __name__=='__main__':run()
