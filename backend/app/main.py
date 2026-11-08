"""FastAPI application. Offline by default; all patients synthetic."""
import asyncio, json, os
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends, Header, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from backend.app.config import DB_PATH
from backend.app.engine import TwinEngine, now
from backend.app.enhanced.services import Services
from backend.app.enhanced.routes import make_router
from backend.app.model48_v3_api import make_v3_router
from backend.app.workspace.service import Workspace
from backend.app.workspace.routes import make_workspace_router
from backend.app.research.routes import router as research_router, bind_service as bind_research_service

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


def create_app(db_path=None,enhanced_settings=None,background_tasks=True):
    hub=Hub()
    @asynccontextmanager
    async def lifespan(app):
        app.state.engine=await asyncio.to_thread(TwinEngine,db_path or DB_PATH)
        app.state.enhanced=Services(app.state.engine,enhanced_settings)
        app.state.workspace=Workspace(app.state.engine,app.state.enhanced)
        app.state.research=await asyncio.to_thread(bind_research_service,app.state.engine.store)
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
    app=FastAPI(title='PranaGuard synthetic COPD twin API',version='0.4.0',lifespan=lifespan,
                description='Research prototype; not clinically validated. All patient data are fictional/simulated. Optional current modelled city context is excluded from frozen ML inputs. No real patient monitoring or physical device integration.')
    origins=[s.strip() for s in os.getenv('PRANAGUARD_CORS_ORIGINS','*').split(',') if s.strip()]
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['*'],allow_headers=['Content-Type','X-Demo-Token','X-Device-Token'])
    app.include_router(make_router(authorize,hub))
    app.include_router(make_v3_router())
    app.include_router(make_workspace_router())
    app.include_router(research_router)
    def engine(request:Request):return request.app.state.engine
    @app.exception_handler(KeyError)
    async def key_error(request,exc):return JSONResponse(status_code=404,content={'detail':str(exc)})
    @app.exception_handler(ValueError)
    async def value_error(request,exc):return JSONResponse(status_code=422,content={'detail':str(exc)})
    @app.get('/api/health')
    def health(e:TwinEngine=Depends(engine)):
        return {'status':'ok','synthetic':True,'model_version':e.bundle['version']}
    @app.get('/api/overview')
    def overview(e:TwinEngine=Depends(engine)):return e.cohort()
    @app.get('/api/patients')
    def patients(q:str='',risk:Literal['all','low','elevated','high']='all',e:TwinEngine=Depends(engine)):
        cohort=e.cohort()['patients']
        return {'patients':[p for p in cohort if (q.lower() in (p['display_name']+p['patient_id']+p['city']).lower()) and (risk=='all' or p['risk_category']==risk)]}
    @app.get('/api/patients/{pid}')
    def patient(pid:str,version:int|None=Query(default=None,ge=1),e:TwinEngine=Depends(engine)):return e.patient(pid,version)
    @app.get('/api/patients/{pid}/history')
    def history(pid:str,limit:int=Query(default=48,ge=2,le=168),e:TwinEngine=Depends(engine)):return e.history(pid,limit)
    @app.get('/api/patients/{pid}/versions')
    def versions(pid:str,e:TwinEngine=Depends(engine)):
        e.patient(pid);return {'versions':e.store.versions(pid)}
    @app.get('/api/patients/{pid}/explanation')
    def explanation(pid:str,horizon:int=Query(default=72),version:int|None=None,e:TwinEngine=Depends(engine)):
        if horizon not in (24,48,72):raise HTTPException(422,'Horizon must be 24, 48 or 72 hours.')
        return e.explain(pid,horizon,version)
    @app.post('/api/patients/{pid}/scenarios',dependencies=[Depends(authorize)])
    def scenario(pid:str,body:Scenario,e:TwinEngine=Depends(engine)):return e.scenario(pid,body.model_dump())
    @app.get('/api/patients/{pid}/scenarios')
    def scenarios(pid:str,e:TwinEngine=Depends(engine)):
        e.patient(pid)
        with e.store.connect() as c:
            return {'scenarios':[{'id':r['id'],'state_version':r['state_version'],'created_at':r['created_at'],'assumptions':json.loads(r['assumptions']),'result':json.loads(r['result'])} for r in c.execute('SELECT * FROM scenarios WHERE patient_id=? ORDER BY id DESC LIMIT 20',(pid,))]}
    @app.get('/api/alerts')
    def alerts(patient_id:str|None=None,e:TwinEngine=Depends(engine)):return {'alerts':e.store.alerts(patient_id)}
    @app.patch('/api/alerts/{alert_id}',dependencies=[Depends(authorize)])
    async def update_alert(alert_id:int,body:AlertUpdate,e:TwinEngine=Depends(engine)):
        with e.store.connect() as c:
            row=c.execute('SELECT * FROM alerts WHERE id=?',(alert_id,)).fetchone()
            if not row:raise HTTPException(404,'Alert not found')
            if row['status']=='resolved':raise HTTPException(409,'Resolved alert is immutable. A later high-risk state may create a new alert.')
            c.execute('UPDATE alerts SET status=?,note=?,updated_at=? WHERE id=?',(body.status,body.note,now(),alert_id))
        await asyncio.to_thread(app.state.enhanced.notifications.sync_legacy)
        await hub.broadcast({'type':'alert_updated','alert_id':alert_id})
        return {'alert':next(a for a in e.store.alerts() if a['id']==alert_id)}
    @app.get('/api/patients/{pid}/interventions')
    def interventions(pid:str,e:TwinEngine=Depends(engine)):
        e.patient(pid);return {'interventions':e.store.interventions(pid)}
    @app.post('/api/patients/{pid}/interventions',dependencies=[Depends(authorize)])
    def add_intervention(pid:str,body:Intervention,e:TwinEngine=Depends(engine)):
        with e.lock:
            state=e.patient(pid)
            with e.store.connect() as c:
                cur=c.execute('INSERT INTO interventions(patient_id,kind,note,created_at,state_version) VALUES (?,?,?,?,?)',(pid,body.kind,body.note,now(),state['version']))
                iid=cur.lastrowid
        return {'intervention':next(i for i in e.store.interventions(pid) if i['id']==iid),'notice':'Logged only. This does not change the patient state or imply a treatment effect.'}
    @app.get('/api/model48/study')
    def model48_study():
        from backend.app.model48_study import study_report
        return study_report()
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
