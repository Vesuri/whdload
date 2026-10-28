#!/usr/bin/env python3
"""Where a C2 window's time goes: inclusive cycles per routine from a c2_capture profile.

  c6_profile.py CAPTURE [--out tmp/...json]

CAPTURE is a c2_capture directory with trace.bin, its chip (and fast or slow) dumps,
the slave listing symbols and the hunk bases. Emulator figures, not hardware timings.
"""
import argparse
import collections
import json
from pathlib import Path
import struct

import _amigaxdev  # noqa: F401
from amigaxdev import barto
from race_profile import StackReduction, image

# Native call targets of the live loop (A3) and the renderer's leaves.
NATIVE = {
    'replay checkpoint h0+396AC': (0, 0x396ac), 'input masks h0+64': (0, 0x64),
    'controller h0+34D24': (0, 0x34d24), 'control edges h0+3BBF6': (0, 0x3bbf6),
    'control ring h0+39654': (0, 0x39654), 'pause/view keys h0+3B5DE': (0, 0x3b5de),
    'session h0+3B346': (0, 0x3b346), 'car update h0+2AC14': (0, 0x2ac14),
    'camera/view h0+3BF96': (0, 0x3bf96), 'background rebuild h0+3C55C': (0, 0x3c55c),
    'camera/projection h0+34028': (0, 0x34028), 'scene h2+280F6': (2, 0x280f6),
    'clocks h0+258A2': (0, 0x258a2), 'cockpit UI h0+39542': (0, 0x39542),
    'HUD h0+2DD74': (0, 0x2dd74),
}
SLAVE = ('c2_live_head', 'c2_acquire', 'c2_drain', 'c2_scene_call', 'c2_repeat_picture',
         'c2_publish', 'c2_hud_flush', 'c2_pacer', 'c2_fill', 'c2_sprite', 'c2_clear',
         'c2_sky', 'c2_sides', 'c2_lights', 'c2_hands', 'c2_blit_queue', 'c2_hud_enqueue')


def report(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    extra = lambda name: (root/name).read_bytes() if (root/name).exists() else b''
    trace = barto.load(str(root/'trace.bin'))
    trace.chip = image((root/'chip.bin').read_bytes(), extra('fast.bin'), extra('slow.bin'))
    red = StackReduction()
    red.feed(trace)
    fields = len(red.fields)
    cycles = sum(f['cycles'] for f in red.fields)
    ms = fields*20/cycles                       # per emulated cycle, in milliseconds
    symbols = {k: int(v, 16) if isinstance(v, str) else v for k, v in meta['symbols'].items()}
    base, bases = meta['slave_base'], meta['hunk_bases']
    targets = {name: bases[h]+offset for name, (h, offset) in NATIVE.items()}
    targets.update({name: base+symbols[name] for name in SLAVE if name in symbols})
    inclusive = collections.Counter()
    by_pc = {pc: name for name, pc in targets.items()}
    for stack, c in red.stacks.items():
        for name in {by_pc[pc] for pc in stack if pc in by_pc}:
            inclusive[name] += c
    rows = {}
    for name, pc in targets.items():
        calls = red.counts.get(pc, 0)
        rows[name] = dict(calls=calls, ms_per_field=inclusive[name]*ms/fields,
                          share=inclusive[name]/cycles,
                          ms_per_call=inclusive[name]*ms/calls if calls else None)
    # Slave self time outside any listed call: the observe/wait loop in c2_live_head.
    end = base+symbols['c2_beam_max']
    slave_self = sum(c for pc, c in red.self.items() if base <= pc < end)
    return dict(setup=meta['setup'], profile_tick=meta.get('profile_tick'), fields=fields,
                cycles_per_field=cycles/fields, slave_self_share=slave_self/cycles,
                routines=dict(sorted(rows.items(), key=lambda kv: -kv[1]['share'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--out')
    args = parser.parse_args()
    result = report(args.capture)
    text = json.dumps(result, indent=2)+'\n'
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(text)
    print(text)
