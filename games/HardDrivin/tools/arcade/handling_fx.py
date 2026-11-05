"""Fixed-point twin of handling.py for the 68000 (plan step E3).

handling_fx.py sweep [N] [--drive]
                            random and extreme input sequences; reports
                            overflows, the peak of every value and op counts
                            (--drive: the game's force rule, fx_total=False)

The same algorithm as handling.Car with load='lag', in the arithmetic the
68000 module will use. Every operation goes through Ops, which enforces the
68000's semantics and records peaks:
- MULS/MULU: word operands, long product; DIVS/DIVU: long by word, the
  quotient must fit a word (the 68000 sets V and leaves the register alone
  otherwise); ASR rounds towards minus infinity; longs must stay in 32 bits.

The step is one PAL field, dt = 0.02 × 0.9765625 = 5/256 arcade model seconds,
folded into the constants. Formats (Qn: value × 2^n):

| Quantity | Format |
|---|---|
| speeds u, v, contact velocities, ẏ, wheel speed | Q6 ft/s words (±512); state longs Q22 |
| yaw rate r | Q11 rad/s word (±16); state long Q27 |
| tire deflection y | Q11 ft word (±16); state long Q27 |
| loads N | Q2 lb words; load transfer state long Q16 lb |
| forces, torques | Q0 lb and lb ft words |
| μ, z, sin, cos, curve terms | Q14 words |
| heading | long, Q16 units of G($994A) (1440 per turn) |

Inputs per field: u as native velocity eighths (G($9928) with the enhanced
build's fraction), the mouse offset X − 320, the tires' total longitudinal
force, the front brake torque and the axles' ground contact. Each axle also
reports whether the step was past the curve's peak or sliding (the screech).
HardDrivinHandling.s (plan step G) is this step in 68000 code;
tools/check_handling_step.py compares the two exactly.
"""
import math
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amiga_units as au                       # noqa: E402
import handling                                # noqa: E402

DT = 5 / 256
P = handling.P
M = P['W'] / handling.G


class Overflow(Exception):
    pass


