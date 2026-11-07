"""Session-protected care workspace API. Demo identities only; no production RBAC claim."""
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Strict(BaseModel):model_config=ConfigDict(extra='forbid',allow_inf_nan=False,str_strip_whitespace=True)
class Login(Strict):username:str=Field(min_length=3,max_length=60);password:str=Field(min_length=6,max_length=120)
class ReviewCreate(Strict):
    patient_id:str=Field(min_length=1,max_length=100)
    note:str=Field(min_length=3,max_length=2000)
    follow_up_at:str|None=None
    @field_validator('follow_up_at')
    @classmethod
    def iso(cls,v):
        if v:
            try:datetime.fromisoformat(v.replace('Z','+00:00'))
            except ValueError:raise ValueError('Follow-up must be an ISO date-time.') from None
            return datetime.fromisoformat(v.replace('Z','+00:00')).astimezone(timezone.utc).isoformat()
        return None
class ReviewUpdate(Strict):
    status:Literal['new','awaiting_review','under_review','follow_up_scheduled','completed','closed']|None=None
    note:str|None=Field(default=None,max_length=2000)
    follow_up_at:str|None=None
    @field_validator('follow_up_at')
    @classmethod
    def iso(cls,v):return ReviewCreate.iso(v)
class PlanSave(Strict):
    goals:str=Field(min_length=3,max_length=3000)
    activity_guidance:str=Field(default='',max_length=2000)
    adherence_support:str=Field(default='',max_length=2000)
    environment_notes:str=Field(default='',max_length=2000)
    review_date:str|None=None
    status:Literal['draft','active','completed','cancelled']='draft'
    change_note:str=Field(default='',max_length=500)
    @field_validator('review_date')
    @classmethod
    def date_ok(cls,v):
        if v:
            try:datetime.fromisoformat(v[:10])
            except ValueError:raise ValueError('Review date must be ISO.') from None
        return v[:10] if v else None
class AttachmentIn(Strict):
    filename:str=Field(min_length=1,max_length=120)
    media_type:Literal['image/png','image/jpeg','image/webp']
    data_base64:str=Field(min_length=8,max_length=750_000)
class SputumIn(Strict):
    occurred_at:str
    colour:Literal['clear','white','cream','yellow','green','rust','other']
    volume:Literal['none','scant','moderate','large']
    consistency:Literal['thin','thick','sticky']
    cough:int=Field(ge=0,le=10)
    breathlessness:int=Field(ge=0,le=10)
    note:str=Field(default='',max_length=1500)
    attachment:AttachmentIn|None=None
    @field_validator('occurred_at')
    @classmethod
    def occurred(cls,v):
        try:t=datetime.fromisoformat(v.replace('Z','+00:00'))
        except ValueError:raise ValueError('Entry time must be ISO.') from None
        t=t.astimezone(timezone.utc)
        if t>datetime.now(timezone.utc):raise ValueError('Entry time cannot be in the future.')
        return t.isoformat()
class SputumReview(Strict):note:str=Field(min_length=3,max_length=1000)
class FollowupComplete(Strict):note:str=Field(default='',max_length=1000)

