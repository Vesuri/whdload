#!/usr/bin/env python3
"""Per-instruction cycle annotation of the stunts code hunk for one capture.

  python3 tools/hotspots.py CAPTURE START END [MIN_PERCENT]
  python3 tools/hotspots.py CAPTURE --sum OFF OFF OFF ...

START/END/OFF are hex code-hunk offsets. Percentages are of all traced cycles.
Disassembly uses capstone and the installed data/stunts, not the live copy, so
slave patches are not shown. Jump-table targets (jsr -$xxxx(a4)) resolve with
--jt DISP ... from the capture's memory.bin.
"""
import argparse, collections, json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev  # noqa: F401
from amigaxdev import barto

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUNTS = os.path.join(ROOT, 'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts')
CODE = (0x28, 0x3a04c)


def histogram(cap):
    meta = json.load(open(os.path.join(cap, 'anchor.json')))
    base = meta['game_base']
    t = barto.load(os.path.join(cap, 'trace.bin'))
    cyc, cnt, total = collections.Counter(), collections.Counter(), 0
    for f in t.fields:
        for pc, cost, _ in t.instructions(f):
            total += cost
            if pc is None or pc == 0x7fffffff:
                continue
            o = pc - base
            if 0 <= o < CODE[1]:
                cyc[o] += cost
                cnt[o] += 1
    return meta, cyc, cnt, total


def main():
    p = argparse.ArgumentParser()
    p.add_argument('capture')
    p.add_argument('range', nargs='*')
    p.add_argument('--sum', action='store_true', help='sum cycles between consecutive offsets')
    p.add_argument('--jt', action='store_true', help='resolve a4 jump-table displacements')
    a = p.parse_args()
    if a.jt:
        meta = json.load(open(os.path.join(a.capture, 'anchor.json')))
        mem = open(os.path.join(a.capture, 'memory.bin'), 'rb').read()
        a4 = meta['data_base'] + 0x7ffe
        for d in a.range:
            w, t = struct.unpack_from('>HI', mem, a4 - int(d, 16) - meta.get('memory_base',0x200000))
            print(f'-${int(d, 16):x}(a4) -> ' + (f'stunts:{t - meta["game_base"]:05x}' if w == 0x4ef9 else f'not a jmp ({w:04x})'))
        return
    _, cyc, cnt, total = histogram(a.capture)
    pts = [int(x, 16) for x in a.range]
    if a.sum:
        for lo, hi in zip(pts, pts[1:]):
            s = sum(c for o, c in cyc.items() if lo <= o < hi)
            print(f'{lo:05x}-{hi:05x} {100 * s / total:6.2f}%')
        return
    import capstone
    code = open(STUNTS, 'rb').read()[CODE[0]:CODE[0] + CODE[1]]
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
    md.skipdata = True
    lo, hi = pts[0], pts[1]
    thr = float(a.range[2]) if len(a.range) > 2 else None
    s = 0
    for i in md.disasm(code[lo:hi], lo):
        c, n = cyc.get(i.address, 0), cnt.get(i.address, 0)
        s += c
        if (thr is None and n) or (thr is not None and 100 * c / total >= thr):
            print(f'{i.address:05x} {100 * c / total:6.3f}% n={n:<6} {i.mnemonic} {i.op_str}')
    print(f'range {lo:05x}-{hi:05x}: {100 * s / total:.2f}% of {total} cycles')


if __name__ == '__main__':
    main()
