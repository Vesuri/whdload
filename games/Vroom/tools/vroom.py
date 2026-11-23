#!/usr/bin/env python3
"""Vroom's gdb-stub server: the shared commands (docs/running.md) plus

  bench [<frames>]           fps over the first frames from the next green light
  statelog <frames> <file>   the race state at every frame end from the next green light
  racelog <fields> <file>    field, frame, clock and distance per field from the next green light
  meter <fields>             frames, clock and distance over the next fields
  race [stay]                from the boot through the title and menu to a player race
  drive <fields> [...]       a test driver for that race
  do <action> ...            fields, mouse, buttons, reads, waits and screenshots, CPU stopped
  decrunch <n> [<seconds>]   stop after each of the next n file decrunches (the loader's return
                             from the slave's Decrunch hook at $1CFC8) and report the destination
                             ($1D90E) and decrunched length ($34F32); gives up after <seconds>
                             of emulated running (default 600) without one

Each command's docstring has the details; docs/development.md ("Tools") how to use them.

    python3 tools/vroom.py serve       (SETUP=, VARIANT=, WARP=1 WINDOW=none, ... as make run)
    python3 tools/vroom.py bench 500
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402
from amigaxdev.gdbserve import profile  # noqa: E402

LOADER_RETURN = 0x1CFC8   # after `jsr $1D0F8` (the slave's Decrunch) in the loader
DEST = 0x1D90E            # decrunch destination
LENGTH = 0x34F32          # decrunched length


def word(g, expr):
    out = g.cmd(f'x/1xw {expr}')
    return int(out.rsplit(':', 1)[1].split()[0], 16)


def decrunch(server, g, rest):
    args = rest.split()
    n = int(args[0]) if args else 1
    timeout = float(args[1]) if len(args) > 1 else 600
    g.stop()
    g.cmd(f'break *{LOADER_RETURN:#x}')
    lines = []
    try:
        for _ in range(n):
            out = g.cmd('continue', timeout=timeout)
            if 'Breakpoint' not in out:
                lines.append('no decrunch: ' + out.strip().splitlines()[-1])
                break
            dest, length = word(g, DEST), word(g, LENGTH)
            lines.append(f'dest ${dest:X} length ${length:X} end ${dest + length:X}')
    finally:
        g.cmd('delete')
        g.cont()
    return '\n'.join(lines)


FIELDS = 0xA884           # the VBL's field counter (long)
# The end of a race frame ($D510) stores the field counter in $E258, and the next frame
# waits ($D142) for the counter to move on: at most one frame ends in a field, and $E258
# changes at each. (The draw buffer $86DE is no frame count: the race loop also toggles it
# twice to draw the panel into both screens, $CC12-$CCE6.)
FRAME_FIELD = 0xE258
CLOCK = 0x8500            # race clock (long, +2 per field while it runs: centiseconds)
POS = 0xDC50              # the player's distance along the track (long)
STEP = 0xDC60             # the player's last step (word), as added to POS at $C782/$C7C2


def longs(g, addr, n):
    out = g.cmd(f'x/{n}xw {addr:#x}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return vals[:n]


def sample(g):
    fields, = longs(g, FIELDS, 1)
    buf, = longs(g, FRAME_FIELD, 1)
    clock, = longs(g, CLOCK, 1)
    pos, = longs(g, POS, 1)
    step = longs(g, STEP, 1)[0] >> 16   # the word at $DC60: the long's high half
    return fields, buf, clock, pos, step


def meter(server, g, rest):
    """meter <fields>: step one field at a time (read-only) and report frames ($E258 changes),
    race-clock, distance and step rates. At most one frame ends per field, so a sample per
    field counts every frame."""
    n = int(rest.split()[0]) if rest.split() else 250
    g.stop()
    g.cmd('monitor fields 1')
    f0, b0, c0, p0, _ = sample(g)
    frames, last, steps, gaps, since = 0, b0, [], [], 0
    for _ in range(n):
        g.cmd('monitor fields 1')
        f, b, c, p, s = sample(g)
        since += 1
        steps.append(s)
        if b != last:
            frames += 1
            gaps.append(since)
            since = 0
            last = b
    g.cont()
    fields = f - f0
    hist = {k: gaps.count(k) for k in sorted(set(gaps))}
    return (f'fields {fields} frames {frames} fps {50.0 * frames / max(fields, 1):.2f} '
            f'fields/frame {hist}\n'
            f'clock +{c - c0} ({(c - c0) / max(fields, 1):.2f}/field) '
            f'distance +{p - p0} ({(p - p0) / max(fields, 1):.1f}/field, '
            f'{(p - p0) / max(frames, 1):.1f}/frame) mean step {sum(steps) / len(steps):.1f}')


def green_light(g, most=20000):
    """Run fields one at a time until the race clock leaves 0 (the green light); stops at the
    first field with it running. False after `most` fields without one."""
    prev = longs(g, CLOCK, 1)[0]
    for _ in range(most):
        g.cmd('monitor fields 1')
        c = longs(g, CLOCK, 1)[0]
        if prev == 0 and 0 < c <= 4:
            return True
        prev = c
    return False


def race_log(server, g, rest):
    """racelog <fields> <file>: wait for a race start (the race clock leaving 0; polled every
    field for at most 20000), then step one field at a time for <fields> fields and write one
    line per field: field counter, frame number (frame ends, $E258 changes, since the start), race clock,
    distance. Field 0 is the first with the clock running: the green light on every machine."""
    args = rest.split()
    n, path = int(args[0]), args[1]
    g.stop()
    if not green_light(g):
        g.cont()
        return 'no race start within 20000 fields'
    frames, last, rows = 0, longs(g, FRAME_FIELD, 1)[0], []
    for _ in range(n):
        g.cmd('monitor fields 1')
        f, b, c, p, s = sample(g)
        if b != last:
            frames, last = frames + 1, b
        rows.append(f'{f} {frames} {c} {p}')
    g.cont()
    with open(path, 'w') as out:
        out.write('\n'.join(rows) + '\n')
    return f'{n} fields, {frames} frames, clock {rows[0].split()[2]}..{c}'


def bench(server, g, rest):
    """bench [<frames>]: the fields a race takes for its first <frames> frames (default 500)
    from the green light, one field at a time (read-only, any CPU). In the first demo race,
    left alone after the boot, that is the same simulation on every machine (one step a
    frame), so the fps it gives compare between machines and builds. Also the distance driven
    (the same on every machine at equal frames) and the fields-per-frame histogram."""
    n = int(rest.split()[0]) if rest.split() else 500
    g.stop()
    try:
        if not green_light(g):
            return 'no race start within 20000 fields'
        f0, last, _, p0, _ = sample(g)
        frames, fields, since, gaps = 0, 0, 0, {}
        while frames < n:
            g.cmd('monitor fields 1')
            fields += 1
            since += 1
            b = longs(g, FRAME_FIELD, 1)[0]
            if b != last:
                frames, last = frames + 1, b
                gaps[since] = gaps.get(since, 0) + 1
                since = 0
            if fields > 50 * n:
                return f'only {frames} frames in {fields} fields'
        p = longs(g, POS, 1)[0]
    finally:
        g.cont()
    return (f'bench {n} frames {fields} fields fps {50.0 * n / fields:.2f} distance {p - p0} '
            f'fields/frame {dict(sorted(gaps.items()))}')


FRAME_END = 0xD510         # the end of a race frame (it stores the field in $E258)
# The race state around the car table: globals from $DBC0, the 16 cars of 64 bytes at $DC4E,
# the car order list at $E050.
STATE = (0xDBC0, 0xE074)


def state_log(server, g, rest):
    """statelog <frames> <file>: from the next green light, stop at every frame end ($D510)
    for <frames> frames and write one line per frame: frame, field counter, race clock, then the state block $DBC0-$E073 in hex. Exact per frame on any
    machine (a breakpoint, so slower than `racelog`). tools/statecmp.py compares two logs."""
    args = rest.split()
    n, path = int(args[0]), args[1]
    words = (STATE[1] - STATE[0]) // 4
    g.stop()
    rows = []
    try:
        if not green_light(g):
            return 'no race start within 20000 fields'
        g.cmd(f'break *{FRAME_END:#x}')
        for frame in range(n):
            out = g.cmd('continue', timeout=120)
            if 'Breakpoint' not in out:
                return f'no frame end after frame {frame}: {out.strip().splitlines()[-1]}'
            f, c = longs(g, FIELDS, 1)[0], longs(g, CLOCK, 1)[0]
            block = ''.join(f'{v:08x}' for v in longs(g, STATE[0], words))
            rows.append(f'{frame} {f} {c} {block}')
    finally:
        g.cmd('delete')
        g.cont()
        Path(path).write_text(f'# frame field clock state ${STATE[0]:X}-${STATE[1] - 1:X}\n'
                              + '\n'.join(rows) + '\n')
    return f'{len(rows)} frames, fields {rows[0].split()[1]}..{rows[-1].split()[1]}'


# While WHDLoad has the OS in (a disk load) chip memory reads back as $FFFFFFFF.
UNREADABLE = 0xFFFFFFFF
BUTTONS = {'L': 'JOY1_FIRE_BUTTON', 'R': 'JOY1_2ND_BUTTON'}   # the port-0 mouse buttons


def pc(g):
    g.cmd('maintenance flush register-cache')
    return int(g.cmd('info registers pc').split()[1], 16)


def shot(server, g, path):
    out, trace = profile(g, 1, os.path.join(server.run_dir, 'shot.bin'))
    Path(path).write_bytes(trace.fields[-1].shot)


def do(server, g, rest):
    """do <action> ...: run actions with the CPU stopped, then let it run again. Actions:
    f<N> run N fields; L1/L0, R1/R0 press/release the left/right mouse button; m<dx>,<dy>
    move the mouse (then run fields so the game reads it); x<addr>[,<n>] read n longs (hex);
    u<addr>=<hex>,<max> (or != or >=, unsigned) run fields until the long at addr
    compares so with hex, at most max (>= skips $FFFFFFFF, read during disk loads);
    pc the stopped PC; shot=<png> screenshot of the next field. A last action `stay` leaves
    the CPU stopped, so the next `do` goes on from the same field. Replies with one line per
    read."""
    g.stop()
    lines, actions = [], rest.split()
    stay = actions[-1:] == ['stay']
    try:
        for a in actions[:len(actions) - stay]:
            if a[0] == 'f':
                g.cmd(f'monitor fields {int(a[1:])}', timeout=600)
            elif a[0] in BUTTONS and a[1:] in ('0', '1'):
                g.cmd(f'monitor input {BUTTONS[a[0]]} {a[1]}')
            elif a[0] == 'm':
                dx, dy = a[1:].split(',')
                g.cmd(f'monitor mouse {int(dx)} {int(dy)}')
            elif a[0] == 'x':
                addr, _, n = a[1:].partition(',')
                vals = longs(g, int(addr, 16), int(n or 1))
                lines.append(f'{addr} ' + ' '.join(f'{v:08x}' for v in vals))
            elif a[0] == 'u':
                cond, _, most = a[1:].partition(',')
                op = next(o for o in ('!=', '>=', '=') if o in cond)
                addr, val = (int(v, 16) for v in cond.split(op))
                test = {'=': val.__eq__, '!=': val.__ne__,
                        '>=': lambda v: val <= v != UNREADABLE}[op]
                waited = 0
                while not test(longs(g, addr, 1)[0]):
                    if waited >= int(most):
                        raise TimeoutError(f'{a}: not after {waited} fields')
                    g.cmd('monitor fields 5')
                    waited += 5
                lines.append(f'{a} after {waited} fields')
            elif a == 'pc':
                lines.append(f'{pc(g):#x}')
            elif a.startswith('shot='):
                shot(server, g, os.path.abspath(a[5:]))
            else:
                raise ValueError(f'unknown action {a}')
    finally:
        if not stay:
            g.cont()
    return '\n'.join(lines) or 'ok'


def sword(v):
    return v - 0x10000 if v & 0x8000 else v


TITLE_VBL, RACE_VBL = 0xA2EC, 0xA3A4   # what the VBL calls through $A56C
MENU_ITEM = 0x86EE        # the menu's highlighted item
MENU_ITEMS = (0x86F2, 0x88C6)   # START (the first highlight) to MANUAL
MENU_CODE = ((0x4800, 0x4E80), (0x8DC0, 0x8E80))   # the menu's loop and its wait


def fields_until(g, test, most, step=5):
    """Run fields `step` at a time until test() holds; the fields it took, or None."""
    for waited in range(0, most + 1, step):
        if test():
            return waited
        g.cmd(f'monitor fields {step}')
    return None


def to_race(server, g, rest):
    """race: from the boot, through the title (right button, repeated until the menu is up)
    and the menu (left button on START, its first highlight; the menu's settings left as they
    are) to the race's green light. Run it in a fresh boot. Leaves the CPU stopped at the
    first field with the race clock running when the last word is `stay`."""
    stay = rest.split()[-1:] == ['stay']
    g.stop()
    log = []
    try:
        w = fields_until(g, lambda: longs(g, 0xA56C, 1)[0] == TITLE_VBL, 8000)
        if w is None:
            raise TimeoutError('no title')
        log.append(f'title after {w}')
        # The title takes the click while it is still loading the menu in the background and
        # shows the menu once the load is done; a click is repeated every 250 fields.
        for click in range(40):
            g.cmd('monitor input JOY1_2ND_BUTTON 1')
            g.cmd('monitor fields 20')
            g.cmd('monitor input JOY1_2ND_BUTTON 0')
            if fields_until(g, lambda: menu_up(g), 230, 10) is not None:
                break
        else:
            raise TimeoutError('no menu after 40 clicks')
        log.append(f'menu after {click} clicks, field {longs(g, FIELDS, 1)[0]:#x}')
        g.cmd('monitor input JOY1_FIRE_BUTTON 1')
        held = fields_until(g, lambda: not menu_up(g), 200)
        g.cmd('monitor input JOY1_FIRE_BUTTON 0')
        if held is None:
            raise TimeoutError('START did not leave the menu')
        log.append(f'START held {held} fields')
        w = fields_until(g, lambda: longs(g, 0xA56C, 1)[0] == RACE_VBL, 6000)
        log.append(f'race after {w}')
        w = fields_until(g, lambda: 0 < longs(g, CLOCK, 1)[0] <= 0x100, 6000, 1)
        if w is None:
            raise TimeoutError('no green light')
        log.append(f'green light after {w}, field {longs(g, FIELDS, 1)[0]:#x}')
    finally:
        if not stay:
            g.cont()
    return '\n'.join(log)


def menu_up(g):
    """The menu is running: its highlight pointer is one of its items and the CPU is in
    its loop (sampled over a few fields)."""
    if not MENU_ITEMS[0] <= longs(g, MENU_ITEM, 1)[0] <= MENU_ITEMS[1]:
        return False
    for _ in range(4):
        p = pc(g)
        if any(lo <= p < hi for lo, hi in MENU_CODE):
            return True
        g.cmd('monitor fields 1')
    return False


def drive(server, g, rest):
    """drive <fields> [<gain>] [<log>]: a test driver for a player race with the menu's MOUSE
    and MANUAL settings. Full throttle (the mouse's y at -94), shift up (right button) out of
    neutral and when the speed has stopped rising, steer (the mouse's x, which the race clamps
    to ±271) against the player's lateral position $DC56 times gain (default 2). A step every
    2 fields; the log has field, gear, speed, lateral position, x and y per step."""
    args = rest.split()
    n = int(args[0])
    gain = float(args[1]) if len(args) > 1 else 2.0
    path = args[2] if len(args) > 2 else None
    g.stop()
    rows, best, flat, field = [], 0, 0, 0
    try:
        while field < n:
            xy = longs(g, 0x825E, 1)[0]
            x, y = sword(xy >> 16), sword(xy & 0xFFFF)
            lat = sword(longs(g, 0xDC56, 1)[0] >> 16)
            speed = longs(g, STEP, 1)[0] >> 16
            gear = longs(g, 0xDC04, 1)[0] >> 16
            want = max(-271, min(271, int(-gain * lat)))
            dx = max(-64, min(64, 2 * (want - x)))
            dy = max(-64, min(64, 2 * (-94 - y)))
            g.cmd(f'monitor mouse {dx} {dy}')
            if speed > best:
                best, flat = speed, 0
            else:
                flat += 1
            if gear == 0 or (flat >= 6 and gear < 6 and speed > 40):
                g.cmd('monitor input JOY1_2ND_BUTTON 1')
                g.cmd('monitor fields 4')
                g.cmd('monitor input JOY1_2ND_BUTTON 0')
                best, flat, field = 0, 0, field + 4
            g.cmd('monitor fields 2')
            rows.append(f'{field} {gear} {speed} {lat} {x} {y}')
            field += 2
    finally:
        g.cont()
    if path:
        Path(path).write_text('field gear speed lateral x y\n' + '\n'.join(rows) + '\n')
    return rows[-1] if rows else 'no steps'


server = game_server('vroom', commands={
    'bench': bench, 'statelog': state_log, 'racelog': race_log, 'meter': meter, 'race': to_race,
    'drive': drive, 'do': do, 'decrunch': decrunch})
if __name__ == '__main__':
    server.main(sys.argv[1:])
