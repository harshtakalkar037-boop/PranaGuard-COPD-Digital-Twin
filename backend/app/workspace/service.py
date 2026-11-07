"""Care workspace service. Demo-only identities (documented passwords, local PBKDF2 hashes,
expiring bearer sessions). This is NOT production identity/RBAC; claims stay honest."""
import base64, hashlib, json, secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

def utcnow():return datetime.now(timezone.utc)
def stamp():return utcnow().isoformat()

SESSION_HOURS=12
# Valid forward transitions for the care-review workflow.
TRANSITIONS={'new':{'awaiting_review','under_review','closed'},
             'awaiting_review':{'under_review','closed'},
             'under_review':{'follow_up_scheduled','completed','closed'},
             'follow_up_scheduled':{'under_review','completed','closed'},
             'completed':{'closed'},
             'closed':set()}

def hash_password(password,salt):return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),120_000).hex()

class Workspace:
    def __init__(self,engine,services):
        self.engine=engine;self.store=engine.store;self.services=services
        self.seed()
    # ---------- seeded demo identities ----------
    def seed(self):
        """Deterministic demo accounts; passwords documented in README, overridable by env before first boot on an empty DB."""
        import os
        users=[('dr-atlas','Dr. Asha Atlas (demo)','doctor',os.getenv('PRANAGUARD_DEMO_DOCTOR_PASSWORD','prana-atlas-demo'),None),
               ('dr-nova','Dr. Neil Nova (demo · empty panel)','doctor',os.getenv('PRANAGUARD_DEMO_DOCTOR2_PASSWORD','prana-nova-demo'),None),
               ('pat-pg0071','Synthetic twin 071 viewer (demo)','patient',os.getenv('PRANAGUARD_DEMO_PATIENT_PASSWORD','prana-patient-demo'),'PG-0071')]
        with self.store.connect() as c:
            for username,name,role,password,pid in users:
                if c.execute('SELECT 1 FROM care_users WHERE username=?',(username,)).fetchone():continue
                salt=secrets.token_hex(16)
                c.execute('INSERT INTO care_users VALUES (?,?,?,?,?,?,?)',(username,name,role,hash_password(password,salt),salt,pid,stamp()))
            atlas=c.execute('SELECT COUNT(*) AS n FROM patient_assignments WHERE doctor=?',('dr-atlas',)).fetchone()['n']
            if not atlas:
                for pid in self.engine.profiles:
                    c.execute('INSERT OR IGNORE INTO patient_assignments VALUES (?,?,?)',(pid,'dr-atlas',stamp()))
            self._seed_demo_content(c)
    def _seed_demo_content(self,c):
        """One-to-one demo: linked patient PG-0071 gets a little example history so the dashboards
        demonstrate connected workflows out of the box. Idempotent: only seeds a completely empty store."""
        if c.execute('SELECT 1 FROM daily_logs LIMIT 1').fetchone() or c.execute('SELECT 1 FROM documents LIMIT 1').fetchone():return
        pid='PG-0071';at=stamp();from datetime import timedelta as _td
        today=utcnow().date()
        logs=[('better',7.5,'good',1800,'Dal, rice, cooked veg; reduced salt',20,'Walked without stopping today. Slept well.'),
              ('same',7.0,'fair',1600,'Khichdi, soup, fruit',10,'Usual breathlessness in the morning.'),
              ('same',6.5,'fair',1700,'Rice, dal, yoghurt',15,'Slightly more cough than usual.')]
        for i,(wb,sh,sq,w,food,actv,note) in enumerate(logs):
            d=(today-_td(days=i)).isoformat()
            cur=c.execute('INSERT INTO daily_logs(patient_id,entry_date,water_ml,food_notes,activity_minutes,sleep_hours,sleep_quality,wellbeing,notes,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                          (pid,d,w,food,actv,sh,sq,wb,note,'pat-pg0071',at,at))
            c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,after_json) VALUES (?,?,?,?,?,?,?,?)',
                      (at,'pat-pg0071','patient','created','daily_log',str(cur.lastrowid),pid,json.dumps({'entry_date':d,'seeded_demo':True})))
        med=c.execute("INSERT INTO plan_medications(patient_id,name,dose,frequency,added_by,created_at) VALUES (?,?,?,?,?,?)",
                      (pid,'Inhaled bronchodilator (demo label)','2 puffs','twice daily','dr-atlas',at))
        mid=med.lastrowid
        for i in range(2):
            t=(utcnow()-_td(days=i)).isoformat()
            c.execute('INSERT INTO med_adherence(patient_id,medication_id,as_prescribed,taken_at,missed_reason,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?)',
                      (pid,mid,1,t,None,None,'pat-pg0071',t))
        c.execute('INSERT INTO follow_ups(patient_id,doctor,instructions,due_at,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
                  (pid,'dr-atlas','Demo instruction: keep recording sputum colour daily and bring the diary to the next review.',(today+_td(days=3)).isoformat()+'T09:00:00+00:00','scheduled',at,at))
        demo_doc=b'PRANAGUARD DEMO DOCUMENT\nThis is a fictional, synthetic prescription-style record used only to demonstrate the document workspace. It contains no real medical advice.\n'
        import hashlib as _hl
        c.execute('INSERT INTO documents(patient_id,title,doc_type,doc_date,notes,filename,media_type,size,sha256,data,uploaded_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                  (pid,'Demo COPD action plan summary (fictional)','action_plan',today.isoformat(),'Seeded demonstration record. Not real medical advice.','demo-action-plan.txt','text/plain',len(demo_doc),_hl.sha256(demo_doc).hexdigest(),demo_doc,'dr-atlas',at))
        c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,after_json) VALUES (?,?,?,?,?,?,?,?)',
                  (at,'dr-atlas','doctor','seeded','document','demo',pid,json.dumps({'title':'Demo COPD action plan summary (fictional)','seeded_demo':True})))
    # ---------- authentication ----------
    def login(self,username,password):
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM care_users WHERE username=?',(username.strip().lower(),)).fetchone()
            if not row or not secrets.compare_digest(row['pass_hash'],hash_password(password,row['salt'])):
                raise HTTPException(401,'Incorrect demo username or password.')
            token='pgw_'+secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
            c.execute('DELETE FROM care_sessions WHERE username=? AND expires_at<?',(row['username'],stamp()))
            c.execute('INSERT INTO care_sessions VALUES (?,?,?,?)',(digest,row['username'],stamp(),(utcnow()+timedelta(hours=SESSION_HOURS)).isoformat()))
        return {'token':token,'user':self.public_user(row)}
    def public_user(self,row):
        with self.store.connect() as c:
            assigned=c.execute('SELECT COUNT(*) AS n FROM patient_assignments WHERE doctor=?',(row['username'],)).fetchone()['n']
        return {'username':row['username'],'display_name':row['display_name'],'role':row['role'],'patient_id':row['patient_id'],'assigned_patients':assigned}
    def principal(self,token):
        if not token:raise HTTPException(401,'Sign in with a documented demo account first.')
        digest=hashlib.sha256(token.encode()).hexdigest()
        with self.store.connect() as c:
            session=c.execute('SELECT * FROM care_sessions WHERE token_hash=?',(digest,)).fetchone()
            if not session:raise HTTPException(401,'Session not recognised. Sign in again.')
            if session['expires_at']<stamp():
                c.execute('DELETE FROM care_sessions WHERE token_hash=?',(digest,));raise HTTPException(401,'Demo session expired. Sign in again.')
            user=c.execute('SELECT * FROM care_users WHERE username=?',(session['username'],)).fetchone()
        return self.public_user(user)
    def logout(self,token):
        with self.store.connect() as c:c.execute('DELETE FROM care_sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
    # ---------- scoping ----------
    def assigned_ids(self,user):
        if user['role']=='patient':
            if not user['patient_id']:raise HTTPException(403,'This demo patient account has no linked synthetic twin.')
            return {user['patient_id']}
        with self.store.connect() as c:
            return {r['patient_id'] for r in c.execute('SELECT patient_id FROM patient_assignments WHERE doctor=?',(user['username'],))}
    def require_assigned(self,user,pid):
        if pid not in self.assigned_ids(user):raise HTTPException(403,f'{pid} is not assigned to this demo account.')
    # ---------- patient directory ----------
    def directory(self,user,q='',city=None,origin=None,risk=None,sort='name',page=1,page_size=12):
        assigned=self.assigned_ids(user)
        cohort={p['patient_id']:p for p in self.engine.cohort()['patients'] if p['patient_id'] in assigned}
        items=[]
        with self.store.connect() as c:
            registered={r['patient_id']:dict(r) for r in c.execute('SELECT patient_id,created_at,source_type FROM registrations')}
            open_notes={r['patient_id']:r['n'] for r in c.execute("SELECT patient_id,COUNT(*) AS n FROM notifications WHERE status IN ('active','acknowledged','under_review') GROUP BY patient_id")}
            pending={r['patient_id']:r['n'] for r in c.execute("SELECT patient_id,COUNT(*) AS n FROM care_reviews WHERE status NOT IN ('completed','closed') GROUP BY patient_id")}
            plans={r['patient_id']:r['status'] for r in c.execute('SELECT patient_id,status FROM care_plans')}
            last_obs={r['patient_id']:r['t'] for r in c.execute('SELECT patient_id,MAX(observed_at) AS t FROM device_readings GROUP BY patient_id')}
            last_obs.update({r['patient_id']:r['t'] for r in c.execute('SELECT patient_id,MAX(created_at) AS t FROM demo_observations GROUP BY patient_id')})
        for pid in assigned:
            historical=pid in cohort
            if historical:
                p=cohort[pid];profile={k:p[k] for k in ('display_name','age','sex','city')};baseline=72.0;riskcat=p['risk_category'];pred=p['prediction_supported'];ts=p['timestamp']
            else:
                try:detail=self.services.registry.detail(pid)
                except Exception:continue
                profile={k:detail['profile'].get(k) for k in ('display_name','age','sex','city')};b=detail['baseline'];baseline=min(72.0,float(b['observed_hours']));riskcat='unavailable';pred=False;ts=b.get('last_observed_at')
            item={'patient_id':pid,**profile,'synthetic':True,'origin':'historical_twin' if historical else 'manual_demo_registration',
                  'registered_at':registered.get(pid,{}).get('created_at') if pid in registered else None,
                  'baseline_hours':baseline,'risk_category':riskcat,'prediction_supported':pred,
                  'risk72':cohort[pid]['risks']['72'] if historical else None,
                  'state_timestamp':ts,'last_observation_at':last_obs.get(pid) or ts,
                  'open_notifications':open_notes.get(pid,0),'open_reviews':pending.get(pid,0),
                  'care_plan_status':plans.get(pid)}
            text=f"{pid} {item['display_name'] or ''} {item['city'] or ''}".lower()
            if q and q.lower() not in text:continue
            if city and item['city']!=city:continue
            if origin and item['origin']!=origin:continue
            if risk and item['risk_category']!=risk:continue
            items.append(item)
        key={'name':lambda x:(x['display_name'] or '').lower(),'city':lambda x:x['city'] or '','risk':lambda x:-(x['risk72'] if x['risk72'] is not None else -1),'updated':lambda x:x['last_observation_at'] or ''}[sort]
        items.sort(key=key)
        total=len(items);start=(page-1)*page_size
        return {'items':items[start:start+page_size],'total':total,'page':page,'page_size':page_size,'assigned':len(assigned),
                'note':'All patients synthetic/fictional. Demo registrations never receive frozen-model predictions until the 72-hour baseline and feature frame exist.'}
    def profile(self,user,pid):
        self.require_assigned(user,pid)
        detail=self.services.registry.detail(pid)
        with self.store.connect() as c:
            reviews=[dict(r) for r in c.execute('SELECT * FROM care_reviews WHERE patient_id=? ORDER BY id DESC LIMIT 25',(pid,))]
            plan=c.execute('SELECT * FROM care_plans WHERE patient_id=?',(pid,)).fetchone()
            sputum=[dict(r) for r in c.execute('SELECT id,occurred_at,colour,volume,consistency,cough,breathlessness,note,reviewed_at,reviewed_by FROM sputum_entries WHERE patient_id=? ORDER BY id DESC LIMIT 30',(pid,))]
        return {'patient_id':pid,'profile':detail['profile'],'details':detail['details'],'origin':detail['origin'],'baseline':detail['baseline'],
                'model_state':{'version':detail['model_state']['version'],'risks':detail['model_state']['risks'],'risk_category':detail['model_state']['risk_category'],'timestamp':detail['model_state']['timestamp'],'prediction_supported':detail['model_state']['prediction_supported'],'model_version':detail['model_state']['model_version']} if detail['model_state'] else None,
                'observations':detail['observations'],'monitoring':{'latest':detail.get('latest_monitoring'),'versions':detail.get('monitoring_versions',[])[:12]},
                'reviews':reviews,'care_plan':dict(plan) if plan else None,'sputum_recent':sputum,
                'notifications':self.services.notifications.list(patient_id=pid,limit=30),
                'caution':'Synthetic/fictional patient. Model scores are research probabilities, not diagnoses or urgency.'}
    # ---------- doctor-scoped overview ----------
    def overview(self,user):
        ids=self.assigned_ids(user);cohort=self.engine.cohort(patient_ids=ids if ids else set())
        return {**cohort,'scope':{'username':user['username'],'assigned':len(ids),'excluded_from_view':len(self.engine.profiles)-len(ids)}},ids
    def care_summary(self,user):
        ids=self.assigned_ids(user)
        with self.store.connect() as c:
            def count(sql,args=()):
                if not ids:return 0
                marks=','.join('?' for _ in ids);return c.execute(sql.format(marks=marks),tuple(ids)+args).fetchone()['n']
            reviews=count("SELECT COUNT(*) AS n FROM care_reviews WHERE patient_id IN ({marks}) AND status NOT IN ('completed','closed')")
            in_progress=count("SELECT COUNT(*) AS n FROM care_reviews WHERE patient_id IN ({marks}) AND status='under_review'")
            completed=count("SELECT COUNT(*) AS n FROM care_reviews WHERE patient_id IN ({marks}) AND status IN ('completed','closed')")
            due=count("SELECT COUNT(*) AS n FROM care_reviews WHERE patient_id IN ({marks}) AND status NOT IN ('completed','closed') AND follow_up_at IS NOT NULL AND follow_up_at<=?",(stamp(),))
            notifications=count("SELECT COUNT(*) AS n FROM notifications WHERE patient_id IN ({marks}) AND status IN ('active','acknowledged','under_review')")
            recent=[dict(r) for r in c.execute('SELECT r.*,u.display_name AS doctor_name FROM care_reviews r LEFT JOIN care_users u ON u.username=r.doctor WHERE r.patient_id IN ({}) ORDER BY r.updated_at DESC LIMIT 8'.format(','.join('?' for _ in ids) or "''"),tuple(ids)).fetchall()] if ids else []
        return {'assigned_patients':len(ids),'pending_reviews':reviews,'reviews_in_progress':in_progress,'completed_reviews':completed,'follow_ups_due':due,'open_notifications':notifications,'recent_reviews':recent,'note':'Demo workflow counts from SQLite. Synthetic patients only.'}
    # ---------- care reviews ----------
    def state_version(self,pid):
        if pid in self.engine.profiles:return self.engine.patient(pid)['version']
        with self.store.connect() as c:return c.execute('SELECT MAX(id) AS v FROM monitoring_states WHERE patient_id=?',(pid,)).fetchone()['v'] or 0
    def create_review(self,user,pid,note,follow_up_at):
        self.require_assigned(user,pid);at=stamp()
        if follow_up_at and follow_up_at<at[:16]:raise HTTPException(422,'Follow-up cannot be in the past.')
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO care_reviews(patient_id,doctor,status,note,follow_up_at,state_version,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                          (pid,user['username'],'awaiting_review' if follow_up_at is None else 'follow_up_scheduled',note,follow_up_at,self.state_version(pid),at,at));rid=cur.lastrowid
            status='awaiting_review' if follow_up_at is None else 'follow_up_scheduled'
            c.execute('INSERT INTO care_review_events(review_id,created_at,event,actor,note) VALUES (?,?,?,?,?)',(rid,at,'created → '+status,user['username'],note))
            self.audit(c,user,'created','care_review',rid,pid,after={'status':status,'note':note[:200]})
        return {'review':self.review_detail(user,rid)['review'],'notice':'Demo review saved. Documentation only — not a clinical action.'}
    def list_reviews(self,user,status=None,pid=None,page=1,page_size=10):
        ids=self.assigned_ids(user);args=list(ids);sql='SELECT * FROM care_reviews WHERE patient_id IN ({})'.format(','.join('?' for _ in ids) or "''")
        if status:sql+=' AND status=?';args.append(status)
        if pid:sql+=' AND patient_id=?';args.append(pid)
        with self.store.connect() as c:
            total=c.execute(f'SELECT COUNT(*) AS n FROM ({sql})',args).fetchone()['n'] if ids else 0
            rows=[dict(r) for r in c.execute(sql+' ORDER BY updated_at DESC LIMIT ? OFFSET ?',args+[page_size,(page-1)*page_size]).fetchall()] if ids else []
        return {'items':rows,'total':total,'page':page,'page_size':page_size}
    def review_detail(self,user,rid):
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM care_reviews WHERE id=?',(rid,)).fetchone()
            if not row:raise HTTPException(404,'Review not found.')
            self.require_assigned(user,row['patient_id'])
            events=[dict(r) for r in c.execute('SELECT id,created_at,event,actor,note FROM care_review_events WHERE review_id=? ORDER BY id',(rid,))]
        return {'review':dict(row),'timeline':events}
    def update_review(self,user,rid,status=None,note=None,follow_up_at=None):
        detail=self.review_detail(user,rid);row=detail['review'];at=stamp()
        if status:
            allowed=TRANSITIONS[row['status']]
            if status not in allowed:raise HTTPException(409,f"Cannot move from '{row['status']}' to '{status}'. Allowed: {sorted(allowed) or 'none — record is closed'}.")
            if status=='follow_up_scheduled' and not (follow_up_at or row['follow_up_at']):raise HTTPException(422,'Choose a follow-up date/time to schedule a follow-up.')
        if follow_up_at and follow_up_at<at[:16] and status!='completed':raise HTTPException(422,'Follow-up cannot be in the past.')
        new_note=(row['note']+'\n'+note.strip()).strip() if note else row['note']
        with self.store.connect() as c:
            c.execute('UPDATE care_reviews SET status=?,note=?,follow_up_at=?,updated_at=? WHERE id=?',
                      (status or row['status'],new_note,follow_up_at if follow_up_at is not None else row['follow_up_at'],at,rid))
            if status:c.execute('INSERT INTO care_review_events(review_id,created_at,event,actor,note) VALUES (?,?,?,?,?)',(rid,at,f"{row['status']} → {status}",user['username'],note or ''))
            elif note or follow_up_at is not None:c.execute('INSERT INTO care_review_events(review_id,created_at,event,actor,note) VALUES (?,?,?,?,?)',(rid,at,'note/follow-up updated',user['username'],note or ''))
            self.audit(c,user,'updated','care_review',rid,detail['review']['patient_id'],before={'status':row['status']},after={'status':status or row['status'],'note_added':bool(note)})
        return {'review':self.review_detail(user,rid)['review']}
    # ---------- care plans ----------
    def get_plan(self,user,pid):
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            plan=c.execute('SELECT * FROM care_plans WHERE patient_id=?',(pid,)).fetchone()
            revisions=[dict(r) for r in c.execute('SELECT id,created_at,actor,change_note FROM care_plan_revisions WHERE patient_id=? ORDER BY id DESC LIMIT 30',(pid,))]
        return {'plan':dict(plan) if plan else None,'revisions':revisions,'notice':'Documentation template only. This app does not prescribe medication or treatment.'}
    def save_plan(self,user,pid,body):
        self.require_assigned(user,pid);at=stamp();data=body.model_dump(mode='json')
        with self.store.connect() as c:
            old=c.execute('SELECT * FROM care_plans WHERE patient_id=?',(pid,)).fetchone()
            if old:
                c.execute('INSERT INTO care_plan_revisions(patient_id,created_at,actor,change_note,snapshot) VALUES (?,?,?,?,?)',(pid,at,user['username'],data['change_note'],json.dumps(dict(old))))
                c.execute('UPDATE care_plans SET doctor=?,goals=?,activity_guidance=?,adherence_support=?,environment_notes=?,review_date=?,status=?,updated_at=? WHERE patient_id=?',
                          (user['username'],data['goals'],data['activity_guidance'],data['adherence_support'],data['environment_notes'],data['review_date'],data['status'],at,pid))
            else:
                c.execute('INSERT INTO care_plans VALUES (?,?,?,?,?,?,?,?,?,?)',(pid,user['username'],data['goals'],data['activity_guidance'],data['adherence_support'],data['environment_notes'],data['review_date'],data['status'],at,at))
            self.audit(c,user,'updated' if old else 'created','care_plan',pid,pid,before=dict(old) if old else None,after={'goals':data['goals'][:200],'status':data['status'],'review_date':data['review_date']})
        return {'plan':self.get_plan(user,pid)['plan'],'notice':'Demo care-plan documentation saved.'}
    # ---------- sputum / symptom diary ----------
    def add_sputum(self,user,pid,body):
        self.require_assigned(user,pid);at=stamp();data=body.model_dump(mode='json')
        attachment=data.pop('attachment',None)
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO sputum_entries(patient_id,occurred_at,colour,volume,consistency,cough,breathlessness,note,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                          (pid,data['occurred_at'],data['colour'],data['volume'],data['consistency'],data['cough'],data['breathlessness'],data['note'],at));eid=cur.lastrowid
            saved_attachment=None
            if attachment:
                raw=base64.b64decode(attachment['data_base64'],validate=True)
                if len(raw)>524288:raise HTTPException(422,'Attachment exceeds the 512 KB demo limit.')
                digest=hashlib.sha256(raw).hexdigest()
                c.execute('INSERT INTO attachments(patient_id,entry_id,filename,media_type,size,sha256,data,created_at) VALUES (?,?,?,?,?,?,?,?)',
                          (pid,eid,attachment['filename'][:120],attachment['media_type'],len(raw),digest,raw,at));saved_attachment=digest[:12]
            self.audit(c,user,'created','sputum_entry',eid,pid,after={'occurred_at':data['occurred_at'],'colour':data['colour'],'attachment':bool(saved_attachment)})
        return {'id':eid,'entry':{k:v for k,v in data.items()},'attachment_sha256_12':saved_attachment,'notice':'Fictional diary entry saved. Photographs are documentation only; they do not diagnose infection.'}
    def list_sputum(self,user,pid,page=1,page_size=15):
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            total=c.execute('SELECT COUNT(*) AS n FROM sputum_entries WHERE patient_id=?',(pid,)).fetchone()['n']
            rows=[]
            for r in c.execute('SELECT * FROM sputum_entries WHERE patient_id=? ORDER BY occurred_at DESC,id DESC LIMIT ? OFFSET ?',(pid,page_size,(page-1)*page_size)).fetchall():
                d=dict(r);att=c.execute('SELECT id,filename,media_type,size,sha256 FROM attachments WHERE entry_id=?',(r['id'],)).fetchone();d['attachment']=dict(att) if att else None
                rows.append(d)
        return {'items':rows,'total':total,'page':page,'page_size':page_size,'notice':'Patient-reported fictional diary. Colour/volume photos are records, not diagnostic reads.'}
    def review_sputum(self,user,eid,note):
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM sputum_entries WHERE id=?',(eid,)).fetchone()
            if not row:raise HTTPException(404,'Diary entry not found.')
            self.require_assigned(user,row['patient_id'])
            if row['reviewed_at']:raise HTTPException(409,'Entry already reviewed; the demo keeps review notes immutable.')
            c.execute('UPDATE sputum_entries SET reviewed_at=?,reviewed_by=?,review_note=? WHERE id=?',(stamp(),user['username'],note,eid))
            self.audit(c,user,'reviewed','sputum_entry',eid,row['patient_id'],after={'review_note':note})
        return {'id':eid,'reviewed':True}
    def attachment(self,user,aid):
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM attachments WHERE id=?',(aid,)).fetchone()
            if not row:raise HTTPException(404,'Attachment not found.')
            self.require_assigned(user,row['patient_id'])
            if hashlib.sha256(row['data']).hexdigest()!=row['sha256']:raise HTTPException(500,'Attachment checksum mismatch; record quarantined.')
            return row
    # ---------- activity / adherence aggregation ----------
    def activity(self,user,pid):
        self.require_assigned(user,pid);detail=self.services.registry.detail(pid)
        manual=[{'at':o['created_at'],'adherence':o['adherence'],'symptom_score':o['symptom_score'],'note':o['note'],'source':'manual (fictional)'} for o in self.services.registry.detail(pid)['observations']]
        days={}
        def bucket(when,key,value):
            day=when[:10];days.setdefault(day,{'date':day})[key]=value
        for o in manual:bucket(o['at'],'adherence_manual',o['adherence']);bucket(o['at'],'symptom_manual',o['symptom_score'])
        readings=[]
        with self.store.connect() as c:
            for r in c.execute("SELECT observed_at,metric,value FROM device_readings WHERE patient_id=? AND metric IN ('steps','heart_rate') ORDER BY observed_at DESC LIMIT 2000",(pid,)):
                readings.append(dict(r));bucket(r['observed_at'],f"{r['metric']}_simulated_device",r['value'])
        series=sorted(days.values(),key=lambda d:d['date'])
        latest=detail['latest_monitoring']
        return {'series':series,'manual_entries':len(manual),'device_samples':len(readings),
                'latest_monitoring':latest,'missing':'Gaps between hand-entered fictional observations are expected; the diary is event-driven, not continuous telemetry.',
                'sources':'manual fictional review entries + simulated device readings + persisted monitoring snapshots. None are live wearable telemetry.'}
    # ---------- audit trail ----------
    def audit(self,c,user,action,entity,entity_id,patient_id,before=None,after=None):
        c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,before_json,after_json) VALUES (?,?,?,?,?,?,?,?,?)',
                  (stamp(),user['username'],user['role'],action,entity,str(entity_id) if entity_id is not None else None,patient_id,
                   json.dumps(before) if before is not None else None,json.dumps(after) if after is not None else None))
    def audit_events(self,user,pid,limit=100):
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            rows=[dict(r) for r in c.execute('SELECT id,created_at,actor,role,action,entity,entity_id,before_json,after_json FROM audit_events WHERE patient_id=? ORDER BY id DESC LIMIT ?',(pid,limit))]
        return {'events':rows,'note':'Immutable demo audit trail. Original submissions and timestamps are preserved in snapshots.'}
    def require_patient(self,user):
        if user['role']!='patient':raise HTTPException(403,'This area is for the patient demo account only.')
    def require_doctor(self,user):
        if user['role']!='doctor':raise HTTPException(403,'Only the doctor demo account can perform this action.')
    def own_pid(self,user):
        self.require_patient(user)
        if not user['patient_id']:raise HTTPException(403,'No linked synthetic twin for this account.')
        return user['patient_id']
    # ---------- daily wellbeing logs ----------
    def add_daily_log(self,user,data):
        pid=self.own_pid(user);at=stamp()
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO daily_logs(patient_id,entry_date,water_ml,food_notes,activity_minutes,sleep_hours,sleep_quality,wellbeing,notes,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                          (pid,data['entry_date'],data['water_ml'],data['food_notes'],data['activity_minutes'],data['sleep_hours'],data['sleep_quality'],data['wellbeing'],data['notes'],user['username'],at,at))
            lid=cur.lastrowid
            self.audit(c,user,'created','daily_log',lid,pid,after={'entry_date':data['entry_date'],'water_ml':data['water_ml'],'activity_minutes':data['activity_minutes'],'sleep_hours':data['sleep_hours'],'wellbeing':data['wellbeing']})
        return {'id':lid,'notice':'Daily log saved. Doctor can review it; it is documentation, not a diagnosis.'}
    def list_daily_logs(self,user,pid=None,page=1,page_size=30):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:self.require_assigned(user,pid)
        with self.store.connect() as c:
            total=c.execute('SELECT COUNT(*) AS n FROM daily_logs WHERE patient_id=?',(pid,)).fetchone()['n']
            rows=[dict(r) for r in c.execute('SELECT * FROM daily_logs WHERE patient_id=? ORDER BY entry_date DESC,id DESC LIMIT ? OFFSET ?',(pid,page_size,(page-1)*page_size))]
        return {'items':rows,'total':total,'page':page,'page_size':page_size,'patient_id':pid,'viewer_is_patient':user['role']=='patient',
                'note':'Patient-reported fictional wellbeing log. Entries are documentation, not telemetry.'}
    def edit_daily_log(self,user,lid,data):
        pid=self.own_pid(user);at=stamp()
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM daily_logs WHERE id=?',(lid,)).fetchone()
            if not row or row['patient_id']!=pid:raise HTTPException(404,'Daily log entry not found for this account.')
            before=dict(row)
            c.execute('UPDATE daily_logs SET water_ml=?,food_notes=?,activity_minutes=?,sleep_hours=?,sleep_quality=?,wellbeing=?,notes=?,edited=1,updated_at=? WHERE id=?',
                      (data['water_ml'],data['food_notes'],data['activity_minutes'],data['sleep_hours'],data['sleep_quality'],data['wellbeing'],data['notes'],at,lid))
            after=dict(c.execute('SELECT * FROM daily_logs WHERE id=?',(lid,)).fetchone())
            self.audit(c,user,'edited','daily_log',lid,pid,before={k:before[k] for k in ('water_ml','food_notes','activity_minutes','sleep_hours','sleep_quality','wellbeing','notes','created_at')},
                       after={k:after[k] for k in ('water_ml','food_notes','activity_minutes','sleep_hours','sleep_quality','wellbeing','notes')})
        return {'id':lid,'edited':True,'notice':'Correction saved. The original submission stays in the audit trail.'}
    def review_daily_log(self,user,lid,note):
        self.require_doctor(user)
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM daily_logs WHERE id=?',(lid,)).fetchone()
            if not row:raise HTTPException(404,'Daily log entry not found.')
            self.require_assigned(user,row['patient_id'])
            if row['reviewed_at']:raise HTTPException(409,'Already reviewed; demo keeps reviews immutable.')
            c.execute('UPDATE daily_logs SET reviewed_by=?,reviewed_at=?,review_note=? WHERE id=?',(user['username'],stamp(),note,lid))
            self.audit(c,user,'reviewed','daily_log',lid,row['patient_id'],after={'review_note':note})
        return {'id':lid,'reviewed':True}
    # ---------- plan medications (doctor-authored) ----------
    def list_medications(self,user,pid=None):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:pass
        self.require_assigned(user,pid)
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            meds=[dict(r) for r in c.execute('SELECT id,patient_id,name,dose,frequency,added_by,created_at,retired FROM plan_medications WHERE patient_id=? AND retired=0 ORDER BY id',(pid,))]
        return {'medication_options':meds,'note':'Clinician-documented demo medication list. Patients only report adherence; they cannot edit prescriptions.'}
    def add_medication(self,user,pid,data):
        self.require_doctor(user);self.require_assigned(user,pid);at=stamp()
        with self.store.connect() as c:
            exists=c.execute('SELECT 1 FROM plan_medications WHERE patient_id=? AND retired=0 AND LOWER(name)=LOWER(?)',(pid,data['name'])).fetchone()
            if exists:raise HTTPException(409,f"Medication '{data['name']}' is already on the documented list.")
            cur=c.execute('INSERT INTO plan_medications(patient_id,name,dose,frequency,added_by,created_at) VALUES (?,?,?,?,?,?)',
                          (pid,data['name'],data['dose'],data['frequency'],user['username'],at))
            self.audit(c,user,'added','plan_medication',cur.lastrowid,pid,after={'name':data['name'],'dose':data['dose'],'frequency':data['frequency']})
        return {'id':cur.lastrowid,'notice':'Demo medication documented (text record only — nothing is prescribed or automated).'}
    def add_adherence(self,user,data):
        pid=self.own_pid(user);at=stamp()
        with self.store.connect() as c:
            med=c.execute('SELECT * FROM plan_medications WHERE id=? AND patient_id=? AND retired=0',(data['medication_id'],pid)).fetchone()
            if not med:raise HTTPException(422,'Unknown medication id for this account. Adherence can only reference clinician-documented medication.')
            if not data['as_prescribed'] and not (data.get('missed_reason') or '').strip():
                raise HTTPException(422,'When a dose is missed, a short reason/note is required.')
            cur=c.execute('INSERT INTO med_adherence(patient_id,medication_id,as_prescribed,taken_at,missed_reason,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?)',
                          (pid,data['medication_id'],1 if data['as_prescribed'] else 0,data['taken_at'],data.get('missed_reason'),data.get('note'),user['username'],at))
            self.audit(c,user,'reported','med_adherence',cur.lastrowid,pid,after={'medication':med['name'],'as_prescribed':bool(data['as_prescribed']),'taken_at':data['taken_at']})
        return {'id':cur.lastrowid,'notice':'Adherence report saved (patient-reported, fictional).'}
    def list_adherence(self,user,pid=None,page=1,page_size=30):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:pass
        self.require_assigned(user,pid)
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            total=c.execute('SELECT COUNT(*) AS n FROM med_adherence WHERE patient_id=?',(pid,)).fetchone()['n']
            rows=[dict(r) for r in c.execute('''SELECT a.*,m.name AS medication_name,m.dose,m.frequency FROM med_adherence a
                JOIN plan_medications m ON m.id=a.medication_id WHERE a.patient_id=? ORDER BY a.taken_at DESC LIMIT ? OFFSET ?''',(pid,page_size,(page-1)*page_size))]
        return {'items':rows,'total':total,'page':page,'page_size':page_size}
    # ---------- clinical documents ----------
    BAD_EXT=('.exe','.bat','.cmd','.sh','.js','.msi','.apk','.com','.scr')
    MAGIC={b'%PDF':'application/pdf',b'\x89PNG':'image/png',b'\xff\xd8\xff':'image/jpeg'}
    def upload_document(self,user,pid,data):
        self.require_doctor(user);self.require_assigned(user,pid);at=stamp()
        fn=data['filename'].lower()
        if any(fn.endswith(e) for e in self.BAD_EXT):raise HTTPException(422,'Executable or unsafe file names are rejected. Allowed: PDF, PNG, JPEG, WEBP, plain text.')
        raw=base64.b64decode(data['data_base64'],validate=True)
        if not raw:raise HTTPException(422,'Empty file.')
        if len(raw)>1_572_864:raise HTTPException(422,'Document exceeds the 1.5 MB demo limit.')
        media=data['media_type']
        if media in self.MAGIC.values():
            ok=False
            for sig,mime in self.MAGIC.items():
                if raw.startswith(sig):ok=(mime==media);break
            if not ok:raise HTTPException(422,'File signature does not match the declared type; upload rejected.')
        digest=hashlib.sha256(raw).hexdigest()
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO documents(patient_id,title,doc_type,doc_date,notes,filename,media_type,size,sha256,data,uploaded_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                          (pid,data['title'],data['doc_type'],data['doc_date'],data['notes'],data['filename'],media,len(raw),digest,raw,user['username'],at))
            self.audit(c,user,'uploaded','document',cur.lastrowid,pid,after={'title':data['title'],'type':data['doc_type'],'size':len(raw),'sha256':digest})
        return {'id':cur.lastrowid,'sha256_12':digest[:12],'notice':'Document stored as a demo record. Documents are record-keeping, never AI diagnosis.'}
    def list_documents(self,user,pid=None):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:pass
        self.require_assigned(user,pid)
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            rows=[dict(r) for r in c.execute('SELECT id,patient_id,title,doc_type,doc_date,notes,filename,media_type,size,sha256,uploaded_by,created_at FROM documents WHERE patient_id=? ORDER BY id DESC',(pid,))]
        return {'items':rows,'note':'Documents shared with the linked patient only. Metadata carries SHA-256 provenance.'}
    def get_document(self,user,did):
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM documents WHERE id=?',(did,)).fetchone()
            if not row:raise HTTPException(404,'Document not found.')
            self.require_assigned(user,row['patient_id'])
            if hashlib.sha256(row['data']).hexdigest()!=row['sha256']:raise HTTPException(500,'Document checksum mismatch; record quarantined.')
        return row
    def delete_document(self,user,did):
        self.require_doctor(user)
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM documents WHERE id=?',(did,)).fetchone()
            if not row:raise HTTPException(404,'Document not found.')
            self.require_assigned(user,row['patient_id'])
            keep={k:row[k] for k in ('patient_id','title','doc_type','filename','size','sha256','uploaded_by','created_at')}
            c.execute('DELETE FROM documents WHERE id=?',(did,))
            self.audit(c,user,'deleted','document',did,row['patient_id'],before=keep)
        return {'deleted':True,'notice':'Record removed; metadata retained in the audit trail.'}
    # ---------- follow-ups ----------
    def create_follow_up(self,user,pid,data):
        self.require_doctor(user);self.require_assigned(user,pid);at=stamp()
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO follow_ups(patient_id,doctor,instructions,due_at,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
                          (pid,user['username'],data['instructions'],data['due_at'],'scheduled',at,at))
            self.audit(c,user,'scheduled','follow_up',cur.lastrowid,pid,after={'instructions':data['instructions'][:200],'due_at':data['due_at']})
        return {'id':cur.lastrowid,'notice':'Follow-up instruction saved and shared with the linked patient.'}
    def list_follow_ups(self,user,pid=None,include_history=True):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:pass
        self.require_assigned(user,pid)
        if pid:self.require_assigned(user,pid)
        ids=self.assigned_ids(user)
        with self.store.connect() as c:
            if pid:
                rows=[dict(r) for r in c.execute('SELECT * FROM follow_ups WHERE patient_id=? ORDER BY status!="scheduled", due_at IS NULL, due_at',(pid,))]
            else:
                marks=','.join('?' for _ in ids) or "''"
                rows=[dict(r) for r in c.execute(f'SELECT * FROM follow_ups WHERE patient_id IN ({marks}) ORDER BY status!="scheduled", due_at IS NULL, due_at LIMIT 100',tuple(ids))] if ids else []
        if not include_history:rows=[r for r in rows if r['status']=='scheduled']
        return {'items':rows,'note':'Doctor-issued demo instructions. They remind and inform; they do not change treatment automatically.'}
    def complete_follow_up(self,user,fid,status):
        self.require_doctor(user)
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM follow_ups WHERE id=?',(fid,)).fetchone()
            if not row:raise HTTPException(404,'Follow-up not found.')
            self.require_assigned(user,row['patient_id'])
            if row['status']!='scheduled':raise HTTPException(409,f"Follow-up is already '{row['status']}'; demo keeps completion immutable.")
            at=stamp()
            c.execute("UPDATE follow_ups SET status=?,updated_at=?,completed_at=?,completed_by=? WHERE id=?",(status,at,at if status=='completed' else None,user['username'] if status=='completed' else None,fid))
            self.audit(c,user,status,'follow_up',fid,row['patient_id'],before={'status':'scheduled'},after={'status':status})
        return {'id':fid,'status':status}
    # ---------- patient home aggregate ----------
    def patient_home(self,user):
        pid=self.own_pid(user)
        detail=self.services.registry.detail(pid)
        plan=self.get_plan(user,pid)
        fu=self.list_follow_ups(user,pid)
        docs=self.list_documents(user,pid)['items']
        logs=self.list_daily_logs(user,page_size=14)['items']
        adh=self.list_adherence(user,page_size=14)['items']
        today=stamp()[:10]
        logged_today=any(l['entry_date']==today for l in logs)
        streak=0;day=today
        from datetime import timedelta as _td
        dates={l['entry_date'] for l in logs}
        while day in dates:
            streak+=1;day=(datetime.fromisoformat(day)-_td(days=1)).date().isoformat()
        now=stamp()
        upcoming=[f for f in fu['items'] if f['status']=='scheduled' and (not f['due_at'] or f['due_at'][:10]>=now[:10])]
        overdue=[f for f in fu['items'] if f['status']=='scheduled' and f['due_at'] and f['due_at'][:10]<now[:10]]
        latest=logs[0] if logs else None
        return {'patient_id':pid,'profile':detail['profile'],'baseline':detail['baseline'],
                'logged_today':logged_today,'streak_days':streak,'recent_logs':logs[:7],'recent_adherence':adh[:7],
                'care_plan':plan['plan'],'follow_ups':upcoming,'overdue_follow_ups':overdue,
                'documents_count':len(docs),'documents_recent':docs[:3],
                'latest_review':{'reviewed':bool(latest and latest['reviewed_at']),'reviewed_by':(latest or {}).get('reviewed_by'),'reviewed_at':(latest or {}).get('reviewed_at')} if latest else {'reviewed':False},
                'note':'Everything here is synthetic demo data shared with the assigned doctor. For emergencies, follow your real clinician-given action plan — this app never overrides it.'}
