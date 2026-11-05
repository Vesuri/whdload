#!/usr/bin/env python3
"""D6 per-item evidence: steering (wheel images) and the rev counter over a whole race.

  d6_items.py CAPTURE [--out tmp/...json]

CAPTURE is a c2_capture --states --snapshot directory (any D1 build). For every run of
consecutive ticks and each car, the steering +$48 that a picture at tick + alpha would
show is compared with the ideal, the steering interpolated between the actual ticks around
that time, once held at the tick and once extrapolated as D5 does the pose words. Errors
are in front-wheel angle units, as h2+$28C30 turns steering into the wheel's angle; a
wheel image spans $1000, so an error above $800 can show the wrong image. The rev
counter is the selected car's bar position, h0+$3940A from its +$62, at every tick.
"""
import argparse
import collections
import gzip
import json
from pathlib import Path
import struct

import d1_snapshot as d1
from race_profile import image

ALPHAS = (0x2000, 0x4000, 0x6000)           # Q14: half, one and one and a half ticks
STEERING, RPM = 0x48, 0x62


def wheel(steering):
    """h2+$28C30: the steering's contribution to the front-wheel angle."""
    a = abs(steering)
    a = (a-0x200)//2 + 0x800 if a >= 0x200 else a*4
    return (a if steering >= 0 else -a) + 2*steering


def quantiles(values):
    values = sorted(values)
    at = lambda p: values[min(len(values)-1, len(values)*p//100)]
    return dict(p50=at(50), p95=at(95), p99=at(99), max=values[-1],
                over_half_image=round(100*sum(v > 0x800 for v in values)/len(values), 2))


def measure(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    states = meta['states']
    record = states['record']
    cars_at = record - states['ranges']['cars'][2] - states['ranges']['session'][2]
    ticks = gzip.decompress((root/'ticks.bin.gz').read_bytes())
    snaps = gzip.decompress((root/'snapshots.bin.gz').read_bytes())
    snap_sizes = [size for _, size in states['snapshot']['regions']]
    h0, h1 = meta['hunk_bases'][:2]
    memory = image((root/'chip.bin').read_bytes(), (root/'fast.bin').read_bytes(), b'')
    scale = struct.unpack_from('>h', memory, h0+0x3a93e)[0]
    top = struct.unpack_from('>h', memory, h0+0x3758c)[0] - 2
    numbers, cars, selected = [], [], []
    for n, item in enumerate(states['ticks']):
        numbers.append(item['tick'])
        cars.append(ticks[n*record+cars_at:n*record+cars_at+states['ranges']['cars'][2]])   # h1+$368 on
        at = n*sum(snap_sizes) + snap_sizes[0]
        cur = d1.split(snaps[at:at+snap_sizes[1]])[0]
        selected.append((struct.unpack_from('>I', cur, d1.HEADER.size+0x14)[0] - h1 - 0x5d6)//0xc0)
    field = lambda t, car, offset, f='>h': struct.unpack_from(f, cars[t], 0x5d6-0x368+car*0xc0+offset)[0]

    def bar(rpm):
        """h0+$3940A: the bar position from +$62."""
        d0 = ((max(rpm-0x1ce8, 0)*scale) << 2 >> 16) << 1 & 0xffff
        return max(0, min(d0-0x10000 if d0 & 0x8000 else d0, top))

    steering = {}
    for alpha in ALPHAS:
        whole, fraction = divmod(alpha, 0x4000)
        held, extrapolated = [], []
        for t in range(1, len(numbers)-whole-1):
            if numbers[t+whole+1] - numbers[t-1] != whole+2:
                continue
            for car in range(26):
                s = [field(t+k, car, STEERING) for k in range(-1, whole+2)]
                a, b = s[whole+1], s[whole+2]
                ideal = round(a + (b-a)*fraction/0x4000)
                guess = s[1] + int((s[1]-s[0])*alpha/0x4000)
                held.append(abs(wheel(ideal)-wheel(s[1])))
                extrapolated.append(abs(wheel(ideal)-wheel(guess)))
        steering[f'{alpha/0x4000:g}'] = dict(held=quantiles(held), extrapolated=quantiles(extrapolated),
                                             car_pictures=len(held))
    steps = collections.Counter()
    for t in range(1, len(numbers)):
        if numbers[t] == numbers[t-1]+1 and selected[t] == selected[t-1]:
            car = selected[t]
            steps[abs(bar(field(t, car, RPM, '>H'))-bar(field(t-1, car, RPM, '>H')))//2] += 1
    return dict(ticks=len(numbers), steering=steering,
                rev_counter=dict(segments=top//2, segments_changed_per_tick=dict(sorted(steps.items()))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--out')
    args = parser.parse_args()
    text = json.dumps(measure(args.capture), indent=2)+'\n'
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(text)
    print(text)
