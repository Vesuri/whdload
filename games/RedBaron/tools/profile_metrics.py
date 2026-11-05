#!/usr/bin/env python3
"""Exact-PC counters and hardware-wait checks for the local Red Baron baseline."""
import collections,json,struct,sys,os
from pathlib import Path
from trace_series import Series
from redbaron_report import Memory,regions,Namer
out=Path(sys.argv[1]);paths=[out/'trace.bin']+sorted(out.glob('trace-*.bin'))
os.environ['SLAVE']=str(out/'slave.slave')
t=Series(paths);mem=Memory(t,(out/'fast-before.bin').read_bytes(),0x200000)
regs=regions(mem.dump,mem.base,t.chip);n=Namer(regs,mem)
sim=next(lo for lo,hi,name,origin in regs if name=='sim')
# Recognize only actual DMACONR byte polls and the adjacent backward BNE.
poll={};branches={}
for lo,hi,name,origin in regs:
 for pc in range(lo,hi-8,2):
  op=mem.word(pc)
  if op is not None and 0x0828<=op<=0x082f and mem.read(pc+2,4)==bytes.fromhex('00060002'):
   poll[pc]=op-0x0828
   if mem.word(pc+6)==0x66f8:branches[pc+6]=op-0x0828
  elif mem.read(pc,8)==bytes.fromhex('0839000600dff002'):
   poll[pc]=None
   if mem.word(pc+8)==0x66f6:branches[pc+8]=None
hits=collections.Counter();pcs=collections.Counter();slots=collections.Counter();region=collections.Counter()
wait=collections.Counter();tot=0;count=0;irq=0;stopped=0;events=[];mirror=[];perfield=[]
watch={sim+0x314c0:'swap-entry',sim+0x3154a:'copper-pointer-update',sim+0x304d0:'mirror-entry',sim+0x2ffcc:'timer-callback',sim+0x2d344:'mouse-callback'}
marker=mem.dump.index(b'RBVERIFY');anchor=struct.unpack_from('>I',mem.dump,marker+48)[0];watch[anchor]='flight-step'
for f in t.fields:
 ft=0;fc=0
 for pc,c,r in t.instructions(f):
  ft+=c;tot+=c;count+=1
  if pc is None:stopped+=c;continue
  if pc==0x7fffffff:irq+=1;continue
  pcs[pc]+=c
  region[next((name for lo,hi,name,origin in regs if lo<=pc<hi),'unmapped')]+=c
  if pc in watch:
   tag=watch[pc];hits[tag]+=1
   if tag in ('swap-entry','copper-pointer-update','flight-step'):events.append(dict(field=f.index,tag=tag,a0=hex(r[8]),d0=hex(r[0]),d1=hex(r[1])))
   if tag=='mirror-entry':
    a0=r[8];raw=mem.read(a0,18)
    mirror.append(dict(field=f.index,descriptor=hex(a0),bytes=raw.hex() if raw else None))
  for points,key in ((poll,'btst'),(branches,'branch')):
   if pc in points:
    reg=points[pc]
    if reg is None or r[8+reg]==0xdff000:wait[key]+=c
  if sim+0x31522<=pc<=sim+0x31548:wait['beam-position-loop']+=c
 for i in range(0,len(f.dma),f.dma_size):slots[f.dma[i+29]]+=1
 perfield.append(ft)
 if f.index in (0,99,100,199,200,249): (out/f'field-{f.index:03}.png').write_bytes(f.shot)
result=dict(gap_before_recorded_fields=sorted(t.gap_fields),gap_fields_each=1,fields=len(t.fields),cycles=tot,expected_cycles=142102*len(t.fields),records=count,irq_records=irq,stopped_cycles=stopped,
 region_cycles=dict(region),dma_record_sizes=sorted(set(f.dma_size for f in t.fields)),dma_slots=dict(slots),wait_cycles=dict(wait),hits=dict(hits),events=events,mirror=mirror,
 mirror_exact_cycles=sum(c for pc,c in pcs.items() if sim+0x304d0<=pc<sim+0x30572),
 bit_reverse_cycles=sum(c for pc,c in pcs.items() if sim+0x3050e<=pc<=sim+0x3054c),
 field_cycles_min=min(perfield),field_cycles_max=max(perfield),
 hottest=[dict(pc=hex(pc),name=n.addr(pc),cycles=c) for pc,c in pcs.most_common(15)])
(out/'metrics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
