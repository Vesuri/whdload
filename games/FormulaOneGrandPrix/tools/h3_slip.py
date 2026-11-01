#!/usr/bin/env python3
"""H3: the player's slip limit at h0+$369C2 in the game's own physics, run in unicorn.

  python3 -m venv tmp/h3/venv; tmp/h3/venv/bin/pip install unicorn
  tmp/h3/venv/bin/python tools/h3_slip.py A3_CAPTURE [--slave tmp/build/F1GP.Slave] [--out tmp/h3/slip.json]

A3_CAPTURE is an A3 state capture of the green window (tools/state_diff.py live, e.g.
tmp/a3/green): whole-memory snapshots around each call of the live loop. Its per-car update
h0+$2AC14 is run in a 68030 emulator from the snapshot before frame 47's call, where the
player's car coasts after the start collision (speed 1606, no input):
- the harness: frames 17, 30, 47 and 48 each give the next snapshot exactly;
- a step changes the step words, then rebuilds what the game derives from them at setup
  (h0+$34932's constants, h0+$2C5BC's AI tables, each car's h0+$347D4); at the stock step
  that reproduces the snapshot apart from the physics' per-call scratch;
- per step and mass (+$44, written before each tick), 6 s of game time natively and with
  the slave's h3_slip (its bytes taken from --slave) at h0+$369C2: the largest slip (heading
  +$0 against body +$1A) and the final speed; a coast-down rate after 3 s settled;
- the fixed and native runs must be identical wherever the native quotient fits.
"""
import argparse
import gzip
import json
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
from unicorn.m68k_const import UC_CPU_M68K_M68030, UC_M68K_REG_A0, UC_M68K_REG_A7, UC_M68K_REG_PC

SIZES = (0x44a54, 0x2a940, 0x41c70, 0x14f84)
RETURN, STACK, ROUTINE = 0xFFF000, 0xF00000, 0xFFE000
H3_SLIP = bytes.fromhex('2f08206f000480e83edc')      # the routine's first instructions
FRAME = 47                                           # coasting after the start collision


