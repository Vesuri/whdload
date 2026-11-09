#!/usr/bin/env python3
"""Enhanced framerate, plan step 3 (src/combat.s): BH's own routines in Unicorn.

  python3 tools/combat_check.py [--cpu 68000|68040] [--only NAME,...] [SLAVE [LISTING]]

The harness is tools/timing_check.py's (BH relocated, the slave's _pl_timing applied, the
original beside it).  Each check runs a game routine over equal game time at T 4, 7, 25
and 50 (mission T 7) and compares it with the exact value; the original's result is
printed beside it.  Checks (--only names):
- attitude, bank, climbloss, sink, fuel: FR-15 and FR-28 (bh:11142, 111bc);
- guns: FR-07, shots held for 9 s (bh:c366, c4d6); ai, surface_ai: FR-12/14, a decision
  each 2 s for every eligible object (bh:f074, 12d22);
- periodic: FR-03 effects, FR-10 aircraft and FR-11 ship damage ticks (bh:aec8, de16,
  e28e); waits: FR-20 (bh:ecaa); timers: object lives with T changing (bh:c94c, 857e,
  ebb6); message: FR-21 (bh:8858, 8862);
- falling: FR-01, a bomb's drop in 5 s (bh:83c0); torpedo: a torpedo or bomb released at
  speed, 10 s of run, drag and fall from the object step on (bh:827e..8504); lead: FR-13 (bh:cab0); flak: FR-06
  jitter (bh:e9d4, e9e8); hit: the swept hit test (bh:dae6); replay: FR-22, the film's
  limits and each step's T (bh:77a2, 78aa, dt_film_t).
Sounds and messages (bh:40bc, 40fa, 87f2) and the routines a check only counts are
stubbed in the test memory.  Run from the game directory.
"""
import argparse, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import timing_check as tc  # noqa: E402
from timing_check import A5, D4, STACK, check  # noqa: E402

TS = (4, 7, 25, 50)
CHECKS = {}


def checker(f):
    CHECKS[f.__name__] = f
    return f

COUNT = 0x5f0000                 # stub counters (outside BH, the slave and its buffer)


def stub(bh, off, code):
    bh.c.write(tc.CODE + off, code)
    bh.c.flush()
    bh.last_end = None


def count_stub(bh, off, back, slot=0):
    """At bh:off: addq.w #1,COUNT+2*slot.l; jmp bh:back."""
    stub(bh, off, b'\x52\x79' + struct.pack('>I', COUNT + 2 * slot) + b'\x4e\xf9'
         + struct.pack('>I', tc.CODE + back))


def counts(bh, n=16):
    return list(struct.unpack('>%dH' % n, bh.c.read(COUNT, 2 * n)))


def zero_counts(bh):
    bh.c.write(COUNT, bytes(64))


def call(bh, off, *args):
    """A C function bh:off with word arguments."""
    bh.c.write(STACK + 4, b''.join(struct.pack('>H', a & 0xffff) for a in args))
    bh.run(off, tc.STOP - tc.CODE)


