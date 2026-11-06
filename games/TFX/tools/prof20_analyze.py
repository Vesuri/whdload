#!/usr/bin/env python3
"""Attribute a 2,000-field strict 040 profile to exact symbol spans, slave labels and call regions.

  prof20_analyze.py PROFILE_DIR SLAVE_LISTING [OUT.json]

Self costs only (callees charged separately). Game hunk-0 PCs use the 723 accepted
relocation-masked TFX.040 spans; uncovered PCs fall back to the nearest observed call
target. Slave PCs use the listing's symbol table. Costs are emulator scheduler ticks.
"""
import csv, json, re, struct, sys, bisect, collections
from pathlib import Path

p = Path(sys.argv[1]); lst = Path(sys.argv[2]); root = Path(__file__).resolve().parents[1]
rows = list(csv.reader((p / 'profile.csv').open()))
meta = list(map(int, rows[0][1:])); duration = meta[1] - meta[0]; frames = meta[2]
F = ['n', 'fetch', 'body', 'special', 'pad', 'reads', 'writes', 'rb', 'wb', 'chipr', 'chipw', 'chiprb', 'chipwb']
pcs = {int(r[1]): dict(zip(F, map(int, r[2:]))) for r in rows if r[0] == 'pc'}
assert sum(v['fetch'] + v['body'] + v['special'] + v['pad'] for v in pcs.values()) == duration
calls = collections.Counter()
for r in rows:
    if r[0] == 'call': calls[int(r[2])] += int(r[3])
exc = [r for r in rows if r[0] == 'exception']
bases = json.loads((p / 'segments.json').read_text()); base = bases[0]
code = (p / 'entry-hunk0.bin').read_bytes()
text = lst.read_text(encoding='latin1')
ssym = {m[1]: int(m[2], 16) for m in re.finditer(r'^([A-Za-z_.][\w.]*)\s+00:([0-9A-Fa-f]{8})$', text, re.M)}
sb = struct.unpack_from('>I', code, 0x19fe)[0] - ssym['do_swap_screen']
slabels = sorted((a, n) for n, a in ssym.items() if a < 0x10000)
spans = sorted((s['target'], s['size'], s['name']) for s in json.loads((root / 'tmp/step6/exact-symbol-spans.json').read_text()))
starts = [s[0] for s in spans]
targets = sorted(t - base for t in calls if base <= t < base + len(code))
manual = {0x4e53a: 'CPU masked sprite merge', 0x3b93a: 'SuperShape view dispatcher', 0x60bfc: 'polygon bounds/edge prep',
          0x77c8: 'aircraft list update loop', 0x249a: 'RGB palette blend loop', 0x5f252: 'left edge generator',
          0x5f1e0: 'right edge generator', 0x5f124: 'paired edge walker', 0x4bdca: 'integer sqrt', 0x4b774: 'matrix angle helper',
          0x3f51e: 'shape handle lookup', 0x3bc56: 'nested SuperShape dispatcher', 0x3d032: 'SuperShape part eval',
          0x7d90: 'aircraft iterator DBF8', 0x7d54: 'aircraft iterator DB30', 0x39cac: 'viewport scale calc'}

def region(pc):
    o = pc - base
    if 0 <= o < len(code):
        i = bisect.bisect_right(starts, o) - 1
        if i >= 0 and o < spans[i][0] + spans[i][1]: return 'game', spans[i][2], spans[i][0]
        j = bisect.bisect_right(targets, o) - 1
        t = targets[j] if j >= 0 else 0
        return 'game', manual.get(t, f'game:${t:x}'), t
    o = pc - sb
    if 0 <= o < 0x10000:
        i = bisect.bisect_right([a for a, _ in slabels], o) - 1
        return 'slave', 'slave:' + slabels[i][1], slabels[i][0]
    if pc < 0x400: return 'lowpage', f'lowpage:${pc & ~0xf:x}', pc & ~0xf
    if 0xf80000 <= pc < 0x1000000: return 'rom', 'kickstart', 0
    for k, b in enumerate(bases[1:], 1):
        if b <= pc < b + 0x40000: return 'game', f'hunk{k}', 0
    return 'other', f'other:${pc & ~0xfff:x}', 0

agg = collections.defaultdict(lambda: collections.Counter()); hot = []
for pc, v in pcs.items():
    space, name, start = region(pc); c = v['fetch'] + v['body'] + v['special'] + v['pad']
    a = agg[(space, name, start)]
    a['cost'] += c; a['n'] += v['n']; a['chipr'] += v['chipr']; a['chipw'] += v['chipw']; a['pad'] += v['pad']
    a['reads'] += v['reads']; a['writes'] += v['writes']
    hot.append((c, pc, space, name, v))
total = duration
res = []
for (space, name, start), a in sorted(agg.items(), key=lambda kv: -kv[1]['cost']):
    res.append(dict(space=space, name=name, start=hex(start), pct=100 * a['cost'] / total, instr=a['n'],
                    per_frame_instr=a['n'] / frames, chipr=a['chipr'], chipw=a['chipw'], pad_pct=100 * a['pad'] / max(1, a['cost']),
                    cpi=a['cost'] / max(1, a['n']) / meta[3], calls=calls.get(base + start, 0) if space == 'game' else None))
hot.sort(reverse=True)
out = dict(frames=frames, fields=2000, fps=frames / 40, ticks=total, cycles=total / meta[3], cycles_per_frame=total / meta[3] / frames,
           instructions=sum(v['n'] for v in pcs.values()), exceptions=len(exc),
           chip_reads=sum(v['chipr'] for v in pcs.values()), chip_writes=sum(v['chipw'] for v in pcs.values()),
           pad_pct=100 * sum(v['pad'] for v in pcs.values()) / total, regions=res,
           hot_pcs=[dict(pc=hex(pc), off=hex(pc - (base if s == 'game' else sb)), region=n, pct=100 * c / total, n=v['n'],
                         cpi=c / max(1, v['n']) / meta[3], chipr=v['chipr'], chipw=v['chipw']) for c, pc, s, n, v in hot[:120]])
if len(sys.argv) > 3: Path(sys.argv[3]).write_text(json.dumps(out, indent=1))
print(f"frames {frames}  fps {frames/40:.3f}  cycles/frame {out['cycles_per_frame']:.0f}  instr/frame {out['instructions']/frames:.0f}"
      f"  chipW/frame {out['chip_writes']/frames:.0f}  chipR/frame {out['chip_reads']/frames:.0f}  pad {out['pad_pct']:.1f}%  exc {len(exc)}")
cum = 0
for r in res[:60]:
    cum += r['pct']
    print(f"{r['pct']:6.2f}% {cum:6.1f}% {r['space']:6} {r['start']:>8} {r['name'][:34]:34} instr/f {r['per_frame_instr']:8.0f} cpi {r['cpi']:5.2f}"
          f" chipW {r['chipw']:9} chipR {r['chipr']:8} calls {r['calls']}")
