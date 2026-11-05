import os,subprocess,sys
from pathlib import Path
from matrix_a import config
for q in map(int,sys.argv[2:]):
 env=config(sys.argv[1]);env['SLAVE']=str(Path(os.environ.get('RR_COST_BUILD',f'tmp/c-cost{q}-build'))/'RoadRash-verify.slave')
 subprocess.run([sys.executable,'tools/cost_c.py',f"tmp/{os.environ.get('RR_COST_PREFIX','c-cost')}-{sys.argv[1]}-q{q}"],env=env,check=True,timeout=240)
