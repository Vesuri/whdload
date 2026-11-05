"""Yaw rate, pitch, roll and wheel contact over time, for plan step H3 round 2.

tilt_report.py RUN_DIR [RUN_DIR...] [--every N] [--from F]

For each run (tools/capture_feel.py output): every N fields (default 10), the
yaw rate over the last N fields, heading, pitch G($994c) and roll G($994e) in
degrees, the wheel contact mask G($9910), the height, the speed, the mouse
offset and the crash and recovery flags. Then the largest |pitch| and |roll|
outside crashes, and the first field where either passes 20 degrees.
"""
import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/arcade'))
import amiga_feel as af        # noqa: E402

MPH_PER_V = 0.28


def wrap(a):
    return (a + 720) % 1440 - 720


def report(path, every, first):
    R = af.records(str(path))
    print('== %s' % path)
    print('  field   yaw deg/s  heading  pitch    roll  mask   y   MPH  mouse crash rec')
    prev = None
    for k in range(0, len(R), every):
        r = R[k]
        if r['field'] < first:
            continue
        rate = 0.0
        if prev is not None:
            rate = wrap(r['heading'] - prev['heading']) / 4 / ((r['field'] - prev['field']) * 0.02)
        prev = r
        print('  %5d %9.1f %8.1f %6.1f %7.1f  %4d %4d %5.1f %5d %4d %3d' % (
            r['field'], rate, r['heading'] / 4, wrap(r['a994c']) / 4, wrap(r['a994e']) / 4, r['mask'],
            r['y8'] >> 3, r['velocity'] * MPH_PER_V, r['mouse'] - 320, r['crash'], r['recovery']))
    calm = [r for r in R if not r['crash'] and not r['recovery'] and r['field'] >= first]
    if calm:
        pitch = max(abs(wrap(r['a994c'])) for r in calm) / 4
        roll = max(abs(wrap(r['a994e'])) for r in calm) / 4
        over = next((r['field'] for r in calm if max(abs(wrap(r['a994c'])), abs(wrap(r['a994e']))) > 80), None)
        print('  largest |pitch| %.1f deg, |roll| %.1f deg outside crashes; past 20 deg at field %s' % (
            pitch, roll, over))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+')
    p.add_argument('--every', type=int, default=10)
    p.add_argument('--from', dest='first', type=int, default=0)
    a = p.parse_args()
    for run in a.runs:
        if os.path.exists(os.path.join(run, 'rec.bin')):
            report(Path(run), a.every, a.first)


if __name__ == '__main__':
    main()
