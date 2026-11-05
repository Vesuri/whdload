exec(open(__file__.replace('test_endpoint_impulse_height_c.py','test_endpoint_impulse_c.py')).read().split('import itertools')[0])
import random
rng=random.Random(29);B=0x3d0000;I=0x3e0000
for actual,base_height,impulse_height in [(0,1,0),(32767,0,1)]:
 c.put(OWNER,bytes(164));c.put(OWNER+158,struct.pack('>HH',20,20));c.put(OWNER+8,struct.pack('>I',777))
 for addr,height in [(LIVE,actual),(B,base_height),(I,impulse_height)]:
  b=bytearray(86);struct.pack_into('>H',b,28,height);c.put(addr,b)
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:OWNER,2:LIVE,3:B,4:I})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym('endpoint_impulse_apply'))
 assert c.rr(9)==0 and c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 assert c.get(LIVE+28,2)==bytes(2) and c.get(OWNER+8,4)==bytes(4)
 assert int.from_bytes(c.get(B+28,2),'big')==base_height and int.from_bytes(c.get(I+28,2),'big')==impulse_height
print(dict(native_height_floor_cases=2,registers_preserved=True,candidates_read_only=True));c.close()
