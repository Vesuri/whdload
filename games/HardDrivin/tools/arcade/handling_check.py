"""Check the handling model against the arcade (plan steps E2 and E3).

handling_check.py ROOT [--dt S|arcade] [--model M] [--steer mouse|native] [--vs M] [--all]

Replays every C manoeuvre in ROOT (a c_runs.sh matrix) through the model: the
model gets the arcade run's steering word, brake pedal and ground speed (on the
Amiga the speed comes from the native engine), integrates its own heading,
sideslip and position, and feel.py measures it with the same code as the arcade
run. Prints model against arcade for the handling groups C1c-C1g; --all also
lists the straight-line groups, whose speeds are replayed and so match by
construction.

--model is the float model of handling.py with its load transfer (lag, the
default, static or pitch), or fixed for the 68000 twin of handling_fx.py.
--vs M compares against model M instead of the arcade, within 5%: E3's check
is --model fixed --vs lag --steer mouse.

--dt S steps the model every S real seconds (default 0.02, one PAL field),
sampling the latest arcade input; --dt arcade steps with the arcade's own
results (ticks x 0.004 s, with its steering-rate prediction).

--steer mouse rounds the steering to the Amiga's mouse resolution (one count
of X - 320 = 4096/320 arcade steer words, amiga_units.py); --steer native to
the native steer value (X - 320) / 20, truncated as DIVS does.
"""
import argparse
import copy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amiga_units                            # noqa: E402
import feel                                   # noqa: E402
import handling                               # noqa: E402
from hdstate import states, TICK, TIME_SCALE  # noqa: E402

TS = TIME_SCALE
HANDLING = ('C1c', 'C1d', 'C1e', 'C1f', 'C1g')


def drag(u):
    return 0.0087 * u * u + 105.0 if u > 0.5 else 0.0


def smooth_accel(S, span=0.1):
    """Ground acceleration (real ft/s²) by central differences over SPAN."""
    out, j0 = [], 0
    for i, s in enumerate(S):
        while S[j0].pt < s.pt - span / 2:
            j0 += 1
        j1 = i
        while j1 + 1 < len(S) and S[j1 + 1].pt <= s.pt + span / 2:
            j1 += 1
        dt = S[j1].pt - S[j0].pt
        out.append((S[j1].speed - S[j0].speed) / dt if dt > 0 else 0.0)
    return out


class Inputs:
    """Inputs of an arcade run as functions of real physics time."""

    def __init__(self, S):
        self.S = S
        self.acc = smooth_accel(S)
        self.i = 0

    def at(self, t):
        S = self.S
        while self.i + 1 < len(S) and S[self.i + 1].pt <= t:
            self.i += 1
        i = self.i
        a, b = S[i], S[min(i + 1, len(S) - 1)]
        f = (t - a.pt) / (b.pt - a.pt) if b.pt > a.pt else 0.0
        f = min(max(f, 0.0), 1.0)
        v = a.speed + (b.speed - a.speed) * f
        ax = self.acc[i] + (self.acc[min(i + 1, len(S) - 1)] - self.acc[i]) * f
        return a, v, ax


def make_car(kind):
    if kind == 'fixed':
        import handling_fx
        return handling_fx.Car()
    return handling.Car(load=kind)


