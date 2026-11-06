"""Native twins for the Gouraud run fill against the chunky fill and c2p it replaces.

  opt20_gouraud_test.py OUT [PROBE_JSON]

Env: DELTA_LISTING (candidate slave listing), PROFILE_SLAVE (candidate slave), MACHINE
(040 default; 060 runs the DIVU.L body), GF_ENTRY=c (C entries: gouraud_fill against
gouraud_runs_c, y and the scan table pushed as TFX does; default: gouraud_fill_new against
gouraud_runs with the stream inline after the return address, as tfx.020 passes it).
Both sides run inside the game process (tfx.020) from the same slave.
The guest points the game screen at its own 64,000-byte buffer and, per scan stream,
fills it with fixed pseudo-random junk, copies the stream to a scratch stack (inline
after the return address, as tfx.020 passes it), loads the same junk into D0-D7/A0-A4/A6 and y
(junk upper word) into A5, calls a side, stores D0-A6 and CCR, and compares all eight
planes of the candidate's screen with the original's (mismatching longs, first index).
Streams: the follow-camera probe's real scan tables (PROBE_JSON, frames 1-2), and
synthetic rows at every start pixel 0-63 with widths 1-320 and colour ramps that are
flat, shallow, steep, negative, wrapping past colour 255, carrying bits above 23,
dcdx of 0, +-1, +-$4000, +-$8000, +-$ffff, +-$10000 and +-$10001, and for every pixel
count 1-320 the largest |rc-lc| the fast path takes (both signs, and just inside). The first DUMPN streams' screens (all synthetic ones, then probe streams) from both sides are checked
on the host against a Python model of the original (bits 16-23 of lc+dcdx/2+i*dcdx, DIVS.L
truncation). Negative controls must be rejected by the same verifiers.
"""
import os, sys, json, struct, subprocess, re
from pathlib import Path
from replay_flight import ROOT, run
out = Path(sys.argv[1]).resolve(); os.chdir(ROOT)
probe = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else None
MACHINE = os.environ.get('MACHINE', '040')
W, H, BPL = 320, 200, 8000; SCR = 8 * BPL; DUMPN = 24; REC = 64
JUNK = [[0x11110000 + 0x1111 * r for r in range(14)], [0xfedc0000 ^ (0x01010101 * r) for r in range(14)]]

def s32(x): x &= 0xffffffff; return x - (1 << 32) if x & 0x80000000 else x

streams, probed = [], []                                   # (y, [(lx, rx, lc, rc)])
if probe:
    for c in probe['calls']:
        if c['frame'] <= 2 and c['rows'] and c['y'] - len(c['rows']) + 1 >= 0 and c['y'] < H:
            probed.append((c['y'], [tuple(r) for r in c['rows']]))
RAMPS = [(0x400000, 0x400000), (0x123456, 0x177777), (0x200000, 0x0f8000), (0x10000, 0x7f0000), (0x7f0000, 0x10000),
         (0xf00000, 0x1180000), (0x3a5a5a5, 0x3a9a5a5), (0xff8000, 0x1008000), (0x0, 0xff0000), (0x500000, 0x4f0000)]
STEPS = [0, 1, -1, 0x3fff, 0x4000, -0x4000, 0x8000, -0x8000, 0xffff, -0xffff, 0x10000, -0x10000, 0x10001, -0x10001]
syn = []
for x0 in range(64):
    for wd in (1, 2, 3, 5, 8, 13, 16, 31, 32, 33, 40, 63, 64, 65, 97, 130, 200, 256, W - x0):
        if x0 + wd > W: continue
        syn.append((x0, x0 + wd - 1))
rows = []
for i, (x0, x1) in enumerate(syn):
    n = x1 - x0 + 1; k = i % (len(RAMPS) + len(STEPS))
    if k < len(RAMPS): lc, rc = RAMPS[k]
    else:                                                  # dcdx at the walk's bounds (|dcdx| <= $ffff) and around them
        d = STEPS[k - len(RAMPS)]; lc = 0x200000 + (i & 7) * 0x10000; rc = lc + d * n
    frac = (i * 0x1357) & 0xffff
    rows.append(((x0 << 16) | frac, (x1 << 16) | (frac ^ 0xffff), (lc + frac) & 0xffffffff, (rc + frac) & 0xffffffff))
