"""Car pose against the loop's road sections: loop_track.py RUN [FROM TO] (run from the game directory)."""
import json, sys, math
g = json.load(open('tmp/track-geometry.json'))['stunt']
run = sys.argv[1]; lo = int(sys.argv[2]) if len(sys.argv) > 2 else 60; hi = int(sys.argv[3]) if len(sys.argv) > 3 else 300
S = [r for r in json.load(open('tmp/prof/%s/motion.json' % run))['rows'] if r['kind'] == 'STEP']
def near(p):
    best = None
    for s in g[35:52]:
        L, R = s['left'], s['right']
        c = [(L[i] + R[i]) / 2 for i in range(3)]
        d = math.dist(p, c)
        if best is None or d < best[0]:
            ax = [(R[i] - L[i]) / 230 for i in range(3)]
            lat = sum((p[i] - c[i]) * ax[i] for i in range(3))
            best = (d, s['index'], lat, s['rest'][1])
    return best
for r in S:
    if not lo <= r['field'] <= hi: continue
    p = (r['x8'] / 8, r['y8'] / 8, r['z8'] / 8)
    d, i, lat, sp = near(p)
    print('%4d sec %2d dist %4.0f lat %+5.0f | pitch %5.1f road %5.1f | v %3d mask %2d heading %d wheels %d %d %d %d' % (
        r['field'], i, d, lat, r['pitch'] / 4, sp / 4, r['velocity'], r['mask'], r['heading'],
        r['wheel_fl'], r['wheel_fr'], r['wheel_rl'], r['wheel_rr']))
