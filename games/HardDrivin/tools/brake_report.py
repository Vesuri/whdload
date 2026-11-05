"""Braking for plan step H3 round 3: brake_report.py RUN_DIR...

For each brake application above 40 MPH (button word 5) in each run: the speed and
throttle at the start, the time to stop (or to the release) and the mean
deceleration, and the deceleration in 20 MPH bands.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools/arcade'))
import amiga_feel as af        # noqa: E402
FT = 0.28 * 5280 / 3600
for path in sys.argv[1:]:
    R = af.records(path)
    starts = [k for k in range(1, len(R)) if R[k]['buttons'] == 5 and R[k - 1]['buttons'] != 5 and R[k]['velocity'] * 0.28 > 40]
    for i in starts:
        r0 = R[i]; v0 = r0['velocity']
        j = next((k for k in range(i, len(R)) if R[k]['velocity'] <= 0 or R[k]['buttons'] != 5), len(R) - 1)
        t = (R[j]['field'] - r0['field']) / 50
        out = '%s: %.0f MPH thr %d -> %.0f MPH in %.1f s (%.2f g)' % (path.split('/')[-2] + '/' + path.split('/')[-1], v0 * .28, r0['throttle'], R[j]['velocity'] * .28, t, (v0 - R[j]['velocity']) * FT / max(t, .02) / 32.2)
        def at(m):
            return next((R[k]['field'] for k in range(i, j + 1) if R[k]['velocity'] * 0.28 <= m), None)
        bands = []
        for hi, lo in ((100, 80), (80, 60), (60, 40), (40, 20), (20, 5)):
            if v0 * .28 < hi - 1 or at(lo) is None:
                continue
            dt = (at(lo) - at(hi)) / 50
            bands.append('%d-%d %.2fg' % (hi, lo, (hi - lo) * 5280 / 3600 / dt / 32.2))
        print(out + '  ' + ' '.join(bands))
