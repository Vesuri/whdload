"""Frame time and where it goes, from an `ab3d.py aprof` capture.

    python3 tools/frametime.py OUT.json [LABELS]

LABELS: tools/srcmatch.py output (default tmp/srcmatch.txt when present) names the hot
routines. Prints:
- calibration: colour clocks a field (PAL: 71051 for a 313-line field, 70824 for 312);
- frames: the complete ones between the first and last drawPt swap, fields a frame;
- work a frame in ms: the frame's fields less the frame wait (`wait` in CATEGORIES, and the
  slave's _waitvbl), mean, p50, p95, max;
- each category's ms a frame and share of the work (CATEGORIES in ab3d.py; `slave` is the
  slave and WHDLoad, `rom` the Kickstart, `logic` the rest of the game). `gap` is aprof's
  time outside instruction bodies: interrupt entry, and on the 68020/030 core the wait
  states and per-instruction tax wait_memory_cycles() adds after each instruction; on the
  040/060 core, instructions that advanced no time. It is charged to no PC, so the last
  column (DERIVED) shares it out by each category's instruction count;
- the routines with the most time;
- the pixel loops (LOOPS): pixels a frame, CPU clocks a pixel and ms a frame, and the c2p's
  ms a frame and clocks a Chip store. The frame totals drift between runs of one build (the
  game's timing follows the frame rate, so a faster build plays a different fight); the
  clocks a pixel hold within about 1%, so compare builds on those.

    python3 tools/frametime.py --loops OUT.json...

prints only the loops, a block a capture. The clocks are the instructions' own (no gap); the
CPU clock is the capture's (`uae_cpu_frequency` in EXTRA_ARGS at capture time), else CPU_MHZ
(default 50). Slave offsets come from the capture's build listing (BUILD at capture time,
else the BUILD environment variable, else release).
"""
import bisect
import re
import json
import os
import sys

GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


# Code no source label starts: the sky writer MAKEBACKROUT copies into backrout, and
# ObjDraw3's start before its first matched label.
EXTRA = [(0x18ffa, 'backrout (the sky writer, copied)'), (0x1931c, 'MAKEBACKROUT/putinbackdrop'),
         (0x21160, 'ObjDraw (object search)')]


def labels(path):
    out = list(EXTRA)
    if path and os.path.exists(path):
        for line in open(path):
            f = line.rstrip('\n').split('\t')
            if len(f) > 2 and f[2].startswith('$'):
                out.append((int(f[2][1:], 16), f[0]))
    out.sort()
    return out


# The pixel loops: (name, parts); a part is ('game', lo, hi, pixel PCs) in game code-hunk
# offsets, or ('slave', first label, end label, pattern) where the pattern matches the
# listing text of the instructions that run once a pixel. A loop that moves into the slave
# keeps its name and gets a slave part beside the game's.
LOOPS = [
    ('walls', [('slave', '_t_wdraw', '_t_walltop', r'K\*DS_STRIDE\(a3\)')]),
    ('gouraud spans', [('game', 0x20fd0, 0x21016, (0x20fe0, 0x21004))]),
    ('bitmap columns, a pixel visited', [('game', 0x21a0e, 0x21a82, (0x21a0e, 0x21a36, 0x21a60))]),
]


def listing(build):
    """The slave listing's labels {name: offset} and first instruction text {offset: text}."""
    path = os.path.join(GAME, 'tmp/build', build, 'AlienBreed3D.lst')
    labs, code = {}, {}
    if not os.path.exists(path):
        return labs, code
    for line in open(path, errors='replace'):
        m = re.match(r'^00:([0-9A-F]{8}) ([0-9A-F]+)\s+\t\s*\d+M?\s*(.*)$', line)
        if m:
            code.setdefault(int(m.group(1), 16), m.group(3).strip())
            continue
        m = re.match(r'^([0-9A-F]{8}) (\w+)$', line.rstrip())
        if m:
            labs[m.group(2)] = int(m.group(1), 16)
    return labs, code


