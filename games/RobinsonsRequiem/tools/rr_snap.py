#!/usr/bin/env python3
"""Machine snapshots at the landscape call: rr_snap.py OUT [N] [GAP]

rr_prof.py's workload (its Session: the direct start, the avion.DO/.CO open, 150 fields,
then keypad 9 held; VARIANT, SETUP and BUILD through the environment as for rr_prof.py, by
default BUILD=profile; the ECS game with VARIANT=RobinsonsRequiem SETUP=custom), then N
times (default 4), GAP fields apart (default 40): a breakpoint at the landscape's entry
(hunk 1 +$d88c in the AGA game, +$bee2 in the ECS one, once per frame), and at it the
registers (d0-a6 from the stack after the entry's movem) and memory (chip and fast: the AGA machine's $0-$1fffff and $200000-$9fffff,
the ECS one's $0-$fffff and $200000-$3fffff) into OUT/snap-<i>.bin with OUT/snap-<i>.json
(the variant, the registers, the hunk bases, the slave's address). tools/rr_land.py runs
the landscape from them under Unicorn. The snapshots are game bytes: tmp/ only.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_prof import PROFILE_SLAVE, Session, hunks  # noqa: E402

# the landscape's entry in hunk 1 and the machine's memory, by variant
LAND = {'RobinsonsRequiemAGA': 0xd88c, 'RobinsonsRequiem': 0xbee2}
REGIONS = {'RobinsonsRequiemAGA': [(0, 0x200000), (0x200000, 0xa00000)],
           'RobinsonsRequiem': [(0, 0x100000), (0x200000, 0x400000)]}
REGS = ['d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7',
        'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'fp', 'sp', 'ps', 'pc']


def main():
    out = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    gap = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    s = Session(out)
    try:
        variant = s.env['VARIANT']
        land, regions = LAND[variant], REGIONS[variant]
        base = s.to_open()[0]
        s.fields(150)
        bases = hunks(s, base)
        s.cmd('monitor key 3f 1')
        for i in range(n):
            s.fields(gap)
            s.cmd(f'break *{bases[1] + land:#x}')
            s.g.cmd('continue', timeout=600)
            s.cmd('delete')
            regs = {}
            for r in REGS:
                regs[r] = int(s.g.cmd(f'info registers {r}').split()[1], 16)
            if regs['pc'] != bases[1] + land:
                raise RuntimeError(f'not at the landscape: pc {regs["pc"]:#x}')
            mem = b''.join(s.read(a, b - a) for a, b in regions)
            # gdb's fp is not the raw a6: d0-a6 as the entry's movem.l d0-a6,-(sp) saves
            # them (the stack below the entry's pointer is not compared)
            if s.read(regs['pc'], 4) != bytes.fromhex('48e7fffe'):
                raise RuntimeError('the landscape does not start with movem.l d0-a6,-(sp)')
            s.cmd(f'break *{bases[1] + land + 4:#x}')
            s.g.cmd('continue', timeout=600)
            s.cmd('delete')
            sp = int(s.g.cmd('info registers sp').split()[1], 16)
            if sp != regs['sp'] - 60:
                raise RuntimeError(f'the movem left sp {sp:#x}')
            saved = s.read(sp, 60)
            for k, r in enumerate(REGS[:15]):
                regs[r] = int.from_bytes(saved[4 * k:4 * k + 4], 'big')
            (out / f'snap-{i}.bin').write_bytes(mem)
            (out / f'snap-{i}.json').write_text(json.dumps(dict(
                variant=variant, regs=regs, hunks=[hex(b) for b in bases], regions=regions,
                slave=hex(int.from_bytes(s.read(PROFILE_SLAVE, 4), 'big'))), indent=1) + '\n')
            print(f'snap-{i}: field {s.field}', flush=True)
        s.cmd('monitor key 3f 0')
    finally:
        s.quit()


if __name__ == '__main__':
    main()