class Ops:
    """68000 integer operations with range checks, op counts and peaks."""

    def __init__(self):
        self.count = Counter()
        self.peak = {}

    def _see(self, site, x):
        p = self.peak.get(site, 0)
        if abs(x) > p:
            self.peak[site] = abs(x)

    def word(self, x, site):
        if not -32768 <= x <= 32767:
            raise Overflow('%s: word %d' % (site, x))
        self._see(site, x)
        return x

    def uword(self, x, site):
        if not 0 <= x <= 65535:
            raise Overflow('%s: uword %d' % (site, x))
        self._see(site, x)
        return x

    def long(self, x, site):
        if not -2 ** 31 <= x < 2 ** 31:
            raise Overflow('%s: long %d' % (site, x))
        self._see(site, x)
        return x

    def muls(self, a, b, site):
        self.count['muls'] += 1
        self.word(a, site + '.a')
        self.word(b, site + '.b')
        return self.long(a * b, site)

    def mulu(self, a, b, site):
        self.count['mulu'] += 1
        self.uword(a, site + '.a')
        self.uword(b, site + '.b')
        r = a * b
        if r >= 2 ** 32:
            raise Overflow(site)
        self._see(site, r)
        return r

    def divs(self, n, d, site):
        self.count['divs'] += 1
        self.long(n, site + '.n')
        self.word(d, site + '.d')
        if d == 0:
            raise Overflow('%s: divide by zero' % site)
        q = abs(n) // abs(d)
        q = q if (n >= 0) == (d > 0) else -q
        return self.word(q, site)

    def divu(self, n, d, site):
        self.count['divu'] += 1
        if not 0 <= n < 2 ** 32:
            raise Overflow('%s: dividend %d' % (site, n))
        self.uword(d, site + '.d')
        if d == 0:
            raise Overflow('%s: divide by zero' % site)
        return self.uword(n // d, site)

    def isqrt(self, n, site):
        """Square root of an unsigned long."""
        self.count['isqrt'] += 1
        if not 0 <= n < 2 ** 32:
            raise Overflow('%s: %d' % (site, n))
        self._see(site + '.n', n)
        return math.isqrt(n)


def q(x, n):
    return int(round(x * (1 << n)))


# constants for one field
K_DT_M = q(DT / M, 22)                 # lb -> Q22 ft/s per field (748)
K_DT_I = q(DT * P['a'] / P['I'], 27)   # lb at 5 ft -> Q27 rad/s per field (6554)
K_PSI = q(DT * au.HEADING_PER_RAD / 2048, 16)   # Q11 rad/s -> Q16 heading per field (143)
K_DN = q(P['h'] / (P['a'] + P['b']), 16)        # lb -> Q16 lb of transfer (10270)
K_LAG = 25                             # dt / tau = 25/128
K_ROLL = q(M / (P['Iw'] + M), 15)      # share of a torque at the road (30025)
K_UNROLL = q((P['Iw'] + M) / M, 14)    # its inverse (17880)
K_W = q(DT / P['Iw'], 22)              # lb ft -> Q22 ft/s of wheel speed (8192)
K_Y = q(1 / P['k'], 27)                # lb -> Q27 ft of deflection (16448)
K_DELTA = q(P['delta_max'] / au.MOUSE_LOCK, 24)  # mouse count -> Q14 rad, then >> 10 (32029)
K_U = q(au.FT_S_PER_V / 8 / au.TIME_SCALE, 19)  # velocity eighth -> Q6 model ft/s, >> 13 (27559)
N0 = q(P['W'] / 2, 2)                  # static axle load, Q2 lb (7050)
FX_MAX = int(handling.FX_MAX)          # input clamp, lb
R_MAX = q(handling.R_MAX, 27)
V_MAX = q(handling.V_MAX, 22)
Y_MAX = q(handling.Y_MAX, 27)
SLIP_MAX = q(handling.SLIP_MAX, 6)


def clamp(x, lim):
    return max(-lim, min(lim, x))
# sqrt(1 - x²) at x = i/256, Q14, for the friction circle
CIRCLE = [q(math.sqrt(max(1 - (i / 256) ** 2, 0)), 14) for i in range(257)]


class Axle:
    def __init__(self, ops, c, mu):
        self.ops = ops
        c1 = c / (P['W'] / 2)
        self.mu = q(mu, 14)
        self.c13 = q(c1 / 3, 8)                    # C'/3, Q8
        self.kd = q(2 * P['k'] * DT / c1, 8)       # lag test, Q8
        self.kc = q(P['k'] / c1, 4)                # k/C', Q4
        self.y = 0                                 # Q27 ft
        self.w = None                              # Q22 ft/s while sliding
        self.Fx = self.Fy = 0
        self.peak = False                          # past the peak of the curve, or sliding

    def force(self, uw, vw, n, torque):
        o = self.ops
        self.peak = False
        if n <= 0:
            self.y, self.w = 0, None
            self.Fx = self.Fy = 0
            return 0, 0
        mun = o.mulu(self.mu, n, 'mu*N') >> 16                       # lb
        if self.w is not None:
            ww = self.w >> 16
            if ww > uw:
                self.w = min(o.long(self.w + (o.word(torque - mun, 'T-muN') << 13), 'w'),
                             (uw + SLIP_MAX) << 16)
                if (self.w >> 16) <= uw:
                    self.w = None
            else:
                self.w = max(o.long(self.w + (o.word(torque + mun, 'T+muN') << 13), 'w'),
                             (uw - SLIP_MAX) << 16)
                if (self.w >> 16) >= uw:
                    self.w = None
            if self.w is not None:
                self.peak = True
                su = o.word(uw - (self.w >> 16), 'slip u')
                s = o.isqrt(o.muls(su, su, 'su²') + o.muls(vw, vw, 'vw²'), 'slip')   # unsigned sum
                if s:
                    self.Fx = -o.divs(o.muls(mun, su, 'muN*su'), s, 'Fx slide')
                    self.Fy = -o.divs(o.muls(mun, vw, 'muN*vw'), s, 'Fy slide')
                else:
                    self.Fx = self.Fy = 0
                return self.Fx, self.Fy
        t = o.muls(torque, K_ROLL, 'T roll') >> 15
        if abs(t) >= mun:
            # starts to slide
            sgn = 1 if t >= 0 else -1
            self.w = o.long((uw << 16) + clamp(o.word(torque - sgn * mun, 'T-muN') << 13, SLIP_MAX << 16), 'w')
            self.Fx, self.Fy = sgn * mun, 0
            self.peak = True
            return self.Fx, self.Fy
        fx = t
        # friction circle
        if fx:
            x = o.divu(abs(fx) << 14, mun, 'Fx/muN')                 # Q14, < 1
            i, f = x >> 6, x & 63
            c = CIRCLE[i] + (o.muls(CIRCLE[i + 1] - CIRCLE[i], f, 'circle') >> 6)
            mu1 = o.muls(self.mu, c, 'mu1') >> 14
        else:
            mu1 = self.mu
        mun1 = o.mulu(mu1, n, "mu'N") >> 16
        auw = max(abs(uw), 64)
        a = o.mulu(abs(vw), self.c13, '|v|C/3')                      # v c13 2^14
        b = o.mulu(mu1, auw, "mu'|u|")                               # mu' u 2^20
        if mu1 == 0 or (a << 6) >= b:
            # past the peak
            self.peak = True
            yd = -vw
            self.y = clamp(o.long(self.y + ((yd * 5) << 13), 'y'), Y_MAX)
            fy = o.long((o.muls(o.word(self.y >> 16, 'y word'), int(P['k']), 'k*y') >> 11)
                        + (o.muls(yd, 25, 'c*yd') >> 2), 'Fy sat')
            if abs(fy) > mun1:
                fy = mun1 if fy > 0 else -mun1
                self.y = o.muls(fy, K_Y, 'y=F/k')
        else:
            if b >= 1 << 24:
                z = o.divu(a << 7, b >> 13, 'z')
            else:
                z = o.divu(a << 11, b >> 9, 'z')
            z = min(z, 16383)
            g = 16384 - z + (o.muls(o.muls(z, z, 'z²') >> 14, 5461, 'z²/3') >> 14)
            lhs = o.mulu(abs(uw), self.kd, '|u|Kd')
            rhs = o.mulu(n, g, 'N*g') >> 2
            if lhs < rhs:
                ng = o.mulu(n, g, 'N*g') >> 16                       # lb
                rate = o.divu(o.mulu(abs(uw), self.kc, '|u|k/C'), ng, 'rate')   # Q10 1/s
                yd = o.word(-(o.muls(o.word(self.y >> 16, 'y word'), rate, 'y*rate') >> 15) - vw, 'yd')
                self.y = clamp(o.long(self.y + ((yd * 5) << 13), 'y'), Y_MAX)
                fy = o.long((o.muls(o.word(self.y >> 16, 'y word'), int(P['k']), 'k*y') >> 11)
                            + (o.muls(yd, 25, 'c*yd') >> 2), 'Fy lag')
                fy = o.word(fy, 'Fy lag word')
            else:
                h = 16384 - z
                h3 = o.muls(o.muls(h, h, 'h²') >> 14, h, 'h³') >> 14
                F = o.muls(mun1, 16384 - h3, 'curve') >> 14
                fy = -F if vw > 0 else F
                self.y = o.muls(fy, K_Y, 'y=F/k')
        self.Fx, self.Fy = fx, fy
        return fx, fy


class FxCar:
    """Integer state and the per-field step."""

    def __init__(self):
        self.ops = Ops()
        self.front = Axle(self.ops, P['C'][0], P['mu'][0])
        self.rear = Axle(self.ops, P['C'][1], P['mu'][1])
        self.v = 0          # Q22 ft/s
        self.r = 0          # Q27 rad/s
        self.dn = 0         # Q16 lb moved to the rear
        self.psi = 0        # Q16 heading units
        self.du = 0         # Q22 ft/s, output

    def step(self, u, counts, fx, brake, contact=3, fx_total=True):
        """u: Q6 model ft/s; counts: mouse X − 320; fx: lb; brake: lb ft at full
        effect (<= 0), faded by the front wheel's speed; contact: bit 0 the
        front axle touches the ground, bit 1 the rear (an axle without contact
        has no load). Returns the sum of the lateral tire forces in lb.

        fx_total: fx is the tires' total longitudinal force, as in the arcade
        replays, and the rear wheels get what the front's force in body axes
        leaves. Otherwise fx is the drive (the game's native force): the rear
        gets fx less the front wheel's own longitudinal force, so the drag of
        the steered front tire is the model's; while braking it gets fx less
        the brake torque, so the brake stays on the front. self.du is the forward speed
        the step adds beyond fx (Q22 ft/s): the tires' deviation from fx and
        v r. The game feeds it back to the native speed."""
        o = self.ops
        fx = clamp(fx, FX_MAX)
        # load transfer, lagged
        dn_t = o.muls(fx, K_DN, 'dn target')
        self.dn = o.long(self.dn + ((dn_t - self.dn) >> 7) * K_LAG, 'dn')
        d = self.dn >> 14                                            # Q2 lb
        nf, nr = max(0, min(2 * N0, N0 - d)), max(0, min(2 * N0, N0 + d))
        if not contact & 1:
            nf = 0
        if not contact & 2:
            nr = 0
        # steering angle, sin and cos by series
        counts = max(-au.MOUSE_LOCK, min(au.MOUSE_LOCK, counts))
        dl = o.word(o.muls(counts, K_DELTA, 'delta') >> 10, 'delta')     # Q14 rad
        d2 = o.muls(dl, dl, 'd²') >> 14
        d3 = o.muls(d2, dl, 'd³') >> 14
        d4 = o.muls(d2, d2, 'd⁴') >> 14
        sd = dl - (o.muls(d3, 2731, 'd³/6') >> 14)
        cd = 16384 - (d2 >> 1) + (o.muls(d4, 683, 'd⁴/24') >> 14)
        vw = o.word(self.v >> 16, 'v word')
        rw = o.word(self.r >> 16, 'r word')
        ar = o.muls(rw, 5, '5r') >> 5                                # Q6 ft/s
        vcf, vcr = o.word(vw + ar, 'vcf'), o.word(vw - ar, 'vcr')
        uwf = o.word(o.long(o.muls(u, cd, 'u cd') + o.muls(vcf, sd, 'v sd'), 'uwf') >> 14, 'uwf')
        vwf = o.word(o.long(o.muls(vcf, cd, 'v cd') - o.muls(u, sd, 'u sd'), 'vwf') >> 14, 'vwf')
        # brake fade s(ω), Q14: 0 below 2 rad/s, 0.05·ω to 10, then 1
        wf = (self.front.w >> 16) if self.front.w is not None else uwf
        aw = abs(wf)
        s = 0 if aw < 128 else (o.muls(aw, 13107, 'fade') >> 10 if aw < 640 else 16384)
        bt = o.muls(brake, s if wf >= 0 else -s, 'brake') >> 14
        fxf, fyf = self.front.force(uwf, vwf, nf, o.word(bt, 'brake word'))
        fxbf = o.long(o.muls(fxf, cd, 'fx cd') - o.muls(fyf, sd, 'fy sd'), 'fxbf') >> 14
        fybf = o.word(o.long(o.muls(fxf, sd, 'fx sd') + o.muls(fyf, cd, 'fy cd'), 'fybf') >> 14, 'fybf')
        if fx_total:
            own = fxbf
        elif brake:
            own = o.word(bt, 'brake word')     # the front brake's share, front only
        else:
            own = o.muls(fxf, cd, 'fx cd') >> 14
        rt = clamp(fx - own, FX_MAX)
        rear_t = o.muls(rt, K_UNROLL, 'rear T') >> 14
        fxr, fyr = self.rear.force(u, vcr, nr, o.word(rear_t, 'rear T word'))
        fyr = o.word(fyr, 'fyr')
        dev = o.word(fxbf + fxr - fx, 'fx deviation')
        self.du = o.long(o.muls(dev, K_DT_M, 'dev dt/m') + (o.muls(vw, rw, 'v r') >> 3) * 5, 'du')
        # integrate: pose from the old rates, then the rates
        self.psi = o.long(self.psi + o.muls(rw, K_PSI, 'psi'), 'psi')
        if self.psi > 720 << 16:
            self.psi -= 1440 << 16
        elif self.psi < -720 << 16:
            self.psi += 1440 << 16
        ur = o.muls(u, rw, 'u r') >> 3
        self.v = clamp(o.long(self.v + o.muls(fybf, K_DT_M, 'Fyf dt/m') + o.muls(fyr, K_DT_M, 'Fyr dt/m')
                              - ur * 5, 'v'), V_MAX)
        self.r = clamp(o.long(self.r + o.muls(fybf, K_DT_I, 'Fyf dt/I') - o.muls(fyr, K_DT_I, 'Fyr dt/I'),
                              'r'), R_MAX)
        o.count['steps'] += 1
        return fybf + fyr


class Car:
    """handling.Car's interface over FxCar, for handling_check.py: floats in
    arcade model units, quantised to the Amiga's inputs."""

    class _W:
        def __init__(self, axle):
            self.a = axle

        @property
        def w(self):
            return None if self.a.w is None else self.a.w / (1 << 22)

    def __init__(self):
        self.fx = FxCar()
        self.front = Car._W(self.fx.front)
        self.psi0 = self.x = self.z = 0.0
        self.turns = 0                      # wraps of the twin's heading, to keep psi continuous

    def set_pose(self, psi, x, z):
        self.psi0, self.x, self.z = psi, x, z

    @property
    def v(self):
        return self.fx.v / (1 << 22)

    @property
    def r(self):
        return self.fx.r / (1 << 27)

    @property
    def psi(self):
        return self.psi0 + (self.fx.psi + self.turns * (1440 << 16)) / 65536 / au.HEADING_PER_RAD

    def step(self, dt, u, delta, fx, brake):
        assert abs(dt - DT) < 1e-6, 'the twin steps one PAL field'
        v8 = int(round(u * au.TIME_SCALE / au.FT_S_PER_V * 8))       # native velocity eighths
        uq = (v8 * K_U) >> 13
        counts = int(round(delta / P['delta_max'] * au.MOUSE_LOCK))
        v, psi = self.v, self.psi
        c, s = math.cos(psi), math.sin(psi)
        ug = uq / 64
        before = self.fx.psi
        f = self.fx.step(uq, counts, int(round(fx)), int(round(brake)))
        if self.fx.psi - before > 720 << 16:
            self.turns -= 1
        elif self.fx.psi - before < -720 << 16:
            self.turns += 1
        self.x += (ug * c - v * s) * dt
        self.z += (-ug * s - v * c) * dt
        return f / M


def sweep(n=200, seed=1, fields=1500, fx_total=True):
    """Random input sequences plus held extremes; no overflow may occur."""
    rnd = random.Random(seed)
    peaks, counts, fails = {}, Counter(), []
    vmax = 8 * 520                    # eighths: 145 MPH plus margin

    def run(seq, label):
        car = FxCar()
        try:
            for v8, m, fx, br in seq:
                car.step((v8 * K_U) >> 13, m, fx, br, fx_total=fx_total)
        except Overflow as e:
            fails.append('%s: %s' % (label, e))
        for k, x in car.ops.peak.items():
            peaks[k] = max(peaks.get(k, 0), x)
        counts.update(car.ops.count)

    # held extremes: every corner of the input box for 30 s
    for v8 in (0, 8, 80, vmax // 2, vmax, -80, -200):
        for m in (-320, -100, 0, 100, 320):
            for fx in (-FX_MAX, 0, FX_MAX, -20000, 20000):
                for br in (0, -4653):
                    run([(v8, m, fx, br)] * fields, 'hold v8=%d m=%d fx=%d br=%d' % (v8, m, fx, br))
    # random sequences: inputs that jump and wander
    for k in range(n):
        seq, v8, m, fx, br = [], rnd.randrange(0, vmax), 0, 0, 0
        for i in range(fields):
            if rnd.random() < 0.05:
                m = rnd.choice((rnd.randint(-320, 320), -320, 320, 0))
            if rnd.random() < 0.03:
                br = rnd.choice((0, 0, -4653, -rnd.randint(0, 4653)))
            if rnd.random() < 0.05:
                fx = rnd.choice((0, rnd.randint(-FX_MAX, FX_MAX), FX_MAX, -FX_MAX, rnd.randint(-32768, 32767)))
            v8 = max(-200, min(vmax, v8 + rnd.randint(-40, 40)))
            seq.append((v8, m, fx, br))
        run(seq, 'random %d' % k)
    return peaks, counts, fails


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'sweep':
        args = [a for a in sys.argv[2:] if a != '--drive']
        n = int(args[0]) if args else 200
        peaks, counts, fails = sweep(n, fx_total='--drive' not in sys.argv)
        print('%d failures' % len(fails))
        for f in fails[:20]:
            print('  ' + f)
        print('\npeaks (site: largest |value|, bits used of the type)')
        for k in sorted(peaks):
            print('  %-16s %12d  %4.1f bits' % (k, peaks[k], math.log2(peaks[k] + 1)))
        s = counts.pop('steps', 1)
        print('\nper field: ' + ', '.join('%s %.2f' % (k, v / s) for k, v in sorted(counts.items())))


if __name__ == '__main__':
    main()
