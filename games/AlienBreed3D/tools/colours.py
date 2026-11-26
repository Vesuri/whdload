"""The colour census and the 1x1 views' palette (resolution plan step 3).

    python3 tools/colours.py census [FRAMES...]   which colours the view shows, and how well
                                                  each palette holds them (default: every
                                                  level's frames)
    python3 tools/colours.py images LEVEL N OUT   frame N of LEVEL, 4x, side by side: the
                                                  original, the slave's palette, Wu's, the cube
    python3 tools/colours.py check DUMP           the slave's area (ab3d.py palette) against
                                                  the model, part by part

Inputs, all from the installed game at analysis time (none is tracked):
  tmp/exe/abd.flat (tools/exe.py)       the shade tables in the executable (game offsets below)
  tmp/colours/tables (ab3d.py tables)   the loaded walls and floor texture
  tmp/colours/frames/L.bin (tools/census.sh, one file a level)  the frames shown: 96x80
                                        big-endian 12-bit colour words each

Colours are 12-bit (r, g, b in 0-15), as the copper writes them: with LOCT clear AGA sets
both nibbles, so a gun shows 17 * value of 255. Errors are CIELAB delta E (CIE76) between
the original colour and the pen shown, weighted by the pixels in the frames; 2.3 is about
one just-noticeable difference.

The slave's method (src/palette.s; `build`, `remap` and `effects` are its model, bit for
bit): a histogram of every shade-table entry the game can show (each class its share, each
row its brightness weight, each entry its texture's texel count), the POPULAR heaviest
colours as pens, then FARTHEST more, each the colour farthest in CIELAB from the pens so
far; every 12-bit colour then takes its nearest pen in CIELAB.

The palettes compared (the free pens: 240 in the small view, 255 in full screen):
  slave     the slave's 240
  cube      a 6x8x5 RGB cube, from no data
  static    Wu's quantiser on the same static histogram (in floating point): mean, its
            boxes' means; 12-bit, those rounded; mode, each box's heaviest colour; +km,
            refined by k-means; +14, with the frame sprites' 14 pens as fixed entries;
            dither, each colour as an ordered 2-pen checkerboard (the error is the pair's mean)
  frames    Wu on all levels' frames (an upper bound for one palette)
  level     Wu on each level's own frames (an upper bound for a palette per level)
"""
import struct
import sys
from pathlib import Path

import numpy as np

GAME = Path(__file__).resolve().parents[1]
FLAT = GAME / 'tmp/exe/abd.flat'
TABLES = GAME / 'tmp/colours/tables'
FRAMES = GAME / 'tmp/colours/frames'

# Shade tables in the executable (game offsets, $c4dc version)
FLOORPAL = 0x536e6      # floorScaleCols: 15 brightness rows of 256 colour words
TEXPAL = 0x3e066        # TexturePal: textured polygons' 15 rows of 256
TEXMAPS = 0x2e066       # TextureMaps: their 64 KB of texel bytes
OBJECTS = 0x2974a       # Objects: 18 entries of (wad, ptr, frames, pal); a pal is 15 rows of 32
N_OBJECTS = 18
GUN = 9                 # the gun in hand is Objects entry 9 (DrawInGun)
BORDERPAL = 0x9a09c     # the template's COLOR00-15, high nibbles, then again with LOCT
SKY = 0x55d00           # BackPicture: 16416 colour words, the backdrop
SKY_WORDS = 16416
BRIGHTEN = 0x766d2      # brightentab: 5632 colour words; LightDraw indexes it by colour,
BRIGHTEN_WORDS = 5632   #   texturedwater by distance row * 256 + water texel
WATER = 0x812d2         # waterfile: the water's 64 KB of texel bytes
WATER_ROWS = 13         # texturedwater's rows: (dst & $ff00) * 2 up to 12 * 512

FREE_SMALL, FREE_FULL = 240, 255


def words(data, off, n):
    return np.frombuffer(data, '>u2', n, off).astype(np.int64)


def rgb(c):
    """12-bit colours -> (..., 3) in 0-15."""
    c = np.asarray(c)
    return np.stack([(c >> 8) & 15, (c >> 4) & 15, c & 15], -1)


