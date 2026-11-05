from pathlib import Path
import os,sys,subprocess,json,hashlib,collections
r=Path(__file__).resolve().parents[1];mp=r/'manifest/render-h11-v2-checks.json';report=json.loads(mp.read_text()) if mp.exists() else {'status':'running','results':{}};group=sys.argv[1];cases=[]
def pair(mode,p,scene,build):
 for a in ['control','candidate']:cases.append((mode,p,scene+'-'+a,build+('-control' if a=='control' else '')))
if group=='exact':
 pair('states','040-40-bce','state','render-h11-v2-matched')
 for scene in ['normal','solo','grid','dense']:pair('frames','040-40-bce',scene,'render-h11-v2-'+('matched' if scene=='normal' else scene)+'-stable-frames')
 cases.append(('timing','040-40-bce','elapsed','render-h11-v2'))
elif group=='fps':
 pair('fps','040-40-bce','grid','render-h11-v2-grid')
 pair('fps','040-40-bce','dense','render-h11-v2-dense')
 cases.append(('fps','060-50-bce','grid-candidate','render-h11-v2-grid'))
 cases.append(('fps','030-50-bce','grid-candidate','render-h11-v2-grid'))
 pair('fps','a1200-fast','normal','render-h11-v2')
elif group=='tracecontrol':cases.append(('trace','040-40-bce','grid-control','render-h11-v2-grid-control'))
elif group=='trace':cases.append(('trace','040-40-bce','grid-candidate','render-h11-v2-grid'))
else:raise ValueError(group)
for mode,profile,tag,bname in cases:
 b=r/'tmp/build'/bname;tag='h11-v2-'+tag;env=dict(os.environ,H5_BUILD=str(b),DRIVE_MATCHED=str(b/'FerrariFormulaOne.slave'),DRIVE_SLAVE=str(b/'FerrariFormulaOne.slave'),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 script={'states':'capture_drive_states.py','frames':'capture_h7_frames.py','timing':'test_h7_elapsed.py','fps':'test_h5_fps.py','trace':'capture_hi25_profile.py'}[mode]
 prefix={'states':'c4-q03-drive-state-production','frames':'c4-q03-h5-frame-production','timing':'c4-q03-drive-timing','fps':'c4-q03-h5-fps','trace':'hi25-profile'}[mode]
 p=r/f'tmp/step5/{prefix}-{profile}-{tag}';key=f'{mode}/{profile}/{tag}';sha=hashlib.sha256((b/'FerrariFormulaOne.slave').read_bytes()).hexdigest()
 prior=json.loads((p/'result.json').read_text()) if (p/'result.json').exists() else {}
 if prior.get('status') not in ('passed','captured') or prior.get('slave_sha256')!=sha:
  print('RUN',key,flush=True)
  with (r/f'tmp/{group}-{profile}-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 x=json.loads((p/'result.json').read_text());assert x.get('error',0)==0
 if mode=='states':assert x['steps']==100 and x['context_after'][6]==100
 if mode=='frames':assert len(x['frames'])==30
 if mode=='timing':assert x['error_percent']<=.25 and x['simulated_seconds']==60
 if tag.endswith('candidate') and mode in ['states','frames','fps']:
  c=p.with_name(p.name.removesuffix('candidate')+'control')
  if c.exists():
   y=json.loads((c/'result.json').read_text())
   if mode=='states':assert (c/'records.bin').read_bytes()==(p/'records.bin').read_bytes();assert json.loads((c/'private.json').read_text())==json.loads((p/'private.json').read_text())
   if mode=='frames':assert x['frames']==y['frames'],tag
   if mode=='fps':assert x['mean_ms']<=y['mean_ms']+1e-9 and x['p95_ms']<=y['p95_ms']+1e-9,(key,x['mean_ms'],y['mean_ms'])
 if mode=='fps':print('FPS',x['fps'],collections.Counter(x['interval_fields']),flush=True)
 report['results'][key]=dict(path=str(p.relative_to(r)),sha256=sha,result=x);mp.write_text(json.dumps(report,indent=2)+'\n');print('PASS',key,flush=True)
 if mode!='trace':subprocess.run([sys.executable,str(r/'tools/archive_h11.py')],check=True)
report[group]='passed';mp.write_text(json.dumps(report,indent=2)+'\n')
