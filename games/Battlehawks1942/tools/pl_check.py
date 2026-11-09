#!/usr/bin/env python3
"""Without CUSTOM2, BH equals the original but for Galahad's manual-check patch and the
cache flush after BH's code generator.

  python3 tools/pl_check.py [SLAVE [LISTING]]     (default: the release build)

The slave applies pl_bh always and timing.s's _pl_timing only with CUSTOM2=1
(_cb_dosLoadSeg, timing_patch).  This decodes pl_bh from the built slave and checks it is
v1.0's patch, PL_PS $25be (the typed character is stored as the expected one) and PL_W
$25c4 = $6078 (bra.s ok), the flush after bh:18360 (PL_PS $170e4 gen_flush, PL_NOP
$170ea) and WaitBlit after BH's RectFill and SetRast stubs (PL_P $1c6c6, $1c6e8), which
change no game state.  pl_span (68040 and 68060) and pl_span_evict (68020
and 68030) replace the span loop's two rts writes and calls with the same sequence and a
flush, or with the written words' instruction-cache lines replaced.
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
got = [(adr, cmd, arg if cmd not in ('P', 'PS') else arg.split(':')[1])
       for adr, cmd, arg in decode(slave_code(slave), syms['pl_bh']) if cmd != 'END']
want = [(0x25be, 'PS', f'{syms["manual_check"]:04x}'), (0x25c4, 'W', '6078'),
        (0x170e4, 'PS', f'{syms["gen_flush"]:04x}'), (0x170ea, 'NOP', '0002'),
        (0x1c6c6, 'P', f'{syms["gfx_rectfill"]:04x}'), (0x1c6e8, 'P', f'{syms["gfx_setrast"]:04x}')]
if got != want:
    sys.exit(f'pl_bh is {got}, expected {want}')
for plist, call in (('pl_span', 'span_call'), ('pl_span_evict', 'span_evict')):
    got = [(adr, cmd, arg if cmd != 'PS' else arg.split(':')[1])
           for adr, cmd, arg in decode(slave_code(slave), syms[plist]) if cmd != 'END']
    want = [(0x1734c, 'PS', f'{syms[call]:04x}'), (0x17352, 'W', '600a'),
            (0x173aa, 'PS', f'{syms[call + "_x8"]:04x}'), (0x173b0, 'W', '600c')]
    if got != want:
        sys.exit(f'{plist} is {got}, expected {want}')
print('pl_bh: only the manual-check patch, the cache flush and the blitter waits (CUSTOM2 off leaves BH as v1.0 does);'
      ' pl_span, pl_span_evict: the span loop with flushes or cache-line evictions')
