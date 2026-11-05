"""Exercise the release heading routine and PAL/NTSC endpoint owner."""
from unicorn_b import *
from amitools.binfmt.Relocate import Relocate
import json
results=[]
for name,game,rate in [('Gunship','Gunship',50),('GunshipNTSC','GunshipNTSC',60)]:
 c=CPU()
 release=root/'tmp/build/release'/f'{name}.Slave'
 c.put(base,bytes(BinFmt().load_image(str(release)).get_segments()[0].get_data()))
 listing=release.with_suffix('.lst').read_text(encoding='latin1')
 syms={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',listing,re.M)}
 def call(n,args):
  for r,v in args.items(): c.rw(r,v)
  c.rw(8,0x8f000);c.call(base+syms[n]);assert c.rr(9)==0,(n,hex(c.rr(9)))
 HG=0x500000;P=0x510000
 cases=0
 for bank in range(-128,128):
  for heading in (0,1,127,128,254,255):
   b=bytearray(86);struct.pack_into('>H',b,28,1024);b[54]=10;b[55]=bank&255;b[53]=b[61]=heading
   c.put(P,b);call('heading_init',{1:HG,9:3})
   call('heading_step',{1:HG,2:P,9:heading,10:heading,11:0})
   actual=c.get(P,86)
   turn=abs(bank)//4 * (-1 if bank<0 else 1)
   assert actual[53]==(heading+turn)&255,(name,bank,heading,actual[53])
   if abs(bank)<4: assert actual[61]==heading
   cases+=1
 # Complete real endpoint intervals (field-rate controls and motion), including
 # small-bank reversal and byte wrap. No damage or injected yaw.
 image=BinFmt().load_image(str(root/'tmp/game'/game/'data/gamemule'))
 h=[0x300000+i*0x10000 for i in range(9)]
 for addr,data in zip(h,Relocate(image).relocate(h)):c.put(addr,data)
 ST=0x600000;EP=0x610000;PACK=0x620000
 call('motion_stages_prepare',{1:h[0],2:ST});c.put(PACK,bytes(10))
 fields=0
 for heading in (0,128,255):
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024)
  b[27]=128;b[53]=b[61]=heading;b[54]=10;b[57]=30;b[66]=28
  c.put(P,b);call('endpoint_player_init',{1:EP,9:rate,10:0})
  stamp=0
  for tick,bank in enumerate((0,1,2,3,2,1,0,-1,-2,-3,-2,-1,0),1):
   span=(tick*rate+2)//3-((tick-1)*rate+2)//3
   c.put(P+55,bytes([bank&255]))
   call('endpoint_player_begin',{1:EP,2:P,9:span,10:tick})
   for _ in range(span):
    stamp+=1
    call('endpoint_player_step',{1:EP,2:P,3:ST,4:h[0]+syms['GS0_7a44'],5:PACK,9:stamp})
    assert c.get(P+53,1)[0]==heading,(name,tick,stamp,bank,c.get(P+53,1).hex())
    assert c.get(P+61,1)[0]==heading
    fields+=1
 results.append(dict(release=name,bank_cases=cases,small_bank_reversal_fields=fields,rate=rate))
 c.close()
print(json.dumps(results,indent=2))
