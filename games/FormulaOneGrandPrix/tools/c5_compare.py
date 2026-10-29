#!/usr/bin/env python3
"""Compare C5(b) per-tick state across render schedules; differences are listed, not hidden.

  c5_compare.py --out tmp/c5/states.json normal=DIR slowed=DIR one-field=DIR [...]
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def load(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    assert meta['status'] == 'CAPTURED' and meta['quit'] == 'OK', directory
    assert hashlib.sha256((root/'slave.bin').read_bytes()).hexdigest() == meta['build']['slave_sha256']
    states = meta['states']
    assert states == json.loads((root/'states.json').read_text())
    archive = (root/'ticks.bin.gz').read_bytes()
    assert hashlib.sha256(archive).hexdigest() == states['archive_sha256']
    data = gzip.decompress(archive)
    size = states['record']
    assert len(data) == size*states['count'] == size*len(states['ticks'])
    header = size - states['ranges']['cars'][2] - states['ranges']['session'][2]
    # Ticks are consecutive within an epoch and start again from 1 in the next (a replay
    # and the race after it): each tick is keyed by its run and its number.
    records, run = {}, 0
    ticks = states['ticks']
    for n, item in enumerate(ticks):
        if n and item['tick'] != ticks[n-1]['tick']+1:
            assert item['tick'] <= ticks[n-1]['tick'], (n, item['tick'])
            run += 1
        body = data[n*size+header:(n+1)*size]
        assert hashlib.sha256(body).hexdigest() == item['sha256']
        records[(run, item['tick'])] = body
    fields = ticks[-1]['serial'] - ticks[0]['serial']
    schedule = dict(ticks=len(ticks), first=ticks[0]['tick'], last=ticks[-1]['tick'], fields=fields,
                    pictures=ticks[-1]['pictures'] - ticks[0]['pictures'],
                    fields_per_picture=fields/max(1, ticks[-1]['pictures']-ticks[0]['pictures']),
                    tick_only=sum(t['draw_mode'] == 2 for t in ticks),
                    max_batch=max(t['batch'] for t in ticks),
                    dropped=ticks[-1]['dropped'] - ticks[0]['dropped'])
    identity = dict(build=meta['build'], runtime=meta['runtime'], setup=meta['setup'],
                    extra_args=meta['extra_args'], whd_args=meta['whd_args'],
                    effective=meta.get('effective'), hunk_bases=meta['hunk_bases'],
                    route_reply=meta['route_reply'], inputs=states.get('inputs'))
    return states['ranges'], records, schedule, identity


def name_offset(ranges, offset):
    """Map a byte of the compared body to its hunk offset (and car record, if any)."""
    h, start, size = ranges['cars']
    if offset < size:
        address = start + offset
        car = (address-0x5d6)//0xc0 if 0x5d6 <= address < 0x5d6+26*0xc0 else None
        return f'h{h}+{address:05x}' + (f' (car {car} +{(address-0x5d6)%0xc0:02x})' if car is not None else '')
    h, start, _ = ranges['session']
    return f'h{h}+{start+offset-size:05x}'


def compare(arms):
    loaded = {name: load(path) for name, path in arms.items()}
    reference = next(iter(loaded))
    ranges = loaded[reference][0]
    result = dict(reference=reference, arms={}, schedules={n: v[2] for n, v in loaded.items()},
                  identities={n: v[3] for n, v in loaded.items()})
    base = loaded[reference][1]
    for name, (other_ranges, records, _, _) in loaded.items():
        if name == reference:
            continue
        assert other_ranges == ranges
        common = sorted(set(base) & set(records))
        differing = [t for t in common if base[t] != records[t]]
        entry = dict(common_ticks=len(common), first_common=common[0], last_common=common[-1],
                     differing_ticks=len(differing), equal=not differing)
        if differing:
            first = differing[0]
            offsets = [i for i, (a, b) in enumerate(zip(base[first], records[first])) if a != b]
            entry.update(first_difference=first,
                         first_offsets=[name_offset(ranges, i) for i in offsets[:64]],
                         first_offset_count=len(offsets))
        result['arms'][name] = entry
    result['status'] = 'PASS' if all(a['equal'] for a in result['arms'].values()) else 'DIFFERENT'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arms', nargs='+', help='NAME=DIR; the first is the reference')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    arms = dict(a.split('=', 1) for a in args.arms)
    result = compare(arms)
    path = Path(args.out).resolve()
    if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
        raise ValueError('output must stay in project tmp/')
    path.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'arms', 'schedules')}, indent=2))
