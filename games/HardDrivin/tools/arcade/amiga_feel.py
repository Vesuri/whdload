"""Step C's feel table for the Amiga runs of plan step F (tools/capture_feel.py).

  amiga_feel.py trace RUN_DIR [STEP_S]                 sampled trace of one run
  amiga_feel.py report ARCADE_ROOT NAME=ROOT [NAME=ROOT...]
                                                       C's metrics: the arcade
                                                       matrix next to Amiga matrices

Each Amiga run is a list of records, one per PAL field. They become states with
the arcade's conventions (hdstate.py), so feel.py measures them with the same code:
- time: 0.02 s per field (nominal PAL, as amiga_units.py);
- position in feet at amiga_units.FT_PER_WORLD, in hdstate's axes (X, Y, Z) =
  (z, y, -x) of the Amiga's world, so heading 0 (+z) points along +X;
- heading: G($994a) / 4 degrees, right positive;
- position and heading change once per drawn frame (every 3 fields or more on
  an A500), so both are interpolated linearly between the poses captured at
  the physics returns (steps.bin; a VBL can see half a pass). The enhanced
  physics (CUSTOM1=1) advances them by the fields it has consumed, so a pose
  is timed by that count, shifted by its median lag behind real time; the
  original advances one native step per frame, so a pose is timed at the
  middle of the field in which its pass returned;
- velocity: the direction of the latest pass's movement vector
  G($991e/$9922), which the native skid holds, and the ground speed from the interpolated positions
  0.1 s either side (0.3 s for the original, which moves one native step per
  frame whatever the frame's length, so its speed over 0.1 s stutters), so MPH
  is ground speed at the E1 scale, like the arcade's;
- steering word: (X - 320) * 4096 / 320, the arcade word that E1 maps to;
- brake: 4095 while both buttons are held;
- gas: the throttle G($991c) as a pedal (0..100 to 0..4095), except while the
  plan holds a button: 4 (raise) is full gas and 1 (lower) is gas off; the
  cruise's is kept within 64..3968, so feel.py never takes it for an action.
"""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amiga_units as au   # noqa: E402
import feel                # noqa: E402

FIELD = au.FIELD
FT = au.FT_PER_WORLD
REC = 80
FMT = '>I3i3h4h2B2hh2B3h4Bh2hI2h3h2hIh'
NAMES = ('field x8 y8 z8 heading a994c a994e velocity speedo rpm gear throttle brake mouse buttons spin skid turn '
         'mvx mvy mvz mask road crash recovery fall entry t clock done phase plan_buttons cruise head roll_rate '
         'pitch_rate consumed a9944').split()
assert struct.calcsize(FMT) == REC and len(NAMES) == len(struct.unpack(FMT, bytes(REC)))
SPAN = 0.1
ORIGINAL_SPAN = 0.3
STEP = 92
STEP_FMT = '>II'


def records(run):
    b = open(os.path.join(run, 'rec.bin'), 'rb').read()
    return [dict(zip(NAMES, struct.unpack_from(FMT, b, i))) for i in range(0, len(b), REC)]


def steps(run):
    """Physics returns: race field, consumed fields and G($98fc)..G($994f)."""
    b = open(os.path.join(run, 'steps.bin'), 'rb').read()
    out = []
    for i in range(0, len(b), STEP):
        field, consumed = struct.unpack_from('>II', b, i)

        def g(addr, fmt):
            return struct.unpack_from('>' + fmt, b, i + 8 + addr - 0x98fc)[0]
        out.append(dict(field=field, consumed=consumed, x8=g(0x98fc, 'i'), z8=g(0x9904, 'i'), heading=g(0x994a, 'h'),
                        mvx=g(0x991e, 'h'), mvz=g(0x9922, 'h')))
    return out


MODEL = 80
MODEL_FMT = '>4i ii2B ii2B 8h 7h i h 3h2B'
MODEL_NAMES = ('v r dn psi fy fw fslide fpeak ry rw rslide rpeak u counts fxin brake contact fysum nf nr '
               'sd cd rwd vcr fx fybf fyr duf fxbf trear fext fxt engine pad').split()
assert struct.calcsize(MODEL_FMT) == MODEL and len(MODEL_NAMES) == len(struct.unpack(MODEL_FMT, bytes(MODEL)))


def models(run):
    """The handling model's state after each physics pass (model.bin, HDFEEL03
    slaves; one entry per steps() entry): v Q22 ft/s, r Q27 rad/s, u Q6 ft/s,
    the inputs, the axles (w Q22 ft/s while slide is set) and the outputs."""
    path = os.path.join(run, 'model.bin')
    if not os.path.exists(path):
        return []
    b = open(path, 'rb').read()
    return [dict(zip(MODEL_NAMES, struct.unpack_from(MODEL_FMT, b, i))) for i in range(0, len(b), MODEL)]


