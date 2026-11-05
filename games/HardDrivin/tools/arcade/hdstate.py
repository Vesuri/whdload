"""Physical state from hd.lua log rows (see ARCADE_ROMS.md, "Result block").

Exact factors from the MSP's result-block writer ($741CD0, plan step D):
- the model works in feet and model seconds; it steps by 0.004 s per tick of
  the 244.14 Hz counter, whose real period is 4.096 ms, so model time runs at
  TIME_SCALE = 0.9765625 of real time;
- position words are 40 per foot; world velocity words are 2.56 per model ft/s;
- $8DEA is 4 per model MPH of the rear wheel's surface speed.
Everything here is in real time: times from the tick count, speeds as ground
covered per real second (so real MPH = $8DEA / 4.096 while rolling).
"""
import math
from hdlog import rows, s16

TICK = 1 / 244.140625             # real seconds per tick
TIME_SCALE = 0.004 / TICK         # model seconds per real second (0.9765625)
MPH_K = 4 / TIME_SCALE            # $8DEA per real MPH (4.096)
FT = 40.0                         # position words per foot
VEL_K = TIME_SCALE / 2.56         # real ft/s per world velocity word
G = 32.174


def s32(lo, hi):
    v = lo | (hi << 16)
    return v - (1 << 32) if v & 0x80000000 else v


class State:
    """One MSP result. World axes: X, Z horizontal, Y vertical."""

    def __init__(self, r):
        x = r['res']
        self.t, self.st, self.ticks, self.raw = r['t'], r['st'], r['inp'][0xa], r
        self.inp = {'steer': s16(r['inp'][0xb]), 'clutch': s16(r['inp'][0xc]), 'brake': s16(r['inp'][0xd]),
                    'gas': s16(r['inp'][0xe]), 'gear': s16(r['inp'][0xf]), 'steer_rate': s16(r['inp'][0x19])}
        # rotation matrix rows ($8DC0..$8DD0, 16384 = 1.0); each row is a vector
        # with components in (X, Z, Y) order; row 1 is the car's forward axis
        m = [[s16(x[3 * i + j]) / 16384 for j in range(3)] for i in range(3)]
        self.side = (m[0][0], m[0][2], m[0][1])          # as (X, Y, Z)
        self.fwd = (m[1][0], m[1][2], m[1][1])
        self.up = (m[2][0], m[2][2], m[2][1])
        self.pos = (s32(x[9], x[10]) / FT, s32(x[0xb], x[0xc]) / FT, s32(x[0xd], x[0xe]) / FT)   # feet
        V = (s16(x[0xf]), s16(x[0x10]), s16(x[0x11]))
        self.vel = tuple(v * VEL_K for v in V)                                                  # ft/s
        self.mph = s16(x[0x15]) / MPH_K
        self.rpm = s16(x[0x16])
        per_gear = [s16(x[0x1a + i]) for i in range(4)]
        self.gear = per_gear.index(0) + 1 if 0 in per_gear else None
        self.rates = (s16(x[0x12]), s16(x[0x13]), s16(x[0x14]))   # $8DE4/6/8 angular rates (raw)
        self.offroad = x[0x29] == 1 or x[0x2a] == 1                 # $8E12 / $8E14
        self.squeal = s16(x[0x25])                                  # $8E0A tire noise level
        self.wheel_torque = s16(x[0x21])                            # $8E02 force feedback

    @property
    def heading(self):
        """Yaw in degrees, positive to the right (clockwise seen from above)."""
        return math.degrees(math.atan2(-self.fwd[2], self.fwd[0]))

    @property
    def speed(self):
        """Horizontal ground speed in ft/s."""
        return math.hypot(self.vel[0], self.vel[2])

    @property
    def slip(self):
        """Sideslip in degrees: velocity direction minus heading, right positive."""
        if self.speed < 1:
            return 0.0
        d = math.degrees(math.atan2(-self.vel[2], self.vel[0])) - self.heading
        return (d + 180) % 360 - 180


def states(path):
    """States with physics time .pt: the MSP steps by the tick count, and the
    count logged with one result is the step that produces the next one."""
    S = [State(r) for r in rows(path)]
    for i, s in enumerate(S):
        s.pt = S[i - 1].pt + S[i - 1].ticks * TICK if i else 0.0
    return S


def wrap(d):
    return (d + 180) % 360 - 180


def derived(S, span=0.1):
    """Yaw rate (deg/s) and lateral/longitudinal acceleration (g) by central
    differences over about SPAN seconds of physics time."""
    out = []
    j0 = 0
    for i, s in enumerate(S):
        while S[j0].pt < s.pt - span / 2:
            j0 += 1
        j1 = i
        while j1 + 1 < len(S) and S[j1 + 1].pt <= s.pt + span / 2:
            j1 += 1
        a, b = S[j0], S[j1]
        dt = b.pt - a.pt
        if dt <= 0:
            out.append(None)
            continue
        yaw = wrap(b.heading - a.heading) / dt
        ax, az = (b.vel[0] - a.vel[0]) / dt, (b.vel[2] - a.vel[2]) / dt
        f = (s.fwd[0], s.fwd[2]); n = math.hypot(*f) or 1
        # heading() puts forward at (cos h, -sin h) in (X, Z), so right is (fz, -fx)
        f = (f[0] / n, f[1] / n); r = (f[1], -f[0])
        lon = (ax * f[0] + az * f[1]) / G
        lat = (ax * r[0] + az * r[1]) / G      # positive = towards the right
        out.append({'yaw': yaw, 'lon': lon, 'lat': lat})
    return out
