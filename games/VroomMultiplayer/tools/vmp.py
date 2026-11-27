#!/usr/bin/env python3
"""Vroom Multiplayer's gdb-stub server: the shared commands (docs/running.md) plus

  do <action> ...            fields, mouse, buttons, reads, waits and screenshots, CPU stopped
  race [stay]                from the boot through the title to the menu's START and a race
  hook                       what the VBL calls through $B028 (the title $ADAC, a race $AE64)
  bench [<frames>]           fps over the first frames from the next green light
  statelog <n> <file> [tick] the race state at every frame end (or pass) from the next green light
  frames <n> <file>          a hash of each drawn frame's lines, at the swap, from the next green light
  shown <n>                  frames whose shown screen changed between the swap and the VBL taking the next

A port of games/Vroom's tools/vroom.py at the Multiplayer's (v1) addresses
(tools/addrmap.py). Each command's docstring has the details.

    python3 tools/vmp.py serve       (SETUP=, WARP=1 WINDOW=none, INSTANCE=, ... as make run)
    python3 tools/vmp.py race
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402
from amigaxdev.gdbserve import profile  # noqa: E402

FIELDS = 0x98DE           # the VBL's field counter (long; Vroom's $A884)
VBL_HOOK = 0xB028         # the VBL's jsr vector (Vroom's $A56C)
TITLE_VBL, RACE_VBL = 0xADAC, 0xAE64   # what it calls in the title and in a race
TITLE_WAIT = (0x145E2, 0x14602)   # the title's idle loop, where it takes the click
UNREADABLE = 0xFFFFFFFF   # what the gdb stub reads during the slave's disk loads
CLOCK = 0xEA54            # the race clock (Vroom's $8500): +2 a field from the green light
LIGHTS = 0xE53E           # the start lights' state (word): negative once they are out
FRAME_FIELD = 0xEB36      # the field of the last swap (Vroom's $E258)
FRAME_END = 0xD37C        # the swap stores the field in $EB36 (Vroom's $D510)
TICK_END = 0xD38C         # after the swap: every pass, drawn or not
POS = 0xE588              # the first car's distance (Vroom's $DC50; player 1 in a race)
ENH_VARS = 0x1C0          # src/enhanced.i: due, ticks, frames drawn, fields dropped
# The race state: the globals, the 16 cars of 64 bytes at $E586 and the car order (Vroom's
# $DBC0-$E073 at $E504-$E9AB), the four players' blocks ($1254C, $106 bytes each), the
# ARCADE score $8B94, and the drawing state an undrawn pass keeps: the ground's top lines
# $12132/$12136 and the horizon's scroll per view ($15120).
STATE = ((0xE504, 0xE9AC), (0x1254C, 0x12964), (0x8B94, 0x8B98), (0x12130, 0x12138),
         (0x15120, 0x15140))
PENDING = 0x972E          # the buffer handed to the VBL; -1 once the VBL has taken it
SWAPPED = 0xD37C          # after `move.l $8F00,$972E`: the frame is handed to the VBL
VBL_TAKEN = 0xAEC4        # the race VBL ($AE64) has taken it: `move.l #-1,$972E`
SCREENS = 0x8EF8          # the two screens' addresses (longs)
SCREEN_BYTES = 32000      # 4 planes of 8000 bytes
BUTTONS = {'L': 'JOY1_FIRE_BUTTON', 'R': 'JOY1_2ND_BUTTON'}   # the port-0 mouse buttons


def longs(g, addr, n):
    out = g.cmd(f'x/{n}xw {addr:#x}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            try:
                vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
            except ValueError:
                break
    return (vals + [UNREADABLE] * n)[:n]


def pc(g):
    g.cmd('maintenance flush register-cache')
    return int(g.cmd('info registers pc').split()[1], 16)


def shot(server, g, path):
    out, trace = profile(g, 1, os.path.join(server.run_dir, 'shot.bin'))
    Path(path).write_bytes(trace.fields[-1].shot)


def vbl_hook(g):
    """What the VBL calls through $B028. On a 68020 or higher src/smc.i has made $B026 a
    `jsr smc_VblA`, which is `jmp ([_smc_vecA,pc])`: the hook is then the slave's variable."""
    v, = longs(g, VBL_HOOK, 1)
    if v < 0x80000 or v == UNREADABLE:
        return v
    op, = longs(g, v, 1)                  # 4EFB, then the extension word
    if op >> 16 != 0x4EFB:
        return v
    ext = op & 0xFFFF
    if (ext >> 4) & 3 == 3:
        bd, = longs(g, v + 4, 1)
    else:
        bd = longs(g, v + 4, 1)[0] >> 16
        bd -= 0x10000 if bd & 0x8000 else 0
    return longs(g, (v + 2 + bd) & 0xFFFFFFFF, 1)[0]


