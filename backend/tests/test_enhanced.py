"""Executed extension tests. Synthetic HTTP test doubles below are NOT provider evidence."""
import asyncio,hashlib,json,socketserver,threading,uuid
from datetime import timedelta
from pathlib import Path
import httpx,pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.store import Store
from backend.app.enhanced.settings import Settings,stamp,utcnow
from backend.app.enhanced.environment import AIR_FIELDS,WEATHER_FIELDS

@pytest.fixture(scope='module')
def _session_client(tmp_path_factory):
    # Load the large immutable historical frame once, not once per parameter case.
    db=tmp_path_factory.mktemp('enhanced-isolated-tests')/'enhanced.sqlite'
    with TestClient(create_app(db,Settings(),background_tasks=False,legacy_demo=True)) as c:yield c

@pytest.fixture
def ec(_session_client):
    from backend.app.enhanced.services import Services
    c=_session_client;e=c.app.state.engine
    # This cleanup is ONLY inside pytest's throwaway DB, never application setup.
    assert 'enhanced-isolated-tests' in str(e.store.path)
    with e.store.connect() as db:
        for table in ['notification_history','notifications','monitoring_states','device_readings','ingestion_events','devices','demo_observations','registrations','enhanced_audit','email_outbox','environment_cache','environment_attempts','scenarios','interventions','alerts','states']:db.execute('DELETE FROM '+table)
        ids=tuple(e.profiles);db.execute('DELETE FROM patients WHERE patient_id NOT IN ('+','.join('?' for _ in ids)+')',ids)
    e.reset();c.app.state.enhanced=Services(e,Settings())
    yield c

def registration(**kw):
    return {'request_id':uuid.uuid4().hex,'fictional_identity_confirmed':True,'demo_alias':'AtlasDemo','age':58,'city':'Pune','sex':'Female',**kw}
def patient(c,**kw):
    r=c.post('/api/enhanced/registry/patients',json=registration(**kw));assert r.status_code==200,r.text;return r.json()['patient_id']
def device(c,pid=None,kind='pulse_oximeter'):
    pid=pid or patient(c);r=c.post('/api/enhanced/devices',json={'patient_id':pid,'kind':kind,'interval_seconds':2});assert r.status_code==200,r.text
    d=r.json();assert c.post('/api/enhanced/devices/'+d['id']+'/start',json={'interval_seconds':2}).status_code==200;return d

def event(d,**kw):
    return {'patient_id':d['patient_id'],'device_id':d['id'],'event_id':uuid.uuid4().hex,'observed_at':stamp(),'source_type':'simulated_device','readings':[{'metric':'spo2','value':95.5,'unit':'%'},{'metric':'heart_rate','value':77,'unit':'bpm'}],**kw}
def ingest(c,d,data):return c.post('/api/enhanced/ingestion',json=data,headers={'X-Device-Token':c.app.state.enhanced.devices.token_for(d['id'])})

def test_migration_is_additive_idempotent_and_checksum_guard(tmp_path):
    db=tmp_path/'legacy.sqlite'
    import sqlite3
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE patients(patient_id TEXT PRIMARY KEY,profile TEXT NOT NULL)');c.execute('INSERT INTO patients VALUES (?,?)',('PG-KEEP',json.dumps({'display_name':'Synthetic existing'})))
    s=Store(db);Store(db)
    with s.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM patients').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0]==7
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        c.execute("UPDATE schema_migrations SET sha256='tampered'")
    with pytest.raises(RuntimeError,match='checksum'):Store(db)

def test_registration_unique_id_and_original_cohort_preserved(ec):
    before=ec.get('/api/overview').json();p1=patient(ec);p2=patient(ec)
    assert p1!=p2 and p1.startswith('PG-DEMO-')
    listed=ec.get('/api/enhanced/registry/patients').json();assert listed['total']==122 and listed['original_cohort_count']==120
    assert ec.get('/api/overview').json()==before
    detail=ec.get('/api/enhanced/registry/patients/'+p1).json()
    assert detail['profile']['display_name'].startswith('Fictional demo') and detail['model_state'] is None
    assert detail['baseline']['prediction_supported'] is False and detail['baseline']['observed_hours']==0

