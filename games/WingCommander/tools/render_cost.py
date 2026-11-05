#!/usr/bin/env python3
"""D1 call-site elapsed costs from the existing read-only PC observer.

No guest instrumentation is added. Times include callees, IRQs and bus stalls;
rows overlap and must not be added. A selected call is paired with its actual
next instruction at the same SP. The class-2 draw branch uses the same rule.
"""
import argparse
import hashlib
import json
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path
from frame_report import dist, summarise, records
from cd32_runtime import ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scopes(build, layout):
    original = ROOT/'tmp/game/WingCommanderCD32/data/wing.english'
    if digest(original) != '093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657':
        raise ValueError('pinned English executable required')
    code = original.read_bytes()[0x2c:0x2c+0x35ea4]
    h, s = layout['hunks'][0], layout['slave']
    rows = []
    def add(name, base, start, end):
        rows.append(dict(name=name, start=base+start, end=base+end))
    # Fixed call sites: enclosing drawing, messages and cockpit/view composition.
    for name, start, end in [('clear',0x306,0x30c), ('scene',0x320,0x326),
                              ('messages_overlay',0x38cc,0x38d0),
                              ('cockpit_composite',0xc4c,0xc52),
                              ('stars',0x2caa6,0x2ca5a),
                              ('objects_dispatch',0x294f0,0x294f6),
                              ('object_bitmap',0x2cac4,0x2caca),
                              ('object_scaled',0x2cb04,0x2cb0a),
                              ('object_rotated',0x2cb48,0x2cb4e)]:
        add(name,h,start,end)
    # Absolute callsites throughout the native hunk. These include all geometry
    # callers and the low-level glyph drawing calls (a subset of text layout).
    for name,target in [('geometry',0x2a086),('text_glyph',0x2fd6a)]:
        needle=b'\x4e\xb9'+target.to_bytes(4,'big')
        for at in range(0,len(code)-6,2):
            if code[at:at+6]==needle:add(name,h,at,at+6)
    listing=(build/'slave.lst').read_text()
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',listing,re.M)}
    wanted={'timing_scene_begin':'prediction', 'timing_scene_end':'restore',
            'timing_scene_snapshot':'world_snapshot', 'flight_delta':'delta_total',
            'flight_kalms_block':'changed_block', '$2a086(a6)':'geometry',
            '$46e6(a6)':'hud_after_publish'}
    for line in listing.splitlines():
        m=re.match(r'00:([0-9A-F]{8}) ([0-9A-F]+)\s+.*?\b(?:bsr\.w|jsr)\s+(\S+)',line)
        if m and m[3] in wanted:
            at=int(m[1],16);add(wanted[m[3]],s,at,at+len(m[2])//2)
    if not all(any(r['name']==v for r in rows) for v in wanted.values()):
        raise ValueError('missing listing anchors')
    # Measure the initial pose backup independently of arithmetic prediction.
    # Lazy attachment backups remain inside native scene cost, not this row.
    if 'timing_scene_save_active' in sy:
        matches=re.findall(r'^00:([0-9A-F]{8}) ([0-9A-F]+).*bsr\.w\s+timing_scene_save_active$',listing,re.M)
        if len(matches)!=1:raise ValueError('ambiguous selective backup anchor')
        start,encoded=matches[0];at=int(start,16)
        add('pose_backup',s,at,at+len(encoded)//2)
    else:
        begin=re.findall(r'^00:([0-9A-F]{8}) [0-9A-F]+.*lea\s+timing_scene_saved\(pc\),a1',listing,re.M)
        staged=[int(x,16) for x in re.findall(r'^00:([0-9A-F]{8}) [0-9A-F]+.*lea\s+timing_scene_staged\(pc\),a0',listing,re.M)]
        if len(begin)!=1:raise ValueError('ambiguous backup anchor')
        at=int(begin[0],16)
        add('pose_backup',s,at,min(x for x in staged if x>at))
    # Draw-entry FSTAT 4 is the frame boundary (pre-camera, pre-prediction).
    # FSTAT expansion is the unique move.w #4 immediately before frame_stat.
    candidates=[]
    lines=listing.splitlines()
    for i,line in enumerate(lines):
        m=re.match(r'00:([0-9A-F]{8}) .*move\.w\s+#4,-\(sp\)',line)
        if m and 'frame_stat' in '\n'.join(lines[i+1:i+3]):candidates.append(s+int(m[1],16))
    if len(candidates)!=1:raise ValueError('ambiguous draw marker')
    return dict(scopes=rows, draw=candidates[0], fixture_sha256=digest(build/'WingCommanderCD32.Slave'),
                layout=layout, symbols={'publish':s+sy['release_presented']})


def pair(events, definitions):
    starts=defaultdict(list)
    ends=defaultdict(list)
    for i,r in enumerate(definitions):
        starts[r['start']].append(i);ends[r['end']].append(i)
    active={};calls=[]
    for pc,cycle,sp in events:
        for i in ends[pc]:
            key=(i,sp)
            if key in active:
                begin=active.pop(key)
                if cycle<begin:raise ValueError('backwards call clock')
                calls.append((begin,cycle,definitions[i]['name']))
        for i in starts[pc]:
            key=(i,sp)
            if key in active:raise ValueError('unclosed/repeated call entry')
            active[key]=cycle
    if active:raise ValueError('incomplete call intervals')
    return calls


def report(run, control=None):
    cfg=json.loads((run/'cost-scopes.json').read_text())
    meta=json.loads((run/'result.json').read_text())
    if digest(run/'framestats.bin')!=meta['framestats_sha256']:
        raise ValueError('frame record hash mismatch')
    if not meta['complete'] or meta['fixture']['sha256']!=cfg['fixture_sha256']:
        raise ValueError('incomplete or different fixture')
    if control is not None:
        for name in ('framestats.bin','displaystats.bin'):
            if (run/name).read_bytes()!=(control/name).read_bytes():
                raise ValueError('observer changes recorded execution: '+name)
        ref=json.loads((control/'result.json').read_text())
        for name in ('fixture','machine','timing_core','baseline_cache_model','custom5','options','held_key','emulator_sha256','live_cpu'):
            if meta[name]!=ref[name]:raise ValueError('unmatched control: '+name)
    frames=[];events=[];clocks=set()
    with (run/'events.txt').open() as f:
        for line in f:
            if line.startswith('#'):continue
            q=line.split();pc=int(q[0],16);cyc=int(q[3]);sp=int(q[23],16)
            clocks.add(int(q[6]))
            events.append((pc,cyc,sp))
            if pc==cfg['draw']:frames.append((cyc,int(q[24])-meta['frame_epoch']))
    if len(clocks)!=1:raise ValueError('changing clock')
    if any(b[1]<a[1] for a,b in zip(events,events[1:])):
        raise ValueError('backwards observer clock')
    # Match the recorder's first full draw and drop its 20 warm-up frames.
    _,lines,recorded=records(run/'framestats.bin')
    field_ms=lines*records.line_ms
    n=sum(e==4 for e,_,_ in recorded)
    frames=[f for f in frames if f[1]>=0][:n]
    if len(frames)!=n:raise ValueError('incomplete observer draw coverage')
    bounds=[f[0] for f in frames][20:]
    if len(bounds)<500:raise ValueError('short capture')
    # Pair only the closed draw-to-draw window: no boot or flush partial calls.
    selected=[e for e in events if bounds[0]<=e[1]<bounds[-1]]
    calls=pair(selected,cfg['scopes'])
    units=clocks.pop()*64/1000
    per=[Counter() for _ in range(len(bounds)-1)]
    counts=Counter()
    for lo,hi,name in calls:
        i=bisect_right(bounds,lo)-1
        if hi>bounds[i+1]:raise ValueError('scope crosses draw boundary')
        per[i][name]+=(hi-lo)/units;counts[name]+=1
    for name in ('prediction','pose_backup','restore','clear','scene','objects_dispatch','delta_total','hud_after_publish'):
        if counts[name]!=len(per):raise ValueError('incomplete per-picture scope: '+name)
    for row in per:
        row['comparison_loop_history']=row['delta_total']-row['changed_block']
        if row['comparison_loop_history']<0:raise ValueError('negative conversion residual')
    # Predict/save is an enclosing scope; all rows are inclusive, never a pie chart.
    names=sorted({r['name'] for r in cfg['scopes']}|{'comparison_loop_history'})
    slow=[i for i,(a,b) in enumerate(zip(bounds,bounds[1:])) if (b-a)/units>field_ms]
    result=dict(run=run.name,control=control.name if control else None,
                neutrality='byte-identical frame and display ledgers' if control else 'not separately checked for this capture',
                frames=len(per),field_ms=field_ms,calls={name:counts[name] for name in names if name!='comparison_loop_history'}, scope='inclusive emulated elapsed ms, not hardware or exclusive CPU costs',
                per_call_ms={name:dist([(hi-lo)/units for lo,hi,k in calls if k==name]) for name in counts},
                per_frame_ms={name:dist([r[name] for r in per]) for name in names},
                over_one_field_frames=len(slow),
                over_one_field_ms={name:dist([per[i][name] for i in slow]) for name in names} if slow else {},
                frame_report=summarise(run),
                input_sha256={name:digest(run/name) for name in ('events.txt','cost-scopes.json','framestats.bin','displaystats.bin')})
    return result


def check_pairs():
    definitions=[dict(name='outer',start=10,end=20),dict(name='inner',start=11,end=12)]
    assert pair([(10,1,100),(11,2,96),(12,3,96),(20,5,100)],definitions)==[(2,3,'inner'),(1,5,'outer')]
    for broken in ([(10,1,100)], [(10,1,100),(20,5,104)], [(10,1,100),(10,2,100)], [(10,5,100),(20,1,100)]):
        try:pair(broken,definitions)
        except ValueError:pass
        else:raise ValueError('scope negative control accepted')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path);p.add_argument('--layout',type=Path)
    p.add_argument('--run',type=Path);p.add_argument('--control',type=Path)
    p.add_argument('--without-neutrality-control',action='store_true',help='report scopes without claiming observer neutrality for this capture')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if (ROOT/'tmp').resolve() not in a.output.resolve().parents or a.output.exists():
        p.error('fresh output in tmp/ required')
    if a.run and (bool(a.control)==a.without_neutrality_control or a.build or a.layout):
        p.error('--run requires --control or --without-neutrality-control, without --build/--layout')
    if not a.run and (not a.build or not a.layout or a.control or a.without_neutrality_control):
        p.error('scope generation requires --build and --layout')
    check_pairs()
    if a.run:
        result=report(a.run,a.control)
    else:result=scopes(a.build,json.loads(a.layout.read_text()))
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(a.output)


if __name__=='__main__':main()
