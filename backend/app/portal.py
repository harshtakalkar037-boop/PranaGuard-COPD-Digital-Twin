"""Authenticated, scoped research portal. Legacy demo endpoints are separate."""
import hashlib
import json
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Literal
from urllib.parse import quote
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from backend.app.config import ROOT

router = APIRouter(prefix='/api/portal', tags=['Research portals'])
MAX_FILE = 10 * 1024 * 1024
TEMPORARY_PASSWORD_HOURS = 24

def temporary_password_expiration():
    return (datetime.now(timezone.utc)+timedelta(hours=TEMPORARY_PASSWORD_HOURS)).isoformat()

def timestamp(): return datetime.now(timezone.utc).isoformat()
def store(request: Request): return request.app.state.engine.store

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f'scrypt${salt.hex()}${digest.hex()}'

def verify_password(password, encoded):
    try:
        _, salt, digest = encoded.split('$')
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError): return False

def current(request: Request, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401, 'Authentication required')
    token_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
    with store(request).connect() as c:
        user = c.execute('SELECT u.id,u.username,u.role,u.must_change_password,u.temporary_password_expires_at,u.temporary_password_used_at FROM portal_sessions s JOIN portal_users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?', (token_hash,timestamp())).fetchone()
    if not user or (user['must_change_password'] and (not user['temporary_password_expires_at'] or user['temporary_password_expires_at']<=timestamp() or not user['temporary_password_used_at'])): raise HTTPException(401, 'Session expired or invalid')
    if user['must_change_password'] and request.url.path not in ('/api/portal/me','/api/portal/logout','/api/portal/password'):
        raise HTTPException(403, 'Password change required')
    return {key:user[key] for key in ('id','username','role','must_change_password')}

def role(user, expected):
    if user['role'] != expected: raise HTTPException(403, 'Not permitted')

def patient_id(c, user):
    role(user, 'patient')
    row = c.execute('SELECT patient_id FROM patient_user_links WHERE user_id=?',(user['id'],)).fetchone()
    if not row: raise HTTPException(409, 'Account not linked. Ask an administrator to link your record.')
    return row['patient_id']

def access(c, user, pid):
    if user['role']=='patient':
        allowed = c.execute('SELECT 1 FROM patient_user_links WHERE user_id=? AND patient_id=?',(user['id'],pid)).fetchone()
    else:
        allowed = c.execute('SELECT 1 FROM doctor_patient_assignments WHERE doctor_id=? AND patient_id=?',(user['id'],pid)).fetchone()
    if not allowed: raise HTTPException(404, 'Record not found')

def notify(c, user_id, pid, title, description, link):
    c.execute('INSERT INTO portal_notifications(user_id,patient_id,title,description,link,created_at) VALUES (?,?,?,?,?,?)',(user_id,pid,title,description,link,timestamp()))

def notify_doctors(c,pid,title,description,link):
    for row in c.execute('SELECT doctor_id FROM doctor_patient_assignments WHERE patient_id=?',(pid,)).fetchall(): notify(c,row['doctor_id'],pid,title,description,link)

class Strict(BaseModel): model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Credentials(Strict):
    model_config=ConfigDict(extra='forbid')
    username: str = Field(min_length=3,max_length=80,pattern=r'^[a-zA-Z0-9_.@-]+$')
    password: str = Field(min_length=12,max_length=128)
class LoginCredentials(Credentials):
    password: str = Field(min_length=1,max_length=128)

class PasswordChange(Strict):
    model_config=ConfigDict(extra='forbid')
    current_password: str = Field(min_length=1,max_length=128)
    new_password: str = Field(min_length=12,max_length=128)

class Checkin(Strict):
    breathlessness: Literal['none','mild','moderate','severe']
    cough: Literal['none','mild','moderate','severe']
    sputum_amount: Literal['none','usual','more','less']
    sputum_colour: Literal['none','clear','white','yellow','green','other']
    wheezing: Literal['no','yes','unsure']
    fatigue: Literal['none','mild','moderate','severe']
    fever: Literal['no','yes','unsure']
    comments: str = Field(default='',max_length=2000)
    additional_symptoms: str = Field(default='',max_length=2000)
class Review(Strict):
    status: Literal['Pending Review','Under Review','Reviewed','Follow-up Required','Completed']
    notes: str = Field(min_length=1,max_length=4000)
    follow_up: str = Field(default='',max_length=4000)
    follow_up_date: date | None = None
    shared: bool = False
    checkin_id: int | None = Field(default=None,gt=0)
    upload_id: int | None = Field(default=None,gt=0)

