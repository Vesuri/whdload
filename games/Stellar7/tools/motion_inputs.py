#!/usr/bin/env python3
"""Inspect complete native movement inputs before deciding whether to cache vectors.

Registers are sampled at the audited instruction boundaries in $8682..$87e8.
The key contains post-update angles, signed-word speed and three linear terms.
This reports cache opportunities, not an implemented optimization or saved cycles.
"""
import argparse
import collections
import json
import re
from pathlib import Path
import barto


def inspect(folder, capacity=4):
    folder = Path(folder)
    code = int(re.search(r'^code=(\S+)', (folder/'anchor.txt').read_text(), re.M)[1], 0)
    trace = barto.load(folder/'trace.bin')
    current = None
    calls = []
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if pc is None:
                continue
            at = pc-code
            if at == 0x868e:
                assert current is None, 'nested movement needs a stack-aware extension'
                current = dict(actor=regs[11], sp=regs[15], trig=[])
            if current is None or not current['sp']-4096 <= regs[15] <= current['sp']:
                continue
            if at == 0x86aa:
                current['pitch'] = regs[0] & 0xffff
            elif at == 0x86ae:
                current['bank'] = regs[1] & 0xffff
            elif at == 0x876c:
                current['yaw'] = regs[0] & 0xffff
            elif at in (0x86b8, 0x8772):
                current['speed'] = regs[1] & 0xffff
            elif at == 0x87be:
                current['speed'] = regs[0] & 0xffff
            elif at == 0x16a90:
                current['trig_kind'] = 'cos'
            elif at == 0x16ab8:
                current['trig_kind'] = 'sin'
            elif at == 0x16a98:
                angle = regs[0] & 0xffff
                if current.get('trig_kind') == 'sin':
                    angle = (angle+0x4000) & 0xffff
                current['trig'].append(angle)
            elif at in (0x87c8, 0x87d2, 0x87dc):
                current[{0x87c8: 'x', 0x87d2: 'z', 0x87dc: 'y'}[at]] = regs[0] & 0xffff
            elif at == 0x87e2:
                if 'yaw' not in current:
                    assert len(current['trig']) == 5, current
                    current['yaw'] = current['trig'][1]
                    assert current['trig'][0] == current['trig'][2] == current['trig'][4] == current['pitch']
                    assert current['trig'][1] == current['trig'][3]
                elif current['yaw']:
                    assert current['trig'] == [current['yaw'], current['yaw']]
                else:
                    assert not current['trig']
                keys = ('pitch', 'bank', 'yaw', 'speed', 'x', 'z', 'y')
                assert all(key in current for key in keys), current
                calls.append((current['actor'], tuple(current[key] for key in keys)))
                current = None
    assert calls, 'no complete native movement calls'
    cache = []
    next_slot = hits = 0
    per_actor = {}
    actor_hits = 0
    for actor, key in calls:
        if key in cache:
            hits += 1
        elif len(cache) < capacity:
            cache.append(key)
        else:
            cache[next_slot] = key
            next_slot = (next_slot+1) % capacity
        actor_hits += per_actor.get(actor) == key
        per_actor[actor] = key
    return dict(complete_calls=len(calls), distinct_inputs=len(set(key for actor, key in calls)),
                actors=len(per_actor),
                zero_pitch_banked_calls=sum(key[0] == 0 and key[1] != 0 for actor, key in calls),
                stationary_calls=sum(not any(key) for actor, key in calls),
                fifo_capacity=capacity, fifo_hits=hits,
                per_actor_last_hits=actor_hits, partial_at_end=current is not None,
                input_counts=[dict(words=list(key), calls=count)
                              for key, count in collections.Counter(key for actor, key in calls).most_common()])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--capacity', type=int, default=4)
    parser.add_argument('--inputs', action='store_true', help='include exact input words and frequencies')
    args = parser.parse_args()
    assert args.capacity > 0
    for capture in args.captures:
        result = inspect(capture, args.capacity)
        if not args.inputs:
            result.pop('input_counts')
        print(capture, json.dumps(result, sort_keys=True))
