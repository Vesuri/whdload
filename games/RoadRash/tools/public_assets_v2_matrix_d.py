import os,sys,subprocess,json
from pathlib import Path
from matrix_a import config,CELLS,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');out=root/'tmp/d-public-assets-v2-matrix';out.mkdir();rows=[]
for cell in [c for c in CELLS if not c.endswith('-mmu')]:
 env=config(cell);env.update(SLAVE=str(root/'tmp/d-public-assets-v2-build/RoadRash.slave'),DEBUG_PORT='27582');env['WHD_ARGS']+=' CUSTOM2=1'
 dest=out/cell;dest.mkdir()
 try:
  with (dest/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(dest),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(dest)
 row=dict(cell=cell,returncode=p.returncode)
 if (dest/'result.json').exists():r=json.loads((dest/'result.json').read_text());row.update(fps=r['fps'],distance=r['distance490'])
 rows.append(row);(out/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n');print(row,flush=True)
 assert not p.returncode
