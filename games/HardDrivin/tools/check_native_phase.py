"""Explore native-endpoint dense output using the actual pristine engine.
No game patch: fixed heading, flat full contact, automatic gears.
"""
from pathlib import Path
import json
# Reuse the read-only native engine fixture setup, not its model comparison loop.
p=Path('tools/check_native_engine_model.py')
exec(p.read_text().split('results=[]')[0])
initial_memory=read(database,0x8000)
def native(s,throttle,brake=0):
 write(database,initial_memory)
 v,rpm,gear=s
 pack(g(0x9928),'h',v);pack(g(0x992a),'h',rpm);pack(g(0x9936),'h',gear)
 pack(g(0x9926),'h',model.engine_speed(rpm,gear))
 write(g(0x991c),bytes([throttle]));write(g(0x9911),bytes([brake]))
 pack(g(0x9940),'I',0x350000+8*gear)
 reg(17,0x2000);reg(5,a4);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
 ok(u.uc_emu_start(h,codebase+0xb662,0x490000,1000000,10000))
 assert reg(8)==0x4ffff4
 return tuple(struct.unpack('>h',read(g(off),2))[0] for off in [0x9928,0x992a,0x9936])
class Phase:
 def __init__(self,s):self.anchor=s;self.phase=0;self.position=0;self.calls=0
 def advance(self,n,throttle,brake=0):
  assert n>0
  while n:
   # Re-evaluate from the phase anchor on EVERY frame. Intermediate input
   # handling is deliberately under examination; do not call this accepted.
   end=native(self.anchor,throttle,brake);self.calls+=1
   dt=min(n,8-self.phase)
   self.phase+=dt;n-=dt
   # Cardinal positive-X native projection: floor(3*velocity/2).
   # Linear endpoint displacement, NOT the rejected Euler extrapolation.
   self.position+=(3*end[0]//2)*dt*8192
   v8=self.anchor[0]*8+(end[0]-self.anchor[0])*self.phase
   rpm8=self.anchor[1]*8+(end[1]-self.anchor[1])*self.phase
   gear=self.anchor[2] if self.phase<8 else end[2]
   if self.phase==8:self.anchor=end;self.phase=0
  return (v8,rpm8,gear,self.position)
results=[]
try:
 for throttle,brake,start in [(22,0,(0,0,1)),(100,0,(0,0,1)),(0,255,(100,3000,1)),(0,255,(1,1000,1))]:
  reference=Phase(start);oracle={0:(start[0]*8,start[1]*8,start[2],0)}
  for t in range(1,257):oracle[t]=reference.advance(1,throttle,brake)
  native_state=start;native_position=0
  for t in range(8,257,8):
   native_state=native(native_state,throttle,brake);native_position+=(3*native_state[0]//2)*65536
   assert oracle[t]==(native_state[0]*8,native_state[1]*8,native_state[2],native_position)
  for interval in [1,2,3,7,8,9,16,31]:
   phase=Phase(start);age=0
   while age<256:
    n=min(interval,256-age);age+=n
    assert phase.advance(n,throttle,brake)==oracle[age],(throttle,brake,interval,age)
   results.append(dict(throttle=throttle,brake=brake,start=start,interval=interval,calls=phase.calls,final=oracle[256]))
  assert all(b[3]>=a[3] for a,b in zip(oracle.values(),list(oracle.values())[1:])),('reverse',throttle,brake)
 # Abrupt brake/input change is a required counterexample, not a waived test.
 a=Phase((100,3000,1));before=a.advance(7,100,0);after=a.advance(1,0,255)
 # Compare a fresh native full brake step with the final one-field response.
 brake_end=native((100,3000,1),0,255)
 input_change=dict(before=before,after=after,velocity_delta_eighths=after[0]-before[0],native_full_brake_velocity=brake_end[0])
 report=dict(held_input_passed=True,configurations=len(results),native_endpoint_checks=128,results=results,input_change=input_change,scope='Exploratory host phase algorithm with actual unmodified 68000 engine per frame segment. Flat automatic, fixed cardinal projection; no native position execution, game integration, changing-input acceptance, collisions, timing or FPS claim.')
 Path('tmp/native-phase-check.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='results'}))
finally:ok(u.uc_close(h))
