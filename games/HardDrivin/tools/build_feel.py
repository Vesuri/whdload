"""Build the plan step F fixture slaves: build_feel.py [--slow] [--source DIR --pad N --prefix P] [NAME...] (default all).

Each NAME is a step C manoeuvre (tools/arcade/mame/c_runs.sh) driven on the
Amiga by tools/feel_fixture.s. The slave goes to tmp/build/feel-NAME.slave, built
from a copy of the current source (the release feature set) with VERIFY_DRIVE
and VERIFY_STEPINPUT, the fixture's hooks and the plan. --slow also builds
tmp/build/feel-slow-NAME.slave with VERIFY_SLOW, whose CUSTOM4=N adds N fields
to every frame: the original build steps once per frame, and this ground
draws far faster than a race. The slow C1g runs at 8 MPH instead of 5. Run from the game directory with
tools/env.sh sourced.

The plans follow C's schedules, mapped to the Amiga's native controls:
- steering: the arcade wheel offset (raw ADC, full lock 0x7f0) becomes mouse
  X - 320 for the steer word the arcade read in C's runs, 2 * offset - 10, at
  4096 words to 320 counts; full lock is full lock (E1 used offset * 320 / 2032);
- gas: the throttle buttons. The Amiga's throttle moves by 2 per native step,
  so lifting is holding button 1 and full power is holding button 4;
- brake: both buttons. The brake is on or off, so C1b's half-pedal run and
  C1e's half-pedal brake use the full brake (C1e) or are left out (C1b);
- C's 25 MPH approach turn is replaced by the start position on the open
  grass north of the start straight; each manoeuvre starts when the speed and
  heading have settled, instead of at a fixed time;
- that ground is about 24,000 units (8,200 ft) long, so C1a holds full
  throttle for 30 s instead of 50 and coasts until the ground ends;
- C1a's stick-shift run is left out (powertrain, not handling).

Two Amiga-only sets, because E1's mapping keeps C1e and C1f far below what the
native car does at its limits:
- c1ex-lim-ACTION: C1e at 60 MPH with 120 counts (native steer 6, the largest
  turn at 60 MPH that the native code does not halve, about 0.45 g);
- c1fx-90-ACTION: C1f at 90 MPH with half lock (160 counts, native steer 8),
  which starts the native skid (it needs a steering force above 2,000, which
  E1's 94 counts at 90 MPH do not reach).

Plan step H2's laps of the real course (lap-ROUTE, see ROUTES): the car stays
at the native start and the ground keeps its off-road rules; the fixture's
FE_FOLLOW drives the route by pure pursuit and holds each point's speed.
The route runs through the centres of the road sections in
tmp/track-geometry.json (tools/inspect_track_geometry.py), every 50 units.
The speed is the lowest of: the route's cruise speed, or a section's own
(the jump and the loop need speed: full throttle, as the native throttle
rises only 2% per native step); 0.9 g of cornering on the route's
curvature (each section corner's angle over the mean of its two sides);
and what braking at 0.35 g from there allows. The loop's sections turn in
the vertical, so their curvature does not count, and the driver holds the
wheel straight there (bit 15 of the point's speed): their centres move
sideways as the loop spirals, and chasing them puts the car into the loop
at an angle (see ARCADE_HANDLING_PLAN.md, H2).
"""
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
SOURCE = ROOT / 'src'
TOOLS = ROOT / 'tools'
WORK = ROOT / 'tmp/feel-source'
BUILD = ROOT / 'tmp/build'
SEED_X, SEED_Z = 23500, 29500
# the ground the car may use (see feel_fixture.s): east of the course road at
# x 22,300, north of the start area's objects, within about 10,000 units of
# the flat start straight and its curves
BOUNDS = dict(X_MIN=22800, X_MAX=47000, Z_MIN=26800, Z_MAX=35500)
OPS = {'end': 0, 'cruise': 1, 'head': 2, 'mouse': 3, 'ramp': 4, 'buttons': 5, 'settle': 6, 'stop': 7, 'follow': 8}
LOWER, RAISE, BRAKE = 1, 4, 5


def counts(raw):
    """Mouse X - 320 for an arcade wheel offset: the steer word the arcade
    reads for it in C's MAME runs, 2 |raw| - 10 (E1's raw * 320 / 2032
    steered 2-7% more), at 4096 words to 320 counts."""
    if not raw:
        return 0
    if abs(raw) >= 2032:
        return 320 if raw > 0 else -320    # full lock reads 4092
    word = 2 * abs(raw) - 10
    return round(word * 320 / 4096) * (1 if raw > 0 else -1)


def f(seconds):
    return round(seconds * 50)


def cruise_to(v):
    # settled for 3 s, or give up after 15 s
    return [(0, 'head', 1), (0, 'cruise', v), (0, 'settle', 150, f(15))]


