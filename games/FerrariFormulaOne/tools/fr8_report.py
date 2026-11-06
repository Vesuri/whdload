#!/usr/bin/env python3
"""FR8 pacing report (FASTRAM_PLAN.md FR8) from a test_h5_fps.py run of a pacing build.

  fr8_report.py RUN_DIR [RUN_DIR...]   e.g. tmp/step5/c4-q03-h5-fps-030-50-bce-fr8-pace

Reads RUN_DIR/result.json, fr8-log.bin (src/FastRenderPacing.s) and the census-*.jsonl
windows, writes RUN_DIR/fr8-report.json and prints a summary:

- per frame, in ms: logic (last tick begin to road preparation, which includes the LoadView
  request), draw (preparation to draw end), wait (the field wait before the copy), copy,
  and idle (copy end to the next tick begin: the wait for a due tick), split by frames
  whose ticks include the native 100 ms pulse (opponent update) and frames without;
- ticks per frame and the displayed intervals (census) as histograms;
- the census alignment: each frame's bank must appear on screen in the field after the
  next frame's preparation (its LoadView request); the share that does;
- tearing: a copy into a bank in a field where the census shows that bank on screen,
  unless the copy started at or after line 256 of that field (past the display);
- smoothness: the fields from a frame's last tick to its first field on screen, and the
  ticks between consecutive frames against the fields between their first showings.
Times read from the field counter and the beam line; a field is 20.032 ms, a line 64 us.
"""
from pathlib import Path
import collections, json, statistics, struct, sys

FIELD_MS = 71051 / 3546895 * 1000
LINES = 312.5
LINE_MS = FIELD_MS / LINES
ENTRIES = 1024
EVENTS = ['begin', 'prep', 'drawn', 'copy', 'done']
SAFE_LINE = 256


def decode(run):
    res = json.loads((run / 'result.json').read_text())
    raw = (run / 'fr8-log.bin').read_bytes()
    count = res['fr8_count']
    size = res.get('fr8_entry', 32)
    frames = []
    full = None
    for n in range(max(0, count - ENTRIES), count):
        e = raw[(n % ENTRIES) * size:(n % ENTRIES + 1) * size]
        ticks, pulses, bank = struct.unpack_from('>IHH', e, 0)
        f = dict(n=n, ticks=ticks, pulses=pulses, bank=bank, written=struct.unpack_from('>I', e, 28)[0])
        if size >= 44:
            # The copy field's VBL service and the last LoadView request (field low words).
            f['vbl'] = struct.unpack_from('>HH', e, 32)
            f['req'] = struct.unpack_from('>HH', e, 36)
            f['req_kind'], f['req_bank'] = struct.unpack_from('>HH', e, 40)
        for i, name in enumerate(EVENTS):
            field, vpos = struct.unpack_from('>HH', e, 8 + 4 * i)
            if full is None:
                # The high bits from the first census window's start.
                base = res['census_game_fields'][0][0]
                full = (base & ~0xffff) | field
                if full > base + 0x8000:
                    full -= 0x10000
            full += (field - full) & 0xffff
            f[name] = (full, vpos)
        frames.append(f)
    return res, frames


def ms(ev):
    return ev[0] * FIELD_MS + ev[1] * LINE_MS


def census(run, res):
    """Game field -> displayed bank (low word) for each census window, at offset delta."""
    out = []
    for before, after, offset in res.get('census_game_fields', []):
        path = run / f'census-{offset}.jsonl'
        if not path.exists():
            continue
        rows = [json.loads(x) for x in path.read_text().splitlines()][1:]
        out.append((before, [(r['planes'][0] - 4) & 0xffff for r in rows]))
    return out


def align(frames, windows):
    """The census offset that best matches 'bank shown from the field after the next
    preparation'; returns (delta, matched, total, displayed(field) function)."""
    best = None
    for delta in range(-4, 8):
        shown = {}
        for before, banks in windows:
            for j, b in enumerate(banks):
                shown[before + j + delta] = b
        ok = total = 0
        for a, b in zip(frames, frames[1:]):
            g = b['prep'][0] + 1
            if g in shown and g - 1 in shown:
                total += 1
                ok += shown[g] == a['bank'] and shown[g - 1] != a['bank']
        if total and (best is None or ok > best[1]):
            best = (delta, ok, total, shown)
    return best


