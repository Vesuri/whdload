#!/usr/bin/env python3
"""Bounded live mouse check on a release build (English; CD32 also German).

The left mouse button (port-0 button, JOY1_FIRE_BUTTON) replaces the Esc
presses that skip the intro in modal_live_check.py. At the start menu the
port-0 mouse moves in small steps, one per field, with no breakpoint in the
room routine: the pointer sprite must follow every field, the native room
position must follow the mouse, and a click must select the menu item, as
Return does. OCS original mode (the unchanged renderer) is only required to
cover the distance; see the assertion. CD32 --name-entry continues into the
simulator, lets the ship be destroyed and, at the top-score name entry, moves
the selection box over the character grid with the mouse and clicks a
character. Screenshots and reports stay in the capture directory under tmp/.
"""
import argparse
import functools
import hashlib
import json
import re
import time
from pathlib import Path
import _amigaxdev  # noqa: F401
import wc_run
from amigaxdev import barto
from ocs_reconstruct import ROOT, new_output
from variants import get
from mouse_model import POINTER, Pointer
from PIL import Image

# Per game: A4 offsets of the room pointer position, the pointer SimpleSprite
# (x at +6) and the field clock; H0 intro waits (wait, done), menu (ready,
# accepted); name entry (input loop, poll result) and its A4 selected cell and
# columns; flight: ramp store site (H0), ramps, view, aperture block and copper
# list pair (A4; OCS none). German CD32 addresses map the English ones by
# matching code.
GAMES = {
    'ocs': dict(pointer=(0x19c, -2150), field=-0x800, intro=((0x180c4, 0x1edde), (0x180c4, 0x1f396)),
                menu=(0x1f43c, 0x1f44e), flight=(0x1869e, 3720, -18318, -4188, 0)),
    'cd32': dict(pointer=(0xa88, -1156), field=-252, intro=((0x1898a, 0x1fbba), (0x1898a, 0x20164)),
                 menu=(0x20214, 0x20226), name=(0x16fc6, 0x16fd0, 17716, 17706),
                 flight=(0x19064, 5882, -18280, -4318, -532)),
    'cd32-de': dict(pointer=(2740, -1112), field=-208, intro=((0x18a44, 0x1fcbe), (0x18a44, 0x2026c)),
                    menu=(0x2031c, 0x2032e), name=(0x17064, 0x1706e, 17766, 17756),
                    flight=(0x1911e, 5926, -18236, -4274, -488)),
}
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant', choices=('ocs', 'cd32'))
    p.add_argument('build', type=Path)
    p.add_argument('--output', required=True)
    p.add_argument('--original-mode', action='store_true', help='CUSTOM5 original behaviour')
    p.add_argument('--setup', default='a1200-030', help='AMIGA_SETUP (OCS also a500: 68000, 4 MiB Fast)')
    p.add_argument('--name-entry', action='store_true', help='CD32: also the TrainSim name entry grid')
    p.add_argument('--flight', action='store_true', help='mouse steering and the pointer in the simulator flight')
    p.add_argument('--german', action='store_true', help='CD32: the German executable (CUSTOM1=1)')
    p.add_argument('--direct-flight', action='store_true',
                   help='CD32 English --flight only, on a tools/flight_fixture.py --release build: the mission flight, no menu')
    a = p.parse_args()
    if a.name_entry and a.variant != 'cd32':
        p.error('--name-entry: the OCS name entry is keyboard only')
    if a.german and a.variant != 'cd32':
        p.error('--german: the OCS release supports English only')
    if a.direct_flight and (a.variant != 'cd32' or a.german or a.original_mode or a.name_entry or not a.flight):
        p.error('--direct-flight: CD32 English enhanced --flight only')
    game = GAMES['cd32-de' if a.german else a.variant]
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
        if a.german:
            whd = 'CUSTOM1=1 '+whd
            locate = functools.partial(locate, german=True)
        if a.direct_flight:     # the fixture's direct-flight argument (docs/development.md)
            whd = 'CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 '+whd
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

    def until(addr, timeout=60):
        print('checkpoint', hex(addr), flush=True)
        r = cmd(f'break *{addr:#x}\ncontinue\ndelete', timeout)
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

    def name_entry():
        # E:16fc6 first name-input iteration; E:16fd0 poll result in d0.
        # Selected cell code at A4+17716, grid columns at A4+17706.
        loop, result, sel, cols = game['name']
        until(h0+loop, 600)
        cmd('monitor fields 4'); until(h0+loop)
        width = number(f'*(short*){a4+cols:#x}')

        def cell():
            c = number(f'*(short*){a4+sel:#x}')-32
            return c % width, c // width
        start = cell(); shot('name-before')
        for dx, dy in [(4, 0)]*9+[(0, 4)]*9:
            cmd(f'monitor mouse {dx} {dy}'); cmd('monitor fields 1')
        cmd('monitor fields 4'); until(h0+loop)
        moved = cell(); shot('name-moved')
        assert moved == (start[0]+2, start[1]+2), (start, moved)
        cmd('monitor input JOY1_FIRE_BUTTON 1')
        r = cmd(f'break *{h0+result:#x}\ncondition $bpnum (short)$d0 != -1\ncontinue\ndelete', 60)
        assert 'Breakpoint' in r, 'click did not pick a character'
        code = number('(short)$d0')
        cmd('monitor input JOY1_FIRE_BUTTON 0')
        assert code not in (13, 127), code
        cmd('monitor fields 4'); shot('name-picked')
        return dict(columns=width, start=start, moved=moved, picked=code)

    def flight():
        # The flight: the controller's ramp stores (the slave's mouse_steer).
        # The pointer (sprite 7, the slave's image) moves with the mouse, two
        # counts a pixel, behind the cockpit; mouse right and down: yaw right,
        # pitch up (stick back), in proportion to its place.
        site, ramp, view, aperture, copper = game['flight']
        if ocs:
            sym = json.loads((a.build/'build.json').read_text())['symbols']
        else:
            sym = {n: int(o, 16) for o, n in re.findall(r'^([0-9A-F]{8}) (\S+)$', (a.build/'slave.lst').read_text(), re.M)}
        sb = layout['slave']
        var = lambda name, kind='short': number(f'*({kind}*){sb+sym[name]:#x}')
        until(h0+site, 900 if a.direct_flight else 600)
        cmd('monitor fields 4'); until(h0+site)
        def state():
            until(h0+site); cmd('stepi')
            until(h0+site); cmd('stepi')
            ss, image = var('stick_ss', 'int'), var('stick_image', 'int')
            row = dict(pitch=number(f'*(short*){a4+ramp:#x}'), yaw=number(f'*(short*){a4+ramp+2:#x}'),
                       view=number(f'*(short*){a4+view:#x}'), stick=(var('stick_x'), var('stick_y')),
                       pointer=(var('stick_ptr'), number(f'*(short*){sb+sym["stick_ptr"]+2:#x}')),
                       aperture=[number(f'*(short*){a4+aperture+2*i:#x}') for i in range(6)],
                       sprite=(number(f'*(short*){ss+6:#x}'), number(f'*(short*){ss+8:#x}')),
                       number=number(f'*(short*){ss+10:#x}'), control=number(f'*(int*){image:#x}'),
                       lines=[number(f'*(unsigned int*){image+4+4*r:#x}') & 0xffffffff for r in range(9)])
            if copper:              # BPLCON4 in both flight copper lists, where mouse.s found it
                lists = sb+sym['bank_lists']
                row['bplcon4'] = [number(f'*(unsigned short*)(*(int*){lists+8*i:#x}+*(short*){lists+8*i+4:#x}+2)') for i in range(2)]
            return row
        def pixels(row, name):
            # Each image pixel at its screen place: playfield origin (74, 92),
            # two screen pixels per playfield pixel, sprite pixel 0 at x+1.
            image = Image.open(out/(name+'.png')).convert('RGB')
            colour = (255, 255, 255) if ocs else (243, 255, 235)
            x, y = row['sprite']
            drawn = [(x+1+c, y+r) for r in range(9) for c in range(9) if row['lines'][r] >> (31-c) & 1]
            return drawn, all(image.getpixel((74+2*px, 92+2*py)) == colour for px, py in drawn)
        rows = [dict(motion=(0, 0), **state())]
        shot('flight-before')
        for dx, dy, n in ((8, 0, 20), (0, 4, 13), (40, 40, 30), (-40, -40, 60), (8, 0, 55)):
            for _ in range(n):
                cmd(f'monitor mouse {dx} {dy}'); cmd('monitor fields 1')
            cmd('monitor fields 4')
            rows.append(dict(motion=(dx*n, dy*n), **state()))
            shot(f'flight-{len(rows)-1}')
            drawn, ok = pixels(rows[-1], f'flight-{len(rows)-1}')
            rows[-1].update(drawn=len(drawn), on_screen=ok)
        # The world tick's ramps can lag the pointer by a call. Right: yaw +;
        # down: pitch - (stick back); full deflection +-9 at the limits.
        r = rows
        assert r[0]['view'] == 0 and r[0]['control'] == 0 and r[1]['yaw'] > 0 and r[1]['pitch'] == 0 and r[2]['pitch'] < 0, r
        assert (r[3]['pitch'], r[3]['yaw']) == (-9, 9) and (r[4]['pitch'], r[4]['yaw']) == (9, -9), r
        ptr = Pointer(tuple(r[1]['aperture']))
        for x in r[1:]:
            # Sprite 7 where the model's pointer is; its lines are the PC
            # pointer's, in colour 3 (both planes), less the pixels over the
            # cockpit, and they are on screen in its colour.
            ptr.move(*x['motion'])
            assert x['pointer'] == (ptr.x, ptr.y) and x['stick'] == ptr.stick(), (x, ptr.x, ptr.y)
            assert x['number'] == 7 and x['control'] != 0 and x['sprite'] == ptr.sprite(), x
            assert all(v >> 16 == v & 0xffff and v >> 16 & ~POINTER[i] == 0 for i, v in enumerate(x['lines'])), x
            assert x['on_screen'], x
            if copper:
                assert all(v & 0x0f == 12 for v in x['bplcon4']), x
        # Half way right, then as far down: the same pixels on both axes.
        w, h, cx, cy, left, top = r[1]['aperture']
        assert r[1]['sprite'] == (cx+80-5, cy-4) and r[2]['sprite'] == (cx+80-5, cy+26-4), r
        assert r[1]['drawn'] > 0 and r[2]['drawn'] > 0, r
        # Bottom right: under the aperture's last row, wholly behind the cockpit.
        # Top left: the aperture's corner; the parts outside it are over the
        # cockpit (all of it in the Hornet, behind the canopy strut). Then right
        # along the top edge, where its lower half shows under the canopy frame.
        assert r[3]['sprite'] == (left+w-1-5, top+h-1+13-4) and r[3]['drawn'] == 0, r[3]
        assert r[4]['sprite'] == (left-5, top-4), r[4]
        assert all(v >> 16 & 0xf000 == 0 for v in r[4]['lines']), r[4]
        assert r[5]['sprite'][1] == top-4 and r[5]['sprite'][0] > cx and r[5]['drawn'] > 0, r[5]
        assert all(v == 0 for x in r[4:] for v in x['lines'][:4]), r[4:]
        return rows

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
        field = a4+game['field']
        pos, sprite = game['pointer']
        steps = None
        if not a.direct_flight:
            # Intro: the left button where modal_live_check presses Esc.
            for wait, done in game['intro']:
                until(h0+wait)
                cmd('monitor input JOY1_FIRE_BUTTON 1')
                until(h0+done)
                cmd('monitor input JOY1_FIRE_BUTTON 0')
            rows['intro_skipped_by_left_button'] = True
            menu, chosen = game['menu']
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
            if a.flight and ocs:
                # OCS starts over the absent Secret Missions option; Vega's
                # rectangle ends at y 89.
                for _ in range(10):
                    cmd('monitor mouse 0 -4'); cmd('monitor fields 1')
                cmd('monitor fields 10')
                until(h0+menu)
                assert number(f'*(short*){a4+pos+2:#x}') <= 85, 'pointer not over Vega'
            rows['clicks'] = [click()]
            assert rows['clicks'] == ['selected'], rows['clicks']
            rows['menu_selected_by_click'] = True
        if a.flight:
            rows['flight'] = flight()
            print(json.dumps(rows['flight']))
        if a.name_entry:
            rows['name_entry'] = name_entry()
            # The language's enhanced (or original) modes were selected, and
            # the enhanced flight clock ran the simulator flight.
            sy = {n: int(o, 16) for o, n in re.findall(r'^([0-9A-F]{8}) (\S+)$', (a.build/'slave.lst').read_text(), re.M)}
            sb = layout['slave']
            state = dict(german=number(f'*(short*){sb+sy["release_german"]:#x}'),
                         mode=number(f'*(int*){sb+0x1de4:#x}'),
                         completed=number(f'*(int*){sb+sy["timing_completed"]:#x}'))
            rows['slave_state'] = state
            assert state['german'] == (a.german and (1 if a.original_mode else 2)), state
            assert state['mode'] == (0 if a.original_mode else 3), state
            assert (state['completed'] > 0) != a.original_mode, state
        (out/'report.json').write_text(json.dumps(dict(complete=True, variant=a.variant, german=a.german, original_mode=a.original_mode, setup=a.setup,
            slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(), **rows), indent=2)+'\n')
        print(json.dumps(dict(complete=True, sprite_steps=steps)))
    finally:
        stop()


if __name__ == '__main__':
    main()
