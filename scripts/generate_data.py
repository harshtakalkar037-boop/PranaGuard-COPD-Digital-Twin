"""Reproducible stochastic longitudinal research data, NOT a clinical simulator."""
import argparse, hashlib, json
import numpy as np
import pandas as pd
from backend.app.config import DATA
from scripts.fetch_environment import SITES

def environment(city, hours, rng, offline):
    folder=DATA/'environment'; airfile=folder/f'{city.lower()}_air.json'; wfile=folder/f'{city.lower()}_weather.json'
    if airfile.exists() and wfile.exists():
        air=json.loads(airfile.read_text()); w=json.loads(wfile.read_text())
        a=pd.DataFrame(air['hourly']).set_index('time'); b=pd.DataFrame(w['hourly']).set_index('time')
        e=a.join(b).rename(columns={'pm2_5':'pm25','nitrogen_dioxide':'no2','temperature_2m':'temperature','relative_humidity_2m':'humidity'})
        if len(e)<hours: raise ValueError('Cache is shorter than requested; fetch a matching interval.')
        if e.iloc[:hours].isna().any().any(): raise ValueError('Environmental cache contains gaps; inspect source before use.')
        return e.iloc[:hours].reset_index(drop=True), 'cached_real_ambient'
    if not offline: raise FileNotFoundError('Run python -m scripts.fetch_environment or use --allow-synthetic-environment')
    t=np.arange(hours); pm=np.clip(27+17*np.sin(t/83)+rng.normal(0,5,hours),2,None)
    return pd.DataFrame({'pm25':pm,'pm10':pm*1.7,'no2':12+pm*.3,'ozone':25+pm*.15,
                         'temperature':27+5*np.sin(t/24*2*np.pi),'humidity':65+12*np.cos(t/24*2*np.pi)}),'synthetic_environment_fallback'