def hook(server, g, rest):
    g.stop()
    try:
        return f'{vbl_hook(g):#x} field {longs(g, FIELDS, 1)[0]:#x}'
    finally:
        g.cont()


def do(server, g, rest):
    """do <action> ...: run actions with the CPU stopped, then let it run again. Actions:
    f<N> run N fields; L1/L0, R1/R0 press/release the left/right mouse button; m<dx>,<dy>
    move the mouse; x<addr>[,<n>] read n longs (hex); u<addr>=<hex>,<max> (or !=) run fields
    until the long at addr compares so, at most max; h=<hex>,<max> run fields until the VBL
    hook is hex; b<addr> run to a breakpoint; r<reg>[,<reg>...] registers; pc;
    shot=<png> screenshot of the next field; d<addr>,<len>=<file> dump memory. A last
    `stay` leaves the CPU stopped."""
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
            elif a[0] in 'uh' and (a[0] == 'u' or a[1] == '='):
                if a[0] == 'h':
                    val, _, most = a[2:].partition(',')
                    val, get, test = int(val, 16), (lambda: vbl_hook(g)), None
                    test = val.__eq__
                else:
                    cond, _, most = a[1:].partition(',')
                    op = '!=' if '!=' in cond else '='
                    addr, val = (int(v, 16) for v in cond.split(op))
                    get = (lambda addr=addr: longs(g, addr, 1)[0])
                    test = val.__ne__ if op == '!=' else val.__eq__
                waited = 0
                while not test(get()):
                    if waited >= int(most):
                        raise TimeoutError(f'{a}: not after {waited} fields')
                    g.cmd('monitor fields 5')
                    waited += 5
                lines.append(f'{a} after {waited} fields')
            elif a[0] == 'b':
                g.cmd(f'break *{int(a[1:], 16):#x}')
                try:
                    g.cmd('continue', timeout=600)
                finally:
                    g.cmd('delete')
            elif a[0] == 'r':
                g.cmd('maintenance flush register-cache')
                out = g.cmd(f'info registers {" ".join(a[1:].split(","))}')
                lines.append(' '.join(f'{w[0]}={int(w[1], 16):08x}' for w in
                                      (l.split() for l in out.splitlines()) if len(w) > 1))
            elif a == 'pc':
                lines.append(f'{pc(g):#x}')
            elif a[0] == 'd' and '=' in a:
                where, _, path = a[1:].partition('=')
                lo, n = (int(v, 16) for v in where.split(','))
                g.cmd(f'dump binary memory {os.path.abspath(path)} {lo:#x} {lo + n:#x}',
                      timeout=600)
            elif a.startswith('shot='):
                shot(server, g, os.path.abspath(a[5:]))
            else:
                raise ValueError(f'unknown action {a}')
    except Exception as e:      # keep what was read before the failing action
        lines.append(f'ERROR {type(e).__name__}: {e}'.splitlines()[0])
    finally:
        if not stay:
            g.cont()
    return '\n'.join(lines) or 'ok'


def fields_until(g, test, most, step=5):
    for waited in range(0, most + 1, step):
        if test():
            return waited
        g.cmd(f'monitor fields {step}')
    return None


def green_light(g, most=20000):
    """Run fields one at a time until the race clock leaves 0 after the start lights (their
    state $E53E negative: the race clock can tick at a race's setup, before the lights); stops
    at the first field with it running. False after `most` fields without one."""
    prev = longs(g, CLOCK, 1)[0]
    for _ in range(most):
        g.cmd('monitor fields 1')
        c, lights = longs(g, CLOCK, 1)[0], longs(g, LIGHTS, 1)[0] >> 16
        if prev == 0 and 0 < c <= 4 and lights & 0x8000:
            return True
        prev = c
    return False