def test_registration_idempotency_and_conflict(ec):
    data=registration();a=ec.post('/api/enhanced/registry/patients',json=data).json();b=ec.post('/api/enhanced/registry/patients',json=data).json()
    assert a['patient_id']==b['patient_id'] and b['duplicate']
    assert ec.post('/api/enhanced/registry/patients',json={**data,'age':61}).status_code==409

@pytest.mark.parametrize('change',[{'age':12},{'city':'Unregistered'},{'fictional_identity_confirmed':False},{'source_type':'real_ehr'},{'baseline_spo2':101},{'patient_id':'PG-0001'},{'demo_alias':'<script>'},{'age':'NaN'}])
def test_registration_validation(ec,change):assert ec.post('/api/enhanced/registry/patients',json=registration(**change)).status_code==422

def test_patient_filters_and_manual_values_do_not_skip_baseline(ec):
    pid=patient(ec,city='Delhi',baseline_spo2=97,baseline_heart_rate=70,baseline_resp_rate=18)
    assert len(ec.get('/api/enhanced/registry/patients',params={'q':pid,'city':'Delhi','risk':'unavailable','status':'baseline_not_started','sex':'Female'}).json()['patients'])==1
    assert not ec.get('/api/enhanced/registry/patients',params={'q':pid,'city':'Mumbai'}).json()['patients']
    assert ec.get('/api/enhanced/registry/patients/'+pid).json()['baseline']['complete'] is False
    assert ec.get('/api/enhanced/registry/patients/NO-PATIENT').status_code==404

def test_device_capability_catalog_and_association_auth(ec,monkeypatch):
    result=ec.get('/api/enhanced/devices').json();assert len(result['catalog'])==4 and result['hardware_supported'] is False
    d=device(ec);assert 'token_hash' not in d and d['status']=='disconnected' and not d['hardware_connected']
    assert ec.post('/api/enhanced/ingestion',json=event(d)).status_code==401
    assert ec.post('/api/enhanced/ingestion',json=event(d),headers={'X-Device-Token':'wrong'}).status_code==401
    monkeypatch.setenv('PRANAGUARD_ADMIN_TOKEN','backend-test-secret')
    assert ec.post('/api/enhanced/devices/'+d['id']+'/stop',json={}).status_code==401
    assert ec.post('/api/enhanced/devices/'+d['id']+'/stop',json={},headers={'X-Demo-Token':'backend-test-secret'}).status_code==200

def test_ingestion_persists_readings_versions_provenance_and_deduplicates(ec):
    d=device(ec);data=event(d);one=ingest(ec,d,data);assert one.status_code==200,one.text
    two=ingest(ec,d,data);assert two.json()['duplicate'] and two.json()['monitoring_version']==one.json()['monitoring_version']
    changed={**data,'readings':[{'metric':'spo2','value':94,'unit':'%'},{'metric':'heart_rate','value':77,'unit':'bpm'}]};assert ingest(ec,d,changed).status_code==409
    profile=ec.get('/api/enhanced/registry/patients/'+d['patient_id']).json()
    assert len(profile['readings'])==2 and len(profile['monitoring_versions'])==1
    assert profile['latest_monitoring']['snapshot']['model_predictions'] is None
    assert profile['readings'][0]['source_type']=='simulated_device'
    assert profile['devices'][0]['status']=='connected_simulation'

@pytest.mark.parametrize('bad',[{'readings':[{'metric':'spo2','value':120,'unit':'%'}]},{'readings':[{'metric':'heart_rate','value':70,'unit':'wrong'}]},{'readings':[{'metric':'fev1','value':1.6,'unit':'L'}]},{'source_type':'real_device'},{'observed_at':'2026-01-01T00:00:00Z'},{'observed_at':'2026-11-05T01:00:00'},{'observed_at':(utcnow()+timedelta(days=1)).isoformat()},{'readings':[{'metric':'spo2','value':95,'unit':'%'},{'metric':'spo2','value':94,'unit':'%'}]}])
def test_ingestion_rejects_invalid_or_backdated_data(ec,bad):
    d=device(ec);assert ingest(ec,d,event(d,**bad)).status_code==422

