"""Try brake mappings for HardDrivinHandling.s offline (plan step H1).

brake_sim.py ROOT [--torque T] [--old]

Replays the brake runs of an Amiga CUSTOM1=2 matrix (tmp/prof/ROOT, from
run_feel.py) through handling_fx.FxCar: each field gets the recorded native
velocity and mouse X, and the brake while the plan holds it, as the module
would. The longitudinal force
is the module's: 295 lb per eighth gained per field, limited to drive 2115 /
coast 705. With the brake on, --old passes the native force (limited to
2470 lb) as both the total force and the brake torque (plan step G); otherwise
the brake torque is -T lb ft and the total force the brake's force at the
road, faded like the brake and at most what a locked front wheel gives
(2604 lb), so the rear wheels get no torque. Prints C1e's
largest yaw change in 1 s and C1f's largest yaw rate from the model's own yaw
rate, next to the arcade's values.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amiga_units as au      # noqa: E402
import handling_fx as hf      # noqa: E402

PROF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../tmp/prof')
REC = 80
ARCADE = {'c1e-mid-brake': 133, 'c1e-lim-brake': 82.8, 'c1e-mid-lift': 13.3, 'c1e-lim-lift': 19.7,
          'c1f-60-brake': 6.1, 'c1f-90-brake': 10.5}
FX_LOCK = 2604        # lb, what a locked front wheel gives: 1.2 * 1762.5 / (1 - 1.2 * 0.1567)
DEG_S = 180 / 3.141592653589793 / (1 << 27)


def fade(u):
    a = abs(u)
    return 0 if a < 128 else ((a * 13107) >> 10 if a < 640 else 16384)


def run(path, torque, old):
    b = open(os.path.join(path, 'rec.bin'), 'rb').read()
    car, prev, out = hf.FxCar(), None, []
    for i in range(0, len(b), REC):
        v = struct.unpack_from('>h', b, i + 22)[0]
        brake = struct.unpack_from('>h', b, i + 34)[0] == 5     # the plan holds the brake
        mouse = struct.unpack_from('>h', b, i + 32)[0]
        v8 = max(-4160, min(4160, v * 8))
        u = (v8 * hf.K_U) >> 13
        fx = 0 if prev is None else (v8 - prev) * 295
        prev = v8
        br = 0
        if brake and old and fx < 0:
            fx = br = max(fx, -2470)
        elif brake and not old:
            br = -torque
            fx = min((torque * hf.K_ROLL >> 15) * fade(u) >> 14, FX_LOCK)
            fx = fx if u < 0 else -fx
        elif fx < 0:
            fx = max(fx, -705)
        else:
            fx = min(fx, 2115)
        car.step(u, mouse - 320, fx, br)
        out.append(dict(r=car.r * DEG_S, brake=brake, mouse=mouse, slide=car.front.w is not None))
    return out


def c1e(S):
    js = next(i for i, s in enumerate(S) if s['mouse'] != 320)
    ia = next(i for i in range(js, len(S)) if S[i]['brake'])
    r0 = sum(S[i]['r'] for i in range(ia - 75, ia)) / 75
    pk = max(range(ia, ia + 50), key=lambda i: abs(S[i]['r'] - r0))
    slid = sum(S[i]['slide'] for i in range(ia, ia + 150))
    return (S[pk]['r'] - r0) / r0 * 100, r0, slid


def main():
    p = argparse.ArgumentParser()
    p.add_argument('root')
    p.add_argument('--torque', type=int, default=4653)
    p.add_argument('--old', action='store_true')
    a = p.parse_args()
    for name in sorted(ARCADE):
        path = os.path.join(PROF, a.root, name)
        if not os.path.exists(os.path.join(path, 'rec.bin')):
            continue
        S = run(path, a.torque, a.old)
        if name.startswith('c1e') and 'brake' in name:
            ch, r0, slid = c1e(S)
            print('%-14s yaw before %5.1f deg/s, largest change in 1 s %+6.1f%% (arcade %+.1f%%), '
                  'front sliding %d fields' % (name, r0, ch, ARCADE[name], slid))
        elif name.startswith('c1f'):
            js = next(i for i, s in enumerate(S) if s['mouse'] != 320)
            pk = max(abs(S[i]['r']) for i in range(js, js + 250))
            slid = sum(S[i]['slide'] for i in range(js, js + 250))
            print('%-14s largest yaw rate %5.1f deg/s (arcade %.1f), front sliding %d fields' % (
                name, pk, ARCADE[name], slid))


if __name__ == '__main__':
    main()
