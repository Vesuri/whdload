"""Native-engine oracle for grounded skid/slope integration before terrain correction."""
from pathlib import Path
import sys,json,math
exec(Path('tools/check_native_phase_incremental.py').read_text().split('results=[];native_checks=0')[0])
def decay(t,c,last,n):
 if last!=t:c=0
 if n==8:return (t*7//8,0,t*7//8)
 coefficient=round(65536*(1-(7/8)**(n/8)))
 q=t*65536+c-t*coefficient-(c*coefficient//65536)
 return (q//65536,q%65536,q//65536)
def native_project(v,tr):
 sy,cy,sp,cp=tr;p=v+(v>>1);y=p*sp//16384;z=p*cp//16384
 return [z*sy//16384,y,z*cy//16384]
try:
 for name in sys.argv[1:]:
  root=Path('tmp/prof')/name;data=json.loads((root/'motion.json').read_text())
  x=None;pending=None;checks=[];position=[F(0)]*3;start=None;offroad=0;decays=0;model_calls=0;modeled_fields=0;skids=0;exits=0;spin_carry=0;spin_last=0;first_unsupported=None
  for row in data['rows']:
   if row['kind']=='INPUT':
    assert pending is None,row
    if row['interval']==0:
     assert x is None and row['velocity']==0 and row['phase_calls']==0,row
     continue
    if row['automatic']!=1 or row.get('crash',0):
     first_unsupported={k:row[k] for k in ['field','mask','fall_velocity','automatic','phase_valid']}
     break
    if x is None:
     assert row['velocity']==row['rpm']==0 and row['gear']==1 and row['phase_calls']==0,row
     x=Incremental((0,0,1));start=[row[k] for k in ['x8','y8','z8']]
    pending=row
   elif row['kind']=='INTEGRATED' and pending is not None:
    before=pending;pending=None;offroad+=not before['road']
    position=[F(before['x8']*65536+before['position_fraction_x']+before['position_carry_x']*512,65536)]
    position += [F(before[k]*65536+before[f'position_fraction_{axis}']+before[f'position_carry_{axis}']*512,65536) for axis,k in [(1,'y8'),(2,'z8')]]
    b=bytearray(initial_memory);b[0x9910-0x8002]=before['mask'];b[0xf790-0x8002]=before['turning'];b[0xe94a-0x8002]=before['road'];b[0xaf31-0x8002]=before['skid'];b[0xf791-0x8002]=before['grade_disabled'];struct.pack_into('>h',b,0x944c-0x8002,before['sin_pitch']);initial_memory=bytes(b)
    tr=[before[k] for k in ['sin_yaw','cos_yaw','sin_pitch','cos_pitch']]
    n=before['interval'];modeled_fields+=n;t=before['throttle'];carry=before['throttle_carry'];last=before['throttle_last'];segments=[]
    while n:
     model_calls+=1
     end,_=endpoint((int(x.anchor[0]),int(x.anchor[1]),x.gear),t,before['braking'])
     remaining=8-x.phase;dt=min(n,remaining)
     dv=(F(end[0])-x.anchor[0]) if before['mask'] else F(0);dr=F(end[1])-x.anchor[1];forecast=x.v+dv*remaining/8
     assert forecast>=0
     whole=int(forecast);lo=native_project(whole,tr);hi=native_project(whole+1,tr)
     fraction=F((forecast-whole)*64//1,64)
     vector=[F(a)+fraction*(b-a) for a,b in zip(lo,hi)]
     if before['skid']:
      vector=[F(before[f'held_vector_{axis}'])+F(before[f'held_fraction_{axis}'],65536) for axis in range(3)]
     position=[a+(b if dt==8 else F((b*65536//8)*dt,65536)) for a,b in zip(position,vector)]
     x.v+=dv*dt/8;x.r+=dr*dt/8;x.phase+=dt;n-=dt
     if before['mask'] and x.gear and not before['road'] and t>30:
      old=(t,carry);t,carry,last=decay(t,carry,last,dt);decays+=1
      segments.append(dict(fields=dt,before=old,after=(t,carry)))
     if x.phase==8:
      old=x.gear;rpm=int(x.r)
      if rpm<2000 and old>1:x.gear-=1
      elif rpm>5200 and old<4:x.gear+=1
      if old!=x.gear:
       a,b=model.TABLE[old];c,d=model.TABLE[x.gear];x.r=F(model.convert(model.convert(rpm,a,b),d,c))
      x.anchor=(x.v,x.r);x.phase=0
    if 'fall_carry' in before:
     fc=before['fall_carry'];accel=before['fall_accel']
     if before['fall_last']!=before['fall_velocity']:fc=0;accel=0
     dt=F(before['interval'],8)
     position[1]+=-dt*(before['fall_velocity']+F(fc,8))+accel*dt*(1-dt)/2
    if before['skid']:
     skids+=1
     spin_carry=before['spin_carry'];spin_last=before['spin_last']
     if before['spin']!=spin_last:spin_carry=0
     if before['interval']==8:
      spin=int(F(before['spin']*9,10));spin_carry=0
     else:
      full=before['spin']*65536+spin_carry
      loss=round(65536*(1-(9/10)**(before['interval']/8)))
      full=(abs(full)-abs(full)*loss//65536)*(-1 if full<0 else 1)
      spin=int(F(full,65536));spin_carry=full-spin*65536
     spin_last=spin
     a,b=model.TABLE[x.gear];mph=model.convert(int(x.r),a,b)
     expected_skid=255 if spin and mph>=18 else 0
     assert row['spin']==spin and bool(row['skid'])==bool(expected_skid),(name,before,row,spin,expected_skid)
     if not expected_skid:
      exits+=1;spin_carry=0;t=t*7//8;carry=0;last=t
     assert row['spin_carry']==spin_carry and row['spin_last']==spin_last,(before,row,spin_carry,spin_last)
     assert all((row[f'held_vector_{axis}'],row[f'held_fraction_{axis}'])==(before[f'held_vector_{axis}'],before[f'held_fraction_{axis}']) for axis in range(3)),(before,row)
    actual=(F(row['phase_current_v'],65536),F(row['phase_current_r'],65536),row['gear'])
    pose=[F(row['x8']*65536+row['position_fraction_x']+row['position_carry_x']*512,65536)]
    pose += [F(row[k]*65536+row[f'position_fraction_{axis}']+row[f'position_carry_{axis}']*512,65536) for axis,k in [(1,'y8'),(2,'z8')]]
    # Absolute per-frame position includes the native ground correction already
    # present at entry. The later ground/contact routine is outside this oracle.
    good=actual==(x.v,x.r,x.gear) and (pose==position if 'fall_carry' in before else [pose[0],pose[2]]==[position[0],position[2]]) and row['phase']==x.phase and row['phase_valid']==1 and (row['throttle'],row['throttle_carry'],row['throttle_last'])==(t,carry,last)
    good=good and row['velocity']==int(x.v) and row['rpm']==int(x.r)
    good=good and row['phase_calls']==model_calls and row['phase_frames']==len(checks)+1 and row['interval']==before['interval']
    checks.append(dict(field=row['field'],skid=before['skid'],pitch=before['pitch'],roll=before['roll'],road=before['road'],interval=before['interval'],actual=encode(actual),expected=encode((x.v,x.r,x.gear)),position=encode(pose),expected_position=encode(position),throttle_actual=(row['throttle'],row['throttle_carry'],row['throttle_last']),throttle_expected=(t,carry,last),decays=segments,passed=good))
  assert checks and skids and exits
  report=dict(passed=all(c['passed'] for c in checks),checks=len(checks),offroad_frames=offroad,decay_segments=decays,engine_segments=model_calls,consumed_fields=modeled_fields,skid_frames=skids,skid_exits=exits,first_unsupported=first_unsupported,complete_capture_validated=first_unsupported is None,results=checks,scope='Automatic flight/skid/slope integration. Y displacement only checked if fall companions are captured. Continuous scalar phase oracle; per-frame XYZ starts from actual terrain-corrected entry pose and ends before later contact/terrain work. Pristine engine, held skid vectors, r^T spin and throttle, discrete skid exit. Not independent terrain/contact/steering dynamics or whole-trajectory acceptance.')
  (root/'phase-air.json').write_text(json.dumps(report,indent=2)+'\n');print(name,report['passed'],len(checks),offroad,decays,'skid',skids,'exits',exits,'first unsupported',first_unsupported,[c for c in checks if not c['passed']][:2],flush=True);assert report['passed']
finally:ok(u.uc_close(h))
