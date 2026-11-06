"""Native twins for scan_fill_040 (step 3b) against the original ScanFillDown.

  opt20_clip_test.py OUT        (env DELTA_LISTING = slave listing)

Both sides run in the game process at a swap stop, drawing into the live fast
buffer from the same background pattern. The original side executes ScanFillDown's
first instruction (MOVE.L (SP)+,cell) in a stub and continues at $6c4f8; the
candidate calls the patched entry with a crafted clip table and predicted-frame
state. Per case the guest saves D0/D7/A2/A3, the return cell and every touched row
of all eight planes. The host requires equal registers and cell, the candidate to
equal the original outside each row's opaque run and to keep the background inside
it. Negative controls corrupt a hidden bit, a visible bit and a register.
"""
import os, sys, json, struct, subprocess, re, random
from pathlib import Path
from replay_flight import ROOT, run
out = Path(sys.argv[1]).resolve(); os.chdir(ROOT)
listing = Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
def sym(n): return int(re.search(r'^' + re.escape(n) + r'\s+00:([0-9A-Fa-f]+)', listing, re.M)[1], 16)

NONE = 0x7fff; MAXN = 40; SLOT = 20 + MAXN * 40 * 8
r = random.Random(30311)
def table(kind):
    rows = [(NONE, NONE)] * 200
    for y in range(95, 150):
        if kind == 0: ol, orr = 40 + y % 37, min(319, 40 + y % 37 + 50 + (y * 7) % 120)
        elif kind == 1: ol, orr = 0, 100 + y                 # touches the left edge
        elif kind == 2: ol, orr = 320 - (y - 60) * 2, 319     # touches the right edge
        else: ol, orr = (96, 223) if y % 3 else (NONE, NONE)  # unclipped rows inside the band
        rows[y] = (ol, orr)
    return rows
tables = [table(k) for k in range(4)]
def y_range(t):
    ys = [y for y, (a, b) in enumerate(t) if a != NONE]
    return ys[0], ys[-1]

cases = []
for i in range(160):
    y = [80, 94, 95, 100, 120, 140, 149, 150, 175, 0][i % 10]
    n = [1, 2, 7, 30, 40, 0, 25][i % 7]
    if y + n > 200: n = 200 - y
    xl = r.choice([0, 3, 31, 32, 60, 95, 96, 150, 223, 224, 300]) << 16 | r.getrandbits(16)
    xr = r.choice([0, 31, 40, 95, 128, 200, 223, 250, 319]) << 16 | r.getrandbits(16)
    dl = r.choice([0, 1 << 16, -(1 << 16), 0x8000, -0x18000, 0x2000])
    dr = r.choice([0, 1 << 16, -(1 << 16), 0x8000, 0x18000, -0x2000])
    if i % 11 == 0: xl = xr + (8 << 16)                     # empty spans (right < left)
    # Keep every drawn row inside the screen, as the polygon clipper does.
    while any(not (0 <= (xl + k * dl) >> 16 <= 319 and 0 <= (xr + k * dr) >> 16 <= 319) for k in range(max(n, 1))):
        if xl >> 16 > 319: xl = 319 << 16
        dl = int(dl / 2); dr = int(dr / 2)
    cases.append(dict(table=i % 4, y=y, n=n, xl=xl & 0xffffffff, xr=xr & 0xffffffff, dl=dl & 0xffffffff, dr=dr & 0xffffffff,
                      colour=[1, 7, 15, 31, 64, 127, 128, 200, 254, 255][i % 10]))

SKIP = bool(os.environ.get('SKIP'))
if SKIP:
    # Whole-call skip: trapezoids inside table 1's runs (x 0..100+y over rows 95-149),
    # including edges exactly on the run end, one pixel past it and rows past the band.
    h = random.Random(4711)
    for i in range(48):
        y = h.randint(95, 140); n = h.randint(1, 9)
        if i % 8 == 7: y, n = 145, 8                           # last rows leave the band
        xl = h.randint(0, 40) << 16; dl = h.choice([0, 0x4000, -0x4000]) if xl else 0
        end = 100 + y + (1 if i % 8 == 3 else 0)               # past the run: must draw
        xr = h.choice([h.randint(41, 90), end if i % 4 == 3 else 95]) << 16; dr = 0
        if i % 8 == 5: xl, xr = (60 << 16), (52 << 16)          # empty spans, shared longword
        cases.append(dict(table=1, y=y, n=n, xl=xl & 0xffffffff, xr=xr & 0xffffffff, dl=dl & 0xffffffff, dr=dr,
                          colour=[1, 7, 15, 31, 64, 127, 128, 200, 254, 255][i % 10]))

def lcg(seed, n):
    o = []
    for _ in range(n):
        o.append(seed); seed = (((seed << 3) | (seed >> 29)) + 0x13ab) & 0xffffffff
    return o
background = b''.join(struct.pack('>I', x) for x in lcg(0x5a5a1234, 16000))
def rows_of(c): return c['y'], c['y'] + c['n']
def slot(c): return 20 + c['n'] * 40 * 8
offsets = []
_o = 0
for _c in cases:
    offsets.append(_o); _o += 2 * slot(_c)
