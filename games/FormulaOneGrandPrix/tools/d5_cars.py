#!/usr/bin/env python3
"""D5 predicted cars: the model of d5_cars and the per-picture check.

  d5_cars.py CAPTURE [--out tmp/...json] [--negative]

CAPTURE is a c2_capture --states --stage directory of a build with D5. For a picture
whose camera D4 predicted, each of the 26 car records is interpolated, cur - (cur -
history) * weight (D10). A track-driven car (+$7E bit 0 clear) advances along its segments:
its progress is the fraction +$1E (Q14) plus $4000 per segment stepped from the
history's segment to cur's, the interpolated progress is placed by stepping again from
the history's segment, and the corrected longitudinal +$1C follows from the fraction with cur's
denominator +$16. Segments step as the native traversal does through h0+$26626 (lap
wrap, pit branch and join points). A car whose history-to-cur step goes into or out
of the pit lane is held; a predicted step that would do so stops at the end of the
segment before it (D9).
An explicit car's world X/Z are interpolated and its segment found by the game's search
h0+$26406. Both interpolate pitch, height, lateral, yaw, correction and height offset
as words. A car whose pose flag changed (collisions) advances along its segments too,
since explicit cars keep their track coordinates, and is drawn track-driven (the slave's
d5_track mask). A car whose status +$96 changed, that jumped, that crosses more
than D5_STEPS segments, or that would stand before its segment (fractions are signed; a
grid car stands slightly before its segment) keeps the tick's pose. This module rebuilds all of it and runs
the D3/D4 check with it.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d3_stage import GLOBALS                                  # noqa: E402
from d4_camera import JUMP, MAIN, SEGMENT, scale, signed   # noqa: E402

STEPS = 3
COUNTERS = ('d5_predicted', 'd5_held', 'd5_moved')
RECORD = 38                      # staged bytes per record
CARS = GLOBALS + RECORD          # first car in the packed stage set (after the synthetic camera)
# (staged offset, record offset): pitch, height, lateral, yaw, correction, height offset.
WORDS = ((2, 0x04), (4, 0x08), (6, 0x0a), (16, 0x1a), (34, 0x4a), (36, 0x8c))
SEG, DEN, LON, FRACTION, X = 10, 14, 18, 20, 24     # staged offsets of +$12, +$16, +$1C, +$1E, +$28


class Cars:
    def __init__(self, model):
        self.model = model
        self.track = model.track
        self.reasons = {}

    def step(self, segment, flags):
        """h0+$26626 after the traversal's step; None where it would change pit state."""
        track = self.track
        segment += SEGMENT
        if not track.marked(segment):
            return segment
        if segment == track.pointer(0x1fac2):
            return track.h1 + MAIN
        if track.pit():
            return None
        if segment == track.pointer(0x1fade):
            return None if flags & 0x80 else segment
        if segment == track.pointer(0x1fad6):
            return None if flags & 0x20 else track.pointer(0x1fae2)
        return segment

    def predict(self, out, history_record, game, weight):
        """Predict the staged cars in OUT in place; returns (predicted, held, moved)."""
        import d1_snapshot as d1
        from d3_stage import record_offset
        counts = [0, 0, 0]
        self.drawn = 0          # bit n: car n explicit at cur, drawn track-driven after a pose flag change
        for n, record in enumerate(d1.RECORDS[1:]):
            staged = CARS + n*RECORD
            hist = history_record(n+1)
            H = lambda o, size=2: hist[record_offset(o):record_offset(o)+size]
            hw = lambda o: struct.unpack_from('>h', H(o), 0)[0]
            hl = lambda o: struct.unpack_from('>l', H(o, 4), 0)[0]
            sw = lambda o: struct.unpack_from('>h', out, staged+o)[0]
            sl = lambda o: struct.unpack_from('>l', out, staged+o)[0]
            explicit = game(1, record+0x7e, 1)[0] & 1
            flags = game(1, record+0x23, 1)[0]
            def hold(reason):
                counts[1] += 1
                self.reasons[reason] = self.reasons.get(reason, 0) + 1
            flipped = (explicit ^ H(0x7e, 1)[0]) & 1
            if game(1, record+0x96, 2) != H(0x96):
                hold('status')
                continue
            cur_segment = sl(SEG) & 0xffffffff
            if flipped or not explicit:
                segment, progress = hl(0x12) & 0xffffffff, 0
                for _ in range(STEPS+1):
                    if segment == cur_segment:
                        break
                    segment = self.step(segment, flags)
                    if segment is None:
                        break
                    progress += 0x4000
                else:
                    segment = None
                if segment != cur_segment:
                    hold('segments')
                    continue
                fraction = sw(FRACTION)      # signed: a grid car can stand before its segment
                moved = progress + fraction - hw(0x1e)
                # D10: from the start of the history's segment, interpolated towards cur.
                progress = hw(0x1e) + moved + scale(moved, weight)
                segment, steps = hl(0x12) & 0xffffffff, 0
                while progress >= 0x4000:
                    if steps == 2*STEPS:
                        segment = None
                        break
                    following = self.step(segment, flags)
                    if following is None:
                        # D9: stop at the end of the segment before a pit change, so a
                        # car predicted towards it never goes back to the tick's pose.
                        progress = 0x3fff
                        self.reasons['stopped before a pit change'] = self.reasons.get(
                            'stopped before a pit change', 0) + 1
                        break
                    segment, progress, steps = following, progress - 0x4000, steps + 1
                if segment is None or progress < 0:
                    hold('before segment' if progress < 0 else 'segments')
                    continue
                lon = (((progress - 0x4000) * sw(DEN)) >> 14) + 0x400
                struct.pack_into('>hH', out, staged+LON, signed(lon), progress)
                if flipped and explicit:    # cur explicit: drawn track-driven
                    self.drawn |= 1 << n
            else:
                if any(abs(sl(X+o) - hl(0x28+o)) >= JUMP for o in (0, 4)):
                    hold('jump')
                    continue
                for o in (0, 4):
                    struct.pack_into('>l', out, staged+X+o, sl(X+o) + scale(sl(X+o) - hl(0x28+o), weight))
                segment = self.track.search(cur_segment, sl(X), sl(X+4))
            if segment != cur_segment:
                struct.pack_into('>I', out, staged+SEG, segment)
                counts[2] += 1
            for at, o in WORDS:
                delta = signed(sw(at) - hw(o))
                struct.pack_into('>H', out, staged+at, (sw(at) + scale(delta, weight)) & 0xffff)
            counts[0] += 1
        return counts


