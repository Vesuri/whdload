#!/usr/bin/env python3
"""Check a native-dialog ABI9 replay against the saved ordinary runtime RAM."""
import json,struct,zlib,hashlib
from pathlib import Path
r=Path('tmp/runtime-later-checkpoint');b=(r/'saved.bin').read_bytes();m=json.loads((r/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base'];p=(r/'a4test.rpl').read_bytes();ptr=lambda o:struct.unpack_from('>I',b,a+o)[0]-m['memory_base']
assert len(p)==62108 and p[:8]==b'4DRPL050'
count=json.loads((r/'replay-ready.json').read_text())['consumer'];assert count==json.loads((r/'saved.json').read_text())['recorded_length']
header=struct.unpack_from('>4H5I',p,8);assert header==(1,9,50,20,1828,count,22400,7840,0),header
assert zlib.crc32(p[:-4])==struct.unpack_from('>I',p,len(p)-4)[0]
assert p[36:1864]==b[a-0x1750:a-0x1750+26]+b[ptr(-0x1778):ptr(-0x1778)+1802]
assert p[1864:1864+count]==b[ptr(-0x1770):ptr(-0x1770)+count]
assert not any(p[1864+count:31864]);h=b.index(b'4DHISTRY')+28;valid=[]
for i in range(20):
 n=p[31864+i*1120:31864+(i+1)*1120];c=p[54264+i*392:54264+(i+1)*392]
 if struct.unpack_from('>H',c)[0]:
  assert struct.unpack_from('>H',c)[0]==50;assert n==b[ptr(-0x16bc)+i*1120:ptr(-0x16bc)+(i+1)*1120];assert c==b[h+i*392:h+(i+1)*392];valid.append(i)
 else:assert not any(n+c)
assert valid==[0,1]
# Check slot1 contains the complete moving-car state captured at tick1500.
live=(r/'live-1500.bin').read_bytes()
assert struct.unpack_from('>H',live,a-0x940)[0]==1500
assert struct.unpack_from('>H',live,a-0x92e+0x2a)[0]>0
assert p[31864+1120:31864+2240]==live[a-0xa80:a-0x620]
comp=live[a+0x228:a+0x22e]
for marker,size in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
 q=live.index(marker)+12;comp+=live[q:q+size]
assert len(comp)==390 and p[54264+392+2:54264+784]==comp
p0=b.index(b'4DRPLSAV');assert struct.unpack_from('>HHII',b,p0+8)==(1,0,1,0)
report=dict(physics_abi=9,bytes=len(p),input_count=count,crc32=hex(zlib.crc32(p[:-4])),sha256=hashlib.sha256(p).hexdigest(),valid_slots=valid,unused_tail_zero=True,native_source_buffers_equal=True,scope='Ordinary runtime native Save Replay menu, filename editing and Enter. NoWriteCache enabled; host file exists and equals captured packet. No guest RAM writes. Default write-cache exit flush remains unverified.')
(r/'file-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