def test_association_mismatch_and_stopped_ingestion(ec):
    d=device(ec);assert ingest(ec,d,event(d,patient_id='PG-0001')).status_code==409
    ec.post('/api/enhanced/devices/'+d['id']+'/stop',json={});assert ingest(ec,d,event(d)).status_code==409
    assert any('stopped' in n['title'] for n in ec.get('/api/enhanced/notifications').json()['notifications'])

def test_backend_simulator_uses_validated_ingestion_and_stops(ec):
    d=device(ec);s=ec.app.state.enhanced
    ec.portal.call(s.devices.tick,ec.app)
    assert len(ec.get('/api/enhanced/devices/'+d['id']+'/readings').json()['readings'])==2
    ec.post('/api/enhanced/devices/'+d['id']+'/stop',json={});ec.portal.call(s.devices.tick,ec.app)
    assert len(ec.get('/api/enhanced/devices/'+d['id']+'/readings').json()['readings'])==2

def test_fast_samples_never_become_72_hours(ec):
    pid=patient(ec);pulse=device(ec,pid);watch=device(ec,pid,'smartwatch');at=stamp()
    for _ in range(10):
        assert ingest(ec,pulse,event(pulse,observed_at=at)).status_code==200
        assert ingest(ec,watch,event(watch,observed_at=at,readings=[{'metric':'resp_rate','value':18,'unit':'breaths/min'}])).status_code==200
    baseline=ec.get('/api/enhanced/registry/patients/'+pid).json()['baseline']
    assert baseline['observed_hours']==1 and baseline['elapsed_hours']==0 and not baseline['complete'] and not baseline['prediction_supported']

def test_even_complete_hourly_test_fixture_does_not_manufacture_model_eligibility(ec):
    pid=patient(ec);pulse=device(ec,pid);watch=device(ec,pid,'smartwatch');first=(utcnow()-timedelta(hours=73)).replace(microsecond=0)
    # Test-only clock fixture. Public API does NOT accept device creation/backfill overrides.
    with ec.app.state.engine.store.connect() as c:c.execute('UPDATE devices SET created_at=? WHERE patient_id=?',((first-timedelta(minutes=1)).isoformat(),pid))
    for i in range(73):
        at=(first+timedelta(hours=i)).isoformat()
        assert ingest(ec,pulse,event(pulse,observed_at=at)).status_code==200
        assert ingest(ec,watch,event(watch,observed_at=at,readings=[{'metric':'resp_rate','value':18,'unit':'breaths/min'}])).status_code==200
    result=ec.get('/api/enhanced/registry/patients/'+pid).json()
    assert result['baseline']['complete'] and result['baseline']['observed_hours']==72
    assert not result['baseline']['prediction_supported'] and result['model_state'] is None

def test_manual_observations_reviews_notification_rule_and_reset_preservation(ec):
    pid=patient(ec)
    assert ec.post(f'/api/enhanced/registry/patients/{pid}/observations',json={'fictional_data_confirmed':True,'symptom_score':8,'adherence':.4,'note':'Fictional test observation.'}).status_code==200
    assert ec.post(f'/api/enhanced/registry/patients/{pid}/reviews',json={'note':'Reviewed fictional baseline.'}).status_code==200
    ec.post('/api/replay/reset',json={'prime_hours':0})
    profile=ec.get('/api/enhanced/registry/patients/'+pid).json()
    assert len(profile['reviews'])==1 and len(profile['observations'])==1
    assert any(n['category']=='patient_monitoring' for n in profile['notifications'])

