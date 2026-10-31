#!/usr/bin/env python3
"""F3: the computer cars' pace in C5(b) state captures taken at different world steps.

  python3 tools/f3_pace.py NAME=CAPTURE... [--out tmp/...json]

Each CAPTURE is a c2_capture --states directory. Over the completed ticks of the race (the
first epoch), each computer car's lap count (+$22) is followed, and the race clock
(h0+$3A77C, whole milliseconds of game time, which keeps its ratio to real time at every
step) is noted when it completes a lap. Reported per lap: the mean completion time over
the cars that completed it, and the mean lap time of laps after the first (the standing
start). A race differs from the next in its events, so compare the field's means, not
one car. The player's record (h0+$3A720) is excluded: it sits on the grid.
"""
import argparse
import json
import struct
from pathlib import Path

from c5_compare import load

CARS = 26


def pace(directory):
    ranges, records, _, identity = load(directory)
    h1, start, size = ranges['cars']
    _, session, _ = ranges['session']
    assert h1 == 1 and start <= 0x5d6 and 0x5d6+CARS*0xc0 <= start+size
    race = sorted((tick, body) for (run, tick), body in records.items() if run == 0)
    clock = lambda body: struct.unpack_from('>I', body, size+0x3a77c-session)[0]
    player = struct.unpack_from('>I', race[0][1], size+0x3a720-session)[0]
    slots = [n for n in range(CARS) if identity['hunk_bases'][1]+0x5d6+n*0xc0 != player]
    laps = lambda body, n: body[0x5d6-start+n*0xc0+0x22]
    done = {n: [] for n in slots}
    previous = {n: laps(race[0][1], n) for n in slots}
    for _, body in race:
        for n in slots:
            now = laps(body, n)
            if now == previous[n]+1:
                done[n].append(clock(body))
            previous[n] = now
    by_lap = {}
    for times in done.values():
        for k, t in enumerate(times):
            by_lap.setdefault(k+1, []).append(t)
    lap_times = [b-a for times in done.values() for a, b in zip(times, times[1:])]
    return dict(cars=len(slots), ticks=len(race), whd_args=identity['whd_args'],
                laps={k: dict(cars=len(v), mean_s=sum(v)/len(v)/1000) for k, v in sorted(by_lap.items())},
                lap_time_s=sum(lap_times)/len(lap_times)/1000 if lap_times else None,
                lap_times=len(lap_times))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--out')
    args = parser.parse_args()
    result = {}
    for item in args.captures:
        name, directory = item.split('=', 1)
        result[name] = pace(directory)
    base = next(iter(result.values()))
    for name, r in result.items():
        ratio = r['lap_time_s']/base['lap_time_s']
        print(f"{name}: {r['ticks']} ticks, {r['cars']} cars; mean lap after the first "
              f"{r['lap_time_s']:.3f} s over {r['lap_times']} laps, /first {ratio:.4f}")
        for k, v in r['laps'].items():
            print(f"  lap {k}: {v['cars']} cars, mean completion {v['mean_s']:.2f} s")
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
