"""Read-only offline fallback verification against an already-running backend.
Requires live environment requests disabled and an empty current-context cache.
Never invokes reset, replay advancement, registration or notification mutations.
"""
import hashlib,json,os,sqlite3
from datetime import datetime,timezone
import httpx
from playwright.sync_api import sync_playwright,expect
from backend.app.config import ROOT,DB_PATH
from backend.app.enhanced.environment import AIR_FIELDS,WEATHER_FIELDS
from backend.app.enhanced.settings import CITIES

def run():
    api=os.getenv('PRANAGUARD_API_URL','http://127.0.0.1:8000')+'/api'
    web=os.getenv('PRANAGUARD_FRONTEND_URL','http://127.0.0.1:5173')
    out=ROOT/'docs/enhanced/verification';shots=ROOT/'docs/enhanced/screenshots';out.mkdir(parents=True,exist_ok=True);shots.mkdir(parents=True,exist_ok=True)
    baseline=json.loads((ROOT/'docs/enhanced/BASELINE_MANIFEST.json').read_text());manifest=json.loads((ROOT/'data/environment/manifest.json').read_text())
    def tables():
        with sqlite3.connect('file:'+str(DB_PATH)+'?mode=ro',uri=True) as c:
            return {t:{'rows':len(rows),'content_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()} for t in baseline['database_before'] for rows in [[tuple(r) for r in c.execute(f'SELECT * FROM {t} ORDER BY rowid')]]}
    before=tables();assert before==baseline['database_before'],'Use the preserved cohort database for this read-only check.'
    results=[]
    with httpx.Client(timeout=20) as client:
        registry=client.get(api+'/enhanced/registry/patients').json();assert registry['total']==120
        for city in ['Pune','Mumbai','Delhi','Bengaluru']:
            response=client.get(api+'/enhanced/environment/'+city);response.raise_for_status();data=response.json();assert data['live_requests_enabled'] is False
            components={}
            for kind,component in data['components'].items():
                assert component['status']=='historical_fallback' and component['historical'] is True
                assert component['source_type']=='modelled_historical_cache' and component['freshness']=='historical'
                assert component['used_by_frozen_model'] is False and component['context_only'] is True
                source=next(s for s in manifest['sources'] if s['city']==city and s['kind']==kind);blob=(ROOT/'data/environment'/source['file']).read_bytes();assert hashlib.sha256(blob).hexdigest()==source['sha256']
                raw=json.loads(blob);hourly=raw['hourly'];index=len(hourly['time'])-1
                expected={key:hourly[key][index] if key in hourly else None for key in (AIR_FIELDS if kind=='air' else WEATHER_FIELDS)}
                valid=datetime.fromisoformat(hourly['time'][index]).replace(tzinfo=timezone.utc).isoformat()
                assert component['values']==expected and component['valid_at']==valid and component['retrieved_at']==source['retrieved_at']
                assert all(m['missing']==(m['value'] is None) for m in component['metrics'])
                components[kind]={'status':component['status'],'original_valid_at':valid,'original_retrieved_at':component['retrieved_at'],'missing_keys':[k for k,v in expected.items() if v is None],'original_values_preserved':True}
            assert data['components']['air']['values']['us_aqi'] is None
            for key in ['weather_code','wind_speed_10m','wind_direction_10m']:assert data['components']['weather']['values'][key] is None
            (out/f'offline-context-{city.lower()}.json').write_text(json.dumps(data,indent=2));results.append({'city':city,'http_status':response.status_code,'components':components})
    errors=[];requests=[];failed=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda error:errors.append(str(error)));page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
        page.on('request',lambda request:requests.append(request.url));page.on('response',lambda r:failed.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        page.goto(web+'/#environment');expect(page.get_by_role('heading',name='Environmental context',exact=True)).to_be_visible()
        for city in ['Pune','Mumbai','Delhi','Bengaluru']:
            page.get_by_label('Context city',exact=True).select_option(city);expect(page.get_by_role('heading',name=city+' · '+CITIES[city]['state'],exact=True)).to_be_visible()
            expect(page.get_by_text('Historical fallback',exact=True)).to_have_count(2)
            expect(page.get_by_text('Modelled historical cache',exact=True)).to_have_count(2)
            expect(page.get_by_text('Provider weather description: Not available in this source',exact=True)).to_be_visible()
            expect(page.locator('.pgx-reading strong').filter(has_text='—')).to_have_count(4)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(shots/f'offline-{city.lower()}.png'),full_page=True,animations='disabled')
        browser.close()
    assert not errors and not failed,(errors,failed)
    assert all(url.startswith(web.replace('http://','ws://')) or url.startswith(web) for url in requests),requests
    after=tables();assert after==before==baseline['database_before']
    report={'executed_at':datetime.now(timezone.utc).isoformat(),'status':'PASS','read_only_no_reset':True,'results':results,'four_missing_metrics_per_city_remain_null':True,'browser_cities_verified':4,'browser_errors':errors,'failed_browser_requests':failed,'external_browser_requests':[],'original_database_tables_unchanged':after,'patient_count':120,'original_states':3000}
    (out/'OFFLINE_FALLBACK_VERIFICATION.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':run()
