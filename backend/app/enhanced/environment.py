"""Independent current city context. Never imported by features.py or model inference."""
import asyncio,hashlib,json,math
from datetime import datetime,timezone,timedelta
from urllib.parse import urlencode
import httpx
from fastapi import HTTPException
from backend.app.config import DATA
from backend.app.enhanced.settings import CITIES,stamp,parse_stamp,utcnow

AIR_FIELDS={'pm2_5':('PM2.5','µg/m³'),'pm10':('PM10','µg/m³'),'nitrogen_dioxide':('NO₂','µg/m³'),'ozone':('O₃','µg/m³'),'us_aqi':('U.S. AQI','USAQI')}
WEATHER_FIELDS={'temperature_2m':('Temperature','°C'),'relative_humidity_2m':('Relative humidity','%'),'weather_code':('Weather code','WMO code'),'wind_speed_10m':('Wind speed','km/h'),'wind_direction_10m':('Wind direction','°')}
WEATHER_CODES={0:'Clear sky',1:'Mainly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Depositing rime fog',51:'Light drizzle',53:'Moderate drizzle',55:'Dense drizzle',56:'Light freezing drizzle',57:'Dense freezing drizzle',61:'Slight rain',63:'Moderate rain',65:'Heavy rain',66:'Light freezing rain',67:'Heavy freezing rain',71:'Slight snowfall',73:'Moderate snowfall',75:'Heavy snowfall',77:'Snow grains',80:'Slight rain showers',81:'Moderate rain showers',82:'Violent rain showers',85:'Slight snow showers',86:'Heavy snow showers',95:'Thunderstorm',96:'Thunderstorm with slight hail',99:'Thunderstorm with heavy hail'}

