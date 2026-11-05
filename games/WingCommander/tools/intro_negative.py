#!/usr/bin/env python3
"""Prove the intro gate rejects missing events, wrong fields, pixels and game bytes."""
import argparse, json, shutil
from pathlib import Path
from intro_check import compare, run_events, validate_trace
from cd32_runtime import ROOT, BASE
from PIL import Image


def rejected(action, expected):
    try:
        action()
    except ValueError as error:
        if expected not in str(error): raise
        return str(error)
    raise AssertionError('damaged evidence passed')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();run=a.run.resolve();out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new output below tmp/ required')
    meta=json.loads((run/'result.json').read_text());events=run_events(run,meta);h0=meta['hunks'][0]
    trace=run/'origin-animation.bin';valid=validate_trace(trace,events,h0)
    field=valid['field_base'];end=field+valid['fields']
    index=next(i for i,e in enumerate(events) if e[0]==h0+0x3378e and field<=e[1]<end)
    missing=events[:index]+events[index+1:]
    shifted=[e[:] for e in events];shifted[index][1]+=1
    result={'missing_event':rejected(lambda:validate_trace(trace,missing,h0),'disagreement'),
            'wrong_field':rejected(lambda:validate_trace(trace,shifted,h0),'disagreement')}
    # The first checkpoint must reject before trying later unchanged snapshots.
    name=meta['milestones'][0];out.mkdir(parents=True)
    for kind in ('pixel','game-byte'):
        fixture=out/kind;fixture.mkdir()
        for file in ('result.json','events.txt',name+'.png',name+'-fast.bin'):
            shutil.copyfile(run/file,fixture/file)
        if kind=='pixel':
            path=fixture/(name+'.png');im=Image.open(path).convert('RGB')
            r,g,b=im.getpixel((0,0));im.putpixel((0,0),(r^1,g,b));im.save(path)
            expected='picture differs'
        else:
            path=fixture/(name+'-fast.bin');data=bytearray(path.read_bytes())
            data[h0-BASE]^=1;path.write_bytes(data);expected='game state differs'
        result[kind]=rejected(lambda:compare(run,fixture),expected)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
