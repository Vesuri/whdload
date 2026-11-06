#!/usr/bin/env python3
"""Step 3c/3d data from a NOFILL cockpit_probe.py run.

  copy_probe_analyze.py PROBE_DIR OPAQUE_MASK.json [OUT.json]

Copy units are 8-byte blocks of one plane row (64 pixels), as in
copy_changed_blocks. Per frame and row band: units that changed since the
same chip buffer's previous frame (two frames back), units written after the panel call (post-panel buffer vs frame
end), and units that a panel-aware skip could prove unchanged without comparing
(entirely inside the opaque panel run and not written after the panel).
"""
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); opaque = json.loads(Path(sys.argv[2]).read_text())
bands = [(0, 97), (97, 146), (146, 200)]
def units(buf): return [buf[o:o + 8] for o in range(0, 64000, 8)]
def band(u): r = (u * 8 % 8000) // 40; return next(i for i, (a, b) in enumerate(bands) if a <= r < b)
def inside(u):
    r = (u * 8 % 8000) // 40; x0 = (u * 8 % 40) * 8
    return all(opaque[r][x] for x in range(x0, x0 + 64))
inside_units = [inside(u) for u in range(8000)]
report = dict(units_per_band=[sum(1 for u in range(8000) if band(u) == i) for i in range(3)],
              opaque_units_per_band=[sum(1 for u in range(8000) if band(u) == i and inside_units[u]) for i in range(3)], frames={})
# Each chip buffer's shadow holds the frame two publications back (double buffering).
f = 2
while (p / f'frame{f}-end.bin').exists() and (p / f'frame{f}-post.bin').exists():
    prev = units((p / f'frame{f - 2}-end.bin').read_bytes()); end = units((p / f'frame{f}-end.bin').read_bytes())
    post = units((p / f'frame{f}-post.bin').read_bytes())
    row = dict(changed=[0, 0, 0], after_panel=[0, 0, 0], provable=[0, 0, 0], provable_but_changed=0)
    for u in range(8000):
        b = band(u); ch = prev[u] != end[u]; ap = post[u] != end[u]
        row['changed'][b] += ch; row['after_panel'][b] += ap
        if inside_units[u] and not ap:
            row['provable'][b] += 1; row['provable_but_changed'] += ch
    report['frames'][f] = row; f += 1
out = Path(sys.argv[3]) if len(sys.argv) > 3 else p / 'copy-analysis.json'
out.write_text(json.dumps(report, indent=1)); print(json.dumps(report, indent=1))
