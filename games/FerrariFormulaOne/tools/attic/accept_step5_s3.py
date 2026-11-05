from pathlib import Path
import json,hashlib,subprocess
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def read(path):return json.loads((r/path).read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
checks={}
for name in ['state','profile']+[f'p{n}-{kind}' for n in (0,1,3) for kind in ('elapsed','replay')]:
 path=f'manifest/step5-s3-{name}-validation.json';d=read(path);assert d['status']=='passed',(path,d['status']);checks[name]=path
fixtures={}
for profile in ('a1200','a1200-fast'):
 fixtures[profile]={}
 for kind,prefix,cases in (('clocks','s3-clocks-v8',264),('recovery','s3-v3-recovery',1008),('flags','s3-flags',216)):
  path=f'tmp/step5/{prefix}-{profile}/result.json';d=read(path)
  assert d['status']=='passed' and not d['failures'] and d['cases']==cases,(path,d.get('status'))
  assert d['slave_sha256']==digest(r/f'tmp/build/step5-s3-{kind}/fine.slave')
  fixtures[profile][kind]={'result':path,'cases':cases,'sha256':d['slave_sha256']}
source=repo/'Games/FerrariFormulaOne_WHD.s';release=r/'tmp/build/release/FerrariFormulaOne.slave'
assert digest(source)=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
assert digest(release)=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
assert b'FerrariFormulaOne_Presentation.s' not in source.read_bytes()
report={'status':'passed','scope':'S3 candidate component simulation/presentation separation on both 020 diagnostics. Same native state at matched ticks; 0/1/3 real presentation passes; elapsed/replay plus isolated transition oracles; corrected-S2 lean A/B with zero native blits and zero dynamically located WaitBlit busy-spin in the simulation-only window. No final Plan B, coarse-path or full renderer acceptance.','checks':checks,'fixtures':fixtures,'cycles':read('manifest/step5-s3-profile-validation.json')['profiles'],'ordinary_source_sha256':digest(source),'ordinary_release_sha256':digest(release),'default_off':True,'source_modules':{n:digest(repo/'Games'/n) for n in ('FerrariFormulaOne_Presentation.s','FerrariFormulaOne_UpdateHooks.s')}}
(r/'manifest/step5-s3-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('S3 gates passed')
