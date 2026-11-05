#!/usr/bin/env python3
"""FR0e budget from the FR0 matrix (tools/fr0_run.py) -> manifest/fr0-budget.json.

Per CPU and scene:
  today    fps of today's slave (same session)
  floor    no-draw fps and per-frame work (FR0a)
  logic    per-frame work with immediate blits: all drawing logic with blits
           free and exact pixels (FR0b; includes today's CPU writes to Chip)
  copy     Fast->Chip copy of one bank (FR0c, bench trace median)
  kernels  CPU replacement for the blits (FR0d unit costs x per-frame counts)
Estimated Fast path frame i: w_i = logic_i + kernels + copy, shown after
ceil(w_i / field) fields (at least one). This assumes the copy is the only
Chip write and no other work is added; it is an estimate, not a measurement.

Blit counts per frame: the grid blit census in RENDERING_PLAN.md (per field,
measured at 2.5 fields per frame) x 2.5: 2 exclusive road fills (24 x 103),
123 lines (~6,273 one-dot rows), 92 one-row BCD spans (24 words x 3 planes as
one unit per 3), 9 D-only fills (taken as two full three-plane clears),
33 ABCD cookie-cuts (one cockpit + 10 car-equivalents of 3 planes) and
25 ABD masks (one plane of a car each). Car work scales per scene with the
measured blitter DMA slots per frame above the solo scene (no cars).
"""
import json, math, statistics, sys
from pathlib import Path

r = Path(__file__).resolve().parents[1]
S = r / 'tmp/step5'
FIELD = 1000 / 49.9204102
PROFILES = ['040-40-bce', '030-50-bce', 'a1200-fast']
SCENES = ['normal', 'solo', 'grid', 'dense']


def fps(p, mode, s):
    f = S / f'c4-q03-h5-fps-{p}-fr0-{mode}-{s}/result.json'
    if not f.exists():
        return None
    x = json.loads(f.read_text())
    if x.get('status') != 'passed':
        return {'status': x.get('status')}
    h = {}
    for v in x['interval_fields']:
        h[str(v)] = h.get(str(v), 0) + 1
    return {'fps': round(x['fps'], 3), 'mean_ms': round(x['mean_ms'], 3), 'histogram': h, 'path': str(f.parent.relative_to(r))}


def frames(p, mode, s):
    f = S / f'hi25-profile-{p}-fr0-{mode}-{s}/fr0-frames.json'
    return json.loads(f.read_text()) if f.exists() else None


def blit_slots_per_frame(s):
    f = S / f'hi25-profile-040-40-bce-fr0-base-{s}/hi25-analysis.json'
    if not f.exists():
        return None
    a = json.loads(f.read_text())
    per_field = a['dma_slots_per_field'].get('blitter', 0)
    fr = frames('040-40-bce', 'base', s)
    fields_per_frame = a['fields'] / fr['n'] if fr else None
    return per_field * fields_per_frame if fields_per_frame else None


def bench(p):
    f = S / f'hi25-profile-{p}-fr0-bench-normal/fr0-bench.json'
    if not f.exists():
        return None
    b = json.loads(f.read_text())['routines']
    if 'FR0Cookie' not in b:
        return None
    med = lambda k: b[k]['median_ms'] if k in b and b[k]['calls'] else None
    cookie = b['FR0Cookie']['ms']
    car = statistics.median(cookie[0::2]); cockpit = statistics.median(cookie[1::2])
    copies = {k: med(k) for k in ['FR0CopyMoveL', 'FR0CopyMovem', 'FR0CopyMove16', 'FR0CopyVisible', 'FR0ReadChip']}
    full = [v for k, v in copies.items() if v and k in ('FR0CopyMoveL', 'FR0CopyMovem', 'FR0CopyMove16')]
    # move16 is skipped (near-zero) below the 040; ignore implausible values.
    full = [v for v in full if v > 0.5]
    u = {'fill_24x103': med('FR0KFill'), 'lines_5150_dots': med('FR0KLines'), 'spans_37': med('FR0KSpans'),
         'background_6': med('FR0KBackground'), 'car_6x40x3': car, 'cockpit_13x57x3': cockpit}
    k_static = (2 * u['fill_24x103'] + u['lines_5150_dots'] * 6273 / 5150 + u['spans_37'] * (92 / 3) / 37
                + 2 * u['background_6'] + u['cockpit_13x57x3'])
    k_car = 10 * car + 25 * car / 3
    return {'units_ms': u, 'copies_ms': copies, 'copy_bank_ms': min(full) * 30960 / 30720,
            'copy_visible_ms': copies['FR0CopyVisible'], 'read_bank_ms': copies['FR0ReadChip'] * 30960 / 30720,
            'kernels_static_ms': k_static, 'kernels_cars_grid_ms': k_car,
            'early_vs_late': {k: {'lines': b[k]['lines'], 'ms': b[k]['ms']} for k in copies if k in b}}


