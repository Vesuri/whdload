#!/usr/bin/env python3
"""End-to-end intro FPS and fixed-update cadence from the slave's recorder."""
import argparse,json,struct
from collections import Counter
from pathlib import Path
from frame_report import records,display_records
from cd32_runtime import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if (ROOT/'tmp').resolve() not in a.output.resolve().parents or a.output.exists():raise ValueError('new tmp output required')
    results=[]
    for run in a.runs:
        meta=json.loads((run/'result.json').read_text());assert meta['complete']
        for name in ('title','credits'):
            hz,lines,events=records(run/name/'framestats.bin');line_s=records.line_ms/1000
            displays=display_records(run/name/'displaystats.bin')
            seconds=(displays[-1][0]-displays[0][0])*lines*line_s
            ticks=[t for e,f,t in events if e==3]
            rate=(len(ticks)-1)/((ticks[-1]-ticks[0])*line_s)
            assert 9.9<=rate<=10.1,(run,name,rate)
            result=dict(machine=meta['machine'],section=name,pictures=len(displays),fps=(len(displays)-1)/seconds,
                fields_per_picture=dict(sorted(Counter(b[0]-a[0] for a,b in zip(displays,displays[1:])).items())),world_updates_per_second=rate)
            results.append(result)
        # The unskipped title always dispatches 296 native world updates.
        layout=meta['layout'];data=layout['hunks'][1]-0x200000
        start=(run/'title-start-fast.bin').read_bytes();credit=(run/'credits-start-fast.bin').read_bytes()
        word=lambda b,o:struct.unpack_from('>H',b,data+o)[0]
        assert (word(credit,0x914c)-word(start,0x914c))%65536==296
        # The first credit page retains the native 320-field deadline.
        end=(run/'credits-end-fast.bin').read_bytes();clock=lambda b:struct.unpack_from('>I',b,data+0x7f02)[0]
        elapsed=clock(end)-clock(credit)
        assert 320<=elapsed<=324,elapsed
        print(meta['machine'], '296 title ticks; credit page',elapsed,'fields')
    a.output.write_text(json.dumps(dict(passed=True,runs=results,scope='slave VBL/beam recorder on named models; 040 not hardware-calibrated'),indent=2)+'\n')
    for r in results:print(r['machine'],r['section'],round(r['fps'],2),'FPS;',round(r['world_updates_per_second'],3),'updates/s;',r['fields_per_picture'])

if __name__=='__main__':main()
