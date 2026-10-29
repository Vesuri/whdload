#!/usr/bin/env python3
"""D9 smoothness: picture by picture, does what is shown move forward every picture?

  d9_smooth.py CAPTURE [--shots NAME=DIR ...] [--out tmp/...json]

CAPTURE is a c2_capture --states --stage --views directory of a build with D7. The D3-D7
check rebuilds every staged picture. Each picture is placed at the field it first reached
the screen (its start plus the lead measured at that display, D2) and shows until the
next picture does: that interval is its frame time. Between consecutive pictures of the
same epoch, mode and view the step of the camera (world X/Z and yaw) and of every car
(world X/Z, track-driven cars placed as h0+$26286 does on that picture's track) is
compared with the object's actual motion around the displayed time, from tick T' to
T'+1 with T' the tick drawn plus the whole ticks of α:
- backwards: the step points against that motion (dot product below zero), or a yaw step
  against a yaw rate of at least TURN per tick;
- stalled: no step while the object moves;
- evenness: the step per field divided by the motion per field of that tick interval.
The same pictures showing their tick (the staged set without prediction) are the
baseline.

--shots measures per-field screenshots of c2_capture --shots runs: the fields between
changes of the shown picture (the frame-time histogram on screen), where on screen they
change, and the share of the pictures submitted in the window that changed it.
"""
import argparse
import collections
import gzip
import hashlib
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

TURN = 32                       # yaw rate per tick below which a yaw step has no direction
PIT = (733, 1128)              # D7 race: epoch 3 ticks with pit stops on (D8)
RATIOS = (0, .25, .5, .75, 1.25, 1.5, 2, 3)                    # evenness bins


def quantiles(values):
    values = sorted(values)
    if not values:
        return None
    pick = lambda p: values[min(len(values)-1, int(len(values)*p))]
    return dict(n=len(values), p5=round(pick(.05), 3), p50=round(pick(.5), 3),
                p95=round(pick(.95), 3), max=round(values[-1], 3))


def ratio_bin(value):
    for low, high in zip(RATIOS, RATIOS[1:]):
        if low <= value < high:
            return f'{low}-{high}'
    return f'>={RATIOS[-1]}'


