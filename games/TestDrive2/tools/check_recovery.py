#!/usr/bin/env python3
"""Check actual life loss, penalty and field-timed recovery from VBL captures.
Use --trainer for CUSTOM1=1; --damage requires a recorded engine-damage recovery.
No target writes. Terminal events are outside the recovery invariants.
"""
import argparse
from pathlib import Path
from state_report import VARIABLES, value
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('state',type=Path)
p.add_argument('--trainer',action='store_true')
p.add_argument('--damage',action='store_true')
a=p.parse_args()
b=[f.read_bytes() for f in sorted(a.state.glob('[0-9][0-9][0-9][0-9].bin'))]
def v(i,n):return value(b[i],*VARIABLES[n])
events=[i for i in range(1,len(b)) if v(i,'penalties')-v(i-1,'penalties')==200]
assert events,'no recovery events captured'
complete=0
for i in events:
    assert v(i,'lives')==v(i-1,'lives')-(0 if a.trainer else 1),f'life loss at {i}'
    assert v(i,'crash_count')+v(i,'damage_count')==v(i-1,'crash_count')+v(i-1,'damage_count')+1,f'event counted more than once at {i}'
    if i+240>=len(b):continue
    assert all(v(j,'speed')==0 for j in range(i,i+240)),f'moving during recovery at {i}'
    assert all(v(j,'distance')==v(i,'distance') for j in range(i,i+240)),f'position changes during recovery at {i}'
    assert v(i+240,'crash')==0,f'recovery not finished in 240 fields at {i}'
    assert v(i+240,'engine_damage')==0,f'damage not cleared at {i}'
    assert all(v(j,'engine_period')==1800 for j in range(i,i+240)),f'engine not idle at {i}'
    complete+=1
assert complete,'no complete 240-field recovery captured'
if a.damage:assert v(len(b)-1,'damage_count')>0,'engine damage not exercised'
print(f'{len(events)} penalties/life losses; {complete} complete 240-field recoveries verified')
