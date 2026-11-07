#!/usr/bin/env python3
"""Find visible flicker in consecutive field screenshots (fixed_window.py --shot-windows).

Two signatures, per field:
  transient  pixels that differ from both neighbours while the neighbours agree with each
             other (A-B-A): an image shown for one field only
  reversion  the whole field equals an earlier image after a different one was shown:
             an older picture shown again, as when an undrawn buffer is redisplayed

Legitimate one-field effects exist (hardware blinking, palette strobes), so each finding is
reported with its displayed bitplane address for review, not rejected outright.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy
from PIL import Image


def load(folder):
    folder = Path(folder)
    meta = json.loads((folder/'shots.json').read_text())['fields']
    images = [numpy.asarray(Image.open(folder/'shots'/f'{f["field"]:05d}.png').convert('RGB')) for f in meta]
    return meta, images


def inspect(folder, minimum=16):
    meta, images = load(folder)
    digests = [hashlib.sha256(image.tobytes()).hexdigest() for image in images]
    transients, reversions, seen = [], [], {}
    for i in range(1, len(images)-1):
        a, b, c = images[i-1], images[i], images[i+1]
        same_neighbours = (a == c).all(axis=2)
        odd = same_neighbours & (b != a).any(axis=2)
        count = int(odd.sum())
        if count >= minimum:
            ys, xs = numpy.nonzero(odd)
            transients.append(dict(field=i, pixels=count, box=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                                   planes=meta[i]['planes'], neighbour_planes=meta[i-1]['planes']))
    for i, digest in enumerate(digests):
        if i and digest != digests[i-1] and digest in seen and seen[digest] < i-1:
            reversions.append(dict(field=i, earlier=seen[digest], planes=meta[i]['planes']))
        seen[digest] = i
    changes = sum(d != p for p, d in zip(digests, digests[1:]))
    return dict(fields=len(images), image_changes=changes, distinct_images=len(set(digests)),
                transients=transients, reversions=reversions, scope=__doc__.strip())


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path)
    p.add_argument('--minimum', type=int, default=16, help='smallest transient pixel count reported')
    a = p.parse_args()
    print(json.dumps(inspect(a.capture, a.minimum), indent=1))
