import sys,os,subprocess
from pathlib import Path
from matrix_a import config,cleanup
cell=sys.argv[1];out=Path(sys.argv[2]);env=config(cell);env.update(SLAVE=os.environ['SLAVE'],WHD_ARGS=env.get('WHD_ARGS','')+' CUSTOM2=1')
try:subprocess.run([sys.executable,str(Path(__file__).with_name('runtime_boundary_c.py')),str(out)],env=env,check=True,timeout=240)
except subprocess.TimeoutExpired:cleanup(out);raise
