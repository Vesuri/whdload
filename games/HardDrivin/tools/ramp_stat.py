"""Rear axle load and slip on a ramp run (H3 round 11): ramp_stat.py RUN_DIR, from the game directory."""
import sys, math
sys.path.insert(0, 'tools/arcade'); import amiga_feel as af
run = sys.argv[1]; M = af.models(run); S = af.steps(run)
z = 0; sl = 0; yw = 0
for s, m in zip(S, M):
    if s['field'] < 100 or (m['nf'] == 0 and m['nr'] == 0): continue
    u = m['u'] / 64.0; v = m['v'] / 4194304.0
    if m['nr'] == 0: z += 1
    if u > 5: sl = max(sl, abs(math.degrees(math.atan2(v, u))))
    yw = max(yw, abs(math.degrees(m['r'] / 134217728.0)))
print('%-28s rear 0 on the ground: %2d passes; max |slip| %5.1f, max |yaw| %6.1f' % (run.split('prof/')[1], z, sl, yw))
