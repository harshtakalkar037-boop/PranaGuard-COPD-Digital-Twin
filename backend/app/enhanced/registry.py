"""Fictional registrations and read-only views of the original historical cohort."""
import hashlib,json,uuid
from datetime import timedelta
from fastapi import HTTPException
from backend.app.enhanced.settings import stamp,parse_stamp,utcnow,METRICS

def public_device(row):
    d=dict(row);d.pop('token_hash',None);d['is_simulating']=bool(d['is_simulating']);d['source_type']='simulated_device';d['hardware_connected']=False
    age=(utcnow()-parse_stamp(d['last_seen_at'])).total_seconds() if d['last_seen_at'] else None
    d['freshness']='stale' if age is not None and age>max(30,d['interval_seconds']*3) else 'recent' if age is not None else 'no_readings'
    return d

def fingerprint(body):return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

class Registry:
    def __init__(self,engine,notifications):self.engine=engine;self.store=engine.store;self.notifications=notifications
    def require(self,pid):
        with self.store.connect() as c:
            row=c.execute('SELECT profile FROM patients WHERE patient_id=?',(pid,)).fetchone()
            if not row:raise HTTPException(404,'Synthetic patient not found.')
            return json.loads(row['profile'])

    def register(self,body,doctor_id=None):
        data=body.model_dump(mode='json');digest=fingerprint(data)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM registrations WHERE request_id=?',(body.request_id,)).fetchone()
            if old:
                # An idempotency key belongs to the creator's assigned record;
                # never reveal a different doctor's ID or whether the payload matched.
                if doctor_id is not None and not c.execute("SELECT 1 FROM doctor_patient_assignments a JOIN patients p ON p.patient_id=a.patient_id WHERE a.doctor_id=? AND a.patient_id=? AND json_type(p.profile,'$.synthetic')='true'",(doctor_id,old['patient_id'])).fetchone():
                    raise HTTPException(404,'Record not found')
                if old['payload_hash']!=digest:raise HTTPException(409,'Registration request ID was reused with different content.')
                return {'patient_id':old['patient_id'],'duplicate':True,'prediction_supported':False,'notice':'Existing fictional registration returned; no duplicate patient created.'}
            pid='PG-DEMO-'+uuid.uuid4().hex[:12].upper();at=stamp()
            profile={'patient_id':pid,'display_name':'Fictional demo · '+body.demo_alias,'synthetic':True,'city':body.city,'age':body.age,'sex':body.sex,'fev1_pct':body.fev1_pct,'bmi':body.bmi,'prior_exacerbations':body.prior_exacerbations,'smoking_pack_years':body.smoking_pack_years,'environment_source':'Independent city context only; not model input','source_type':'manual_demo'}
            c.execute('INSERT INTO patients VALUES (?,?)',(pid,json.dumps(profile)))
            c.execute('INSERT INTO registrations VALUES (?,?,?,?,?,?)',(pid,body.request_id,digest,at,json.dumps(data),'manual_demo'))
            # Portal-mode registration occurs only for a fully assigned doctor.
            # Keep creation, assignment and audit in the same SQLite transaction.
            if doctor_id is not None:
                c.execute('INSERT INTO doctor_patient_assignments(doctor_id,patient_id) VALUES (?,?)',(doctor_id,pid))
                c.execute('INSERT INTO portal_audit(actor_id,patient_id,action,created_at) VALUES (?,?,?,?)',(doctor_id,pid,'synthetic_registration_assigned',at))
            self.notifications.create(category='data_quality',title='New fictional patient · baseline incomplete',reason='At least 72 real elapsed hours of suitable baseline observations are required. Manual reference values and frequent simulated samples do not create model eligibility.',source='Fictional patient registration',source_type='manual_demo',patient_id=pid,dedupe_key='registration:'+pid,conn=c)
            c.execute('INSERT INTO enhanced_audit(created_at,category,patient_id,source,detail) VALUES (?,?,?,?,?)',(at,'registration',pid,'manual_demo','Fictional registration created; frozen cohort and models unchanged.'))
        return {'patient_id':pid,'duplicate':False,'prediction_supported':False,'notice':'Fictional patient saved. 72-hour baseline warm-up has not been bypassed; no prediction is generated.'}

    def baseline(self,pid):
        if pid in self.engine.profiles:
            state=self.engine.patient(pid)
            return {'status':'historical_baseline','required_hours':72,'observed_hours':72,'elapsed_hours':72,'complete':True,'means':state['baseline'],'coverage':{},'prediction_supported':state['prediction_supported'],'notice':'Original first 72h historical baseline. New device streams never replace this baseline or alter frozen predictions.'}
        with self.store.connect() as c:
            extent=c.execute('SELECT MIN(observed_at) AS first,MAX(observed_at) AS last FROM device_readings WHERE patient_id=?',(pid,)).fetchone()
            first=extent['first'];last=extent['last'];coverage={};means={}
            if first:
                end=(parse_stamp(first)+timedelta(hours=72)).isoformat()
                rows=c.execute('''SELECT metric,COUNT(*) AS samples,
                    COUNT(DISTINCT CAST((CAST(strftime('%s',observed_at) AS INTEGER)-CAST(strftime('%s',?) AS INTEGER))/3600 AS INTEGER)) AS hours,AVG(value) AS mean
                    FROM device_readings WHERE patient_id=? AND observed_at>=? AND observed_at<? GROUP BY metric''',(first,pid,first,end)).fetchall()
                coverage={r['metric']:r['hours'] for r in rows};means={r['metric']:r['mean'] for r in rows}
            elapsed=max(0,(parse_stamp(last)-parse_stamp(first)).total_seconds()/3600) if first and last else 0
            observed=min((coverage.get(m,0) for m in ('spo2','heart_rate','resp_rate')),default=0)
            complete=bool(first and elapsed>=72 and observed>=72)
        return {'status':'baseline_collected_no_model' if complete else 'collecting_baseline' if first else 'baseline_not_started','required_hours':72,'observed_hours':min(72,observed),'elapsed_hours':round(elapsed,4),'first_observed_at':first,'last_observed_at':last,'complete':complete,'means':means,'coverage':coverage,'prediction_supported':False,'notice':'72 hourly baseline bins and 72 elapsed hours are necessary, not sufficient. Device-only data lack the compatible full clinical/symptom/adherence/sleep/environment feature frame. No prediction is manufactured.'}

    def list(self,q='',city=None,status=None,risk=None,sex=None,doctor_id=None):
        with self.store.connect() as c:
            # None is reserved for the explicitly unsafe isolated legacy mode.
            scope='' if doctor_id is None else " WHERE EXISTS (SELECT 1 FROM doctor_patient_assignments a WHERE a.doctor_id=? AND a.patient_id=p.patient_id) AND json_type(p.profile,'$.synthetic')='true'"
            params=() if doctor_id is None else (doctor_id,)
            rows=c.execute('SELECT p.*,r.created_at,r.details FROM patients p LEFT JOIN registrations r USING(patient_id)'+scope+' ORDER BY p.patient_id',params).fetchall()
            model={r['patient_id']:json.loads(r['state']) for r in c.execute('SELECT s.patient_id,s.state FROM states s JOIN (SELECT patient_id,MAX(version) AS v FROM states GROUP BY patient_id) x ON x.patient_id=s.patient_id AND x.v=s.version JOIN patients p ON p.patient_id=s.patient_id'+scope,params)}
            counts={r['patient_id']:r['n'] for r in c.execute('SELECT p.patient_id,COUNT(d.id) AS n FROM patients p JOIN devices d ON d.patient_id=p.patient_id'+scope+' GROUP BY p.patient_id',params)}
        original_count=sum(row['patient_id'] in self.engine.profiles for row in rows)
        result=[]
        for row in rows:
            p=json.loads(row['profile']);pid=p['patient_id'];historical=pid in self.engine.profiles;s=model.get(pid)
            state='historical_twin' if historical else self.baseline(pid)['status']
            p.update({'origin':'original_synthetic_cohort' if historical else 'manual_demo_registration','registered_at':row['created_at'],'monitoring_status':state,'risk_category':s['risk_category'] if s else 'unavailable','prediction_supported':s['prediction_supported'] if s else False,'device_count':counts.get(pid,0),'synthetic':True})
            if q.lower() not in (pid+' '+p['display_name']+' '+p['city']).lower():continue
            if city and p['city']!=city:continue
            if status and state!=status:continue
            if risk and p['risk_category']!=risk:continue
            if sex and p.get('sex','Not specified')!=sex:continue
            result.append(p)
        return {'patients':result,'total':len(result),'original_cohort_count':original_count,'synthetic_only':True}

    def detail(self,pid,doctor_id=None):
        profile=self.require(pid);historical=pid in self.engine.profiles
        with self.store.connect() as c:
            reg=c.execute('SELECT * FROM registrations WHERE patient_id=?',(pid,)).fetchone()
            devices=[public_device(r) for r in c.execute('SELECT * FROM devices WHERE patient_id=? ORDER BY created_at DESC',(pid,))]
            readings=[dict(r) for r in c.execute('SELECT * FROM device_readings WHERE patient_id=? ORDER BY observed_at DESC,id DESC LIMIT 300',(pid,))][::-1]
            monitoring=[{'version':r['id'],'created_at':r['created_at'],'snapshot':json.loads(r['snapshot'])} for r in c.execute('SELECT * FROM monitoring_states WHERE patient_id=? ORDER BY id DESC LIMIT 72',(pid,))]
            observations=[dict(r) for r in c.execute('SELECT * FROM demo_observations WHERE patient_id=? ORDER BY id DESC LIMIT 50',(pid,))]
            archives=[{'archived_at':r['created_at'],'source':r['source'],'record':json.loads(r['detail'])} for r in c.execute("SELECT * FROM enhanced_audit WHERE patient_id=? AND category='legacy_review_archive' ORDER BY id DESC LIMIT 100",(pid,))]
        details=json.loads(reg['details']) if reg else {'copd_history':'Synthetic cohort attributes from the frozen generator; not a diagnosed clinical record.','diagnosis_info':'No individual diagnosis document was supplied.','medications':'No manually recorded demo plan.','clinician_alias':'Not assigned','source_type':'synthetic_cohort'}
        return {'profile':profile,'details':details,'registered_at':reg['created_at'] if reg else None,'origin':'original_synthetic_cohort' if historical else 'manual_demo_registration','baseline':self.baseline(pid),'model_state':self.engine.patient(pid) if historical else None,'model_history':self.engine.history(pid,72) if historical else None,'devices':devices,'readings':readings,'monitoring_versions':monitoring,'latest_monitoring':monitoring[0] if monitoring else None,'observations':observations,'reviews':self.store.interventions(pid),'archived_reviews_and_alerts':archives,'notifications':self.notifications.list(patient_id=pid,doctor_id=doctor_id)['notifications'],'model_boundary':'Device/manual monitoring and current city environment are separate context. They do not mutate historical twin risks, TreeSHAP or frozen feature frames.','metrics':METRICS}

    def observation(self,pid,body):
        self.require(pid);at=stamp()
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO demo_observations(patient_id,created_at,symptom_score,adherence,note) VALUES (?,?,?,?,?)',(pid,at,body.symptom_score,body.adherence,body.note));oid=cur.lastrowid
            if body.symptom_score>=7 or body.adherence<.5:
                self.notifications.create(category='patient_monitoring',title='Manual demo monitoring rule',reason='Fictional symptom score≥7 or adherence<50% matched an unvalidated demonstration rule. This is not a diagnosis, urgency assessment or model prediction.',source='Manual fictional observation',source_type='manual_demo',patient_id=pid,dedupe_key=f'observation:{oid}',metadata={'observation_id':oid},conn=c)
        return {'id':oid,'created_at':at,'source_type':'manual_demo','prediction_updated':False}

    def review(self,pid,body):
        self.require(pid);at=stamp();historical=pid in self.engine.profiles
        with self.store.connect() as c:
            current=c.execute('SELECT MAX(id) AS v FROM monitoring_states WHERE patient_id=?',(pid,)).fetchone()['v'] or 0
            version=self.engine.patient(pid)['version'] if historical else current
            cur=c.execute('INSERT INTO interventions(patient_id,kind,note,created_at,state_version) VALUES (?,?,?,?,?)',(pid,body.kind,body.note,at,version));iid=cur.lastrowid
            c.execute('INSERT INTO enhanced_audit(created_at,category,patient_id,source,detail) VALUES (?,?,?,?,?)',(at,'review_created',pid,'manual_demo_review',json.dumps({'intervention_id':iid,'version_kind':'historical_model' if historical else 'monitoring_only','state_version':version})))
        return {'id':iid,'state_version':version,'notice':'Demo review saved to existing intervention ledger. No clinical action or model change was performed.'}
