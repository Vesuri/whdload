#!/usr/bin/env python3
"""Machine snapshots at the ECS game's landscape call: rr_snap.py OUT [N] [GAP]

rr_prof.py's workload (its Session: the direct start, the avion.CO open, 150 fields, then
keypad 9 held; VARIANT=RobinsonsRequiem SETUP=custom and BUILD through the environment, by
default BUILD=profile), then N times (default 4), GAP fields apart (default 40): a
breakpoint at the landscape's entry (hunk 1 +$bee2, once per frame), and at it the
registers and memory (chip $0-$fffff, fast $200000-$3fffff) into OUT/snap-<i>.bin with
OUT/snap-<i>.json (the registers, the hunk bases, the slave's address). tools/rr_ecsland.py
runs the landscape from them under Unicorn. The snapshots are game bytes: tmp/ only.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('VARIANT', 'RobinsonsRequiem')
os.environ.setdefault('SETUP', 'custom')
from rr_prof import PROFILE_SLAVE, Session, find_hunk0, hunks, layout  # noqa: E402

LAND = 0xbee2
REGIONS = [(0, 0x100000), (0x200000, 0x400000)]
REGS = ['d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7',
        'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'fp', 'sp', 'ps', 'pc']


def main():
    out = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    gap = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    s = Session(out)
    try:
        if s.env['VARIANT'] != 'RobinsonsRequiem':
            raise SystemExit('the ECS game only')
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
        bases = hunks(s, base)
        s.cmd('monitor key 3f 1')
        for i in range(n):
            s.fields(gap)
            s.cmd(f'break *{bases[1] + LAND:#x}')
            s.g.cmd('continue', timeout=600)
            s.cmd('delete')
            regs = {}
            for r in REGS:
                regs[r] = int(s.g.cmd(f'info registers {r}').split()[1], 16)
            if regs['pc'] != bases[1] + LAND:
                raise RuntimeError(f'not at the landscape: pc {regs["pc"]:#x}')
            mem = b''.join(s.read(a, b - a) for a, b in REGIONS)
            (out / f'snap-{i}.bin').write_bytes(mem)
            (out / f'snap-{i}.json').write_text(json.dumps(dict(
                regs=regs, hunks=[hex(b) for b in bases], regions=REGIONS,
                slave=hex(int.from_bytes(s.read(PROFILE_SLAVE, 4), 'big'))), indent=1) + '\n')
            print(f'snap-{i}: field {s.field}', flush=True)
        s.cmd('monitor key 3f 0')
    finally:
        s.quit()


if __name__ == '__main__':
    main()
