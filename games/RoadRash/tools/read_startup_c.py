import sys,json,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);target=rd(s,0x86618);data=read_bytes(s,target,160);off=data.find(b'RRSTART1');assert off>=0
 addr=target+off+8;assert rd(s,addr)==1
 state=read_bytes(s,addr+4,0x2e40);rng=read_bytes(s,addr+4+0x2e40,0x88)
 (s.out/'race-state.bin').write_bytes(state);(s.out/'actors.bin').write_bytes(state[0x460:0x15e0]);(s.out/'rng.bin').write_bytes(rng)
 result=dict(field=int.from_bytes(state[0x44c:0x450],'big'),cursor=int.from_bytes(state[0x450:0x454],'big'),delta=int.from_bytes(state[0x1600:0x1602],'big'),target=hex(target),provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
