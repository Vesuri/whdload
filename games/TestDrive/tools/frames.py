#!/usr/bin/env python3
"""TD gameplay LoadView publications, CPU service costs and DMA shares.
Marker is root:$7AAA, independently checked against alternating plane DMA.
Use only a gameplay window; menus also call LoadView. Routine costs overlap.
"""
import argparse,collections,json,struct
from pathlib import Path
from td_report import regions,Memory,Namer,analyse
from amigaxdev import barto
p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace');p.add_argument('dump');p.add_argument('base',type=lambda x:int(x,0));p.add_argument('--swap-offset',type=lambda x:int(x,0),default=0x7aaa);a=p.parse_args()
t=barto.load(a.trace);dump=Path(a.dump).read_bytes();mem=Memory(t,dump,a.base);regs=regions(dump,a.base,t.chip);rr={n:lo for lo,hi,n,o in regs};marker=rr['td']+a.swap_offset
if a.swap_offset==0x7aaa and mem.read(marker,12)!=bytes.fromhex('226f00042c6c83d64eeeff22'):raise ValueError('LoadView signature mismatch')
vec=mem.long(0x6c)
if mem.read(vec+0x1e,4)!=bytes.fromhex('08010006') or mem.read(vec+0x24,6)!=bytes.fromhex('4cee2200009c'):raise ValueError('unrecognized level-3 blitter dispatch')
counts=[];total=idle=wait=irqcost=irqcount=0;pcs=collections.Counter();slots=collections.Counter();active=None;partial_irqs=0
for f in t.fields:
 n=0
 for pc,c,r in t.instructions(f):
  total+=c
  if pc==marker:n+=1
  if pc not in (None,0x7fffffff):pcs[pc]+=c
  if pc is None or (pc not in (None,0x7fffffff) and mem.word(pc)==0x4e72):idle+=c
  if pc is not None and rr['td']+0xd44<=pc<rr['td']+0xd66:wait+=c
  if pc==vec:
   if active is not None:partial_irqs+=1
   active=[r[15],0,False]
  if active is not None:
   active[1]+=c
   if pc==vec+0x24:active[2]=True;irqcount+=1
   if pc not in (None,0x7fffffff) and mem.word(pc)==0x4e73 and r[15]>=active[0]:
    if active[2]:irqcost+=active[1]
    active=None
 counts.append(n)
 for j in range(0,len(f.dma),f.dma_size):slots[struct.unpack_from('<h',f.dma,j+29)[0]]+=1
result=dict(fields=len(t.fields),marker='td:'+hex(a.swap_offset),marker_counts=counts,presentations=sum(counts),window_fps=50*sum(counts)/len(counts) if a.swap_offset==0x7aaa else None,instruction_records_available=bool(pcs),cycles=total,partial_irq_intervals=partial_irqs+int(active is not None))
if pcs:
 self_c,incl,calls,edges,pc_c,kinds,contexts=analyse(t,mem,Namer(regs,mem),t.fields)
 names={'wait':'td:00d44','clear':'td:00d72','fill':'td:00dbe','shape':'td:010c4','span':'h4:03796','span_setup':'h4:03828','projection':'h4:03b10','object_dispatch':'h4:03b56','road_walk':'h4:01a14'}
 result.update(wait_routine_percent=100*wait/total,blitter_irq_count=irqcount,blitter_irq_service_percent=100*irqcost/total,idle_stop_percent=100*idle/total,routines={name:dict(routine=fn,self_percent=100*self_c[fn]/total,inclusive_percent=100*incl[fn]/total,calls=calls[fn]) for name,fn in names.items()})
 ds=sum(slots.values());result['dma_percent']={str(k):100*v/ds for k,v in sorted(slots.items())}
else:
 result.update(window_fps=None,presentations=None,marker_counts=None,limitation='CPU backend emits no instruction PCs; use swap_fields.py. CPU costs unavailable; do not interpret missing DMA as zero work.')
Path(a.trace).with_suffix('.frames.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
