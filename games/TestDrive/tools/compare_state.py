#!/usr/bin/env python3
"""Compare TD snapshots at matching VBL entries; reject empty, partial or misaligned inputs."""
import argparse
from state_report import VARIABLES,value,read,VOLATILE

def compare(a,b,raw=False):
    ma,aa=read(a);mb,bb=read(b)
    for k in ('fields','anchor','skip_fields','game_sha256','machine'):
        if ma[k]!=mb[k]:raise ValueError(f'incomparable capture metadata: {k}')
    result={}
    for name,v in VARIABLES.items():
        xa=[value(x,*v) for x in aa];xb=[value(x,*v) for x in bb]
        if name in ('vbl','sound_vbl'):
            xa=[(x-xa[0])&0xffffffff for x in xa];xb=[(x-xb[0])&0xffffffff for x in xb]
        result[name]=[i for i,(x,y) in enumerate(zip(xa,xb)) if x!=y]
    if raw:result['raw_data']=[i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y]
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('a');p.add_argument('b');p.add_argument('--assert-match',action='store_true');p.add_argument('--raw',action='store_true');p.add_argument('--allow-different-window',action='store_true');a=p.parse_args()
    if a.allow_different_window:
        # Different-window diagnostic: compare values directly, without claiming equal VBL alignment.
        ma,aa=read(a.a);mb,bb=read(a.b)
        if len(aa)!=len(bb):p.error('capture lengths differ')
        result={name:[i for i,(x,y) in enumerate(zip(aa,bb)) if value(x,*v)!=value(y,*v)] for name,v in VARIABLES.items()}
        if a.raw:result['raw_data']=[i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y]
        print('DIAGNOSTIC: different windows, no determinism assertion')
    else:result=compare(a.a,a.b,a.raw)
    for name,bad in result.items():print(name,'MATCH' if not bad else 'DIFF',bad[:12])
    if a.assert_match and any(result.values()):raise SystemExit(1)
if __name__=='__main__':main()
