#!/usr/bin/env python3
"""Audit the causal ordering experiment without claiming contact/full-course validity."""
import json,hashlib,re,struct
from pathlib import Path
from simulation_fixture import read_fixture,compare
P=Path(__file__).resolve().parents[1]/'tmp/prof'
control=P/'airborne-order-control';candidate=P/'airborne-order-candidate'
a=json.loads((control/'order-result.json').read_text());b=json.loads((candidate/'order-result.json').read_text())
assert a['identity'] and not b['identity']
assert (control/'slave.slave').read_bytes()==(candidate/'slave.slave').read_bytes()
# Initial fixture samples and complete live car/private/RNG state agree.
initial=compare(read_fixture(control),read_fixture(candidate));assert not initial['mismatches']
def dynamic_state(cap):
    m=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes()
    car=m['data_base']+0x7ffe-0x92e-m['memory_base'];priv=mem.index(b'4DA4PHYS')+12
    rng=m['data_base']+0x7ffe+0x228-m['memory_base']
    return mem[car:car+208]+mem[priv:priv+152]+mem[rng:rng+6]
assert dynamic_state(control)==dynamic_state(candidate)
for cap,result in ((control,a),(candidate,b)):
    assert len(result['records'])==len(result['bodies'])==28
    assert len(re.findall(r'^APPLIED ',(cap/'order-log.txt').read_text(),re.M))==28
    assert result['clearance_checks']==224
    for r,out in zip(result['records'],result['bodies']):
        assert r['tick']==out['tick'] and r['prediction']['pitch']==out['pitch'] and r['prediction']['carry']==out['carry']
        assert r['prediction']['velocities']==[out[f'v{i}'] for i in range(4)]
base=json.loads((P/'matched-flight50/landing-motion-check.json').read_text())['rows']
assert all(x['final_position']==[y[k] for k in ('x','y','z')] for x,y in zip(base,a['bodies']))
cumulative=[0,0,0]
for ca,cb,r in zip(a['bodies'],b['bodies'],b['records']):
    assert all(ca[k]==cb[k] for k in ('tick','pitch','carry','v0','v1','v2','v3'))
    cumulative=[x+y for x,y in zip(cumulative,r['correction'])]
    assert [cb[k]-ca[k] for k in ('x','y','z')]==cumulative
sa=read_fixture(control,'order-end.bin');sb=read_fixture(candidate,'order-end.bin');assert len(sa)==len(sb)==4
for (t,h,s),(u,j,z) in zip(sa,sb):
    assert (t,h)==(u,j)
    assert s[0x466:0x466+152]==z[0x466:0x466+152]
    assert s[0x152+0x18:0x152+0x74]==z[0x152+0x18:0x152+0x74]
native={r['tick']:r for r in json.loads((P/'matched-flight20/landing-motion-check.json').read_text())['rows']}
ix={r['tick']:r for r in a['bodies']};common=[]
for r in b['bodies']:
    t=r['tick']
    if t%5:continue
    n=native[t*2//5]['final_position']
    common.append(dict(seconds=t/50,control_error=[ix[t][k]-n[i] for i,k in enumerate(('x','y','z'))],
                       candidate_error=[r[k]-n[i] for i,k in enumerate(('x','y','z'))]))
# Saved fixture source is old only in non-kinematic work; prove six relevant
# assembly sources equal current code after removing comments/blank lines.
root=Path(__file__).resolve().parents[1];cur=root/'src';old=root/'tmp/fixtures/matched-flight232/source'
norm=lambda p:[l.split(';',1)[0].strip() for l in p.read_text().splitlines() if l.split(';',1)[0].strip()]
source_checks={}
for name in ('simulation_tilt.s','simulation_yaw.s','simulation_physics.s','simulation_a4000.s','simulation_centroid.s','simulation_centroid_hooks.s'):
    assert norm(cur/name)==norm(old/name);source_checks[name]=True
report=dict(runtime_accepted=False,matched_airborne_improvement=True,initial_equal_live_state_bytes=366,
    identity_exact_positions=28,verified_write_batches_per_run=28,predicted_pitch_carry_velocity_checks_per_run=28,
    positive_clearance_checks_per_run=224,unchanged_dynamics_checkpoints=4,common=common,
    correction_sum=cumulative,final_host_residues=b['records'][-1]['residues'],current_kinematic_sources_equal=source_checks,
    derivation='For a smooth direction change, matching source left-endpoint time T=.05 with h=.02 gives extra vector D*(T-h)/(2*h)*(u_old-u_new). Coefficient3/4 is time-derived, not fitted. u_new is predicted from current rebuilt geometry/gravity before actual contact; it is not a later input sample.',
    limits='Only matched straight fully-extended flight, corrected ticks4..31 (.08.. .62s); initial ticks1..3 remain unmodified. Leading-order direction correction, not an exact general modified flow. No contact/suspension-reset/general yaw/roll/collision law, runtime implementation, replay state or capacity proof.',
    decision='Keep as evidence for orientation/translation coupling. Do not install as an airborne-only workaround for the full course: baseline takeoff gravity/pitch mismatch remains and first-jump height already runs too high.',
    slave_sha256=hashlib.sha256((candidate/'slave.slave').read_bytes()).hexdigest())
(P/'airborne-order-decision.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