def lab(x):
    """(..., 3) RGB in 0-255 -> CIELAB (D65)."""
    x = np.asarray(x, float) / 255
    x = np.where(x > 0.04045, ((x + 0.055) / 1.055) ** 2.4, x / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = x @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], -1)


LAB12 = lab(rgb(np.arange(4096)) * 17)          # every 12-bit colour


# --- the static histogram: what every shade table can show ---------------------------------

def sources():
    """{class: [(name, colours (rows, n), texel counts (n,) or None)]} from the executable
    and the dumped tables."""
    f = FLAT.read_bytes()
    out = {'walls': [], 'floor': [], 'polygons': [], 'objects': [], 'gun': [], 'sky': [],
           'water': []}
    for p in sorted(TABLES.glob('wall*')):
        d = p.read_bytes()
        cols = words(d, 0, 1024).reshape(32, 32)
        t = words(d, 2048, (len(d) - 2048) // 2)
        texels = np.concatenate([t & 31, (t >> 5) & 31, (t >> 10) & 31])
        out['walls'].append((p.name, cols, np.bincount(texels, minlength=32)))
    floortile = np.frombuffer((TABLES / 'floortile').read_bytes(), np.uint8)
    out['floor'].append(('floor', words(f, FLOORPAL, 15 * 256).reshape(15, 256),
                         np.bincount(floortile, minlength=256)))
    tex = np.frombuffer(f, np.uint8, 65536, TEXMAPS)
    out['polygons'].append(('polygons', words(f, TEXPAL, 15 * 256).reshape(15, 256),
                            np.bincount(tex, minlength=256)))
    seen = set()
    for i in range(N_OBJECTS):
        pal = struct.unpack_from('>I', f, OBJECTS + 16 * i + 12)[0]
        if pal not in seen:
            seen.add(pal)
            # DrawInGun draws from the pal's first row only
            rows = 1 if i == GUN else 15
            out['gun' if i == GUN else 'objects'].append(
                (f'object{i}', words(f, pal, rows * 32).reshape(rows, 32), None))
    out['sky'].append(('sky', words(f, SKY, SKY_WORDS).reshape(1, -1), None))
    water = np.frombuffer(f, np.uint8, 65536, WATER)
    out['water'].append(('water', words(f, BRIGHTEN, WATER_ROWS * 256).reshape(WATER_ROWS, 256),
                         np.bincount(water, minlength=256)))
    return out


# the static histogram's share of each class: about the view's split in the baseline
# scenes (walls, then floors and ceilings, objects); the gun is in every frame, the sky,
# water and the polygons are rare
SHARES = {'walls': 45, 'floor': 30, 'objects': 8, 'gun': 5, 'sky': 2, 'polygons': 4,
          'water': 3}


def sprite_pens():
    """The frame sprites' pens 1-14 (pen 15 changes every line), as 24-bit colours in 0-15
    units: in the small view the 1x1 palette can use them as 14 fixed entries."""
    w = words(FLAT.read_bytes(), BORDERPAL, 68)
    hi, lo = w[3:35:2], w[37:69:2]
    return np.array([[((h >> s & 15) << 4 | (l >> s & 15)) / 17 for s in (8, 4, 0)]
                     for h, l in zip(hi[1:15], lo[1:15])])


# a row's weight, row 0 the brightest: (1 - row / rows) ** ROW_GAMMA. Near surfaces are both
# the brightest and the largest on screen
ROW_GAMMA = 2


def static_hist(src=None, shares=SHARES, gamma=ROW_GAMMA):
    """4096-bin histogram: each class gets its share, each table in it an equal part, each
    row (brightness) its ROW_GAMMA part of that, each entry its texel count's part of a row."""
    src = src or sources()
    h = np.zeros(4096)
    for cls, tables in src.items():
        for name, cols, counts in tables:
            rows, n = cols.shape
            w = np.ones(n) if counts is None else counts[:n].astype(float)
            if w.sum() == 0:
                continue
            rw = (1 - np.arange(rows) / rows) ** gamma
            w = np.outer(rw / rw.sum(), w / w.sum()) * shares[cls] / len(tables)
            np.add.at(h, cols.ravel(), w.ravel())
    return h / h.sum()


def static_union(src=None):
    src = src or sources()
    return {cls: set(np.concatenate([c.ravel() for _, c, _ in t]).tolist())
            for cls, t in src.items()}


# --- palettes -------------------------------------------------------------------------------

def wu(hist, k, scale=(1, 1, 1)):
    """Xiaolin Wu's quantiser (Graphics Gems II) on the 16x16x16 grid of 12-bit colours,
    with channels scaled by `scale` in the variance. Returns (palette (k, 3) of means in 0-15,
    tag: box index of each of the 4096 colours, or -1 for those with no weight)."""
    sr, sg, sb = scale
    w = np.zeros((17, 17, 17))
    c = rgb(np.arange(4096))
    w[c[:, 0] + 1, c[:, 1] + 1, c[:, 2] + 1] = hist
    r, g, b = np.meshgrid(np.arange(17) - 1, np.arange(17) - 1, np.arange(17) - 1, indexing='ij')
    mr, mg, mb = w * r * sr, w * g * sg, w * b * sb
    m2 = w * ((r * sr) ** 2 + (g * sg) ** 2 + (b * sb) ** 2)
    M = [np.cumsum(np.cumsum(np.cumsum(a, 0), 1), 2) for a in (w, mr, mg, mb, m2)]

    def vol(box, a):
        r0, r1, g0, g1, b0, b1 = box
        return (a[r1, g1, b1] - a[r1, g1, b0] - a[r1, g0, b1] + a[r1, g0, b0]
                - a[r0, g1, b1] + a[r0, g1, b0] + a[r0, g0, b1] - a[r0, g0, b0])

    def var(box):
        dw = vol(box, M[0])
        if dw <= 0:
            return 0.0
        d = [vol(box, M[i]) for i in (1, 2, 3)]
        return vol(box, M[4]) - sum(x * x for x in d) / dw

    def cut(box):
        whole = [vol(box, a) for a in M[:4]]
        best = (0.0, None, None)
        for axis in range(3):
            lo, hi = box[2 * axis], box[2 * axis + 1]
            for i in range(lo + 1, hi):
                half = list(box)
                half[2 * axis + 1] = i
                hw = [vol(half, a) for a in M[:4]]
                ow = [x - y for x, y in zip(whole, hw)]
                if hw[0] <= 0 or ow[0] <= 0:
                    continue
                t = sum(x * x for x in hw[1:]) / hw[0] + sum(x * x for x in ow[1:]) / ow[0]
                if t > best[0]:
                    best = (t, axis, i)
        if best[1] is None:
            return None
        _, axis, i = best
        a, b2 = list(box), list(box)
        a[2 * axis + 1] = i
        b2[2 * axis] = i
        return a, b2

    boxes = [[0, 16, 0, 16, 0, 16]]
    v = [var(boxes[0])]
    while len(boxes) < k:
        n = int(np.argmax(v))
        if v[n] <= 0:
            break
        s = cut(boxes[n])
        if s is None:
            v[n] = 0
            continue
        boxes[n], nb = s
        boxes.append(nb)
        v[n] = var(boxes[n])
        v.append(var(nb))
    pal = np.zeros((len(boxes), 3))
    tag = np.full(4096, -1)
    for i, box in enumerate(boxes):
        dw = vol(box, M[0])
        if dw > 0:
            pal[i] = [vol(box, M[j]) / dw / s for j, s in ((1, sr), (2, sg), (3, sb))]
        r0, r1, g0, g1, b0, b1 = box
        sel = ((c[:, 0] >= r0) & (c[:, 0] < r1) & (c[:, 1] >= g0) & (c[:, 1] < g1)
               & (c[:, 2] >= b0) & (c[:, 2] < b1) & (hist > 0))
        tag[sel] = i
    return pal, tag


def kmeans(hist, pal, scale=(1, 1, 1), iters=20):
    """Lloyd's iterations from `pal` on the weighted colours."""
    s = np.array(scale, float)
    idx = np.nonzero(hist)[0]
    x, w = rgb(idx) * s, hist[idx]
    p = np.array(pal, float) * s
    for _ in range(iters):
        a = ((x[:, None, :] - p[None]) ** 2).sum(-1).argmin(1)
        for j in range(len(p)):
            m = a == j
            if m.any():
                p[j] = (x[m] * w[m, None]).sum(0) / w[m].sum()
    return p / s


def cube(k):
    """An RGB cube of k entries: 6x8x5 for 240, 6x7x6 for 252."""
    nr, ng, nb = {240: (6, 8, 5), 255: (6, 7, 6)}[k]
    g = np.stack(np.meshgrid(np.linspace(0, 15, nr), np.linspace(0, 15, ng),
                             np.linspace(0, 15, nb), indexing='ij'), -1)
    return g.reshape(-1, 3)


def nearest(pal, scale=(1, 1, 1)):
    """For each of the 4096 colours the nearest entry (scaled RGB)."""
    s = np.array(scale, float)
    return ((rgb(np.arange(4096))[:, None, :] * s - np.asarray(pal)[None] * s) ** 2).sum(-1).argmin(1)


def dither_pairs(pal, cand=12, spread=0.25):
    """Each colour's best ordered-dither pair (p, q): the pair's mean closest to it in Lab,
    plus `spread` times the pair's own distance (a noisy pair costs). Returns (p, q) arrays."""
    pl = lab(np.asarray(pal) * 17)
    near = ((LAB12[:, None, :] - pl[None]) ** 2).sum(-1).argsort(1)[:, :cand]
    best_p = near[:, 0].copy()
    best_q = near[:, 0].copy()
    best = ((LAB12 - pl[best_p]) ** 2).sum(-1)
    for i in range(cand):
        for j in range(i + 1, cand):
            p, q = near[:, i], near[:, j]
            mean = lab((np.asarray(pal)[p] + np.asarray(pal)[q]) / 2 * 17)
            e = ((LAB12 - mean) ** 2).sum(-1) + spread * ((pl[p] - pl[q]) ** 2).sum(-1)
            better = e < best
            best = np.where(better, e, best)
            best_p = np.where(better, p, best_p)
            best_q = np.where(better, q, best_q)
    return best_p, best_q


def modes(hist, tag, k):
    """Each box's heaviest colour (exact 12-bit entries) in place of its mean."""
    pal = np.zeros((k, 3))
    for j in range(k):
        m = np.nonzero(tag == j)[0]
        if len(m):
            pal[j] = rgb(m[np.argmax(hist[m])])
    return pal


# --- the slave's builder, as integers ------------------------------------------------------
# What src/palette.s computes once the game has loaded its data, bit for bit: `build` is the
# model the slave is checked against (`check`), and the census's "slave" row.

WALLTILES = 0x42a66     # walltiles: a pointer to each loaded wall file
WALLCHUNKDATA = 0x42b06  # wallchunkdata: (name, unpacked size) pairs, ended by zeros
FLOORTILE = 0x55cee     # floortile: a pointer to the 64 KB floor texture
TOTAL = 1 << 30         # the histogram's total weight
POPULAR, FARTHEST = 200, 40     # pens: the heaviest colours, then the farthest from those
PEN0 = 16               # the first free pen: pens 0-15 are the border and the frame sprites
# the slave's constants: sRGB to linear (4095 = 1) for each 4-bit level, and linear RGB to
# XYZ over the D65 white, times 4096
LIN = [round(4095 * (v / 15 / 12.92 if v / 15 <= 0.04045 else ((v / 15 + 0.055) / 1.055) ** 2.4))
       for v in range(16)]
XYZ = [[round(4096 * m / w) for m in row] for row, w in zip(
    [[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]],
    [0.95047, 1.0, 1.08883])]
FLIN_A = round(7.787037 * 4096 / 4095 * 65536)  # f(t) = 7.787 t + 16/116 below (6/29)^3,
FLIN_B = round(16 / 116 * 4096 * 65536)         # in 1/4096, from t in 1/4095, over 65536
FLIN_T = 36                                      # the last t on that line


def model_inputs(tables=TABLES):
    """The builder's tables in its order, as (class, rows (R, n) of colour words, counts
    (n,) or None), from the executable and the dumped walls and floor texture."""
    f = FLAT.read_bytes()
    out = []
    for i in range(40):
        size = struct.unpack_from('>I', f, WALLCHUNKDATA + 8 * i + 4)[0]
        if not size:
            break
        d = (Path(tables) / f'wall{i:02d}').read_bytes()
        t = words(d, 2048, (size - 2048) // 2)
        cnt = np.bincount(np.concatenate([t & 31, (t >> 5) & 31, (t >> 10) & 31]), minlength=32)
        out.append(('walls', words(d, 0, 1024).reshape(32, 32), cnt))
    ft = np.frombuffer((Path(tables) / 'floortile').read_bytes(), np.uint8)
    out.append(('floor', words(f, FLOORPAL, 3840).reshape(15, 256), np.bincount(ft, minlength=256)))
    tex = np.frombuffer(f, np.uint8, 65536, TEXMAPS)
    out.append(('polygons', words(f, TEXPAL, 3840).reshape(15, 256), np.bincount(tex, minlength=256)))
    seen = []
    for i in range(N_OBJECTS):
        pal = struct.unpack_from('>I', f, OBJECTS + 16 * i + 12)[0]
        if pal in seen:
            continue
        seen.append(pal)
        rows = 1 if i == GUN else 15
        out.append(('gun' if i == GUN else 'objects', words(f, pal, rows * 32).reshape(rows, 32),
                    None))
    out.append(('sky', words(f, SKY, SKY_WORDS).reshape(1, -1), None))
    wt = np.frombuffer(f, np.uint8, 65536, WATER)
    out.append(('water', words(f, BRIGHTEN, WATER_ROWS * 256).reshape(WATER_ROWS, 256),
                np.bincount(wt, minlength=256)))
    return out


def model_hist(inputs, shares=SHARES):
    """The integer histogram: a table's budget TOTAL * share / (sum of shares * tables in its
    class); entry (r, i) gets budget * (R - r)^2 * count_i // (sum of (R - r)^2 * sum of counts)."""
    ssum = sum(shares.values())
    per = {}
    for cls, _, _ in inputs:
        per[cls] = per.get(cls, 0) + 1
    h = [0] * 4096
    for cls, cols, cnt in inputs:
        R, n = cols.shape
        c = [1] * n if cnt is None else [int(x) for x in cnt[:n]]
        rw = [(R - r) ** 2 for r in range(R)]
        d = sum(rw) * sum(c)
        if not d:
            continue
        b = TOTAL * shares[cls] // (ssum * per[cls])
        for r in range(R):
            for i in range(n):
                h[int(cols[r, i]) & 0xfff] += b * (rw[r] * c[i]) // d
    return h


def model_lab():
    """(L, a, b) of each 12-bit colour in 1/16 units, as the slave computes them."""
    ft = []
    x = 0
    for t in range(4096):
        if t <= FLIN_T:
            ft.append((t * FLIN_A + FLIN_B) >> 16)
            continue
        n = (t << 36) // 4095
        while (x + 1) ** 3 <= n:
            x += 1
        ft.append(x)
    out = []
    for c in range(4096):
        lin = [LIN[(c >> 8) & 15], LIN[(c >> 4) & 15], LIN[c & 15]]
        fx, fy, fz = (ft[min(4095, (sum(m * v for m, v in zip(row, lin)) + 2048) >> 12)]
                      for row in XYZ)
        out.append(((116 * fy - 65536) >> 8, (500 * (fx - fy)) >> 8, (200 * (fy - fz)) >> 8))
    return out


def model_dist(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2


def build(inputs=None, shares=SHARES):
    """The slave's palette (12-bit colour words of pens PEN0 on) and its 4096-entry map
    from 12-bit colour to pen."""
    inputs = inputs or model_inputs()
    h = model_hist(inputs, shares)
    u = [c for c in range(4096) if h[c]]
    w = h[:]
    pal = []
    for _ in range(min(POPULAR, len(u))):
        best = max(u, key=lambda c: (w[c], -c))
        pal.append(best)
        w[best] = 0
    L = model_lab()
    md = [min(model_dist(L[c], L[p]) for p in pal) for c in u]
    for _ in range(FARTHEST):
        j = max(range(len(u)), key=lambda j: (md[j], -j))
        if not md[j]:
            break
        pal.append(u[j])
        md = [min(m, model_dist(L[c], L[u[j]])) for m, c in zip(md, u)]
    lp = [L[p] for p in pal]
    mp = []
    for c in range(4096):
        ds = [model_dist(L[c], q) for q in lp]
        mp.append(PEN0 + ds.index(min(ds)))
    return pal, mp


def remap(mp, f=None, tables=TABLES):
    """The slave's remapped tables, in its layout (see src/palette.s): the walls (1024 pens
    each), floor, polygons, each Objects entry's pal (480), the sky and brightentab."""
    f = f or FLAT.read_bytes()
    out = bytearray()
    m = np.array(mp, np.uint8)
    for i in range(14):
        size = struct.unpack_from('>I', f, WALLCHUNKDATA + 8 * i + 4)[0]
        if not size:
            out += bytes(1024 * (14 - i))     # the slave leaves the rest clear
            break
        out += m[words((Path(tables) / f'wall{i:02d}').read_bytes(), 0, 1024) & 0xfff].tobytes()
    out += m[words(f, FLOORPAL, 3840) & 0xfff].tobytes()
    out += m[words(f, TEXPAL, 3840) & 0xfff].tobytes()
    for i in range(N_OBJECTS):
        pal = struct.unpack_from('>I', f, OBJECTS + 16 * i + 12)[0]
        out += m[words(f, pal, 480) & 0xfff].tobytes()
    out += m[words(f, SKY, SKY_WORDS) & 0xfff].tobytes()
    out += m[words(f, BRIGHTEN, BRIGHTEN_WORDS) & 0xfff].tobytes()
    return bytes(out)


def effects(pal, mp, f=None):
    """Pen to pen, 256 entries each: light beams (brightentab by colour), the water tint
    (red removed) and the pause screen (half brightness); other pens map to themselves."""
    f = f or FLAT.read_bytes()
    bt = words(f, BRIGHTEN, 4096)
    out = []
    for fn in (lambda c: int(bt[c]) & 0xfff, lambda c: c & 0x0ff, lambda c: (c & 0xeee) >> 1):
        t = list(range(256))
        for i, c in enumerate(pal):
            t[PEN0 + i] = mp[fn(c)]
        out.append(bytes(t))
    return out


# the slave's area (src/palette.s PA_*), as `ab3d.py palette` dumps it
PA_NPENS, PA_STATE, PA_PALETTE, PA_MAP, PA_LIGHT, PA_WALLS, PA_END = 0, 2, 4, 512, 4608, 5376, 58080


def cmd_check(args):
    """check DUMP: the slave's area against build, effects and remap, part by part."""
    d = Path(args[0]).read_bytes()
    if len(d) != PA_END:
        sys.exit(f'{args[0]}: {len(d)} bytes, not {PA_END}')
    pal, mp = build()
    want = {
        'state': struct.pack('>H', 2),
        'pens': struct.pack('>H', len(pal)),
        'palette': struct.pack(f'>{len(pal)}H', *pal),
        'map': bytes(mp),
        'effects': b''.join(effects(pal, mp)),
        'tables': remap(mp),
    }
    at = {'state': PA_STATE, 'pens': PA_NPENS, 'palette': PA_PALETTE, 'map': PA_MAP,
          'effects': PA_LIGHT, 'tables': PA_WALLS}
    bad = 0
    for name, w in want.items():
        got = d[at[name]:at[name] + len(w)]
        diff = [i for i in range(len(w)) if got[i] != w[i]]
        if diff:
            bad += 1
            print(f'{name}: {len(diff)} of {len(w)} bytes differ, the first at +{diff[0]} '
                  f'(area +{at[name] + diff[0]}): {got[diff[0]]:#04x}, the model {w[diff[0]]:#04x}')
        else:
            print(f'{name}: {len(w)} bytes as the model')
    print(f'{len(pal)} pens' + ('' if not bad else f'; {bad} parts differ'))
    sys.exit(1 if bad else 0)


# --- evaluation -----------------------------------------------------------------------------

def errors(hist, orig, shown):
    """Over the histogram's pixels: mean and p95 delta E, the shares over 2.3 and 5, the
    share shown exactly (12-bit colours) and the share off by over one 12-bit step in some
    channel, and the max delta E."""
    idx = np.nonzero(hist)[0]
    e = np.sqrt(((LAB12[idx] - lab(shown[idx] * 17)) ** 2).sum(-1))
    step = np.abs(orig[idx] - shown[idx]).max(-1)
    w = hist[idx] / hist[idx].sum()
    order = np.argsort(e)
    p95 = e[order][min(len(e) - 1, np.searchsorted(np.cumsum(w[order]), 0.95))]
    return dict(mean=float((e * w).sum()), p95=float(p95), jnd=float(w[e > 2.3].sum()),
                over5=float(w[e > 5].sum()), exact=float(w[step < 0.02].sum()),
                step=float(w[step > 1.02].sum()), max=float(e.max()))


def ramp_kept(src, assign, hist):
    """Brightness steps along the shade tables' columns (adjacent rows whose 12-bit colours
    differ) whose pens also differ, weighted by the frames' use of the two colours: the
    banding a palette adds."""
    kept = total = 0.0
    for tables in src.values():
        for _, cols, _ in tables:
            if cols.shape[0] < 2:
                continue
            a, b = cols[1:].ravel(), cols[:-1].ravel()
            w = (hist[a] + hist[b]) * (a != b)
            total += w.sum()
            kept += (w * (assign[a] != assign[b])).sum()
    return kept / total


def load_frames(paths):
    return {Path(p).stem: np.fromfile(p, '>u2').astype(np.int64).reshape(-1, 80, 96)
            for p in paths}


def palettes(hs, hall, k, fixed=None):
    """name -> (entries (n, 3) in 0-15 units, shown: each 12-bit colour's entry)."""
    out = {}
    ext = (lambda p: p) if fixed is None else (lambda p: np.concatenate([p, fixed]))
    pm, tag = wu(hs, k)
    for name, p in (('mean', pm), ('12-bit', np.round(pm)), ('mode', modes(hs, tag, k)),
                    ('mean +km', kmeans(hs, pm))):
        p = ext(p)
        out[f'static {k}{"+14" if fixed is not None else ""} {name}'] = (p, nearest(p))
    if fixed is None and hall is not None:
        pf, tf = wu(hall, k)
        out[f'frames {k} mode'] = (modes(hall, tf, k), None)
    return out


def cmd_census(args):
    paths = args or sorted(FRAMES.glob('*.bin'))
    frames = load_frames(paths)
    src = sources()
    union = static_union(src)
    allu = set().union(*union.values())
    print('Static: distinct 12-bit colours each class can show')
    for cls, u in union.items():
        print(f'  {cls:9s} {len(u):5d}')
    print(f'  all       {len(allu):5d}')
    hl = {L: np.bincount(f.ravel(), minlength=4096).astype(float) for L, f in frames.items()}
    hall = sum(hl.values())
    print('\nFrames: distinct colours, and pixels in no static table')
    print('  level frames distinct  outside')
    for L, h in list(hl.items()) + [('all', hall)]:
        nz = np.nonzero(h)[0]
        out = h[[c for c in nz if c not in allu]].sum() / h.sum()
        n = len(frames[L]) if L in frames else sum(len(f) for f in frames.values())
        print(f'  {L.upper():5s} {n:6d} {len(nz):8d}  {out:7.2%}')
    print('  share of the frames\' pixels whose colour each class can show')
    for cls, u in union.items():
        print(f'    {cls:9s} {hall[sorted(u)].sum() / hall.sum():6.1%}')

    hs = static_hist(src)
    orig = rgb(np.arange(4096)).astype(float)
    rows = []
    pal, mp = build()
    cands = {f'slave {len(pal)}': (rgb(np.array(pal)), np.array(mp) - PEN0)}
    for k in (FREE_SMALL, FREE_FULL):
        c = cube(k)
        cands[f'cube {k}'] = (c, nearest(c))
    cands.update(palettes(hs, hall, FREE_SMALL))
    cands.update(palettes(hs, None, FREE_SMALL, sprite_pens()))
    cands.update(palettes(hs, None, FREE_FULL))
    for name, (p, a) in cands.items():
        if a is None:
            a = nearest(p)
        shown = np.asarray(p, float)[a]
        rows.append((name, errors(hall, orig, shown),
                     {L: errors(h, orig, shown) for L, h in hl.items()}, ramp_kept(src, a, hall)))
        if name == f'static {FREE_SMALL} mode':
            dp, dq = dither_pairs(p)
            dshown = (p[dp] + p[dq]) / 2
            rows.append((name + ' dither', errors(hall, orig, dshown),
                         {L: errors(h, orig, dshown) for L, h in hl.items()},
                         ramp_kept(src, dp * 256 + dq, hall)))
    # one palette per level from its own frames, judged on that level only
    per = {}
    for L, h in hl.items():
        pl, tl = wu(h, FREE_SMALL)
        pl = modes(h, tl, FREE_SMALL)
        per[L] = errors(h, orig, pl[nearest(pl)])
    w = np.array([hl[L].sum() for L in hl]) / hall.sum()
    tot = {m: float(sum(per[L][m] * wi for L, wi in zip(hl, w))) for m in per[next(iter(hl))]}
    tot['max'] = max(per[L]['max'] for L in hl)
    rows.append((f'level {FREE_SMALL} mode', tot, per, float('nan')))

    print('\nError over all frames\' pixels: delta E mean and p95, shares over 2.3 and 5, shown'
          ' exactly, off by over one 12-bit step; brightness steps kept; max delta E')
    print(f'  {"palette":24s} {"mean":>5s} {"p95":>5s} {">2.3":>6s} {">5":>6s} {"exact":>6s}'
          f' {">1step":>6s} {"ramp":>6s} {"max":>5s}')
    for name, t, per, ramp in rows:
        print(f'  {name:24s} {t["mean"]:5.2f} {t["p95"]:5.2f} {t["jnd"]:6.1%} {t["over5"]:6.1%}'
              f' {t["exact"]:6.1%} {t["step"]:6.1%} {ramp:6.1%} {t["max"]:5.1f}')
    print('\nMean delta E per level')
    print('  ' + ' ' * 24 + ''.join(f'{L.upper():>6s}' for L in hl))
    for name, t, per, ramp in rows:
        print(f'  {name:24s}' + ''.join(f'{per[L]["mean"]:6.2f}' for L in hl))


def cmd_images(args):
    from PIL import Image
    level, n, out = args[0], int(args[1]), Path(args[2])
    f = load_frames([FRAMES / f'{level}.bin'])[level][n]
    pal, mp = build()
    hs = static_hist()
    pm, tag = wu(hs, FREE_SMALL)
    pw = modes(hs, tag, FREE_SMALL)
    c = cube(FREE_SMALL)
    views = [rgb(f), rgb(np.array(pal))[np.array(mp)[f] - PEN0], pw[nearest(pw)[f]],
             c[nearest(c)[f]]]
    img = np.concatenate([np.clip(np.round(v * 17), 0, 255).astype(np.uint8) for v in views], 1)
    Image.fromarray(img).resize((img.shape[1] * 4, img.shape[0] * 4), Image.NEAREST).save(out)
    print(f'{out}: original | slave {len(pal)} | static {FREE_SMALL} mode | cube {FREE_SMALL}')


if __name__ == '__main__':
    cmds = {'census': cmd_census, 'images': cmd_images, 'check': cmd_check}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](sys.argv[2:])
