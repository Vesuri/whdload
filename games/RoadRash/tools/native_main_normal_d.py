from pathlib import Path
import os,sys,subprocess,json
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');rows=[]
for i,(kind,cell) in enumerate([('reference','a500-1m'),('public','a500-1m'),('public','a1200-fast'),('public','060-50')]):
 out=root/f'tmp/d-native-main-normal-{kind}-{cell}';out.mkdir();env=config(cell);env.update(SLAVE=str(root/f'tmp/d-native-main-{kind}-build/RoadRash.slave'),DEBUG_PORT=str(27560+i),WHD_ARGS='CUSTOM2=1')
 if cell=='a500-1m':env['FAST_KB']='8192'
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
 finally:cleanup(out)
 print(kind,cell,p.returncode,flush=True);assert not p.returncode
 r=json.loads((out/'result.json').read_text());rows.append(dict(kind=kind,cell=cell,fps=r['fps'],distance=r['distance490']))
print(rows,flush=True)
