#!/usr/bin/env python3
"""Sequential, bounded guest fixtures. Capture failures stop the matrix."""
import os,subprocess,json,time,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.chdir(root)
prefix=os.environ.get('SERIES','matrix-v1')
mode=os.environ.get('MATRIX','handling')
cases=[]
if mode=='handling':
 cases=[('native',0,0,7,0),('p6',1,4,7,0),('p2',1,0,7,0),('traffic-p6',1,4,7,1),('traffic-p2',1,0,7,1)]
elif mode=='events':
 for event,name in [(1,'overheat'),(2,'crash'),(3,'spin'),(4,'pause'),(5,'neutral'),(6,'pit'),(7,'offroad')]:
  cases += [(name+'-p6',1,4,7+256*event,0),(name+'-p2',1,0,7+256*event,0)]
else:raise ValueError(mode)
for name,c2,c4,c5,c1 in cases:
 out=Path('tmp/phase6')/(prefix+'-'+name)
 env=os.environ|{'AMIGA_MODEL':'A1200','CPU':'68EC020','CHIP_KB':'2048','FAST_KB':'4096','SLOW_KB':'0','KICKSTART':str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200'),'WHD_ARGS':f'CUSTOM1={c1} CUSTOM2={c2} CUSTOM3=1 CUSTOM4={c4} CUSTOM5={c5}','SKIP_FIELDS':'0','PHASE3_FIELDS':'720' if mode=='handling' else ('1200' if name.startswith('pit') else '420')}
 if os.environ.get('CALIBRATION'):
  calibration=Path(os.environ['CALIBRATION']);m=json.loads((calibration/'metadata.json').read_text())
  assert m['slave_sha256']==hashlib.sha256(Path('tmp/build/verify/GrandPrixCircuit.Slave').read_bytes()).hexdigest()
  assert m['options']['CPU']=='68EC020' and m['options']['FAST_KB']=='4096'
  env['BOOT_HUNK']=hex(m['code_base'])
 if out.exists() and os.environ.get('RESUME')=='1':
  assert (out/'fsuae.log').exists() and (out/'state/metadata.json').exists(),out
  saved=json.loads((out/'metadata.json').read_text())
  digest=hashlib.sha256(Path('tmp/build/verify/GrandPrixCircuit.Slave').read_bytes()).hexdigest()
  assert saved['slave_sha256']==digest==hashlib.sha256((out/'slave.slave').read_bytes()).hexdigest()
  assert saved['options']['WHD_ARGS']==env['WHD_ARGS']
  counts=json.loads((out/'state/counts.json').read_text());assert len(counts)==int(env['PHASE3_FIELDS'])
  subprocess.run(['python3','tools/phase6_units.py',str(out),str(out/'slave.slave.lst')],check=True)
  print('VERIFIED existing completed capture',str(out),flush=True)
  continue
 assert not out.exists(),out
 print('START',str(out),flush=True)
 for attempt in range(3):
  try:
   subprocess.run(['bash','tools/fixed_window.sh',str(out)],env=env,check=True,timeout=600)
   break
  except subprocess.CalledProcessError:
   transcripts=[out/'state/gdb.txt',out/'dump-gdb.txt']
   if attempt==2 or not any(p.exists() and 'Invalid hex digit' in p.read_text() for p in transcripts):raise
   rejected=out.with_name(out.name+f'-transport-rejected-{attempt+1}')
   assert not rejected.exists(),rejected
   out.rename(rejected)
   print('REJECTED debugger transport; fresh boot retry:',str(rejected),flush=True)
 subprocess.run(['python3','tools/phase6_units.py',str(out),str(out/'slave.slave.lst')],env=env,check=True)
 print('DONE',str(out),flush=True)
