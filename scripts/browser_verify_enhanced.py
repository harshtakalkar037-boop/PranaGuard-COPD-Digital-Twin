"""Actual Chromium + REST enhancement verification. Uses a throwaway verification DB.
Run against a separately configured backend, never an original user's database.
No external browser assets, fabricated provider responses or frontend fake readings.
"""
import json,os,traceback
from datetime import datetime,timezone
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect
from backend.app.config import ROOT
BASE=os.getenv('PRANAGUARD_BROWSER_URL','http://127.0.0.1:5173')
API=os.getenv('PRANAGUARD_API_URL','http://127.0.0.1:8000')+'/api'
OUT=ROOT/'docs/enhanced/verification';SHOTS=ROOT/'docs/enhanced/screenshots';FIXTURES=ROOT/'frontend/src/enhanced/__fixtures__'

def run():
    OUT.mkdir(parents=True,exist_ok=True);SHOTS.mkdir(parents=True,exist_ok=True);FIXTURES.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];console=[];failed_api=[];external=[];pid=None
    headers={'X-Demo-Token':os.environ['PRANAGUARD_ADMIN_TOKEN']} if os.getenv('PRANAGUARD_ADMIN_TOKEN') else {}
    def api(path,body=None):
        response=httpx.post(API+path,json=body,headers=headers,timeout=35) if body is not None else httpx.get(API+path,headers=headers,timeout=35)
        response.raise_for_status();return response.json()
    def mark(name,detail=''):checks.append({'name':name,'status':'PASS','detail':detail});print('PASS',name,flush=True)
    def fixture(name,data):(FIXTURES/name).write_text(json.dumps(data,indent=2))
    report={'executed_at':datetime.now(timezone.utc).isoformat(),'scope':'Actual browser and HTTP integration; no real patients/hardware; verification DB only'}
    try:
        assert api('/enhanced/email')['mode']=='disabled','Browser verification requires disabled email mode; never sends external mail.'
        original_id=api('/replay')['demo']['patient_id'];before=api('/patients/'+original_id);initial_registry=api('/enhanced/registry/patients')['total']
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1512,'height':1120},accept_downloads=True)
            if headers:context.add_init_script("sessionStorage.setItem('pg-demo-token',"+json.dumps(headers['X-Demo-Token'])+")")
            def block(route):
                url=route.request.url
                if not url.startswith((BASE,'data:','blob:')):external.append(url);route.abort()
                else:route.continue_()
            context.route('**/*',block);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
            page.on('response',lambda r:failed_api.append({'url':r.url,'status':r.status}) if '/api/' in r.url and r.status>=400 else None)
            def nav(name):page.locator('aside').get_by_role('button',name=name,exact=True).click()
            def shot(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(SHOTS/name),full_page=True,animations='disabled',style='.toast{visibility:hidden!important}')
            page.goto(BASE,wait_until='networkidle');expect(page.get_by_role('heading',name='Your patient cohort')).to_be_visible()
            theme=page.locator('aside').evaluate('(e)=>({background:getComputedStyle(e).backgroundColor,font:getComputedStyle(e).fontFamily})')
            nav('Patients');expect(page.get_by_role('heading',name='All synthetic patients')).to_be_visible();mark('Patient registry navigation and original cohort available')
            search=page.get_by_label('Search registry by patient ID');search.fill(original_id);expect(page.get_by_role('button',name='Open profile '+original_id)).to_be_visible();mark('ID search backed by registry API')
            search.fill('NO-SUCH-DEMO-ID');expect(page.get_by_text('No fictional patients match these registry filters.')).to_be_visible();mark('Patient registry empty state')
            search.fill('');page.get_by_role('button',name='Add fictional patient').click();expect(page.get_by_role('button',name='Save fictional patient')).to_be_disabled();mark('Explicit fictional-data confirmation required')
            page.get_by_label('Fictional alias',exact=True).fill('Atlas Workflow');page.get_by_label('Demo age (18–100)').fill('59');page.get_by_label('Demo sex attribute').select_option('Female');page.get_by_label('Demo city',exact=True).select_option('Pune')
            page.get_by_label('Manual reference SpO₂ (%)').fill('96');page.get_by_label('Manual reference heart rate (bpm)').fill('76');page.get_by_label('Manual reference respiratory rate').fill('18')
            page.get_by_label('Fictional COPD history',exact=True).fill('Fictional example history for software demonstration only.');page.get_by_label('Demo diagnosis information').fill('Demo information, not an established diagnosis.');page.get_by_label('Fictional medication / management context').fill('Fictional plan placeholder; no prescribing recommendation.')
            page.get_by_label('I confirm that all identity and health details entered here are fictional demo data.').check();shot('enhanced-01-registration.png')
            with page.expect_response(lambda r:r.url.endswith('/api/enhanced/registry/patients') and r.request.method=='POST') as response:page.get_by_role('button',name='Save fictional patient').click()
            result=response.value.json();assert response.value.status==200,result;pid=result['patient_id']
            expect(page.get_by_role('heading',name='Fictional demo · Atlas Workflow')).to_be_visible();expect(page.get_by_text('No 24/48/72h prediction is available for this registration.')).to_be_visible();assert api('/enhanced/registry/patients')['total']==initial_registry+1;mark('Validated fictional registration, server ID and SQLite persistence')
            expect(page.get_by_role('progressbar',name='Baseline collection progress')).to_have_attribute('aria-valuenow','0');assert api('/enhanced/registry/patients/'+pid)['baseline']['prediction_supported'] is False;mark('Manual baseline values do not bypass72h warm-up or fabricate predictions')
            with page.expect_download() as download:page.get_by_role('button',name='Export profile').click()
            dest=OUT/'exported-fictional-profile.json';download.value.save_as(str(dest));assert json.loads(dest.read_text())['profile']['patient_id']==pid;mark('Correct selected fictional-profile JSON export')
            page.get_by_label('Fictional symptom score (0–10)').fill('8');page.get_by_label('Fictional adherence (%)').fill('40');page.get_by_label('Fictional observation note',exact=True).fill('Fictional monitoring example only.');page.get_by_label('This observation is fictional demo data.').check();page.get_by_role('button',name='Save fictional observation').click();expect(page.get_by_text('Symptoms 8/10 · adherence 40%',exact=True)).to_be_visible();mark('Persistent manual symptoms/adherence and demo monitoring rule')
            page.get_by_label('Fictional review note',exact=True).fill('Reviewed fictional baseline. No clinical care was provided.');page.get_by_role('button',name='Save demo review',exact=True).click();expect(page.get_by_text('Reviewed fictional baseline. No clinical care was provided.',exact=True)).to_be_visible();mark('Profile review extends existing intervention ledger')
            page.get_by_role('button',name='Manage simulated devices').click();expect(page.get_by_label('Synthetic patient',exact=True)).to_have_value(pid)
            device_ids=[]
            for index,kind in enumerate(['pulse_oximeter','smartwatch','fitness_band','portable_spirometer']):
                page.get_by_label('Generic device type').select_option(kind);page.get_by_label('Optional fictional device label').fill('Atlas simulated '+kind);page.get_by_label('Simulation interval (seconds)').fill('2')
                with page.expect_response(lambda r:r.url.endswith('/api/enhanced/devices') and r.request.method=='POST') as response:page.get_by_role('button',name='Associate simulated device').click()
                device=response.value.json();did=device['id'];device_ids.append(did);assert device['status']=='disconnected'
                page.get_by_role('button',name='Start simulation '+did,exact=True).click()
                page.wait_for_function("n => document.querySelectorAll('table.pgx-table tbody tr').length>=n",arg=4 if index==0 else 2,timeout=15000)
                assert len(api('/enhanced/devices/'+did+'/readings')['readings']) >= (4 if index==0 else 2)
                expect(page.get_by_role('button',name='Stop simulation '+did,exact=True)).to_be_enabled()
                page.get_by_role('button',name='Stop simulation '+did,exact=True).click();expect(page.get_by_role('button',name='Start simulation '+did,exact=True)).to_be_enabled();mark('Actual backend simulation and ingestion: '+kind)
            all_devices=api('/enhanced/devices?patient_id='+pid);assert len(all_devices['devices'])==4 and all(not d['is_simulating'] for d in all_devices['devices']);mark('Explicit Start/Stop and all4 generic capability types')
            count=len(api('/enhanced/devices/'+device_ids[0]+'/readings')['readings']);page.wait_for_timeout(2300);assert len(api('/enhanced/devices/'+device_ids[0]+'/readings')['readings'])==count;mark('Stopped simulation does not create further readings')
            shot('enhanced-02-devices.png');page.get_by_role('button',name='Open patient profile',exact=True).click();expect(page.get_by_label('Simulated reading chart')).to_be_visible();assert page.locator('.recharts-line-curve').first.get_attribute('d');mark('Patient trends render actual persisted ingestion data')
            profile=api('/enhanced/registry/patients/'+pid);assert len(profile['latest_monitoring']['snapshot']['current'])==6 and profile['latest_monitoring']['snapshot']['model_predictions'] is None
            assert profile['baseline']['elapsed_hours']<72 and not profile['baseline']['prediction_supported'];mark('Monitoring state versions and missingness isolated from model outputs')
            old=profile['monitoring_versions'][-1]['version'];page.get_by_label('Monitoring version',exact=True).select_option(str(old));expect(page.locator('p').filter(has_text='Monitoring v'+str(old)+' · received')).to_be_visible();page.get_by_label('Monitoring version',exact=True).select_option('latest');mark('Persisted monitoring version selection')
            shot('enhanced-03-profile.png');page.reload(wait_until='networkidle');search=page.get_by_label('Search registry by patient ID');search.fill(pid);page.get_by_role('button',name='Open profile '+pid).click();expect(page.get_by_text('Reviewed fictional baseline. No clinical care was provided.',exact=True)).to_be_visible();mark('Registration, readings, observation and review survive browser reload')
            nav('Notifications');expect(page.get_by_role('heading',name='Notification centre',exact=True).last).to_be_visible();page.get_by_label('Notification patient filter').select_option(pid);page.get_by_label('Notification category filter').select_option('patient_monitoring');expect(page.get_by_text('Manual demo monitoring rule',exact=True)).to_be_visible();mark('Patient/category notification filtering')
            page.get_by_label('Notification patient filter').select_option('');page.get_by_label('Notification category filter').select_option('')
            with page.expect_response(lambda r:r.url.endswith('/api/enhanced/notifications/test') and r.request.method=='POST') as response:page.get_by_role('button',name='Create test notification').click()
            nid=response.value.json()['id'];expect(page.get_by_role('heading',name='Test notification · synthetic demo')).to_be_visible();page.get_by_role('button',name='Mark read',exact=True).click();mark('Demonstrable test notification and unread/read persistence')
            page.get_by_label('Demo review note (no real patient information)').fill('Synthetic review timeline demonstration.')
            for button,status in [('Acknowledge notification','acknowledged'),('Mark under review','under_review'),('Resolve notification','resolved'),('Close notification','closed')]:
                page.get_by_role('button',name=button,exact=True).click();page.wait_for_function("async a => (await (await fetch('/api/enhanced/notifications/'+a[0])).json()).status===a[1]",arg=[nid,status])
            n=api('/enhanced/notifications/'+str(nid));assert n['status']=='closed' and len(n['history'])>=6;mark('Active→acknowledged→under_review→resolved→closed with append-only history')
            outbox=api('/enhanced/email')['outbox']
            if outbox:
                age=(datetime.now(timezone.utc)-datetime.fromisoformat(outbox[0]['created_at'])).total_seconds()
                if age<31:page.wait_for_timeout((31-age)*1000)
            with page.expect_response(lambda r:r.url.endswith('/api/enhanced/email/test') and r.request.method=='POST') as email_response:page.get_by_role('button',name='Run demo email test',exact=True).click()
            assert email_response.value.status==200,email_response.value.text()
            expect(page.get_by_text('Not sent disabled',exact=True).first).to_be_visible();assert api('/enhanced/email')['outbox'][0]['status']=='not_sent_disabled';mark('Disabled email records honest not-sent status; no patient email')
            shot('enhanced-04-notifications.png');nav('Environment')
            for city in ['Pune','Mumbai','Delhi','Bengaluru']:
                page.get_by_label('Context city',exact=True).select_option(city);expect(page.get_by_role('heading',name=city+' · ',exact=False)).to_be_visible();expect(page.get_by_text('U.S. AQI, NOT Indian CPCB NAQI.',exact=False).first).to_be_visible();data=api('/enhanced/environment/'+city);assert all(c['source_type']=='modelled_external' for c in data['components'].values());mark('Actual/cached provider context and honest timestamps: '+city)
            page.get_by_label('Context city',exact=True).select_option('Pune');shot('enhanced-05-environment.png');nav('Data sources');expect(page.get_by_role('heading',name='Record-level source ledger')).to_be_visible();page.get_by_label('Provenance patient filter').select_option(pid);expect(page.get_by_text('Simulated device',exact=True).first).to_be_visible();mark('Dedicated record-level provenance/classification/missingness section')
            with page.expect_download() as download:page.get_by_role('button',name='Export provenance JSON',exact=True).click()
            dest=OUT/'exported-provenance.json';download.value.save_as(str(dest));provenance=json.loads(dest.read_text());assert provenance['no_real_patient_records'] and any(r['patient_id']==pid for r in provenance['records']);mark('Backend provenance JSON export contains selected patient records')
            shot('enhanced-06-provenance.png');assert api('/patients/'+original_id)==before;mark('Original model twin, probabilities, features and baseline unchanged after enhancements')
            assert page.locator('aside').evaluate('(e)=>({background:getComputedStyle(e).backgroundColor,font:getComputedStyle(e).fontFamily})')==theme;mark('Original sidebar theme/font retained across new sections')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');mark('Desktop new views have no viewport overflow')
            mobile=context.new_page();mobile.set_viewport_size({'width':390,'height':844});mobile.on('pageerror',lambda e:errors.append(str(e)));mobile.goto(BASE+'/#registry',wait_until='networkidle')
            def mobile_nav(name):mobile.get_by_role('button',name='Open navigation').click();mobile.locator('aside').get_by_role('button',name=name,exact=True).click();mobile.wait_for_function("() => document.querySelector('aside').getBoundingClientRect().right<=1")
            for name in ['Patients','Device integration','Environment','Notifications','Data sources']:
                mobile_nav(name);mobile.wait_for_load_state('networkidle')
                if name=='Patients':
                    mobile.get_by_label('Search registry by patient ID').fill(pid);mobile.get_by_role('button',name='Open profile '+pid).click();expect(mobile.get_by_role('heading',name='Fictional demo · Atlas Workflow')).to_be_visible()
                if name=='Device integration':expect(mobile.get_by_role('heading',name='Associate a generic simulated device')).to_be_visible()
                if name=='Data sources':mobile.get_by_label('Provenance patient filter').select_option(pid);mobile.get_by_label('Provenance category filter').select_option('simulated_device')
                assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),name;mark('390px responsive navigation/layout: '+name)
                mobile.screenshot(path=str(SHOTS/('enhanced-mobile-'+name.lower().replace(' ','-')+'.png')),full_page=True)
            assert not external,external;assert not errors,errors;assert not console,console;assert not failed_api,failed_api;mark('No external browser assets, JS/console errors or failed browser API calls')
            fixture('registry.json',api('/enhanced/registry/patients'));fixture('profile.json',api('/enhanced/registry/patients/'+pid));fixture('devices.json',api('/enhanced/devices?patient_id='+pid));fixture('device-readings.json',api('/enhanced/devices/'+device_ids[0]+'/readings'));fixture('cities.json',api('/enhanced/environment/cities'));fixture('environment.json',api('/enhanced/environment/Pune'));fixture('notifications.json',api('/enhanced/notifications'));fixture('notification-detail.json',api('/enhanced/notifications/'+str(nid)));fixture('email.json',api('/enhanced/email'));fixture('provenance.json',api('/enhanced/provenance?patient_id='+pid));fixture('CAPTURE_METADATA.json',{'source':'Actual local FastAPI responses captured after real browser verification; device samples are explicitly software simulations; external context was retrieved from actual provider APIs.','captured_at':datetime.now(timezone.utc).isoformat(),'fictional_patient_id':pid,'test_notification_id':nid})
            browser.close()
        report.update({'status':'PASS','passed':len(checks),'failed':0,'checks':checks,'browser_errors':errors,'console_errors':console,'failed_api':failed_api,'external_browser_requests':external,'fictional_patient_id':pid})
    except Exception as exc:
        report.update({'status':'FAIL','passed':len(checks),'failed':1,'checks':checks,'failure':str(exc),'traceback':traceback.format_exc(),'browser_errors':errors,'console_errors':console,'failed_api':failed_api});raise
    finally:(OUT/'ENHANCED_BROWSER_VERIFICATION.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'passed':len(checks),'failed':0}))

if __name__=='__main__':run()
