#!/usr/bin/env python3
"""Validate game render markers against COP1LC writes and following-field DMA.
The result is a rate for this observed workload, not a cross-boot speedup claim.
"""
import argparse,collections,json,struct
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();cap=a.capture
meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base'];t=barto.load(cap/'trace.bin')
boundaries=barto.capture_part_starts(cap,t)
swaps=[];markers=[];pending=None;boundary_markers=0;boundary_updates=0
for f in t.fields:
 if f.index in boundaries:
  if pending is not None:boundary_updates+=1
  pending=None;seen_part_event=False
 for pc,c,r in t.instructions(f):
  if pc==g+0x35332:
   assert pending is None,'More than one list update before a render marker'
   pending=(f.index,r[8]);swaps.append(pending);seen_part_event=True
  if pc==g+0x7500:
   if pending is None:
    assert not seen_part_event,'Render marker without display update inside capture part'
    boundary_markers+=1;seen_part_event=True
   else:
    assert f.index-pending[0]<=1,(pending,f.index)
    markers.append(f.index);pending=None
  assert pc!=g+0x35344,'Other display path active; inspect before counting frames'
assert len(swaps)>=2
if pending is not None:boundary_updates+=1
lists={addr for f,addr in swaps};assert len(lists)==2,lists
selected=[];planes_by_list=collections.defaultdict(set)
for f in t.fields:
 starts=[];words={};first={}
 for off in range(0,len(f.dma),f.dma_size):
  typ=f.dma[off+29];reg,data=struct.unpack_from('<HH',f.dma,off);addr=struct.unpack_from('<I',f.dma,off+12)[0]
  if typ==3:
   if addr in lists:starts.append(addr)
   if 0xe0<=reg<0x100:words[reg]=data
  if typ==6 and 0x110<=reg<0x120:
   plane=(reg-0x110)//2
   if plane not in first:
    high=0xe0+4*plane
    expected=(words[high]<<16)|words[high+2]
    assert addr==expected,(f.index,plane,hex(addr),hex(expected))
    first[plane]=addr
 assert len(starts)==1,(f.index,starts)
 assert set(first)=={0,1,2,3},(f.index,first)
 selected.append(starts[0]);planes_by_list[starts[0]].add(tuple(first[i] for i in range(4)))
for addr,planes in planes_by_list.items():assert len(planes)==1,(addr,planes)
assert len({next(iter(v)) for v in planes_by_list.values()})==2
visible=[];visibility=[];same_field=[]
for field,addr in swaps:
 if field+1<len(selected) and field+1 not in boundaries:
  actual=field+1
  if selected[field]==addr:
   # A split long COP1LC store can finish in slot 0 of this field, before
   # the copper's first fetch. Instruction records land on its completion.
   assert field>0 and field not in boundaries and selected[field-1]!=addr
   f=t.fields[field];low=[];starts=[]
   for slot,off in enumerate(range(0,len(f.dma),f.dma_size)):
    typ=f.dma[off+29];reg,data=struct.unpack_from('<HH',f.dma,off);busaddr=struct.unpack_from('<I',f.dma,off+12)[0]
    if typ==2 and reg==0x1102 and busaddr==0xdff082 and data==addr&65535:low.append(slot)
    if typ==3 and busaddr==addr:starts.append(slot)
   assert len(low)==len(starts)==1 and low[0]<starts[0],(field,low,starts)
   actual=field;same_field.append(dict(field=field,low_write_slot=low[0],copper_start_slot=starts[0]))
  else:assert selected[field+1]==addr,(field,addr,selected[field:field+2])
  visible.append(actual);visibility.append(dict(copper_write_field=field,visible_field=actual,copper_list=addr))
transitions=[i for i in range(1,len(selected)) if i not in boundaries and selected[i]!=selected[i-1]]
assert transitions==visible,(transitions,visible)
intervals=[]
ends=sorted(boundaries)+[len(t.fields)]
for lo,hi in zip(ends,ends[1:]):
 v=[f for f in visible if lo<=f<hi]
 if len(v)>1:intervals.append({'part_start':lo,'first':v[0],'last':v[-1],'intervals':len(v)-1,'fields':v[-1]-v[0]})
assert intervals,'Not enough transitions inside contiguous capture parts'
rate=50*sum(v['intervals'] for v in intervals)/sum(v['fields'] for v in intervals)
result={'fields':len(t.fields),'render_markers':len(markers),'boundary_markers':boundary_markers,'copper_writes':swaps,'displayed_transition_fields':visible,
 'bitplanes_by_copper_list':{hex(k):[hex(x) for x in next(iter(v))] for k,v in planes_by_list.items()},
 'swap_visibility':visibility,'same_field_switches':same_field,'capture_part_starts':sorted(boundaries),'boundary_updates':boundary_updates,'contiguous_intervals':intervals,'validated_fps_within_contiguous_parts':rate,'scope':'Within each capture part, render markers match copper-list switches and four-bitplane DMA (next field, or a bus-proven same-field switch). Boundary-partial events excluded; rate uses only intervals within contiguous parts and is not an A/B speedup.'}
(cap/'display-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
