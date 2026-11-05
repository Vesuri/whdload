#!/usr/bin/env python3
"""Short-trace measurements; render-loop counts are not validated displayed FPS."""
from pathlib import Path
import collections,json,struct,sys
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=Path(sys.argv[1]); t=barto.load(p/'trace.bin'); m=(p/'memory.bin').read_bytes()
a=json.loads((p/'anchor.json').read_text()); g=a['game_base']; base=a.get('memory_base',0x200000)
raw=lambda pc,n: m[pc-base:pc-base+n] if base<=pc<base+len(m)-n else t.chip[pc:pc+n] if 0<=pc<len(t.chip)-n else b''
# Static immediate-bit-6 DMACONR busy loops used in this binary.
polls={}; branches={}
for region,org in [(m,base),(t.chip,0)]:
 for pattern,mode in [(bytes.fromhex('082e00060002'),'a6'),(bytes.fromhex('0839000600dff002'),'abs')]:
  at=0
  while (at:=region.find(pattern,at))>=0:
   polls[org+at]=mode
   after=at+len(pattern)
   if region[after:after+1]==b'\x66': branches[org+after]=mode
   at+=2
counts=collections.Counter();cycles=collections.Counter(); pcs=collections.Counter();dma=collections.Counter();frames=[]
for f in t.fields:
 frame=0
 for pc,c,r in t.instructions(f):
  cycles['total']+=c;counts['instructions']+=1
  if pc is None: cycles['no_pc']+=c;continue
  if pc==0x7fffffff:cycles['irq_entry']+=c;continue
  pcs[pc]+=c
  if pc==g+0x7500: frame+=1
  mode=polls.get(pc) or branches.get(pc)
  if mode=='abs' or (mode=='a6' and r[14]==0xdff000): cycles['blitter_poll_loops']+=c
  op=raw(pc,2)
  if len(op)==2:
   w=int.from_bytes(op,'big')
   if (w&0xf0c0)==0x80c0: cycles['div_instructions']+=c;counts['div']+=1
   if (w&0xf0c0)==0xc0c0: cycles['mul_instructions']+=c;counts['mul']+=1
 frames.append(frame)
 for i in range(0,len(f.dma),f.dma_size):dma[f.dma[i+29]]+=1
names={0:'free',1:'refresh',2:'CPU',3:'copper',4:'audio',5:'blitter',6:'bitplane',7:'sprite',8:'disk'}
result={'fields':len(t.fields),'approx_seconds':len(t.fields)/50,'cycles':dict(cycles),'counts':dict(counts),
 'cycle_percent':{k:round(v/cycles['total']*100,3) for k,v in cycles.items()},
 'render_loop_completions_per_field':frames,'render_loop_completions':sum(frames),
 'dma_slot_percent':{names.get(k,str(k)):round(v/sum(dma.values())*100,3) for k,v in sorted(dma.items())}}
(p/'first.png').write_bytes(t.fields[0].shot);(p/'last.png').write_bytes(t.fields[-1].shot)
(p/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
(p/'pc-cycles.json').write_text(json.dumps({hex(pc-g):c for pc,c in pcs.items() if g<=pc<g+0x3a04c},indent=2)+'\n')
print(json.dumps(result,indent=2))
