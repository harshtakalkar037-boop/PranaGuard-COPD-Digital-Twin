"""Cache unmodified public API responses, exact URLs and checksums. Explicit opt-in network."""
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import httpx
from backend.app.config import DATA
SITES = {'Pune': (18.5204, 73.8567), 'Mumbai': (19.0760, 72.8777),
         'Delhi': (28.6139, 77.2090), 'Bengaluru': (12.9716, 77.5946)}

def fetch(start='2026-08-01', end='2026-09-29'):
    folder = DATA / 'environment'; folder.mkdir(parents=True, exist_ok=True)
    records=[]
    for city, (lat, lon) in SITES.items():
        for kind, url, hourly in [
            ('air', 'https://air-quality-api.open-meteo.com/v1/air-quality', 'pm2_5,pm10,nitrogen_dioxide,ozone'),
            ('weather', 'https://archive-api.open-meteo.com/v1/archive', 'temperature_2m,relative_humidity_2m')]:
            params={'latitude':lat,'longitude':lon,'start_date':start,'end_date':end,'hourly':hourly,'timezone':'UTC'}
            if kind == 'air': params['domains']='cams_global'
            response=httpx.get(url,params=params,timeout=60); response.raise_for_status()
            obj=response.json()
            if len(obj.get('hourly',{}).get('time',[])) < 720: raise ValueError('Insufficient hourly coverage')
            name=f'{city.lower()}_{kind}.json'; (folder/name).write_bytes(response.content)
            records.append({'city':city,'kind':kind,'file':name,'url':str(response.url),
                            'retrieved_at':datetime.now(timezone.utc).isoformat(),
                            'sha256':hashlib.sha256(response.content).hexdigest(),
                            'hours':len(obj['hourly']['time']), 'start':obj['hourly']['time'][0], 'end':obj['hourly']['time'][-1],
                            'source':'Open-Meteo / CAMS global atmospheric composition' if kind=='air' else 'Open-Meteo Historical Weather API',
                            'license':'CC BY 4.0', 'license_url':'https://creativecommons.org/licenses/by/4.0/',
                            'personal_exposure':False})
            print(f'Cached {city} {kind}: {records[-1]["hours"]} hours')
    manifest={'notice':'Ambient gridded model products, not personal exposure or ground truth. No clinical records.',
              'access':'No API key; non-commercial fair-use access. Commercial hosting requires appropriate plan.',
              'sources':records}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--start',default='2026-08-01'); p.add_argument('--end',default='2026-09-29'); a=p.parse_args(); fetch(a.start,a.end)
