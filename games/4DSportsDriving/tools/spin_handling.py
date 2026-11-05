#!/usr/bin/env python3
"""Freeze paired-native physical handling bounds for an ordinary-input spin recovery."""
import argparse, hashlib, json, math, struct
from pathlib import Path
from simulation_fixture import read_fixture

def read(root):
    root=Path(root); meta=json.loads((root/'anchor.json').read_text()); hz=meta['active_simulation_word']
    assert meta['opponent']==0
    mem=(root/'memory.bin').read_bytes(); a4=meta['data_base']+0x7ffe-meta['memory_base']
    history=struct.unpack_from('>I',mem,a4-0x1770)[0]-meta['memory_base']; count=meta['simulation_tick']
    expected=bytes(1 if t<10*hz or 2*t>=25*hz else 5 if 2*t<23*hz else 9 for t in range(count))
    assert mem[history:history+count]==expected,'Input schedule differs'
    rows=[]
    for tick,rate,b in read_fixture(root):
        assert rate==hz
        x,y,z=struct.unpack_from('>iii',b,0x152)
        angles=[(v+512)%1024-512 for v in struct.unpack_from('>hhh',b,0x16a)]
        rows.append(dict(time=tick/rate,x=x,y=y,z=z,heading=angles[0],pitch=angles[1],roll=angles[2],
            speed=struct.unpack_from('>H',b,0x17c)[0],slip=struct.unpack_from('>h',b,0x188)[0],
            spin=struct.unpack_from('>h',b,0x190)[0],contact=b[0x213],wheel_surfaces=list(b[0x214:0x218]),crash=b[0x21b]))
    assert len(rows)==64 and [r['time'] for r in rows]==[i/5 for i in range(64)]
    assert tuple(rows[0][k] for k in ('x','y','z'))==(493824,512,347008)
    turn=[r for r in rows if r['time']>=10]
    metrics={'peak_slip':max(abs(r['slip']) for r in turn),'peak_spin':max(abs(r['spin']) for r in turn),
        'turn_path_length':sum(math.hypot(b['x']-a['x'],b['z']-a['z']) for a,b in zip(turn,turn[1:]))}
    metrics.update({'final_'+k:rows[-1][k] for k in ('x','y','z','heading','pitch','roll','speed','slip','spin')})
    active=[r for r in turn if r['spin']]
    if active:
        metrics['first_spin']=active[0]['time'];metrics['last_spin']=active[-1]['time']
    return dict(rows=rows,metrics=metrics,has_spin=bool(active),crash_free=all(r['crash']==0 for r in rows),
        recovered=rows[-1]['slip']==rows[-1]['spin']==0,ends_grounded=all(rows[-1]['wheel_surfaces']),
        slave_sha256=hashlib.sha256((root/'slave.slave').read_bytes()).hexdigest())

def diff(left,right):
    result={}
    for key in ('x','y','z','heading','pitch','roll','speed','slip','spin'):
        errors=[]
        for a,b in zip(left['rows'],right['rows']):
            if a['time']<10:continue
            d=a[key]-b[key]
            errors.append(abs((d+512)%1024-512) if key in ('heading','pitch','roll') else abs(d))
        result[key]=max(errors)
    return result

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate')
a=p.parse_args();low=read(a.native10);ref=read(a.native20);path=Path(a.criteria)
if not a.candidate:
    assert not path.exists(),'Never overwrite prospective criteria'
    assert all(r[k] for r in (low,ref) for k in ('has_spin','crash_free','recovered','ends_grounded'))
    limits={k:max(abs(low['metrics'][k]-v),0.2 if k in ('first_spin','last_spin') else 1) for k,v in ref['metrics'].items()}
    envelopes={k:max(v,1) for k,v in diff(low,ref).items()}
    result=dict(native10=low,native20=ref,limits=limits,envelopes=envelopes,
        rationale='Stock grid, ten seconds throttle then 1.5s right/1s left/release; no pose injection. Per-metric native10/20 disagreement with one raw-unit floor or 0.2s sample resolution. Separate maximum common-time errors during turn/recovery. Must spin, remain crash-free, finish grounded and recover zero spin/slip. Not airborne spin or collision coverage.')
    path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(native10=low['metrics'],native20=ref['metrics'],limits=limits,envelopes=envelopes),indent=2))
else:
    criteria=json.loads(path.read_text());assert criteria['native10']==low and criteria['native20']==ref
    c=read(a.candidate)
    checks={k:dict(reference=v,actual=c['metrics'].get(k),limit=criteria['limits'][k],passed=k in c['metrics'] and abs(c['metrics'][k]-v)<=criteria['limits'][k]+1e-8) for k,v in ref['metrics'].items()}
    checks.update({'max_'+k:dict(actual=v,limit=criteria['envelopes'][k],passed=v<=criteria['envelopes'][k]) for k,v in diff(c,ref).items()})
    checks.update({k:dict(passed=c[k]) for k in ('has_spin','crash_free','recovered','ends_grounded')})
    result=dict(candidate=c,checks=checks,passed=all(v['passed'] for v in checks.values()),criteria_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (Path(a.candidate)/'spin-handling.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2));raise SystemExit(0 if result['passed'] else 1)
