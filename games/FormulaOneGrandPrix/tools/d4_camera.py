#!/usr/bin/env python3
"""D4 predicted camera: the model of d4_camera and the per-picture check.

  d4_camera.py CAPTURE [--out tmp/...json] [--negative]

CAPTURE is a c2_capture --states --stage directory of a build with D4. For a picture
with a usable history (D3) and alpha above 0, the slave extrapolates the published
camera, cur + (cur - history) * alpha: direction, pitch, height and yaw as wrapped
words, world X/Z as longs. The reduced and coarse X/Z follow as in h0+$33F32; the road
anchor comes from the game's segment search h0+$26406 started at the tick's anchor;
the yaw coefficients (h0+$3409E), horizon (+$3404C) and viewport (+$33F6E) are
recomputed. Lateral offset and lap segment stay at the tick (d5_cars.py: the cars). A camera
that moved D4_JUMP or more in X or Z snaps. This module rebuilds all of it from the
saved bytes, the D1 history and the track dumped at the end of the race, and runs the
D3 check with it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_disabled import relocated_original   # noqa: E402

JUMP = 0x100000
CAMERA = 4                       # published camera in the packed stage globals
WORDS = (0, 2, 6, 0x14)          # direction, pitch, height, yaw
LONGS = (0xa, 0xe)               # world X, Z
TRACK_H1 = 0x2bfa                # pit and alternate segments, then the track at +$53DE
MAIN = 0x53de
SEGMENT = 0x2e
POINTERS = (0x1fab8, 0x30)       # h2: pit flag +$1FABA, end/length/alternates +$1FAC2–1FAE5


def dump_track(command, out, bases):
    """At the end of the race: h2 wrap pointers, then h1 from the pit segments to the end."""
    pointers = out/'track-h2.bin'
    command('gdb', f'dump binary memory {pointers} {bases[2]+POINTERS[0]:#x} '
                   f'{bases[2]+POINTERS[0]+POINTERS[1]:#x}')
    end = struct.unpack_from('>I', pointers.read_bytes(), 0x1fac2-POINTERS[0])[0]
    track = out/'track-h1.bin'
    command('gdb', f'dump binary memory {track} {bases[1]+TRACK_H1:#x} {end+SEGMENT:#x}')
    return dict(h1=[TRACK_H1, end+SEGMENT-bases[1]-TRACK_H1], h2=list(POINTERS),
                sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (track, pointers)})


def signed(value, bits=16):
    value &= (1 << bits)-1
    return value - (1 << bits) if value >> (bits-1) else value


def scale(delta, alpha):
    """delta * alpha >> 14 towards zero, as d4_scale."""
    magnitude = (abs(delta)*alpha) >> 14
    return -magnitude if delta < 0 else magnitude


class Track:
    def __init__(self, root, meta):
        info = meta['states']['track']
        for name, digest in info['sha256'].items():
            assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, name
        self.h1 = meta['hunk_bases'][1]
        self.data = (root/'track-h1.bin').read_bytes()
        self.pointers = (root/'track-h2.bin').read_bytes()

    def pointer(self, offset):
        return struct.unpack_from('>I', self.pointers, offset-POINTERS[0])[0]

    def pit(self):
        return self.pointers[0x1faba-POINTERS[0]] & 0x80

    def word(self, segment, offset):
        return struct.unpack_from('>h', self.data, segment-self.h1-TRACK_H1+offset)[0]

    def marked(self, segment):
        return self.data[segment-self.h1-TRACK_H1+0x1f] & 8

    def project(self, segment, x, z):
        """h0+$2651E: the coarse point along the segment's direction from its start."""
        d4 = signed(x - self.word(segment, 4))
        d5 = signed(z - self.word(segment, 8))
        return (self.word(segment, 0xc) >> 6)*d5 + (self.word(segment, 0xe) >> 6)*d4

    def forward(self, segment):  # h0+$2679A, after the step
        if segment == self.pointer(0x1fac2):
            return self.h1+MAIN
        if segment == self.pointer(0x1fad6):
            return self.pointer(0x1fae2)
        if segment == self.pointer(0x1fade) and self.pit():
            return self.h1+TRACK_H1
        return segment

    def back(self, segment):     # h0+$267DA, including the step
        if segment == self.h1+MAIN:
            return self.pointer(0x1fac2)-SEGMENT
        if segment == self.h1+TRACK_H1:
            return self.pointer(0x1fade)-SEGMENT
        if segment == self.pointer(0x1fae2) and self.pit():
            segment = self.pointer(0x1fad6)
        return segment-SEGMENT

    def step_back(self, segment):
        return self.back(segment) if self.marked(segment) else segment-SEGMENT

    def search(self, segment, wx, wz):
        """h0+$26406 from SEGMENT for world X/Z."""
        x, z = signed(wx >> 11), signed(wz >> 11)
        if self.project(segment, x, z) >= 0:
            while True:
                segment += SEGMENT
                if self.marked(segment):
                    segment = self.forward(segment)
                if self.project(segment, x, z) < 0:
                    return self.step_back(segment)
        while True:
            segment = self.step_back(segment)
            if self.project(segment, x, z) >= 0:
                return segment


