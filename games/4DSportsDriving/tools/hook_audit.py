#!/usr/bin/env python3
"""Audit hook instruction spans and HUNK_RELOC32 references in the pristine image."""
import struct,re,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
b=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes();pos=0
u=lambda off:struct.unpack_from('>I',b,off)[0]
assert u(0)==1011 and u(4)==0
nh=u(8);pos=20+4*nh;hunks=[];relocs=[];current=-1
while pos<len(b):
 kind=u(pos)&0x3fffffff;pos+=4
 if kind in (1001,1002,1003):
  current+=1;n=u(pos)*4;pos+=4
  hunks.append(b[pos:pos+n] if kind!=1003 else bytes(n))
  if kind!=1003:pos+=n
 elif kind==1004:
  while (n:=u(pos)):
   target=u(pos+4);pos+=8
   for _ in range(n):relocs.append((current,u(pos),target));pos+=4
  pos+=4
 elif kind==1010:pass
 elif kind==1008:
  while (n:=u(pos)):pos+=4+4*n+4
  pos+=4
 else:raise ValueError((hex(pos-4),kind))
code=hunks[0]
import capstone
md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000)
spans={}
for f in (root/'src').glob('*.s'):
 for off,n in re.findall(r'(?:PERF|TIMING|FIX)_RANGE h0:([0-9a-fA-F]+) (\d+)',f.read_text()):spans[int(off,16)]=int(n)
# Adjacent JMP+NOP ranges form one replacement span.
for lo in sorted(list(spans)):
 if lo not in spans:continue
 while lo+spans[lo] in spans:spans[lo]+=spans.pop(lo+spans[lo])
for lo,n in sorted(spans.items()):
 ins=list(md.disasm(code[lo:lo+n+16],lo));end=lo;covered=[]
 for i in ins:
  if end>=lo+n:break
  assert i.address==end;end+=i.size;covered.append(i.mnemonic+' '+i.op_str)
 assert end==lo+n,(hex(lo),n,hex(end))
 print(f'{lo:05x}+{n}: '+ '; '.join(covered))
for source,off,target in relocs:
 if target!=0:continue
 dst=struct.unpack_from('>I',hunks[source],off)[0]
 for lo,n in spans.items():
  assert not lo<dst<lo+n,('Relocation enters overwritten instruction',source,hex(off),hex(dst))
print(f'{len(relocs)} relocations checked; none enters the middle of a hook')

# Conservatively inspect every aligned word, including data, for direct PC-relative
# branches. This cannot miss a real branch because a linear disassembly stopped
# at an embedded table; false positives must be inspected instead of ignored.
# Verified inline resource table: RTS at $2a96, six NUL-terminated names,
# then LINK at $2ab6. PEA $2ab1 at $2a58 passes "titl" to the loader.
# Assert every byte and the reference, so a different executable fails closed.
assert code[0x2a96:0x2ab6]==b'\x4e\x75!pa0\0!def\0prod\0prod\0!pa1\0titl\0'
assert code[0x2a58:0x2a5c]==bytes.fromhex('487a0057')
assert code[0x2ab6:0x2aba]==bytes.fromhex('4e55ffb2')
resource_table=range(0x2a98,0x2ab6)
relative_count=0
for at in range(0,len(code)-6,2):
 if at in resource_table:continue
 op=struct.unpack_from('>H',code,at)[0];dst=None
 if op&0xf000==0x6000:
  d=op&255
  if d==0:d=struct.unpack_from('>h',code,at+2)[0]
  elif d>=128:d-=256
  dst=at+2+d
 elif op&0xf0f8==0x50c8 or op in (0x4eba,0x4efa):
  dst=at+2+struct.unpack_from('>h',code,at+2)[0]
 if dst is not None:
  relative_count+=1
  for lo,n in spans.items():
   # A branch removed by the same complete replacement cannot enter its stub.
   assert not lo<dst<lo+n or lo<=at<lo+n,('Potential external PC-relative branch into hook',hex(at),hex(dst),hex(op))
print(f'{relative_count} aligned PC-relative branch candidates checked; no interior hook targets')
