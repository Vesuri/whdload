#!/usr/bin/env python3
"""D7 every view: the model of d7_aim, and the D3–D5 check broken down by view.

  d7_views.py CAPTURE [--out tmp/...json]

In an external view (pose source the synthetic camera h1+$256) the slave places the
staged camera from the staged viewed car h1+$238, as the native view code does in the
tick. Chase (view bit 5, h0+$398AA): the camera stands the distance h0+$3A90C from the
car's world position along the chase heading h0+$3A710, turned by $8000 in front chase
(bit 4); the heading is extrapolated like the camera words. TV (h0+$39BD0): the camera
stays where D4 put it. Both aim the direction and yaw at the car with the game's atan
h0+$256B6 (h0+$39CBE). The cockpit views and a TV camera on a track point (h1+$240
nonzero) keep D4's camera. This module rebuilds that, and checks that the same
placement from the tick's own car and heading gives the game's camera.

CAPTURE is a c2_capture --states --stage --views directory. The check is d5_cars.py's;
its pictures are then grouped by the view at the draw: cockpit (the player's car),
onboard (the cockpit of another car), TV, rear chase and front chase. Per view the
camera and car errors are d4_camera.py's and d5_cars.py's. In the external views the
viewed car is what the camera is aimed at, so its bearing from the camera relative to
the camera's yaw is where it appears across the screen: the bearing error is the
staged bearing against the ideal one (camera and car at the time shown, tick -
weight, interpolated between the actual ticks), in angle units ($10000 a turn), beside
the error of showing the tick.
"""
import argparse
import gzip
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d1_snapshot as d1                                       # noqa: E402
import d3_stage                                                # noqa: E402
import d4_camera                                               # noqa: E402
import d5_cars                                                 # noqa: E402
from d4_camera import CAMERA, JUMP, scale, signed              # noqa: E402

CARS_AT = 0x5d6
COUNTERS = ('d7_aimed', 'd7_faults')
ATAN = 0x242f4                   # h0: the atan table of h0+$256B6, 2049 words


