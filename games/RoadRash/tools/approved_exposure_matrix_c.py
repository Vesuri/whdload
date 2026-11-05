import os,sys,json,subprocess,time
from pathlib import Path
from matrix_a import config,cleanup
root=Path(__file__).resolve().parents[1]; out=root/'tmp/c-approved-exposure-matrix';out.mkdir(exist_ok=True)
cells=['a1200-fast','a1200-fast+cache','a1200-fast+nocache','030-50','030-50+cache','040-25','040-25+cache','060-50','060-50+cache']
results=[]
for i,cell in enumerate(cells):
 for j,(kind,build,toggle) in enumerate([('b','b-provenance-build',3),('c','c-approved-lane-motion-build',1)]):
  dest=out/cell/kind
  if dest.exists():raise RuntimeError(str(dest))
  dest.mkdir(parents=True)
  os.environ['RR_WHD_EXTRA']=f'CUSTOM2={toggle}'
  env=config(cell);env.update(SLAVE=str(root/'tmp'/build/'RoadRash.slave'),DEBUG_PORT=str(27249+i*2+j))
  with (dest/'run.log').open('w') as log:
   p=subprocess.Popen([sys.executable,str(root/'tools/npc_acceleration_trace_c.py'),str(dest)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try: rc=p.wait(timeout=240)
   finally:cleanup(dest)
  results.append(dict(cell=cell,kind=kind,returncode=rc));(out/'runs.json').write_text(json.dumps(results,indent=2)+'\n');print(results[-1],flush=True)
  if rc:raise RuntimeError('trace failed')
