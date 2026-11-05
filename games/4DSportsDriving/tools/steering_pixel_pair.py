#!/usr/bin/env python3
"""Paired steering/control image evidence; reject mismatched pre-edge runs."""
import argparse,hashlib,io,json,struct,re
from pathlib import Path
from PIL import Image,ImageChops
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('steering',type=Path);p.add_argument('control',type=Path);a=p.parse_args()
left,right=a.steering,a.control
m,n=[json.loads((v/'anchor.json').read_text()) for v in (left,right)]
for key in ('settings','game_base','data_base','frame','simulation_tick','first_driving_field','input_events'):
 assert m[key]==n[key],(key,m[key],n[key])
lb,rb=[(v/'slave.slave').read_bytes() for v in (left,right)]
pattern=bytes.fromhex('004f00cf004e00ce');assert lb.count(pattern)==1
at=lb.index(pattern);diff=[i for i,(x,y) in enumerate(zip(lb,rb)) if x!=y]
assert len(lb)==len(rb) and diff==[at+1,at+5] and all(lb[i]^rb[i]==128 for i in diff),diff
assert (left/'state.bin').read_bytes()==(right/'state.bin').read_bytes(),'Initial game data differs'
lat=json.loads((left/'input-edge-latency.json').read_text());edge=lat['edges'][0]['trace'];request=edge['request_field']
assert lat['controls']=='steering'
end=(right/'end-memory.bin').read_bytes()
listing=(right/'slave.lst').read_text(encoding='latin1')
symbols={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',listing,re.M)}
base=n['marker']+8-symbols['tape_game']-n['memory_base'];off=base+symbols['tape_edge_phase']
assert struct.unpack_from('>H',end,off)[0]==4
control_events=[struct.unpack_from('>II4H',end,off+4+i*16) for i in range(4)]
assert [r[2] for r in control_events]==[0xcf,0xcf,0xce,0xce]
assert all(r[3]==0 for r in control_events)
assert control_events[0][0]==lat['edges'][0]['request_clock']
aa=n['data_base']+0x7ffe-n['memory_base'];count=struct.unpack_from('>H',end,aa-0x1738)[0]
ptr=struct.unpack_from('>I',end,aa-0x1770)[0]-n['memory_base'];history=end[ptr:ptr+count]
assert history and 1 in history and set(history)<={0,1},'Control run received steering'
def frames(cap):
 t=barto.load(cap/'trace.bin');assert len(t.fields)==250
 # Copy only compact image and bitplane-DMA evidence before dropping the trace.
 shots=[f.shot for f in t.fields]
 dma=[]
 for f in t.fields:
  words=[]
  for off in range(0,len(f.dma),f.dma_size):
   reg,data=struct.unpack_from('<HH',f.dma,off)
   if f.dma[off+29]==6 and 0x110<=reg<0x118:words.append((reg,data))
  dma.append(hashlib.sha256(repr(words).encode()).hexdigest())
 return shots,dma
ls,ld=frames(left);rs,rd=frames(right)
rows=[]
for i,(x,y) in enumerate(zip(ls,rs)):
 im,jm=Image.open(io.BytesIO(x)).convert('RGB'),Image.open(io.BytesIO(y)).convert('RGB')
 assert im.size==jm.size==(754,576)
 # Exclude only bottom emulator-status strip; retain entire game and borders.
 box=ImageChops.difference(im.crop((0,0,754,568)),jm.crop((0,0,754,568))).getbbox()
 rows.append(dict(field=i,image_diff_box=box,bitplane_dma_equal=ld[i]==rd[i]))
first=next(r for r in rows if r['image_diff_box'] is not None)
assert request>0 and all(r['image_diff_box'] is None and r['bitplane_dma_equal'] for r in rows[:request])
assert first['field']>=edge['sample_field'] and first['field']<100,'Cannot use a capture join or later edge'
assert not first['bitplane_dma_equal'],'JPEG difference without bitplane change'
first_dma=next(r['field'] for r in rows if not r['bitplane_dma_equal'])
assert first_dma==first['field'],('DMA/image field alignment differs',first_dma,first['field'])
result=dict(first_bitplane_dma_difference=first_dma,fields=250,first_request=request,first_sample=edge['sample_field'],first_containing_display=edge['visible_field'],first_pixel_difference=first,request_to_first_pixel_fields=first['field']-request,identical_pre_request_fields=request,only_slave_changes=diff,initial_game_data_equal=True,scope='Paired ordinary guest key press versus already-released key release. First image difference in the game area, corroborated by changed bitplane DMA, after identical pre-request frames. Guest input.device request timing, not host-keyboard/hardware latency. First steering press only; later differences accumulate and are not independent edge-latency measurements.')
(left/'steering-pixel-pair.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
(left/'first-steering-difference.jpg').write_bytes(ls[first['field']]);(right/'first-steering-difference-control.jpg').write_bytes(rs[first['field']])
