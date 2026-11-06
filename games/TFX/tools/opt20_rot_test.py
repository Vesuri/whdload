"""Native twins for rot_delta2_040 (step 8) against DoRotPt0's two-component case ($59748).

  opt20_rot_test.py OUT

Env: DELTA_LISTING (slave listing, for the cache variables).
Each case is a command stream of chained delta points (dx.w, dy.w, next opcode 254)
ended by opcode 255. The fixture owns both dispatch-table entries: 255 returns to the
fixture, 254 chains to the original copy (original side) or to $59748 (candidate side),
so neither side runs the other's code. (Entry 104, the game's own opcode for $59748,
is not stable at run time.)
The original side runs a verbatim copy of $59748-$59777 (position-independent) and the
game's own tail at $59778; the candidate enters the patched $59748. The cache is reset
before the first case and then persists, so later cases hit entries of earlier ones:
matrices come from a pool larger than the slot count (eviction), deltas from a pool
with repeats, bucket collisions and (0,0)/(32,0)/extreme values, and some matrices
differ only in register halves the products do not use. A block of cases runs with the
table pointer cleared (the multiplying fallback). Per case the guest compares the
stored points; the host compares D0-D7/A0-A6 and CCR, checks the points against an
independent model, and counts cache hits with a model of the cache.
"""
import os, sys, json, struct, subprocess, re
from pathlib import Path
from replay_flight import ROOT, run
out = Path(sys.argv[1]).resolve(); os.chdir(ROOT)
# EXE=TFX: plain TFX, whose interpreter and delta handler are identical $5e28 higher; MACHINE selects the CPU.
EXE = os.environ.get('EXE', 'tfx.020'); MACHINE = os.environ.get('MACHINE', '040'); D = 0x5e28 if EXE == 'TFX' else 0
A = lambda x: x + D
listing = Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
def sym(n): return int(re.search(r'^' + re.escape(n) + r'\s+00:([0-9A-Fa-f]+)', listing, re.M)[1], 16)
SLOTS, BUCKETS = 4, 256


def lcg(seed):
    while True:
        seed = (seed * 1103515245 + 12345) & 0xffffffff; yield seed


g = lcg(0x13579bdf)
mats = []
for k in range(6):
    m = [next(g) for _ in range(4)] + [next(g) & 0xffff0000]       # d4, d5, d6, a5, d7 high
    mats.append(m)
# Same used halves as mats[0] (d4.hi, d5, a5.hi, d6.lo, d7.hi), other halves changed.
m = list(mats[0]); m[0] = (m[0] & 0xffff0000) | 0x1234; m[2] = (m[2] & 0xffff) | 0x56780000; m[3] = (m[3] & 0xffff0000) | 0x9abc
mats.append(m)


def rol(v, n): return ((v << n) | (v >> (16 - n))) & 0xffff
def bucket(x, y): return ((rol(y & 0xffff, 5) ^ (x & 0xffff)) >> 5) & (BUCKETS - 1)


deltas = [(0, 0), (32, 0), (1, 0), (0, 1), (-1, -1), (32767, -32768), (-32768, 32767), (-191, -662), (800, 90), (1160, 1837)]
deltas += [(next(g) & 0xffff, next(g) & 0xffff) for _ in range(20)]
# Pairs sharing a bucket with a different key.
for x, y in list(deltas[:10]):
    for t in range(1, 1 << 16):
        if bucket(t, y) == bucket(x, y) and t != (x & 0xffff): deltas.append((t, y)); break