class Environment:
    def __init__(self,store,settings,notifications,cache_dir=None,transport=None):
        self.store=store;self.settings=settings;self.notifications=notifications;self.cache_dir=cache_dir or DATA/'environment';self.transport=transport
        self.locks={c:asyncio.Lock() for c in CITIES}
    @staticmethod
    def _date(s):
        d=datetime.fromisoformat(str(s).replace('Z','+00:00'))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
    def request(self,city,component):
        coords=CITIES[city];fields=AIR_FIELDS if component=='air' else WEATHER_FIELDS
        prefix='customer-' if self.settings.provider_key else ''
        host=f'{prefix}air-quality-api.open-meteo.com' if component=='air' else f'{prefix}api.open-meteo.com'
        base=f"https://{host}/v1/{'air-quality' if component=='air' else 'forecast'}"
        params={'latitude':coords['latitude'],'longitude':coords['longitude'],'current':','.join(fields),'timezone':'UTC'}
        if component=='air':params['domains']='cams_global'
        else:params['wind_speed_unit']='kmh'
        public_url=base+'?'+urlencode(params)
        if self.settings.provider_key:params['apikey']=self.settings.provider_key
        return base,params,public_url
    def _normalize(self,raw,city,component,retrieved):
        fields=AIR_FIELDS if component=='air' else WEATHER_FIELDS;current=raw.get('current');units=raw.get('current_units',{})
        if not isinstance(current,dict) or not current.get('time'):raise ValueError('Missing current provider observation.')
        valid=self._date(current['time']);age=(utcnow()-valid).total_seconds()
        if age<-7200:raise ValueError('Provider timestamp is implausibly far in the future.')
        values={}
        for key in fields:
            value=current.get(key)
            if value is not None and (not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value)):raise ValueError('Invalid provider numeric field.')
            if value is not None and key!='temperature_2m' and value<0:raise ValueError('Negative provider field.')
            if value is not None and key=='relative_humidity_2m' and value>100:raise ValueError('Invalid relative humidity.')
            if value is not None and key=='wind_direction_10m' and value>360:raise ValueError('Invalid wind direction.')
            if value is not None:
                reported=str(units.get(key,'')).replace('μ','µ').replace(' ','')
                expected=fields[key][1].replace(' ','')
                if reported.casefold()!=expected.casefold():raise ValueError('Unexpected/missing provider unit.')
            values[key]=value
        if not any(v is not None for v in values.values()):raise ValueError('Provider returned no supported values.')
        return {'values':values,'units':{k:units.get(k,fields[k][1]) for k in fields},'valid_at':valid.isoformat(),'retrieved_at':retrieved,'grid_latitude':raw.get('latitude'),'grid_longitude':raw.get('longitude'),'source_url':self.request(city,component)[2],'source':'Open-Meteo / CAMS global' if component=='air' else 'Open-Meteo weather models','source_type':'modelled_external','scope':'city_grid_not_personal','license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','historical':False}
    def historical(self,city,component):
        try:
            manifest=json.loads((self.cache_dir/'manifest.json').read_text())
            source=next(s for s in manifest['sources'] if s['city']==city and s['kind']==component)
            path=self.cache_dir/source['file'];blob=path.read_bytes()
            if hashlib.sha256(blob).hexdigest()!=source['sha256']:return None
            raw=json.loads(blob);hourly=raw['hourly'];idx=len(hourly['time'])-1;fields=AIR_FIELDS if component=='air' else WEATHER_FIELDS
            values={k:(hourly[k][idx] if k in hourly and len(hourly[k])>idx else None) for k in fields}
            return {'values':values,'units':{k:raw.get('hourly_units',{}).get(k,fields[k][1]) for k in fields},'valid_at':self._date(hourly['time'][idx]).isoformat(),'retrieved_at':source['retrieved_at'],'grid_latitude':raw.get('latitude'),'grid_longitude':raw.get('longitude'),'source_url':source['url'],'source':source['source'],'source_type':'modelled_historical_cache','scope':'city_grid_not_personal','license':source['license'],'license_url':source.get('license_url','https://creativecommons.org/licenses/by/4.0/'),'historical':True}
        except (OSError,KeyError,ValueError,StopIteration,IndexError):return None
    def _decorate(self,payload,city,component,status,error=None,attempted_at=None):
        fields=AIR_FIELDS if component=='air' else WEATHER_FIELDS
        if payload is None:
            payload={'values':{k:None for k in fields},'units':{k:spec[1] for k,spec in fields.items()},'valid_at':None,'retrieved_at':None,'source':'Unavailable','source_type':'missing','source_url':None,'scope':'city_grid_not_personal','historical':False}
        valid=payload.get('valid_at');retrieved=payload.get('retrieved_at')
        valid_age=max(0,(utcnow()-self._date(valid)).total_seconds()) if valid else None
        cache_age=max(0,(utcnow()-self._date(retrieved)).total_seconds()) if retrieved else None
        fresh=status in ('live','cached') and valid_age is not None and valid_age<=10800
        result={**payload,'city':city,'component':component,'status':status,'freshness':'fresh' if fresh else 'historical' if payload.get('historical') else 'stale' if valid else 'missing','valid_age_seconds':round(valid_age) if valid_age is not None else None,'cache_age_seconds':round(cache_age) if cache_age is not None else None,'last_error':error,'last_attempt_at':attempted_at,'context_only':True,'used_by_frozen_model':False}
        result['metrics']=[{'key':k,'label':label,'value':payload['values'].get(k),'unit':payload['units'].get(k,unit),'missing':payload['values'].get(k) is None,'source':payload['source'],'source_type':payload['source_type'],'valid_at':valid,'retrieved_at':retrieved,'freshness':result['freshness'],'scope':'city_grid_not_personal','patient_id':None,'context_only':True} for k,(label,unit) in fields.items()]
        if component=='weather':
            code=payload['values'].get('weather_code');result['weather_summary']=WEATHER_CODES.get(int(code),f'Provider WMO code {code}') if code is not None else 'Not available in this source'
        return result
    async def component(self,city,kind,refresh=False):
        s=self.settings
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM environment_cache WHERE city=? AND component=?',(city,kind)).fetchone()
            attempt=c.execute('SELECT * FROM environment_attempts WHERE city=? AND component=?',(city,kind)).fetchone()
        cached=json.loads(row['payload']) if row else None
        cache_fresh=bool(row and (utcnow()-parse_stamp(row['retrieved_at'])).total_seconds()<s.cache_ttl_seconds and (utcnow()-parse_stamp(row['valid_at'])).total_seconds()<10800)
        cooldown=bool(attempt and (parse_stamp(attempt['next_retry_at'])>utcnow() if attempt['next_retry_at'] else (utcnow()-parse_stamp(attempt['attempted_at'])).total_seconds()<s.retry_seconds))
        attempted=attempt['attempted_at'] if attempt else None;error=attempt['error'] if attempt else None
        if not s.environment_enabled:
            payload=cached or self.historical(city,kind)
            return self._decorate(payload,city,kind,'stale_cache' if cached else 'historical_fallback' if payload else 'unavailable','Current provider requests are disabled in backend configuration.',attempted)
        if (cache_fresh and not refresh) or cooldown:
            payload=cached or self.historical(city,kind)
            status='cached' if cache_fresh else 'stale_cache' if cached else 'historical_fallback' if payload else 'unavailable'
            return self._decorate(payload,city,kind,status,error,attempted)
        at=stamp()
        # Record before requesting. City lock prevents duplicate refreshes from concurrent pages.
        with self.store.connect() as c:c.execute('INSERT INTO environment_attempts(city,component,attempted_at,error,next_retry_at) VALUES (?,?,?,NULL,?) ON CONFLICT(city,component) DO UPDATE SET attempted_at=excluded.attempted_at,error=NULL,next_retry_at=excluded.next_retry_at',(city,kind,at,(utcnow()+timedelta(seconds=s.retry_seconds)).isoformat()))
        base,params,_=self.request(city,kind)
        try:
            async with httpx.AsyncClient(timeout=s.provider_timeout_seconds,transport=self.transport,follow_redirects=False) as client:
                response=await client.get(base,params=params);response.raise_for_status();payload=self._normalize(response.json(),city,kind,stamp())
            with self.store.connect() as c:
                c.execute('INSERT OR REPLACE INTO environment_cache(city,component,retrieved_at,valid_at,payload,last_attempt_at,last_error) VALUES (?,?,?,?,?,?,NULL)',(city,kind,payload['retrieved_at'],payload['valid_at'],json.dumps(payload,allow_nan=False),at))
            with self.store.connect() as c:c.execute('UPDATE environment_attempts SET consecutive_failures=0 WHERE city=? AND component=?',(city,kind))
            result=self._decorate(payload,city,kind,'live',None,at)
            if result['freshness']!='fresh':
                result['status']='stale_cache'
                self.notifications.create(category='data_quality',title=f'{city} {kind} provider timestamp is stale',reason='The provider returned a value more than 3 hours old. It is retained with its real timestamp, not presented as a fresh measurement.',source=payload['source'],source_type='system_demo',dedupe_key=f"env-stale:{city}:{kind}:{payload['valid_at']}",metadata={'city':city,'valid_at':payload['valid_at']})
            if kind=='air' and result['freshness']=='fresh':
                v=payload['values']
                if (v.get('pm2_5') is not None and v['pm2_5']>=35) or (v.get('us_aqi') is not None and v['us_aqi']>=100):
                    self.notifications.create(category='environment',title=f'{city} context matched a demo rule',reason='Modelled city PM2.5≥35µg/m³ or U.S.AQI≥100 matched an unvalidated demo rule. Not a CPCB Indian AQI, patient exposure estimate or clinical warning.',source=payload['source'],source_type='modelled_external',dedupe_key=f"env-rule:{city}:{payload['valid_at']}",metadata={'city':city,'valid_at':payload['valid_at'],'retrieved_at':payload['retrieved_at'],'context_only':True})
            return result
        except Exception as exc:
            # Never persist/log response URLs or bodies: a customer key may be in the URL.
            code=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None
            detail=f'Provider unavailable ({type(exc).__name__}'+(f', HTTP{code}' if code else '')+'). No current values fabricated.'
            with self.store.connect() as c:
                failures=(attempt['consecutive_failures'] if attempt else 0)+1
                delay=min(3600,s.retry_seconds*(2**min(failures-1,4)))
                if isinstance(exc,httpx.HTTPStatusError):
                    try:delay=max(delay,min(86400,max(0,int(exc.response.headers.get('Retry-After','0')))))
                    except ValueError:pass
                c.execute('UPDATE environment_attempts SET error=?,consecutive_failures=?,next_retry_at=? WHERE city=? AND component=?',(detail,failures,(utcnow()+timedelta(seconds=delay)).isoformat(),city,kind))
                if row:c.execute('UPDATE environment_cache SET last_attempt_at=?,last_error=? WHERE city=? AND component=?',(at,detail,city,kind))
            self.notifications.create(category='data_quality',title=f'{city} {kind} provider unavailable',reason=detail,source='Backend environmental retrieval',source_type='system_demo',dedupe_key=f'env-error:{city}:{kind}:{at[:13]}',metadata={'city':city,'component':kind,'historical_fallback_possible':True})
            payload=cached or self.historical(city,kind)
            return self._decorate(payload,city,kind,'stale_cache' if cached else 'historical_fallback' if payload else 'unavailable',detail,at)
    async def get(self,city,refresh=False):
        if city not in CITIES:raise HTTPException(422,'Unknown city; select a configured India city.')
        async with self.locks[city]:air,weather=await asyncio.gather(self.component(city,'air',refresh),self.component(city,'weather',refresh))
        with self.store.connect() as c:
            for name,result in [('air',air),('weather',weather)]:
                attempt=c.execute('SELECT next_retry_at,consecutive_failures FROM environment_attempts WHERE city=? AND component=?',(city,name)).fetchone()
                result['next_retry_at']=attempt['next_retry_at'] if attempt else None
                result['consecutive_failures']=attempt['consecutive_failures'] if attempt else 0
        return {'city':city,'location':CITIES[city],'components':{'air':air,'weather':weather},'metrics':air['metrics']+weather['metrics'],'live_requests_enabled':self.settings.environment_enabled,'attribution':'Open-Meteo; Copernicus Atmosphere Monitoring Service (CAMS) and weather model providers. Data: CC BY 4.0.','attribution_url':'https://open-meteo.com/','aqi_scale':'U.S. AQI, NOT Indian CPCB NAQI','scope':'City-centre gridded model context, not station observation or personal exposure.','model_boundary':'Context only. Never enters frozen ML features or changes historical predictions.','retrieval_policy':{'cache_ttl_seconds':self.settings.cache_ttl_seconds,'minimum_retry_seconds':self.settings.retry_seconds},'not_integrated':['CPCB/Data.gov.in station observations: access/terms not fully verified','IMD weather: API key required; not configured or integrated']}
