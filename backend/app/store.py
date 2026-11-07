"""SQLite persistence, atomic replay transactions and immutable twin-state versions."""
import hashlib, json, sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS patients(patient_id TEXT PRIMARY KEY, profile TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS states(patient_id TEXT NOT NULL, version INTEGER NOT NULL, hour INTEGER NOT NULL, timestamp TEXT NOT NULL, state TEXT NOT NULL, PRIMARY KEY(patient_id,version), FOREIGN KEY(patient_id) REFERENCES patients(patient_id));
            CREATE INDEX IF NOT EXISTS state_hour ON states(patient_id,hour);
            CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL, state_version INTEGER NOT NULL, created_at TEXT NOT NULL, risk REAL NOT NULL, horizon INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'new', note TEXT NOT NULL DEFAULT '', updated_at TEXT, FOREIGN KEY(patient_id) REFERENCES patients(patient_id));
            CREATE TABLE IF NOT EXISTS interventions(id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL, kind TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL, state_version INTEGER NOT NULL, FOREIGN KEY(patient_id) REFERENCES patients(patient_id));
            CREATE TABLE IF NOT EXISTS scenarios(id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL, state_version INTEGER NOT NULL, created_at TEXT NOT NULL, assumptions TEXT NOT NULL, result TEXT NOT NULL, FOREIGN KEY(patient_id) REFERENCES patients(patient_id));
            ''')
        self.apply_migrations()

    def apply_migrations(self):
        """Versioned, additive migrations; fail rather than silently rewriting applied SQL."""
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,sha256 TEXT NOT NULL,applied_at TEXT NOT NULL)')
        for path in sorted((Path(__file__).parent/'migrations').glob('*.sql')):
            version=int(path.name.split('_',1)[0]);sql=path.read_text();digest=hashlib.sha256(sql.encode()).hexdigest()
            with self.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                old=c.execute('SELECT sha256 FROM schema_migrations WHERE version=?',(version,)).fetchone()
                if old:
                    if old['sha256']!=digest:raise RuntimeError(f'Applied migration checksum mismatch: {path.name}')
                    continue
                # Each checked-in statement is trusted DDL. Execute within this transaction.
                for statement in sql.split(';'):
                    if statement.strip():c.execute(statement)
                c.execute('INSERT INTO schema_migrations VALUES (?,?,?,?)',(version,path.name,digest,datetime.now(timezone.utc).isoformat()))

    @contextmanager
    def connect(self):
        conn=sqlite3.connect(self.path,timeout=30);conn.row_factory=sqlite3.Row;conn.execute('PRAGMA foreign_keys=ON')
        try:
            yield conn;conn.commit()
        except BaseException:
            conn.rollback();raise
        finally:conn.close()

    def meta(self,key,default=None):
        with self.connect() as c:
            row=c.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
            return json.loads(row['value']) if row else default

    def set_meta(self,key,value):
        with self.connect() as c:c.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(key,json.dumps(value)))

    def latest(self,pid,version=None):
        with self.connect() as c:
            row=c.execute('SELECT state FROM states WHERE patient_id=? '+('ORDER BY version DESC LIMIT 1' if version is None else 'AND version=?'),(pid,) if version is None else (pid,version)).fetchone()
            if not row:raise KeyError('Patient or version not found')
            return json.loads(row['state'])

    def versions(self,pid,limit=72):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT version,hour,timestamp FROM states WHERE patient_id=? ORDER BY version DESC LIMIT ?',(pid,limit))]

    def history(self,pid,limit=72):
        with self.connect() as c:
            rows=c.execute('SELECT state FROM states WHERE patient_id=? ORDER BY version DESC LIMIT ?',(pid,limit)).fetchall()
            return [json.loads(r['state']) for r in rows][::-1]

    def alerts(self,pid=None,pids=None,doctor_id=None):
        with self.connect() as c:
            query='SELECT a.*,p.profile FROM alerts a JOIN patients p USING(patient_id)'
            args=[];filters=[]
            if pid is not None and pids is not None:raise ValueError('Choose one patient filter')
            if pids is not None:
                ids=tuple(pids)
                if not ids:return []
                filters.append('a.patient_id IN ('+','.join('?' for _ in ids)+')');args.extend(ids)
            elif pid:
                if doctor_id is not None and not c.execute("SELECT 1 FROM patients p JOIN doctor_patient_assignments d ON d.patient_id=p.patient_id WHERE d.doctor_id=? AND p.patient_id=? AND json_type(p.profile,'$.synthetic')='true'",(doctor_id,pid)).fetchone():
                    raise KeyError('Record not found')
                filters.append('a.patient_id=?');args.append(pid)
            if doctor_id is not None:
                filters.append("json_type(p.profile,'$.synthetic')='true' AND EXISTS (SELECT 1 FROM doctor_patient_assignments d WHERE d.doctor_id=? AND d.patient_id=a.patient_id)")
                args.append(doctor_id)
            if filters:query+=' WHERE '+' AND '.join(filters)
            rows=c.execute(query+' ORDER BY a.id DESC LIMIT 500',args).fetchall()
            result=[]
            for row in rows:
                d=dict(row);d['display_name']=json.loads(d.pop('profile'))['display_name'];d['synthetic']=True;result.append(d)
            return result

    def interventions(self,pid=None):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM interventions'+(' WHERE patient_id=?' if pid else '')+' ORDER BY id DESC LIMIT 300',(pid,) if pid else ())]
