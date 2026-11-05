#!/usr/bin/env python3
"""Validate x86_64 FS-UAE profiler window operands against its pinned binary."""
import hashlib,json,os,struct,sys
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
root=Path(__file__).resolve().parents[1]
p=Path(os.environ.get('AMIGA_PREFIX',str(Path.home()/'.local')))/'fs-uae/fs-uae'
b=p.read_bytes(); assert b[:4]==bytes.fromhex('cffaedfe')
pos=32;text=None
for _ in range(struct.unpack_from('<I',b,16)[0]):
 cmd,size=struct.unpack_from('<II',b,pos)
 if cmd==0x19:
  for j in range(struct.unpack_from('<I',b,pos+64)[0]):
   q=pos+72+80*j
   if b[q:q+16].rstrip(b'\0')==b'__text':
    addr,length,offset=struct.unpack_from('<QQI',b,q+32);text=(addr,length,offset)
 pos+=size
assert text
addr,length,offset=text
md=Cs(CS_ARCH_X86,CS_MODE_64);md.detail=True
refs=[]
for lo,hi in [(0x5a400,0x5a600),(0x5f200,0x5f500)]:
 for start in range(lo,hi):
  for ins in md.disasm(b[offset+start-addr:offset+start-addr+15],start,count=1):
   for op in ins.operands:
    if op.type==3 and ins.reg_name(op.mem.base)=='rip':
     target=ins.address+ins.size+op.mem.disp
     if target in (0x32dea04,0x32dea08):refs.append(dict(pc=hex(ins.address),target=hex(target),instruction=ins.mnemonic+' '+ins.op_str))
assert {x['target'] for x in refs}=={'0x32dea04','0x32dea08'}, refs
result=dict(sha256=hashlib.sha256(b).hexdigest(),baseText='0x32dea04',sizeText='0x32dea08',references=refs)
manifest=root/'manifest/profiler.json'
if sys.argv[1:]==['--pin']: manifest.write_text(json.dumps(result,indent=2)+'\n')
else: assert json.loads(manifest.read_text())==result, 'profiler binary/operands changed; rederive before capture'
print(json.dumps(result,indent=2))
