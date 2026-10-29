#!/usr/bin/env python3
"""D8 prediction error: every tick's prediction one tick ahead against the next tick.

  d8_error.py CAPTURE [--out tmp/...json]

CAPTURE is a c2_capture --states --stage --views directory of a build with D7. For
every tick t whose history (tick t-1, same epoch, mode and view) is usable, the D4/D5/
D7 models predict the staged set at alpha 1 (and 2, the clamp) exactly as the slave
would, from the game state at t's first picture. The prediction is compared with the
stage set of tick t+1 (t+2), from its D1 snapshot; holding tick t is the baseline.
Camera: world position (the larger of the X/Z errors), yaw, direction, pitch and height.
Cars: position (track-driven poses placed as h0+$26286 does) and yaw. A car whose pose
flag or status changes, or a camera whose view changes, by the target tick has no
comparable pose; ticks D4 would snap for a jump are reported with their movement.

Each car-tick is classed from its speed +$10 and yaw +$1A at t-1, t and t+1:
collision (speed falls by more than COLLISION, beyond the hardest braking, or the
damage byte +$25 changes), braking (falls by BRAKING or more), steering reversal (the
yaw rate changes sign, both at least REVERSAL), otherwise steady. The camera is classed
by the car it is in or follows. The camera's errors are also binned by its movement
from t-1 to t, the quantity the jump threshold tests.
"""
import argparse
import gzip
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d1_snapshot as d1                                       # noqa: E402
import d3_stage                                                # noqa: E402
import d4_camera                                               # noqa: E402
import d5_cars                                                 # noqa: E402
import d7_views                                                # noqa: E402
from d4_camera import CAMERA, signed                           # noqa: E402

COLLISION, BRAKING, REVERSAL = 1100, 256, 32
ALPHAS = (0x4000, 0x8000)
MOVES = (0, 100000, 200000, 300000, 400000, 600000, 0x100000)   # movement bins, world units
CLASSES = ('steady', 'braking', 'reversal', 'collision')


