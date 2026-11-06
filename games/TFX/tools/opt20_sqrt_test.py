"""Native twins for isqrt_040 (step 9) against @SquareRoot ($4bdca).

  opt20_sqrt_test.py OUT

Both sides run inside the game process: the original is a verbatim copy of $4bdca-$4bdf3
(position-independent: short branches only), the candidate is the patched entry. One guest
loop calls each side per input with junk in D1-D7/A0-A6 and X set or clear, and stores
D0-D7/A0-A6 and CCR. The host compares the sides and checks the candidate against
floor(sqrt(n)), unchanged D1-D7/A0-A6 and CCR X/V/C clear, N/Z from the root. Inputs:
every entry block (each leading-bit position, 0 and 2^32-1), squares and their
neighbours, powers of two and four and their neighbours, and pseudo-random values.
Negative controls must be rejected by the same verifier.
"""
import os, sys, json, struct, subprocess, re, math
from pathlib import Path
from replay_flight import ROOT, run
out = Path(sys.argv[1]).resolve(); os.chdir(ROOT)

inputs = set([0, 1, 2, 3, 4, 5, 0xffffffff, 0xfffffffe, 0x80000000, 0x7fffffff, 0x40000000, 0x3fffffff, 0xfffe0001, 0xfffe0000])
for b in range(32):
    for d in (-1, 0, 1):
        inputs.add(((1 << b) + d) & 0xffffffff)
    inputs.add((1 << b) | ((1 << b) - 1))                  # all ones below the leading bit
for k in list(range(0, 300)) + list(range(65200, 65536)) + [k * 97 for k in range(1, 675)]:
    for d in (-1, 0, 1):
        inputs.add((k * k + d) & 0xffffffff)
seed = 0x13579bdf
for i in range(1200):
    seed = (seed * 1103515245 + 12345) & 0xffffffff
    inputs.add(seed >> (i % 32))                           # every magnitude
