#!/usr/bin/env python3
"""Independent host check of the emulator's tagged replay golden packet."""
import argparse,json,struct,zlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();m=json.loads((a.capture/'anchor.json').read_text())
i=b.index(b'4DRPLTST');v,n,passed=struct.unpack_from('>HHI',b,i+8)
assert (v,n,passed) in ((3,38,38),),(v,n,passed)
size=63912;start=i+40;packet=b[start:start+size]
assert b[i+36:i+40]==b'RPL1' and b[start+size:start+size+4]==b'RPL2'
assert b[start+size+4+(size-36):start+size+8+(size-36)]==b'RPL3'
assert packet[:8]==b'4DRPL050'
version,physics,rate,slots,prefix,count,native,private,epoch=struct.unpack_from('>4H5I',packet,8)
assert (version,physics,rate,slots,prefix,native,private)==(2,10,50,20,1828,22400,7840)
assert zlib.crc32(packet[:-4])==struct.unpack_from('>I',packet,size-4)[0]
assert 0<count<=30000 and epoch%1500==0 and epoch+count<=75000
at=m['data_base']+0x7ffe-m['memory_base'];ptr=lambda o:struct.unpack_from('>I',b,at+o)[0]-m['memory_base']
assert packet[36:60]==b[at-0x1750:at-0x1750+24]
assert struct.unpack_from('>H',packet,60)[0]==count
assert packet[62:1864]==b[ptr(-0x1778):ptr(-0x1778)+1802]
inputs=packet[1864:31864];assert inputs[:count]==b[ptr(-0x1770):ptr(-0x1770)+count]
assert not any(inputs[count:])
h=b.index(b'4DHISTRY');hv,hn,hs,_=struct.unpack_from('>4H',b,h+8);assert (hv,hn,hs)==(9,20,392)
records=h+28;valid=[]
for slot in range(20):
 ns=packet[31864+1120*slot:31864+1120*(slot+1)]
 cs=packet[54264+392*slot:54264+392*(slot+1)]
 if struct.unpack_from('>H',cs)[0]:
  assert struct.unpack_from('>H',cs)[0]==50 and ns[0x3f4]==1
  assert struct.unpack_from('>H',ns,0x140)[0]==1500*slot<count
  assert ns==b[ptr(-0x16bc)+1120*slot:ptr(-0x16bc)+1120*(slot+1)]
  assert cs==b[records+392*slot:records+392*(slot+1)]
  valid.append(slot)
 else:assert not any(ns) and not any(cs)
assert valid and valid[0]==0
route=list(struct.unpack_from('>901H',packet,62104))
assert all(0<=v<=900 for v in route)
end=next(i for i in range(1,901) if route[i]==0)
assert not any(route[end:]) and packet[63906:63908]==b'\0\0'
if b[at-0x174a]:
 live=list(struct.unpack_from('>901H',b,ptr(-0x17a4)))
 assert route[:end+1]==live[:end+1]
else:assert not any(route)
(a.capture/'golden.r50').write_bytes(packet)
r=dict(physics_abi=physics,checks=passed,bytes=size,rate=rate,input_count=count,epoch=epoch,valid_slots=valid,crc32=hex(zlib.crc32(packet[:-4])),guards=True,source_buffers_match=True)
(a.capture/'replay-file-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
