from pathlib import Path
import json,hashlib,re,struct
r=Path(__file__).resolve().parents[1]
def read(p):return json.loads((r/p).read_text())
b=r/'tmp/build/step5-c4-divide-frame-r3g-v1-ab/000'
c=(b/'candidate.slave').read_bytes();a=(b/'baseline-render.slave').read_bytes()
assert len(a)==len(c)
diff=[i for i,(x,y) in enumerate(zip(a,c)) if x!=y]
listing=(b/'fine.list').read_text();symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
host_size=len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes()[32:-4]);gate=32+host_size+symbols['FF1C4DivideShortGate']
assert diff and set(diff)<=set(range(gate,gate+4)),diff
assert a[gate:gate+4]==bytes.fromhex('2f022400')
assert c[gate:gate+2]==bytes.fromhex('6000') and struct.unpack_from('>h',c,gate+2)[0]==symbols['FF1C4DivideShortFast']-symbols['FF1C4DivideShortGate']-2
m=dict(status='in-progress',optimization='R3g short positive division guard and quotient/remainder unpack without D2 save frames',build=str(b.relative_to(r)),candidate_sha256=hashlib.sha256(c).hexdigest(),baseline_sha256=hashlib.sha256(a).hexdigest(),equal_layout_difference_offsets=diff,disabled_equivalence='manifest/step5-c4-r3g-disabled.json',exact_state='manifest/step5-c4-divide-frame-r3g-v1-ab-a500-baseline-render-candidate.json',plan_target_saved_cycles=None)
files=['FerrariFormulaOne_Coarse200Divide.s']
m['source_sha256']={f:hashlib.sha256((r.parents[1]/'Games'/f).read_bytes()).hexdigest() for f in files}
assert read(m['disabled_equivalence'])['status']=='passed'
m['unchanged_prior_sources']='manifest/step5-c4-wait-direct-r3f-validation.json'
for name,digest in read(m['unchanged_prior_sources'])['source_sha256'].items():assert hashlib.sha256((r.parents[1]/'Games'/name).read_bytes()).hexdigest()==digest
for arm,key in [('baseline-render','control'),('candidate','candidate')]:
 j=read(f'tmp/step5/c4-divide-frame-r3g-v1-fullloop-a500-{arm}/percar.json')
 m['logic_cycles_'+key]=sum(v for k,v in j['segment_totals_exact'].items() if k!='post')
m['logic_saved_cycles']=m['logic_cycles_control']-m['logic_cycles_candidate'];m['logic_saved_ms']=m['logic_saved_cycles']/7093.79
m['plan_target_met']=None
assert m['logic_saved_cycles']>0
mp='manifest/step5-c4-divide-frame-r3g-validation.json'
assert read(m['exact_state'])['status']=='passed'
assert read('manifest/step5-c4-divide-frame-r3g-images.json')['status']=='passed'
assert read('manifest/step5-c4-r2-frame-padding.json')['status']=='passed'
m['measurements']={}
for scene,part,suffix in [('normal','ab','fps300'),('grid','start-grid-center','heavy-fps300'),('dense','heavy-v2','heavy-fps300')]:
 rows={};reports=[]
 for arm in (('baseline-render','candidate') if scene=='normal' else ('baseline-render','candidate','native')):
  p=f'tmp/step5/c4-divide-frame-r3g-v1-{part}-a500-{arm}-{suffix}/result.json';j=read(p);reports.append(j)
  assert j['presentations']==300 and j['untraced'] and j['warp_start']==j['warp_end']=='warp=0'
  assert j['start']['error']==j['end']['error']==0
  if scene!='normal':assert j['restoration_exact'] and j['all_opponents_drawn'] and j['end']['HeavyIncomplete']==0
  rows[arm]=dict(fps=j['presented_fps'],evidence=p)
 assert rows['candidate']['fps']>=rows['baseline-render']['fps']
 assert rows['candidate']['fps']>=read('manifest/step5-c4-wait-direct-r3f-validation.json')['measurements'][scene]['candidate']['fps']
 if scene!='dense':assert rows['candidate']['fps']>=3.494
 if scene=='grid':assert rows['candidate']['fps']>=rows['native']['fps']
 if scene!='normal':assert len({j['fixed_scene_hex'] for j in reports})==1
 m['measurements'][scene]=rows
p='tmp/step5/c4-divide-frame-r3g-v1-ab-a500-candidate-elapsed/result.json';j=read(p);assert j['status']=='passed'
fps=(j['end']['B8Frames']-j['start']['B8Frames'])/j['elapsed_seconds'];assert fps>=3.6
m['elapsed']=dict(evidence=p,fps=fps,error_percent=j['error_percent'])
m['images']='manifest/step5-c4-divide-frame-r3g-images.json';m['image_padding_audit']='manifest/step5-c4-r2-frame-padding.json'
m['exit']='tmp/step5/c4-divide-frame-r3g-v1-ab-a500-exit/result.json';assert read(m['exit'])['status']=='passed'
assert read(m['exit'])['ledger_restore_checked_words']>0
assert read(m['exit'])['native_multiply_sites_confirmed'] and 'native_multiply_sites' in read(m['exit'])['restored_helpers']
m['legacy_exact']='manifest/step5-c4-divide-frame-r3g-v1-default-validation.json';assert read(m['legacy_exact'])['status']=='passed'
m['profiles']={}
for arm in ('baseline-render','candidate'):
 p=f'tmp/step5/c4-divide-frame-r3g-v1-fullloop-a500-{arm}';audit=read(p+'/audit.json')
 assert audit['status']=='passed' and audit['analyzer_totals_agree'] and audit['normalization']['all_costs_and_registers_unchanged']
 assert audit['dma']['fields']==100 and not audit['dma']['bad']
 assert (r/p/'trace-archives.json').exists();m['profiles'][arm]=p
assert read(m['exit'])['direct_wait_sites_confirmed']==read(m['exit'])['direct_wait_sites_restored']==20
m['direct_sites']='manifest/step5-c4-wait-direct-planning.json'
m['arithmetic_oracle']='tmp/step5/c4-divide-frame-r3g-v1-oracle-a500-0/result.json'
oracle=read(m['arithmetic_oracle']);assert oracle['status']=='passed'
for name,digest in oracle['expected']['source_sha256'].items():assert hashlib.sha256((r.parents[1]/'Games'/name).read_bytes()).hexdigest()==digest
m['status']='passed';m['disabled_candidate_sha256']='085fe03dca73c7969448eb6410a896d41c52449b730232c004013001b32212a8'
m['p01_same_workload_passed']=m['measurements']['dense']['candidate']['fps']>=m['measurements']['dense']['native']['fps']
m['dense_target_reached']=m['measurements']['dense']['candidate']['fps']>=3.33
m['further_work_required']=m['measurements']['dense']['candidate']['fps']<3.33
(r/mp).write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
