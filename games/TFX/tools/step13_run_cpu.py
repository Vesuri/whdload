"""Run one CPU's matrix and startup checks serially in its own runtime."""
import os,sys,subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];cpu=sys.argv[1];out=root/'tmp/step13'
e=dict(os.environ,STEP13_CPUS=cpu,STEP13_WORKER_ROOT=str(out/'workers'/cpu),DEBUG_PORT=str({'040':2462,'020':2463,'030':2465,'060':2466}[cpu]),FSUAE=str(root/'tmp/step9-emulator/fs-uae/fs-uae'))
steps=[('step13_matrix.py',out/('candidate-'+cpu),'candidate'),('step13_startup.py',out/('startup-'+cpu))]
if cpu=='020':steps.append(('step13_no_fpu.py',out/'no-fpu'))
status={}
for tool,*args in steps:
 r=subprocess.run([sys.executable,str(root/'tools'/tool),*map(str,args)],env=e)
 status[tool]=r.returncode;(out/(cpu+'-run-status.json')).write_text(json.dumps(status,indent=2))
 if r.returncode:sys.exit(r.returncode)
