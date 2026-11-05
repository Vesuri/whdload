from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1]
def read(p):return json.loads((r/p).read_text())
mp='manifest/step5-c4-divide-r3a-validation.json';m=read(mp)
assert read(m['exact_state'])['status']=='passed'
assert read(m['arithmetic_oracle'])['status']=='passed'
assert read('manifest/step5-c4-divide-r3a-images.json')['status']=='passed'
assert read('manifest/step5-c4-r2-frame-padding.json')['status']=='passed'
m['measurements']={}
for scene,part,suffix in [('normal','ab','fps300'),('grid','start-grid-center','heavy-fps300'),('dense','heavy-v2','heavy-fps300')]:
 rows={};reports=[]
 for arm in (('baseline-render','candidate') if scene=='normal' else ('baseline-render','candidate','native')):
  p=f'tmp/step5/c4-divide-r3a-v3-{part}-a500-{arm}-{suffix}/result.json';j=read(p);reports.append(j)
  assert j['presentations']==300 and j['untraced'] and j['warp_start']==j['warp_end']=='warp=0'
  assert j['start']['error']==j['end']['error']==0
  if scene!='normal':assert j['restoration_exact'] and j['all_opponents_drawn'] and j['end']['HeavyIncomplete']==0
  rows[arm]=dict(fps=j['presented_fps'],evidence=p)
 assert rows['candidate']['fps']>=rows['baseline-render']['fps']
 if scene!='dense':assert rows['candidate']['fps']>=3.494
 if scene!='normal':assert len({j['fixed_scene_hex'] for j in reports})==1
 m['measurements'][scene]=rows
p='tmp/step5/c4-divide-r3a-v3-ab-a500-candidate-elapsed/result.json';j=read(p);assert j['status']=='passed'
fps=(j['end']['B8Frames']-j['start']['B8Frames'])/j['elapsed_seconds'];assert fps>=3.6
m['elapsed']=dict(evidence=p,fps=fps,error_percent=j['error_percent'])
m['images']='manifest/step5-c4-divide-r3a-images.json';m['image_padding_audit']='manifest/step5-c4-r2-frame-padding.json'
m['exit']='tmp/step5/c4-divide-r3a-v3-ab-a500-exit/result.json';assert read(m['exit'])['status']=='passed'
m['legacy_exact']='manifest/step5-c4-divide-r3a-v3-default-validation.json';assert read(m['legacy_exact'])['status']=='passed'
m['profiles']={}
for arm in ('baseline-render','candidate'):
 p=f'tmp/step5/c4-divide-r3a-v3-fullloop-a500-{arm}';assert read(p+'/audit.json')['status']=='passed';assert (r/p/'trace-archives.json').exists();m['profiles'][arm]=p
m['status']='passed';m['disabled_candidate_sha256']='acba24f17014009b7f203ac8d6b669609114cbcb3c392655d2e5589ef5a3a3eb'
m['p01_same_workload_passed']=m['measurements']['dense']['candidate']['fps']>=m['measurements']['dense']['native']['fps']
m['r3b_required']=m['measurements']['dense']['candidate']['fps']<3.33
(r/mp).write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
