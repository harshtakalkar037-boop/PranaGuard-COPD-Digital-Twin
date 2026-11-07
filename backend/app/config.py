from pathlib import Path
import os
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
DATA = ROOT / 'data'
ARTIFACTS = ROOT / 'artifacts'
DB_PATH = Path(os.getenv('PRANAGUARD_DB', str(DATA / 'pranaguard.sqlite')))
HORIZONS = (24, 48, 72)
MODEL_VERSION = 'pg-synthetic-v1'
