#!/usr/bin/env python3
# Blitter busy/idle timeline from DMA records (cycle-exact blitter traces only):
# busy = from first to last blitter slot of a run with internal gaps < GAP CCKs.
from pathlib import Path
import sys,struct,collections,statistics
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path(sys.argv[1]);GAP=int(sys.argv[2]) if len(sys.argv)>2 else 8
t=barto.load(p/'detail.bin');f0=t.fields[0];n=len(f0.dma)//f0.dma_size
H=256 if n%256==0 else 227;V=n//H
print('records/field',n,'H',H,'V',V)
busy=0;idle_gaps=collections.Counter();runs=0;slots=collections.Counter();total=0
pos=0;last=None;start=None
for f in t.fields:
 for y in range(min(V,313)):
  for x in range(227):
   at=(y*H+x)*f.dma_size
   typ=struct.unpack_from('<h',f.dma,at+29)[0]
   if typ==5:
    if last is None or pos-last>GAP:
     if last is not None:busy+=last-start+1;g=pos-last;idle_gaps[min(g//16*16,2000)]+=1
     start=pos;runs+=1
    last=pos
   pos+=1
if last is not None:busy+=last-start+1
cck=1/3546895*1000
print('fields',len(t.fields),'blit runs',runs,'per field %.1f'%(runs/len(t.fields)))
print('blitter busy ms/field %.2f of %.2f'%(busy*cck/len(t.fields),pos*cck/len(t.fields)))
small=sum(v for k,v in idle_gaps.items() if k<=64);print('gaps <=64 CCK',small,'(~%.1f us each)'%(32*cck*1000))
tot_small=sum((k+8)*v for k,v in idle_gaps.items() if k<=256)*cck
print('idle time in gaps <=256 CCK: %.2f ms/field'%(tot_small/len(t.fields)))
print(sorted(idle_gaps.items())[:24])
