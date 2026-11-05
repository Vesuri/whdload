"""Conservative executable reachability from the unpacked image's entry point."""
from pathlib import Path
from capstone import *
import json,re,collections
root=Path('tmp/d-original-hunk');b=(root/'main-unrelocated.bin').read_bytes();cs=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020)
seen={};todo=[0];unresolved=[];bad=[]
while todo:
 pc=todo.pop()
 while 0<=pc<len(b) and pc not in seen:
  ii=list(cs.disasm(b[pc:pc+16],pc,count=1))
  if not ii:bad.append(pc);break
  i=ii[0];m=i.mnemonic.split('.')[0];op=i.op_str;seen[pc]=dict(size=i.size,mnemonic=i.mnemonic,operands=op,bytes=i.bytes.hex())
  t=re.fullmatch(r'\$([0-9a-f]+)(?:\.l|\(pc\))?',op)
  target=int(t[1],16) if t else None
  if m.startswith('b') and m not in ['btst','bset','bclr','bchg'] or m in ['jmp','jsr']:
   if target is not None and target<len(b):todo.append(target)
   elif m in ['jmp','jsr']:unresolved.append(dict(pc=hex(pc),mnemonic=m,operands=op))
  if m.startswith('db'):
   t=re.search(r'\$([0-9a-f]+)$',op)
   if t:todo.append(int(t[1],16))
  if m in ['rts','rte','rtr','jmp','bra','illegal','stop']:break
  if m in ['dc','invalid']:bad.append(pc);break
  pc+=i.size
(root/'reachable.json').write_text(json.dumps(dict(bytes=sum(x['size'] for x in seen.values()),instructions={hex(k):v for k,v in sorted(seen.items())},unresolved=unresolved,bad=[hex(x) for x in bad]),indent=2)+'\n')
print(len(seen),'instructions',sum(x['size'] for x in seen.values()),'bytes','indirect',unresolved,'bad',bad)
