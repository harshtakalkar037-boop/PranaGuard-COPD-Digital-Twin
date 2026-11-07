"""v6 browser round trip: doctor risk visibility + patient insights in real Chromium.
Point PRANAGUARD_BROWSER_URL / PRANAGUARD_API_URL at running dev servers; DB must be disposable."""
import json,os
from playwright.sync_api import sync_playwright,expect
from backend.app.config import ROOT

def run():
    web=os.getenv('PRANAGUARD_BROWSER_URL','http://127.0.0.1:5173')
    out=ROOT/'docs/v6-verification';shots=out/'screenshots';shots.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];failed=[]
    def mark(name):checks.append({'name':name,'status':'PASS'});print('PASS',name,flush=True)
    def login_as(page,label):
        page.wait_for_timeout(600)
        if page.get_by_role('heading',name='Sign in',exact=True).count()==0:page.goto(web)
        expect(page.get_by_role('heading',name='Sign in',exact=True)).to_be_visible()
        page.get_by_role('button',name=label).click()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('response',lambda r:failed.append({'url':r.url,'status':r.status}) if r.status>=400 and '/workspace/me' not in r.url else None)

        # ---- Doctor: risk watchlist on care dashboard
        login_as(page,'Dr. Asha Atlas')
        page.get_by_role('button',name='Care action centre',exact=True).click()
        expect(page.get_by_role('heading',name='72-hour model risk watchlist (experimental)')).to_be_visible()
        expect(page.get_by_text('Experimental synthetic-data model estimate',exact=False).first).to_be_visible()
        page.screenshot(path=str(shots/'01-care-centre-watchlist.png'),full_page=False)
        mark('Doctor dashboard shows experimental 24/48/72-watchlist with honest disclaimer')

        # ---- Doctor: Model risk tab on patient profile
        page.get_by_role('button',name='Patients',exact=True).click()
        page.get_by_label('Search directory').fill('PG-0071')
        page.get_by_role('button',name='Profile',exact=True).first.dispatch_event('click')
        expect(page.get_by_test_id('patient-profile')).to_be_visible()
        page.get_by_role('button',name='Model risk',exact=True).click()
        expect(page.get_by_text('24h horizon')).to_be_visible()
        expect(page.get_by_text('48h horizon')).to_be_visible()
        expect(page.get_by_text('72h horizon')).to_be_visible()
        expect(page.get_by_text('pg-synthetic-v1').first).to_be_visible()
        expect(page.get_by_role('heading',name='Prediction history (timestamped captures)')).to_be_visible()
        page.get_by_role('button',name='Show model explanation (72h)').click()
        expect(page.get_by_role('heading',name='Feature contributions (72h)')).to_be_visible()
        expect(page.get_by_text('correlation, not causation',exact=False)).to_be_visible()
        page.screenshot(path=str(shots/'02-profile-model-risk.png'),full_page=True)
        mark('Patient profile Model-risk tab: 24/48/72 cards, timestamped history, engine explanation, disclaimers')

        # ---- Doctor: risk context inside a care review
        page.get_by_role('button',name='Care action centre',exact=True).click()
        page.wait_for_timeout(800)
        page.locator('.care-queue button.care-card').first.click()
        expect(page.get_by_text('Experimental model risk (context only)')).to_be_visible()
        page.screenshot(path=str(shots/'03-review-risk-context.png'))
        mark('Care review workspace embeds read-only model-risk context for the patient')

        # ---- Patient: home summary + insights
        page.get_by_role('button',name='Sign out').click()
        login_as(page,'Twin 071 viewer')
        expect(page.get_by_role('heading',name='Recent health summary')).to_be_visible()
        page.screenshot(path=str(shots/'04-patient-home-summary.png'))
        mark('Patient Home shows data-backed recent health summary lines')
        page.get_by_role('button',name='My Health Records').click()
        page.get_by_role('button',name='Insights',exact=True).click()
        expect(page.get_by_text('Breathlessness & cough',exact=True).first).to_be_visible()
        expect(page.get_by_text('Breathing-rate history')).to_be_visible()
        expect(page.get_by_text('Date range',exact=True).first).to_be_visible()
        expect(page.get_by_text('not wearable',exact=False).first).to_be_visible()
        page.screenshot(path=str(shots/'05-patient-insights.png'),full_page=True)
        mark('Patient insights tab renders record-backed graphs with honest replay labelling')

        # ---- Mobile overflow check on insights
        page.set_viewport_size({'width':390,'height':844})
        page.reload()
        page.get_by_role('button',name='Open navigation').click();page.get_by_role('button',name='My Health Records').click()
        page.get_by_role('button',name='Insights',exact=True).click()
        page.wait_for_timeout(900)
        overflow=page.evaluate('document.documentElement.scrollWidth>390')
        assert not overflow,'mobile horizontal overflow detected'
        page.screenshot(path=str(shots/'06-patient-insights-mobile.png'))
        mark('Mobile 390px insights layout has no horizontal overflow')

        assert not errors,[f'JS/console errors: {errors}']
        assert not failed,[f'Failed requests: {failed}']
        mark('No JS/console errors or failed requests during the v6 round trip')
        browser.close()
    out.mkdir(parents=True,exist_ok=True)
    (out/'V6_BROWSER_RESULTS.json').write_text(json.dumps({'passed':len(checks),'checks':checks},indent=1))
    print(json.dumps({'passed':len(checks)},indent=1))

if __name__=='__main__':run()