@router.post('/register', status_code=201)
def register(body: Credentials, request: Request):
    try:
        with store(request).connect() as c: c.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',(body.username,hash_password(body.password),'patient',timestamp()))
    except sqlite3.IntegrityError: raise HTTPException(409,'Account cannot be created')
    return {'message':'Account created. An administrator must link your record.'}

@router.post('/login')
def login(body: LoginCredentials, request: Request):
    with store(request).connect() as c:
        row=c.execute('SELECT * FROM portal_users WHERE username=?',(body.username,)).fetchone()
        # Perform a hash even for missing usernames.
        valid=verify_password(body.password,row['password_hash'] if row else 'scrypt$00000000000000000000000000000000$'+'00'*32)
        if not row or not valid: raise HTTPException(401,'Invalid credentials')
        now=timestamp(); token=secrets.token_urlsafe(32)
        expires=(datetime.now(timezone.utc)+timedelta(hours=8)).isoformat()
        if row['must_change_password']:
            # Consume atomically so concurrent login attempts cannot reuse the
            # secret. Pre-migration credentials with no deadline fail closed.
            used=c.execute('UPDATE portal_users SET temporary_password_used_at=? WHERE id=? AND password_hash=? AND must_change_password=1 AND temporary_password_used_at IS NULL AND temporary_password_expires_at>?',(now,row['id'],row['password_hash'],now))
            if used.rowcount!=1: raise HTTPException(401,'Invalid credentials')
            expires=min(expires,row['temporary_password_expires_at'])
        c.execute('DELETE FROM portal_sessions WHERE expires_at<=?',(now,))
        # Also prevent an in-flight login with the old hash surviving a reset.
        created=c.execute('INSERT INTO portal_sessions(token_hash,user_id,expires_at) SELECT ?,id,? FROM portal_users WHERE id=? AND password_hash=?',(hashlib.sha256(token.encode()).hexdigest(),expires,row['id'],row['password_hash']))
        if created.rowcount!=1: raise HTTPException(401,'Invalid credentials')
    return {'token':token,'role':row['role'],'username':row['username'],'must_change_password':bool(row['must_change_password'])}

@router.post('/password')
def change_password(body:PasswordChange,request:Request,user=Depends(current),authorization:str=Header()):
    with store(request).connect() as c:
        row=c.execute('SELECT password_hash FROM portal_users WHERE id=?',(user['id'],)).fetchone()
        if not verify_password(body.current_password,row['password_hash']): raise HTTPException(401,'Invalid credentials')
        link=c.execute('SELECT patient_id FROM patient_user_links WHERE user_id=?',(user['id'],)).fetchone()
        if body.new_password==body.current_password or (link and body.new_password==link['patient_id']+'@123'): raise HTTPException(422,'Choose a different password')
        now=timestamp()
        updated=c.execute('''UPDATE portal_users SET password_hash=?,must_change_password=0,temporary_password_expires_at=NULL,temporary_password_used_at=NULL
            WHERE id=? AND password_hash=? AND (must_change_password=0 OR (temporary_password_used_at IS NOT NULL AND temporary_password_expires_at>?))
            AND EXISTS(SELECT 1 FROM portal_sessions WHERE user_id=portal_users.id AND token_hash=? AND expires_at>?)''',
            (hash_password(body.new_password),user['id'],row['password_hash'],now,hashlib.sha256(authorization[7:].encode()).hexdigest(),now))
        if updated.rowcount!=1: raise HTTPException(401,'Session expired or invalid')
        c.execute('DELETE FROM portal_sessions WHERE user_id=?',(user['id'],))
        c.execute('INSERT INTO portal_audit(actor_id,action,created_at) VALUES (?,?,?)',(user['id'],'password_changed',timestamp()))
    return {'message':'Password changed. Sign in again.'}

@router.post('/logout')
def logout(request:Request, user=Depends(current), authorization:str=Header()):
    with store(request).connect() as c:c.execute('DELETE FROM portal_sessions WHERE token_hash=?',(hashlib.sha256(authorization[7:].encode()).hexdigest(),))
    return {'message':'Signed out'}

@router.get('/me')
def me(request:Request,user=Depends(current)):
    with store(request).connect() as c:
        link=c.execute('SELECT patient_id FROM patient_user_links WHERE user_id=?',(user['id'],)).fetchone() if user['role']=='patient' else None
    return {**user,'patient_id':link['patient_id'] if link else None}

