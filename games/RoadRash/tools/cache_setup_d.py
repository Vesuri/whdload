"""Read immediate SetCPU policy/CACR and race state without altering memory."""
import json,os,struct,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 stats=counters(s,stats_address(s))
 data=read_bytes(s,stats_address(s)+320,128)
 off=data.find(b'RRDCPU01');assert off>=0
 old,post,calls=struct.unpack_from('>3I',data,off+8)
 selected=rd(s,0x8747e,2)==0x4ef9
 assert calls==int(selected),(calls,selected)
 if selected:assert post==stats['race_cacr'],(post,stats)
 else:assert post==0xffffffff
 result=dict(previous_policy=old,post_cacr=post,calls=calls,selected=selected,stats=stats,provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'cache.json').write_text(json.dumps(result,indent=2)+'\n')
 print(dict(post_cacr=hex(post),calls=calls,race_cacr=hex(stats['race_cacr']),selected=selected),flush=True)
finally:s.quit()