def loops(d):
    """[(name, pixels a frame, clocks a pixel, ms a frame)] and the c2p's (ms a frame, clocks
    a Chip store), or None for a part the capture or listing lacks."""
    m = d['meta']
    build = m.get('build') or os.environ.get('BUILD', 'release')
    hz = m.get('cpu_hz') or float(os.environ.get('CPU_MHZ', 50)) * 1e6
    unit = 1 / (m['colorclock_hz'] * m['CYCLE_UNIT'])          # seconds a unit
    frames = max(1, sum(f['swap'] for f in d['fields']))
    gp = {int(k, 16): v for k, v in d['pcs'].items()}
    sp = {int(k, 16): v for k, v in d.get('slave_pcs', {}).items() if not k.startswith('-')}
    labs, code = listing(build)
    out = []
    for name, parts in LOOPS:
        px = units = 0
        ok = True
        for part in parts:
            if part[0] == 'game':
                _, lo, hi, pcs = part
                units += sum(v[0] for o, v in gp.items() if lo <= o < hi)
                px += sum(gp.get(o, [0, 0])[1] for o in pcs)
            else:
                _, a, b, pat = part
                if a not in labs or b not in labs:
                    ok = False
                    continue
                lo, hi = labs[a], labs[b]
                units += sum(v[0] for o, v in sp.items() if lo <= o < hi)
                px += sum(v[1] for o, v in sp.items()
                          if lo <= o < hi and re.search(pat, code.get(o, '')))
        out.append((name, px / frames if ok else None, units * unit * hz / px if ok and px else None,
                    units * unit * 1000 / frames if ok else None))
    c2 = [v for v in sp.values() if v[3] == 'c2p']
    st = [v for v in c2 if v[2] > v[0] / 2]                    # mostly Chip time: the stores
    c2p = (sum(v[0] for v in c2) * unit * 1000 / frames,
           sum(v[0] for v in st) * unit * hz / sum(v[1] for v in st) if st else None)
    return build, hz, frames, out, c2p


def print_loops(d):
    build, hz, frames, out, (c2ms, c2st) = loops(d)
    print(f'pixel loops ({frames} frames, build {build}, {hz / 1e6:g} MHz; instruction clocks, no gap):')
    print(f"  {'loop':32} {'px/frame':>9} {'clk/px':>7} {'ms/frame':>9}")
    for name, px, clk, msf in out:
        if px is None:
            print(f'  {name:32} not in the listing of build {build}')
            continue
        print(f"  {name:32} {px:9.0f} {clk if clk is not None else float('nan'):7.2f} {msf:9.2f}")
    st = f'{c2st:.1f} clocks a Chip store' if c2st else 'no Chip stores'
    print(f"  {'c2p':32} {'':9} {'':7} {c2ms:9.2f}  ({st})")


