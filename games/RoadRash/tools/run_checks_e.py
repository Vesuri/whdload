import os,sys,subprocess,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');out=Path(sys.argv[1]);out.mkdir();rows=[]
for cell in sys.argv[3:]:
 env=config(cell);env.update(SLAVE=str(Path(sys.argv[2]).resolve()),DEBUG_PORT=os.environ.get('E_PORT','27750'),WHD_ARGS=env['WHD_ARGS']+' CUSTOM2=1');dest=out/cell;dest.mkdir()
 try:
  with (dest/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/invoke_e.py','tools/check_a.py',str(dest),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(dest)
 row=dict(cell=cell,returncode=p.returncode)
 if (dest/'result.json').exists():r=json.loads((dest/'result.json').read_text());row.update(fps=r['fps'],distance=r['distance490'])
 rows.append(row);(out/'matrix.json').write_text(json.dumps(rows,indent=2));print(row,flush=True)
 assert not p.returncode
