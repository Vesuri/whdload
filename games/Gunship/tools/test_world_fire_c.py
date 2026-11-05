"""Native edge-counter collapse and scheduled press retention without held repeats."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-fire.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-fire.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
TS=0x300000;TC=0x301000;TH=0x302000;CQ=0x304000;OUT=0x305000;S=0x306000;REC=0x307000
rng=random.Random(0x4e4c);calls=0

def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
def init(rate):
 assert call('clock_init',{1:TC,9:0,10:rate})==0
 assert call('history_init',{1:TH,9:0})==0
 assert call('commands_init',{1:CQ,9:0})==0
 assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
init(50);c.put(TS+12,b'\0\2');native=0
for first in [0,1,2,32767,32768,65535]:
 for second in [0,1,2,32767,32768,65535]:
  for held in range(4):
   c.put(h[0]+0x4e26,struct.pack('>HH',first,second));c.put(h[6]+0x4292,b'\x88\x99')
   c.rw(8,0x8f000);c.call(h[0]+0x4e4c,end=h[0]+0x4e88)
   expected=c.get(h[6]+0x4292,2)
   c.put(TS+40,struct.pack('>IH',held,(1 if first else 0)|(2 if second else 0)|0xfffc))
   c.put(OUT,b'\xaa\xbb');before=c.get(TS,48)
   assert call('world_fire_prepare',{1:TS,2:OUT})==0
   assert c.get(OUT,2)==expected and c.get(TS,48)==before
   native+=1
runs=[]
for rate in [50,60]:
 for tape in ['brief','held']:
  baseline=None
  for batch in [1,25]:
   init(rate);results=[]
   for start in range(1,121,batch):
    for f in range(start,min(start+batch,121)):
     held=1 if (f==2 if tape=='brief' else 2<=f<90) else 0
     # Fire sampler edges are stamped at the next field, as native ordering dictates.
     edges=1 if f==3 else 0
     b=bytearray(40);struct.pack_into('>I',b,0,f);struct.pack_into('>I',b,12,held);struct.pack_into('>H',b,30,edges)
     c.put(S,b);assert call('history_publish',{1:TH,2:S})==1
    assert call('scheduler_begin',{1:TS,9:128,10:8})==0
    while True:
     got=call('scheduler_next',{1:TS,2:REC})
     if not got:break
     assert got==1
     if call('scheduler_player_done',{1:TS})==1:
      assert call('world_fire_prepare',{1:TS,2:OUT})==0
      results.append((int.from_bytes(c.get(TS+24,4),'big'),c.get(OUT,2)))
      assert call('scheduler_world_done',{1:TS})==0
   assert results[0][1]==b'\1\0' and all(flags==b'\0\0' for f,flags in results[1:])
   if baseline is None:baseline=results
   else:assert results==baseline
   runs.append((rate,tape,batch,len(results)))
for phase,fault in [(0,False),(1,False),(2,True)]:
 init(50);c.put(TS+12,struct.pack('>H',phase));c.put(OUT,b'\xaa\xbb')
 if fault:c.put(TH+6,b'\0\1')
 assert call('world_fire_prepare',{1:TS,2:OUT})==(0xffffffff if fault else 0xfffffffd)
 assert c.get(OUT,2)==b'\xaa\xbb'
print(json.dumps(dict(status='passed',native_cases=native,scheduled_runs=runs,rejections=3,calls=calls)))
c.close()
