source=open(__file__.replace('test_timing_fifo_owner_c.py','test_timing_live_input_c.py')).read()
exec(source.split('for flags in range(32):')[0])
def init(owner=1,active=1):
 c.put(H,struct.pack('>4H3I',0,0,active,0,0,0,0))
 c.put(Q,struct.pack('>4H4I',0,0,0,1,0,10,0,0))
 c.put(M+24,struct.pack('>I',10));c.put(M+38,struct.pack('>H',owner))
def word(a):return int.from_bytes(c.get(a,2),'big')
def long(a):return int.from_bytes(c.get(a,4),'big')
checks=0
# Native register/CCR results remain exact for every FIFO depth and flags.
for flags in range(32):
 for count in range(1,11):
  init();rs=state(flags);rs.update({1:EV,9:(count-1)*2,15:0x804})
  before=struct.pack('>11HI',*range(0x100,0x10b),count);c.put(EV,before)
  c.put(REF,bytes.fromhex('3186080070564e75'));want=run(REF,rs)
  c.put(EV,before);got=run(addr('timing_live_command'),rs)
  assert got==want
  expected=bytearray(before);expected[(count-1)*2:count*2]=bytes(2);expected[22:26]=struct.pack('>I',count-1)
  assert c.get(EV,26)==expected
  assert c.get(Q+24,6)==struct.pack('>IH',11,0x804) and word(Q)==1
  checks+=1
for owner,active in [(0,1),(1,0),(2,1)]:
 init(owner,active);c.put(EV,bytes(22)+struct.pack('>I',1));rs=state(31);rs.update({1:EV,9:0,15:0x7f});run(addr('timing_live_command'),rs)
 assert word(EV)==0x7f and long(EV+22)==1 and word(Q)==1;checks+=1
# Bad native structure faults private ownership rather than guessing a repair.
for slot,count in [(20,10),(0,0),(0,11),(0,2),(0,0x80000001)]:
 init();c.put(EV,bytes(22)+struct.pack('>I',count));rs=state(31);rs.update({1:EV,9:slot,15:0x51});run(addr('timing_live_command'),rs)
 assert long(EV+22)==count and word(EV+slot)==0x51
 assert word(Q+8)==1 and word(H+6)==1 and word(Q)==1;checks+=1
# Queue overflow does not remove a key that could not be retained privately.
init();c.put(Q,struct.pack('>H',128));c.put(EV,bytes(22)+struct.pack('>I',1));rs=state(31);rs.update({1:EV,9:0,15:0x51});run(addr('timing_live_command'),rs)
assert word(Q+8)==1 and word(EV)==0x51 and long(EV+22)==1;checks+=1
# Run the actual native producer repeatedly: no artificial count increments.
from amitools.binfmt.Relocate import Relocate
img=BinFmt().load_image(str(root/'tmp/game/Gunship/data/gamemule'))
addresses=[H0+i*0x20000 for i in range(len(img.get_segments()))];native=bytes(Relocate(img).relocate(addresses)[0]);c.put(H0,native)
c.put(H0+0x34c8,bytes.fromhex('4eb9')+struct.pack('>I',addr('timing_live_command')))
H2=addresses[2];c.put(H2+0x26,struct.pack('>I',EV));a4=0x570000;fifo=a4+0x4c68
init();c.put(fifo,bytes(26))
for n in range(1,257):
 key=0x51 if n%2 else 0x38;modifier=8 if n%3==0 else 0
 c.put(EV+4,b'\xff\0'+struct.pack('>HH',key,modifier))
 rs=state(n%32);rs[5]=a4;run(H0+0x3488,rs)
 assert long(fifo+22)==0 and word(fifo)==0
 cursor=word(Q);assert cursor==n
 off=Q+24+((n-1)&127)*8
 assert c.get(off,6)==struct.pack('>IH',10+n,key|(modifier<<8))
 c.put(Q+2,struct.pack('>HH',cursor,cursor))
 checks+=1
print(json.dumps(dict(status='passed',checks=checks,native_producer_keys=256,abi_cases=320)));c.close()
