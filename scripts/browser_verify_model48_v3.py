"""Actual Chromium v3/legacy/offline regression; read-only on its API/SQLite.
Point PRANAGUARD_BROWSER_URL and PRANAGUARD_API_URL to the running app.
Optional verification dependency: playwright==1.56.0 and its Chromium browser.
"""
import json,os
from datetime import datetime,timezone
import httpx,numpy as np
from playwright.sync_api import sync_playwright,expect
from backend.app.config import ROOT

def run():
    web=os.getenv('PRANAGUARD_BROWSER_URL','http://127.0.0.1:5173');api=os.getenv('PRANAGUARD_API_URL','http://127.0.0.1:8011')+'/api';out=ROOT/'docs/model-v3/verification';shots=out/'screenshots';shots.mkdir(parents=True,exist_ok=True)
    def get(path):r=httpx.get(api+path,timeout=30);r.raise_for_status();return r.json()
    before=get('/patients/PG-0071');history=get('/patients/PG-0071/history');pred=get('/model48/v3/patients/PG-0071');expected=f'{pred["probability"]*100:.1f}%';checks=[];errors=[];failed=[];requests=[]
    def mark(name):checks.append({'name':name,'status':'PASS'});print('PASS',name,flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None);page.on('request',lambda r:requests.append(r.url));page.on('response',lambda r:failed.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        page.goto(web);expect(page.get_by_role('heading',name='Your patient cohort')).to_be_visible();assert get('/overview')['summary']['total']==120;mark('Original120-patient overview intact')
        theme=page.locator('aside').evaluate('(e)=>({background:getComputedStyle(e).backgroundColor,font:getComputedStyle(e).fontFamily})')
        page.get_by_role('button',name='Patient twins',exact=True).click();card=page.get_by_test_id('risk-card-48');expect(card.get_by_text('v3 · experimental synthetic model',exact=True)).to_be_visible();expect(card.get_by_text(expected,exact=True)).to_be_visible();mark('Patient48h card matches actual frozen v3 inference')
        for h in [24,72]:expect(page.get_by_test_id(f'risk-card-{h}').get_by_text('Original v1 calibrated model',exact=True)).to_be_visible()
        expect(card.get_by_text('Stored v1:',exact=False)).to_be_visible();expect(page.get_by_text('Original v1 only · v3 was not backfilled into saved history',exact=True)).to_be_visible();mark('Legacy horizons/stored48h/history clearly distinguished')
        page.screenshot(path=str(shots/'desktop-patient.png'),full_page=True,animations='disabled')
        page.get_by_label('Twin state version').select_option('1');expect(page.locator('.twin-banner-right').get_by_text('State v1',exact=False)).to_be_visible();expect(card.get_by_text('v3 · experimental synthetic model',exact=True)).to_be_visible();assert any('version=1' in url and '/model48/v3/patients/' in url for url in requests);mark('Saved-state selection requests the matching v3 version')
        page.get_by_label('Twin state version').select_option('current');expect(page.locator('.twin-banner-right').get_by_text('State v25',exact=False)).to_be_visible()
        page.get_by_role('button',name='Risk explainability',exact=True).click();expect(page.get_by_role('heading',name='Local model drivers',exact=True)).to_be_visible();page.get_by_role('button',name='48 hours',exact=True).click();ex=page.get_by_test_id('model48-v3-explanation');expect(ex.get_by_role('heading',name='v3 local model drivers',exact=True)).to_be_visible();expect(ex.get_by_text(expected,exact=True)).to_be_visible();mark('48h explanation uses v3, not old TreeSHAP')
        ex.get_by_text('All v3 inputs and exact explanation audit',exact=True).click();expect(ex.locator('tbody tr')).to_have_count(len(pred['explanation']['drivers']));e=pred['explanation'];assert np.isclose(e['base_value']+sum(d['contribution'] for d in e['drivers']),e['calibrated_margin'],atol=1e-12);assert np.isclose(1/(1+np.exp(-e['calibrated_margin'])),pred['probability'],atol=1e-12);mark('All feature provenance/imputation and exact calibrated log-odds audit inspectable')
        page.get_by_role('button',name='24 hours',exact=True).click();expect(page.get_by_text('24h calibrated risk',exact=True)).to_be_visible();page.get_by_role('button',name='72 hours',exact=True).click();expect(page.get_by_text('72h calibrated risk',exact=True)).to_be_visible();mark('24h/72h original explanations preserved')
        page.get_by_role('button',name='What-if studio',exact=True).click();expect(page.get_by_text('Scenario comparisons use original v1 models',exact=False)).to_be_visible();mark('Scenario model-version boundary explicit')
        page.get_by_role('button',name='Model validation',exact=True).click();expect(page.get_by_role('heading',name='Executed ablations')).to_be_visible();expect(page.get_by_text('0.3951',exact=True).first).to_be_visible();mark('Original negative72h evidence retained')
        study=page.get_by_test_id('model48-v3-study');expect(study.get_by_text('SYNTHETIC GATES PASSED',exact=True)).to_be_visible();table=study.get_by_role('table',name='Fresh v3 48h comparison');expect(table.get_by_text('0.5986',exact=True)).to_be_visible();expect(table.get_by_text('0.5579',exact=True)).to_be_visible();expect(study.get_by_text('PASS',exact=True)).to_have_count(5);mark('Fresh audit metrics and all five unchanged gates rendered')
        study.get_by_text('v3 development, uncertainty and earlier test',exact=True).click();expect(study.get_by_text('tree_context15 · selected',exact=True)).to_be_visible();expect(study.get_by_text('AUROC interval crosses zero.',exact=False)).to_be_visible();mark('All six candidates, uncertainty and known-test limitation inspectable')
        # Capture only the latest evidence panel, not a huge duplicate historical page.
        study.screenshot(path=str(shots/'desktop-v3-study.png'),animations='disabled')
        page.get_by_text('Previous failed v2 study — historical evidence',exact=True).click();prior=page.get_by_test_id('model48-study');expect(prior.get_by_text('NOT PROMOTED',exact=True)).to_be_visible();expect(prior.get_by_text('0.1099',exact=True)).to_be_visible();mark('Earlier v2 failure stays visible and rejected')
        assert theme==page.locator('aside').evaluate('(e)=>({background:getComputedStyle(e).backgroundColor,font:getComputedStyle(e).fontFamily})');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');mark('Existing theme/font/layout preserved without desktop overflow')
        page.get_by_role('button',name='Patients',exact=True).click();expect(page.get_by_role('heading',name='All synthetic patients',exact=True)).to_be_visible();page.get_by_role('button',name='Device integration',exact=True).click();page.get_by_label('Synthetic patient',exact=True).select_option('PG-0071');expect(page.get_by_role('heading',name='Associate a generic simulated device',exact=True)).to_be_visible();mark('Registry and simulated-device sections remain reachable')
        page.get_by_role('button',name='Environment',exact=True).click();expect(page.get_by_role('heading',name='Environmental context',exact=True)).to_be_visible()
        for city in ['Pune','Mumbai','Delhi','Bengaluru']:
            page.get_by_label('Context city',exact=True).select_option(city);expect(page.get_by_text('Historical fallback',exact=True)).to_have_count(2)
        mark('Four-city offline fallback remains separate from model inputs')
        page.set_viewport_size({'width':390,'height':844});page.goto(web+'/#patient');expect(page.get_by_test_id('risk-card-48').get_by_text('v3 · experimental synthetic model',exact=True)).to_be_visible();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(shots/'mobile-patient.png'),full_page=True,animations='disabled');mark('390px patient cards/version labels have no viewport overflow')
        page.goto(web+'/#validation');study=page.get_by_test_id('model48-v3-study');expect(study).to_be_attached();study.scroll_into_view_if_needed();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');study.screenshot(path=str(shots/'mobile-v3-study.png'),animations='disabled');mark('390px study tables scroll within the original layout')
        browser.close()
    assert get('/patients/PG-0071')==before and get('/patients/PG-0071/history')==history;mark('Viewing v3 never mutates persisted v1 predictions/history')
    assert not errors and not failed,(errors,failed);external=[url for url in requests if not url.startswith((web,web.replace('http://','ws://')))];assert not external,external;mark('No JS/console/API failures or external browser assets')
    report={'status':'PASS','created_at':datetime.now(timezone.utc).isoformat(),'passed':len(checks),'failed':0,'checks':checks,'browser_errors':errors,'failed_requests':failed,'external_browser_requests':external,'legacy_probabilities_and_history_unchanged':True,'clinical_validation':False};(out/'BROWSER.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':len(checks),'failed':0}))
if __name__=='__main__':run()
