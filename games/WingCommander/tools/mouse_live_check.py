#!/usr/bin/env python3
"""Bounded live mouse check on a release build (English).

The left mouse button (port-0 button, JOY1_FIRE_BUTTON) replaces the Esc
presses that skip the intro in modal_live_check.py. At the start menu the
port-0 mouse moves in small steps, one per field, with no breakpoint in the
room routine: the pointer sprite must follow every field, the native room
position must follow the mouse, and a click must select the menu item, as
Return does. OCS original mode (the unchanged renderer) is only required to
cover the distance; see the assertion. Screenshots and reports stay in the
capture directory under tmp/.
"""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
import _amigaxdev  # noqa: F401
import wc_run
from amigaxdev import barto
from ocs_reconstruct import new_output
from variants import get

# Native A4 offsets: room pointer position and the pointer SimpleSprite (x at +6).
POINTER = {'ocs': (0x19c, -2150), 'cd32': (0xa88, -1156)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant', choices=('ocs', 'cd32'))
    p.add_argument('build', type=Path)
    p.add_argument('--output', required=True)
    p.add_argument('--original-mode', action='store_true', help='CUSTOM5 original behaviour')
    p.add_argument('--setup', default='a1200-030', help='AMIGA_SETUP (OCS also a500: 68000, 4 MiB Fast)')
    a = p.parse_args()
    out = new_output(a.output); out.mkdir(parents=True)
    v = get(a.variant); ocs = a.variant == 'ocs'
    if ocs:
        from ocs_runtime import locate
        slave = a.build/'WingCommander.Slave'
        whd = 'CUSTOM5=0 DCACHE' if a.original_mode else 'CUSTOM5=1 DCACHE'
    else:
        from cd32_runtime import locate
        slave = a.build/'WingCommanderCD32.Slave'
        whd = 'CUSTOM5=1 DCACHE' if a.original_mode else 'CUSTOM5=0 DCACHE'
    length = 0x400000 if ocs else 0x800000
    env = wc_run.run_env(out, variant=a.variant, SLAVE=str(slave.resolve()),
                         WARP='1', NTSC='0', WINDOW='front', JOY0='none', JOY1='none',
                         DETERMINISTIC='1', AMIGA_SETUP=a.setup, WHD_ARGS=whd,
                         EXTRA_ARGS='--fast_memory=4096' if ocs and a.setup != 'a500' else '', OCS_STOCK_CLOCK='0',
                         INTRO_STOCK_CLOCK='0',
                         WC_BASELINE_CACHE_MODEL='0' if a.setup == 'a500' else '1')
    g = None

    def stop():
        nonlocal g
        if g:
            g.p.kill(); g = None
        wc_run.stop(env)

    def boot():
        return wc_run.server('wc-mouse', env, profile_window=False).boot(env)

    def cmd(s, timeout=60):
        r = g.cmd(s, timeout=timeout)
        if any(x in r for x in ('Remote connection closed', 'Cannot access', 'Error', 'Invalid hex', 'Protocol error')):
            raise RuntimeError(r)
        return r

    def until(addr):
        print('checkpoint', hex(addr), flush=True)
        r = cmd(f'break *{addr:#x}\ncontinue\ndelete', 60)
        if 'Breakpoint' not in r:
            raise ValueError('checkpoint missed: '+r)

    def number(expr):
        r = cmd('printf "VALUE %d\\n", '+expr)
        return int(re.search(r'VALUE (-?\d+)', r)[1])

    def shot(name):
        path = out/(name+'.bin')
        cmd(f'monitor profile 1 "" "{path}"', 60)
        (out/(name+'.png')).write_bytes(barto.load(str(path)).fields[-1].shot)
        path.unlink()

    rows = {}
    try:
        g = boot()
        snapshot = out/'calibration.bin'
        for _ in range(12):
            g.cont(); time.sleep(1); g.stop()
            cmd(f'dump binary memory {snapshot.resolve()} 0x200000 {0x200000+length:#x}')
            try:
                layout = locate(snapshot.read_bytes()); break
            except ValueError:
                pass
        else:
            raise ValueError('live segment chain not found')
        snapshot.unlink(); stop()
        (out/'layout.json').write_text(json.dumps(layout, indent=2)+'\n')
        g = boot(); h0, h1, _, _ = layout['hunks']
        a4 = h1+v.A4_BASE
        field = a4+v.A4['field_clock']
        pos, sprite = POINTER[a.variant]
        # Intro: the left button where modal_live_check presses Esc.
        for wait, done in ((0x180c4, 0x1edde), (0x180c4, 0x1f396)) if ocs else ((0x1898a, 0x1fbba), (0x1898a, 0x20164)):
            until(h0+wait)
            cmd('monitor input JOY1_FIRE_BUTTON 1')
            until(h0+done)
            cmd('monitor input JOY1_FIRE_BUTTON 0')
        rows['intro_skipped_by_left_button'] = True
        menu, chosen = (0x1f43c, 0x1f44e) if ocs else (0x20214, 0x20226)
        until(h0+menu)
        cmd('monitor fields 4')
        until(h0+menu)
        start = dict(x=number(f'*(short*){a4+pos:#x}'), y=number(f'*(short*){a4+pos+2:#x}'),
                     sprite=number(f'*(short*){a4+sprite+6:#x}'))
        shot('menu-before')
        trace = []
        for dx in [4]*12+[-4]*12:
            cmd(f'monitor mouse {dx} 0')
            cmd('monitor fields 1')
            trace.append(dict(field=number(f'*(unsigned int*){field:#x}'),
                              sprite=number(f'*(short*){a4+sprite+6:#x}'),
                              x=number(f'*(short*){a4+pos:#x}')))
            if len(trace) == 12:
                shot('menu-moved')
        sprites = [r['sprite'] for r in trace]
        steps = [b-a for a, b in zip([start['sprite']]+sprites, sprites)]
        rows.update(start=start, trace=trace, sprite_steps=steps)
        # The sprite covers the mouse's 24 pixels out and back. OS event timing
        # can split two fields' motion 1/3. OCS original mode keeps the native
        # renderer, whose Forbid/Disable stretches leave input.device (and the
        # native room loop) without CPU time for several fields: motion arrives
        # in bursts there, so per-field updates are required everywhere else.
        assert max(sprites) >= start['sprite']+22, steps
        per_field = all(1 <= s <= 3 for s in steps[1:12]) and all(-3 <= s <= -1 for s in steps[13:])
        rows['per_field'] = per_field
        native_renderer = ocs and (a.original_mode or a.setup == 'a500')   # 68000: original path
        assert per_field or native_renderer, steps
        assert max(r['x'] for r in trace) >= start['x']+20, 'room position did not follow the mouse'
        cmd('monitor fields 10')                # let queued input events arrive
        until(h0+menu)
        settled = dict(x=number(f'*(short*){a4+pos:#x}'), sprite=number(f'*(short*){a4+sprite+6:#x}'))
        rows['settled'] = settled
        assert settled == dict(x=start['x'], sprite=start['sprite']), (start, settled)
        # The menu's pad record reset armed a release guard that swallowed the
        # first click natively; the slave arms it only while fire is held, so
        # the first click selects.
        def click():
            cmd('monitor input JOY1_FIRE_BUTTON 1'); cmd('monitor fields 3')
            cmd('monitor input JOY1_FIRE_BUTTON 0')
            for _ in range(3):                  # room routine results after the release
                until(h0+menu+10)
                if number('(short)$d0') >= 0:
                    return 'selected'
            return 'ignored'
        rows['clicks'] = [click()]
        assert rows['clicks'] == ['selected'], rows['clicks']
        rows['menu_selected_by_click'] = True
        (out/'report.json').write_text(json.dumps(dict(complete=True, variant=a.variant, original_mode=a.original_mode, setup=a.setup,
            slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(), **rows), indent=2)+'\n')
        print(json.dumps(dict(complete=True, sprite_steps=steps)))
    finally:
        stop()


if __name__ == '__main__':
    main()
