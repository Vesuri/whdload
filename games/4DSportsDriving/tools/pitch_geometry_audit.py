#!/usr/bin/env python3
"""Independently verify geometry trace and reject the paired fraction candidate."""
import json,hashlib,struct,re
from pathlib import Path
from native_contact_response import sine,rotate,atan_native
from simulation_fixture import read_fixture,compare
P=Path(__file__).resolve().parents[1]/'tmp/prof'
cap=P/'pitch-geometry-d9';d=json.loads((cap/'geometry.json').read_text());rows=d['records']
build={(r[0],r[1]):r[2:] for r in rows['BUILD']};built={(r[0],r[1]):r[2:] for r in rows['BUILT']}
def matrix(p,f=0):
    k,t=divmod(p*256+f,256)
    s=(sine(k)*(256-t)+sine(k+1)*t)//256;c=(sine(k+256)*(256-t)+sine(k+257)*t)//256
    return [16384,0,0,0,c,-s,0,s,c]
def baseline_angle(t,m):
    wheels=[]
    for w in range(4):
        local=build[t,w];a=rotate(local,m);b=rotate([0,-local[1],0],m)
        wheels.append([x+y for x,y in zip(a,b)])
    x=-(wheels[2][2]+wheels[3][2]-wheels[0][2]-wheels[1][2])
    y=wheels[2][1]+wheels[3][1]-wheels[0][1]-wheels[1][1]
    return atan_native(x,y)-256
poses={};mismatches=[];local_errors=[]
for r in rows['POSE']:
    tick,car,pitch,roll,heading,pf,rf,*m=r
    assert roll==heading==rf==0 and m==matrix(pitch)
    poses[tick]=(m,pitch,pf)
    assert baseline_angle(tick,m)==pitch
    fractional=matrix(pitch,pf);angle=baseline_angle(tick,fractional)
    if angle!=pitch:mismatches.append(dict(tick=tick,pitch=pitch,fraction=pf,fractional_geometry_native_angle=angle))
    for w in range(4):
        assert rotate(build[tick,w],m)==built[tick,w]
        alt=rotate(build[tick,w],fractional)
        local_errors.append(dict(tick=tick,wheel=w,delta=[a-b for a,b in zip(alt,built[tick,w])]))
for tick,w,selector,distance,lookup,x,y,z in rows['MOVE']:
    m,pitch,pf=poses[tick]
    assert selector==-1 and lookup==pitch
    assert [x,y,z]==rotate([0,0,distance],m)
control=P/'fractional-pitch-identity';candidate=P/'fractional-pitch-geometry'
cd=json.loads((control/'fractional-result.json').read_text());nd=json.loads((candidate/'fractional-result.json').read_text())
assert cd['identity'] and not nd['identity']
initial=compare(read_fixture(control),read_fixture(candidate));assert not initial['mismatches']
ref={r['tick']:r for r in json.loads((P/'crest-d9e7903/bridge.json').read_text())['rows']}
assert all(r==ref[r['tick']] for r in cd['bodies'])
full={t:s for t,hz,s in read_fixture(P/'crest-d9e7903','bridge-end.bin')}
samples=read_fixture(control,'fractional-end.bin');assert all(s==full[t] for t,hz,s in samples)
for p,q in ((control,cd),(candidate,nd)):
    assert len(q['writes'])==400 and len(re.findall(r'^APPLIED ',(p/'fractional-log.txt').read_text(),re.M))==400
body={r['tick']:r for r in nd['bodies']};aligned=0
for t,hz,state in read_fixture(candidate,'fractional-end.bin'):
    if t in body:
        r=body[t];assert tuple(r[k] for k in ('x','y','z'))==struct.unpack_from('>iii',state,0x152)
        assert tuple(r[k] for k in ('heading','pitch','roll'))==struct.unpack_from('>hhh',state,0x16a)
        aligned+=1
errors=next(r['error'] for r in nd['common'] if r['time']==13)
assert errors==dict(y=3467,z=-4,pitch=12)
criteria=P/'natural-crest-criteria.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(criteria)=='90570d37e39d7fbdf804bbc497959ffe30e60f51bbb60c3e938f041c1d3401db'
report=dict(accepted=False,source_slave_sha256=sha(candidate/'slave.slave'),
    read_only=dict(exact_matrices=135,nonzero_pitch_carries=sum(pf!=0 for m,p,pf in poses.values()),exact_wheel_projections=540,exact_movement_vectors=540,all_movement_selectors=-1,exact_full_states=d['matching_full_states'],
        naive_fractional_matrix_baseline_rounding_changes=mismatches,max_local_wheel_delta=[max(abs(r['delta'][i]) for r in local_errors) for i in range(3)]),
    control=dict(verified_writes=400,exact_body_updates=200,exact_full_states=len(samples)),
    candidate=dict(verified_writes=400,body_updates=200,aligned_saved_states=aligned,initial_exact_states=initial['equal_samples'],
        altered_matrices=sum(r['modified']!=r['original'] for r in nd['poses']),
        altered_native_baselines=sum(r['native_baseline']!=r['anchored_baseline'] for r in nd['angles']),
        errors_at_13s=errors,canonical_errors_at_13s=next(r['error'] for r in cd['common'] if r['time']==13)),
    criteria_sha256=sha(criteria),decision='Reject: height3467>1247 and pitch12>11 at13s. Fractional wheel-matrix feedback plus anchored old pitch is not a standalone handling fix.',
    scope='Straight heading0/roll0 diagnostic451..650 only. Later body-obstacle matrices remain native integer; no general fractional-orientation/replay/capacity acceptance. No time interpolation.')
(P/'pitch-geometry-decision.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
