import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1');symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)',listing,re.M)}
 base=rd(s,0x87480)-symbols['step_main'];names=['step_main','step_physics_aux_init','aux_8d2c0','aux_8dd66','aux_lane_scan'];r=dict(base=hex(base),symbols={n:hex(base+symbols[n]) for n in names if n in symbols},provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'placement.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
finally:s.quit()
