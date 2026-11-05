from pathlib import Path
import os,sys,subprocess,json,collections,hashlib
r=Path(__file__).resolve().parents[1];group=sys.argv[1];cases=[]
def pair(mode,profile,name,base):
 for arm in ['control','candidate']:cases.append((mode,profile,name+'-'+arm,base+('-control' if arm=='control' else ''),{}))
if group=='exact':
 for p in ['a1200-fast','040-40-bce']:
  pair('states',p,'state','render-h7-matched')
  for scene in ['normal','solo','grid','dense']:pair('frames',p,scene,'render-h7-'+('matched' if scene=='normal' else scene)+'-stable-frames')
  pair('timing',p,'normal','render-h7')
elif group=='smoke':
 for p in ['040-40','040-40-bce']:
  for scene in ['solo','grid']:pair('fps',p,scene,'render-h7-'+scene)
elif group=='fps':
 for p in ['a1200-fast','030-50','040-40','060-50','030-50-bce','040-40-bce','060-50-bce']:
  for scene in ['normal','solo','grid','dense']:pair('fps',p,scene,'render-h7'+('' if scene=='normal' else '-'+scene))
else:raise ValueError(group)
results={}
for mode,profile,tag,build,extra in cases:
 b=r/'tmp/build'/build;env=dict(os.environ,H5_BUILD=str(b),DRIVE_MATCHED=str(b/'FerrariFormulaOne.slave'),DRIVE_SLAVE=str(b/'FerrariFormulaOne.slave'),C1_VARIANT='h7-'+tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache');env.update(extra)
 script={'states':'capture_drive_states.py','frames':'capture_h7_frames.py','timing':'test_h5_timing.py','fps':'test_h5_fps.py'}[mode]
 print('Starting',mode,profile,tag,flush=True)
 prior=r/f'tmp/step5/c4-q03-h5-fps-{profile}-h7-{tag}/result.json'
 reuse=mode=='fps' and prior.exists() and json.loads(prior.read_text()).get('status')=='passed' and json.loads(prior.read_text()).get('slave_sha256')==hashlib.sha256((b/'FerrariFormulaOne.slave').read_bytes()).hexdigest()
 if not reuse:
  with (r/f'tmp/h7-{mode}-{profile}-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 prefix={'states':'drive-state-production','frames':'h5-frame-production','timing':'drive-timing','fps':'h5-fps'}[mode]
 path=r/f'tmp/step5/c4-q03-{prefix}-{profile}-h7-{tag}'
 results[mode+'/'+profile+'/'+tag]=json.loads((path/'result.json').read_text())
 current=results[mode+'/'+profile+'/'+tag];assert current.get('error',0)==0,current
 if mode=='states':assert current['steps']==100 and current['context_after'][6]==100
 if mode=='frames':assert len(current['frames'])==30
 if mode=='timing':assert current['error_percent']<=.25 and current['simulated_seconds']==60
 if tag.endswith('candidate'):
  arms=[r/f'tmp/step5/c4-q03-{prefix}-{profile}-h7-{tag.removesuffix("candidate")}{a}' for a in ['control','candidate']]
  if mode=='states':
   assert (arms[0]/'records.bin').read_bytes()==(arms[1]/'records.bin').read_bytes()
   assert json.loads((arms[0]/'private.json').read_text())==json.loads((arms[1]/'private.json').read_text())
  if mode=='frames':assert json.loads((arms[0]/'result.json').read_text())['frames']==json.loads((arms[1]/'result.json').read_text())['frames']
  if mode=='fps':
   a,b=[json.loads((x/'result.json').read_text()) for x in arms]
   print('FPS',profile,tag,a['fps'],'->',b['fps'],collections.Counter(b['interval_fields']),flush=True)
   assert b['mean_ms']<=a['mean_ms']+1e-9,(profile,tag,'mean regression',a['mean_ms'],b['mean_ms'])
   assert b['p95_ms']<=a['p95_ms']+1e-9,(profile,tag,'p95 regression')
   if profile in ['030-50','040-40','060-50'] and tag.split('-')[0] in ['solo','grid']:assert set(b['interval_fields'])=={2},('material expectation difference',profile,tag)
   if profile in ['030-50-bce','040-40-bce','060-50-bce'] and tag.startswith('solo'):assert set(b['interval_fields'])=={2},('material expectation difference',profile,tag)
   if profile in ['030-50-bce','040-40-bce','060-50-bce'] and tag.startswith('grid'):assert abs(b['fps']-19.9681637134)<1,('material expectation difference',profile,tag,b['fps'])
  print('PASS',mode,profile,tag,flush=True)
 (r/f'manifest/render-h7-{group}-raw.json').write_text(json.dumps({'status':'running','results':results},indent=2)+'\n')
(r/f'manifest/render-h7-{group}-raw.json').write_text(json.dumps({'status':'passed','results':results},indent=2)+'\n')
