"""Forecast prefix/mode and modal barriers versus original instructions."""
from pathlib import Path
exec(Path(__file__).with_name('test_script_preview_c.py').read_text().replace(';c.close()', ''))
prefix=0x740000
c.put(prefix,c.get(h[0]+0x9f74,0x36)+bytes.fromhex('4e75'))
count=int.from_bytes(c.get(h[0]+0xb430,4),'big')
table=int.from_bytes(c.get(h[0]+0xb436,4),'big')
matched=blocked=unknown=0
for inside in (False,True):
 for state in (0,1,2,4,5,128,255):
  for timer in (0,1,2,255):
   for flags in range(4):
    c.put(low,initial)
    ps=bytearray(0x2d6)
    x,y=12000,30000
    struct.pack_into('>HH',ps,0,x,y)
    struct.pack_into('>H',ps,28,100)
    ps[0x2c]=int(not inside) # stale mode must be replaced
    ps[0x53]=state;ps[0x54]=timer
    for hi,lo,value in [(0x5b,0xd5,x),(0xdb,0x155,y-256),(0x255,0x1d5,100)]:ps[hi]=value>>8;ps[lo]=value&255
    c.put(p,ps);c.put(h[6]+0x157b,b'\0');c.put(h[6]+0x395c,bytes([flags]))
    c.put(count,struct.pack('>H',1 if inside else 0))
    c.put(table,bytes([(x+128)>>8,0,0,0,(y+128)>>8,0,0,0]))
    c.put(bitmap+8,struct.pack('>I',planes[0]));c.put(h[6]+0x47c4,struct.pack('>I',bitmap))
    c.put(palette,b'\x1e\x1f');c.put(h[6]+0x16dc+24,b'\x1e\x1f')
    before=c.get(low,length);bad.clear();checking=True
    got=call('script_preview_forecast',{1:spv,2:p,3:bitmap,4:palette});checking=False
    assert not bad and c.get(low,length)==before,(inside,state,timer,flags,bad)
    predicted=bytes(c.get(private+off,1)[0] for off in pose_offsets)
    c.rw(6,p);c.rw(8,0x8f000);c.call(prefix)
    native_state,native_timer=c.get(p+0x53,2)
    modal=0<native_state<128 and native_timer==1
    assert c.get(private+0x2c,1)==c.get(p+0x2c,1)==bytes([inside])
    if modal:
     assert got==0 and c.get(spv+sym('SP_VALID'),1)==b'\0'
     blocked+=1;continue
    c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x8050)
    assert c.get(private+0x53,2)==c.get(p+0x53,2)
    if not got:unknown+=1;continue
    c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x9fb0)
    actual=bytes(c.get(p+off,1)[0] for off in pose_offsets)
    assert predicted==actual,(inside,state,timer,flags,predicted.hex(),actual.hex())
    matched+=1
# All prefix words and interpreter guard words reject atomically.
rejected=0
for start,n in [(0x9f74,0x36),(0x8050,16)]:
 for off in range(0,n,2):
  address=h[0]+start+off;old=c.get(address,2);c.put(address,bytes(v^1 for v in old));before=c.get(spv,size)
  call('script_preview_prepare',{1:h[0],2:h[6],3:spv},0xffffffff)
  assert c.get(spv,size)==before;c.put(address,old);rejected+=1
assert matched and blocked and not any(flag for flag,off in effects)
print(json.dumps(dict(status='passed',forecast_matches=matched,modal_rejections=blocked,terrain_rejections=unknown,prefix_signature_rejections=rejected,native_writes=0)))
c.close()
