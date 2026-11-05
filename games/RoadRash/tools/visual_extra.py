import os,sys,subprocess,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,(name,cell,toggle) in enumerate([('000-fast','a500-1m',1)]):
 env=config(cell);env.update(SLAVE=str(root/'tmp/visual-height-build/RoadRash.slave'),WHD_ARGS=f'CUSTOM2={toggle}',DEBUG_PORT=str(24341+i))
 if name=='000-fast':env.update(FAST_KB='8192')
 out=root/f'tmp/visual-extra-{name}';out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(out)
 print(name,p.returncode,flush=True);assert not p.returncode
