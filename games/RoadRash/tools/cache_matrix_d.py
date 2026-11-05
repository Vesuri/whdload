import json,os,subprocess,sys
from pathlib import Path
from matrix_a import config,CELLS,cleanup
root=Path.cwd();out=root/'tmp/d-cache-matrix-validated';out.mkdir(exist_ok=True)
os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
rows=[]
checks=[(c,c,'CUSTOM2=1') for c in CELLS]+[('040-nocache','040-25','CUSTOM2=1 NoCache'),('060-nocache','060-50','CUSTOM2=1 NoCache'),('020-off','a1200-fast','CUSTOM2=0')]
for i,(name,cell,opts) in enumerate(checks):
 env=config(cell);env.update(SLAVE=str(root/'tmp/d-cache-audit-build/RoadRash-verify.slave'),DEBUG_PORT=str(27300+i));env['WHD_ARGS']+=' '+opts
 dest=out/name;dest.mkdir()
 try:
  with (dest/'run.log').open('w') as log:
   p=subprocess.run([sys.executable,'tools/cache_setup_d.py',str(dest)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  row=dict(cell=name,returncode=p.returncode)
  if (dest/'cache.json').exists():row.update(json.loads((dest/'cache.json').read_text()))
 finally:cleanup(dest)
 rows.append(row);(out/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');print(name,p.returncode,flush=True)
assert all(r['returncode']==0 for r in rows)
