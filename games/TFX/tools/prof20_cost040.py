#!/usr/bin/env python3
"""Re-weight a strict profile with an approximate MC68040 cycle table.

  prof20_cost040.py PROFILE_DIR LISTING [OUT.json]

The NOMMU observer charges almost every instruction the same padded cost, so its
ranking is close to an instruction count. This script multiplies each PC's execution
count by an estimated 68040 issue cost (cache hits, MC68040 UM-style figures) and adds a
fixed penalty per logical chip access. It is an estimate for prioritising work, not a
hardware measurement; calibrate against Apollo micro-benchmarks before relying on it.
"""
import csv, json, re, struct, sys, os, collections
from pathlib import Path
sys.path.insert(0, os.environ.get('AMIGA_PYLIB', os.path.expanduser('~/.local/share/amiga/pylib')))
from amigaxdev.disasm import records
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prof20_analyze_lib as lib

CHIP_W = float(os.environ.get('CHIP_W', 20)); CHIP_R = float(os.environ.get('CHIP_R', 24))

def cost(text):
    m = text.split()[0] if text else ''
    ops = text[len(m):]
    mem = ops.count('(') - ops.count('(pc') - ops.count(',pc')  # memory operands (approx)
    mem = max(0, ops.count('(')) if '(' in ops else 0
    base = m.split('.')[0]
    if base in ('muls', 'mulu'): return 20 if m.endswith('.l') else 16
    if base in ('divs', 'divu', 'divsl', 'divul'): return 44 if m.endswith('.l') else 27
    if base.startswith('bf'):
        reg = '(' not in ops
        return (3 if base in ('bfextu', 'bfexts', 'bftst', 'bfffo') else 5) if reg else (8 if base in ('bfextu', 'bfexts', 'bftst') else 10)
    if base == 'fdiv' or base == 'fsdiv' or base == 'fddiv': return 38 + (4 if '#' not in ops and 'fp' not in ops.split(',')[0] else 0)
    if base == 'fsqrt': return 103
    if base in ('fmul', 'fsmul', 'fdmul'): return 5 + (4 if 'fp' not in ops.split(',')[0] else 0)
    if base in ('fadd', 'fsub', 'fcmp', 'fsadd', 'fssub', 'fdadd', 'fdsub'): return 3 + (4 if 'fp' not in ops.split(',')[0] else 0)
    if base == 'fmove':
        src, dst = (ops.split(',') + [''])[:2]
        if 'fpcr' in ops or 'fpsr' in ops: return 6
        if 'fp' in src and 'fp' not in dst: return 8      # FP -> integer/memory with conversion
        if 'fp' not in src: return 4                      # integer/memory -> FP
        return 2
    if base == 'fmovem': return 3 + 4 * max(1, ops.count('fp'))
    if base.startswith('f'): return 4
    if base == 'movem':
        regs = ops.split(',')[0] if '(' not in ops.split(',')[0] else ops.split(',')[-1]
        n = 0
        for part in regs.split('/'):
            r = re.findall(r'([ad])(\d)', part)
            if len(r) == 2:
                (ka, a), (kb, b) = r; n += (int(b) + 8 * (kb == 'a')) - (int(a) + 8 * (ka == 'a')) + 1
            else: n += max(1, len(r))
        return 2 + n
    if base in ('rts', 'rte', 'rtr'): return 7
    if base in ('jsr', 'bsr'): return 3
    if base in ('jmp',): return 3 if '[' not in ops else 6
    if base in ('dbf', 'dbra') or base.startswith('db'): return 3
    if base in ('bra', 'bcc', 'bcs', 'beq', 'bne', 'bge', 'bgt', 'ble', 'blt', 'bhi', 'bls', 'bmi', 'bpl', 'bvc', 'bvs') or re.match(r'b(ra|eq|ne|cc|cs|ge|gt|le|lt|hi|ls|mi|pl|vc|vs)$', base): return 2
    if base in ('link', 'unlk'): return 4
    if base in ('lsl', 'lsr', 'asl', 'asr', 'rol', 'ror', 'roxl', 'roxr'): return 2 + (1 if '(' in ops else 0)
    if base in ('subx', 'addx'): return 1 + (2 if '(' in ops else 0)
    if '([' in ops or '[' in ops: return 5           # memory-indirect addressing
    if base == 'move16': return 9
    return 1 + (1 if '(' in ops and base not in ('lea', 'pea') else 0) + (1 if ops.count('(') >= 2 else 0)

def estimate(p, lst):
    """Return (context, total estimated cycles, {region: [est, emu, instructions]})."""
    p = Path(p); ctx = lib.Context(p, lst)
    dump = str(p / 'fast.bin')
    text = {}
    fast = sorted(pc for pc in ctx.pcs if 0x40000000 <= pc < 0x42000000)
    ranges = []
    for pc in fast:
        if ranges and pc - ranges[-1][1] < 256: ranges[-1][1] = pc + 12
        else: ranges.append([pc, pc + 12])
    for a, b in ranges:
        for off, raw, t in records(dump, 0x40000000, 0, a, b, '68040'):
            text[off] = t
    agg = collections.defaultdict(lambda: [0.0, 0.0, 0])
    tot = 0.0
    for pc, v in ctx.pcs.items():
        t = text.get(pc)
        c = v['n'] * (cost(t) if t else 2) + v['chipw'] * CHIP_W + v['chipr'] * CHIP_R
        key = ctx.region(pc)[1]
        agg[key][0] += c; agg[key][1] += ctx.emu_cost(v); agg[key][2] += v['n']
        tot += c
    return ctx, tot, agg

def main():
    ctx, tot, agg = estimate(sys.argv[1], sys.argv[2])
    emu = ctx.duration
    f = ctx.frames
    print(f"estimated 040 cycles/frame {tot/f:,.0f} -> {40e6/(tot/f):.1f} fps if CPU-bound at 40 MHz (no cache misses, chip W={CHIP_W} R={CHIP_R})")
    print(f"emulator cycles/frame {emu/ctx.div/f:,.0f}")
    res = sorted(agg.items(), key=lambda kv: -kv[1][0])
    out = []
    for name, (c, e, n) in res[:45]:
        print(f"{100*c/tot:6.2f}% est  {100*e/emu:6.2f}% emu  {c/f:10,.0f} cyc/f  cpi {c/max(n,1):5.2f}  {name}")
        out.append(dict(name=name, est_pct=100 * c / tot, emu_pct=100 * e / emu, est_cycles_per_frame=c / f, est_cpi=c / max(n, 1)))
    if len(sys.argv) > 3: Path(sys.argv[3]).write_text(json.dumps(dict(est_cycles_per_frame=tot / f, chip_w=CHIP_W, chip_r=CHIP_R, regions=out), indent=1))

if __name__ == '__main__': main()
