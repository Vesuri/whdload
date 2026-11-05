"""Reprepare one arena across relocated native images; execute cached motion."""
source=open(__file__.replace('test_runtime_relocation_c.py','test_timing_runtime_c.py')).read()
exec(source.split('# Loader-facing lookup')[0])
from amitools.binfmt.Relocate import Relocate
import hashlib
image=BinFmt().load_image(str(root/'tmp/game/Gunship/data/gamemule'))
layouts=[[0x200000+i*0x20000 for i in range(9)],
         [0x400000+((i*5)%9)*0x20000 for i in range(9)],
         [0x780000+((i*7)%9)*0x20000 for i in range(9)]]
forbidden=[];old_access=[];watch_old=False
@MEM
def stale(handle,kind,a,n,value,user):
 if watch_old and any(lo<=a<hi or lo<a+n<=hi for lo,hi in forbidden):old_access.append((kind,hex(a),n))
old_hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(old_hook),(1<<10)|(1<<11)|(1<<12),stale,None,1,0))
rows=[]
for rate in (50,60):
 baseline=None;previous=[]
 for index,addresses in enumerate(layouts):
  hunks=Relocate(image).relocate(addresses)
  # Poison retired game storage. A memory hook also detects stale reads,
  # writes or instruction fetches even if poison happens to be harmless.
  for address,n in previous:c.put(address,b'\xa5'*n)
  for address,blob in zip(addresses,hunks):c.put(address,blob)
  forbidden=[(a,a+n) for a,n in previous]+[(low,low+length)]
  old_access.clear();watch_old=True
  c.put(TABLE,struct.pack('>9I',*addresses))
  native_before=[c.get(a,len(b)) for a,b in zip(addresses,hunks)]
  if index==0:c.put(ARENA-16,b'\xa5'*(size+32))
  # Later cases reuse the preceding retired arena, without host clearing.
  call('timing_runtime_prepare',{1:ARENA,2:TABLE,9:rate})
  assert [c.get(a,len(b)) for a,b in zip(addresses,hunks)]==native_before
  assert c.get(ptr('HUNKS'),36)==struct.pack('>9I',*addresses)
  assert word(ptr('PLAYER_CACHE'))==0
  # Minimal native initialization needed for activation and player motion.
  pp=addresses[6]+0x3b88
  player=bytearray(86);struct.pack_into('>HH',player,0,0x7000,0x8000)
  struct.pack_into('>H',player,28,1024);player[27]=128;player[57]=30;player[66]=28
  c.put(pp,player);c.put(addresses[5]+0x60,struct.pack('>I',addresses[6]))
  c.put(addresses[6]+0x4c68,bytes(26));c.put(addresses[2]+0x0c,bytes(4));c.put(addresses[2]+0x1c,struct.pack('>I',1000))
  call('timing_runtime_activate',{1:ARENA})
  assert word(ptr('CAPTURE_OWNER'))==1 and word(ptr('PLAYER_CACHE'))==0
  digest=hashlib.sha256();poses=[];last=0
  for field in range(1,rate*2+1):
   tick=(field-1)*3//rate+1
   if tick!=last:
    span=(tick*rate+2)//3-((tick-1)*rate+2)//3
    call('endpoint_player_begin',{1:ptr('ENDPOINT'),2:pp,9:span,10:tick});last=tick
   x=1 if field%41 in range(5,10) else -1 if field%59 in range(19,24) else 0
   y=-1 if field%47 in range(6,13) else 0
   c.put(ptr('PACKET'),struct.pack('>hhhhh',x,y,0,0,0))
   call('endpoint_player_step_cached',{1:ptr('ENDPOINT'),2:pp,3:ptr('STAGES'),4:addresses[0]+0x7a44,5:ptr('PACKET'),6:ptr('PLAYER_CACHE'),9:field})
   pose=c.get(pp,86)+c.get(ptr('ENDPOINT'),sym('EP_SIZE'));poses.append(pose);digest.update(pose)
  if baseline is None:baseline=poses
  else:assert poses==baseline,(rate,index)
  call('timing_runtime_suspend',{1:ARENA});call('timing_runtime_retire',{1:ARENA})
  assert c.get(ptr('ENDPOINT'),sym('EP_SIZE'))==bytes(sym('EP_SIZE'))
  assert c.get(ARENA-16,16)==c.get(ARENA+size,16)==b'\xa5'*16
  assert not old_access,old_access[:10]
  watch_old=False;previous=[(a,len(b)) for a,b in zip(addresses,hunks)]
  rows.append(dict(rate=rate,layout=index,fields=rate*2,trace_sha256=digest.hexdigest(),retired_native_accesses=len(old_access)))
# Positive control: an executed read from retired captured storage must be seen.
old_access.clear();watch_old=True
c.put(SAMPLE,bytes.fromhex('3039')+struct.pack('>I',low)+bytes.fromhex('4e75'))
c.rw(8,0x8f000);c.call(SAMPLE)
assert any(a==hex(low) for kind,a,n in old_access)
watch_old=False
print(json.dumps(dict(status='passed',runs=rows,stale_access_detector_positive_control=True,native_code_preserved_by_prepare=True,scope='Original PAL game relocated into three layouts, PAL/NTSC field rates; cached player motion and arena reprepare, not complete native world/render/loader execution.')))
c.close()
