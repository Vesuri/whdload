#!/usr/bin/env python3
"""Independent completeness/bounds audit of the committed relocation table."""
import re,struct,json,collections
from pathlib import Path
import map_symbols as m
root=m.ROOT;hs=m.load(m.GAME/'tfx.020');text=(root/'src/chip_reloc_new.i').read_text();entries=[]
labels=['chip_reloc_mouse:','chip_reloc_display:','chip_reloc_audio:','chip_reloc_video:']
for index,label in enumerate(labels):
 target=2 if index==3 else 1;endlabel=labels[index+1] if index<3 else None
 t=text.split(label)[1];t=t.split(endlabel)[0] if endlabel else t
 words=[]
 for line in t.splitlines():
  if 'dc.' not in line:continue
  size,values=re.search(r'dc\.([wl])\s+(.+)',line).groups()
  words.extend((size,int(x.strip().replace('$','0x'),0)) for x in values.split(','))
 pos=0
 while words[pos]!=('w',-1):
  kind,src=words[pos];assert kind=='w';kind,n=words[pos+1];assert kind=='w' and n>0;pos+=2
  for _ in range(n):
   kind,offset=words[pos];pos+=1;assert kind=='l'
   value=struct.unpack_from('>I',hs[src]['data'],offset)[0]
   lo,hi=[(0xd98,0x24d4),(0x27e0,0x4330),(0x4938,0x4a00),(0x7cec,0x270f4)][index]
   assert lo<=value<hi
   entries.append((src,target,offset))
 assert pos==len(words)-1
ranges={1:[(0xd98,0x24d4),(0x27e0,0x4330),(0x4938,0x4a00)],2:[(0x7cec,0x270f4)]}
expected={(s,t,o) for s,h in enumerate(hs) for t,offs in h['relocs'].items() if t in ranges for o in offs if any(lo<=struct.unpack_from('>I',h['data'],o)[0]<hi for lo,hi in ranges[t])}
assert len(entries)==len(set(entries))==62 and set(entries)==expected
# Negative control: a missing site is rejected by the completeness condition.
assert set(entries[:-1])!=expected
for src,tgt,o in entries:
 assert o%2==0 and o+4<=len(hs[src]['data'])
 v=struct.unpack_from('>I',hs[src]['data'],o)[0]
 assert any(lo<=v<hi for lo,hi in ranges[tgt])
# These are the only PL_GA addresses within copied ranges. PatchSeg uses flat hunk offsets.
s=(root/'src/TFXHD.s').read_text().split('pl_fpu_new\n')[1].split('pl_fpu_new_040:')[0]
flat=len(hs[0]['data']);gas=[]
for off,name in re.findall(r'PL_GA\s+\$([0-9a-f]+),([^\s;]+)',s):
 off=int(off,16)
 if any(flat+lo<=off<flat+hi for lo,hi in ranges[1]):gas.append(name)
assert gas==[],gas
print('62 relocation sites exact and bounded; omission negative control passed; all PL_GA pointers stay in fast RAM')
