"""Compare pristine and enhanced steering decisions at matched physical inputs."""
from pathlib import Path
import json,struct,itertools
exec(Path("tools/check_c3_steering_native_frame.py").read_text().split("rng=random.Random")[0])
cases=list(itertools.product([60,69,70,71,80,100],range(0,641,20),[0,255],[0,255],[0,3,15],[0,255]))
outputs=[]
try:
 for enhanced in [False,True]:
  for addr,b in images:write(addr,b)
  if not enhanced:write(code,bytes(native))
  ok(u.uc_ctl(h,0x4000000a));out=[]
  for mph,mouse,brake,road,mask,disabled in cases:
   velocity=round(mph*500/140)
   for off,value in [(0x9606,0),(0x9910,mask),(0x9911,brake),(0xe94a,road),(0xaf31,0),(0xf790,0),(0xf791,disabled)]:pack(a4+off-65536,"B",value)
   for off,value in [(0x9928,velocity),(0x992c,mph),(0x95fa,mouse),(0x9946,0),(0x9948,0),(0x994a,360),(0x9944,0),(0x9942,0),(0x9914,0),(0x9916,0),(0x991a,0)]:pack(a4+off-65536,"h",value)
   write(sy["_motion_state"],bytes(32));pack(sy["_dispatch_state"]+28,"h",mouse);pack(sy["_time_scalar_fields"],"H",1);write(sy["_dispatch_state"]+24,b"\x01")
   reg(5,a4);reg(17,0x2000)
   invoke(sy["_phase_steering_call"] if enhanced else code+0xb35e)
   out.append([read(a4-0x50cf,1)[0],read(a4-0x870,1)[0],struct.unpack(">h",read(a4-0x66e6,2))[0]])
  outputs.append(out)
 assert outputs[0]==outputs[1],[(case,a,b) for case,a,b in zip(cases,*outputs) if a!=b][:5]
 assert not any(r[0] for c,r in zip(cases,outputs[1]) if c[0]<=70)
 report=dict(passed=True,cases=len(cases),skid_entries=sum(bool(r[0]) for r in outputs[1]),at_or_below_70_entries=0,scope="Actual original steering versus enhanced deferred steering at identical speed/MPH/mouse/brake/contact/road/grade inputs. Full mouse range, on/off road, brake and airborne. Tests onset decisions, not whether live inputs/speeds are sampled identically.")
 Path("tmp/skid-onset-check.json").write_text(json.dumps(report,indent=2)+"\n");print(report)
finally:ok(u.uc_close(h))
