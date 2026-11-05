import os,sys,json,subprocess
from pathlib import Path
from PIL import Image,ImageChops
from matrix_a import config,cleanup
root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=True)
kind=sys.argv[2];port=int(sys.argv[3]);results=[]
slave=Path(os.environ.get('RR_VISIBLE_SLAVE','tmp/b-final-build/RoadRash.slave' if kind=='B' else 'tmp/c-pose-project-runtime-build/RoadRash.slave')).resolve()
for tick in range(306,308):
 runs=[]
 for right in [0,1]:
  out=root/f'{tick}-{right}'
  if kind=='C' and tick==300:out=Path('tmp/c-visible-pilot-'+('right' if right else 'neutral')).resolve()
  elif kind=='candidate' and tick==300:out=Path(f'tmp/c-steering-candidate-{right}').resolve()
  else:
   out.mkdir(exist_ok=False);env=config(os.environ.get('RR_VISIBLE_CELL','a1200-fast+cache'));env.update(DEBUG_PORT=str(port),SLAVE=str(slave),WHD_ARGS='Cache CUSTOM2='+('3' if kind=='B' else '1'),RR_INJECT=str(tick),RR_RIGHT=str(right))
   with (out/'run.log').open('w') as log:
    try:subprocess.run([sys.executable,'tools/visible_latency_c.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    finally:cleanup(out)
  runs.append(out)
 a,b=[json.loads((p/'visible.json').read_text()) for p in runs]
 assert a['initial']==b['initial'],('initial mismatch',tick)
 first=None;bounds=[]
 for f in range(tick+2,tick+22):
  x,y=[Image.open(p/f'field-{f}.png').convert('RGB') for p in runs]
  diff=ImageChops.difference(x,y).crop((74,100,714,324));box=diff.getbbox()
  if box:
   bounds.append([f,box])
   if first is None:
    first=f;diff.save(root/f'difference-{tick}.png')
 assert first is not None,('no visible response',tick)
 assert first>tick+2,('already different on first captured field',tick)
 row=dict(injection=tick,first_different_capture=first,milliseconds_upper_estimate=20*(first-tick),last_equal_capture=first-1,difference_bounds=bounds,neutral=str(runs[0]),right=str(runs[1]))
 results.append(row);(root/'results.json').write_text(json.dumps(dict(kind=kind,slave=str(slave),samples=results),indent=2));print(kind,tick,first,row['milliseconds_upper_estimate'],flush=True)
