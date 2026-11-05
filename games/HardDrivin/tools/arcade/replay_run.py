"""Replay a game run's native speed and mouse through the twin (plan step H3 round 2).

replay_run.py RUN_DIR [--from F] [--to F] [--every N]

Per field: u = the record's native velocity (G($9928) word), the mouse from
the record, the force as the module measures it (the native speed change
less what the model added, 295 lb per eighth per field, limited to drive
2115 / coast -705 / brake -2470 lb), all four wheels on the ground. Prints the
twin's yaw rate next to the game's (from the heading), the speed, sideways
speed and the wheels' sliding state.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import amiga_feel as af       # noqa: E402
import handling_fx as hf      # noqa: E402

DEG = 180 / math.pi / (1 << 27)


def wrap(a):
    return (a + 720) % 1440 - 720


def main():
    p = argparse.ArgumentParser()
    p.add_argument('run')
    p.add_argument('--from', dest='first', type=int, default=0)
    p.add_argument('--to', type=int, default=10 ** 9)
    p.add_argument('--every', type=int, default=10)
    a = p.parse_args()
    R = af.records(a.run)
    car = hf.FxCar()
    du_sum = 0.0          # Q22 ft/s the model added since the last whole unit
    prev = None
    for i, r in enumerate(R):
        if r['field'] < a.first or r['field'] > a.to:
            continue
        v8 = r['velocity'] * 8
        if prev is None:
            prev = v8
        # the native change less the model's own (in eighths: Q22 ft/s -> eighths)
        model8 = du_sum / (1 << 22) * 64 * 8192 / hf.K_U
        fx = (v8 - prev - model8) * 295
        prev = v8
        du_sum = 0
        fx = int(max(-2470 if r['brake'] else -705, min(2115, fx)))
        u = (v8 * hf.K_U) >> 13
        car.step(u, r['mouse'] - 320, fx, -fx if (r['brake'] and fx < 0) else 0, contact=3, fx_total=False)
        du_sum += car.du
        if i % a.every == 0 and i:
            g = wrap(r['heading'] - R[i - a.every]['heading']) / 4 / (a.every * 0.02)
            print('%5d game %6.1f twin %6.1f deg/s  %5.1f MPH  v %6.1f  fx %5d  mouse %4d  rear %s front %s' % (
                r['field'], g, car.r * DEG, r['velocity'] * 0.28, car.v / (1 << 22), fx, r['mouse'] - 320,
                'S' if car.rear.w is not None else '-', 'S' if car.front.w is not None else '-'))


if __name__ == '__main__':
    main()
