"""Native twins for poly_fill_040 (step 5) against Polygon's edge tables, walker and fills.

  opt20_poly_test.py OUT

Both sides run inside the game process. Per side the guest writes the six bytes at $60d92
(the original MOVEA/LEA, or the slave JMP) and at $6c514 (the original side runs the game's
own ScanFillDown loop, the candidate side the production sfd_span_040), pushes the caches,
points the current screen at a test buffer, sets the colour, clears the edge tables, copies
the case's vertex list between guard vertices and enters at $60d92 as Polygon reaches it:
A0 vertices, D0.w count, A4 the top vertex's y, D5.w/D6.w bottom/top row, the caller's A0
on the stack. The guest compares the whole buffer between the sides; the host compares A0,
SP and the SP cell ($62a44), and checks the candidate's rows against an independent model
of the original (doubled list, GenLeft/GenRight, walker, line fill). Cases cover convex
polygons of 1-32 vertices in both windings, flat and vertical edges, x-major edges, one-row
polygons, climbing chains (nothing drawn), x beyond 319 (the original loop), and inputs that
run the original code: more than 32 vertices, chains that do not reach the bottom row or end
on different rows, rows outside 0-199. Negative controls must be rejected.
"""
import os, sys, json, struct, subprocess, re, math
from pathlib import Path
from replay_flight import ROOT, run
out = Path(sys.argv[1]).resolve(); os.chdir(ROOT)

PLANE = 8000; ROW = 40; REGION = 81920; SEED = 0x2468ace1
VMAX = 48; GUARD = 64          # vertex slots per copy, guard vertices on each side
GUARD_Y = -1000                # any step onto a guard vertex climbs


def lcg(seed, n):
    r = []
    for _ in range(n):
        seed = (((seed << 3) | (seed >> 29)) + 0x13ab) & 0xffffffff; r.append(seed)
    return r


