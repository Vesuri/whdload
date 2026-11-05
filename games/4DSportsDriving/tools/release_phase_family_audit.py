#!/usr/bin/env python3
"""Reconstruct gravity/reset histories across the frozen phase family."""
import hashlib,json,struct
from pathlib import Path
from fractions import Fraction as F
from simulation_fixture import read_fixture
P=Path(__file__).resolve().parents[1]/'tmp/prof'
cases=[('nominal',20,'crest-release-d9-20','natural-crest20'),
       ('nominal',50,'crest-release-d9-50','crest-d9e7903'),
       ('minus64',20,'phase-release-minus64-20','phase-minus64-native20'),
       ('plus64',20,'phase-release-plus64-20','phase-plus64-native20'),
       ('minus64',50,'phase-release-minus64-50','phase-minus64-d9'),
       ('pitch_plus1',20,'release-pitch-plus1-native20',None)]
report=[]
for phase,hz,name,baseline in cases:
    cap=P/name;trace=json.loads((cap/'takeoff-plane.json').read_text())
    samples=read_fixture(cap,'release-end.bin');states={t:s for t,m,s in samples}
    matching=None
    if baseline:
        reference={t:s for t,m,s in read_fixture(P/baseline,'bridge-end.bin')}
        assert all(s==reference[t] for t,m,s in samples);matching=len(samples)
    target=hz*58//5;state=states[target];wheels=[]
    for w in range(4):
        rows=[r for r in trace['rows'] if r['wheel']==w and r['tick']<=target]
        assert rows[0]['event']=='SELECT'
        v=F(rows[0]['velocity'])+(F(rows[0]['velocity_fraction'],5) if hz==50 else 0)
        suffix=[];all_gravity=[];resets=[]
        for r in rows:
            observed=F(r['velocity'])+(F(r['velocity_fraction'],5) if hz==50 else 0)
            assert observed==v,(name,w,r['tick'],r['event'],observed,v)
            if r['event']=='GRAVITY':
                v+=F((21 if w<2 else 15)*20,hz);suffix.append(r);all_gravity.append(r['tick'])
            elif r['event'] in ('ZERO','PENETRATION_ZERO'):
                v=F(0);suffix=[];resets.append(dict(tick=r['tick'],event=r['event'],plane=r['plane']))
        saved=F(struct.unpack_from('>h',state,0x152+0x4c+2*w)[0])+(F(struct.unpack_from('>h',state,0x466+8+4*w)[0],5) if hz==50 else 0)
        assert saved==v
        assert [r['tick'] for r in suffix]==list(range(suffix[0]['tick'],target+1))
        first=suffix[0];select=next(r for r in rows if r['tick']==first['tick'] and r['event']=='SELECT')
        word=lambda x:(x+32768)%65536-32768
        normal=[select['normal_'+a] for a in 'xyz']
        origin=[64*word(select['base_'+a]+select['node_'+a]) for a in 'xyz']
        distances=[F(sum((select[prefix+a]-o)*n for a,o,n in zip('xyz',origin,normal)),8192) for prefix in ('old_world_','world_')]
        checks=[r for r in trace['plane_checks'] if r['tick']==first['tick'] and r['wheel']==w and r['event']=='SELECT']
        assert len(checks)==1 and abs(float(distances[1])-checks[0]['unrounded_world_distance'])<1e-9
        wheels.append(dict(wheel=w,last_reset=resets[-1],first_uninterrupted_gravity_tick=first['tick'],first_gravity_plane=select['plane'],
            first_gravity_clearance=select['clearance'],raw_old_new_clearance=list(map(str,distances)),
            first_gravity_old_new_z=[select['old_world_z'],select['world_z']],gravity_ticks=all_gravity,
            resets=resets,completed_velocity=str(saved),effective_gravity_start=str(F(first['tick']-1,hz))))
    report.append(dict(phase=phase,hz=hz,capture=name,exact_baseline_full_states=matching,
        trace_sha256=hashlib.sha256((cap/'takeoff-plane.json').read_bytes()).hexdigest(),wheels=wheels))
index={(r['phase'],r['hz']):r for r in report}
assert index['minus64',20]['wheels'][0]['completed_velocity']=='210'
assert index['nominal',20]['wheels'][0]['completed_velocity']=='189'
assert index['minus64',20]['wheels'][0]['first_gravity_plane']==12
assert index['nominal',20]['wheels'][0]['first_gravity_plane']==14
assert index['minus64',50]['wheels'][0]['completed_velocity']==index['nominal',50]['wheels'][0]['completed_velocity']=='882/5'
assert [w['completed_velocity'] for w in index['pitch_plus1',20]['wheels']]==[w['completed_velocity'] for w in index['nominal',20]['wheels']]
probe=json.loads((P/'release-pitch-plus1-native20/intervention.json').read_text());assert probe['whole_ram_verified'] and len(probe['changed_bytes'])==1
out=dict(cases=report,pitch_intervention=probe,conclusion='Phase-minus64 native front wheels start accumulating gravity on uphill plane12 before the crest and retain it into plane14. Rear wheels also briefly accumulate on plane12 but reset again. One-unit native pitch intervention raises raw clearance yet does not reproduce the extra retained gravity step. The combined approach pose/contact history matters; nominal seam timing is not a universal release law.',
    scope='Read-only phase probes match59 complete baseline states each. Pitch experiment is one verified body-word intervention, not a proposed runtime correction or full handling result. Frozen criteria unchanged.')
(P/'release-phase-family-audit.json').write_text(json.dumps(out,indent=2)+'\n')
for r in report:
    print(r['phase'],r['hz'],'velocity',[w['completed_velocity'] for w in r['wheels']],
        'first final gravity tick',[w['first_uninterrupted_gravity_tick'] for w in r['wheels']],
        'plane',[w['first_gravity_plane'] for w in r['wheels']])