TOTAL = _o
def runmask(ol, orr): return 0 if ol == NONE else ((1 << (orr - ol + 1)) - 1) << (319 - orr)

def verify(c, o, k, i):
    lo, hi = rows_of(c); t = tables[c['table']]; y0, y1 = y_range(t); size = (hi - lo) * 40
    clip_path = c['n'] > 0 and hi > y0 and lo <= y1
    bad = hidden = drawn = outside = differ = 0; same = []; skipped = []
    for p in range(8):
        for row in range(lo, hi):
            m = runmask(*t[row]) if clip_path else 0
            off = 20 + p * size + (row - lo) * 40
            O = int.from_bytes(o[off:off + 40], 'big'); K = int.from_bytes(k[off:off + 40], 'big')
            B = int.from_bytes(background[p * 8000 + row * 40:p * 8000 + row * 40 + 40], 'big')
            if SKIP:
                # Either the original exactly, or (skipped) the background with the
                # original drawing only inside the opaque runs.
                full = (1 << 320) - 1; m = runmask(*t[row])
                same.append(K == O); skipped.append(K == B)
                outside += bin((O ^ B) & ~m & full).count('1'); differ += bin(K ^ O).count('1')
            else:
                bad += bin((K ^ B) & m).count('1') + bin((K ^ O) & ~m & ((1 << 320) - 1)).count('1')
            hidden += bin((O ^ B) & m).count('1'); drawn += bin(O ^ B).count('1')
    # The return cell holds each side's own return address.
    cells = (int.from_bytes(o[16:20], 'big'), int.from_bytes(k[16:20], 'big')) == (RET[f'ret{i}_0'], RET[f'ret{i}_1'])
    extra = {}
    if SKIP:
        is_same = all(same); is_skip = all(skipped) and not is_same
        bad = 0 if is_same else (outside if is_skip else differ)
        extra = dict(skipped=is_skip)
    return dict(regs=o[:16] == k[:16] and cells, bad_bits=bad, hidden_bits=hidden, drawn_bits=drawn, clip_path=clip_path, **extra)

