from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1]
def read(p):return json.loads((r/p).read_text())
b=r/'tmp/build/step5-c4-wait-direct-r3f-v1-ab/000'
c=(b/'candidate.slave').read_bytes();a=(b/'baseline-render.slave').read_bytes()
assert len(a)==len(c)
diff=[i for i,(x,y) in enumerate(zip(a,c)) if x!=y]
assert len(diff)==1,diff
m=dict(status='in-progress',optimization='R3f direct routing of 20 measured native WaitBlit JSR operands to the unchanged R1 helper',build=str(b.relative_to(r)),candidate_sha256=hashlib.sha256(c).hexdigest(),baseline_sha256=hashlib.sha256(a).hexdigest(),equal_layout_difference_offsets=diff,disabled_equivalence='manifest/step5-c4-r3f-disabled.json',exact_state='manifest/step5-c4-wait-direct-r3f-v1-ab-a500-baseline-render-candidate.json',plan_target_saved_cycles=None)
files=['FerrariFormulaOne_Coarse200Complete.s','FerrariFormulaOne_Coarse200WaitDirect.s']
m['source_sha256']={f:hashlib.sha256((r.parents[1]/'Games'/f).read_bytes()).hexdigest() for f in files}
assert read(m['disabled_equivalence'])['status']=='passed'
m['unchanged_arithmetic']='manifest/step5-c4-native-frame-r3e-validation.json'
for name,digest in read(m['unchanged_arithmetic'])['source_sha256'].items():assert hashlib.sha256((r.parents[1]/'Games'/name).read_bytes()).hexdigest()==digest
for arm,key in [('baseline-render','control'),('candidate','candidate')]:
 j=read(f'tmp/step5/c4-wait-direct-r3f-v1-fullloop-a500-{arm}/percar.json')
 m['logic_cycles_'+key]=sum(v for k,v in j['segment_totals_exact'].items() if k!='post')
m['logic_saved_cycles']=m['logic_cycles_control']-m['logic_cycles_candidate'];m['logic_saved_ms']=m['logic_saved_cycles']/7093.79
m['plan_target_met']=None
# Render-call routing need not reduce logic-only time; untraced workload FPS is authoritative.
mp='manifest/step5-c4-wait-direct-r3f-validation.json'
assert read(m['exact_state'])['status']=='passed'
assert read('manifest/step5-c4-wait-direct-r3f-images.json')['status']=='passed'
assert read('manifest/step5-c4-r2-frame-padding.json')['status']=='passed'
m['measurements']={}
for scene,part,suffix in [('normal','ab','fps300'),('grid','start-grid-center','heavy-fps300'),('dense','heavy-v2','heavy-fps300')]:
 rows={};reports=[]
 for arm in (('baseline-render','candidate') if scene=='normal' else ('baseline-render','candidate','native')):
  p=f'tmp/step5/c4-wait-direct-r3f-v1-{part}-a500-{arm}-{suffix}/result.json';j=read(p);reports.append(j)
  assert j['presentations']==300 and j['untraced'] and j['warp_start']==j['warp_end']=='warp=0'
  assert j['start']['error']==j['end']['error']==0
  if scene!='normal':assert j['restoration_exact'] and j['all_opponents_drawn'] and j['end']['HeavyIncomplete']==0
  rows[arm]=dict(fps=j['presented_fps'],evidence=p)
 assert rows['candidate']['fps']>=rows['baseline-render']['fps']
 assert rows['candidate']['fps']>=read('manifest/step5-c4-native-frame-r3e-validation.json')['measurements'][scene]['candidate']['fps']
 if scene!='dense':assert rows['candidate']['fps']>=3.494
 if scene=='grid':assert rows['candidate']['fps']>=rows['native']['fps']
 if scene!='normal':assert len({j['fixed_scene_hex'] for j in reports})==1
 m['measurements'][scene]=rows
p='tmp/step5/c4-wait-direct-r3f-v1-ab-a500-candidate-elapsed/result.json';j=read(p);assert j['status']=='passed'
fps=(j['end']['B8Frames']-j['start']['B8Frames'])/j['elapsed_seconds'];assert fps>=3.6
m['elapsed']=dict(evidence=p,fps=fps,error_percent=j['error_percent'])
m['images']='manifest/step5-c4-wait-direct-r3f-images.json';m['image_padding_audit']='manifest/step5-c4-r2-frame-padding.json'
m['exit']='tmp/step5/c4-wait-direct-r3f-v1-ab-a500-exit/result.json';assert read(m['exit'])['status']=='passed'
assert read(m['exit'])['ledger_restore_checked_words']>0
assert read(m['exit'])['native_multiply_sites_confirmed'] and 'native_multiply_sites' in read(m['exit'])['restored_helpers']
m['legacy_exact']='manifest/step5-c4-wait-direct-r3f-v1-default-validation.json';assert read(m['legacy_exact'])['status']=='passed'
m['profiles']={}
for arm in ('baseline-render','candidate'):
 p=f'tmp/step5/c4-wait-direct-r3f-v1-fullloop-a500-{arm}';audit=read(p+'/audit.json')
 assert audit['status']=='passed' and audit['analyzer_totals_agree'] and audit['normalization']['all_costs_and_registers_unchanged']
 assert audit['dma']['fields']==100 and not audit['dma']['bad']
 assert (r/p/'trace-archives.json').exists();m['profiles'][arm]=p
assert read(m['exit'])['direct_wait_sites_confirmed']==read(m['exit'])['direct_wait_sites_restored']==20
m['direct_sites']='manifest/step5-c4-wait-direct-planning.json'
m['status']='passed';m['disabled_candidate_sha256']='baf8e551b5a564380f154c1cc5ae955256da99d1b2b67b02a12c44701d2072ab'
m['p01_same_workload_passed']=m['measurements']['dense']['candidate']['fps']>=m['measurements']['dense']['native']['fps']
m['dense_target_reached']=m['measurements']['dense']['candidate']['fps']>=3.33
m['further_work_required']=m['measurements']['dense']['candidate']['fps']<3.33
(r/mp).write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
