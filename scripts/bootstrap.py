"""Offline demo DB initialization, using bundled executed model and cached synthetic cohort."""
import argparse
from backend.app.config import DB_PATH
from backend.app.engine import TwinEngine

def bootstrap(reset=False):
    existed=DB_PATH.exists();e=TwinEngine(DB_PATH)
    if reset or not existed:
        target=e.demo['start_hour'];e.reset(target-24);e.step(24)
    print('SQLite initialized:',DB_PATH)
    print('Replay:',e.replay_status());print('Cohort:',e.cohort()['summary'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reset',action='store_true');a=p.parse_args();bootstrap(a.reset)