def c1a_auto():
    return [(0, 'head', 1), (f(1), 'buttons', RAISE), (f(31), 'buttons', LOWER), (f(91), 'end')]


def c1b_full():
    stop = [(0, 'cruise', 0), (0, 'buttons', BRAKE), (0, 'stop', 25), (0, 'buttons', -1)]
    return cruise_to(60) + stop + cruise_to(100) + stop + [(f(1), 'end')]


def c1c(v, lock):
    full = counts(2048 - int(2048 - 2032 * lock))
    return cruise_to(v) + [(0, 'head', 0), (f(0.1), 'ramp', -full, f(16)), (f(16.5), 'mouse', 0), (f(18), 'end')]


def c1d(v, small, large):
    return cruise_to(v) + [(0, 'head', 0), (f(1), 'mouse', -counts(small)), (f(4), 'mouse', 0),
                           (f(7), 'mouse', -counts(large)), (f(10), 'mouse', 0), (f(13), 'end')]


def c1e(wheel, action):
    act = {'lift': LOWER, 'brake': BRAKE, 'power': RAISE}[action]
    return cruise_to(60) + [(0, 'head', 0), (f(0.1), 'mouse', -counts(wheel)), (f(4.5), 'cruise', 0),
                            (f(4.5), 'buttons', act), (f(7.5), 'mouse', 0), (f(7.5), 'buttons', LOWER), (f(9), 'end')]


