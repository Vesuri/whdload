#!/usr/bin/env python3
"""Check per-tick motion smoothness in a fixed_window.py --motion-ticks capture.

The trace records the player and every active actor at s60_recenter entry, after the
tick's movement and collisions and before the world shift. World positions are rebuilt
by adding back the player displacements already subtracted (type 7 is not recentred);
X/Z differences are taken modulo 65536, the recenter's wrap. Rotations are 16-bit.

Per object (pointer, while its type stays the same and it is present every tick):
  outlier  one tick's position or rotation is off the path that both the two ticks
           before and the two after predict: a hitch, or a stall followed by catch-up.
           When the object's own speed or turn rate changes there, it is counted as
           explained (input or AI alternating the rate).
  burst    one step unlike both neighbouring steps, which agree, without a change of the
           object's own speed or turn rate (those are counted as explained): motion that lands only
           on some ticks between still ones.
  step     the step changes and stays changed. Speed, turn-rate or AI changes do this;
           it is counted by whether the object's speed or turn rate changed with it, or
           only its height rate (not traced; flight AI). The rest are listed as
           unexplained: sudden position or rotation changes to review.
  idle     a zero position step while the object's speed is 64 or more (slower speeds
           move less than a unit per tick and carry remainders).
Presented ticks must not decrease within a session; repeats (scripted sequences such as
a level exit present again without running ticks) are counted.

Usage: tools/motion_check.py CAPTURE [--json OUT] [--show N]
"""
import argparse
import collections
import json
import math
from pathlib import Path

FIELDS = ('ptr', 'type', 'x', 'z', 'y', 'pitch', 'bank', 'yaw', 'speed', 'vpitch', 'vbank', 'vyaw', 'health', 'flags',
          'radius', 'owner')


def load(folder):
    ticks, renders = [], []
    for line in (Path(folder)/'motion.txt').read_text().splitlines():
        kind, *rest = line.split()
        if kind == 'T':
            tick, session, level, field, player, px, pz = rest
            ticks.append(dict(tick=int(tick), session=int(session), level=int(level), field=int(field),
                              px=int(px), pz=int(pz), player=None, actors=[]))
        elif kind in ('P', 'A'):
            values = [int(rest[0], 16)]+[int(v) for v in rest[1:15]]+[int(v, 16) for v in rest[15:16]]
            record = dict(zip(FIELDS, values))
            if kind == 'P':
                ticks[-1]['player'] = record
            else:
                ticks[-1]['actors'].append(record)
        elif kind == 'R':
            renders.append(dict(tick=int(rest[0]), field=int(rest[1])))
    return ticks, renders


def wrap(value, bits=16):
    half = 1 << (bits-1)
    return ((value+half) & ((1 << bits)-1))-half


def tracks(ticks):
    """Per object: a list of samples with world positions, split when it disappears, changes type
    or its slot is reused (new owner, lifetime or health increased)."""
    origin_x = origin_z = 0
    live, done = {}, []
    for t in ticks:
        seen = set()
        objects = [('player', t['player'])] if t['player'] else []
        objects += [(a['ptr'], a) for a in t['actors']]
        for key, a in objects:
            shift = (0, 0) if a['type'] == 7 else (origin_x, origin_z)
            if key == 'player':
                x, z = t['px']+origin_x, t['pz']+origin_z
            else:
                x, z = a['x']+shift[0], a['z']+shift[1]
            sample = dict(a, tick=t['tick'], wx=x, wz=z, wy=a['y'])
            track = live.get(key)
            # A slot reused within one tick: a new owner, or a lifetime/health reset.
            reused = track and (track[-1].get('owner') != a.get('owner') or a['health'] > track[-1]['health'])
            if track and (reused or track[-1]['type'] != a['type'] or track[-1]['tick'] != t['tick']-1):
                done.append(track)
                track = None
            if track is None:
                track = live[key] = []
            track.append(sample)
            seen.add(key)
        for key in [k for k in live if k not in seen]:
            done.append(live.pop(key))
        origin_x += t['px']
        origin_z += t['pz']
    return done+list(live.values())


def steps(track):
    out = []
    for a, b in zip(track, track[1:]):
        out.append(dict(tick=b['tick'],
                        pos=(wrap(b['wx']-a['wx']), wrap(b['wz']-a['wz']), b['wy']-a['wy']),
                        rot=(wrap(b['pitch']-a['pitch']), wrap(b['bank']-a['bank']), wrap(b['yaw']-a['yaw'])),
                        speed=(a['speed'], b['speed']), turn=((a['vpitch'], a['vbank'], a['vyaw']),
                                                              (b['vpitch'], b['vbank'], b['vyaw']))))
    return out


def norm(v):
    return math.sqrt(sum(c*c for c in v))


def diff(u, v):
    return norm([a-b for a, b in zip(u, v)])


def tolerance(*vectors):
    # Integration remainders move each axis by one unit; allow 5% of the step for gradual
    # turning and speed ramps within an interval. Real traces stay clean even at 2%.
    return 2+0.05*max(norm(v) for v in vectors)


