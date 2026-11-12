#!/usr/bin/env python3
"""Drive Encounter in FS-UAE through the gdb stub (common/tools/game_server.py).

  python3 tools/encounter.py serve          boot (common/run.sh DEBUG=1), attach gdb, run; listen
  python3 tools/encounter.py <command...>   send one command to the running server, print the reply

Commands are the shared server's (AmigaXDev amigaxdev.gdbserve): stop, cont, gdb <text>,
shot <png>, profile <fields> <bin>, wait <s>, until <addr>, quit; and this game's

  hash STEPS ADDR OUT RANGES [TRAP]
                               run to ADDR STEPS times (a breakpoint, emulated time is not
                               disturbed) and at each hit append the memory RANGES
                               (LO-HI,LO-HI,... hex, end exclusive) to OUT.bin, the field
                               counter $11DEA to OUT.fields; leaves the CPU stopped at the
                               last hit; with TRAP (the VERIFY slave's trap loop) stops with
                               an error there. tools/route.py's `hash` step and
                               tools/statehash.py use it.

The run options of common/run.sh (SETUP, BUILD, SLAVE, WHD_ARGS, INSTANCE, WARP, WINDOW, ...)
apply to serve; SLAVE=original boots the installed v1.2 slave.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

FIELD_COUNTER = 0x11DEA


def hash_steps(server, g, rest):
    steps, addr, out, rngs, *trap = rest.split()
    steps = int(steps)
    rngs = [tuple(int(x, 16) for x in r.split('-')) for r in rngs.split(',')]
    out = Path(out)
    tmp = out.with_suffix('.part')
    g.stop()
    g.cmd('delete')
    g.cmd(f'break *{addr}')
    if trap:
        g.cmd(f'break *{trap[0]}')
    fields = []
    with open(out.with_suffix('.bin'), 'wb') as f:
        for _ in range(steps):
            r = g.cmd('continue', timeout=600)
            if 'Breakpoint' not in r:
                g.cmd('delete')
                return f'ERROR not at the breakpoint: {r[-300:]}'
            if trap and int(g.cmd('x/1xw $pc').split(':')[0], 16) == int(trap[0], 16):
                pc = g.cmd(f'x/1xw {int(trap[0], 16) - 4:#x}').split(':')[1].split()[0]
                g.cmd('delete')
                return f'ERROR VERIFY trap: chip code executed at {pc}'
            for lo, hi in rngs:
                g.cmd(f'dump binary memory {tmp} {lo:#x} {hi:#x}')
                f.write(tmp.read_bytes())
            v = g.cmd(f'x/1xw {FIELD_COUNTER:#x}')
            fields.append(int(v.split(':')[1].split()[0], 16))
    tmp.unlink(missing_ok=True)
    g.cmd('delete')
    out.with_suffix('.fields').write_text(' '.join(map(str, fields)) + '\n')
    return f'{steps} steps, fields {fields[0]}..{fields[-1]}'


server = game_server('enc', commands={'hash': hash_steps})

if __name__ == '__main__':
    server.main(sys.argv[1:])
