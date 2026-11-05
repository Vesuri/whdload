"""Certified scripted XYZ fractions, identity barriers and world isolation."""
from pathlib import Path
exec(Path(__file__).with_name('test_script_preview_c.py').read_text().split('for case in range(1800):')[0])
ps=bytearray(0x2d6)
for off,value in zip(pose_offsets,bytes.fromhex('100020003000400102')): ps[off]=value
cache=0x160000;gen=0x161000;out=0x162000
frames=barriers=0
for rate in (50,60):
 for anchor in range(3):
  c.put(p,ps);c.put(gen,struct.pack('>I',7)+bytes(22));c.put(cache,bytes(36));c.put(bitmap+8,struct.pack('>I',planes[0]))
  before=c.get(low,length)
  call('script_present_capture',{1:cache,2:spv,3:gen,4:p,5:bitmap,6:palette,9:19,10:anchor},1)
  assert c.get(low,length)==before
  current=c.get(cache+sym('SPC_CURRENT'),7);nextpose=c.get(cache+sym('SPC_NEXT'),7)
  assert current==nextpose # first capture snaps
  for off in pose_offsets[:7]:ps[off]=(ps[off]+1)&255
  c.put(p,ps);c.put(gen,struct.pack('>I',8)+bytes(22))
  call('script_present_capture',{1:cache,2:spv,3:gen,4:p,5:bitmap,6:palette,9:20,10:anchor},1)
  c.put(cache+sym('SPC_TICK'),struct.pack('>I',19))
  current=c.get(cache+sym('SPC_CURRENT'),7);nextpose=c.get(cache+sym('SPC_NEXT'),7)
  assert current!=nextpose
  # Rendering is independent of both preview scratch and bitmap lifetime.
  saved=c.get(spv,size);c.put(spv,bytes(size));c.put(bitmap+8,bytes(4))
  for phase in range(anchor,rate,3):
   native=c.get(low,length);snapshot=c.get(cache,36);elapsed=(phase-anchor)//3;interval=(rate-anchor+2)//3
   want=bytearray()
   for v,n in zip(struct.unpack('>3H',current[:6]),struct.unpack('>3H',nextpose[:6])):
    delta=((n-v+32768)&65535)-32768;want+=struct.pack('>H',(v+delta*elapsed//interval)&65535)
   delta=((nextpose[6]-current[6]+128)&255)-128
   want+=bytes([(current[6]+delta*elapsed//interval)&255])
   for repeat in range(2):
    call('script_present_build',{1:cache,2:gen,3:out,4:p,9:19,10:phase,11:rate},1)
    assert c.get(out,7)==want and c.get(cache,36)==snapshot and c.get(low,length)==native
   frames+=1
  c.put(spv,saved)
  for offset in pose_offsets:
   old=c.get(p+offset,1);c.put(p+offset,bytes([old[0]^1]));expected=bytes(c.get(p+o,1)[0] for o in pose_offsets[:6])
   call('script_present_build',{1:cache,2:gen,3:out,4:p,9:19,10:anchor+3,11:rate},0)
   assert c.get(out,6)==expected;c.put(p+offset,old);barriers+=1
  for addr,data in [(gen,struct.pack('>I',9)),(gen+24,b'\0\1'),(cache+sym('SPC_VALID'),b'\0\0')]:
   old=c.get(addr,len(data));c.put(addr,data)
   call('script_present_build',{1:cache,2:gen,3:out,4:p,9:19,10:anchor+3,11:rate},0)
   assert c.get(out,7)==current;c.put(addr,old);barriers+=1
  for tick,phase in [(20,anchor),(19,anchor+1)]:
   call('script_present_build',{1:cache,2:gen,3:out,4:p,9:tick,10:phase,11:rate},0)
   assert c.get(out,7)==current;barriers+=1
  for phase,hz in [(rate,rate),(0,49),(0,61),(0xffffffff,rate)]:
   before=c.get(out,6)
   call('script_present_build',{1:cache,2:gen,3:out,4:p,9:19,10:phase,11:hz},0xfffffffd)
   assert c.get(out,6)==before
print(json.dumps(dict(status='passed',fraction_frames=frames,repeated_frames=frames,identity_clock_barriers=barriers,native_writes=0)))
c.close()