inputs = sorted(inputs)
JUNK = [[0x11110000 + 0x1111 * r for r in range(14)], [0xfedc0000 ^ (0x01010101 * r) for r in range(14)]]
cases = [(n, i % 2, (i // 2) % 2) for i, n in enumerate(inputs)]  # (input, x, junk set)
REC = 64


def isqrt(n): return math.isqrt(n)


def capture(cmd, dump, bases, hs, out):
    b = bases[0]; code = b + 0x8000
    orig = hs[0]['bytes'][0x4bdca:0x4bdf4]
    assert orig[:6].hex() == '48e70f002e00' and orig[-2:].hex() == '4e75', orig.hex()
    assert dump('sqrt-patch.bin', b + 0x4bdca, 2) == bytes.fromhex('4ef9')
    n = len(cases)
    a = [' mc68040', f' org ${code:x}', f' move.l #{2 * n * REC},d0', ' move.l #$10001,d1', ' move.l 4.w,a6', ' jsr -198(a6)', ' move.l d0,results',
         ' beq.l finished', ' move.l d0,outp', ' lea table(pc),a0', ' move.l a0,inp', f' move.w #{n - 1},count']
    a += ['next:']
    for side in (0, 1):
        a += [' move.l inp(pc),a0', ' move.l (a0),d0', ' move.w 6(a0),d1', ' lea junk0(pc),a1', ' tst.w 4(a0)', f' beq.s j{side}', ' lea junk1(pc),a1', f'j{side}:',
              ' move.w d1,ccrv', ' movem.l (a1),d1-d7/a0-a6', ' move.w ccrv(pc),ccr', f' jsr {"orig" if side == 0 else "cand"}',
              ' movem.l d0-d7/a0-a6,save', ' move.w ccr,d0', ' move.w d0,save+60', ' move.l outp(pc),a0', ' lea save(pc),a1', ' moveq #15,d7',
              f'copy{side}:', ' move.l (a1)+,(a0)+', f' dbf d7,copy{side}', ' move.l a0,outp']
    a += [' addq.l #8,inp', ' subq.w #1,count', ' bpl.w next', 'finished: bra.s finished', 'orig:'] + [f' dc.b ${x:02x}' for x in orig] + [f'cand: jmp ${b + 0x4bdca:x}',
          ' cnop 0,4', 'junk0:'] + [f' dc.l ${x:08x}' for x in JUNK[0]] + ['junk1:'] + [f' dc.l ${x:08x}' for x in JUNK[1]] + \
         ['results: dc.l 0', 'outp: dc.l 0', 'inp: dc.l 0', 'count: dc.w 0', 'ccrv: dc.w 0', f'save: ds.b {REC}', 'table:'] + \
         [f' dc.l ${nv:08x}\n dc.w {j}\n dc.w ${0x1f if x else 0x0f:x}' for nv, x, j in cases]
    src = out / 'fixture.s'; src.write_text('\n'.join(a) + '\n'); binary = out / 'fixture.bin'; listing = out / 'fixture.lst'
    subprocess.run(['bash', '-c', '. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"', 'fixture', str(src), str(binary), str(listing)], check=True)
    labels = {k: int(re.search(r'^' + k + r'\s+A:([0-9A-Fa-f]+)', listing.read_text(), re.M)[1], 16) for k in ['finished', 'results', 'orig']}
    blob = binary.read_bytes(); assert code + len(blob) < b + 0x4b000, 'fixture overlaps game code'
    assert blob[labels['orig'] - code:labels['orig'] - code + len(orig)] == orig
    cmd('delete breakpoints'); cmd('monitor tfxreg 16 2700')
    for off in range(0, len(blob), 32): cmd(f'monitor tfxmem {code + off:x} {blob[off:off + 32].hex()}')
    cmd(f'monitor tfxreg 17 {code:x}'); cmd(f'break *{labels["finished"]:#x}'); reply = cmd('continue')
    assert f'0x{labels["finished"]:08x}' in reply, reply[-1000:]
    cmd(f'monitor tfxsync {labels["results"]:x} 4')
    res = int.from_bytes(dump('results-ptr.bin', labels['results'], 4), 'big'); assert res, 'allocation failed'
    cmd(f'monitor tfxsync {res:x} {2 * n * REC}'); data = dump('results.bin', res, 2 * n * REC)

    def verify(c, ro, rc):
        nv, x, j = c; R = lambda r: struct.unpack_from('>15I', r, 0); o, k = R(ro), R(rc)
        oc, cc = struct.unpack_from('>H', ro, 60)[0] & 0x1f, struct.unpack_from('>H', rc, 60)[0] & 0x1f
        root = isqrt(nv)
        return dict(regs=o == k, ccr=oc == cc, model_root=k[0] == root, model_kept=list(k[1:]) == JUNK[j],
                    model_ccr=cc == (4 if root == 0 else 0))

    results = []
    for i, c in enumerate(cases):
        ro, rc = data[(2 * i) * REC:(2 * i + 1) * REC], data[(2 * i + 1) * REC:(2 * i + 2) * REC]
        v = verify(c, ro, rc); lead = 32 - c[0].bit_length()
        results.append(dict(input=c[0], x=c[1], junk=c[2], entry=min(lead // 2, 16), **v, ok=all(v.values())))
    k = next(i for i, r in enumerate(results) if r['input'] == 0xfffe0001 and r['x'] == 1) if any(r['input'] == 0xfffe0001 and r['x'] == 1 for r in results) else \
        next(i for i, r in enumerate(results) if r['x'] == 1 and r['input'] > 1)
    c = cases[k]; ro, rc = data[(2 * k) * REC:(2 * k + 1) * REC], data[(2 * k + 1) * REC:(2 * k + 2) * REC]
    controls = {}
    for name, off, mask in (('root', 3, 1), ('register', 7, 1), ('x_flag', 61, 0x10), ('z_flag', 61, 4)):
        bad = bytearray(rc); bad[off] ^= mask; controls[name] = not all(verify(c, ro, bytes(bad)).values())
    # An off-by-one root (floor(sqrt) + 1 at k^2 - 1) on both sides: the model must reject it.
    k2 = next(i for i, r in enumerate(results) if r['input'] == 99)
    c2 = cases[k2]; ro2 = bytearray(data[(2 * k2) * REC:(2 * k2 + 1) * REC]); ro2[3] += 1
    controls['both_sides_wrong'] = not all(verify(c2, bytes(ro2), bytes(ro2)).values())
    entries = sorted(set(r['entry'] for r in results))
    summary = dict(cases=len(cases), passed=sum(r['ok'] for r in results), x_set=sum(r['x'] for r in results), entries=entries,
                   negative_controls_rejected=controls)
    (out / 'results.json').write_text(json.dumps(dict(summary, results=results), indent=0))
    assert summary['passed'] == len(cases), [r for r in results if not r['ok']][:3]
    assert entries == list(range(17)), entries
    assert all(controls.values()), controls
    print('PASS', json.dumps(summary), flush=True)


v = dict(executable='tfx.020', custom3=3, custom4=18, swap=0x19fc, extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040', out, Path(str(out) + '-seed'), capture, v)
