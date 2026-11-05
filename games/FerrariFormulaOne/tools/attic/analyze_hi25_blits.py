#!/usr/bin/env python3
# Blit census from a cycle-exact-blitter trace: CPU custom writes to BLTCON0/1
# and BLTSIZE (DMA write records) plus blitter slot timeline -> per-blit type,
# size and busy time (BLTSIZE write to last blitter slot before the next start).
from pathlib import Path
import sys,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p/'detail.bin');cck=1/3546895*1000
con0=con1=0;blits=[];cur=None;pos=0
for f in t.fields:
 for y in range(313):
  for x in range(227):
   at=(y*227+x)*f.dma_size
   reg=struct.unpack_from('<H',f.dma,at)[0];dat=struct.unpack_from('<Q',f.dma,at+2)[0]&0xffff;addr=struct.unpack_from('<I',f.dma,at+12)[0];typ=struct.unpack_from('<h',f.dma,at+29)[0]
   if (reg&0xff00)==0x1100:
    if addr==0xdff040:con0=dat
    elif addr==0xdff042:con1=dat
    elif addr==0xdff058:
     cur={'con0':con0,'con1':con1,'w':dat&63 or 64,'h':(dat>>6) or 1024,'start':pos,'end':pos,'slots':0};blits.append(cur)
   if typ==5 and cur is not None:cur['end']=pos;cur['slots']+=1
   pos+=1
nf=len(t.fields)
def kind(b):
 if b['con1']&1:return 'line'
 use=(b['con0']>>8)&15;ch=''.join(c for c,bit in zip('ABCD',(8,4,2,1)) if use&bit)
 fill=' fill' if b['con1']&0x18 else ''
 return ch+fill
agg=collections.defaultdict(lambda:[0,0,0])
for b in blits:
 k=kind(b);a=agg[k];a[0]+=1;a[1]+=(b['end']-b['start']+1);a[2]+=b['w']*b['h']
print('fields',nf,'blits/field %.1f'%(len(blits)/nf))
print('%-12s %8s %10s %10s %8s'%('kind','n/field','ms/field','words/fld','us/blit'))
for k,(n,d,w) in sorted(agg.items(),key=lambda x:-x[1][1]):print('%-12s %8.1f %10.3f %10.0f %8.1f'%(k,n/nf,d*cck/nf,w/nf,d*cck*1000/n))
big=sorted(blits,key=lambda b:-(b['end']-b['start']))[:15]
print('largest:');[print(' ',kind(b),hex(b['con0']),hex(b['con1']),'%dx%d'%(b['w'],b['h']),'%.3f ms'%((b['end']-b['start'])*cck)) for b in big]
sizes=collections.Counter((kind(b),b['w'],b['h']) for b in blits)
print('common:');[print(' ',k,v/nf) for k,v in sizes.most_common(15)]
