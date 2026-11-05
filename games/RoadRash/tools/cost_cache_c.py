import os,sys,json,struct
from harness_a import *
# C experiments explicitly opt into the public master switch.
if not any(x.upper().startswith("CUSTOM2=") for x in os.environ.get("WHD_ARGS", "").split()):
 os.environ["WHD_ARGS"] = os.environ.get("WHD_ARGS", "") + " CUSTOM2=1"
s=Session(sys.argv[1])
try:
 route(s)
 target=rd(s,0x87480);data=read_bytes(s,target,1024);offset=data.find(b'RRCSTEP1');assert offset>=0
 addr=target+offset
 def point():
  cursor,steps,captured,quantum=struct.unpack_from('>4I',read_bytes(s,addr,24),8)
  return dict(field=field(s),cursor=cursor,steps=steps,quantum=quantum,frames=counters(s,stats_address(s))['frames'],position=rd(s,0xa5d64),dma=rd(s,0xdff002,2),frame_dma=counters(s,stats_address(s))['dma_frame'],cacr=counters(s,stats_address(s))['race_cacr'])
 points=[point()];s.input('JOY2_UP',1)
 for f in [300,600,1000]:
  advance(s,f);points.append(point());print(points[-1],flush=True)
 result=dict(provenance=provenance(os.environ['SLAVE'],s),points=points)
 (s.out/'cost.json').write_text(json.dumps(result,indent=2)+'\n');s.shot('final.png')
finally:s.quit()
