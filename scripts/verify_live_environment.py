"""Opt-in verification against a RUNNING backend with current context enabled.
Records actual live/cache/fallback states; never invents successful provider evidence.
"""
import json,os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import httpx
from backend.app.config import ROOT

def run():
    base=os.getenv('PRANAGUARD_API_URL','http://127.0.0.1:8000')+'/api/enhanced';out=ROOT/'docs/enhanced/verification';out.mkdir(parents=True,exist_ok=True)
    def fetch(city):
        response=httpx.get(base+'/environment/'+city,timeout=35);response.raise_for_status();data=response.json();(out/f'live-context-{city.lower()}.json').write_text(json.dumps(data,indent=2))
        return {'city':city,'http_status':response.status_code,'components':{key:{f:value.get(f) for f in ['status','source_type','valid_at','retrieved_at','last_error','next_retry_at']} for key,value in data['components'].items()}}
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,['Pune','Mumbai','Delhi','Bengaluru']))
    current=all(c['source_type']=='modelled_external' and c['status'] in ('live','cached') for record in records for c in record['components'].values())
    report={'executed_at':datetime.now(timezone.utc).isoformat(),'evidence_type':'Actual integrated backend live/cache results; no transport test doubles. Dated evidence, not production fallback.','status':'PASS' if current else 'FALLBACK_OR_UNAVAILABLE','results':records,'all_components_current_available':current,'all_components_live':all(c['status']=='live' for r in records for c in r['components'].values())}
    (out/'LIVE_PROVIDER_VERIFICATION.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':run()
