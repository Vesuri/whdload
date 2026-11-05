"""Step C feel measurements from hd.lua logs (see ARCADE_ROMS.md, "Feel measurements").

  feel.py trace RUN_DIR [STEP_S]        sampled trace with trouble flags
  feel.py report ROOT [REPEAT_ROOT]     feel table for the c_runs.sh matrix in ROOT,
                                        compared with a repeat matrix; SVG plots go
                                        to ROOT/plots

Times are physics time (the MSP's tick count), speeds come from the
speedometer calibration and angles are in degrees. The manoeuvres turn left;
the tables give yaw rates as magnitudes and sideslip as the nose-in angle:
positive when the nose points into the turn relative to the direction of
travel (the usual attitude at speed), negative when it points outside (the
low-speed geometry of a reference point ahead of the rear axle).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hdstate import states, derived, G   # noqa: E402

GROUND_Y = 3.5        # feet: the flat ground around the start line
MPH_S_TO_G = 1.4666667 / G


def load(run):
    """States of a run directory, or RUN itself when it is already a list
    (handling_check.py passes model states)."""
    if not isinstance(run, str):
        return run
    return states(os.path.join(run, 'log.txt'))


def trouble(S, i):
    """Why sample i is not clean flat-ground driving, or ''."""
    s = S[i]
    why = []
    if abs(s.pos[1] - GROUND_Y) > 1:
        why.append('height')
    if 6 in s.raw['srf'] or 7 in s.raw['srf']:
        why.append('contact')
    if i and math.dist(S[i - 1].pos, s.pos) > 1 + S[i - 1].speed * (s.t - S[i - 1].t) * 1.5:
        why.append('jump')
    # a collision: losing more than 3 MPH in 0.1 s (1.4 g; full braking is
    # 0.9 g) without a gear change, which jerks the speed when braking
    j = i
    while j > 0 and S[j].pt > s.pt - 0.1:
        j -= 1
    near = S[max(0, j - 3):i + 3]
    if S[j].mph - s.mph > 3 and len(set(x.gear for x in near)) == 1:
        why.append('impact')
    return ','.join(why)


def trace(run, step=0.25):
    S = load(run)
    D = derived(S)
    nxt = S[0].st
    print('   st   mph  rpm g  head  slip   yaw   lat   lon     X      Z srf   steer  gas brake trouble')
    for i, (s, d) in enumerate(zip(S, D)):
        tr = trouble(S, i)
        if s.st < nxt and not tr:
            continue
        nxt = s.st + step
        d = d or {'yaw': 0, 'lat': 0, 'lon': 0}
        print('%6.2f %5.1f %4d %s %6.1f %5.1f %5.1f %5.2f %5.2f %6.0f %6.0f %d%d %6d %5d %5d %s' % (
            s.st, s.mph, s.rpm, s.gear or '-', s.heading, s.slip, d['yaw'], d['lat'], d['lon'],
            s.pos[0], s.pos[2], *s.raw['srf'], s.inp['steer'], s.inp['gas'], s.inp['brake'], tr))


# ---- helpers ---------------------------------------------------------------

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float('nan')


def yaw_rates(S, span):
    return [d['yaw'] if d else 0.0 for d in derived(S, span)]


def crossing(S, i0, f, level):
    """Physics time where f(S[i]) first reaches LEVEL at or after index i0."""
    for i in range(max(i0, 1), len(S)):
        a, b = f(S[i - 1]), f(S[i])
        if b >= level:
            if b == a:
                return S[i].pt
            return S[i - 1].pt + (S[i].pt - S[i - 1].pt) * (level - a) / (b - a)
    return None


def index_at(S, pt):
    for i, s in enumerate(S):
        if s.pt >= pt:
            return i
    return len(S) - 1


def slope(S, i0, i1, f):
    """Least-squares slope of f against physics time over S[i0:i1]."""
    xs = [S[i].pt for i in range(i0, i1)]
    ys = [f(S[i]) for i in range(i0, i1)]
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else float('nan')


APPROACH_END = 34    # script time: the turn onto the open ground is over (c.lua)


def steer_jumps(S, size=80):
    """Indices after the approach where the steering input word jumps by more than SIZE."""
    return [i for i in range(1, len(S)) if S[i].st > APPROACH_END and
            abs(S[i].inp['steer'] - S[i - 1].inp['steer']) > size]


def troubled(S, i0, i1):
    for i in range(i0, i1):
        if trouble(S, i):
            return '%s at %.1f' % (trouble(S, i), S[i].st)
    return ''


# Metrics are (group, name, value, unit). Units set the repeat tolerance as
# (absolute, relative): the larger one applies. Response times are in ms with
# a two-frame floor, as one MSP result takes about 16 ms; '' is an input word.
TOL = {'s': (0.1, 0.05), 'ms': (35, 0.1), 'g': (0.03, 0.05), 'deg': (0.5, 0.05), 'deg/s': (1.0, 0.05),
       'mph': (1.0, 0.02), 'ft': (3.0, 0.05), 'rpm': (60, 0.02), '%': (10.0, 0.0), '1/kft': (0.3, 0.05),
       'deg/s/k': (1.0, 0.05), '': (30, 0.03)}


class Report:
    def __init__(self):
        self.rows = []
        self.notes = []

    def add(self, group, name, value, unit):
        self.rows.append((group, name, value, unit))

    def note(self, text):
        self.notes.append(text)


# ---- manoeuvres ------------------------------------------------------------

def c1a_auto(run, R, P):
    S = load(run)
    g = 'C1a automatic'
    i_brake = max(i for i, s in enumerate(S) if s.inp['brake'] > 1000)
    i0 = next(i for i in range(i_brake, len(S)) if S[i].inp['gas'] > 2000)
    i_off = next(i for i in range(i0, len(S)) if S[i].inp['gas'] < 100)
    t0 = S[i0].pt
    for v in (30, 60, 100):
        R.add(g, '0-%d MPH' % v, crossing(S, i0, lambda s: s.mph, v) - t0, 's')
    i1 = index_at(S, t0 + 1.0)
    R.add(g, 'launch, first 1 s', (S[i1].mph - S[i0].mph) / (S[i1].pt - t0) * MPH_S_TO_G, 'g')
    for i in range(i0 + 1, i_off):
        if S[i].gear and S[i - 1].gear and S[i].gear > S[i - 1].gear:
            R.add(g, 'shift %d-%d at' % (S[i - 1].gear, S[i].gear), S[i - 1].mph, 'mph')
            R.add(g, 'shift %d-%d rpm' % (S[i - 1].gear, S[i].gear), S[i - 1].rpm, 'rpm')
    R.add(g, 'top speed (50 s full throttle)', max(s.mph for s in S[i0:i_off]), 'mph')
    coast(S, i_off, len(S), g, 'coast in gear', R)
    if troubled(S, i0, len(S)):
        R.note('%s: %s' % (g, troubled(S, i0, len(S))))
    P['c1a'] = [('automatic', [s.pt - t0 for s in S[i0:]], [s.mph for s in S[i0:]])]


def coast(S, i0, i1, g, label, R):
    """Deceleration while coasting, at several speeds."""
    for v in (130, 110, 90, 70):
        idx = [i for i in range(i0, i1) if abs(S[i].mph - v) < 4]
        if len(idx) > 20 and idx[-1] - idx[0] == len(idx) - 1:
            R.add(g, '%s at %d MPH' % (label, v), -slope(S, idx[0], idx[-1] + 1, lambda s: s.mph) * MPH_S_TO_G, 'g')


def c1a_stick(run, R, P):
    S = load(run)
    g = 'C1a stick'
    for i in range(1, len(S)):
        if S[i - 1].gear in (1, 2, 3) and S[i].gear != S[i - 1].gear and S[i].inp['clutch'] > 2000 \
                and S[i - 1].mph > 5:
            R.add(g, 'gear %d max speed' % S[i - 1].gear, S[i - 1].mph, 'mph')
            R.add(g, 'gear %d max rpm' % S[i - 1].gear, max(s.rpm for s in S[max(0, i - 120):i]), 'rpm')
    i_n = next(i for i in range(len(S)) if S[i].gear is None and S[i].mph > 50)
    R.add(g, 'top speed in 4th', max(s.mph for s in S[:i_n]), 'mph')
    i_stall = next((i for i in range(i_n, len(S)) if S[i].rpm < 500), len(S))
    coast(S, i_n, i_stall, g, 'coast in neutral', R)
    if troubled(S, 0, len(S)):
        R.note('%s: %s' % (g, troubled(S, 0, len(S))))
    t0 = next(s.pt for s in S if s.mph > 0.5)
    P['c1a'].append(('stick', [s.pt - t0 for s in S if s.pt >= t0], [s.mph for s in S if s.pt >= t0]))


def c1b(run, R, P, label):
    S = load(run)
    g = 'C1b braking, %s' % label
    on = [i for i in range(1, len(S)) if S[i].inp['brake'] > 500 and S[i - 1].inp['brake'] <= 500]
    for i0 in on:
        v0 = S[i0].mph
        i_stop = next(i for i in range(i0, len(S)) if S[i].mph < 0.5)
        dist = sum(S[i].speed * (S[i + 1].pt - S[i].pt) for i in range(i0, i_stop))
        ia = next(i for i in range(i0, i_stop) if S[i].mph <= 0.9 * v0)
        ib = next(i for i in range(i0, i_stop) if S[i].mph <= 10)
        name = 'from %d MPH' % round(v0, -1)
        R.add(g, name + ': deceleration', -slope(S, ia, ib, lambda s: s.mph) * MPH_S_TO_G, 'g')
        R.add(g, name + ': stopping distance', dist, 'ft')
        R.add(g, name + ': time to stop', S[i_stop].pt - S[i0].pt, 's')
        if troubled(S, i0, i_stop):
            R.note('%s %s: %s' % (g, name, troubled(S, i0, i_stop)))
    R.add(g, 'pedal input word', max(s.inp['brake'] for s in S), '')


def c1c(run, R, P, v):
    S = load(run)
    g = 'C1c steady state, %d MPH' % v
    yaw = yaw_rates(S, 0.5)
    J = [i for i, s in enumerate(S) if s.st > APPROACH_END and abs(s.inp['steer']) > 60]
    i0, i1 = J[0], next(i for i in range(J[0], len(S)) if abs(S[i].inp['steer']) < 60) - 15
    centre = mean(s.inp['steer'] for s in S[i0 - 120:i0 - 5])
    pts = []   # (|steer|, |yaw|, lateral g, |slip|)
    raw = []   # (steer, yaw), signed, below 0.4 g
    for i in range(i0 + 30, i1):
        s = S[i]
        ay = s.speed * math.radians(abs(yaw[i])) / G
        pts.append((abs(s.inp['steer'] - centre), abs(yaw[i]), ay, s.slip if yaw[i] < 0 else -s.slip))
        if ay < 0.4:
            raw.append((s.inp['steer'], yaw[i]))
    ay_max = sorted(p[2] for p in pts)[int(0.95 * len(pts))]
    # the slope of yaw on steer with an intercept: the arcade runs approach
    # holding a heading with a steer offset and a yaw of their own (90 MPH:
    # -20 words and -0.85 deg/s), and a fit through the centre's steer alone
    # took the offset for gain (45.4 instead of 38)
    mx = mean(p[0] for p in raw)
    my = mean(p[1] for p in raw)
    gain = abs(sum((p[0] - mx) * (p[1] - my) for p in raw) / sum((p[0] - mx) ** 2 for p in raw)) * 1000
    R.add(g, 'yaw gain below 0.4 g', gain, 'deg/s/k')
    R.add(g, 'path curvature gain below 0.4 g', math.radians(gain) / (v * 1.4666667) * 1000, '1/kft')
    R.add(g, 'max lateral', ay_max, 'g')
    R.add(g, 'steer word at 95% of max lateral', next(p[0] for p in pts if p[2] >= 0.95 * ay_max), '')
    for a in (0.5, 0.8):
        near = [p[3] for p in pts if abs(p[2] - a) < 0.05]
        R.add(g, 'sideslip at %.1f g' % a, mean(near), 'deg')
    R.add(g, 'sideslip at the end of the ramp', mean(p[3] for p in pts[-30:]), 'deg')
    if troubled(S, i0, i1):
        R.note('%s: %s' % (g, troubled(S, i0, i1)))
    P.setdefault('c1c', []).append(('%d MPH' % v, [p[0] for p in pts], [p[2] for p in pts]))
    P.setdefault('c1c_slip', []).append(('%d MPH' % v, [p[2] for p in pts], [p[3] for p in pts]))


def c1d(run, R, P, v):
    S = load(run)
    yaw = yaw_rates(S, 0.04)
    yaw_m = yaw_rates(S, 0.1)
    yaw_s = yaw_rates(S, 0.5)
    J = steer_jumps(S)
    for n, (ja, jb) in enumerate(((J[0], J[1]), (J[2], J[3]))):
        g = 'C1d step steer, %d MPH, %s' % (v, ('small', 'large')[n])
        t0 = S[ja].pt
        iss = [i for i in range(ja, jb) if S[i].pt >= t0 + 2.0]
        r_ss = mean(yaw_s[i] for i in iss)
        sgn = 1 if r_ss > 0 else -1
        fy = {id(s): sgn * yaw[i] for i, s in enumerate(S)}
        f = lambda s: fy[id(s)]
        R.add(g, 'steer word', abs(S[ja + 2].inp['steer'] - S[ja - 5].inp['steer']), '')
        R.add(g, 'steady yaw rate', abs(r_ss), 'deg/s')
        R.add(g, 'steady lateral', mean(S[i].speed * math.radians(abs(yaw_s[i])) for i in iss) / G, 'g')
        if abs(r_ss) < 0.05:
            # no response (a step below the steering's resolution): no timing
            for name, unit in (('yaw at 63% after', 'ms'), ('yaw at 90% after', 'ms'), ('yaw overshoot', '%'),
                               ('yaw within 10% after', 's')):
                R.add(g, name, float('nan'), unit)
            R.add(g, 'steady sideslip', mean(S[i].slip for i in iss), 'deg')
            R.add(g, 'yaw back to 10% after release', float('nan'), 'ms')
            continue
        for p in (63, 90):
            R.add(g, 'yaw at %d%% after' % p, (crossing(S, ja, f, p / 100 * abs(r_ss)) - t0) * 1000, 'ms')
        i15 = index_at(S, t0 + 1.5)
        peak = max(sgn * yaw_m[i] for i in range(ja, i15))
        R.add(g, 'yaw overshoot', (peak / abs(r_ss) - 1) * 100, '%')
        out = [i for i in range(ja, i15) if abs(sgn * yaw_m[i] / abs(r_ss) - 1) > 0.1]
        R.add(g, 'yaw within 10% after', S[out[-1]].pt - t0 if out else 0.0, 's')
        R.add(g, 'steady sideslip', mean(-sgn * S[i].slip for i in iss), 'deg')
        # release: time until the yaw rate falls to 10% of the steady value
        tr = S[jb].pt
        i_rel = next((i for i in range(jb, len(S)) if f(S[i]) < 0.1 * abs(r_ss)), None)
        R.add(g, 'yaw back to 10% after release', (S[i_rel].pt - tr) * 1000 if i_rel else float('nan'), 'ms')
        if troubled(S, ja, jb):
            R.note('%s: %s' % (g, troubled(S, ja, jb)))
        i3 = index_at(S, t0 + 3)
        P.setdefault('c1d', []).append(('%d MPH %s' % (v, ('small', 'large')[n]),
                                        [S[i].pt - t0 for i in range(ja - 10, i3)],
                                        [f(S[i]) / abs(r_ss) for i in range(ja - 10, i3)]))


def c1e(run, R, P, level, action):
    S = load(run)
    g = 'C1e corner at 60 MPH, %s, %s' % ({'mid': '0.7 g', 'lim': '0.9 g'}[level], action)
    yaw = yaw_rates(S, 0.1)
    js = steer_jumps(S)[0]
    i_c = index_at(S, S[js].pt + 2.5)
    if action == 'brake':
        ia = next(i for i in range(i_c, len(S)) if S[i].inp['brake'] > 500)
    elif action == 'lift':
        ia = next(i for i in range(i_c, len(S)) if S[i].inp['gas'] < 50)
    else:
        ia = next(i for i in range(i_c, len(S)) if S[i].inp['gas'] > 4000)
    ie = next(i for i in range(ia, len(S)) if abs(S[i].inp['steer']) < 60)
    ta = S[ia].pt
    base = [i for i in range(len(S)) if ta - 1.5 <= S[i].pt < ta]
    r0, b0 = mean(-yaw[i] for i in base), mean(S[i].slip for i in base)
    R.add(g, 'yaw before', r0, 'deg/s')
    R.add(g, 'sideslip before', b0, 'deg')
    w1 = range(ia, index_at(S, ta + 1.0))
    ipk = max(w1, key=lambda i: abs(-yaw[i] - r0))
    R.add(g, 'largest yaw change in 1 s', (-yaw[ipk] - r0) / r0 * 100, '%')
    R.add(g, 'largest sideslip in 1 s', max(S[i].slip for i in w1), 'deg')
    w2 = [i for i in range(ia, ie) if ta + 2.0 <= S[i].pt < ta + 2.5]
    R.add(g, 'yaw change after 2 s', (mean(-yaw[i] for i in w2) - r0) / r0 * 100, '%')
    R.add(g, 'speed after 2 s', mean(S[i].mph for i in w2), 'mph')
    if troubled(S, js, ie):
        R.note('%s: %s' % (g, troubled(S, js, ie)))
    P.setdefault('c1e', []).append(('%s %s' % (level, action), [S[i].pt - ta for i in range(ia - 60, ie)],
                                    [-yaw[i] for i in range(ia - 60, ie)]))


def c1f(run, R, P, v, action):
    S = load(run)
    g = 'C1f slide, %d MPH, %s' % (v, action)
    yaw = yaw_rates(S, 0.1)
    J = steer_jumps(S)
    js = J[0]
    ts = S[js].pt
    i5 = index_at(S, ts + 5)
    if action == 'brake':
        ib = next(i for i in range(js, len(S)) if S[i].inp['brake'] > 500)
        ia = next(i for i in range(ib, len(S)) if S[i].inp['brake'] < 500)
    else:
        ia = J[1] if len(J) > 1 and action != 'hold' else index_at(S, ts + 1.0)
    R.add(g, 'steer word', abs(S[js + 2].inp['steer'] - S[js - 5].inp['steer']), '')
    R.add(g, 'largest sideslip', max(S[i].slip for i in range(js, i5)), 'deg')
    R.add(g, 'largest yaw rate', max(-yaw[i] for i in range(js, i5)), 'deg/s')
    slid = max(S[i].slip for i in range(js, i5)) > 2
    if action == 'hold':
        R.add(g, 'heading change in 5 s', sum(abs(yaw[i]) * (S[i + 1].pt - S[i].pt) for i in range(js, i5)), 'deg')
        tail = [i for i in range(js, i5) if S[i].pt >= ts + 4]
        R.add(g, 'yaw rate after 4 s', mean(-yaw[i] for i in tail), 'deg/s')
        R.add(g, 'sideslip after 4 s', mean(S[i].slip for i in tail), 'deg')
    elif slid:
        ta = S[ia].pt

        def settled(i):
            return all(abs(S[k].slip) < 1 and abs(yaw[k]) < 2 for k in range(i, min(i + 30, len(S))))
        i_ok = next((i for i in range(ia, i5) if settled(i)), None)
        R.add(g, 'settled after the action (|slip| < 1, |yaw| < 2)', S[i_ok].pt - ta if i_ok else float('nan'), 's')
        R.add(g, 'sideslip overshoot after the action', -min(S[i].slip for i in range(ia, i5)), 'deg')
    R.add(g, 'speed lost in 5 s', S[js].mph - S[i5].mph, 'mph')
    if troubled(S, js, i5):
        R.note('%s: %s' % (g, troubled(S, js, i5)))
    P.setdefault('c1f', []).append(('%d %s' % (v, action), [S[i].pt - ts for i in range(js - 30, i5)],
                                    [S[i].slip for i in range(js - 30, i5)]))


def c1g(run, R, P):
    S = load(run)
    yaw = yaw_rates(S, 0.5)
    # segments of constant steering and speed after the heading control ends:
    # a sample is steady when the steering and speed match those 1 s earlier
    start = steer_jumps(S, 300)[0]
    steady = [i >= start + 60 and abs(S[i].inp['steer'] - S[i - 60].inp['steer']) < 100 and
              abs(S[i].mph - S[i - 60].mph) < 0.7 for i in range(len(S))]
    segs, a = [], None
    for i in range(start, len(S) + 1):
        if i < len(S) and steady[i]:
            a = i if a is None else a
        elif a is not None:
            segs.append((a, i))
            a = None
    for a, b in segs:
        if S[b - 1].pt - S[a].pt < 2.5:
            continue
        idx = [i for i in range(a, b) if S[i].pt > S[a].pt + 0.5 * (S[b - 1].pt - S[a].pt)]
        st = mean(S[i].inp['steer'] for i in idx)
        u = mean(S[i].speed for i in idx)
        r = mean(yaw[i] for i in idx)
        side = 'left' if st < 0 else 'right'
        g = 'C1g low speed, %s %d%%, %.0f MPH' % (side, round(abs(st) / 4092 * 100), u / 1.4666667)
        R.add(g, 'yaw rate', abs(r), 'deg/s')
        R.add(g, 'path radius from yaw rate', u / math.radians(abs(r)), 'ft')
        R.add(g, 'path radius from a circle fit', circle_radius([S[i].pos for i in idx]), 'ft')
        R.add(g, 'sideslip', mean(S[i].slip for i in idx) * (-1 if r > 0 else 1), 'deg')
        R.add(g, 'lateral', u * math.radians(abs(r)) / G, 'g')
        if troubled(S, a, b):
            R.note('%s: %s' % (g, troubled(S, a, b)))


def circle_radius(P):
    """Least-squares (Kasa) circle fit to the horizontal positions."""
    xs, zs = [p[0] for p in P], [p[2] for p in P]
    mx, mz = mean(xs), mean(zs)
    u, v = [x - mx for x in xs], [z - mz for z in zs]
    suu, svv, suv = sum(a * a for a in u), sum(b * b for b in v), sum(a * b for a, b in zip(u, v))
    suuu, svvv = sum(a ** 3 for a in u), sum(b ** 3 for b in v)
    suvv, svuu = sum(a * b * b for a, b in zip(u, v)), sum(b * a * a for a, b in zip(u, v))
    det = suu * svv - suv * suv
    if not det:
        return float('nan')
    uc = (0.5 * (suuu + suvv) * svv - 0.5 * (svvv + svuu) * suv) / det
    vc = (0.5 * (svvv + svuu) * suu - 0.5 * (suuu + suvv) * suv) / det
    return math.sqrt(uc * uc + vc * vc + (suu + svv) / len(P))


def analyse(root, get=None):
    """Metrics of the matrix in ROOT; GET(name) may supply each run instead."""
    R, P = Report(), {}
    j = get or (lambda n: os.path.join(root, n))
    c1a_auto(j('c1a-auto'), R, P)
    c1a_stick(j('c1a-stick'), R, P)
    c1b(j('c1b-full'), R, P, 'full pedal')
    c1b(j('c1b-half'), R, P, 'pedal amount 1500')
    for v in (30, 60, 90):
        c1c(j('c1c-%d' % v), R, P, v)
    for v in (30, 60, 90):
        c1d(j('c1d-%d' % v), R, P, v)
    for level in ('mid', 'lim'):
        for a in ('lift', 'brake', 'power'):
            c1e(j('c1e-%s-%s' % (level, a)), R, P, level, a)
    for v in (60, 90):
        for a in ('hold', 'release', 'counter', 'brake'):
            c1f(j('c1f-%d-%s' % (v, a)), R, P, v, a)
    c1g(j('c1g'), R, P)
    return R, P


def spread(name, runs):
    """Metrics of one manoeuvre NAME (a c_runs.sh run name) over several runs."""
    parts = name.split('-')
    fn = {'c1e': lambda r, R: c1e(r, R, {}, parts[1], parts[2]),
          'c1f': lambda r, R: c1f(r, R, {}, int(parts[1]), parts[2]),
          'c1d': lambda r, R: c1d(r, R, {}, int(parts[1]))}[parts[0]]
    rows = []
    for r in runs:
        R = Report()
        fn(r, R)
        rows.append(R.rows)
    print('| Metric | Unit | ' + ' | '.join(os.path.basename(os.path.dirname(r.rstrip('/'))) for r in runs) + ' |')
    print('|---|---|' + '---|' * len(runs))
    for k, (g, n, _, unit) in enumerate(rows[0]):
        print('| %s | %s | %s |' % (n, unit, ' | '.join(fmt(rr[k][2], unit) for rr in rows)))


# ---- output ----------------------------------------------------------------

def fmt(x, unit):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return '-'
    if unit in ('rpm', '') or abs(x) >= 100:
        return '%.0f' % x
    if unit in ('g', 's'):
        return '%.2f' % x
    return '%.1f' % x


def repeats(a, b, unit):
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        return a is b or (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b))
    ab, rel = TOL[unit]
    return abs(a - b) <= max(ab, rel * max(abs(a), abs(b)))


def report(root, rep_root=None):
    R, P = analyse(root)
    Q = analyse(rep_root)[0] if rep_root else None
    if Q and [r[:2] for r in R.rows] != [r[:2] for r in Q.rows]:
        print('repeat matrix gives different metrics:', set(r[:2] for r in R.rows) ^ set(r[:2] for r in Q.rows))
        Q = None
    group = None
    bad = 0
    for k, (g, name, val, unit) in enumerate(R.rows):
        if g != group:
            group = g
            print('\n**%s**\n' % g)
            print('| Metric | Value | Unit |' + (' Repeat | Same |' if Q else ''))
            print('|---|---|---|' + ('---|---|' if Q else ''))
        line = '| %s | %s | %s |' % (name, fmt(val, unit), unit)
        if Q:
            q = Q.rows[k][2]
            ok = repeats(val, q, unit)
            bad += not ok
            line += ' %s | %s |' % (fmt(q, unit), 'yes' if ok else '**no**')
        print(line)
    for n in R.notes:
        print('\nTrouble: ' + n)
    if Q:
        print('\n%d of %d metrics repeat within tolerance.' % (len(R.rows) - bad, len(R.rows)))
    plots(P, os.path.join(root, 'plots'))


def svg_plot(path, title, series, xlabel, ylabel, xr=None, yr=None):
    W, H, L, B, T, Rm = 640, 400, 60, 40, 30, 150
    xs = [x for _, X, _ in series for x in X]
    ys = [y for _, _, Y in series for y in Y]
    x0, x1 = xr or (min(xs), max(xs))
    y0, y1 = yr or (min(ys), max(ys))
    if x1 == x0:
        x1 = x0 + 1
    if y1 == y0:
        y1 = y0 + 1
    sx = lambda x: L + (x - x0) / (x1 - x0) * (W - L - Rm)
    sy = lambda y: H - B - (y - y0) / (y1 - y0) * (H - B - T)
    colours = ['#1f77b4', '#d62728', '#2ca02c', '#9467bd', '#ff7f0e', '#8c564b', '#e377c2', '#17becf']
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="11">' % (W, H),
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="%d" y="18" font-size="13">%s</text>' % (L, title),
           '<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#888"/>' % (L, T, W - L - Rm, H - B - T)]
    for k in range(6):
        xv, yv = x0 + (x1 - x0) * k / 5, y0 + (y1 - y0) * k / 5
        out.append('<text x="%.0f" y="%d" text-anchor="middle">%.3g</text>' % (sx(xv), H - B + 14, xv))
        out.append('<text x="%d" y="%.0f" text-anchor="end">%.3g</text>' % (L - 4, sy(yv) + 4, yv))
        out.append('<line x1="%d" x2="%d" y1="%.0f" y2="%.0f" stroke="#eee"/>' % (L, W - Rm, sy(yv), sy(yv)))
    out.append('<text x="%d" y="%d" text-anchor="middle">%s</text>' % ((L + W - Rm) / 2, H - 6, xlabel))
    out.append('<text x="14" y="%d" transform="rotate(-90 14 %d)" text-anchor="middle">%s</text>' % (H / 2, H / 2, ylabel))
    for n, (label, X, Y) in enumerate(series):
        c = colours[n % len(colours)]
        pts = ' '.join('%.1f,%.1f' % (sx(x), sy(y)) for x, y in zip(X, Y) if x0 <= x <= x1 and y0 <= y <= y1)
        out.append('<polyline fill="none" stroke="%s" stroke-width="1.2" points="%s"/>' % (c, pts))
        out.append('<text x="%d" y="%d" fill="%s">%s</text>' % (W - Rm + 10, T + 14 + 16 * n, c, label))
    out.append('</svg>')
    with open(path, 'w') as f:
        f.write('\n'.join(out))


def plots(P, d):
    os.makedirs(d, exist_ok=True)
    svg_plot(os.path.join(d, 'c1a_speed.svg'), 'C1a full throttle', P['c1a'], 'time (s)', 'MPH')
    svg_plot(os.path.join(d, 'c1c_lateral.svg'), 'C1c steady state: lateral g against steering', P['c1c'],
             'steering input word', 'lateral (g)', yr=(0, 1.3))
    svg_plot(os.path.join(d, 'c1c_slip.svg'), 'C1c sideslip against lateral g', P['c1c_slip'],
             'lateral (g)', 'nose-in angle (deg)', xr=(0, 1.3))
    svg_plot(os.path.join(d, 'c1d_yaw.svg'), 'C1d step steer: yaw rate / steady value', P['c1d'],
             'time after the step (s)', 'yaw / steady', xr=(-0.2, 1.5), yr=(-0.1, 1.6))
    svg_plot(os.path.join(d, 'c1e_yaw.svg'), 'C1e corner at 60 MPH: yaw rate', P['c1e'],
             'time after the action (s)', 'yaw (deg/s)')
    svg_plot(os.path.join(d, 'c1f_slip.svg'), 'C1f slides: sideslip', P['c1f'],
             'time after the steer step (s)', 'nose-in angle (deg)')


if __name__ == '__main__':
    if sys.argv[1] == 'spread':
        spread(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == 'trace':
        trace(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.25)
    elif sys.argv[1] == 'report':
        report(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
