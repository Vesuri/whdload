from pathlib import Path
import subprocess,os
root=Path(__file__).resolve().parents[1];src=root/'src';out=root/'tmp/build'
s=(src/'timing-cpu-render.i').read_text();needle=' movea.l cpu_render_buffer(pc),a0\n moveq #4,d7\n.plane:'
probe=''' bsr cpu_view_compare
 movea.l cpu_render_h6(pc),a0
 movea.l $47c4(a0),a2
 lea 8(a2),a2
'''
assert s.count(needle)==1;s=s.replace(needle,probe+needle)
s+='''
cpu_view_compare:
 movem.l d0-d7/a0-a6,-(sp)
 movea.l cpu_render_h0(pc),a6
 movea.l a6,a0
 adda.l #$8524,a0
 move.w #4,(a0)
 movea.l a6,a0
 adda.l #$77b8,a0
 jsr (a0)
 movea.l cpu_render_h0(pc),a6
 movea.l a6,a0
 adda.l #$8524,a0
 move.w #3,(a0)
 movea.l a6,a0
 adda.l #$60a8,a0
 jsr (a0)
 movea.l cpu_render_h0(pc),a6
 movea.l a6,a0
 adda.l #$8524,a0
 move.w #4,(a0)
 movea.l a6,a0
 adda.l #$468c,a0
 jsr (a0)
 movea.l cpu_render_h0(pc),a0
 adda.l #$6224,a0
 jsr (a0)
 movea.l cpu_render_h0(pc),a0
 adda.l #$867e,a0
 movea.l (a0),a0
 movea.l (a0),a6
 jsr -228(a6)
 lea cpu_view_results(pc),a4
 addq.l #1,8(a4)
 movea.l cpu_render_h6(pc),a0
 movea.l $47c4(a0),a2
 lea 8(a2),a2
 movea.l cpu_render_buffer(pc),a0
 moveq #4,d7
.plane:
 movea.l (a2)+,a1
 move.w #1799,d6
.word:
 move.w (a0)+,d0
 cmp.w (a1)+,d0
 beq .same
 addq.l #1,12(a4)
 cmpi.l #16,16(a4)
 bhs .same
 move.l 16(a4),d1
 lsl.w #3,d1
 lea 20(a4,d1.w),a3
 move.w d7,(a3)+
 move.w d6,(a3)+
 move.w d0,(a3)+
 move.w -2(a1),(a3)
 addq.l #1,16(a4)
.same:
 dbf d6,.word
 dbf d7,.plane
 movem.l (sp)+,d0-d7/a0-a6
 rts
cpu_view_results: dc.b "GSCPUV01"
 dc.l 0,0,0
 ds.b 128
'''
(out/'cpu-view-check.i').write_text(s)
slave=(src/'GunshipHD.s').read_text().replace('include "timing-cpu-render.i"','include "'+str(out/'cpu-view-check.i')+'"')
if os.environ.get('KEEP_FINAL_WAIT')=='1':
    overhead=(src/'timing-draw-overhead.i').read_text()
    overhead='\n'.join(line for line in overhead.splitlines() if not line.startswith((' PL_L $8d7a',' PL_NOP $8d7e')))+'\n'
    (out/'span-only.i').write_text(overhead)
    slave=slave.replace('include "timing-draw-overhead.i"','include "'+str(out/'span-only.i')+'"')
if os.environ.get('SPAN_AUDIT')=='1':
    overhead=(src/'timing-draw-overhead.i').read_text()
    overhead=overhead.replace('.done:\n movem.l (sp)+,d0-d2/a0-a1', ' bsr span_audit\n.done:\n movem.l (sp)+,d0-d2/a0-a1')
    overhead += """
span_audit:
 movem.l d0-d4/a0-a2,-(sp)
 lea span_audit_log(pc),a2
 cmpi.l #16,8(a2)
 bhs .done
 movea.l draw_overhead_h0(pc),a0
 adda.l #$8d88,a0
 moveq #0,d3
.loop:
 cmpi.l #$ffff0000,(a0)+
 beq .next
 move.l 8(a2),d0
 lsl.w #4,d0
 lea 12(a2,d0.w),a1
 move.w d3,(a1)+
 move.w d1,(a1)+
 move.l -4(a0),(a1)+
 movea.l draw_overhead_h0(pc),a0
 adda.l #$90a8,a0
 move.l (a0)+,(a1)+
 move.l (a0),(a1)
 addq.l #1,8(a2)
 bra .done
.next:
 addq.w #1,d3
 cmpi.w #200,d3
 blo .loop
.done:
 movem.l (sp)+,d0-d4/a0-a2
 rts
span_audit_log: dc.b "GSSPAN01"
 dc.l 0
 ds.b 256
"""
    (out/'span-audit.i').write_text(overhead)
    slave=slave.replace('include "timing-draw-overhead.i"','include "'+str(out/'span-audit.i')+'"')
(out/'cpu-view-check.s').write_text(slave)
cmd=[os.environ['VASM'],'-DTIMING_RUNTIME=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym']
for p in [Path(os.environ['AMIGA_INCLUDE']),Path(os.environ['WHDLOAD'])/'Include',Path(os.environ['WHDLOAD'])/'Src',Path(os.environ['WHDLOAD'])/'Src/sources',Path(os.environ['AMIGA_SHARE'])/'ndk/Include_I',src]:cmd+=['-I'+str(p)]
cmd+=['-L',str(out/'cpu-view-check.slave.lst'),'-o',str(out/'cpu-view-check.slave'),str(out/'cpu-view-check.s')]
subprocess.run(cmd,cwd=src,check=True)
