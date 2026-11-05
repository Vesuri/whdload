from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1];group=sys.argv[1];cases=[]
def pair(mode,profile,name,base):
 for arm in ['control','candidate']:cases.append((mode,profile,name+'-'+arm,base+('-control' if arm=='control' else ''),{}))
if group=='initial':
 pair('states','a1200-fast','state','render-h2-matched')
 pair('frames','a1200-fast','normal','render-h2-matched-frames')
 pair('timing','a1200-fast','normal','render-h2')
elif group=='scenes':
 for scene in ['grid','dense']:
  pair('frames','a1200-fast',scene,'render-h2-'+scene+'-frames')
  pair('fps','a1200-fast',scene,'render-h2-'+scene)
elif group=='profiles':
 pair('profile','a1200-fast','matched','render-h2-matched-frames')
 cases.append(('profile','a1200-fast','census','render-h2',{'RENDER_CAPTURE':'census'}))
elif group=='accelerated':
 for profile in ['030-50','040-40','060-50']:
  pair('fps',profile,'normal','render-h2')
  for scene in ['grid','dense']:pair('fps',profile,scene,'render-h2-'+scene)
elif group=='controls':
 cases=[('live','a1200-fast','candidate','render-h2',{}),('controls','a1200-fast','clutch','render-h2',{'DRIVE_CLUTCH':'1'}),('manual','a1200-fast','manual','render-h2',{})]
elif group=='user-config':
 launch=json.loads((r/'tmp/step5/c4-q03-controls-a1200-fast-fixed-040-mmu-32m-controls/result.json').read_text())
 over={k:launch['launch'][k] for k in ['CPU','AMIGA_MODEL','CHIP_KB','SLOW_KB','FAST_KB']};over['EXTRA_ARGS']=launch['extra_args'];over['DRIVE_Z3_KB']='32768'
 cases=[('controls','a1200-fast','040-mmu-32m','render-h2',{'DRIVE_CLUTCH':'1','RELEASE_FSUAE':str(r/'tmp/step5-frame-observer-build/fs-uae'),'RELEASE_PROFILE_OVERRIDES':json.dumps(over)})]
else:raise ValueError(group)
for mode,profile,tag,build,extra in cases:
 b=r/'tmp/build'/build;env=dict(os.environ,H2_BUILD=str(b),DRIVE_MATCHED=str(b/'FerrariFormulaOne.slave'),DRIVE_SLAVE=str(b/'FerrariFormulaOne.slave'),C1_VARIANT='h2-'+tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache');env.update(extra)
 script={'states':'capture_drive_states.py','frames':'capture_h2_frames.py','timing':'test_h2_timing.py','fps':'test_h2_fps.py','profile':'capture_h2_profile.py','live':'run_h2_live.py','controls':'test_drive_controls.py','manual':'run_h2_manual.py'}[mode]
 print('Starting',mode,profile,tag,flush=True)
 log=r/f'tmp/h2-{mode}-{profile}-{tag}.log'
 with log.open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Finished',mode,profile,tag,flush=True)
 if tag.endswith('candidate') and mode in ['frames','states']:
  prefix='h2-frame' if mode=='frames' else 'drive-state'
  paths=[r/f'tmp/step5/c4-q03-{prefix}-production-{profile}-h2-'+Path('dummy')] if False else [r/f'tmp/step5/c4-q03-{prefix}-production-{profile}-h2-{tag.removesuffix("candidate")}{arm}' for arm in ['control','candidate']]
  if mode=='frames':
   x,y=[json.loads((p/'result.json').read_text())['frames'] for p in paths];assert x==y,(paths,x,y)
  else:
   assert (paths[0]/'records.bin').read_bytes()==(paths[1]/'records.bin').read_bytes(),paths
   assert json.loads((paths[0]/'private.json').read_text())==json.loads((paths[1]/'private.json').read_text()),paths
  print('EXACT',mode,profile,tag,flush=True)

 if tag.endswith('candidate') and mode=='fps':
  prefix=tag.removesuffix('candidate')
  pairs=[json.loads((r/f'tmp/step5/c4-q03-h2-fps-{profile}-h2-{prefix}{a}/result.json').read_text()) for a in ['control','candidate']]
  assert pairs[1]['mean_ms']<=pairs[0]['mean_ms']+1e-9,(profile,tag,pairs[0]['mean_ms'],pairs[1]['mean_ms'])
  assert pairs[1]['p95_ms']<=pairs[0]['p95_ms']+1e-9,(profile,tag,'p95')
  print('NO REGRESSION',profile,tag,pairs[0]['fps'],'->',pairs[1]['fps'],flush=True)
