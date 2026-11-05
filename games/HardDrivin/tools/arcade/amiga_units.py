"""Arcade and Amiga units for the handling model (plan step E1).

Arcade (ARCADE_ROMS.md, "MSP vehicle model"): feet, pounds, slugs, radians and
model seconds; model time runs at TIME_SCALE = 0.9765625 of real time.

Amiga (GAME_TIME.md, PHYSICS_ACCURACY.md and the native code):
- time: one PAL field is 1/50 s nominal (49.92 Hz measured); a native step is
  eight fields in the enhanced build's game time (f0 = 6.25 steps/s). The
  handling model steps once per field.
- heading G($994A): quarter degrees, 1440 per turn, wrapped to ±720 ($b44e).
  Native steering adds its steer value per step ($b1d0).
- forward velocity G($9928), a signed word: a native step moves the long
  position by 1.5·v along the heading ($b512..$b592), and a world unit is
  eight long units, so v moves 0.1875·v world units per step.
- speedometer G($992C): about 0.28·v MPH, through the RPM and the gears.
- mouse X G($95FA): accumulated per frame and clamped to 0..639, centre 320
  ($024c..$026e). Native steering uses (X − 320) / 20, at most ±16.

The length scale (2026-10-23) follows from the road: every Amiga road section
is 230 world units from edge to edge, and the arcade's road at the start line
is 41.2 ft wide (MAME runs w1L and w1R: the front wheel reaches the grass at
z = 5,021.0 and 4,979.8 ft). So a world unit is 0.1791 ft and v = 1 is
0.2099 ft/s, and the native speedometer's 0.28·v MPH reads about twice the
speed at which the car crosses the course. The native steering was tuned to
that speedometer. E1 first took the speedometer's MPH as real, which made a
world unit 0.3504 ft (FT_PER_WORLD_SPEEDO): arcade handling up to H3 round 8
drove at about half the arcade's speed past the scenery, and the arcade's
time limits had to be doubled.
"""
import math

FIELD = 0.02                     # s, nominal PAL field
STEP_FIELDS = 8                  # fields per native step at f0
F0 = 1 / (STEP_FIELDS * FIELD)   # native steps per second (6.25)
TIME_SCALE = 0.9765625           # arcade model seconds per real second
MPH = 5280 / 3600                # ft/s per MPH

HEADING_TURN = 1440              # G($994A) units per turn
HEADING_PER_RAD = HEADING_TURN / (2 * math.pi)
WORLD_PER_V = 1.5 / 8            # world units per native step per unit of G($9928)
MPH_PER_V = 0.28                 # native speedometer, approximate
FT_PER_WORLD_SPEEDO = MPH * MPH_PER_V / (WORLD_PER_V * F0)    # 0.3504, E1's first scale
ROAD_FT, ROAD_WORLD = 41.2, 230  # the road's width: arcade ft, Amiga world units
FT_PER_WORLD = ROAD_FT / ROAD_WORLD                     # 0.1791
FT_S_PER_V = WORLD_PER_V * F0 * FT_PER_WORLD            # 0.2099 real ft/s

MOUSE_CENTRE, MOUSE_LOCK = 320, 320      # X − 320 = ±320 is full lock
STEER_WORD = 4096                        # arcade steer word at full lock
DELTA_MAX = 0.6109                       # road wheel angle at full lock, rad


def ft_s_from_v(v):
    """Real ft/s for native velocity v."""
    return v * FT_S_PER_V


def v_from_ft_s(u):
    return u / FT_S_PER_V


def model_speed(v):
    """Arcade model-time ft/s for native velocity v."""
    return ft_s_from_v(v) / TIME_SCALE


def heading_from_rad(a):
    return a * HEADING_PER_RAD


def rad_from_heading(h):
    return h / HEADING_PER_RAD


def heading_per_field(r):
    """Heading units per field for a real yaw rate r (rad/s)."""
    return r * FIELD * HEADING_PER_RAD


def world_from_ft(x):
    return x / FT_PER_WORLD


def ft_from_world(x):
    return x * FT_PER_WORLD


def steer_word(counts):
    """Arcade steer word for a mouse offset X − 320."""
    return counts * STEER_WORD / MOUSE_LOCK


def mouse_from_word(word):
    return word * MOUSE_LOCK / STEER_WORD


def delta_from_mouse(counts):
    """Road wheel angle (rad, right positive) for a mouse offset X − 320."""
    return DELTA_MAX * counts / MOUSE_LOCK


def g_from_ft_s2(a):
    return a / 32.174


if __name__ == '__main__':
    print('world unit %.4f ft; v = 1 is %.4f ft/s (%.4f MPH)' % (FT_PER_WORLD, FT_S_PER_V, FT_S_PER_V / MPH))
    print('heading %.3f units per rad; 1 rad/s = %.3f units per field' % (HEADING_PER_RAD, heading_per_field(1)))
    print('mouse count = %.2f arcade steer words = %.4f° at the road wheel' % (
        steer_word(1), math.degrees(delta_from_mouse(1))))
    for mph in (5, 30, 60, 90, 140):
        print('%3d MPH: v = %5.1f' % (mph, v_from_ft_s(mph * MPH)))
