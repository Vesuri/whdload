#!/usr/bin/env python3
"""Build the VERIFY slave's input tape (whdload/tape.s) from a text script.

  python3 tools/tape.py SCRIPT OUT        e.g. tools/tapes/load.txt tmp/tapes/load.tape

Script lines: `FIELDS X Y [BUTTONS]`.  The tape holds pointer position (X,Y) and BUTTONS
(`-`, `L`, `R` or `LR`) for FIELDS PAL fields; FIELDS 0 holds forever (put it last).
X/Y are written to the game window's MouseX/MouseY (window-relative, lores pixels).  `#` starts a comment.
Run the game with SLAVE=<verify build> WHD_ARGS=CUSTOM5=1 TAPE=OUT JOY0=none.
"""
import struct, sys

out = b''
for n, line in enumerate(open(sys.argv[1]), 1):
    f = line.split('#')[0].split()
    if not f:
        continue
    fields, x, y = (int(v, 0) for v in f[:3])
    b = f[3] if len(f) > 3 else '-'
    assert set(b) <= set('LR-'), f'line {n}: buttons {b!r}'
    out += struct.pack('>HhhH', fields, x, y, ('L' in b) | ('R' in b) << 1)
assert out and struct.unpack_from('>H', out, len(out) - 8)[0] == 0, 'last entry must hold forever (FIELDS 0)'
assert len(out) <= 8192
open(sys.argv[2], 'wb').write(out)
print(f'{sys.argv[2]}: {len(out) // 8} entries')
