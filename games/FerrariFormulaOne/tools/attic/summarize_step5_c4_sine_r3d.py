from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1]
def read(p):return json.loads((r/p).read_text())
b=r/'tmp/build/step5-c4-sine-r3d-v1-ab/000'
c=(b/'candidate.slave').read_bytes();a=(b/'baseline-render.slave').read_bytes()
assert len(a)==len(c)
diff=[i for i,(x,y) in enumerate(zip(a,c)) if x!=y]
assert len(diff)==3,diff
m=dict(status='in-progress',optimization='R3d sine products reuse outer scratch registers; shared product selector uses a fixed branch',build=str(b.relative_to(r)),candidate_sha256=hashlib.sha256(c).hexdigest(),baseline_sha256=hashlib.sha256(a).hexdigest(),equal_layout_difference_offsets=diff,arithmetic_oracle='tmp/step5/c4-sine-r3d-physics-oracle-a500-1/result.json',disabled_equivalence='manifest/step5-c4-r3d-disabled.json',exact_state='manifest/step5-c4-sine-r3d-v1-ab-a500-baseline-render-candidate.json',plan_target_saved_cycles=13000)
files=['FerrariFormulaOne_Coarse200MulInline.s','FerrariFormulaOne_Wide000.s','FerrariFormulaOne_CoarseInstall.s']
m['source_sha256']={f:hashlib.sha256((r.parents[1]/'Games'/f).read_bytes()).hexdigest() for f in files}
assert read(m['disabled_equivalence'])['status']=='passed'
for name,digest in read(m['arithmetic_oracle'])['expected']['source_sha256'].items():assert hashlib.sha256((r.parents[1]/'Games'/name).read_bytes()).hexdigest()==digest
for arm,key in [('baseline-render','control'),('candidate','candidate')]:
 j=read(f'tmp/step5/c4-sine-r3d-v1-fullloop-a500-{arm}/percar.json')
 m['logic_cycles_'+key]=sum(v for k,v in j['segment_totals_exact'].items() if k!='post')
m['logic_saved_cycles']=m['logic_cycles_control']-m['logic_cycles_candidate'];m['logic_saved_ms']=m['logic_saved_cycles']/7093.79
m['plan_target_met']=m['logic_saved_cycles']>=13000
mp='manifest/step5-c4-sine-r3d-validation.json'
assert read(m['exact_state'])['status']=='passed'
assert read(m['arithmetic_oracle'])['status']=='passed'
assert read('manifest/step5-c4-sine-r3d-images.json')['status']=='passed'
assert read('manifest/step5-c4-r2-frame-padding.json')['status']=='passed'
m['measurements']={}
for scene,part,suffix in [('normal','ab','fps300'),('grid','start-grid-center','heavy-fps300'),('dense','heavy-v2','heavy-fps300')]:
 rows={};reports=[]
 for arm in (('baseline-render','candidate') if scene=='normal' else ('baseline-render','candidate','native')):
  p=f'tmp/step5/c4-sine-r3d-v1-{part}-a500-{arm}-{suffix}/result.json';j=read(p);reports.append(j)
  assert j['presentations']==300 and j['untraced'] and j['warp_start']==j['warp_end']=='warp=0'
  assert j['start']['error']==j['end']['error']==0
  if scene!='normal':assert j['restoration_exact'] and j['all_opponents_drawn'] and j['end']['HeavyIncomplete']==0
  rows[arm]=dict(fps=j['presented_fps'],evidence=p)
 assert rows['candidate']['fps']>=rows['baseline-render']['fps']
 assert rows['candidate']['fps']>=read('manifest/step5-c4-mul-r3c-validation.json')['measurements'][scene]['candidate']['fps']
 if scene!='dense':assert rows['candidate']['fps']>=3.494
 if scene=='grid':assert rows['candidate']['fps']>=rows['native']['fps']
 if scene!='normal':assert len({j['fixed_scene_hex'] for j in reports})==1
 m['measurements'][scene]=rows
p='tmp/step5/c4-sine-r3d-v1-ab-a500-candidate-elapsed/result.json';j=read(p);assert j['status']=='passed'
fps=(j['end']['B8Frames']-j['start']['B8Frames'])/j['elapsed_seconds'];assert fps>=3.6
m['elapsed']=dict(evidence=p,fps=fps,error_percent=j['error_percent'])
m['images']='manifest/step5-c4-sine-r3d-images.json';m['image_padding_audit']='manifest/step5-c4-r2-frame-padding.json'
m['exit']='tmp/step5/c4-sine-r3d-v1-ab-a500-exit/result.json';assert read(m['exit'])['status']=='passed'
m['legacy_exact']='manifest/step5-c4-sine-r3d-v1-default-validation.json';assert read(m['legacy_exact'])['status']=='passed'
m['profiles']={}
for arm in ('baseline-render','candidate'):
 p=f'tmp/step5/c4-sine-r3d-v1-fullloop-a500-{arm}';audit=read(p+'/audit.json')
 assert audit['status']=='passed' and audit['analyzer_totals_agree'] and audit['normalization']['all_costs_and_registers_unchanged']
 assert audit['dma']['fields']==100 and not audit['dma']['bad']
 assert (r/p/'trace-archives.json').exists();m['profiles'][arm]=p
m['status']='passed';m['disabled_candidate_sha256']='c9c0543a3d95b6f445f6e7036de239a467db0372d454f3ac53840317b82beebf'
m['p01_same_workload_passed']=m['measurements']['dense']['candidate']['fps']>=m['measurements']['dense']['native']['fps']
m['further_work_required']=m['measurements']['dense']['candidate']['fps']<3.33
(r/mp).write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