def main():
    slots = {s: blit_slots_per_frame(s) for s in SCENES}
    out = {'date': '2026-11-02', 'field_ms': FIELD, 'method': __doc__.strip(), 'blitter_slots_per_frame_040': slots,
           'profiles': {}}
    for p in PROFILES:
        bp = bench(p); rows = {}
        for s in SCENES:
            row = {'today': fps(p, 'base', s), 'imm_fps': fps(p, 'imm', s), 'floor_fps': fps(p, 'nodraw', s)}
            fl = frames(p, 'nodraw', s); lg = frames(p, 'imm', s)
            if fl:
                row['floor_work_ms'] = {'mean': round(fl['work_mean'], 3), 'max': round(fl['work_max'], 3)}
            if lg:
                row['logic_work_ms'] = {'mean': round(lg['work_mean'], 3), 'max': round(lg['work_max'], 3),
                                        'draw_cpu': round(lg['mean']['draw_cpu'], 3),
                                        'out_busy': round(lg['mean']['out_busy'], 3), 'irq': round(lg['mean']['irq'], 3)}
            if bp and lg and None not in (slots.get(s), slots.get('solo'), slots.get('grid')):
                scale = max(0.0, (slots[s] - slots['solo']) / (slots['grid'] - slots['solo']))
                kern = bp['kernels_static_ms'] + bp['kernels_cars_grid_ms'] * scale
                add = kern + bp['copy_bank_ms']
                est = [max(1, math.ceil((x['work'] + add) / FIELD)) for x in lg['frames']]
                est_fps = 49.9204102 * len(est) / sum(est)
                h = {}
                for v in est:
                    h[str(v)] = h.get(str(v), 0) + 1
                row['estimate'] = {'car_scale': round(scale, 3), 'kernels_ms': round(kern, 3),
                                   'copy_ms': round(bp['copy_bank_ms'], 3),
                                   'work_mean_ms': round(lg['work_mean'] + add, 3),
                                   'work_max_ms': round(lg['work_max'] + add, 3), 'fps': round(est_fps, 2),
                                   'histogram': h}
                # Time left for all blit replacements so that a frame fits one field,
                # with the visible-only copy (FR1 to confirm 40 of 48 bytes per row).
                row['estimate']['kernel_target_ms'] = {
                    'mean_frame': round(FIELD - lg['work_mean'] - bp['copy_visible_ms'], 3),
                    'worst_frame': round(FIELD - lg['work_max'] - bp['copy_visible_ms'], 3)}
                room = FIELD - lg['work_mean'] - bp['copy_visible_ms']
                row['estimate']['kernel_speedup_needed'] = round(kern / room, 2) if room > 0 else None  # None: logic+copy alone exceed a field
                t = row['today'] or {}
                if 'fps' in t:
                    row['estimate']['gain'] = round(est_fps / t['fps'], 3)
            rows[s] = row
        gains = [rows[s]['estimate'].get('gain') for s in SCENES if 'estimate' in rows[s]]
        verdict = None
        if gains and None not in gains:
            verdict = 'plausible gain' if max(gains) > 1.05 else 'no plausible gain'
        out['profiles'][p] = {'bench': bp, 'scenes': rows, 'gains': gains, 'verdict': verdict}
    (r / 'tmp/manifest/fr0-budget.json').write_text(json.dumps(out, indent=1) + '\n')
    for p, v in out['profiles'].items():
        print('==', p, v['verdict'])
        for s, row in v['scenes'].items():
            e = row.get('estimate', {})
            print(f"  {s:7} today {row['today'] and row['today'].get('fps')}  imm {row['imm_fps'] and row['imm_fps'].get('fps')}"
                  f"  floor {row['floor_fps'] and row['floor_fps'].get('fps')}  logic {row.get('logic_work_ms')}  "
                  f"est {e.get('work_mean_ms')} ms -> {e.get('fps')} fps (x{e.get('gain')}) kern {e.get('kernels_ms')} target {e.get('kernel_target_ms')} need x{e.get('kernel_speedup_needed')}")


if __name__ == '__main__':
    main()
