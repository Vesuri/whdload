import os,sys,re,json
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 sy={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)$',listing,re.M)}
 base=rd(s,0x87480)-sy['step_main'];flag=read_bytes(s,base+sy['step_geometry_reuse_flag'],2)
 expected=int(os.environ['RR_EXPECT_REUSE'])
 assert bool(flag[1])==bool(expected),(flag,expected)
 (s.out/'gate.json').write_text(json.dumps(dict(expected=expected,flag=flag.hex(),attn=rd(s,base+sy['verify_attn']),provenance=provenance(os.environ['SLAVE'],s)),indent=2))
 print('geometry reuse selected',bool(flag[1]),flush=True)
finally:s.quit()
