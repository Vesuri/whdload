import os,subprocess,sys
from pathlib import Path
from matrix_a import config,cleanup
cell=sys.argv[1];out=Path(os.environ.get('RR_LATENCY_PREFIX','tmp/c-latency')+'-'+cell)
env=config(cell);env['SLAVE']=str((Path(os.environ.get('RR_LATENCY_BUILD','tmp/c-latency-build'))/'RoadRash-verify.slave').resolve())
try:subprocess.run([sys.executable,'tools/latency_c.py',str(out)],env=env,check=True,timeout=240)
except subprocess.TimeoutExpired:cleanup(out);raise
