from pathlib import Path
import subprocess,sys,json,time
r=Path(__file__).resolve().parents[1]
for arm in ['control','candidate']:
 p=r/f'tmp/step5/hi25-profile-040-40-bce-h11-v2-grid-{arm}'
 if not (p/'hi25-analysis.json').exists():
  import gzip,shutil
  for n in ['detail.bin','start.bin','start-fast.bin','canonical.bin']:
   f=p/n
   if not f.exists():
    with gzip.open(str(f)+'.gz','rb') as a,f.open('wb') as b:shutil.copyfileobj(a,b)
  subprocess.run([sys.executable,str(r/'tools/analyze_h11_trace.py'),str(p)],check=True)
a=[json.loads((r/f'tmp/step5/hi25-profile-040-40-bce-h11-v2-grid-{arm}/hi25-analysis.json').read_text())['mean_after_wait_ms'] for arm in ['control','candidate']]
print('MATCHED',a,flush=True)
assert a[1]<a[0],a
for group in ['fps','exact']:
 subprocess.run([sys.executable,str(r/'tools/run_h11_checks.py'),group],check=True)