class Game:
    def __init__(self, capture, serial, routine=None):
        meta = json.loads((capture/'meta.json').read_text())
        self.B = meta['hunk_bases']
        raw = gzip.open(capture/f'{serial:05d}.bin.gz').read()
        self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.uc.ctl_set_cpu_model(UC_CPU_M68K_M68030)
        self.uc.mem_map(0, 0x1000000)
        o = 0
        for base, size in zip(self.B, SIZES):
            self.uc.mem_write(base, raw[o:o+size])
            o += size
        self.uc.mem_write(RETURN, b'\x4e\x71'*4)
        if routine:
            self.uc.mem_write(ROUTINE, routine)
            self.uc.mem_write(self.a(0, 0x369c2), b'\x4e\xb9' + struct.pack('>I', ROUTINE))
        self.player = self.r(0, 0x3a720, '>I') - self.B[1]

    def a(self, h, off):
        return self.B[h] + off

    def r(self, h, off, fmt='>h'):
        return struct.unpack(fmt, self.uc.mem_read(self.a(h, off), struct.calcsize(fmt)))[0]

    def w(self, h, off, value, fmt='>h'):
        self.uc.mem_write(self.a(h, off), struct.pack(fmt, value))

    def hunks(self):
        return [bytes(self.uc.mem_read(b, n)) for b, n in zip(self.B, SIZES)]

    def call(self, h, off, a0=None):
        if a0 is not None:
            self.uc.reg_write(UC_M68K_REG_A0, a0)
        self.uc.mem_write(STACK, struct.pack('>I', RETURN))
        self.uc.reg_write(UC_M68K_REG_A7, STACK)
        self.uc.emu_start(self.a(h, off), RETURN, count=50_000_000)
        if self.uc.reg_read(UC_M68K_REG_PC) != RETURN:
            raise RuntimeError(f'h{h}+{off:#x} did not return')

    def set_step(self, step):
        for off, value in ((0x34362, step//2), (0x34364, step), (0x34366, step), (0x34368, step)):
            self.w(0, off, value, '>H')
        self.call(0, 0x34932)
        # h0+$2C5BC borrows car 0, clears the player pointer, draws from the gameplay
        # RNG (h0+$3A7B0-$3A7B4) and sets the flag h2+$231EA: put them back
        keep = [(h, off, bytes(self.uc.mem_read(self.a(h, off), n)))
                for h, off, n in ((1, 0, SIZES[1]), (0, 0x3a720, 4), (0, 0x3a7b0, 5), (2, 0x231ea, 1))]
        self.call(0, 0x2c5bc)
        for h, off, data in keep:
            self.uc.mem_write(self.a(h, off), data)
        for n in range(26):
            self.call(0, 0x347d4, self.a(1, 0x5d6 + n*0xc0))

    def slip(self):
        p = self.player
        return (self.r(1, p) - self.r(1, p+0x1a) + 0x8000) % 0x10000 - 0x8000


def serial(frame):
    """The snapshot before frame's call of h0+$2AC14 (32 a frame, that call's is the 15th)."""
    return 14 + 32*frame


def harness(capture):
    for frame in (17, 30, 47, 48):
        g = Game(capture, serial(frame))
        g.call(0, 0x2ac14)
        after = gzip.open(capture/f'{serial(frame)+1:05d}.bin.gz').read()
        if b''.join(g.hunks()) != after:
            raise ValueError(f'frame {frame}: the emulated update differs from the game')
    g = Game(capture, serial(FRAME))
    before = g.hunks()
    g.set_step(8192)
    scratch = lambda h0: h0[:0x25644] + h0[0x25646:0x3a82e] + h0[0x3a8f8:]   # per-call scratch
    after = g.hunks()
    if scratch(after[0]) != scratch(before[0]) or after[1:] != before[1:]:
        raise ValueError('rebuilding at the stock step changed the state')


def roll(capture, step, mass, routine, seconds=6):
    g = Game(capture, serial(FRAME), routine)
    if step != 8192:
        g.set_step(step)
    worst, states = 0, []
    for _ in range(round(seconds*65536/step)):
        g.w(1, g.player+0x44, mass)
        g.call(0, 0x2ac14)
        worst = max(worst, abs(g.slip()))
        states.append(g.hunks()[1])
    return dict(speed=g.r(1, g.player+0x10), worst_slip=worst, spin=worst >= 0x1000), states


def coast(capture, step, routine):
    g = Game(capture, serial(FRAME), routine)
    for _ in range(24):
        g.call(0, 0x2ac14)
    if step != 8192:
        g.set_step(step)
    start, ticks = g.r(1, g.player+0x10), round(2*65536/step)
    for _ in range(ticks):
        g.call(0, 0x2ac14)
    return (start - g.r(1, g.player+0x10)) / (ticks*step/65536)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--slave', default='tmp/build/F1GP.Slave')
    parser.add_argument('--out')
    args = parser.parse_args()
    capture = Path(args.capture)
    slave = Path(args.slave).read_bytes()
    at = slave.find(H3_SLIP)
    if at < 0 or slave.find(H3_SLIP, at+1) >= 0:
        raise ValueError('h3_slip not found once in the slave')
    routine = slave[at:slave.index(b'\x4e\x75', at)+2]
    harness(capture)
    print('harness: four updates exact, stock rebuild exact')
    result = dict(rows=[], coast={})
    cases = ((8192, (1272, 1650, 4095, 4096)), (6750, (1650,)), (3375, (1650, 1686, 1687)),
             (3276, (1272, 1612, 1637, 1638, 1650)), (2700, (1272, 1349, 1350, 1612, 1650)))
    for step, masses in cases:
        for mass in masses:
            native, a = roll(capture, step, mass, None)
            fixed, b = roll(capture, step, mass, routine)
            fits = mass < step//2       # the native quotient fits a signed word
            if fits and a != b:
                raise ValueError(f'step {step} mass {mass}: the fix changed a native-safe run')
            row = dict(step=step, mass=mass, native=native, fixed=fixed, identical=a == b)
            result['rows'].append(row)
            print(f'step {step} mass {mass}: native slip {native["worst_slip"]}'
                  f'{" SPIN" if native["spin"] else ""}, fixed slip {fixed["worst_slip"]}'
                  f'{" SPIN" if fixed["spin"] else ""}{", identical" if a == b else ""}', flush=True)
    for step in (8192, 6750, 3276, 2700):
        result['coast'][step] = coast(capture, step, routine)
    print('coast-down a second:', ' '.join(f'{k} {v:.1f}' for k, v in result['coast'].items()))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