class Aim:
    def __init__(self, model, meta):
        from check_disabled import relocated_original
        self.model = model
        self.h1 = meta['hunk_bases'][1]
        self.atan_table = relocated_original(meta['hunk_bases'])[0][ATAN:ATAN+0x1002]
        self.tick_differs = False

    def atan(self, dx, dz):
        """h0+$256B6 for coarse word deltas."""
        a, b = signed(abs(dx)), signed(abs(dz))
        entry = lambda q: struct.unpack_from('>h', self.atan_table, signed(q*2))[0]
        if a >= b:
            if not a:
                return 0
            angle = 0x4000 - entry(((b << 11) & 0xffffffff) // (a & 0xffff))
        else:
            angle = entry(((a << 11) & 0xffffffff) // (b & 0xffff))
        if signed(dx ^ dz) < 0:
            angle = -angle
        if dz < 0:
            angle += 0x8000
        return angle & 0xffff

    def place(self, car, heading, camera, code, distance):
        """h0+$3990C's placement in chase, then h0+$39CBE's aim: (X, Z, yaw)."""
        x, z = camera
        if code & 0x20:
            h = (heading + (0x8000 if code & 0x10 else 0)) & 0xffff
            z = car[1] + ((self.model.lookup(h)*distance) >> 6)
            x = car[0] + ((self.model.lookup(0x4000-h)*distance) >> 6)
        return x, z, self.atan(signed((car[0]-x) >> 11), signed((car[1]-z) >> 11))

    def predict(self, out, saved, history, read, weight, drawn=0):
        """Place OUT's camera from its predicted viewed car; returns 1 if placed. DRAWN:
        the cars D5 draws track-driven (bit n = car n)."""
        self.tick_differs = False
        u32 = lambda b: struct.unpack('>I', b)[0]
        s16 = lambda b: struct.unpack('>h', b)[0]
        if u32(read(1, 0x234, 4)) != self.h1+0x256:
            return 0
        code = read(1, 0x23c, 1)[0]
        if not code & 0x20 and s16(read(1, 0x240, 2)):
            return 0
        heading, distance = struct.unpack('>H', read(0, 0x3a710, 2))[0], s16(read(0, 0x3a90c, 2))
        record = u32(read(1, 0x238, 4)) - self.h1
        flag = read(1, record+0x7e, 1)[0]
        track, table = self.model.track, self.model.table

        def pose(segment, lateral, longitudinal, x, z):
            return (x, z) if flag & 1 else d5_cars.position(track, table, segment, lateral, longitudinal)

        def camera(buffer):
            return struct.unpack_from('>l', buffer, CAMERA+0xa)[0], struct.unpack_from('>l', buffer, CAMERA+0xe)[0]
        car = pose(u32(read(1, record+0x12, 4)), s16(read(1, record+0xa, 2)), s16(read(1, record+0x1c, 2)),
                   struct.unpack('>l', read(1, record+0x28, 4))[0], struct.unpack('>l', read(1, record+0x2c, 4))[0])
        x, z, yaw = self.place(car, heading, camera(saved), code, distance)
        if ((x, z) != camera(saved) or struct.unpack_from('>H', saved, CAMERA+0x14)[0] != yaw
                or struct.unpack_from('>H', saved, CAMERA)[0] != yaw):
            self.tick_differs = True
        past = struct.unpack_from('>h', history, d1.HEADER.size + d3_stage.snapshot_offset(0, 0x3a710))[0]
        heading = (heading + scale(signed(heading-past), weight)) & 0xffff
        at = d5_cars.CARS + (record-CARS_AT)//0xc0*d5_cars.RECORD
        g = lambda o, f='>h': struct.unpack_from(f, out, at+o)[0]
        flag ^= drawn >> (record-CARS_AT)//0xc0 & 1
        car = pose(g(d5_cars.SEG, '>I'), g(6), g(d5_cars.LON), g(d5_cars.X, '>l'), g(d5_cars.X+4, '>l'))
        x, z, yaw = self.place(car, heading, camera(out), code, distance)
        struct.pack_into('>ll', out, CAMERA+0xa, x, z)
        struct.pack_into('>H', out, CAMERA, yaw)
        struct.pack_into('>H', out, CAMERA+0x14, yaw)
        return 1


def view_name(code, selected, player):
    if code & 0x80 and not code & 0x20:
        return 'tv'
    if code & 0x20:
        return 'front chase' if code & 0x10 else 'rear chase'
    return 'cockpit' if selected == player else 'onboard'


def quantiles(values):
    values = sorted(values)
    if not values:
        return None
    return dict(p50=round(values[len(values)//2]), p95=round(values[len(values)*95//100]),
                max=round(values[-1]), n=len(values))


def angle(dx, dz):
    """The native yaw of a direction: h0+$256B6 as h0+$39CBE uses it, in $10000 a turn."""
    return round(math.atan2(dx, dz) * 0x8000 / math.pi) & 0xffff


def measure(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    pictures = []
    result = d3_stage.check(directory, collect=pictures)
    h1 = meta['hunk_bases'][1]
    states = meta['states']
    snaps = gzip.decompress((root/'snapshots.bin.gz').read_bytes())
    sizes = [size for _, size in states['snapshot']['regions']]
    tick_cur = {}
    for n, item in enumerate(states['ticks']):
        at = n*sum(sizes) + sizes[0]
        cur = d1.split(snaps[at:at+sizes[1]])[0]
        tick_cur[d3_stage.key(d1.HEADER.unpack_from(cur)[2], item['tick'])] = cur
    first = tick_cur[min(tick_cur)]
    player = struct.unpack_from('>I', first, d1.HEADER.size + d3_stage.snapshot_offset(0, 0x3a720))[0]
    camera_at = d1.HEADER.size + d3_stage.snapshot_offset(0, 0x3a7f8)
    records = d1.HEADER.size + sum(size for _, _, size in d1.RANGES)
    model = d4_camera.Model(root, meta)
    track, table = model.track, model.table

    def actual_car(snap, n):
        rec = snap[records+(n+1)*d1.RECORD:records+(n+2)*d1.RECORD]
        g = lambda o, f='>h': struct.unpack_from(f, rec, d3_stage.record_offset(o))[0]
        flag = rec[d3_stage.record_offset(0x7e)]
        if flag & 1:
            return flag, (g(0x28, '>l'), g(0x2c, '>l'))
        return flag, d5_cars.position(track, table, g(0x12, '>I'), g(0x0a), g(0x1c))

    def staged_car(buffer, flag, n):
        at = d5_cars.CARS + n*d5_cars.RECORD
        g = lambda o, f='>h': struct.unpack_from(f, buffer, at+o)[0]
        if flag & 1:
            return g(d5_cars.X, '>l'), g(d5_cars.X+4, '>l')
        return d5_cars.position(track, table, g(d5_cars.SEG, '>I'), g(6), g(d5_cars.LON))

    def camera(buffer, at):
        return (struct.unpack_from('>l', buffer, at+0xa)[0], struct.unpack_from('>l', buffer, at+0xe)[0],
                struct.unpack_from('>H', buffer, at+0x14)[0])

    views = {}
    for tick, weight, staged, saved, read, decision, outcome, mode in pictures:
        code = read(1, 0x23c, 1)[0]
        selected = struct.unpack_from('>I', read(1, 0x238, 4))[0]
        name = ('replay ' if mode == 2 else '') + view_name(code, selected, player)
        v = views.setdefault(name, dict(pictures=0, decisions={}, bearing={'predicted': [], 'latest': []}, aim=[],
                                        shown=[]))
        v['pictures'] += 1
        key = outcome or decision
        v['decisions'][key] = v['decisions'].get(key, 0) + 1
        if outcome not in ('moved', 'same', 'held'):
            continue
        v['shown'].append((tick, weight, staged, saved))
        if name.endswith(('cockpit', 'onboard')):
            continue
        whole, fraction = divmod(-weight, 0x4000)
        ends = [tick_cur.get(tick+whole), tick_cur.get(tick+whole+1)]
        if None in ends:
            continue
        n = (selected - h1 - CARS_AT) // 0xc0
        (fa, ca), (fb, cb) = (actual_car(end, n) for end in ends)
        a, b = camera(ends[0], camera_at), camera(ends[1], camera_at)
        if fa != fb or max(abs(cb[0]-ca[0]), abs(cb[1]-ca[1]), abs(b[0]-a[0]), abs(b[1]-a[1])) >= JUMP:
            continue
        mix = lambda p, q: p + (q-p)*fraction/0x4000
        car = (mix(ca[0], cb[0]), mix(ca[1], cb[1]))
        yaw = a[2] + signed(b[2]-a[2])*fraction/0x4000
        ideal = signed(round(angle(car[0]-mix(a[0], b[0]), car[1]-mix(a[1], b[1])) - yaw))
        for kind, buffer in (('predicted', staged), ('latest', saved)):
            x, z, y = camera(buffer, CAMERA)
            cx, cz = staged_car(buffer, fa, n)
            bearing = signed(angle(cx-x, cz-z) - y)
            v['bearing'][kind].append(abs(signed(bearing - ideal)))
            if kind == 'latest':
                v['aim'].append(abs(bearing))   # the native aim at the tick: about 0
    out = dict(status=result['status'], failure_count=result['failure_count'], problems=result['problems'],
               failures=result['failures'][:5], views={})
    for name, v in views.items():
        out['views'][name] = dict(
            pictures=v['pictures'], decisions=v['decisions'],
            camera=d4_camera.error(v['shown'], tick_cur),
            cars=d5_cars.error(v['shown'], tick_cur, d5_cars.Cars(model)),
            bearing=dict({k: quantiles(b) for k, b in v['bearing'].items()}, aim_at_tick=quantiles(v['aim']))
            if not name.endswith(('cockpit', 'onboard')) else None)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--out')
    parser.add_argument('--negative', action='store_true')
    args = parser.parse_args()
    result = measure(args.capture)
    if args.negative:
        result['negative'] = d3_stage.negative(args.capture, camera=True, cars=True, aim=True)
        if any(v != 'FAIL' for v in result['negative'].values()):
            result['status'] = 'FAIL'
    text = json.dumps(result, indent=2)+'\n'
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(text)
    print(text)
