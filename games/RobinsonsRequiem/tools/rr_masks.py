#!/usr/bin/env python3
"""The values START's 24-bit masks receive in play: rr_masks.py OUT (docs/internals.md)

rr_prof.py's boot (its Session: the direct start and OPEN's open; the run options through
the environment, VARIANT=RobinsonsRequiem for the ECS game), SETTLE fields (default 150),
then a dprintf at each `andi.l #$ffffff` ("24-bit pointers") printing the register it
masks while keypad 9 is held for TURN fields (default 300) and keypad 8 for WALK (default
900), counted at the VBL, and OUT/end.png after them. Prints, per site, the
values, their high bytes and the range of their low 24 bits; OUT/masks.log keeps every
value, and START's fast pool variables (hunk 1 +$f0, ECS +$e4).
"""
import collections
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rr_prof  # noqa: E402

# (hunk, offset, register) of each andi.l #$ffffff
SITES = {
    'RobinsonsRequiemAGA': [
        (1, 0x42e8, 'd2'), (1, 0x8d72, 'd1'), (1, 0x8f06, 'd1'), (1, 0x93be, 'd2'),
        (1, 0x93da, 'd2'), (1, 0xa7e0, 'd3'), (1, 0xb04e, 'd0'), (1, 0xb072, 'd0'),
        (1, 0xea42, 'd0'), (2, 0x2100, 'd2')],
    'RobinsonsRequiem': [
        (1, 0x29ac, 'd2'), (1, 0x7352, 'd1'), (1, 0x74e6, 'd1'), (1, 0x799e, 'd2'),
        (1, 0x79ba, 'd2'), (1, 0x8e4a, 'd3'), (1, 0x96b8, 'd0'), (1, 0x96dc, 'd0'),
        (1, 0xd098, 'd0'), (2, 0x147a, 'd2')]}
# START's fast pool variables, three longwords (docs/internals.md, "Memory")
POOL = {'RobinsonsRequiemAGA': 0xf0, 'RobinsonsRequiem': 0xe4}
# the VBL's addq.l #1 to its field count (hunk 1 +$ee6c, ECS +$d4c2)
VBL = {'RobinsonsRequiemAGA': 0x99ea, 'RobinsonsRequiem': 0x7fca}


def main():
    out = Path(sys.argv[1]).resolve()
    s = rr_prof.Session(out)
    try:
        base, _, _ = s.to_open()
        b = rr_prof.hunks(s, base)
        sites = SITES[s.env['VARIANT']]
        s.fields(int(os.environ.get('SETTLE', 150)))
        pool = s.read(b[1] + POOL[s.env['VARIANT']], 12)
        print('fast pool', ' '.join(f'${int.from_bytes(pool[i:i + 4], "big"):08x}'
                                    for i in range(0, 12, 4)), flush=True)
        log = out / 'masks.log'
        s.cmd(f'set logging file {log}')
        s.cmd('set logging overwrite on')
        s.cmd('set logging redirect off')   # on, the Session's replies are lost
        s.cmd('set logging enabled on')
        for hh, oo, r in sites:
            s.cmd(f'dprintf *{b[hh] + oo:#x},"M {hh} {oo:x} %x\\n",${r}')
        # dprintfs print only while gdb continues, not in monitor fields; the phases end at a
        # breakpoint on the VBL's count, its ignore count the fields (an interrupt can land
        # in a dprintf's stop and leave the CPU running)
        for key, n in (('3f', int(os.environ.get('TURN', 300))),
                       ('3e', int(os.environ.get('WALK', 900)))):
            s.cmd(f'monitor key {key} 1')
            s.cmd(f'break *{b[1] + VBL[s.env["VARIANT"]]:#x}')
            s.cmd(f'ignore $bpnum {n - 1}')
            s.g.cmd('continue', timeout=1800)
            s.cmd('delete $bpnum')
            s.cmd(f'monitor key {key} 0')
        s.cmd('set logging enabled off')
        s.cmd('delete')
        s.shot('end.png')
    finally:
        s.quit()
    seen = collections.defaultdict(list)
    for line in log.read_text(errors='replace').splitlines():
        p = line.split()
        if len(p) == 4 and p[0] == 'M':
            seen[(int(p[1]), int(p[2], 16))].append(int(p[3], 16))
    for h, o, _ in sites:
        v = seen.get((h, o), [])
        if not v:
            print(f'hunk {h} +${o:x}: none')
            continue
        low = [x & 0xffffff for x in v]
        high = collections.Counter(x >> 24 for x in v)
        print(f'hunk {h} +${o:x}: {len(v)}, low 24 bits ${min(low):06x}-${max(low):06x}, '
              'high bytes ' + ' '.join(f'${k:02x}:{c}' for k, c in sorted(high.items())))
    print('total', sum(len(v) for v in seen.values()))


if __name__ == '__main__':
    main()