def replay(S, dt=0.02, kind='lag', steer_res=None):
    """Model states at the arcade results' times, as copies of S."""
    car = make_car(kind)
    car.set_pose(math.radians(S[0].heading), S[0].pos[0], S[0].pos[2])
    inp = Inputs(S)
    m = handling.P['W'] / handling.G
    track = []                           # (t, psi, v, x, z, u) after each step
    t = S[0].pt

    def record(u):
        track.append((t, car.psi, car.v, car.x, car.z, u))

    record(0.0)
    ay = 0.0
    if dt == 'arcade':
        steps = [(S[i].pt, S[i].ticks * TICK) for i in range(len(S) - 1)]
    else:
        n = int((S[-1].pt - S[0].pt) / dt)
        steps = [(S[0].pt + k * dt, dt) for k in range(n)]
    for t0, h in steps:
        s, v_real, ax_real = inp.at(t0 + 1e-9)
        vg = v_real / TS                                 # ground speed, model ft/s
        u = math.sqrt(max(vg * vg - car.v * car.v, 0.0))
        hm = h * TS                                      # model seconds
        steer = s.inp['steer'] + (s.inp['steer_rate'] * s.ticks / 2 if dt == 'arcade' else 0)
        if steer_res == 'mouse':
            steer = amiga_units.steer_word(round(amiga_units.mouse_from_word(steer)))
        elif steer_res == 'native':
            steer = amiga_units.steer_word(20 * int(amiga_units.mouse_from_word(steer) / 20))
        delta = handling.P['delta_max'] * steer / 4096
        # the tires' longitudinal force in body axes: the path acceleration
        # less the part of the lateral acceleration that lies along the path
        beta = math.atan2(car.v, u) if u else 0.0
        fx = m * (ax_real / (TS * TS) - ay * math.sin(beta)) / math.cos(beta) + drag(u)
        ay = car.step(hm, u, delta, fx, -s.inp['brake'] / 4096 * handling.P['brake_max'])
        t = t0 + h
        record(u)
    # sample the track at the arcade results' times
    out, k = [], 0
    for s in S:
        while k + 1 < len(track) and track[k + 1][0] <= s.pt:
            k += 1
        a, b = track[k], track[min(k + 1, len(track) - 1)]
        f = (s.pt - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
        f = min(max(f, 0.0), 1.0)
        psi, v, x, z, u = (a[j] + (b[j] - a[j]) * f for j in range(1, 6))
        c, sn = math.cos(psi), math.sin(psi)
        q = copy.copy(s)
        q.fwd = (c, 0.0, -sn)
        q.vel = ((u * c - v * sn) * TS, 0.0, (-u * sn - v * c) * TS)
        q.pos = (x, s.pos[1], z)
        out.append(q)
    return out


def tol_ok(a, m, unit, rel=0.10):
    if a is None or m is None or any(isinstance(x, float) and math.isnan(x) for x in (a, m)):
        return None
    ab = feel.TOL[unit][0]
    return abs(a - m) <= max(ab, rel * abs(a))


def compare(root, dt, kind, show_all=False, out=sys.stdout, steer_res=None, ref=None):
    cache = {}

    def loader(k):
        def get(name):
            if (k, name) not in cache:
                cache[k, name] = replay(states(os.path.join(root, name, 'log.txt')), dt, k, steer_res)
            return cache[k, name]
        return get
    A = feel.analyse(root, loader(ref) if ref else None)[0]
    M = feel.analyse(root, loader(kind))[0]
    rel = 0.05 if ref else 0.10
    head = ref or 'Arcade'
    mrows = {(g, n): v for g, n, v, _ in M.rows}
    group, counts = None, {}
    for g, n, a, unit in A.rows:
        if not show_all and not g.startswith(HANDLING):
            continue
        m = mrows.get((g, n))
        ok = tol_ok(a, m, unit, rel)
        key = g.split()[0]
        c = counts.setdefault(key, [0, 0])
        if ok is not None:
            c[0] += ok
            c[1] += 1
        if g != group:
            group = g
            out.write('\n**%s**\n\n| Metric | %s | %s | Unit | Within %d%% |\n|---|---|---|---|---|\n'
                      % (g, head, kind, rel * 100))
        out.write('| %s | %s | %s | %s | %s |\n' % (n, feel.fmt(a, unit), feel.fmt(m, unit), unit,
                                                 '-' if ok is None else ('yes' if ok else '**no**')))
    out.write('\n')
    for k, (a, b) in counts.items():
        out.write('%s: %d of %d within %d%% (or the repeat floor)\n' % (k, a, b, rel * 100))
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--dt', default='0.02')
    ap.add_argument('--model', default='lag', choices=('pitch', 'lag', 'static', 'fixed'),
                    help='float model with this load transfer, or the fixed-point twin')
    ap.add_argument('--steer', choices=('mouse', 'native'))
    ap.add_argument('--vs', choices=('pitch', 'lag', 'static', 'fixed'))
    ap.add_argument('--all', action='store_true')
    o = ap.parse_args()
    dt = o.dt if o.dt == 'arcade' else float(o.dt)
    compare(o.root, dt, o.model, o.all, steer_res=o.steer, ref=o.vs)


if __name__ == '__main__':
    main()