def summary(xs):
    if not xs:
        return None
    xs = sorted(xs)
    return dict(n=len(xs), mean=round(statistics.mean(xs), 2), p50=round(xs[len(xs) // 2], 2),
                p95=round(xs[min(len(xs) - 1, int(len(xs) * .95))], 2), max=round(xs[-1], 2))


def report(run):
    res, frames = decode(run)
    rows = []
    for a, b in zip(frames, frames[1:]):
        rows.append(dict(ticks=b['ticks'] - a['ticks'], pulse=b['pulses'] > 0,
                         logic=ms(b['prep']) - ms(b['begin']), draw=ms(b['drawn']) - ms(b['prep']),
                         wait=ms(b['copy']) - ms(b['drawn']), copy=ms(b['done']) - ms(b['copy']),
                         idle=ms(b['begin']) - ms(a['done']), written=b['written'] - a['written'],
                         copy_field=b['copy'][0], copy_line=b['copy'][1], done_field=b['done'][0],
                         bank=b['bank'], waited=b['copy'] != b['drawn']))
    out = dict(run=str(run), slave_sha256=res.get('slave_sha256'), fps=res.get('fps'), frames=len(rows),
               displayed_intervals=dict(sorted(collections.Counter(res.get('interval_fields', [])).items())),
               ticks_per_frame=dict(sorted(collections.Counter(r['ticks'] for r in rows).items())))
    for kind, sel in [('all', lambda r: True), ('pulse', lambda r: r['pulse']), ('plain', lambda r: not r['pulse'])]:
        part = [r for r in rows if sel(r) and r['ticks'] == 1]
        out[kind] = {k: summary([r[k] for r in part]) for k in ['logic', 'draw', 'wait', 'copy', 'idle']}
        out[kind]['busy'] = summary([r['logic'] + r['draw'] + r['copy'] for r in part])
        out[kind]['written_longs'] = summary([r['written'] for r in part])
    out['copy_start_line'] = summary([r['copy_line'] for r in rows])
    out['copies_crossing_vbl'] = sum(r['done_field'] != r['copy_field'] for r in rows)
    out['frames_waiting'] = sum(r['waited'] for r in rows)
    windows = census(run, res)
    a = align(frames, windows) if windows else None
    if a:
        delta, ok, total, shown = a
        out['census'] = dict(delta=delta, matched=ok, checked=total)
        tears, checked = [], 0
        for f in frames:
            (fc, lc), (fd, _) = f['copy'], f['done']
            for g in range(fc, fd + 1):
                if g not in shown:
                    continue
                checked += 1
                if shown[g] == f['bank'] and not (g == fc and lc >= SAFE_LINE):
                    tears.append(dict(frame=f['n'], field=g, copy=f['copy'], done=f['done'], bank=hex(f['bank'])))
        out['tearing'] = dict(fields_checked=checked, violations=len(tears), first=tears[:5])
        # Smoothness: the field a frame first shows in against the field its last tick
        # began in (latency), and the ticks between frames against their fields on screen.
        # The first field on screen: after the copy, at the latest the field after the
        # next frame's preparation (the native request); earlier with FF1FastRenderEarly.
        shows = []
        for a, b in zip(frames, frames[1:]):
            g = next((g for g in range(a['done'][0] + 1, b['prep'][0] + 2)
                      if shown.get(g) == a['bank'] and shown.get(g - 1) != a['bank']), None)
            if g is not None:
                shows.append((a, g))
        out['shown_early'] = sum(1 for a, g in shows if g == a['done'][0] + 1)
        out['shown'] = len(shows)
        out['latency_fields'] = dict(sorted(collections.Counter(g - a['begin'][0] for a, g in shows).items()))
        pairs = collections.Counter((b['ticks'] - a['ticks'], h - g) for (a, g), (b, h) in zip(shows, shows[1:]))
        out['ticks_vs_fields'] = {f'{t} ticks/{f} fields': n for (t, f), n in sorted(pairs.items())}
        out['ticks_match_fields'] = sum(n for (t, f), n in pairs.items() if t == f) / max(1, sum(pairs.values()))
    (run / 'fr8-report.json').write_text(json.dumps(out, indent=1) + '\n')
    return out


if __name__ == '__main__':
    for d in sys.argv[1:]:
        o = report(Path(d))
        print(Path(d).name, 'fps', o['fps'] and round(o['fps'], 2), 'frames', o['frames'])
        print(' displayed intervals', o['displayed_intervals'], 'ticks/frame', o['ticks_per_frame'])
        for kind in ['plain', 'pulse']:
            print(f' {kind:5}', {k: (v and (v['mean'], v['p95'], v['max'])) for k, v in o[kind].items()})
        print(' copy start line', o['copy_start_line'], 'copies crossing VBL', o['copies_crossing_vbl'],
              'frames waiting', o['frames_waiting'])
        print(' census', o.get('census'), 'tearing', o.get('tearing'))
        print(' latency (fields from tick begin to display)', o.get('latency_fields'),
              'shown', o.get('shown'), 'in the field after the copy', o.get('shown_early'))
        print(' ticks vs fields on screen', o.get('ticks_vs_fields'), 'match', o.get('ticks_match_fields'))