class Model:
    def __init__(self, root, meta):
        hunks = relocated_original(meta['hunk_bases'])
        self.table = hunks[0][0x222f0:0x222f0+0x2004]
        self.track = Track(root, meta)

    def lookup(self, angle):
        angle &= 0xffff
        if angle & 0x8000:
            angle = -angle & 0xffff
        return struct.unpack_from('>h', self.table, (angle >> 2) & ~1)[0]

    def derive(self, buffer, spring, clamp, view):
        """Coefficients, horizon and viewport into the packed globals, as d4_derive."""
        w = lambda o: struct.unpack_from('>h', buffer, o)[0]
        yaw, pitch, heading = w(CAMERA+0x14), w(CAMERA+2), w(CAMERA+0x26)
        struct.pack_into('>hh', buffer, 44, self.lookup(yaw), self.lookup(0x4000-yaw))
        total = pitch + (spring if view == 0 else 0)
        horizon = signed((self.lookup(0x4000-total) >> 6) + 0x50)
        struct.pack_into('>h', buffer, 48, min(horizon, clamp))
        relative, flag = (heading-yaw) & 0xffff, 0
        if relative & 0x8000:
            relative = -relative & 0xffff
        if relative >= 0x4000:
            relative, flag = (0x8000-relative) & 0xffff, 0x8000
        struct.pack_into('>HH', buffer, 50, flag, relative)

    def predict(self, saved, history, alpha, spring, clamp, view):
        """(staged bytes, outcome): outcome is 'jump', 'moved', 'held' or 'same'."""
        out = bytearray(saved)
        L = lambda b, o: struct.unpack_from('>l', b, o)[0]
        W = lambda b, o: struct.unpack_from('>h', b, o)[0]
        base = CAMERA
        if any(abs(L(saved, base+o)-L(history, o)) >= JUMP for o in LONGS):
            return bytes(saved), 'jump'
        for o in WORDS:
            delta = signed(W(saved, base+o)-W(history, o))
            struct.pack_into('>H', out, base+o, (W(saved, base+o)+scale(delta, alpha)) & 0xffff)
        for o in LONGS:
            struct.pack_into('>l', out, base+o, L(saved, base+o)+scale(L(saved, base+o)-L(history, o), alpha))
        for o, reduced, coarse in ((0xa, 0x18, 4), (0xe, 0x20, 8)):
            value = L(out, base+o) >> 8
            struct.pack_into('>l', out, base+reduced, value)
            struct.pack_into('>H', out, base+coarse, (value >> 3) & 0xffff)
        anchor = struct.unpack_from('>I', saved, 0)[0]
        found = self.track.search(anchor, L(out, base+0xa), L(out, base+0xe))
        if found < self.track.h1+MAIN:
            outcome = 'held'
        else:
            outcome = 'moved' if found != anchor else 'same'
            struct.pack_into('>I', out, 0, found)
            struct.pack_into('>h', out, base+0x26, self.track.word(found, 0))
        self.derive(out, spring, clamp, view)
        return bytes(out), outcome


def error(shown, tick_cur):
    """Each predicted picture against the ideal camera at its displayed time, tick +
    alpha, interpolated between the actual published cameras of the ticks around it;
    beside the error of showing the tick itself. Position is the larger of the X/Z
    errors in world units, yaw in angle units ($10000 a turn)."""
    def camera(buffer, at):
        return [struct.unpack_from('>l', buffer, at+0xa)[0], struct.unpack_from('>l', buffer, at+0xe)[0],
                struct.unpack_from('>h', buffer, at+0x14)[0]]
    from d3_stage import snapshot_offset
    import d1_snapshot as d1
    at = d1.HEADER.size + snapshot_offset(0, 0x3a7f8)
    out = {name: [] for name in ('predicted_position', 'latest_position', 'predicted_yaw', 'latest_yaw')}
    for tick, alpha, staged, saved in shown:
        whole, fraction = divmod(alpha, 0x4000)
        ends = [tick_cur.get(tick+whole), tick_cur.get(tick+whole+1)]
        if None in ends:
            continue
        a, b = camera(ends[0], at), camera(ends[1], at)
        yaw = a[2] + signed(b[2]-a[2])*fraction/0x4000
        ideal = [a[0]+(b[0]-a[0])*fraction/0x4000, a[1]+(b[1]-a[1])*fraction/0x4000]
        for name, buffer in (('predicted', staged), ('latest', saved)):
            value = camera(buffer, CAMERA)
            out[name+'_position'].append(max(abs(value[0]-ideal[0]), abs(value[1]-ideal[1])))
            out[name+'_yaw'].append(abs(signed(round(value[2]-yaw))))
    summary = {}
    for name, values in out.items():
        values.sort()
        if values:
            summary[name] = dict(p50=round(values[len(values)//2]), p95=round(values[len(values)*95//100]),
                                 max=round(values[-1]))
    summary['pictures'] = len(out['latest_yaw'])
    return summary


def main():
    import d3_stage
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--out')
    parser.add_argument('--negative', action='store_true')
    args = parser.parse_args()
    result = d3_stage.check(args.capture)
    if args.negative:
        result['negative'] = d3_stage.negative(args.capture, camera=True)
        if any(v != 'FAIL' for v in result['negative'].values()):
            result['status'] = 'FAIL'
    text = json.dumps(result, indent=2)+'\n'
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
