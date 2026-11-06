#!/usr/bin/env python3
"""Check the VERIFY CUSTOM5=5 fatal event enters the original terminal path.
Run without the trainer; read only captured game state.
"""
import argparse
from pathlib import Path
from state_report import VARIABLES, value
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('state',type=Path)
a=p.parse_args()
b=[f.read_bytes() for f in sorted(a.state.glob('[0-9][0-9][0-9][0-9].bin'))]
def v(i,n):return value(b[i],*VARIABLES[n])
assert len(b)>=1200,'capture at least 1200 fields'
fatal=next(i for i in range(len(b)) if v(i,'crash')==17)
assert 900<=fatal<=903,f'wrong fatal-event field: {fatal}'
assert any(v(i,'lives')==0 for i in range(fatal,len(b))),'fatal event did not exhaust lives'
assert max(v(i,'crash_count') for i in range(fatal,len(b)))==v(fatal-1,'crash_count')+1,'fatal event not counted once'
assert all(v(i,'clock')==v(fatal+3,'clock') for i in range(fatal+3,len(b))),'race clock advances after terminal step'
assert v(len(b)-1,'vbl')>v(fatal,'vbl'),'VBL stopped during terminal presentation'
print(f'Fatal crash at field {fatal}: lives exhausted, race clock frozen, VBL continues')
