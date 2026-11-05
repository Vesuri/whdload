#!/usr/bin/env python3
# Interrupt entries/cost in a hi25 trace: WHDLoad glue entry -> matching RTE.
from pathlib import Path
import sys,json,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path(sys.argv[1]);glue=int(sys.argv[2],16) if len(sys.argv)>2 else 0x9eff00
mem=bytearray((p/'start.bin').read_bytes());fast=(p/'start-fast.bin').read_bytes();mem+=bytes(0x200000-len(mem))+fast
def op(pc):return struct.unpack_from('>H',mem,pc)[0] if pc+2<=len(mem) else 0
# Kick 1.3 exec level handlers located by signature: movem.l d0-d1/a0-a1/a5-a6,-(sp); lea $dff000,a0
heads={}
sig=bytes.fromhex('48e7c0c641f900dff000')
at=0x800000
while True:
 at=mem.find(sig,at,0xa00000)
 if at<0:break
 heads[at]=len(heads)+1;at+=2
print('handler entries',{hex(k):v for k,v in heads.items()})
t=barto.load(p/'detail.bin');n=len(t.fields)
depth=0;level=None;cnt=collections.Counter();cost=collections.Counter();entries=0;total=0
for f in t.fields:
 for pc,c,regs in t.instructions(f):
  total+=c
  if pc==glue:depth+=1;entries+=1;level='glue-only' if depth==1 else level
  if depth and pc in heads and level=='glue-only':level='L%d'%heads[pc];cnt[level]+=1
  if depth:cost[level]+=c
  if pc not in (None,0x7fffffff) and depth and op(pc)==0x4e73:
   depth-=1
   if not depth:level=None
cyc_ms=20.031886677085037/(total/n)
print('fields',n,'glue entries',entries,'per field %.2f'%(entries/n))
for k,v in cnt.most_common():print(' ',k,'entries/field %.2f'%(v/n),'ms/field %.3f'%(cost[k]*cyc_ms/n),'us/entry %.1f'%(cost[k]*cyc_ms*1000/v))
print('glue-only ms/field %.3f'%(cost['glue-only']*cyc_ms/n),'total irq ms/field %.3f'%(sum(cost.values())*cyc_ms/n))
