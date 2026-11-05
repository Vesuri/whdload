"""Full lock then a steering change with the native speed fed back or not (plan step H3).

spin_sim.py MPH FX STEER_S AFTER [--old] [--every N]

Holds the force FX (lb, the native drive), full left lock for STEER_S
seconds, then AFTER (centre, counter: full right lock, half: half right lock,
hold) for the rest of 8 s, and prints the yaw rate, speed, sideways speed and
heading every N fields (default 12).
- The default is the game since H3: handling_fx's step with fx_total=False,
  and the step's du added to the forward speed every field, which stops at
  zero rather than changing sign.
- --old is G: fx_total=True, and the speed changes only by FX/m, as the
  native engine alone would change it. It reproduces the runaway spin the
  user met in H3.
The native engine is idealised: its own speed change is FX/m per field.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handling_fx as hf      # noqa: E402

DEG = 180 / math.pi / (1 << 27)
MPH_PER_FT_S = 0.6818 * 0.9765625      # model ft/s -> real MPH


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mph', type=float)
    p.add_argument('fx', type=int)
    p.add_argument('steer_s', type=float)
    p.add_argument('after', choices=('centre', 'counter', 'half', 'hold'))
    p.add_argument('--old', action='store_true')
    p.add_argument('--every', type=int, default=12)
    a = p.parse_args()
    u = a.mph / 0.28 * 8 * hf.K_U / 8192 / 64          # model ft/s
    back = {'centre': 0, 'counter': 320, 'half': 160, 'hold': -320}[a.after]
    car = hf.FxCar()
    peak = 0
    for i in range(int(8 / 0.02)):
        t = i * 0.02
        counts = -320 if t < a.steer_s else back
        car.step(int(round(u * 64)), counts, a.fx, 0, fx_total=a.old)
        new = u + a.fx / hf.M * hf.DT + (0 if a.old else car.du / (1 << 22))
        u = 0 if u > 0 > new else new
        if t >= a.steer_s:
            peak = max(peak, abs(car.r * DEG))
        if i % a.every == 0:
            print('t %.2f counts %4d yaw %7.1f deg/s  %5.1f MPH  v %6.1f ft/s  heading %7.1f deg  rear %s front %s' % (
                t, counts, car.r * DEG, u * MPH_PER_FT_S, car.v / (1 << 22), car.psi / 65536 / 4,
                'slides' if car.rear.w is not None else '-', 'slides' if car.front.w is not None else '-'))
    print('largest yaw rate after the change %.1f deg/s, final %.1f deg/s, final speed %.1f MPH' % (
        peak, car.r * DEG, u * MPH_PER_FT_S))


if __name__ == '__main__':
    main()