def test_legacy_alert_bridge_both_directions_and_review_history(ec):
    e=ec.app.state.engine;e.reset(e.demo['focus_hour']);alert=e.store.alerts(e.demo['patient_id'])[0]
    notices=ec.get('/api/enhanced/notifications').json()['notifications'];n=next(x for x in notices if x['legacy_alert_id']==alert['id']);nid=n['id']
    assert ec.patch(f'/api/enhanced/notifications/{nid}',json={'status':'under_review','note':'Fictional review started.'}).status_code==200
    assert e.store.alerts(e.demo['patient_id'])[0]['status']=='acknowledged'
    assert ec.patch(f"/api/alerts/{alert['id']}",json={'status':'resolved','note':'Original workflow reviewed.'}).status_code==200
    detail=ec.get(f'/api/enhanced/notifications/{nid}').json();assert detail['status']=='resolved' and len(detail['history'])==3
    assert ec.patch(f'/api/enhanced/notifications/{nid}',json={'status':'active'}).status_code==409
    assert ec.patch(f'/api/enhanced/notifications/{nid}',json={'status':'closed'}).status_code==200
    e.reset();assert ec.get(f'/api/enhanced/notifications/{nid}').json()['legacy_alert_id'] is None
    with e.store.connect() as c:assert c.execute("SELECT COUNT(*) FROM enhanced_audit WHERE source='alerts'").fetchone()[0]>=1

def test_notification_unread_filters_and_all_review_states(ec):
    n=ec.post('/api/enhanced/notifications/test',json={}).json();nid=n['id'];assert n['unread']
    assert ec.get('/api/enhanced/notifications/counts').json()['unread']==1
    ec.patch(f'/api/enhanced/notifications/{nid}',json={'read':True})
    assert not ec.get('/api/enhanced/notifications',params={'unread_only':True}).json()['notifications']
    for status in ('acknowledged','under_review','resolved','closed'):
        result=ec.patch(f'/api/enhanced/notifications/{nid}',json={'status':status,'note':'Demo status transition.'});assert result.status_code==200,result.text
    detail=ec.get(f'/api/enhanced/notifications/{nid}').json();assert len(detail['history'])==6
    assert ec.get('/api/enhanced/notifications',params={'category':'system','status':'closed'}).json()['notifications'][0]['id']==nid
    assert ec.patch(f'/api/enhanced/notifications/{nid}',json={}).status_code==422

def test_stale_device_and_sanitized_ingestion_error_notifications(ec,monkeypatch):
    d=device(ec);s=ec.app.state.enhanced
    with s.store.connect() as c:c.execute('UPDATE devices SET last_seen_at=? WHERE id=?',((utcnow()-timedelta(minutes=10)).isoformat(),d['id']))
    s.devices.sweep_stale()
    def broken(_):raise RuntimeError('private-token-must-not-leak')
    monkeypatch.setattr(s.devices,'sample',broken);ec.portal.call(s.devices.tick,ec.app)
    text=ec.get('/api/enhanced/notifications').text
    assert 'stale' in text and 'ingestion error' in text and 'private-token-must-not-leak' not in text
    assert s.devices.list()['devices'][0]['status']=='error'

# Explicit synthetic provider transport doubles: never shipped as current/fallback data.
def provider_double(request):
    air='air-quality' in request.url.host;fields=AIR_FIELDS if air else WEATHER_FIELDS
    values={'pm2_5':60,'pm10':80,'nitrogen_dioxide':20,'ozone':30,'us_aqi':110,'temperature_2m':29,'relative_humidity_2m':50,'weather_code':2,'wind_speed_10m':5,'wind_direction_10m':90}
    return httpx.Response(200,json={'latitude':18.5,'longitude':73.9,'current':{'time':stamp(),**{k:values[k] for k in fields}},'current_units':{k:v[1] for k,v in fields.items()}})

def test_environment_disabled_uses_real_historical_cache_and_missing_values(ec):
    s=ec.app.state.enhanced
    s.environment.transport=httpx.MockTransport(lambda request:pytest.fail('Disabled environment must not access network.'))
    data=ec.get('/api/enhanced/environment/Pune').json()
    assert data['components']['air']['status']=='historical_fallback'
    assert data['components']['air']['valid_at'].startswith('2026-09-29')
    assert data['components']['air']['values']['us_aqi'] is None
    assert data['components']['weather']['values']['wind_speed_10m'] is None
    assert all(not x['used_by_frozen_model'] for x in data['components'].values())

