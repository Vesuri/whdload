#!/usr/bin/env python3
"""Same-period named-state regression against completed Phase 6 captures."""
import os,subprocess,json
from pathlib import Path
os.chdir(Path(__file__).resolve().parents[1])
for name,ref,exact in [('a500','core-a500-p6',True),('020','matrix-v5-p2',True),('030','core-030-p2',True),('traffic','matrix-v5-traffic-p2',False)]:
 old=Path('tmp/phase6')/ref;m=json.loads((old/'metadata.json').read_text());out=Path('tmp/phase7/accepted-core-'+name);out.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,**{k:v for k,v in m['options'].items() if v is not None});env.pop('BOOT_HUNK',None);env.update(PHASE3_FIELDS='720',SKIP_FIELDS='0',LATCH_AUDIT='1')
 print('START',name,flush=True)
 with (out/'run.log').open('w') as log:subprocess.run(['bash','tools/fixed_window.sh',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 with (out/'acceptance.log').open('w') as log:
  for args in [['tools/phase6_units.py',str(out),str(out/'slave.slave.lst')],['tools/check_phase6.py',str(out)],['tools/phase7_tables.py',str(out)]]:
   subprocess.run(['python3',*args],stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['python3','tools/phase6_compare.py',str(old),str(out),'--output',str(out/'phase6-regression.json'),*(['--assert-core'] if exact else [])],stdout=log,stderr=subprocess.STDOUT,check=True)
 latches=json.loads((out/'state/latches.json').read_text());assert len(latches)>10
 intervals=[b[0]-a[0] for a,b in zip(latches,latches[1:])];steps=[b[1]-a[1] for a,b in zip(latches,latches[1:])]
 assert min(steps)>=1,(name,steps)
 (out/'cadence.json').write_text(json.dumps(dict(render_latches=len(latches),field_intervals=sorted(set(intervals)),physics_updates_per_draw=sorted(set(steps))),indent=2)+'\n')
 print('PASS',name,flush=True)