deltas = [((x + 0x8000) % 0x10000 - 0x8000, (y + 0x8000) % 0x10000 - 0x8000) for x, y in deltas]
cases = []
for i in range(int(os.environ.get('ROT_CASES', '220'))):
    n = [1, 2, 5, 9, 27, 3][i % 6]
    mat = [0, 1, 0, 2, 3, 4, 5, 6, 1, 0, 2][i % 11] if i % 37 else 6
    pts = [deltas[(i * 7 + j * (3 + i % 5)) % len(deltas)] for j in range(n)]
    if i % 4 == 3: pts = list(cases[i - 3]['points'])          # a shape drawn again
    cases.append(dict(mat=mat, points=pts, sums=[next(g) for _ in range(3)], x=(i // 3) % 2, plain=150 <= i < 170))


def model_points(c):
    m = mats[c['mat']]; a2, a3, a4 = c['sums']; outp = []
    s = lambda v: v - 0x10000 if v & 0x8000 else v
    for dx, dy in c['points']:
        a2 = (a2 + s(m[0] >> 16) * dx + s(m[1] >> 16) * dy) & 0xffffffff
        a3 = (a3 + s(m[1] & 0xffff) * dx + s(m[2] & 0xffff) * dy) & 0xffffffff
        a4 = (a4 + s(m[3] >> 16) * dx + s(m[4] >> 16) * dy) & 0xffffffff
        outp.append((a2, a3, a4))
    d3 = (s(m[4] >> 16) * c['points'][-1][1]) & 0xffffffff
    return outp, d3


def model_hits():
    slots = [None] * SLOTS; nxt = 0; table = {}; cur = None; hits = []
    for c in cases:
        h = 0
        for dx, dy in c['points']:
            if c['plain']: continue
            key = tuple(mats[c['mat']])
            if key != cur:
                if key in slots: s = slots.index(key)
                else:
                    s = nxt; nxt = (nxt + 1) % SLOTS; slots[s] = key
                    for b in range(BUCKETS): table[(s, b)] = (0, 0) if b else (32, 0)
                cur = key; slot = s
            b = bucket(dx, dy); k = (dx & 0xffff, dy & 0xffff)
            if table.get((slot, b)) == k: h += 1
            else: table[(slot, b)] = k
        hits.append(h)
    return hits


def capture(cmd, dump, bases, hs, out):
    b = bases[0]; code = b + 0x8000; tbl = b + A(0x565d8)
    orig = hs[0]['bytes'][A(0x59748):A(0x59778)]
    assert orig[:6].hex() == '4c9800032604' and len(orig) == 0x30
    assert hs[0]['bytes'][A(0x59778):A(0x5977c)].hex() == '48d61c00'
    assert dump('rot-patch.bin', b + A(0x59748), 2) == bytes.fromhex('4ef9')
    sb = int.from_bytes(dump('swap-target.bin', b + (0x18a8 if EXE == 'TFX' else 0x19fe), 4), 'big') - sym('do_swap_screen')
    entry104 = int.from_bytes(dump('entry104.bin', tbl + 104 * 4, 4), 'big') - b
    rt = sb + sym('rot_table'); table_ptr = int.from_bytes(dump('rot-table.bin', rt, 4), 'big'); assert table_ptr
    # Fresh cache: no matrix slot matches anything (low words set), oldest slot 0.
    cmd(f'monitor tfxmem {sb + sym("rot_next"):x} 0000')
    cmd(f'monitor tfxmem {sb + sym("rot_cur"):x} ' + '00000001' * 5)
    for k in range(SLOTS): cmd(f'monitor tfxmem {sb + sym("rot_mats") + 20 * k:x} ' + '00000001' * 5)
    n = len(cases); total = sum(len(c['points']) for c in cases)
    a = [' mc68040', f' org ${code:x}', f' move.l #{total * 36 * 2},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,mem',
         f' move.l ${tbl + 255 * 4:x},saved255', f' move.l ${tbl + 254 * 4:x},saved254', f' move.l #rethandler,${tbl + 255 * 4:x}']
    off = 0
    for i, c in enumerate(cases):
        m = mats[c['mat']]; np_ = len(c['points'])
        if c['plain'] and (i == 0 or not cases[i - 1]['plain']):
            # The table is never released at run time; invalidate the current matrix with it.
            a += [f' clr.l ${rt:x}', f' move.l #1,${sb + sym("rot_cur") + 16:x}']
        if not c['plain'] and i and cases[i - 1]['plain']: a += [f' move.l #${table_ptr:x},${rt:x}']
        for side in (0, 1):
            slot = (i * 2 + side) * 64
            a += [f' move.l #{"orig" if side == 0 else "$%x" % (b + A(0x59748))},${tbl + 254 * 4:x}', f' move.l #cont{i}_{side},cont', f' lea stream{i}(pc),a0', ' move.l mem(pc),a6', f' add.l #{(off + side * total) * 36},a6',
                  f' move.l #${c["sums"][0]:x},a2', f' move.l #${c["sums"][1]:x},a3', f' move.l #${c["sums"][2]:x},a4',
                  f' move.l #${m[0]:x},d4', f' move.l #${m[1]:x},d5', f' move.l #${m[2]:x},d6', f' move.l #${m[3]:x},a5', f' move.l #${m[4] | 104:x},d7',
                  ' move.l #$d0d0d0d0,d0', ' move.l #$d1d1d1d1,d1', ' move.l #$d2d2d2d2,d2', ' move.l #$d3d3d3d3,d3', ' move.l #$a1a1a1a1,a1',
                  f' move.w #${0x1f if c["x"] else 0x0f:x},ccr', f' jmp {"orig" if side == 0 else "cand"}', f'cont{i}_{side}:',
                  f' lea regs+{slot},a1', ' lea lastregs,a0', ' moveq #15,d7', f'cp{i}_{side}:', ' move.l (a0)+,(a1)+', f' dbf d7,cp{i}_{side}']
        a += [' move.l mem(pc),a0', f' add.l #{off * 36},a0', ' move.l a0,a1', f' add.l #{total * 36},a1', ' moveq #0,d0', f' move.w #{np_ * 9 - 1},d7',
              f'cmp{i}:', ' cmpm.l (a0)+,(a1)+', f' beq.s eq{i}', ' addq.l #1,d0', f'eq{i}:', f' dbf d7,cmp{i}', f' move.l d0,diffs+{i * 4}']
        off += np_
    a += [f' move.l saved255,${tbl + 255 * 4:x}', f' move.l saved254,${tbl + 254 * 4:x}', f' move.l #${table_ptr:x},${rt:x}', 'finished: bra.s finished',
          'rethandler:', ' move.w ccr,lastregs+60', ' movem.l d0-d7/a0-a6,lastregs', ' move.l cont,a0', ' jmp (a0)',
          'orig:'] + [f' dc.b ${x:02x}' for x in orig] + [f' jmp ${b + A(0x59778):x}', f'cand: jmp ${b + A(0x59748):x}']
    for i, c in enumerate(cases):
        body = b''
        for j, (dx, dy) in enumerate(c['points']):
            body += struct.pack('>hhB', dx, dy, 255 if j == len(c['points']) - 1 else 254)
        a += [' cnop 0,2', f'stream{i}:'] + [f' dc.b ${x:02x}' for x in body]
    a += [' cnop 0,4', 'mem: dc.l 0', 'saved255: dc.l 0', 'saved254: dc.l 0', 'cont: dc.l 0', 'lastregs: ds.b 64', f'regs: ds.b {n * 128}', f'diffs: ds.l {n}']
    src = out / 'fixture.s'; src.write_text('\n'.join(a) + '\n'); binary = out / 'fixture.bin'; lst = out / 'fixture.lst'
    subprocess.run(['bash', '-c', '. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"', 'fixture', str(src), str(binary), str(lst)], check=True)
    labels = {k: int(re.search(r'^' + k + r'\s+A:([0-9A-Fa-f]+)', lst.read_text(), re.M)[1], 16) for k in ['finished', 'mem', 'regs', 'diffs']}
    blob = binary.read_bytes(); assert code + len(blob) < b + 0x4d000, 'fixture overlaps game code'
    cmd('delete breakpoints'); cmd('monitor tfxreg 16 2700')
    for o in range(0, len(blob), 32): cmd(f'monitor tfxmem {code + o:x} {blob[o:o + 32].hex()}')
    cmd(f'monitor tfxreg 17 {code:x}'); cmd(f'break *{labels["finished"]:#x}'); reply = cmd('continue')
    assert f'0x{labels["finished"]:08x}' in reply, reply[-1000:]
    mem = int.from_bytes(dump('allocation.bin', labels['mem'], 4), 'big'); assert mem
    regs = dump('regs.bin', labels['regs'], n * 128); diffs = struct.unpack(f'>{n}I', dump('diffs.bin', labels['diffs'], n * 4))
    cmd(f'monitor tfxsync {mem + total * 36:x} {total * 36}'); cand_pts = dump('points.bin', mem + total * 36, total * 36)
    assert int.from_bytes(dump('rot-table-after.bin', rt, 4), 'big') == table_ptr
    cmd(f'monitor tfxsync {table_ptr:x} {SLOTS * BUCKETS * 32}'); dump('rot-table-data.bin', table_ptr, SLOTS * BUCKETS * 32)
    dump('rot-vars.bin', sb + sym('rot_table'), 4 + 4 + 2 + 2 + 20 + 20 * SLOTS)

    def verify(c, ro, rc, pts, diff):
        exp, d3 = model_points(c)
        got = [struct.unpack_from('>3I', pts, 36 * j) for j in range(len(c['points']))]
        R = lambda r, k: struct.unpack_from('>I', r, 4 * k)[0]
        return dict(points_diff_longs=diff, regs=ro[:56] == rc[:56] and R(rc, 14) - R(ro, 14) == total * 36, ccr=(ro[61] & 0x1f) == (rc[61] & 0x1f), model_points=got == exp,
                    model_d3=R(rc, 3) == d3, model_d01=(R(rc, 0), R(rc, 1)) == tuple(v & 0xffffffff for v in c['points'][-1]),
                    model_a2a4=tuple(R(rc, k) for k in (10, 11, 12)) == exp[-1], x_kept=((rc[61] >> 4) & 1) == c['x'])

    def passed(v): return v['points_diff_longs'] == 0 and all(v[k] for k in v if k != 'points_diff_longs')

    hits = model_hits(); results = []; off = 0
    for i, c in enumerate(cases):
        np_ = len(c['points']); ro, rc = regs[i * 128:i * 128 + 64], regs[i * 128 + 64:i * 128 + 128]
        v = verify(c, ro, rc, cand_pts[off * 36:(off + np_) * 36], diffs[i]); off += np_
        results.append(dict(case=i, mat=c['mat'], points=np_, plain=c['plain'], x=c['x'], hits=hits[i], **v, ok=passed(v)))
    # Negative controls: a wrong stored sum, a wrong D3, a wrong X, and a stale entry
    # (the points of the same deltas under another matrix).
    k = next(i for i, r in enumerate(results) if r['hits'] >= 3 and r['points'] == 27); c = cases[k]
    o = sum(len(x['points']) for x in cases[:k]) * 36; pts = bytearray(cand_pts[o:o + 27 * 36]); ro, rc = regs[k * 128:k * 128 + 64], regs[k * 128 + 64:k * 128 + 128]
    controls = {}
    bad = bytearray(pts); bad[36 * 5 + 7] ^= 1; controls['sum'] = not passed(verify(c, ro, rc, bad, diffs[k]))
    badr = bytearray(rc); badr[15] ^= 1; controls['d3'] = not passed(verify(c, ro, bytes(badr), pts, diffs[k]))
    badx = bytearray(rc); badx[61] ^= 0x10; controls['x_flag'] = not passed(verify(c, ro, bytes(badx), pts, diffs[k]))
    other = dict(c, mat=(c['mat'] + 1) % len(mats)); stale = b''.join(struct.pack('>3I', *p) + bytes(24) for p in model_points(other)[0])
    controls['stale_matrix'] = not passed(verify(c, ro, rc, stale, diffs[k]))
    summary = dict(cases=n, passed=sum(r['ok'] for r in results), points=total, modelled_hits=sum(hits),
                   plain_points=sum(r['points'] for r in results if r['plain']), matrices=len(mats), game_entry104=hex(entry104), negative_controls_rejected=controls)
    (out / 'results.json').write_text(json.dumps(dict(summary, results=results), indent=1))
    assert summary['passed'] == n, [r for r in results if not r['ok']][:3]
    assert all(controls.values()), controls
    print('PASS', json.dumps(summary), flush=True)


EXTRA = {'040': '--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true', '060': '--uae_fpu_no_unimplemented=true',
         '030': '--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true', '020': '--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true'}[MACHINE]
v = dict(executable='tfx.020', custom3=3, custom4=18, swap=0x19fc, extra_args=EXTRA) if EXE == 'tfx.020' else dict(executable='TFX', custom3=1, custom4=18, swap=0x18a6, extra_args=EXTRA)
run(MACHINE, out, Path(str(out) + '-seed'), capture, v)
