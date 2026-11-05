"""Summarize retained equal-tick evidence; never remove raw differences."""
import json,sys
from pathlib import Path
sys.path.insert(0,'tools')
from render_mutations import Snapshot
from shape_lease import state
from shape_selection import selection
p=Path('tmp/prof/w6-shape-replay-normal-030');q=Path('tmp/prof/w6-shape-replay-none-030')
d=json.loads((p/'heap-inventory.json').read_text());lm=json.loads((p/'poses.json').read_text());rm=json.loads((q/'poses.json').read_text());h3=lm['h3']
assert len(d['rows'])==len(lm['frames'])==len(rm['frames'])==40
assert d['initial']['h3']['changed_bytes']==d['initial']['player']['changed_bytes']==0
assert not d['initial']['allocation_differences'] and not d['initial']['right_only_allocations']
assert all(s['changes']['changed_bytes']==0 for s in d['initial']['segments'])
contexts=set();shape_indices=set();extra_ticks=[];prefixes=0
for row,lf,rf in zip(d['rows'],lm['frames'],rm['frames']):
 l=Snapshot(p,lf['banks']);r=Snapshot(q,rf['banks'])
 assert all(row[k] for k in ['registry_equal','display_list_equal','camera_equal','lifecycle_equal','player_pointer_equal'])
 assert row['player']['changed_bytes']==0 and not row['object_prefix_differences']
 prefixes+=row['registered_objects']
 assert state(l.read,h3)==state(r.read,h3)
 assert selection(l.read,h3)==selection(r.read,h3)
 shape_indices.add(selection(l.read,h3)['index'])
 for a in row['allocation_differences']:
  if a.get('layout_changed'):
   assert a['size']==1808;extra_ticks.append(row['tick']);continue
  assert a['size']==392 and [(x['start'],x['end']) for x in a['changes']['ranges']]==[(353,354)]
  slots=[i for i in range(3) if int.from_bytes(l.read(h3+0xa184+4*i,4),'big')==a['address']+8]
  assert len(slots)==1
  assert l.read(h3+0xa184+4*slots[0],4)==r.read(h3+0xa184+4*slots[0],4)
  contexts.add(slots[0])
 assert not row['right_only_allocations']
result=dict(sha256=d['sha256'],boundaries=40,matching_registered_prefixes=prefixes,matching_player_bytes_per_boundary=280,shape_indices=sorted(shape_indices),shape_bytes_compared=8*40,sound_context_slots=sorted(contexts),sound_payload_changed_offset=345,drawing_only_allocation_ticks=extra_ticks,final_h3_changed_bytes=d['rows'][-1]['h3']['changed_bytes'],final_segment_changed_bytes=[s['changes']['changed_bytes'] for s in d['rows'][-1]['segments']],funding=d['funding'],limitation='Raw differences retained. No full-global, sound-event, combat or capacity acceptance.')
(p/'replay-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
