#!/usr/bin/env python3
"""Rank a cpu_profile.py profile by region on any CPU (no 040 cycle-accounting checks).

  cpu_profile_report.py PROFILE_DIR SLAVE_LISTING [N]

Cost = fetch+body+special+pad per PC as the observer recorded it; shares are of the sum
over all PCs. Slave PCs take the listing's nearest symbol; game hunk-0 PCs take the
nearest preceding observed call target (game:$offset); others are grouped per 64 KB.
"""
import csv, json, re, sys, bisect, collections
from pathlib import Path
p = Path(sys.argv[1]); lst = Path(sys.argv[2]).read_text(encoding='latin1'); N = int(sys.argv[3]) if len(sys.argv) > 3 else 30
rows = list(csv.reader((p / 'profile.csv').open())); frames = json.loads((p / 'counts.json').read_text())['publications']
F = ['n', 'fetch', 'body', 'special', 'pad', 'reads', 'writes', 'rb', 'wb', 'chipr', 'chipw', 'chiprb', 'chipwb']
pcs = {int(r[1]): dict(zip(F, map(int, r[2:]))) for r in rows if r[0] == 'pc'}
targets = sorted({int(r[2]) for r in rows if r[0] == 'call'})
bases = json.loads((p / 'segments.json').read_text()); base = bases[0]
size0 = len((p / 'entry-hunk0.bin').read_bytes())
v = json.loads((p / 'launch.json').read_text())['variant']; ent = (p / 'entry-hunk0.bin').read_bytes()
sb = int.from_bytes(ent[v['swap'] + 2:v['swap'] + 6], 'big') - int(re.search(r'^do_swap_screen\s+00:([0-9A-Fa-f]+)', lst, re.M)[1], 16)
syms = sorted((int(a, 16), n) for n, a in re.findall(r'^([A-Za-z_@][\w@]*)\s+00:([0-9A-Fa-f]+)', lst, re.M))
sa = [a for a, _ in syms]
def region(pc):
    if base <= pc < base + size0:
        i = bisect.bisect_right(targets, pc) - 1
        t = targets[i] if i >= 0 and targets[i] >= base else base
        return f'game:${t - base:x}'
    if sb is not None and sb <= pc < sb + 0x20000:
        i = bisect.bisect_right(sa, pc - sb) - 1
        return 'slave:' + (syms[i][1] if i >= 0 else '?')
    return f'other:${pc >> 16 << 16:x}'
agg = collections.defaultdict(lambda: [0, 0, 0])
for pc, v in pcs.items():
    c = v['fetch'] + v['body'] + v['special'] + v['pad']; r = agg[region(pc)]; r[0] += c; r[1] += v['n']; r[2] += v['chipw']
tot = sum(r[0] for r in agg.values())
print(f'frames {frames}  cost/frame {tot / frames:,.0f}  instr/frame {sum(r[1] for r in agg.values()) / frames:,.0f}')
for name, (c, n, w) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:N]:
    print(f'{100 * c / tot:6.2f}%  instr/f {n / frames:9,.0f}  chipW/f {w / frames:8,.0f}  {name}')
