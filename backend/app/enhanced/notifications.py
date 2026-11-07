"""In-app demo notifications, legacy-alert bridge and append-only review history."""
import json
from contextlib import nullcontext
from fastapi import HTTPException
from backend.app.enhanced.settings import stamp

CATEGORIES=('patient_monitoring','environment','data_quality','system')
STATUSES=('active','acknowledged','under_review','resolved','closed')

class Notifications:
    def __init__(self,store):self.store=store

    def create(self,*,category,title,reason,source,source_type,dedupe_key,patient_id=None,metadata=None,legacy_alert_id=None,conn=None):
        at=stamp()
        with (nullcontext(conn) if conn is not None else self.store.connect()) as c:
            cur=c.execute('INSERT OR IGNORE INTO notifications(patient_id,category,title,reason,source,source_type,created_at,updated_at,dedupe_key,legacy_alert_id,metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (patient_id,category,title,reason,source,source_type,at,at,dedupe_key,legacy_alert_id,json.dumps(metadata or {},allow_nan=False)))
            row=c.execute('SELECT id FROM notifications WHERE dedupe_key=?',(dedupe_key,)).fetchone();nid=row['id']
            if cur.rowcount:
                c.execute('INSERT INTO notification_history(notification_id,created_at,to_status,action,note,actor) VALUES (?,?,?,?,?,?)',(nid,at,'active','created',reason,'demo_service'))
            return nid

    def sync_legacy(self):
        """Bridge persisted source alerts, never replace or silently delete them."""
        with self.store.connect() as c:
            for a in c.execute('SELECT * FROM alerts ORDER BY id').fetchall():
                nid=self.create(category='patient_monitoring',title=f"Experimental replay alert · {a['patient_id']}",
                    reason=f"Historical synthetic 72h model risk {a['risk']:.1%} crossed the demonstration threshold 0.35. Not a clinical alert; held-out sensitivity is zero at this threshold.",
                    source='Frozen LightGBM historical replay',source_type='synthetic_model',patient_id=a['patient_id'],legacy_alert_id=a['id'],
                    dedupe_key=f"legacy_alert:{a['id']}:{a['created_at']}:{a['state_version']}",
                    metadata={'risk':a['risk'],'horizon':a['horizon'],'state_version':a['state_version'],'source_valid_at':a['created_at'],'frozen_model':True},conn=c)
                old=c.execute('SELECT status FROM notifications WHERE id=?',(nid,)).fetchone()['status']
                target={'new':'active','acknowledged':'acknowledged','resolved':'resolved'}[a['status']]
                if (target=='resolved' and old not in ('resolved','closed')) or (target=='acknowledged' and old=='active'):
                    at=stamp();c.execute('UPDATE notifications SET status=?,updated_at=?,read_at=COALESCE(read_at,?) WHERE id=?',(target,at,at,nid))
                    c.execute('INSERT INTO notification_history(notification_id,created_at,from_status,to_status,action,note) VALUES (?,?,?,?,?,?)',(nid,at,old,target,'legacy_review',a['note'] or 'Source model alert reviewed in original care activity.'))

    @staticmethod
    def serialize(row):
        d=dict(row);d['metadata']=json.loads(d['metadata']);d['unread']=d['read_at'] is None;return d

    def list(self,patient_id=None,category=None,status=None,unread_only=False,limit=200):
        self.sync_legacy();where=[];args=[]
        for key,value in [('patient_id',patient_id),('category',category),('status',status)]:
            if value:where.append('n.'+key+'=?');args.append(value)
        if unread_only:where.append('n.read_at IS NULL')
        clause=(' WHERE '+' AND '.join(where)) if where else ''
        with self.store.connect() as c:
            rows=c.execute('SELECT n.* FROM notifications n'+clause+' ORDER BY n.id DESC LIMIT ?',[*args,limit]).fetchall()
            counts=dict(c.execute("SELECT SUM(CASE WHEN read_at IS NULL THEN 1 ELSE 0 END) AS unread,COUNT(*) AS total,SUM(CASE WHEN status NOT IN ('resolved','closed') THEN 1 ELSE 0 END) AS open FROM notifications").fetchone())
        return {'notifications':[self.serialize(r) for r in rows],'counts':{k:v or 0 for k,v in counts.items()},'demo_only':True,'limit':limit}

    def detail(self,nid,conn=None):
        with (nullcontext(conn) if conn is not None else self.store.connect()) as c:
            row=c.execute('SELECT * FROM notifications WHERE id=?',(nid,)).fetchone()
            if not row:raise HTTPException(404,'Notification not found.')
            result=self.serialize(row)
            result['history']=[dict(r) for r in c.execute('SELECT * FROM notification_history WHERE notification_id=? ORDER BY id',(nid,))]
        return result

    def update(self,nid,body,authorize=None):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM notifications WHERE id=?',(nid,)).fetchone()
            if not row:raise HTTPException(404,'Notification not found.')
            if authorize is not None:authorize(c,row['patient_id'])
            old=row['status'];target=body.status or old;at=stamp()
            if target!=old:
                if old=='closed' or (old=='resolved' and target!='closed') or target=='active':raise HTTPException(409,'Closed/resolved reviews cannot be reopened; use a new notification for a new event.')
                c.execute('UPDATE notifications SET status=?,updated_at=? WHERE id=?',(target,at,nid))
                if row['legacy_alert_id'] is not None:
                    legacy='resolved' if target in ('resolved','closed') else 'acknowledged'
                    c.execute('UPDATE alerts SET status=?,note=?,updated_at=? WHERE id=?',(legacy,body.note or f'Demo notification review: {target}',at,row['legacy_alert_id']))
            read_at=at if body.read is True else None if body.read is False else (at if target!=old else row['read_at'])
            if body.read is not None or target!=old:c.execute('UPDATE notifications SET read_at=? WHERE id=?',(read_at,nid))
            if target!=old or body.read is not None or body.note:
                action='review' if target!=old else 'mark_read' if body.read is True else 'mark_unread' if body.read is False else 'note'
                c.execute('INSERT INTO notification_history(notification_id,created_at,from_status,to_status,action,note) VALUES (?,?,?,?,?,?)',(nid,at,old,target,action,body.note or 'Read state updated in synthetic demo.'))
            result=self.detail(nid,conn=c)
        return result

    def test(self):
        import uuid
        nid=self.create(category='system',title='Test notification · synthetic demo',reason='User-triggered test of in-app notification persistence. No patient condition or emergency is represented.',source='Notification test control',source_type='system_demo',dedupe_key='test:'+uuid.uuid4().hex)
        return self.detail(nid)
