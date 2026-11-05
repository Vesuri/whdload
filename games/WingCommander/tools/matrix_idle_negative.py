#!/usr/bin/env python3
"""Require rejection of damaged STOP ledgers derived from a completed valid capture."""
import argparse
import json
from pathlib import Path
from cd32_runtime import ROOT
from matrix_idle_check import check


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();run=(ROOT/a.run).resolve();out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    check(run)
    original=(run/'idle-events.txt').read_text().splitlines()
    transition=next(i for i,s in enumerate(original) if s.startswith('T '))
    boundary=next(i for i,s in enumerate(original) if s.startswith('B 2 '))
    cases={}
    lines=original.copy();lines.insert(transition+1,lines[transition]);cases['duplicate-transition']=lines
    lines=original.copy();del lines[boundary];cases['missing-boundary']=lines
    lines=original.copy();parts=lines[boundary].split();parts[4]=str(1<<63);lines[boundary]=' '.join(parts);cases['overcounted-wait']=lines
    if len(original[boundary].split())==8:
        lines=original.copy();parts=lines[boundary].split();parts[6]=str(int(parts[6])+1);lines[boundary]=' '.join(parts);cases['wrong-stop-count']=lines
    out.mkdir();results=[]
    for name,lines in cases.items():
        fixture=out/name;fixture.mkdir()
        for filename in ('result.json','matrix-events.txt','fast.bin'):
            (fixture/filename).symlink_to(run/filename)
        (fixture/'idle-events.txt').write_text('\n'.join(lines)+'\n')
        try:check(fixture)
        except ValueError as error:results.append(dict(case=name,rejected=True,reason=str(error)))
        else:raise ValueError('damaged idle ledger was accepted: '+name)
    (out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
