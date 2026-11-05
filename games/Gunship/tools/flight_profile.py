#!/usr/bin/env python3
"""Profile the first take-off: flight_profile.py OUT

Route (warp, DETERMINISTIC, JOY0=none, mouse injected): Return in the intro helicopter, click
T-74 on the vehicle identification, Continue on pilot, ops order, checklist and arming
screens, wait for the cockpit, press 1, 2, 3. Then trace 500 fields (10 s PAL): F1 ten times
(held 4 fields, 6 apart) and 400 fields more. Keys go in between trace chunks, so the chunks
(OUT/chunk_NNN.bin) are consecutive with no untraced cycles. OUT/profile.pkl.gz is the
amigaxdev.callprofile reduction of all of them.
"""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from gunship import Session
from route import run
import _amigaxdev  # noqa: F401
ROUTE=('f:2000 t:ret f:1000 m:30:226 f:4 c f:300 c f:300 m:540:0 f:4 c f:300 '
       'm:-90:-14 f:4 c f:300 m:488:16 f:4 c f:800 t:n1 f:50 t:n2 f:50 t:n3 f:50').split()

def window(s,chunk):
    """The traced part: F1 ten times, then 400 fields; chunk(fields) traces consecutively."""
    for i in range(10):
        s.key('f1',1);chunk(4);s.key('f1',0);chunk(6)
    for i in range(4):chunk(100)

def main(out):
    from amigaxdev.callprofile import Reduction
    s=Session(out);red=Reduction();n=[0]
    def chunk(fields):
        p=s.out/f'chunk_{n[0]:03d}.bin';s.profile(fields,p);red.feed(str(p));n[0]+=1
    try:
        run(s,ROUTE);start=s.field
        print('trace starts at field',start,flush=True)
        window(s,chunk)
        print('traced fields',start,'-',s.field,flush=True)
        red.save(str(s.out/'profile.pkl.gz'))
        s.shot('end.png')
    finally:s.quit()

if __name__=='__main__':main(sys.argv[1])
