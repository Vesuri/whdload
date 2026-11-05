#!/usr/bin/env python3
"""Count publications, check their display DMA, and summarize interrupts/bus costs."""
import argparse,collections,json,os,struct
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from gpc_report import Memory,regions
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();out=a.capture
m=json.loads((out/'metadata.json').read_text());os.environ['SLAVE']=str((out/'slave.slave').resolve())
t=barto.load(out/'trace.bin');d=(out/'code.bin').read_bytes();mem=Memory(t,d,m['base']);h=m['code_base']
rr={n:(lo,hi,o) for lo,hi,n,o in regions(d,m['base'])};k=rr['kick'][2]
handlers={struct.unpack_from('>I',t.chip,0x60+4*n)[0]:n for n in range(1,7)}
counts=collections.Counter();irq_cycles=collections.Counter();active=[];total=wait=idle=overhead=0
swaps=[];selected=[];dma=collections.Counter();vbl=[]
for f in t.fields:
 n=0;nv=0
 for pc,c,r in t.instructions(f):
  total+=c
  if pc is None:idle+=c;continue
  if pc==0x7fffffff:overhead+=c;continue
  if pc==h+0x39e:n+=1
  if pc==h+0x772a:nv+=1
  if pc in handlers:
   level=handlers[pc];counts[level]+=1;active.append(level)
  for level in active:irq_cycles[level]+=c
  op=mem.read(pc,8) or b''
  if op[:2]==b'\x4e\x73' and active:active.pop()
  poll=bytes.fromhex('082e00060002')
  if op[:6]==poll or (op[:2]==b'\x4e\x71' and poll in (mem.read(pc,10) or b'')) or (op[:2] in (b'\x66\xf4',b'\x66\xf8') and mem.read(pc-6,6)==poll):wait+=c
   # KickEmu WaitBlit uses absolute DMACONR byte accesses and a word branch.
  if op[:6]==bytes.fromhex('4a3900dff002') or op==bytes.fromhex('0839000600dff002') or (op[:4]==bytes.fromhex('66000004') and mem.read(pc-8,8)==bytes.fromhex('0839000600dff002')):
   wait+=c
 swaps.append(n);vbl.append(nv);first={}
 for off in range(0,len(f.dma),f.dma_size):
  typ=f.dma[off+29];dma[typ]+=1
  reg=struct.unpack_from('<H',f.dma,off)[0]
  if typ==6 and 0x110<=reg<0x120 and reg not in first:first[reg]=struct.unpack_from('<I',f.dma,off+12)[0]
 selected.append(tuple(sorted(first.items())))
assert sum(swaps)>1 and all(n<=1 for n in swaps)
assert len(set(selected))==2,'expected two displayed bitplane sets'
transitions=[i for i in range(1,len(selected)) if selected[i]!=selected[i-1]]
published=[i for i,n in enumerate(swaps) if n]
# First plane fetch must move to the other set in this or the following field.
pairs=[];remaining=set(transitions)
for field in published:
 if field==len(swaps)-1:continue
 match=next((x for x in (field,field+1) if x in remaining),None)
 assert match is not None,(field,transitions)
 remaining.remove(match);pairs.append((field,match))
assert not remaining,remaining
names={0:'free',1:'refresh',2:'CPU',3:'copper',4:'audio',5:'blitter',6:'bitplane',7:'sprite',8:'disk'}
result=dict(fields=len(swaps),swap_pattern=swaps,publication_dma_pairs=pairs,display_buffer_sets=len(set(selected)),native_vbl_pattern=vbl,total_cycles=total,cycles_per_field=total/len(swaps),idle_cycles=idle,overhead_cycles=overhead,blitter_wait_percent=100*wait/total,irq_entries=dict(counts),irq_inclusive_percent={str(n):100*c/total for n,c in irq_cycles.items()},dma_percent={names.get(n,str(n)):100*c/sum(dma.values()) for n,c in dma.items()})
(out/'metrics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if not k.endswith('pattern')},indent=2))
