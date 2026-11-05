"""Actual steering decisions through the enhanced frame, across phase speeds."""
from pathlib import Path
import itertools,json,struct
exec(Path("tools/check_c3_steering_native_frame.py").read_text().split("rng=random.Random")[0])
cases=list(itertools.product(range(1,8),range(0,641,20),[0,255],[0,255],[0,3,15],[-1,1]));outputs=[]
try:
 for version in ["native","old","fixed"]:
  for a,b in images:write(a,b)
  if version=="native":write(code,bytes(native))
  if version=="fixed":write(0x81000,Path("tmp/steering-current-frame.bin").read_bytes())
  write(a4-0x7fe0,bytes.fromhex("4e75"));ok(u.uc_ctl(h,0x4000000a));out=[]
  for phase,mouse,brake,road,mask,direction in cases:
   # The decelerating case is the exact original-engine braking endpoint
   # 260/3200 -> 244/3060. The rising case checks the opposite speed crossing
   # as a controlled phase state, without claiming a specific driving tape.
   anchor_v,anchor_r=(260,3200) if direction<0 else (244,3060)
   v=anchor_v+direction*2*phase;r=anchor_r*65536+direction*(140 if direction<0 else 240)*8192*phase;rpm=r//65536
   for off,value in [(0x9606,0),(0x9605,0),(0x9910,mask),(0x993e,1),(0x991c,0),(0x9911,brake),(0x991d,0),(0x95ff,0),(0xe94a,road),(0xaf31,0),(0xf790,0),(0xf791,0),(0xaddc,0)]:pack(a4+off-65536,"B",value)
   for off,value in [(0x9928,v),(0x992a,rpm),(0x9936,4),(0x990e,0),(0x95fa,mouse),(0x994a,360),(0x9946,0),(0x9948,0),(0x9944,0),(0x9942,0),(0x9914,0),(0x9916,0),(0x991a,0),(0x992c,rpm*10//450)]:pack(a4+off-65536,"h",value)
   import drivetrain_model as model
   pack(a4-0x66da,"h",model.engine_speed(rpm,4));pack(a4-0x66c0,"I",a4-0x68c6+4*8);pack(a4-0x6bb8,"4h",16384,0,0,16384)
   for symbol,size in [("_phase_state",78),("_phase_speed_cache",8),("_time_scalar_state",16),("_drivetrain_state",16),("_projection_state",36),("_motion_position_state",20),("_motion_state",32)]:write(sy[symbol],bytes(size))
   ph=sy["_phase_state"];pack(ph,"HHH",1,0,phase);pack(ph+12,"4i",anchor_v*65536,v*65536,anchor_r*65536,r);pack(ph+32,"4h",4,v,rpm,4)
   pack(sy["_dispatch_state"]+28,"h",mouse);pack(sy["_time_scalar_fields"],"H",1);write(sy["_dispatch_state"]+24,b"\x01");reg(5,a4);reg(17,0x2000)
   invoke(code+0xb35e)
   if version!="native":
    reg(8,sp);pack(sp,"I",stop)
    ok(u.uc_emu_start(h,0x81000 if version=="fixed" else sy["_phase_frame"],sy["_phase_engine_call"],1000000,100000));assert reg(18)==sy["_phase_engine_call"]
   out.append((read(a4-0x50cf,1)[0],read(a4-0x870,1)[0],struct.unpack(">h",read(a4-0x66e6,2))[0]))
  outputs.append(out)
 assert outputs[0]==outputs[2],[(c,a,b) for c,a,b in zip(cases,outputs[0],outputs[2]) if a!=b][:5]
 extra=sum(bool(not a[0] and b[0]) for a,b in zip(outputs[0],outputs[1]));missed=sum(bool(a[0] and not b[0]) for a,b in zip(outputs[0],outputs[1]))
 assert extra>0
 report=dict(passed=True,cases=len(cases),old_extra_skid_entries=extra,old_missed_skid_entries=missed,fixed_decisions_match_native=True,scope="Compare original steering with the actual enhanced frame at all seven interior phase positions, full mouse range, brake/on-off road and wheel-contact masks. Matched CURRENT velocity/RPM. Downward speed path uses pristine-engine braking endpoint; upward crossing is a synthetic control.")
 Path("tmp/skid-current-speed-check.json").write_text(json.dumps(report,indent=2)+"\n");print(report)
finally:ok(u.uc_close(h))
