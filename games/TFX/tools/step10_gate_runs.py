"""Additional gate audits, executed after the final serial regression run."""
import os,subprocess,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];dev=root;out=dev/'tmp/step10/final';status={}
for cpu,c4 in [('040',114),('040',118),('030',114),('060',114)]:
 name=f'gate-{cpu}-{c4}'
 r=subprocess.run([sys.executable,str(dev/'tools/audit_step10_options.py'),str(out/name),cpu,str(c4)],env=dict(os.environ,FSUAE=str(dev/'tmp/step9-emulator/fs-uae/fs-uae')),cwd=root)
 status[name]=r.returncode;(out/'gate-status.json').write_text(json.dumps(status,indent=2))
assert not any(status.values()),status