def test_environment_success_cache_throttle_and_context_notification(ec):
    s=ec.app.state.enhanced;s.settings.environment_enabled=True;calls=[]
    def handler(r):calls.append(str(r.url));return provider_double(r)
    s.environment.transport=httpx.MockTransport(handler)
    first=ec.get('/api/enhanced/environment/Pune').json();second=ec.get('/api/enhanced/environment/Pune').json()
    assert first['components']['air']['status']=='live' and second['components']['air']['status']=='cached'
    ec.post('/api/enhanced/environment/Pune/refresh',json={});assert len(calls)==2
    assert 'NOT Indian' in first['aqi_scale'] and first['components']['air']['source_type']=='modelled_external'
    assert any(n['category']=='environment' for n in s.notifications.list()['notifications'])

def test_environment_failure_partial_data_and_unavailable_without_cache(ec,tmp_path):
    s=ec.app.state.enhanced;s.settings.environment_enabled=True
    def handler(r):return httpx.Response(503) if 'air-quality' in r.url.host else provider_double(r)
    s.environment.transport=httpx.MockTransport(handler)
    data=ec.get('/api/enhanced/environment/Delhi').json();assert data['components']['air']['status']=='historical_fallback' and data['components']['weather']['status']=='live'
    assert 'HTTP503' in data['components']['air']['last_error']
    s.environment.cache_dir=tmp_path;s.environment.transport=httpx.MockTransport(lambda r:httpx.Response(503))
    data=ec.get('/api/enhanced/environment/Mumbai').json();assert all(x['status']=='unavailable' for x in data['components'].values())
    assert ec.get('/api/enhanced/environment/London').status_code==422

def test_stale_cache_failure_never_fabricates_replacement(ec):
    s=ec.app.state.enhanced;s.settings.environment_enabled=True;s.environment.transport=httpx.MockTransport(provider_double)
    first=ec.get('/api/enhanced/environment/Pune').json();old=(utcnow()-timedelta(hours=4)).isoformat()
    with s.store.connect() as c:c.execute('UPDATE environment_cache SET retrieved_at=?',(old,));c.execute('UPDATE environment_attempts SET attempted_at=?,next_retry_at=?',(old,old))
    s.environment.transport=httpx.MockTransport(lambda r:httpx.Response(429))
    result=ec.get('/api/enhanced/environment/Pune').json();assert result['components']['air']['status']=='stale_cache'
    assert result['components']['air']['values']==first['components']['air']['values'] and result['components']['air']['freshness']=='stale'

def test_provider_validation_and_api_key_redaction(ec):
    s=ec.app.state.enhanced;s.settings.environment_enabled=True;s.settings.provider_key='secret-not-for-output'
    def bad(r):
        data=provider_double(r).json();data['current_units'][next(iter(data['current_units']))]='wrong-unit';return httpx.Response(200,json=data)
    s.environment.transport=httpx.MockTransport(bad)
    text=ec.get('/api/enhanced/environment/Pune').text;assert 'secret-not-for-output' not in text and 'historical_fallback' in text and 'ValueError' in text

def test_monitoring_and_current_environment_never_change_frozen_twin(ec):
    s=ec.app.state.enhanced;pid=s.engine.demo['patient_id'];before=s.engine.patient(pid);d=device(ec,pid)
    assert ingest(ec,d,event(d,readings=[{'metric':'spo2','value':91,'unit':'%'}])).status_code==200
    s.settings.environment_enabled=True;s.environment.transport=httpx.MockTransport(provider_double);ec.get('/api/enhanced/environment/Pune')
    assert s.engine.patient(pid)==before
    data=ec.get('/api/enhanced/provenance',params={'patient_id':pid}).json()
    assert data['no_real_patient_records'] and any(r['source_type']=='simulated_device' for r in data['records'])
    assert all(not r['used_by_frozen_model'] for r in data['records'] if r['category']=='current_environment')

