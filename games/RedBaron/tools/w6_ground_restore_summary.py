"""Check scoped post-fix ground evidence without filtering raw state."""
import json,sys
from pathlib import Path
sys.path.insert(0,'tools')
from world_comparison import load
from presentation_state import symbol
from render_mutations import Snapshot
from pose_history import registry
p=Path('tmp/prof/w6-ground-restore-030-v2');q=p.with_name('w6-ground-restore-none-030')
a=load(p);b=load(q);d=json.loads((p/'heap-inventory.json').read_text());h3=a[1]['h3']
assert a[0]['slave_sha256']==b[0]['slave_sha256']==d['sha256']
assert len(d['rows'])==len(a[1]['frames'])==len(b[1]['frames'])==15
assert not d['initial']['player']['changed_bytes'] and not d['initial']['h3']['changed_bytes']
assert not d['initial']['allocation_differences'] and not d['initial']['right_only_allocations']
assert all(s['changes']['changed_bytes']==0 for s in d['initial']['segments'])
flags=0;slots=set();sound_offsets=set()
for row,lf,rf in zip(d['rows'],a[1]['frames'],b[1]['frames']):
 l=Snapshot(p,lf['banks']);r=Snapshot(q,rf['banks'])
 assert not row['player']['changed_bytes'] and not row['object_prefix_differences']
 assert all(row[k] for k in ['player_pointer_equal','camera_equal','registry_equal','display_list_equal','lifecycle_equal'])
 for name,size in [('time_keys_bitmap',128),('time_keys_commands',516),('time_keys_consumed',8)]:
  assert l.read(a[3]+symbol(a[4],name),size)==r.read(b[3]+symbol(b[4],name),size)
 for ptr in registry(l.read,h3):
  if l.read(ptr,1)[0]&64:continue
  assert l.read(ptr+36,1)==r.read(ptr+36,1);flags+=1
 for alloc in row['allocation_differences']:
  assert alloc['size']==392 and not alloc.get('layout_changed')
  matches=[i for i in range(3) if int.from_bytes(l.read(h3+0xa184+4*i,4),'big')==alloc['address']+8]
  assert len(matches)==1;slots.add(matches[0])
  for v in alloc['changes']['ranges']:sound_offsets.update(range(v['start']-8,v['end']-8))
 assert not row['right_only_allocations']
assert all(v['exact_funding'] for v in d['funding'].values())
result=dict(sha256=d['sha256'],boundaries=15,player_bytes_per_boundary=280,registered_flag_bytes=flags,input_states_equal=True,sound_slots=sorted(slots),sound_payload_offsets=sorted(sound_offsets),funding=d['funding'],scope='Scoped equality only; raw globals and sound behavior remain unclosed.')
(p/'ground-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
