source=open(__file__.replace('test_runtime_lifecycle_c.py','test_timing_runtime_c.py')).read()
exec(source.split("c.put(ARENA-16,")[0].split('# Loader-facing lookup')[0])
# All checks use the real runtime preparation and initialized pointer bindings.
c.put(ARENA-16,b'\xa5'*(size+32));c.put(p+24,bytes(1));c.put(h[2]+0x0c,bytes(4));prepare(50)
fifo=h[6]+0x4c68
c.put(fifo,struct.pack('>11HI',*range(11),3))
c.put(h[2]+0x1c,struct.pack('>I',0xfffffff0));c.put(h[2]+0x0c,b'\0\0\0\xff');c.put(ptr('CAPTURE')+24,struct.pack('>I',0xfffffffd))
c.put(ptr('CAPTURE')+28,bytes.fromhex('7fffffff8000000000030000'))
c.put(ptr('MODE'),bytes(2));c.put(p+66,b'\x1c')
def snap():return c.get(ARENA,size),c.get(low,length)
def reject():
 before=snap();call('timing_runtime_activate',{1:ARENA},0xfffffffd);assert snap()==before
# Atomic rejection at every externally meaningful unfinished boundary.
for a,width,values in [
 (ARENA,4,[0]),(ptr('CAPTURE_OWNER'),2,[1,2]),
 (ptr('CLOCK')+24,2,[1]),(ptr('HISTORY')+4,2,[1]),(ptr('COMMANDS')+6,2,[1]),
 (ptr('SCHEDULER')+12,2,[1,2]),(ptr('EVENT'),4,[1,0x0007b401]),
 (ptr('CLOCK')+22,2,[3,49,61]),(ptr('CONSUMER')+60,2,[1,2,3,5,7]),
 (ptr('BODY')+28,2,[1,4]),(ptr('MODAL')+12,2,[1,2,3]),
 (h[5]+0x60,4,[h[6]+2]),(fifo+22,4,[11,0xffffffff]),
 (p+24,1,[1]),(h[2]+0xf,1,[2,254])]:
 saved=c.get(a,width)
 for value in values:c.put(a,value.to_bytes(width,'big'));reject()
 c.put(a,saved)
# Stale successful metadata must not leak into a new epoch.
for name,offset,size0 in [('PLAYER_READER',12,12),('WORLD_READER',16,12),('FIELD',16,8),('START',12,8),('IMPULSES',20,18),('PLAYER',24,6),('GEOMETRY',16,10)]:c.put(ptr(name)+offset,b'\x55'*size0)
c.put(ptr('CONSUMER')+60,struct.pack('>HHI',4,9,17));c.put(ptr('BODY')+28,b'\0\2');c.put(ptr('MODAL')+12,b'\0\4')
c.put(ptr('FIRE'),b'\1\1');c.put(ptr('HEADING'),b'\xff\0');c.put(ptr('PENDING'),b'\1\0');c.put(ptr('CAMERA'),b'\x55'*12)
c.put(ptr('PACKET'),b'\x55'*10);c.put(ptr('RECORD'),b'\x55'*40);c.put(ptr('SAMPLE'),b'\x55'*40)
c.put(ptr('ENDPOINT'),struct.pack('>10I',*([680]*10)))
c.put(ptr('GUIDANCE_PRESENT')+16,b'\x55'*42)
clones=c.get(ptr('STAGES'),sym('RT_GUIDANCE_PRESENT')-sym('RT_STAGES'));native_before=bytearray(c.get(low,length));native_before[fifo-low:fifo-low+26]=bytes(26)
assert long(ptr('PLAYER')+sym('SE_CACHE'))==ptr('PLAYER_CACHE')
c.put(ptr('PLAYER_CACHE'),b'\x00\x01')
call('timing_runtime_activate',{1:ARENA})
assert word(ptr('PLAYER_CACHE'))==0
assert long(ptr('PLAYER')+sym('SE_CACHE'))==ptr('PLAYER_CACHE')
assert c.get(low,length)==native_before and c.get(ptr('STAGES'),len(clones))==clones
assert word(ptr('GUIDANCE_PRESENT')+56)==3
assert c.get(ptr('GUIDANCE_PRESENT')+24,8)==b'\xff\xff\xff\xe0'*2
assert c.get(ptr('GUIDANCE_PRESENT')+44,8)==b'\xff\xff\xff\xe0'*2
assert long(ptr('NATIVE_DISCARDED'))==3 and word(ptr('CAPTURE_OWNER'))==1 and c.get(ptr('CAPTURE')+28,10)==bytes(10)
assert long(ptr('CLOCK'))==0xfffffff0 and long(ptr('COMMANDS')+12)==0xfffffffd and word(ptr('MODE'))==1
for name,offset,size0 in [('PLAYER_READER',12,12),('WORLD_READER',16,12),('FIELD',16,8),('START',12,8),('IMPULSES',20,18),('PLAYER',24,6),('GEOMETRY',16,10),('CONSUMER',60,8),('BODY',28,2),('MODAL',12,2)]:assert c.get(ptr(name)+offset,size0)==bytes(size0),(name,'stale')
assert c.get(ptr('ENDPOINT'),40)==bytes(40) and c.get(ptr('ENDPOINT')+52,20)==b'\xff'*20
reject()
# Suspension preserves pending work while giving the native FIFO back.
c.put(ptr('SCHEDULER')+12,b'\0\2');c.put(ptr('BODY')+28,b'\0\1')
call('timing_runtime_suspend',{1:ARENA})
assert word(ptr('CAPTURE_OWNER'))==0 and word(ptr('SCHEDULER')+12)==2 and word(ptr('BODY')+28)==1
assert word(ptr('CLOCK')+24)==word(ptr('HISTORY')+4)==word(ptr('COMMANDS')+6)==0
reject();before=snap();call('timing_runtime_suspend',{1:ARENA});assert snap()==before
# Explicitly resolved world ownership permits the next epoch without replay caches.
c.put(ptr('SCHEDULER')+12,bytes(2));c.put(ptr('BODY')+28,b'\0\2')
c.put(h[2]+0x1c,struct.pack('>I',5000));c.put(h[2]+0x0c,bytes(4))
call('timing_runtime_activate',{1:ARENA});assert long(ptr('CLOCK'))==5000 and long(ptr('NATIVE_DISCARDED'))==3
print(json.dumps(dict(status='passed',calls=calls,atomic_rejections=True,metadata_reset=True,native_fifo_accounted=True,clones_preserved=True)));c.close()
