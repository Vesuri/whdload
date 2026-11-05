#!/usr/bin/env python3
"""Native world ground block extraction and side-effect/ABI checks."""
import json,random,struct,re
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/player-ground.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/player-ground.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
rng=random.Random(0x95a0);p=0x320000;code=0x330000;ref=0x340000;counter=0x350000;calls=0
c.put(ref,c.get(h[0]+0x95a0,0x96)+bytes.fromhex('4e75'))
# Preserve notification call and argument; actual UI routine has separate scope.
c.put(h[0]+0xa150,bytes.fromhex('52b9')+struct.pack('>I',counter)+bytes.fromhex('23c0')+struct.pack('>I',counter+4)+bytes.fromhex('4e75'))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 for r,v in regs.items():
  if r!=9:assert c.rr(r)==v,(name,r)
 return c.rr(9)
assert call('ground_prepare',{1:h[0],2:code,3:h[6]})==0
assert c.get(code,0x98)==c.get(ref,0x98)
notifications=0;crashes=set();shadow=0x380000;resets=0
for n in range(10000):
 b=bytearray(rng.randrange(256) for _ in range(86));air=n%2
 struct.pack_into('>H',b,28,0 if n%3 else rng.randrange(1,65536))
 b[0x18]=0 if n%4 else b[0x18];b[0x52]=0 if n%4 else b[0x52]
 rate=[3,50,60][n%3];sh=bytearray(76)
 for off in [0,12,36,56]:struct.pack_into('>H',sh,off,rate)
 struct.pack_into('>h',sh,2,rng.randrange(-1,2))
 for off in [58,72]:struct.pack_into('>H',sh,off,rng.randrange(2))
 if rate!=3:
  for off in [4,8,24,32,44,52,64,68]:struct.pack_into('>i',sh,off,rng.randrange(1-rate,rate))
  for off in [16,20,28,40,48]:struct.pack_into('>i',sh,off,rng.randrange(-32766,32767))
  struct.pack_into('>I',sh,60,rng.randrange(rate))
 c.put(shadow,sh)
 timer=rng.randrange(256)
 c.put(p,b);c.put(counter,bytes(8));c.put(h[6]+0x42f6,bytes([timer]))
 if b[28:30]==bytes(2):
  c.rw(6,p);c.rw(11,255 if air else 0);c.rw(8,0x8f000);c.call(ref)
 expected=(c.get(p,86),c.get(counter,8),c.get(h[6]+0x42f6,1))
 c.put(p,b);c.put(counter,bytes(8));c.put(h[6]+0x42f6,bytes([timer]))
 reset=int(b[28:30]==bytes(2));resets+=reset
 assert call('player_ground_step',{1:shadow,2:p,3:code,9:air})==reset
 want=bytearray(sh)
 if reset:
  for off in [4,8,16,20,24,60]:want[off:off+4]=bytes(4)
  want[58:60]=bytes(2)
 assert c.get(shadow,76)==want,n
 assert expected==(c.get(p,86),c.get(counter,8),c.get(h[6]+0x42f6,1)),n
 if int.from_bytes(expected[1][:4],'big'):
  assert expected[1]==struct.pack('>II',1,7);notifications+=1
 crashes.add(expected[0][0x52])
for flag in [2,255,0xffffffff]:
 before=(c.get(p,86),c.get(counter,8),c.get(h[6]+0x42f6,1))
 shadow_before=c.get(shadow,76)
 assert call('player_ground_step',{1:shadow,2:p,3:code,9:flag})==0xffffffff
 assert c.get(shadow,76)==shadow_before
 assert before==(c.get(p,86),c.get(counter,8),c.get(h[6]+0x42f6,1))
# Every validated boundary/call/timer byte fails closed on corruption.
invalid=0
for off in list(range(6))+list(range(0x48,0x4e))+list(range(0x54,0x5c))+list(range(0x86,0x96)):
 addr=h[0]+0x95a0+off;old=c.get(addr,1);c.put(addr,bytes([old[0]^1]));before=c.get(code,0x98)
 assert call('ground_prepare',{1:h[0],2:code,3:h[6]})==0xffffffff,off
 assert c.get(code,0x98)==before;c.put(addr,old);invalid+=1
r=dict(native_cases=10000,shadow_resets=resets,notification_cases=notifications,invalid_flags=3,signature_rejections=invalid,calls=calls,scope='native ground consequences plus fractional reset ownership; airborne/invalid leave shadow unchanged; notification UI stubbed')
(root/'tmp/c/player-ground-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
