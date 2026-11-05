"""Check the 68000 handling step against its Python twin (plan step G4).

check_handling_step.py SLAVE LISTING [--random N] [--fields F] [--seed S]

Loads the slave's code hunk into Unicorn (68000 model), calls _handling_step
with a private state block and compares the complete model state after every
step with tools/arcade/handling_fx.py (the game's force rule,
fx_total=False): lateral velocity, yaw rate, load transfer, heading, both
axles' deflection, wheel speed, slide and peak flags, the lateral force sum
and the forward speed output. The inputs are handling_fx.sweep's: every corner
of the input box held, then random sequences; contact is varied as well.
Exits nonzero on the first difference.
"""
import argparse
import ctypes as C
import os
import random
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/arcade'))
import handling_fx as hf                     # noqa: E402

u = C.CDLL(str(Path(os.environ['AMIGA_UNICORN']) / 'lib/libunicorn.dylib'))
P, U, Z, I = C.c_void_p, C.c_uint64, C.c_size_t, C.c_int
for name, args in [('uc_open', [I, I, C.POINTER(P)]), ('uc_ctl', [P, C.c_uint32]),
                   ('uc_mem_map', [P, U, Z, C.c_uint32]), ('uc_mem_write', [P, U, P, Z]),
                   ('uc_mem_read', [P, U, P, Z]), ('uc_reg_write', [P, I, P]),
                   ('uc_reg_read', [P, I, P]), ('uc_emu_start', [P, U, U, U, Z]), ('uc_close', [P])]:
    f = getattr(u, name)
    f.argtypes = args
    f.restype = I
u.uc_strerror.argtypes = [I]
u.uc_strerror.restype = C.c_char_p
REG_A0, REG_A7, REG_PC = 1, 8, 18

# state offsets, as in HardDrivinHandling.s
HS_V, HS_R, HS_DN, HS_PSI, HS_FRONT, HS_REAR = 0, 4, 8, 12, 16, 26
HS_U, HS_COUNTS, HS_FXIN, HS_BRAKE, HS_CONTACT, HS_FYSUM = 36, 38, 40, 42, 44, 46
HS_DUF, HS_MODEL = 66, 72


def ok(x):
    assert x == 0, u.uc_strerror(x)