def capture(cmd, dump, bases, hs, out):
    b = bases[0]; code = b + 0x8000
    sb = int.from_bytes(dump('swap-target.bin', b + 0x19fe, 4), 'big') - sym('do_swap_screen')
    assert dump('scan-patch.bin', b + 0x6c4f2, 2) == bytes.fromhex('4ef9')
    assert hs[0]['bytes'][0x6c4f2:0x6c4f4] == bytes.fromhex('23df')
    cmd(f'monitor tfxsync {sb + sym("fast_buf"):x} 4')
    fast = int.from_bytes(dump('fast.bin', sb + sym('fast_buf'), 4), 'big'); assert fast
    cell = b + 0x6c4c0; S = lambda n: sb + sym(n)
    a = [' mc68040', f' org ${code:x}', f' move.l #{TOTAL},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,mem']
    for i, c in enumerate(cases):
        y0, y1 = y_range(tables[c['table']]); lo, hi = rows_of(c)
        for side in range(2):
            a += [f' lea ${fast:x},a0', ' move.l #$5a5a1234,d0', ' move.w #15999,d7', f'bg{i}_{side}:', ' move.l d0,(a0)+', ' rol.l #3,d0',
                  ' add.l #$13ab,d0', f' dbf d7,bg{i}_{side}']
            # Clip state of a predicted frame: the candidate makes no decision itself.
            a += [f' st ${S("clip_decided"):x}', f' move.w #{y0},${S("clip_y0"):x}', f' move.w #{y1},${S("clip_y1"):x}',
                  f' lea table{c["table"]}(pc),a0', f' move.l a0,${S("clip_rows_ptr"):x}',
                  f' moveq #{c["colour"] - 256 if c["colour"] > 127 else c["colour"]},d0', f' move.l #${c["n"] | 0x12340000:x},d7',
                  f' move.l #{c["y"]},a6', f' move.l #${c["xl"]:x},a2', f' move.l #${c["xr"]:x},a3',
                  f' move.l #${c["dl"]:x},a4', f' move.l #${c["dr"]:x},a5', f' jsr {"orig" if side == 0 else "cand"}', f'ret{i}_{side}:',
                  f' move.w #{NONE},${S("clip_y0"):x}', f' sf ${S("clip_decided"):x}',
                  ' move.l mem(pc),a1', f' add.l #{offsets[i] + side * slot(c)},a1', ' move.l d0,(a1)+', ' move.l d7,(a1)+', ' move.l a2,(a1)+',
                  ' move.l a3,(a1)+', f' move.l ${cell:x},(a1)+']
            if hi > lo:
                a += [f' lea ${fast + lo * 40:x},a0', ' moveq #7,d6', f'pl{i}_{side}:', ' move.l a0,a2', f' move.w #{(hi - lo) * 10 - 1},d7',
                      f'rw{i}_{side}:', ' move.l (a2)+,(a1)+', f' dbf d7,rw{i}_{side}', ' lea 8000(a0),a0', f' dbf d6,pl{i}_{side}']
    a += ['finished: bra.s finished',
          f'orig: move.l (sp)+,${cell:x}', f' jmp ${b + 0x6c4f8:x}',   # unpatched entry
          f'cand: jmp ${b + 0x6c4f2:x}', 'mem: dc.l 0', ' even']
    for k, t in enumerate(tables):
        a += [f'table{k}:'] + [f' dc.w {x},{z}' for x, z in t]
    src = out / 'fixture.s'; src.write_text('\n'.join(a) + '\n'); binary = out / 'fixture.bin'; lst = out / 'fixture.lst'
    subprocess.run(['bash', '-c', '. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"', 'fixture', str(src), str(binary), str(lst)], check=True)
    labels = {n: int(re.search(r'^' + n + r'\s+A:([0-9A-Fa-f]+)', lst.read_text(), re.M)[1], 16) for n in ['finished', 'mem']}
    global RET
    RET = {n: int(re.search(r'^' + n + r'\s+A:([0-9A-Fa-f]+)', lst.read_text(), re.M)[1], 16) for n in [f'ret{i}_{s}' for i in range(len(cases)) for s in range(2)]}
    blob = binary.read_bytes(); assert code + len(blob) < b + 0x5f000, 'fixture overlaps the fill code it calls'
    cmd('delete breakpoints'); cmd('monitor tfxreg 16 2700')
    for off in range(0, len(blob), 32): cmd(f'monitor tfxmem {code + off:x} {blob[off:off + 32].hex()}')
    cmd(f'monitor tfxreg 17 {code:x}'); cmd(f'break *{labels["finished"]:#x}'); reply = cmd('continue')
    assert f'0x{labels["finished"]:08x}' in reply, reply[-1000:]
    cmd(f'monitor tfxsync {labels["mem"]:x} 4'); mem = int.from_bytes(dump('mem.bin', labels['mem'], 4), 'big'); assert mem
    cmd(f'monitor tfxsync {mem:x} {TOTAL}'); data = dump('results.bin', mem, TOTAL)
    results = []
    for i, c in enumerate(cases):
        o = data[offsets[i]:offsets[i] + slot(c)]; k = data[offsets[i] + slot(c):offsets[i] + 2 * slot(c)]
        results.append(dict(c, **verify(c, o, k, i)))
    ok = [x for x in results if x['regs'] and x['bad_bits'] == 0]
    # Negative controls on a case with hidden pixels.
    j = next(i for i, x in enumerate(results) if x['hidden_bits'] > 0); c = cases[j]
    o = data[offsets[j]:offsets[j] + slot(c)]; k = bytearray(data[offsets[j] + slot(c):offsets[j] + 2 * slot(c)])
    lo, hi = rows_of(c); t = tables[c['table']]; controls = {}
    for name in ['hidden_bit', 'visible_bit', 'register']:
        kk = bytearray(k)
        if name == 'register': kk[8] ^= 1
        else:
            row = next(rw for rw in range(lo, hi) if t[rw][0] != NONE); ol, orr = t[row]
            x = ol if name == 'hidden_bit' else (orr + 1 if orr < 319 else ol - 1)
            kk[20 + (row - lo) * 40 + (x >> 3)] ^= 0x80 >> (x & 7)
        v = verify(c, o, bytes(kk), j); controls[name] = not (v['regs'] and v['bad_bits'] == 0)
    if SKIP:
        # A skip of a call that draws outside the runs must be rejected.
        w = next(i for i, x in enumerate(results) if x['clip_path'] and not x.get('skipped') and x['drawn_bits'] > x['hidden_bits'])
        cw = cases[w]; lo, hi = rows_of(cw); ow = data[offsets[w]:offsets[w] + slot(cw)]
        kw = bytearray(data[offsets[w] + slot(cw):offsets[w] + 2 * slot(cw)]); size = (hi - lo) * 40
        for pl in range(8): kw[20 + pl * size:20 + (pl + 1) * size] = background[pl * 8000 + lo * 40:pl * 8000 + hi * 40]
        v = verify(cw, ow, bytes(kw), w); controls['wrong_skip'] = not (v['regs'] and v['bad_bits'] == 0)
    summary = dict(cases=len(cases), passed=len(ok), clip_path=sum(x['clip_path'] for x in results),
                   skipped=sum(bool(x.get('skipped')) for x in results),
                   with_hidden=sum(x['hidden_bits'] > 0 for x in results), drawn_bits=sum(x['drawn_bits'] for x in results),
                   hidden_bits=sum(x['hidden_bits'] for x in results), negative_controls_rejected=controls)
    (out / 'results.json').write_text(json.dumps(dict(summary, results=results), indent=1)); print(summary, flush=True)
    assert len(ok) == len(cases), [x for x in results if x not in ok][:2]
    assert all(controls.values()), controls

v = dict(executable='tfx.020', custom3=3, custom4=18, swap=0x19fc, extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040', out, Path(str(out) + '-seed'), capture, v)
