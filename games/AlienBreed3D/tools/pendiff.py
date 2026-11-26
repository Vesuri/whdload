#!/usr/bin/env python3
"""Compare two tools/pencheck.sh runs frame by frame (resolution plan step 7).

    python3 tools/pendiff.py REF NEW [PNGDIR]

For each frame in both: the pixels whose pens differ and their bounding box. Line 0 is left
out (the convert writes it black; no writer draws it). With PNGDIR, each differing frame
as a PNG of REF | NEW | the differing pixels, the pens as grey levels. Exit status 1 if any
frame differs.
"""
import struct
import sys
from pathlib import Path


def frame(path):
    b = path.read_bytes()
    w, h = struct.unpack('>HH', b[:4])
    return w, h, b[4:]


def main(ref, new, pngdir=None):
    ref, new = Path(ref), Path(new)
    names = sorted(p.name for p in ref.glob('*.pens'))
    bad = 0
    for name in names:
        if not (new / name).exists():
            print(f'{name}: missing in {new}')
            bad += 1
            continue
        w, h, a = frame(ref / name)
        w2, h2, b = frame(new / name)
        if (w, h) != (w2, h2):
            print(f'{name}: {w}x{h} against {w2}x{h2}')
            bad += 1
            continue
        diff = [i for i in range(w, w * h) if a[i] != b[i]]
        if not diff:
            continue
        bad += 1
        xs, ys = [i % w for i in diff], [i // w for i in diff]
        print(f'{name}: {len(diff)} pixels, x {min(xs)}-{max(xs)} y {min(ys)}-{max(ys)}')
        if pngdir:
            png(Path(pngdir) / (name + '.png'), w, h, a, b, set(diff))
    print(f'{len(names)} frames, {bad} differ')
    return 1 if bad else 0


def png(path, w, h, a, b, diff):
    from PIL import Image
    img = Image.new('L', (3 * w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            i = y * w + x
            px[x, y], px[w + x, y] = a[i], b[i]
            px[2 * w + x, y] = 255 if i in diff else 0
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
