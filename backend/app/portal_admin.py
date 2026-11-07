"""Local administrator-only account provisioning. Never exposed as an HTTP API."""
import argparse
import getpass
import json
import re
import secrets
from backend.app.config import DB_PATH, DATA
from backend.app.portal import hash_password, timestamp, temporary_password_expiration, login_identifier
from backend.app.store import Store

def main():
    parser=argparse.ArgumentParser(description='PranaGuard local portal administration')
    sub=parser.add_subparsers(dest='command',required=True)
    doc=sub.add_parser('create-doctor');doc.add_argument('username')
    link=sub.add_parser('link');link.add_argument('patient_username');link.add_argument('patient_id');link.add_argument('doctor_username')
    assign=sub.add_parser('assign-synthetic');assign.add_argument('patient_id');assign.add_argument('doctor_username')
    reset=sub.add_parser('reset-password');reset.add_argument('username')
    cohort=sub.add_parser('assign-cohort');cohort.add_argument('doctor_username')
    args=parser.parse_args();store=Store(DB_PATH)
    with store.connect() as c:
        if args.command=='create-doctor':
            if not re.fullmatch(r'[a-zA-Z0-9_.@-]{3,80}',args.username): parser.error('Invalid username')
            password=getpass.getpass('Doctor password (at least 12 characters): ')
            if len(password)<12 or len(password)>128 or password!=getpass.getpass('Confirm password: '): parser.error('Invalid or mismatched password')
            c.execute('INSERT INTO portal_users(username,password_hash,role,created_at) VALUES (?,?,?,?)',(args.username,hash_password(password),'doctor',timestamp()))
            c.execute("INSERT INTO portal_admin_audit(action,username,created_at) VALUES ('create_doctor',?,?)",(args.username,timestamp()))
            print('Doctor created.')
        elif args.command=='assign-cohort':
            doctor=c.execute("SELECT id FROM portal_users WHERE username=? AND role='doctor'",(args.doctor_username,)).fetchone()
            if not doctor: parser.error('Doctor account not found')
            profiles=json.loads((DATA/'patients.json').read_text())
            ids=[p['patient_id'] for p in profiles if p.get('synthetic') is True]
            if not ids or len(ids)!=len(profiles) or len(set(ids))!=len(ids): parser.error('Original cohort is not entirely synthetic or has duplicate IDs')
            for pid in ids:
                record=c.execute('SELECT profile FROM patients WHERE patient_id=?',(pid,)).fetchone()
                if not record or json.loads(record['profile']).get('synthetic') is not True: parser.error('Existing database cohort does not match the synthetic source')
            for pid in ids:
                c.execute('INSERT OR IGNORE INTO doctor_patient_assignments(doctor_id,patient_id) VALUES (?,?)',(doctor['id'],pid))
            c.execute("INSERT INTO portal_admin_audit(action,username,created_at) VALUES ('assign_synthetic_cohort',?,?)",(args.doctor_username,timestamp()))
            print(f'Assigned {len(ids)} existing synthetic cohort records; no patient account or record changed.')
        elif args.command=='reset-password':
            user=c.execute('SELECT id FROM portal_users WHERE username=?',(args.username,)).fetchone()
            if not user: parser.error('Account not found')
            password=secrets.token_urlsafe(24)
            c.execute('UPDATE portal_users SET password_hash=?,must_change_password=1,temporary_password_expires_at=?,temporary_password_used_at=NULL WHERE id=?',(hash_password(password),temporary_password_expiration(),user['id']))
            c.execute('DELETE FROM portal_sessions WHERE user_id=?',(user['id'],))
            c.execute('DELETE FROM portal_login_failures WHERE username_hash=?',(login_identifier(args.username),))
            c.execute("INSERT INTO portal_admin_audit(action,username,created_at) VALUES ('password_reset',?,?)",(args.username,timestamp()))
            print('One-time temporary password (deliver securely):',password)
        else:
            doctor=c.execute("SELECT id FROM portal_users WHERE username=? AND role='doctor'",(args.doctor_username,)).fetchone()
            record=c.execute('SELECT profile FROM patients WHERE patient_id=?',(args.patient_id,)).fetchone()
            if not doctor or not record: parser.error('Doctor account or existing patient record not found')
            if json.loads(record['profile']).get('synthetic') is not True: parser.error('Only synthetic records may be assigned or linked through this command')
            if args.command=='assign-synthetic':
                c.execute('INSERT OR IGNORE INTO doctor_patient_assignments(doctor_id,patient_id) VALUES (?,?)',(doctor['id'],args.patient_id))
                c.execute("INSERT INTO portal_admin_audit(action,username,patient_id,created_at) VALUES ('assign_synthetic',?,?,?)",(args.doctor_username,args.patient_id,timestamp()))
                print('Existing synthetic record assigned. No patient account was created.')
            else:
                patient=c.execute("SELECT id FROM portal_users WHERE username=? AND role='patient'",(args.patient_username,)).fetchone()
                if not patient: parser.error('Patient account not found')
                c.execute('INSERT INTO patient_user_links(user_id,patient_id) VALUES (?,?)',(patient['id'],args.patient_id))
                c.execute('INSERT OR IGNORE INTO doctor_patient_assignments(doctor_id,patient_id) VALUES (?,?)',(doctor['id'],args.patient_id))
                c.execute("INSERT INTO portal_admin_audit(action,username,patient_id,created_at) VALUES ('link_patient',?,?,?)",(args.patient_username,args.patient_id,timestamp()))
                print('Record linked and doctor assigned. No patient data was created or reset.')
if __name__=='__main__':main()