def c1f(v, wheel, action, brake=False):
    t1 = f(0.5 + 1)
    e = [(0, 'head', 0), (f(0.5), 'mouse', -counts(wheel))]
    if brake:
        e += [(f(0.5), 'cruise', 0), (f(0.5), 'buttons', BRAKE), (t1, 'buttons', LOWER)]
    if action == 'counter':
        e += [(t1, 'mouse', counts(wheel // 2)), (t1 + f(1), 'mouse', 0)]
    elif action == 'release':
        e += [(t1, 'mouse', 0)]
    # the driver runs entries in order, so they must be in time order
    return cruise_to(v) + sorted(e, key=lambda x: x[0]) + [(f(7), 'end')]


def c1g(low=5):
    def left(frac):
        return -counts(2048 - int(2048 - 2032 * frac))
    return cruise_to(low) + [(0, 'head', 0), (f(0.1), 'mouse', left(0.25)), (f(10), 'mouse', left(0.5)),
                             (f(20), 'mouse', left(0.75)), (f(30), 'mouse', -counts(2032)), (f(45), 'cruise', 10),
                             (f(57), 'cruise', 15), (f(69), 'cruise', low), (f(69), 'mouse', counts(2032)),
                             (f(84), 'end')]


PLANS = {
    'c1a-auto': c1a_auto(),
    'c1b-full': c1b_full(),
    'c1c-30': c1c(30, 0.5), 'c1c-60': c1c(60, 0.3), 'c1c-90': c1c(90, 0.2),
    'c1d-30': c1d(30, 250, 650), 'c1d-60': c1d(60, 105, 260), 'c1d-90': c1d(90, 80, 235),
}
for level, wheel in (('mid', 180), ('lim', 240)):
    for action in ('lift', 'brake', 'power'):
        PLANS['c1e-%s-%s' % (level, action)] = c1e(wheel, action)
for v, wheel in ((60, 650), (90, 600)):
    for action in ('counter', 'hold', 'release'):
        PLANS['c1f-%d-%s' % (v, action)] = c1f(v, wheel, action)
PLANS['c1f-60-brake'] = c1f(60, 260, 'release', brake=True)
PLANS['c1f-90-brake'] = c1f(90, 235, 'release', brake=True)
PLANS['c1g'] = c1g()
# The user (2026-11-04): "test the rear end getting loose while coasting
# and steering". C1h: cruise, then shut the gas and turn at once, held
# (MAME plans/c1h_coast.lua; the mouse's gas lifts at its own rate).
for v, wheel in ((40, 350), (40, 650), (60, 200), (60, 380)):
    PLANS['c1h-%d-%d' % (v, wheel)] = cruise_to(v) + [(0, 'head', 0), (f(0.5), 'mouse', -counts(wheel)),
                                                      (f(0.5), 'cruise', 0), (f(0.5), 'buttons', LOWER),
                                                      (f(7.5), 'end')]
# The user (2026-10-23): "even on the first gear the car is really lazy to
# accelerate on low RPMs". The arcade's c1e-mid-power run floors it at 25 MPH
# in 1st (3,040 rpm): 25 to 47.6 MPH in 2.5 s.
for v in (15, 25):
    PLANS['rollon-%d' % v] = cruise_to(v) + [(0, 'head', 0), (f(0.1), 'buttons', RAISE), (f(5), 'buttons', LOWER),
                                             (f(6), 'end')]
# The original build cannot hold 5 MPH: in first gear its velocity is either
# about 9 (2.5 MPH, 350 rpm) or about 28 (7.8 MPH, idle at 800 rpm). Its C1g
# runs at the idle speed.
SLOW_PLANS = {'c1g': c1g(8)}
for action in ('lift', 'brake', 'power'):
    PLANS['c1ex-lim-%s' % action] = c1e(762, action)
for action in ('counter', 'hold', 'release'):
    PLANS['c1fx-90-%s' % action] = c1f(90, 1016, action)
# Plan step H2's cost case: braking in a turn from 100 MPH, so that the
# locked front wheel takes the model's longest path (a sliding wheel) for
# several seconds.
PLANS['h2-brake-turn'] = cruise_to(100) + [(0, 'head', 0), (f(0.5), 'mouse', -100), (f(0.5), 'cruise', 0),
                                          (f(0.5), 'buttons', BRAKE), (f(12), 'buttons', LOWER), (f(13), 'end')]
# Plan step H3's runaway spin (the user's drive, 2026-10-21): full throttle
# and full lock until the car slides, then full or half countersteer, or the
# wheel centred, for 3 s, the throttle still held.
def h3_spin(v, after):
    t1 = f(0.5 + 1.5)
    back = {'counter': 319, 'half': 160, 'centre': 0}[after]
    return cruise_to(v) + [(0, 'head', 0), (f(0.5), 'cruise', 0), (f(0.5), 'buttons', RAISE),
                           (f(0.5), 'mouse', -320), (t1, 'mouse', back), (t1 + f(3), 'mouse', 0), (f(9), 'end')]


for v in (60, 90):
    for after in ('counter', 'half', 'centre'):
        PLANS['h3-spin-%d-%s' % (v, after)] = h3_spin(v, after)
for route in ('main', 'stunt', 'jump', 'loop', 'offroad', 'slow'):     # ROUTES, below
    PLANS['lap-' + route] = [(0, 'follow', 1), (32000, 'end')]
# Plan step H3 round 2 (the user's drive, 2026-10-22): a spin at 100 MPH in
# the long right curve after the bridge, which then went off the road and
# rolled the car over. The driver follows the curve route for 1 s, then
# steers full right for 0.5 s with full throttle, then centres, countersteers
# or holds half lock.
ROUTE_OF = {}


def h3_curve(after):
    t1, t2 = f(1), f(1.5)
    e = [(0, 'follow', 1), (t1, 'follow', 0), (t1, 'buttons', RAISE), (t1, 'mouse', 320)]
    if after == 'counter':
        e += [(t2, 'mouse', -320), (t2 + f(0.7), 'mouse', 0)]
    elif after == 'hold':
        e += [(t2, 'mouse', 160), (t2 + f(3), 'mouse', 0)]
    else:
        e += [(t2, 'mouse', 0)]
    return e + [(f(12), 'end')]


for after in ('centre', 'counter', 'hold'):
    PLANS['h3-curve-' + after] = h3_curve(after)
    ROUTE_OF['h3-curve-' + after] = 'curve'
# The same round's roll-over on slopes: on the stunt road's banked curve
# (46 degrees of roll), follow it for 0.5 s at 40 MPH, then full lock
# (right, up the bank, or left, down it) with full throttle for 4 s, then
# centre: the car circles on the slope.
def h3_bank(mouse):
    t1 = f(0.5)
    return [(0, 'follow', 1), (t1, 'follow', 0), (t1, 'buttons', RAISE), (t1, 'mouse', mouse),
            (t1 + f(4), 'mouse', 0), (f(9), 'end')]


for v in (30, 40, 60, 75, 90):
    PLANS['h3-bankf-%d' % v] = [(0, 'follow', 1), (f(16), 'end')]
    ROUTE_OF['h3-bankf-%d' % v] = 'bankf-%d' % v
for side, mouse in (('right', 320), ('left', -320)):
    PLANS['h3-bank-' + side] = h3_bank(mouse)
    ROUTE_OF['h3-bank-' + side] = 'bank'
    # at 15 MPH under cruise control the car circles on the bank, wheels down
    PLANS['h3-bank-slow-' + side] = [(0, 'follow', 1), (f(0.5), 'follow', 0), (f(0.5), 'cruise', 15),
                                    (f(0.5), 'mouse', mouse), (f(6.5), 'mouse', 0), (f(9), 'end')]
    ROUTE_OF['h3-bank-slow-' + side] = 'bank-slow'
# A spin on the main road's slopes, as in the drive: the hill (3.5 degrees)
# and the dip (5.3 degrees) on the way back to the start, at 60 MPH: follow
# 0.5 s, then full right lock with full throttle for 2 s, then centre.
for v in (50, 60, 70, 80, 90, 100, 110):
    PLANS['h3-ramp-%d' % v] = [(0, 'follow', 1), (f(12), 'end')]
    ROUTE_OF['h3-ramp-%d' % v] = 'ramp-%d' % v
# The user's drive of r26 (2026-11-02, recording at 2:28): the first ramp at
# about 65 MPH near the centre line, between the car parked on the left
# and the oncoming truck on the right, holding the speed;
# the nose rose into the sky past the lip and stayed there for 12 s.
for v in (60, 65, 70):
    PLANS['h3-rampr-%d' % v] = [(0, 'follow', 1), (f(16), 'end')]
    ROUTE_OF['h3-rampr-%d' % v] = 'rampr-%d' % v
# The same at 65 MPH further left (the recording's OFF ROAD came while the
# car flew beside the far half of the bridge).
for lane in (60, 70, 80, 90, 110):
    PLANS['h3-rampl-%d' % lane] = [(0, 'follow', 1), (f(16), 'end')]
    ROUTE_OF['h3-rampl-%d' % lane] = 'rampl-%d' % lane
# The stunt road's underpass (sections 61-68 dip 46 units under the main
# road; the user's drive of r26 crashed "with the bridge" there), from a
# seeded start on section 57 at 60 to 120 MPH, following the road.
for v in (60, 80, 100, 105, 110, 120):
    PLANS['h3-under-%d' % v] = [(0, 'follow', 1), (f(8), 'end')]
    ROUTE_OF['h3-under-%d' % v] = 'under-%d' % v
# The same from section 61, past the curve before the dip, at 80 to 130 MPH.
for v in (80, 100, 105, 110, 115, 130):
    PLANS['h3-dip-%d' % v] = [(0, 'follow', 1), (f(5), 'end')]
    ROUTE_OF['h3-dip-%d' % v] = 'sdip-%d' % v
# The user's drive of r32 (2026-11-03, recording 09.09.10 at 1:17): through the
# dip at 105-110 MPH, crashing on the climb out past the bridge; the same
# from section 61 left and right of the centre line.
for v in (105, 110):
    for lane in (-60, -30, 30, 60):
        PLANS['h3-dipl-%d-%d' % (v, lane)] = [(0, 'follow', 1), (f(6), 'end')]
        ROUTE_OF['h3-dipl-%d-%d' % (v, lane)] = 'sdipl-%d-%d' % (v, lane)
for slope in ('hill', 'dip'):
    PLANS['h3-%s-spin' % slope] = [(0, 'follow', 1), (f(0.5), 'follow', 0), (f(0.5), 'buttons', RAISE),
                                   (f(0.5), 'mouse', 320), (f(2.5), 'mouse', 0), (f(9), 'end')]
    ROUTE_OF['h3-%s-spin' % slope] = slope
# Round 1's roll-over (tmp/prof/i-hang-probe, lap-stunt at field 8150): on
# the grass south of the bridge at 55 MPH with the throttle held, full left
# lock, then the follower's steering, full right lock and full left lock as
# that run had them. The car climbed a raised edge and rolled over while
# spinning at 60-106 deg/s.
PLANS['h3-rollover'] = [(0, 'buttons', RAISE), (0, 'mouse', -320), (43, 'mouse', -35), (73, 'mouse', -29),
                        (95, 'mouse', -15), (118, 'mouse', 0), (143, 'mouse', 15), (161, 'mouse', 30),
                        (167, 'mouse', 319), (211, 'mouse', -320), (232, 'mouse', -31), (f(9), 'end')]
ROUTE_OF['h3-rollover'] = 'rollover'
# The user's braking (2026-10-22: "it takes forever to get the speed down"):
# full throttle from rest to about 60 or 100 MPH, then both buttons until the
# car stands still. The throttle is still open when the brake goes on.
for v, t in ((60, f(3.5)), (100, f(8))):
    PLANS['h3-brake-floor-%d' % v] = [(0, 'head', 1), (f(1), 'buttons', RAISE), (t, 'buttons', BRAKE),
                                      (t, 'stop', 25), (0, 'buttons', -1), (f(1), 'end')]


# Laps (plan step H2): (road, first section, last section) pieces, and
# speeds: the cruise speed, and (road, first, last, MPH) for sections that
# need more. The stunt road leaves the main road on the bridge at its
# section 12 and joins it again at section 149; its first and last sections
# lie a few units behind those, so the route skips them.
ROUTES = {
    'main': dict(pieces=[('main', 0, 150), ('main', 0, 6)], cruise=85, fast=[]),
    'stunt': dict(pieces=[('main', 0, 11), ('stunt', 0, 121), ('main', 150, 150), ('main', 0, 6)], cruise=80,
                  fast=[('stunt', 6, 24, 125), ('stunt', 33, 52, 125)]),
}
# The stunt route from a seeded start at 112 MPH (velocity 400): before the
# jump, and before the loop. Segment, next waypoint and speed as the step 4
# course probes seeded them (build_c4_geometry_probe.py), which landed the
# jump at that speed.
# A vehicle stands on the jump ramp's centre line; the probes' clear seed
# ran about 70 units left of it, so this route keeps to that lane.
ROUTES['jump'] = dict(ROUTES['stunt'], seed=('stunt', 13, 2, 400), lane=-70)
ROUTES['loop'] = dict(ROUTES['stunt'], seed=('stunt', 33, 4, 400))
# Off the road: parallel to the main road's start, 350 units to its right
# (the road is about 230 wide), on the grass with its native rules.
ROUTES['offroad'] = dict(pieces=[('main', 0, 45)], cruise=60, fast=[], lane=350)
# The main road slowly enough that arcade race timing (CUSTOM5=1) runs out
# before the checkpoint.
ROUTES['slow'] = dict(ROUTES['main'], cruise=55)
# The long right curve after the bridge, from a seeded start at 100 MPH
# (velocity 357) on the straight just before it (h3-curve-*).
ROUTES['curve'] = dict(pieces=[('main', 20, 60)], cruise=100, fast=[], seed=('main', 20, 0, 357))
# The stunt road's banked curve at 40 MPH (velocity 143), from its section 79
# (h3-bank-*).
ROUTES['bank'] = dict(pieces=[('stunt', 78, 90)], cruise=40, fast=[], seed=('stunt', 79, 6, 143))
ROUTES['bank-slow'] = dict(ROUTES['bank'], cruise=15, seed=('stunt', 80, 6, 54))
# The user's drive of r32 (recording 09.09.10 at 1:52-2:05): onto the bank at
# about 75 MPH, off its low side, and back on it at 20-40 MPH (h3-bankf-*).
for v in (30, 40, 60, 75, 90):
    ROUTES['bankf-%d' % v] = dict(pieces=[('stunt', 68, 94)], cruise=v, fast=[], seed=('stunt', 69, 2, round(v * 3.57)))
# The main road's hill and dip on the way back, at 60 MPH (velocity 214)
# (h3-hill-spin, h3-dip-spin).
ROUTES['hill'] = dict(pieces=[('main', 72, 90)], cruise=60, fast=[], seed=('main', 74, 0, 214))
ROUTES['dip'] = dict(pieces=[('main', 66, 80)], cruise=60, fast=[], seed=('main', 67, 0, 214))
# The stunt road's first ramp (sections 17-19, 9 degrees up to the lip at
# section 20), from a seeded start on section 13 at 50 to 110 MPH, 40
# units left of the centre line (a vehicle stands on it), under full
# throttle (h3-ramp-*, the user's drive of round 11).
for v in (50, 60, 70, 80, 90, 100, 110):
    ROUTES['ramp-%d' % v] = dict(pieces=[('stunt', 12, 40)], cruise=140, fast=[], lane=-40,
                                 seed=('stunt', 13, 2, round(v * 3.57)))
for v in (60, 65, 70):
    ROUTES['rampr-%d' % v] = dict(pieces=[('stunt', 12, 40)], cruise=v, fast=[], lane=-15,
                                  seed=('stunt', 13, 2, round(v * 3.57)))
for lane in (60, 70, 80, 90, 110):
    ROUTES['rampl-%d' % lane] = dict(ROUTES['rampr-65'], lane=-lane)
for v in (60, 80, 100, 105, 110, 120):
    ROUTES['under-%d' % v] = dict(pieces=[('stunt', 56, 80)], cruise=v, fast=[], seed=('stunt', 57, 2, round(v * 3.57)))
for v in (80, 100, 105, 110, 115, 130):
    ROUTES['sdip-%d' % v] = dict(pieces=[('stunt', 60, 80)], cruise=v, fast=[], seed=('stunt', 61, 2, round(v * 3.57)))
for v in (105, 110):
    for lane in (-60, -30, 30, 60):
        ROUTES['sdipl-%d-%d' % (v, lane)] = dict(ROUTES['sdip-%d' % v], lane=lane)
# A seed at a given place (h3-rollover): X, Y, Z, heading and velocity, with
# the road cursor on a main road section nearby.
ROUTES['rollover'] = dict(pieces=[('main', 14, 22)], cruise=55, fast=[],
                          at=dict(X=-31484, Y=1, Z=22745, HEAD=-18, V=199, MAIN=1, SEGMENT=17))
# A world unit is 0.1791 ft: the arcade road's 41.2 ft over the Amiga road's
# 230 units (amiga_units.py; E1 first took 0.3504 from the speedometer).
FT_PER_UNIT = 0.1791
LOOP = ('stunt', 37, 49)
SPACING = 50
GEOMETRY = Path(__file__).resolve().parents[1] / 'tmp/track-geometry.json'


def route_points(route):
    """(x, y, z, MPH, road, section) every SPACING units along a route, x
    unwrapped (the course's words wrap at 32768)."""
    g = json.loads(GEOMETRY.read_text())
    r = ROUTES[route]
    centres, prev = [], None
    for road, first, last in r['pieces']:
        for i in range(first, last + 1):
            row = g[road][i]
            c = []
            for a in range(3):
                lo, hi = row['left'][a], row['right'][a]
                if abs(lo - hi) > 32768:
                    lo, hi = lo % 65536, hi % 65536
                c.append((lo + hi) / 2)
            if prev:
                for a in (0, 2):
                    while c[a] - prev[a] > 32768:
                        c[a] -= 65536
                    while c[a] - prev[a] < -32768:
                        c[a] += 65536
            if prev and math.dist(c, prev) < 1:
                continue
            centres.append((c, road, i))
            prev = c
    # each corner's radius in feet: its angle over the mean of its two sides
    radius = [1e9] * len(centres)
    for k in range(1, len(centres) - 1):
        a, b, c = (centres[k + d][0] for d in (-1, 0, 1))
        h0 = math.atan2(b[0] - a[0], b[2] - a[2])
        h1 = math.atan2(c[0] - b[0], c[2] - b[2])
        dh = abs((h1 - h0 + math.pi) % (2 * math.pi) - math.pi)
        loop = centres[k][1] == LOOP[0] and LOOP[1] <= centres[k][2] <= LOOP[2]
        if dh > 1e-6 and not loop:
            radius[k] = (math.dist(a, b) + math.dist(b, c)) / 2 / dh * FT_PER_UNIT
    pts, vmax = [], []
    for k, ((a, road, i), (b, _, _)) in enumerate(zip(centres, centres[1:])):
        n = max(1, round(math.dist(a, b) / SPACING))
        v = r['cruise']
        for fr, first, last, mph in r['fast']:
            if road == fr and first <= i <= last:
                v = mph
        v = min(v, math.sqrt(0.9 * 32.17 * min(radius[k], radius[k + 1])) / (5280 / 3600))
        for j in range(n):
            pts.append([a[m] + (b[m] - a[m]) * j / n for m in range(3)] + [road, i])
            vmax.append(max(30.0, v))
    pts.append(list(centres[-1][0]) + [centres[-1][1], centres[-1][2]])
    vmax.append(vmax[-1])
    # a lane: offset to the right (positive) or left of the centre line
    lane = r.get('lane', 0)
    if lane:
        moved = []
        for k, p in enumerate(pts):
            a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
            dx, dz = b[0] - a[0], b[2] - a[2]
            n = math.hypot(dx, dz) or 1
            # right of the direction (dx, dz) is (dz, -dx), as right of heading psi is (cos, -sin)
            moved.append([p[0] + lane * dz / n, p[1], p[2] - lane * dx / n] + p[3:])
        pts = moved
    for k in range(len(pts) - 2, -1, -1):
        ds = math.dist(pts[k][:3], pts[k + 1][:3]) * FT_PER_UNIT
        v1 = vmax[k + 1] * 5280 / 3600
        vmax[k] = min(vmax[k], math.sqrt(v1 * v1 + 2 * 0.35 * 32.17 * ds) / (5280 / 3600))
    return [(round(p[0]), round(p[1]), round(p[2]), round(v), p[3], p[4]) for p, v in zip(pts, vmax)]


def gain_table():
    """(k, gain) per 8 MPH: aim k points ahead, about 0.8 s plus 42 ft,
    and steer gain * offset / 256 counts: the curvature 2 e / L^2 of the arc
    to the aim point, as a wheel angle over the 10 ft wheelbase (35 degrees
    is 320 counts), times the understeer at that speed (1 + (MPH / 70)^2,
    from step C's yaw gains). The fixture scales it by (L / D)^2 for the
    real distance D to the aim point."""
    out = []
    for j in range(20):
        mph = 8 * j + 4
        # 0.8 s plus 42 ft ahead; 2 L = 111.7 units (10 ft) times 523.8
        # counts per radian of wheel angle
        k = max(3, round((42 + 1.173 * mph) / FT_PER_UNIT / SPACING))
        gain = 2 * 10 / FT_PER_UNIT * 523.8 * 256 / (k * SPACING) ** 2 * (1 + mph * mph / 4900)
        out.append((k, round(gain)))
    return out


def plan_source(plan, route=None):
    """The plan's constants (feel_plan_equ.i, included first: the fixture's
    conditionals need them) and its data (feel_plan.i, at the end)."""
    seed = dict(X=SEED_X, Y=0, Z=SEED_Z, HEAD=360, V=0, STUNT=0, MAIN=0, SEGMENT=0, WAYPOINT=0)
    start = 0
    if route:
        seed['X'] = 0
        seed.update(ROUTES[route].get('at', {}))
        if 'seed' in ROUTES[route]:
            road, segment, waypoint, v = ROUTES[route]['seed']
            row = json.loads(GEOMETRY.read_text())[road][segment]
            # the route's first point on that section (in its lane), in words
            pts = route_points(route)
            start = next(k for k, p in enumerate(pts) if p[4] == road and p[5] == segment)
            x, z = pts[start][0], pts[start][2]
            seed.update(X=(x + 32768) % 65536 - 32768, Y=pts[start][1], Z=(z + 32768) % 65536 - 32768,
                        HEAD=(row['rest'][0] + 720) % 1440 - 720, V=v, STUNT=int(road == 'stunt'),
                        MAIN=int(road == 'main'), SEGMENT=segment, WAYPOINT=waypoint)
    equ = ['; generated by build_feel.py'] + ['FEEL_SEED_%s equ %d' % kv for kv in seed.items()]
    equ += ['FEEL_START_IDX equ %d' % start]
    equ += ['FEEL_%s equ %d' % kv for kv in BOUNDS.items()]
    equ += ['FEEL_PATH equ %d' % (1 if route else 0), 'FEEL_T_MAX equ %d' % (32000 if route else 12000)]
    lines = ['; generated by build_feel.py', '\tCNOP 0,2', '_feel_plan:']
    for e in plan:
        t, op, a, b = (tuple(e) + (0, 0))[:4]
        lines.append('\tdc.w %d,%d,%d,%d\t; %s' % (t, OPS[op], a, b, op))
    if route:
        pts = route_points(route)
        gains = gain_table()
        equ += ['FEEL_PATH_N equ %d' % len(pts), 'FEEL_GAIN_N equ %d' % len(gains), 'FEEL_SPACING equ %d' % SPACING]
        lines.append('_feel_gain:')
        lines += ['\tdc.w %d,%d\t; %d MPH' % (k, g, 8 * j + 4) for j, (k, g) in enumerate(gains)]
        lines.append('_feel_path:')
        for x, y, z, v, road, i in pts:
            straight = 0x8000 if road == LOOP[0] and LOOP[1] <= i <= LOOP[2] else 0
            lines.append('\tdc.w %d,%d,%d,$%04x\t; %s %d' % ((x + 32768) % 65536 - 32768, y, (z + 32768) % 65536 - 32768,
                                                          v | straight, road, i))
    return '\n'.join(equ) + '\n', '\n'.join(lines) + '\n'


def prepare(source=SOURCE, pad=0, native_ground=False):
    """The source copy with the fixture's hooks, shared by every plan. PAD
    zero bytes after everything else make a control slave the same size as
    another build, so the game loads at the same address. NATIVE_GROUND
    (the laps) keeps the grass's native rules."""
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(source, WORK)
    if os.environ.get('FEEL_FORCE_RATE'):
        # Experiment: every rear-only contact pass sets the pitch rate (units per native step).
        q = WORK / 'HardDrivinContact.s'
        m = q.read_text()
        needle = '\tmoveq #0,d2\n\tbsr _contact_response\n\tlea _contact_rates+8(pc),a0'
        assert m.count(needle) == 1
        q.write_text(m.replace(needle, needle.replace('\tlea', '\tmove.l #%d,d1\n\tlea' % (int(os.environ['FEEL_FORCE_RATE']) * 65536)), 1))
    p = WORK / 'HardDrivinVerify.s'
    s = p.read_text(encoding='latin-1')
    constant = ('\tmove.l #(VERIFY_STEPINPUT_X<<16)|200,-$6a06(a4)\n\tIFD VERIFY_STEPINPUT_STEER_AT\n'
                '\tbsr _verify_step_delayed_steering\n\tENDC\n\tmove.w #4,-$6a0a(a4)\n')
    assert s.count(constant) == 2
    s = s.replace(constant, '\tFEEL_CALL _feel_vbl\n', 1).replace(constant, '\tFEEL_CALL _feel_input\n', 1)
    race = '\tmove.w #2,(a0)\n.done:'
    assert s.count(race) == 1
    s = s.replace(race, '\tFEEL_CALL _feel_seed\n' + race)
    # long calls to the fixture at the end of the slave, preserving every register
    s = ('FEEL_CALL MACRO\n\tmove.l a0,-(a7)\n\tlea _verify_drive_state(pc),a0\n'
         '\tadda.l #\\1-_verify_drive_state,a0\n\tjsr (a0)\n\tmovea.l (a7)+,a0\n\tENDM\n' + s +
         '\n_feel_after_tramp:\n\tFEEL_CALL _feel_after_native\n\trts\n')
    p.write_text(s, encoding='latin-1')
    shutil.copyfile(TOOLS / 'feel_fixture.s', WORK / 'feel_fixture.s')
    p = WORK / 'HardDrivinHD.s'
    s = p.read_text(encoding='latin-1')
    entry = '\tPL_PSS $10ecc,_verify_drive_race,2\n'
    assert s.count(entry) == 1
    # grass as road: no grass branch in the engine (nop for beq.s at $b762), no
    # off-road deadline (bra.s for bne.s at $b146); and the original build's
    # pass end (the enhanced dispatch replaces this patch with its own)
    grass = '' if native_ground else '\tPL_W $b762,$4e71\n\tPL_W $b146,$6040\n'
    s = s.replace(entry, entry + grass + '\tPL_PSS $10f28,_feel_after_tramp,2\n')
    s = s.rstrip('\n') + '\n\n\tIFD VERIFY_DRIVE\n\tINCLUDE "feel_fixture.s"\n\tENDC\n'
    if pad:
        s += '\tdcb.b %d,0\n' % pad
    p.write_text(s, encoding='latin-1')
    if not native_ground:
        # the arcade drivetrain's own grass test (CUSTOM1=2)
        p = WORK / 'HardDrivinHandling.s'
        s = p.read_text(encoding='latin-1')
        flag = '\tseq HS_GRASS(a0)\n'
        assert s.count(flag) == 1
        p.write_text(s.replace(flag, '\tsf HS_GRASS(a0)\n'), encoding='latin-1')
    p = WORK / 'HardDrivinDispatch.s'
    s = p.read_text(encoding='latin-1')
    after = '_dispatch_after_physics:\n'
    assert s.count(after) == 1
    s = s.replace(after, after + '\tmove.l a0,-(a7)\n\tlea _dispatch_after_physics(pc),a0\n'
                  '\tadda.l #_feel_pass-_dispatch_after_physics,a0\n\tjsr (a0)\n\tmovea.l (a7)+,a0\n')
    p.write_text(s, encoding='latin-1')
    # the fixture pushes _resload beyond the installer's 16-bit PC reach
    p = WORK / 'HardDrivinPhase.s'
    s = p.read_text(encoding='latin-1')
    far = ' movea.l _resload(pc),a2'
    assert s.count(far) == 1
    s = s.replace(far, ' lea _phase_install(pc),a2\n adda.l #_resload-_phase_install,a2\n movea.l (a2),a2')
    p.write_text(s, encoding='latin-1')


def build(name, slow=False, prefix='feel-'):
    route = ROUTE_OF.get(name, name[4:] if name.startswith('lap-') else None)
    equ, data = plan_source(SLOW_PLANS.get(name, PLANS[name]) if slow else PLANS[name], route)
    (WORK / 'feel_plan_equ.i').write_text(equ)
    (WORK / 'feel_plan.i').write_text(data)
    out = BUILD / ('%s%s%s' % (prefix, 'slow-' if slow else '', name))
    args = [os.environ['VASM'], '-m68000', '-pic', '-x', '-devpac', '-Fhunkexe', '-nosym', '-quiet',
            '-I' + str(WORK), '-I' + os.environ['AMIGA_INCLUDE'], '-I' + os.environ['WHDLOAD'] + '/Include',
            '-I' + os.environ['WHDLOAD'] + '/Src/sources', '-I' + os.environ['NDK'],
            '-DVERIFY_DRIVE=1', '-DVERIFY_STEPINPUT=1'] + (['-DVERIFY_SLOW=1'] if slow else []) + [
            '-o', str(out.with_suffix('.slave')),
            '-L', str(out.with_suffix('.lst')), 'HardDrivinHD.s']
    subprocess.run(args, cwd=WORK, check=True)
    return out.with_suffix('.slave')


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--slow', action='store_true')
    ap.add_argument('--source', type=Path, default=SOURCE, help='another source tree (a control build)')
    ap.add_argument('--pad', type=int, default=0, help='zero bytes appended to the slave')
    ap.add_argument('--prefix', default='feel-', help='output name prefix')
    ap.add_argument('names', nargs='*')
    a = ap.parse_args()
    names = a.names or list(PLANS)
    assert all(n in PLANS for n in names), set(names) - set(PLANS)
    BUILD.mkdir(parents=True, exist_ok=True)
    for laps in (False, True):
        group = [n for n in names if (n.startswith('lap-') or n in ROUTE_OF) == laps]
        if not group:
            continue
        prepare(a.source.resolve(), a.pad, native_ground=laps)
        for n in group:
            print(build(n, prefix=a.prefix).relative_to(ROOT))
            if a.slow:
                print(build(n, True, a.prefix).relative_to(ROOT))


if __name__ == '__main__':
    main()
