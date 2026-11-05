from pathlib import Path
import json,hashlib,collections
from PIL import Image
r=Path(__file__).resolve().parents[1];out={'status':'pending','scope':'User-reduced acceptance: representative020 correctness/no-regression;040 matched FPS;030/060 grid both models;20directedownership/faultcases;040native lifecycle/unload;020Fast CUSTOM2=0 bothCUSTOM1;030EC/040/060BCE candidate traces. No full CPU-by-scene matrix claim.'}
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof={}
def result(name,build=None):
 p=r/'tmp/step5'/name/'result.json';x=read(p)
 if build:assert x['slave_sha256']==sha(r/'tmp/build'/build/'FerrariFormulaOne.slave'),name
 proof[name]={'result':str(p.relative_to(r)),'sha256':sha(p)}
 return x
build=read(r/'tmp/manifest/render-h7-build-audit.json');assert build['status']=='passed' and build['candidate_sha256']==sha(r/'tmp/build/render-h7/FerrariFormulaOne.slave');out['build']=build
states=[]
for arm in ['control','candidate']:
 name='c4-q03-drive-state-production-a1200-fast-h7-state-'+arm;x=result(name,'render-h7-matched'+('-control' if arm=='control' else ''));assert x['steps']==100 and x['context_after'][6]==100 and x['error']==0;states.append(r/'tmp/step5'/name)
assert (states[0]/'records.bin').read_bytes()==(states[1]/'records.bin').read_bytes();assert read(states[0]/'private.json')==read(states[1]/'private.json')
for scene in ['normal','solo','grid','dense']:
 pair=[]
 for arm in ['control','candidate']:
  name=f'c4-q03-h5-frame-production-a1200-fast-h7-{scene}-{arm}';b='render-h7-'+('matched' if scene=='normal' else scene)+'-stable-frames'+('-control' if arm=='control' else '')
  x=result(name,b);assert x['error']==0 and len(x['frames'])==30
  for f in x['frames']:
   im=Image.open(r/'tmp/step5'/name/f"frame-{f['update']}.png").convert('RGB');assert hashlib.sha256(im.tobytes()).hexdigest()==f['pixel_sha256']
  pair.append(x['frames'])
 assert pair[0]==pair[1]
x=result('c4-q03-drive-timing-a1200-fast-h7-reduced-elapsed','render-h7');assert x['status']=='passed' and x['simulated_seconds']==60 and x['error_percent']<=.25;out['elapsed_error_percent']=x['error_percent']
fps={}
def fpscase(profile,scene,tag,build):
 x=result(f'c4-q03-h5-fps-{profile}-{tag}',build);assert x['status']=='passed' and x['error']==0 and len(x['interval_fields'])==300 and x.get('heavy_incomplete',0)==0
 return {k:x[k] for k in ['fps','mean_ms','p95_ms','slave_sha256']}|{'histogram':dict(sorted(collections.Counter(x['interval_fields']).items()))}
for scene,tag in [('normal','h7-reduced-normal'),('dense','h7-dense-repeat')]:
 pair=[]
 for arm in ['control','candidate']:
  v=fpscase('a1200-fast',scene,tag+'-'+arm,'render-h7'+('' if scene=='normal' else '-dense')+('-control' if arm=='control' else ''));fps['a1200-fast/'+scene+'/'+arm]=v;pair.append(v)
 assert pair[1]['mean_ms']<=pair[0]['mean_ms'] and pair[1]['p95_ms']<=pair[0]['p95_ms']
for p in ['040-40','040-40-bce']:
 for s in ['solo','grid']:
  for a in ['control','candidate']:fps[p+'/'+s+'/'+a]=fpscase(p,s,'h7-'+s+'-'+a,'render-h7-'+s+('-control' if a=='control' else ''))
  a,b=[fps[p+'/'+s+'/'+v] for v in ['control','candidate']];assert b['mean_ms']<=a['mean_ms'] and b['p95_ms']<=a['p95_ms']
for p in ['030-50','060-50','030-50-bce','060-50-bce']:fps[p+'/grid/candidate']=fpscase(p,'grid','h7-reduced-grid','render-h7-grid')
for k,v in fps.items():
 if k.startswith(('030','040','060')) and k.endswith('candidate'):
  if '-bce/grid/' in k:assert abs(v['fps']-19.9681637134)<1
  else:assert v['histogram']=={2:300}
out['fps']=fps
for p in ['a1200-fast','030-50','040-40','060-50']:
 for c in ['ownership','fault-set','fault-clear','schedule-fault','velocity-fault']:assert result(f'c4-q03-h7-ownership-{p}-{c}','render-h7-'+c)['status']=='passed'
x=result('c4-q03-h7-unload-040-40-unload-64','render-h7-unload-64');assert x['status']=='passed' and x['native_unload_returned']
x=result('c4-q03-h7-live-040-40-h7-candidate','render-h7');assert x['status']=='passed' and x['error']==0;out['lifecycle_ledger_restored_words']=x['ledger_restored_words']
for option in [0,1]:
 p=r/f'tmp/manifest/render-h7-default-c{option}-validation.json';x=read(p);assert x['status']=='passed' and x['profiles']['a1200-fast']['passed'];proof['legacy'+str(option)]={'result':str(p.relative_to(r)),'sha256':sha(p)}
traces=read(r/'tmp/manifest/render-h7-traces.json');assert len(traces)==3
out['residual']={}
for key,v in traces.items():
 p=r/v['trace'];assert read(p/'h7-safety.json')['status']=='passed';x=read(p/'result.json');assert x['slave_sha256']==sha(r/'tmp/build/render-h7-grid/FerrariFormulaOne.slave');a=read(p/'hi25-analysis.json');out['residual'][key]=a['mean_after_wait_ms']
assert read(r/'tmp/manifest/render-h7-enabler.json')['status']=='passed'
out['proof']=proof;out['traces']=traces;out['status']='passed';(r/'tmp/manifest/render-h7-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['status','elapsed_error_percent','residual']},indent=2))
