"""Care workspace service. Demo-only identities (documented passwords, local PBKDF2 hashes,
expiring bearer sessions). This is NOT production identity/RBAC; claims stay honest."""
import base64, hashlib, json, secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

def utcnow():return datetime.now(timezone.utc)
def stamp():return utcnow().isoformat()

SESSION_HOURS=12
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
            self._seed_demo_content(c)
            self._ensure_patient_workspace_records(c)
            self._ensure_demo_prescription_pdf(c)
    def _seed_demo_content(self,c):
        """One-to-one demo: linked patient PG-0071 gets a little example history so the dashboards
        demonstrate connected workflows out of the box. Idempotent: only seeds a completely empty store."""
        if c.execute('SELECT 1 FROM daily_logs LIMIT 1').fetchone() or c.execute('SELECT 1 FROM documents LIMIT 1').fetchone():return
        pid='PG-0071';at=stamp();from datetime import timedelta as _td
        today=utcnow().date()
        logs=[('better',7.5,'good',1800,'Dal, rice, cooked veg; reduced salt',20,'Walked without stopping today. Slept well.'),
              ('same',7.0,'fair',1600,'Khichdi, soup, fruit',10,'Usual breathlessness in the morning.'),
              ('same',6.5,'fair',1700,'Rice, dal, yoghurt',15,'Slightly more cough than usual.')]
        for i,(wb,sh,sq,w,food,actv,note) in enumerate(logs):
            d=(today-_td(days=i)).isoformat()
            cur=c.execute('INSERT INTO daily_logs(patient_id,entry_date,water_ml,food_notes,activity_minutes,sleep_hours,sleep_quality,wellbeing,notes,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                          (pid,d,w,food,actv,sh,sq,wb,note,'pat-pg0071',at,at))
            c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,after_json) VALUES (?,?,?,?,?,?,?,?)',
                      (at,'pat-pg0071','patient','created','daily_log',str(cur.lastrowid),pid,json.dumps({'entry_date':d,'seeded_demo':True})))
        med=c.execute("INSERT INTO plan_medications(patient_id,name,dose,frequency,added_by,created_at) VALUES (?,?,?,?,?,?)",
                      (pid,'Inhaled bronchodilator (demo label)','2 puffs','twice daily','dr-atlas',at))
        mid=med.lastrowid
        for i in range(2):
            t=(utcnow()-_td(days=i)).isoformat()
            c.execute('INSERT INTO med_adherence(patient_id,medication_id,as_prescribed,taken_at,missed_reason,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?)',
                      (pid,mid,1,t,None,None,'pat-pg0071',t))
        c.execute('INSERT INTO follow_ups(patient_id,doctor,instructions,due_at,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
                  (pid,'dr-atlas','Demo instruction: keep recording sputum colour daily and bring the diary to the next review.',(today+_td(days=3)).isoformat()+'T09:00:00+00:00','scheduled',at,at))
        demo_doc=base64.b64decode('JVBERi0xLjQKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3VyY2UpCjEgMCBvYmoKPDwKL0YxIDIgMCBSIC9GMiAzIDAgUgo+PgplbmRvYmoKMiAwIG9iago8PAovQmFzZUZvbnQgL0hlbHZldGljYSAvRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZyAvTmFtZSAvRjEgL1N1YnR5cGUgL1R5cGUxIC9UeXBlIC9Gb250Cj4+CmVuZG9iagozIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhLUJvbGQgL0VuY29kaW5nIC9XaW5BbnNpRW5jb2RpbmcgL05hbWUgL0YyIC9TdWJ0eXBlIC9UeXBlMSAvVHlwZSAvRm9udAo+PgplbmRvYmoKNCAwIG9iago8PAovQ29udGVudHMgOCAwIFIgL01lZGlhQm94IFsgMCAwIDU5NS4yNzU2IDg0MS44ODk4IF0gL1BhcmVudCA3IDAgUiAvUmVzb3VyY2VzIDw8Ci9Gb250IDEgMCBSIC9Qcm9jU2V0IFsgL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSSBdCj4+IC9Sb3RhdGUgMCAvVHJhbnMgPDwKCj4+IAogIC9UeXBlIC9QYWdlCj4+CmVuZG9iago1IDAgb2JqCjw8Ci9QYWdlTW9kZSAvVXNlTm9uZSAvUGFnZXMgNyAwIFIgL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0F1dGhvciAoUHJhbmFHdWFyZCBEZW1vbnN0cmF0aW9uKSAvQ3JlYXRpb25EYXRlIChEOjIwMjYxMTA3MTQyODQ3KzAwJzAwJykgL0NyZWF0b3IgKFwodW5zcGVjaWZpZWRcKSkgL0tleXdvcmRzICgpIC9Nb2REYXRlIChEOjIwMjYxMTA3MTQyODQ3KzAwJzAwJykgL1Byb2R1Y2VyIChSZXBvcnRMYWIgUERGIExpYnJhcnkgLSBcKG9wZW5zb3VyY2VcKSkgCiAgL1N1YmplY3QgKFwodW5zcGVjaWZpZWRcKSkgL1RpdGxlIChQcmFuYUd1YXJkIERlbW8gUHJlc2NyaXB0aW9uKSAvVHJhcHBlZCAvRmFsc2UKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0NvdW50IDEgL0tpZHMgWyA0IDAgUiBdIC9UeXBlIC9QYWdlcwo+PgplbmRvYmoKOCAwIG9iago8PAovRmlsdGVyIFsgL0FTQ0lJODVEZWNvZGUgL0ZsYXRlRGVjb2RlIF0gL0xlbmd0aCAxNzU0Cj4+CnN0cmVhbQpHYXRtPEQwK0RqJkg5dFlmVDBhRWtrJj1lZWpoQD5QWU9oS25ELj5eMTM7SW0mX3F1L2c4OFRhck42IVA5ZVwjYUsxVztTbFtAWVxDR1ZYWUFdPVtnJGgxJilKJVRGMDM7PiIzJVdUOyFMNUEuaTUlIywnPC5vO05FX3FXK1RkW2hVT0EpVUlkZHIhLl8xV0ZkIkQ/MDVPP08oTC0+Vio6bkAsP0oiL2YwJyhLTFFYNGxUOm4sTWNfRGBVLyUwKWRXRCJSWkg/VnJ0WUlAMF5OaFE2KGRbb2JVQyw9KS0lUD9LUWE9XWl1STtzYjU3LSxpIl4sY0NRaXB1J0ZuJyw6I2o/blMoWVpOTzhTN2UlLUVibW0xY2FCayRSJztIOS5PJV9BdVBeKDExXFFMUF8nYmpNXkg9J3NfMCZabEo9ZjRsTTJBI2gqSEszbXRvMk02N1xXOUs1LVhlJk1KdFkrcXFSXixlLmNKRWxKK2sjWzJGT0tldTA2WyVsKD5cbWZxQ0I4UV0kSTZ1JC9GcixbPUNPYElNcChxZ2VjcjtmYEE/QytgRGVNdFkhQzw8a3U8UEosSDQvT10oL0tFTmBpYEhYWnVKUU5tcl88bV9aM2I4SV9jWCVWUiN1WydIWHNVP2xdRSs0UlwiYSElYlhdWzVFSUVVVEp0XTtII2tVQF4oWiw4OTg9TmJPKVNxKUpkYT0yRUZLO1Q3UlNdMyZSWGlkPlY2LiJuR00tTGdlXkVcN044UjwrXGZZJ10xTzJuZTJTNlBRYzVeIlBLSEAkXl5FZ08jLC4tdWNYc1EsO1NvTTEpSk5HMltIVGBESUhVblZdQ2c2VWZVZEVDc1cnWFRLRiVSaW0/cU1jQ0pSOyVhLCcxL0Q9cV9WTF1KRjdqOTxrOWBtTix0dT80LWddQlRAUHE9Ryo3IlI1V3EodENPOC9IbDVlSUZSNFFSXyVpTk1zUmNrX0lvTWVMWFloc0ouL2xSYEs9JTpbalVnPWA+LmJVcDdFSk9JUk9aWiQxXTtLWXF0SF9pXWdRU2kzSmVebilcZ2k6TWo9ZEVbSWpVa0lWIU9rMjlVPFc7PyV0YT51QypWXUomNnJYTDw+ZSMuIkM8Tlo+QCFMSFUnMmFEYCpeV29fZVMsOy9gMHFnZkI6JlJVaDxkJzFjTy9xMC0hXHNFRlFYS24vKzVEY0xOZnIqPUUuTmwqKCg1J25SalE/S0p1YEI8Wmc+KGw1OSE/JUVPPiQsIzxiSG8rIjtOcz5eVjh1V2g+a1JVOTlLZXVpXkhKPTFYSysublQ1IihBMjxwLkkhIzUjPzkpMjJXYSsjY0shZiNfTjxkWy1gb1NUOzlKbyRIUSZLJTRMUjJUXk9VIiVgaFtZNEY0YGZuaFA6XFFQV3JHbGc5S2FNbW1aWV9jREM9bWNrPzxbXCQhSmhUXD00SmpHNWUqLDMlK1Q1dU80SENfdSYuY2VxV0BkQnFQJytQTT5HX1FeXEdAZTVDXFdwYj49SUJOKVppaW9OMnU1XT89Z21dXTNbPjIzSHJbQShKJVJbLldSMS04YT83bSE3ZFVlJjE+JFFEaTcpcVVZTTErRXNmb283aT5pSzc1KC5dMl06T11LaUppVEQhO0F1ME1lSj0hQHFUOEFYJls+MXMxOldfbUtmY18sSE1HPkFdTk4sZiI3OGA1MHRWOD0nSVY9RTBhTyE6R0lKQ0M3K2w/WVVgNmcyNkRULkdmV2xRQVhbOkpIXSw+RSZHbyFfT2ZmLldwTUpHR2Y9V2g1Qz80PmskZ3I+X21PcTdVbSg6ITBoSCMxNyFBYnBNJThAKGtRRUI+WjROKCIsTnFeNyg9PDRSR0YrY11MKHFaKkhmRlhzUkFPamVNLjsodV0kcCNqaFQ5cFIqbVM7UCloI2dCPlZwT3FgP1goLz5nWllOKlIuS2lOYjJPZEdyLWEzVC1lcjQnI01vW3E/b0tgRSNlK1xIbDBdV1VbLi5dNSMnJkdiTCYxMEhPQiw/TmlGcmckdG1bM0lnWFZJVDM8KU83dSRTZk0uNiklIWwnIylKR1U1PilyJiVASEpdXC5jPmNhaGp0OkdAQi5nOUddJzJRMkVydDpjZUBRUTRTLTAuQjNDOCtVSEVVKVdsNktbNipsOWpgYHQ/JDBwSyVnU2AzRkFyaGw/Z103RGlNP01BNU1FRShAT2leKFZxXXFbYmRYS1coU0NPbEJPIyg1czo2KW46N2c0PCE4XTonTnFXMWw3LDknX0hDIVZnQWlbYW5dQW5vJGkpRm5oaHNeTi50VHMzT3ElJkIoSUouLGYubmtfYG8iOSNJQkZqTCZ+PmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDkKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDYxIDAwMDAwIG4gCjAwMDAwMDAxMDIgMDAwMDAgbiAKMDAwMDAwMDIwOSAwMDAwMCBuIAowMDAwMDAwMzIxIDAwMDAwIG4gCjAwMDAwMDA1MjQgMDAwMDAgbiAKMDAwMDAwMDU5MiAwMDAwMCBuIAowMDAwMDAwODk4IDAwMDAwIG4gCjAwMDAwMDA5NTcgMDAwMDAgbiAKdHJhaWxlcgo8PAovSUQgCls8MDliYjQyMjFlYzk1OTVkY2JiZmJlMTk5ZjE2NDQ0YzM+PDA5YmI0MjIxZWM5NTk1ZGNiYmZiZTE5OWYxNjQ0NGMzPl0KJSBSZXBvcnRMYWIgZ2VuZXJhdGVkIFBERiBkb2N1bWVudCAtLSBkaWdlc3QgKG9wZW5zb3VyY2UpCgovSW5mbyA2IDAgUgovUm9vdCA1IDAgUgovU2l6ZSA5Cj4+CnN0YXJ0eHJlZgoyODAyCiUlRU9GCg==')
        import hashlib as _hl
        c.execute('INSERT INTO documents(patient_id,title,doc_type,doc_date,notes,filename,media_type,size,sha256,data,uploaded_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                  (pid,'Sample COPD prescription (fictional)','prescription',today.isoformat(),'Formatted fictional PDF for software demonstration only; not medical advice.','sample-copd-prescription.pdf','application/pdf',len(demo_doc),_hl.sha256(demo_doc).hexdigest(),demo_doc,'dr-atlas',at))
        c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,after_json) VALUES (?,?,?,?,?,?,?,?)',
                  (at,'dr-atlas','doctor','seeded','document','demo',pid,json.dumps({'title':'Sample COPD prescription (fictional)','seeded_demo':True})))
    def _ensure_patient_workspace_records(self,c):
        """Idempotently populate the linked synthetic patient with persisted workspace history.
        These are fictional records in the already-disclosed synthetic cohort, not real patient data."""
        pid='PG-0071'
        today=utcnow().date()
        from datetime import timedelta as _td
        def day(n): return (today-_td(days=n)).isoformat()
        def at(n,hour=8,minute=0): return (datetime.combine(today-_td(days=n),datetime.min.time(),tzinfo=timezone.utc)+_td(hours=hour,minutes=minute)).isoformat()
        # Patient-submitted daily wellbeing records. Seed per patient, not only on an empty database.
        if not c.execute('SELECT 1 FROM daily_logs WHERE patient_id=? LIMIT 1',(pid,)).fetchone():
            entries=[
                (0,1900,'Oats, dal, rice and cooked vegetables',28,7.5,'good','better','Morning walk completed; slept well.'),
                (1,1650,'Khichdi, curd and fruit',18,7.0,'fair','same','Usual morning cough; no notable change reported.'),
                (2,1750,'Rice, dal and vegetable soup',22,7.0,'good','same','Completed usual household activity.'),
                (3,1500,'Soft rice, dal and banana',12,6.5,'fair','same','Needed a short rest after walking.'),
                (4,1800,'Chapati, dal and cooked vegetables',25,7.5,'good','better','Reported a comfortable day overall.')
            ]
            for offset,water,food,activity,sleep,quality,wellbeing,note in entries:
                d=day(offset); created=at(offset,19,30)
                cur=c.execute('''INSERT INTO daily_logs(patient_id,entry_date,water_ml,food_notes,activity_minutes,sleep_hours,sleep_quality,wellbeing,notes,created_by,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',(pid,d,water,food,activity,sleep,quality,wellbeing,note,'pat-pg0071',created,created))
                c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,after_json) VALUES (?,?,?,?,?,?,?,?)',
                    (created,'pat-pg0071','patient','created','daily_log',str(cur.lastrowid),pid,json.dumps({'entry_date':d,'seeded_synthetic_record':True})))
        # A clinician-authored documentation plan, with an auditable revision row.
        if not c.execute('SELECT 1 FROM care_plans WHERE patient_id=?',(pid,)).fetchone():
            created=at(5,10,15)
            c.execute('INSERT INTO care_plans VALUES (?,?,?,?,?,?,?,?,?,?)',
                (pid,'dr-atlas','Maintain a consistent symptom and wellbeing diary for review.','Record usual daily activity and note changes from the patient’s reported baseline.','Record medication-taking patterns in the adherence diary for discussion at review.','City-level environmental context is contextual only and is not a personal exposure measurement.',day(-7),'active',created,created))
            c.execute('INSERT INTO care_plan_revisions(patient_id,created_at,actor,change_note,snapshot) VALUES (?,?,?,?,?)',
                (pid,created,'dr-atlas','Initial documented plan',json.dumps({'status':'active','seeded_synthetic_record':True})))
            c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,after_json) VALUES (?,?,?,?,?,?,?,?)',
                (created,'dr-atlas','doctor','created','care_plan',pid,pid,json.dumps({'status':'active','seeded_synthetic_record':True})))
        # Sputum diary: patient-entered records; no clinical interpretation is attached.
        if not c.execute('SELECT 1 FROM sputum_entries WHERE patient_id=? LIMIT 1',(pid,)).fetchone():
            entries=[
                (1,8,15,'clear','scant','thin',2,1,'Usual morning entry.'),
                (2,8,10,'white','scant','thin',3,2,'No notable change from usual report.'),
                (4,8,12,'clear','none','thin',2,1,'No sputum reported at this entry.')
            ]
            for offset,hour,minute,colour,volume,consistency,cough,breath,note in entries:
                created=at(offset,hour,minute)
                cur=c.execute('INSERT INTO sputum_entries(patient_id,occurred_at,colour,volume,consistency,cough,breathlessness,note,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                    (pid,created,colour,volume,consistency,cough,breath,note,created))
                c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,after_json) VALUES (?,?,?,?,?,?,?,?)',
                    (created,'pat-pg0071','patient','created','sputum_entry',str(cur.lastrowid),pid,json.dumps({'colour':colour,'seeded_synthetic_record':True})))
        # A review and follow-up are persisted in the same workflow tables used by the UI.
        if not c.execute('SELECT 1 FROM care_reviews WHERE patient_id=? LIMIT 1',(pid,)).fetchone():
            created=at(1,11,0)
            cur=c.execute('INSERT INTO care_reviews(patient_id,doctor,status,note,follow_up_at,state_version,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                (pid,'dr-atlas','completed','Reviewed the recent patient-entered wellbeing and sputum diary records. No treatment change documented.',None,self.state_version(pid),created,created))
            c.execute('INSERT INTO care_review_events(review_id,created_at,event,actor,note) VALUES (?,?,?,?,?)',
                (cur.lastrowid,created,'created → completed','dr-atlas','Routine documentation review.'))
            c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,after_json) VALUES (?,?,?,?,?,?,?,?)',
                (created,'dr-atlas','doctor','created','care_review',str(cur.lastrowid),pid,json.dumps({'status':'completed','seeded_synthetic_record':True})))
        if not c.execute('SELECT 1 FROM follow_ups WHERE patient_id=? LIMIT 1',(pid,)).fetchone():
            created=at(1,11,5)
            c.execute('INSERT INTO follow_ups(patient_id,doctor,instructions,due_at,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
                (pid,'dr-atlas','Bring the symptom diary and medication-adherence record to the next routine review.',at(-5,9,0),'scheduled',created,created))
        # Existing medication/adherence tables power both the patient and clinician views.
        if not c.execute('SELECT 1 FROM plan_medications WHERE patient_id=? AND retired=0',(pid,)).fetchone():
            created=at(6,9,0)
            cur=c.execute('INSERT INTO plan_medications(patient_id,name,dose,frequency,added_by,created_at) VALUES (?,?,?,?,?,?)',
                (pid,'Maintenance inhaler (fictional record)','As documented','As recorded in the sample history','dr-atlas',created))
            mid=cur.lastrowid
            for offset in range(4):
                taken=at(offset,8,0)
                c.execute('INSERT INTO med_adherence(patient_id,medication_id,as_prescribed,taken_at,missed_reason,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?)',
                    (pid,mid,1,taken,None,'Patient-reported adherence entry.','pat-pg0071',taken))

    def _ensure_demo_prescription_pdf(self,c):
        """Upgrade the original seeded TXT demo document to a formatted PDF in existing demo databases."""
        import hashlib as _hl
        import base64 as _b64
        raw=_b64.b64decode('JVBERi0xLjQKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3VyY2UpCjEgMCBvYmoKPDwKL0YxIDIgMCBSIC9GMiAzIDAgUgo+PgplbmRvYmoKMiAwIG9iago8PAovQmFzZUZvbnQgL0hlbHZldGljYSAvRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZyAvTmFtZSAvRjEgL1N1YnR5cGUgL1R5cGUxIC9UeXBlIC9Gb250Cj4+CmVuZG9iagozIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhLUJvbGQgL0VuY29kaW5nIC9XaW5BbnNpRW5jb2RpbmcgL05hbWUgL0YyIC9TdWJ0eXBlIC9UeXBlMSAvVHlwZSAvRm9udAo+PgplbmRvYmoKNCAwIG9iago8PAovQ29udGVudHMgOCAwIFIgL01lZGlhQm94IFsgMCAwIDU5NS4yNzU2IDg0MS44ODk4IF0gL1BhcmVudCA3IDAgUiAvUmVzb3VyY2VzIDw8Ci9Gb250IDEgMCBSIC9Qcm9jU2V0IFsgL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSSBdCj4+IC9Sb3RhdGUgMCAvVHJhbnMgPDwKCj4+IAogIC9UeXBlIC9QYWdlCj4+CmVuZG9iago1IDAgb2JqCjw8Ci9QYWdlTW9kZSAvVXNlTm9uZSAvUGFnZXMgNyAwIFIgL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0F1dGhvciAoUHJhbmFHdWFyZCBEZW1vbnN0cmF0aW9uKSAvQ3JlYXRpb25EYXRlIChEOjIwMjYxMTA3MTQyODQ3KzAwJzAwJykgL0NyZWF0b3IgKFwodW5zcGVjaWZpZWRcKSkgL0tleXdvcmRzICgpIC9Nb2REYXRlIChEOjIwMjYxMTA3MTQyODQ3KzAwJzAwJykgL1Byb2R1Y2VyIChSZXBvcnRMYWIgUERGIExpYnJhcnkgLSBcKG9wZW5zb3VyY2VcKSkgCiAgL1N1YmplY3QgKFwodW5zcGVjaWZpZWRcKSkgL1RpdGxlIChQcmFuYUd1YXJkIERlbW8gUHJlc2NyaXB0aW9uKSAvVHJhcHBlZCAvRmFsc2UKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0NvdW50IDEgL0tpZHMgWyA0IDAgUiBdIC9UeXBlIC9QYWdlcwo+PgplbmRvYmoKOCAwIG9iago8PAovRmlsdGVyIFsgL0FTQ0lJODVEZWNvZGUgL0ZsYXRlRGVjb2RlIF0gL0xlbmd0aCAxNzU0Cj4+CnN0cmVhbQpHYXRtPEQwK0RqJkg5dFlmVDBhRWtrJj1lZWpoQD5QWU9oS25ELj5eMTM7SW0mX3F1L2c4OFRhck42IVA5ZVwjYUsxVztTbFtAWVxDR1ZYWUFdPVtnJGgxJilKJVRGMDM7PiIzJVdUOyFMNUEuaTUlIywnPC5vO05FX3FXK1RkW2hVT0EpVUlkZHIhLl8xV0ZkIkQ/MDVPP08oTC0+Vio6bkAsP0oiL2YwJyhLTFFYNGxUOm4sTWNfRGBVLyUwKWRXRCJSWkg/VnJ0WUlAMF5OaFE2KGRbb2JVQyw9KS0lUD9LUWE9XWl1STtzYjU3LSxpIl4sY0NRaXB1J0ZuJyw6I2o/blMoWVpOTzhTN2UlLUVibW0xY2FCayRSJztIOS5PJV9BdVBeKDExXFFMUF8nYmpNXkg9J3NfMCZabEo9ZjRsTTJBI2gqSEszbXRvMk02N1xXOUs1LVhlJk1KdFkrcXFSXixlLmNKRWxKK2sjWzJGT0tldTA2WyVsKD5cbWZxQ0I4UV0kSTZ1JC9GcixbPUNPYElNcChxZ2VjcjtmYEE/QytgRGVNdFkhQzw8a3U8UEosSDQvT10oL0tFTmBpYEhYWnVKUU5tcl88bV9aM2I4SV9jWCVWUiN1WydIWHNVP2xdRSs0UlwiYSElYlhdWzVFSUVVVEp0XTtII2tVQF4oWiw4OTg9TmJPKVNxKUpkYT0yRUZLO1Q3UlNdMyZSWGlkPlY2LiJuR00tTGdlXkVcN044UjwrXGZZJ10xTzJuZTJTNlBRYzVeIlBLSEAkXl5FZ08jLC4tdWNYc1EsO1NvTTEpSk5HMltIVGBESUhVblZdQ2c2VWZVZEVDc1cnWFRLRiVSaW0/cU1jQ0pSOyVhLCcxL0Q9cV9WTF1KRjdqOTxrOWBtTix0dT80LWddQlRAUHE9Ryo3IlI1V3EodENPOC9IbDVlSUZSNFFSXyVpTk1zUmNrX0lvTWVMWFloc0ouL2xSYEs9JTpbalVnPWA+LmJVcDdFSk9JUk9aWiQxXTtLWXF0SF9pXWdRU2kzSmVebilcZ2k6TWo9ZEVbSWpVa0lWIU9rMjlVPFc7PyV0YT51QypWXUomNnJYTDw+ZSMuIkM8Tlo+QCFMSFUnMmFEYCpeV29fZVMsOy9gMHFnZkI6JlJVaDxkJzFjTy9xMC0hXHNFRlFYS24vKzVEY0xOZnIqPUUuTmwqKCg1J25SalE/S0p1YEI8Wmc+KGw1OSE/JUVPPiQsIzxiSG8rIjtOcz5eVjh1V2g+a1JVOTlLZXVpXkhKPTFYSysublQ1IihBMjxwLkkhIzUjPzkpMjJXYSsjY0shZiNfTjxkWy1gb1NUOzlKbyRIUSZLJTRMUjJUXk9VIiVgaFtZNEY0YGZuaFA6XFFQV3JHbGc5S2FNbW1aWV9jREM9bWNrPzxbXCQhSmhUXD00SmpHNWUqLDMlK1Q1dU80SENfdSYuY2VxV0BkQnFQJytQTT5HX1FeXEdAZTVDXFdwYj49SUJOKVppaW9OMnU1XT89Z21dXTNbPjIzSHJbQShKJVJbLldSMS04YT83bSE3ZFVlJjE+JFFEaTcpcVVZTTErRXNmb283aT5pSzc1KC5dMl06T11LaUppVEQhO0F1ME1lSj0hQHFUOEFYJls+MXMxOldfbUtmY18sSE1HPkFdTk4sZiI3OGA1MHRWOD0nSVY9RTBhTyE6R0lKQ0M3K2w/WVVgNmcyNkRULkdmV2xRQVhbOkpIXSw+RSZHbyFfT2ZmLldwTUpHR2Y9V2g1Qz80PmskZ3I+X21PcTdVbSg6ITBoSCMxNyFBYnBNJThAKGtRRUI+WjROKCIsTnFeNyg9PDRSR0YrY11MKHFaKkhmRlhzUkFPamVNLjsodV0kcCNqaFQ5cFIqbVM7UCloI2dCPlZwT3FgP1goLz5nWllOKlIuS2lOYjJPZEdyLWEzVC1lcjQnI01vW3E/b0tgRSNlK1xIbDBdV1VbLi5dNSMnJkdiTCYxMEhPQiw/TmlGcmckdG1bM0lnWFZJVDM8KU83dSRTZk0uNiklIWwnIylKR1U1PilyJiVASEpdXC5jPmNhaGp0OkdAQi5nOUddJzJRMkVydDpjZUBRUTRTLTAuQjNDOCtVSEVVKVdsNktbNipsOWpgYHQ/JDBwSyVnU2AzRkFyaGw/Z103RGlNP01BNU1FRShAT2leKFZxXXFbYmRYS1coU0NPbEJPIyg1czo2KW46N2c0PCE4XTonTnFXMWw3LDknX0hDIVZnQWlbYW5dQW5vJGkpRm5oaHNeTi50VHMzT3ElJkIoSUouLGYubmtfYG8iOSNJQkZqTCZ+PmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDkKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDYxIDAwMDAwIG4gCjAwMDAwMDAxMDIgMDAwMDAgbiAKMDAwMDAwMDIwOSAwMDAwMCBuIAowMDAwMDAwMzIxIDAwMDAwIG4gCjAwMDAwMDA1MjQgMDAwMDAgbiAKMDAwMDAwMDU5MiAwMDAwMCBuIAowMDAwMDAwODk4IDAwMDAwIG4gCjAwMDAwMDA5NTcgMDAwMDAgbiAKdHJhaWxlcgo8PAovSUQgCls8MDliYjQyMjFlYzk1OTVkY2JiZmJlMTk5ZjE2NDQ0YzM+PDA5YmI0MjIxZWM5NTk1ZGNiYmZiZTE5OWYxNjQ0NGMzPl0KJSBSZXBvcnRMYWIgZ2VuZXJhdGVkIFBERiBkb2N1bWVudCAtLSBkaWdlc3QgKG9wZW5zb3VyY2UpCgovSW5mbyA2IDAgUgovUm9vdCA1IDAgUgovU2l6ZSA5Cj4+CnN0YXJ0eHJlZgoyODAyCiUlRU9GCg==')
        row=c.execute("SELECT id FROM documents WHERE patient_id='PG-0071' AND filename IN ('demo-action-plan.txt','sample-copd-prescription.pdf') ORDER BY id LIMIT 1").fetchone()
        if not row:
            return
        c.execute("UPDATE documents SET title=?,doc_type='prescription',doc_date=?,notes=?,filename=?,media_type='application/pdf',size=?,sha256=?,data=?,uploaded_by='dr-atlas' WHERE id=?",
                  ('Sample COPD prescription (fictional)',utcnow().date().isoformat(),'Formatted fictional PDF for software demonstration only; not medical advice.','sample-copd-prescription.pdf',len(raw),_hl.sha256(raw).hexdigest(),raw,row['id']))
    # ---------- authentication ----------
    def login(self,username,password):
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM care_users WHERE username=?',(username.strip().lower(),)).fetchone()
            if not row or not secrets.compare_digest(row['pass_hash'],hash_password(password,row['salt'])):
                raise HTTPException(401,'Incorrect demo username or password.')
            token='pgw_'+secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
            c.execute('DELETE FROM care_sessions WHERE username=? AND expires_at<?',(row['username'],stamp()))
            c.execute('INSERT INTO care_sessions VALUES (?,?,?,?)',(digest,row['username'],stamp(),(utcnow()+timedelta(hours=SESSION_HOURS)).isoformat()))
        return {'token':token,'user':self.public_user(row)}
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
            self.audit(c,user,'created','care_review',rid,pid,after={'status':status,'note':note[:200]})
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
            self.audit(c,user,'updated','care_review',rid,detail['review']['patient_id'],before={'status':row['status']},after={'status':status or row['status'],'note_added':bool(note)})
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
            self.audit(c,user,'updated' if old else 'created','care_plan',pid,pid,before=dict(old) if old else None,after={'goals':data['goals'][:200],'status':data['status'],'review_date':data['review_date']})
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
            self.audit(c,user,'created','sputum_entry',eid,pid,after={'occurred_at':data['occurred_at'],'colour':data['colour'],'attachment':bool(saved_attachment)})
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
            self.audit(c,user,'reviewed','sputum_entry',eid,row['patient_id'],after={'review_note':note})
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
    # ---------- audit trail ----------
    def audit(self,c,user,action,entity,entity_id,patient_id,before=None,after=None):
        c.execute('INSERT INTO audit_events(created_at,actor,role,action,entity,entity_id,patient_id,before_json,after_json) VALUES (?,?,?,?,?,?,?,?,?)',
                  (stamp(),user['username'],user['role'],action,entity,str(entity_id) if entity_id is not None else None,patient_id,
                   json.dumps(before) if before is not None else None,json.dumps(after) if after is not None else None))
    def audit_events(self,user,pid,limit=100):
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            rows=[dict(r) for r in c.execute('SELECT id,created_at,actor,role,action,entity,entity_id,before_json,after_json FROM audit_events WHERE patient_id=? ORDER BY id DESC LIMIT ?',(pid,limit))]
        return {'events':rows,'note':'Immutable demo audit trail. Original submissions and timestamps are preserved in snapshots.'}
    def require_patient(self,user):
        if user['role']!='patient':raise HTTPException(403,'This area is for the patient demo account only.')
    def require_doctor(self,user):
        if user['role']!='doctor':raise HTTPException(403,'Only the doctor demo account can perform this action.')
    def own_pid(self,user):
        self.require_patient(user)
        if not user['patient_id']:raise HTTPException(403,'No linked synthetic twin for this account.')
        return user['patient_id']
    # ---------- daily wellbeing logs ----------
    def add_daily_log(self,user,data):
        pid=self.own_pid(user);at=stamp()
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO daily_logs(patient_id,entry_date,water_ml,food_notes,activity_minutes,sleep_hours,sleep_quality,wellbeing,notes,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                          (pid,data['entry_date'],data['water_ml'],data['food_notes'],data['activity_minutes'],data['sleep_hours'],data['sleep_quality'],data['wellbeing'],data['notes'],user['username'],at,at))
            lid=cur.lastrowid
            self.audit(c,user,'created','daily_log',lid,pid,after={'entry_date':data['entry_date'],'water_ml':data['water_ml'],'activity_minutes':data['activity_minutes'],'sleep_hours':data['sleep_hours'],'wellbeing':data['wellbeing']})
        return {'id':lid,'notice':'Daily log saved. Doctor can review it; it is documentation, not a diagnosis.'}
    def list_daily_logs(self,user,pid=None,page=1,page_size=30):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:self.require_assigned(user,pid)
        with self.store.connect() as c:
            total=c.execute('SELECT COUNT(*) AS n FROM daily_logs WHERE patient_id=?',(pid,)).fetchone()['n']
            rows=[dict(r) for r in c.execute('SELECT * FROM daily_logs WHERE patient_id=? ORDER BY entry_date DESC,id DESC LIMIT ? OFFSET ?',(pid,page_size,(page-1)*page_size))]
        return {'items':rows,'total':total,'page':page,'page_size':page_size,'patient_id':pid,'viewer_is_patient':user['role']=='patient',
                'note':'Patient-reported fictional wellbeing log. Entries are documentation, not telemetry.'}
    def edit_daily_log(self,user,lid,data):
        pid=self.own_pid(user);at=stamp()
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM daily_logs WHERE id=?',(lid,)).fetchone()
            if not row or row['patient_id']!=pid:raise HTTPException(404,'Daily log entry not found for this account.')
            before=dict(row)
            c.execute('UPDATE daily_logs SET water_ml=?,food_notes=?,activity_minutes=?,sleep_hours=?,sleep_quality=?,wellbeing=?,notes=?,edited=1,updated_at=? WHERE id=?',
                      (data['water_ml'],data['food_notes'],data['activity_minutes'],data['sleep_hours'],data['sleep_quality'],data['wellbeing'],data['notes'],at,lid))
            after=dict(c.execute('SELECT * FROM daily_logs WHERE id=?',(lid,)).fetchone())
            self.audit(c,user,'edited','daily_log',lid,pid,before={k:before[k] for k in ('water_ml','food_notes','activity_minutes','sleep_hours','sleep_quality','wellbeing','notes','created_at')},
                       after={k:after[k] for k in ('water_ml','food_notes','activity_minutes','sleep_hours','sleep_quality','wellbeing','notes')})
        return {'id':lid,'edited':True,'notice':'Correction saved. The original submission stays in the audit trail.'}
    def review_daily_log(self,user,lid,note):
        self.require_doctor(user)
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM daily_logs WHERE id=?',(lid,)).fetchone()
            if not row:raise HTTPException(404,'Daily log entry not found.')
            self.require_assigned(user,row['patient_id'])
            if row['reviewed_at']:raise HTTPException(409,'Already reviewed; demo keeps reviews immutable.')
            c.execute('UPDATE daily_logs SET reviewed_by=?,reviewed_at=?,review_note=? WHERE id=?',(user['username'],stamp(),note,lid))
            self.audit(c,user,'reviewed','daily_log',lid,row['patient_id'],after={'review_note':note})
        return {'id':lid,'reviewed':True}
    # ---------- plan medications (doctor-authored) ----------
    def list_medications(self,user,pid=None):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:pass
        self.require_assigned(user,pid)
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            meds=[dict(r) for r in c.execute('SELECT id,patient_id,name,dose,frequency,added_by,created_at,retired FROM plan_medications WHERE patient_id=? AND retired=0 ORDER BY id',(pid,))]
        return {'medication_options':meds,'note':'Clinician-documented demo medication list. Patients only report adherence; they cannot edit prescriptions.'}
    def add_medication(self,user,pid,data):
        self.require_doctor(user);self.require_assigned(user,pid);at=stamp()
        with self.store.connect() as c:
            exists=c.execute('SELECT 1 FROM plan_medications WHERE patient_id=? AND retired=0 AND LOWER(name)=LOWER(?)',(pid,data['name'])).fetchone()
            if exists:raise HTTPException(409,f"Medication '{data['name']}' is already on the documented list.")
            cur=c.execute('INSERT INTO plan_medications(patient_id,name,dose,frequency,added_by,created_at) VALUES (?,?,?,?,?,?)',
                          (pid,data['name'],data['dose'],data['frequency'],user['username'],at))
            self.audit(c,user,'added','plan_medication',cur.lastrowid,pid,after={'name':data['name'],'dose':data['dose'],'frequency':data['frequency']})
        return {'id':cur.lastrowid,'notice':'Demo medication documented (text record only — nothing is prescribed or automated).'}
    def add_adherence(self,user,data):
        pid=self.own_pid(user);at=stamp()
        with self.store.connect() as c:
            med=c.execute('SELECT * FROM plan_medications WHERE id=? AND patient_id=? AND retired=0',(data['medication_id'],pid)).fetchone()
            if not med:raise HTTPException(422,'Unknown medication id for this account. Adherence can only reference clinician-documented medication.')
            if not data['as_prescribed'] and not (data.get('missed_reason') or '').strip():
                raise HTTPException(422,'When a dose is missed, a short reason/note is required.')
            cur=c.execute('INSERT INTO med_adherence(patient_id,medication_id,as_prescribed,taken_at,missed_reason,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?)',
                          (pid,data['medication_id'],1 if data['as_prescribed'] else 0,data['taken_at'],data.get('missed_reason'),data.get('note'),user['username'],at))
            self.audit(c,user,'reported','med_adherence',cur.lastrowid,pid,after={'medication':med['name'],'as_prescribed':bool(data['as_prescribed']),'taken_at':data['taken_at']})
        return {'id':cur.lastrowid,'notice':'Adherence report saved (patient-reported, fictional).'}
    def list_adherence(self,user,pid=None,page=1,page_size=30):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:pass
        self.require_assigned(user,pid)
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            total=c.execute('SELECT COUNT(*) AS n FROM med_adherence WHERE patient_id=?',(pid,)).fetchone()['n']
            rows=[dict(r) for r in c.execute('''SELECT a.*,m.name AS medication_name,m.dose,m.frequency FROM med_adherence a
                JOIN plan_medications m ON m.id=a.medication_id WHERE a.patient_id=? ORDER BY a.taken_at DESC LIMIT ? OFFSET ?''',(pid,page_size,(page-1)*page_size))]
        return {'items':rows,'total':total,'page':page,'page_size':page_size}
    # ---------- clinical documents ----------
    BAD_EXT=('.exe','.bat','.cmd','.sh','.js','.msi','.apk','.com','.scr')
    MAGIC={b'%PDF':'application/pdf',b'\x89PNG':'image/png',b'\xff\xd8\xff':'image/jpeg'}
    def upload_document(self,user,pid,data):
        self.require_doctor(user);self.require_assigned(user,pid);at=stamp()
        fn=data['filename'].lower()
        if any(fn.endswith(e) for e in self.BAD_EXT):raise HTTPException(422,'Executable or unsafe file names are rejected. Allowed: PDF, PNG, JPEG, WEBP, plain text.')
        raw=base64.b64decode(data['data_base64'],validate=True)
        if not raw:raise HTTPException(422,'Empty file.')
        if len(raw)>1_572_864:raise HTTPException(422,'Document exceeds the 1.5 MB demo limit.')
        media=data['media_type']
        if media in self.MAGIC.values():
            ok=False
            for sig,mime in self.MAGIC.items():
                if raw.startswith(sig):ok=(mime==media);break
            if not ok:raise HTTPException(422,'File signature does not match the declared type; upload rejected.')
        digest=hashlib.sha256(raw).hexdigest()
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO documents(patient_id,title,doc_type,doc_date,notes,filename,media_type,size,sha256,data,uploaded_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                          (pid,data['title'],data['doc_type'],data['doc_date'],data['notes'],data['filename'],media,len(raw),digest,raw,user['username'],at))
            self.audit(c,user,'uploaded','document',cur.lastrowid,pid,after={'title':data['title'],'type':data['doc_type'],'size':len(raw),'sha256':digest})
        return {'id':cur.lastrowid,'sha256_12':digest[:12],'notice':'Document stored as a demo record. Documents are record-keeping, never AI diagnosis.'}
    def list_documents(self,user,pid=None):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:pass
        self.require_assigned(user,pid)
        self.require_assigned(user,pid)
        with self.store.connect() as c:
            rows=[dict(r) for r in c.execute('SELECT id,patient_id,title,doc_type,doc_date,notes,filename,media_type,size,sha256,uploaded_by,created_at FROM documents WHERE patient_id=? ORDER BY id DESC',(pid,))]
        return {'items':rows,'note':'Documents shared with the linked patient only. Metadata carries SHA-256 provenance.'}
    def get_document(self,user,did):
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM documents WHERE id=?',(did,)).fetchone()
            if not row:raise HTTPException(404,'Document not found.')
            self.require_assigned(user,row['patient_id'])
            if hashlib.sha256(row['data']).hexdigest()!=row['sha256']:raise HTTPException(500,'Document checksum mismatch; record quarantined.')
        return row
    def delete_document(self,user,did):
        self.require_doctor(user)
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM documents WHERE id=?',(did,)).fetchone()
            if not row:raise HTTPException(404,'Document not found.')
            self.require_assigned(user,row['patient_id'])
            keep={k:row[k] for k in ('patient_id','title','doc_type','filename','size','sha256','uploaded_by','created_at')}
            c.execute('DELETE FROM documents WHERE id=?',(did,))
            self.audit(c,user,'deleted','document',did,row['patient_id'],before=keep)
        return {'deleted':True,'notice':'Record removed; metadata retained in the audit trail.'}
    # ---------- follow-ups ----------
    def create_follow_up(self,user,pid,data):
        self.require_doctor(user);self.require_assigned(user,pid);at=stamp()
        with self.store.connect() as c:
            cur=c.execute('INSERT INTO follow_ups(patient_id,doctor,instructions,due_at,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
                          (pid,user['username'],data['instructions'],data['due_at'],'scheduled',at,at))
            self.audit(c,user,'scheduled','follow_up',cur.lastrowid,pid,after={'instructions':data['instructions'][:200],'due_at':data['due_at']})
        return {'id':cur.lastrowid,'notice':'Follow-up instruction saved and shared with the linked patient.'}
    def list_follow_ups(self,user,pid=None,include_history=True):
        if user['role']=='patient':
            own=self.own_pid(user)
            if pid is not None and pid!=own:raise HTTPException(403,f'{pid} is not assigned to this demo account.')
            pid=own
        else:pass
        self.require_assigned(user,pid)
        if pid:self.require_assigned(user,pid)
        ids=self.assigned_ids(user)
        with self.store.connect() as c:
            if pid:
                rows=[dict(r) for r in c.execute('SELECT * FROM follow_ups WHERE patient_id=? ORDER BY status!="scheduled", due_at IS NULL, due_at',(pid,))]
            else:
                marks=','.join('?' for _ in ids) or "''"
                rows=[dict(r) for r in c.execute(f'SELECT * FROM follow_ups WHERE patient_id IN ({marks}) ORDER BY status!="scheduled", due_at IS NULL, due_at LIMIT 100',tuple(ids))] if ids else []
        if not include_history:rows=[r for r in rows if r['status']=='scheduled']
        return {'items':rows,'note':'Doctor-issued demo instructions. They remind and inform; they do not change treatment automatically.'}
    def complete_follow_up(self,user,fid,status):
        self.require_doctor(user)
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM follow_ups WHERE id=?',(fid,)).fetchone()
            if not row:raise HTTPException(404,'Follow-up not found.')
            self.require_assigned(user,row['patient_id'])
            if row['status']!='scheduled':raise HTTPException(409,f"Follow-up is already '{row['status']}'; demo keeps completion immutable.")
            at=stamp()
            c.execute("UPDATE follow_ups SET status=?,updated_at=?,completed_at=?,completed_by=? WHERE id=?",(status,at,at if status=='completed' else None,user['username'] if status=='completed' else None,fid))
            self.audit(c,user,status,'follow_up',fid,row['patient_id'],before={'status':'scheduled'},after={'status':status})
        return {'id':fid,'status':status}
    # ---------- patient home aggregate ----------
    def patient_home(self,user):
        pid=self.own_pid(user)
        detail=self.services.registry.detail(pid)
        plan=self.get_plan(user,pid)
        fu=self.list_follow_ups(user,pid)
        docs=self.list_documents(user,pid)['items']
        logs=self.list_daily_logs(user,page_size=14)['items']
        adh=self.list_adherence(user,page_size=14)['items']
        today=stamp()[:10]
        logged_today=any(l['entry_date']==today for l in logs)
        streak=0;day=today
        from datetime import timedelta as _td
        dates={l['entry_date'] for l in logs}
        while day in dates:
            streak+=1;day=(datetime.fromisoformat(day)-_td(days=1)).date().isoformat()
        now=stamp()
        upcoming=[f for f in fu['items'] if f['status']=='scheduled' and (not f['due_at'] or f['due_at'][:10]>=now[:10])]
        overdue=[f for f in fu['items'] if f['status']=='scheduled' and f['due_at'] and f['due_at'][:10]<now[:10]]
        latest=logs[0] if logs else None
        return {'patient_id':pid,'profile':detail['profile'],'baseline':detail['baseline'],
                'logged_today':logged_today,'streak_days':streak,'recent_logs':logs[:7],'recent_adherence':adh[:7],
                'care_plan':plan['plan'],'follow_ups':upcoming,'overdue_follow_ups':overdue,
                'documents_count':len(docs),'documents_recent':docs[:3],'summary_lines':self.patient_home_summary_lines(user,pid),
                'latest_review':{'reviewed':bool(latest and latest['reviewed_at']),'reviewed_by':(latest or {}).get('reviewed_by'),'reviewed_at':(latest or {}).get('reviewed_at')} if latest else {'reviewed':False},
                'note':'Everything here is synthetic demo data shared with the assigned doctor. For emergencies, follow your real clinician-given action plan — this app never overrides it.'}
    # ---------- risk visibility (doctor-only; raw model outputs, honestly labelled) ----------
    RISK_DISCLAIMER=('Experimental synthetic-data model estimate. Not clinically validated. '
                     'Not intended for diagnosis, triage, or treatment decisions.')
    def _record_prediction_row(self,c,s):
        """Persist current twin-state predictions once per (state,horizon,model). Never repeats, never rewrites."""
        supported=bool(s['prediction_supported'])
        for h,raw in s['risks'].items():
            c.execute('''INSERT OR IGNORE INTO prediction_history
                (patient_id,horizon,model_version,risk,state_version,input_timestamp,recorded_at,data_status,provenance)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                (s['patient_id'],int(h),s['model_version'],float(raw),s['version'],s['timestamp'],stamp(),
                 'supported' if supported else 'outside_evaluated',
                 json.dumps({'pipeline':'frozen LightGBM replay inference','cohort':'120 synthetic patients','calibration':'none — raw model score','recorded_via':'doctor risk view'})))
    def risk_snapshot(self,user,pid):
        self.require_doctor(user);self.require_assigned(user,pid)
        if pid in self.engine.profiles:
            s=self.engine.patient(pid)
            with self.store.connect() as c:self._record_prediction_row(c,s)
            with self.store.connect() as c:
                latest_review=c.execute('SELECT status,updated_at FROM care_reviews WHERE patient_id=? ORDER BY updated_at DESC LIMIT 1',(pid,)).fetchone()
                latest_edit=c.execute('SELECT MAX(updated_at) AS t FROM daily_logs WHERE patient_id=?',(pid,)).fetchone()['t']
            horizons={str(h):{'risk':s['risks'][str(h)],'label':'raw 0–1 score ×100'} for h in (24,48,72)}
            return {'patient_id':pid,'available':s['prediction_supported'],'source':'frozen replay inference (pg-synthetic-v1)',
                    'horizons':horizons,'risk_category':s['risk_category'],'model_version':s['model_version'],
                    'predicted_at':s['timestamp'],'state_version':s['version'],
                    'input_window':'hourly twin state at '+s['timestamp'],
                    'data_completeness':('outside evaluated cohort (episode or incomplete follow-up)' if not s['prediction_supported'] else ('supported; note: '+', '.join(s['missing_fields'])+' imputed' if s['missing_fields'] else 'supported')),
                    'missing_fields':s['missing_fields'],'warnings':s['warnings'],
                    'freshness':{'state_timestamp':s['timestamp'],'latest_patient_record_update':latest_edit},
                    'review_status':(dict(latest_review) if latest_review else {'status':'none','updated_at':None}),
                    'calibration':'none (raw LightGBM score — do not describe as calibrated probability)',
                    'disclaimer':self.RISK_DISCLAIMER,
                    'note':'Risk outputs are model-side estimates on synthetic data; a low score never implies safety.'}
        # registered demo patient without replay: honest unavailability
        detail=self.services.registry.detail(pid)
        return {'patient_id':pid,'available':False,'source':'frozen replay inference (pg-synthetic-v1)','horizons':None,
                'risk_category':'unavailable','model_version':'pg-synthetic-v1','predicted_at':None,'state_version':None,
                'input_window':None,'data_completeness':f"72h baseline {detail['baseline']['observed_hours']:.0f}/72h — predictions unavailable until the baseline and feature frame exist",
                'missing_fields':[],'warnings':['No frozen-model prediction: baseline not complete.'],
                'freshness':{'state_timestamp':None,'latest_patient_record_update':detail['baseline'].get('last_observed_at')},
                'review_status':{'status':'none','updated_at':None},
                'calibration':'n/a — no prediction','disclaimer':self.RISK_DISCLAIMER,
                'note':'Predictions are honestly unavailable for this demo registration; nothing is fabricated.'}
    def risk_history(self,user,pid,horizon=None,limit=200):
        self.require_doctor(user);self.require_assigned(user,pid)
        sql='SELECT id,horizon,model_version,risk,state_version,input_timestamp,recorded_at,data_status,provenance FROM prediction_history WHERE patient_id=?'
        args=[pid]
        if horizon:sql+=' AND horizon=?';args.append(int(horizon))
        sql+=' ORDER BY datetime(input_timestamp) DESC, id DESC LIMIT ?';args.append(limit)
        with self.store.connect() as c:rows=[dict(r) for r in c.execute(sql,args)]
        return {'items':rows,'count':len(rows),
                'note':'Timestamped captures of raw model outputs from the frozen pipeline. Identical predictions are never re-recorded; model versions are never mixed — each row names its version.',
                'disclaimer':self.RISK_DISCLAIMER}
    def risk_overview(self,user):
        self.require_doctor(user)
        ids=self.assigned_ids(user)
        full=self.engine.cohort();cohort={p['patient_id']:p for p in full['patients'] if p['patient_id'] in ids}
        rows=[]
        with self.store.connect() as c:
            reviews={r['patient_id']:r['status'] for r in c.execute('SELECT patient_id,status FROM care_reviews WHERE id IN (SELECT MAX(id) FROM care_reviews GROUP BY patient_id)')}
            last_log={r['patient_id']:r['t'] for r in c.execute('SELECT patient_id,MAX(updated_at) AS t FROM daily_logs GROUP BY patient_id')}
            for pid in ids:
                if pid in cohort:
                    p=cohort[pid]
                    rows.append({'patient_id':pid,'display_name':p.get('display_name'),'city':p.get('city'),
                                 'risk24':p['risks']['24'],'risk48':p['risks']['48'],'risk72':p['risks']['72'],
                                 'risk_category':p['risk_category'],'prediction_supported':p['prediction_supported'],
                                 'predicted_at':p['timestamp'],'model_version':full['model_version'],'origin':'historical_twin',
                                 'review_status':reviews.get(pid,'none'),'latest_patient_record_update':last_log.get(pid)})
                else:
                    try:detail=self.services.registry.detail(pid);name=detail['profile'].get('display_name');city=detail['profile'].get('city')
                    except Exception:name=None;city=None
                    rows.append({'patient_id':pid,'display_name':name,'city':city,'risk24':None,'risk48':None,'risk72':None,
                                 'risk_category':'unavailable','prediction_supported':False,'predicted_at':None,'model_version':'pg-synthetic-v1',
                                 'origin':'manual_demo_registration','review_status':reviews.get(pid,'none'),'latest_patient_record_update':last_log.get(pid)})
        rows.sort(key=lambda r:(r['risk72'] is None,-(r['risk72'] or 0)))
        return {'items':rows,'assigned':len(ids),'disclaimer':self.RISK_DISCLAIMER,
                'note':'Raw replay-model scores on synthetic data. Percentages = score ×100. Never drive treatment automatically.'}
    def risk_explanation(self,user,pid,horizon=72):
        self.require_doctor(user);self.require_assigned(user,pid)
        if pid not in self.engine.profiles:
            return {'patient_id':pid,'horizon':horizon,'available':False,'drivers':[],'method':None,
                    'note':'Explanation unavailable: this demo registration has no frozen-model prediction.'}
        e=self.engine.explain(pid,horizon)
        return {'patient_id':pid,'horizon':horizon,'available':bool(e.get('drivers')),
                'drivers':e['drivers'][:12],'method':e.get('method','TreeSHAP (raw contributions, uncalibrated)'),
                'probability':e.get('probability'),'risk_change':e.get('risk_change'),
                'model_version':'pg-synthetic-v1','relative_deviations':e.get('relative_deviations'),
                'caution':'Feature contributions are model-side associations for this synthetic cohort — correlation, not causation. Raw TreeSHAP weights are not calibrated outputs.'}
    # ---------- patient health insights ----------
    def patient_insights(self,user,start,end):
        pid=self.own_pid(user)
        import re as _re
        for v in (start,end):
            if not _re.compile(r'^\d{4}-\d{2}-\d{2}$').match(v or ''):raise HTTPException(422,'Dates must be YYYY-MM-DD.')
        if start>end:raise HTTPException(422,'Start date must not be after end date.')
        if (datetime.fromisoformat(end)-datetime.fromisoformat(start)).days>400:raise HTTPException(422,'Range limited to 400 days for the demo.')
        with self.store.connect() as c:
            logs=[dict(r) for r in c.execute('SELECT * FROM daily_logs WHERE patient_id=? AND entry_date>=? AND entry_date<=? ORDER BY entry_date',(pid,start,end))]
            sputum=[dict(r) for r in c.execute("SELECT occurred_at,colour,volume,consistency,cough,breathlessness FROM sputum_entries WHERE patient_id=? AND substr(occurred_at,1,10)>=? AND substr(occurred_at,1,10)<=? ORDER BY occurred_at",(pid,start,end))]
            adh=[dict(r) for r in c.execute('''SELECT a.taken_at,a.as_prescribed,a.missed_reason,m.name AS medication_name FROM med_adherence a JOIN plan_medications m ON m.id=a.medication_id
                 WHERE a.patient_id=? AND substr(a.taken_at,1,10)>=? AND substr(a.taken_at,1,10)<=? ORDER BY a.taken_at''',(pid,start,end))]
            vitals=[dict(r) for r in c.execute('''SELECT hour,timestamp,json_extract(state,'$.current.resp_rate') AS resp_rate,
                 json_extract(state,'$.current.symptom_score') AS symptom_score, json_extract(state,'$.current.steps') AS replay_steps,
                 json_extract(state,'$.current.sleep_hours') AS replay_sleep
                 FROM states WHERE patient_id=? AND substr(timestamp,1,10)>=? AND substr(timestamp,1,10)<=? ORDER BY hour''',(pid,start,end))]
            rw=dict(c.execute("SELECT MIN(substr(timestamp,1,10)) AS first, MAX(substr(timestamp,1,10)) AS last FROM states WHERE patient_id=?",(pid,)).fetchone() or {})
        # daily aggregation of replay vitals (honest synthetic source)
        vit_days: dict={}
        for r in vitals:
            d=r['timestamp'][:10];b=vit_days.setdefault(d,{'date':d,'resp_values':[],'symptom_values':[],'steps':[]})
            if r['resp_rate'] is not None:b['resp_values'].append(r['resp_rate'])
            if r['symptom_score'] is not None:b['symptom_values'].append(r['symptom_score'])
            if r['replay_steps'] is not None:b['steps'].append(r['replay_steps'])
        breathing=[{'date':d,'mean':sum(v['resp_values'])/len(v['resp_values']),'min':min(v['resp_values']),'max':max(v['resp_values']),'samples':len(v['resp_values'])}
                   for d,v in sorted(vit_days.items()) if v['resp_values']]
        replay_symptoms=[{'date':d,'mean':sum(v['symptom_values'])/len(v['symptom_values']),'samples':len(v['symptom_values'])} for d,v in sorted(vit_days.items()) if v['symptom_values']]
        logs_by_day={l['entry_date']:l for l in logs}
        days=[(datetime.fromisoformat(start)+timedelta(days=i)).date().isoformat() for i in range((datetime.fromisoformat(end)-datetime.fromisoformat(start)).days+1)]
        def bounded(fn):
            out=[]
            for d in days:
                l=logs_by_day.get(d)
                row={'date':d}
                if l:
                    row.update(fn(l))
                out.append(row)
            return out
        sleep=bounded(lambda l:{'value':l['sleep_hours'],'quality':l['sleep_quality']})
        activity=bounded(lambda l:{'value':l['activity_minutes']})
        hydration=bounded(lambda l:{'value':l['water_ml']})
        wellbeing={'better':2,'same':1,'worse':0}
        wellbeing_series=bounded(lambda l:({'value':wellbeing.get(l['wellbeing']),'label':l['wellbeing']} if l['wellbeing'] else {}))
        sputum_series=[{'date':s['occurred_at'][:10], 'cough':s['cough'],'breathlessness':s['breathlessness'],'colour':s['colour'],'volume':s['volume']} for s in sputum]
        adh_series=[{'date':a['taken_at'][:10],'taken':bool(a['as_prescribed']),'name':a['medication_name'],'missed_reason':a['missed_reason']} for a in adh]
        # ---- summaries: only statements supported by real records ----
        summary=[]
        span_days=len(days);logged_days=len(logs)
        summary.append(f'You recorded daily wellbeing on {logged_days} of the {span_days} day(s) in this range.')
        taken=sum(1 for a in adh if a['as_prescribed']);missed=len(adh)-taken
        if adh:summary.append(f'Medication reports this range: {taken} taken as documented, {missed} marked missed.')
        sleeps=[l['sleep_hours'] for l in logs if l['sleep_hours'] is not None]
        if len(sleeps)>=2:summary.append(f'Recorded sleep averaged {sum(sleeps)/len(sleeps):.1f} h/night across {len(sleeps)} logged days.')
        waters=[l['water_ml'] for l in logs if l['water_ml'] is not None]
        if waters:summary.append(f'Recorded hydration averaged {sum(waters)/len(waters):.0f} ml/day across {len(waters)} logged days.')
        if sputum_series:summary.append(f'Sputum diary entries this range: {len(sputum_series)} (highest recorded cough {max(s["cough"] for s in sputum_series)}/10, breathlessness {max(s["breathlessness"] for s in sputum_series)}/10).')
        if breathing:summary.append(f'Simulated replay vitals available for {len(breathing)} day(s) (synthetic 60-day replay, not wearable telemetry).')
        return {'range':{'start':start,'end':end,'days':span_days},'summary':summary,
                'daily_logs':logs,'sputum_entries':sputum_series,'adherence':adh_series,
                'sleep':sleep,'activity':activity,'hydration':hydration,'wellbeing':wellbeing_series,
                'breathing_rate':breathing,'replay_symptom_score':replay_symptoms,
                'units':{'water_ml':'ml','activity_minutes':'minutes','sleep_hours':'hours','resp_rate':'breaths/min','symptom_score':'0–10'},
                'sources':{'daily_logs':'patient-reported demo entries','sputum':'patient/self-reported fictional diary',
                           'medication':'patient-reported adherence against clinician-documented demo list',
                           'breathing_rate':'frozen synthetic replay dataset (hourly simulated vitals) — not wearable data',
                           'replay_symptom_score':'frozen synthetic replay dataset'},
                'replay_window':{'first':rw.get('first'),'last':rw.get('last'),
                                 'note':'Frozen synthetic replay timestamps; outside this window no replay vitals exist.'},
                'note':'Graphs show only real records. Missing dates remain missing; nothing is invented to fill gaps.'}
    def patient_home_summary_lines(self,user,pid):
        """Small evidence-based lines for Patient Home (last 14 days window)."""
        end=stamp()[:10];start=(utcnow()-timedelta(days=13)).date().isoformat()
        with self.store.connect() as c:
            logged=c.execute('SELECT COUNT(*) AS n FROM daily_logs WHERE patient_id=? AND entry_date>=?',(pid,start)).fetchone()['n']
            adh=dict(c.execute('SELECT SUM(as_prescribed) AS taken,COUNT(*) AS total FROM med_adherence WHERE patient_id=? AND substr(taken_at,1,10)>=?',(pid,start)).fetchone() or {})
            latest_reviewed=c.execute('SELECT entry_date,reviewed_by FROM daily_logs WHERE patient_id=? AND reviewed_at IS NOT NULL ORDER BY reviewed_at DESC LIMIT 1',(pid,)).fetchone()
        lines=[f'You logged your wellbeing on {logged} of the last 14 days.']
        if adh.get('total'):lines.append(f"Medication reports in the last 14 days: {adh['taken']} of {adh['total']} taken as documented.")
        if latest_reviewed:lines.append(f"Last doctor review: {latest_reviewed['entry_date']} entry, by {latest_reviewed['reviewed_by']}.")
        return lines
