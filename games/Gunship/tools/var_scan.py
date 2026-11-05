#!/usr/bin/env python3
"""Per-field swap counts and game-memory snapshots after the route: var_scan.py OUT FIELDS

Traces one field at a time (counting entries to the swap routine +04496), then dumps the
gamemule hunks ($985CD8-$99A400 in the a500-fast/a1200-fast layout). Saves OUT/scan.npz with
swaps[FIELDS] and mem[FIELDS, bytes]: frame counters change with swaps, clocks with fields.
"""
import os,sys
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from gunship import Session
from route import run
from flight_profile import ROUTE
import _amigaxdev  # noqa: F401
from amigaxdev import barto
LO,HI,SWAP=0x985cd8,0x99a400,0x985cd8+0x4496
out,n=sys.argv[1],int(sys.argv[2]);s=Session(out)
try:
    run(s,ROUTE);sw=[];mem=[]
    for i in range(n):
        p=s.out/'f.bin';s.profile(1,p);t=barto.load(str(p))
        sw.append(sum(1 for f in t.fields for pc,c,r in t.instructions(f) if pc==SWAP));os.unlink(p)
        mem.append(np.frombuffer(s.read(LO,HI-LO),dtype=np.uint8))
    np.savez_compressed(s.out/'scan.npz',swaps=np.array(sw),mem=np.stack(mem),lo=LO)
    print('swaps',sum(sw),sw)
finally:s.quit()
