#!/usr/bin/env python3
"""Blitter busy-wait per frame, by routine (fields/frame).
  blit_waits.py TRACE.bin CODE.bin BASE
Same poll idioms as frames.py; frames are counted at the swap game:0b2e2.
"""
import sys, struct, collections, bisect; sys.path.insert(0, __import__('os').path.dirname(__file__)); import _amigaxdev; from amigaxdev import barto
from i500_report import regions, Memory, Namer
t=barto.load(sys.argv[1]); code=open(sys.argv[2],'rb').read(); base=int(sys.argv[3],0)
regs=regions(code,base,t.chip); mem=Memory(t,code,base); nm=Namer(regs,mem); g=[r for r in regs if r[2]=='game'][0][0]
starts=sorted(nm.starts)
POLL=bytes.fromhex('0839000600dff002')
def raw(a,n): o=a-base; return code[o:o+n] if 0<=o<len(code)-n else b''
w=collections.Counter(); sites=collections.Counter(); tot=0; frames=0
for f in t.fields:
  for pc,c,r in t.instructions(f):
    tot+=c
    if pc is None: continue
    if pc==g+0xb2e2: frames+=1
    b=raw(pc,8); op=struct.unpack('>H',b[:2])[0] if len(b)>=2 else 0
    isw = b==POLL or (b[:1]==b'\x66' and raw(pc-8,8)==POLL) or ((op&0xf1f8)==0x0110 and r[8+(op&7)]==0xdff002) or (b[:2]==b'\x66\xfc' and (struct.unpack('>H',raw(pc-2,2))[0]&0xf1f8)==0x0110)
    if isw:
      i=bisect.bisect_right(starts,pc)-1; w[starts[i]-g]+=c; sites[pc-g]+=c
fl=tot/len(t.fields)
print('frames',frames,'total blitter wait %.2f fields/frame'%(sum(w.values())/frames/fl))
for k,v in w.most_common(8): print(' game:%05x  %.3f fields/frame'%(k,v/frames/fl))
