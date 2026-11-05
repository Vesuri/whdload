from unicorn_b import *
import random
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/endpoint-camera.hunk')).get_segments()[0].get_data()))
lst=(root/'tmp/c/endpoint-camera.lst').read_text();sym=lambda n:base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',lst,re.M)[1],16)
rng=random.Random(1360);P=0x330000;S=0x340000;CAM=0x350000;cases=0
sb=lambda x:x-256 if x&128 else x
for rate in [3,50,60]:
 for pitch in range(256):
  for rem in [0,272,1359] if rate!=3 else [0]:
   b=bytearray(rng.randbytes(86));b[54]=pitch;state=bytearray(164);struct.pack_into('>H',state,40,rate)
   rs=[rem,rng.randrange(1360) if rate!=3 else 0,rng.randrange(1360) if rate!=3 else 0]
   for off,val in zip([20,28,32],rs):struct.pack_into('>I',state,off,val)
   c.put(P,b);c.put(S,state);original=rng.randbytes(12);c.put(CAM,original)
   regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:P,2:S,3:CAM})
   for r,v in regs.items():c.rw(r,v)
   c.rw(8,0x8f000);c.call(sym('endpoint_camera_angles'));cases+=1
   assert c.rr(9)==0 and c.rr(18)==0x90000 and c.rr(8)==0x8f004
   assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
   heading=-(((b[53]+b[26])%256)*256+rs[0]*256//1360)
   half=(sb((-pitch)%256)>>1)*256 if rate==3 else sb((-pitch)%256)*128-rs[1]*128//1360
   roll=((-b[55])%256)*256-rs[2]*256//1360
   expected=original[:6]+struct.pack('>HHH',heading&65535,half&65535,roll&65535)
   assert c.get(CAM,12)==expected,(rate,pitch,rs)
   assert c.get(P,86)==b and c.get(S,164)==state
for rate,off,value in [(0,20,0),(3,20,1),(3,28,1),(3,32,1),(50,20,1360),(50,28,0xffffffff),(60,32,1360)]:
 state=bytearray(164);struct.pack_into('>H',state,40,rate);struct.pack_into('>I',state,off,value);c.put(S,state);before=c.get(CAM,12)
 for r,v in {1:P,2:S,3:CAM}.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym('endpoint_camera_angles'));assert c.rr(9)==0xffffffff and c.get(CAM,12)==before
# A 1/5-unit roll contribution already changes the camera angle by 51 units.
c.put(P,bytes(86));state=bytearray(164);struct.pack_into('>H',state,40,60);struct.pack_into('>I',state,32,272);c.put(S,state)
for r,v in {1:P,2:S,3:CAM}.items():c.rw(r,v)
c.rw(8,0x8f000);c.call(sym('endpoint_camera_angles'));assert c.get(CAM+10,2)==struct.pack('>H',(-51)&65535)
print(dict(angle_cases=cases,rejections=7,fractional_roll_visible_in_camera=True,state_read_only=True));c.close()
# Production damage-yaw adapter: only camera yaw may change.
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data())
listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
symbol=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
A=0x300000;H6=0x400000;cases=0
for rate in (50,60):
 for impulse in (-2,-1,0,1,2):
  for age in range(22):
   c=CPU();c.put(base,blob);state=bytearray(symbol('RT_ARENA_SIZE'))
   struct.pack_into('>I',state,symbol('RT_HUNKS')+24,H6)
   struct.pack_into('>H',state,symbol('RT_CLOCK')+symbol('TC_RATE'),rate)
   struct.pack_into('>H',state,symbol('RT_IMPULSES')+symbol('SI_VALID'),1)
   struct.pack_into('>h',state,symbol('RT_IMPULSES')+symbol('SI_CACHE')+4,impulse)
   struct.pack_into('>I',state,symbol('RT_IMPULSES')+symbol('SI_FIELD'),0xfffffff8)
   struct.pack_into('>I',state,symbol('RT_RECORD')+symbol('TR_FIELD'),(0xfffffff8+age)&0xffffffff)
   struct.pack_into('>H',state,symbol('RT_CAMERA')+6,12345)
   c.put(A,state);c.put(H6+0x3ba4,b'\0\x30');c.put(H6+0x3b96,b'\0\x02')
   regs={r:0x543210+r for r in range(1,17) if r!=8};regs[1]=A
   for r,v in regs.items():c.rw(r,v)
   c.rw(8,0x8f000);c.call(base+symbol('timing_runtime_damage_yaw'))
   span=rate//6;delta=int(impulse*256*max(0,span-age)/span)
   expected=bytearray(state);struct.pack_into('>H',expected,symbol('RT_CAMERA')+6,(12345+delta)&65535)
   assert c.get(A,len(state))==expected,(rate,impulse,age)
   assert all(c.rr(r)==v for r,v in regs.items())
   assert c.get(H6+0x3b96,2)==b'\0\x02'
   c.close();cases+=1
print(dict(damage_yaw_cases=cases,only_camera_changes=True,max_smoothing_ms=[160,1000/6]))
