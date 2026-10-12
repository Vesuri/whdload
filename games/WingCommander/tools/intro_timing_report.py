#!/usr/bin/env python3
"""Check the phase 5 motion/coupling ledger and report clock and music evidence."""
import argparse,collections,json,statistics
from pathlib import Path
from intro_capture import SCENES


def report(run):
    meta=json.loads((run/'result.json').read_text());h=meta['hunks'];s=meta['slave']
    if not meta['complete']:raise ValueError('incomplete capture')
    events=[]
    for line in (run/'events.txt').read_text().splitlines():
        if line.startswith('#'):continue
        p=line.split()
        if len(p)!=31:raise ValueError('truncated record')
        e=[int(v,16 if i==0 or 8<=i<24 else 10) for i,v in enumerate(p)]
        events.append(e)
        if e[0]==h[0]+0x20214:break
    expected=128 if meta['machine']=='a1200-fast' else 36
    if not events or events[-1][0]!=h[0]+0x20214:raise ValueError('missing menu')
    if any(e[5]!=312 or e[6]!=28375160 or e[7]!=expected for e in events):raise ValueError('clock mismatch')
    if any(b[3]<a[3] for a,b in zip(events,events[1:])):raise ValueError('nonmonotonic timestamps')
    first=lambda pc:next(e for e in events if e[0]==pc)
    cuts=[('reset',first(0xf800d2)),('game-startup',first(h[3]))]
    cuts += [(name,first(h[n]+pc)) for n,pc,name in SCENES]
    pages=[e for e in events if e[0]==h[0]+0x1fdd6]
    if [e[13]&65535 for e in pages]!=list(range(18)):raise ValueError('credits sequence differs')
    cuts += [(f'credits-{i:02d}',e) for i,e in enumerate(pages)]
    cuts += [('cycle-complete',first(h[0]+0x1fe48)),('menu',events[-1])]
    seconds=lambda a,b:(b[3]-a[3])/(512*3546895)
    publications=[];pending=None;copper=0
    for e in events:
        if e[0]==h[0]+0x3378e:
            if pending is not None:raise ValueError('nested publication')
            pending=e;copper=0
        elif e[0]==h[0]+0x33ce2 and pending is not None:copper+=1
        elif e[0]==h[0]+0x3379a:
            if pending is None or copper!=1:raise ValueError('publication ledger differs')
            publications.append(pending);pending=None
    if pending is not None:raise ValueError('incomplete publication')
    game=[e for e in events if e[0]==h[0]+0x34162]
    if any(b[1]-a[1]!=1 or (b[24]-a[24])&0xffffffff!=1 for a,b in zip(game,game[1:])):raise ValueError('game clock drift')
    music=[e for e in events if e[0]==h[0]+0x27810]
    if len(music)<100 or any(b[1]-a[1]!=1 for a,b in zip(music,music[1:])):raise ValueError('music callback drift')
    title=[e for e in events if e[0]==h[0]+0x1fd00 and e[3]<pages[0][3]]
    if [e[10]&65535 for e in title]!=list(range(296)):raise ValueError('title steps changed')
    limiter=[e for e in events if e[0]==s+0x17e6]
    # D1 holds the absolute CIA-A TOD sample; D0 the delta after the first call.
    tod_errors=[i for i,(a,b) in enumerate(zip(limiter,limiter[1:])) if ((b[9]-a[9])&0xffffff)!=b[1]-a[1]]
    if len(limiter)<100 or tod_errors or any(e[8]<2 for e in limiter[1:]):
        raise ValueError('CIA-A limiter cadence/threshold differs')
    def pairs(begin,end):
        spans=[];a=None
        for e in events:
            if e[0]==s+begin:
                if a is not None:raise ValueError('nested timing span')
                a=e
            elif e[0]==s+end:
                if a is None:raise ValueError('unmatched timing span')
                spans.append(seconds(a,e));a=None
        if a is not None:raise ValueError('unfinished timing span')
        return dict(count=len(spans),min= min(spans),median=statistics.median(spans),max=max(spans)) if spans else None
    if sum(a[0]==h[0]+0x3378e and title[0][3]<=a[3]<first(h[0]+0x1fd96)[3] for a in events)!=148:
        raise ValueError('title publication count differs')
    scenes=[]
    for (name,a),(next_name,b) in zip(cuts,cuts[1:]):
        frames=[e for e in publications if a[3]<=e[3]<b[3]]
        scenes.append(dict(scene=name,seconds=seconds(a,b),fields=b[1]-a[1],publications=len(frames),music_start=a[25:30],music_end=b[25:30]))
    return dict(scenes=scenes,game_vbl_intervals=len(game)-1,music_vbl_intervals=len(music)-1,
                title_updates=len(title),title_publications=sum(x['publications'] for x in scenes if x['scene'].startswith('title-') and x['scene']!='title-load'),
                limiter_calls=len(limiter),tod_field_disagreements=len(tod_errors),limiter_deltas=dict(collections.Counter(e[8] for e in limiter[1:])),
                beam_delay=pairs(0x1774,0x1784),render_delay=pairs(0x178e,0x1792),
                live_cpu=meta['live_cpu'],complete=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);a=p.parse_args()
    print(json.dumps(report(a.run),indent=2))

if __name__=='__main__':main()
