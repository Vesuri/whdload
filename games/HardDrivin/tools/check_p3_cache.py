"""Exact cached/native endpoint segment equivalence using the live patched 68000 image."""
import ctypes as C,json,os,random,re,struct
from pathlib import Path
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0x50000,0xfb0000,7))
root=Path('tmp/prof/p3-check-motion');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4'];code=lay['code_base']
sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',Path('tmp/build/p3-check-a.lst').read_text(encoding='latin1'),re.M)}
base=lay['published']-sy['_code_start'];sy={k:base+v for k,v in sy.items()}
for name,addr in [('chip',0),('slow',0xc00000)]:
 if addr==0:ok(u.uc_mem_map(h,0,0x10000,7))
 write(addr,(root/f'timing-state-{name}.bin').read_bytes())
ph=sy['_phase_state'];ss=sy['_time_scalar_state'];cv=sy['_phase_cache_valid'];dt=sy['_drivetrain_state'];stop=0x41000;sp=0x4f000
# Audio body is replaced only in this private fixture with a call counter. Its
# publication and final-segment gate still execute real game/slave instructions.
write(a4-0x7fe0,bytes.fromhex('4ef900042000'));write(0x42000,bytes.fromhex('52b9000430004e75'))
def invoke(n):
 reg(8,sp);pack(sp,'I',stop);ok(u.uc_emu_start(h,sy[n],stop,1000000,40000));assert reg(18)==stop and reg(8)==sp+4
saved_data=read(lay['data_base'],31948)
rng=random.Random(33198);hits=misses=0
keys=[('anchorv',None),('anchorr',None),('gear',None),(0x991c,'B'),(0x9911,'B'),(0xaf31,'B'),(0xe94a,'B'),(0xf790,'B'),(0xf791,'B'),(0x944c,'h')]
for case in range(6000):
 write(lay['data_base'],saved_data);write(ph,bytes(78));write(ss,bytes(16));write(cv,bytes(40));write(0x43000,bytes(4));reg(17,0x2000);reg(5,a4);reg(7,ph)
 phase=rng.randrange(1,8);n=rng.randint(1,8-phase);gear=rng.randint(1,4)
 av=rng.randrange(0,1900*8)*8192;ar=rng.randrange(6500*8)*8192
 for off,fmt,v in [(0,'H',1),(2,'H',1),(4,'H',phase),(10,'H',n),(12,'I',av),(16,'I',av),(20,'I',ar),(24,'I',ar),(32,'H',gear),(72,'H',rng.choice([0,255])),(74,'H',8-phase)]:pack(ph+off,fmt,v)
 for off,v in [(0x991c,rng.randrange(101)),(0x9910,15),(0x993e,1),(0x9606,0),(0xe94a,rng.choice([0,255])),(0xaf31,rng.choice([0,255])),(0xf790,rng.choice([0,255])),(0xf791,rng.choice([0,255])),(0xaddc,rng.choice([0,255]))]:write(a4+off-65536,bytes([v]))
 pack(a4-0x6bb4,'h',rng.randint(-16384,16384));pack(a4-0x66c0,'I',0x44000+8*gear)
 pack(dt,'HHHH',rng.randint(1,255),rng.choice([1,2]),0,1)
 pack(ss+4,'i',rng.randrange(-65535,65536));write(ss+8,read(a4-0x66e4,1))
 invoke('_phase_prepare_anchor')
 # Seed a native miss, then restore its entry state while retaining the cache.
 before=[read(lay['data_base'],31948),read(ph,78),read(ss,16),read(dt,16)]
 invoke('_phase_engine_call')
 for addr,b in zip([lay['data_base'],ph,ss,dt],before):write(addr,b)
 if case%3==0:
  key,fmt=keys[(case//3)%len(keys)]
  if key=='anchorv':pack(ph+12,'I',av+8192)
  elif key=='anchorr':pack(ph+20,'I',ar+8192)
  elif key=='gear':pack(ph+32,'H',1+gear%4)
  else:
   addr=a4+key-65536
   if fmt=='h':pack(addr,'h',rng.randint(-16384,16384))
   else:write(addr,bytes([(read(addr,1)[0]+1)%101]))
  if key==0x9911:pack(ph+72,'H',read(a4-0x66ef,1)[0])
 # Re-prepare both runs exactly as phase_frame does.
 invoke('_phase_prepare_anchor')
 if case%17==0:pack(ph+4,'H',0);pack(ph+74,'H',8)
 if case%19==0:pack(cv,'H',0)
 before=[read(lay['data_base'],31948),read(ph,78),read(ss,16),read(dt,16),read(cv,40)]
 outputs=[]
 for forced in [False,True]:
  for addr,b in zip([lay['data_base'],ph,ss,dt,cv],before):write(addr,b)
  if forced:pack(cv,'H',0)
  write(0x43000,bytes(4));reg(17,0x2010 if case%2 else 0x2000);reg(5,a4);reg(7,ph)
  preserved={k:reg(k) for k in [4,5,6,7,13,14,15,16]}
  invoke('_phase_engine_call');assert all(reg(k)==v for k,v in preserved.items()),(case,'register')
  outputs.append([read(lay['data_base'],31948),read(ph,78),read(ss,16),read(dt,16),read(0x43000,4)])
  if not forced:
   hit=struct.unpack('>I',read(cv+32,4))[0]>struct.unpack_from('>I',before[-1],32)[0];hits+=hit;misses+=not hit
 assert outputs[0]==outputs[1],(case,[(i,[(k,x,y) for k,(x,y) in enumerate(zip(a,b)) if x!=y][:8]) for i,(a,b) in enumerate(zip(*outputs)) if a!=b])
report=dict(passed=True,cases=6000,hits=hits,misses=misses,exact=['all native globals','phase Q16 state','scalar companions including throttle decay','gear pointer and shifts','audio publication/call count','preserved registers and stack'],scope='Actual live patched 68000 image; cached versus forced-native evaluation with randomized grounded automatic states, changed inputs, phase boundaries and invalidation. Private audio body counts calls; native pitch calculation and audio gate remain real.')
Path('tmp/p3-cache-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