def generate(seed=2026, patients=120, days=60, allow_synthetic_environment=False):
    if patients<30 or days<30: raise ValueError('Minimum 30 patients and 30 days required.')
    rng=np.random.default_rng(seed); n=days*24
    envs={c:environment(c,n,rng,allow_synthetic_environment) for c in SITES}
    profiles=[]; frames=[]
    for i in range(patients):
        pid=f'PG-{i+1:04d}'; city=list(SITES)[i%4]; e,env_kind=envs[city]
        age=int(rng.integers(48,84)); fev=float(rng.uniform(28,79)); severity=(80-fev)/50
        prior=int(rng.poisson(1+severity)); pack=round(float(rng.uniform(8,62)),1); bmi=round(float(rng.uniform(18,33)),1)
        base_o2=float(rng.uniform(92.7,97.5)-severity*.7); base_hr=float(rng.uniform(64,87)); base_rr=float(rng.uniform(15,21))
        base_sym=float(rng.uniform(.4,2)); base_steps=float(rng.uniform(120,340))
        propensity=float(rng.uniform(.7,.98)); adherence=np.clip(propensity+rng.normal(0,.13,n),0,1)
        # Short missing-adherence streaks are generated independently of labels.
        for start in rng.integers(96,n-48,size=6): adherence[start:start+24] *= rng.uniform(.2,.6)
        load=np.zeros(n); onset=np.zeros(n,dtype=int); active=np.zeros(n,dtype=int); last=-10000
        pm=e.pm25.to_numpy(); hum=e.humidity.to_numpy()
        for t in range(72,n):
            shock=rng.gamma(2,1.2) if rng.random()<.0038 else 0
            load[t]=max(0,.966*load[t-1]+.014*max(0,(pm[t]-15)/35)+.045*(1-adherence[t])+shock+rng.normal(0,.045))
            hazard=(.00065+.018/(1+np.exp(-(2.5*load[t]-4.7))))*(.6+.7*severity)
            if t-last>144 and t>96 and rng.random()<hazard:
                onset[t]=1; last=t
            active[t]=int(0<=t-last<72)
        circ=np.sin((np.arange(n)%24-7)*2*np.pi/24)
        body_load=load+active*.8
        spo2=np.clip(base_o2-1.18*body_load+rng.normal(0,.4,n),82,99.5)
        hr=np.clip(base_hr+4.6*body_load+2*circ+rng.normal(0,2.4,n),45,135)
        rr=np.clip(base_rr+1.6*body_load+rng.normal(0,.9,n),10,38)
        sym=np.clip(base_sym+1.05*body_load+rng.normal(0,.42,n),0,10)
        steps=np.clip(base_steps*(1-.12*body_load)*(.8+.55*np.maximum(circ,0))+rng.normal(0,35,n),0,800)
        sleep=np.clip(7.3-.4*body_load+rng.normal(0,.45,n),2,10)
        future=np.full(n,np.nan); next_at=np.inf
        for t in range(n-1,-1,-1):
            future[t]=next_at-t
            if onset[t]: next_at=t
        eligible=(np.arange(n)>=72)&(active==0)&(onset==0)&(np.arange(n)<n-72)
        df=pd.DataFrame({'patient_id':pid,'hour':np.arange(n),'timestamp':pd.date_range('2026-08-01',periods=n,freq='h',tz='UTC').astype(str),
             'age':age,'fev1_pct':round(fev,2),'prior_exacerbations':prior,'smoking_pack_years':pack,'bmi':bmi,
             'spo2':spo2,'heart_rate':hr,'resp_rate':rr,'symptom_score':sym,'steps':steps,'sleep_hours':sleep,'adherence':adherence,
             'pm25':e.pm25.to_numpy(),'pm10':e.pm10.to_numpy(),'no2':e.no2.to_numpy(),'ozone':e.ozone.to_numpy(),
             'temperature':e.temperature.to_numpy(),'humidity':hum,'event_onset':onset,'active_episode':active,'eligible':eligible,
             'city':city,'environment_source':env_kind})
        # Approximately 1% missing wearable measurements. Imputed only from TRAIN data during fitting.
        for col in ['spo2','heart_rate','resp_rate','steps']:
            mask=(rng.random(n)<.012)&(np.arange(n)>=72); df.loc[mask,col]=np.nan
        for h in [24,48,72]:
            df[f'label_{h}']=np.where(eligible,(future<=h).astype(float),np.nan)
        num=df.select_dtypes('number').columns; df[num]=df[num].round(4)
        frames.append(df)
        profiles.append({'patient_id':pid,'display_name':f'Synthetic twin {i+1:03d}','synthetic':True,'city':city,
                         'age':age,'fev1_pct':round(fev,1),'prior_exacerbations':prior,'smoking_pack_years':pack,'bmi':bmi,
                         'sex':str(rng.choice(['Female','Male'])),'environment_source':env_kind})
    all_df=pd.concat(frames,ignore_index=True); DATA.mkdir(exist_ok=True)
    target=DATA/'synthetic_longitudinal.csv.gz'; all_df.to_csv(target,index=False,compression={'method':'gzip','mtime':0})
    (DATA/'patients.json').write_text(json.dumps(profiles,indent=2))
    info={'seed':seed,'patients':patients,'days':days,'hours_per_patient':n,'rows':len(all_df),
          'synthetic_events':int(all_df.event_onset.sum()),'eligible_rows':int(all_df.eligible.sum()),
          'environment_sources':sorted(all_df.environment_source.unique().tolist()),
          'generator':'Causal stochastic latent burden with probabilistic onsets; all physiology and labels synthetic.',
          'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'start':'2026-08-01T00:00:00Z',
          'clinical_validity':'NONE; not a validated physiological disease model'}
    (DATA/'generation_manifest.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=2026);p.add_argument('--patients',type=int,default=120);p.add_argument('--days',type=int,default=60);p.add_argument('--allow-synthetic-environment',action='store_true');a=p.parse_args();generate(a.seed,a.patients,a.days,a.allow_synthetic_environment)
