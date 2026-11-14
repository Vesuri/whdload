#!/usr/bin/env python3
"""The AGA game's script objects and how often they run: rr_objects.py OUT [EVENTS]

rr_prof.py's workload (its Session: the direct start, the avion.DO open, 150 fields, then a
key held; the run options through the environment, SLAVE= for another slave), KEY=hex the
raw key (default 3f, keypad 9, which turns the player on the spot; 3e walks forward, none for no key), then
after 50 fields a breakpoint on the scheduler's timed run (hunk 1 +$2590, the next run just
computed) for EVENTS runs (default 300), each with the object (its offset in MAIN's object
table, +$ed6c), its period (-58(a6)) and the VBL count (+$ee6c). docs/internals.md, "Objects
and the scheduler", has the layout.

Prints per object: its program's slot (the first word of its header, -20(a6)) and file
(the name MAIN's load op `45 <slot> name.AO` gives that slot, searched in chip memory and
the fast pool; MAIN for slot 0), its period, its runs, the mean interval in fields and their histogram.
OUT/objects.json keeps the events. Breakpoints stop the emulation, not its time.
"""
import collections
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_prof import Session, find_hunk0, hunks, layout  # noqa: E402

SCHED = 0x2590      # move.l a3,-62(a6): the object is running, its next run computed
OBJTAB = 0xed6c
VBL = 0xee6c
POOL = 0xf0         # the fast pool: address, size
CHIP = 0x1a0000


def main():
    out = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    key = os.environ.get('KEY', '3f')
    s = Session(out)

    def long(a):
        return int.from_bytes(s.read(a, 4), 'big')
    try:
        if s.env['VARIANT'] != 'RobinsonsRequiemAGA':
            raise SystemExit('the AGA game only')
        base = None
        while base is None:
            if s.field > 3000:
                raise TimeoutError('START hunk 0 not found in 3000 fields')
            s.fields(10)
            try:
                base = find_hunk0(s.g, s.env['VARIANT'])
            except RuntimeError:
                pass
        open_at = base + layout(s.env['VARIANT'])['calls']['open']
        s.cmd(f'break *{open_at:#x}')
        s.cmd('condition $bpnum *(unsigned int *)$d1 == 0x6176696f')
        s.g.cmd('continue', timeout=1200)
        s.cmd('delete')
        s.fields(150)
        h1 = hunks(s, base)[1]
        if key != 'none':
            s.cmd(f'monitor key {key} 1')
        s.fields(50)
        s.cmd(f'break *{h1 + SCHED:#x}')
        ev = []
        for _ in range(n):
            s.g.cmd('continue', timeout=300)
            a6 = int(s.g.cmd('info registers a6').split()[1], 16)
            d5 = int(s.g.cmd('info registers d5').split()[1], 16) & 0xffff
            per = int.from_bytes(s.read(a6 - 58, 2), 'big', signed=True)
            ev.append((d5, a6, per, long(h1 + VBL)))
        s.cmd('delete')
        if key != 'none':
            s.cmd(f'monitor key {key} 0')
        slots = {a6: int.from_bytes(s.read(long(a6 - 20), 2), 'big') for _, a6, _, _ in ev}
        pool, size = long(h1 + POOL), long(h1 + POOL + 4)
        mem = s.read(0, CHIP) + (s.read(pool, size) if size else b'')
    finally:
        s.quit()
    names = {}
    for slot in set(slots.values()):
        pat = re.escape(bytes([0x45, slot >> 8, slot & 0xff])) + rb'([A-Za-z0-9_]{1,12})\.AO\0'
        found = sorted({m.group(1).decode() for m in re.finditer(pat, mem)})
        names[slot] = '/'.join(found) or ('MAIN' if slot == 0 else '?')
    runs = collections.defaultdict(list)
    for d5, a6, per, vbl in ev:
        runs[(d5, a6)].append((vbl, per))
    span = ev[-1][3] - ev[0][3]
    print(f'{len(ev)} runs in {span} fields (KEY={key})')
    print(' obj slot file         period runs interval  intervals (fields: count)')
    for (d5, a6), r in sorted(runs.items()):
        gaps = [b[0] - a[0] for a, b in zip(r, r[1:])]
        mean = f'{sum(gaps) / len(gaps):8.2f}' if gaps else '       -'
        pers = '/'.join(str(p) for p in sorted({p for _, p in r}))
        hist = ' '.join(f'{g}:{c}' for g, c in sorted(collections.Counter(gaps).items()))
        print(f'{d5:4d} {slots[a6]:4d} {names[slots[a6]]:12s} {pers:>6s} {len(r):4d} {mean}  {hist}')
    (out / 'objects.json').write_text(json.dumps(dict(env=s.env, names=names, events=ev,
                                                      slots={hex(k): v for k, v in slots.items()})) + '\n')


if __name__ == '__main__':
    main()
