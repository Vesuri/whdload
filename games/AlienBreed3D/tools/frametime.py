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
- the routines with the most time.
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


def main():
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
    # the slave's own code by the release build's labels (ab3d.py aprof's slave_pcs)
    spcs = d.get('slave_pcs')
    lst = os.path.join(GAME, 'tmp/build/release/AlienBreed3D.lst')
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


if __name__ == '__main__':
    main()
