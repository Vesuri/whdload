"""Summarise plan step H2's laps (build_feel.py lap-ROUTE, capture_feel.py).

lap_report.py RUN [RUN...]     (runs below tmp/prof)

For each run: how far along its route the car got and how long it took,
its distance from the route, its speeds, and the events on the way: road
sections where it left the road, flights (no wheel on the ground: take-off
speed, length, landing), the loop (pitch past 90 degrees), crashes and
recoveries, replays (no physics pass for 40 fields), checkpoint bonuses
(the remaining-time clock going up) and how the run ended.
"""
import json
import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'tools/arcade'))
import amiga_feel as af        # noqa: E402
import build_feel as bf        # noqa: E402

PROF = HERE.parent / 'tmp/prof'
MPH_PER_V = 0.28               # the native speedometer
SCALE = 0.3504 / 0.1791        # arcade handling: a world unit is 0.1791 ft, not 0.3504
FT_PER_UNIT = 0.1791
DONE = {0: 'still running at the field limit', 1: 'end of the route', 2: 'crash', 3: 'time limit', 4: 'left the ground'}


def bcd(x):
    s = '%08x' % x
    return s


def wrap(d):
    return (d + 32768) % 65536 - 32768


def pitch_steps(run):
    b = (run / 'steps.bin').read_bytes()
    out = []
    for i in range(0, len(b), 92):
        field = struct.unpack_from('>I', b, i)[0]
        pitch = struct.unpack_from('>h', b, i + 8 + 0x9946 - 0x98fc)[0]
        roll = struct.unpack_from('>h', b, i + 8 + 0x9948 - 0x98fc)[0]
        out.append((field, pitch, roll))
    return out


def report(run):
    global MPH_PER_V
    meta = json.loads((run / 'metadata.json').read_text())
    MPH_PER_V = 0.28 / SCALE if meta['custom1'] == 2 else 0.28   # real MPH at CUSTOM1=2
    route = bf.ROUTE_OF.get(meta['plan'], meta['plan'][4:])
    pts = bf.route_points(route)
    R = af.records(str(run))
    idx, worst, off_route = 0, 0, []
    progress = []
    for r in R:
        x, y, z = r['x8'] >> 3, r['y8'] >> 3, r['z8'] >> 3

        def dist(k):
            p = pts[k]
            return abs(wrap(p[0] - x)) + abs(wrap(p[2] - z)) + abs(p[1] - y)
        if dist(idx) > 1500:
            idx = min(range(max(0, idx - 200), min(len(pts), idx + 200)), key=dist)
        while idx + 1 < len(pts) and dist(idx + 1) <= dist(idx):
            idx += 1
        progress.append(idx)
        live = not r['crash'] and not r['recovery']
        if live:
            # lateral distance to the segment idx..idx+1
            p, q = pts[idx], pts[min(idx + 1, len(pts) - 1)]
            dx, dz = wrap(x - p[0]), wrap(z - p[2])
            ux, uz = wrap(q[0] - p[0]), wrap(q[2] - p[2])
            n = (ux * ux + uz * uz) ** 0.5 or 1
            lat = abs(dx * uz - dz * ux) / n
            worst = max(worst, lat)
            if lat > 150:
                off_route.append((r['field'], pts[idx][4], pts[idx][5], round(lat)))
    events = []
    prev = None
    flight = None
    for i, r in enumerate(R):
        state = 'crash' if r['crash'] else 'recovery' if r['recovery'] else 'live'
        if prev is not None and state != prev:
            events.append((r['field'], '%s -> %s' % (prev, state), pts[progress[i]][4], pts[progress[i]][5]))
        prev = state
        if state == 'live' and r['mask'] == 0 and flight is None:
            flight = (i, r['velocity'])
        elif flight is not None and (r['mask'] != 0 or state != 'live'):
            i0, v0 = flight
            if i - i0 >= 5:
                events.append((R[i0]['field'], 'flight %d fields from %.0f MPH, landed at %.0f MPH, mask %d' % (
                    i - i0, v0 * MPH_PER_V, r['velocity'] * MPH_PER_V, r['mask']),
                    pts[progress[i0]][4], pts[progress[i0]][5]))
            flight = None
        if i and r['clock'] > R[i - 1]['clock'] and state == 'live':
            events.append((r['field'], 'clock %s -> %s' % (bcd(R[i - 1]['clock']), bcd(r['clock'])),
                           pts[progress[i]][4], pts[progress[i]][5]))
    # replays: the poses stop for more than 40 fields (A500 frames near the start take up to 17)
    steps = pitch_steps(run)
    for (f0, _, _), (f1, _, _) in zip(steps, steps[1:]):
        if f1 - f0 > 40:
            events.append((f0, 'no physics pass for %d fields (replay)' % (f1 - f0), '', ''))
    loop = [(f, p) for f, p, _ in steps if abs(p) > 360]
    if loop:
        events.append((loop[0][0], 'pitch past 90 degrees for %d passes, up to %.0f degrees' % (
            len(loop), max(abs(p) for _, p in loop) / 4), '', ''))
    events.sort(key=lambda e: e[0])
    last = R[-1]
    speeds = [r['velocity'] * MPH_PER_V for r in R if not r['crash'] and not r['recovery']]
    print('== %s (%s route, CUSTOM1=%d)' % (run.name, route, meta['custom1']))
    print('  %d fields (%.1f s), reached point %d of %d (%s %d), ended: %s' % (
        len(R), len(R) * 0.02, max(progress), len(pts) - 1, pts[max(progress)][4], pts[max(progress)][5],
        DONE.get(last['done'], last['done'])))
    print('  speed: mean %.0f MPH, top %.0f MPH; largest distance from the route %.0f units (%.0f ft)' % (
        sum(speeds) / max(1, len(speeds)), max(speeds or [0]), worst, worst * FT_PER_UNIT))
    if off_route:
        print('  more than 150 units from the route: %d fields, first at field %d (%s %d, %d units)' % (
            len(off_route), off_route[0][0], off_route[0][1], off_route[0][2], off_route[0][3]))
    for f, text, road, sec in events:
        print('  field %5d %-8s %s' % (f, ('%s %s' % (road, sec)).strip(), text))
    return dict(run=run.name, fields=len(R), reached=max(progress), points=len(pts), done=last['done'])


def main():
    for name in sys.argv[1:]:
        report(PROF / name)


if __name__ == '__main__':
    main()
