#!/usr/bin/env python3
"""Instruction/gap and DMA-slot census for a Barto validation slice."""
import argparse,collections,json,struct
from pathlib import Path
import _amigaxdev
from amigaxdev import barto


def report(path):
    t=barto.load(str(path));slots=collections.Counter();costs=collections.Counter();counts=collections.Counter()
    for f in t.fields:
        if f.dma_size!=58:raise ValueError('unvalidated DMA record layout')
        if len(f.dma)!=227*313*58:raise ValueError('unexpected PAL DMA field')
        for i in range(0,len(f.dma),58):
            kind=struct.unpack_from('<h',f.dma,i+29)[0]
            if not 0<=kind<=9:raise ValueError('invalid DMA type')
            slots[kind]+=1
        for pc,cost,regs in t.instructions(f):
            kind='STOP/no-PC' if pc is None else 'between-instructions' if pc==0x7fffffff else 'instructions'
            costs[kind]+=cost;counts[kind]+=1
    if not counts['instructions']:raise ValueError('no instruction coverage; timing unavailable')
    names=['unclaimed','refresh','CPU','copper','audio','blitter','bitplanes','sprites','disk','conflict']
    return dict(fields=len(t.fields),cost_units=dict(costs),record_counts=dict(counts),
                dma_slots={names[i]:slots[i] for i in range(10)},
                dma_fractions={names[i]:slots[i]/sum(slots.values()) for i in range(10)})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);a=p.parse_args()
    print(json.dumps(report(a.trace),indent=2))

if __name__=='__main__':main()
