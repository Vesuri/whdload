source=open(__file__.replace('test_runtime_forecast_workspace_c.py','test_timing_runtime_c.py')).read()
exec(source.split("c.put(ARENA-16,")[0].split('# Loader-facing lookup')[0])
from functools import lru_cache
sym=lru_cache(None)(sym)
def rf(n):return ptr('FORECAST')+sym('RF_'+n)
def seed():
 c.put(rf('TAPE'),bytes.fromhex('00010007'));c.put(rf('TAPE')+4,struct.pack('>I',1));c.put(rf('EVENT'),bytes.fromhex('0007b401'))
def empty():
 assert c.get(rf('TAPE'),8)==bytes(8) and c.get(rf('EVENT'),4)==bytes(4)
runs=[]
for rate in (50,60):
 c.put(ARENA-16,b'\xa5'*(size+32));c.put(p+24,bytes(1));c.put(h[2]+0x0c,bytes(4));prepare(rate)
 assert c.get(rf('CONTEXT'),24)==struct.pack('>6I',1,0,rf('STAGES'),rf('SINE'),rf('GROUND'),0)
 assert c.get(rf('SINE')+24,512)==c.get(h[4]+0x1c8,512)
 assert long(rf('SINE')+8)==rf('SINE')+24
 for i in range(7):
  for offset in (0x14e,0x180,0x1a0,0x2c6,0x304,0x33c):assert long(rf('STAGES')+i*0x41e+offset+2)==rf('SINE')
 assert long(rf('GROUND')+0x4a)==rf('EVENT') and long(rf('GROUND')+0x58)==rf('EVENT')+2
 assert long(ptr('GROUND')+0x4a)==ptr('EVENT')
 # Invalid activation must preserve the existing forecast, too.
 seed();c.put(ARENA,bytes(4));before=c.get(ARENA,size)
 call('timing_runtime_activate',{1:ARENA},0xfffffffd);assert c.get(ARENA,size)==before;c.put(ARENA,struct.pack('>I',1))
 seed();call('timing_runtime_suspend',{1:ARENA});empty()
 seed();call('timing_runtime_retire',{1:ARENA});empty()
 c.put(h[5]+0x60,struct.pack('>I',h[6]));c.put(h[6]+0x4c68,bytes(26));c.put(h[2]+0x1c,struct.pack('>I',100));c.put(p+66,b'\x1c')
 seed();call('timing_runtime_activate',{1:ARENA});empty()
 # Accepted suspend clears the forecast while preserving authoritative event.
 c.put(ptr('EVENT'),bytes.fromhex('0007b401'));seed()
 call('timing_runtime_suspend',{1:ARENA});empty();assert c.get(ptr('EVENT'),4)==bytes.fromhex('0007b401')
 c.put(ptr('EVENT'),bytes(4))
 assert c.get(ARENA-16,16)==c.get(ARENA+size,16)==b'\xa5'*16
 runs.append(rate)
report=dict(status='passed',rates=runs,arena_bytes=size,private_event_binding=True,lifecycle_retirement=True,invalid_activation_atomic=True,guards=True)
(root/'tmp/c/runtime-forecast-workspace-test.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
c.close()
