"""Native twins for fade_cols_040 (step 7) against @AltFadeColsMiss ($249a).

  opt20_fade_test.py OUT

Both sides run inside the game process on the same 4 KB memory image: the original is a
verbatim copy of $249a-$2599 (position-independent: internal branches, A4-relative flag),
the candidate is the patched entry. Per case the guest compares the whole region, the
palette-dirty flag and the 40-byte stack frame below SP; the host compares D0-D7/A0-A6
and CCR, and checks the candidate region and D0/D1/X against an independent model of the
original. Cases cover factor 50 (the copy path), 0-49 (the reciprocal blend) and others
(fallback), counts 0-256,
negative and wrapping first indices, magenta and partial-magenta entries, and aliased
destinations. Negative controls must be rejected by the same verifier.
"""
import os, sys, json, struct, subprocess, re
from pathlib import Path
from replay_flight import ROOT, run
out = Path(sys.argv[1]).resolve(); os.chdir(ROOT)

REGION = 4096; A0, B0, D0 = 256, 1536, 2816
# Zeroed space below the region holds the accesses of index ranges that wrap (fallback
# cases): B there is zero, never magenta, and A = B = 0 blends to 0, so it stays zero.
RBASE = 200704


def lcg(seed, n):
    r = []
    for _ in range(n):
        r.append(seed); seed = (((seed << 3) | (seed >> 29)) + 0x13ab) & 0xffffffff
    return r


