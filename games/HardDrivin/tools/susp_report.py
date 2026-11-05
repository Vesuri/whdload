"""Pitch, height and axle loads per physics pass, for plan step H3 round 11 (the suspension).

susp_report.py RUN_DIR [RUN_DIR...] [--from F] [--to F] [--every N] [--summary]

For each run (tools/capture_feel.py output): per physics pass, the race field,
fields consumed, pitch G($994c) in degrees, height y in units, contact mask,
fall velocity G($990e), the handling model's front and rear loads (lb, from
model.bin), speed (MPH at the real scale) and the brake (the fixture's buttons). --summary prints only
the load and pitch statistics: the loads' spread on the ground at steady speed
(|change of speed| < 1 MPH over 0.5 s, mask 15, no brake) and the largest
nose-down pitch while braking.
"""
import argparse
import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/arcade'))
import amiga_feel as af        # noqa: E402

MPH_PER_V = 0.28 * 0.1791 / 0.3504
STEP = 92


def wrap(a):
    return (a + 720) % 1440 - 720


def passes(run):
    b = open(os.path.join(run, 'steps.bin'), 'rb').read()
    out = []
    for i in range(0, len(b), STEP):
        field, consumed = struct.unpack_from('>II', b, i)

        def g(addr, fmt):
            return struct.unpack_from('>' + fmt, b, i + 8 + addr - 0x98fc)[0]
        out.append(dict(field=field, consumed=consumed, y8=g(0x9900, 'i'), pitch=g(0x994c, 'h'),
                        roll=g(0x994e, 'h'), mask=g(0x9910, 'B'), fall=g(0x990e, 'h'), v=g(0x9928, 'h'),
                        brake=g(0x9911, 'B')))
    return out


def report(run, a):
    P = passes(run)
    M = af.models(run)
    held = {r['field']: r['brake'] for r in af.records(run)}
    for p in P:
        p['brake'] = 1 if held.get(p['field'], 0) else 0
    print('== %s (%d passes)' % (run, len(P)))
    rows = []
    for k, p in enumerate(P):
        m = M[k] if k < len(M) else None
        nf = m['nf'] / 4 if m else 0
        nr = m['nr'] / 4 if m else 0
        rows.append((p, nf, nr))
    if not a.summary:
        print('  field  n  pitch   roll      y  mask fall    nf    nr   MPH brake')
        for k, (p, nf, nr) in enumerate(rows):
            if p['field'] < a.first or p['field'] > a.last or k % a.every:
                continue
            print('  %5d %2d %6.2f %6.2f %7.2f %4d %4d %5.0f %5.0f %5.1f %d' % (
                p['field'], p['consumed'], wrap(p['pitch']) / 4, wrap(p['roll']) / 4, p['y8'] / 8, p['mask'],
                p['fall'], nf, nr, p['v'] * MPH_PER_V, p['brake']))
    steady = []
    for k, (p, nf, nr) in enumerate(rows):
        if p['mask'] != 15 or p['brake'] or k < 5 or k + 5 >= len(rows):
            continue
        dv = abs(rows[k + 5][0]['v'] - rows[k - 5][0]['v']) * MPH_PER_V
        if dv < 1 and p['v'] > 20:
            steady.append((nf, nr))
    if steady:
        for name, i in (('front', 0), ('rear', 1)):
            xs = [s[i] for s in steady]
            mean = sum(xs) / len(xs)
            sd = (sum((x - mean) ** 2 for x in xs) / len(xs)) ** 0.5
            print('  steady %s load: mean %.0f lb, sd %.0f, range %.0f..%.0f (%d passes)' % (
                name, mean, sd, min(xs), max(xs), len(xs)))
    braking = [wrap(p['pitch']) / 4 for p, nf, nr in rows if p['brake'] and p['mask'] == 15]
    if braking:
        print('  braking: pitch %.2f..%.2f deg' % (min(braking), max(braking)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+')
    p.add_argument('--from', dest='first', type=int, default=0)
    p.add_argument('--to', dest='last', type=int, default=1 << 30)
    p.add_argument('--every', type=int, default=1)
    p.add_argument('--summary', action='store_true')
    a = p.parse_args()
    for run in a.runs:
        report(run, a)


if __name__ == '__main__':
    main()
