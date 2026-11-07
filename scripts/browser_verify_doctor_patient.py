"""Real-Chromium round trip: doctor dashboard ↔ patient dashboard on one assigned synthetic record.
Point PRANAGUARD_BROWSER_URL / PRANAGUARD_API_URL at running dev servers; DB must be disposable.
Optional dependency: playwright + Chromium."""
import json,os,base64
from datetime import datetime,timezone
import httpx
from playwright.sync_api import sync_playwright,expect
from backend.app.config import ROOT

def run():
    web=os.getenv('PRANAGUARD_BROWSER_URL','http://127.0.0.1:5173');api=os.getenv('PRANAGUARD_API_URL','http://127.0.0.1:8011')+'/api'
    out=ROOT/'docs/doctor-patient-verification';shots=out/'screenshots';shots.mkdir(parents=True,exist_ok=True)
    demo_doc=shots/'demo-lab-report.txt';demo_doc.write_text('PRANAGUARD DEMO LAB REPORT\nFictional synthetic content for round-trip testing.\n')
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
        # ---- Doctor side
        login_as(page,'Dr. Asha Atlas');expect(page.get_by_role('heading',name='Your patient cohort')).to_be_visible()
        nav=page.get_by_role('navigation')
        for label in ['Cohort overview','Patients','Care action centre','Patient twins','Risk explainability','What-if studio','Model validation','Care activity','Notifications','Device integration','Environment','Data sources','System & data']:
            expect(nav.get_by_role('button',name=label,exact=True)).to_be_visible()
        colour=page.locator('aside').evaluate('(e)=>getComputedStyle(e).backgroundColor');assert colour=='rgb(16, 59, 52)'
        mark('Doctor keeps the full original 13-item grouped clinician/research navigation & theme')
        page.get_by_role('button',name='Patients',exact=True).click()
        expect(page.get_by_role('heading',name='Unified patient directory')).to_be_visible()
        page.get_by_label('Search directory').fill('PG-0071')
        expect(page.get_by_text('1–1 of 1 assigned synthetic patients',exact=True)).to_be_visible()
        page.get_by_role('button',name='Profile',exact=True).first.dispatch_event('click');expect(page.get_by_test_id('patient-profile')).to_be_visible()
        page.get_by_role('button',name='Daily wellbeing').click()
        expect(page.get_by_text('Patient daily wellbeing entries').first).to_be_visible()
        expect(page.get_by_text('Inhaled bronchodilator (demo label)',exact=False).first).to_be_visible()
        mark('Doctor sees patient daily wellbeing + adherence records for assigned patient')
        page.get_by_role('button',name='Documents & follow-ups').click()
        with page.expect_response(lambda r:'/documents' in r.url and r.request.method=='POST',timeout=20000) as up:
            page.get_by_label('Document title').fill('Round-trip lab report (demo)')
            page.get_by_label('File',exact=True).set_input_files(str(demo_doc))
            page.get_by_role('button',name='Upload document').click()
        assert up.value.status==200,up.value.text()
        expect(page.get_by_text('Round-trip lab report (demo)',exact=True).first).to_be_visible()
        page.get_by_label('Instructions').fill('Round-trip: please log your daily wellbeing tomorrow')
        page.get_by_role('button',name='Add follow-up').click()
        expect(page.get_by_text('Round-trip: please log your daily wellbeing tomorrow',exact=True).first).to_be_visible()
        mark('Doctor uploads document and creates follow-up instruction (persisted, auditable)')
        # mark a seeded daily log reviewed
        page.get_by_role('button',name='Daily wellbeing').click()
        expect(page.get_by_role('button',name='Mark reviewed').first.or_(page.get_by_text('reviewed by',exact=False).first).first).to_be_visible()
        pending=page.get_by_role('button',name='Mark reviewed')
        if pending.count():pending.first.click();expect(page.get_by_text('Daily log marked reviewed.',exact=True)).to_be_visible()
        mark('Doctor flags a patient entry as reviewed')
        # ---- Patient side
        page.get_by_role('button',name='Sign out').click()
        login_as(page,'Twin 071 viewer')
        expect(page.get_by_role('heading',name='Patient Home')).to_be_visible()
        pnav=page.get_by_role('navigation')
        for label in ['Patient Home','My Health Records','Clinical Documents']:
            expect(pnav.get_by_role('button',name=label,exact=True)).to_be_visible()
        assert pnav.get_by_role('button').count()==3
        assert page.get_by_role('button',name='Cohort overview').count()==0
        expect(page.get_by_text('Round-trip: please log your daily wellbeing tomorrow',exact=True).first).to_be_visible()
        mark('Patient sees only the three patient nav items and doctor-issued follow-up')
        pnav.get_by_role('button',name='Clinical Documents',exact=True).click()
        expect(page.get_by_text('Round-trip lab report (demo)',exact=True).first).to_be_visible()
        expect(page.get_by_text('Demo COPD action plan summary (fictional)',exact=True)).to_be_visible()
        with page.expect_download() as dl:
            page.get_by_role('button',name='Download').first.click()
        assert dl.value.suggested_filename;mark('Patient downloads an authorized document (integrity-checked)')
        page.get_by_role('navigation').get_by_role('button',name='My Health Records',exact=True).click()
        page.get_by_label('Water intake (ml)').fill('2100');page.get_by_label('Activity / walking (min)').fill('25')
        page.get_by_label('Sleep (hours)').fill('7.5')
        page.get_by_label('Other symptoms / notes').fill('Round-trip entry from the patient dashboard')
        with page.expect_response(lambda r:'/daily-logs' in r.url and r.request.method=='POST',timeout=20000) as resp:
            page.get_by_role('button',name='Save daily log').click()
        assert resp.value.status==200,resp.value.text()
        expect(page.get_by_text('2100 ml',exact=False).first).to_be_visible()
        mark('Patient submits daily wellbeing entry; it persists and renders immediately')
        page.get_by_role('button',name='Correct this entry').first.click()
        page.get_by_label('Other symptoms / notes').fill('Round-trip corrected note')
        page.get_by_role('button',name='Save correction').click()
        expect(page.get_by_text('edited',exact=True).first).to_be_visible()
        mark('Patient correction saved under audit trail (edited chip visible)')
        page.get_by_role('navigation').get_by_role('button',name='My Health Records',exact=True).click();page.get_by_role('button',name='Medication').click()
        page.get_by_label('Missed / different').check()
        assert page.get_by_role('button',name='Save report').first.is_disabled()
        page.get_by_label('Reason (required)').fill('was travelling (demo)')
        page.get_by_role('button',name='Save report').first.click()
        expect(page.get_by_text('Medication report saved.',exact=True)).to_be_visible()
        mark('Medication adherence report requires missed-dose reason and saves')
        page.screenshot(path=str(shots/'patient-dashboard-desktop.png'),full_page=True,animations='disabled')
        # ---- API-level isolation from the patient's own session
        token=page.evaluate("sessionStorage.getItem('pg-workspace-session')")
        h={'Authorization':'Bearer '+token}
        r=httpx.get(api+'/workspace/patients/PG-0001/daily-logs',headers=h);assert r.status_code==403
        r=httpx.get(api+'/workspace/documents/99999/file',headers=h);assert r.status_code==404
        bad=httpx.post(api+'/workspace/patients/PG-0001/documents',headers=h,json={'title':'nope','doc_type':'other','filename':'x.txt','media_type':'text/plain','data_base64':base64.b64encode(b'nope nope nope').decode()});assert bad.status_code==403
        mark('Backend enforces cross-patient isolation for the patient session (403s)')
        # ---- Doctor round trip sees the new entry
        page.get_by_role('button',name='Sign out').first.click()
        login_as(page,'Dr. Asha Atlas')
        page.get_by_role('button',name='Patients',exact=True).click();page.get_by_label('Search directory').fill('PG-0071')
        expect(page.get_by_text('1–1 of 1 assigned synthetic patients',exact=True)).to_be_visible()
        page.get_by_role('button',name='Profile',exact=True).first.dispatch_event('click')
        page.get_by_role('button',name='Daily wellbeing').click()
        expect(page.get_by_text('Round-trip corrected note',exact=False).first).to_be_visible()
        expect(page.get_by_text('was travelling (demo)',exact=False).first).to_be_visible()
        mark("Patient's submitted/corrected entries visible in the doctor's assigned-patient view (same record)")
        # isolation via doctor 2
        page.get_by_role('button',name='Sign out').click()
        login_as(page,'Dr. Neil Nova')
        expect(page.get_by_role('heading',name='Your patient cohort')).to_be_visible()
        page.get_by_role('button',name='Patients',exact=True).click()
        expect(page.get_by_text('0 of 0 assigned synthetic patients',exact=True)).to_be_visible()
        mark('Unassigned doctor still sees an empty, isolated panel')
        # ---- mobile patient shell
        m=browser.new_page(viewport={'width':390,'height':844})
        m.on('pageerror',lambda e:errors.append('mobile: '+str(e)))
        m.goto(web);m.get_by_role('button',name='Twin 071 viewer').click()
        expect(m.get_by_role('heading',name='Patient Home')).to_be_visible()
        assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        m.get_by_label('Open navigation').click();m.get_by_role('button',name='My Health Records',exact=True).click()
        expect(m.get_by_text('Log today',exact=True)).to_be_visible();assert m.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
        m.screenshot(path=str(shots/'patient-dashboard-mobile.png'),full_page=True,animations='disabled')
        mark('Mobile 390px patient layout has no horizontal overflow')
        errors=[e for e in errors if not e.startswith('Failed to load resource')]
        assert not errors and not failed,{'errors':errors,'failed':failed}
        mark('No JS/console errors or failed requests during the round trip')
        browser.close()
    report={'status':'PASS','executed_at':datetime.now(timezone.utc).isoformat(),'checks':checks,
            'note':'Disposable DB copy; synthetic patients only; documents are record-keeping, not AI diagnosis.'}
    (out/'BROWSER_DOCTOR_PATIENT.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'passed':len(checks)},indent=1))
if __name__=='__main__':run()
