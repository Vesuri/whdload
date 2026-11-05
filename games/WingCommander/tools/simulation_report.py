#!/usr/bin/env python3
"""Conservative native-world reservations and design budget models (not new-code FPS)."""
import argparse
import hashlib
import json
import math
import statistics
import struct
from pathlib import Path
from flight_report import HZ, SIZE, STATE_RANGES
from simulation_capture import cpu


def report(run):
    m = json.loads((run/'result.json').read_text())
    if not m['complete']:
        raise ValueError('incomplete capture')
    h = m['hunks'][0]
    events = []
    for line in (run/'events.txt').read_text().splitlines():
        if line.startswith('#'):
            continue
        p = line.split()
        if len(p) != 31:
            raise ValueError('truncated event')
        events.append(dict(pc=int(p[0],16)-h, cycles=int(p[3]), sp=int(p[23],16), unit=int(p[7])))
    starts = [i for i,e in enumerate(events) if e['pc']==0x698]
    states = (run/'states.bin').read_bytes()
    if len(states) != len(starts)*SIZE or len(starts)<41:
        raise ValueError('insufficient or mismatched state samples')
    samples = []
    for ordinal in range(10,40):
        first, last = starts[ordinal:ordinal+2]
        # No sample may straddle a debugger field-window stop.
        if not any(w['first_event']<=first and last<w['end_event'] for w in m['windows']):
            continue
        ee = events[first:last]
        def one(pc):
            found = [e for e in ee if e['pc']==pc]
            if len(found)!=1:
                raise ValueError('non-ordinary frame')
            return found[0]
        enter, ret, draw = one(0x2a8), one(0x6bc), one(0x6c0)
        one(0x3378e)
        if any(e['unit'] != int(cpu(m['live_cpu'])['unit']) for e in ee):
            raise ValueError('clock unit changed')
        if enter['sp']+4!=ret['sp'] or ret['sp']!=draw['sp'] or ret['sp']!=events[first]['sp']:
            raise ValueError('root return stack mismatch')
        if not events[first]['cycles']<enter['cycles']<ret['cycles']<draw['cycles']<events[last]['cycles']:
            raise ValueError('non-monotonic frame')
        state = states[ordinal*SIZE:(ordinal+1)*SIZE]
        nextstate = states[(ordinal+1)*SIZE:(ordinal+2)*SIZE]
        counter = lambda b,o: struct.unpack_from('>H',b,o)[0]
        if any(((counter(nextstate,o)-counter(state,o))&65535)!=1 for o in (0x914c,0x9150)):
            raise ValueError('world/draw counter mismatch')
        types = struct.unpack_from('>61h',state,0x96fe)
        s = (ret['cycles']-enter['cycles'])/HZ*1000
        frame = (events[last]['cycles']-events[first]['cycles'])/HZ*1000
        samples.append(dict(update=ordinal, world_ms=s, residual_ms=frame-s,
            elapsed_clock_counts=(ret['cycles']-enter['cycles'])/enter['unit'],
            ships=sum(x>=12 for x in types), objects=sum(x>3 for x in types)))
    if len(samples)<25 or min(s['ships'] for s in samples)<5:
        raise ValueError('insufficient busy combat coverage')
    s = statistics.mean(x['world_ms'] for x in samples)
    r = statistics.mean(x['residual_ms'] for x in samples)
    p95 = sorted(x['world_ms'] for x in samples)[math.ceil(.95*len(samples))-1]
    # Unchanged-world budget, zero added implementation overhead. S includes
    # preemption; residual includes input/HUD/drawing/waits. These are bounds,
    # not measurements of implemented B/C/D or exclusive CPU utilisation.
    model = {}
    for name,hz in [('C20',20),('C25',25),('C50',50),('D10',10)]:
        model[name] = dict(world_reservation_percent=hz*s/10,
            render_budget_hz=max(0,1000-hz*s)/r,
            p95_reservation_percent=hz*p95/10)
    model['B'] = dict(render_budget_hz=1000/(s+r),
        world_reservation_percent=100*s/(s+r))
    state_hashes = {name:[hashlib.sha256(states[i*SIZE+off:i*SIZE+off+n]).hexdigest()
        for i in range(10,40)] for name,(off,n) in STATE_RANGES.items()}
    return dict(cell=run.name, samples=len(samples), world_ms=s, world_p95_ms=p95,
        elapsed_clock_counts=statistics.mean(x['elapsed_clock_counts'] for x in samples),
        residual_ms=r, ships=sorted(set(x['ships'] for x in samples)),
        objects=[min(x['objects'] for x in samples), max(x['objects'] for x in samples)],
        cpu=cpu(m['live_cpu']), model=model, state_hashes=state_hashes,
        input_sha256={f:hashlib.sha256((run/f).read_bytes()).hexdigest() for f in ('result.json','events.txt','states.bin')})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    if (root/'tmp').resolve() not in a.output.resolve().parents:
        raise ValueError('derived report must stay in tmp')
    rows = [report(run) for run in a.runs]
    baseline = next(r for r in rows if r['cell']=='020-default')
    baseline_hashes = baseline['state_hashes']
    for row in rows:
        row['equal_to_020_by_update'] = {k:v==baseline_hashes[k] for k,v in row.pop('state_hashes').items()} if row is not baseline else {}
    baseline.pop('state_hashes',None)
    a.output.write_text(json.dumps(rows,indent=2)+'\n')
    print('| Cell | n | world ms mean / p95 | elapsed clock counts | residual ms | B Hz / % | C20 Hz / % | C25 Hz / % | C50 Hz / % | D10 Hz / % |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for r in rows:
        budgets = [f"{r['model'][k]['render_budget_hz']:.1f} / {r['model'][k]['world_reservation_percent']:.1f}" for k in ('B','C20','C25','C50','D10')]
        print(f"| {r['cell']} | {r['samples']} | {r['world_ms']:.2f} / {r['world_p95_ms']:.2f} | {r['elapsed_clock_counts']:.0f} | {r['residual_ms']:.2f} | "+' | '.join(budgets)+' |')


if __name__ == '__main__':
    main()
