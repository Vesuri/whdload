#!/usr/bin/env python3
"""Cross-check actual wheel-stage data against separately captured clearance decisions."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tmp/prof'
report={}
for hz in (20,50):
    cap=P/f'baseline-wheel-landing{hz}'
    motion=json.loads((cap/'landing-motion-check.json').read_text())
    contact_cap=P/f'baseline-landing-contact{hz}'
    decisions=json.loads((contact_cap/'takeoff-plane.json').read_text())
    assert (cap/'slave.slave').read_bytes()==(contact_cap/'slave.slave').read_bytes()
    events={}
    for r in decisions['rows']:
        events.setdefault((r['tick'],r['wheel']),{})[r['event']]=r
    rows=[]
    previous=None
    for r in motion['rows']:
        stages=r['wheel_stages']
        for wheel in range(4):
            e=events[(r['tick'],wheel)]
            select=e['SELECT']
            # Independent runs must meet at the same actual wheel coordinates.
            assert stages['rebuilt'][wheel]==[select['old_world_'+a] for a in 'xyz']
            assert stages['translated'][wheel]==[select['world_'+a] for a in 'xyz']
            last=e.get('PENETRATION_ZERO',e.get('ZERO',e['AFTER']))
            assert stages['contact'][wheel]==[last['world_'+a] for a in 'xyz']
        wheels=[]
        for w in range(4):
            v={k:stages[k][w] for k in stages}
            delta=lambda a,b:[v[a][i]-v[b][i] for i in range(3)]
            rec=dict(wheel=w,rebuilt=v['rebuilt'],translation=delta('translated','rebuilt'),gravity_and_contact=delta('contact','translated'),suspension_addition=delta('suspension','contact'))
            if previous is not None:
                # Rebuilding includes previous final body orientation and the
                # current stored extension. It is not pure floor error.
                rec['next_basis_from_previous_contact']=[v['rebuilt'][i]-previous['contact'][w][i] for i in range(3)]
            wheels.append(rec)
        rows.append(dict(tick=r['tick'],time=r['tick']/hz,preupdate_pitch=(r['angles'][1]+32768)%65536-32768,extensions=r['extension'],wheels=wheels,vertical_rear_minus_front={k:values[2][1]-values[0][1] for k,values in stages.items()}))
        previous=stages
    report[str(hz)]=dict(slave_sha256=hashlib.sha256((cap/'slave.slave').read_bytes()).hexdigest(),motion_sha256=hashlib.sha256((cap/'landing-motion-check.json').read_bytes()).hexdigest(),independently_matched_wheel_stages=len(rows)*4*3,rows=rows)
first={20:311,50:778}
comparison={}
for hz,tick in first.items():
    r=next(r for r in report[str(hz)]['rows'] if r['tick']==tick)
    following=next(r for r in report[str(hz)]['rows'] if r['tick']==tick+1)
    comparison[str(hz)]=dict(time=r['time'],rear_minus_front=r['vertical_rear_minus_front'],rear=r['wheels'][2],next_front_rebuild_delta=following['wheels'][0]['next_basis_from_previous_contact'],next_rear_rebuild_delta=following['wheels'][2]['next_basis_from_previous_contact'])
native=comparison['20']['rear_minus_front']
candidate=comparison['50']['rear_minus_front']
contributions=dict(initial_gap=candidate['rebuilt']-native['rebuilt'],motion_and_contact=(candidate['contact']-candidate['translated'])-(native['contact']-native['translated']),suspension=(candidate['suspension']-candidate['contact'])-(native['suspension']-native['contact']))
assert sum(contributions.values())==candidate['suspension']-native['suspension']
report['first_contact_vertical_gap_difference']=dict(contributions=contributions,total=candidate['suspension']-native['suspension'])
report['first_front_contact_comparison']=comparison
report['scope']='No counterfactual simulation. Wheel stages independently match actual clearance-probe runs. Suspension addition includes restoring baseline wheel-to-body offset; do not interpret it as pure spring motion. Next-basis delta includes orientation, centroid, extension update and projection. Different timestep endpoints are not matched physical states.'
(P/'baseline-wheel-ledger.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(comparison,indent=2))
