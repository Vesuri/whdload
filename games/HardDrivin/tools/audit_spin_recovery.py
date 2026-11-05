"""Compare actual native and enhanced spin-decay lifetimes from identical starts."""
from pathlib import Path
import json,struct
exec(Path("tools/check_c3_steering_native_frame.py").read_text().split("rng=random.Random")[0])
for addr,b in images: write(addr,b)
write(code,bytes(native))
# The enhanced decay helper is in the separately loaded slave image.
results=[]
try:
 for start in [-52,-24,-11,-7,-3,3,7,11,24,52]:
  for dt in [1,2,4,8]:
   write(sy["_motion_state"],bytes(32));pack(sy["_time_scalar_fields"],"H",dt)
   pack(a4-0x66e6,"h",start);reg(5,a4);reg(17,0x2000)
   fields=0;states=[]
   while fields<1000:
    invoke(sy["_motion_spin_decay"]);fields+=dt
    value=struct.unpack(">h",read(a4-0x66e6,2))[0]
    states.append([fields,value])
    if not value: break
   value=start;native_fields=0;native_states=[]
   while value:
    pack(a4-0x66e6,"h",value);reg(8,sp)
    ok(u.uc_emu_start(h,code+0xb62a,code+0xb63c,1000000,10000))
    value=struct.unpack(">h",read(a4-0x66e6,2))[0];native_fields+=8
    native_states.append([native_fields,value])
   results.append(dict(start=start,interval=dt,native_exit_fields=native_fields,enhanced_exit_fields=fields,native=native_states,enhanced=states))
 report=dict(scope="Actual pristine spin instructions versus assembled enhanced helper; fixed MPH above exit threshold, no contact/input/renderer. Exit when published spin becomes zero.",results=results)
 Path("tmp/spin-recovery-before.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps([{k:r[k] for k in ("start","interval","native_exit_fields","enhanced_exit_fields")} for r in results],indent=2))
finally:ok(u.uc_close(h))