class State:
    def __init__(self, r, pt, st, speed, x, z, h, mv):
        self.r = r
        self.raw = r
        self.pt, self.st, self.t = pt, st, pt
        self.ticks = 0
        steer = (r['mouse'] - 320) * au.STEER_WORD / au.MOUSE_LOCK
        pb = r['plan_buttons']
        gas = {4: 4095, 1: 0, 5: 0}.get(pb, r['throttle'] * 4095 / 100)
        if pb == -1:
            # the cruise's gas shuts and opens fully for a field at times: not the
            # plan's lift (gas < 50) or full power (> 4000), which feel.py looks for
            gas = min(max(gas, 64), 3968)
        self.inp = {'steer': steer, 'brake': 4095 if r['buttons'] == 5 else 0, 'gas': gas, 'clutch': 0,
                    'gear': r['gear'], 'steer_rate': 0}
        self.pos = (z / 8 * FT, r['y8'] / 8 * FT, -x / 8 * FT)
        h = math.radians(h / 4)
        self.fwd = (math.cos(h), 0.0, -math.sin(h))
        c = math.atan2(mv[0], mv[1]) if any(mv) else h
        self.vel = (speed * math.cos(c), 0.0, -speed * math.sin(c))
        self.mph = speed / au.MPH
        self.rpm = r['rpm']
        self.gear = r['gear'] or None
        self.offroad = not r['road']

    @property
    def heading(self):
        return math.degrees(math.atan2(-self.fwd[2], self.fwd[0]))

    @property
    def speed(self):
        return math.hypot(self.vel[0], self.vel[2])

    @property
    def slip(self):
        if self.speed < 1:
            return 0.0
        d = math.degrees(math.atan2(-self.vel[2], self.vel[0])) - self.heading
        return (d + 180) % 360 - 180


def start_index(R):
    """The manoeuvre's start: the end of the plan's first wait, else the engine start."""
    first = next(i for i, r in enumerate(R) if r['phase'])
    # a wait's end restarts the plan clock in the field it ends
    return next((i for i in range(first + 1, len(R)) if R[i]['t'] < R[i - 1]['t']), first)


