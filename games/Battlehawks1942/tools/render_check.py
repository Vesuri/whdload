#!/usr/bin/env python3
"""Check the Enhanced framerate's rendering routines (src/render.s) against BH's own code.

  python3 tools/render_check.py [--cpu 68000|68020|68030] [--n N] [SLAVE [LISTING]]

Runs the original routine and the slave's replacement in Unicorn (BH's hunks relocated, as
timing_check.py) from the same random inputs and compares everything they leave behind:
- xform: bh:16bca, the point transform, cull and screen position (render.s's xform on the
  68000, xform20 on the 68020 and 68030; Unicorn's 68040 model lacks the 64-bit mulu.l that
  the real 68040 has).  Inputs: the point (stack), the camera
  460..468(a4), the matrix magnitudes 420..434 and signs 436..450, the projection words
  452..458, the flags 582 and 5830, the view words -6062, -6058, -6052, -142 and the shade
  tables 5552.., 5809..  Compared: all registers, the data hunk except the original's
  scratch 536..566, 578 and 580 (written before they are read, render.s), the stack.
- fill: bh:160ba and bh:15ea2..15ece, a row of the sky and sea fill (render.s's fill_row
  and fill_a0): the row area and the registers.
- overlay: bh:161ec, the run-length image (render.s's overlay): the buffer, the registers.
Points are drawn around the camera at scales from 2^4 to 2^22 so that every exit is taken;
the counts per exit are printed.  A case where the original faults is skipped (bh:16f6e's
divide by zero, or its branch to bh:16f5e with its return address still on the stack).
No emulator services, timing or interrupts are modelled.  Run from the game directory.
"""
import argparse, collections, random, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import timing_check as tc  # noqa: E402

REGS = list(range(1, 17))          # Unicorn m68k A0..A7 = 1..8, D0..D7 = 9..16
SCRATCH = set(range(536, 567)) | {578, 579, 580, 581}
MODELS = {'68000': 1, '68020': 2, '68030': 3}  # Unicorn's 68040 has no 64-bit mulu.l


def apply(b, code, start):
    """Apply a patch list as WHDLoad does (P, PS, S; NEXT continues with another list)."""
    for adr, cmd, arg in tc.decode(code, start):
        if cmd == 'END':
            return
        if cmd == 'NEXT':
            return apply(b, code, int(arg.split(':')[1], 16))
        if cmd in ('P', 'PS'):
            dest = tc.SLAVE + int(arg.split(':')[1], 16)
            b.c.write(tc.CODE + adr, (b'\x4e\xf9' if cmd == 'P' else b'\x4e\xb9')
                      + struct.pack('>I', dest))
        elif cmd == 'S':
            b.c.write(tc.CODE + adr, struct.pack('>HH', 0x6000, int(arg, 16) - 2))
        else:
            raise SystemExit(f'render_check: PL_{cmd} not handled')


def bh(model, slave, listing, plist):
    b = tc.BH(model, slave, listing, False)
    apply(b, tc.slave_code(slave), b.syms[plist])
    b.c.write(tc.SLAVE + b.syms['xf_16f6e'], struct.pack('>I', tc.CODE + 0x16f6e))
    b.c.flush()
    return b


def setup(b, r):
    w = lambda o, v: b.c.write(b.a4 + o, struct.pack('>H', v & 0xffff))
    l = lambda o, v: b.c.write(b.a4 + o, struct.pack('>I', v & 0xffffffff))
    for o, v in r['words'].items():
        w(o, v)
    for o, v in r['longs'].items():
        l(o, v)
    b.c.write(b.a4 + 5552, r['t1'])
    b.c.write(b.a4 + 5808, r['t2'])
    b.c.write(tc.STACK + 4, struct.pack('>3I', *[v & 0xffffffff for v in r['point']]))
    for i, reg in enumerate(REGS):
        if reg != 8:
            b.c.reg(reg, r['regs'][i])


