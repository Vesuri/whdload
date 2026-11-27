#!/usr/bin/env python3
"""Enhanced resolution's display (resolution plan steps 4 and 5) against the original.

    python3 tools/display.py check SHOT FRAME [AREA]
    python3 tools/display.py compare ORIG.png OURS.png AREA
    python3 tools/display.py scale ORIG.frame OURS.frame

check: SHOT (an FS-UAE screenshot, 2 pixels a lores pixel and a raster) must show FRAME
(`ab3d.py frame`: colour words, the view byte, the width and height; 96x80, or 192x160
for the small view at 1x1) where the view is, in 12-bit
colour, or with AREA through the slave's palette. Where the original shows it: the small
view's chunky rows 2 rasters each from line $2c, rows 0-78 (the panel's list starts at
$ca); full screen's 3 rasters each from line $2b, shown from $2c to $117 (rows 0-78), 288
pixels 16 in from the window's left edge. In the original's full screen line $ff shows row
71, not row 70's last raster: its list's WAIT for line $100 compares 8 bits and is met a
line early. Ours shows row 70 there, so without AREA (the original) that raster is row 71.

compare: ORIG is a screenshot with CUSTOM5=0, OURS the same moment with CUSTOM5=1, AREA a dump of
the slave's area (`ab3d.py palette AREA 1`). The skeleton shows the original's own frame
through the 1x1 palette, so each pixel of OURS must equal ORIG's, or be ORIG's 12-bit
colour through the area's map and palette (the view). Prints the pixels that are neither,
with their bounding box, and the box of the palette's differences (inside the view). In
full screen (the view byte of OURS.frame, next to OURS) line $ff is left out, the original's
early row 71 above. In the small view line $ca is left out: the panel's list rewrites the
frame sprites' colours there, high nibbles then low, and the original's view list, which
has no WAITs, reaches it at a time no WAIT of ours matches (from $c8df to $ca09 the
sprites differ in 88 pixels of that line, from $ca11 on more, from $ca21 the panel's
lines too). Exit status 1 when any pixel is neither.

FRAME.alt, when `ab3d.py frame` found a view in the other list too, is that list: check
passes if either is on the screen (a stop can fall between the game's pointer swap and the
switch of the screen). At 1x1 (192x160, 288x240) line 0 is black, as `_ds_one` shows it.

scale: OURS is the same moment as ORIG at S times its width and height (S = 2: the small
view at 1x1, 3: full screen): the share of ORIG's pixels (lines 1-78, columns 1-94) whose
colour is in the S x S block of OURS that covers them, rows S(y - 1) + 1 to Sy, columns Sx
to Sx + S - 1 (the writers draw row y at line y + 1). The rest is mostly texture sampled
at other points where a texture is shrunk (far or slanted walls). Exit status 1 below
SCALE_MIN. `compare` does this when OURS.frame, next to OURS, is S times ORIG.frame's
width, with either side's FRAME.alt too, and then checks the view's lines beside it (the
border): each pixel must be ORIG's (from the 68040 on full screen's rows are 320 pixels,
whose last 32 the c2p does not write).
"""
import os
import sys

import numpy as np
from PIL import Image

PA_PALETTE = 4
PA_MAP = 512
PEN0 = 16


def load(path):
    return np.array(Image.open(path).convert('RGB')).astype(np.int32)


def box(mask):
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return 'none'
    return 'x %d-%d, y %d-%d' % (xs.min(), xs.max(), ys.min(), ys.max())


# (left, top) in a screenshot, png pixels a chunky pixel at 96x80, first and last png row
# shown; at 1x1 2 png pixels a pixel
GEOMETRY = {0: (202, 36, 4, 36, 36 + 4 * 79), 1: (106, 34, 6, 36, 36 + 2 * (0x118 - 0x2c))}


def read_frame(path):
    """`ab3d.py frame`'s file: (words as an H x W array, view byte)."""
    raw = open(path, 'rb').read()
    w, h = int.from_bytes(raw[-4:-2], 'big'), int.from_bytes(raw[-2:], 'big')
    words = np.frombuffer(raw[:w * h * 2], '>u2').reshape(h, w).astype(np.int64) & 0xfff
    return words, raw[w * h * 2]
EARLY = 36 + 2 * (0xff - 0x2c)          # the original's full screen: line $ff shows row 71
PANEL = 36 + 2 * (0xca - 0x2c)          # the small view: the panel's colours load on line $ca


def palette(area):
    raw = open(area, 'rb').read()
    pens = int.from_bytes(raw[0:2], 'big')
    pal = [int.from_bytes(raw[PA_PALETTE + 2 * k:PA_PALETTE + 2 * k + 2], 'big')
           for k in range(pens)]
    return pal, raw[PA_MAP:PA_MAP + 4096]


def check(shot, frame, area=None):
    """The game swaps its list pointers a little before it shows the finished list (COP2LC
    in the original, `_p_show` in ours), and a stop between the two finds the other list
    on screen: FRAME.alt, that list, is tried as well."""
    alt = frame + '.alt'
    if not os.path.exists(alt):
        return check1(shot, frame, area)
    return check1(shot, frame, area, quiet=True) and check1(shot, alt, area)


