#!/usr/bin/env python3
"""Summarise --frame-stats captures (phase 11b A1/A3).

Times come from the game's VBL count and the beam line sampled by the slave:
a PAL line is 227 colour clocks of 3546895 Hz over 313 lines per field, an NTSC
line 227.5 of 3579545 Hz over 263 lines. Intervals
include interrupts. A frame is one pass from the loop's draw entry to the next.
A picture is published between the post-conversion wait and the return from
$510; it is displayed from the next field. When those two samples straddle a
field edge the later field is used (ambiguous by at most one field). A later picture published in the
same field replaces it before display ("overwritten").
"""
import argparse
import json
import statistics
import struct
from collections import Counter
from pathlib import Path

NAMES = {1: 'loop', 2: 'world_begin', 3: 'world_end', 4: 'draw', 5: 'predicted', 6: 'scene_drawn',
         7: 'hud_done', 8: 'restored', 9: 'convert_entry', 10: 'limit_begin', 11: 'limit_end',
         12: 'convert_begin', 13: 'convert_end', 14: 'wait_begin', 15: 'wait_end', 16: 'queued'}
# Interval name: (start event, end event)
# Observed order inside $510: native drawing, then the converter call (limiter,
# conversion, display wait) and publication; $46e6 runs after publication.
SPANS = {'prediction_save': (4, 5), 'native_draw': (5, 9), 'converter_setup': (9, 12),
         'limiter_wait': (10, 11), 'conversion': (12, 13), 'display_wait': (14, 15),
         'publish': (15, 6), 'after_publish_46e6': (6, 7), 'restore': (7, 8), 'world_ticks': (2, 3)}
WARMUP_FRAMES = 20


def records(path):
    raw = path.read_bytes()
    magic, hz, count, skip = struct.unpack_from('>4sIII', raw)
    if magic != b'WCFS' or hz not in (50, 60) or len(raw) != 16+4*count:
        raise ValueError(f'{path}: not a frame statistics file')
    lines = 313 if hz == 50 else 263
    records.line_ms = 1000*(227/3546895 if hz == 50 else 227.5/3579545)
    rows = [(w >> 27, (w >> 9) & 0x3ffff, w & 0x1ff) for (w,) in struct.iter_unpack('>I', raw[16:])]
    if any(r[0] not in NAMES for r in rows):
        raise ValueError(f'{path}: unknown event id')
    ev, corrected = [], 0
    for e, f, v in rows:
        # Early in a field the beam can wrap before the game's VBL handler
        # increments its count; such a sample belongs to the next field.
        if ev and f*lines+v < ev[-1][2] and v < 20:
            f += 1
            corrected += 1
        ev.append((e, f, f*lines+v))
    if any(b[2] < a[2] for a, b in zip(ev, ev[1:])):
        raise ValueError(f'{path}: timestamps go backwards')
    records.corrected = corrected
    return hz, lines, ev


def pct(values, q):
    values = sorted(values)
    return values[min(len(values)-1, int(round(q*(len(values)-1))))]


def dist(values):
    return dict(mean=round(statistics.fmean(values), 3), p50=round(pct(values, .5), 3),
                p95=round(pct(values, .95), 3), max=round(max(values), 3))


SETTINGS = ('cpu_model', 'mmu_model', 'cpu_speed', 'cpu_cycle_exact', 'cpu_memory_cycle_exact',
            'blitter_cycle_exact', 'cpu_data_cache', 'finegrain_cpu_speed', 'cpu_multiplier', 'cpu_frequency')


def settings(run):
    found = {}
    for path in run.glob('run/fsuae/Cache/Logs/debug.uae'):
        for line in path.read_text(errors='replace').splitlines():
            key, _, value = line.partition('=')
            if key in SETTINGS:
                found[key] = value
    return found


def display_records(path):
    raw=path.read_bytes()
    magic,hz,count,size=struct.unpack_from('>4sIII',raw)
    if magic!=b'WCDS' or hz not in (50,60) or size!=16 or len(raw)!=16+16*count:
        raise ValueError('invalid display ledger')
    rows=list(struct.iter_unpack('>IHHII',raw[16:]))
    if count<100 or any(not 4<=v<=16 or index>1 or not plane or not copper for f,v,index,plane,copper in rows):
        raise ValueError('invalid/late copper handoff')
    if any(b[0]<=a[0] or b[2]==a[2] or b[3]==a[3] for a,b in zip(rows,rows[1:])):
        raise ValueError('display ownership/order violated')
    return rows


