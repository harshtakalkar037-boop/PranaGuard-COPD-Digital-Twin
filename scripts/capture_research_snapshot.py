"""Capture a deterministic synthetic research snapshot in a NEW disposable database.

Run from a source tree with PYTHONPATH=. and pass a new database path and output path.
Do not point this script at a production or existing database: it advances replay
and creates a scenario. Compare snapshots from the same dependency environment.
"""
import json,sys
from pathlib import Path
if len(sys.argv)!=3 or Path(sys.argv[1]).exists() or Path(sys.argv[2]).exists() or Path(sys.argv[1]).resolve()==Path(sys.argv[2]).resolve():
    raise SystemExit("Usage: snapshot NEW_DISPOSABLE_DB NEW_OUTPUT_JSON (both paths must not exist and must differ)")
from backend.app.engine import TwinEngine
engine=TwinEngine(sys.argv[1]);ids=sorted(engine.profiles)
assert len(ids)==120 and len(engine.raw)==172800
result={'ids':ids,'raw_index':engine.ingestion_validation,'start':{pid:engine.patient(pid) for pid in ids},'cohort_start':engine.cohort(),'validation':engine.evaluation,'environment':engine.environment_manifest}
engine.step(2)
result.update(replay=engine.replay_status(),after={pid:engine.patient(pid) for pid in ids},histories={pid:engine.history(pid,48) for pid in ids},cohort_after=engine.cohort(),explanations={str(h):engine.explain(ids[0],h) for h in (24,48,72)},scenario=engine.scenario(ids[0],{'pm25_change_pct':-30,'adherence':.95,'activity_multiplier':1}))
with open(sys.argv[2],'w') as out:json.dump(result,out,sort_keys=True,allow_nan=False)
