#!/usr/bin/env python3
"""Disjoint PC-cost analysis of the continuous Practice launch capture.
Usage: python3 tools/analyze_practice.py CAPTURE_DIRECTORY > CAPTURE_DIRECTORY/analysis.json
Ranges are game-hunk offsets, half open. Counts are executed entry PCs, not inferred calls.
Uses the capture's retained slave and initial memory for region/opcode identification.
"""
import collections
import json
import os
from pathlib import Path
import sys
import barto
from powerdrome_report import Memory, regions

RANGES = [
    (0x15b68, 0x15da8, 'multiword span writes'),
    (0x15da8, 0x15e68, 'singleword span writes'),
    (0x15ee8, 0x15fd4, 'polygon edge setup and stepping'),
    (0x15fd4, 0x1609c, 'polygon span setup and iteration'),
    (0x1609c, 0x163e2, 'polygon clipping'),
    (0x1578a, 0x15836, 'CPU background fill'),
    (0x10df2, 0x10f1e, 'camera transform and setup'),
    (0x10f1e, 0x10fc6, 'near-plane clipping'),
    (0x10fc6, 0x1108e, 'perspective projection and setup'),
    (0x1108e, 0x1118c, 'visibility and backface checks'),
    (0x1118c, 0x117dc, 'renderer dispatch and other inline work'),
    (0x79b4, 0x7a0e, 'bitmap unpack'),
]
WATCH = {0x14764:'pit animation iteration', 0x10df2:'renderer entry',
         0x117da:'renderer return', 0xca3e:'main loop entry', 0x8056:'display update entry',
         0x1580c:'zero plane fill entry', 0x15810:'one plane fill entry',
         0x1582c:'40-byte background store', 0x1602a:'polygon scanline',
         0x15ee8:'rasterizer entry', 0x1609c:'clipper entry', 0x5684:'VBL callback'}
MARKERS = {0x147a6: 'transition', 0x1020e:'cockpit departure', 0xca3e:'track'}
DMA = {0:'free',1:'refresh',2:'CPU',3:'copper',4:'audio',5:'blitter',6:'bitplane',7:'sprite',8:'disk'}

def main():
    root = Path(sys.argv[1])
    os.environ['SLAVE'] = str(root / 'slave.slave')
    trace = barto.load(root / 'trace.bin')
    dump = (root / 'code.bin').read_bytes()
    base = int((root / 'dump-base.txt').read_text().strip(), 0)
    reg = regions(dump, base, trace.chip)
    game = next(o for _, _, n, o in reg if n == 'game')
    slave = next(o for _, _, n, o in reg if n == 'slave')
    mem = Memory(trace, dump, base)
    expected_wait = bytes.fromhex('4a3900dff0020839000600dff002660000044e75')
    if mem.read(slave + 0x34a, len(expected_wait)) != expected_wait:
        raise ValueError('WaitBlit layout differs; verify its range before analysis')
    cache = {}
    def classify(pc):
        if pc in cache:
            return cache[pc]
        label, addr = 'unmapped', 'unmapped'
        for lo, hi, name, origin in reg:
            if pc is not None and lo <= pc < hi:
                label, addr = name + ' other', f'{name}:{pc-origin:05x}'
                break
        off = pc-game if pc is not None else -1
        for lo, hi, name in RANGES:
            if lo <= off < hi:
                label = name
                break
        if off in (0x112a6, 0x112aa): label = 'VBL handshake wait'
        if pc is not None and slave+0x34a <= pc < slave+0x37e: label = 'KickEmu WaitBlit'
        if pc is None or (pc != 0x7fffffff and mem.word(pc) == 0x4e72): label = 'STOP records'
        if pc == 0x7fffffff: label, addr = 'interrupt entry', 'interrupt entry'
        cache[pc] = label, addr
        return label, addr
    phase = 'pit'
    seen = set()
    phases = collections.defaultdict(lambda: {'cycles':collections.Counter(), 'counts':collections.Counter(), 'instructions':0, 'pcs':collections.Counter()})
    starts = [{'phase':phase, 'field':0, 'recorded_cycles_before':0}]
    total = 0
    pcs = collections.Counter()
    fields = []
    events = collections.defaultdict(list)
    for f in trace.fields:
        fc, fs = collections.Counter(), collections.Counter()
        field_phases = set()
        for pc, cost, r in trace.instructions(f):
            off = pc-game if pc is not None else -1
            if off in MARKERS and off not in seen:
                seen.add(off)
                phase = MARKERS[off]
                starts.append({'phase':phase,'field':f.index,'recorded_cycles_before':total})
            p = phases[phase]
            label, addr = classify(pc)
            p['cycles'][label] += cost
            p['pcs'][addr] += cost
            p['instructions'] += 1
            fc[label] += cost
            pcs[addr] += cost
            field_phases.add(phase)
            if off in WATCH:
                p['counts'][WATCH[off]] += 1
                if off in (0x10df2,0x117da,0xca3e,0x8056):
                    events[WATCH[off]].append([f.index,total,phase])
            total += cost
        for typ in f.dma[29::f.dma_size]: fs[DMA.get(typ,str(typ))] += 1
        fields.append({'field':f.index,'phases':sorted(field_phases),'cycles':fc,'dma':fs})
    assert total == sum(sum(p['cycles'].values()) for p in phases.values())
    if [s['phase'] for s in starts] != ['pit', 'transition', 'cockpit departure', 'track']:
        raise ValueError('Expected one complete Practice departure sequence')
    print(json.dumps({'fields':len(fields),'cycles':total,'phase_starts':starts,
                      'phases':phases,'hot_pcs':pcs.most_common(40),'events':events,'per_field':fields},indent=2))

if __name__ == '__main__':
    main()