def inputs(rng):
    cam = [rng.randrange(-1 << 22, 1 << 22) for _ in range(3)]
    scale = 1 << rng.randrange(4, 23)
    point = [c + rng.randrange(-scale, scale) for c in cam]
    words = {o: rng.randrange(0x10000) for o in range(420, 436, 2)}
    words.update({o: rng.choice((0, 0x8000)) for o in range(436, 452, 2)})
    words.update({452: rng.randrange(0x10000), 454: rng.randrange(0x10000),
                  456: rng.choice((0, 0x8000)), 458: rng.choice((0, 0x8000)),
                  582: rng.choice((0, 0, 0, 1)), 5830: rng.choice((0, 1)),
                  -6062: rng.choice((96, 160, 256, rng.randrange(1, 400))),
                  -6058: rng.choice((96, 160, rng.randrange(1, 400))),
                  -6052: rng.choice((96, 128, rng.randrange(1, 300))),
                  -142: rng.randrange(0x10000), 576: rng.randrange(0x10000)})
    longs = {o: rng.randrange(1 << 32) for o in (568, 572)}
    words[570] = rng.randrange(0x10000)
    longs.update({460: cam[0], 464: cam[1], 468: cam[2]})
    return {'point': point, 'words': words, 'longs': longs,
            't1': bytes(rng.randrange(256) for _ in range(258)),
            't2': bytes(rng.randrange(256) for _ in range(258)),
            'regs': [rng.randrange(1 << 32) for _ in REGS]}


def state(b):
    regs = [b.c.reg(r) for r in REGS]
    data = bytearray(b.c.read(tc.DATA, tc.DATA_ALLOC))
    for o in SCRATCH:
        data[b.a4 - tc.DATA + o] = 0
    return regs, bytes(data), b.c.read(tc.STACK, 16)


def exit_kind(b):
    s = struct.unpack('>h', b.c.read(b.a4 + 576, 2))[0]
    return 'culled' if s == -1 else 'shaded'


ROW = 0x300000                     # a scratch chunky area (outside BH's hunks)


def fill(orig, fixed, rng, n):
    """bh:160ba (a row, then the next row) and bh:15ea2..15ece (the same row in bh:15cb6),
    from random split x (up to 300 pixels: runs past 32 longs take the original loop),
    longs per row 32 or random, fill longs and table: the row area, the registers."""
    bad = 0
    for i in range(n):
        d2 = rng.choice((rng.randrange(256), rng.randrange(320)))
        d6 = rng.choice((32, 32, rng.randrange(1, 48)))
        regs = [rng.randrange(1 << 32) for _ in REGS]
        regs[9 - 1 + 2] = (regs[10] & 0xffff0000) | d2      # D2
        regs[9 - 1 + 6] = (regs[14] & 0xffff0000) | d6      # D6
        table = bytes(rng.randrange(256) for _ in range(32))
        flag, step = rng.choice((0, 1)), rng.choice((40, 128, 256))
        for name, start, end in (('row', 0x160ba, 0x160f2), ('loop', 0x15ea2, 0x15ece)):
            res = []
            for b in (orig, fixed):
                b.c.write(ROW, bytes(0x1000))
                b.c.write(0x310000, table)
                b.c.write(0x320000, struct.pack('>HH', d2, d2 + 3))  # (A0) for the loop
                b.set(-5962, flag)
                b.set(-6056, step)
                for k, reg in enumerate(REGS):
                    if reg != 8:
                        b.c.reg(reg, regs[k])
                b.c.reg(1, 0x320000)                          # A0
                b.c.reg(2, ROW + 0x400)                       # A1
                b.c.reg(4, 0x310000)                          # A3
                # the row returns (a bsr from bh:160a0); the loop body runs to bh:15ece
                b.run(start, tc.STOP - tc.CODE if name == 'row' else end)
                res.append(([b.c.reg(r) for r in REGS], b.c.read(ROW, 0x1000)))
            if res[0] != res[1]:
                bad += 1
                if bad <= 5:
                    print(f'FAIL fill {name}: d2 {d2} d6 {d6}')
                    for k, (x, y) in enumerate(zip(res[0][0], res[1][0])):
                        if x != y:
                            print(f'  reg {k}: {x:#x} != {y:#x}')
                    if res[0][1] != res[1][1]:
                        print('  row area differs')
    print(f'# fill: {2 * n} rows, {bad} differ')
    return bad


IMG, BUF = 0x330000, 0x340000


