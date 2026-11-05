# Cache-policy correctness gates against the accepted B8-PAL references.
from pathlib import Path
import os,sys,json,subprocess,hashlib,gzip,shutil
r=Path(__file__).resolve().parents[1];report={'status':'running','results':{}};mp=r/'manifest/cache-policy-validation.json'
def raw(p,name):
 f=p/name
 if f.exists():return f.read_bytes()
 with gzip.open(p/(name+'.gz')) as z:return z.read()
cases=[('states','040-40-bce','state','render-cachepol-matched'),('frames','040-40-bce','normal','render-cachepol-matched-stable-frames'),('frames','040-40-bce','grid','render-cachepol-grid-stable-frames'),('timing','040-40-bce','elapsed','tmp/build/cache-policy')]
sel=sys.argv[1:]
for mode,profile,tag,bname in cases:
 if sel and f'{mode}/{profile}/{tag}' not in sel:continue
 b=r/'tmp/build'/bname if not bname.startswith('tmp/') else r/bname;ctag='cachepol-'+tag;env=dict(os.environ,H5_BUILD=str(b),DRIVE_MATCHED=str(b/'FerrariFormulaOne.slave'),C1_VARIANT=ctag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 script={'states':'capture_drive_states.py','frames':'capture_h7_frames.py','timing':'test_h7_elapsed.py'}[mode];prefix={'states':'c4-q03-drive-state-production','frames':'c4-q03-h5-frame-production','timing':'c4-q03-drive-timing'}[mode]
 p=r/f'tmp/step5/{prefix}-{profile}-{ctag}';old=r/f'tmp/step5/{prefix}-040-40-bce-b8pal-{tag}';print('RUN',mode,profile,tag,flush=True)
 with (r/f'tmp/cachepol/{mode}-{profile}-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 x=json.loads((p/'result.json').read_text());assert x['error']==0 and x['slave_sha256']==hashlib.sha256((b/'FerrariFormulaOne.slave').read_bytes()).hexdigest()
 if mode=='states':
  assert x['steps']==100;assert raw(p,'records.bin')==raw(old,'records.bin');assert json.loads((p/'private.json').read_text())==json.loads((old/'private.json').read_text())
 if mode=='frames':assert len(x['frames'])==30 and x['frames']==json.loads((old/'result.json').read_text())['frames']
 if mode=='timing':assert x['simulated_seconds']==60 and x['error_percent']<=.25;print('elapsed error %',x['error_percent'],flush=True)
 report['results'][f'{mode}/{profile}/{tag}']={'path':str(p.relative_to(r)),'reference':str(old.relative_to(r)),'error':x['error']};mp.write_text(json.dumps(report,indent=2)+'\n');print('PASS',mode,profile,tag,flush=True)
 for f in p.glob('*.bin'):
  if f.stat().st_size<262144:continue
  h=hashlib.sha256(f.read_bytes()).hexdigest();z=f.with_suffix('.bin.gz')
  with f.open('rb') as a,gzip.open(z,'wb',compresslevel=1) as d:shutil.copyfileobj(a,d)
  with gzip.open(z,'rb') as a:assert hashlib.file_digest(a,'sha256').hexdigest()==h
  f.unlink()
