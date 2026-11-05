"""Probe the steering decision with decelerating substep state."""
from pathlib import Path
import json,struct
exec(Path("tools/check_c3_steering_native_frame.py").read_text().split("rng=random.Random")[0])
outputs=[]
try:
 for enhanced in [False,True,2]:
  for a,b in images:write(a,b)
  if not enhanced:write(code,bytes(native))
  if enhanced==2:write(0x81000,Path("tmp/steering-current-frame.bin").read_bytes())
  write(a4-0x7fe0,bytes.fromhex("4e75"));ok(u.uc_ctl(h,0x4000000a))
  for k in range(1,17):reg(k,k*0x10101)
  reg(17,0x2000);reg(5,a4)
  for off,value in [(0x9606,0),(0x9605,0),(0x9910,15),(0x993e,1),(0x991c,0),(0x9911,255),(0x991d,0),(0x95ff,0),(0xe94a,255),(0xaf31,0),(0xf790,0),(0xf791,0),(0xaddc,0)]:pack(a4+off-65536,"B",value)
  for off,value in [(0x9928,246),(0x992a,3077),(0x9936,4),(0x990e,0),(0x95fa,639),(0x994a,360),(0x9946,0),(0x9948,0),(0x9914,0),(0x9916,0),(0x991a,0),(0x992c,68)]:pack(a4+off-65536,"h",value)
  import drivetrain_model as model
  pack(a4-0x66da,"h",model.engine_speed(3077,4));pack(a4-0x66c0,"I",a4-0x68c6+4*8);pack(a4-0x6bb8,"4h",16384,0,0,16384)
  for symbol,size in [("_phase_state",78),("_phase_speed_cache",8),("_time_scalar_state",16),("_drivetrain_state",16),("_projection_state",36),("_motion_position_state",20),("_motion_state",32)]:write(sy[symbol],bytes(size))
  ph=sy["_phase_state"];pack(ph,"HHH",1,0,7);pack(ph+12,"4i",260*65536,246*65536,3200*65536,3077*65536+32768);pack(ph+32,"4h",4,246,3077,4)
  pack(sy["_dispatch_state"]+28,"h",639);pack(sy["_time_scalar_fields"],"H",1);write(sy["_dispatch_state"]+24,b"\x01")
  invoke(code+0xb35e)
  if enhanced:invoke(0x81000 if enhanced==2 else sy["_phase_frame"])
  outputs.append(dict(enhanced=enhanced,skid=read(a4-0x50cf,1)[0],spin=struct.unpack(">h",read(a4-0x66e6,2))[0]))
 assert [r["skid"] for r in outputs]==[0,255,0],outputs
 print(outputs)
 Path("tmp/skid-anchor-probe.json").write_text(json.dumps(dict(scope="Seven fields into pristine braking endpoint (260,3200,4) -> (244,3060,4); current (246,3077.5,4), sudden steering on field8. Initial anchor is a controlled state, not a full driving tape.",outputs=outputs),indent=2)+"\n")
finally:ok(u.uc_close(h))
