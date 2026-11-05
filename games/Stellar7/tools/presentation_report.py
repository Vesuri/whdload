#!/usr/bin/env python3
"""Summarize read-only beam observations; overlapping scopes include interrupts."""
import argparse
import json
import statistics
from pathlib import Path
from presentation_fields import SCOPES


def inspect(folder):
    raw=json.loads((Path(folder)/'presentation-events.json').read_text())
    events=raw['events'];hz=raw['field_hz'];ntsc=hz==60
    assert hz in (50,60)
    vbl=[e for e in events if e['site']=='vbl']
    assert [e['epoch'] for e in vbl]==list(range(raw['fields']))
    starts=[];total=0;geometry=[]
    for e in vbl:
        beam=e['beam'];line=(beam>>8)&511
        if beam&255==1:line+=1
        assert line<32, 'VBL observation unexpectedly delayed'
        lines=(262 if ntsc else 312)+(beam>>31&1)
        first_lol=((beam>>23)&1)^(line&1) if ntsc else 0
        assert ntsc or first_lol==0
        length=lines*227+((lines+first_lol)//2 if ntsc else 0)
        starts.append(total);total+=length
        geometry.append((lines,first_lol))
    unit=1000*raw['fields']/hz/total
    # Extend one field for observations after beam wrap but before its VBL
    # handler. The handler can be delayed by interrupt masking.
    lines,lol=geometry[-1]
    starts.append(total);geometry.append((lines,lol^(lines&1) if ntsc else 0))
    times=[];physical=0;previous_y=0
    for e in events:
        epoch=e['epoch'];beam=e['beam'];y=(beam>>8)&511;x=beam&255
        lines,lol=geometry[max(epoch,physical)]
        assert y<lines and x<228
        # UAE vhpos_adj exposes HP one clock ahead: HP=0 is the last
        # clock of this line; HP=1 is clock zero with the previous VP.
        if x==1:
            y+=1;x=0
        elif x==0:
            x=226+((beam>>23&1) if ntsc else 0)
        else:
            x-=1
        if y==lines:y=0
        if y<previous_y and previous_y>lines-32 and y<32:
            physical+=1
        physical=max(epoch,physical)
        assert physical in (epoch,epoch+1),'unobserved field boundary'
        if e['site']=='vbl':assert physical==epoch
        lines,lol=geometry[physical]
        if ntsc:assert (beam>>23&1)==(lol^(y&1)), 'inconsistent long-line bit'
        times.append(starts[physical]+y*227+((y+lol)//2 if ntsc else 0)+x)
        previous_y=y
    assert times==sorted(times),'beam timestamps moved backwards'
    result=dict(fields=raw['fields'],field_hz=hz,window_ms=1000*raw['fields']/hz,scopes={},presentations=[],scope='Complete observed calls only; inclusive beam elapsed time includes interrupts and wrapper overhead. Scopes overlap. Not pure DMA cost or physical hardware timing.')
    for name,(begin,end) in SCOPES.items():
        pending=None;durations=[]
        for e,t in zip(events,times):
            if e['site']==begin:
                assert pending is None,(name,'nested start')
                pending=t
            if e['site']==end and pending is not None:
                durations.append((t-pending)*unit);pending=None
        ordered=sorted(durations)
        result['scopes'][name]=dict(calls=len(ordered),total_ms=sum(ordered),mean_ms=statistics.mean(ordered) if ordered else None,p50_ms=statistics.median(ordered) if ordered else None,p95_ms=ordered[min(len(ordered)-1,int(len(ordered)*.95))] if ordered else None,max_ms=max(ordered) if ordered else None)
    for e,t in zip(events,times):
        if e['site'] in ('present_start','present_end'):
            result['presentations'].append(dict(e,time_ms=t*unit))
    result['geometry']=dict(lines=sorted(set(g[0] for g in geometry)),colour_clocks=total,long_lines=ntsc)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    print(json.dumps(inspect(p.parse_args().capture),indent=2))
