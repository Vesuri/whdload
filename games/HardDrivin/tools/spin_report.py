"""Yaw rate, heading and speed over time for plan step H3's spin runs.

spin_report.py ROOT [ROOT...]     (matrices below tmp/prof, from run_feel.py)

For every run in ROOT with a throttle phase (build_feel.py h3-spin-*): from
half a second before full throttle and full lock to the end, every half
second, the yaw rate between physics passes, the heading turned since the
start, the speed, the mouse offset and the crash flag. Then the largest yaw
rate from 1.5 s on, after the steering change.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/arcade'))
import amiga_feel as af        # noqa: E402

PROF = HERE.parent / 'tmp/prof'
MPH_PER_V = 0.28
RAISE = 4


def wrap(d):
    return (d + 720) % 1440 - 720


def report(path):
    S, R = af.steps(str(path)), af.records(str(path))
    start = next(r['field'] for r in R if r['plan_buttons'] == RAISE)
    rows, turned, peak, prev = [], 0, 0, None
    for s in S:
        if s['field'] < start - 25:
            continue
        if prev is not None and s['field'] > prev['field']:
            d = wrap(s['heading'] - prev['heading'])
            turned += d
            rate = d / 4 / ((s['field'] - prev['field']) * 0.02)
            if s['field'] > start + 75:
                peak = max(peak, abs(rate))
            rows.append((s['field'] - start, rate, turned / 4))
        prev = s
    print('== %s' % path.relative_to(PROF))
    marks = iter(range(-25, 9 * 50, 25))
    mark = next(marks)
    for f, rate, h in rows:
        if mark is not None and f >= mark:
            r = min(R, key=lambda x: abs(x['field'] - f - start))
            print('  t %5.2f s  yaw %7.1f deg/s  turned %7.1f deg  %5.1f MPH  mouse %4d  crash %d' % (
                f * 0.02, rate, h, r['velocity'] * MPH_PER_V, r['mouse'] - 320, r['crash']))
            while mark is not None and f >= mark:
                mark = next(marks, None)
    print('  largest yaw rate after the steering change %.0f deg/s; %.1f MPH at the end' % (
        peak, R[-1]['velocity'] * MPH_PER_V))


def main():
    for root in sys.argv[1:]:
        for name in sorted(os.listdir(PROF / root)):
            if (PROF / root / name / 'rec.bin').exists():
                report(PROF / root / name)


if __name__ == '__main__':
    main()
