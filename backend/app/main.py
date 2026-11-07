"""FastAPI application. Offline by default; all patients synthetic."""
import asyncio, json, os, re
from contextlib import asynccontextmanager, contextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends, Header, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from backend.app.config import DB_PATH
from backend.app.engine import TwinEngine, now
from backend.app.enhanced.services import Services
from backend.app.enhanced.routes import make_router
from backend.app.portal import router as portal_router, current, require_full_historical_assignment, authorize_patient, begin_authorized_write

class StrictModel(BaseModel):model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
class Step(StrictModel):hours:int=Field(default=1,ge=1,le=72)
class Reset(StrictModel):hour:int|None=Field(default=None,ge=72);prime_hours:int=Field(default=24,ge=0,le=48)
class Scenario(StrictModel):
    pm25_change_pct:float=Field(default=-30,ge=-80,le=100)
    adherence:float=Field(default=.95,ge=0,le=1)
    activity_multiplier:float=Field(default=1,ge=.5,le=1.5)
class AlertUpdate(StrictModel):status:Literal['acknowledged','resolved'];note:str=Field(default='',max_length=2000)
class Intervention(StrictModel):kind:Literal['clinical_review','contact','adherence_review','exposure_review','other'];note:str=Field(min_length=3,max_length=2000)

async def authorize(x_demo_token:str|None=Header(default=None)):
    configured=os.getenv('PRANAGUARD_ADMIN_TOKEN','')
    if configured:
        import secrets
        if not x_demo_token or not secrets.compare_digest(configured,x_demo_token):raise HTTPException(401,'Demo admin token required (X-Demo-Token).')

class Hub:
    def __init__(self):self.clients=set()
    async def broadcast(self,message):
        for socket in list(self.clients):
            try:await socket.send_json(message)
            except Exception:self.clients.discard(socket)



def bootstrap_demo_portal(engine):
    """Idempotently provision synthetic-only demo accounts from password hashes."""
    raw = os.getenv("PRANAGUARD_DEMO_BOOTSTRAP", "")
    if not raw:
        return
    cfg = json.loads(raw)
    doctor = cfg["doctor"]
    patients = cfg["patients"]
    if len(patients) < 5:
        raise RuntimeError("Demo bootstrap requires at least five synthetic patients")
    if not doctor["password_hash"].startswith("scrypt$"):
        raise RuntimeError("Invalid doctor password hash")
    for item in patients:
        profile = engine.profiles.get(item["patient_id"])
        if not profile or profile.get("synthetic") is not True:
            raise RuntimeError("Demo bootstrap may link only existing synthetic patient records")
        if not item["password_hash"].startswith("scrypt$"):
            raise RuntimeError("Invalid patient password hash")
    with engine.store.connect() as c:
        c.execute(
            "INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?) ON CONFLICT(username) DO NOTHING",
            (doctor["username"], doctor["password_hash"], "doctor", now()),
        )
        d = c.execute("SELECT id,role FROM portal_users WHERE username=?", (doctor["username"],)).fetchone()
        if not d or d["role"] != "doctor":
            raise RuntimeError("Demo doctor username is already used by a different account")
        for item in patients:
            stored = c.execute('SELECT profile FROM patients WHERE patient_id=?', (item['patient_id'],)).fetchone()
            if not stored or json.loads(stored['profile']).get('synthetic') is not True:
                raise RuntimeError('Demo bootstrap requires existing synthetic records')
            c.execute(
                "INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?) ON CONFLICT(username) DO NOTHING",
                (item["username"], item["password_hash"], "patient", now()),
            )
            p = c.execute("SELECT id,role FROM portal_users WHERE username=?", (item["username"],)).fetchone()
            if not p or p["role"] != "patient":
                raise RuntimeError("Demo patient username is already used by a different account")
            c.execute(
                "INSERT OR IGNORE INTO patient_user_links(user_id,patient_id) VALUES (?,?)",
                (p["id"], item["patient_id"]),
            )
            link = c.execute("SELECT patient_id FROM patient_user_links WHERE user_id=?", (p["id"],)).fetchone()
            if not link or link["patient_id"] != item["patient_id"]:
                raise RuntimeError("Demo patient account is already linked to a different record")
            c.execute(
                "INSERT OR IGNORE INTO doctor_patient_assignments(doctor_id,patient_id) VALUES (?,?)",
                (d["id"], item["patient_id"]),
            )
        if cfg.get("assign_cohort") is True:
            for pid, profile in engine.profiles.items():
                stored = c.execute('SELECT profile FROM patients WHERE patient_id=?', (pid,)).fetchone()
                if profile.get('synthetic') is not True or not stored or json.loads(stored['profile']).get('synthetic') is not True:
                    raise RuntimeError('Cohort assignment requires matching existing synthetic records')
                c.execute('INSERT OR IGNORE INTO doctor_patient_assignments(doctor_id,patient_id) VALUES (?,?)', (d['id'], pid))

