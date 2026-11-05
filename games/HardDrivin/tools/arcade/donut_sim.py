"""A spin at low speed with the native speed held (plan step H3 round 2).

donut_sim.py MPH YAW_DEG_S [--k K] [--fx FX] [--seconds S]

Starts the twin (the game's force rule) at MPH with the yaw rate YAW, the
wheel centred, and feeds it a native force that pulls the speed back to MPH:
FX lb (constant) or, with --k, K lb per ft/s below MPH, limited to the
module's drive limit 2115 lb. That is what the native grass rules do: they
hold the car at the speed its cut throttle gives. Prints the yaw rate,
speed, sideways speed and the rear wheel's state.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handling_fx as hf      # noqa: E402

DEG = 180 / math.pi / (1 << 27)
MPH_PER_FT_S = 0.6818 * 0.9765625


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mph', type=float)
    p.add_argument('yaw', type=float)
    p.add_argument('--k', type=float, default=0)
    p.add_argument('--fx', type=int, default=0)
    p.add_argument('--seconds', type=float, default=6)
    p.add_argument('--every', type=int, default=25)
    a = p.parse_args()
    u0 = a.mph / MPH_PER_FT_S
    u = u0
    car = hf.FxCar()
    car.r = int(a.yaw / DEG)
    for i in range(int(a.seconds / 0.02)):
        fx = a.fx if not a.k else int(max(-705, min(2115, a.k * (u0 - u))))
        car.step(int(round(u * 64)), 0, fx, 0, fx_total=False)
        new = u + fx / hf.M * hf.DT + car.du / (1 << 22)
        u = 0 if u > 0 > new else new
        if i % a.every == 0:
            print('t %.2f fx %5d yaw %7.1f deg/s  %5.1f MPH  v %6.1f ft/s  rear %s front %s' % (
                i * 0.02, fx, car.r * DEG, u * MPH_PER_FT_S, car.v / (1 << 22),
                'slides' if car.rear.w is not None else '-', 'slides' if car.front.w is not None else '-'))


if __name__ == '__main__':
    main()
