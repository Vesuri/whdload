#!/usr/bin/env python3
"""Build the VERIFY slave's input tape (whdload/tape.s) from a text script.

  python3 tools/tape.py SCRIPT OUT        e.g. tools/tapes/load.txt tmp/tapes/load.tape

Script lines: `FIELDS X Y [BUTTONS]`.  The tape holds pointer position (X,Y) and BUTTONS
(`-` or any of `L`, `R`, `A`, `W`, `D`) for FIELDS PAL fields; FIELDS 0 holds forever (put it last).
`A` marks the anchor: the slave runs `_tape_anchor` on the entry's first field, where
tools/fixed_window.sh breaks.  `W` waits on game state instead of counting: FIELDS is then a
button id (0: any), and the entry holds until the game hit-tests a button list that has that
button at (X,Y) (whdload/tape.s).
`H` waits until the heading h11:08c28 equals FIELDS, while holding X/Y/BUTTONS.
It shares the wait bit with W and uses bit 13 to select the heading condition.
`D` with `A` requests the TIMING_STUDY drawing delay only upon reaching the anchor.
This allows paired runs to use identical WHDLoad options before the anchor.
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
    assert set(b) <= set('LRAWHD-'), f'line {n}: buttons {b!r}'
    assert 'D' not in b or 'A' in b, f'line {n}: D requires A'
    out += struct.pack('>HhhH', fields, x, y, ('L' in b) | ('R' in b) << 1 | ('D' in b) << 12 | ('H' in b) << 13 | ('W' in b or 'H' in b) << 14 | ('A' in b) << 15)
last = struct.unpack_from('>HhhH', out, len(out) - 8) if out else (1, 0, 0, 0)
assert last[0] == 0 and not last[3] & 0x4000, 'last entry must hold forever (FIELDS 0, no W)'
assert len(out) <= 8192
open(sys.argv[2], 'wb').write(out)
print(f'{sys.argv[2]}: {len(out) // 8} entries')
