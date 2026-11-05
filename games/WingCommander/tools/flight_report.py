#!/usr/bin/env python3
"""Report flight cadence, source changes, bounded PC costs and state trajectories."""
import argparse,json,math,struct,statistics
from pathlib import Path
from matrix_report import read_aprof
HZ=512*3546895
SIZE=0xfda0
# Hunk-1 ranges: 61 world entities, ten full ship slots.
STATE_RANGES = {
    'positions': (0x919a, 61*12), 'velocities': (0x9d6c, 61*12),
    'forward_vectors': (0xa148, 61*12), 'object_types': (0x96fe, 61*2),
    'ship_actions': (0x9564, 10*2), 'set_speeds': (0x99be, 10*4),
    'fuel': (0xa7cc, 10*4), 'gun_energy': (0x9546, 10*2),
    'shields': (0xa7f4, 10*4), 'armour': (0x9876, 10*8),
    'targets': (0x955a, 10), 'rng': (0x6f18, 4),
    'update_counter': (0x914c, 2), 'draw_counter': (0x9150, 2),
}

def equal_ranges(a, b):
    return {k: a[o:o+n] == b[o:o+n] for k, (o,n) in STATE_RANGES.items()}


def validate_trace(run, window, events, h):
    import _amigaxdev
    from amigaxdev import barto
    watch = {h+x for x in (0x698, 0x2da, 0x3378e, 0x34162)}
    trace = barto.load(str(run/(window['name']+'.bin')))
    records = [(pc, f.index, tuple(regs[:16])) for f in trace.fields
               for pc, _, regs in trace.instructions(f) if pc in watch]
    observed = [e for e in events[window['first_event']:window['end_event']]
                if e['pc'] in watch]
    if not records:raise ValueError('empty full trace')
    matches=[]
    for start,e in enumerate(observed):
        if (e['pc'],tuple(e['regs']))!=(records[0][0],records[0][2]):continue
        chunk=observed[start:start+len(records)]
        if len(chunk)!=len(records):continue
        delta=e['field']-records[0][1]
        if all((q['pc'],q['field']-delta,tuple(q['regs']))==r for q,r in zip(chunk,records)):
            matches.append((chunk,delta))
    if len(matches)!=1:raise ValueError('trace/observer PC, field or register mismatch')
    chunk,delta=matches[0]
    if [e for e in observed if delta<=e['field']<delta+len(trace.fields)]!=chunk:
        raise ValueError('trace lost an edge event')
    counts = {hex(pc-h): sum(r[0] == pc for r in records) for pc in watch}
    if counts['0x34162'] != len(trace.fields):
        raise ValueError('VBL count mismatch')
    return dict(fields=len(trace.fields), counts=counts, identical=True)


