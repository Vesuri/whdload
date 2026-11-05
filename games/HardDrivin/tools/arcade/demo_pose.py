"""The attract demo's car pose from RAM dumps: demo_pose.py RUN_DIR START STEP.

RUN_DIR holds ramNNN.bin (68010 $FF0000-$FFFFFF, plans/a_dump2.lua); START is the
time of ram000 and STEP the interval. The playback keeps the pose at $FF8404:
X, Y, Z longs (40 per foot, Y up), then a 2.14 matrix whose column 2 is the
car's forward axis in (X, Y, Z). Prints pitch against the entry heading, the
forward axis and the velocity along the horizontal axis square to the entry
heading, and the sideways distance from the first sample."""
import glob, math, os, struct, sys
run, start, step = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
files = sorted(glob.glob(os.path.join(run, 'ram*.bin')))
P, M = [], []
for f in files:
    b = open(f, 'rb').read()
    P.append([v / 40 for v in struct.unpack('>3i', b[0x8404:0x8410])])
    M.append([v / 16384 for v in struct.unpack('>9h', b[0x8414:0x8426])])
f0 = [M[0][2], 0, M[0][8]]; h = math.hypot(f0[0], f0[2]); f0 = [f0[0] / h, 0, f0[2] / h]
a = [-f0[2], 0, f0[0]]
for n in range(1, len(P) - 1):
    f = [M[n][2], M[n][5], M[n][8]]
    d = [P[n + 1][i] - P[n - 1][i] for i in range(3)]; L = math.sqrt(sum(x * x for x in d))
    if L == 0: continue
    d = [x / L for x in d]
    pitch = math.degrees(math.atan2(f[1], sum(f[i] * f0[i] for i in range(3))))
    print('%6.2f y %6.1f ft pitch %6.1f | fwd.axis %+.3f vel.axis %+.3f | sideways %+6.1f ft | %5.1f ft/s' % (
        start + n * step, P[n][1], pitch, sum(f[i] * a[i] for i in range(3)), sum(d[i] * a[i] for i in range(3)),
        sum((P[n][i] - P[0][i]) * a[i] for i in range(3)), L / (2 * step)))
