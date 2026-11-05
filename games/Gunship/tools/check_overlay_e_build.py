from pathlib import Path
import subprocess,os
root=Path(__file__).resolve().parents[1];src=root/'src';out=root/'tmp/build'
s=(src/'timing-cpu-render.i').read_text()
s=s.replace('CPU_VIEW_BYTES EQU 36010','CPU_VIEW_BYTES EQU 76010')
s=s.replace(' lea cpu_render_overlay_ready(pc),a0\n move.w #1,(a0)', ' bsr overlay_compare\n lea cpu_render_overlay_ready(pc),a0\n move.w #1,(a0)')
s+="""
overlay_compare:
 movem.l d0-d7/a0-a6,-(sp)
 movea.l cpu_render_h6(pc),a0
 movea.l $47c4(a0),a2
 lea 8(a2),a2
 movea.l cpu_render_buffer(pc),a0
 adda.l #36010,a0
 moveq #4,d7
.saveplane:
 movea.l (a2)+,a1
 move.w #1800,d6
.saveword:
 move.w (a1)+,(a0)+
 dbf d6,.saveword
 dbf d7,.saveplane
 movea.l cpu_render_rects(pc),a2
 moveq #1,d7
.restore:
 move.l d7,-(sp)
 move.l a2,-(sp)
 movea.l cpu_render_h0(pc),a0
 adda.l #$ab24,a0
 jsr (a0)
 movea.l (sp)+,a2
 move.l (sp)+,d7
 adda.w #12,a2
 dbf d7,.restore
 movea.l cpu_render_h0(pc),a0
 adda.l #$867e,a0
 movea.l (a0),a6
 movea.l (a6),a6
 jsr -228(a6)
 lea overlay_results(pc),a4
 addq.l #1,8(a4)
 movea.l cpu_render_h6(pc),a0
 movea.l $47c4(a0),a2
 lea 8(a2),a2
 movea.l cpu_render_buffer(pc),a0
 adda.l #36010,a0
 moveq #4,d7
.plane:
 movea.l (a2)+,a1
 move.w #1800,d6
.word:
 move.w (a0)+,d0
 cmp.w (a1)+,d0
 beq .same
 addq.l #1,12(a4)
.same:
 dbf d6,.word
 dbf d7,.plane
 movem.l (sp)+,d0-d7/a0-a6
 rts
overlay_results: dc.b "GSEOVL01"
 dc.l 0,0

"""

needle=s[s.index('overlay_compare:'):s.index('overlay_results:')]
needle=needle.replace('overlay_compare:', 'needle_compare:').replace('overlay_results','needle_results').replace('#1800,d6','#3999,d6')
a=needle.index(' movea.l cpu_render_rects(pc),a2')
b=needle.index(' movea.l cpu_render_h0(pc),a0\n adda.l #$867e',a)
needle=needle[:a]+' bsr cockpit_native_erase\n bsr cockpit_native_draw\n'+needle[b:]
needle=needle.replace(' movem.l d0-d7/a0-a6,-(sp)', ' movem.l d0-d7/a0-a6,-(sp)\n movea.l cpu_render_h0(pc),a0\n adda.l #$867e,a0\n movea.l (a0),a6\n movea.l (a6),a6\n jsr -228(a6)',1)
needle=needle.replace(' addq.l #1,12(a4)', """ addq.l #1,12(a4)
 move.l 12(a4),d1
 cmpi.l #16,d1
 bhi .same
 subq.l #1,d1
 lsl.w #3,d1
 lea 16(a4,d1.w),a3
 move.w d7,(a3)+
 move.w d6,(a3)+
 move.w d0,(a3)+
 move.w -2(a1),(a3)
""")
s+=needle+'needle_results: dc.b "GSENDL01"\n dc.l 0,0\n ds.b 128\n'
cockpit=(src/'timing-cockpit.i').read_text().replace(' beq cockpit_native_draw\n rts',' beq cockpit_native_draw\n bra needle_compare')
(out/'needle-check.i').write_text(cockpit)
(out/'cpu-view-check.i').write_text(s)
slave=(src/'GunshipHD.s').read_text().replace('include "timing-cpu-render.i"','include "'+str(out/'cpu-view-check.i')+'"')
slave=slave.replace('include "timing-cockpit.i"','include "'+str(out/'needle-check.i')+'"')
(out/'cpu-view-check.s').write_text(slave)
cmd=[os.environ['VASM'],'-DTIMING_RUNTIME=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym']
for p in [Path(os.environ['AMIGA_INCLUDE']),Path(os.environ['WHDLOAD'])/'Include',Path(os.environ['WHDLOAD'])/'Src',Path(os.environ['WHDLOAD'])/'Src/sources',Path(os.environ['AMIGA_SHARE'])/'ndk/Include_I',src]:cmd+=['-I'+str(p)]
cmd+=['-L',str(out/'cpu-view-check.slave.lst'),'-o',str(out/'cpu-view-check.slave'),str(out/'cpu-view-check.s')]
subprocess.run(cmd,cwd=src,check=True)
