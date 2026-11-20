#!/usr/bin/env python3
"""Executed game PCs from traced runs, merged into tmp/re/coverage.pkl for tools/relocmap.py.

    python3 tools/coverage.py STEP...

Needs a server just booted with tools/boot.sh on a core that records a trace. Steps, run in
order (every field is traced unless the step says otherwise):

    trace N            trace N fields (25-field chunks)
    until ADDR         run to ADDR, untraced (hex)
    key HEX 1|0        press or release a raw key, then trace a field
    mouse DX DY        move the mouse, then trace a field
    button NAME 1|0    JOY1_FIRE_BUTTON (left), JOY1_2ND_BUTTON (right), then trace a field
    shot FILE          a screenshot
    wander N           trace N fields, moving the mouse and pressing the buttons by a fixed
                       pseudo-random pattern every 5 fields
    dive N DY          trace N fields with both buttons held (RMB thrust, LMB fire), the
                       mouse moved by DY every 5 fields (negative: up, the quickest way to
                       lose a life)
    thrust N DY        the same with RMB alone: no shots, which cost a point each

NOTRACE=1 runs the same steps untraced (driving a build, not collecting). The set keeps,
for each PC, the step that first reached it; `python3 tools/coverage.py`
alone prints the count by step.
"""
import os
import pickle
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
from game_server import game_server  # noqa: E402
from amigaxdev import barto  # noqa: E402

BASE, END = 0x3b800, 0x3b800 + 184320
OUT = ROOT / 'tmp/re/coverage.pkl'
CHUNK = 25


def load():
    return pickle.load(open(OUT, 'rb')) if OUT.exists() else {}


def pcs(path):
    t = barto.load(path)
    d, u, seen = t.data, struct.unpack_from, set()
    for f in t.fields:
        off, end = f.insn_off, f.insn_end
        while off < end:
            pc = u('<I', d, off)[0]
            off += 4
            while u('<I', d, off)[0] < 0xffff0000:
                off += 4
            off += 4 + 68
            if BASE <= pc < END:
                seen.add(pc)
    return seen


def main(args):
    cov = load()
    if not args:
        by = {}
        for tag in cov.values():
            by[tag] = by.get(tag, 0) + 1
        print(f'{len(cov)} PCs')
        for tag, n in by.items():
            print(f'  {n:6d}  {tag}')
        return
    srv = game_server('virus')
    chunk = ROOT / 'tmp/re/cov.bin'
    rng = random.Random(1)

    def trace(n, tag):
        if os.environ.get('NOTRACE'):
            srv.request(f'fields {n}')
            return
        while n > 0:
            k = min(n, CHUNK)
            reply = srv.request(f'profile {k} {chunk}')
            if not chunk.exists():
                sys.exit(f'profile failed: {reply}')
            new = 0
            for pc in pcs(chunk):
                if pc not in cov:
                    cov[pc] = tag
                    new += 1
            chunk.unlink()
            n -= k
            print(f'{tag}: +{new} ({len(cov)})', flush=True)
        pickle.dump(cov, open(OUT, 'wb'))

    i = 0
    while i < len(args):
        cmd = args[i]
        if cmd == 'trace':
            trace(int(args[i + 1]), ' '.join(args[i:i + 2]))
            i += 2
        elif cmd == 'until':
            print(srv.request(f'until 0x{args[i + 1]}').strip().splitlines()[-1])
            i += 2
        elif cmd == 'key':
            srv.request(f'gdb monitor key {args[i + 1]} {args[i + 2]}')
            trace(1, f'key {args[i + 1]}')
            i += 3
        elif cmd == 'mouse':
            srv.request(f'gdb monitor mouse {args[i + 1]} {args[i + 2]}')
            trace(1, 'mouse')
            i += 3
        elif cmd == 'button':
            srv.request(f'gdb monitor input {args[i + 1]} {args[i + 2]}')
            trace(1, f'button {args[i + 1]}')
            i += 3
        elif cmd == 'shot':
            srv.request(f'shot {args[i + 1]}')
            i += 2
        elif cmd == 'wander':
            n, tag = int(args[i + 1]), 'wander'
            while n > 0:
                srv.request(f'gdb monitor mouse {rng.randint(-40, 40)} {rng.randint(-30, 30)}')
                srv.request(f'gdb monitor input JOY1_FIRE_BUTTON {rng.random() < 0.6:d}')
                srv.request(f'gdb monitor input JOY1_2ND_BUTTON {rng.random() < 0.5:d}')
                trace(min(5, n), tag)
                n -= 5
            i += 2
        elif cmd in ('dive', 'thrust'):
            n, dy = int(args[i + 1]), int(args[i + 2])
            srv.request(f'gdb monitor input JOY1_FIRE_BUTTON {int(cmd == "dive")}')
            srv.request('gdb monitor input JOY1_2ND_BUTTON 1')
            while n > 0:
                if dy:
                    srv.request(f'gdb monitor mouse 0 {dy}')
                trace(min(5, n), cmd)
                n -= 5
            srv.request('gdb monitor input JOY1_FIRE_BUTTON 0')
            srv.request('gdb monitor input JOY1_2ND_BUTTON 0')
            i += 3
        else:
            sys.exit(f'unknown step {cmd}')


if __name__ == '__main__':
    main(sys.argv[1:])
