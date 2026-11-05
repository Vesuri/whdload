#!/usr/bin/env python3
"""Execute original mission-duration conversion in PAL and NTSC binaries."""
import json
from unicorn_b import *
from amitools.binfmt.Relocate import Relocate
results={}
for version,folder in {'658':'Gunship','1489':'GunshipNTSC'}.items():
 img=BinFmt().load_image(str(root/'tmp/game'/folder/'data/gamemule'))
 addrs=[0x200000+i*0x20000 for i in range(len(img.get_segments()))]
 hunks=Relocate(img).relocate(addrs);code=bytes(hunks[0]);gb=addrs[0];tick=addrs[6]+0x3b94
 # First duration conversion reads unsigned tick count, divides by 3 then 60.
 prefix=bytes.fromhex('70003039')+struct.pack('>I',tick)+bytes.fromhex('72034eba')
 hits=[i for i in range(0,len(code)-20,2) if code[i:i+len(prefix)]==prefix]
 assert len(hits)==2, hits
 minutes,seconds=hits
 assert code[minutes+14:minutes+18]==bytes.fromhex('723c4eba')
 assert seconds-minutes==0x2a
 c=CPU()
 for a,b in zip(addrs,hunks):c.put(a,b)
 cases=sorted(set([0,1,2,3,4,178,179,180,181,182,1799,1800,10799,10800,65533,65534,65535]+[x for m in range(1,365) for x in (m*180-1,m*180,m*180+1)]))
 for n in cases:
  c.put(tick,struct.pack('>H',n));c.rw(8,0x8f000)
  c.call(gb+minutes,gb+minutes+20);assert c.rr(9)==n//180,(version,n,'minutes',c.rr(9))
  c.rw(8,0x8f000);c.call(gb+seconds,gb+seconds+0x34)
  assert c.rr(10)==n//3%60,(version,n,'seconds',c.rr(10))
 c.close()
 data=bytes(hunks[6])
 results[version]=dict(ticks_per_second=3,minutes_offset=hex(minutes),seconds_offset=hex(seconds),cases=len(cases),display_strings=[data[o:o+40].split(b'\0')[0].decode('latin1') for o in (0x78e,0x7aa)])
(root/'tmp/c/clock-contract.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
