"""Replay recorded selection candidates and isolate pixel/candidate dependencies."""
from unicorn_b import *
import json,sys
base=0x100000
listing=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
live=(build/'selector-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
reports=[]
for folder in map(Path,sys.argv[1:]):
 for world in range(20,47):
  states=[];outputs=[]
  for tick in (world,world+1):
   d=folder/f'world-{tick}';a=(d/'before-target-arena.bin').read_bytes();h=struct.unpack_from('>9I',a,ls('RT_HUNKS'))
   post=(d/'arena.bin').read_bytes();outputs.append(post[ls('RT_TARGET')+sym('WT_STATE'):ls('RT_TARGET')+sym('WT_STATE')+sym('WT_STATE_SIZE')])
   states.append(a[ls('RT_TARGET'):ls('RT_TARGET')+sym('WT_SIZE')])
  c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
  for i in (0,2,4,5,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
  work=0x300000
  def call(name,rs):
   for r,v in rs.items():c.rw(r,v)
   c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000 and c.rr(9)==0
  call('target_select_prepare',{1:h[0],2:h[6],3:work})
  originals={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)}
  rows=[]
  for candidate in (0,1):
   for pixel in (0,1):
    c.put(work+sym('WT_STATE'),states[candidate][sym('WT_STATE'):])
    c.put(work+sym('WT_PIXELS'),states[pixel][sym('WT_PIXELS'):sym('WT_PIXELS')+6])
    call('target_select_step',{1:work,2:work+sym('WT_PIXELS'),3:work+sym('WT_PALETTE')+24})
    out=c.get(work+sym('WT_STATE'),sym('WT_STATE_SIZE'))
    expected=outputs[candidate]
    if candidate==pixel:assert out==expected,(world,candidate,[(i,x,y) for i,(x,y) in enumerate(zip(out,expected)) if x!=y])
    rows.append(dict(candidate_world=world+candidate,pixel_world=world+pixel,status=out[0],selection=out[4:8].hex(),selectors=out[0x6c:0x78].hex(),pixels=states[pixel][sym('WT_PIXELS'):sym('WT_PIXELS')+6].hex(),input_count=int.from_bytes(states[candidate][sym('WT_STATE')+2:sym('WT_STATE')+4],'big'),input_selectors=states[candidate][sym('WT_STATE')+0x6c:sym('WT_STATE')+0x78].hex(),count=int.from_bytes(out[2:4],'big')))
    assert all(c.get(h[i],len(v))==v for i,v in originals.items())
  reports.append(dict(run=folder.name,world=world,variants=rows,native_memory_unchanged=True));c.close()
print(json.dumps(dict(pairs=len(reports),native_replays=2*len(reports),crossed_pixel_replays=2*len(reports),native_memory_unchanged=True)));(root/'tmp/c/homing-selection-isolation.json').write_text(json.dumps(reports,indent=2)+'\n')