def code_hunk(path):
    d = Path(path).read_bytes()
    w = struct.unpack('>%dI' % (len(d) // 4), d[:len(d) // 4 * 4])
    assert w[0] == 0x3f3, 'not a hunk executable'
    i = 1
    while w[i]:                                    # resident library names
        i += w[i] + 1
    i += 1
    count, first, last = w[i], w[i + 1], w[i + 2]
    i += 3 + (last - first + 1)
    assert w[i] == 0x3e9, 'first hunk is not code'
    n = w[i + 1] & 0x3fffffff
    return d[(i + 2) * 4:(i + 2 + n) * 4]


def label_offsets(listing, names):
    """Offsets of labels in section 0 from a vasm listing: the address of the
    first addressed line after the label's own line."""
    want, found, pending = set(names), {}, []
    addr = re.compile(r'^00:([0-9A-F]{8}) ')
    lab = re.compile(r'^\s+\d+: (\S+):')
    for line in open(listing, encoding='latin-1'):
        m = lab.match(line[28:]) if len(line) > 28 else None
        if m and m.group(1) in want:
            pending.append(m.group(1))
        a = addr.match(line)
        if a and pending:
            for p in pending:
                found[p] = int(a.group(1), 16)
            pending = []
    missing = want - set(found)
    assert not missing, missing
    return found


class Emu:
    BASE, STATE, STACK, END = 0x10000, 0x80000, 0x8fff0, 0x88000

    def __init__(self, code, step):
        self.h = P()
        ok(u.uc_open(7, 1 << 30, C.byref(self.h)))
        ok(u.uc_ctl(self.h, 0x44000007, I(1)))     # CPU model: 68000
        ok(u.uc_mem_map(self.h, 0, 0x100000, 7))
        self.write(self.BASE, code)
        self.write(self.END, bytes.fromhex('4e714e71'))
        self.step_addr = self.BASE + step
        self.write(self.STATE, bytes(HS_MODEL))

    def write(self, a, b):
        ok(u.uc_mem_write(self.h, a, b, len(b)))

    def read(self, a, n):
        b = C.create_string_buffer(n)
        ok(u.uc_mem_read(self.h, a, b, n))
        return b.raw

    def reg(self, k, v):
        x = C.c_uint32(v & 0xffffffff)
        ok(u.uc_reg_write(self.h, k, C.byref(x)))

    def step(self, uq, counts, fx, brake, contact):
        self.write(self.STATE + HS_U, struct.pack('>hhhhh', uq, counts, fx, brake, contact))
        self.write(self.STACK, struct.pack('>I', self.END))
        self.reg(REG_A0, self.STATE)
        self.reg(REG_A7, self.STACK)
        ok(u.uc_emu_start(self.h, self.step_addr, self.END, 0, 100000))
        return self.read(self.STATE, HS_MODEL)

    def close(self):
        ok(u.uc_close(self.h))


def unpack(b):
    v, r, dn, psi = struct.unpack('>iiii', b[:16])
    axles = []
    for o in (HS_FRONT, HS_REAR):
        y, w, slide, peak = struct.unpack('>iibb', b[o:o + 10])
        axles.append((y, w if slide else None, bool(peak)))
    fysum = struct.unpack('>h', b[HS_FYSUM:HS_FYSUM + 2])[0]
    du = struct.unpack('>i', b[HS_DUF:HS_DUF + 4])[0]
    return v, r, dn, psi, axles, fysum, du


def expected(car, f):
    axles = [(a.y, a.w, a.peak) for a in (car.front, car.rear)]
    return car.v, car.r, car.dn, car.psi, axles, (f + 32768) % 65536 - 32768, car.du


def sequences(n_random, fields, seed):
    vmax = 8 * 520
    rnd = random.Random(seed)
    fx_max = hf.FX_MAX
    for v8 in (0, 8, 80, vmax // 2, vmax, -80, -200):
        for m in (-320, -100, 0, 100, 320):
            for fx in (-fx_max, 0, fx_max, -20000, 20000):
                for br in (0, -4653):
                    yield 'hold v8=%d m=%d fx=%d br=%d' % (v8, m, fx, br), [(v8, m, fx, br, 3)] * fields
    for c in (0, 1, 2):
        for v8 in (80, vmax // 2):
            for m in (-320, 100):
                yield 'contact %d v8=%d m=%d' % (c, v8, m), [(v8, m, 2000, 0, 3)] * (fields // 2) + \
                    [(v8, m, 2000, 0, c)] * (fields // 2)
    for k in range(n_random):
        seq, v8, m, fx, br, c = [], rnd.randrange(0, vmax), 0, 0, 0, 3
        for i in range(fields):
            if rnd.random() < 0.05:
                m = rnd.choice((rnd.randint(-320, 320), -320, 320, 0))
            if rnd.random() < 0.03:
                br = rnd.choice((0, 0, -4653, -rnd.randint(0, 4653)))
            if rnd.random() < 0.05:
                fx = rnd.choice((0, rnd.randint(-fx_max, fx_max), fx_max, -fx_max, rnd.randint(-32768, 32767)))
            if rnd.random() < 0.01:
                c = rnd.choice((3, 3, 3, 0, 1, 2))
            v8 = max(-200, min(vmax, v8 + rnd.randint(-40, 40)))
            seq.append((v8, m, fx, br, c))
        yield 'random %d' % k, seq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slave')
    ap.add_argument('listing')
    ap.add_argument('--random', type=int, default=200)
    ap.add_argument('--fields', type=int, default=1500)
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    off = label_offsets(a.listing, ['_handling_step'])
    emu = Emu(code_hunk(a.slave), off['_handling_step'])
    runs = steps = slides = peaks = 0
    try:
        for label, seq in sequences(a.random, a.fields, a.seed):
            car = hf.FxCar()
            emu.write(emu.STATE, bytes(HS_MODEL))
            for i, (v8, m, fx, br, c) in enumerate(seq):
                uq = (v8 * hf.K_U) >> 13
                f = car.step(uq, m, fx, br, c, fx_total=False)
                got = unpack(emu.step(uq, m, fx, br, c))
                want = expected(car, f)
                if got != want:
                    print('MISMATCH %s, field %d, inputs %s' % (label, i, (uq, m, fx, br, c)))
                    print('  68000 %s' % (got,))
                    print('  twin  %s' % (want,))
                    sys.exit(1)
                steps += 1
                slides += any(x[1] is not None for x in want[4])
                peaks += any(x[2] for x in want[4])
            runs += 1
    finally:
        emu.close()
    print('%d sequences, %d steps: 68000 state equals the twin after every step '
          '(%d steps with a sliding wheel, %d past a peak)' % (runs, steps, slides, peaks))


if __name__ == '__main__':
    main()
