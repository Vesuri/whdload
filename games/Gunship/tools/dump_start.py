#!/usr/bin/env python3
"""Replay flight_profile's route to the trace start and dump memory: dump_start.py OUT [CHECK]

Writes OUT/fast.bin ($200000-$A00000), OUT/chip.bin, OUT/regs.txt. With CHECK (a flight_profile
directory), also traces the first chunk (F1 down, 4 fields) for a determinism comparison.
"""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from gunship import Session
from route import run
from flight_profile import ROUTE
out=sys.argv[1];s=Session(out)
try:
    run(s,ROUTE)
    s.cmd('maintenance flush register-cache')
    (s.out/'regs.txt').write_text(s.regs('d0 d1 d2 d3 d4 d5 d6 d7 a0 a1 a2 a3 a4 a5 a6 sp pc'))
    (s.out/'fast.bin').write_bytes(s.read(0x200000,0x800000))
    (s.out/'chip.bin').write_bytes(s.read(0,0x80000))
    if len(sys.argv)>2:
        s.key('f1',1);s.profile(4,s.out/'chunk_000.bin')
finally:s.quit()
