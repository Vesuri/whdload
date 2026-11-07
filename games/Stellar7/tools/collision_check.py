#!/usr/bin/env python3
"""Check projectile collisions in a fixed_window.py --motion-ticks capture.

The trace is recorded after each tick's collision pass, before the recenter shift.
Overlap is the native box test at $85f6: every axis within the mean of the two radii
(actor offset 4). The projectile scan skips targets flagged $fc/$fd and the projectile's
owner (offset 106), and $85f6 skips type 7. Native hit handling ($3274-$3292) then ignores
the player, type 46 and one special object, so overlaps with those are reported apart.

For each type-23 projectile (the type the native hit scan at $325a handles) and target:
  missed     the projectile still overlaps the target in a record and survives to the
             next tick with its lifetime not reset (it drops once per native interval):
             it passed through without a hit
  tunnelled  the projectile's path between two records, relative to the target, gets
             within half the reach on every axis at once although neither record
             overlaps, and it survives. One tick's relative step is shorter than the
             reach, so this cannot happen when every tick is tested
  grazed     the same, but the path only clips the box's outer half (a corner between
             two samples), which any per-step test misses
  hit        the projectile is removed with lifetime left; listed with the nearest target
             by box distance (1.0 = at the edge of the overlap box) and whether that
             target lost health or was removed in the same tick. The level 0 boss helper
             moves the boss to the projectile's height for its test ($10c3c/$10d6e), so
             boss hits are judged by X/Z distance

Relative positions are frame-independent, so the recenter shift between records cancels
except for type 7, which is not recentred and is not a target.

Usage: tools/collision_check.py CAPTURE [--json OUT]
"""
import argparse
import collections
import json
from pathlib import Path

from motion_check import load, wrap

PROJECTILE = 23


def relative(p, q, t):
    qx, qz = (t['px'], t['pz']) if q is t['player'] else (q['x'], q['z'])
    return wrap(p['x']-qx), wrap(p['z']-qz), p['y']-q['y']


def reach(p, q):
    return (p['radius']+q['radius'])//2


def inside(r, half):
    return all(abs(c) <= half for c in r)


def crosses(r0, r1, half):
    """Does the segment r0->r1 enter the box [-half, half]^3 (slab test)?"""
    lo, hi = 0.0, 1.0
    for a, b in zip(r0, r1):
        d = b-a
        if d == 0:
            if abs(a) > half:
                return False
            continue
        t0, t1 = sorted(((-half-a)/d, (half-a)/d))
        lo, hi = max(lo, t0), min(hi, t1)
        if lo > hi:
            return False
    return True


def depth(r0, r1, half):
    """The deepest point of the segment r0->r1 in box units (0 = centre, 1 = edge)."""
    return min(max(abs(a+(b-a)*k/256) for a, b in zip(r0, r1)) for k in range(257))/max(1, half)


def targets(t, p):
    out = [q for q in t['actors'] if q is not p]
    if t['player']:
        out.append(t['player'])
    return [q for q in out if q['type'] != 7 and q['flags'] not in (0xfc, 0xfd) and q['ptr'] != p['owner']]


def check(ticks):
    if not ticks or 'radius' not in (ticks[0]['actors'] or [{}])[0]:
        raise SystemExit('trace has no radius/owner fields; recapture with the current fixed_window.py')
    missed, tunnelled, grazed, ignored, hits = [], [], [], [], []
    counts = collections.Counter()
    for t, nxt in zip(ticks, ticks[1:]):
        if nxt['session'] != t['session'] or nxt['tick'] != t['tick']+1:
            continue  # a level exit or Continue clears the actors between these records
        later = {a['ptr']: a for a in nxt['actors']}
        if nxt['player']:
            later[nxt['player']['ptr']] = nxt['player']
        for p in t['actors']:
            if p['type'] != PROJECTILE:
                continue
            counts['projectile ticks'] += 1
            after = later.get(p['ptr'])
            survives = after is not None and after['type'] == PROJECTILE and after['health'] <= p['health']
            for q in targets(t, p):
                r0, half = relative(p, q, t), reach(p, q)
                special = q is t['player'] or q['type'] == 46
                event = dict(tick=t['tick'], projectile=f"{p['ptr']:#x}", owner=f"{p['owner']:#x}",
                             target=f"{q['ptr']:#x}", target_type='player' if q is t['player'] else q['type'])
                if inside(r0, half):
                    if survives:
                        (ignored if special else missed).append(event)
                    continue
                q1 = later.get(q['ptr'])
                if survives and q1 is not None:
                    r1 = relative(after, q1, nxt)
                    # Follow the step, not the wrapped value: a pair ~32768 apart wraps
                    # between records, and the straight line between wrapped values
                    # would cross the box.
                    r1 = tuple(a+wrap(b-a) for a, b in zip(r0, r1))
                    if not inside(r1, half) and crosses(r0, r1, half):
                        d = depth(r0, r1, half)
                        # A step shorter than the reach cannot jump a chord at depth 0.5 or
                        # less; shallower crossings clip a corner between samples, as any
                        # per-step test (the native one at a coarser step) does.
                        kind = ignored if special else tunnelled if d <= 0.5 else grazed
                        kind.append(dict(event, path=[r0, r1], reach=half, depth=round(d, 2)))
            if not survives and p['health'] > 1:
                # Removed with lifetime left: a hit (projectile or terrain). The hit happened
                # in the next tick's collision pass, from this record's positions plus one step.
                near = []
                for q in targets(t, p):
                    r = relative(p, q, t)
                    q1 = later.get(q['ptr'])
                    near.append((max(abs(c) for c in r)/max(1, reach(p, q)), q,
                                 q1 is None or q1['health'] < q['health'] or q1['type'] != q['type'],
                                 max(abs(c) for c in r[:2])/max(1, reach(p, q))))
                near.sort(key=lambda n: n[0])
                hit = dict(tick=nxt['tick'], projectile=f"{p['ptr']:#x}", lifetime=p['health'])
                if near:
                    d, q, damaged, xz = near[0]
                    hit.update(target_type='player' if q is t['player'] else q['type'], box_distance=round(d, 2),
                               box_distance_xz=round(xz, 2), target_damaged=damaged)
                hits.append(hit)
    counts['hits'] = len(hits)
    # One tick's relative step stays below half the smallest reach, so a hit should come
    # from within 1.5 boxes. The level 0 boss helper tests at the projectile's height
    # ($10c3c/$10d6e), so its hits count by X/Z distance.
    def near(h):
        return h.get('target_damaged') and (h['box_distance_xz'] if h['target_type'] in (44, 45) else h['box_distance']) <= 1.5
    counts['hits on a damaged target within 1.5 boxes'] = sum(1 for h in hits if near(h))
    return dict(ticks=len(ticks), counts=dict(counts), missed=missed, tunnelled=tunnelled, grazed=grazed,
                ignored_by_native_rules=ignored, hits=hits)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path)
    p.add_argument('--json', type=Path)
    a = p.parse_args()
    ticks, _ = load(a.capture)
    r = check(ticks)
    if a.json:
        a.json.write_text(json.dumps(r, indent=1)+'\n')
    print(json.dumps({k: v[:20] if isinstance(v, list) else v for k, v in r.items()}, indent=1))
