#!/usr/bin/env python3
"""Report a TD-only seed state map. Full physics/score state mapping belongs to phase 5."""
import argparse,json,collections
from pathlib import Path
# d16(a4), width. Evidence is in docs/internals.md; no TD2 variable offsets.
VARIABLES={'vbl':(-31782,4),'joystick_direction':(-31762,2),
           'mode_a818':(-22504,2),'selection_a81c':(-22500,2),
           'blitter_calls':(-31922,4),'blitter_busy_loops':(-31926,4),
           'sound_vbl':(-31548,4)}
A4_BIAS=0x7ffe
DATA_SIZE=0x32a4
VOLATILE={'vbl','sound_vbl','blitter_calls','blitter_busy_loops'}
def value(b,offset,size):
    i=A4_BIAS+offset
    if len(b)!=DATA_SIZE or not 0<=i<=len(b)-size:raise ValueError('invalid TD state size/offset')
    return int.from_bytes(b[i:i+size],'big')
def read(path):
    root=Path(path);m=json.loads((root/'metadata.json').read_text())
    if m.get('game')!='TD' or m.get('data_size')!=DATA_SIZE:raise ValueError('not a TD capture')
    files=sorted(root.glob('[0-9][0-9][0-9][0-9].bin'))
    if len(files)!=m['fields'] or [p.stem for p in files]!=[f'{i:04d}' for i in range(len(files))]:raise ValueError('missing/nonconsecutive samples')
    data=[p.read_bytes() for p in files]
    if not data or any(len(b)!=DATA_SIZE for b in data):raise ValueError('empty/truncated state capture')
    return m,data

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('path');p.add_argument('--changes',action='store_true');a=p.parse_args()
    m,data=read(a.path);print('sample,'+','.join(VARIABLES))
    for i,b in enumerate(data):print(str(i)+','+','.join(str(value(b,*v)) for v in VARIABLES.values()))
    if a.changes:
        for off in range(0,DATA_SIZE,2):
            changed=[i for i in range(1,len(data)) if data[i][off:off+2]!=data[i-1][off:off+2]]
            if changed:print(f'a4{off-A4_BIAS:+d}: changes at {changed[:40]}')
if __name__=='__main__':main()