def interpolated(table, angle):
    """h0+$25648: the sine table at |ANGLE| with the low three bits interpolated."""
    angle &= 0xffff
    if angle & 0x8000:
        angle = -angle & 0xffff
    at = (angle >> 2) & ~1
    low, high = (struct.unpack_from('>h', table, at+o)[0] for o in (0, 2))
    return signed(low + ((signed(high-low)*(angle & 7)) >> 3))


def position(track, table, segment, lateral, longitudinal):
    """h0+$26286: world X/Z of a track-driven pose."""
    w = lambda o: track.word(segment, o)
    along = longitudinal
    if w(0x14):
        along = signed(longitudinal - signed(((w(0x14)*lateral) << 1) >> 16))
    sine, cosine = interpolated(table, w(0)), interpolated(table, 0x4000-w(0))
    z = signed((along*sine - lateral*cosine) << 2 >> 16)
    x = signed((lateral*sine + along*cosine) << 2 >> 16)
    low = track.data[segment-track.h1+0x21-0x2bfa]
    x += (w(4) << 3) | (low & 7)
    z += (w(8) << 3) | (low >> 4)
    return x << 8, z << 8


def error(shown, tick_cur, cars):
    """Each drawn car of each predicted picture against its ideal pose at the displayed
    time minus the delay, tick - weight, interpolated between the actual poses of the ticks around it;
    beside the error of showing the tick. Position is the larger of the X/Z errors in
    world units, yaw (+$1A) in angle units. A car whose pose flag or status changes
    between those ticks, or that jumps, has no ideal and is left out."""
    import d1_snapshot as d1
    from d3_stage import record_offset
    track, table = cars.track, cars.model.table
    records = d1.HEADER.size + sum(size for _, _, size in d1.RANGES)

    def pose(flag, segment, lateral, longitudinal, x, z, yaw):
        if flag & 1:
            return x, z, yaw
        return position(track, table, segment, lateral, longitudinal) + (yaw,)

    def actual(snap, n):
        rec = snap[records+(n+1)*d1.RECORD:records+(n+2)*d1.RECORD]
        g = lambda o, f='>h': struct.unpack_from(f, rec, record_offset(o))[0]
        return (rec[record_offset(0x7e)], g(0x96, '>H')), pose(
            rec[record_offset(0x7e)], g(0x12, '>I'), g(0x0a), g(0x1c), g(0x28, '>l'), g(0x2c, '>l'), g(0x1a))

    def staged(buffer, flag, n):
        at = CARS + n*RECORD
        g = lambda o, f='>h': struct.unpack_from(f, buffer, at+o)[0]
        return pose(flag, g(SEG, '>I'), g(6), g(LON), g(X, '>l'), g(X+4, '>l'), g(16))

    out = {name: [] for name in ('predicted_position', 'latest_position', 'predicted_yaw', 'latest_yaw')}
    for tick, weight, staged_bytes, saved in shown:
        whole, fraction = divmod(-weight, 0x4000)
        ends = [tick_cur.get(tick+whole), tick_cur.get(tick+whole+1), tick_cur.get(tick)]
        if None in ends:
            continue
        for n in range(26):
            (state_a, a), (state_b, b), (state, _) = (actual(end, n) for end in ends)
            if state_a != state_b or state_a != state or state[1] & 0x8000:
                continue
            if max(abs(b[0]-a[0]), abs(b[1]-a[1])) >= JUMP:
                continue
            ideal = [a[i]+(b[i]-a[i])*fraction/0x4000 for i in (0, 1)]
            yaw = a[2] + signed(b[2]-a[2])*fraction/0x4000
            for name, buffer in (('predicted', staged_bytes), ('latest', saved)):
                value = staged(buffer, state[0], n)
                out[name+'_position'].append(max(abs(value[0]-ideal[0]), abs(value[1]-ideal[1])))
                out[name+'_yaw'].append(abs(signed(round(value[2]-yaw))))
    summary = {}
    for name, values in out.items():
        values.sort()
        if values:
            summary[name] = dict(p50=round(values[len(values)//2]), p95=round(values[len(values)*95//100]),
                                 max=round(values[-1]))
    summary['cars'] = len(out['latest_yaw'])
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
        result['negative'] = d3_stage.negative(args.capture, camera=True, cars=True)
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
