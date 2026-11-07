"""Persistent personalized digital twin, hourly deterministic replay, exact model inference."""
import hashlib, json, threading, warnings
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from backend.app.config import DATA, ARTIFACTS, HORIZONS
from backend.app.features import add_features, FEATURES, MEASURES, BASE_MAP, DISPLAY, risk_category
from backend.app.store import Store
from backend.app.validation import validate_longitudinal
warnings.filterwarnings('ignore',message='X does not have valid feature names')

def now():return datetime.now(timezone.utc).isoformat()
def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,list):return [clean(v) for v in x]
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(float,np.floating)):return None if not np.isfinite(x) else float(x)
    if isinstance(x,np.bool_):return bool(x)
    return x

class TwinEngine:
    def __init__(self,path):
        self.store=Store(path);self.lock=threading.RLock()
        self.raw=pd.read_csv(DATA/'synthetic_longitudinal.csv.gz')
        self.ingestion_validation=validate_longitudinal(self.raw)
        self.frame=add_features(self.raw).set_index(['patient_id','hour'],drop=False).sort_index()
        self.profiles={p['patient_id']:p for p in json.loads((DATA/'patients.json').read_text())}
        self.bundle=joblib.load(ARTIFACTS/'models.joblib'); self.models=self.bundle['models']
        if hashlib.sha256((DATA/'synthetic_longitudinal.csv.gz').read_bytes()).hexdigest()!=self.bundle['data_hash']:
            raise RuntimeError('Dataset checksum differs from the fitted model. Regenerate/retrain as a consistent bundle.')
        self.evaluation=json.loads((ARTIFACTS/'evaluation.json').read_text())
        self.demo=json.loads((ARTIFACTS/'demo_case.json').read_text());self.max_hour=int(self.raw.hour.max())
        self.environment_manifest=json.loads((DATA/'environment'/'manifest.json').read_text()) if (DATA/'environment'/'manifest.json').exists() else {'sources':[]}
        self.running=False
        if self.store.meta('data_hash') not in [None,self.bundle['data_hash']]:
            raise RuntimeError('Database/model data mismatch. Back up DB and run demo reset/bootstrap with a fresh DB.')
        with self.store.connect() as c:
            for p in self.profiles.values():c.execute('INSERT OR IGNORE INTO patients VALUES (?,?)',(p['patient_id'],json.dumps(p)))
        if self.store.meta('cursor') is None:self.reset(self.demo['start_hour'])

    @property
    def cursor(self):return self.store.meta('cursor',self.demo['start_hour'])

    def _states_for_hour(self,hour,version):
        rows=self.frame.xs(hour,level='hour',drop_level=False).reset_index(drop=True).sort_values('patient_id')
        probabilities={h:self.models[h].predict(rows) for h in HORIZONS}
        states=[]
        for i,(_,r) in enumerate(rows.iterrows()):
            pid=r.patient_id;missing=[m for m in MEASURES if pd.isna(r[m])]
            supported=bool(r.eligible)
            s={'patient_id':pid,'synthetic':True,'version':version,'hour':hour,'timestamp':r.timestamp,
               'model_version':self.bundle['version'],'profile':self.profiles[pid],
               'current':{m:r[m] for m in MEASURES},'baseline':{src:r[target] for src,target in BASE_MAP.items()},
               'features':{f:r[f] for f in FEATURES},
               'risks':{str(h):float(probabilities[h][i]) for h in HORIZONS},
               'risk_category':risk_category(float(probabilities[72][i])),
               'prediction_supported':supported,'missing_fields':missing,
               'warnings':([] if supported else ['Current synthetic episode or incomplete follow-up: outside evaluated forecasting states.'])+(['Missing fields use training-set median imputation.'] if missing else []),
               'data_sources':{'body':'synthetic hourly replay','environment':r.environment_source,'baseline':'median of first72h (pre-fit calibration)'},
               'freshness':{'body_hours_behind_replay':0,'environment_hours_behind_replay':0,'mode':'historical cached replay, NOT live monitoring'}}
            states.append(clean(s))
        return states

    def _persist(self,c,states):
        for s in states:
            c.execute('INSERT INTO states VALUES (?,?,?,?,?)',(s['patient_id'],s['version'],s['hour'],s['timestamp'],json.dumps(s,allow_nan=False)))
            if s['prediction_supported'] and s['risks']['72']>=.35:
                open_alert=c.execute("SELECT id FROM alerts WHERE patient_id=? AND status!='resolved' LIMIT 1",(s['patient_id'],)).fetchone()
                if not open_alert:c.execute('INSERT INTO alerts(patient_id,state_version,created_at,risk,horizon) VALUES (?,?,?,?,?)',(s['patient_id'],s['version'],s['timestamp'],s['risks']['72'],72))

    def reset(self,hour=None):
        hour=self.demo['start_hour'] if hour is None else hour
        if not 72<=hour<=self.max_hour:raise ValueError('Replay hour outside available post-calibration range')
        with self.lock:
            self.running=False; states=self._states_for_hour(hour,1)
            with self.store.connect() as c:
                # An explicit replay reset affects the original replay cohort only.
                # Archive review/alert/scenario records before clearing the active run;
                # do not erase new registrations, monitoring streams or their reviews.
                ids=tuple(self.profiles);marks=','.join('?' for _ in ids);at=now()
                for table in ['alerts','interventions','scenarios']:
                    for row in c.execute(f'SELECT * FROM {table} WHERE patient_id IN ({marks})',ids).fetchall():
                        c.execute('INSERT INTO enhanced_audit(created_at,category,patient_id,source,detail) VALUES (?,?,?,?,?)',(at,'legacy_review_archive',row['patient_id'],table,json.dumps(dict(row))))
                for row in c.execute("SELECT id,status FROM notifications WHERE legacy_alert_id IN (SELECT id FROM alerts) AND status!='closed'").fetchall():
                    c.execute("UPDATE notifications SET status='closed',updated_at=? WHERE id=?",(at,row['id']))
                    c.execute('INSERT INTO notification_history(notification_id,created_at,from_status,to_status,action,note) VALUES (?,?,?,?,?,?)',(row['id'],at,row['status'],'closed','replay_reset','Replay reset archived the source alert; this does not assert recovery.'))
                for t in ['scenarios','interventions','alerts','states']:c.execute(f'DELETE FROM {t} WHERE patient_id IN ({marks})',ids)
                # Keep monotonic alert/action IDs so archived notification links cannot
                # accidentally bind to an unrelated later replay alert.
                self._persist(c,states)
                for k,v in [('cursor',hour),('version',1),('data_hash',self.bundle['data_hash'])]:c.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(k,json.dumps(v)))
            return self.replay_status()

    def step(self,hours=1):
        with self.lock:
            cursor=self.cursor;version=self.store.meta('version',1)
            if cursor+hours>self.max_hour:raise ValueError('Replay would exceed dataset end')
            with self.store.connect() as c:
                for h in range(cursor+1,cursor+hours+1):
                    version+=1;self._persist(c,self._states_for_hour(h,version))
                c.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('cursor',json.dumps(cursor+hours)))
                c.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('version',json.dumps(version)))
            return self.replay_status()

    def replay_status(self):
        cursor=self.cursor
        return {'running':self.running,'cursor_hour':cursor,'max_hour':self.max_hour,'version':self.store.meta('version',1),
                'timestamp':str(self.frame.iloc[cursor]['timestamp']) if cursor<len(self.frame) else '',
                'mode':'deterministic offline replay','seed':2026,'demo':self.demo,'interval_seconds':2}

    def cohort(self,patient_ids=None):
        """Whole-cohort by default. Optional patient_ids restricts every aggregate (patient lists,
        summaries, trend and open-alert counts) with no cross-scope leakage; empty set is valid."""
        scope=None if patient_ids is None else set(patient_ids)
        with self.store.connect() as c:
            rows=c.execute('SELECT s.state FROM states s JOIN (SELECT patient_id,MAX(version) AS v FROM states GROUP BY patient_id) latest ON s.patient_id=latest.patient_id AND s.version=latest.v').fetchall()
        states=[json.loads(r['state']) for r in rows if scope is None or json.loads(r['state'])['patient_id'] in scope]
        if scope is None or scope:
            with self.store.connect() as c:
                marks='' if scope is None else ' WHERE patient_id IN ('+','.join('?' for _ in scope)+')'
                trend=[dict(r) for r in c.execute(f'''SELECT hour,MIN(timestamp) AS timestamp,
                    AVG(json_extract(state,'$.risks."24"')) AS risk_24,
                    AVG(json_extract(state,'$.risks."48"')) AS risk_48,
                    AVG(json_extract(state,'$.risks."72"')) AS risk_72
                    FROM states{marks} GROUP BY hour ORDER BY hour DESC LIMIT 48''',tuple(scope) if scope is not None else ())][::-1]
        else:trend=[]
        alerts=[a for a in self.store.alerts() if scope is None or a['patient_id'] in scope];open_counts={}
        for a in alerts:
            if a['status']!='resolved':open_counts[a['patient_id']]=open_counts.get(a['patient_id'],0)+1
        patients=[{'patient_id':s['patient_id'],**s['profile'],'risks':s['risks'],'risk_category':s['risk_category'],
                   'current':s['current'],'version':s['version'],'timestamp':s['timestamp'],'missing_fields':s['missing_fields'],
                   'prediction_supported':s['prediction_supported'],'open_alerts':open_counts.get(s['patient_id'],0)} for s in states]
        return {'patients':patients,'summary':{'total':len(patients),'high':sum(p['risk_category']=='high' for p in patients),
                'elevated':sum(p['risk_category']=='elevated' for p in patients),'low':sum(p['risk_category']=='low' for p in patients),
                'open_alerts':sum(a['status']!='resolved' for a in alerts),'missing_measurements':sum(len(s['missing_fields']) for s in states)},
                'replay':self.replay_status(),'model_version':self.bundle['version'],'synthetic':True,'trend':trend}

    def patient(self,pid,version=None):return self.store.latest(pid,version)

    def history(self,pid,limit=48):
        s=self.patient(pid); history=self.store.history(pid,limit)
        # Earlier physiology remains available from the observed data; model history only exists for persisted versions.
        rows=self.frame.loc[pid];raw=rows[(rows.hour<=s['hour'])&(rows.hour>s['hour']-limit)]
        risk_by_hour={r['hour']:r for r in history}
        obs=[]
        for _,r in raw.iterrows():
            snap=risk_by_hour.get(int(r.hour))
            obs.append(clean({'hour':int(r.hour),'timestamp':r.timestamp,'spo2':r.spo2,'heart_rate':r.heart_rate,'resp_rate':r.resp_rate,'pm25':r.pm25,'symptom_score':r.symptom_score,
                              'risk_24':snap['risks']['24'] if snap else None,'risk_48':snap['risks']['48'] if snap else None,'risk_72':snap['risks']['72'] if snap else None,'version':snap['version'] if snap else None}))
        return {'patient_id':pid,'observations':obs,'versions':self.store.versions(pid,limit),'risk_history_note':'Null risk values were not persisted/predicted during replay; no fabricated historical predictions.'}

    def explain(self,pid,horizon=72,version=None):
        s=self.patient(pid,version);row=pd.DataFrame([s['features']]);e=self.models[horizon].explain(row)
        previous=self.store.history(pid,2)
        prev=next((x for x in previous if x['version']<s['version']),None) if version is None else None
        previous_e=self.models[horizon].explain(pd.DataFrame([prev['features']])) if prev else None
        prevcon={d['feature']:d['contribution'] for d in previous_e['drivers']} if previous_e else {}
        for d in e['drivers']:
            d['label']=DISPLAY.get(d['feature'],d['feature'].replace('_',' ').title())
            d['contribution_change']=d['contribution']-prevcon[d['feature']] if d['feature'] in prevcon else None
        e['drivers'].sort(key=lambda d:abs(d['contribution']),reverse=True)
        e.update({'patient_id':pid,'version':s['version'],'horizon':horizon,'probability':s['risks'][str(horizon)],
                  'previous_probability':prev['risks'][str(horizon)] if prev else None,
                  'risk_change':s['risks'][str(horizon)]-prev['risks'][str(horizon)] if prev else None,
                  'relative_deviations':{k:(s['current'][k]-v if s['current'][k] is not None and v is not None else None) for k,v in s['baseline'].items()},
                  'missing_fields':s['missing_fields']})
        return clean(e)

    def scenario(self,pid,assumptions):
        """Conditional feature-path sensitivity, not a causal intervention or treatment model.
        Body measurements persist at last observation; environmental/adherence/activity paths
        transition exponentially toward requested assumptions. Past observations never change.
        """
        with self.lock:
            original=self.patient(pid);before=json.dumps(original,sort_keys=True)
            hour=original['hour']; past=self.raw[(self.raw.patient_id==pid)&(self.raw.hour<=hour)].copy()
            last=past.iloc[-1].copy(); records=[];lastvals=original['current']
            for step in range(1,73):
                for name,changed in [('baseline',False),('scenario',True)]:
                    r=last.copy();r['hour']=hour+step;r['timestamp']=(pd.Timestamp(original['timestamp'])+pd.Timedelta(hours=step)).isoformat()
                    r['patient_id']=pid+'-'+name
                    r['eligible']=True
                    r['pm25']=lastvals['pm25']*(1+(assumptions['pm25_change_pct']/100 if changed else 0)*(1-np.exp(-step/6)))
                    r['pm10']=lastvals['pm10']*(r['pm25']/max(lastvals['pm25'],1))
                    r['adherence']=assumptions['adherence'] if changed else lastvals['adherence']
                    r['steps']=(lastvals['steps'] or original['baseline']['steps'])*(assumptions['activity_multiplier'] if changed else 1)
                    records.append(r)
            # Each path has its own immutable past and prospective branch. No future replay rows used.
            paths=[]
            for name in ['baseline','scenario']:
                p=past.copy();p['patient_id']=pid+'-'+name
                f=pd.DataFrame([r for r in records if r.patient_id==pid+'-'+name])
                paths.append(add_features(pd.concat([p,f],ignore_index=True)))
            allpaths=pd.concat(paths,ignore_index=True)
            future=allpaths[allpaths.hour>hour].copy()
            pred={h:self.models[h].predict(future) for h in HORIZONS}
            for h in HORIZONS:future[f'risk_{h}']=pred[h]
            trajectory=[]
            for step in [0,6,12,24,36,48,60,72]:
                item={'hours':step}
                for h in HORIZONS:
                    for name in ['baseline','scenario']:
                        item[f'{name}_{h}']=original['risks'][str(h)] if step==0 else float(future[(future.patient_id==pid+'-'+name)&(future.hour==hour+step)].iloc[0][f'risk_{h}'])
                trajectory.append(item)
            result=clean({'patient_id':pid,'state_version':original['version'],'assumptions':assumptions,'trajectory':trajectory,
                          'baseline_risks':{str(h):trajectory[-1][f'baseline_{h}'] for h in HORIZONS},
                          'scenario_risks':{str(h):trajectory[-1][f'scenario_{h}'] for h in HORIZONS},
                          'method':'Conditional feature-path sensitivity with observed physiology held constant and causal trailing windows recomputed. Independent calibrated horizon models at each projected time.',
                          'warning':'NOT causal, NOT a treatment recommendation. No proven effect of adherence, exposure reduction or activity. Forecasts at projected times extend beyond the original horizon. No future observed records used.',
                          'original_state_preserved':before==json.dumps(self.patient(pid),sort_keys=True)})
            with self.store.connect() as c:
                cur=c.execute('INSERT INTO scenarios(patient_id,state_version,created_at,assumptions,result) VALUES (?,?,?,?,?)',(pid,original['version'],now(),json.dumps(assumptions),json.dumps(result)))
                result['scenario_id']=cur.lastrowid
            return result

    def status(self):
        with self.store.connect() as c:
            counts={t:c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['patients','states','alerts','interventions','scenarios']}
        sources=self.environment_manifest['sources']
        return {'healthy':True,'mode':'offline cached historical demonstration','network_required':False,'live_patient_feed':False,
                'model_version':self.bundle['version'],'algorithm':self.bundle['algorithm'],'model_data_sha256':self.bundle['data_hash'],
                'replay':self.replay_status(),'database':{'engine':'SQLite','counts':counts},'environment_sources':sources,
                'environment_freshness':'Historical 2026-08-01 to 2026-09-29; not current conditions. Age is relative to replay, not wall-clock.',
                'synthetic':True,'ingestion_validation':self.ingestion_validation,'security':'Local demonstration only; no authentication by default. Do not expose real patient data.',
                'safety':'Research prototype. Not clinically validated. Risk categories are demonstration thresholds, not clinical cutoffs.'}