image = bytearray(b''.join(struct.pack('>I', x) for x in lcg(0x2468ace1, REGION // 4)))
# Region-wide magenta patterns, so every A, B and destination placement sees them.
for j in range(REGION // 3):
    o = 3 * j
    if j % 3 == 0: image[o:o + 3] = b'\xff\x00\xff'          # magenta: skipped
    elif j % 7 == 1: image[o:o + 3] = b'\xff\x00\x10'        # partial: blended
    elif j % 11 == 2: image[o:o + 3] = b'\xff\x01\xff'
    elif j % 13 == 3: image[o:o + 3] = b'\x10\x00\xff'

ALIAS = {'none': (A0, B0, D0), 'dest=B': (A0, B0, B0), 'dest=A': (A0, B0, A0), 'dest=B+1': (A0, B0, B0 + 1),
         'dest=B-1': (A0, B0, B0 - 1), 'A=B': (B0, B0, D0), 'dest=A+2': (A0, B0, A0 + 2)}
cases = []
factors = [50, 50, 50, 0x12340032, 50, 0, 1, 25, 49, 51, -50 & 0xffffffff, 100, 0x00320000, 10, 33, 48, 0x55550017, 0xffff]
counts = [256, 1, 2, 3, 7, 64, 255, 0, 100]
firsts = [0, 1, 5, 100, 200, -1, -100, 4, 33]
aliases = list(ALIAS)
for i in range(180):
    cases.append(dict(factor=factors[i % len(factors)], count=counts[(i // 2) % len(counts)], first=firsts[(i // 3) % len(firsts)],
                      alias=aliases[(i // 5) % len(aliases)], x=(i // 7) % 2))
# Index-range edges: the copy path up to first + count = 32768, fallback beyond.
for f in (50, 49, 51):
    for first, count in ((32767, 1), (32766, 2), (32767, 2), (32700, 100), (-32768, 256), (-2, 4)):
        for x in (0, 1):
            cases.append(dict(factor=f, count=count, first=first, alias='none', x=x))


def s16(v): v &= 0xffff; return v - 0x10000 if v & 0x8000 else v


def model(c, entry_d0, entry_d1):
    """The original routine, byte by byte in its own read/write order.
    Returns region, D0, D1, final index, X, and whether the last entry was skipped."""
    m = bytearray(RBASE) + bytearray(image); a, b, d = (x + RBASE - 3 * c['first'] for x in ALIAS[c['alias']])
    skipped = False
    f = s16(c['factor']); n = c['count'] & 0xffff; idx = c['first'] & 0xffff; d0, d1 = entry_d0, entry_d1
    for _ in range(n):
        i = s16(idx); o = 3 * i; d0 = i & 0xffffffff; d1 = o & 0xffffffff
        assert min(a, b, d) + o >= 0
        skipped = m[b + o] == 0xff and m[b + o + 1] == 0 and m[b + o + 2] == 0xff
        if not skipped:
            for k in range(3):
                p = m[a + o + k] * f - m[b + o + k] * f; q = abs(p) // 50 * (1 if p >= 0 else -1)
                r = (m[b + o + k] + q) & 0xff; m[d + o + k] = r; d0 = r
        idx = (idx + 1) & 0xffff
    assert not any(m[:RBASE])
    return m[RBASE:], d0, d1, idx, (0 if n else c['x']), skipped


def capture(cmd, dump, bases, hs, out):
    b = bases[0]; code = b + 0x8000
    orig = hs[0]['bytes'][0x249a:0x259a]
    assert orig[:6].hex() == '594f48e73f34' and orig[-2:].hex() == '4e75', orig.hex()
    assert dump('fade-patch.bin', b + 0x249a, 2) == bytes.fromhex('4ef9')
    n = len(cases)
    # rgn = mem + RBASE: region (0), saved original region (4096), saved candidate region (8192), flag (12288).
    a = [' mc68040', f' org ${code:x}', f' move.l #{RBASE + 16384},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,mem', f' add.l #{RBASE},d0', ' move.l d0,rgn',
         f' move.l #{n * REGION},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,windows']
    for i, c in enumerate(cases):
        pa, pb, pd = (x - 3 * c['first'] for x in ALIAS[c['alias']])
        for side in (0, 1):
            slot = (i * 2 + side) * 104
            a += [' move.l rgn(pc),a0', ' lea image(pc),a1', f' move.w #{REGION // 4 - 1},d7', f'init{i}_{side}:', ' move.l (a1)+,(a0)+', f' dbf d7,init{i}_{side}',
                  ' move.l rgn(pc),a0', ' clr.b 12288(a0)', ' move.l a0,d7', f' add.l #{pb & 0xffffffff},d7', ' move.l d7,a1',
                  ' move.l a0,d7', f' add.l #{pd & 0xffffffff},d7', ' move.l d7,a2', ' move.l a0,d7', f' add.l #{pa & 0xffffffff},d7',
                  ' lea 12288+32736(a0),a4', ' move.l d7,a0',
                  f' move.l #${(0x5a5a0000 | (c["first"] & 0xffff)):x},-(sp)', ' move.l a2,-(sp)',
                  f' move.l #${c["factor"] & 0xffffffff:x},d0', f' move.l #${(0x7e7e0000 | c["count"]):x},d1',
                  ' move.l #$22222222,d2', ' move.l #$33333333,d3', ' move.l #$44444444,d4', ' move.l #$55555555,d5', ' move.l #$66666666,d6',
                  ' move.l #$77777777,d7', ' move.l #$a2a2a2a2,a2', ' move.l #$a3a3a3a3,a3', ' move.l #$a5a5a5a5,a5', ' move.l #$a6a6a6a6,a6',
                  f' move.w #${0x1f if c["x"] else 0x0f:x},ccr', f' jsr {"orig" if side == 0 else "cand"}',
                  f' movem.l d0-d7/a0-a6,regs+{slot}', ' move.w ccr,d0', f' move.w d0,regs+{slot + 60}',
                  ' lea -44(sp),a0', f' lea regs+{slot + 64},a1', ' moveq #9,d7', f'frame{i}_{side}:', ' move.l (a0)+,(a1)+', f' dbf d7,frame{i}_{side}',
                  ' addq.l #8,sp', ' move.l rgn(pc),a0', f' move.b 12288(a0),regs+{slot + 62}', ' move.l a0,a1', f' lea {4096 * (side + 1)}(a0),a2',
                  f' move.w #{REGION // 4 - 1},d7', f'save{i}_{side}:', ' move.l (a1)+,(a2)+', f' dbf d7,save{i}_{side}']
        a += [' move.l rgn(pc),a0', ' lea 4096(a0),a1', ' lea 8192(a0),a2', ' moveq #0,d0', f' move.w #{REGION // 4 - 1},d7', f'cmp{i}:', ' cmpm.l (a1)+,(a2)+',
              f' beq.s eq{i}', ' addq.l #1,d0', f'eq{i}:', f' dbf d7,cmp{i}', f' move.l d0,diffs+{i * 4}',
              ' move.l rgn(pc),a1', ' lea 8192(a1),a1', ' move.l windows(pc),a2', f' add.l #{i * REGION},a2', f' move.w #{REGION // 4 - 1},d7',
              f'win{i}:', ' move.l (a1)+,(a2)+', f' dbf d7,win{i}']
    a += ['finished: bra.s finished', 'orig:'] + [f' dc.b ${x:02x}' for x in orig] + [f'cand: jmp ${b + 0x249a:x}',
          ' cnop 0,4', 'image:'] + [f' dc.b ${x:02x}' for x in image] + ['mem: dc.l 0', 'windows: dc.l 0', 'rgn: dc.l 0', f'regs: ds.b {n * 208}', f'diffs: ds.l {n}']
    src = out / 'fixture.s'; src.write_text('\n'.join(a) + '\n'); binary = out / 'fixture.bin'; listing = out / 'fixture.lst'
    subprocess.run(['bash', '-c', '. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"', 'fixture', str(src), str(binary), str(listing)], check=True)
    labels = {k: int(re.search(r'^' + k + r'\s+A:([0-9A-Fa-f]+)', listing.read_text(), re.M)[1], 16) for k in ['finished', 'mem', 'windows', 'rgn', 'regs', 'diffs', 'orig']}
    blob = binary.read_bytes(); assert code + len(blob) < b + 0x4d000, 'fixture overlaps game code'
    assert blob[labels['orig'] - code:labels['orig'] - code + 256] == orig
    cmd('delete breakpoints'); cmd('monitor tfxreg 16 2700')
    for off in range(0, len(blob), 32): cmd(f'monitor tfxmem {code + off:x} {blob[off:off + 32].hex()}')
    cmd(f'monitor tfxreg 17 {code:x}'); cmd(f'break *{labels["finished"]:#x}'); reply = cmd('continue')
    assert f'0x{labels["finished"]:08x}' in reply, reply[-1000:]
    cmd(f'monitor tfxsync {labels["mem"]:x} {12 + n * 212}')
    mem = int.from_bytes(dump('allocation.bin', labels['mem'], 4), 'big'); win = int.from_bytes(dump('windows.bin', labels['windows'], 4), 'big')
    assert mem and win
    regs = dump('regs.bin', labels['regs'], n * 208); diffs = struct.unpack(f'>{n}I', dump('diffs.bin', labels['diffs'], n * 4))
    cmd(f'monitor tfxsync {win:x} {n * REGION}'); windows = dump('windows-data.bin', win, n * REGION)

    def verify(c, ro, rc, region, diff):
        R = lambda r, k: struct.unpack_from('>I', r, 4 * k)[0]
        exp, d0, d1, idx, x, _ = model(c, c['factor'] & 0xffffffff, 0x7e7e0000 | c['count'])
        o_ccr, c_ccr = struct.unpack_from('>H', ro, 60)[0] & 0x1f, struct.unpack_from('>H', rc, 60)[0] & 0x1f
        return dict(region_diff_longs=diff, regs=ro[:60] == rc[:60], ccr=o_ccr == c_ccr, flag=ro[62] == rc[62] == 1, frame=ro[64:104] == rc[64:104],
                    local=struct.unpack_from('>H', rc, 64 + 38)[0] == idx,
                    model_region=bytes(region) == bytes(exp), model_d0=R(rc, 0) == d0, model_d1=R(rc, 1) == d1, model_x=(c_ccr >> 4) == x,
                    nzvc=c_ccr & 15 == 0)

    def passed(v): return v['region_diff_longs'] == 0 and all(v[k] for k in v if k != 'region_diff_longs')

    results = []
    for i, c in enumerate(cases):
        ro, rc = regs[i * 208:i * 208 + 104], regs[i * 208 + 104:i * 208 + 208]
        v = verify(c, ro, rc, windows[i * REGION:(i + 1) * REGION], diffs[i])
        n_ = c['count'] & 0xffff; f16 = c['factor'] & 0xffff; inrange = n_ > 0 and s16(c['first']) + n_ <= 32768
        mo = model(c, 0, 0)
        results.append(dict(c, **v, ok=passed(v), copy_path=inrange and f16 == 50, blend_path=inrange and f16 < 50, changed=sum(p != q for p, q in zip(mo[0], image)),
                            last_skipped=n_ > 0 and mo[5]))
    # Negative controls on a factor-50 case with skipped and blended entries: a wrong byte,
    # a wrong register, a wrong X flag, and a copy that ignores magenta entries.
    k = next(i for i, r in enumerate(results) if r['copy_path'] and r['count'] == 256 and r['alias'] == 'none')
    c = cases[k]; ro, rc = regs[k * 208:k * 208 + 104], regs[k * 208 + 104:k * 208 + 208]; region = bytearray(windows[k * REGION:(k + 1) * REGION])
    controls = {}
    bad = bytearray(region); bad[D0 + 4] ^= 1; controls['byte'] = not passed(verify(c, ro, rc, bad, diffs[k]))
    badr = bytearray(rc); badr[7] ^= 1; controls['register'] = not passed(verify(c, ro, bytes(badr), region, diffs[k]))
    badx = bytearray(rc); badx[61] ^= 0x10; controls['x_flag'] = not passed(verify(c, ro, bytes(badx), region, diffs[k]))
    nomag = bytearray(region); a_, b_, d_ = ALIAS['none']
    for j in range(256): nomag[d_ + 3 * j:d_ + 3 * j + 3] = image[a_ + 3 * j:a_ + 3 * j + 3]
    controls['ignores_magenta'] = nomag != region and not passed(verify(c, ro, rc, nomag, diffs[k]))
    k2 = next(i for i, r in enumerate(results) if r['blend_path'] and r['count'] == 256 and 0 < (r['factor'] & 0xffff) < 50)
    c2 = cases[k2]; region2 = bytearray(windows[k2 * REGION:(k2 + 1) * REGION]); exp2 = model(c2, 0, 0)[0]
    j = next(o for o in range(REGION) if exp2[o] != image[o]); region2[j] = (region2[j] + 1) & 0xff
    controls['quotient'] = not passed(verify(c2, regs[k2 * 208:k2 * 208 + 104], regs[k2 * 208 + 104:k2 * 208 + 208], region2, diffs[k2]))
    summary = dict(cases=n, passed=sum(r['ok'] for r in results), copy_path=sum(r['copy_path'] for r in results), blend_path=sum(r['blend_path'] for r in results),
                   fallback=sum(not r['copy_path'] and not r['blend_path'] and (r['count'] & 0xffff) > 0 for r in results), empty=sum((r['count'] & 0xffff) == 0 for r in results),
                   last_skipped=sum(r['last_skipped'] for r in results), aliased=sum(r['alias'] != 'none' for r in results), negative_controls_rejected=controls)
    (out / 'results.json').write_text(json.dumps(dict(summary, results=results), indent=1))
    assert summary['passed'] == n, [r for r in results if not r['ok']][:3]
    assert all(controls.values()), controls
    print('PASS', json.dumps(summary), flush=True)


v = dict(executable='tfx.020', custom3=3, custom4=18, swap=0x19fc, extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040', out, Path(str(out) + '-seed'), capture, v)
