"""Composition root for additive demo services; not a second prediction engine."""
import logging
from backend.app.enhanced.settings import Settings,stamp
from backend.app.enhanced.notifications import Notifications
from backend.app.enhanced.registry import Registry
from backend.app.enhanced.devices import Devices
from backend.app.enhanced.environment import Environment
from backend.app.enhanced.email import DemoEmail

class Services:
    def __init__(self,engine,settings=None):
        self.engine=engine;self.store=engine.store;self.settings=settings or Settings.from_env()
        self.notifications=Notifications(self.store);self.registry=Registry(engine,self.notifications)
        self.devices=Devices(self.store,self.settings,self.notifications,self.registry)
        self.environment=Environment(self.store,self.settings,self.notifications)
        self.email=DemoEmail(self.store,self.settings,self.notifications);self._ticks=0
    async def tick(self,app):
        await self.devices.tick(app);self._ticks+=1
        if self._ticks%15==0:
            self.devices.sweep_stale();self.notifications.sync_legacy()
    def failure(self,exc):
        logging.getLogger('pranaguard.enhanced').error('Enhanced background task failure: %s',type(exc).__name__)
        try:self.notifications.create(category='system',title='Demo background service problem',reason=f'Enhanced service task failed ({type(exc).__name__}). Check backend configuration. This is not a clinical or emergency service.',source='Backend service loop',source_type='system_demo',dedupe_key='service-error:'+stamp()[:13])
        except Exception:pass # Database unavailable: sanitized log above remains the fallback.
    def status(self):
        with self.store.connect() as c:
            tables=['registrations','devices','device_readings','monitoring_states','notifications','notification_history','email_outbox','enhanced_audit']
            counts={t:c.execute('SELECT COUNT(*) AS n FROM '+t).fetchone()['n'] for t in tables}
            migrations=[dict(r) for r in c.execute('SELECT version,name,applied_at FROM schema_migrations ORDER BY version')]
        return {'synthetic_only':True,'counts':counts,'migrations':migrations,'environment_enabled':self.settings.environment_enabled,'email':self.email.config(),'real_hardware_supported':False,'new_patient_predictions_supported':False,'model_boundary':'Historical model and context/monitoring streams are isolated. No retraining or feature substitution.','security':'Local synthetic demonstration only. Optional admin token protects writes; device ingestion additionally requires a per-device backend token. Production RBAC, identity/consent, device enrollment, TLS termination and medical-device validation are not implemented.'}