def make_workspace_router():
    r=APIRouter(prefix='/api/workspace',tags=['Care workspace (demo auth)'])
    def workspace(request:Request):return request.app.state.workspace
    def principal(authorization:str|None=Header(default=None),w=Depends(workspace)):
        token=None
        if authorization and authorization.startswith('Bearer '):token=authorization[7:]
        return w.principal(token)
    @r.post('/login')
    def login(body:Login,w=Depends(workspace)):return w.login(body.username,body.password)
    @r.post('/logout')
    def logout(authorization:str|None=Header(default=None),w=Depends(workspace)):
        if authorization and authorization.startswith('Bearer '):w.logout(authorization[7:])
        return {'logged_out':True}
    @r.get('/me')
    def me(u=Depends(principal)):return {'user':u,'demo':True,'disclaimer':'Local synthetic demo identity. Not production authentication.'}
    @r.get('/overview')
    def overview(u=Depends(principal),w=Depends(workspace)):
        cohort,_=w.overview(u);return cohort
    @r.get('/patients')
    def directory(q:str=Query(default='',max_length=100),city:str|None=None,origin:Literal['historical_twin','manual_demo_registration']|None=None,
                  risk:Literal['low','elevated','high','unavailable']|None=None,sort:Literal['name','city','risk','updated']='name',
                  page:int=Query(default=1,ge=1),page_size:int=Query(default=12,ge=1,le=50),u=Depends(principal),w=Depends(workspace)):
        return w.directory(user=u,q=q,city=city,origin=origin,risk=risk,sort=sort,page=page,page_size=page_size)
    @r.get('/patients/{pid}')
    def profile(pid:str,u=Depends(principal),w=Depends(workspace)):return w.profile(u,pid)
    @r.get('/patients/{pid}/activity')
    def activity(pid:str,u=Depends(principal),w=Depends(workspace)):return w.activity(u,pid)
    @r.get('/patients/{pid}/plan')
    def plan(pid:str,u=Depends(principal),w=Depends(workspace)):return w.get_plan(u,pid)
    @r.put('/patients/{pid}/plan')
    def save_plan(pid:str,body:PlanSave,u=Depends(principal),w=Depends(workspace)):return w.save_plan(u,pid,body)
    @r.get('/patients/{pid}/sputum')
    def sputum(pid:str,page:int=Query(default=1,ge=1),page_size:int=Query(default=15,ge=1,le=50),u=Depends(principal),w=Depends(workspace)):
        return w.list_sputum(u,pid,page,page_size)
    @r.post('/patients/{pid}/sputum')
    def add_sputum(pid:str,body:SputumIn,u=Depends(principal),w=Depends(workspace)):return w.add_sputum(u,pid,body)
    @r.patch('/sputum/{eid}/review')
    def review_sputum(eid:int,body:SputumReview,u=Depends(principal),w=Depends(workspace)):return w.review_sputum(u,eid,body.note)
    @r.get('/attachments/{aid}')
    def attachment(aid:int,u=Depends(principal),w=Depends(workspace)):
        row=w.attachment(u,aid);return Response(content=row['data'],media_type=row['media_type'],headers={'Content-Disposition':f"inline; filename={row['filename']}"})
    @r.get('/care/summary')
    def care_summary(u=Depends(principal),w=Depends(workspace)):return w.care_summary(u)
    @r.get('/care/reviews')
    def reviews(status:str|None=None,patient_id:str|None=None,page:int=Query(default=1,ge=1),page_size:int=Query(default=10,ge=1,le=50),u=Depends(principal),w=Depends(workspace)):
        return w.list_reviews(u,status,patient_id,page,page_size)
    @r.post('/care/reviews')
    def create_review(body:ReviewCreate,u=Depends(principal),w=Depends(workspace)):return w.create_review(u,body.patient_id,body.note,body.follow_up_at)
    @r.post('/care/reviews/{rid}/complete-follow-up')
    def complete_follow_up(rid:int,body:FollowupComplete,u=Depends(principal),w=Depends(workspace)):
        return w.complete_follow_up(u,rid,body.note)
    @r.get('/patients/{pid}/follow-up-ledger')
    def followup_ledger(pid:str,page:int=Query(default=1,ge=1),page_size:int=Query(default=20,ge=1,le=100),u=Depends(principal),w=Depends(workspace)):
        return w.followup_ledger(u,pid,page,page_size)
    @r.get('/care/reviews/{rid}')
    def review(rid:int,u=Depends(principal),w=Depends(workspace)):return w.review_detail(u,rid)
    @r.patch('/care/reviews/{rid}')
    def update_review(rid:int,body:ReviewUpdate,u=Depends(principal),w=Depends(workspace)):return w.update_review(u,rid,body.status,body.note,body.follow_up_at)
    # Friendly errors for ignored-but-known write attempts (never fake success).
    @r.post('/activate-model')
    def no_activation(u=Depends(principal)):raise HTTPException(404,'No model activation endpoint exists. Model versions change only through audited studies.')
    return r
