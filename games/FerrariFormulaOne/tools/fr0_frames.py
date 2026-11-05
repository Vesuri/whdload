#!/usr/bin/env python3
"""FR0 per-frame work from a hi25-profile trace (gzip or raw detail.bin).

  fr0_frames.py TRACE_DIR [...]      -> TRACE_DIR/fr0-frames.json

One row per interval between consecutive B8Draw entries, in ms:
  draw_cpu   drawing instructions (incl. Chip/DMA stalls)
  beam       the line-256/field wait loop
  waitblit   WaitBlit loops
  out_busy   main task outside B8Draw except scheduler idle (ticks, poses...)
  idle       scheduler idle (FF1TimeDue/FF1TimeSnapshot/schedule_begin)
  irq        interrupt handlers (inside or outside drawing)
work = draw_cpu + out_busy + irq: what a CPU-only path still has to execute.
Categories follow tools/analyze_hi25_profile.py.
"""
from pathlib import Path
import sys, json, bisect, collections, statistics, struct, gzip, tempfile, os
sys.path.insert(0, str(Path.home() / '.local/share/amiga/pylib'))
from amigaxdev import barto


def blob(p, name):
    f = p / name
    return f.read_bytes() if f.exists() else gzip.open(str(f) + '.gz').read()


def analyze(p):
    r = json.loads((p / 'result.json').read_text()); sy = r['symbols']; probe = int(r['probe'], 16)
    host = int(r['host'], 16); hs = r['host_symbols']
    rows = sorted(json.loads((p / 'addresses.json').read_text()), key=lambda x: x['actual'])
    keys = [x['actual'] for x in rows]

    def canon(pc):
        i = bisect.bisect_right(keys, pc) - 1
        if i >= 0 and pc < rows[i]['actual'] + rows[i]['size']:
            return rows[i]['old'] + pc - rows[i]['actual']
        return pc
    labels = sorted((v, k) for k, v in sy.items()); sk = [v for v, k in labels]

    def owner(pc):
        if probe <= pc < probe + max(sk) + 0x400:
            return labels[bisect.bisect_right(sk, pc - probe) - 1][1]
        return None
    mem = bytearray(blob(p, 'start.bin')); mem += bytes(0x200000 - len(mem)) + blob(p, 'start-fast.bin')
    glues = set(); at = 0x200000
    while True:
        at = mem.find(bytes.fromhex('514f40d7007c0700'), at)
        if at < 0:
            break
        glues.add(at); at += 2
    assert glues
    op = lambda pc: struct.unpack_from('>H', mem, pc)[0] if pc + 2 <= len(mem) else 0
    hw = host + hs['gfx_WaitBlit']; hwe = hw + 0x3a
    entry = probe + sy['B8Draw']; end = probe + sy['B8Frames'] - 2
    beam = {'B8_65728', 'B8_6572e', 'B8_65732'}; idle = {'schedule_begin', 'FF1TimeDue', 'FF1TimeSnapshot'}
    d = p / 'detail.bin'
    tmp = None
    if not d.exists():
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
        with gzip.open(str(d) + '.gz') as z:
            while True:
                b = z.read(1 << 24)
                if not b:
                    break
                tmp.write(b)
        tmp.close(); d = Path(tmp.name)
    trace = barto.load(d)
    heads = [f.cycles for f in trace.fields]; cyc_ms = (1000 / 49.9204102) / statistics.mean(heads)
    frames = []; cur = None; inside = False; depth = 0; pending = 0
    for f in trace.fields:
        for pc, cost, regs in trace.instructions(f):
            if pc == 0x7fffffff:
                pending += cost; continue
            cost += pending; pending = 0
            if pc is None:
                continue
            if pc in glues:
                depth += 1
            if pc == entry and not depth:
                if cur is not None:
                    frames.append(cur)
                cur = collections.Counter(); inside = True
            if depth:
                k = 'irq'
            elif inside:
                o = owner(pc)
                c = canon(pc)
                if hw <= pc < hwe or 0x2a130 <= c < 0x2a140:
                    k = 'waitblit'
                elif o in beam:
                    k = 'beam'
                else:
                    k = 'draw_cpu'
            else:
                k = 'idle' if owner(pc) in idle else 'out_busy'
            if depth and op(pc) == 0x4e73:
                depth -= 1
            if cur is not None:
                cur[k] += cost
            if pc == end and not depth:
                inside = False
    if tmp:
        os.unlink(tmp.name)
    rows = []
    for c in frames:
        x = {k: round(v * cyc_ms, 4) for k, v in c.items()}
        x['total'] = round(sum(c.values()) * cyc_ms, 4)
        x['work'] = round((c['draw_cpu'] + c['out_busy'] + c['irq']) * cyc_ms, 4)
        rows.append(x)
    w = [x['work'] for x in rows]
    out = {'trace': p.name, 'frames': rows, 'n': len(rows),
           'work_mean': statistics.mean(w), 'work_max': max(w), 'work_min': min(w),
           'mean': {k: statistics.mean(x.get(k, 0) for x in rows) for k in
                    ['draw_cpu', 'beam', 'waitblit', 'out_busy', 'idle', 'irq', 'total', 'work']}}
    (p / 'fr0-frames.json').write_text(json.dumps(out, indent=1) + '\n')
    print(p.name, 'n', out['n'], 'work mean %.2f max %.2f' % (out['work_mean'], out['work_max']),
          {k: round(v, 2) for k, v in out['mean'].items()})
    return out


if __name__ == '__main__':
    for a in sys.argv[1:]:
        analyze(Path(a))
