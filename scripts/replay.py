"""Control a running demo through the actual REST API."""
import argparse,json,os
import httpx
p=argparse.ArgumentParser();p.add_argument('command',choices=['status','reset','step','start','pause']);p.add_argument('--hours',type=int,default=1);p.add_argument('--url',default='http://127.0.0.1:8000');a=p.parse_args()
headers={'X-Demo-Token':os.getenv('PRANAGUARD_ADMIN_TOKEN','')}
url=a.url+'/api/replay'+('' if a.command=='status' else '/'+a.command)
r=httpx.get(url,headers=headers,timeout=60) if a.command=='status' else httpx.post(url,headers=headers,json={'hours':a.hours} if a.command=='step' else {'prime_hours':24} if a.command=='reset' else {},timeout=60)
r.raise_for_status();print(json.dumps(r.json(),indent=2))