def create_app(db_path=None,enhanced_settings=None,background_tasks=True, legacy_demo=None):
    if legacy_demo is None: legacy_demo = os.getenv("PRANAGUARD_UNSAFE_LEGACY_DEMO", "0") == "1"
    hub=Hub()
    @asynccontextmanager
    async def lifespan(app):
        app.state.engine=await asyncio.to_thread(TwinEngine,db_path or DB_PATH)
        await asyncio.to_thread(bootstrap_demo_portal, app.state.engine)
        app.state.enhanced=Services(app.state.engine,enhanced_settings)
        async def enhanced_loop():
            while True:
                await asyncio.sleep(1)
                try:await app.state.enhanced.tick(app)
                except Exception as exc:app.state.enhanced.failure(exc)
        async def replay_loop():
            while True:
                await asyncio.sleep(2)
                engine=app.state.engine
                if engine.running:
                    try:
                        result=await asyncio.to_thread(engine.step,1)
                        await hub.broadcast({'type':'twin_updated','replay':result})
                    except Exception as e:
                        engine.running=False;await hub.broadcast({'type':'replay_stopped','detail':str(e)})
        tasks=[asyncio.create_task(replay_loop()),asyncio.create_task(enhanced_loop())] if background_tasks else []
        try:yield
        finally:
            for task in tasks:task.cancel()
            for task in tasks:
                try:await task
                except asyncio.CancelledError:pass
    app=FastAPI(title='PranaGuard synthetic COPD twin API',version='0.2.0',lifespan=lifespan,
                description='Research prototype; not clinically validated. All patient data are fictional/simulated. Optional current modelled city context is excluded from frozen ML inputs. No real patient monitoring or physical device integration.')
    origins=[s.strip() for s in os.getenv('PRANAGUARD_CORS_ORIGINS','*').split(',') if s.strip()]
    app.state.hub=hub
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['*'],allow_headers=['Content-Type','Authorization','X-Demo-Token','X-Device-Token'])
    # The original APIs include cohort-wide and unscoped registry operations.
    # Unscoped methods require a single-doctor DB and complete synthetic
    # assignment. Explicitly enumerated historical, registry and city routes
    # instead use the narrower policies below.
    @app.middleware('http')
    async def isolate_legacy(request, call_next):
        path = request.url.path
        # CORS preflight requests intentionally carry no bearer token. Let
        # CORSMiddleware answer them before applying API authentication/scope.
        if request.method == 'OPTIONS':
            response = await call_next(request)
            if path.startswith('/api/'):
                response.headers['Cache-Control'] = 'no-store'
            return response
        if path.startswith('/api/portal/'):
            if legacy_demo:
                return JSONResponse(status_code=404, content={'detail':'Portal unavailable in isolated legacy demo mode'})
        elif path.startswith('/api/') and path != '/api/health' and not legacy_demo:
            try:
                user = current(request, request.headers.get('authorization'))
                if user['role'] != 'doctor':
                    raise HTTPException(403, 'Doctor access required')
                request.state.research_doctor_id = user['id']
                request.state.research_user = user
                # These original twin endpoints operate on one explicit ID only.
                # Explicit registry, historical and city exceptions follow;
                # all other original/enhanced routes remain whole-workspace gated.
                per_patient={
                    ('GET',''),('GET','history'),('GET','versions'),('GET','explanation'),
                    ('GET','scenarios'),('POST','scenarios'),
                    ('GET','interventions'),('POST','interventions'),
                }
                match=re.fullmatch(r'/api/patients/([^/]+)(?:/([^/]+))?',path)
                scoped=match and (request.method,match.group(2) or '') in per_patient
                historical_cohort=request.method=='GET' and path=='/api/validation'
                scoped_cohort=request.method=='GET' and path in ('/api/overview','/api/patients')
                registry_match=re.fullmatch(r'/api/enhanced/registry/patients/([^/]+)(?:/([^/]+))?',path)
                registry_patient=registry_match and (request.method,registry_match.group(2) or '') in {
                    ('GET',''),('POST','observations'),('POST','reviews')}
                registry_collection=path=='/api/enhanced/registry/patients' and request.method in ('GET','POST')
                scoped_notifications=(request.method=='GET' and (path in ('/api/enhanced/notifications','/api/enhanced/notifications/counts') or re.fullmatch(r'/api/enhanced/notifications/[0-9]+',path))) or (request.method=='PATCH' and re.fullmatch(r'/api/enhanced/notifications/[0-9]+',path))
                scoped_alerts=(request.method=='GET' and path=='/api/alerts') or (request.method=='PATCH' and re.fullmatch(r'/api/alerts/[^/]+',path))
                city_context=(request.method=='GET' and re.fullmatch(r'/api/enhanced/environment/[^/]+',path)) or (request.method=='POST' and re.fullmatch(r'/api/enhanced/environment/[^/]+/refresh',path))
                with request.app.state.engine.store.connect() as c:
                    if scoped:
                        pid=match.group(1)
                        row=c.execute('SELECT p.profile FROM patients p JOIN doctor_patient_assignments a ON a.patient_id=p.patient_id WHERE p.patient_id=? AND a.doctor_id=?',(pid,user['id'])).fetchone()
                        if pid not in request.app.state.engine.profiles or not row or json.loads(row['profile']).get('synthetic') is not True:
                            raise HTTPException(404, 'Record not found')
                    elif registry_patient:
                        pid=registry_match.group(1)
                        row=c.execute('SELECT p.profile FROM patients p JOIN doctor_patient_assignments a ON a.patient_id=p.patient_id WHERE p.patient_id=? AND a.doctor_id=?',(pid,user['id'])).fetchone()
                        if not row or json.loads(row['profile']).get('synthetic') is not True:
                            raise HTTPException(404, 'Record not found')
                    elif registry_collection or city_context or scoped_alerts or scoped_notifications or scoped_cohort:
                        # The registry handler restricts lists and idempotent retries
                        # to this doctor. City-grid context contains no patient records; writes still
                        # require the optional legacy token in the handler.
                        pass
                    elif historical_cohort:
                        require_full_historical_assignment(c,request.app.state.engine,user['id'])
                        request.state.historical_cohort_only=True
                    else:
                        # Unscoped readers can otherwise pass the assignment check
                        # immediately before a different doctor registers a record.
                        # Until those operations are scoped, disallow them in
                        # multi-doctor databases, even when all rows are assigned.
                        # Administrative DB changes still require quiescing traffic.
                        doctors=c.execute("SELECT COUNT(*) FROM portal_users WHERE role='doctor'").fetchone()[0]
                        if doctors != 1:
                            raise HTTPException(403, 'Unscoped workspace operations require a single-doctor synthetic database')
                        rows = c.execute('SELECT patient_id,profile FROM patients').fetchall()
                        assigned = {r['patient_id'] for r in c.execute('SELECT patient_id FROM doctor_patient_assignments WHERE doctor_id=?', (user['id'],))}
                        if not rows or any(json.loads(r['profile']).get('synthetic') is not True or r['patient_id'] not in assigned for r in rows):
                            raise HTTPException(403, 'Research workspace requires assignment to every synthetic record')
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={'detail':exc.detail})
        response = await call_next(request)
        if path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response
    app.include_router(portal_router)
    app.include_router(make_router(authorize,hub))
    def engine(request:Request):return request.app.state.engine
    @app.exception_handler(KeyError)
    async def key_error(request,exc):return JSONResponse(status_code=404,content={'detail':str(exc)})
    @app.exception_handler(ValueError)
    async def value_error(request,exc):return JSONResponse(status_code=422,content={'detail':str(exc)})
    @app.get('/api/health')
    def health(e:TwinEngine=Depends(engine)):
        return {'status':'ok','synthetic':True,'model_version':e.bundle['version']}
    def doctor_cohort(request:Request,e:TwinEngine):
        doctor_id=getattr(request.state,'research_doctor_id',None)
        if doctor_id is None: # isolated unsafe legacy mode only
            return e.cohort()
        with e.store.connect() as c:
            # Assignment, synthetic classification, states, trends and alerts
            # share one SQLite read snapshot rather than a middleware ID check.
            c.execute('BEGIN')
            assigned={r['patient_id'] for r in c.execute("SELECT p.patient_id FROM patients p JOIN doctor_patient_assignments d ON d.patient_id=p.patient_id WHERE d.doctor_id=? AND json_type(p.profile,'$.synthetic')='true'",(doctor_id,))}
            ids=[pid for pid,profile in e.profiles.items() if profile.get('synthetic') is True and pid in assigned]
            result=e.cohort(ids,conn=c)
            complete=len(ids)==len(e.profiles) and bool(ids)
            doctors=c.execute("SELECT COUNT(*) FROM portal_users WHERE role='doctor'").fetchone()[0]
            whole_workspace=doctors==1 and c.execute("SELECT COUNT(*) FROM patients p WHERE json_type(p.profile,'$.synthetic') IS NOT 'true' OR NOT EXISTS (SELECT 1 FROM doctor_patient_assignments d WHERE d.doctor_id=? AND d.patient_id=p.patient_id)",(doctor_id,)).fetchone()[0]==0
            result['permissions']={'complete_historical_cohort':complete,'can_control_replay':whole_workspace}
            if not complete:
                # The global demo metadata includes another twin's identity/risk.
                result['replay']={**result['replay'],'demo':None}
            return result
    @app.get('/api/overview')
    def overview(request:Request,e:TwinEngine=Depends(engine)):
        return doctor_cohort(request,e)
    @app.get('/api/patients')
    def patients(request:Request,q:str='',risk:Literal['all','low','elevated','high']='all',e:TwinEngine=Depends(engine)):
        cohort=doctor_cohort(request,e)['patients']
        return {'patients':[p for p in cohort if (q.lower() in (p['display_name']+p['patient_id']+p['city']).lower()) and (risk=='all' or p['risk_category']==risk)]}
    def authorize_historical(c,request,e,pid):
        user=getattr(request.state,'research_user',None)
        if user is not None:  # isolated legacy demo deliberately has no portal identity
            authorize_patient(c,request,user,pid)
            if e.profiles.get(pid,{}).get('synthetic') is not True:
                raise HTTPException(404,'Record not found')

    @contextmanager
    def twin_snapshot(request,e,pid,write=False):
        with e.store.connect() as c:
            c.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            authorize_historical(c,request,e,pid)
            yield c

    @app.get('/api/patients/{pid}')
    def patient(pid:str,request:Request,version:int|None=Query(default=None,ge=1),e:TwinEngine=Depends(engine)):
        with twin_snapshot(request,e,pid) as c:return e.patient(pid,version,conn=c)
    @app.get('/api/patients/{pid}/history')
    def history(pid:str,request:Request,limit:int=Query(default=48,ge=2,le=168),e:TwinEngine=Depends(engine)):
        with twin_snapshot(request,e,pid) as c:return e.history(pid,limit,conn=c)
    @app.get('/api/patients/{pid}/versions')
    def versions(pid:str,request:Request,e:TwinEngine=Depends(engine)):
        with twin_snapshot(request,e,pid) as c:
            e.patient(pid,conn=c);return {'versions':e.store.versions(pid,conn=c)}
    @app.get('/api/patients/{pid}/explanation')
    def explanation(pid:str,request:Request,horizon:int=Query(default=72),version:int|None=None,e:TwinEngine=Depends(engine)):
        if horizon not in (24,48,72):raise HTTPException(422,'Horizon must be 24, 48 or 72 hours.')
        with twin_snapshot(request,e,pid) as c:return e.explain(pid,horizon,version,conn=c)
    @app.post('/api/patients/{pid}/scenarios',dependencies=[Depends(authorize)])
    def scenario(pid:str,body:Scenario,request:Request,e:TwinEngine=Depends(engine)):
        check=(lambda c:authorize_historical(c,request,e,pid)) if getattr(request.state,'research_user',None) is not None else None
        return e.scenario(pid,body.model_dump(),authorize=check)
    @app.get('/api/patients/{pid}/scenarios')
    def scenarios(pid:str,request:Request,e:TwinEngine=Depends(engine)):
        with twin_snapshot(request,e,pid) as c:
            e.patient(pid,conn=c)
            return {'scenarios':[{'id':r['id'],'state_version':r['state_version'],'created_at':r['created_at'],'assumptions':json.loads(r['assumptions']),'result':json.loads(r['result'])} for r in c.execute('SELECT * FROM scenarios WHERE patient_id=? ORDER BY id DESC LIMIT 20',(pid,))]}
    @app.get('/api/alerts')
    def alerts(request:Request,patient_id:str|None=None,e:TwinEngine=Depends(engine)):
        return {'alerts':e.store.alerts(patient_id,doctor_id=getattr(request.state,'research_doctor_id',None))}
    @app.patch('/api/alerts/{alert_id}',dependencies=[Depends(authorize)])
    async def update_alert(alert_id:int,body:AlertUpdate,request:Request,e:TwinEngine=Depends(engine)):
        doctor_id=getattr(request.state,'research_doctor_id',None)
        with e.store.connect() as c:
            # Check session and assignment under the same SQLite write lock.
            user=getattr(request.state,'research_user',None)
            if user is None: c.execute('BEGIN IMMEDIATE')  # isolated legacy demo
            else: begin_authorized_write(c,request,user)
            sql='SELECT a.*,p.profile FROM alerts a JOIN patients p ON p.patient_id=a.patient_id WHERE a.id=?'
            args=[alert_id]
            if doctor_id is not None:
                sql+=" AND json_type(p.profile,'$.synthetic')='true' AND EXISTS (SELECT 1 FROM doctor_patient_assignments d WHERE d.doctor_id=? AND d.patient_id=a.patient_id)"
                args.append(doctor_id)
            row=c.execute(sql,args).fetchone()
            if not row:raise HTTPException(404,'Alert not found')
            if row['status']=='resolved':raise HTTPException(409,'Resolved alert is immutable. A later high-risk state may create a new alert.')
            updated=now()
            c.execute('UPDATE alerts SET status=?,note=?,updated_at=? WHERE id=?',(body.status,body.note,updated,alert_id))
            result=dict(row);result.update(status=body.status,note=body.note,updated_at=updated)
            result['display_name']=json.loads(result.pop('profile'))['display_name'];result['synthetic']=True
        await asyncio.to_thread(app.state.enhanced.notifications.sync_legacy)
        await hub.broadcast({'type':'alert_updated','alert_id':alert_id})
        return {'alert':result}
    @app.get('/api/patients/{pid}/interventions')
    def interventions(pid:str,request:Request,e:TwinEngine=Depends(engine)):
        with twin_snapshot(request,e,pid) as c:
            e.patient(pid,conn=c);return {'interventions':e.store.interventions(pid,conn=c)}
    @app.post('/api/patients/{pid}/interventions',dependencies=[Depends(authorize)])
    def add_intervention(pid:str,body:Intervention,request:Request,e:TwinEngine=Depends(engine)):
        with e.lock:
            with twin_snapshot(request,e,pid,write=True) as c:
                state=e.patient(pid,conn=c)
                cur=c.execute('INSERT INTO interventions(patient_id,kind,note,created_at,state_version) VALUES (?,?,?,?,?)',(pid,body.kind,body.note,now(),state['version']))
                intervention=dict(c.execute('SELECT * FROM interventions WHERE id=?',(cur.lastrowid,)).fetchone())
        return {'intervention':intervention,'notice':'Logged only. This does not change the patient state or imply a treatment effect.'}
    @app.get('/api/validation')
    def validation(e:TwinEngine=Depends(engine)):return e.evaluation
    @app.get('/api/status')
    def status(e:TwinEngine=Depends(engine)):
        result=e.status();result['admin_token_required']=bool(os.getenv('PRANAGUARD_ADMIN_TOKEN',''));return result
    @app.get('/api/replay')
    def replay(e:TwinEngine=Depends(engine)):return e.replay_status()
    @app.post('/api/replay/step',dependencies=[Depends(authorize)])
    async def step(body:Step,e:TwinEngine=Depends(engine)):
        result=await asyncio.to_thread(e.step,body.hours);await hub.broadcast({'type':'twin_updated','replay':result});return result
    @app.post('/api/replay/start',dependencies=[Depends(authorize)])
    def start(e:TwinEngine=Depends(engine)):
        e.running=True;return e.replay_status()
    @app.post('/api/replay/pause',dependencies=[Depends(authorize)])
    def pause(e:TwinEngine=Depends(engine)):
        e.running=False;return e.replay_status()
    @app.post('/api/replay/reset',dependencies=[Depends(authorize)])
    async def reset(body:Reset,e:TwinEngine=Depends(engine)):
        def perform():
            with e.lock:
                target=body.hour if body.hour is not None else e.demo['start_hour']
                if target-body.prime_hours<72:raise ValueError('Primed replay must start after baseline calibration')
                e.reset(target-body.prime_hours)
                if body.prime_hours:e.step(body.prime_hours)
                return e.replay_status()
        result=await asyncio.to_thread(perform);await hub.broadcast({'type':'twin_updated','replay':result});return result
    @app.websocket('/api/ws')
    async def websocket(socket:WebSocket):
        # Browser WebSockets cannot safely provide our bearer header. Keep the
        # unscoped stream isolated; the authenticated workspace uses polling.
        if not legacy_demo:
            await socket.close(code=1008)
            return
        await socket.accept();hub.clients.add(socket)
        try:
            await socket.send_json({'type':'connected','synthetic':True})
            while True:
                data=await socket.receive_text()
                if data=='ping':await socket.send_json({'type':'pong'})
        except WebSocketDisconnect:pass
        finally:hub.clients.discard(socket)
    return app

app=create_app()
