#!/usr/bin/env python3
"""Verify native gravity-state ownership and audit the separated-release test."""
import hashlib,json,re,struct
from fractions import Fraction
from pathlib import Path
from simulation_fixture import read_fixture,compare
P=Path(__file__).resolve().parents[1]/'tmp/prof'
cap=P/'native-release-support'
result=json.loads((cap/'callback-intervention.json').read_text())
raw=(P.parents[0]/'game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
code=raw[0x28:0x28+0x3a04c]
# Exact original code guards: eligibility, accumulate, subtract, both resets.
guards={0xcb06:'4a6c0bc0',0xcb0a:'6f000122',0xcb70:'d150',
        0xcb86:'3031084c',0xcb8c:'9190',0xcca2:'4270084c',0xd1b4:'4270084c'}
for off,hexbytes in guards.items():
    expected=bytes.fromhex(hexbytes);assert code[off:off+len(expected)]==expected
initial=compare(read_fixture(cap),read_fixture(P/'continuous-support-native-reset'))
assert initial['equal_samples']==initial['samples']==46
assert len(result['interventions'])==536
assert len(re.findall(r'^APPLIED ',(cap/'callback.txt').read_text(),re.M))==536
body={r['tick']:r for r in result['bodies']};assert sorted(body)==list(range(451,651))
aligned=0
for t,hz,state in read_fixture(cap,'callback-end.bin'):
    if t not in body:continue
    r=body[t];assert tuple(r[k] for k in ('x','y','z'))==struct.unpack_from('>iii',state,0x152)
    assert tuple(r[k] for k in ('heading','pitch','roll'))==struct.unpack_from('>hhh',state,0x16a)
    aligned+=1
assert result['airborne_handoff_verified']
# All returned persistent states are native nonnegative gravity accumulators.
assert all(r['model']['velocity']>=0 for r in result['interventions'])
assert all(r['model']['velocity']==0 for r in result['interventions'] if r['model']['supported'])
old=json.loads((P/'crest-release-d9-velocity-audit.json').read_text())
native=next(r for r in old['rates'] if r['hz']==20)
ages=[]
for w in range(4):
    n=native['wheels'][w]
    seams=[r for r in result['interventions'] if r['wheel']==w and not r['model']['supported']
           and any(e.get('release_gravity_reset') for e in r['model']['events'])]
    assert len(seams)==1
    seam=seams[0];event=next(e for e in seam['model']['events'] if e.get('release_gravity_reset'))
    release=(seam['tick']-1+event['time'])/50
    v=next(r['model']['velocity'] for r in result['interventions'] if r['tick']==580 and r['wheel']==w)
    acceleration=n['acceleration_per_second'];age=11.6-release
    assert abs(v-acceleration*age)<1e-9
    native_v=float(Fraction(n['completed_velocity']))
    effective=float(Fraction(n['effective_start_time']))
    secant=next(r['time_seconds'] for r in old['plane_segment_crossings'] if r['hz']==20 and r['wheel']==w)
    gap=native_v-v
    assert abs(gap-acceleration*(release-effective))<1e-9
    ages.append(dict(wheel=w,release_time=release,gravity_age_at_11_6=age,velocity=v,native_velocity=native_v,
        velocity_gap=gap,native_effective_gravity_start=effective,native_raw_plane_secant=secant,
        effective_start_to_native_secant_seconds=secant-effective,
        native_secant_to_candidate_seam_seconds=release-secant,
        scope='Exact gravity-age accounting; secant and candidate crease are different geometry constructions, not proven physical release times or additive causal effects.'))
criteria_path=P/'natural-crest-criteria.json';criteria=json.loads(criteria_path.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(criteria_path)=='90570d37e39d7fbdf804bbc497959ffe30e60f51bbb60c3e938f041c1d3401db'
ref={r['tick']:r for r in json.loads((P/'natural-crest20/bridge.json').read_text())['rows']}
errors={k:body[650][k]-ref[260][k] for k in ('y','z','pitch')}
assert errors==dict(y=2332,z=307,pitch=8)
report=dict(accepted=False,verified_writes=536,body_updates=200,aligned_saved_states=aligned,
    initial_exact_states=46,slave_sha256=sha(cap/'slave.slave'),code_guards={hex(k):v for k,v in guards.items()},
    state_contract='Native car+$4c per-wheel state accumulates downward gravity on positive clearance, is subtracted from world Y, and resets to zero on contact. It is not a persistent general normal-reaction velocity.',
    errors_at_13s=errors,original_limits={k:criteria['envelope'][k] for k in errors},
    criteria_sha256=sha(criteria_path),gravity_age_audit=ages,
    decision='Reject for height. Separating transient reaction from native gravity removes the large v2 regression but does not satisfy the existing handling gate. Do not fit release impulses to the reference values.',
    scope='Prototype intervention452..585; native continuation through650. Not full16s handling, replay, general geometry or capacity acceptance.',
    model_sha256=sha(Path(__file__).with_name('native_release_support_reference.py')))
(P/'native-release-support-decision.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('code_guards','gravity_age_audit')},indent=2))
for r in ages[::2]:
    print('wheel',r['wheel'],'release',r['release_time'],'velocity gap',r['velocity_gap'],'effective start -> secant -> seam(ms)',1000*r['effective_start_to_native_secant_seconds'],1000*r['native_secant_to_candidate_seam_seconds'])