def quantiles(values):
    values = sorted(values)
    if not values:
        return None
    return dict(n=len(values), p50=round(values[len(values)//2]), p95=round(values[len(values)*95//100]),
                p99=round(values[len(values)*99//100]), max=round(values[-1]))


def measure(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    pictures = []
    result = d3_stage.check(directory, collect=pictures)
    states = meta['states']
    snaps = gzip.decompress((root/'snapshots.bin.gz').read_bytes())
    sizes = [size for _, size in states['snapshot']['regions']]
    tick_cur = {}
    for n, item in enumerate(states['ticks']):
        at = n*sum(sizes) + sizes[0]
        cur = d1.split(snaps[at:at+sizes[1]])[0]
        tick_cur[d3_stage.key(d1.HEADER.unpack_from(cur)[2], item['tick'])] = cur
    h1 = meta['hunk_bases'][1]
    ranges = [tuple(r) for r in states['stages']['game']]
    model = d4_camera.Model(root, meta)
    cars = d5_cars.Cars(model)
    aim = d7_views.Aim(model, meta)
    track, table = model.track, model.table
    body = lambda snap, h, o, f: struct.unpack_from(f, snap, d1.HEADER.size + d3_stage.snapshot_offset(h, o))[0]
    player = body(tick_cur[min(tick_cur)], 0, 0x3a720, '>I')
    records = d1.HEADER.size + sum(size for _, _, size in d1.RANGES)

    def field(snap, n, o, f='>h'):
        return struct.unpack_from(f, snap, records + n*d1.RECORD + d3_stage.record_offset(o))[0]

    def car_pose(buffer, n, flag, on=track):
        at = d5_cars.CARS + n*d5_cars.RECORD
        g = lambda o, f='>h': struct.unpack_from(f, buffer, at+o)[0]
        xz = (g(d5_cars.X, '>l'), g(d5_cars.X+4, '>l')) if flag & 1 else d5_cars.position(
            on, table, g(d5_cars.SEG, '>I'), g(6), g(d5_cars.LON))
        return xz + (g(16),)

    def camera(buffer):
        g = lambda o, f='>h': struct.unpack_from(f, buffer, CAMERA+o)[0]
        return dict(x=g(0xa, '>l'), z=g(0xe, '>l'), yaw=g(0x14), direction=g(0), pitch=g(2), height=g(6))

    def classify(snaps, n):
        """Car n's class over ticks t-1, t, t+1 (record 0 is the synthetic camera)."""
        speed = [field(s, n, 0x10, '>H') for s in snaps]
        yaw = [field(s, n, 0x1a) for s in snaps]
        if speed[1]-speed[2] > COLLISION or field(snaps[1], n, 0x25, '>B') != field(snaps[2], n, 0x25, '>B'):
            return 'collision'
        if speed[1]-speed[2] >= BRAKING:
            return 'braking'
        before, after = signed(yaw[1]-yaw[0]), signed(yaw[2]-yaw[1])
        if min(abs(before), abs(after)) >= REVERSAL and (before < 0) != (after < 0):
            return 'reversal'
        return 'steady'

    def move_bin(value):
        for low, high in zip(MOVES, MOVES[1:]):
            if low <= value < high:
                return f'{low}-{high}'
        return f'>={MOVES[-1]}'

    errors = {}

    def add(*path_value):
        *path, value = path_value
        errors.setdefault('/'.join(path), []).append(value)

    # Each tick's poses are placed on its own track: pit stops swap ranges between ticks.
    readers = {}
    for tick, *_, read, _, _, _ in pictures:
        readers.setdefault(tick, read)

    def track_at(tick):
        at = d4_camera.Track(root, meta)
        at.update(readers[tick], ranges)
        return at

    seen, counts, worst = set(), {}, []
    count = lambda name: counts.__setitem__(name, counts.get(name, 0)+1)
    for tick, alpha, staged, saved, read, decision, outcome, mode in pictures:
        if tick in seen:
            continue
        seen.add(tick)
        history, current = tick_cur.get(tick-1), tick_cur.get(tick)
        header = d1.HEADER.unpack_from(history) if history else None
        view_of = lambda snap: (body(snap, 1, 0x234, '>Q'), body(snap, 1, 0x23c, '>B'))
        if not history or header[2] != tick >> 16 or header[5] != mode or view_of(history) != (
                struct.unpack('>Q', read(1, 0x234, 8))[0], read(1, 0x23c, 1)[0]):
            count('no history')
            continue
        model.track.update(read, ranges)
        code = read(1, 0x23c, 1)[0]
        selected = struct.unpack('>I', read(1, 0x238, 4))[0]
        view = ('replay ' if mode == 2 else '') + d7_views.view_name(code, selected, player)
        viewed = (selected - h1 - d7_views.CARS_AT) // 0xc0 + 1
        viewed = viewed if 1 <= viewed <= 26 else 0
        spring = body(current, 0, 0x3a820, '>h')
        clamp = struct.unpack('>h', read(2, 0x231cc, 2))[0]
        camera_history = history[d1.HEADER.size + d3_stage.snapshot_offset(0, 0x3a7f8):]
        hist_rec = lambda r: history[records + r*d1.RECORD:records + (r+1)*d1.RECORD]
        moved = max(abs(camera(saved)[c] - body(history, 0, 0x3a7f8 + 0xa + 4*i, '>l'))
                    for i, c in enumerate(('x', 'z')))
        count('ticks')
        history_stage = d3_stage.from_snapshot(history)[0]
        history_track = track_at(tick-1) if tick-1 in readers else track
        for steps, a in enumerate(ALPHAS, 1):
            target = tick_cur.get(tick+steps)
            if not target:
                count(f'alpha {steps}: no next tick')
                continue
            if any(view_of(tick_cur.get(tick+s, target)) != view_of(current) for s in range(1, steps+1)):
                count(f'alpha {steps}: view changes by then (a cut or a key)')
                continue
            def between(out):
                cars.predict(out, hist_rec, read, a)
                aim.predict(out, saved, history, read, a)
            predicted, result_outcome = model.predict(saved, camera_history, a, spring, clamp, code, between)
            actual = d3_stage.from_snapshot(target)[0]
            target_track = track_at(tick+steps) if tick+steps in readers else track
            label = f'alpha {steps}'
            if result_outcome == 'jump':
                count(f'{label}: camera jump')
                add(label, 'jump movement', moved)
                continue
            following = tick_cur.get(tick+1, target)
            camera_class = classify((history, current, following), viewed) if viewed else 'steady'
            want = camera(actual)
            pair = []
            for name, buffer in (('predicted', predicted), ('latest', saved)):
                got = camera(buffer)
                position = max(abs(got['x']-want['x']), abs(got['z']-want['z']))
                pair.append(position)
                add(label, 'camera', name, 'position', position)
                add(label, 'camera', name, 'position by class', camera_class, position)
                add(label, 'camera', name, 'position by movement', move_bin(moved), position)
                add(label, 'camera', name, 'position by view', view, position)
                for word in ('yaw', 'direction', 'pitch', 'height'):
                    add(label, 'camera', name, word, abs(signed(got[word]-want[word])))
                if steps == 1 and name == 'predicted':
                    worst.append((position, tick, 'camera', view, camera_class))
            if pair[1]:
                count(f'{label}: camera moved')
                if pair[0] > pair[1]:
                    count(f'{label}: camera worse than holding')
            for n in range(1, 27):
                flag, status = field(current, n, 0x7e, '>B'), field(current, n, 0x96, '>H')
                if (field(target, n, 0x7e, '>B'), field(target, n, 0x96, '>H')) != (flag, status) or status & 0x8000:
                    count(f'{label}: car not comparable')
                    continue
                if (field(history, n, 0x7e, '>B') ^ flag) & 1:
                    count(f'{label}: car pose flag changed')
                    continue
                cls = classify((history, current, following), n)
                want = car_pose(actual, n-1, flag, target_track)
                if steps == 1:
                    past, now = car_pose(history_stage, n-1, flag, history_track), car_pose(saved, n-1, flag)
                    add(label, 'cars', 'movement', max(abs(now[i]-past[i]) for i in (0, 1)))
                pair = []
                for name, buffer in (('predicted', predicted), ('latest', saved)):
                    got = car_pose(buffer, n-1, flag)
                    position = max(abs(got[0]-want[0]), abs(got[1]-want[1]))
                    pair.append((position, abs(signed(got[2]-want[2]))))
                    add(label, 'cars', name, 'position', position)
                    add(label, 'cars', name, 'position by class', cls, position)
                    add(label, 'cars', name, 'yaw', abs(signed(got[2]-want[2])))
                    add(label, 'cars', name, 'yaw by class', cls, abs(signed(got[2]-want[2])))
                    if steps == 1 and name == 'predicted':
                        worst.append((position, tick, f'car {n}', view, cls))
                if pair[1][0]:
                    count(f'{label}: car moved')
                    if pair[0] == pair[1]:
                        count(f'{label}: car held')
                    elif pair[0][0] > pair[1][0]:
                        count(f'{label}: car worse than holding')
                    if pair[0][1] > pair[1][1]:
                        count(f'{label}: car yaw worse than holding')
                        count(f'{label}: car yaw worse than holding, {cls}')
    worst.sort(reverse=True)
    worst = worst[:20] + [w for w in worst if w[2] == 'camera'][:10]
    return dict(check=result['status'], failure_count=result['failure_count'], counts=counts,
                thresholds=dict(collision=COLLISION, braking=BRAKING, reversal=REVERSAL),
                errors={name: quantiles(values) for name, values in sorted(errors.items())},
                worst=[dict(error=e, epoch=t >> 16, tick=t & 0xffff, item=i, view=v, cls=c)
                       for e, t, i, v, c in worst])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--out')
    args = parser.parse_args()
    out = measure(args.capture)
    text = json.dumps(out, indent=2)+'\n'
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(text)
    print(text)
