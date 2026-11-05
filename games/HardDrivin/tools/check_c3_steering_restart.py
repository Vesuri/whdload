from pathlib import Path
import ctypes as C,json,os,random,re,struct
exec(Path('tools/check_c3_steering_native_frame.py').read_text().split('rng=random.Random')[0])
import drivetrain_model as model

def initialize(enabled):
 for addr,body in images:write(addr,body)
 if not enabled:write(code,bytes(native))
 write(a4-0x7fe0,bytes.fromhex('4e75'))
 ok(u.uc_ctl(h,0x4000000a))
 reg(17,0x2000);reg(5,a4)
 for off,value in [(0x9606,0),(0x9605,0),(0x9910,15),(0x993e,255),(0x991c,0),(0x9911,0),(0x991d,0),(0x95ff,0),(0xe94a,255),(0xaf31,0),(0xf790,0),(0xf791,255),(0xaddc,0)]:pack(a4+off-65536,'B',value)
 for off,value in [(0x9928,0),(0x992a,0),(0x9936,1),(0x990e,0),(0x9926,0),(0x992c,0),(0x994a,360),(0x9946,0),(0x9948,0),(0x9914,0),(0x9916,0),(0x991a,0),(0x95fa,400)]:pack(a4+off-65536,'h',value)
 pack(a4-0x66c0,'I',a4-0x68c6+8);pack(a4-0x6bb8,'4h',16384,0,0,16384)
 write(sy['_dispatch_state']+24,b'\x01');pack(sy['_dispatch_state']+28,'h',400)
 for symbol,size in [('_phase_state',78),('_phase_speed_cache',8),('_time_scalar_state',16),('_drivetrain_state',16),('_projection_state',36),('_motion_position_state',20),('_motion_state',32),('_phase_steering_pending',2)]:write(sy[symbol],bytes(size))

def run(interval,enabled):
 initialize(enabled);age=0;out={};stopped=0
 for duration,throttle,brake in [(256,22,0),(256,0,255),(64,0,0),(256,22,0),(256,0,255)]:
  while duration:
   n=min(interval,duration);duration-=n;age+=n
   pack(a4-0x66e4,'B',throttle);pack(a4-0x66ef,'B',brake);pack(sy['_time_scalar_fields'],'H',n)
   invoke(code+0xb35e)
   if enabled:invoke(sy['_phase_frame'])
   else:invoke(code+0xb662);invoke(code+0xb500)
   state=tuple(struct.unpack('>h',read(a4+off-65536,2))[0] for off in [0x9928,0x992a,0x9936,0x994a])
   out[age]=state;stopped+=state[0]==0
 return out,stopped
try:
 reference,stopped=run(8,False);assert stopped>5
 counts={}
 fine,_=run(1,True);assert all(fine[t]==v for t,v in reference.items())
 for n in [1,2,3,7,8,14,18,31]:
  actual,_=run(n,True);assert all(v==fine[t] for t,v in actual.items()),(n,next((t,actual[t],fine[t]) for t in actual if actual[t]!=fine[t]));counts[n]=len(actual)
 report=dict(passed=True,interval_endpoint_checks=counts,stopped_endpoints=stopped,scope='Pristine native eight-field velocity/RPM/gear/heading endpoints across acceleration, full braking, stationary idle and restart; candidate frame partitions from 1 to31 fields match the validated one-field curve. Flat contact, X400 and no contact pass. Position is intentionally excluded because projection still samples current segment orientation.')
 Path('tmp/c3-steering-restart.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
