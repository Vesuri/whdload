#!/usr/bin/env python3
"""H2: the computer cars' cornering loss and pace in C5(b) state captures at any step.

  python3 tools/h2_corner.py REF=CAPTURE:STEP NAME=CAPTURE:STEP... [--out tmp/...json]

Each CAPTURE is a c2_capture --states directory and STEP its world step (h0+$34366: 8192
stock, 3276 with --step20, 6750 for the 1995-2002 datafiles' frame rate). Over the race
(the first epoch, after 30 s of game time) and the computer cars on the track (not in the
explicit pose, +$7E bit 0, nor on the pit segments below h1+$53DE):
- per car-second of game time, the speed (+$10) gained and lost through +$72, the change
  the speed update records, and the rest of each tick's change, the cornering loss
  h0+$2B352-$2B388 takes after it (by speed, in 2000-unit bands);
- the median and 10th-percentile lap after the first, by the race clock (h0+$3A77C);
- each 16-segment stretch's median speed against REF's.
A race differs from the next in its events, which move the mean lap by several per cent;
the median lap and the loss a second are the stable measures.
"""
import argparse
import json
import statistics as st
import struct

from c5_compare import load

CARS, TRACK = 26, 0x53de
W = lambda r, o: struct.unpack_from('>H', r, o)[0]
S = lambda r, o: struct.unpack_from('>h', r, o)[0]
L = lambda r, o: struct.unpack_from('>I', r, o)[0]


def race(directory):
    ranges, records, _, identity = load(directory)
    h1, start, size = ranges['cars']
    _, session, _ = ranges['session']
    assert h1 == 1 and start <= 0x5d6 and 0x5d6+CARS*0xc0 <= start+size
    ticks = sorted((tick, body) for (run, tick), body in records.items() if run == 0)
    player = L(ticks[0][1], size+0x3a720-session)
    base = identity['hunk_bases'][1]
    slots = [n for n in range(CARS) if base+0x5d6+n*0xc0 != player]
    out = []
    for _, body in ticks:
        cars = [body[0x5d6-start+n*0xc0:0x5d6-start+(n+1)*0xc0] for n in slots]
        out.append((L(body, size+0x3a77c-session), cars))
    return base, out, identity


def measure(directory, step):
    base, ticks, identity = race(directory)
    dt = step/65536
    gain = brake = loss = seconds = 0
    bands, stretches, laps, previous = {}, {}, {}, {}
    on_track = lambda r: not r[0x7e] & 1 and L(r, 0x12)-base >= TRACK
    for (c0, r0), (c1, r1) in zip(ticks, ticks[1:]):
        for n, r in enumerate(r1):
            if r[0x22] != previous.get(n):
                laps.setdefault(n, []).append(c1)
                previous[n] = r[0x22]
        if c0 < 30000:
            continue
        seconds += dt
        for a, b in zip(r0, r1):
            if not (on_track(a) and on_track(b)):
                continue
            change = S(b, 0x72)
            rest = W(b, 0x10)-W(a, 0x10)-change
            gain += max(change, 0)
            brake += min(change, 0)
            loss += max(-rest, 0)
            band = bands.setdefault(W(a, 0x10)//2000*2000, [0, 0])
            band[0] += 1
            band[1] -= rest
            stretches.setdefault((L(a, 0x12)-base-TRACK)//0x2e//16*16, []).append(W(a, 0x10))
    cars = len(ticks[0][1])
    lap_times = sorted(b-a for t in laps.values() for a, b in zip(t[1:], t[2:]))
    return dict(whd_args=identity['whd_args'], step=step, ticks=len(ticks), cars=cars,
                per_car_second=dict(gain=gain/seconds/cars, brake=brake/seconds/cars,
                                    cornering_loss=loss/seconds/cars),
                loss_by_speed={k: v[1]/v[0]/dt for k, v in sorted(bands.items()) if v[0] >= 500},
                laps=len(lap_times), median_lap_s=st.median(lap_times)/1000,
                p10_lap_s=lap_times[len(lap_times)//10]/1000,
                stretch_speed={k: st.median(v) for k, v in sorted(stretches.items())})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--out')
    args = parser.parse_args()
    result, ref = {}, None
    for item in args.captures:
        name, rest = item.split('=', 1)
        directory, step = rest.rsplit(':', 1)
        m = result[name] = measure(directory, int(step))
        ref = ref or m
        common = sorted(set(m['stretch_speed']) & set(ref['stretch_speed']))
        m['speed_vs_ref'] = st.mean(m['stretch_speed'][k]/ref['stretch_speed'][k] for k in common)
        p = m['per_car_second']
        print(f"{name}: step {m['step']}, median lap {m['median_lap_s']:.2f} s "
              f"({m['median_lap_s']/ref['median_lap_s']-1:+.1%}) over {m['laps']} laps, p10 {m['p10_lap_s']:.2f} s; "
              f"per car-second +{p['gain']:.0f} {p['brake']:.0f}, cornering loss {p['cornering_loss']:.0f}; "
              f"stretch speed /ref {m['speed_vs_ref']:.3f}")
        print('   loss a second by speed:', ' '.join(f'{k//1000}k {v:.0f}' for k, v in m['loss_by_speed'].items()))
    if args.out:
        for m in result.values():
            m['stretch_speed'] = {str(k): v for k, v in m['stretch_speed'].items()}
            m['loss_by_speed'] = {str(k): v for k, v in m['loss_by_speed'].items()}
        with open(args.out, 'w') as f:
            json.dump(result, f, indent=2)
            f.write('\n')


if __name__ == '__main__':
    main()
