from pathlib import Path
import json,os,sys,subprocess,hashlib,collections
r=Path(__file__).resolve().parents[1]
p=r/'manifest/step3-profiles.json';profiles=json.loads(p.read_text())
for n in ['030-50','040-40','060-50']:
 profiles[n+'-bce']=dict(profiles[n],EXTRA_ARGS=profiles[n]['EXTRA_ARGS']+' --uae_blitter_cycle_exact=true')
profiles['030-50-trace']=dict(profiles['030-50'],CPU='68EC030')
profiles['030-50-trace-bce']=dict(profiles['030-50-bce'],CPU='68EC030')
p.write_text(json.dumps(profiles,indent=2)+'\n')
base=r/'tmp/build/render-h6'
subprocess.run([sys.executable,str(r.parents[1]/'Games/FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(base)],check=True,stdout=(r/'tmp/h6-build.log').open('w'))
assert (base/'FerrariFormulaOne.slave').read_bytes()==(r/'tmp/build/render-h5/FerrariFormulaOne.slave').read_bytes()
# Fixture sources are H5 matched HEAD; frozen code is byte-identical to HEAD.
subprocess.run([sys.executable,str(r/'tools/build_hi25_fixtures.py'),'solo','grid','dense'],check=True,stdout=(r/'tmp/h6-fixtures.log').open('w'))
results={}
for profile in ['a1200-fast','030-50','040-40','060-50','030-50-bce','040-40-bce','060-50-bce']:
 for scene in ['normal','solo','grid','dense']:
  tag='h6-'+scene;out=r/f'tmp/step5/c4-q03-h5-fps-{profile}-{tag}/result.json'
  build=base if scene=='normal' else r/f'tmp/build/render-hi25-{scene}'
  env=dict(os.environ,H5_BUILD=str(build),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
  print('H6',profile,scene,flush=True)
  with (r/f'tmp/h6-{profile}-{scene}.log').open('w') as log:subprocess.run([sys.executable,str(r/'tools/test_h5_fps.py'),profile],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  d=json.loads(out.read_text());results[profile+'/'+scene]={k:d[k] for k in ['fps','mean_ms','p95_ms','slave_sha256','emulator_sha256','extra_args','error']};results[profile+'/'+scene]['histogram']=dict(collections.Counter(d['interval_fields']));results[profile+'/'+scene]['result']=str(out.relative_to(r))
  (r/'manifest/render-h6-baseline.json').write_text(json.dumps(dict(status='running',results=results),indent=2)+'\n')
  print(results[profile+'/'+scene],flush=True)
(r/'manifest/render-h6-baseline.json').write_text(json.dumps(dict(status='passed',results=results),indent=2)+'\n')