def summarise(run):
    meta = json.loads((run/'result.json').read_text())
    hz, lines, ev = records(run/'framestats.bin')
    ms = records.line_ms
    draws = [i for i, e in enumerate(ev) if e[0] == 4]
    buffered=meta['fixture'].get('buffered',False)
    spans=dict(SPANS)
    if buffered:spans['publish']=(16,6)
    frames = []
    for a, b in zip(draws, draws[1:]):
        seg = ev[a:b+1]
        part = Counter()
        opened = {}
        for e, f, t in seg[:-1]:
            for name, (s0, s1) in spans.items():
                if e == s0:
                    opened[name] = t
                elif e == s1 and name in opened:
                    part[name] += t-opened.pop(name)
        shown = [f+1 for (e0, _, _), (e, f, t) in zip(seg[:-1], seg[1:-1]) if e0 == 15 and e == 6]
        frames.append(dict(ms=(seg[-1][2]-seg[0][2])*ms, worlds=sum(e == 3 for e, _, _ in seg[:-1]),
                           parts={k: v*ms for k, v in part.items()}, shown=shown[-1] if shown else None,
                           converted=any(e == 12 for e, _, _ in seg)))
    frames = frames[WARMUP_FRAMES:]
    if len(frames) < 100:
        raise ValueError(f'{run}: fewer than 100 measured frames')
    published = [f['shown'] for f in frames if f['shown'] is not None]
    if buffered:
        ledger=display_records(run/'displaystats.bin')
        first_time=ev[draws[WARMUP_FRAMES]][2]
        last_time=ev[draws[-1]][2]
        published=[f for f,v,index,plane,copper in ledger if first_time<=f*lines+v<last_time]
    shown = sorted(set(published))
    overwritten = len(published)-len(shown)
    intervals = [b-a for a, b in zip(shown, shown[1:])]
    seconds = sum(f['ms'] for f in frames)/1000
    get = lambda f, k: f['parts'].get(k, 0.0)
    rows = {k: dist([get(f, k) for f in frames]) for k in SPANS}
    # converter_setup spans the limiter; report setup without it.
    rows['converter_setup'] = dist([get(f, 'converter_setup')-get(f, 'limiter_wait')-(get(f,'display_wait') if buffered else 0) for f in frames])
    accounted = ('prediction_save', 'native_draw', 'converter_setup', 'conversion', 'display_wait',
                 'publish', 'after_publish_46e6', 'restore', 'world_ticks')
    rows['input_player_other'] = dist([f['ms']-sum(get(f, k) for k in accounted)+(get(f,'display_wait') if buffered else 0) for f in frames])
    busy = [f['ms']-get(f, 'limiter_wait')-get(f, 'display_wait') for f in frames]
    return dict(run=run.name, machine=meta['machine'], timing_core=meta['timing_core'], custom5=meta['custom5'],
        options=meta['options'], held_key=meta['held_key'], cpu_speed=meta.get('cpu_speed'),
        live_cpu=meta.get('live_cpu'), emulator_settings=settings(run), field_hz=hz,
        early_line_corrections=records.corrected, frames=len(frames), seconds=round(seconds, 3), pictures_per_second=round((len(shown)-1)/((shown[-1]-shown[0])*lines*ms/1000), 3),
        pictures_published=len(published), pictures_overwritten=overwritten,
        fields_per_picture=dict(sorted(Counter(intervals).items())),
        frames_with_delta_conversion=sum(f['converted'] for f in frames),
        world_updates_per_second=round(sum(f['worlds'] for f in frames)/seconds, 3),
        world_ticks_per_frame=dict(sorted(Counter(f['worlds'] for f in frames).items())),
        frame_ms=dist([f['ms'] for f in frames]), busy_ms_excluding_waits=dist(busy), parts_ms=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    rows = [summarise(r) for r in a.runs]
    for r in rows:
        print(f"{r['run']}: {r['pictures_per_second']:.2f} pictures/s, fields/picture {r['fields_per_picture']}, "
              f"world {r['world_updates_per_second']:.2f}/s, frame p50 {r['frame_ms']['p50']:.1f} ms, "
              f"busy p50 {r['busy_ms_excluding_waits']['p50']:.1f} ms")
        print('   '+', '.join(f"{k} {v['mean']:.1f}" for k, v in r['parts_ms'].items() if True))
    if a.output:
        a.output.write_text(json.dumps(dict(runs=rows, scope='slave-recorded VBL/beam time in the named emulator configuration; not physical hardware'), indent=2)+'\n')


if __name__ == '__main__':
    main()
