"""Recheck retained acceptance evidence before closing P01/P02 (not full C4 release)."""
from pathlib import Path
import json,hashlib,subprocess
from PIL import Image
r=Path(__file__).resolve().parents[1];root=r.parent.parent
read=lambda p:json.loads((r/p).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stages=['wait-r1','colour-r2','divide-r3a','rotate-r3b','mul-r3c','sine-r3d','native-frame-r3e','wait-direct-r3f','divide-frame-r3g']
report={'status':'in-progress','scope':'C4-P01 and C4-P02 performance closure only; Q01/Q02/Q03/T01 and production acceptance remain separate','stages':{}}
previous=None;previous_fps=None;fixed_scenes={}
for stage in stages:
 mp=f'manifest/step5-c4-{stage}-validation.json';m=read(mp);assert m['status']=='passed',stage
 commit=m['commit'];raw=subprocess.check_output(['git','cat-file','commit',commit],cwd=root,text=True)
 for who in ('author','committer'):assert who+' Vesa Halttunen <vesuri@jormas.com>' in raw
 assert '\ngpgsig ' not in raw and 'Co-Authored-By:' not in raw
 subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=root,check=True)
 if previous:subprocess.run(['git','merge-base','--is-ancestor',previous,commit],cwd=root,check=True)
 previous=commit
 for file,digest in m.get('source_sha256',{}).items():
  data=subprocess.check_output(['git','show',commit+':Games/'+file],cwd=root)
  assert hashlib.sha256(data).hexdigest()==digest,(stage,file)
 state=read(m['exact_state']);assert state['status']=='passed' and state['steps']==100 and len(state['blocks'])==27 and not state['failures']
 legacy=read(m['legacy_exact']);assert legacy['status']=='passed' and set(legacy['profiles'])=={'a500','a500-fast','a1200','a1200-fast'}
 assert all(x['passed'] and not x['failures'] for x in legacy['profiles'].values())
 for arm,path in m['profiles'].items():
  a=read(path+'/audit.json');assert a['status']=='passed' and a['analyzer_totals_agree'] and a['normalization']['all_costs_and_registers_unchanged']
  assert a['dma']['fields']==100 and not a['dma']['bad']
  assert (r/path/'trace-archives.json').exists()
 measured={}
 for scene,arms in m['measurements'].items():
  scene_reports=[]
  for arm,row in arms.items():
   j=read(row['evidence']);assert j['presentations']==300 and j['untraced'] and j['warp_start']==j['warp_end']=='warp=0'
   assert j['start']['error']==j['end']['error']==0
   assert abs(j['presented_fps']-300/j['elapsed_seconds'])<1e-12
   assert row['fps']==j['presented_fps']
   if scene!='normal':assert j['restoration_exact'] and j['all_opponents_drawn'] and j['end']['HeavyIncomplete']==0
   scene_reports.append(j)
  assert arms['candidate']['fps']>=arms['baseline-render']['fps'],(stage,scene)
  if previous_fps is not None:assert arms['candidate']['fps']>=previous_fps[scene],(stage,scene,'previous accepted stage')
  if scene=='grid':assert arms['candidate']['fps']>=arms['native']['fps']
  if scene!='dense':assert arms['candidate']['fps']>=3.494
  if scene!='normal':assert len({j['fixed_scene_hex'] for j in scene_reports})==1
  if scene!='normal':
   fixed_scenes.setdefault(scene,scene_reports[0]['fixed_scene_hex'])
   assert fixed_scenes[scene]==scene_reports[0]['fixed_scene_hex'],(stage,scene,'changed workload')
  measured[scene]=arms['candidate']['fps']
 previous_fps=measured
 im=read(m['images']);assert im['status']=='passed'
 assert len(im['workloads'])==3
 frames=0
 for scene,item in im['workloads'].items():
  a,b=[read(p) for p in item['arms']];assert a['frames']==b['frames'] and len(a['frames'])==10 and a['error']==b['error']==0
  for p,j in zip(item['arms'],(a,b)):
   for f in j['frames']:
    image=Image.open((r/p).parent/f"frame-{f['update']}.png").convert('RGB')
    assert list(image.size)==list(f['size']) and hashlib.sha256(image.tobytes()).hexdigest()==f['pixel_sha256']
  frames+=len(a['frames'])
 e=read(m['elapsed']['evidence']);assert e['status']=='passed' and e['simulated_seconds']==60 and e['error_percent']<=1
 assert all(b-a==600 for a,b in zip(e['clocks_start'],e['clocks_end']))
 assert e['context'][7]==200
 assert (e['end']['B8Frames']-e['start']['B8Frames'])/e['elapsed_seconds']>=3.6
 assert read(m['exit'])['status']=='passed'
 report['stages'][stage]=dict(commit=commit,evidence=mp,exact_updates=100,semantic_blocks=27,identical_full_frames=frames,workload_fps=measured,elapsed_error_percent=e['error_percent'])
final=read('manifest/step5-c4-divide-frame-r3g-validation.json')
assert final['p01_same_workload_passed'] and final['dense_target_reached']
assert final['measurements']['dense']['candidate']['fps']>=max(3.33,final['measurements']['dense']['native']['fps'])
assert final['measurements']['grid']['candidate']['fps']>=final['measurements']['grid']['native']['fps']
for file,digest in final['source_sha256'].items():assert sha(root/'Games'/file)==digest
assert sha(root/'Games/FerrariFormulaOne_WHD.s')=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
assert sha(r/final['build']/'candidate.slave')==final['candidate_sha256']
oracle=read(final['arithmetic_oracle']);assert oracle['status']=='passed' and oracle['expected']['ccr_values']==32
assert oracle['probe']==dict(installed=1,checked=oracle['expected']['comparisons'],error=0)
assert 'SP preservation' in oracle['expected']['checks']
for file,digest in oracle['expected']['source_sha256'].items():assert sha(root/'Games'/file)==digest
for file,digest in read(final['unchanged_prior_sources'])['source_sha256'].items():assert sha(root/'Games'/file)==digest
exit_report=read(final['exit']);assert exit_report['direct_wait_sites_confirmed']==exit_report['direct_wait_sites_restored']==20 and exit_report['ledger_restore_checked_words']>0
choice=read('manifest/step5-c4-open-cases.json')['p01_gate_decision'];assert choice['user_choice']=='Same-workload no-regression versus legacy' and not choice['fallback']
boot=(r/final['build']/'fine.s').read_text()
assert 'selection_custom2: dc.l 0' in boot and 'selection_path: dc.l 0' in boot
profile=(root/'Games/FerrariFormulaOne_Profile.s').read_text()
assert 'tst.l   d0\n        beq.b   .legacy' in profile
assert '.legacy:\n        moveq   #0,d0' in profile
install=(root/'Games/FerrariFormulaOne_CoarseInstall.s').read_text()
assert 'move.l selection_path(pc),d0\n cmpi.l #1,d0\n bne.w done' in install
report['default_off_sources']={n:sha(root/'Games'/n) for n in ('FerrariFormulaOne_Profile.s','FerrariFormulaOne_CoarseInstall.s')}
report.update(status='passed',final_evidence='manifest/step5-c4-divide-frame-r3g-validation.json',user_gate=choice,original_slave_unchanged=True,simulation_ms=200,default_off=True,r3_stopped_at_target=True)
(r/'manifest/step5-c4-performance-closure-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
