#!/usr/bin/env python3
from pathlib import Path
import shutil
src=Path('src');dst=Path('tmp/fixtures/render-beam/source');assert not dst.exists();shutil.copytree(src,dst)
p=dst/'4DSportsDrivingHD.s';s=p.read_text();needle='    PL_PSS $70E0,sim_schedule_poll,2';assert s.count(needle)==1;p.write_text(s.replace(needle,needle+'\n    PL_PSS $7140,sim_render_beam_probe,2'))
p=dst/'simulation_schedule.s'
with p.open('a') as f:f.write('''
; Isolated VERIFY-only observation of actual render-start beam/buffer state.
 IFND VERIFY
 FAIL "Render beam diagnostic must not enter playable builds"
 ENDC
sim_render_beam_probe:
 movem.l d0-d3/a0-a2,-(sp)
 moveq #0,d0
 addx.w d0,d0
 move.w d0,-(sp)
 lea sim_render_beam_count(pc),a2
 move.l (a2),d1
 move.l d1,d0
 and.l #15,d0
 mulu #24,d0
 lea sim_render_beam_records(pc),a0
 adda.l d0,a0
 move.l sim_clock_fields(pc),(a0)+
 move.w -$940(a4),(a0)+
 moveq #0,d0
 move.b $45(a4),d0
 move.w d0,(a0)+
 move.l -$2de(a4),a1
 move.l 6(a1),d3
 move.l $dff004,d2
sim_render_beam_read:
 move.l d2,(a0)+
 move.l d3,(a0)+
 move.l 10(a1),(a0)+
 move.l d1,(a0)
 addq.l #1,(a2)
 move.w (sp)+,d0
 lsr.w #1,d0
 movem.l (sp)+,d0-d3/a0-a2
 move.w -$a88(a4),d0
 cmp.w -$a8a(a4),d0
 rts
 even
 dc.b "4DDSPBM!"
 dc.w 1,24
sim_render_beam_count: dc.l 0
sim_render_beam_records: dcb.b 16*24,0
''')
print(dst)
