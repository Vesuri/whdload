#!/usr/bin/env python3
"""Scene publication counts, measured beam time and tracker position; no rate target."""
import argparse,collections,json,statistics
from pathlib import Path
from intro_capture import SCENES
from intro_check import run_events


def report(run):
    meta=json.loads((run/'result.json').read_text());h=meta['hunks'];events=run_events(run,meta)
    if not meta['complete']:raise ValueError('incomplete intro')
    def first(pc,condition=lambda row:True):
        return next(e for e in events if e[0]==pc and condition(e))
    boundaries=[('reset',first(0xf800d2)),('game-startup',first(h[3]))]
    boundaries += [(name,first(h[n]+offset)) for n,offset,name in SCENES]
    boundaries += [(f'credits-{page:02d}',first(h[0]+0x1fdd6,lambda e:e[13]&65535==page)) for page in range(18)]
    boundaries += [('cycle-complete',first(h[0]+0x1fe48)),('menu',first(h[0]+0x20214))]
    if any(b[3]<a[3] for (_,a),(_,b) in zip(boundaries,boundaries[1:])):raise ValueError('scene order changed')
    # Validate the marker for the whole run, not merely the short trace window.
    pending=None;publications=[];other=[]
    for e in events:
        if e[0]==h[0]+0x3378e:
            if pending is not None:raise ValueError('nested publication')
            pending=[e,[]]
        elif e[0]==h[0]+0x33ce2:
            if pending is None:other.append(e)
            else:pending[1].append(e)
        elif e[0]==h[0]+0x3379a:
            if pending is None or len(pending[1])!=1:raise ValueError('publication does not have exactly one COP2LC store')
            publications.append(pending[0]);pending=None
    if pending is not None:raise ValueError('unfinished publication')
    vbl=[e for e in events if e[0]==h[0]+0x34162]
    if len(vbl)<100 or any(b[1]-a[1]!=1 or b[24]-a[24]!=1 for a,b in zip(vbl,vbl[1:])):raise ValueError('VBL/physical-field disagreement')
    if any(e[6]!=28375160 or e[5]!=312 for e in events):raise ValueError('unexpected clock/geometry')
    # UAE CYCLE_UNIT=512; baseclock=8*CHIPSET_CLOCK. VBL entry has small
    # interrupt latency; elapsed time comes from monotonic emulator cycle stamps.
    seconds=lambda a,b:(b[3]-a[3])*8/(512*a[6])
    scenes=[]
    for (name,start),(next_name,end) in zip(boundaries,boundaries[1:]):
        frames=[e for e in publications if start[3]<=e[3]<end[3]]
        gaps=[b[1]-a[1] for a,b in zip(frames,frames[1:])]
        scenes.append(dict(scene=name,next=next_name,fields=end[1]-start[1],
                           seconds=seconds(start,end),publications=len(frames),
                           fields_per_publication_mean=statistics.mean(gaps) if gaps else None,
                           gap_histogram=dict(sorted(collections.Counter(gaps).items())),
                           other_copper_writes=sum(start[3]<=e[3]<end[3] for e in other),
                           music_start=dict(zip(('cue16','order','row','tick','active'),start[25:30])),
                           music_end=dict(zip(('cue16','order','row','tick','active'),end[25:30]))))
    result=dict(scenes=scenes,total_publications=sum(s['publications'] for s in scenes),
                elapsed_seconds=seconds(boundaries[0][1],boundaries[-1][1]),
                vbl_intervals=len(vbl)-1,non_publication_copper_writes=len(other))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args()
    print(json.dumps(report(a.run),indent=2))

if __name__=='__main__':main()
