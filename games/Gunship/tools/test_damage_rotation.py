"""Run release camera adapter over consecutive damage ticks and field rates."""
from unicorn_b import *
import json,random
reports=[]
for name,rate in [('Gunship',50),('GunshipNTSC',60)]:
 c=CPU();f=build/'release'/f'{name}.Slave';c.put(base,bytes(BinFmt().load_image(str(f)).get_segments()[0].get_data()))
 sy={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',f.with_suffix('.lst').read_text(encoding='latin1'),re.M)}
 A=0x500000;H=0x510000
 def execute(field,stamp,phase,impulse,raw,height=1024,damage=2,valid=1):
  state=bytearray(sy['RT_ARENA_SIZE'])
  def put(off,n,v):state[off:off+n]=(v% (1<<(8*n))).to_bytes(n,'big')
  put(sy['RT_HUNKS']+24,4,H);put(sy['RT_CLOCK']+sy['TC_RATE'],2,rate);put(sy['RT_CLOCK']+sy['TC_PHASE'],2,phase)
  put(sy['RT_IMPULSES']+sy['SI_VALID'],2,valid);put(sy['RT_IMPULSES']+sy['SI_CACHE']+4,2,impulse)
  put(sy['RT_IMPULSES']+sy['SI_FIELD'],4,stamp);put(sy['RT_RECORD']+sy['TR_FIELD'],4,field);put(sy['RT_CAMERA']+6,2,raw)
  c.put(A,state);c.put(H+0x3ba4,struct.pack('>H',height));c.put(H+0x3b96,struct.pack('>H',damage))
  regs={r:0x543210+r for r in range(1,17) if r!=8};regs[1]=A
  for r,v in regs.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(base+sy['timing_runtime_damage_yaw'])
  actual=c.get(A,len(state));yaw=int.from_bytes(actual[sy['RT_CAMERA']+6:sy['RT_CAMERA']+8],'big')
  changed=bytearray(state);changed[sy['RT_CAMERA']+6:sy['RT_CAMERA']+8]=yaw.to_bytes(2,'big')
  assert actual==changed and all(c.rr(r)==v for r,v in regs.items())
  assert c.get(H+0x3b96,2)==struct.pack('>H',damage)
  return yaw
 cases=0
 for start_phase in range(3) if rate==50 else (0,):
  span=(rate-start_phase+2)//3
  for impulse in range(-2,3):
   for age in range(span):
    stamp=0xfffffff8;field=(stamp+age)&0xffffffff;phase=start_phase+3*age
    actual=execute(field,stamp,phase,impulse,12345)
    expected=(12345+int(impulse*256*(span-age)/span))&65535
    assert actual==expected,(name,start_phase,age,impulse,actual,expected)
    # Fresh steering must propagate identically in the same rendered field.
    assert execute(field,stamp,phase,impulse,12345+73)==(actual+73)&65535
    cases+=1
 # Consecutive identical impulses: no world-boundary jump or half-tick pause.
 # Also exercise reversals and zero impulses, measuring the prior interval's
 # final increment across the next deadline.
 sequence=[2]*6+[-2]*6+[0,1,-1,2,0]
 raw=65500;phase=0;stamp=0;previous=None;previous_step=0;max_step=0;zero_steps=0
 for impulse in sequence:
  span=(rate-phase+2)//3;raw=(raw-impulse*256)&65535
  for age in range(span):
   actual=execute(stamp+age,stamp,phase+3*age,impulse,raw)
   if previous is not None:
    delta=(actual-previous+32768)%65536-32768
    assert abs(delta)<=33,(name,stamp,age,delta)
    max_step=max(max_step,abs(delta))
    if age and impulse:assert delta!=0,(name,stamp,age,'turn stopped')
   previous=actual
  stamp+=span;phase=(phase+3*span)%rate
 # Ground, repaired, invalid and stale samples must not move the camera.
 for args in [dict(height=0),dict(damage=0),dict(valid=0)]:assert execute(100,100,0,2,12345,**args)==12345
 assert execute(121,100,13,2,12345)==12345
 reports.append(dict(release=name,field_cases=cases,same_field_steering_cases=cases,consecutive_intervals=len(sequence),max_damage_yaw_step=max_step,registers_and_gameplay_unchanged=True))
 c.close()
print(json.dumps(reports,indent=2))
