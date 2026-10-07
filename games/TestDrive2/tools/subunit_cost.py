#!/usr/bin/env python3
"""Measure the complete sub-unit patch's A500 self cycles in a fixed_window trace.
  subunit_cost.py CAPTURE [--limit 3]
Conservatively includes the displaced instructions and all nine hook calls and the walker branch.
Use a CPU=68000 trace. Slave 1.6b always enables BLTPRI with the sub-unit code;
do not use an A1200 trace with BLTPRI: its instruction records can be corrupt.
"""
import argparse,os
from pathlib import Path
import barto
from td2_report import regions

def measure(path,limit):
    os.environ['SLAVE']=str((path/'slave.slave').resolve())
    mem=(path/'code.bin').read_bytes();base=0xc00000
    rr={n:(lo,hi) for lo,hi,n,o in regions(mem,base)}
    lo,hi=rr['slave'];duel=rr['duel'][0]
    start=mem.find(bytes.fromhex('397c000ae24648e7fef0'),lo-base,hi-base)
    end_signature=bytes.fromhex('9440c5c4d4824842d0423429000c9441c5c4d4824842d2424e75')
    end=mem.find(end_signature,start,hi-base)
    assert start>=0 and end>=0,'normal sub-unit patch not found'
    start+=base;end+=base+len(end_signature)
    hooks={duel+offset for offset in (0x6c66,0x6daa,0x6474,0x7a34,0x7a78,0x801a,0x8052,0x73ec,0x8c90)}
    hooks|={duel+offset for offset in (0x73f2,0x8c96,0x8c98,0x8c9a,0x8c9c)}  # PL_S branch, PL_PSS NOPs
    trace=barto.load(path/'trace.bin')
    total=cost=calls=0
    for field in trace.fields:
        for pc,cycles,registers in trace.instructions(field):
            total+=cycles
            if pc==start:calls+=1
            if pc is not None and (start<=pc<end or pc in hooks):cost+=cycles
    assert abs(total-len(trace.fields)*142102)<=142102,"CPU trace does not represent the requested PAL fields"
    percent=100*cost/total
    print(path,f'{calls} main-view calls; {cost}/{total} cycles = {percent:.3f}% (limit {limit:.1f}%)')
    assert calls and percent<=limit,'sub-unit rendering exceeds the agreed A500 cost limit'
    return percent

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    p.add_argument('--limit',type=float,default=3)
    a=p.parse_args();measure(a.capture,a.limit)
