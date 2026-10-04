#!/usr/bin/env python3
"""Check three-field PAL pacing and race-clock elapsed time from VBL state samples.
Cross-CPU state equality is checked separately by compare_state.py. This checks
against video-field time, not against a second implementation of the physics.
Terminal/menu phases are reported separately from the continuous driving prefix.
"""
import argparse
from pathlib import Path
from state_report import VARIABLES, value
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('state',type=Path)
p.add_argument('--min-fields',type=int,default=1000)
p.add_argument('--fatal-end',action='store_true',help='without trainer: stop active checks at fatal crash 17')
a=p.parse_args()
data=[f.read_bytes() for f in sorted(a.state.glob('[0-9][0-9][0-9][0-9].bin'))]
assert len(data)>=a.min_fields, 'insufficient field samples'
clock=[value(b,*VARIABLES['clock']) for b in data]
vbl=[value(b,*VARIABLES['vbl']) for b in data]
deadline=[value(b,*VARIABLES['deadline']) for b in data]
active=next((i for i,b in enumerate(data) if value(b,-7670,2)),None)
assert active is not None, 'race never started moving'
last=len(data)
if a.fatal_end:
    last=next((i for i,b in enumerate(data) if value(b,*VARIABLES['crash'])==17),last)
for i in range(1,last):
    assert (vbl[i]-vbl[i-1])&0xffffffff==1, f'non-consecutive VBL at {i}'
    lag=(vbl[i]-deadline[i])&0xffffffff
    advance=(deadline[i]-deadline[i-1])&0xffffffff
    if lag>2 or advance not in (0,3):
        last=i
        break
assert last>=a.min_fields, f'continuous pacing ends at field {last}'
changes=[i for i in range(1,last) if deadline[i]!=deadline[i-1]]
assert all(b-a==3 for a,b in zip(changes,changes[1:])), 'deadline interval is not three fields'
penalty=0
errors=[]
for i in range(active,last):
    change=clock[i]-clock[i-1] if i else 0
    if change>=200:
        penalty+=200*(change//200)
    ticks=1+(i-active)//3
    # PAL: 50 fields/second; the dashboard unit is 1/10 second.
    expected=clock[active]+(ticks*3)//5+penalty
    if clock[i]!=expected:errors.append((i,clock[i],expected))
assert not errors, f'elapsed-clock mismatch: {errors[:8]}'
print(f'{last} consecutive fields: deadline lag 0..2; three-field pacing holds')
print(f'Clock follows PAL elapsed time from field {active}, plus {penalty} penalty units')
if last<len(data):print(f'Race-end/menu phase begins at field {last}; not claimed as active simulation')
