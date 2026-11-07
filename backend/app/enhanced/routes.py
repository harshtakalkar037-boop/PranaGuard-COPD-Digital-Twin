"""Typed REST extension; original REST/WebSocket routes are retained."""
import asyncio, os
from typing import Literal
from fastapi import APIRouter,Depends,Header,Query,Request
from backend.app.enhanced.schemas import Registration,AssociateDevice,SimulationControl,Ingestion,Observation,NotificationUpdate,Review,EmptyBody
from backend.app.enhanced.settings import CITIES
from backend.app.enhanced.provenance import provenance

def make_router(authorize,hub):
    r=APIRouter(prefix='/api/enhanced',tags=['Enhanced synthetic demonstration'])
    def services(request:Request):return request.app.state.enhanced
    write=[Depends(authorize)]
    async def changed(kind='enhanced_updated',**kwargs):await hub.broadcast({'type':kind,**kwargs})
    def mutation_authorizer(request,pid=None):
        if os.getenv('PRANAGUARD_REQUIRE_WORKSPACE_AUTH','0')!='1':return None
        user=request.state.workspace_user
        header=request.headers.get('authorization','')
        token=header[7:] if header.startswith('Bearer ') else None
        def check(conn,actual_pid=None):
            request.app.state.workspace.authorize_write(conn,token,user['username'],actual_pid if actual_pid is not None else pid,full_cohort=True)
        return check
    @r.get('/status')
    def status(s=Depends(services)):return s.status()
    @r.get('/registry/patients')
    def patients(q:str=Query(default='',max_length=100),city:str|None=None,status:Literal['historical_twin','baseline_not_started','collecting_baseline','baseline_collected_no_model']|None=None,risk:Literal['low','elevated','high','unavailable']|None=None,sex:Literal['Female','Male','Other','Not specified']|None=None,s=Depends(services)):
        return s.registry.list(q,city,status,risk,sex)
    @r.post('/registry/patients',dependencies=write)
    async def register(body:Registration,request:Request,s=Depends(services)):
        user=getattr(request.state,'workspace_user',None)
        result=await asyncio.to_thread(s.registry.register,body,user['username'] if user else None,mutation_authorizer(request));await changed();return result
    @r.get('/registry/patients/{pid}')
    async def patient(pid:str,s=Depends(services)):
        result=await asyncio.to_thread(s.registry.detail,pid);result['environment']=await s.environment.get(result['profile']['city']);return result
    @r.post('/registry/patients/{pid}/observations',dependencies=write)
    async def observation(pid:str,body:Observation,request:Request,s=Depends(services)):
        result=await asyncio.to_thread(s.registry.observation,pid,body,mutation_authorizer(request,pid));await changed();return result
    @r.post('/registry/patients/{pid}/reviews',dependencies=write)
    async def review(pid:str,body:Review,request:Request,s=Depends(services)):
        result=await asyncio.to_thread(s.registry.review,pid,body,mutation_authorizer(request,pid));await changed();return result
    @r.get('/devices')
    def devices(patient_id:str|None=None,s=Depends(services)):return s.devices.list(patient_id)
    @r.post('/devices',dependencies=write)
    async def associate(body:AssociateDevice,request:Request,s=Depends(services)):
        result=await asyncio.to_thread(s.devices.associate,body,mutation_authorizer(request));await changed();return result
    @r.post('/devices/{did}/start',dependencies=write)
    async def start(did:str,body:SimulationControl,request:Request,s=Depends(services)):
        result=await asyncio.to_thread(s.devices.start,did,body.interval_seconds,mutation_authorizer(request));await changed();return result
    @r.post('/devices/{did}/stop',dependencies=write)
    async def stop(did:str,body:EmptyBody,request:Request,s=Depends(services)):
        result=await asyncio.to_thread(s.devices.stop,did,mutation_authorizer(request));await changed();return result
    @r.get('/devices/{did}/readings')
    def readings(did:str,limit:int=Query(default=100,ge=1,le=1000),s=Depends(services)):
        s.devices.require(did)
        with s.store.connect() as c:return {'readings':[dict(row) for row in c.execute('SELECT * FROM device_readings WHERE device_id=? ORDER BY id DESC LIMIT ?',(did,limit))]}
    @r.post('/ingestion',dependencies=write)
    async def ingestion(body:Ingestion,request:Request,x_device_token:str|None=Header(default=None),s=Depends(services)):
        result=await asyncio.to_thread(s.devices.ingest,body,x_device_token,mutation_authorizer(request))
        if not result['duplicate']:await changed(patient_id=body.patient_id)
        return result
    @r.get('/environment/cities')
    def cities():return {'cities':[{'name':name,**data} for name,data in CITIES.items()]}
    @r.get('/environment/{city}')
    async def environment(city:str,s=Depends(services)):return await s.environment.get(city)
    @r.post('/environment/{city}/refresh',dependencies=write)
    async def refresh(city:str,body:EmptyBody,s=Depends(services)):
        result=await s.environment.get(city,refresh=True);await changed();return result
    @r.get('/notifications/counts')
    def counts(s=Depends(services)):return s.notifications.list(limit=1)['counts']
    @r.get('/notifications')
    def notifications(patient_id:str|None=None,category:Literal['patient_monitoring','environment','data_quality','system']|None=None,status:Literal['active','acknowledged','under_review','resolved','closed']|None=None,unread_only:bool=False,limit:int=Query(default=200,ge=1,le=500),s=Depends(services)):
        return s.notifications.list(patient_id,category,status,unread_only,limit)
    @r.post('/notifications/test',dependencies=write)
    async def test_notification(body:EmptyBody,s=Depends(services)):
        result=await asyncio.to_thread(s.notifications.test);await changed();return result
    @r.get('/notifications/{nid}')
    def notification(nid:int,s=Depends(services)):return s.notifications.detail(nid)
    @r.patch('/notifications/{nid}',dependencies=write)
    async def update_notification(nid:int,body:NotificationUpdate,request:Request,s=Depends(services)):
        result=await asyncio.to_thread(s.notifications.update,nid,body,mutation_authorizer(request));await changed();return result
    @r.get('/email')
    def email(s=Depends(services)):return s.email.history()
    @r.post('/email/test',dependencies=write)
    async def email_test(body:EmptyBody,s=Depends(services)):
        result=await asyncio.to_thread(s.email.send_test);await changed();return result
    @r.get('/provenance')
    async def sources(patient_id:str|None=None,city:str='Pune',s=Depends(services)):return await provenance(s,patient_id,city)
    return r
