#!/usr/bin/env python3
"""Isolated A4000 wait experiment; requires DMA/pixel and latency acceptance."""
from pathlib import Path
import shutil
src=Path('tmp/fixtures/render-beam/source');dst=Path('tmp/fixtures/display-wait/source');assert not dst.exists();shutil.copytree(src,dst)
p=dst/'simulation_schedule.s';s=p.read_text();needle='.supported:\n addq.w #1,d7';assert s.count(needle)==1;s=s.replace(needle,'''.supported:
 ; Diagnostic only: native publication clears this, native VBL sets it.
 ; Wait before importing pending physics so the next render uses fresh input.
 cmp.w #50,-$15fa(a4)
 bne .display_ready
.wait_display:
 tst.w $d28(a4)
 beq .wait_display
.display_ready:
 addq.w #1,d7''');p.write_text(s);print(dst)
