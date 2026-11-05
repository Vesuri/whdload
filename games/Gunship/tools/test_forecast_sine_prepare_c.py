from unicorn_b import *
from functools import lru_cache
import json
base=0x100000;l=(root/'tmp/c/runtime.lst').read_text()
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
helper=0x300000;table=0x301000;out=0x302002;stages=0x304002
code=bytes.fromhex('024000ffd04041f9')+struct.pack('>I',table)+bytes.fromhex('d0c03010c1c1d08048404e75')
c.put(table,bytes(range(256))*2)
def call(name,args):
 regs={r:0x1400+r for r in range(1,17) if r!=8};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name))
 assert c.rr(18)==0x90000
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 return c.rr(9)
for i in range(24):
 broken=bytearray(code);broken[i]^=1;c.put(helper,broken);c.put(out-2,b'Z'*540)
 assert call('forecast_sine_prepare',{1:helper,2:table,3:out})==0xfffffffd
 assert c.get(out-2,540)==b'Z'*540
c.put(helper,code)
assert call('forecast_sine_prepare',{1:helper,2:table,3:out})==0
assert c.get(out,8)==code[:8] and c.get(out+8,4)==struct.pack('>I',out+24)
assert c.get(out+12,12)==code[12:] and c.get(out+24,512)==c.get(table,512)
assert c.get(out-2,2)==c.get(out+536,2)==b'ZZ'
size=7*0x41e;image=bytearray(size);sites=[i*0x41e+j for i in range(7) for j in (0x14e,0x180,0x1a0,0x2c6,0x304,0x33c)]
for at in sites:image[at:at+6]=bytes.fromhex('4eb9')+struct.pack('>I',helper)
for at in sites:
 for offset in range(6):
  broken=bytearray(image);broken[at+offset]^=1;c.put(stages-2,b'ZZ'+broken+b'ZZ')
  assert call('forecast_stages_bind_sine',{1:stages,2:helper,3:out})==0xfffffffd
  assert c.get(stages-2,size+4)==b'ZZ'+broken+b'ZZ'
c.put(stages-2,b'ZZ'+image+b'ZZ')
assert call('forecast_stages_bind_sine',{1:stages,2:helper,3:out})==0
for at in sites:image[at+2:at+6]=struct.pack('>I',out)
assert c.get(stages-2,size+4)==b'ZZ'+image+b'ZZ'
report=dict(status='passed',helper_byte_rejections=24,stage_byte_rejections=252,bindings=42,atomic_rejection=True,abi=True,canaries=True)
(root/'tmp/c/forecast-sine-prepare-test.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
c.close()
