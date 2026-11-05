"""Read the MPH needle from snapshots and compare it with result $8DEA.
Usage: needle.py RUN_DIR T1 [T2...]   (snapshot times, in snapshot order)
The dial is linear: 0 MPH at 225 degrees, 140 MPH at -90 (2.25 degrees per
MPH), pivot at pixel (305, 322) of the 508x384 snapshot."""
import sys, os, glob, math
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I omits it
from hdlog import rows, s16
run, times = sys.argv[1], [float(a) for a in sys.argv[2:]]
R = list(rows(run + '/log.txt'))
files = sorted(glob.glob(run + '/snap/harddriv/*.png'))
box, cx, cy = (262, 272, 352, 368), 305.0, 322.0
for t, f in zip(times, files):
    im = Image.open(f).convert('RGB')
    px = [(x, y) for y in range(box[1], box[3]) for x in range(box[0], box[2])
          if (lambda p: p[0] > 180 and p[1] < 80 and p[2] < 80)(im.getpixel((x, y)))]
    far = [(x, y) for x, y in px if math.hypot(x - cx, y - cy) > 10]
    fx = sum(x for x, y in far) / len(far); fy = sum(y for x, y in far) / len(far)
    a = math.degrees(math.atan2(-(fy - cy), fx - cx)); a = a if a < 0 else a - 360
    mph = (-135 - a) / 2.25
    r = min(R, key=lambda r: abs(r['t'] - t))
    print('t=%.2f $8DEA=%d needle %.1f MPH ratio %.3f' % (t, s16(r['res'][0x15]), mph, s16(r['res'][0x15]) / mph if mph > 1 else 0))
