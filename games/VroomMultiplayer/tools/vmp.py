#!/usr/bin/env python3
"""Vroom Multiplayer's gdb-stub server: the shared commands (docs/running.md) plus

  do <action> ...            fields, mouse, buttons, reads, waits and screenshots, CPU stopped
  race [stay]                from the boot through the title to the menu's START and a race
  hook                       what the VBL calls through $B028 (the title $ADAC, a race $AE64)

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


server = game_server('vmp', commands={'do': do, 'race': to_race, 'hook': hook})
if __name__ == '__main__':
    server.main(sys.argv[1:])
