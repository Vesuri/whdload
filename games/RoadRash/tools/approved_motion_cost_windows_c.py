import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path(__file__).resolve().parents[1]
for i,cell in enumerate(['030-50','040-25','060-50']):
 out=root/'tmp'/('c-approved-motion-cost-window-'+cell);assert not out.exists();out.mkdir()
 os.environ['RR_WHD_EXTRA']='CUSTOM2=1';env=config(cell);env.update(SLAVE=str(root/'tmp/c-approved-lane-motion-build/RoadRash.slave'),DEBUG_PORT=str(27270+i))
 with (out/'run.log').open('w') as log:
  try:subprocess.run([sys.executable,str(root/'tools/simulation_wait_window_c.py'),str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
  finally:cleanup(out)
 print(cell,'passed',flush=True)
