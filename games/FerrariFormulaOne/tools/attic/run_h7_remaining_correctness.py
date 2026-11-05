from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1];mp=r/'manifest/render-h7-exact-raw.json';report=json.loads(mp.read_text());results=report['results']
for scene in ['normal','solo','grid','dense']:
 frames=[]
 for arm in ['control','candidate']:
  b=r/('tmp/build/render-h7-'+('matched' if scene=='normal' else scene)+'-stable-frames'+('-control' if arm=='control' else ''))
  tag='h7-stable-'+scene+'-'+arm;print('STABLE RGB',scene,arm,flush=True)
  env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
  with (r/f'tmp/{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/capture_h7_frames.py'),'040-40-bce'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  result=json.loads((r/f'tmp/step5/c4-q03-h5-frame-production-040-40-bce-{tag}/result.json').read_text());assert result['error']==0 and len(result['frames'])==30
  frames.append(result['frames']);results['stable-frames/040-40-bce/'+scene+'-'+arm]=result
 assert frames[0]==frames[1],scene
 mp.write_text(json.dumps(report,indent=2)+'\n');print('PASS stable RGB',scene,flush=True)
for arm in ['control','candidate']:
 b=r/('tmp/build/render-h7'+('-control' if arm=='control' else ''));tag='h7-normal-'+arm
 print('ELAPSED 040-bce',arm,flush=True)
 env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 with (r/f'tmp/h7-timing-040-40-bce-normal-{arm}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h5_timing.py'),'040-40-bce'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 v=json.loads((r/f'tmp/step5/c4-q03-drive-timing-040-40-bce-{tag}/result.json').read_text());assert v['error_percent']<=.25 and v['simulated_seconds']==60 and v['error']==0
 results['timing/040-40-bce/normal-'+arm]=v;mp.write_text(json.dumps(report,indent=2)+'\n')
report['status']='passed';report['frame_capture_correction']='040-bce original two-field capture included timing-dependent B8-PAL transitions. Preserved failed captures. Test-only 3-field post-draw CPU hold obtains 30 complete stable RGB fields for each scene, exact without masks or palette changes. Production untouched;020 original complete RGB pairs all passed.';mp.write_text(json.dumps(report,indent=2)+'\n')