def test_protected_scientific_and_design_baseline_with_documented_font_fix():
    root=Path(__file__).resolve().parents[2];manifest=json.loads((root/'docs/enhanced/BASELINE_MANIFEST.json').read_text())
    for path,digest in manifest['protected_files'].items():
        content=(root/path).read_bytes()
        if path=='frontend/src/styles.css':
            # The pre-existing font fix in 14bb7535de is the sole approved change.
            # Check the complete current file AND reconstruct the recorded baseline.
            assert hashlib.sha256(content).hexdigest()=='c3fc6f4abf0a66e968e9514419cc6c5e7f8cbca32d0c30d7e76a92def7cf2939'
            before=b'"Inter Variable",Inter';after=b'Inter'
            assert content.count(before)==1
            content=content.replace(before,after,1)
        assert hashlib.sha256(content).hexdigest()==digest,path

def test_email_disabled_preview_recipient_override_and_rate_limit(ec):
    r=ec.post('/api/enhanced/email/test',json={});assert r.json()['status']=='not_sent_disabled' and not r.json()['inbox_delivery_verified']
    assert ec.post('/api/enhanced/email/test',json={}).status_code==429
    assert ec.post('/api/enhanced/email/test',json={'recipient':'arbitrary@example.test'}).status_code==422
    with ec.app.state.engine.store.connect() as c:c.execute('UPDATE email_outbox SET created_at=?',((utcnow()-timedelta(minutes=1)).isoformat(),))
    ec.app.state.enhanced.settings.email_mode='preview';assert ec.post('/api/enhanced/email/test',json={}).json()['status']=='preview_not_sent'

class SMTPSink(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b'220 localhost demo sink\r\n');self.wfile.flush();data=[];in_data=False
        while True:
            line=self.rfile.readline()
            if not line:break
            if in_data:
                if line==b'.\r\n':self.server.messages.append(b''.join(data));in_data=False;self.wfile.write(b'250 captured locally\r\n')
                else:data.append(line)
            elif line.upper().startswith(b'DATA'):in_data=True;self.wfile.write(b'354 end with dot\r\n')
            elif line.upper().startswith(b'QUIT'):self.wfile.write(b'221 bye\r\n');self.wfile.flush();break
            else:self.wfile.write(b'250 localhost\r\n')
            self.wfile.flush()

def test_actual_local_smtp_acceptance_no_patient_details(ec):
    with socketserver.TCPServer(('127.0.0.1',0),SMTPSink) as server:
        server.messages=[];thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            s=ec.app.state.enhanced.settings;s.email_mode='smtp';s.smtp_host='127.0.0.1';s.smtp_port=server.server_address[1];s.smtp_starttls=False;s.allow_insecure_local=True;s.smtp_from='demo@example.test';s.demo_recipient='configured-demo@example.test'
            r=ec.post('/api/enhanced/email/test',json={}).json();assert r['status']=='accepted_by_smtp' and not r['inbox_delivery_verified']
            assert len(server.messages)==1 and b'PG-' not in server.messages[0] and b'patient details' in server.messages[0]
        finally:server.shutdown();thread.join(timeout=2)

def test_smtp_configuration_failure_redacts_errors(ec,monkeypatch):
    import smtplib
    s=ec.app.state.enhanced.settings;s.email_mode='smtp';s.smtp_host='smtp.example.test';s.smtp_from='demo@example.test';s.demo_recipient='configured-demo@example.test'
    def fail(**kwargs):raise smtplib.SMTPAuthenticationError(535,b'password-secret-must-not-leak')
    monkeypatch.setattr(smtplib,'SMTP',fail)
    result=ec.post('/api/enhanced/email/test',json={});assert result.json()['status']=='failed'
    assert 'password-secret-must-not-leak' not in ec.get('/api/enhanced/email').text

def test_restart_preserves_registered_data_but_stops_simulation(tmp_path):
    db=tmp_path/'restart.sqlite'
    with TestClient(create_app(db,Settings(),background_tasks=False,legacy_demo=True)) as c:
        d=device(c);assert ingest(c,d,event(d)).status_code==200
    import gc
    del c
    gc.collect()
    with TestClient(create_app(db,Settings(),background_tasks=False,legacy_demo=True)) as c:
        profile=c.get('/api/enhanced/registry/patients/'+d['patient_id']).json()
        assert len(profile['readings'])==2 and profile['devices'][0]['status']=='disconnected' and not profile['devices'][0]['is_simulating']
        assert profile['latest_monitoring']['snapshot']['model_predictions'] is None

