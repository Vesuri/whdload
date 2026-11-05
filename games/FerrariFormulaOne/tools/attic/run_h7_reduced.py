from pathlib import Path
import os,sys,json,subprocess,time,hashlib,collections
r=Path(__file__).resolve().parents[1];report={'status':'running','scope':'User reduced matrix: one020 correctness pass; representative020 no-regression and040 matched FPS; grid030/060 bothmodels; one040 native lifecycle/unload;020Fast legacybothCUSTOM1; threecandidate traces. Existing20directedcases reused byhash.','results':{}}
mp=r/'manifest/render-h7-reduced.json'
def save():mp.write_text(json.dumps(report,indent=2)+'\n')
def run(script,args,tag,env):
 print('REDUCED',tag,flush=True)
 with (r/f'tmp/h7-reduced-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),*args],env=dict(os.environ,**env),stdout=f,stderr=subprocess.STDOUT,check=True)
def env(build,tag):return dict(H5_BUILD=str(r/'tmp/build'/build),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
# Allow the in-flight dense control to finish its own cleanup.
for _ in range(300):
 try:os.kill(20599,0)
 except ProcessLookupError:break
 time.sleep(1)
else:raise RuntimeError('Prior capture still running')
run('capture_h7_frames.py',['a1200-fast'],'dense-rgb',env('render-h7-dense-stable-frames','h7-dense-candidate'))
for scene in ['normal','solo','grid','dense']:
 p=[r/f'tmp/step5/c4-q03-h5-frame-production-a1200-fast-h7-{scene}-{a}/result.json' for a in ['control','candidate']]
 a,b=[json.loads(x.read_text()) for x in p];assert a['error']==b['error']==0 and len(a['frames'])==len(b['frames'])==30 and a['frames']==b['frames'];report['results']['rgb/'+scene]=[str(x.relative_to(r)) for x in p]
run('test_h7_elapsed.py',['a1200-fast'],'elapsed',env('render-h7','h7-reduced-elapsed'))
p=r/'tmp/step5/c4-q03-drive-timing-a1200-fast-h7-reduced-elapsed/result.json';x=json.loads(p.read_text());assert x['status']=='passed';report['results']['elapsed']=x;save()
for arm in ['control','candidate']:
 tag='h7-reduced-normal-'+arm;run('test_h5_fps.py',['a1200-fast'],'fps-020-'+arm,env('render-h7'+('-control' if arm=='control' else ''),tag));p=r/f'tmp/step5/c4-q03-h5-fps-a1200-fast-{tag}/result.json';report['results']['fps/020/normal/'+arm]=json.loads(p.read_text());save()
a,b=[report['results']['fps/020/normal/'+arm] for arm in ['control','candidate']];assert b['mean_ms']<=a['mean_ms'] and b['p95_ms']<=a['p95_ms']
for profile in ['030-50','060-50','030-50-bce','060-50-bce']:
 tag='h7-reduced-grid';run('test_h5_fps.py',[profile],'fps-'+profile,env('render-h7-grid',tag));p=r/f'tmp/step5/c4-q03-h5-fps-{profile}-{tag}/result.json';x=json.loads(p.read_text());assert x['status']=='passed' and len(x['interval_fields'])==300
 if profile.endswith('bce'):assert abs(x['fps']-19.9681637134)<1,('material expectation difference',profile,x['fps'])
 else:assert set(x['interval_fields'])=={2},('material expectation difference',profile)
 report['results']['fps/'+profile+'/grid']=x;save();print('FPS',profile,x['fps'],collections.Counter(x['interval_fields']),flush=True)
run('test_h7_unload.py',['040-40'],'native-unload',env('render-h7-unload-64','unload-64'))
run('run_h7_live.py',['040-40'],'native-lifecycle',env('render-h7','h7-candidate'))
for option in ['0','1']:
 run('test_h7_legacy.py',[],'legacy-'+option,dict(RELEASE_CUSTOM1=option,RELEASE_PROFILES='a1200-fast'))
run('run_h7_reduced_profiles.py',[],'residual-traces',{})
report['status']='passed';save();print('REDUCED H7 GATES COMPLETED',flush=True)
