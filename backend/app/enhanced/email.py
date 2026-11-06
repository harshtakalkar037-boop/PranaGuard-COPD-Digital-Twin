"""Explicit SMTP connectivity test only; no automatic patient/model-alert email."""
import re, smtplib, ssl
from email.message import EmailMessage
from fastapi import HTTPException
from backend.app.enhanced.settings import stamp,parse_stamp,utcnow

TEST_BODY='PranaGuard synthetic prototype email connectivity test. This is not a patient notification, clinical intervention or emergency message. No patient details are included. Inbox delivery is not verified by this application.'

class DemoEmail:
    def __init__(self,store,settings,notifications):self.store=store;self.settings=settings;self.notifications=notifications
    def config(self):
        s=self.settings
        return {'mode':s.email_mode,'recipient_configured':bool(s.demo_recipient),'smtp_configured':bool(s.smtp_host and s.smtp_from and s.demo_recipient),'automatic_patient_email':False,'notice':'Test channel only. SMTP acceptance is not proof of inbox delivery. No patient details are sent.'}
    def history(self):
        with self.store.connect() as c:return {'outbox':[dict(r) for r in c.execute('SELECT * FROM email_outbox ORDER BY id DESC LIMIT 30')],**self.config()}
    def send_test(self):
        s=self.settings
        # Reserve before network I/O so concurrent clicks cannot send duplicate tests.
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');last=c.execute('SELECT created_at FROM email_outbox ORDER BY id DESC LIMIT 1').fetchone()
            if last and (utcnow()-parse_stamp(last['created_at'])).total_seconds()<30:raise HTTPException(429,'Wait 30 seconds between demo email tests.')
            cur=c.execute("INSERT INTO email_outbox(created_at,status,detail) VALUES (?,'pending','Preparing demo-only connectivity test.')",(stamp(),));eid=cur.lastrowid
        status='not_sent_disabled';detail='Email is disabled. No message was sent.'
        if s.email_mode=='preview':status='preview_not_sent';detail='Preview recorded in SQLite. No SMTP connection or email delivery occurred.'
        elif s.email_mode=='smtp':
            try:
                address=lambda v:bool(re.fullmatch(r'[^@\s,;<>]+@[^@\s,;<>]+',v))
                if not s.smtp_host or not address(s.smtp_from) or not address(s.demo_recipient):raise ValueError('Missing/invalid SMTP host or single configured addresses.')
                local=s.smtp_host in ('localhost','127.0.0.1','::1')
                if not (s.smtp_ssl or s.smtp_starttls) and not (local and s.allow_insecure_local):raise ValueError('Encrypted SMTP is required except an explicitly configured localhost test sink.')
                msg=EmailMessage();msg['Subject']='PranaGuard — synthetic demo connectivity test';msg['From']=s.smtp_from;msg['To']=s.demo_recipient;msg.set_content(TEST_BODY)
                smtp_cls=smtplib.SMTP_SSL if s.smtp_ssl else smtplib.SMTP
                kwargs={'host':s.smtp_host,'port':s.smtp_port,'timeout':8}
                if s.smtp_ssl:kwargs['context']=ssl.create_default_context()
                with smtp_cls(**kwargs) as smtp:
                    if s.smtp_starttls and not s.smtp_ssl:smtp.starttls(context=ssl.create_default_context())
                    if s.smtp_user:smtp.login(s.smtp_user,s.smtp_password)
                    smtp.send_message(msg)
                status='accepted_by_smtp';detail='Configured SMTP server accepted the demo test. Inbox delivery is not verified.'
            except Exception as exc:
                # Never store exception text: providers can include credentials/addresses.
                status='failed';detail=f'Demo email failed ({type(exc).__name__}). Check backend-only configuration; no patient email was attempted.'
        elif s.email_mode not in ('disabled','preview'):
            status='configuration_error';detail='Invalid email mode. Use disabled, preview or smtp. No message was sent.'
        with self.store.connect() as c:c.execute('UPDATE email_outbox SET status=?,detail=? WHERE id=?',(status,detail,eid))
        self.notifications.create(category='system',title='Demo email test result',reason=detail,source='Backend SMTP test channel',source_type='system_demo',dedupe_key=f'email-test:{eid}',metadata={'delivery_status':status,'outbox_id':eid})
        return {'id':eid,'status':status,'detail':detail,'patient_data_included':False,'inbox_delivery_verified':False}
