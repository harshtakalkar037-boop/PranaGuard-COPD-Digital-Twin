"""Generic backend-owned simulation through the validated ingestion service.
No Bluetooth, commercial hardware SDK or real-device compatibility is implemented.
"""
import asyncio,hashlib,hmac,json,math,random,secrets,uuid
from datetime import timedelta
from fastapi import HTTPException
from backend.app.enhanced.settings import DEVICE_CATALOG,METRICS,stamp,parse_stamp,utcnow
from backend.app.enhanced.registry import public_device,fingerprint

class Devices:
    def __init__(self,store,settings,notifications,registry):
        self.store=store;self.settings=settings;self.notifications=notifications;self.registry=registry
        self._secret=settings.device_secret or secrets.token_urlsafe(48)
        # A restart never resumes a simulation without a deliberate Start action.
        with store.connect() as c:
            for row in c.execute('SELECT * FROM devices').fetchall():
                digest=hashlib.sha256(self.token_for(row['id']).encode()).hexdigest()
                c.execute("UPDATE devices SET token_hash=?,is_simulating=0,status=CASE WHEN is_simulating=1 THEN 'disconnected' ELSE status END,next_due_at=NULL WHERE id=?",(digest,row['id']))
                if row['is_simulating']:
                    notifications.create(category='data_quality',title='Simulation interrupted by backend restart',reason='The synthetic device stream is stopped. Restart simulation explicitly; no physical device was connected.',source='Device simulator lifecycle',source_type='system_demo',patient_id=row['patient_id'],dedupe_key=f"restart:{row['id']}:{row['run_id']}",conn=c)
    def token_for(self,device_id):
        """Backend-only token. Never returned by public API or logged."""
        return hmac.new(self._secret.encode(),device_id.encode(),hashlib.sha256).hexdigest()
    def require(self,did):
        with self.store.connect() as c:row=c.execute('SELECT * FROM devices WHERE id=?',(did,)).fetchone()
        if not row:raise HTTPException(404,'Simulated device not found.')
        return dict(row)
    def list(self,pid=None):
        with self.store.connect() as c:
            rows=c.execute('SELECT * FROM devices'+(' WHERE patient_id=?' if pid else '')+' ORDER BY created_at DESC',(pid,) if pid else ()).fetchall()
        return {'devices':[public_device(r) for r in rows],'catalog':DEVICE_CATALOG,'metrics':METRICS,'hardware_supported':False,'authentication':'Per-device HMAC token; backend-owned simulator. Provisioning real hardware is not implemented.','persistent_device_secret_configured':bool(self.settings.device_secret)}
    def associate(self,body):
        self.registry.require(body.patient_id);did='SIM-'+uuid.uuid4().hex[:16].upper();at=stamp()
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT COUNT(*) AS n FROM devices WHERE patient_id=?',(body.patient_id,)).fetchone()['n']>=16:raise HTTPException(409,'Demo limit: 16 simulated devices per patient.')
            catalog=next(x for x in DEVICE_CATALOG if x['kind']==body.kind)
            label=body.label or catalog['label']
            c.execute('INSERT INTO devices(id,patient_id,kind,label,created_at,interval_seconds,token_hash) VALUES (?,?,?,?,?,?,?)',(did,body.patient_id,body.kind,label,at,body.interval_seconds,hashlib.sha256(self.token_for(did).encode()).hexdigest()))
        return public_device(self.require(did))
    def start(self,did,interval):
        d=self.require(did);at=stamp();run=uuid.uuid4().hex
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not d['is_simulating'] and c.execute('SELECT COUNT(*) AS n FROM devices WHERE is_simulating=1').fetchone()['n']>=16:raise HTTPException(409,'Demo limit: 16 concurrent simulations.')
            c.execute("UPDATE devices SET status='connected_simulation',is_simulating=1,interval_seconds=?,next_due_at=?,last_error=NULL,run_id=?,sequence=0 WHERE id=?",(interval,at,run,did))
        return public_device(self.require(did))
    def stop(self,did):
        d=self.require(did)
        with self.store.connect() as c:
            c.execute("UPDATE devices SET status='disconnected',is_simulating=0,next_due_at=NULL,last_error=NULL WHERE id=?",(did,))
            if d['is_simulating']:
                self.notifications.create(category='data_quality',title='Simulated device stream stopped',reason='The user explicitly stopped this synthetic stream. New readings are not being collected; no physical-device disconnection is implied.',source='Device simulation control',source_type='system_demo',patient_id=d['patient_id'],dedupe_key=f"device-stop:{did}:{d['run_id']}",metadata={'device_id':did},conn=c)
        return public_device(self.require(did))
    def ingest(self,body,token,expected_run_id=None):
        d=self.require(body.device_id)
        if not token or not secrets.compare_digest(hashlib.sha256(token.encode()).hexdigest(),d['token_hash']):raise HTTPException(401,'Valid per-device ingestion token required (X-Device-Token).')
        if d['patient_id']!=body.patient_id:raise HTTPException(409,'Device/patient association mismatch.')
        allowed=next(x['metrics'] for x in DEVICE_CATALOG if x['kind']==d['kind'])
        if any(r.metric not in allowed for r in body.readings):raise HTTPException(422,'Metric is not a capability of this generic simulated device.')
        if body.observed_at<parse_stamp(d['created_at'])-timedelta(minutes=2):raise HTTPException(422,'Observation predates device registration; backfilling cannot bypass baseline warm-up.')
        data=body.model_dump(mode='json');data['readings']=sorted(data['readings'],key=lambda x:x['metric']);digest=fingerprint(data);received=stamp();observed=body.observed_at.isoformat()
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if expected_run_id is not None:
                run=c.execute('SELECT run_id,is_simulating FROM devices WHERE id=?',(body.device_id,)).fetchone()
                if not run or not run['is_simulating'] or run['run_id']!=expected_run_id:raise HTTPException(409,'Simulation run changed.')
            existing=c.execute('SELECT * FROM ingestion_events WHERE device_id=? AND event_id=?',(body.device_id,body.event_id)).fetchone()
            if existing:
                if existing['payload_hash']!=digest:raise HTTPException(409,'Event ID already exists with different content.')
                version=c.execute('SELECT id FROM monitoring_states WHERE event_pk=?',(existing['id'],)).fetchone()['id']
                return {'duplicate':True,'event_pk':existing['id'],'monitoring_version':version,'prediction_updated':False,'source_type':'simulated_device'}
            live=c.execute('SELECT is_simulating FROM devices WHERE id=?',(body.device_id,)).fetchone()
            if not live['is_simulating']:raise HTTPException(409,'Start this device simulation before submitting new simulated observations.')
            cur=c.execute('INSERT INTO ingestion_events(device_id,patient_id,event_id,payload_hash,observed_at,received_at,source_type) VALUES (?,?,?,?,?,?,?)',(body.device_id,body.patient_id,body.event_id,digest,observed,received,body.source_type));event=cur.lastrowid
            prior=c.execute('SELECT snapshot FROM monitoring_states WHERE patient_id=? ORDER BY id DESC LIMIT 1',(body.patient_id,)).fetchone()
            current=json.loads(prior['snapshot'])['current'] if prior else {}
            for r in body.readings:
                c.execute('INSERT INTO device_readings(event_pk,patient_id,device_id,metric,value,unit,observed_at,received_at,source_type) VALUES (?,?,?,?,?,?,?,?,?)',(event,body.patient_id,body.device_id,r.metric,r.value,r.unit,observed,received,body.source_type))
                if r.metric not in current or parse_stamp(observed)>=parse_stamp(current[r.metric]['observed_at']):
                    current[r.metric]={'value':r.value,'unit':r.unit,'observed_at':observed,'received_at':received,'device_id':body.device_id,'source_type':'simulated_device'}
            snapshot={'patient_id':body.patient_id,'synthetic':True,'current':current,'missing_fields':[m for m in METRICS if m not in current],'model_predictions':None,'model_input_eligible':False,'boundary':'Monitoring-only version. Frozen historical risk and features are unchanged.'}
            cur=c.execute('INSERT INTO monitoring_states(patient_id,event_pk,created_at,snapshot) VALUES (?,?,?,?)',(body.patient_id,event,received,json.dumps(snapshot)));version=cur.lastrowid
            c.execute("UPDATE devices SET last_seen_at=?,status='connected_simulation',last_error=NULL WHERE id=?",(received,body.device_id))
            matches=[f'{r.metric}={r.value:g}{r.unit}' for r in body.readings if (r.metric=='spo2' and r.value<=92) or (r.metric=='heart_rate' and r.value>=110)]
            if matches:
                self.notifications.create(category='patient_monitoring',title='Simulated reading matched a demo rule',reason='; '.join(matches)+'. Unvalidated demonstration rules: SpO₂≤92% or heart rate≥110bpm. Not clinical triage, an emergency alert or a model prediction.',source='Validated simulated-device ingestion',source_type='simulated_device',patient_id=body.patient_id,dedupe_key=f"device-rule:{body.device_id}:{received[:13]}",metadata={'device_id':body.device_id,'event_id':body.event_id,'monitoring_version':version},conn=c)
        return {'duplicate':False,'event_pk':event,'monitoring_version':version,'prediction_updated':False,'source_type':'simulated_device'}
    @staticmethod
    def sample(d):
        sequence=d['sequence']+1;seed=int(hashlib.sha256(f"{d['id']}:{d['run_id']}:{sequence}".encode()).hexdigest()[:16],16);rng=random.Random(seed)
        values={'spo2':round(95.5+math.sin(sequence/7)*.8+rng.uniform(-1.2,1.2),1),'heart_rate':round(75+math.sin(sequence/5)*5+rng.uniform(-3,3),1),'resp_rate':round(18+math.sin(sequence/6)+rng.uniform(-1,1),1),'steps':rng.randint(0,min(1000,d['interval_seconds']*2)),'fev1':round(1.65+rng.uniform(-.12,.12),2),'fvc':round(2.8+rng.uniform(-.15,.15),2)}
        fields=next(x['metrics'] for x in DEVICE_CATALOG if x['kind']==d['kind'])
        return {'patient_id':d['patient_id'],'device_id':d['id'],'event_id':f"{d['run_id']}:{sequence}",'observed_at':stamp(),'source_type':'simulated_device','readings':[{'metric':m,'value':values[m],'unit':METRICS[m]['unit']} for m in fields]}
    async def tick(self,app):
        at=stamp()
        with self.store.connect() as c:due=[dict(r) for r in c.execute('SELECT * FROM devices WHERE is_simulating=1 AND (next_due_at IS NULL OR next_due_at<=?) LIMIT 16',(at,))]
        if not due:return
        from backend.app.enhanced.schemas import Ingestion
        for d in due:
            try:
                # The internal simulator is not a doctor session and must not
                # bypass HTTP authorization. Use the same schema and token-checked
                # ingestion service directly; external HTTP still requires its
                # normal doctor session, optional admin token and device token.
                body=Ingestion.model_validate(self.sample(d))
                result=await asyncio.to_thread(self.ingest,body,self.token_for(d['id']),d['run_id'])
                if not result['duplicate']:
                    await app.state.hub.broadcast({'type':'enhanced_updated','patient_id':d['patient_id']})
                with self.store.connect() as c:c.execute('UPDATE devices SET sequence=sequence+1,next_due_at=? WHERE id=? AND run_id=? AND is_simulating=1',((utcnow()+timedelta(seconds=d['interval_seconds'])).isoformat(),d['id'],d['run_id']))
            except Exception as exc:
                with self.store.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    live=c.execute('SELECT is_simulating,run_id FROM devices WHERE id=?',(d['id'],)).fetchone()
                    if live and live['is_simulating'] and live['run_id']==d['run_id']:
                        detail=f'Synthetic ingestion failed ({type(exc).__name__}); simulation stopped. No physical device is involved.'
                        c.execute("UPDATE devices SET status='error',is_simulating=0,last_error=?,next_due_at=NULL WHERE id=?",(detail,d['id']))
                        self.notifications.create(category='data_quality',title='Simulated device ingestion error',reason=detail,source='Backend simulator ingestion service',source_type='system_demo',patient_id=d['patient_id'],dedupe_key=f"device-error:{d['id']}:{d['run_id']}",metadata={'device_id':d['id']},conn=c)
    def sweep_stale(self):
        for d in self.list()['devices']:
            anchor=d['last_seen_at'] or d['created_at'];age=(utcnow()-parse_stamp(anchor)).total_seconds()
            if d['is_simulating'] and age>max(30,d['interval_seconds']*3):
                self.notifications.create(category='data_quality',title='Simulated device stream is stale',reason=f'No simulated ingestion for {round(age)} seconds while simulation is enabled. This is a demo data-quality event, not a hardware/medical alert.',source='Backend stream freshness check',source_type='system_demo',patient_id=d['patient_id'],dedupe_key=f"device-stale:{d['id']}:{d['run_id']}",metadata={'device_id':d['id']})
