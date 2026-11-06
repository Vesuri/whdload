#!/usr/bin/env python3
"""Annotated disassembly of a profiled address range.

  prof20_annotate.py PROFILE_DIR (game|slave|abs) START END [MIN_PCT]

START/END are hunk-0 offsets for game, slave offsets (listing addresses) for slave.
Columns: % of window, executions per published frame, logical chip writes.
"""
import csv, json, struct, sys, re, os
from pathlib import Path
sys.path.insert(0, os.environ.get('AMIGA_PYLIB', os.path.expanduser('~/.local/share/amiga/pylib')))
from amigaxdev.disasm import records

p = Path(sys.argv[1]); space = sys.argv[2]; s, e = int(sys.argv[3], 0), int(sys.argv[4], 0)
minp = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
rows = list(csv.reader((p / 'profile.csv').open())); meta = list(map(int, rows[0][1:]))
total = meta[1] - meta[0]; frames = meta[2]
pcs = {int(r[1]): list(map(int, r[2:])) for r in rows if r[0] == 'pc'}
base = json.loads((p / 'segments.json').read_text())[0]
if space == 'game': hb = base
elif space == 'slave':
    lst = Path(os.environ.get('LISTING', Path(__file__).resolve().parents[1] / 'tmp/opt20/delta-eight-verified.lst')).read_text(encoding='latin1')
    swap = int(re.search(r'^do_swap_screen\s+00:([0-9A-Fa-f]{8})$', lst, re.M)[1], 16)
    hb = struct.unpack_from('>I', (p / 'entry-hunk0.bin').read_bytes(), 0x19fe)[0] - swap
else: hb = 0
dump = p / 'fast.bin'
acc = 0
for off, raw, text in records(str(dump), 0x40000000, hb, s, e, '68040'):
    v = pcs.get(hb + off)
    pct = 100 * sum(v[1:5]) / total if v else 0.0
    acc += pct
    if v is None and minp > 0: continue
    if pct < minp: continue
    n = v[0] / frames if v else 0
    cw = v[10] if v else 0
    print(f"{off:06x} {pct:6.3f}% {n:9.1f}/f {cw:8} {raw:22} {text}")
print(f"range total {acc:.3f}%")