def main():
    if sys.argv[1] == '--loops':
        for i, path in enumerate(sys.argv[2:]):
            if i:
                print()
            print(path)
            print_loops(json.load(open(path)))
        return
    d = json.load(open(sys.argv[1]))
    lab = labels(sys.argv[2] if len(sys.argv) > 2 else os.path.join(GAME, 'tmp/srcmatch.txt'))
    m, fields = d['meta'], d['fields']
    cu = m['CYCLE_UNIT']
    ms = 1000 / m['colorclock_hz'] / cu          # ms per unit
    cc = [f['units'] / cu for f in fields]
    print(f"{len(fields)} fields, {m['cpu_model']}, CACR ${m['cacr']:x}; colour clocks a field "
          f"mean {sum(cc) / len(cc):.1f} min {min(cc):.0f} max {max(cc):.0f} (PAL 70824/71051)")
    bad = [i for i, f in enumerate(fields) if f['vsyncs'] != 1]
    if bad:
        print(f'WARNING: fields with vsyncs != 1: {bad[:10]}')
    # A field's own accounting: per-category PC units plus gap and high equal its units
    # less the tail.
    worst = max(abs(sum(f['cats'].values()) + f['gap'] + f['high'] + f['tail'] - f['units'])
                for f in fields)
    print(f'accounting: categories + gap + high + tail = units within {worst} units in every field;'
          f" largest stop tail {max(f['tail'] for f in fields) / cu:.1f} colour clocks")
    swaps = [i for i, f in enumerate(fields) if f['swap']]
    if len(swaps) < 2:
        sys.exit('fewer than two drawPt swaps: no complete frame')
    # A swap read after field i means the frame drawn in fields (previous swap, i] was shown,
    # so frame k is fields swaps[k]+1 .. swaps[k+1].
    frames = [(a + 1, b + 1) for a, b in zip(swaps, swaps[1:])]
    span = [b - a for a, b in frames]
    work = []
    tot, ex = {}, {}
    for a, b in frames:
        w = 0
        for f in fields[a:b]:
            cats = dict(f['cats'])
            cats['gap'] = f['gap'] + f['high']
            for k, v in cats.items():
                tot[k] = tot.get(k, 0) + v
            for k, v in f.get('execs', {}).items():
                ex[k] = ex.get(k, 0) + v
            w += f['units'] - cats.get('wait', 0) - f['tail']
        work.append(w * ms)
    n = len(frames)
    nf = sum(span)
    hist = ' '.join(f'{k}:{span.count(k)}' for k in sorted(set(span)))
    print(f'{n} complete frames over {nf} fields: {50 * n / nf:.2f} fps; fields a frame '
          f'p50 {pct(span, .5)} p95 {pct(span, .95)} max {max(span)}; histogram {hist}')
    print(f'work a frame (ms, less the vblank wait): mean {sum(work) / n:.2f} p50 '
          f'{pct(work, .5):.2f} p95 {pct(work, .95):.2f} max {max(work):.2f}')
    # The wait loop's instructions can collect gap too (the 040 core does): fit each field's
    # gap to its wait and other instruction counts (DERIVED).
    try:
        import numpy as np
        X = np.array([[f['execs'].get('wait', 0),
                       sum(v for k, v in f['execs'].items() if k != 'wait')] for f in fields], float)
        y = np.array([f['gap'] for f in fields], float)
        c = np.linalg.lstsq(X, y, rcond=None)[0]
        rms = np.sqrt(((X @ c - y) ** 2).mean()) / y.mean()
        wg = max(0.0, c[0]) * sum(X[a:b, 0].sum() for a, b in frames) * ms / n
        print(f'gap fit: {c[0]:.1f} units a wait instruction, {c[1]:.1f} a work one (rms {100 * rms:.1f}%);'
              f' work less the wait\'s gap (DERIVED): mean {sum(work) / n - wg:.2f}')
    except ImportError:
        pass
    worksum = sum(v for k, v in tot.items() if k != 'wait')
    exwork = sum(v for k, v in ex.items() if k != 'wait')
    gap = tot.get('gap', 0)
    print(f"{'category':12} {'ms/frame':>9} {'share':>7}   {'with gap by instructions':>24}")
    for k, v in sorted(tot.items(), key=lambda kv: -kv[1]):
        if k == 'wait':
            print(f'{k:12} {v * ms / n:9.2f}    wait')
            continue
        share = f'{100 * v / worksum:6.1f}%'
        if k == 'gap' or not exwork:
            print(f'{k:12} {v * ms / n:9.2f} {share}')
            continue
        w = v + gap * ex.get(k, 0) / exwork
        print(f'{k:12} {v * ms / n:9.2f} {share}   {w * ms / n:9.2f} {100 * w / worksum:6.1f}%')
    print(f'{"work":12} {worksum * ms / n:9.2f}')
    # hot routines: units by the nearest matched label at or below the offset
    by = {}
    offs = [o for o, _ in lab]
    for k, (units, execs, chip, cat) in d['pcs'].items():
        if cat == 'wait':
            continue
        o = int(k, 16)
        i = bisect.bisect_right(offs, o) - 1
        name = f'{cat:9} {lab[i][1]} ${lab[i][0]:x}' if i >= 0 else f'{cat:9} ${o:x}'
        t = by.setdefault(name, [0, 0])
        t[0] += units
        t[1] += chip
    allpc = sum(v[0] for v in by.values())
    print('hot routines, % of the work PCs (category, nearest source label at or below; chip ='
          ' chip-bus share of its time):')
    for name, (u, c) in sorted(by.items(), key=lambda kv: -kv[1][0])[:20]:
        print(f'  {100 * u / allpc:5.1f}%  chip {100 * c / max(u, 1):3.0f}%  {name}')
    # the slave's own code by the profiled build's labels (BUILD, as ab3d.py aprof's slave_pcs)
    spcs = d.get('slave_pcs')
    lst = os.path.join(GAME, 'tmp/build', m.get('build') or os.environ.get('BUILD', 'release'),
                       'AlienBreed3D.lst')
    if spcs and os.path.exists(lst):
        slab = sorted((int(m.group(1), 16), m.group(2)) for m in
                      (re.match(r'^([0-9A-F]{8}) (\w+)$', l.rstrip()) for l in open(lst, errors='replace'))
                      if m and m.group(2)[0] in '_c')
        soffs = [o for o, _ in slab]
        sby = {}
        for k, (units, execs, chip, cat) in spcs.items():
            i = bisect.bisect_right(soffs, int(k, 16)) - 1
            name = f'{cat:9} {slab[i][1]}' if i >= 0 else f'{cat:9} ${k}'
            sby[name] = sby.get(name, 0) + units
        print('the slave\'s routines, ms a frame (category, nearest label at or below):')
        for name, u in sorted(sby.items(), key=lambda kv: -kv[1])[:12]:
            print(f'  {u * ms / n:8.2f}  {name}')
    print_loops(d)


if __name__ == '__main__':
    main()