class Path:
    """Long position and unwrapped heading, linear between their changes."""

    def __init__(self, R, T, f0):
        def real(t):
            return (t['field'] - f0 + 0.5) * FIELD
        game = [t for t in T if t['consumed']]
        lag = sorted(real(t) - t['consumed'] * FIELD for t in game)[len(game) // 2] if game else 0.0
        self.t, self.p, self.mv = [0.0], [(R[0]['x8'], R[0]['z8'], R[0]['heading'])], [(0, 0)]
        turns, last = 0, R[0]['heading']
        for t in T:
            d = t['heading'] - last
            turns += -1440 if d > 720 else 1440 if d < -720 else 0
            last = t['heading']
            when = t['consumed'] * FIELD + lag if t['consumed'] else real(t)
            self.t.append(max(when, self.t[-1] + 1e-6))
            self.p.append((t['x8'], t['z8'], t['heading'] + turns))
            self.mv.append((t['mvx'], t['mvz']))
        self.k = 0

    def movement(self, t):
        """The movement vector of the latest pass at time t."""
        k = self.k
        while k + 1 < len(self.t) and self.t[k + 1] <= t:
            k += 1
        return self.mv[k]

    def at(self, t):
        T = self.t
        if t <= T[0]:
            return self.p[0]
        if t >= T[-1]:
            return self.p[-1]
        k = self.k if self.k + 1 < len(T) and T[self.k] <= t else 0
        while T[k + 1] < t:
            k += 1
        self.k = k
        f = (t - T[k]) / (T[k + 1] - T[k])
        return tuple(a + (b - a) * f for a, b in zip(self.p[k], self.p[k + 1]))


def states(run):
    R = records(run)
    f0 = R[0]['field']
    pts = [(r['field'] - f0) * FIELD for r in R]
    i0 = start_index(R)
    T = steps(run)
    path = Path(R, T, f0)
    span = SPAN if any(t['consumed'] for t in T) else ORIGINAL_SPAN
    out = []
    for i, r in enumerate(R):
        a, b = max(pts[0], pts[i] - span), min(pts[-1], pts[i] + span)
        (xa, za, _), (xb, zb, _) = path.at(a), path.at(b)
        speed = math.hypot(xb - xa, zb - za) / 8 * FT / (b - a) if b > a else 0.0
        x, z, h = path.at(pts[i])
        out.append(State(r, pts[i], pts[i] - pts[i0] + feel.APPROACH_END + 1e-6, speed, x, z, h,
                         path.movement(pts[i])))
    return out


def trouble(S, i):
    s = S[i]
    if not isinstance(s, State):
        return arcade_trouble(S, i)
    r = s.r
    why = []
    if abs(s.pos[1]) > 1:
        why.append('height')
    if r['mask'] != 15 and i and S[i - 1].r['mask'] != 15:
        why.append('contact')         # one field of a partial mask is mid-pass
    if r['crash'] or r['recovery']:
        why.append('crash')
    if i and math.dist(S[i - 1].pos, s.pos) > 1 + S[i - 1].speed * (s.pt - S[i - 1].pt) * 3:
        why.append('jump')
    return ','.join(why)


arcade_trouble = feel.trouble
feel.trouble = trouble          # feel's metrics flag trouble through this


def c1a_auto(S, R, P):
    """feel.c1a_auto from the Amiga's launch: the plan starts with the car at rest."""
    g = 'C1a automatic'
    i0 = next(i for i, s in enumerate(S) if s.r['plan_buttons'] == 4)
    i_off = next(i for i in range(i0, len(S)) if S[i].r['plan_buttons'] == 1)
    t0 = S[i0].pt
    for v in (30, 60, 100):
        c = feel.crossing(S, i0, lambda s: s.mph, v)
        R.add(g, '0-%d MPH' % v, c - t0 if c is not None else float('nan'), 's')
    i1 = feel.index_at(S, t0 + 1.0)
    R.add(g, 'launch, first 1 s', (S[i1].mph - S[i0].mph) / (S[i1].pt - t0) * feel.MPH_S_TO_G, 'g')
    for i in range(i0 + 1, i_off):
        if S[i].gear and S[i - 1].gear and S[i].gear > S[i - 1].gear:
            R.add(g, 'shift %d-%d at' % (S[i - 1].gear, S[i].gear), S[i - 1].mph, 'mph')
            R.add(g, 'shift %d-%d rpm' % (S[i - 1].gear, S[i].gear), S[i - 1].rpm, 'rpm')
    R.add(g, 'top speed (50 s full throttle)', max(s.mph for s in S[i0:i_off]), 'mph')
    feel.coast(S, i_off, len(S), g, 'coast in gear', R)
    if feel.troubled(S, i0, len(S)):
        R.note('%s: %s' % (g, feel.troubled(S, i0, len(S))))


def c1g(S, R, P):
    """feel.c1g with the segments the plan commands (constant mouse X and cruise
    target, at least 5 s), measured over their second half: at 5 MPH the native
    throttle (2 per step) and the whole-MPH speedometer let the speed wobble by
    about 1.5 MPH, which feel.c1g's steadiness test rejects. The label's speed
    is the cruise target, except that the original build's C1g holds 8 MPH
    (its idle speed) for C's 5 MPH segments; the speed row says what it was."""
    yaw = feel.yaw_rates(S, 0.5)
    start = next(i for i in range(1, len(S)) if S[i].st > feel.APPROACH_END)
    segs, a = [], start
    for i in range(start + 1, len(S) + 1):
        if i == len(S) or (S[i].r['mouse'], S[i].r['cruise']) != (S[a].r['mouse'], S[a].r['cruise']):
            segs.append((a, i))
            a = i
    for a, b in segs:
        if S[b - 1].pt - S[a].pt < 5 or S[a].r['mouse'] == 320 or not S[a].r['cruise']:
            continue
        idx = [i for i in range(a, b) if S[i].pt > S[a].pt + 0.5 * (S[b - 1].pt - S[a].pt)]
        st = feel.mean(S[i].inp['steer'] for i in idx)
        u = feel.mean(S[i].speed for i in idx)
        r = feel.mean(yaw[i] for i in idx)
        side = 'left' if st < 0 else 'right'
        nominal = 5 if S[a].r['cruise'] < 10 else S[a].r['cruise']
        g = 'C1g low speed, %s %d%%, %d MPH' % (side, round(abs(st) / 4092 * 100), nominal)
        R.add(g, 'yaw rate', abs(r), 'deg/s')
        R.add(g, 'path radius from yaw rate', u / math.radians(abs(r)), 'ft')
        R.add(g, 'path radius from a circle fit', feel.circle_radius([S[i].pos for i in idx]), 'ft')
        R.add(g, 'sideslip', feel.mean(S[i].slip for i in idx) * (-1 if r > 0 else 1), 'deg')
        R.add(g, 'lateral', u * math.radians(abs(r)) / feel.G, 'g')
        R.add(g, 'speed', u / au.MPH, 'mph')
        if feel.troubled(S, a, b):
            R.note('%s: %s' % (g, feel.troubled(S, a, b)))


def relabel(R, fn, group):
    """Run fn into a report of its own and add its rows under GROUP."""
    T = feel.Report()
    fn(T)
    for g, n, v, u in T.rows:
        R.add(group + g[g.rindex(','):], n, v, u)
    R.notes.extend(T.notes)


def analyse(root):
    """C's metrics for the Amiga matrix in ROOT; runs that fail are noted."""
    R, P = feel.Report(), {}

    def run(name, fn):
        path = os.path.join(root, name)
        if not os.path.exists(os.path.join(path, 'rec.bin')):
            R.note('%s: no run' % name)
            return
        S = states(path)
        if S[-1].r['done'] != 1:
            R.note('%s: ended with code %d at field %d' % (name, S[-1].r['done'], S[-1].r['field']))
        try:
            fn(S)
        except (ValueError, ZeroDivisionError, StopIteration, IndexError, TypeError) as e:
            R.note('%s: %s %s' % (name, type(e).__name__, e))
    run('c1a-auto', lambda S: c1a_auto(S, R, P))
    run('c1b-full', lambda S: feel.c1b(S, R, P, 'full pedal'))
    for v in (30, 60, 90):
        run('c1c-%d' % v, lambda S, v=v: feel.c1c(S, R, P, v))
    for v in (30, 60, 90):
        run('c1d-%d' % v, lambda S, v=v: feel.c1d(S, R, P, v))
    for level in ('mid', 'lim'):
        for a in ('lift', 'brake', 'power'):
            run('c1e-%s-%s' % (level, a), lambda S, level=level, a=a: feel.c1e(S, R, P, level, a))
    for v in (60, 90):
        for a in ('hold', 'release', 'counter', 'brake'):
            run('c1f-%d-%s' % (v, a), lambda S, v=v, a=a: feel.c1f(S, R, P, v, a))
    run('c1g', lambda S: c1g(S, R, P))
    for a in ('lift', 'brake', 'power'):
        run('c1ex-lim-%s' % a, lambda S, a=a: relabel(R, lambda T: feel.c1e(S, T, P, 'lim', a),
                                                       'C1e corner at 60 MPH, Amiga limit (native steer 6)'))
    for a in ('hold', 'release', 'counter'):
        run('c1fx-90-%s' % a, lambda S, a=a: relabel(R, lambda T: feel.c1f(S, T, P, 90, a),
                                                      'C1f native skid, 90 MPH, half lock'))
    return R, P


def report(arcade_root, columns):
    A = feel.analyse(arcade_root)[0]
    M = [(name, analyse(root)[0]) for name, root in columns]
    groups = {}                   # group: metric names, the arcade's first
    for Rr in [A] + [m for _, m in M]:
        for g, n, _, _ in Rr.rows:
            names = groups.setdefault(g, [])
            if n not in names:
                names.append(n)
    rows = [(g, n) for g, names in groups.items() for n in names]
    units = {(g, n): u for _, Rr in [('', A)] + M for g, n, _, u in Rr.rows}
    vals = [{(g, n): v for g, n, v, _ in R.rows} for R in [A] + [m for _, m in M]]
    group = None
    for g, n in rows:
        if g != group:
            group = g
            print('\n**%s**\n' % g)
            print('| Metric | Arcade | %s | Unit |' % ' | '.join(name for name, _ in M))
            print('|---|---|%s---|' % ('---|' * len(M)))
        u = units[(g, n)]
        print('| %s | %s | %s |' % (n, ' | '.join(feel.fmt(v.get((g, n)), u) for v in vals), u))
    for name, R in M:
        for note in R.notes:
            print('\n%s: %s' % (name, note))


def trace(run, step=0.25):
    S = states(run)
    D = feel.derived(S)
    nxt = S[0].pt
    print('    pt    st   mph speedo  v  thr g  head  slip   yaw   lat   lon     X      Z   X-320 btn skid spin entry trouble')
    for i, (s, d) in enumerate(zip(S, D)):
        tr = trouble(S, i)
        if s.pt < nxt and not tr:
            continue
        nxt = s.pt + step
        d = d or {'yaw': 0, 'lat': 0, 'lon': 0}
        r = s.r
        print('%6.2f %5.1f %5.1f %4d %4d %3d %s %6.1f %5.1f %5.1f %5.2f %5.2f %6.0f %6.0f %5d %3d %4d %4d %3d %s' % (
            s.pt, s.st, s.mph, r['speedo'], r['velocity'], r['throttle'], r['gear'], s.heading, s.slip, d['yaw'],
            d['lat'], d['lon'], s.pos[0], s.pos[2], r['mouse'] - 320, r['buttons'], r['skid'], r['spin'],
            r['entry'], tr))


if __name__ == '__main__':
    if sys.argv[1] == 'trace':
        trace(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.25)
    elif sys.argv[1] == 'report':
        report(sys.argv[2], [a.split('=', 1) for a in sys.argv[3:]])