def read(run):
    m=json.loads((run/'result.json').read_text());h=m['hunks'][0];s=m['slave']
    events=[]
    for line in (run/'events.txt').read_text().splitlines():
        if line.startswith('#'):continue
        p=line.split()
        if len(p)!=31:raise ValueError('truncated event')
        events.append(dict(pc=int(p[0],16),field=int(p[1]),cycles=int(p[3]),regs=[int(v,16) for v in p[8:24]]))
    raw=(run/'states.bin').read_bytes() if m['state_snapshots'] else b''
    state_events=[e for e in events if e['pc']==h+0x698]
    if m['state_snapshots'] and len(raw)!=len(state_events)*SIZE:raise ValueError('state/event count mismatch')
    states=[]
    for i,e in enumerate(state_events if raw else []):
        b=raw[i*SIZE:(i+1)*SIZE]
        def v(offset,fmt):return struct.unpack_from('>'+fmt,b,0x7ffe+offset)
        states.append(dict(field=e['field'],cycles=e['cycles'],update=v(0x114e,'H')[0],draw=v(0x1152,'H')[0],position=v(0x119c,'3i'),velocity=v(0x1d6e,'3i'),forward=v(0x214a,'3i'),set_kps=v(0x19c0,'i')[0]/256*10,actual_kps=math.sqrt(sum(x*x for x in v(0x1d6e,'3i')))/256*10,rng=v(-4326,'I')[0],mode=v(-32630,'H')[0],status=v(0x1700,'10h'),state=v(0x1566,'10h'),nav_range=v(0x2b82,'i')[0],fuel=v(0x27ce,'i')[0],gun_energy=v(0x1548,'h')[0],bytes=b))
    census=[]
    for line in (run/'matrix-events.txt').read_text().splitlines():
        p=line.split()
        if p[0]=='C':census.append([int(x) for x in p[2:8]])
    result=dict(machine=m['machine'],iterations=m['fixture']['iterations'],windows=[])
    for w in m['windows']:
        ee=events[w['first_event']:w['end_event']]
        updates=[e for e in ee if e['pc']==h+0x698];pub=[e for e in ee if e['pc']==h+0x3378e]
        if len(updates)<2:
            if w['name']!='pause':raise ValueError('insufficient complete updates')
            result['windows'].append(dict(name='pause',updates=len(updates),publications=len(pub),vbls=sum(q['pc']==h+0x34162 for q in ee)))
            continue
        a,b=updates[0],updates[-1];sec=(b['cycles']-a['cycles'])/HZ
        samples=[c for c in census if a['cycles']<=c[1]<b['cycles'] and c[3]]
        ww=dict(name=w['name'],complete_intervals=len(updates)-1,seconds=sec,update_hz=(len(updates)-1)/sec,
                publications=sum(a['cycles']<=e['cycles']<b['cycles'] for e in pub),
                mean_changed_percent=100*sum(c[4] for c in samples)/sum(c[2] for c in samples) if samples else None,
                census_samples=len(samples),geometries=sorted(set(c[2]//320 for c in samples)))
        intervals=[(y['cycles']-x['cycles'])/HZ*1000 for x,y in zip(updates,updates[1:])]
        ww.update(mean_ms=statistics.mean(intervals),p95_ms=sorted(intervals)[math.ceil(.95*len(intervals))-1],max_ms=max(intervals))
        ss=[q for q in states if a['cycles']<=q['cycles']<=b['cycles']]
        if ss:
            if len(ss)!=len(updates) or any(((y['update']-x['update'])&65535)!=1 for x,y in zip(ss,ss[1:])):raise ValueError('world counter/entry mismatch')
            if ww['publications']!=len(updates)-1:raise ValueError('update/publication mismatch')
            travel=sum(math.dist(x['position'],y['position'])/256 for x,y in zip(ss,ss[1:]))
            ww.update(distance_km=travel,km_per_update=travel/(len(ss)-1),measured_kps=travel/sec,display_kps=[ss[0]['actual_kps'],ss[-1]['actual_kps']],update_counter_delta=(ss[-1]['update']-ss[0]['update'])&65535,nav_range=[ss[0]['nav_range'],ss[-1]['nav_range']],gun_energy=[min(q['gun_energy'] for q in ss),max(q['gun_energy'] for q in ss)],fuel=[ss[0]['fuel'],ss[-1]['fuel']])
        if w['aprof']:
            header,pcs,_,_,residual=read_aprof(run/(w['name']+'.aprof'))
            def share(lo,hi,base=h):return 100*sum(p[1] for p in pcs if base+lo<=p[0]<base+hi)/header['units']
            ww['pc_cost_percent']=dict(converters=share(0x17f6,0x1e04,s),limiter=share(0x17b8,0x17f6,s),world_dispatch_and_motion=share(0x65b4,0x10c7a),drawing=share(0x2d000,0x31fc2),math=share(0x2a9d4,0x2cbd8),gap=100*header['gap']/header['units'],residual=100*residual/header['units'])
        result['windows'].append(ww)
    if any(w['name']=='pause' for w in m['windows']):
        from cd32_runtime import BASE
        o=m['hunks'][1]-BASE
        a,b=[(run/n).read_bytes()[o:o+SIZE] for n in ('pause-start-fast.bin','pause-end-fast.bin')]
        checks=equal_ranges(a,b)
        clocks=[struct.unpack_from('>I',x,0x7f02)[0] for x in (a,b)]
        if not all(checks.values()) or clocks[1]-clocks[0]!=10:
            raise ValueError('pause world/clock invariant failed')
        result['pause_check']=dict(unchanged=checks,vbl_clock=clocks)
    return m,events,states,result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--compare');p.add_argument('--observer-control');p.add_argument('--validate-trace',choices=('coast-0','coast-1','coast-2'));a=p.parse_args()
    run=Path(a.run);m,e,states,result=read(run)
    if a.compare:
        _,_,other,_=read(Path(a.compare));n=min(len(states),len(other))
        if not n:raise ValueError('comparison requires state snapshots')
        result['matched_update_comparison']=dict(count=n,fields={key:all(states[i][key]==other[i][key] for i in range(n)) for key in ('update','draw','position','velocity','forward','set_kps','actual_kps','rng','status','state')})
        result['matched_update_comparison']['ranges']={k:all(equal_ranges(states[i]['bytes'],other[i]['bytes'])[k] for i in range(n)) for k in STATE_RANGES}
        if not all(result['matched_update_comparison']['fields'].values()) or not all(result['matched_update_comparison']['ranges'].values()):raise ValueError('matched update states differ')
    if a.observer_control:
        from PIL import Image
        other=Path(a.observer_control);om,oe,_,_=read(other)
        names=[]
        for w,v in zip(m['windows'][:3],om['windows'][:3]):
            if w['name']!=v['name'] or e[w['first_event']:w['end_event']]!=oe[v['first_event']:v['end_event']]:raise ValueError('observer control events differ')
            x,y=[Image.open(p/(w['name']+'.png')).convert('RGB') for p in (run,other)]
            if x.size!=y.size or x.tobytes()!=y.tobytes():raise ValueError('observer control pixels differ')
            names.append(w['name'])
        if len(names)!=3:raise ValueError('incomplete observer control')
        result['observer_control']=dict(windows=names,events_and_pixels_identical=True)
    if a.validate_trace:
        w=next(w for w in m['windows'] if w['name']==a.validate_trace)
        result['trace_validation']=validate_trace(run,w,e,m['hunks'][0])
    (run/'flight-report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
