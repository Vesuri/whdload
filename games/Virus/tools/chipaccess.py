#!/usr/bin/env python3
"""What the CPU's chip-bus slots go to, in a short sample of the demo.

    python3 tools/chipaccess.py [SKIP [FIELDS]]

Needs a server just booted with tools/boot.sh (a CPU that records a trace). Runs to the
demo's start, lets SKIP fields pass (default 300), traces FIELDS (default 10) and classifies
every CPU slot of the trace's DMA records (58-byte records: size at byte 0, bit 0 of
byte 1 set for a write, the address at byte 12, the slot type at byte 29) by target region,
and the reads in chip as instruction fetches (bytes of an executed instruction) or data.
Also tallies the slot types while the blitter clears. The trace is deleted afterwards.
"""
import collections
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
import capstone  # noqa: E402
from amigaxdev import barto  # noqa: E402
from game_server import game_server  # noqa: E402

TYPES = {0: 'free', 1: 'refresh', 2: 'CPU', 3: 'copper', 4: 'audio', 5: 'blitter', 6: 'bitplane'}


def region(a):
    if a >= 0xdff000:
        return 'custom registers'
    if 0xbf0000 <= a < 0xc00000:
        return 'CIA'
    if 0x70000 <= a < 0x80000:
        return 'display buffers $70000-$7ffff'
    if a >= 0x80000:
        return 'above $80000'
    if 0x57000 <= a < 0x68800:
        return 'Disk.1 code area $57000-$687ff'
    if 0x3b800 <= a < 0x57000:
        return 'Disk.1 data $3b800-$56fff'
    return 'work memory $0-$3b7ff'


def main(args):
    skip = int(args[0]) if args else 300
    n = int(args[1]) if len(args) > 1 else 10
    srv = game_server('virus')
    trace = ROOT / 'tmp/prof/chipaccess.bin'
    trace.parent.mkdir(parents=True, exist_ok=True)
    srv.request('until 0x641fe')
    srv.request(f'fields {skip}')
    srv.request(f'profile {n} {trace}')
    t = barto.load(str(trace))
    trace.unlink()
    d, u = t.data, struct.unpack_from
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
    words, seen = set(), set()
    for f in t.fields:
        off, end = f.insn_off, f.insn_end
        while off < end:
            pc = None
            while True:
                v = u('<I', d, off)[0]
                off += 4
                if v >= 0xffff0000:
                    break
                if pc is None:
                    pc = v
            off += 68
            if pc is not None and pc < 0x80000 and pc not in seen:
                seen.add(pc)
                i = next(md.disasm(bytes(t.chip[pc:pc + 10]), pc), None)
                words.update(range(pc, pc + (i.size if i else 2), 2))
    reg, kind, word, clear = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    cpu = 0
    for f in t.fields:
        b, s = bytes(f.dma), f.dma_size
        ty = [b[i + 29] for i in range(0, len(b), s)]
        bl = [k for k, x in enumerate(ty) if x == 5]
        if bl:
            clear.update(ty[bl[0]:bl[-1] + 1])
        for i in range(0, len(b), s):
            if b[i + 29] != 2:
                continue
            cpu += 1
            a = u('<I', b, i + 12)[0]
            w = b[i + 1] & 1
            reg[(region(a), 'write' if w else 'read')] += 1
            word[a] += 1
            if not w and a < 0x80000:
                kind['instruction fetch' if (a & ~1) in words or (a & ~1) + 2 in words else 'data'] += 1
    print(f'{n} fields from demo field {skip}: {cpu} CPU slots')
    for (r, w), c in reg.most_common():
        print(f'  {r:34} {w:5} {100 * c / cpu:6.2f}%')
    tk = sum(kind.values())
    print('  chip reads: ' + ', '.join(f'{k} {100 * c / tk:.1f}%' for k, c in kind.most_common()))
    a, c = word.most_common(1)[0]
    print(f'  most read word: ${a:05x}, {100 * c / cpu:.1f}% of the CPU slots')
    tc = sum(clear.values()) or 1
    print('  slots while the blitter clears: ' + ', '.join(f'{TYPES.get(k, k)} {100 * c / tc:.1f}%' for k, c in clear.most_common()))


if __name__ == '__main__':
    main(sys.argv[1:])
