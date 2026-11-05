from pathlib import Path
import sys,json,subprocess
r=Path(__file__).resolve().parents[1];paths=[r/f'tmp/step5/c4-q03-render-profile-a1200-fast-h4-matched-{a}' for a in ['control','candidate']]
for p in paths:
 for script in ['analyze_h4_render.py','analyze_h3_road.py']:
  subprocess.run([sys.executable,str(r/'tools'/script),str(p)],check=True,stdout=subprocess.DEVNULL)
a,b=[json.loads((p/'road-analysis.json').read_text()) for p in paths];n=min(len(a['draws']),len(b['draws']));assert n>0
register_diff=[]
for i,(x,y) in enumerate(zip(a['draws'],b['draws'])):
 for k in ['planes','clip_shift','clear_dest']:assert x[k]==y[k],(i,k)
 assert [v[:15] for v in x['road_regs']]==[v[:15] for v in y['road_regs']],(i,'projection registers')
 if x['road_regs']!=y['road_regs']:register_diff.append(dict(draw=i,control=x['road_regs'],candidate=y['road_regs']))
def compact(x):
 seq=[]
 for row in x['display_fields'][1:-1]:
  h=row['pixel_dma_sha256']
  if not seq or seq[-1]!=h:seq.append(h)
 return seq
x,y=compact(a),compact(b)
# A field window can start or end in different frames after the reschedule.
# Keep all interior transitions and require a contiguous exact overlap.
common=[]
for i in range(len(x)):
 for j in range(len(y)):
  k=0
  while i+k<len(x) and j+k<len(y) and x[i+k]==y[j+k]:k+=1
  if k>len(common):common=x[i:i+k];alignment=(i,j)
assert alignment == (0,0) and len(common)==min(len(x),len(y)),(len(x),len(y),len(common),alignment)
stats=[json.loads((p/'render-analysis.json').read_text()) for p in paths]
out=dict(status='passed',matched_draws=n,mean_draw_ms={arm:sum(s['draw_ms'][:n])/n for arm,s in zip(['control','candidate'],stats)},stages={arm:{k:sum(v.get(k,0) for v in s['per_draw_stages_ms'][:n])/n for k in s['stage_ms_per_draw']} for arm,s in zip(['control','candidate'],stats)},whole_loop_mean_interval_ms={arm:sum(s['draw_interval_ms'][:n])/n for arm,s in zip(['control','candidate'],stats)},exact_planes_clipping_destinations=True,projection_d0_d7_a0_a6_exact=True,raw_sr_note='Observer newcpu.cpp copies regs.sr without MakeSR; CCR reads materialize lazy flags only in the candidate. Raw trace low SR bits are not an architectural CCR oracle. Native 6b372 overwrites NZVC immediately; register/semantic/pixel gates unchanged.',register_differences=register_diff,intermediate_field_pixels=dict(compact_fields=[len(x),len(y)],exact_contiguous_common=len(common),alignment=alignment),safe_transitions=b['transitions'],display_banks=b['display_banks'])
(r/'manifest/render-h4-matched-profile.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['register_differences','safe_transitions']},indent=2));print('Register differences',len(register_diff))