image = b''.join(struct.pack('>I', x) for x in lcg(SEED, REGION // 4))
s16 = lambda v: ((v + 0x8000) & 0xffff) - 0x8000
s32 = lambda v: ((v + 0x80000000) & 0xffffffff) - 0x80000000


def top_index(vs):
    """Polygon's top vertex: the last one with the smallest y."""
    t = 0
    for i, (_, y) in enumerate(vs):
        if y <= vs[t][1]: t = i
    return t


def case(vs, colour, **kw):
    t = top_index(vs)
    c = dict(v=vs, colour=colour, t=t, d5=max(y for _, y in vs), d6=min(y for _, y in vs))
    c.update(kw); return c


def model(c, recip, half=True, vertex_bottom=True):
    """The original's lines: [(row, left x, right x)], or 'fail', or None (another path)."""
    vs = c['v']; n = len(vs); dup = vs + vs; d5 = s16(c['d5'])

    def gen(start, step):
        i = start; x0, y0 = dup[i]; recs = []
        while True:
            j = i + step
            if not 0 <= j < 2 * n: return None
            x1, y1 = dup[j]; dx = s16(x1 - x0); dy = s16(y1 - y0)
            if dy < 0: return 'fail'
            if dy:
                if dy >= len(recip): return None
                dx2 = s16(2 * dx); slope = s32(dx2 * recip[dy]); x = ((x0 & 0xffff) << 16) | 0x8000
                if s16(abs(dx2)) >= s16(2 * dy) and half: x = (x + (slope >> 1)) & 0xffffffff
                recs.append([dy, x, slope & 0xffffffff])
            i = j; x0, y0 = dup[i]
            if s16(y0) >= d5: recs.append([0, (x0 & 0xffff) << 16, 0]); return recs

    L = gen(c['t'] + n, -1)
    if L in (None, 'fail'): return L
    R = gen(c['t'], 1)
    if R in (None, 'fail'): return R
    if len(L) > 17 or len(R) > 17: return None   # beyond the game's edge tables
    if sum(r[0] for r in L) != sum(r[0] for r in R): return None
    out = []; y = s16(c['d6']); li = ri = 0
    a2, a4 = L[0][1], L[0][2]; a3, a5 = R[0][1], R[0][2]

    def draw(k):
        nonlocal a2, a3, y
        for _ in range(k):
            out.append((y, a2 >> 16, a3 >> 16)); a2 = (a2 + a4) & 0xffffffff; a3 = (a3 + a5) & 0xffffffff; y += 1
    if L[0][0] | R[0][0]:
        while True:
            cl, cr = L[li][0], R[ri][0]
            if cl == cr:
                draw(cl); li += 1; ri += 1
                a2, a4 = L[li][1], L[li][2]
                if not L[li][0]: break
                a3, a5 = R[ri][1], R[ri][2]
                if not R[ri][0]: break
            elif cl < cr:
                R[ri][0] -= cl; draw(cl); li += 1; a2, a4 = L[li][1], L[li][2]
                if not L[li][0]: break
            else:
                L[li][0] -= cr; draw(cr); ri += 1; a3, a5 = R[ri][1], R[ri][2]
                if not R[ri][0]: break
    if vertex_bottom: out.append((y, L[li][1] >> 16, R[ri][1] >> 16))
    else: out.append((y, a2 >> 16, a3 >> 16))
    if any(not 0 <= r <= 199 for r, _, _ in out): return None
    return out


def paint(lines, colour, right_exclusive=False):
    m = bytearray(image); kinds = dict(lines=0, skip=0, beyond=0, narrow=0, wide=0)
    for row, xl, xr in lines:
        kinds['lines'] += 1
        if xr < xl: kinds['skip'] += 1; continue
        if xr > 319: kinds['beyond'] += 1
        l, r = xl >> 5, xr >> 5; assert r - l <= 9, (xl, xr)
        kinds['narrow' if r == l else 'wide'] += 1
        for li in range(l, r + 1):
            lo = xl & 31 if li == l else 0; hi = xr & 31 if li == r else 31
            if right_exclusive and li == r: hi -= 1
            mask = 0
            for bit in range(lo, hi + 1): mask |= 1 << (31 - bit)
            for p in range(8):
                o = p * PLANE + row * ROW + 4 * li; v = struct.unpack_from('>I', m, o)[0]
                v = (v | mask) if (colour >> p) & 1 else (v & ~mask & 0xffffffff)
                struct.pack_into('>I', m, o, v)
    return m, kinds


def band(c):
    lo = max(0, min(s16(c['d6']), min(y for _, y in c['v']))); hi = min(201, max(y for _, y in c['v']) + 1)
    return lo, hi


def bands(c):
    lo, hi = band(c); return [(p * PLANE + lo * ROW, (hi - lo + 1) * ROW) for p in range(8)]


colours = [0, 255, 1, 0x80, 0x55, 0xaa, 0x0f, 0xf0, 0x3c, 0x7e, 0x81, 0x13, 0xc9, 0x6b, 0xfe, 0x01]
cases = []
# Hand-made shapes, each in both windings.
shapes = [
    [(10, 10), (100, 10), (100, 60), (10, 60)],              # rectangle
    [(160, 5), (300, 120), (20, 140)],                       # triangle
    [(50, 20), (51, 180), (49, 100)],                        # thin, nearly vertical
    [(0, 50), (319, 51), (160, 52)],                         # wide, x-major edges
    [(5, 100), (300, 100), (200, 110), (40, 110)],           # flat top and bottom
    [(30, 30), (30, 90), (30, 60)],                          # vertical line
    [(64, 70), (64, 70), (64, 70)],                          # one point, repeated
    [(10, 77), (200, 77)],                                   # one row, two vertices
    [(100, 2), (150, 40), (150, 41), (100, 80), (50, 41), (50, 40)],
    [(0, 0), (319, 0), (319, 199), (0, 199)],                # full screen
    [(0, 120), (319, 121), (300, 199), (2, 198)],            # bottom rows
    [(31, 10), (32, 10), (64, 50), (63, 50)],                # long boundaries
    [(160, 100), (161, 101), (159, 102)],                    # tiny
    [(20, 3), (40, 3), (60, 3), (80, 30), (10, 30)],         # three on the top row
    [(5, 5), (300, 6), (6, 7)],                              # sliver
    [(200, 10), (260, 40), (250, 100), (210, 140), (150, 120), (140, 50)],
]
for i, vs in enumerate(shapes):
    cases.append(case(vs, colours[i % 16], kind='shape'))
    cases.append(case(vs[::-1], colours[(i + 5) % 16], kind='shape-reversed'))
cases.append(case([(77, 33)], 0x5a, kind='one-vertex'))
# Random convex polygons (hull of random points), both windings, 3-32 vertices.
for i in range(140):
    rs = lcg(0x5000 + i, 100)
    n0 = [3, 3, 4, 4, 5, 6, 8, 12, 20, 40][i % 10]
    w = [319, 160, 40, 8][i % 4]; h = [90, 50, 24, 6][(i // 4) % 4]
    cx = rs[0] % (320 - w) if w < 320 else 0; cy = rs[1] % (200 - h) if h < 200 else 0
    pts = sorted({(cx + rs[2 + 2 * k] % (w + 1), cy + rs[3 + 2 * k] % (h + 1)) for k in range(n0)})
    if n0 == 40:  # many points on an ellipse: 20-32 hull vertices
        pts = sorted({(cx + w // 2 + round(w / 2 * math.cos(2 * math.pi * k / (16 + i % 17))), cy + h // 2 + round(h / 2 * math.sin(2 * math.pi * k / (16 + i % 17)))) for k in range(16 + i % 17)})
    hull = []
    for half in (pts, pts[::-1]):
        part = []
        for p in half:
            while len(part) >= 2 and (part[-1][0] - part[-2][0]) * (p[1] - part[-2][1]) - (part[-1][1] - part[-2][1]) * (p[0] - part[-2][0]) <= 0: part.pop()
            part.append(p)
        hull += part[:-1]
    if len(hull) < 3 or len(hull) > 32: continue
    r = rs[90] % len(hull); hull = hull[r:] + hull[:r]
    cases.append(case(hull if i % 2 else hull[::-1], rs[91] % 256, kind='convex'))
# Climbing chains: nothing is drawn (left or right chain, early or late).
for i, vs in enumerate([[(10, 10), (100, 50), (60, 30), (20, 80)], [(10, 10), (20, 80), (60, 30), (100, 50)],
                        [(50, 5), (90, 40), (80, 30), (85, 90), (20, 60)], [(50, 5), (20, 60), (85, 90), (80, 30), (90, 40)],
                        [(100, 100), (150, 120), (140, 110), (145, 115), (120, 130)], [(5, 5), (6, 50), (7, 20), (8, 60), (3, 40)]]):
    cases.append(case(vs, colours[i], kind='climb'))
# x beyond 319: the run continues in the original loop.
for i, vs in enumerate([[(300, 20), (345, 40), (330, 60), (290, 50)], [(310, 100), (330, 100), (330, 110), (310, 110)],
                        [(250, 150), (321, 150), (300, 170)], [(319, 30), (340, 31), (320, 60)]]):
    cases.append(case(vs, colours[i + 3], kind='beyond'))
# The top row taken from D6 rather than the top vertex.
cases.append(case([(40, 20), (90, 30), (60, 50)], 0x33, d6=17, kind='d6-above'))
cases.append(case([(140, 60), (190, 70), (160, 90)], 0xcc, d6=65, kind='d6-below'))
# Input that runs the original code.
ring = lambda n, cx, cy, rx, ry: [(cx + round(rx * math.cos(2 * math.pi * k / n)), cy + round(ry * math.sin(2 * math.pi * k / n))) for k in range(n)]
# The most vertices poly_fill_040 takes, and a chain of 16 edges (the tables' limit).
cases.append(case(ring(17, 160, 100, 90, 80), 0x77, kind='ring-17'))
cases.append(case([(10, 10), (200, 190)] + [(150 - 9 * k, 180 - 10 * k) for k in range(15)], 0x3b, kind='fan-16'))
cases.append(case(ring(18, 160, 100, 90, 80), 0x99, kind='original-18'))
cases.append(case(ring(32, 100, 100, 60, 90), 0x66, kind='original-32'))
cases.append(case([(100, 20), (180, 60)] + [(180 - 5 * k, 60) for k in range(1, 21)] + [(60, 50), (70, 30)], 0x5d, kind='original-24'))
cases.append(case([(20, 40), (80, 40), (60, 40)], 0x21, d5=45, kind='original-no-bottom'))
cases.append(case([(10, 10), (60, 30), (30, 25)], 0x42, d5=24, kind='original-ends-differ'))
cases.append(case([(20, -3), (60, 10), (30, 12)], 0x18, kind='original-row-negative'))
cases.append(case([(20, 190), (60, 198), (30, 201)], 0x81, kind='original-row-200'))
cases.append(case([(20, 10), (60, 20), (30, 30)], 0x81, d6=-2, kind='original-d6-negative'))


def capture(cmd, dump, bases, hs, out):
    b = bases[0]; code = b + 0x8000
    orig = hs[0]['bytes'][0x60d92:0x60d98]; assert orig.hex() == '244847f20400', orig.hex()
    sorig = hs[0]['bytes'][0x6c514:0x6c51a]; assert sorig.hex() == '4dfa000ad1fc', sorig.hex()
    patch = dump('poly-patch.bin', b + 0x60d92, 6); assert patch[:2].hex() == '4ef9', patch.hex()
    spatch = dump('sfd-patch.bin', b + 0x6c514, 6); assert spatch[:2].hex() == '4ef9', spatch.hex()
    recip = struct.unpack('>512h', dump('recip.bin', b + 0x62e70, 1024))
    rows = struct.unpack('>200h', dump('rows.bin', b + 0x7cd10, 400)); assert rows == tuple(40 * y for y in range(200)), rows
    exp = {i: model(c, recip) for i, c in enumerate(cases)}
    n = len(cases); wsize = sum(l for c in cases for _, l in bands(c))
    a = [' mc68040', f' org ${code:x}', f' move.l #{3 * REGION},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,rgn',
         ' move.l #$20000,d1', ' move.l 4.w,a6', ' jsr -216(a6)', ' move.l d0,largest',
         f' move.w ${b + 0x71608:x},d0', f' lea ${b + 0x4ce00:x},a0', ' move.l rgn(pc),(a0,d0.w)']
    wo = 0
    for i, c in enumerate(cases):
        vs = c['v']; nv = len(vs); assert nv <= VMAX
        for side in (0, 1):
            slot = (i * 2 + side) * 72
            if side == 0:
                a += [f' move.l #${orig[:4].hex()},${b + 0x60d92:x}', f' move.w #${orig[4:].hex()},${b + 0x60d96:x}',
                      f' move.l #${sorig[:4].hex()},${b + 0x6c514:x}', f' move.w #${sorig[4:].hex()},${b + 0x6c518:x}']
            else:
                a += [f' move.l #${patch[:4].hex()},${b + 0x60d92:x}', f' move.w #${patch[4:].hex()},${b + 0x60d96:x}',
                      f' move.l #${spatch[:4].hex()},${b + 0x6c514:x}', f' move.w #${spatch[4:].hex()},${b + 0x6c518:x}']
            a += [' cpusha bc', ' move.l rgn(pc),a0', f' move.l #${SEED:x},d0', f' move.w #{REGION // 4 - 1},d7', f'init{i}_{side}:', ' rol.l #3,d0', ' add.l #$13ab,d0',
                  ' move.l d0,(a0)+', f' dbf d7,init{i}_{side}',
                  f' lea ${b + 0x62afc:x},a0', f' move.w #{884 // 4 - 1},d7', f'clr{i}_{side}:', ' clr.l (a0)+', f' dbf d7,clr{i}_{side}',
                  f' lea vbuf,a0', f' move.w #{2 * GUARD + 2 * VMAX - 1},d7', f'grd{i}_{side}:', f' move.l #${GUARD_Y & 0xffff | 0x00400000:x},(a0)+', f' dbf d7,grd{i}_{side}',
                  f' lea vbuf+{4 * GUARD},a0', f' lea vtx{i},a1', f' move.w #{nv - 1},d7', f'cpy{i}_{side}:', ' move.l (a1)+,(a0)+', f' dbf d7,cpy{i}_{side}',
                  f' move.b #{c["colour"]},${b + 0x55cc8:x}', f' move.l #$5e5e5e5e,${b + 0x62a44:x}',
                  f' pea ret{i}_{side}', ' move.l #$a0c0ffee,-(sp)',
                  f' lea vbuf+{4 * GUARD},a0', f' lea vbuf+{4 * GUARD + 4 * c["t"] + 2},a4',
                  f' move.l #${0x5a5a0000 | nv:x},d0', ' move.l #$11111111,d1', ' move.l #$22222222,d2', ' move.l #$33333333,d3',
                  ' move.l #$44444444,d4', f' move.l #${0x7e7e0000 | (c["d5"] & 0xffff):x},d5', f' move.l #${0x6d6d0000 | (c["d6"] & 0xffff):x},d6',
                  ' move.l #$77777777,d7', ' move.l #$a1a1a1a1,a1', ' move.l #$a2a2a2a2,a2', ' move.l #$a3a3a3a3,a3', ' move.l #$a5a5a5a5,a5',
                  ' move.l #$a6a6a6a6,a6', f' move.w #${0x1f if i & 1 else 0x00:x},ccr', f' jmp ${b + 0x60d92:x}',
                  f'ret{i}_{side}:', f' movem.l d0-d7/a0-a6,regs+{slot}', f' move.w ccr,regs+{slot + 60}', f' move.l sp,regs+{slot + 64}',
                  f' move.l ${b + 0x62a44:x},regs+{slot + 68}',
                  ' move.l rgn(pc),a1', f' lea {REGION * (side + 1)}(a1),a2', f' move.w #{REGION // 4 - 1},d7', f'save{i}_{side}:', ' move.l (a1)+,(a2)+', f' dbf d7,save{i}_{side}']
        a += [' move.l rgn(pc),a0', f' lea {REGION}(a0),a1', f' lea {2 * REGION}(a0),a2', ' moveq #0,d0', f' move.w #{REGION // 4 - 1},d7', f'cmp{i}:', ' cmpm.l (a1)+,(a2)+',
              f' beq.s eq{i}', ' addq.l #1,d0', f'eq{i}:', f' dbf d7,cmp{i}', f' move.l d0,diffs+{i * 4}']
        a += [f' move.l #{sum(l for _, l in bands(c))},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', f' move.l d0,wtab+{4 * i}',
              ' beq.l nomem', ' move.l d0,a2']
        for p, (o, ln) in enumerate(bands(c)):
            a += [' move.l rgn(pc),a1', f' add.l #{2 * REGION + o},a1', f' move.w #{ln // 4 - 1},d7',
                  f'win{i}_{p}:', ' move.l (a1)+,(a2)+', f' dbf d7,win{i}_{p}']
    a += ['nomem:', 'finished: bra.s finished', ' cnop 0,4', 'largest: dc.l 0', 'rgn: dc.l 0', f'regs: ds.b {n * 144}', f'diffs: ds.l {n}', f'wtab: ds.l {n}',
          f'vbuf: ds.l {2 * GUARD + 2 * VMAX}']
    for i, c in enumerate(cases):
        a += [f'vtx{i}:'] + [f' dc.w {x},{y}' for x, y in c['v']]
    src = out / 'fixture.s'; src.write_text('\n'.join(a) + '\n'); binary = out / 'fixture.bin'; listing = out / 'fixture.lst'
    subprocess.run(['bash', '-c', '. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"', 'fixture', str(src), str(binary), str(listing)], check=True)
    labels = {k: int(re.search(r'^' + k + r'\s+A:([0-9A-Fa-f]+)', listing.read_text(), re.M)[1], 16) for k in ['finished', 'largest', 'rgn', 'regs', 'diffs', 'wtab']}
    blob = binary.read_bytes(); assert code + len(blob) < b + 0x4d000, 'fixture overlaps game code'
    cmd('delete breakpoints'); cmd('monitor tfxreg 16 2700')
    for off in range(0, len(blob), 32): cmd(f'monitor tfxmem {code + off:x} {blob[off:off + 32].hex()}')
    cmd(f'monitor tfxreg 17 {code:x}'); cmd(f'break *{labels["finished"]:#x}'); reply = cmd('continue')
    assert f'0x{labels["finished"]:08x}' in reply, reply[-1000:]
    cmd(f'monitor tfxsync {labels["largest"]:x} {8 + n * 152}')
    largest = int.from_bytes(dump('largest.bin', labels['largest'], 4), 'big')
    wtab = struct.unpack(f'>{n}I', dump('wtab.bin', labels['wtab'], n * 4)); assert all(wtab), (hex(largest), wtab.index(0))
    regs = dump('regs.bin', labels['regs'], n * 144); diffs = struct.unpack(f'>{n}I', dump('diffs.bin', labels['diffs'], n * 4))
    windows = b''
    for i, c in enumerate(cases):
        ln = sum(l for _, l in bands(c)); cmd(f'monitor tfxsync {wtab[i]:x} {ln}'); windows += dump(f'w{i}.bin', wtab[i], ln)

    def verify(c, e, ro, rc, wins, diff, half=True, vertex_bottom=True, right_exclusive=False):
        R = lambda r, k: struct.unpack_from('>I', r, 4 * k)[0]
        v = dict(region_diff_longs=diff, a0=R(ro, 8) == R(rc, 8) == 0xa0c0ffee, sp=ro[64:68] == rc[64:68], sp_cell=ro[68:72] == rc[68:72])
        if not (half and vertex_bottom): e = model(c, recip, half, vertex_bottom)
        if e is not None:
            m, _ = paint([] if e == 'fail' else e, c['colour'], right_exclusive)
            v['model_rows'] = wins == b''.join(bytes(m[o:o + ln]) for o, ln in bands(c))
        return v

    def passed(v): return v['region_diff_longs'] == 0 and all(v[k] for k in v if k != 'region_diff_longs')

    results = []; slices = []; wo = 0
    for i, c in enumerate(cases):
        ln = sum(l for _, l in bands(c)); slices.append((wo, ln)); wo += ln
        ro, rc = regs[i * 144:i * 144 + 72], regs[i * 144 + 72:i * 144 + 144]
        v = verify(c, exp[i], ro, rc, windows[wo - ln:wo], diffs[i])
        e = exp[i]; kinds = paint(e, c['colour'])[1] if isinstance(e, list) else {}
        outcome = 'original-code' if e is None else 'nothing' if e == 'fail' else 'drawn'
        results.append(dict(kind=c['kind'], n=len(c['v']), colour=c['colour'], outcome=outcome, **v, ok=passed(v), lines=kinds,
                            sp_cell_value=ro[68:72].hex(), stack=struct.unpack_from('>I', ro, 64)[0]))
    # Negative controls on a drawn convex case with x-major edges: a wrong bitplane byte, a wrong
    # A0, a model without the x-major half step, a model whose bottom line follows the edges, and
    # a model whose right edge is exclusive.
    k = next(i for i, r in enumerate(results) if r['kind'] == 'convex' and r['outcome'] == 'drawn' and r['lines']['lines'] > 40
             and r['lines']['skip'] == 0 and all(paint(model(cases[i], recip, **mk), cases[i]['colour'])[0] != paint(exp[i], cases[i]['colour'])[0]
                                                 for mk in (dict(half=False), dict(vertex_bottom=False))))
    c = cases[k]; ro, rc = regs[k * 144:k * 144 + 72], regs[k * 144 + 72:k * 144 + 144]; o, ln = slices[k]; w = windows[o:o + ln]
    lo, _ = band(c); row = exp[k][len(exp[k]) // 2]
    controls = {}
    bad = bytearray(w); bad[(row[0] - lo) * ROW + (row[1] >> 3)] ^= 0x80 >> (row[1] & 7); controls['byte'] = not passed(verify(c, exp[k], ro, rc, bytes(bad), diffs[k]))
    badr = bytearray(rc); badr[35] ^= 1; controls['a0'] = not passed(verify(c, exp[k], ro, bytes(badr), w, diffs[k]))
    controls['no_half_step'] = not passed(verify(c, exp[k], ro, rc, w, diffs[k], half=False))
    controls['edge_bottom'] = not passed(verify(c, exp[k], ro, rc, w, diffs[k], vertex_bottom=False))
    controls['right_exclusive'] = not passed(verify(c, exp[k], ro, rc, w, diffs[k], right_exclusive=True))
    tot = {key: sum(r['lines'].get(key, 0) for r in results) for key in ('lines', 'skip', 'beyond', 'narrow', 'wide')}
    outcomes = {o_: sum(r['outcome'] == o_ for r in results) for o_ in ('drawn', 'nothing', 'original-code')}
    summary = dict(largest_free=largest, cases=n, passed=sum(r['ok'] for r in results), outcomes=outcomes, lines=tot,
                   kinds={k_: sum(r['kind'] == k_ for r in results) for k_ in sorted({r['kind'] for r in results})},
                   vertices=[min(r['n'] for r in results), max(r['n'] for r in results)], control_case=k, negative_controls_rejected=controls)
    (out / 'results.json').write_text(json.dumps(dict(summary, results=results), indent=1))
    assert summary['passed'] == n, [r for r in results if not r['ok']][:3]
    assert all(controls.values()), controls
    print('PASS', json.dumps(summary), flush=True)


v = dict(executable='tfx.020', custom3=3, custom4=18, swap=0x19fc, extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040', out, Path(str(out) + '-seed'), capture, v)
