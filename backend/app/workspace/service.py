"""Care workspace service. Demo-only identities (documented passwords, local PBKDF2 hashes,
expiring bearer sessions). This is NOT production identity/RBAC; claims stay honest."""
import base64, hashlib, json, secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

def utcnow():return datetime.now(timezone.utc)
def stamp():return utcnow().isoformat()

SESSION_HOURS=12
LOGIN_FAILURE_LIMIT=5
LOGIN_FAILURE_WINDOW_MINUTES=15
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
    # ---------- authentication ----------
    def login(self,username,password):
        normalized=username.strip().lower()
        username_hash=hashlib.sha256(normalized.encode()).hexdigest()
        failure_status=None
        result=None
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            now=stamp()
            failure=c.execute('SELECT * FROM care_login_failures WHERE username_hash=?',(username_hash,)).fetchone()
            active=failure is not None and failure['window_expires_at']>now
            if active and failure['failure_count']>=LOGIN_FAILURE_LIMIT:
                failure_status=429
            else:
                if failure is not None and not active:
                    c.execute('DELETE FROM care_login_failures WHERE username_hash=?',(username_hash,))
                row=c.execute('SELECT * FROM care_users WHERE username=?',(normalized,)).fetchone()
                valid=bool(row and secrets.compare_digest(row['pass_hash'],hash_password(password,row['salt'])))
                if not valid:
                    count=(failure['failure_count']+1) if active else 1
                    expires=(failure['window_expires_at'] if active else (utcnow()+timedelta(minutes=LOGIN_FAILURE_WINDOW_MINUTES)).isoformat())
                    c.execute('INSERT OR REPLACE INTO care_login_failures(username_hash,failure_count,window_expires_at) VALUES (?,?,?)',(username_hash,count,expires))
                    failure_status=429 if count>=LOGIN_FAILURE_LIMIT else 401
                else:
                    c.execute('DELETE FROM care_login_failures WHERE username_hash=?',(username_hash,))
                    token='pgw_'+secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
                    c.execute('DELETE FROM care_sessions WHERE username=? AND expires_at<?',(row['username'],now))
                    c.execute('INSERT INTO care_sessions VALUES (?,?,?,?)',(digest,row['username'],now,(utcnow()+timedelta(hours=SESSION_HOURS)).isoformat()))
                    result={'token':token,'user':self.public_user(row)}
        if failure_status==429:
            raise HTTPException(429,'Too many failed sign-in attempts. Try again after the 15-minute lockout window.')
        if failure_status==401:
            raise HTTPException(401,'Incorrect demo username or password.')
        return result
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
