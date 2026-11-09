#!/usr/bin/env python3
"""Without CUSTOM2, BH equals the original but for Galahad's manual-check patch.

  python3 tools/pl_check.py [SLAVE [LISTING]]     (default: the release build)

The slave applies pl_bh always and timing.s's _pl_timing only with CUSTOM2=1
(_cb_dosLoadSeg, timing_patch).  This decodes pl_bh from the built slave and checks it is
v1.0's patch and nothing else: PL_PS $25be (the typed character is stored as the expected
one) and PL_W $25c4 = $6078 (bra.s ok).
"""
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _amigaxdev  # noqa: F401,E402
from amigaxdev.patchlist import decode, slave_code  # noqa: E402

slave = sys.argv[1] if len(sys.argv) > 1 else 'tmp/build/release/Battlehawks1942.Slave'
listing = sys.argv[2] if len(sys.argv) > 2 else str(Path(slave).with_suffix('.lst'))
syms = {m[1]: int(m[0], 16) for m in
        re.findall(r'^([0-9A-F]{8}) (\S+)$', Path(listing).read_text(encoding='latin1'), re.M)}
got = [(adr, cmd, arg if cmd != 'PS' else arg.split(':')[1])
       for adr, cmd, arg in decode(slave_code(slave), syms['pl_bh']) if cmd != 'END']
want = [(0x25be, 'PS', f'{syms["manual_check"]:04x}'), (0x25c4, 'W', '6078')]
if got != want:
    sys.exit(f'pl_bh is {got}, expected {want}')
print('pl_bh: only the manual-check patch (CUSTOM2 off leaves BH as v1.0 does)')
