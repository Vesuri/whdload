"""Native twins for sfd_span_040 (step 4) against ScanFillDown's scanline loop.

  opt20_sfd_test.py OUT

Both sides run inside the game process on the same 8-plane buffer. Per side the guest
writes the six bytes at $6c514 (the original LEA/ADDA, or the slave JMP), pushes the
caches, sets the return cell $6c4c0 and enters at $6c514 with controlled registers, as
ScanFillDown's entry leaves them. The guest compares the whole buffer between the sides;
the host compares D0, D7, A0, A2-A5, SP and CCR (D1-D6, A1 and A6 are scratch, see the
slave comment), and checks the candidate's rows against an independent model. Cases cover
empty calls, crossing edges, spans inside one long, edge longs with 0-8 longs between
them, aligned edges, full width, colours 0-255, and edges beyond x = 319 that continue
in the original loop. Negative controls must be rejected by the same verifier.
"""
import os, sys, json, struct, subprocess, re
from pathlib import Path
from replay_flight import ROOT, run
out = Path(sys.argv[1]).resolve(); os.chdir(ROOT)

PLANE = 8000; ROW = 40; REGION = 81920; SEED = 0x2468ace1


def lcg(seed, n):
    r = []
    for _ in range(n):
        seed = (((seed << 3) | (seed >> 29)) + 0x13ab) & 0xffffffff; r.append(seed)
    return r