def seconds(bh, t, s, step, tchange=None):
    """Run step() for s game seconds at T t (or the list of (T, seconds) in tchange)."""
    plan = tchange or [(t, s)]
    for tt, ss in plan:
        bh.set(10184, tt)
        bh.set(10186, tt // 8 + 1)
        for _ in range(round(tt * ss)):
            step()


def both(fixed, orig, prepare, measure):
    out = {}
    for nm, bh in (('fixed', fixed), ('orig', orig)):
        prepare(bh)
        out[nm] = measure(bh)
    return out


def plane(bh, d4, **kw):
    """One active plane for the attitude update bh:11142, all others off."""
    for k in range(12):
        bh.set(10596 + k, 0, 'B')
    bh.set(10596 + d4, 1, 'B')
    bh.set(10452 + d4, 1, 'B')
    fields = dict(power=0, rollcmd=0, fast=0, rolltarget=0, roll=0, pitchcmd=0, pitchtarget=0,
                  pitch=0x4000, pitch2=0x4000, state=2, aiturn=0, snap=0, heading=0, speed=100)
    fields.update(kw)
    bh.set(19628 + 2 * d4, fields['power'])
    bh.set(15528 + d4, fields['rollcmd'], 'B')
    bh.set(15540 + d4, fields['fast'], 'B')
    bh.set(15552 + 2 * d4, fields['rolltarget'])
    bh.set(15240 + 2 * d4, fields['roll'])
    bh.set(15576 + d4, fields['pitchcmd'], 'B')
    bh.set(15588 + d4, fields['snap'], 'B')
    bh.set(15600 + 2 * d4, fields['pitchtarget'])
    bh.set(14952 + 2 * d4, fields['pitch'])
    bh.set(14616 + 2 * d4, fields['pitch2'])
    bh.set(14328 + 2 * d4, fields['heading'])
    bh.set(19616 + d4, fields['state'], 'B')
    bh.set(14904 + d4, fields['aiturn'], 'B')
    bh.set(15624 + d4, 0, 'B')
    bh.set(15636 + d4, 0, 'B')
    bh.set(15696 + 2 * d4, fields['speed'])
    bh.set(15984 + 2 * d4, 0)


def attitude_second(bh, t, d4, steps=None, **kw):
    bh.timing(t, 7)
    plane(bh, d4, **kw)
    for _ in range(t if steps is None else steps):
        bh.c.reg(D4, 0)
        bh.run(0x11142, tc.STOP - tc.CODE)


@checker
def attitude(fixed, orig):
    print('# FR-15 attitude: commands over one game second, plane 3 (bh:11142)')
    cases = (
        ('roll 4096/s', dict(rollcmd=1, rolltarget=0x6000, roll=0), 15240, 4096),
        ('fast roll 16384/s', dict(rollcmd=1, fast=1, rolltarget=0x7000, roll=0x0100), 15240, 16384),
        ('roll left', dict(rollcmd=1, rolltarget=0xa000, roll=0), 15240, -4096),
        ('dive 9216/s', dict(pitchcmd=1, pitchtarget=0x0000, pitch=0x6000), 14952, -9216),
        ('climb 5120/s', dict(pitchcmd=2, pitchtarget=0x7800, pitch=0x2000), 14952, 5120),
        ('falling 728/s', dict(state=4, pitch2=0x1000), 14616, 728),
        ('stalled 6400/s', dict(state=1, pitch2=0x1000, speed=20), 14616, 6400),
    )
    for name, kw, off, exact in cases:
        for t in TS:
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                attitude_second(bh, t, 3, **kw)
                v0 = kw.get({15240: 'roll', 14952: 'pitch', 14616: 'pitch2'}[off],
                            0 if off == 15240 else 0x4000)
                d = (bh.get(off + 6, 'H') - v0 + 0x8000) % 0x10000 - 0x8000
                res[nm] = d
            check(abs(res['fixed'] - exact) <= 1,
                  f'{name:18s} T {t:2d}: {res["fixed"]:+6d} (exact {exact:+d}; original {res["orig"]:+d})')
    # The pole: diving from 500 crosses at 500/9216 s and climbs the rest at 5120/s.
    exact = 5120 * (1 - 500 / 9216)
    for t in TS:
        res = {}
        for nm, bh in (('fixed', fixed), ('orig', orig)):
            attitude_second(bh, t, 3, pitchcmd=1, pitchtarget=0x7000, pitch=500)
            res[nm] = (bh.get(14952 + 6, 'H'), bh.get(15576 + 3, 'B'), bh.get(14328 + 6, 'H'))
        f = res['fixed']
        check(abs(f[0] - exact) <= 2 and f[1] == 2 and f[2] == 0x8000,
              f'pole crossing T {t:2d}: pitch {f[0]} (exact {exact:.1f}), command {f[1]}, '
              f'heading {f[2]:#06x} (original {res["orig"][0]})')


@checker
def bank(fixed, orig):
    print("# FR-15 the player's bank pitch (bh:114ea..115ae) over one game second")
    for roll, power in ((0x3800, 0), (0x2400, 0x0400), (0xc900, 0)):
        rate = None
        orig.timing(1, 7)                       # T 1: the step is the rate per second
        orig.set(15240, roll)
        orig.set(19628, power)
        orig.set(14952, 0x2000)
        orig.c.reg(D4, 0)
        orig.c.reg(A5, STACK - 0x100)
        orig.run(0x114ea, 0x115ae)
        rate = orig.get(14952, 'H') - 0x2000
        for t in TS:
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                bh.timing(t, 7)
                bh.set(15240, roll)
                bh.set(19628, power)
                bh.set(14952, 0x2000)
                for _ in range(t):
                    bh.c.reg(D4, 0)
                    bh.c.reg(A5, STACK - 0x100)
                    bh.run(0x114ea, 0x115ae)
                res[nm] = bh.get(14952, 'H') - 0x2000
            check(abs(res['fixed'] - rate) <= 1,
                  f'bank roll {roll:#06x} power {power:#06x} T {t:2d}: pitch {res["fixed"]:+d} '
                  f'(exact {rate:+d}; original {res["orig"]:+d})')


@checker
def climbloss(fixed, orig):
    print('# FR-15 speed lost climbing (bh:1164e) over one game second: tm max(1, floor(r/tm)), plane 3')
    for excess in (0x0300, 0x2000, 0x3f00):
        exact = 7 * max(1, (excess >> 8) // 7)
        for t in TS:
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                bh.timing(t, 7)
                bh.set(15696 + 6, 300)
                bh.set(15984 + 6, 0)
                for _ in range(t):
                    bh.c.reg(D4, 3)
                    bh.c.reg(A5, STACK - 0x100)
                    bh.c.write(STACK - 0x100 - 12, struct.pack('>H', excess))
                    bh.run(0x1164e, 0x1169e)
                res[nm] = 300 - bh.get(15696 + 6)
            check(abs(res['fixed'] - exact) <= 1,
                  f'climb r {excess >> 8:2d} T {t:2d}: lost {res["fixed"]} (exact {exact}; '
                  f'original {res["orig"]})')


@checker
def sink(fixed, orig):
    print('# FR-15 underpowered nose rise (bh:117ec): 16 per mission step = 112/s at mission T 7')
    for t in TS:
        res = {}
        for nm, bh in (('fixed', fixed), ('orig', orig)):
            bh.timing(t, 7)
            bh.set(14616 + 6, 0x3000)
            for _ in range(t):
                bh.c.reg(D4, 3)
                bh.run(0x117e0, 0x1180a)
            res[nm] = bh.get(14616 + 6) - 0x3000
        check(abs(res['fixed'] - 112) <= 1 and bh.get(14952 + 6) == bh.get(14616 + 6),
              f'nose rise T {t:2d}: {res["fixed"]:+d} (exact +112; original {res["orig"]:+d})')


@checker
def fuel(fixed, orig):
    print('# FR-28 fuel (bh:111bc..11226): power 19628 per game second off 19720')
    for power in (7, 1000, 40000):
        for t in TS:
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                bh.timing(t, 7)
                bh.set(19628 + 6, power)
                bh.set(19720 + 12, 0x01000000, 'l')
                for _ in range(t):
                    bh.c.reg(D4, 3)
                    bh.run(0x111bc, 0x11226)
                res[nm] = 0x01000000 - bh.get(19720 + 12, 'l')
            check(abs(res['fixed'] - power) <= 1,
                  f'fuel power {power:5d} T {t:2d}: {res["fixed"]} (exact {power}; original {res["orig"]})')


def stubs_sound(bh):
    for off in (0x40bc, 0x40fa, 0x87f2):          # sounds, messages (jump table targets)
        stub(bh, off, b'\x4e\x75')


@checker
def guns(fixed, orig):
    print('# FR-07 guns: the player holding fire for 9 game seconds (bh:c366 pass, bh:c4d6 fire)')
    exact = None
    for t in TS:
        res = {}
        for nm, bh in (('fixed', fixed), ('orig', orig)):
            stubs_sound(bh)
            bh.timing(t, 7)
            for k in range(144):
                bh.set(10596 + k, 0, 'B')
            bh.set(10596, 1, 'B')
            bh.set(19792, 30000)                 # ammunition
            bh.set(9864, 0, 'B')
            bh.set(19768, 0, 'B')
            bh.set(19852, 0, 'B')
            bh.set(19888, 0, 'B')

            def step():
                call(bh, 0xc366)
                call(bh, 0xc4d6, 0, 0)
                for k in range(28, 44):
                    bh.set(10596 + k, 0, 'B')
            seconds(bh, t, 9, step)
            res[nm] = 30000 - bh.get(19792)
        # floor(7/3)/7 s a shot: the first at once, then every 2/7 s
        exact = 1 + int(9 / (2 / 7) + 1e-9)
        check(abs(res['fixed'] - exact) <= 1,
              f'shots in 9 s T {t:2d}: {res["fixed"]} (exact {exact}; original {res["orig"]})')


@checker
def ai(fixed, orig):
    print('# FR-12 AI decisions: 12 eligible planes over 20 game seconds, a decision each 2 s')
    for t in TS:
        res = {}
        for nm, bh in (('fixed', fixed), ('orig', orig)):
            bh.timing(t, 7)
            zero_counts(bh)
            # bh:f130: count the decision for plane 10190(a4), then return
            code = (b'\x30\x2c' + struct.pack('>h', 10190) + b'\xd0\x40'          # move.w 10190(a4),d0; add.w d0,d0
                    + b'\x41\xf9' + struct.pack('>I', COUNT)                          # lea COUNT,a0
                    + b'\x52\x70\x00\x00' + b'\x4e\x75')                          # addq.w #1,(a0,d0.w); rts
            stub(bh, 0xf130, code)
            for k in range(12):
                bh.set(10596 + k, 1, 'B')
                bh.set(20056 + k, 0, 'B')
                bh.set(16296 + 2 * k, 2 * t)
            bh.set(10190, 0)
            seconds(bh, t, 20, lambda: call(bh, 0xf074))
            res[nm] = counts(bh, 12)
        f = res['fixed']
        check(all(9 <= c <= 11 for c in f),
              f'decisions T {t:2d}: {f} (exact 10 each; original {res["orig"]})')


@checker
def periodic(fixed, orig):
    print('# FR-03 effects, FR-10 aircraft damage, FR-11 ships: ticks in 60 game seconds (mission T 7)')
    cases = (('effects', 0xaec8, 0xaee2, 0xb12c, 7 / 1),
             ('aircraft damage', 0xde16, 0xde3e, 0xe16c, 7 / 3),
             ('ships', 0xe28e, 0xe2ac, 0xe550, 7 / 29))
    for name, entry, body, epi, rate in cases:
        for t in TS:
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                bh.timing(t, 7)
                zero_counts(bh)
                count_stub(bh, body, epi)
                bh.set(10188, 1)
                bh.set(10198, 0)
                bh.set(10196, 0)
                seconds(bh, t, 60, lambda: call(bh, entry))
                res[nm] = counts(bh, 1)[0]
            exact = 60 * rate
            check(abs(res['fixed'] - exact) <= 1.5,
                  f'{name:16s} T {t:2d}: {res["fixed"]} (exact {exact:.1f}; original {res["orig"]})')


@checker
def waits(fixed, orig):
    print('# FR-20 mission waits over 300 game seconds: the reminder (40 tm+1 steps), the scan (4 tm+1)')
    for mode, name, body, back, period in ((1, 'reminder', 0xecdc, 0xed0e, 281 / 7),
                                         (0, 'scan', 0xed24, 0xef1c, 29 / 7)):
        for t in TS:
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                bh.timing(t, 7)
                zero_counts(bh)
                count_stub(bh, body, back)
                bh.set(10139, mode, 'B')
                bh.set(28474, 0, 'B')
                bh.set(10142, 0)
                bh.set(10140, 0)
                seconds(bh, t, 300, lambda: call(bh, 0xecaa))
                res[nm] = counts(bh, 1)[0]
            exact = 1 + int(300 / period)
            # the reminder's stub skips the native re-arm (40T at bh:ecdc), so no original
            o = res['orig'] if mode == 0 else 'n/a'
            check(abs(res['fixed'] - exact) <= 1,
                  f'{name:8s} T {t:2d}: {res["fixed"]} (exact {exact}; original {o})')


def life_run(bh, slot, setter, plan, dec_start, dec_end):
    """Set slot's timer with the setter segment, count it down; > its life in seconds."""
    bh.set(10596 + slot, 1, 'B')
    t0 = plan[0][0]
    bh.set(10184, t0)
    bh.c.reg(A5, STACK - 0x100)
    bh.c.write(STACK - 0x100 - 2, struct.pack('>H', slot))
    bh.c.reg(D4, slot)
    bh.run(*setter)
    life = 0.0
    for tt, ss in plan:
        bh.set(10184, tt)
        for _ in range(round(tt * ss)):
            bh.c.reg(D4, slot)
            bh.c.reg(A5, STACK - 0x100)
            bh.run(dec_start, dec_end)
            life += 1 / tt
            if bh.get(16816 + 2 * slot) == 0:
                return life
    return None


@checker
def timers(fixed, orig):
    print("# object timers 16816: a shot's 2T set (bh:c94c), counted down by the projectile step "
          "(bh:857e) and the flak delay (bh:ebb6), T changing mid-life")
    plans = ([(8, 0.5), (50, 9)], [(50, 0.5), (8, 9)], [(25, 9)], [(4, 9)])
    for name, slot, setter, dec, exact in (
            ('shot 2 s', 30, (0xc94c, 0xc962), (0x857e, 0x8590), 2.0),
            ('flak delay 2 s', 90, (0xc94c, 0xc962), (0xebb6, 0xebe4), 2.0)):
        for plan in plans:
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                bh.lput('dt_tm', 7)
                bh.c.write(tc.BUF, bytes(0x1000))
                res[nm] = life_run(bh, slot, setter, plan, *dec)
            f = res['fixed']
            ok = f is not None and abs(f - exact) <= 1 / min(p[0] for p in plan) + 1e-9
            check(ok, f'{name:15s} T {plan}: {f and round(f, 3)} s (exact {exact}; original '
                      f'{res["orig"] and round(res["orig"], 3)})')


@checker
def falling(fixed, orig):
    print('# FR-01 a bomb (class 4) falling for 5 game seconds from rest (bh:83c0..8504)')
    slot = 20
    g = 7 * max(1, 11 // 7)
    exact = 4660 / 256 * g * 25 / 2
    for t in TS:
        res = {}
        for nm, bh in (('fixed', fixed), ('orig', orig)):
            bh.timing(t, 7)
            bh.set(10452 + slot, 4, 'B')
            bh.set(10596 + slot, 1, 'B')
            bh.set(15696 + 2 * slot, 0)
            bh.set(16008 + 2 * slot, 0)
            bh.set(16816 + 2 * slot, 0)
            bh.set(12060 + 4 * slot, 1000000, 'l')

            def step():
                bh.c.reg(D4, slot)
                bh.c.reg(A5, STACK - 0x100)
                bh.run(0x83c0, 0x8504)
            seconds(bh, t, 5, step)
            res[nm] = 1000000 - bh.get(12060 + 4 * slot, 'l')
        check(abs(res['fixed'] - exact) <= exact * 0.01,
              f'fall T {t:2d}: {res["fixed"]} (exact {exact:.0f}; original {res["orig"]})')


@checker
def torpedo(fixed, orig):
    print('# FR-01/05 a torpedo or bomb (class 4) released at speed: 10 game seconds of run,'
          ' drag and fall (bh:83c0..8504), against the original at the mission T 7')
    slot, start = 20, 65536000

    def run(bh, t, z):
        bh.timing(t, 7)
        bh.set(10452 + slot, 4, 'B')
        bh.set(10596 + slot, 1, 'B')
        bh.set(15696 + 2 * slot, 250)
        bh.set(14328 + 2 * slot, 0x2000)
        bh.set(14616 + 2 * slot, 0x4000)
        bh.set(16008 + 2 * slot, 0)
        bh.set(16816 + 2 * slot, 5 * t)
        bh.set(10908 + 4 * slot, start, 'l')
        bh.set(11484 + 4 * slot, start, 'l')
        bh.set(12060 + 4 * slot, z, 'l')

        def step():
            bh.c.reg(D4, slot)
            bh.c.reg(A5, STACK - 0x100)
            bh.run(0x827e, 0x8504)          # from the object step (bh:8290), then the switch
        seconds(bh, t, 10, step)
        dx = bh.get(10908 + 4 * slot, 'l') - start
        dy = bh.get(11484 + 4 * slot, 'l') - start
        return round((dx * dx + dy * dy) ** 0.5), bh.get(15696 + 2 * slot, 'H'), bh.get(12060 + 4 * slot, 'l')

    for z, name in ((0, 'on the water'), (60000, 'dropped')):
        ref = run(orig, 7, z)
        for t in TS:
            f, o = run(fixed, t, z), run(orig, t, z)
            ok = abs(f[0] - ref[0]) <= ref[0] * 0.02 and abs(f[1] - ref[1]) <= 1 and \
                (f[2] == ref[2] == 0 or abs(f[2] - ref[2]) <= max(ref[2], 1) * 0.02)
            check(ok, f'{name:12s} T {t:2d}: run {f[0]}, speed {f[1]}, height {f[2]} (original at'
                      f' T 7: {ref[0]}, {ref[1]}, {ref[2]}; original at T {t}: {o[0]}, {o[1]}, {o[2]})')


@checker
def lead(fixed, orig):
    print("# FR-13 a gunner's lead (bh:cab0..cb34): 4 steps at mission T 7 = 4/7 s of the target's motion")
    for t in TS:
        res = {}
        for nm, bh in (('fixed', fixed), ('orig', orig)):
            bh.timing(t, 7)
            tgt = 5
            v = (7000, -3500, 700)                   # units per second
            for k, off in enumerate((13596, 13644, 13692)):
                bh.set(off + 4 * tgt, round(v[k] / t), 'l')
            for off in (10908, 11484, 12060):
                bh.set(off + 4 * tgt, 100000, 'l')
            bh.c.reg(A5, STACK - 0x100)
            bh.c.write(STACK - 0x100 - 14, struct.pack('>H', 4))
            bh.c.reg(13 + 1, tgt)                    # D5
            bh.run(0xcab0, 0xcb34)
            res[nm] = tuple(struct.unpack('>l', bh.c.read(STACK - 0x100 - o, 4))[0] - 100000
                            for o in (4, 8, 12))
        exact = tuple(round(x * 4 / 7) for x in v)
        f = res['fixed']
        check(all(abs(a - b) <= max(2, abs(b) * 0.02) for a, b in zip(f, exact)),
              f'lead T {t:2d}: {f} (exact {exact}; original {res["orig"]})')


@checker
def hit(fixed, orig):
    print('# the hit test (bh:dae6): a shot passing the plane, the same path cut into steps of T 4..50')
    # bh:dbca (hit) and bh:dc5e (miss) end the test run with D7 = 1 or 2
    for bh in (fixed, orig):
        stub(bh, 0xdbca, b'\x7e\x01\x4e\xf9' + struct.pack('>I', tc.STOP))
        stub(bh, 0xdc5e, b'\x7e\x02\x4e\xf9' + struct.pack('>I', tc.STOP))
    paths = (('through', (-3000, 2400, 100), (3000, -2400, 100), True),
             ('beside', (-3000, 1800, 0), (3000, 1300, 0), False),
             ('diagonal miss', (-3000, -3000, 0), (3000, 3000, 1200), False))
    for name, a, b, want in paths:
        for t in TS:
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                n = max(1, round(t / 4))             # steps across the path
                got = False
                for k in range(n):
                    p0 = [a[i] + (b[i] - a[i]) * k / n for i in range(3)]
                    p1 = [a[i] + (b[i] - a[i]) * (k + 1) / n for i in range(3)]
                    for i, (o0, o1) in enumerate(((6, 18), (10, 22), (14, 26))):
                        bh.c.write(STACK - 0x100 - o0, struct.pack('>l', round(p0[i])))
                        bh.c.write(STACK - 0x100 - o1, struct.pack('>l', round(p1[i])))
                        bh.c.write(STACK - 0x100 - (30 + 4 * i), struct.pack('>l', abs(round(p1[i]))))
                    bh.c.reg(A5, STACK - 0x100)
                    bh.c.reg(16, 0)
                    bh.run(0xdae6, tc.STOP - tc.CODE)
                    got = got or bh.c.reg(16) == 1
                res[nm] = got
            check(res['fixed'] == want, f'{name:13s} T {t:2d}: {"hit" if res["fixed"] else "miss"} '
                                        f'(original {"hit" if res["orig"] else "miss"})')


@checker
def surface_ai(fixed, orig):
    print('# FR-14 surface AI (bh:12d22): objects 12..15 over 20 game seconds, a decision each 2 s')
    for t in TS:
        res = {}
        for nm, bh in (('fixed', fixed), ('orig', orig)):
            bh.timing(t, 7)
            zero_counts(bh)
            code = (b'\x30\x2c' + struct.pack('>h', 10192) + b'\xd0\x40'
                    + b'\x41\xf9' + struct.pack('>I', COUNT)
                    + b'\x52\x70\x00\x00' + b'\x4e\x75')
            stub(bh, 0x12ddc, code)
            for k in range(12, 16):
                bh.set(10596 + k, 1, 'B')
                bh.set(20056 + k, 0, 'B')
                bh.set(16296 + 2 * k, 2 * t)
            bh.set(10192, 12)
            seconds(bh, t, 20, lambda: call(bh, 0x12d22))
            res[nm] = counts(bh, 16)[12:]
        f = res['fixed']
        check(all(9 <= c <= 11 for c in f),
              f'decisions T {t:2d}: {f} (exact 10 each; original {res["orig"]})')


@checker
def flak(fixed, orig):
    print('# FR-06 flak jitter (bh:e9d4, e9e8): -22(a5) steps at mission T 7, as many x T/7 at T')
    w = STACK - 0x400
    for t in TS:
        for j in (5, -3, 22):
            res = {}
            for nm, bh in (('fixed', fixed), ('orig', orig)):
                bh.timing(t, 7)
                got = []
                for seg in ((0xe9d4, 0xe9da), (0xe9e8, 0xe9ee)):
                    bh.c.write(w, struct.pack('>h', 1000))
                    bh.c.reg(1, w)                                  # A0
                    bh.c.reg(A5, STACK - 0x100)
                    bh.c.write(STACK - 0x100 - 22, struct.pack('>h', j))
                    bh.run(*seg)
                    got.append(struct.unpack('>h', bh.c.read(w, 2))[0] - 1000)
                res[nm] = got
            k = round(abs(j) * t / 7) * (1 if j >= 0 else -1)
            check(res['fixed'] == [k, -k],
                  f'jitter {j:3d} T {t:2d}: {res["fixed"]} (exact {[k, -k]}; original {res["orig"]})')


def slave_call(bh, name, a4=True):
    bh.c.reg(tc.A4, bh.a4)
    bh.c.flush()
    bh.last_end = None
    bh.c.run(tc.SLAVE + bh.syms[name], tc.STOP)


@checker
def replay(fixed, orig):
    print('# FR-22 the replay: filming (bh:77a2, bh:78aa..791c) ends at 128 s or 7680 steps; '
          'each step keeps its T')
    bh = fixed
    stubs_sound(bh)
    for plan, want in (([(50, 200)], 6400), ([(100, 200)], 7680), ([(4, 30), (50, 200)], 120 + 4900)):
        bh.timing(plan[0][0], 7)
        bh.run(0x77a2, 0x77a8)
        bh.set(28498, 0)
        bh.set(28475, 1, 'B')
        bh.set(10160, 0, 'B')
        steps, ts = 0, []
        for tt, ss in plan:
            bh.set(10184, tt)
            for _ in range(tt * ss):
                if bh.get(28475, 'B') != 1:
                    break
                bh.run(0x78aa, 0x791c)
                steps += 1
                ts.append(tt)
        # the filmed T read back as a replay would (dt_film_t, from dt_frame)
        film = bh.get(24864, 'l') - steps * 8
        back = []
        for k in range(0, steps, max(1, steps // 50)):
            bh.set(24864, film + 8 * k, 'l')
            bh.set(10184, 1)
            slave_call(bh, 'dt_film_t')
            back.append((bh.get(10184), ts[k]))
        check(abs(steps - want) <= 1 and all(a == b for a, b in back),
              f'film at T {plan}: {steps} steps (exact {want}); T read back '
              f'{"as filmed" if all(a == b for a, b in back) else back[:5]}')


@checker
def message(fixed, orig):
    print('# FR-21 a message (bh:8858 sets 80 steps, bh:8862 counts down): 80/7 s at mission T 7')
    exact = 80 / 7
    for plan in ([(7, 30)], [(50, 30)], [(4, 30)], [(50, 3), (8, 30)]):
        res = {}
        for nm, bh in (('fixed', fixed), ('orig', orig)):
            bh.timing(plan[0][0], 7)
            stub(bh, 0x8876, b'\x4e\xf9' + struct.pack('>I', tc.STOP))   # expired: the redraw
            bh.run(0x8858, 0x885e)
            life = None
            el = 0.0
            for tt, ss in plan:
                bh.set(10184, tt)
                for _ in range(tt * ss):
                    call(bh, 0x8862)
                    el += 1 / tt
                    if bh.get(28522) == 0:
                        life = el
                        break
                if life is not None:
                    break
            res[nm] = life
        f = res['fixed']
        ok = f is not None and abs(f - exact) <= 1 / min(p[0] for p in plan) + 1e-9
        check(ok, f'message T {plan}: {f and round(f, 2)} s (exact {exact:.2f}; original '
                  f'{res["orig"] and round(res["orig"], 2)})')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cpu', default='68000', choices=('68000', '68040'))
    p.add_argument('--only', default='')
    p.add_argument('slave', nargs='?', default='tmp/build/release/Battlehawks1942.Slave')
    p.add_argument('listing', nargs='?')
    a = p.parse_args()
    listing = a.listing or str(Path(a.slave).with_suffix('.lst'))
    model = 1 if a.cpu == '68000' else 4
    fixed = tc.BH(model, a.slave, listing, True)
    orig = tc.BH(model, a.slave, listing, False)
    print(f'# Unicorn {a.cpu}')
    only = [x for x in a.only.split(',') if x]
    for name, f in CHECKS.items():
        if not only or name in only:
            f(fixed, orig)
    print(f'# {len(tc.failures)} failed' if tc.failures else '# all passed')
    sys.exit(1 if tc.failures else 0)


if __name__ == '__main__':
    main()
