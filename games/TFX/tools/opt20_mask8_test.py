"""Native twins for mask_sprite8_040 (step 2) against the original eight-call plane loop.

  opt20_mask8_test.py OUT

Env: EXE=TFX (plain TFX, game addresses $1ba8 lower), MACHINE (040 default).
Both sides run inside the game process with _MaskSprite's real frame: LINK and the
MOVEM save of $4e23c, the plane loop (original copy, or the patched $4e400 jump), then
the game's own epilogue at $4e42e. Per case the guest compares all 64,064 destination
bytes of both sides; the host compares D0/D1/A0/A1/CCR and the parameter block, and
checks the candidate's eight plane windows against an independent byte oracle.
"""
import os, sys, json, struct, subprocess, re
from pathlib import Path
from replay_flight import ROOT, run
out = Path(sys.argv[1]).resolve(); os.chdir(ROOT)
# EXE=TFX: plain TFX, whose _MaskSprite is byte-identical $1ba8 lower; MACHINE selects the CPU.
EXE = os.environ.get('EXE', 'tfx.020'); MACHINE = os.environ.get('MACHINE', '040'); D = 0x1ba8 if EXE == 'TFX' else 0
A = lambda x: x - D

cases = []
for i in range(192):
    w = [1, 2, 3, 7, 20, 40][(i // 16) % 6]
    cases.append(dict(shift=i % 16, width=w, height=[1, 2, 8][i % 3],
                      first=[0xffff, 0, 0xa55a, 0x0fff][i % 4], last=[0xffff, 0, 0x6996, 0xf000][(i // 4) % 4],
                      amod=[0, 2, 6][i % 3], bmod=[0, 2, 6][(i // 2) % 3], dmod=[0, 2, 8, 40 - 2 * w if w <= 20 else 0][(i // 3) % 4],
                      stride=[4096, 1000, 2 * w * 8 + 64][i % 3], odd=i % 2))
MASK, DATA, DSTA, DSTB, SIZE = 0, 4096, 49152, 49152 + 65536, 49152 + 2 * 65536


def lcg(seed, n):
    out = []
    for _ in range(n):
        out.append(seed); seed = (((seed << 3) | (seed >> 29)) + 0x13ab) & 0xffffffff
    return out


mask = bytearray(b''.join(struct.pack('>I', x) for x in lcg(0x12345678, 1024)))
for k in range(0, 2048, 5): mask[2 * k:2 * k + 2] = b'\0\0'
data = b''.join(struct.pack('>I', x) for x in lcg(0x87654321, 8192)) + bytes(8192)
initial = b''.join(struct.pack('>I', x) for x in lcg(0xa55a6996, 16016))


def oracle(c):
    d = bytearray(initial)
    for p in range(8):
        mp = 32 + c['odd']; ip = 32 + c['odd'] + p * c['stride']; dp = 32 + p * 8000
        for y in range(c['height']):
            for x in range(c['width']):
                m = int.from_bytes(mask[mp:mp + 2], 'big'); v = int.from_bytes(data[ip:ip + 2], 'big')
                if x == 0: m &= c['first']
                if x == c['width'] - 1: m &= c['last']
                m <<= 16 - c['shift']; v <<= 16 - c['shift']; old = int.from_bytes(d[dp:dp + 4], 'big')
                d[dp:dp + 4] = ((old & ~m & 0xffffffff) | (v & m)).to_bytes(4, 'big')
                mp += 2; ip += 2; dp += 2
            mp += c['amod']; ip += c['bmod']; dp += c['dmod']
    return d


def capture(cmd, dump, bases, hs, out):
    b = bases[0]; code = b + 0x8000; param = b + A(0x4e518)
    assert hs[0]['bytes'][A(0x4e400):A(0x4e404)].hex() == '700723c9'
    assert dump('mask-patch.bin', b + A(0x4e400), 2) == bytes.fromhex('4ef9')
    orig_loop = hs[0]['bytes'][A(0x4e400):A(0x4e42e)]
    # Original $4e400 loop: MOVEQ #7,D0; five parameter stores; BSR $4e53a; ADDA.L A4,A0;
    # LEA 8000(A3),A3; DBF. Rewritten with absolute addresses (the BSR is PC-relative).
    assert orig_loop.hex() == ('7007' + '23c9' + struct.pack('>I', A(0x4e518) + 18).hex() + '23c8' + struct.pack('>I', A(0x4e518) + 22).hex()
                               + '23cb' + struct.pack('>I', A(0x4e518) + 26).hex() + '23cb' + struct.pack('>I', A(0x4e518) + 30).hex()
                               + '33c6' + struct.pack('>I', A(0x4e518) + 8).hex() + '61000118' + 'd1cc' + '47eb1f40' + '51c8ffd6'), orig_loop.hex()
    orig_asm = [' moveq #7,d0', 'oplane\\@:', f' move.l a1,${param + 18:x}', f' move.l a0,${param + 22:x}', f' move.l a3,${param + 26:x}',
                f' move.l a3,${param + 30:x}', f' move.w d6,${param + 8:x}', f' jsr ${b + A(0x4e53a):x}', ' adda.l a4,a0', ' lea 8000(a3),a3', ' dbf d0,oplane\\@']
    a = [' mc68040', f' org ${code:x}', f' move.l #{SIZE},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,mem',
         f' move.l #{len(cases) * 8192},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,windows',
         ' move.l mem(pc),a0', ' move.l #$12345678,d0', ' move.w #1023,d7', 'msrc:', ' move.l d0,(a0)+', ' rol.l #3,d0', ' add.l #$13ab,d0', ' dbf d7,msrc',
         # Zero every fifth mask word (transparent words exercise the skip path).
         ' move.l mem(pc),a0', ' move.w #2047,d7', ' moveq #0,d6', 'mzero:', ' tst.w d6', ' bne.s mnz', ' clr.w (a0)', 'mnz:', ' addq.l #2,a0',
         ' addq.w #1,d6', ' cmp.w #5,d6', ' bne.s mnr', ' moveq #0,d6', 'mnr:', ' dbf d7,mzero',
         ' move.l mem(pc),a0', f' lea {DATA}(a0),a0', ' move.l #$87654321,d0', ' move.w #8191,d7', 'dsrc:', ' move.l d0,(a0)+', ' rol.l #3,d0', ' add.l #$13ab,d0', ' dbf d7,dsrc']
    for i, c in enumerate(cases):
        a += [' move.l mem(pc),a0', f' lea {DSTA}(a0),a1', f' lea {DSTB}(a0),a2', ' move.l #$a55a6996,d0', ' move.w #16015,d7', f'init{i}:',
              ' move.l d0,(a1)+', ' move.l d0,(a2)+', ' rol.l #3,d0', ' add.l #$13ab,d0', f' dbf d7,init{i}']
        for side, dst in ((0, DSTA), (1, DSTB)):
            a += [f' lea ${param:x},a6', f' move.l #${(c["first"] << 16) | c["last"]:x},(a6)', f' move.w #${(c["shift"] << 12) | 0xfca:x},4(a6)',
                  f' move.w #{c["amod"]},10(a6)', f' move.w #{c["bmod"]},12(a6)', f' move.w #{c["dmod"]},16(a6)',
                  ' move.l mem(pc),a0', f' lea {32 + c["odd"]}(a0),a1', f' lea {DATA + 32 + c["odd"]}(a0),a2', f' lea {dst + 32}(a0),a3',
                  f' move.l #{c["stride"]},a4', f' move.w #{(c["height"] << 6) | c["width"]},d6', ' move.l a2,a0', ' move.l #$9abc1234,d1',
                  f' jsr {"orig" if side == 0 else "cand"}', ' move.w ccr,d7', f' movem.l d0-d1/d7/a0-a1,regs+{(i * 2 + side) * 20}',
                  f' lea ${param:x},a6', f' lea params+{(i * 2 + side) * 28},a5', ' move.l 4(a6),(a5)+', ' move.l 8(a6),(a5)+', ' move.l 18(a6),(a5)+',
                  ' move.l 22(a6),(a5)+', ' move.l 26(a6),(a5)+', ' move.l 30(a6),(a5)+', ' move.l (a6),(a5)+']
        a += [' move.l mem(pc),a0', f' lea {DSTA}(a0),a1', f' lea {DSTB}(a0),a2', ' moveq #0,d0', ' move.w #16015,d7', f'cmp{i}:', ' cmpm.l (a1)+,(a2)+',
              f' beq.s eq{i}', ' addq.l #1,d0', f'eq{i}:', f' dbf d7,cmp{i}', f' move.l d0,diffs+{i * 4}']
        if True:
            # Copy candidate plane windows for the host oracle.
            a += [' move.l mem(pc),a0', f' lea {DSTB}(a0),a1', ' move.l windows(pc),a2', f' lea {i * 8 * 1024}(a2),a2', ' moveq #7,d5', f'win{i}:',
                  ' move.w #255,d7', ' move.l a1,a3', f'wl{i}:', ' move.l (a3)+,(a2)+', f' dbf d7,wl{i}', ' lea 8000(a1),a1', f' dbf d5,win{i}']
    regs_entry = [' link a6,#0', ' movem.l d2-d7/a2-a6,-(sp)']
    a += ['finished: bra.s finished',
          'orig:'] + regs_entry + [x.replace('\\@', '') for x in orig_asm] + [f' jmp ${b + A(0x4e42e):x}',
          'cand:'] + regs_entry + [f' jmp ${b + A(0x4e400):x}',
          'mem: dc.l 0', 'windows: dc.l 0', f'regs: ds.b {len(cases) * 40}', f'params: ds.b {len(cases) * 56}', f'diffs: ds.l {len(cases)}']
    src = out / 'fixture.s'; src.write_text('\n'.join(a) + '\n'); binary = out / 'fixture.bin'; listing = out / 'fixture.lst'
    subprocess.run(['bash', '-c', '. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"', 'fixture', str(src), str(binary), str(listing)], check=True)
    labels = {n: int(re.search(r'^' + n + r'\s+A:([0-9A-Fa-f]+)', listing.read_text(), re.M)[1], 16) for n in ['finished', 'mem', 'windows', 'regs', 'params', 'diffs']}
    blob = binary.read_bytes(); assert code + len(blob) < b + 0x4d000, 'fixture overlaps game code it calls'
    cmd('delete breakpoints'); cmd('monitor tfxreg 16 2700')
    for off in range(0, len(blob), 32): cmd(f'monitor tfxmem {code + off:x} {blob[off:off + 32].hex()}')
    cmd(f'monitor tfxreg 17 {code:x}'); cmd(f'break *{labels["finished"]:#x}'); reply = cmd('continue')
    assert f'0x{labels["finished"]:08x}' in reply, reply[-1000:]
    n = len(cases)
    cmd(f'monitor tfxsync {labels["mem"]:x} {8 + n * 100}')
    mem = int.from_bytes(dump('allocation.bin', labels['mem'], 4), 'big'); win = int.from_bytes(dump('windows.bin', labels['windows'], 4), 'big')
    assert mem and win
    regs = dump('regs.bin', labels['regs'], n * 40); params = dump('params.bin', labels['params'], n * 56); diffs = struct.unpack(f'>{n}I', dump('diffs.bin', labels['diffs'], n * 4))
    cmd(f'monitor tfxsync {win:x} {n * 8192}'); windows = dump('windows-data.bin', win, n * 8192)
    results = []
    for i, c in enumerate(cases):
        ro, rc = regs[i * 40:i * 40 + 20], regs[i * 40 + 20:i * 40 + 40]
        po, pc = params[i * 56:i * 56 + 28], params[i * 56 + 28:i * 56 + 56]
        # Parameter-block pointers refer to each side's own destination.
        pc_adj = bytearray(pc); pc_adj[16:24] = (struct.pack('>I', struct.unpack_from('>I', pc, 16)[0] - (DSTB - DSTA)) * 2)
        rc_adj = bytearray(rc)
        exp = oracle(c); got = windows[i * 8192:(i + 1) * 8192]
        win_ok = all(got[p * 1024:(p + 1) * 1024] == exp[p * 8000:p * 8000 + 1024] for p in range(8))
        d0o, d1o, ccro, a0o, a1o = struct.unpack('>5I', ro); d0c, d1c, ccrc, a0c, a1c = struct.unpack('>5I', rc)
        results.append(dict(c, dest_diff_longs=diffs[i], d0=d0o == d0c == 0xffff, d1=d1o == d1c, ccr=(ccro & 0x1f) == (ccrc & 0x1f), ccr_value=ccro & 0x1f,
                            a0=a0o == a0c, a1=a1o == a1c, params=bytes(pc_adj) == po, oracle=win_ok, changed=sum(x != y for x, y in zip(exp, initial))))
    ok = [r for r in results if r['dest_diff_longs'] == 0 and r['d0'] and r['d1'] and r['ccr'] and r['a0'] and r['a1'] and r['params'] and r['oracle']]
    (out / 'results.json').write_text(json.dumps(dict(cases=n, passed=len(ok), results=results), indent=1))
    assert len(ok) == n, [r for r in results if r not in ok][:3]
    print('PASS', n, 'mask8 cases', flush=True)


EXTRA = {'040': '--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true', '060': '--uae_fpu_no_unimplemented=true',
         '030': '--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true', '020': '--uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true'}[MACHINE]
v = dict(executable='tfx.020', custom3=3, custom4=18, swap=0x19fc, extra_args=EXTRA) if EXE == 'tfx.020' else dict(executable='TFX', custom3=1, custom4=18, swap=0x18a6, extra_args=EXTRA)
run(MACHINE, out, Path(str(out) + '-seed'), capture, v)
