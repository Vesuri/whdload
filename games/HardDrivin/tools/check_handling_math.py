"""Check the VERIFY_HANDLING_MATH boot fixture (plan step G4).

check_handling_math.py NEW-RUN [--slave S] [--profile P]
check_handling_math.py --unicorn SLAVE LISTING

The fixture in HardDrivinHandling.s runs 64 sequences of 250 steps through
_handling_step at boot, with xorshift32 inputs, and publishes per sequence a
checksum of the whole model state after every step plus its final v, r and
heading, after the signature HDHANDM1. The state includes the step's forward
speed output; the step uses the game's force rule (fx_total=False). This
script generates the same inputs, runs them through
tools/arcade/handling_fx.py and compares.

The default mode boots the slave in the FS-UAE harness (CUSTOM1=2, A500)
and reads the results from memory at the title screen; NEW-RUN is a new
directory below tmp/prof. --unicorn runs the fixture's code from the slave
image in Unicorn instead, a quick check of this script's mirror.
"""
import argparse
import os
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'tools/arcade'))
import handling_fx as hf                     # noqa: E402

RUNS, FIELDS, SEED = 64, 250, 0x2545f491
SIG = b'HDHANDM1'
M32 = 0xffffffff


def xorshift(x):
    x ^= (x << 13) & M32
    x ^= x >> 17
    x ^= (x << 5) & M32
    return x


def s32(x):
    return (x + 2 ** 31) % 2 ** 32 - 2 ** 31


def expected():
    out, x = [], SEED
    for run in range(RUNS):
        car = hf.FxCar()
        x = xorshift(x)
        v8, m, fx, br, c = (x >> 8) & 4095, 0, 0, 0, 3
        check = 0

        def mix(value):
            nonlocal check
            check = (((check << 5) | (check >> 27)) + value) & M32

        for _ in range(FIELDS):
            x = xorshift(x)
            if x & 31 == 0:
                m = ((x >> 5) & 1023) % 641 - 320
            if (x >> 15) & 31 == 0:
                br = -((x >> 20) & 4095)
            if (x >> 10) & 31 == 1:
                fx = ((x >> 16) + 32768) % 65536 - 32768
            if x & 1023 == 1023:
                c = (x >> 12) & 3
            v8 = max(-200, min(4160, v8 + ((x >> 26) & 63) - 32))
            uq = (v8 * hf.K_U) >> 13
            f = car.step(uq, m, fx, br, c, fx_total=False)
            for value in (car.v, car.r, car.dn, car.psi):
                mix(value & M32)
            for a in (car.front, car.rear):
                mix(a.y & M32)
                mix((a.w if a.w is not None else 0) & M32)
                mix((1 if a.w is not None else 0) + (2 if a.peak else 0))
            mix(((f + 32768) % 65536 - 32768) & M32)
            mix(car.du & M32)
        out.append((check, s32(car.v), s32(car.r), s32(car.psi)))
    return out


def parse(block):
    return [(r[0], r[1], r[2], r[3]) for r in struct.iter_unpack('>Iiii', block[:RUNS * 16])]


def from_unicorn(slave, listing):
    import check_handling_step as cs
    off = cs.label_offsets(listing, ['_handling_math_test', '_handling_math_signature'])
    emu = cs.Emu(cs.code_hunk(slave), off['_handling_math_test'])
    try:
        emu.write(emu.STACK, struct.pack('>I', emu.END))
        emu.reg(cs.REG_A7, emu.STACK)
        cs.ok(cs.u.uc_emu_start(emu.h, emu.step_addr, emu.END, 0, 0))
        b = emu.read(emu.BASE + off['_handling_math_signature'], 8 + RUNS * 16)
    finally:
        emu.close()
    assert b[:8] == SIG
    return parse(b[8:])


def from_emulator(name, slave, profile):
    from capture_demo import ROOT
    from capture_session import Session
    os.chdir(ROOT)
    out = ROOT / 'tmp/prof' / name
    out.mkdir(exist_ok=False)
    shutil.copyfile(slave, out / 'slave.slave')
    s = Session(out, profile, out / 'slave.slave', 0x8520)
    s.env['WHD_ARGS'] += ' CUSTOM1=2'
    try:
        s.boot()
        found = []
        for base, b in s.dump_banks('handling'):
            i = b.find(SIG)
            if i >= 0:
                found.append(b[i + 8:i + 8 + RUNS * 16])
    finally:
        s.close()
    assert len(found) == 1, 'signature found %d times' % len(found)
    return parse(found[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name', nargs='?')
    ap.add_argument('--slave', default=str(HERE.parent / 'tmp/build/g-handling-math.slave'))
    ap.add_argument('--profile', default='a500')
    ap.add_argument('--unicorn', nargs=2, metavar=('SLAVE', 'LISTING'))
    a = ap.parse_args()
    want = expected()
    if a.unicorn:
        got = from_unicorn(*a.unicorn)
        where = 'Unicorn'
    else:
        assert a.name, 'NEW-RUN name required'
        got = from_emulator(a.name, os.path.abspath(a.slave), a.profile)
        where = 'FS-UAE %s' % a.profile
    bad = [i for i in range(RUNS) if got[i] != want[i]]
    for i in bad[:5]:
        print('sequence %d: 68000 %s, twin %s' % (i, got[i], want[i]))
    if bad:
        print('%s: %d of %d sequences differ' % (where, len(bad), RUNS))
        sys.exit(1)
    print('%s: all %d sequences of %d steps match the twin (checksums of the full state '
          'after every step, final v, r, heading)' % (where, RUNS, FIELDS))


if __name__ == '__main__':
    main()
