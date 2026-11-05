"""One profile's rendering A/B matrix, compacting completed captures immediately."""
import sys,os,subprocess,json,hashlib,time
from pathlib import Path
profile=sys.argv[1];prefix=os.environ.get('S5_MATRIX_PREFIX','s5-rot-v2');root=Path.cwd();summary=[]
result_path=root/'tmp'/f'{prefix}-{profile}-matrix.json'
lock=result_path.with_suffix('.pid')
if lock.exists():
 pid=int(lock.read_text())
 while True:
  if result_path.exists() and len(json.loads(result_path.read_text()))==6:
   print('ALREADY COMPLETE',profile);sys.exit(0)
  try:os.kill(pid,0)
  except ProcessLookupError:raise RuntimeError('Previous matrix incomplete; inspect before retry')
  time.sleep(1)
lock.write_text(str(os.getpid()))
for window in os.environ.get('S5_WINDOWS','A B attract').split():
 for state in map(int,os.environ.get('S5_RENDER_STATES','0 2').split()):
  name=f'{prefix}-{profile}-{window.lower()}-{state}';instance='s5m'+hashlib.sha256(name.encode()).hexdigest()[:8];env=dict(os.environ,INSTANCE=instance)
  args=[sys.executable,'tools/capture_render_window.py',name,'--slave',os.environ.get('S5_BUILD_PREFIX','s5-rotation-v2')+f'-{window.lower()}.slave','--profile',profile,'--render',str(state),'--window',window]
  trace=profile in ['a500','a500-fast','a1200-020']
  if trace:args+=['--trace']
  subprocess.run(args,env=env,check=True)
  out=root/'tmp/prof'/name
  if trace:
   subprocess.run([sys.executable,'tools/analyse_render_trace.py',str(out)],env=env,check=True,stdout=(out/'analysis.log').open('w'))
   r=json.loads((out/'render-costs.json').read_text());swaps=r['counts']['swaps']
  else:swaps=json.loads((out/'render-result.json').read_text())['swaps']
  summary.append(dict(window=window,render=state,swaps=swaps,fps=swaps/(500*142102/7093790),capture=name))
  subprocess.run([sys.executable,'tools/compact_render_capture.py',name,instance],env=env,check=True)
  (root/'tmp'/f'{prefix}-{profile}-matrix.json').write_text(json.dumps(summary,indent=2)+'\n')
  print('RESULT',profile,summary[-1],flush=True)
