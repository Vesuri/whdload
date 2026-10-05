#!/usr/bin/env python3
"""Completed-call renderer costs for W2 A/B; partial boundary calls are excluded."""
import argparse, os, statistics
from pathlib import Path
import barto
from lov_report import regions
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--base', type=lambda x: int(x,0), default=0xc00000)
a = p.parse_args(); os.environ['SLAVE'] = str(a.capture/'slave.slave')
b = (a.capture/'code.bin').read_bytes(); t = barto.load(str(a.capture/'trace.bin'))
r = {n:(lo,hi) for lo,hi,n,o in regions(b,a.base,t.chip)}
h = r['h12'][0]
entries = {h+0x27bc:'render', h+0x4c1a:'wall columns', h+0x4cbe:'wall columns',
           h+0x4d42:'wall columns', h+0x51a2:'sky/floor clear'}
blob = b[h-a.base:r['h12'][1]-a.base]
returns = {h+i for i in range(0,len(blob)-1,2) if blob[i:i+2]==b'\x4e\x75'}
active = {}; calls = {name:[] for name in set(entries.values())}
for field in t.fields:
    for pc,cost,regs in t.instructions(field):
        if pc in entries:
            name = entries[pc]
            assert name not in active, f'nested {name}'
            active[name] = [regs[15],0,0]
        for sample in active.values():
            sample[1] += cost
            if abs(regs[15]-sample[0]) < 0x10000: sample[2] += cost
        if pc in returns:
            for name in list(active):
                if regs[15]==active[name][0]:
                    calls[name].append(active.pop(name)[1:])
for name in ('render','wall columns','sky/floor clear'):
    samples = calls[name]
    if not samples:
        print(f'{name}: no completed calls'); continue
    inc,main = zip(*samples)
    print(f'{name}: {len(samples)} complete calls; inclusive {statistics.mean(inc):.0f}, main-task {statistics.mean(main):.0f} cycles/call')
