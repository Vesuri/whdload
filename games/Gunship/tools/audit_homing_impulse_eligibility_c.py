"""Check envelope eligibility against assembled native RNG adapter, all byte draws."""
from unicorn_b import *
import json
base=0x100000;l=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()));player=0x300000;packet=0x301000;rng=0x302000
for draw in range(256):c.put(rng+8*draw,bytes.fromhex('303c')+struct.pack('>H',draw)+bytes.fromhex('4e75'))
rows=json.loads((root/'tmp/c/homing-impulse-envelope.json').read_text());cases=0
for row in rows:
 c.put(player,bytes.fromhex(row['eligibility_player']));seen=set()
 # These captures admit only pitch or no disturbance, so one exhaustive
 # byte sweep covers every admitted packet, without assuming RNG correlations.
 assert row['roll_options']==row['heading_options']==[0]
 for draw in range(256):
  c.put(packet,bytes(10));c.rw(1,player);c.rw(2,packet);c.rw(3,rng+8*draw);c.rw(8,0x8f000);c.call(base+sym('world_motion_impulses'))
  assert c.rr(18)==0x90000 and c.rr(9)==0
  seen.add(struct.unpack('>hhh',c.get(packet+4,6)));cases+=1
  assert c.get(player,86)==bytes.fromhex(row['eligibility_player'])
 assert seen=={tuple(v['impulses']) for v in row['variants']},(row['world'],seen)
 assert row['all_match']
report=dict(status='passed',native_adapter_calls=cases,worlds=len(rows),admitted_packets=sum(len(r['variants']) for r in rows),candidate_sets_stable=True,scope='Captured neutral-control flight; only pitch/no-impulse eligibility, not every damage/configuration state')
(root/'tmp/c/homing-impulse-eligibility-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
