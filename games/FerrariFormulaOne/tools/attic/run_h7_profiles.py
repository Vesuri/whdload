from pathlib import Path
import os,sys,subprocess,json,gzip,hashlib,shutil
r=Path(__file__).resolve().parents[1];index={}
for profile,scene in [('a1200-fast','normal'),('030-50-trace-bce','grid'),('040-40-bce','grid'),('060-50-bce','grid')]:
 for arm in ['control','candidate']:
  tag='h7-'+scene+'-'+arm;b=r/('tmp/build/render-h7'+('' if scene=='normal' else '-'+scene)+('-control' if arm=='control' else ''))
  env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache',HI25_FIELDS='30')
  print('TRACE',profile,tag,flush=True)
  with (r/f'tmp/h7-profile-{profile}-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/capture_hi25_profile.py'),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  p=r/f'tmp/step5/hi25-profile-{profile}-{tag}'
  for script in ['analyze_hi25_profile.py','analyze_hi25_calls.py','analyze_hi25_blits.py','analyze_hi25_blitgaps.py','audit_h7_trace.py']:
   with (p/(script+'.log')).open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
  raw=p/'detail.bin';sha=hashlib.sha256(raw.read_bytes()).hexdigest();z=raw.with_suffix('.bin.gz')
  with raw.open('rb') as src,gzip.open(z,'wb',compresslevel=6) as dst:shutil.copyfileobj(src,dst)
  with gzip.open(z,'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==sha
  index[profile+'/'+arm]={'trace':str(p.relative_to(r)),'raw_sha256':sha,'raw_bytes':raw.stat().st_size,'compressed_bytes':z.stat().st_size};raw.unlink()
  (r/'manifest/render-h7-traces.json').write_text(json.dumps(index,indent=2)+'\n')
  a=json.loads((p/'hi25-analysis.json').read_text());print('POST-WAIT',profile,arm,a['mean_after_wait_ms'],flush=True)