def test_provider_backoff_budget_and_retry_after(ec):
    s=ec.app.state.enhanced;s.settings.environment_enabled=True;calls=[]
    def busy(r):calls.append(str(r.url));return httpx.Response(429,headers={'Retry-After':'600'})
    s.environment.transport=httpx.MockTransport(busy)
    ec.get('/api/enhanced/environment/Pune');ec.post('/api/enhanced/environment/Pune/refresh',json={});assert len(calls)==2
    with s.store.connect() as c:
        rows=c.execute('SELECT * FROM environment_attempts').fetchall()
        assert all(r['consecutive_failures']==1 and r['next_retry_at'] for r in rows)
        old=(utcnow()-timedelta(hours=1)).isoformat();c.execute('UPDATE environment_attempts SET attempted_at=?,next_retry_at=?',(old,old))
    ec.get('/api/enhanced/environment/Pune')
    with s.store.connect() as c:assert all(r['consecutive_failures']==2 for r in c.execute('SELECT * FROM environment_attempts'))
    assert len(calls)==4

def test_http_success_with_old_provider_timestamp_is_explicitly_stale(ec):
    s=ec.app.state.enhanced;s.settings.environment_enabled=True
    def old(r):
        value=provider_double(r).json();value['current']['time']=(utcnow()-timedelta(hours=6)).isoformat();return httpx.Response(200,json=value)
    s.environment.transport=httpx.MockTransport(old);value=ec.get('/api/enhanced/environment/Pune').json()
    assert all(c['status']=='stale_cache' and c['freshness']=='stale' for c in value['components'].values())
    assert any('timestamp is stale' in n['title'] for n in s.notifications.list()['notifications'])

def test_backend_settings_clamp_request_rate_and_hide_secrets(monkeypatch):
    monkeypatch.setenv('PRANAGUARD_ENV_RETRY_SECONDS','1');monkeypatch.setenv('PRANAGUARD_ENV_TTL_SECONDS','1')
    monkeypatch.setenv('OPEN_METEO_API_KEY','private-api-value');monkeypatch.setenv('PRANAGUARD_SMTP_PASSWORD','private-smtp-value')
    s=Settings.from_env();assert s.retry_seconds>=300 and s.cache_ttl_seconds>=300
    assert 'private-api-value' not in repr(s) and 'private-smtp-value' not in repr(s)

def test_background_service_error_is_sanitized_and_notifies(ec):
    ec.app.state.enhanced.failure(RuntimeError('do-not-leak-service-detail'))
    text=ec.get('/api/enhanced/notifications').text
    assert 'background service problem' in text and 'do-not-leak-service-detail' not in text

def test_simulator_uses_internal_ingestion_when_admin_guard_is_configured(ec,monkeypatch):
    d=device(ec);monkeypatch.setenv('PRANAGUARD_ADMIN_TOKEN','backend-only-test-admin')
    ec.portal.call(ec.app.state.enhanced.devices.tick,ec.app)
    assert len(ec.get('/api/enhanced/devices/'+d['id']+'/readings').json()['readings'])==2
    assert ec.post('/api/enhanced/notifications/test',json={}).status_code==401


def test_stale_simulator_run_cannot_ingest_or_stop_restarted_run(ec):
    from backend.app.enhanced.schemas import Ingestion
    devices=ec.app.state.enhanced.devices;d=device(ec)
    old=devices.require(d['id']);body=Ingestion.model_validate(devices.sample(old))
    assert ec.post('/api/enhanced/devices/'+d['id']+'/stop',json={}).status_code==200
    assert ec.post('/api/enhanced/devices/'+d['id']+'/start',json={'interval_seconds':2}).status_code==200
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:devices.ingest(body,devices.token_for(d['id']),old['run_id'])
    assert error.value.status_code==409
    assert devices.require(d['id'])['is_simulating']==1
    assert not ec.get('/api/enhanced/devices/'+d['id']+'/readings').json()['readings']