@router.get('/patients')
def patients(request:Request,user=Depends(current)):
    role(user,'doctor')
    with store(request).connect() as c: ids=[r['patient_id'] for r in c.execute('SELECT patient_id FROM doctor_patient_assignments WHERE doctor_id=? ORDER BY patient_id',(user['id'],))]
    result=[]
    for pid in ids:
        try:
            s=request.app.state.engine.patient(pid)
            result.append({'patient_id':pid,'profile':s['profile'],'risks':s['risks'],'prediction_supported':s['prediction_supported']})
        except KeyError: result.append({'patient_id':pid,'profile':{},'risks':None,'prediction_supported':False})
    return {'patients':result}

@router.get('/patients/{pid}')
def details(pid:str,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        access(c,user,pid)
        row=c.execute('SELECT profile FROM patients WHERE patient_id=?',(pid,)).fetchone()
        profile=json.loads(row['profile']) if row else None
        checkins=[dict(r) for r in c.execute('SELECT * FROM symptom_checkins WHERE patient_id=? ORDER BY id DESC LIMIT 100',(pid,))]
        uploads=[dict(r) for r in c.execute('SELECT id,patient_id,kind,original_name,mime,description,created_at,review_status FROM patient_uploads WHERE patient_id=? ORDER BY id DESC LIMIT 100',(pid,))]
        reviews=[dict(r) for r in c.execute('SELECT * FROM doctor_reviews WHERE patient_id=? '+('AND shared=1 ' if user['role']=='patient' else '')+'ORDER BY id DESC LIMIT 100',(pid,))]
    try:
        twin=request.app.state.engine.patient(pid)
        history=request.app.state.engine.history(pid) if user['role']=='doctor' else None
    except KeyError: twin=None;history=None
    if user['role']=='patient' and twin: twin={'profile':twin['profile'],'timestamp':twin['timestamp'],'synthetic':True}
    return {'profile':profile,'twin':twin,'history':history,'checkins':checkins,'uploads':uploads,'reviews':reviews}

@router.get('/patients/{pid}/environment')
async def environment(pid:str,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        access(c,user,pid)
        row=c.execute('SELECT profile FROM patients WHERE patient_id=?',(pid,)).fetchone()
    if not row: raise HTTPException(404,'Record not found')
    # Historical cohort uses its original engine profile; newly registered
    # synthetic records have only a persisted profile and no historical twin.
    if pid in request.app.state.engine.profiles:
        city=request.app.state.engine.profiles[pid]['city']
    else:
        city=json.loads(row['profile']).get('city')
    if not city: raise HTTPException(422,'City context unavailable for this record')
    return await request.app.state.enhanced.environment.get(city)

@router.post('/checkins',status_code=201)
def checkin(body:Checkin,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        pid=patient_id(c,user); d=body.model_dump(); cur=c.execute('INSERT INTO symptom_checkins(patient_id,created_at,breathlessness,cough,sputum_amount,sputum_colour,wheezing,fatigue,fever,comments,additional_symptoms) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(pid,timestamp(),*d.values()))
        notify_doctors(c,pid,'New symptom check-in',f'{pid} submitted observations.',f'/doctor/dashboard?patient={quote(pid)}&view=Care%20Action%20Centre')
    return {'id':cur.lastrowid,'message':'Check-in saved'}

@router.post('/uploads',status_code=201)
async def upload(request:Request, kind:Literal['photo','care_plan']=Form(), description:str=Form(default='',max_length=1000), sputum_entry_id:int|None=Form(default=None,gt=0), file:UploadFile=File(),user=Depends(current)):
    with store(request).connect() as c:
        pid=patient_id(c,user)
        if sputum_entry_id and (kind!='photo' or not c.execute('SELECT 1 FROM sputum_entries WHERE id=? AND patient_id=?',(sputum_entry_id,pid)).fetchone()): raise HTTPException(404,'Diary entry not found')
    filename=Path(file.filename or '').name
    ext=Path(filename).suffix.lower()
    allowed={'.pdf':'application/pdf','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png'}
    if ext not in allowed or (kind=='photo' and ext=='.pdf'): raise HTTPException(415,'Unsupported file type')
    data=await file.read(MAX_FILE+1)
    if len(data)>MAX_FILE: raise HTTPException(413,'File exceeds 10 MB')
    signatures={'.pdf':b'%PDF-', '.jpg':b'\xff\xd8\xff', '.jpeg':b'\xff\xd8\xff', '.png':b'\x89PNG\r\n\x1a\n'}
    if not data.startswith(signatures[ext]): raise HTTPException(415,'File content does not match its extension')
    directory=Path(os.getenv('PRANAGUARD_UPLOAD_DIR',str(ROOT/'private_uploads'))).resolve(); directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    name=secrets.token_hex(24)+ext; path=directory/name
    try:
        with path.open('xb') as f: os.chmod(path,0o600); f.write(data)
        with store(request).connect() as c:
            cur=c.execute('INSERT INTO patient_uploads(patient_id,kind,original_name,stored_name,mime,description,created_at,sputum_entry_id) VALUES (?,?,?,?,?,?,?,?)',(pid,kind,filename[:255],name,allowed[ext],description.strip(),timestamp(),sputum_entry_id))
            if sputum_entry_id: c.execute("UPDATE sputum_entries SET review_status='Pending Review' WHERE id=? AND patient_id=?",(sputum_entry_id,pid))
            notify_doctors(c,pid,'New patient upload',f'{pid} uploaded a {"photo" if kind=="photo" else "care plan"}.',f'/doctor/dashboard?patient={quote(pid)}&view='+('Sputum%20Monitoring' if sputum_entry_id else 'Care%20Action%20Centre'))
    except BaseException:
        path.unlink(missing_ok=True); raise
    return {'id':cur.lastrowid,'message':'Upload saved for clinician review'}

@router.get('/uploads/{upload_id}')
def download(upload_id:int,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        row=c.execute('SELECT * FROM patient_uploads WHERE id=?',(upload_id,)).fetchone()
        if not row: raise HTTPException(404,'File not found')
        access(c,user,row['patient_id'])
    directory=Path(os.getenv('PRANAGUARD_UPLOAD_DIR',str(ROOT/'private_uploads'))).resolve()
    path=(directory/row['stored_name']).resolve()
    if path.parent != directory or not path.is_file(): raise HTTPException(404,'File not found')
    return FileResponse(path,media_type='application/octet-stream',filename=row['original_name'],headers={'X-Content-Type-Options':'nosniff','Cache-Control':'no-store'})

@router.post('/patients/{pid}/reviews',status_code=201)
def review(pid:str,body:Review,request:Request,user=Depends(current)):
    role(user,'doctor')
    with store(request).connect() as c:
        access(c,user,pid)
        for table,ident in [('symptom_checkins',body.checkin_id),('patient_uploads',body.upload_id)]:
            if ident and not c.execute(f'SELECT 1 FROM {table} WHERE id=? AND patient_id=?',(ident,pid)).fetchone(): raise HTTPException(404,'Related record not found')
        cur=c.execute('INSERT INTO doctor_reviews(patient_id,doctor_id,checkin_id,upload_id,status,notes,follow_up,follow_up_date,shared,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',(pid,user['id'],body.checkin_id,body.upload_id,body.status,body.notes,body.follow_up,str(body.follow_up_date) if body.follow_up_date else None,int(body.shared),timestamp()))
        if body.upload_id: c.execute('UPDATE patient_uploads SET review_status=? WHERE id=?',(body.status,body.upload_id))
        if body.checkin_id: c.execute('UPDATE symptom_checkins SET review_status=? WHERE id=?',(body.status,body.checkin_id))
        c.execute('INSERT INTO portal_audit(actor_id,patient_id,action,record_id,created_at) VALUES (?,?,?,?,?)',(user['id'],pid,'doctor_review',cur.lastrowid,timestamp()))
        if body.shared:
            linked=c.execute('SELECT user_id FROM patient_user_links WHERE patient_id=?',(pid,)).fetchone()
            if linked: notify(c,linked['user_id'],pid,'A doctor shared an update','Your doctor has shared a review or follow-up.','/patient/dashboard?view=My%20Health')
    return {'id':cur.lastrowid,'message':'Review saved; documentation only'}

@router.get('/notifications')
def notifications(request:Request,user=Depends(current)):
    with store(request).connect() as c: return {'notifications':[dict(r) for r in c.execute('SELECT * FROM portal_notifications WHERE user_id=? ORDER BY id DESC LIMIT 200',(user['id'],))]}

@router.post('/notifications/{notification_id}/read')
def read_notification(notification_id:int,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        cur=c.execute('UPDATE portal_notifications SET read_at=COALESCE(read_at,?) WHERE id=? AND user_id=?',(timestamp(),notification_id,user['id']))
        if not cur.rowcount: raise HTTPException(404,'Notification not found')
    return {'message':'Marked as read'}

class ScenarioInput(Strict):
    pm25_change_pct: float = Field(default=-30,ge=-80,le=100,allow_inf_nan=False)
    adherence: float = Field(default=.95,ge=0,le=1,allow_inf_nan=False)
    activity_multiplier: float = Field(default=1,ge=.5,le=1.5,allow_inf_nan=False)

@router.get('/validation')
def validation(request:Request,user=Depends(current)):
    role(user,'doctor')
    evaluation=request.app.state.engine.evaluation
    # Do not expose the protocol's patient ID lists to unassigned users.
    return {'model_version':evaluation['model_version'],'warning':evaluation['warning'],'results':evaluation['results']}

@router.get('/patients/{pid}/explanation')
def explanation(pid:str,request:Request,horizon:int=72,user=Depends(current)):
    role(user,'doctor')
    with store(request).connect() as c: access(c,user,pid)
    if horizon not in (24,48,72): raise HTTPException(422,'Horizon must be 24, 48 or 72 hours')
    return request.app.state.engine.explain(pid,horizon)

@router.post('/patients/{pid}/scenarios')
def scenario(pid:str,body:ScenarioInput,request:Request,user=Depends(current)):
    role(user,'doctor')
    with store(request).connect() as c: access(c,user,pid)
    return request.app.state.engine.scenario(pid,body.model_dump())

# Daily-care records are patient reported; no clinical rules are inferred from them.
class SputumInput(Strict):
    observed_at: datetime
    colour: Literal['clear','white','yellow','green','brown','blood-stained','other/unsure']
    amount: Literal['none','small','moderate','large']
    consistency: Literal['thin','thick','sticky','other/unsure']
    cough: Literal['none','mild','moderate','severe']
    description: str = Field(default='',max_length=2000)

class SputumReview(Strict):
    notes: str = Field(min_length=1,max_length=4000)
    follow_up: str = Field(default='',max_length=4000)
    shared: bool = False

class PlanInput(Strict):
    title: str = Field(min_length=1,max_length=200)
    active: bool = True
    start_date: date
    review_date: date | None = None
    food_guidance: str = Field(default='',max_length=4000)
    breakfast: str = Field(default='',max_length=1000)
    lunch: str = Field(default='',max_length=1000)
    dinner: str = Field(default='',max_length=1000)
    snacks: str = Field(default='',max_length=1000)
    hydration_target_ml: int | None = Field(default=None,ge=1,le=10000)
    hydration_instructions: str = Field(default='',max_length=4000)
    activities: str = Field(default='',max_length=4000)
    activity_schedule: str = Field(default='',max_length=4000)
    activity_restrictions: str = Field(default='',max_length=4000)
    notes: str = Field(default='',max_length=4000)

class DailyInput(Strict):
    kind: Literal['meal','hydration','activity']
    occurred_at: datetime
    item: str = Field(min_length=1,max_length=500)
    status: Literal['Completed','Not completed','Not applicable']
    amount_ml: int | None = Field(default=None,ge=1,le=5000)
    duration_minutes: int | None = Field(default=None,ge=0,le=1440)
    effort: Literal['','light','moderate','hard','unsure'] = ''
    comments: str = Field(default='',max_length=2000)
    client_key: str = Field(min_length=16,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')

class DailyReview(Strict):
    notes: str = Field(min_length=1,max_length=2000)
    shared: bool = False

def utc_time(value):
    if value.tzinfo is None: raise HTTPException(422,'Timestamp must include a timezone')
    return value.astimezone(timezone.utc).isoformat()

def patient_notice(c,pid,title,description,view='My%20Health'):
    linked=c.execute('SELECT user_id FROM patient_user_links WHERE patient_id=?',(pid,)).fetchone()
    if linked: notify(c,linked['user_id'],pid,title,description,'/patient/dashboard?view='+view)

def audit(c,user,pid,action,record_id):
    c.execute('INSERT INTO portal_audit(actor_id,patient_id,action,record_id,created_at) VALUES (?,?,?,?,?)',(user['id'],pid,action,record_id,timestamp()))

@router.post('/sputum',status_code=201)
def add_sputum(body:SputumInput,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        pid=patient_id(c,user); at=timestamp()
        cur=c.execute('INSERT INTO sputum_entries(patient_id,user_id,observed_at,colour,amount,consistency,cough,description,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)',(pid,user['id'],utc_time(body.observed_at),body.colour,body.amount,body.consistency,body.cough,body.description,at,at))
        notify_doctors(c,pid,'New sputum diary entry',f'{pid} submitted a diary entry.',f'/doctor/dashboard?patient={quote(pid)}&view=Sputum%20Monitoring')
        return {'id':cur.lastrowid}

@router.put('/sputum/{entry_id}')
def edit_sputum(entry_id:int,body:SputumInput,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        pid=patient_id(c,user)
        old=c.execute('SELECT * FROM sputum_entries WHERE id=? AND patient_id=? AND user_id=?',(entry_id,pid,user['id'])).fetchone()
        if not old: raise HTTPException(404,'Entry not found')
        at=timestamp()
        c.execute('INSERT INTO sputum_entry_history(entry_id,changed_at,actor_id,snapshot) VALUES (?,?,?,?)',(entry_id,at,user['id'],json.dumps(dict(old))))
        c.execute("UPDATE sputum_entries SET observed_at=?,colour=?,amount=?,consistency=?,cough=?,description=?,updated_at=?,review_status='Pending Review' WHERE id=?",(utc_time(body.observed_at),body.colour,body.amount,body.consistency,body.cough,body.description,at,entry_id))
        notify_doctors(c,pid,'Sputum entry updated',f'{pid} updated a diary entry.',f'/doctor/dashboard?patient={quote(pid)}&view=Sputum%20Monitoring')
    return {'message':'Entry updated; previous version retained'}

@router.get('/patients/{pid}/sputum')
def list_sputum(pid:str,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        access(c,user,pid)
        entries=[dict(r) for r in c.execute('SELECT * FROM sputum_entries WHERE patient_id=? ORDER BY observed_at DESC,id DESC LIMIT 500',(pid,))]
        for entry in entries:
            entry['photos']=[dict(r) for r in c.execute('SELECT id,original_name,created_at,review_status FROM patient_uploads WHERE patient_id=? AND sputum_entry_id=? ORDER BY id',(pid,entry['id']))]
            entry['reviews']=[dict(r) for r in c.execute('SELECT id,notes,follow_up,shared,created_at FROM sputum_reviews WHERE entry_id=? '+('AND shared=1 ' if user['role']=='patient' else '')+'ORDER BY id DESC',(entry['id'],))]
            entry['edit_history']=[dict(r) for r in c.execute('SELECT changed_at,snapshot FROM sputum_entry_history WHERE entry_id=? ORDER BY id DESC',(entry['id'],))]
    return {'entries':entries}

@router.post('/patients/{pid}/sputum/{entry_id}/reviews',status_code=201)
def review_sputum(pid:str,entry_id:int,body:SputumReview,request:Request,user=Depends(current)):
    role(user,'doctor')
    with store(request).connect() as c:
        access(c,user,pid)
        if not c.execute('SELECT 1 FROM sputum_entries WHERE id=? AND patient_id=?',(entry_id,pid)).fetchone(): raise HTTPException(404,'Entry not found')
        cur=c.execute('INSERT INTO sputum_reviews(entry_id,patient_id,doctor_id,notes,follow_up,shared,created_at) VALUES (?,?,?,?,?,?,?)',(entry_id,pid,user['id'],body.notes,body.follow_up,int(body.shared),timestamp()))
        c.execute("UPDATE sputum_entries SET review_status='Reviewed' WHERE id=?",(entry_id,))
        c.execute("UPDATE patient_uploads SET review_status='Reviewed' WHERE sputum_entry_id=?",(entry_id,))
        audit(c,user,pid,'sputum_review',cur.lastrowid)
        if body.shared: patient_notice(c,pid,'Sputum diary reviewed','Your doctor shared a diary review or follow-up.','Sputum%20Diary')
    return {'id':cur.lastrowid}

@router.get('/patients/{pid}/care-plan')
def get_plan(pid:str,request:Request,user=Depends(current)):
    with store(request).connect() as c:
        access(c,user,pid)
        plans=[dict(r) for r in c.execute('SELECT * FROM care_plan_versions WHERE patient_id=? ORDER BY id DESC LIMIT 100',(pid,))]
    return {'current':plans[0] if plans and plans[0]['active'] else None,'history':plans if user['role']=='doctor' else []}

@router.post('/patients/{pid}/care-plan',status_code=201)
def save_plan(pid:str,body:PlanInput,request:Request,user=Depends(current)):
    role(user,'doctor')
    if body.review_date and body.review_date<body.start_date: raise HTTPException(422,'Review date cannot be before start date')
    with store(request).connect() as c:
        access(c,user,pid)
        d=body.model_dump(mode='json')
        cols=['title','active','start_date','review_date','food_guidance','breakfast','lunch','dinner','snacks','hydration_target_ml','hydration_instructions','activities','activity_schedule','activity_restrictions','notes']
        cur=c.execute('INSERT INTO care_plan_versions(patient_id,doctor_id,created_at,'+','.join(cols)+') VALUES ('+','.join('?' for _ in range(len(cols)+3))+')',(pid,user['id'],timestamp(),*[d[k] for k in cols]))
        audit(c,user,pid,'care_plan_saved',cur.lastrowid)
        patient_notice(c,pid,'Care plan updated','Your doctor updated your care plan.','My%20Care%20Plan')
    return {'id':cur.lastrowid,'message':'Care plan version saved'}

@router.post('/daily-care',status_code=201)
def add_daily(body:DailyInput,request:Request,user=Depends(current)):
    if body.kind=='hydration' and body.amount_ml is None: raise HTTPException(422,'Amount in millilitres is required')
    if body.kind!='hydration' and body.amount_ml is not None: raise HTTPException(422,'Amount is only valid for hydration')
    if body.kind!='activity' and (body.duration_minutes is not None or body.effort): raise HTTPException(422,'Duration and effort are only valid for activity')
    if body.kind=='meal' and body.item not in ('Breakfast','Lunch','Dinner','Snack'): raise HTTPException(422,'Choose a meal')
    with store(request).connect() as c:
        pid=patient_id(c,user)
        existing=c.execute('SELECT * FROM daily_care_logs WHERE user_id=? AND client_key=?',(user['id'],body.client_key)).fetchone()
        if existing:
            actual=(existing['kind'],existing['occurred_at'],existing['item'],existing['status'],existing['amount_ml'],existing['duration_minutes'],existing['effort'],existing['comments'])
            expected=(body.kind,utc_time(body.occurred_at),body.item,body.status,body.amount_ml,body.duration_minutes,body.effort,body.comments)
            if actual!=expected: raise HTTPException(409,'Submission key was already used for a different entry')
            return {'id':existing['id'],'duplicate':True}
        cur=c.execute('INSERT INTO daily_care_logs(patient_id,user_id,kind,occurred_at,created_at,item,status,amount_ml,duration_minutes,effort,comments,client_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(pid,user['id'],body.kind,utc_time(body.occurred_at),timestamp(),body.item,body.status,body.amount_ml,body.duration_minutes,body.effort,body.comments,body.client_key))
        notify_doctors(c,pid,'New daily care activity',f'{pid} recorded {body.kind}.',f'/doctor/dashboard?patient={quote(pid)}&view=Patient%20Activity%20%26%20Adherence')
    return {'id':cur.lastrowid,'duplicate':False}

@router.get('/patients/{pid}/daily-care')
def list_daily(pid:str,request:Request,kind:Literal['all','meal','hydration','activity']='all',start:date|None=None,end:date|None=None,review_status:Literal['all','Pending Review','Reviewed']='all',user=Depends(current)):
    if start and end and start>end: raise HTTPException(422,'Invalid date range')
    with store(request).connect() as c:
        access(c,user,pid)
        sql='SELECT id,patient_id,kind,occurred_at,created_at,item,status,amount_ml,duration_minutes,effort,comments,review_status FROM daily_care_logs WHERE patient_id=?';args=[pid]
        if kind!='all':sql+=' AND kind=?';args.append(kind)
        if start:sql+=' AND substr(occurred_at,1,10)>=?';args.append(str(start))
        if end:sql+=' AND substr(occurred_at,1,10)<=?';args.append(str(end))
        if review_status!='all':sql+=' AND review_status=?';args.append(review_status)
        logs=[dict(r) for r in c.execute(sql+' ORDER BY occurred_at DESC,id DESC LIMIT 500',args)]
        for log in logs:
            log['reviews']=[dict(r) for r in c.execute('SELECT notes,shared,created_at FROM daily_care_reviews WHERE log_id=? '+('AND shared=1 ' if user['role']=='patient' else '')+'ORDER BY id DESC',(log['id'],))]
        return {'logs':logs}

@router.post('/patients/{pid}/daily-care/{log_id}/reviews',status_code=201)
def review_daily(pid:str,log_id:int,body:DailyReview,request:Request,user=Depends(current)):
    role(user,'doctor')
    with store(request).connect() as c:
        access(c,user,pid)
        if not c.execute('SELECT 1 FROM daily_care_logs WHERE id=? AND patient_id=?',(log_id,pid)).fetchone():raise HTTPException(404,'Activity not found')
        cur=c.execute('INSERT INTO daily_care_reviews(log_id,doctor_id,notes,shared,created_at) VALUES (?,?,?,?,?)',(log_id,user['id'],body.notes,int(body.shared),timestamp()))
        c.execute("UPDATE daily_care_logs SET review_status='Reviewed' WHERE id=?",(log_id,))
        audit(c,user,pid,'daily_care_review',cur.lastrowid)
        if body.shared:patient_notice(c,pid,'Daily activity reviewed','Your doctor shared an update about your daily activity.','My%20Daily%20Care%20Plan')
    return {'id':cur.lastrowid}

@router.post('/patients/{pid}/provision-demo',status_code=201)
def provision_demo(pid:str,request:Request,user=Depends(current)):
    role(user,'doctor')
    if os.getenv('PRANAGUARD_SYNTHETIC_DEMO_PROVISIONING')!='1': raise HTTPException(403,'Synthetic demo provisioning is disabled')
    with store(request).connect() as c:
        access(c,user,pid)
        row=c.execute('SELECT profile FROM patients WHERE patient_id=?',(pid,)).fetchone()
        if not row or not json.loads(row['profile']).get('synthetic'): raise HTTPException(403,'Only synthetic records are supported')
        temporary=secrets.token_urlsafe(18);expires_at=temporary_password_expiration()
        try:
            cur=c.execute("INSERT INTO portal_users(username,password_hash,role,created_at,must_change_password,temporary_password_expires_at) VALUES (?,?,'patient',?,1,?)",(pid,hash_password(temporary),timestamp(),expires_at))
            c.execute('INSERT INTO patient_user_links(user_id,patient_id) VALUES (?,?)',(cur.lastrowid,pid))
        except sqlite3.IntegrityError: raise HTTPException(409,'Account or link already exists')
        audit(c,user,pid,'synthetic_account_provisioned',cur.lastrowid)
    return {'login_id':pid,'patient_id':pid,'assigned_doctor':user['username'],'status':'Password change required','temporary_password':temporary,'temporary_password_expires_at':expires_at}

@router.get('/care-queue')
def care_queue(request:Request,user=Depends(current)):
    """Workflow state only; ordering is not a clinical urgency score."""
    role(user,'doctor')
    with store(request).connect() as c:
        rows=c.execute("""
            SELECT 'checkin' AS kind,s.id,s.patient_id,s.created_at AS timestamp,s.review_status AS status
              FROM symptom_checkins s JOIN doctor_patient_assignments a ON a.patient_id=s.patient_id
             WHERE a.doctor_id=? AND s.review_status='Pending Review'
            UNION ALL
            SELECT 'sputum',s.id,s.patient_id,s.created_at,s.review_status
              FROM sputum_entries s JOIN doctor_patient_assignments a ON a.patient_id=s.patient_id
             WHERE a.doctor_id=? AND s.review_status='Pending Review'
            UNION ALL
            SELECT 'upload',u.id,u.patient_id,u.created_at,u.review_status
              FROM patient_uploads u JOIN doctor_patient_assignments a ON a.patient_id=u.patient_id
             WHERE a.doctor_id=? AND u.review_status='Pending Review'
            UNION ALL
            SELECT 'daily',d.id,d.patient_id,d.created_at,d.review_status
              FROM daily_care_logs d JOIN doctor_patient_assignments a ON a.patient_id=d.patient_id
             WHERE a.doctor_id=? AND d.review_status='Pending Review'
            UNION ALL
            SELECT 'followup',r.id,r.patient_id,r.follow_up_date,r.status
              FROM doctor_reviews r JOIN doctor_patient_assignments a ON a.patient_id=r.patient_id
             WHERE a.doctor_id=? AND r.follow_up_date IS NOT NULL
               AND r.follow_up_date<=date('now') AND r.status!='Completed'
             ORDER BY timestamp DESC LIMIT 200
        """,(user['id'],)*5).fetchall()
    return {'items':[dict(row) for row in rows], 'limit':200,
            'notice':'Workflow states only; not a measure of clinical urgency.'}

@router.get('/doctor-summary')
def doctor_summary(request:Request,user=Depends(current)):
    role(user,'doctor')
    with store(request).connect() as c:
        ids=[r['patient_id'] for r in c.execute('SELECT patient_id FROM doctor_patient_assignments WHERE doctor_id=?',(user['id'],))]
        if not ids:return {'assigned':0,'pending_checkins':0,'pending_sputum':0,'pending_uploads':0,'followups_due':0}
        marks=','.join('?' for _ in ids)
        def count(table,where): return c.execute(f'SELECT COUNT(*) FROM {table} WHERE patient_id IN ({marks}) AND {where}',ids).fetchone()[0]
        return {'assigned':len(ids),'pending_checkins':count('symptom_checkins',"review_status='Pending Review'"),'pending_sputum':count('sputum_entries',"review_status='Pending Review'"),'pending_uploads':count('patient_uploads',"review_status='Pending Review'"),'followups_due':count('doctor_reviews',"follow_up_date IS NOT NULL AND follow_up_date<=date('now') AND status!='Completed'")}