def displays(root, meta):
    """Per staged picture: (start field, kind, shown field or None) from the D2 state."""
    info = meta['states']['stages']
    symbols = {k: int(v, 16) if isinstance(v, str) else v for k, v in meta['symbols'].items()}
    sizes = [size for _, size in info['regions']]
    data = gzip.decompress((root/'stages.bin.gz').read_bytes())
    at = lambda name: symbols[name]-symbols['c2_serial']
    items = []
    for n in range(info['count']):
        slave = data[n*sum(sizes):n*sum(sizes)+sizes[0]]
        items.append((struct.unpack_from('>I', slave, at('d2_start'))[0],
                      struct.unpack_from('>H', slave, at('d2_kind'))[0],
                      struct.unpack_from('>2H', slave, at('d2_leads'))))
    # The lead of a picture is measured when it reaches the screen, before the next
    # picture of either kind is drawn, so the next record holds it.
    return [(start, kind, start + items[n+1][2][kind//2] if n+1 < len(items) else None)
            for n, (start, kind, _) in enumerate(items)]


def poses(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    pictures = []
    result = d3_stage.check(directory, collect=pictures)
    shown = displays(root, meta)
    assert len(shown) == len(pictures)
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
    table = model.table
    body = lambda snap, h, o, f: struct.unpack_from(f, snap, d1.HEADER.size + d3_stage.snapshot_offset(h, o))[0]
    player = body(tick_cur[min(tick_cur)], 0, 0x3a720, '>I')
    records = d1.HEADER.size + sum(size for _, _, size in d1.RANGES)
    field = lambda snap, n, o, f: struct.unpack_from(f, snap, records + n*d1.RECORD + d3_stage.record_offset(o))[0]

    def camera(buffer):
        g = lambda o, f='>h': struct.unpack_from(f, buffer, CAMERA+o)[0]
        return g(0xa, '>l'), g(0xe, '>l'), g(0x14)

    def car(buffer, n, flag, track):
        at = d5_cars.CARS + n*d5_cars.RECORD
        g = lambda o, f='>h': struct.unpack_from(f, buffer, at+o)[0]
        xz = (g(d5_cars.X, '>l'), g(d5_cars.X+4, '>l')) if flag & 1 else d5_cars.position(
            track, table, g(d5_cars.SEG, '>I'), g(6), g(d5_cars.LON))
        return xz + (g(16),)

    readers = {}
    for tick, *_, read, _, _, _ in pictures:
        readers.setdefault(tick, read)
    tracks = {}

    def track_at(tick):
        if tick not in tracks:
            tracks[tick] = d4_camera.Track(root, meta)
            tracks[tick].update(readers[tick], ranges)
        return tracks[tick]

    actual = {}

    def actual_poses(tick):
        """Camera and car poses of a tick from its D1 snapshot, on its own track."""
        if tick not in actual:
            cur = tick_cur.get(tick)
            if cur is None or tick not in readers:
                actual[tick] = None
            else:
                stage = d3_stage.from_snapshot(cur)[0]
                flags = [(field(cur, n, 0x7e, '>B'), field(cur, n, 0x96, '>H')) for n in range(1, 27)]
                state = (tick >> 16, d1.HEADER.unpack_from(cur)[5], body(cur, 1, 0x234, '>Q'), body(cur, 1, 0x23c, '>B'))
                actual[tick] = (camera(stage), [car(stage, n, flags[n][0], track_at(tick)) for n in range(26)],
                                flags, state)
        return actual[tick]

    # One entry per picture: when it shows, what it shows, predicted and at the tick.
    frames = []
    for (tick, alpha, staged, saved, read, decision, outcome, mode), (start, kind, at) in zip(pictures, shown):
        track = track_at(tick)
        code = read(1, 0x23c, 1)[0]
        selected = struct.unpack('>I', read(1, 0x238, 4))[0]
        view = ('replay ' if mode == 2 else '') + d7_views.view_name(code, selected, player)
        state = (tick >> 16, mode, struct.unpack('>Q', read(1, 0x234, 8))[0], code)
        flags = [(read(1, d7_views.CARS_AT + n*0xc0 + 0x7e, 1)[0],
                  struct.unpack('>H', read(1, d7_views.CARS_AT + n*0xc0 + 0x96, 2))[0]) for n in range(26)]
        frames.append(dict(
            tick=tick, alpha=alpha, decision=decision, outcome=outcome, view=view, state=state,
            start=start, shown=at, flags=flags,
            predicted=(camera(staged), [car(staged, n, flags[n][0], track) for n in range(26)]),
            latest=(camera(saved), [car(saved, n, flags[n][0], track) for n in range(26)])))

    histogram, per_view = collections.Counter(), {}
    counts = collections.Counter()
    count = lambda *name: counts.__setitem__('/'.join(name), counts['/'.join(name)]+1)
    values = {}
    add = lambda *path_value: values.setdefault('/'.join(path_value[:-1]), []).append(path_value[-1])
    worst = []
    for a, b in zip(frames, frames[1:]):
        if a['shown'] is None or b['shown'] is None:
            continue
        span = b['shown'] - a['shown']
        if span <= 0:
            count('display order', 'not after the previous picture')
            continue
        # Frame time: how long picture a stays on screen.
        histogram[span] += 1
        per_view.setdefault(a['view'], collections.Counter())[span] += 1
        if a['state'] != b['state']:
            count('pairs', 'view or epoch change')
            continue
        whole = (b['tick'] & 0xffff) + b['alpha'] // 0x4000
        motion_from, motion_to = actual_poses(d3_stage.key(b['tick'] >> 16, whole)), actual_poses(
            d3_stage.key(b['tick'] >> 16, whole+1))
        if not motion_from or not motion_to:
            count('pairs', 'no actual motion (race end)')
            continue
        if motion_from[3] != b['state'] or motion_to[3] != b['state']:
            count('pairs', 'view changes during the reference motion')
            continue
        count('pairs', 'compared')
        snapped = 'snapped' if b['decision'] != 'history' or b['outcome'] == 'jump' else 'predicted'
        interval = 6.25                     # fields per tick, PAL (8 ticks in 50 fields)
        for name in ('predicted', 'latest'):
            label = f'{name}' if name == 'latest' else f'{name} ({snapped})' if snapped == 'snapped' else name
            # Camera.
            (ax, az, ayaw), (bx, bz, byaw) = a[name][0], b[name][0]
            (fx, fz, fyaw), (tx, tz, tyaw) = motion_from[0], motion_to[0]
            step, move = (bx-ax, bz-az), (tx-fx, tz-fz)
            moving = move != (0, 0)
            if moving:
                count(label, 'camera', 'moving pairs')
                dot = step[0]*move[0] + step[1]*move[1]
                length = (move[0]**2 + move[1]**2) ** .5
                along = dot / length
                if step == (0, 0):
                    count(label, 'camera', 'stalled')
                elif dot < 0:
                    count(label, 'camera', 'backwards')
                    add(label, 'camera', 'backwards distance', -along)
                    if name == 'predicted':
                        worst.append((-along, b['tick'], 'camera', a['view'], snapped, span))
                ratio = (along/span) / (length/interval)
                add(label, 'camera', 'evenness', ratio)
                add(label, 'camera', 'evenness by view', a['view'], ratio)
                counts[f'{label}/camera/evenness bins/{ratio_bin(ratio)}'] += 1
            rate = signed(tyaw-fyaw)
            if abs(rate) >= TURN:
                count(label, 'camera', 'turning pairs')
                yaw_step = signed(byaw-ayaw)
                if yaw_step == 0:
                    count(label, 'camera', 'yaw stalled')
                elif (yaw_step < 0) != (rate < 0):
                    count(label, 'camera', 'yaw backwards')
                    add(label, 'camera', 'yaw backwards angle', abs(yaw_step))
            # Cars whose pose flag and status stay the same over the two pictures and the motion.
            for n in range(26):
                flag = a['flags'][n]
                if b['flags'][n] != flag or motion_from[2][n] != flag or motion_to[2][n] != flag or flag[1] & 0x8000:
                    count(label, 'cars', 'not comparable')
                    continue
                (ax, az, ayaw), (bx, bz, byaw) = a[name][1][n], b[name][1][n]
                (fx, fz, _), (tx, tz, _) = motion_from[1][n], motion_to[1][n]
                step, move = (bx-ax, bz-az), (tx-fx, tz-fz)
                if move == (0, 0):
                    continue
                count(label, 'cars', 'moving pairs')
                dot = step[0]*move[0] + step[1]*move[1]
                length = (move[0]**2 + move[1]**2) ** .5
                along = dot / length
                if step == (0, 0):
                    count(label, 'cars', 'stalled')
                elif dot < 0 and snapped == 'snapped' and name == 'predicted':
                    count(label, 'cars', 'backwards')
                    add(label, 'cars', 'backwards distance', -along)
                    worst.append((-along, b['tick'], f'car {n+1}', a['view'], snapped, span))
                elif dot < 0:
                    count(label, 'cars', 'backwards')
                    add(label, 'cars', 'backwards distance', -along)
                    if name == 'predicted':
                        held = 'held at b' if b['predicted'][1][n] == b['latest'][1][n] else \
                            'held at a' if a['predicted'][1][n] == a['latest'][1][n] else 'both predicted'
                        count(label, 'cars', 'backwards', held)
                        if b['tick'] >> 16 == 3 and PIT[0] <= b['tick'] & 0xffff <= PIT[1]:
                            count(label, 'cars', 'backwards', 'pit stops on')
                        worst.append((-along, b['tick'], f'car {n+1}', a['view'], f'{snapped}, {held}', span))
                ratio = (along/span) / (length/interval)
                add(label, 'cars', 'evenness', ratio)
                counts[f'{label}/cars/evenness bins/{ratio_bin(ratio)}'] += 1
    worst.sort(reverse=True)
    return dict(
        check=result['status'], failure_count=result['failure_count'], pictures=len(frames),
        decisions=result['decisions'], camera_outcomes=result['camera']['outcomes'],
        cars={k: result['cars'][k] for k in ('predicted', 'held', 'moved', 'reasons')},
        frame_fields=dict(all=dict(sorted(histogram.items())),
                          mean=round(sum(k*v for k, v in histogram.items())/sum(histogram.values()), 3),
                          by_view={v: dict(sorted(h.items())) for v, h in sorted(per_view.items())},
                          mean_by_view={v: round(sum(k*c for k, c in h.items())/sum(h.values()), 3)
                                        for v, h in sorted(per_view.items())}),
        counts=dict(sorted(counts.items())),
        values={name: quantiles(v) for name, v in sorted(values.items())},
        worst=[dict(distance=round(d), epoch=t >> 16, tick=t & 0xffff, item=i, view=v, decision=s, fields=f)
               for d, t, i, v, s, f in worst[:20]],
        backwards=sorted(((round(d), t >> 16, t & 0xffff, i, v, s, f) for d, t, i, v, s, f in worst), key=lambda w: (w[1], w[2])))


def shots(directory):
    """Fields between changes of the shown picture, from one screenshot per field."""
    from PIL import Image, ImageChops
    files = sorted(Path(directory).glob('field-*.png'))
    images = [Image.open(f).convert('RGB') for f in files]
    digests = [hashlib.sha256(i.tobytes()).hexdigest() for i in images]
    changes = [n for n in range(1, len(images)) if digests[n] != digests[n-1]]
    spans = collections.Counter(b-a for a, b in zip(changes, changes[1:]))
    boxes = collections.Counter()
    for n in changes:
        box = ImageChops.difference(images[n], images[n-1]).getbbox()
        boxes['view' if box and box[3]-box[1] > 40 else 'small'] += 1
    meta = json.loads((Path(directory)/'meta.json').read_text())
    # The slave's picture counter after each field: pictures submitted in the window.
    start, size = meta['shot_region']
    data = gzip.decompress((Path(directory)/'fields.bin.gz').read_bytes())
    at = meta['symbols']['c2_pictures']
    at = (int(at, 16) if isinstance(at, str) else at) - start
    pictures = [struct.unpack_from('>I', data, n*size + at)[0] for n in range(len(images))]
    return dict(fields=len(images), changes=len(changes), spans=dict(sorted(spans.items())),
                pictures_in_window=pictures[-1]-pictures[0],
                changes_per_picture=round(len(changes)/(pictures[-1]-pictures[0]), 3),
                mean=round((changes[-1]-changes[0])/(len(changes)-1), 3) if len(changes) > 1 else None,
                change_areas=dict(boxes), view_code=meta.get('view_code'),
                whd_args=meta['whd_args'], tick=meta['clock']['completed'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', nargs='?')
    parser.add_argument('--shots', nargs='*', default=[], metavar='NAME=DIR')
    parser.add_argument('--out')
    args = parser.parse_args()
    out = {}
    if args.capture:
        out['poses'] = poses(args.capture)
    out['shots'] = {name: shots(path) for name, path in (s.split('=', 1) for s in args.shots)}
    text = json.dumps(out, indent=2)+'\n'
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(text)
    print(text)
