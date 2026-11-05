#!/usr/bin/env python3
"""Check actual native save files against their source arrays and guards."""
import argparse,json,struct,zlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--format-only',action='store_true');a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();m=json.loads((a.capture/'anchor.json').read_text())
i=b.index(b'4DRPLSVT');assert struct.unpack_from('>HHI',b,i+8)==(2,3,3)
rate,tick=struct.unpack_from('>HH',b,i+16)
i=b.index(b'4DRPLSAV');assert struct.unpack_from('>HH2I',b,i+8)==(1,0,2,0)
size=61628;passed=3
g=b.index(b'MNU1');assert b[g+4+61630:g+8+61630]==b'MNU2'
assert b[g+8+2*61630:g+12+2*61630]==b'SAVE'
saved=Path('tmp/run/default/.run/dh1/data')
packet=(saved/'A4000-native-direct.rpl').read_bytes()
assert packet==(saved/'A4000-native-dialog.rpl').read_bytes()
assert (saved/'replay-other-test.dat').read_bytes()==b'TEST'
assert rate in (10,20)
count=struct.unpack_from('>H',packet,24)[0]
assert packet[22]==rate and 0<count<=rate*600 and len(packet)==1828+count
at=m['data_base']+0x7ffe-m['memory_base'];ptr=lambda o:struct.unpack_from('>I',b,at+o)[0]-m['memory_base']
assert packet[:26]==b[at-0x1750:at-0x1750+26]
assert packet[26:1828]==b[ptr(-0x1778):ptr(-0x1778)+1802]
assert packet[1828:]==b[ptr(-0x1770):ptr(-0x1770)+count]
for name in ('A4000-native-direct.rpl','A4000-native-dialog.rpl','replay-other-test.dat'):
 (a.capture/name).write_bytes((saved/name).read_bytes())
reference=Path(f'tmp/prof/sim-mode-menu{rate}')
rb=(reference/'memory.bin').read_bytes();rm=json.loads((reference/'anchor.json').read_text())
def race(blob,meta):
 x=meta['data_base']+0x7ffe-meta['memory_base']
 ph=blob.index(b'4DA4PHYS')+12;tm=blob.index(b'4DTSTATE')+12
 aux=blob[blob.index(b'4DAUXPHY')+12:blob.index(b'4DAUXPHY')+204] if b'4DAUXPHY' in blob else bytes(192)
 return blob[x-0xa80:x-0x620]+blob[x+0x228:x+0x22e]+blob[ph:ph+128]+blob[tm:tm+32]+aux+(blob[blob.index(b'4DCAM050')+12:blob.index(b'4DCAM050')+20] if b'4DCAM050' in blob else bytes(8))
if not a.format_only: assert race(b,m)==race(rb,rm),'post-save state differs from reference'
r=dict(race_bytes_equal=None if a.format_only else 1486,checks=passed,bytes=len(packet),rate=rate,tick=tick,input_count=count,guards=True,source_buffers_match=True,native_format=True)
(a.capture/'replay-native-save-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
