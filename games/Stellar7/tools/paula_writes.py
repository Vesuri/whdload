#!/usr/bin/env python3
"""List and compare CPU writes to Paula audio registers in Barto traces.

  python3 tools/paula_writes.py list CAPTURE [--out writes.json]
  python3 tools/paula_writes.py compare BASELINE CANDIDATE [--out result.json]

Writes come from the trace's DMA records (CPU word writes): DMACON ($dff096) writes
that touch an audio DMA bit (0-3), INTENA/INTREQ ($dff09a/$dff09c) writes that touch
an audio interrupt bit (7-10), and every word of $dff0a0-$dff0df. Each has its field
and beam slot (vpos*227+hpos, colour clocks). A long write appears as two word writes.

compare passes only with an identical (register, value) sequence; it then reports
the largest timing shift between matched writes, in colour clocks across fields.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto

SLOTS = 227


def audio(register, value):
    if 0xa0 <= register < 0xe0:
        return True
    if register == 0x96:
        return bool(value & 0x000f)
    if register in (0x9a, 0x9c):
        return bool(value & 0x0780)
    return False


def writes(capture):
    trace = barto.load(Path(capture)/'trace.bin')
    rows = []
    lines = None
    for field in trace.fields:
        assert field.dma_size == 58, 'unknown DMA record layout'
        count = len(field.dma)//58
        lines = lines or count//SLOTS
        assert count == lines*SLOTS, 'unexpected DMA slot grid'
        for slot in range(count):
            off = slot*58
            if struct.unpack_from('<h', field.dma, off+29)[0] != 2:
                continue
            kind, value = struct.unpack_from('<HQ', field.dma, off)
            if kind != 0x1102:  # CPU word write
                continue
            address = struct.unpack_from('<I', field.dma, off+12)[0]
            if not 0xdff000 <= address < 0xdff200:
                continue
            register, value = address & 0x1fe, value & 0xffff
            if audio(register, value):
                rows.append(dict(field=field.index, vpos=slot//SLOTS, hpos=slot % SLOTS,
                                 register=f'${register:03x}', value=f'${value:04x}'))
    return dict(capture=str(capture), fields=len(trace.fields), lines=lines, writes=rows)


def compare(a, b):
    x, y = writes(a), writes(b)
    key = lambda w: (w['register'], w['value'])
    sx, sy = [key(w) for w in x['writes']], [key(w) for w in y['writes']]
    result = dict(baseline=a, candidate=b, baseline_writes=len(sx), candidate_writes=len(sy),
                  identical=sx == sy)
    if sx == sy:
        clock = lambda r, w: (w['field']*r['lines']+w['vpos'])*SLOTS+w['hpos']
        shifts = [clock(y, wy)-clock(x, wx) for wx, wy in zip(x['writes'], y['writes'])]
        result['largest_shift_clocks'] = max(map(abs, shifts), default=0)
    else:
        first = next((i for i, (p, q) in enumerate(zip(sx, sy)) if p != q), min(len(sx), len(sy)))
        result['first_difference'] = dict(index=first,
                                          baseline=x['writes'][first] if first < len(sx) else None,
                                          candidate=y['writes'][first] if first < len(sy) else None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('list')
    p.add_argument('capture')
    p.add_argument('--out')
    p = sub.add_parser('compare')
    p.add_argument('baseline')
    p.add_argument('candidate')
    p.add_argument('--out')
    args = parser.parse_args()
    result = writes(args.capture) if args.command == 'list' else compare(args.baseline, args.candidate)
    text = json.dumps(result, indent=1)
    if args.out:
        Path(args.out).write_text(text+'\n')
    if args.command == 'list':
        print(f"{len(result['writes'])} audio writes in {result['fields']} fields")
    else:
        print(json.dumps({k: v for k, v in result.items() if k != 'writes'}, indent=1))
        sys.exit(0 if result['identical'] else 1)


if __name__ == '__main__':
    main()
