#!/usr/bin/env python3
"""Check actual native save files against their source arrays and guards."""
import argparse,json,struct,zlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();m=json.loads((a.capture/'anchor.json').read_text())
i=b.index(b'4DRPLSVT');assert struct.unpack_from('>HHI',b,i+8) in ((1,3,3),(2,3,3))
i=b.index(b'4DRPLSAV');assert struct.unpack_from('>HH2I',b,i+8)==(1,0,2,0)
size=61628;passed=3
g=b.index(b'MNU1');assert b[g+4+61630:g+8+61630]==b'MNU2'
assert b[g+8+2*61630:g+12+2*61630]==b'SAVE'
saved=Path('tmp/run/default/.run/dh1/data')
packet=(saved/'A4000-native-direct.rpl').read_bytes()
assert packet==(saved/'A4000-native-dialog.rpl').read_bytes()
assert (saved/'replay-other-test.dat').read_bytes()==b'TEST'
assert len(packet)==size
for name in ('A4000-native-direct.rpl','A4000-native-dialog.rpl','replay-other-test.dat'):
 (a.capture/name).write_bytes((saved/name).read_bytes())
assert packet[:8]==b'4DRPL050'
version,physics,rate,slots,prefix,count,native,private,epoch=struct.unpack_from('>4H5I',packet,8)
assert (version,physics,rate,slots,prefix,native,private)==(1,4,50,20,1828,22400,7360)
assert zlib.crc32(packet[:-4])==struct.unpack_from('>I',packet,size-4)[0]
assert 0<count<=30000 and epoch%1500==0 and epoch+count<=75000
at=m['data_base']+0x7ffe-m['memory_base'];ptr=lambda o:struct.unpack_from('>I',b,at+o)[0]-m['memory_base']
assert packet[36:60]==b[at-0x1750:at-0x1750+24]
assert struct.unpack_from('>H',packet,60)[0]==count
assert packet[62:1864]==b[ptr(-0x1778):ptr(-0x1778)+1802]
inputs=packet[1864:31864];assert inputs[:count]==b[ptr(-0x1770):ptr(-0x1770)+count]
assert not any(inputs[count:])
h=b.index(b'4DHISTRY');hv,hn,hs,_=struct.unpack_from('>4H',b,h+8);assert (hv,hn,hs)==(6,20,368)
records=h+28;valid=[]
for slot in range(20):
 ns=packet[31864+1120*slot:31864+1120*(slot+1)]
 cs=packet[54264+368*slot:54264+368*(slot+1)]
 if struct.unpack_from('>H',cs)[0]:
  assert struct.unpack_from('>H',cs)[0]==50 and ns[0x3f4]==1
  assert struct.unpack_from('>H',ns,0x140)[0]==1500*slot<count
  assert ns==b[ptr(-0x16bc)+1120*slot:ptr(-0x16bc)+1120*(slot+1)]
  assert cs==b[records+368*slot:records+368*(slot+1)]
  valid.append(slot)
 else:assert not any(ns) and not any(cs)
assert valid and valid[0]==0
(a.capture/'golden.r50').write_bytes(packet)
reference=Path('tmp/prof/sim-mode-menu50')
rb=(reference/'memory.bin').read_bytes();rm=json.loads((reference/'anchor.json').read_text())
def race(blob,meta):
 x=meta['data_base']+0x7ffe-meta['memory_base']
 ph=blob.index(b'4DA4PHYS')+12;tm=blob.index(b'4DTSTATE')+12
 aux=blob[blob.index(b'4DAUXPHY')+12:blob.index(b'4DAUXPHY')+204] if b'4DAUXPHY' in blob else bytes(192)
 return blob[x-0xa80:x-0x620]+blob[x+0x228:x+0x22e]+blob[ph:ph+128]+blob[tm:tm+32]+aux+(blob[blob.index(b'4DCAM050')+12:blob.index(b'4DCAM050')+20] if b'4DCAM050' in blob else bytes(8))
assert race(b,m)==race(rb,rm),'post-save160 state differs from reference'
r=dict(race_bytes_equal=1486,checks=passed,bytes=size,rate=rate,input_count=count,epoch=epoch,valid_slots=valid,crc32=hex(zlib.crc32(packet[:-4])),guards=True,source_buffers_match=True)
(a.capture/'replay-native-save-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
