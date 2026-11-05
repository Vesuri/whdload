#!/usr/bin/env python3
"""Cost of each simulation tick: SOFT handler (game:007ee) entry to its rte, and its callees.
  soft_cost.py TRACE.bin CODE.bin BASE
Interrupts nested inside the handler are included.
"""
import sys, struct, collections; sys.path.insert(0, __import__('os').path.dirname(__file__)); import _amigaxdev; from amigaxdev import barto
from i500_report import regions
t=barto.load(sys.argv[1]); code=open(sys.argv[2],'rb').read(); base=int(sys.argv[3],0)
g=[r for r in regions(code,base,t.chip) if r[2]=='game'][0][0]
def word(a):
  o=a-base; return struct.unpack('>H',code[o:o+2])[0] if 0<=o<len(code)-2 else None
costs=[]; cur=None; calls=collections.Counter(); pend=None; total=0
for f in t.fields:
  for pc,c,r in t.instructions(f):
    total+=c
    if pc==g+0x7ee and cur is None: cur=[r[15],0]
    if cur is not None:
      cur[1]+=c
      if pend is not None and r[15]==pend-4: calls[pc-g]+=1
      pend=None
      w=word(pc) if pc else None
      if w is not None and ((w&0xff00)==0x6100 or (w&0xffc0)==0x4e80): pend=r[15]
      if w==0x4e73 and r[15]==cur[0]: costs.append(cur[1]); cur=None
nf=len(t.fields)
print('SOFT entries',len(costs),'cycles each: min %d max %d mean %d'%(min(costs),max(costs),sum(costs)/len(costs)))
print('share of all cycles %.1f%%, per tick = %.2f fields'%(100*sum(costs)/total, sum(costs)/len(costs)/(total/nf)))
print('callees (calls):', ', '.join('%05x:%d'%(k,v) for k,v in calls.most_common(15)))
