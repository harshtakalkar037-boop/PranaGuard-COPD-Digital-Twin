"""Seed-specific synthetic generation and memory-bounded feature extraction.
All large raw/derived data work stays outside the distributable project, in cache.
"""
import gc,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from backend.app.config import ROOT
from backend.app.model48_v3 import ALL,features_v3
CACHE=ROOT.parent/'corpus-v3'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def generate_seed(seed,patients):
    folder=CACHE/str(seed);rawfile=folder/'synthetic_longitudinal.csv.gz'
    if rawfile.exists():
        manifest=json.loads((folder/'generation_manifest.json').read_text());assert manifest['seed']==seed and manifest['patients']==patients and sha(rawfile)==manifest['sha256'];return rawfile,manifest
    folder.mkdir(parents=True,exist_ok=True)
    from scripts import generate_data as generator
    original_environment=generator.environment;original_data=generator.DATA
    def environment(city,hours,rng,offline):
        previous=generator.DATA;generator.DATA=ROOT/'data'
        try:return original_environment(city,hours,rng,offline)
        finally:generator.DATA=previous
    generator.DATA=folder;generator.environment=environment
    try:generator.generate(seed=seed,patients=patients,days=60)
    finally:generator.DATA=original_data;generator.environment=original_environment
    gc.collect();return rawfile,json.loads((folder/'generation_manifest.json').read_text())

def partition(name,spec):
    path=CACHE/(name+'-features.npz');meta_path=CACHE/(name+'-features.json');CACHE.mkdir(parents=True,exist_ok=True)
    if path.exists():return load_partition(path),json.loads(meta_path.read_text())
    arrays=[];labels=[];ids=[];hours=[];sources=[]
    for seed in spec['seeds']:
        rawfile,manifest=generate_seed(seed,spec['patients_per_seed']);sources.append({'seed':seed,'patients':manifest['patients'],'rows':manifest['rows'],'raw_sha256':manifest['sha256']})
        for raw in pd.read_csv(rawfile,chunksize=1440):
            assert raw.patient_id.nunique()==1
            raw=raw[raw.hour<=spec['hours'][1]].copy();raw['patient_id']=raw.patient_id.map(lambda pid:f'V3-{seed}-{pid}')
            frame=features_v3(raw);part=frame[frame.eligible.astype(bool)&frame.hour.between(*spec['hours'])&(frame.hour%spec['stride']==0)]
            arrays.append(part[ALL].to_numpy(dtype=np.float32));labels.append(part.label_48.to_numpy(dtype=np.int8));ids.extend(part.patient_id.tolist());hours.extend(part.hour.tolist())
    x=np.concatenate(arrays);y=np.concatenate(labels);pid=np.asarray(ids);hour=np.asarray(hours,dtype=np.int16);np.savez_compressed(path,x=x,y=y,patient_id=pid,hour=hour)
    meta={'partition':name,'sources':sources,'protocol':spec,'rows':len(y),'positive_rows':int(y.sum()),'patients':len(np.unique(pid)),'features':ALL,'feature_file_sha256':sha(path),'generator_sha256':sha(ROOT/'scripts/generate_data.py')};meta_path.write_text(json.dumps(meta,indent=2))
    return {'x':pd.DataFrame(x,columns=ALL),'y':y,'patient_id':pid,'hour':hour},meta

def load_partition(path):
    with np.load(path) as a:return {'x':pd.DataFrame(a['x'],columns=ALL),'y':a['y'],'patient_id':a['patient_id'],'hour':a['hour']}