def bench(server, g, rest):
    """bench [<frames>]: the fields a race takes for its first <frames> frames (default 300)
    from the green light, one field at a time (read-only). In the first demo race, left alone
    after the boot, that is the same simulation on every machine, so the fps compare between
    machines and builds. Also the distance driven at the last frame's end (a breakpoint at
    $D37C) and the fields-per-frame histogram; with Enhanced framerate the ticks (race loop
    passes), the passes left undrawn and the fields dropped."""
    n = int(rest.split()[0]) if rest.split() else 300
    g.stop()
    try:
        if not green_light(g):
            return 'no race start within 20000 fields'
        last, p0 = longs(g, FRAME_FIELD, 1)[0], longs(g, POS, 1)[0]
        e0 = longs(g, ENH_VARS, 4)
        frames, fields, since, gaps = 0, 0, 0, {}
        while frames < n - 1:
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
        at = longs(g, FIELDS, 1)[0]
        g.cmd(f'break *{FRAME_END:#x}')
        try:
            g.cmd('continue', timeout=600)
        finally:
            g.cmd('delete')
        p, now = longs(g, POS, 1)[0], longs(g, FIELDS, 1)[0]
        gaps[since + now - at] = gaps.get(since + now - at, 0) + 1
        fields += now - at
        e1 = longs(g, ENH_VARS, 4)
    finally:
        g.cont()
    enh = ''
    if e1[1] != e0[1] and UNREADABLE not in e0 + e1:
        ticks, drawn = e1[1] - e0[1], e1[2] - e0[2]
        enh = (f' ticks {ticks} ' + (f'undrawn {ticks - drawn}' if drawn <= ticks else
                                     f'frames/tick {drawn / ticks:.2f}') +
               f' dropped {e1[3] - e0[3]}')
    return (f'bench {n} frames {fields} fields fps {50.0 * n / fields:.2f} distance {p - p0} '
            f'fields/frame {dict(sorted(gaps.items()))}{enh}')


