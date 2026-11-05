#!/usr/bin/env python3
"""FR0 benchmark trace analysis: per-call cost of every FR0* routine.

  fr0_bench_analyze.py TRACE_DIR     -> TRACE_DIR/fr0-bench.json

Cost is charged to the FR0 label owning each instruction (nearest preceding
fine symbol), including memory/DMA stalls and excluding interrupts (other
owners). A call starts when the routine's entry PC executes; its start line is
the PAL beam line. 040/060 gap records are charged to the next instruction.
"""
from pathlib import Path
import sys, json, bisect, collections, statistics
sys.path.insert(0, str(Path.home() / '.local/share/amiga/pylib'))
from amigaxdev import barto

p = Path(sys.argv[1]); r = json.loads((p / 'result.json').read_text())
sy = r['symbols']; probe = int(r['probe'], 16)
labels = sorted((v, k) for k, v in sy.items()); sk = [v for v, k in labels]


def owner(pc):
    if pc is None or not probe <= pc < probe + max(sk) + 0x400:
        return None
    return labels[bisect.bisect_right(sk, pc - probe) - 1][1]


entries = {probe + v: k for k, v in sy.items() if k.startswith('FR0')}
trace = barto.load(p / 'detail.bin')
heads = [f.cycles for f in trace.fields]; field_ms = 1000 / 49.9204102; cyc_ms = field_ms / statistics.mean(heads)
calls = collections.defaultdict(list); cur = {}; pending = 0
for f in trace.fields:
    run = 0
    for pc, cost, regs in trace.instructions(f):
        if pc == 0x7fffffff:
            pending += cost; continue
        cost += pending; pending = 0
        if pc in entries:
            name = entries[pc]
            cur[name] = {'line': round(313 * run / f.cycles), 'field': f.index, 'cycles': 0}
            calls[name].append(cur[name])
        o = owner(pc)
        if o in cur:
            cur[o]['cycles'] += cost
        run += cost
COPY = {'FR0CopyMoveL': 30720, 'FR0CopyMovem': 30720, 'FR0CopyMove16': 30720, 'FR0CopyVisible': 24000,
        'FR0ReadChip': 30720}
out = {'trace': p.name, 'cpu_mhz': 1 / cyc_ms / 1000, 'routines': {}}
for name, xs in sorted(calls.items()):
    # Drop a call cut by the trace window end (its last instruction is missing).
    ms = [x['cycles'] * cyc_ms for x in xs]
    row = {'calls': len(xs), 'ms': [round(v, 4) for v in ms], 'lines': [x['line'] for x in xs],
           'median_ms': round(statistics.median(ms), 4) if ms else None}
    if name in COPY and ms:
        row['bytes'] = COPY[name]
        row['ms_per_30960'] = round(statistics.median(ms) * 30960 / COPY[name], 4) if name != 'FR0CopyVisible' else None
    out['routines'][name] = row
(p / 'fr0-bench.json').write_text(json.dumps(out, indent=1) + '\n')
for k, v in out['routines'].items():
    print(f"{k:16} calls={v['calls']:3} median={v['median_ms']} ms lines={v['lines'][:8]}")