def check(ticks, renders):
    findings, unexplained, per_type = [], [], collections.defaultdict(lambda: collections.Counter())
    for track in tracks(ticks):
        kind = 'player' if track[0]['ptr'] == (ticks[0]['player'] or {}).get('ptr') and track[0]['type'] == 0 else track[0]['type']
        s = steps(track)
        per_type[kind]['objects'] += 1
        per_type[kind]['steps'] += len(s)
        for quantity in ('pos', 'rot'):
            # Sample i sits between steps i-1 (into it) and i (out of it). A hitch or a stall
            # moves only sample i, so the step changes go +d, -2d, +d: the prediction from
            # the two samples before misses it by d, the one from the two after by d too, and
            # the step out of it changes by -2d. Steady acceleration (a turn rate ramping up)
            # changes every step by the same amount instead, and is not an outlier.
            for i in range(2, len(s)-1):
                before, into, out, after = s[i-2][quantity], s[i-1][quantity], s[i][quantity], s[i+1][quantity]
                tol = tolerance(before, after)
                d1 = [b-a for a, b in zip(before, into)]
                d2 = [b-a for a, b in zip(into, out)]
                d3 = [b-a for a, b in zip(out, after)]
                if norm(d1) > tol and norm(d3) > tol and diff(d1, d3) <= tol \
                        and diff(d2, [-2*c for c in d1]) <= 2*tol:
                    if any(x['turn'][0] != x['turn'][1] or x['speed'][0] != x['speed'][1] for x in (s[i-1], s[i])):
                        per_type[kind][quantity+' outliers explained'] += 1  # input or AI changed the rate
                        continue
                    per_type[kind][quantity+' outliers'] += 1
                    findings.append(dict(kind='outlier', quantity=quantity, type=kind, ptr=f"{track[0]['ptr']:#x}",
                                         tick=s[i-1]['tick'], steps=[before, into, out, after],
                                         speed=s[i-1]['speed'], turn=s[i-1]['turn']))
            # A burst is one step unlike both neighbouring steps, which agree with each other:
            # motion landing only on some ticks (e.g. once per native interval) between still ticks.
            for prev, cur, nxt in zip(s, s[1:], s[2:]):
                tol = tolerance(prev[quantity], nxt[quantity])
                if diff(cur[quantity], prev[quantity]) > tol and diff(cur[quantity], nxt[quantity]) > tol \
                        and diff(prev[quantity], nxt[quantity]) <= tol:
                    # A one-tick change of the object's own turn rate or speed (input, AI)
                    # moves it by exactly that step: counted, not a finding.
                    if cur['turn'][0] != cur['turn'][1] or cur['speed'][0] != cur['speed'][1] \
                            or nxt['turn'][0] != nxt['turn'][1] or nxt['speed'][0] != nxt['speed'][1]:
                        per_type[kind][quantity+' bursts explained'] += 1
                        continue
                    per_type[kind][quantity+' bursts'] += 1
                    findings.append(dict(kind='burst', quantity=quantity, type=kind, ptr=f"{track[0]['ptr']:#x}",
                                         tick=cur['tick'], steps=[prev[quantity], cur[quantity], nxt[quantity]],
                                         speed=cur['speed'], turn=cur['turn']))
            for prev, cur in zip(s, s[1:]):
                tol = tolerance(prev[quantity], cur[quantity])
                if diff(cur[quantity], prev[quantity]) > tol:
                    explained = prev['speed'] != cur['speed'] or prev['turn'] != cur['turn'] \
                        or cur['speed'][0] != cur['speed'][1] or cur['turn'][0] != cur['turn'][1]
                    # Vertical rate is not traced; a change in height rate alone is flight AI.
                    altitude = quantity == 'pos' and diff(cur['pos'][:2], prev['pos'][:2]) <= tol
                    label = '' if explained else ' altitude rate' if altitude else ' unexplained'
                    per_type[kind][quantity+' steps'+label] += 1
                    if label == ' unexplained':
                        unexplained.append(dict(quantity=quantity, type=kind, ptr=f"{track[0]['ptr']:#x}",
                                                tick=cur['tick'], steps=[prev[quantity], cur[quantity]],
                                                speed=cur['speed'], turn=cur['turn']))
        for cur in s:
            if cur['pos'] == (0, 0, 0) and min(abs(cur['speed'][0]), abs(cur['speed'][1])) >= 64:
                per_type[kind]['idle with speed'] += 1
    ticks_shown = [r['tick'] for r in renders]
    session_starts = [b['field'] for a, b in zip(ticks, ticks[1:]) if b['session'] != a['session']]
    gaps = collections.Counter(b-a for a, b in zip(ticks_shown, ticks_shown[1:]))
    fields = collections.Counter(b['field']-a['field'] for a, b in zip(renders, renders[1:]))
    display = dict(presentations=len(renders), tick_gaps=dict(sorted(gaps.items())),
                   field_gaps=dict(sorted(fields.items())),
                   # Scripted sequences (a level exit) present again without running ticks.
                   repeated=sum(1 for a, b in zip(ticks_shown, ticks_shown[1:]) if b == a),
                   # A new session restarts the tick count; any other decrease is a fault.
                   decreasing=sum(1 for a, b in zip(renders, renders[1:]) if b['tick'] < a['tick']
                                  and not any(a['field'] < f <= b['field'] for f in session_starts)))
    return dict(ticks=len(ticks), first_tick=ticks[0]['tick'], last_tick=ticks[-1]['tick'],
                levels=sorted({t['level'] for t in ticks}), display=display,
                per_type={str(k): dict(v) for k, v in sorted(per_type.items(), key=lambda kv: str(kv[0]))},
                findings=findings, unexplained_steps=unexplained)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path)
    p.add_argument('--json', type=Path)
    p.add_argument('--show', type=int, default=20, help='findings to print')
    a = p.parse_args()
    r = check(*load(a.capture))
    if a.json:
        a.json.write_text(json.dumps(r, indent=1)+'\n')
    print(json.dumps({k: v for k, v in r.items() if k not in ('findings', 'unexplained_steps')}, indent=1))
    print(len(r['unexplained_steps']), 'unexplained steps')
    print(len(r['findings']), 'outliers and bursts')
    for f in r['findings'][:a.show]:
        print(f)
