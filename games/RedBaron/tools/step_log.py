#!/usr/bin/env python3
"""Read the VERIFY observer ring, or run to a requested flight step before reading it."""
import argparse,json,re,struct
from pathlib import Path
import route_status as r
ROOT=Path(__file__).resolve().parents[1]
def header():
    r.locate();b=(ROOT/'tmp/build/route-ram.bin').read_bytes()
    base=r.DUMP_BASE
    matches=[];start=0
    while (i:=b.find(b'RBSTEPS1',start))>=0:
        v=struct.unpack_from('>8I',b,i+8)
        if v[0]==1 and v[1]==44 and base<=v[4]<base+len(b):matches.append((base+i,v))
        start=i+8
    if len(matches)!=1:raise RuntimeError(f'Expected one live observer: {matches}')
    return matches[0]
def collect():
    at,h=header();version,stride,capacity,count,buf,h3,sim,vbl=h
    r.command(f'gdb dump binary memory tmp/build/steps.bin {buf:#x} {buf+capacity*stride:#x}')
    b=(ROOT/'tmp/build/steps.bin').read_bytes();rows=[]
    names=['step','ticks','beam','display','elapsed','dt','secondary_dt','F','time_scale','view_dirty','message_dirty','top_dirty','world_frames','message_timer','reserved','vbl']
    for seq in range(max(0,count-capacity),count):
        v=struct.unpack_from('>4I8HI2HI',b,(seq%capacity)*stride)
        rows.append(dict(zip(names,v)))
    return dict(version=version,stride=stride,capacity=capacity,count=count,h3=h3,sim=sim,vbl=vbl,header=at,records=rows)
def advance(step):
    at=r.locate();state=r.read(at);remaining=step-state['game_steps']
    if remaining<=0:raise ValueError(f'Current step {state["game_steps"]}; target must be later')
    return r.command(f'gdb break *{state["game_anchor"]:#x}\nignore $bpnum {remaining-1}\ncontinue\ndelete')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--step',type=int);p.add_argument('--out');a=p.parse_args()
    if a.step:advance(a.step)
    result=collect();s=json.dumps(result,indent=2)+'\n'
    if a.out:Path(a.out).write_text(s)
    print(s,end='')