# Largest |rc-lc| the fast path takes (span 8 + (pixels-1)/4) for every pixel count, both
# signs, and just inside: the reciprocal multiply's exactness bound.
for n in range(1, W + 1):
    amax = ((8 + (n - 1) // 4) + 1) * 65536 - 1; x0 = (n * 37) % (W - n + 1)
    for j, d in enumerate((amax, -amax, amax - n, -(amax - 2 * n - 1))):
        lc = 0x300000 + ((n * 0x9e37 + j * 0x1111) & 0xffff)
        rows.append(((x0 << 16) | (j * 0x4321 & 0xffff), ((x0 + n - 1) << 16), lc & 0xffffffff, (lc + d) & 0xffffffff))
for o in range(0, len(rows), 150):
    streams.append((H - 1, rows[o:o + 150]))
streams += probed + [(50, [])]                             # synthetic first (model-checked), terminator only last
assert all(len(r) < 300 for _, r in streams)

def model(junk, y, rws):
    scr = bytearray(junk)
    for r, (lx, rx, lc, rc) in enumerate(rws):
        x0, x1 = lx >> 16, rx >> 16; n = x1 - x0 + 1; d = s32(rc - lc); q = abs(d) // n; dc = q if d >= 0 else -q
        c = (lc + (dc >> 1)) & 0xffffffff; row = (y - r) * 40
        for i in range(n):
            col = ((c + i * dc) & 0xffffffff) >> 16 & 0xff; x = x0 + i
            for p in range(8):
                a = p * BPL + row + (x >> 3); bit = 0x80 >> (x & 7)
                scr[a] = (scr[a] | bit) if col >> p & 1 else (scr[a] & ~bit)
    return bytes(scr)

def junk_bytes():
    v = 0x12345678; b = bytearray()
    for _ in range(SCR // 4): v = (v * 1103515245 + 12345) & 0xffffffff; b += struct.pack('>I', v)
    return bytes(b)

def capture(cmd, dump, bases, hs, out):
    b = bases[0]; code = b + 0x8000
    lst = Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
    sym = lambda n: int(re.search(r'^' + n + r'\s+00:([0-9A-Fa-f]+)', lst, re.M)[1], 16)
    sb = int.from_bytes(dump('swap-target.bin', b + 0x19fe, 4), 'big') - sym('do_swap_screen')
    C = os.environ.get('GF_ENTRY') == 'c'
    orig, cand = (sb + sym('gouraud_fill'), sb + sym('gouraud_runs_c')) if C else (sb + sym('gouraud_fill_new'), sb + sym('gouraud_runs'))
    if MACHINE == '040':
        assert dump('gouraud-patch.bin', b + 0x4f840, 6) == bytes.fromhex('4ef9') + (sb + sym('gouraud_runs')).to_bytes(4, 'big')
    assert dump('orig-entry.bin', orig, 4).hex() == ('4e560000' if C else '48e7fffe')
    logbase, screen1 = sb + sym('_logbase_ptr'), sb + sym('_screen1_ptr')
    n = len(streams); RES = n * (2 * REC + 8)
    # Allocation: junk, screen, results, DUMPN screen pairs, scratch copy of the original's screen.
    alloc = 2 * SCR + RES + DUMPN * 2 * SCR + SCR
    a = [' mc68040', f' org ${code:x}', f' move.l #{alloc},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,mem', ' beq.l finished',
         ' move.l d0,a0', ' move.l #$12345678,d0', f' move.w #{SCR // 4 - 1},d1', 'lcg: mulu.l #1103515245,d0', ' add.l #12345,d0', ' move.l d0,(a0)+', ' dbf d1,lcg',
         f' move.l ${logbase:x},a0', ' clr.w (a0)', f' move.l ${screen1:x},a0', ' move.l mem(pc),d0', f' add.l #{SCR},d0', ' move.l d0,(a0)',
         f' add.l #{SCR},d0', ' move.l d0,resp', f' add.l #{RES},d0', ' move.l d0,dumpp', f' add.l #{DUMPN * 2 * SCR},d0', ' move.l d0,scratchp',
         ' lea cases(pc),a0', ' move.l a0,casep', f' move.w #{n - 1},count', ' clr.w index', 'next:']
    copy = lambda src, dst, lbl: [src, dst, f' move.w #{SCR // 4 - 1},d0', f'{lbl}: move.l (a0)+,(a1)+', f' dbf d0,{lbl}']
    for side in (0, 1):
        a += copy(' move.l mem(pc),a0', f' move.l mem(pc),a1\n add.l #{SCR},a1', f'cj{side}')
        a += [' move.l casep(pc),a0', ' move.l (a0)+,a1', ' move.w (a0)+,d1', ' move.w (a0)+,d0', ' lea stk_top(pc),a2',
              f'cs{side}: move.l (a1)+,(a2)+', f' dbf d0,cs{side}',
              ' move.w d1,yv+2', ' move.w index(pc),d0', ' and.w #1,d0', ' lsl.w #4,d0', ' move.w d0,ccrv',     # X set on odd streams
              ' move.l sp,savesp'] + ([' lea cstk_top(pc),sp', ' pea stk_top(pc)', ' move.l yv(pc),-(sp)'] if C else [' lea stk_top(pc),sp']) + [' movem.l junk1(pc),d0-d7/a0-a4/a6', ' move.l yv(pc),a5', ' move.w ccrv(pc),ccr',
              f' jsr ${orig if side == 0 else cand:x}', ' move.l savesp(pc),sp', ' movem.l d0-d7/a0-a6,save', ' move.w ccr,d0', ' move.w d0,save+60',
              ' move.l resp(pc),a0', ' lea save(pc),a1', ' moveq #15,d7', f'cr{side}: move.l (a1)+,(a0)+', f' dbf d7,cr{side}', ' move.l a0,resp']
        if side == 0:
            a += copy(f' move.l mem(pc),a0\n add.l #{SCR},a0', ' move.l scratchp(pc),a1', 'ca0')
        else:
            a += [' move.l mem(pc),a1', f' add.l #{SCR},a1', ' move.l scratchp(pc),a2', ' moveq #0,d1', ' moveq #-1,d2', ' moveq #0,d3', f' move.w #{SCR // 4 - 1},d0',
                  'cmp1: cmpm.l (a1)+,(a2)+', ' beq.s eq1', ' addq.l #1,d1', ' tst.l d2', ' bpl.s eq1', ' move.l d3,d2', 'eq1: addq.l #1,d3', ' dbf d0,cmp1',
                  ' move.l resp(pc),a0', ' move.l d1,(a0)+', ' move.l d2,(a0)+', ' move.l a0,resp',
                  f' cmp.w #{DUMPN},index', ' bhs.w nodump']
            a += copy(' move.l scratchp(pc),a0', ' move.l dumpp(pc),a1', 'd0l') + [' move.l a1,dumpp']
            a += copy(f' move.l mem(pc),a0\n add.l #{SCR},a0', ' move.l dumpp(pc),a1', 'd1l') + [' move.l a1,dumpp', 'nodump:']
    a += [' addq.l #8,casep', ' addq.w #1,index', ' subq.w #1,count', ' bpl.w next', 'finished: bra.s finished']
    a += [' cnop 0,4', 'junk0:'] + [f' dc.l ${x:08x}' for x in JUNK[0]] + ['junk1:'] + [f' dc.l ${x:08x}' for x in JUNK[1]]
    a += ['mem: dc.l 0', 'resp: dc.l 0', 'dumpp: dc.l 0', 'scratchp: dc.l 0', 'casep: dc.l 0', 'savesp: dc.l 0', 'yv: dc.l $a5a50000', 'count: dc.w 0', 'index: dc.w 0',
          'ccrv: dc.w 0', f'save: ds.b {REC}', ' ds.b 1024', 'cstk_top:', ' ds.b 2048', 'stk_top:', f' ds.b {16 * 300 + 16}', 'cases:']
    a += [f' dc.l s{i}\n dc.w {y}\n dc.w {(len(rws) + 1) * 4 - 1}' for i, (y, rws) in enumerate(streams)]
    for i, (y, rws) in enumerate(streams):
        a += [f's{i}:'] + [f' dc.l ${lx:08x},${rx:08x},${lc:08x},${rc:08x}' for lx, rx, lc, rc in rws] + [' dc.l $00020000,$00010000,0,0']
    txt = '\n'.join(a) + '\n'
    src = out / 'fixture.s'; src.write_text(txt); binary = out / 'fixture.bin'; listing = out / 'fixture.lst'
    subprocess.run(['bash', '-c', '. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"', 'fixture', str(src), str(binary), str(listing)], check=True)
    labels = {k: int(re.search(r'^' + k + r'\s+A:([0-9A-Fa-f]+)', listing.read_text(), re.M)[1], 16) for k in ['finished', 'mem', 'resp']}
    blob = binary.read_bytes(); assert code + len(blob) < b + 0x4b000, 'fixture overlaps game code'
    for ptr in (logbase, screen1):
        target = int.from_bytes(dump('ptr.bin', ptr, 4), 'big'); assert not code <= target < code + len(blob), hex(target)
    cmd('delete breakpoints'); cmd('monitor tfxreg 16 2700')
    for off in range(0, len(blob), 32): cmd(f'monitor tfxmem {code + off:x} {blob[off:off + 32].hex()}')
    cmd(f'monitor tfxreg 17 {code:x}'); cmd(f'break *{labels["finished"]:#x}'); reply = cmd('continue')
    assert f'0x{labels["finished"]:08x}' in reply, reply[-1000:]
    cmd(f'monitor tfxsync {labels["mem"]:x} 4')
    mem = int.from_bytes(dump('mem-ptr.bin', labels['mem'], 4), 'big'); assert mem, 'allocation failed'
    size = RES + DUMPN * 2 * SCR
    cmd(f'monitor tfxsync {mem:x} {2 * SCR + size}'); junk = dump('junk.bin', mem, SCR); data = dump('results.bin', mem + 2 * SCR, size)
    assert junk == junk_bytes()
    results = []; recs = data[:RES]; dumps = data[RES:]
    def verify(r, y):
        o, c = struct.unpack_from('>15I', r, 0), struct.unpack_from('>15I', r, REC)
        oc, cc = struct.unpack_from('>H', r, 60)[0] & 0x1f, struct.unpack_from('>H', r, REC + 60)[0] & 0x1f
        bad, first = struct.unpack_from('>Ii', r, 2 * REC)
        return dict(regs=o == c, ccr=oc == cc, planes=bad == 0 and first == -1,
                    kept=list(c[:13]) == JUNK[1][:13] and c[14] == JUNK[1][13] and (c[13] & 0xffff) == y), bad, first
    rec = lambda i: recs[i * (2 * REC + 8):(i + 1) * (2 * REC + 8)]
    for i, (y, rws) in enumerate(streams):
        v, bad, first = verify(rec(i), y)
        results.append(dict(stream=i, y=y, rows=len(rws), **v, bad_longs=bad, first=first, ok=all(v.values())))
    def model_ok(i, so, sc):
        y, rws = streams[i]; m = model(junk, y, rws); return so == m and sc == m
    checked = []
    for i in range(min(DUMPN, n)):
        so, sc = dumps[(2 * i) * SCR:(2 * i + 1) * SCR], dumps[(2 * i + 1) * SCR:(2 * i + 2) * SCR]
        checked.append(model_ok(i, so, sc))
    k = next(i for i in range(min(DUMPN, n)) if streams[i][1])
    so, sc = dumps[(2 * k) * SCR:(2 * k + 1) * SCR], dumps[(2 * k + 1) * SCR:(2 * k + 2) * SCR]
    y, rws = streams[k]; lx = rws[0][0] >> 16; at = 5 * BPL + y * 40 + (lx >> 3)
    flip = lambda s: s[:at] + bytes([s[at] ^ (0x80 >> (lx & 7))]) + s[at + 1:]
    def corrupt(off, mask):
        r = bytearray(rec(k)); r[off] ^= mask; return not all(verify(bytes(r), streams[k][0])[0].values())
    controls = dict(candidate_pixel=not model_ok(k, so, flip(sc)), both_sides_pixel=not model_ok(k, flip(so), flip(sc)),
                    plane_count=corrupt(2 * REC + 3, 1), register=corrupt(REC + 7, 1), x_flag=corrupt(REC + 61, 0x10), a5_kept=corrupt(REC + 55, 1))
    summary = dict(streams=n, rows=sum(len(s[1]) for s in streams), probe_streams=len(probed),
                   passed=sum(r['ok'] for r in results), model_checked=len(checked), model_passed=sum(checked),
                   negative_controls_rejected=controls)
    (out / 'results.json').write_text(json.dumps(dict(summary, results=results), indent=0))
    assert summary['passed'] == n, [r for r in results if not r['ok']][:3]
    assert all(checked), checked
    assert all(controls.values()), controls
    print('PASS', json.dumps(summary), flush=True)

EXTRA = {'040': '--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true', '060': '--uae_fpu_no_unimplemented=true',
         '020': '--uae_fpu_model=68882 --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true', '030': '--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true'}[MACHINE]
v = dict(executable='tfx.020', custom3=3, custom4=18, swap=0x19fc, extra_args=EXTRA)
run(MACHINE, out, Path(str(out) + '-seed'), capture, v)
