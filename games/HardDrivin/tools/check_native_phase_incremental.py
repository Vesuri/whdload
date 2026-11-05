"""Incremental native-endpoint exploration; no game patch or acceptance claim."""
from pathlib import Path
from fractions import Fraction as F
import json,random
exec(Path('tools/check_native_phase.py').read_text().split('class Phase:')[0])
intermediate=[]
CALLBACK=C.CFUNCTYPE(None,P,U,C.c_uint32,P)
@CALLBACK
def sample_engine(handle,pc,size,data):
 intermediate.append(tuple(struct.unpack('>h',read(g(off),2))[0] for off in [0x9928,0x992a]))
u.uc_hook_add.argtypes=[P,C.POINTER(C.c_size_t),I,P,P,U,U];u.uc_hook_add.restype=I
hook=C.c_size_t();ok(u.uc_hook_add(h,C.byref(hook),4,C.cast(sample_engine,P),None,codebase+0xb904,codebase+0xb904))
def endpoint(s,throttle,brake=0):
 intermediate.clear();after=native(s,throttle,brake)
 assert len(intermediate)==1,(s,throttle,brake,intermediate)
 return intermediate[0],after

def project(v):
 whole=int(v);q=F(3*whole//2)
 return q+(v-whole)*((3*(whole+1)//2)-(3*whole//2))
class Incremental:
 def __init__(self,s):
  self.anchor=(F(s[0]),F(s[1]));self.v,self.r=self.anchor;self.gear=s[2];self.phase=0;self.position=F(0);self.calls=0;self.shifts=[];self.age=0
 def advance(self,n,throttle,brake=0):
  assert n>0
  while n:
   end,_=endpoint((int(self.anchor[0]),int(self.anchor[1]),self.gear),throttle,brake);self.calls+=1
   remaining=8-self.phase;dt=min(n,remaining)
   dv=F(end[0])-self.anchor[0];dr=F(end[1])-self.anchor[1]
   # Forecast only the UNCONSUMED part of this phase with the new input.
   forecast=self.v+dv*remaining/8
   assert forecast>=0
   self.position+=project(forecast)*dt/8
   self.v+=dv*dt/8;self.r+=dr*dt/8
   self.phase+=dt;n-=dt;self.age+=dt
   assert self.v>=0 and 0<=self.r<=6500
   if self.phase==8:
    old=self.gear;rpm=int(self.r)
    if rpm<2000 and old>1:self.gear-=1
    elif rpm>5200 and old<4:self.gear+=1
    if old!=self.gear:
     a,b=model.TABLE[old];c,d=model.TABLE[self.gear]
     self.r=F(model.convert(model.convert(rpm,a,b),d,c));self.shifts.append((self.age,old,self.gear))
    self.anchor=(self.v,self.r);self.phase=0
  # Exact implementation requires at most Q6 scalar/Q9 position precision here.
  assert (self.v*64).denominator==1 and (self.r*64).denominator==1 and (self.position*512).denominator==1
  return (self.v,self.r,self.gear,self.position)

def encode(x):
 if isinstance(x,F):return str(x)
 if isinstance(x,(tuple,list)):return [encode(v) for v in x]
 if isinstance(x,dict):return {k:encode(v) for k,v in x.items()}
 return x
results=[];native_checks=0
try:
 for throttle,brake,start in [(22,0,(0,0,1)),(100,0,(0,0,1)),(0,255,(100,3000,1)),(0,255,(1,1000,1))]:
  reference=Incremental(start);oracle={0:(F(start[0]),F(start[1]),start[2],F(0))}
  for t in range(1,257):oracle[t]=reference.advance(1,throttle,brake)
  actual=start;position=0
  for t in range(8,257,8):
   actual=native(actual,throttle,brake);position+=3*actual[0]//2
   assert oracle[t]==(*actual,position);native_checks+=1
  for interval in [1,2,3,7,8,9,16,31]:
   x=Incremental(start);age=0
   while age<256:
    n=min(interval,256-age);age+=n
    assert x.advance(n,throttle,brake)==oracle[age]
   assert x.shifts==reference.shifts
   results.append(dict(throttle=throttle,brake=brake,start=start,interval=interval,shifts=x.shifts))
  assert all(b[3]>=a[3] for a,b in zip(oracle.values(),list(oracle.values())[1:]))
 # Previously failing abrupt input change, with exactly preserved past motion.
 x=Incremental((100,3000,1));before=x.advance(7,100);after=x.advance(1,0,255)
 assert before[0]==135 and after[0]==F(537,4) and after[0]-before[0]==F(-3,4)
 abrupt=dict(before=before,after=after,velocity_delta=after[0]-before[0])
 rng=random.Random(8406);tape=[(rng.randrange(1,32),rng.randrange(101),rng.choice([0,0,255])) for _ in range(40)]
 ref=Incremental((100,3000,1));oracle={};age=0
 for duration,throttle,brake in tape:
  for _ in range(duration):age+=1;oracle[age]=ref.advance(1,throttle,brake)
 checks=0
 for interval in [1,2,3,7,8,9,16,31]:
  x=Incremental((100,3000,1));age=0
  for duration,throttle,brake in tape:
   while duration:
    n=min(interval,duration);duration-=n;age+=n
    assert x.advance(n,throttle,brake)==oracle[age],(interval,age);checks+=1
  assert x.shifts==ref.shifts
 boundary=[];x=Incremental((0,0,1));age=0
 for target in [7,8,9,16]:
  out=x.advance(target-age,22);age=target;boundary.append(dict(fields=target,state=out))
 report=dict(boundary=boundary,held_input_configurations=len(results),native_endpoint_checks=native_checks,input_change_checks=checks,input_segments=len(tape),input_fields=sum(t[0] for t in tape),abrupt=abrupt,shifts=ref.shifts,held_results=results,scope='Host incremental phase prototype with actual unmodified engine evaluation every frame segment. Flat full-contact automatic fixed-heading. Native gear decisions occur at phase completion; not yet an accepted policy for changing inputs, manual controls, steering, contacts or per-frame gear behavior. No runtime implementation/FPS claim.')
 Path('tmp/native-phase-incremental.json').write_text(json.dumps(encode(report),indent=2)+'\n');print(json.dumps(encode({k:v for k,v in report.items() if k!='held_results'})))
finally:ok(u.uc_close(h))