image = b''.join(struct.pack('>I', x) for x in lcg(SEED, REGION // 4))


def fx(x): return int(round(x * 65536)) & 0xffffffff


def lines(c):
    """Per line: (left x, right x) as the loop sees them (unsigned words)."""
    a2, a3 = c['xl'], c['xr']; r = []
    for _ in range(c['n']):
        r.append(((a2 >> 16) & 0xffff, (a3 >> 16) & 0xffff)); a2 = (a2 + c['sl']) & 0xffffffff; a3 = (a3 + c['sr']) & 0xffffffff
    return r


cases = []
colours = [0, 255, 1, 0x80, 0x55, 0xaa, 0x0f, 0xf0, 0x3c, 0x7e, 0x81, 0x13, 0xc9, 0x6b, 0xfe, 0x01]
# Alignment sweeps: one edge fixed, the other moving one pixel per line.
for i, (xl, xr, sl, sr, n) in enumerate([(0, 0, 0, 1, 200), (0, 120, 0, 1, 200), (31, 0, 0, 1, 200), (32, 120, 0, 1, 200), (33, 150, 0, 1, 170),
                                          (63, 64, 0, 1, 200), (100, 200, 0, 0.5, 200), (0, 319, 1, 0, 200), (120, 319, 1, 0, 200), (288, 319, -1, 0, 200),
                                          (319, 319, -1, 0, 200), (15, 16, -0.25, 0.75, 60), (5, 300, 0.37, -0.41, 200)]):
    cases.append(dict(xl=fx(xl), xr=fx(xr), sl=fx(sl), sr=fx(sr), n=n, y=0, colour=colours[i % len(colours)], x=i % 2))
# Narrow strips sliding across long boundaries.
for i, (x0, w, s_, n) in enumerate([(0, 0, 1.5, 200), (10, 3, 0.1, 200), (31, 0, 1, 180), (2, 29, 0.75, 200), (300, 19, -1.25, 200), (64, 5, 0.33, 200)]):
    cases.append(dict(xl=fx(x0), xr=fx(x0 + w), sl=fx(s_), sr=fx(s_), n=n, y=0, colour=colours[(i * 3 + 1) % len(colours)], x=i % 2))
# Single lines at every interesting alignment pair.
pts = [0, 1, 15, 16, 30, 31, 32, 33, 63, 64, 95, 96, 160, 287, 288, 300, 318, 319]
for i, a in enumerate(pts):
    for j, b in enumerate(pts):
        if (i + j) % 3 == 0:
            cases.append(dict(xl=fx(a) | 0x8000 * (i & 1), xr=fx(b) | 0x4000 * (j & 1), sl=0, sr=0, n=1, y=(i * 7 + j * 3) % 199, colour=colours[(i + j) % len(colours)], x=(i ^ j) & 1))
# Trapezoids with fractional edges, crossings and edges leaving the screen.
for i in range(48):
    rs = lcg(0x1000 + i, 8)
    xl = rs[0] % 320; xr = xl + rs[1] % (320 - xl); n = [0, 1, 2, 5, 17, 40, 100, 150][i % 8]
    sl = ((rs[2] % 2001) - 1000) / 400; sr = ((rs[3] % 2001) - 1000) / 400
    y = rs[4] % (200 - n) if n < 200 else 0
    c = dict(xl=fx(xl + (rs[5] % 65536) / 65536), xr=fx(xr + (rs[6] % 65536) / 65536), sl=fx(sl), sr=fx(sr), n=n, y=y, colour=rs[7] % 256, x=i % 2)
    # Keep every drawn line within the original's ten-long dispatch table.
    while any(r >= l and (r >> 5) - (l >> 5) > 9 for l, r in lines(c)): c['n'] -= 1
    cases.append(c)
# Right edges beyond x = 319 (the original loop continues), crossing it mid-call or from the start.
for i, (xl, xr, sl, sr, n, y) in enumerate([(100, 300, 0, 1, 50, 10), (40, 330, 0.5, 0.25, 30, 0), (64, 383, 0, 0, 3, 100), (320, 340, 0, 0, 4, 20),
                                             (330, 335, 0.5, 0.5, 10, 50), (290, 310, 0, 3, 20, 150), (319, 319, 0, 1, 5, 5), (-10, -3, 0, 0, 3, 2),
                                             (200, 330, 0, -2, 20, 60), (32, 340, 0, 0, 1, 199)]):
    cases.append(dict(xl=fx(xl), xr=fx(xr), sl=fx(sl), sr=fx(sr), n=n, y=y, colour=colours[(i * 5) % len(colours)], x=i % 2))
# Empty calls with junk edges.
cases.append(dict(xl=0x12345678, xr=0x9abcdef0, sl=0, sr=0, n=0, y=7, colour=0x42, x=1))
cases.append(dict(xl=fx(10), xr=fx(5), sl=0, sr=0, n=0, y=0, colour=0, x=0))


def model(c, right_exclusive=False):
    """The original loop's writes on a copy of the region: bit 31 is the left pixel of a long."""
    m = bytearray(image); kinds = dict(skip=0, narrow=0, wide1=0, middle=0, aligned_left=0, aligned_right=0, beyond=0)
    for k, (xl, xr) in enumerate(lines(c)):
        if xr < xl: kinds['skip'] += 1; continue
        if xr > 319: kinds['beyond'] += 1
        l, r = xl >> 5, xr >> 5; assert r - l <= 9
        if r == l: kinds['narrow'] += 1
        elif r - l == 1: kinds['wide1'] += 1
        else: kinds['middle'] += 1
        if r > l and xl & 31 == 0: kinds['aligned_left'] += 1
        if r > l and xr & 31 == 31: kinds['aligned_right'] += 1
        row = (c['y'] + k) * ROW
        for li in range(l, r + 1):
            lo = xl & 31 if li == l else 0; hi = xr & 31 if li == r else 31
            if right_exclusive and li == r: hi -= 1
            mask = 0
            for bit in range(lo, hi + 1): mask |= 1 << (31 - bit)
            for p in range(8):
                o = p * PLANE + row + 4 * li; v = struct.unpack_from('>I', m, o)[0]
                v = (v | mask) if (c['colour'] >> p) & 1 else (v & ~mask & 0xffffffff)
                struct.pack_into('>I', m, o, v)
    return m, kinds


def bands(c):
    """(region offset, length) per plane: the call's rows plus one."""
    return [(p * PLANE + c['y'] * ROW, (c['n'] + 1) * ROW) for p in range(8)]


def capture(cmd, dump, bases, hs, out):
    b = bases[0]; code = b + 0x8000
    orig = hs[0]['bytes'][0x6c514:0x6c51a]
    assert orig.hex() == '4dfa000ad1fc', orig.hex()
    patch = dump('sfd-patch.bin', b + 0x6c514, 6); assert patch[:2].hex() == '4ef9', patch.hex()
    slave = int.from_bytes(patch[2:], 'big')
    n = len(cases); wsize = sum(l for c in cases for _, l in bands(c))
    # rgn: region (0), original copy (REGION), candidate copy (2 * REGION).
    a = [' mc68040', f' org ${code:x}', f' move.l #{3 * REGION},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,rgn',
         f' move.l #{wsize},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,windows']
    wo = 0
    for i, c in enumerate(cases):
        for side in (0, 1):
            slot = (i * 2 + side) * 72
            if side == 0: a += [f' move.l #${orig[:4].hex()},${b + 0x6c514:x}', f' move.w #${orig[4:].hex()},${b + 0x6c518:x}']
            else: a += [f' move.w #$4ef9,${b + 0x6c514:x}', f' move.l #${slave:x},${b + 0x6c516:x}']
            a += [' cpusha bc', ' move.l rgn(pc),a0', f' move.l #${SEED:x},d0', f' move.w #{REGION // 4 - 1},d7', f'init{i}_{side}:', ' rol.l #3,d0', ' add.l #$13ab,d0',
                  ' move.l d0,(a0)+', f' dbf d7,init{i}_{side}', f' move.l #ret{i}_{side},${b + 0x6c4c0:x}',
                  ' move.l rgn(pc),a0', f' add.l #{c["y"] * ROW},a0',
                  f' move.l #${c["xl"]:x},a2', f' move.l #${c["xr"]:x},a3', f' move.l #${c["sl"]:x},a4', f' move.l #${c["sr"]:x},a5',
                  f' move.l #${0x5a5a0080 | (c["colour"] << 8):x},d0', ' move.l #$11111111,d1', ' move.l #$22222222,d2', ' move.l #$33333333,d3',
                  ' move.l #$44444444,d4', ' move.l #$55555555,d5', ' move.l #$66666666,d6', f' move.l #${0x7e7e0000 | c["n"]:x},d7',
                  ' move.l #$a1a1a1a1,a1', ' move.l #$a6a6a6a6,a6', f' move.w #${0x1f if c["x"] else 0x0f:x},ccr', f' jmp ${b + 0x6c514:x}',
                  f'ret{i}_{side}:', f' movem.l d0-d7/a0-a6,regs+{slot}', f' move.w ccr,regs+{slot + 60}', f' move.l sp,regs+{slot + 64}',
                  ' move.l rgn(pc),a1', f' lea {REGION * (side + 1)}(a1),a2', f' move.w #{REGION // 4 - 1},d7', f'save{i}_{side}:', ' move.l (a1)+,(a2)+', f' dbf d7,save{i}_{side}']
        a += [' move.l rgn(pc),a0', f' lea {REGION}(a0),a1', f' lea {2 * REGION}(a0),a2', ' moveq #0,d0', f' move.w #{REGION // 4 - 1},d7', f'cmp{i}:', ' cmpm.l (a1)+,(a2)+',
              f' beq.s eq{i}', ' addq.l #1,d0', f'eq{i}:', f' dbf d7,cmp{i}', f' move.l d0,diffs+{i * 4}']
        for p, (o, ln) in enumerate(bands(c)):
            a += [' move.l rgn(pc),a1', f' add.l #{2 * REGION + o},a1', ' move.l windows(pc),a2', f' add.l #{wo},a2', f' move.w #{ln // 4 - 1},d7',
                  f'win{i}_{p}:', ' move.l (a1)+,(a2)+', f' dbf d7,win{i}_{p}']
            wo += ln
    a += ['finished: bra.s finished', ' cnop 0,4', 'windows: dc.l 0', 'rgn: dc.l 0', f'regs: ds.b {n * 144}', f'diffs: ds.l {n}']
    src = out / 'fixture.s'; src.write_text('\n'.join(a) + '\n'); binary = out / 'fixture.bin'; listing = out / 'fixture.lst'
    subprocess.run(['bash', '-c', '. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"', 'fixture', str(src), str(binary), str(listing)], check=True)
    labels = {k: int(re.search(r'^' + k + r'\s+A:([0-9A-Fa-f]+)', listing.read_text(), re.M)[1], 16) for k in ['finished', 'windows', 'rgn', 'regs', 'diffs']}
    blob = binary.read_bytes(); assert code + len(blob) < b + 0x4d000, 'fixture overlaps game code'
    cmd('delete breakpoints'); cmd('monitor tfxreg 16 2700')
    for off in range(0, len(blob), 32): cmd(f'monitor tfxmem {code + off:x} {blob[off:off + 32].hex()}')
    cmd(f'monitor tfxreg 17 {code:x}'); cmd(f'break *{labels["finished"]:#x}'); reply = cmd('continue')
    assert f'0x{labels["finished"]:08x}' in reply, reply[-1000:]
    cmd(f'monitor tfxsync {labels["windows"]:x} {8 + n * 148}')
    win = int.from_bytes(dump('windows.bin', labels['windows'], 4), 'big'); assert win
    regs = dump('regs.bin', labels['regs'], n * 144); diffs = struct.unpack(f'>{n}I', dump('diffs.bin', labels['diffs'], n * 4))
    cmd(f'monitor tfxsync {win:x} {wsize}'); windows = dump('windows-data.bin', win, wsize)
    assert dump('sfd-patch-end.bin', b + 0x6c514, 6) == patch

    KEPT = [0, 7, 8, 10, 11, 12, 13]   # D0, D7, A0, A2-A5

    def verify(c, ro, rc, wins, diff, right_exclusive=False):
        R = lambda r, k: struct.unpack_from('>I', r, 4 * k)[0]
        exp, _ = model(c, right_exclusive)
        a2, a3 = (c['xl'] + c['n'] * c['sl']) & 0xffffffff, (c['xr'] + c['n'] * c['sr']) & 0xffffffff
        o_ccr, c_ccr = struct.unpack_from('>H', ro, 60)[0] & 0x1f, struct.unpack_from('>H', rc, 60)[0] & 0x1f
        mw = b''.join(bytes(exp[o:o + ln]) for o, ln in bands(c))
        return dict(region_diff_longs=diff, regs=all(R(ro, k) == R(rc, k) for k in KEPT), sp=ro[64:68] == rc[64:68], ccr=o_ccr == c_ccr,
                    model_rows=wins == mw, model_regs=R(rc, 10) == a2 and R(rc, 11) == a3 and R(rc, 12) == c['sl'] and R(rc, 13) == c['sr']
                    and R(rc, 0) == 0x5a5a0080 | (c['colour'] << 8) and R(rc, 7) == 0x7e7effff,
                    model_ccr=c_ccr == 0x19)

    def passed(v): return v['region_diff_longs'] == 0 and all(v[k] for k in v if k != 'region_diff_longs')

    results = []; wo = 0; slices = []
    for i, c in enumerate(cases):
        ln = sum(l for _, l in bands(c)); slices.append((wo, ln)); wo += ln
        ro, rc = regs[i * 144:i * 144 + 72], regs[i * 144 + 72:i * 144 + 144]
        v = verify(c, ro, rc, windows[wo - ln:wo], diffs[i])
        _, kinds = model(c)
        a0o, a0c = struct.unpack_from('>I', ro, 32)[0], struct.unpack_from('>I', rc, 32)[0]
        scratch = [k for k in (1, 2, 3, 4, 5, 6, 9, 14) if ro[4 * k:4 * k + 4] != rc[4 * k:4 * k + 4]]
        results.append(dict(c, **v, ok=passed(v), kinds=kinds, a0_steps=(a0c - a0o), scratch_differs=scratch))
    # Negative controls: a wrong bitplane byte, a wrong kept register, a wrong X flag, and a
    # model whose right edge is exclusive.
    k = next(i for i, r in enumerate(results) if r['kinds']['middle'] > 10 and r['kinds']['narrow'] > 10)
    c = cases[k]; ro, rc = regs[k * 144:k * 144 + 72], regs[k * 144 + 72:k * 144 + 144]; o, ln = slices[k]; w = bytearray(windows[o:o + ln])
    controls = {}
    bad = bytearray(w); bad[3 * ROW + 5] ^= 0x10; controls['byte'] = not passed(verify(c, ro, rc, bytes(bad), diffs[k]))
    badr = bytearray(rc); badr[43] ^= 1; controls['register'] = not passed(verify(c, ro, bytes(badr), bytes(w), diffs[k]))
    badx = bytearray(rc); badx[61] ^= 0x10; controls['x_flag'] = not passed(verify(c, ro, bytes(badx), bytes(w), diffs[k]))
    controls['right_exclusive'] = not passed(verify(c, ro, rc, bytes(w), diffs[k], right_exclusive=True))
    tot = {key: sum(r['kinds'][key] for r in results) for key in results[0]['kinds']}
    summary = dict(cases=n, passed=sum(r['ok'] for r in results), lines=tot, empty_calls=sum(r['n'] == 0 for r in results),
                   scratch_differs=sum(bool(r['scratch_differs']) for r in results), negative_controls_rejected=controls)
    (out / 'results.json').write_text(json.dumps(dict(summary, results=results), indent=1))
    assert summary['passed'] == n, [r for r in results if not r['ok']][:3]
    assert all(controls.values()), controls
    print('PASS', json.dumps(summary), flush=True)


v = dict(executable='tfx.020', custom3=3, custom4=18, swap=0x19fc, extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040', out, Path(str(out) + '-seed'), capture, v)
