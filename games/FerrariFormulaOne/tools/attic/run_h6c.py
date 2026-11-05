from pathlib import Path
import os,sys,json,subprocess,hashlib,collections,gzip,shutil
r=Path.cwd()/'tmp/dev';out=r/'manifest/render-h6c-validation.json'
report={'status':'running','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'results':{}}
for profile in ['040-40-bce','060-50-bce','030-50-bce']:
 for scene in ['normal','solo','grid']:
  b=r/('tmp/build/render-h11-v2'+('' if scene=='normal' else '-'+scene));sha=hashlib.sha256((b/'FerrariFormulaOne.slave').read_bytes()).hexdigest()
  tag='h11-v2-grid-candidate' if scene=='grid' else 'h6c-'+scene
  p=r/f'tmp/step5/c4-q03-h5-fps-{profile}-{tag}'
  if scene!='grid':
   print('RUN',profile,scene,flush=True)
   env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
   with (r/f'tmp/h6c-{profile}-{scene}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h5_fps.py'),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  x=json.loads((p/'result.json').read_text());assert x['slave_sha256']==sha and x['status']=='passed' and len(x['interval_fields'])==300 and x['error']==0
  hist=dict(sorted(collections.Counter(x['interval_fields']).items()));row={'path':str(p.relative_to(r)),'origin':'retained H11 same-source measurement' if scene=='grid' else 'fresh H6c measurement','sha256':sha,'fps':x['fps'],'mean_ms':x['mean_ms'],'p95_ms':x['p95_ms'],'histogram':hist,'target_pass':x['interval_fields']==[2]*300}
  report['results'][profile+'/'+scene]=row;out.write_text(json.dumps(report,indent=2)+'\n');print('RESULT',profile,scene,row,flush=True)
  if scene!='grid':
   for f in p.glob('*.bin'):
    if f.stat().st_size<262144:continue
    h=hashlib.sha256(f.read_bytes()).hexdigest();z=f.with_suffix('.bin.gz')
    with f.open('rb') as a,gzip.open(z,'wb',compresslevel=1) as d:shutil.copyfileobj(a,d)
    with gzip.open(z,'rb') as a:assert hashlib.file_digest(a,'sha256').hexdigest()==h
    f.unlink()
report['status']='measurement-complete';report['required_target_pass']=all(x['target_pass'] for k,x in report['results'].items() if not k.startswith('030'));out.write_text(json.dumps(report,indent=2)+'\n')
