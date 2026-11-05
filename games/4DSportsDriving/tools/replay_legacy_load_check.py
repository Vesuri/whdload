#!/usr/bin/env python3
"""Check that the native loader preserved recorded inputs in a fresh process."""
import argparse,json,struct,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('source',type=Path);a=p.parse_args()
m=json.loads((a.capture/'anchor.json').read_text());b=(a.capture/'replay-clock-start.bin').read_bytes();packet=(a.source/'A4000-native-direct.rpl').read_bytes();rate=packet[22];count=struct.unpack_from('>H',packet,24)[0]
assert rate in (10,20) and len(packet)==1828+count
q=b.index(b'4DRPLLEG');assert struct.unpack_from('>HHIH',b,q+8)==(1,rate,1,count)
q=b.index(b'4DRPLMNU');assert struct.unpack_from('>HH4IH',b,q+8)==(1,0,0,1,0xffffffff,0,0)
aa=m['data_base']+0x7ffe-m['memory_base'];u16=lambda off:struct.unpack_from('>H',b,aa+off)[0];ptr=lambda off:struct.unpack_from('>I',b,aa+off)[0]-m['memory_base']
assert b[aa+0x45]==2 and u16(-0x15fa)==rate and u16(-0x1738)==count
assert b[ptr(-0x1770):ptr(-0x1770)+count]==packet[1828:]
assert b[ptr(-0x1778):ptr(-0x1778)+1802]==packet[26:1828]
for marker,size in [(b'4DA4PHYS',128),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
 q=b.index(marker)+12;assert not any(b[q:q+size]),marker
r=dict(rate=rate,input_count=count,native_file_bytes=len(packet),inputs_exact=True,tracks_exact=True,tagged_install_not_used=True,a4000_fractions_zero=True,sha256=hashlib.sha256(packet).hexdigest())
(a.capture/'legacy-load-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
