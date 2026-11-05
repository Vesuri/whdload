import os,sys,subprocess,json,concurrent.futures,hashlib,gzip,shutil
from pathlib import Path
root=Path.cwd(); profiles={'a500':6,'a500-fast':6,'a1200-020':6,'a1200-030-50':0,'a4000-040-25':2,'a4000-040-40':2,'a4000-060-50':2}
def run(job):
 profile,window=job;name='s6f-'+profile+'-'+window.lower();instance='s6m'+hashlib.sha256(name.encode()).hexdigest()[:7];out=root/'tmp/prof'/name
 env=dict(os.environ,INSTANCE=instance,SWAP_ONLY='1')
 if not out.exists():
  log=root/'tmp'/(name+'.log')
  with log.open('w') as f:subprocess.run([sys.executable,'tools/capture_render_window.py',name,'--slave','s6f-'+window.lower()+'.slave','--profile',profile,'--render',str(profiles[profile]),'--window',window.upper() if window!='attract' else window],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 subprocess.run([sys.executable,'tools/check_render_patches.py',str(out)],env=env,check=True)
 result=json.loads((out/'render-result.json').read_text()); row=dict(profile=profile,window=window,swaps=result['swaps'],fields=result['fields'],render=profiles[profile])
 for f in out.glob('*.bin'):
  data=f.read_bytes();z=f.with_suffix(f.suffix+'.gz')
  with gzip.open(z,'wb',compresslevel=1) as g:g.write(data)
  with gzip.open(z,'rb') as g:assert hashlib.sha256(g.read()).digest()==hashlib.sha256(data).digest()
  f.unlink()
 runtime=root/'tmp/run'/instance/'.run'
 if runtime.exists():
  for f in runtime.glob('*.pid'):
   try:os.kill(int(f.read_text()),0)
   except ProcessLookupError:pass
   else:raise RuntimeError('Runtime still live')
  shutil.rmtree(runtime)
 print(row,flush=True);return row
jobs=[(p,w) for p in profiles for w in ['a','b','attract']]
# First A500 capture was already collected; re-use it after the same patch audit.
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,jobs))
(root/'tmp/s6-final-matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
