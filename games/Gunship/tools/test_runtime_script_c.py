"""Committed-raster capture and renderer-only scripted XYZ publication."""
__file__=__file__.replace('test_runtime_script_c.py','test_runtime_batch_c.py')
exec(open(__file__).read().split('runs=[];yields=0')[0])
bitmap=0x120000;planes=[0x130000+i*0x10000 for i in range(5)]
for a in planes:c.put(a,bytes(65536))
c.put(bitmap,struct.pack('>HHBBH5I',80,512,0,5,0,*planes))
frames=0
for rate in (50,60):
 setup(rate)
 assert word(ptr('SCRIPT_PRESENT')+sym('SPC_VALID'))==0
 # An active helicopter, no modal pending, inside a native region.
 ps=bytearray(c.get(p,0x2d6));x,y=12000,30000
 struct.pack_into('>HH',ps,0,x,y);struct.pack_into('>H',ps,28,100)
 ps[0x53]=255;ps[0x54]=255
 for hi,lo,v in [(0x5b,0xd5,x),(0xdb,0x155,y-256),(0x255,0x1d5,100)]:ps[hi]=v>>8;ps[lo]=v&255
 c.put(p,ps);c.put(h[6]+0x157b,b'\0');c.put(h[6]+0x47c4,struct.pack('>I',bitmap))
 count=long(h[0]+0xb430);table=long(h[0]+0xb436)
 c.put(count,b'\0\1');c.put(table,bytes([(x+128)>>8,0,0,0,(y+128)>>8,0,0,0]))
 c.put(ptr('TARGET')+sym('WT_PALETTE')+24,b'\x1e\x1f')
 c.put(ptr('SCRIPT_BITMAP'),struct.pack('>I',bitmap));c.put(ptr('TARGET_PHASE'),b'\0\2')
 field=long(ptr('RECORD')+sym('TR_FIELD'));c.put(ptr('TARGET_FIELD'),struct.pack('>I',field))
 c.put(ptr('CLOCK')+sym('TC_TICKS'),struct.pack('>I',1));c.put(ptr('CLOCK')+sym('TC_PHASE'),bytes(2))
 before=c.get(low,length);call('timing_runtime_script_seed',{1:ARENA})
 assert c.get(low,length)==before and word(ptr('SCRIPT_PRESENT')+sym('SPC_VALID'))==1
 cache=ptr('SCRIPT_PRESENT');current=c.get(cache+sym('SPC_CURRENT'),6);nextpose=c.get(cache+sym('SPC_NEXT'),6)
 assert current!=nextpose
 for phase in range(0,rate,3):
  c.put(ptr('CLOCK')+sym('TC_PHASE'),struct.pack('>H',phase));before=c.get(p,0x2d6)
  call('timing_runtime_present_state',{1:ARENA})
  want=bytearray()
  for v,n in zip(struct.unpack('>3H',current),struct.unpack('>3H',nextpose)):
   delta=((n-v+32768)&65535)-32768;want+=struct.pack('>H',(v+delta*(phase//3)//((rate+2)//3))&65535)
  for dest in (ptr('PRESENT_SCENE')+48,h[4]+48,h[5]+58,h[6]+0x3934):assert c.get(dest,6)==want,(rate,phase,hex(dest),c.get(dest,6).hex(),want.hex())
  start=c.get(cache+sym('SPC_CURRENT')+6,1)[0];end=c.get(cache+sym('SPC_NEXT')+6,1)[0]
  delta=((end-start+128)&255)-128
  assert c.get(ptr('SCRIPT_POSE')+6,1)==bytes([(start+delta*(phase//3)//((rate+2)//3))&255])
  assert c.get(p,0x2d6)==before
  frames+=1
 c.put(ptr('SCRIPT_GENERATION'),struct.pack('>I',1));call('timing_runtime_present_state',{1:ARENA});assert c.get(ptr('PRESENT_SCENE')+48,6)==current
 # Missing, wrong-field or rebound raster leaves the new snapshot invalid.
 c.put(ptr('CLOCK')+sym('TC_PHASE'),bytes(2))
 for addr,data in [(ptr('TARGET_PHASE'),bytes(2)),(ptr('TARGET_FIELD'),struct.pack('>I',field+1)),(ptr('SCRIPT_BITMAP'),struct.pack('>I',bitmap+40))]:
  old=c.get(addr,len(data));c.put(addr,data);before=c.get(low,length)
  call('timing_runtime_script_seed',{1:ARENA});assert not word(cache+sym('SPC_VALID')) and c.get(low,length)==before
  c.put(addr,old)
 # Lifecycle reseeds actors but must not recycle a scripted raster forecast.
 c.put(cache+sym('SPC_VALID'),b'\0\1');call('timing_runtime_suspend',{1:ARENA});call('timing_runtime_activate',{1:ARENA});assert not word(cache+sym('SPC_VALID')) and not long(ptr('SCRIPT_BITMAP'))
print(json.dumps(dict(status='passed',renderer_publications=frames,raster_barriers=6,lifecycle_resets=2,player_writes=0)))
c.close()
