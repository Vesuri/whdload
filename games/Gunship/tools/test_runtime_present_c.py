"""Direct runtime render inputs versus native endpoint publication."""
__file__=__file__.replace('test_runtime_present_c.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
setup(50)
regions=[(h[4],54),(h[4]+0x36,9),(h[4]+0x40,9),(h[5]+4,60),(h[6]+0x3904,54),(h[6]+0x157d,16)]
checking_present=False;unexpected=[]
@MEM
def published_write(handle,kind,a,n,v,user):
 if checking_present and not(ARENA<=a and a+n<=ARENA+size or 0x8e000<=a and a+n<=0x8f004 or any(start<=a and a+n<=start+length0 for start,length0 in regions)):unexpected.append((hex(a),n))
wh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(wh),1<<11,published_write,None,1,0))
c.put(h[0]+0x5c04,bytes.fromhex('4e75'))
cases=0
for rate in (50,60):
 c.put(ptr('ENDPOINT')+sym('EP_DELAY')+sym('CD_RATE'),struct.pack('>H',rate))
 for n in range(128):
  b=bytearray(rng.randbytes(86));b[54]=(2*rng.randrange(-6,11))&255;c.put(p,b);c.put(h[6]+0x157d,rng.randbytes(16));c.put(h[0]+0xc6a0,rng.randbytes(36))
  for off in (0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d):c.put(h[6]+off,rng.randbytes(1))
  native_before=c.get(low,length)
  c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x56d8,end=h[0]+0x5830)
  assert c.get(p,86)==b
  instruments=c.get(h[6]+0x157d,16)
  c.put(h[5]+10,rng.randbytes(54));c.put(h[6]+0x1548,struct.pack('>HHH',1,1,0))
  c.rw(8,0x8f000);c.call(h[0]+0x4288,end=h[0]+0x444a)
  scene=c.get(h[6]+0x3904,54);gauges=c.get(h[4]+0x36,9)
  c.put(low,native_before);c.put(ptr('ENDPOINT'),bytes(40));unexpected.clear();checking_present=True
  call('timing_runtime_present_state',{1:ARENA});checking_present=False
  assert not unexpected,unexpected
  assert c.get(h[4],54)==c.get(h[5]+10,54)==c.get(h[6]+0x3904,54)==scene
  assert c.get(h[5]+4,6)==scene[:6]
  assert c.get(h[6]+0x157d,16)==instruments
  assert c.get(h[4]+0x36,9)==c.get(h[4]+0x40,9)==gauges
  assert c.get(p,86)==b
  expected=bytearray(native_before)
  for start,size0 in regions:expected[start-low:start-low+size0]=c.get(start,size0)
  assert c.get(low,length)==expected
  before=c.get(low,length),c.get(ptr('ENDPOINT'),164);call('timing_runtime_present_state',{1:ARENA});assert (c.get(low,length),c.get(ptr('ENDPOINT'),164))==before
  cases+=1
# Independent fractional-angle oracle; no full-byte camera staircase.
for n in range(256):
 b=bytearray(rng.randbytes(86));c.put(p,b);fh,fp,fr=[rng.randrange(1360) for _ in range(3)]
 for off,value in ((20,fh),(28,fp),(32,fr)):c.put(ptr('ENDPOINT')+off,struct.pack('>I',value))
 call('timing_runtime_present_state',{1:ARENA})
 negpitch=(-b[54])&255;negpitch=negpitch if negpitch<128 else negpitch-256
 want=struct.pack('>3H',(-(((b[53]+b[26])&255)*256+fh*256//1360))&65535,(negpitch*128-fp*128//1360)&65535,((((-b[55])&255)*256)-fr*256//1360)&65535)
 assert c.get(h[6]+0x390a,6)==want
# Invalid admission writes nothing; invalid fractions never publish native inputs.
for address,width,value in [(ARENA,4,0),(ptr('CAPTURE_OWNER'),2,0),(ptr('VIEW_PHASE'),2,2),(ptr('BOUNDARY_PHASE'),2,4),(ptr('BATCH'),2,1),(ptr('SCHEDULER')+12,2,1),(ptr('SCHEDULER')+16,2,1),(ptr('SCHEDULER')+20,2,1),(ptr('CLOCK')+26,2,1),(ptr('HISTORY')+4,2,0),(ptr('COMMANDS')+8,2,1)]:
 saved=c.get(address,width);c.put(address,value.to_bytes(width,'big'));before=c.get(ARENA,size),c.get(low,length)
 call('timing_runtime_present_state',{1:ARENA},0xfffffffd);assert (c.get(ARENA,size),c.get(low,length))==before;c.put(address,saved)
for off in (20,28,32):
 saved=c.get(ptr('ENDPOINT')+off,4);c.put(ptr('ENDPOINT')+off,struct.pack('>I',1360));before=c.get(low,length)
 call('timing_runtime_present_state',{1:ARENA},0xffffffff);assert c.get(low,length)==before;c.put(ptr('ENDPOINT')+off,saved)
setup(50);call('timing_runtime_present_state',{1:ARENA});old=c.get(h[6]+0x390a,6)
publish(1,0);assert pump()==0;call('timing_runtime_present_state',{1:ARENA});assert c.get(h[6]+0x390a,6)!=old and long(ptr('SCHEDULER')+36)==0
print(json.dumps(dict(status='passed',native_endpoint_cases=cases,fractional_camera_cases=256,first_field_camera_changes=True,write_ranges_checked=True)));c.close()
