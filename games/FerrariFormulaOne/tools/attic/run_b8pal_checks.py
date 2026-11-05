from pathlib import Path
import os,sys,json,subprocess,hashlib,gzip,shutil,collections
r=Path(__file__).resolve().parents[1];report={'status':'running','results':{}};mp=r/'manifest/b8-pal-validation.json'
cases=[('states','040-40-bce','state','render-b8pal-matched'),('frames','040-40-bce','normal','render-b8pal-matched-stable-frames'),('frames','040-40-bce','grid','render-b8pal-grid-stable-frames'),('timing','040-40-bce','elapsed','render-b8pal'),('fps','040-40-bce','grid','render-b8pal-grid'),('trace','040-40-bce','grid','render-b8pal-grid')]
for mode,profile,tag,bname in cases:
 b=r/'tmp/build'/bname;tag='b8pal-'+tag;env=dict(os.environ,H5_BUILD=str(b),DRIVE_MATCHED=str(b/'FerrariFormulaOne.slave'),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache',HI25_FIELDS='6')
 script={'states':'capture_drive_states.py','frames':'capture_h7_frames.py','timing':'test_h7_elapsed.py','fps':'test_h5_fps.py','trace':'capture_hi25_profile.py'}[mode];prefix={'states':'c4-q03-drive-state-production','frames':'c4-q03-h5-frame-production','timing':'c4-q03-drive-timing','fps':'c4-q03-h5-fps','trace':'hi25-profile'}[mode]
 p=r/f'tmp/step5/{prefix}-{profile}-{tag}';print('RUN',mode,tag,flush=True)
 with (r/f'tmp/b8pal-{mode}-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 x=json.loads((p/'result.json').read_text());assert x['error']==0 and x['slave_sha256']==hashlib.sha256((b/'FerrariFormulaOne.slave').read_bytes()).hexdigest()
 oldtag=tag.replace('b8pal-','h11-v2-')+'-candidate';old=r/f'tmp/step5/{prefix}-{profile}-{oldtag}'
 if mode=='states':
  assert x['steps']==100;assert (p/'records.bin').read_bytes()==(old/'records.bin').read_bytes();assert json.loads((p/'private.json').read_text())==json.loads((old/'private.json').read_text())
 if mode=='frames':assert len(x['frames'])==30 and x['frames']==json.loads((old/'result.json').read_text())['frames']
 if mode=='timing':assert x['simulated_seconds']==60 and x['error_percent']<=.25
 if mode=='fps':
  assert len(x['interval_fields'])==300 and x['interval_fields'].count(2)>=285 and max(x['interval_fields'])<=3
  print('FPS',x['fps'],collections.Counter(x['interval_fields']),flush=True)
 report['results'][mode+'/'+tag]={'path':str(p.relative_to(r)),'result':x};mp.write_text(json.dumps(report,indent=2)+'\n');print('PASS',mode,tag,flush=True)
 if mode!='trace':
  for f in p.glob('*.bin'):
   if f.stat().st_size<262144:continue
   h=hashlib.sha256(f.read_bytes()).hexdigest();z=f.with_suffix('.bin.gz')
   with f.open('rb') as a,gzip.open(z,'wb',compresslevel=1) as d:shutil.copyfileobj(a,d)
   with gzip.open(z,'rb') as a:assert hashlib.file_digest(a,'sha256').hexdigest()==h
   f.unlink()
report['capture_status']='passed';mp.write_text(json.dumps(report,indent=2)+'\n')
