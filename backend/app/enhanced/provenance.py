"""Record-level provenance with explicit absence of real clinical/device observations."""
import json
from backend.app.enhanced.settings import METRICS,stamp,parse_stamp,utcnow

HISTORICAL_UNITS={'spo2':'%','heart_rate':'bpm','resp_rate':'breaths/min','symptom_score':'score 0–10','steps':'steps/hour','sleep_hours':'hours','adherence':'fraction 0–1','pm25':'µg/m³','pm10':'µg/m³','no2':'µg/m³','ozone':'µg/m³','temperature':'°C','humidity':'%'}
ENV_KEYS={'pm25','pm10','no2','ozone','temperature','humidity'}

async def provenance(s,patient_id=None,city='Pune'):
    if patient_id:s.registry.require(patient_id)
    env=await s.environment.get(city);records=[]
    with s.store.connect() as c:
        params=(patient_id,) if patient_id else ();where=' WHERE patient_id=?' if patient_id else ''
        for row in c.execute('SELECT * FROM device_readings'+where+' ORDER BY id DESC LIMIT 100',params):
            d=dict(row);records.append({'record_id':'reading:'+str(d['id']),'category':'simulated_device','field':d['metric'],'value':d['value'],'unit':d['unit'],'patient_id':d['patient_id'],'source':d['device_id'],'source_type':'simulated_device','valid_at':d['observed_at'],'retrieved_at':d['received_at'],'freshness':'recent' if (utcnow()-parse_stamp(d['observed_at'])).total_seconds()<=60 else 'stale','missing':False,'used_by_frozen_model':False})
        for row in c.execute('SELECT * FROM demo_observations'+where+' ORDER BY id DESC LIMIT 20',params):
            for key,unit in [('symptom_score','score 0–10'),('adherence','fraction 0–1')]:records.append({'record_id':f"manual:{row['id']}:{key}",'category':'manual_demo','field':key,'value':row[key],'unit':unit,'patient_id':row['patient_id'],'source':'Manual fictional observation','source_type':'manual_demo','valid_at':row['created_at'],'retrieved_at':row['created_at'],'freshness':'manual_demo_timestamp','missing':False,'used_by_frozen_model':False})
        regs=c.execute('SELECT * FROM registrations'+where+' ORDER BY created_at DESC LIMIT 10',params).fetchall()
        for row in regs:
            data=json.loads(row['details'])
            for key,unit in [('age','years'),('sex','category'),('baseline_spo2','%'),('baseline_heart_rate','bpm'),('baseline_resp_rate','breaths/min'),('fev1_pct','% predicted'),('bmi','kg/m²')]:records.append({'record_id':f"registration:{row['patient_id']}:{key}",'category':'manual_demo','field':key,'value':data.get(key),'unit':unit,'patient_id':row['patient_id'],'source':'Fictional registration / manual reference','source_type':'manual_demo','valid_at':row['created_at'],'retrieved_at':row['created_at'],'freshness':'manual_reference_not_observed_baseline','missing':data.get(key) is None,'used_by_frozen_model':False})
        counts={t:c.execute('SELECT COUNT(*) AS n FROM '+t).fetchone()['n'] for t in ('patients','states','registrations','device_readings','notifications')}
    if patient_id and patient_id in s.engine.profiles:
        state=s.engine.patient(patient_id)
        for key,value in state['current'].items():
            external=key in ENV_KEYS
            records.append({'record_id':f"historical:{patient_id}:v{state['version']}:{key}",'category':'historical_environment' if external else 'synthetic_cohort','field':key,'value':value,'unit':HISTORICAL_UNITS.get(key,'not specified'),'patient_id':patient_id,'source':state['data_sources']['environment'] if external else 'Frozen synthetic longitudinal replay','source_type':'modelled_historical_cache' if external else 'synthetic_cohort','valid_at':state['timestamp'],'retrieved_at':None,'freshness':'historical_replay_clock_only','missing':value is None,'used_by_frozen_model':True})
        for horizon,value in state['risks'].items():records.append({'record_id':f"model:{patient_id}:v{state['version']}:{horizon}",'category':'model_output','field':f'risk_{horizon}h','value':value,'unit':'calibrated experimental probability','patient_id':patient_id,'source':state['model_version'],'source_type':'synthetic_model','valid_at':state['timestamp'],'retrieved_at':None,'freshness':'historical_replay_clock_only','missing':False,'used_by_frozen_model':False})
    for metric in env['metrics']:
        records.append({'record_id':f"environment:{city}:{metric['key']}:{metric['valid_at']}",'category':'current_environment' if metric['source_type']=='modelled_external' else 'historical_environment','field':metric['key'],'value':metric['value'],'unit':metric['unit'],'patient_id':None,'source':metric['source'],'source_type':metric['source_type'],'valid_at':metric['valid_at'],'retrieved_at':metric['retrieved_at'],'freshness':metric['freshness'],'missing':metric['missing'],'used_by_frozen_model':False})
    return {'generated_at':stamp(),'categories':[
        {'id':'synthetic_cohort','label':'Synthetic patient physiology / outcomes','classification':'synthetic','status':'implemented_frozen','description':'Original 120 fictional patients and 172800 historical hourly rows; no real clinical records.'},
        {'id':'manual_demo','label':'Manually entered fictional profiles / observations','classification':'synthetic_manual','status':'implemented','description':'Explicitly confirmed fictional references; not clinical diagnosis or72-hour baseline observations.'},
        {'id':'simulated_device','label':'Generic simulated device stream','classification':'simulated','status':'implemented','description':'Backend-generated readings pass through authenticated ingestion; no physical hardware connected.'},
        {'id':'current_environment','label':'Open-Meteo / CAMS current city context','classification':'modelled_external','status':'external_optional','description':'Actual provider requests, cached with source/valid/retrieved timestamps; not station/personal exposure and never a new frozen-model input.'},
        {'id':'historical_environment','label':'Historical licensed city caches','classification':'modelled_historical','status':'implemented_frozen','description':'Original cached provider values with2026 coverage; explicitly stale as current context.'},
        {'id':'model_output','label':'Frozen experimental model outputs','classification':'synthetic_model','status':'implemented_frozen','description':'24/48/72h LightGBM probabilities and raw-margin TreeSHAP.72h below chance; sensitivity zero at0.35 at all horizons.'},
        {'id':'real_clinical','label':'Real clinical / real hardware observations','classification':'not_available','status':'not_implemented','description':'None. CPCB/IMD adapters, real hardware enrollment, clinical validity and emergency services are not implemented.'}],
        'counts':counts,'records':records,'environment':env,'no_real_patient_records':True,'model_data_sha256':s.engine.bundle['data_hash'],'limitation':'Current context and all new monitoring/manual records are excluded from the frozen ML pipeline. Original model artifacts, split/evaluation files and historical caches remain unchanged.'}
