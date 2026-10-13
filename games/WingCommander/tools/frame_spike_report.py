#!/usr/bin/env python3
"""C4: separate visible display intervals from internal processing intervals.

The existing slave recorder supplies queue/world timestamps; its IRQ ledger
supplies actual display fields. A completed queue request must map to exactly
one subsequent display before the following queue request. Whole-world ticks
between queue submissions are attributed to the following displayed interval.
This is correlation, not isolated routine-cost attribution.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
from cd32_runtime import ROOT
from frame_report import records, display_records, dist, pct, WARMUP_FRAMES


def steady_gate(intervals, tick_counts):
    assert len(intervals) >= 500, 'insufficient display intervals'
    assert sum(n > 0 for n in tick_counts) >= 100, 'world-tick coverage missing'
    assert pct(intervals,.5) == pct(intervals,.95) == 1, 'visible steady-flight spikes'


def report(run, steady=False):
    meta=json.loads((run/'result.json').read_text())
    assert meta['complete'] and meta['fixture']['buffered'] and meta['observer']
    raw=(run/'framestats.bin').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==meta['framestats_sha256']
    hz,lines,events=records(run/'framestats.bin');line_ms=records.line_ms
    shown=display_records(run/'displaystats.bin')
    # Requiring one queue event between successive displays makes the join
    # fail loudly if either instrument skips or duplicates a publication.
    queues=[(i,t) for i,(event,field,t) in enumerate(events) if event==16]
    matched=[];q=0;last_display=-1
    for field,line,index,plane,copper in shown:
        now=field*lines+line
        pending=[]
        while q<len(queues) and queues[q][1]<now:
            if queues[q][1]>last_display:pending.append(queues[q])
            q+=1
        if pending:
            assert len(pending)==1, 'multiple queues for one display'
            matched.append((field,*pending[0]))
        else:
            assert not matched, 'display without a recorded queue'
        last_display=now
    matched=matched[WARMUP_FRAMES:]
    intervals=[];ticks=[];groups=defaultdict(lambda:dict(display=[],queue=[],world=[]))
    for (f0,i0,t0),(f1,i1,t1) in zip(matched,matched[1:]):
        segment=events[i0:i1]
        count=sum(e==3 for e,_,_ in segment)
        starts=[t for e,_,t in segment if e==2]
        ends=[t for e,_,t in segment if e==3]
        assert len(starts)==len(ends)==count, 'partial world boundary'
        assert all(b>=a for a,b in zip(starts,ends))
        interval=f1-f0;intervals.append(interval);ticks.append(count)
        group=groups[count];group['display'].append(interval*lines*line_ms)
        group['queue'].append((t1-t0)*line_ms)
        group['world'].append(sum(b-a for a,b in zip(starts,ends))*line_ms)
    assert intervals and any(ticks), 'empty workload'
    if steady:steady_gate(intervals,ticks)
    magic,ledger_hz,count,size=struct.unpack_from('>4sIII',(run/'displaystats.bin').read_bytes())
    assert magic==b'WCDS' and ledger_hz==hz and size==32
    ledger=(run/'displaystats.bin').read_bytes()
    forecasts=[struct.unpack_from('>IHHIIIIII',ledger,16+i*size) for i in range(count)]
    return dict(run=run.name,steady_gate_passed=True if steady else None,
        fixture_sha256=meta['fixture']['sha256'],field_hz=hz,
        intervals=len(intervals),fields_per_picture=dict(sorted(Counter(intervals).items())),
        display_interval_ms=dist([i*lines*line_ms for i in intervals]),
        world_ticks_per_display_interval=dict(sorted(Counter(ticks).items())),
        catchup_intervals=sum(n>1 for n in ticks),
        around_world_ticks={str(k):dict(count=len(v['display']),
            display_interval_ms=dist(v['display']),queue_interval_ms=dist(v['queue']),
            world_work_ms=dist(v['world'])) for k,v in sorted(groups.items())},
        prediction_target_misses=sum(r[0]!=r[5] for r in forecasts),
        prediction_fraction_misses=sum(r[8]!=r[7]+((r[0]-r[6])&0xffffffff)*10 for r in forecasts),
        hashes={name:hashlib.sha256((run/name).read_bytes()).hexdigest()
                for name in ('framestats.bin','displaystats.bin','result.json')})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--steady',nargs='+',type=Path,required=True)
    p.add_argument('--turn',nargs='*',type=Path,default=[])
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        p.error('fresh output below tmp required')
    rows=[report(r,True) for r in a.steady]+[report(r) for r in a.turn]
    assert len({r['fixture_sha256'] for r in rows})==1, 'use the same fixture'
    negatives=[]
    for label,intervals,ticks in (
        ('missed-fields',[1]*450+[2]*150,[1]*120+[0]*480),
        ('half-rate',[2]*600,[1]*120+[0]*480),
        ('no-world-coverage',[1]*600,[0]*600)):
        try:steady_gate(intervals,ticks)
        except AssertionError as e:negatives.append(dict(name=label,rejected=str(e)))
        else:raise AssertionError('negative control accepted: '+label)
    result=dict(runs=rows,negative_controls=negatives,
        scope='actual displayed cadence; queue intervals are CPU-work cadence, not screen stutter; no hardware calibration')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    for row in rows:
        print(row['run'],row['fields_per_picture'],row['around_world_ticks'])
if __name__=='__main__':main()
