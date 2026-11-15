#!/usr/bin/env python3
"""The game's script objects and how often they run: rr_objects.py OUT [EVENTS]

rr_prof.py's workload (its Session: the direct start, the avion open, 150 fields, then a
key held; the run options through the environment, SLAVE= for another slave,
VARIANT=RobinsonsRequiem for the ECS game), KEY=hex the raw key (default 3f, keypad 9, which
turns the player on the spot; 3e walks forward, none for no key), then after 50 fields a
breakpoint on the scheduler's timed run (hunk 1 AGA +$2590, ECS +$d34: the next run just
computed) for EVENTS runs (default 300), each with the object (its offset in MAIN's object
table, +$ed6c, +$d3c2), its period (-58(a6)), the count it ran by (a3, its next run, less the
period: the VBL count, or in the AGA game the slave's world count W in 3D mode since plan
step 7) and the VBL count (+$ee6c, +$d4c2). docs/internals.md, "Objects and the scheduler",
has the layout; the ECS game's MAIN loop is the AGA's instruction for instruction.

Prints per object: its program's slot (the first word of its header, -20(a6)) and file
(the name MAIN's load op `45 <slot> name.AO` gives that slot, searched in chip memory and
the fast pool; MAIN for slot 0), its period, its runs, the mean interval in fields of the
count it ran by and their histogram, and the mean interval of the VBL count.
POSE=1 also reads each object's pose at its runs (the position words +0/+8/+16 and the
angles +24/+32/+40, before the run) and prints the largest step between runs.
OUT/objects.json keeps the events. Breakpoints stop the emulation, not its time.
"""
import collections
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_prof import Session, hunks  # noqa: E402

# hunk 1: the scheduler's move.l a3,-62(a6) (the object is running, its next run computed),
# the VBL count and the fast pool (address, size); the slave's chip memory
SITES = {'RobinsonsRequiemAGA': dict(sched=0x2590, vbl=0xee6c, pool=0xf0, chip=0x1a0000),
         'RobinsonsRequiem': dict(sched=0xd34, vbl=0xd4c2, pool=0xe4, chip=0x100000)}


def main():
    out = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    key = os.environ.get('KEY', '3f')
    pose = os.environ.get('POSE') == '1'
    s = Session(out)

    def long(a):
        return int.from_bytes(s.read(a, 4), 'big')
    try:
        site = SITES[s.env['VARIANT']]
        base = s.to_open()[0]
        s.fields(150)
        h1 = hunks(s, base)[1]
        if key != 'none':
            s.cmd(f'monitor key {key} 1')
        s.fields(50)
        s.cmd(f'break *{h1 + site["sched"]:#x}')
        ev = []
        for _ in range(n):
            s.g.cmd('continue', timeout=300)
            a6 = int(s.g.cmd('info registers a6').split()[1], 16)
            d5 = int(s.g.cmd('info registers d5').split()[1], 16) & 0xffff
            a3 = int(s.g.cmd('info registers a3').split()[1], 16)
            per = int.from_bytes(s.read(a6 - 58, 2), 'big', signed=True)
            e = [d5, a6, per, (a3 - per) & 0xffffffff, long(h1 + site['vbl'])]
            if pose:
                b = s.read(a6, 42)
                e.append([int.from_bytes(b[o:o + 2], 'big', signed=True) for o in (0, 8, 16, 24, 32, 40)])
            ev.append(e)
        s.cmd('delete')
        if key != 'none':
            s.cmd(f'monitor key {key} 0')
        slots = {a6: int.from_bytes(s.read(long(a6 - 20), 2), 'big') for _, a6, *_ in ev}
        pool, size = long(h1 + site['pool']), long(h1 + site['pool'] + 4)
        mem = s.read(0, site['chip']) + (s.read(pool, size) if size else b'')
    finally:
        s.quit()
    names = {}
    for slot in set(slots.values()):
        pat = re.escape(bytes([0x45, slot >> 8, slot & 0xff])) + rb'([A-Za-z0-9_]{1,12})\.AO\0'
        found = sorted({m.group(1).decode() for m in re.finditer(pat, mem)})
        names[slot] = '/'.join(found) or ('MAIN' if slot == 0 else '?')
    runs = collections.defaultdict(list)
    poses = collections.defaultdict(list)
    for d5, a6, per, count, vbl, *p in ev:
        runs[(d5, a6)].append((count, per, vbl))
        if p:
            poses[(d5, a6)].append(p[0])
    span = ev[-1][3] - ev[0][3]
    print(f'{len(ev)} runs in {span} fields of the count, {ev[-1][4] - ev[0][4]} VBL (KEY={key})')
    print(' obj slot file         period runs interval    VBL  intervals (fields: count)')
    for (d5, a6), r in sorted(runs.items()):
        gaps = [b[0] - a[0] for a, b in zip(r, r[1:])]
        vgaps = [b[2] - a[2] for a, b in zip(r, r[1:])]
        mean = f'{sum(gaps) / len(gaps):8.2f} {sum(vgaps) / len(vgaps):6.2f}' if gaps else '       -      -'
        pers = '/'.join(str(p) for p in sorted({p for _, p, _ in r}))
        hist = ' '.join(f'{g}:{c}' for g, c in sorted(collections.Counter(gaps).items()))
        print(f'{d5:4d} {slots[a6]:4d} {names[slots[a6]]:12s} {pers:>6s} {len(r):4d} {mean}  {hist}')
    if pose:
        print(' obj file         largest step: x y z, angles (degrees, the short way)')
        for k, ps in sorted(poses.items()):
            st = [max((abs(b[i] - a[i]) for a, b in zip(ps, ps[1:])), default=0) for i in range(3)]
            st += [max((abs((b[i] - a[i] + 180) % 360 - 180) for a, b in zip(ps, ps[1:])), default=0)
                   for i in range(3, 6)]
            print(f'{k[0]:4d} {names[slots[k[1]]]:12s} {st}')
    (out / 'objects.json').write_text(json.dumps(dict(env=s.env, names=names, events=ev,
                                                      slots={hex(k): v for k, v in slots.items()})) + '\n')


if __name__ == '__main__':
    main()