def check1(shot, frame, area=None, quiet=False):
    img = load(shot)
    words, view = read_frame(frame)
    if words.shape[1] != 96:
        words = words.copy()
        words[0] = 0            # line 0 black (display.s _ds_one): no writer draws it
    if area:
        pal, cmap = palette(area)
        lut = np.array([pal[cmap[c] - PEN0] for c in range(4096)])
        words = lut[words]
    rgb = np.stack([(words >> 8) * 17, ((words >> 4) & 15) * 17, (words & 15) * 17], -1)
    x0, y0, k, top, bottom = GEOMETRY[view]
    if words.shape[1] != 96:
        k = 2
    want = np.repeat(np.repeat(rgb, k, 0), k, 1)
    if view and not area:
        want[EARLY - y0:EARLY - y0 + 2] = want[(71 * k):(71 * k) + 2]
    got = img[top:bottom, x0:x0 + words.shape[1] * k]
    want = want[top - y0:bottom - y0]
    bad = (got != want).any(2)
    if quiet and bad.any():
        return 1
    print('%s against %s (%s%s): %d view pixels, %d differ (%s)'
          % (shot, frame, 'full screen' if view else 'small view',
             ', through the palette' if area else '', bad.size, bad.sum(), box(bad)))
    return 1 if bad.any() else 0


def compare(orig, ours, area):
    fo, fu = orig[:-4] + '.frame', ours[:-4] + '.frame'
    if (os.path.exists(fo) and os.path.exists(fu)
            and read_frame(fu)[0].shape[1] in (2 * 96, 3 * 96)
            and read_frame(fo)[0].shape[1] == 96):
        # a view at 1x1: scale, with whichever list each side showed
        pairs = [(o, u) for o in (fo, fo + '.alt') for u in (fu, fu + '.alt')
                 if os.path.exists(o) and os.path.exists(u)]
        o, u = next(((o, u) for o, u in pairs if scale(o, u, quiet=True) == 0), (fo, fu))
        return scale(o, u) | sides(orig, ours, read_frame(fu)[1])
    a, b = load(orig), load(ours)
    if a.shape != b.shape:
        sys.exit('%s is %s, %s is %s' % (orig, a.shape, ours, b.shape))
    pal, cmap = palette(area)
    # 24-bit pen colours of every 12-bit colour, -1 where a pixel is not 12-bit
    expand = np.full(1 << 24, -1, np.int64)
    for c in range(4096):
        p = pal[cmap[c] - PEN0]
        r, g, bl = (c >> 8) * 17, ((c >> 4) & 15) * 17, (c & 15) * 17
        pr, pg, pb = (p >> 8) * 17, ((p >> 4) & 15) * 17, (p & 15) * 17
        expand[(r << 16) | (g << 8) | bl] = (pr << 16) | (pg << 8) | pb
    av = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    bv = (b[..., 0] << 16) | (b[..., 1] << 8) | b[..., 2]
    same = av == bv
    mapped = ~same & (expand[av] == bv)
    wrong = ~same & ~mapped
    frame = ours[:-4] + '.frame'
    try:
        full = read_frame(frame)[1]
    except OSError:
        full = 0
    if full:
        wrong[EARLY:EARLY + 2] = False
    else:
        wrong[PANEL:PANEL + 2] = False
    print('%s against %s: %d pixels, %d the same, %d through the palette (%s), %d neither (%s)'
          % (ours, orig, av.size, same.sum(), mapped.sum(), box(mapped), wrong.sum(), box(wrong)))
    return 1 if wrong.any() else 0


def sides(orig, ours, view):
    """The view's lines left and right of it (the border, pen 0) must be ORIG's pixels."""
    a, b = load(orig), load(ours)
    x0, _, k, top, bottom = GEOMETRY[view]
    x1 = x0 + 96 * k
    bad = (a != b).any(2)[top:bottom]
    bad[:, x0:x1] = False
    print('%s against %s: %d pixels beside the view, %d differ (%s)'
          % (ours, orig, bad[:, :x0].size + bad[:, x1:].size, bad.sum(), box(bad)))
    return 1 if bad.any() else 0


SCALE_MIN = 0.80    # level 1's start, pause and end gave 88-94% at 2x2 (26.11.2026)


def scale(orig, ours, quiet=False):
    a, _ = read_frame(orig)
    b, _ = read_frame(ours)
    h, w = a.shape
    f = b.shape[1] // w
    if f not in (2, 3) or b.shape != (f * h, f * w):
        sys.exit('%s is %s, %s is %s: not 2 or 3 times' % (orig, a.shape, ours, b.shape))
    v = a[1:h - 1, 1:w - 1]
    found = np.zeros(v.shape, bool)
    for j in range(-(f - 1), 1):
        for i in range(f):
            found |= b[f + j:f * (h - 1) + j:f, f + i:f * (w - 1) + i:f] == v
    share = found.mean()
    if quiet:
        return 0 if share >= SCALE_MIN else 1
    print('%s against %s at %dx%d: %.1f%% of the pixels found (at least %.0f%%)'
          % (ours, orig, f, f, 100 * share, 100 * SCALE_MIN))
    return 0 if share >= SCALE_MIN else 1


def main(argv):
    if len(argv) in (3, 4) and argv[0] == 'check':
        return check(*argv[1:])
    if len(argv) == 4 and argv[0] == 'compare':
        return compare(*argv[1:])
    if len(argv) == 3 and argv[0] == 'scale':
        return scale(*argv[1:])
    sys.exit(__doc__)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
