#!/usr/bin/env python3
"""Dump chip RAM and the slave's expansion memory from a running game.

  SLAVE=tmp/build/Mercenary3.verify.Slave WHD_ARGS='CUSTOM5=0 CUSTOM1=...' \\
  python3 tools/memory_dump.py OUTDIR

Boots like the route tools (AMIGA_SETUP, SLAVE, WHD_ARGS, BOOT_TIMEOUT), stops at the
verified entry and writes OUTDIR/chip (512 KB from 0), OUTDIR/exp (EXPSIZE bytes, default
the slave's $48000, from ws_ExpMem) and OUTDIR/expmem.txt. Needs a VERIFY slave (it finds
ws_ExpMem through the publication counter block). For tools/translate.py --dump/--check.
Dumps hold game bytes: keep them in tmp/.
"""
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_runtime import session, word  # noqa: E402
from route_profile import slave_code, SLAVE  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    size = int(os.environ.get('EXPSIZE', '0x48000'), 16)
    with session(float(os.environ.get('BOOT_TIMEOUT', '120'))) as (g, _):
        base = g.publication_counter - (slave_code(SLAVE).index(b'M3PUB001') + 8)
        exp = (word(g, base + 0x20) << 16) | word(g, base + 0x22)
        # gdb splits unquoted paths at spaces: dump with paths relative to the cwd.
        chip, expf = (os.path.relpath(out / n) for n in ('chip', 'exp'))
        g.cmd(f'dump binary memory {chip} 0 0x80000', timeout=120)
        g.cmd(f'dump binary memory {expf} {exp:#x} {exp + size:#x}', timeout=120)
    (out / 'expmem.txt').write_text(f'{exp:#x}\n')
    print(f'wrote {out} (ws_ExpMem {exp:#x})')


if __name__ == '__main__':
    main()
