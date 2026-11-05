import os,sys,subprocess
from pathlib import Path
from matrix_a import config
root=Path.cwd()
for i,cell in enumerate(['a1200-fast','a1200-fast+nocache']):
 env=config(cell);env.update(SLAVE=str(root/'tmp/c-approved-lane-motion-build/RoadRash.slave'),DEBUG_PORT=str(27247+i));env['WHD_ARGS']+=' CUSTOM2=1'
 subprocess.run([sys.executable,'tools/simulation_wait_window_c.py','tmp/c-approved-motion-wait-'+cell],env=env,check=True)
