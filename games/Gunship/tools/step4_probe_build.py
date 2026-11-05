"""Reuse the flight-entry probe for focused step-4 reported-state checks."""
from pathlib import Path
root=Path(__file__).resolve().parents[1];src=root/'src';out=root/'tmp/build'
loop=(src/'timing-live-loop.i').read_text()
needle=' movea.l timing_runtime_arena(pc),a0\n'
insert=''' movea.l RT_HUNKS+24(a0),a5
 move.w #2,$3b96(a5)
'''
assert loop.count(needle)==1
(out/'step4-damage-loop.i').write_text(loop.replace(needle,needle+insert))
slave=(src/'GunshipHD.s').read_text().replace('include "timing-live-loop.i"','include "'+str(out/'step4-damage-loop.i')+'"')
(out/'step4-damage.s').write_text(slave)
p=root/'tools/capture_damage_yaw.py';s=p.read_text();s=s.replace(" s.cmd(f'set {{unsigned short}}{h6+0x3b96:#x} = 2')", " assert s.read(h6+0x3b96,2)==b'\\0\\x02'");p.write_text(s)