def state_log(server, g, rest):
    """statelog <n> <file> [tick]: from the next green light, stop at every frame end ($D37C),
    or with `tick` at every race loop pass ($D38C, after the swap or the pass that left it
    out), for <n> stops, and write one line per stop: number, field counter, race clock, then
    the long words of STATE in hex. tools/statecmp.py compares two logs (Vroom's)."""
    args = rest.split()
    n, path = int(args[0]), args[1]
    at = TICK_END if args[2:3] == ['tick'] else FRAME_END
    g.stop()
    rows = []
    try:
        if not green_light(g):
            return 'no race start within 20000 fields'
        g.cmd(f'break *{at:#x}')
        for frame in range(n):
            out = g.cmd('continue', timeout=120)
            if 'Breakpoint' not in out:
                return f'no stop after {frame}: {out.strip().splitlines()[-1]}'
            f, c = longs(g, FIELDS, 1)[0], longs(g, CLOCK, 1)[0]
            block = ''.join(f'{v:08x}' for lo, hi in STATE for v in longs(g, lo, (hi - lo) // 4))
            rows.append(f'{frame} {f} {c} {block}')
    finally:
        g.cmd('delete')
        g.cont()
        ranges = ' '.join(f'${lo:X}-${hi - 1:X}' for lo, hi in STATE)
        Path(path).write_text(f'# frame field clock state {ranges} (at ${at:X})\n'
                              + '\n'.join(rows) + '\n')
    return f'{len(rows)} stops, fields {rows[0].split()[1]}..{rows[-1].split()[1]}' if rows else 'none'


def screen_diff(a, b):
    """Where two screen reads differ: plane, first and last line."""
    rows = sorted({(i * 4 // 8000, i * 4 % 8000 // 40) for i in range(len(a)) if a[i] != b[i]})
    planes = sorted({p for p, _ in rows})
    return f'planes {planes} lines {min(r for _, r in rows)}-{max(r for _, r in rows)}'


def frames(server, g, rest):
    """frames <n> <file>: from the next green light, at each swap ($D37C) for <n> frames, one
    line: the frame number, the tick (Enhanced framerate's pass count, else 0), then a short
    hash of each of the 800 plane lines of the frame just handed to the VBL. Two builds that
    draw the same ticks compare line for line (games/Vroom's tools/framecmp.py)."""
    import hashlib
    n, path = int(rest.split()[0]), rest.split()[1]
    g.stop()
    rows = []
    try:
        if not green_light(g):
            return 'no race start within 20000 fields'
        g.cmd(f'break *{SWAPPED:#x}')
        for i in range(n):
            out = g.cmd('continue', timeout=120)
            if 'Breakpoint' not in out:
                return f'no swap after {i}'
            tick = longs(g, ENH_VARS + 4, 1)[0]
            words = longs(g, longs(g, PENDING, 1)[0], SCREEN_BYTES // 4)
            raw = b''.join(w.to_bytes(4, 'big') for w in words)
            lines = [hashlib.sha1(raw[k:k + 40]).hexdigest()[:6] for k in range(0, SCREEN_BYTES, 40)]
            rows.append(f'{i} {0 if tick == 0xCCCCCCCC else tick} ' + ' '.join(lines))
    finally:
        g.cmd('delete')
        g.cont()
        Path(path).write_text('\n'.join(rows) + '\n')
    return f'{len(rows)} frames'


def shown(server, g, rest):
    """shown <n>: from the next green light, for <n> frames: at each swap ($D37C) read the
    screen still on display (the one not handed to the VBL), and again when the VBL takes the
    new one ($AEC4). A difference means the game drew into the screen on display (flicker)."""
    n = int(rest.split()[0]) if rest.split() else 40
    g.stop()
    changed, bad = 0, []
    try:
        if not green_light(g):
            return 'no race start within 20000 fields'
        for i in range(n):
            g.cmd(f'break *{SWAPPED:#x}')
            out = g.cmd('continue', timeout=120)
            g.cmd('delete')
            if 'Breakpoint' not in out:
                return f'no swap after {i}'
            new = longs(g, PENDING, 1)[0]
            a, b = longs(g, SCREENS, 2)
            old = b if new == a else a
            before = longs(g, old, SCREEN_BYTES // 4)
            g.cmd(f'break *{VBL_TAKEN:#x}')
            out = g.cmd('continue', timeout=120)
            g.cmd('delete')
            if 'Breakpoint' not in out:
                return f'no VBL after {i}'
            after = longs(g, old, SCREEN_BYTES // 4)
            if after != before:
                changed += 1
                bad.append(f'{i}: {screen_diff(before, after)}')
    finally:
        g.cmd('delete')
        g.cont()
    return f'{n} frames, {changed} with the shown screen changed' + ''.join(f'\n  {b}' for b in bad[:20])


def to_race(server, g, rest):
    """race [stay]: from the boot, through the title (right button in its idle loop,
    repeated until the VBL hook leaves the title) to the menu, then the left button held
    until a race's VBL hook runs: the menu's first highlight, START, with its settings as
    they are. Run it in a fresh boot. With `stay` the CPU stays stopped in the race."""
    stay = rest.split()[-1:] == ['stay']
    g.stop()
    log = []
    try:
        w = fields_until(g, lambda: vbl_hook(g) == TITLE_VBL, 8000)
        if w is None:
            raise TimeoutError('no title')
        log.append(f'title after {w}')
        for click in range(40):
            if fields_until(g, lambda: vbl_hook(g) != TITLE_VBL
                            or TITLE_WAIT[0] <= pc(g) < TITLE_WAIT[1], 4000, 10) is None:
                raise TimeoutError('the title does not wait for a click')
            if vbl_hook(g) != TITLE_VBL:
                break
            g.cmd('monitor input JOY1_2ND_BUTTON 1')
            g.cmd('monitor fields 20')
            g.cmd('monitor input JOY1_2ND_BUTTON 0')
            if fields_until(g, lambda: vbl_hook(g) != TITLE_VBL, 300, 10) is not None:
                break
        else:
            raise TimeoutError('no menu after 40 clicks')
        log.append(f'menu after {click} clicks, field {longs(g, FIELDS, 1)[0]:#x}')
        g.cmd('monitor fields 400')         # the menu's wipe and load
        g.cmd('monitor input JOY1_FIRE_BUTTON 1')
        held = fields_until(g, lambda: vbl_hook(g) == RACE_VBL, 3000, 10)
        g.cmd('monitor input JOY1_FIRE_BUTTON 0')
        if held is None:
            raise TimeoutError('START did not start a race')
        log.append(f'race after {held} fields held, field {longs(g, FIELDS, 1)[0]:#x}')
    finally:
        if not stay:
            g.cont()
    return '\n'.join(log)


server = game_server('vmp', commands={'do': do, 'race': to_race, 'hook': hook,
                                     'bench': bench, 'statelog': state_log,
                                     'frames': frames, 'shown': shown})
if __name__ == '__main__':
    server.main(sys.argv[1:])
