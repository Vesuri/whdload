"""Live steering phase oracle: pristine engine and independent XYZ projection."""
from pathlib import Path
import sys,json
exec(Path('tools/check_native_phase_incremental.py').read_text().split('results=[];native_checks=0')[0])
try:
 for name in sys.argv[1:]:
  root=Path('tmp/prof')/name;data=json.loads((root/'motion.json').read_text())
  x=None;pending=None;checks=[];position=[F(0)]*3;start=None;turns=0
  for row in data['rows']:
   if row['kind']=='INPUT':
    assert pending is None,row
    if row['interval']==0:
     assert x is None and row['velocity']==0 and row['phase_calls']==0,row
     continue
    assert row['mask']==15 and row['road']==255 and row['fall_velocity']==0 and row['skid']==row['pitch']==row['roll']==0 and row['automatic']==1,row
    if x is None:
     assert row['velocity']==row['rpm']==0 and row['gear']==1 and row['phase_calls']==0,row
     x=Incremental((0,0,1));start=[row[k] for k in ['x8','y8','z8']]
    pending=row
   elif row['kind']=='STEP' and pending is not None:
    before=pending;pending=None;turns+=bool(before['turning'])
    # The untouched engine fixture resets its globals on each evaluation.
    # Set the held native turning input in that pristine image for this frame.
    b=bytearray(initial_memory);b[0xf790-0x8002]=before['turning'];initial_memory=bytes(b)
    tr=[before[k] for k in ['sin_yaw','cos_yaw','sin_pitch','cos_pitch']]
    def native_projection(v):
     sy,cy,sp,cp=tr;p=v+(v>>1);y=p*sp//16384;z=p*cp//16384
     return [z*sy//16384,y,z*cy//16384]
    vectors=[]
    def project(v):
     whole=int(v);lo=native_projection(whole);hi=native_projection(whole+1)
     vec=[F(a)+(v-whole)*(b-a) for a,b in zip(lo,hi)];vectors.append(vec);return vec[0]
    phase=x.phase;n=before['interval'];expected=x.advance(n,before['throttle'],before['braking'])
    for vec in vectors:
     dt=min(n,8-phase);n-=dt;phase=(phase+dt)%8
     position=[a+b*dt/8 for a,b in zip(position,vec)]
    assert n==0
    actual=(F(row['phase_current_v'],65536),F(row['phase_current_r'],65536),row['gear'])
    pose=[F(row['x8']*65536+row['position_fraction_x']+row['position_carry_x']*512,65536)]
    pose += [F(row[k]*65536+row[f'position_fraction_{axis}']+row[f'position_carry_{axis}']*512,65536) for axis,k in [(1,'y8'),(2,'z8')]]
    pose=[a-b for a,b in zip(pose,start)]
    assert row['velocity']==int(actual[0]) and row['rpm']==int(actual[1]),row
    good=actual==expected[:3] and pose==position and row['phase']==x.phase and row['phase_valid']==1
    checks.append(dict(field=row['field'],turning=before['turning'],heading=before['heading'],actual=encode(actual),expected=encode(expected[:3]),position=encode(pose),expected_position=encode(position),passed=good))
  assert checks and turns
  report=dict(passed=all(c['passed'] for c in checks),checks=len(checks),turning_force_frames=turns,results=checks,scope='Actual steering input, grounded flat automatic, changing native turning force. Pristine engine oracle and independent projection of captured native Q14 trig. Exact fractional XYZ and scalars per complete frame; not independent steering-angle dynamics, contact or FPS acceptance.')
  (root/'phase-steering.json').write_text(json.dumps(report,indent=2)+'\n');print(name,report['passed'],len(checks),turns,[c for c in checks if not c['passed']][:2],flush=True);assert report['passed']
finally:ok(u.uc_close(h))