def overlay(orig, fixed, rng, n):
    """bh:161ec from random images (colour runs of 1..256 pixels with colour bytes 0..$fc,
    skips, row changes), x positions, row tables and buffer contents: the buffer, the
    registers and the stack's arguments."""
    bad = 0
    for i in range(n):
        img, rows = bytearray(), rng.randrange(1, 12)
        for r in range(rows):
            for _ in range(rng.randrange(0, 12)):
                if rng.random() < 0.2:
                    img += bytes((0xfd, rng.randrange(256 if rng.random() < 0.1 else 20)))
                else:
                    img += bytes((rng.randrange(0xfd), rng.randrange(256 if rng.random() < 0.1
                                                                       else 24)))
            img.append(0xfe if r < rows - 1 else 0xff)
        x, row = rng.randrange(0, 300), rng.randrange(0, 8)
        table = [rng.randrange(0, 0x6000) for _ in range(row + rows + 1)]
        mem = bytes(rng.randrange(256) for _ in range(0x7000))
        res = []
        for b in (orig, fixed):
            b.c.write(IMG, bytes(img))
            b.c.write(BUF, mem)
            b.c.write(b.a4 - 6066, struct.pack('>I', BUF))
            b.c.write(b.a4 - 4642, struct.pack(f'>{len(table)}H', *table))
            b.c.write(tc.STACK + 4, struct.pack('>IHHH', IMG, rng.randrange(1 << 16) & 0, x, row))
            for k, reg in enumerate(REGS):
                if reg != 8:
                    b.c.reg(reg, 0x1000 * k + 0x100)
            b.run(0x161ec, tc.STOP - tc.CODE)
            res.append(([b.c.reg(r) for r in REGS], b.c.read(BUF, 0x7000),
                        b.c.read(tc.STACK, 16), b.c.read(b.a4 + 6626, 4)))
        if res[0] != res[1]:
            bad += 1
            if bad <= 5:
                print(f'FAIL overlay case {i}: x {x} row {row}, {len(img)} bytes')
                for k, (u_, v) in enumerate(zip(res[0][0], res[1][0])):
                    if u_ != v:
                        print(f'  reg {k}: {u_:#x} != {v:#x}')
                d = [k for k in range(0x7000) if res[0][1][k] != res[1][1][k]]
                if d:
                    print(f'  buffer: {len(d)} bytes differ, first at {d[0]:#x}')
    print(f'# overlay: {n} images, {bad} differ')
    return bad


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cpu', default='68000', choices=MODELS)
    p.add_argument('--n', type=int, default=20000)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('slave', nargs='?', default='tmp/build/release/Battlehawks1942.Slave')
    p.add_argument('listing', nargs='?')
    a = p.parse_args()
    listing = a.listing or str(Path(a.slave).with_suffix('.lst'))
    model = MODELS[a.cpu]
    orig = tc.BH(model, a.slave, listing, False)
    fixed = bh(model, a.slave, listing, '_pl_render' if a.cpu == '68000' else '_pl_render20')
    base_o, base_f = orig.c.read(tc.DATA, tc.DATA_ALLOC), fixed.c.read(tc.DATA, tc.DATA_ALLOC)
    rng = random.Random(a.seed)
    kinds, bad, skipped = collections.Counter(), 0, 0
    for i in range(a.n):
        r = inputs(rng)
        res = []
        for b, base in ((orig, base_o), (fixed, base_f)):
            b.c.write(tc.DATA, base)
            setup(b, r)
            try:
                b.run(0x16bca, tc.STOP - tc.CODE)
            except RuntimeError as e:
                res.append(('fault', str(e)))
                continue
            res.append(state(b))
        if res[0][0] == 'fault':
            skipped += 1
            continue
        kinds[exit_kind(orig)] += 1
        if res[0] != res[1]:
            bad += 1
            if bad <= 5:
                print(f'FAIL case {i}: point {r["point"]} 582 {r["words"][582]}')
                if res[1][0] == 'fault':
                    print('  replacement faulted:', res[1][1])
                else:
                    ro, rf = res
                    for k, (x, y) in enumerate(zip(ro[0], rf[0])):
                        if x != y:
                            print(f'  reg {k}: {x:#x} != {y:#x}')
                    for k, (x, y) in enumerate(zip(ro[1], rf[1])):
                        if x != y:
                            print(f'  data {k - (orig.a4 - tc.DATA)}(a4): {x:#x} != {y:#x}')
                    if ro[2] != rf[2]:
                        print('  stack differs')
    print(f'# xform {a.cpu}: {a.n - skipped} cases ({dict(kinds)}), {skipped} skipped '
          f'(the original faults), {bad} differ')
    bad += fill(orig, fixed, rng, a.n // 10)
    bad += overlay(orig, fixed, rng, a.n // 10)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
