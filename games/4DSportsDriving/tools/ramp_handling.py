#!/usr/bin/env python3
"""Prospective paired-native acceptance for the coherent two-second ramp fall."""
import argparse,hashlib,json,struct
from pathlib import Path
from simulation_fixture import read_fixture

def read(root):
    root=Path(root); meta=json.loads((root/'anchor.json').read_text())
    blob=(root/'memory.bin').read_bytes(); rate=meta['active_simulation_word']
    a4=meta['data_base']+0x7ffe-meta['memory_base']
    ptr=struct.unpack_from('>I',blob,a4-0x1770)[0]-meta['memory_base']
    count=meta['simulation_tick']
    expected=bytes(1 if t<rate or t>=2*rate else 5 if 2*t<3*rate else 9 for t in range(count))
    assert blob[ptr:ptr+count]==expected,'Input schedule differs'
    rows=[]
    for tick,hz,b in read_fixture(root):
        assert hz==rate
        x,y,z=struct.unpack_from('>iii',b,0x152)
        heading,pitch,roll=((v+512)%1024-512 for v in struct.unpack_from('>hhh',b,0x16a))
        rows.append(dict(time=tick/hz,x=x,y=y,z=z,heading=heading,pitch=pitch,roll=roll,
                         speed=struct.unpack_from('>H',b,0x17c)[0],contact=b[0x213],crash=b[0x21b]))
    assert len(rows)==21 and [r['time'] for r in rows]==[t/10 for t in range(21)]
    assert tuple(rows[0][k] for k in ('x','y','z'))==(1474560,20480,288358)
    # Ignore initial cached contact flags; require an actual airborne interval,
    # subsequent wheel contact and a crash-free climb at the end.
    airborne=[r for r in rows[1:] if not r['contact']]
    assert airborne and airborne[0]['time']==0.1
    first=next(r for r in rows[1:] if r['contact'])
    full=next(r for r in rows[1:] if r['contact']==4)
    lowest=min(rows,key=lambda r:r['y'])
    metrics=dict(first_contact=first['time'],four_wheel_contact=full['time'],
                 minimum_height=lowest['y'],minimum_height_time=lowest['time'])
    metrics.update({'final_'+k:rows[-1][k] for k in ('x','y','z','heading','pitch','roll','speed')})
    return dict(rows=rows,metrics=metrics,crash_free=all(not r['crash'] for r in rows),
                ends_grounded=rows[-1]['contact']==4,
                slave_sha256=hashlib.sha256((root/'slave.slave').read_bytes()).hexdigest())

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate')
a=p.parse_args();low,ref=read(a.native10),read(a.native20);path=Path(a.criteria)
windows={'airborne':(0.1,0.7),'landing_climb':(0.8,2.0)}
def errors(left,right):
    return {phase+'_'+axis:max(abs(l[axis]-r[axis]) for l,r in zip(left['rows'],right['rows']) if start<=l['time']<=end)
            for phase,(start,end) in windows.items() for axis in ('x','y','z')}
if not a.candidate:
    assert not path.exists(),'Never overwrite prospective criteria'
    assert low['crash_free'] and ref['crash_free'] and low['ends_grounded'] and ref['ends_grounded']
    limits={k:max(abs(low['metrics'][k]-v),0.1 if k in ('first_contact','four_wheel_contact','minimum_height_time') else 1) for k,v in ref['metrics'].items()}
    trajectory_limits={k:max(v,1) for k,v in errors(low,ref).items()}
    result=dict(native10=low,native20=ref,limits=limits,trajectory_limits=trajectory_limits,
                rationale='Per-metric native10/20 disagreement; one raw-unit floor or0.1s observation resolution. Separate XYZ maximum common-time error envelopes before contact (0.1..0.7s) and during landing/climb (0.8..2s). Require airborne transition, subsequent four-wheel contact, crash-free outcome and grounded endpoint. Coherent synthetic ramp fall only; not natural jump or collision acceptance.')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(native10=low['metrics'],native20=ref['metrics'],limits=limits,trajectory_limits=trajectory_limits),indent=2))
else:
    criteria=json.loads(path.read_text());assert criteria['native10']==low and criteria['native20']==ref
    candidate=read(a.candidate)
    checks={k:dict(reference=v,actual=candidate['metrics'][k],limit=criteria['limits'][k],passed=abs(candidate['metrics'][k]-v)<=criteria['limits'][k]+1e-8) for k,v in ref['metrics'].items()}
    checks.update({k:dict(actual=v,limit=criteria['trajectory_limits'][k],passed=v<=criteria['trajectory_limits'][k]) for k,v in errors(candidate,ref).items()})
    checks.update({k:dict(passed=candidate[k]) for k in ('crash_free','ends_grounded')})
    result=dict(candidate=candidate,checks=checks,passed=all(c['passed'] for c in checks.values()),criteria_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (Path(a.candidate)/'ramp-handling.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(checks,indent=2));raise SystemExit(0 if result['passed'] else 1)
