import os,sys,subprocess,json,time
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd()
os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
out=root/'tmp/performance-comparison-3.0b';out.mkdir(exist_ok=True)
rows=[]
for repeat in (1,2):
 for cell in ['a500-1m','a1200','a1200-fast','030-50','040-25']:
  for enhanced in (0,1):
   dest=out/f'{cell}-custom2-{enhanced}-r{repeat}'
   env=config(cell)
   env.update(SLAVE=str(root/'tmp/release-3.0b-visual-final/RoadRash.slave'),DEBUG_PORT='24410',WHD_ARGS=f'Cache CUSTOM2={enhanced}')
   if cell in ('030-50','040-25'):
    env['EXTRA_ARGS']+=' --uae_cpu_data_cache=true'
   if not (dest/'result.json').exists():
    dest.mkdir(exist_ok=True)
    try:
     with (dest/'run.log').open('w') as log:
      p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(dest),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    finally:cleanup(dest)
    if p.returncode:raise RuntimeError(f'{dest}: exit {p.returncode}')
   result=json.loads((dest/'result.json').read_text())
   row=dict(cell=cell,enhanced=enhanced,repeat=repeat,fps=result['fps'],frames=result['rotation_frames'],fields=result['end']['field']-result['initial']['field'],provenance=result['provenance'],state=result['end']['state_sha256'])
   rows.append(row)
   (out/'matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
   print({k:v for k,v in row.items() if k not in ('provenance','state')},flush=True)
