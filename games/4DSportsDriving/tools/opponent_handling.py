#!/usr/bin/env python3
"""Paired-native, prospective handling gate for the normal five-second grid start."""
import argparse, hashlib, json, math, struct
from pathlib import Path
from simulation_fixture import read_fixture

def read(root):
    root=Path(root); meta=json.loads((root/'anchor.json').read_text())
    assert meta['opponent']==1
    rate=meta['active_simulation_word']; mem=(root/'memory.bin').read_bytes()
    a4=meta['data_base']+0x7ffe-meta['memory_base']
    history=struct.unpack_from('>I',mem,a4-0x1770)[0]-meta['memory_base']
    count=meta['simulation_tick']
    expected=bytes(1 if t<rate or t>=2*rate else 5 if 2*t<3*rate else 9 for t in range(count))
    assert mem[history:history+count]==expected,'unexpected player controls'
    rows=[]
    for tick,hz,state in read_fixture(root):
        assert hz==rate
        row={'time':tick/hz}
        for name,off in [('player',0x152),('opponent',0x222)]:
            x,y,z=struct.unpack_from('>iii',state,off)
            heading,pitch,roll=[(v+512)%1024-512 for v in struct.unpack_from('>hhh',state,off+0x18)]
            row[name]=dict(x=x,y=y,z=z,heading=heading,pitch=pitch,roll=roll,
                speed=struct.unpack_from('>H',state,off+0x2a)[0],
                route=struct.unpack_from('>H',state,off+0x4a)[0],segment=state[off+0xce],
                contact=state[off+0xc1],crash=state[off+0xc9])
        rows.append(row)
    assert len(rows)==51 and [r['time'] for r in rows]==[n/10 for n in range(51)]
    metrics={}
    for name in ('player','opponent'):
        for key in ('x','y','z','heading','pitch','roll','speed','route','segment'):
            metrics[name+'_final_'+key]=rows[-1][name][key]
        metrics[name+'_path_length']=sum(math.hypot(b[name]['x']-a[name]['x'],b[name]['z']-a[name]['z']) for a,b in zip(rows,rows[1:]))
    return dict(rows=rows,metrics=metrics,
        crash_free=all(r[n]['crash']==0 for r in rows for n in ('player','opponent')),
        ends_grounded=all(rows[-1][n]['contact']==4 for n in ('player','opponent')),
        slave_sha256=hashlib.sha256((root/'slave.slave').read_bytes()).hexdigest())

def differences(left,right):
    result={}
    for name in ('player','opponent'):
        for key in ('x','y','z','heading','pitch','roll','speed'):
            def delta(a,b):
                d=a[name][key]-b[name][key]
                return abs((d+512)%1024-512) if key in ('heading','pitch','roll') else abs(d)
            result[name+'_'+key]=max(delta(a,b) for a,b in zip(left['rows'],right['rows']))
    return result

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('native10'); p.add_argument('native20'); p.add_argument('criteria'); p.add_argument('--candidate')
a=p.parse_args(); low=read(a.native10); ref=read(a.native20); path=Path(a.criteria)
if not a.candidate:
    assert not path.exists(),'Never overwrite prospective criteria'
    assert low['crash_free'] and ref['crash_free'] and low['ends_grounded'] and ref['ends_grounded']
    limits={k:max(abs(low['metrics'][k]-v),0 if k.endswith(('_route','_segment')) else 1) for k,v in ref['metrics'].items()}
    envelopes={k:max(v,1) for k,v in differences(low,ref).items()}
    result=dict(native10=low,native20=ref,limits=limits,envelopes=envelopes,
        rationale='Five-second unmodified grid start, opponent1 and standard common-time controls. Per-metric and common-time maximum deviations may not exceed Normal/A2500 disagreement, with one raw-unit floor for continuous quantities. Discrete route/segment allow only native disagreement. Both cars must remain crash-free and finish grounded. Path length sums common 100ms samples; this is handling coverage, not PAL-field capacity or all opponents/tracks.')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(native10=low['metrics'],native20=ref['metrics'],limits=limits,envelopes=envelopes),indent=2))
else:
    criteria=json.loads(path.read_text()); assert criteria['native10']==low and criteria['native20']==ref
    candidate=read(a.candidate)
    checks={k:dict(actual=candidate['metrics'][k],reference=v,limit=criteria['limits'][k],passed=abs(candidate['metrics'][k]-v)<=criteria['limits'][k]+1e-8) for k,v in ref['metrics'].items()}
    checks.update({'max_'+k:dict(actual=v,limit=criteria['envelopes'][k],passed=v<=criteria['envelopes'][k]) for k,v in differences(candidate,ref).items()})
    checks.update({k:dict(passed=candidate[k]) for k in ('crash_free','ends_grounded')})
    result=dict(passed=all(x['passed'] for x in checks.values()),candidate=candidate,checks=checks,criteria_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (Path(a.candidate)/'opponent-handling.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(checks,indent=2)); raise SystemExit(0 if result['passed'] else 1)
