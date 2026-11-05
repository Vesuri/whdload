from pathlib import Path
from capstone import *
import json,re,collections
root=Path('tmp/game/RoadRash/data');out=Path('tmp/d-raw-modules');out.mkdir(exist_ok=True)
cs=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
for name,base in [('lomain.ami',0x400),('INTRO.AMI',0x8000),('TITLE.AMI',0x8000)]:
 b=(root/name).read_bytes();todo=[base]+({"TITLE.AMI":[0x12aa8,0x13846],"INTRO.AMI":[0x8bea,0x98ce,0x8d14,0x8d64,0x8dac,0x8ddc,0x9b1c],"lomain.ami":[0x4c4e,0x4c50,0x645c,0x4c7a,0x4c84]})[name];seen={};indirect=[];external=[];bad=[]
 while todo:
  pc=todo.pop()
  while base<=pc<base+len(b) and pc not in seen:
   ii=list(cs.disasm(b[pc-base:pc-base+16],pc,count=1))
   if not ii:bad.append(pc);break
   i=ii[0];seen[pc]=dict(bytes=i.bytes.hex(),size=i.size,mnemonic=i.mnemonic,operands=i.op_str)
   m=i.mnemonic.split('.')[0];t=re.fullmatch(r'\$([0-9a-f]+)(?:\.[wl]|\(pc\))?',i.op_str);target=int(t[1],16) if t else None
   if m.startswith('b') and m not in ['btst','bset','bclr','bchg'] or m in ['jsr','jmp']:
    if target is not None:
     if base<=target<base+len(b):todo.append(target)
     else:external.append([hex(pc),hex(target)])
    elif m in ['jsr','jmp']:indirect.append([hex(pc),i.op_str])
   if m.startswith('db'):
    t=re.search(r'\$([0-9a-f]+)$',i.op_str)
    if t:todo.append(int(t[1],16))
   if m in ['rts','rte','rtr','jmp','bra','illegal','stop']:break
   if m in ['dc','invalid']:bad.append(pc);break
   pc+=i.size
 rows={hex(k):v for k,v in sorted(seen.items())};r=dict(name=name,base=hex(base),file_bytes=len(b),code_bytes=sum(v['size'] for v in seen.values()),instructions=rows,indirect=indirect,external=external,bad=[hex(x) for x in bad]);(out/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(name,'code',r['code_bytes'],'instructions',len(rows),'indirect',indirect,'external',external,'bad',r['bad'])
