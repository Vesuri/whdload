"""Brake applications in a lap run and what followed: brake_events.py RUN_DIR...

For each run of physics passes with the model's brake on (model.bin, HDFEEL03):
its fields, the forward speed at the start and the end and 3 s (150 fields)
later, the mouse, the yaw rate before and the largest within those 3 s, and
the largest sideways speed. More than 50 ft/s sideways is a spin.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools/arcade'))
import amiga_feel as af        # noqa: E402
for run in sys.argv[1:]:
    M = af.models(run); S = af.steps(run)
    print('==', run)
    k = 0
    n = len(M)
    while k < n:
        if M[k]['brake'] and (k == 0 or not M[k - 1]['brake']):
            f0 = S[k]['field']
            j = k
            while j < n and M[j]['brake']:
                j += 1
            win = [i for i in range(k, n) if S[i]['field'] <= f0 + 150]
            rmax = max(abs(M[i]['r']) / 2**27 * 57.3 for i in win)
            vmax = max(abs(M[i]['v']) / 4194304 for i in win)
            print('  field %5d brake %3d fields  u %3d -> %3d ft/s (3 s later %3d)  counts %4d  r before %5.1f max %5.1f deg/s  |v| max %5.1f ft/s' % (
                f0, S[min(j, n - 1)]['field'] - f0, M[k]['u'] >> 6, M[min(j, n - 1)]['u'] >> 6, M[win[-1]]['u'] >> 6,
                M[k]['counts'], M[k]['r'] / 2**27 * 57.3, rmax, vmax))
            k = j
        k += 1
