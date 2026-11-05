#!/usr/bin/env python3
"""D2 matched tick-state and bounded A500 cadence gate, including negative controls."""
import argparse, json
from pathlib import Path
from ocs_baseline_report import parse, distribution
from ocs_reconstruct import new_output, require

# OCS native world arrays, mission/target state, score/time and gameplay RNG.
# OD:9cca..9cd9 are eight old/current cockpit annunciator bytes (O:1aea,
# 1b0e,1b5c); their drawing/flash history is not authoritative world state.
RANGES=((0x8928,0x9cca),(0x9cda,0xbbd0),(0x6f9a,0x6f9e),
        (0x88da,0x88de),(0x8906,0x8910),(0xaf4,0xb00),(0x3860,0x389c),
        (0xaa,0xae))


def equal(a,b):
    for lo,hi in RANGES:
        require(a[lo:hi]==b[lo:hi],f'world/event mismatch OD:{lo:x}..{hi:x}')


def report(fast,slow,build):
    b=json.loads((build/'build.json').read_text());sy=b['symbols']
    metas=[json.loads((r/'result.json').read_text()) for r in (fast,slow)]
    for key in ('slave_sha256','fsuae_sha256','effective','hunks','slave','a4'):
        require(metas[0][key]==metas[1][key],'unmatched run '+key)
    require(metas[0]['slave_sha256']==b['sha256'] and b['clock'],'wrong clock candidate')
    samples=[json.loads((r/'clock-samples.json').read_text()) for r in (fast,slow)]
    require([x['draw_every'] for x in samples]==[1,5],'render-rate control absent')
    comparisons=[]
    draw_counts=[]
    for root in (fast,slow):
        raw=(root/'tick31-clock.bin').read_bytes();offset=sy['ocs_clock_drawn']-sy['ocs_clock_state']
        draw_counts.append(int.from_bytes(raw[offset:offset+4],'big'))
    require(draw_counts[0]>=2*draw_counts[1]>0,'render-rate contrast not reached')
    # Tick 2 precedes the slow arm's first HUD draw; compare world state after
    # both have produced their first picture, not uninitialized HUD scratch.
    for tick in (11,21,31):
        a,c=[(r/f'tick{tick}-data.bin').read_bytes() for r in (fast,slow)]
        equal(a,c);comparisons.append(tick)
    bad=bytearray(a);bad[0x8928]^=1
    try:equal(bad,c)
    except ValueError:pass
    else:raise ValueError('position corruption survived')
    measures=[]
    for root,meta in zip((fast,slow),metas):
        rows=parse(root/'fire-events.txt');begin=next(x for x in rows if x[0]=='B');end=next(x for x in rows if x[0]=='E')
        fields=[r for r in rows if r[0]=='F'];require(len(fields)==100,'use bounded active-flight window')
        clocks=[r[1] for r in fields];deltas=[b-a for a,b in zip([begin[1]]+clocks[:-1],clocks)]
        require(set(deltas)<={227*312*512,227*313*512} and begin[2:5]==[28375160,512,256],'uncalibrated PAL instrument')
        hz=begin[2]/8*begin[3];seconds=(end[1]-begin[1])/hz
        ticks=[r[1] for r in rows if r[0]=='P' and r[2]==0x2dc]
        require(len(ticks)==((fields[-1][3]-begin[5])&65535),'native tick counter disagreement')
        # Require the bounded window to end inside the new flight loop, not
        # the native post-flight deadline/landing sequence.
        mem=(root/'fire-fast.bin').read_bytes();base=meta['slave']-0x200000
        def value(name,size=4):return int.from_bytes(mem[base+sy[name]:base+sy[name]+size],'big')
        if root==slow and value('ocs_clock_active',2)!=1:
            measures.append(dict(excluded='sparse draw schedule reached native flight exit during the later firing window'))
            continue
        require(value('ocs_clock_active',2)==1,'measurement crossed native modal/flight exit')
        require(19<=len(ticks)<=21,'normal-load cadence outside one-tick boundary tolerance')
        dma=[r for r in rows if r[0]=='D'];flips=sum(a[3]!=b[3] for a,b in zip(dma,dma[1:]))
        scopes=[(r[1]-r[3])/hz*1000 for r in rows if r[0]=='R' and r[2]==0x2be]
        measures.append(dict(seconds=seconds,ticks=len(ticks),world_hz=len(ticks)/seconds,
            world_intervals_ms=distribution([(y-x)/hz*1000 for x,y in zip(ticks,ticks[1:])]),
            native_world_ms=distribution(scopes),display_changes=flips,displayed_hz=flips/seconds,
            maximum_observed_backlog_fields=value('ocs_clock_backlog_max'),
            bounded_batch_limit_hits=value('ocs_clock_overload_batches'),
            completed=value('ocs_clock_completed'),drawn=value('ocs_clock_drawn')))
    return dict(passed=True,equal_ticks=comparisons,draws_at_tick31=draw_counts,ranges=[list(x) for x in RANGES],
                rejected=['changed authoritative position'],measurements=measures,
                scope='English simulator, PAL A500/4 MiB Fast; no hardware or whole-campaign claim')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('normal',type=Path);p.add_argument('slow',type=Path)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=report(a.normal,a.slow,a.build);out=new_output(a.output);out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
