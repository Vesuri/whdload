"""Pristine-engine/trig reconstruction of the complete flat steering captures."""
from pathlib import Path
import json,sys,math,itertools
exec(Path('tools/check_native_phase_incremental.py').read_text().split('results=[];native_checks=0')[0])
trig_cache={}
def trig(angle):
 if angle not in trig_cache:
  result=[]
  for fn in [0x80da,0x80d4]:
   reg(17,0x2000);reg(5,a4);reg(8,0x4ffff0);pack(0x4ffff0,'Ih',0x490000,angle)
   ok(u.uc_emu_start(h,g(fn),0x490000,1000000,10000));value=reg(9)&65535;result.append(value-65536 if value>=32768 else value)
  trig_cache[angle]=result
 return trig_cache[angle]
def pose(r):
 return [F(r[k])+F(r[f'position_fraction_{i}']+512*r[f'position_carry_{i}'],65536) for i,k in [('x','x8'),('1','y8'),('2','z8')]]
reports=[];curves=[];capture_rates=[]
try:
 for suffix in ['a500','slow','020','040']:
  name='c3-steering-phase-v2-'+suffix;p=Path('tmp/prof')/name;rows=json.loads((p/'motion.json').read_text())['rows']
  x=Incremental((0,0,1));position=[F(213368),F(0),F(200224)];heading=F(360);age=0;curve={0:(x.v,heading,position[:])};pending=None;checks=0;segments=0;observed=[]
  for row in rows:
   if row['kind']=='INPUT':
    if not row['interval']:continue
    assert pending is None;pending=row
   elif row['kind']=='INTEGRATED' and pending:
    before=pending;pending=None
    assert before['consumed']-before['interval']==age
    assert pose(before)==position,(name,'terrain correction',age,pose(before),position)
    assert before['mask']==15 and before['pitch']==before['roll']==before['spin']==before['fall_velocity']==before['skid']==0
    assert before['automatic']==1 and before['throttle'] in [0,22] and before['braking']==0
    if x.v==x.r==0:x.anchor=(F(0),F(0));x.phase=0
    b=bytearray(initial_memory);b[0xe94a-0x8002]=before['road'];initial_memory=bytes(b)
    n=before['interval']
    while n:
     remain=8-x.phase;dt=min(n,remain);segments+=1
     # Native rate4, no turn-force/skid threshold in this fixture. Its
     # eligibility is evaluated from native phase-anchor velocity.
     h0=heading
     if int(x.anchor[0]):heading+=F(dt,2)
     sy,cy=trig(int(heading))
     end,_=endpoint((int(x.anchor[0]),int(x.anchor[1]),x.gear),before['throttle'],0)
     dv=F(end[0])-x.anchor[0];dr=F(end[1])-x.anchor[1];forecast=x.v+dv*remain/8
     whole=int(forecast);fraction=F((forecast-whole)*64//1,64)
     def projected(v):
      speed=v+(v>>1)
      return [speed*sy//16384,0,speed*cy//16384]
     lo=projected(whole);hi=projected(whole+1);vector=[F(a)+fraction*(b-a) for a,b in zip(lo,hi)]
     increments=[F(v*65536//8,65536) for v in vector]
     v0=x.v;p0=position[:]
     for t in range(1,dt+1):curve[age+t]=(v0+dv*t/8,h0+(heading-h0)*t/dt,[a+b*t for a,b in zip(p0,increments)])
     position=[a+b*dt for a,b in zip(position,increments)];x.v+=dv*dt/8;x.r+=dr*dt/8;x.phase+=dt;age+=dt;n-=dt
     if x.phase==8:
      old=x.gear;rpm=int(x.r)
      if rpm<2000 and old>1:x.gear-=1
      elif rpm>5200 and old<4:x.gear+=1
      if old!=x.gear:
       a,b=model.TABLE[old];c,d=model.TABLE[x.gear];x.r=F(model.convert(model.convert(rpm,a,b),d,c))
      x.anchor=(x.v,x.r);x.phase=0
    actual=(F(row['phase_current_v'],65536),F(row['phase_current_r'],65536),row['gear'],row['heading'],pose(row))
    expected=(x.v,x.r,x.gear,int(heading),position)
    assert actual==expected,(name,age,actual,expected)
    assert not row['turning'] and not row['skid'];checks+=1;observed.append(row)
  assert pending is None and checks>0
  rates=[]
  for a,b in zip(observed,observed[1:]):
   t=b['consumed']-a['consumed'];rates.append((abs(b['phase_current_v']-a['phase_current_v'])/65536/t,math.dist(pose(a),pose(b))/8/t))
  capture_rates.append((max(r[0] for r in rates),max(r[1] for r in rates)))
  report=dict(name=name,passed=True,returns=checks,segments=segments,fields=age,scope='Global trajectory, no per-frame pose resets. Captured road-state history is an input; pristine engine and trig plus independent Q6 XYZ integration reproduce every captured fractional V/R/gear/heading/XYZ return. Dense fields retain each actual frame chunk projection, not linear interpolation across a whole frame.')
  (p/'steering-curve.json').write_text(json.dumps(dict(report,curve=[dict(field=t,velocity=str(v),heading=str(hh),position=[str(z) for z in pos]) for t,(v,hh,pos) in curve.items()]),indent=2)+'\n');reports.append(report);curves.append(curve)
 common=min(max(c) for c in curves);spreads=[0.,0.,0.]
 for t in range(common+1):
  for a,b in itertools.combinations([c[t] for c in curves],2):
   spreads=[max(spreads[0],float(abs(a[0]-b[0]))),max(spreads[1],float(abs(a[1]-b[1]))),max(spreads[2],math.dist(a[2],b[2])/8)]
 ordinary=json.loads(Path('tmp/prof/c3-steering-phase-v2-a500/motion.json').read_text())['rows'];frame=max(r['interval'] for r in ordinary if r['kind']=='INPUT')
 vr=max(r[0] for r in capture_rates);pr=max(r[1] for r in capture_rates);bounds=[frame*vr,frame*.5,frame*pr]
 summary=dict(passed=all(a<=b+1e-9 for a,b in zip(spreads,bounds)),common_elapsed_fields=common,ordinary_a500_frame_fields=frame,spread_velocity_heading_distance=spreads,bound_velocity_heading_distance=bounds,reports=reports,scope='C3 original held-steering fixture, full common elapsed interval, after exact global reconstruction. Road classification is captured, not independently predicted. Does not pass lap/checkpoint, C4 or full C3 by itself.')
 Path('tmp/c3-steering-curve-comparison.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));assert summary['passed']
finally:ok(u.uc_close(h))
