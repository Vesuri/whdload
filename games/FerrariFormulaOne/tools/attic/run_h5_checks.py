from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1];group=sys.argv[1];cases=[]
def pair(mode,profile,name,base):
 for arm in ['control','candidate']:cases.append((mode,profile,name+'-'+arm,base+('-control' if arm=='control' else ''),{}))
if group=='frames-timing':
 pair('frames','a1200-fast','normal','render-h5-matched-frames')
 pair('timing','a1200-fast','normal','render-h5')
elif group=='initial':
 pair('states','a1200-fast','state','render-h5-matched')
 pair('frames','a1200-fast','normal','render-h5-matched-frames')
 pair('timing','a1200-fast','normal','render-h5')
elif group=='scenes':
 for scene in ['grid','dense']:
  pair('frames','a1200-fast',scene,'render-h5-'+scene+'-frames')
  pair('fps','a1200-fast',scene,'render-h5-'+scene)
elif group=='profiles':
 pair('profile','a1200-fast','matched','render-h5-matched-frames')
 cases.append(('profile','a1200-fast','census','render-h5',{'RENDER_CAPTURE':'census'}))
elif group=='accelerated':
 for profile in os.environ.get('H5_PROFILES','030-50,040-40,060-50').split(','):
  pair('fps',profile,'normal','render-h5')
  for scene in ['grid','dense']:pair('fps',profile,scene,'render-h5-'+scene)
elif group=='controls':
 cases=[('live','a1200-fast','candidate','render-h5',{}),('controls','a1200-fast','clutch','render-h5',{'DRIVE_CLUTCH':'1'}),('manual','a1200-fast','manual','render-h5',{})]
elif group=='user-config':
 launch=json.loads((r/'tmp/step5/c4-q03-controls-a1200-fast-fixed-040-mmu-32m-controls/result.json').read_text())
 over={k:launch['launch'][k] for k in ['CPU','AMIGA_MODEL','CHIP_KB','SLOW_KB','FAST_KB']};over['EXTRA_ARGS']=launch['extra_args'];over['DRIVE_Z3_KB']='32768'
 cases=[('controls','a1200-fast','040-mmu-32m','render-h5',{'DRIVE_CLUTCH':'1','RELEASE_FSUAE':str(r/'tmp/step5-frame-observer-build/fs-uae'),'RELEASE_PROFILE_OVERRIDES':json.dumps(over)})]
else:raise ValueError(group)
for mode,profile,tag,build,extra in cases:
 b=r/'tmp/build'/build;env=dict(os.environ,H5_BUILD=str(b),DRIVE_MATCHED=str(b/'FerrariFormulaOne.slave'),DRIVE_SLAVE=str(b/'FerrariFormulaOne.slave'),C1_VARIANT='h5-'+tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache');env.update(extra)
 script={'states':'capture_drive_states.py','frames':'capture_h5_frames.py','timing':'test_h5_timing.py','fps':'test_h5_fps.py','profile':'capture_h5_profile.py','live':'run_h5_live.py','controls':'test_drive_controls.py','manual':'run_h5_manual.py'}[mode]
 print('Starting',mode,profile,tag,flush=True)
 log=r/f'tmp/h5-{mode}-{profile}-{tag}.log'
 with log.open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Finished',mode,profile,tag,flush=True)
 if tag.endswith('candidate') and mode in ['frames','states']:
  prefix='h5-frame' if mode=='frames' else 'drive-state'
  paths=[r/f'tmp/step5/c4-q03-{prefix}-production-{profile}-h5-'+Path('dummy')] if False else [r/f'tmp/step5/c4-q03-{prefix}-production-{profile}-h5-{tag.removesuffix("candidate")}{arm}' for arm in ['control','candidate']]
  if mode=='frames':
   x,y=[json.loads((p/'result.json').read_text())['frames'] for p in paths];assert x==y,(paths,x,y)
  else:
   assert (paths[0]/'records.bin').read_bytes()==(paths[1]/'records.bin').read_bytes(),paths
   assert json.loads((paths[0]/'private.json').read_text())==json.loads((paths[1]/'private.json').read_text()),paths
  print('EXACT',mode,profile,tag,flush=True)

 if tag.endswith('candidate') and mode=='fps':
  prefix=tag.removesuffix('candidate')
  pairs=[json.loads((r/f'tmp/step5/c4-q03-h5-fps-{profile}-h5-{prefix}{a}/result.json').read_text()) for a in ['control','candidate']]
  assert pairs[1]['mean_ms']<=pairs[0]['mean_ms']+1e-9,(profile,tag,pairs[0]['mean_ms'],pairs[1]['mean_ms'])
  assert pairs[1]['p95_ms']<=pairs[0]['p95_ms']+1e-9,(profile,tag,'p95')
  print('NO REGRESSION',profile,tag,pairs[0]['fps'],'->',pairs[1]['fps'],flush=True)
