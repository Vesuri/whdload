"""Ignored paired diagnostic: copy the complete P3 renderer and its local state."""
from pathlib import Path
import shutil
src=Path('src').resolve()
for bank in ('chip','fast'):
 dst=Path('tmp/fixtures/p3-full-code-v2-'+bank)/'source'
 assert not dst.exists(),dst
 shutil.copytree(src,dst)
 p=dst/'4DSportsDrivingHD.s';s=p.read_text()
 needle='\tinclude "performance.s"\n'
 assert s.count(needle)==1
 s=s.replace(needle,needle+'p3_clone_end:\n')
 p.write_text(s)
 p=dst/'performance.s';s=p.read_text()
 s=s.replace(' bsr raster_init\n',' bsr raster_init\n bsr p3_clone_init\n',1)
 s=s.replace(' bsr raster_patch\n',' bsr p3_clone_patch\n',1)
 s+='''
; Both diagnostic variants use the same copy, cache flush and patch trampoline.
; Copy the prefix so all renderer PC-relative code/state references retain their
; displacement. Non-renderer game hooks and the simulation remain in the original.
p3_clone_init:
 movem.l d0-d2/a0-a2/a6,-(sp)
 move.l raster_buffer(pc),d0
 beq .done
 move.l 4.w,a6
 move.l #p3_clone_end-slv_base,d0
 moveq #MEMF_BANK,d1
 jsr _LVOAllocMem(a6)
 tst.l d0
 beq .failed
 lea p3_clone_address(pc),a0
 move.l d0,(a0)
 move.l d0,a1
 lea slv_base(pc),a0
 move.w #(p3_clone_end-slv_base)/2-1,d2
.copy:
 move.w (a0)+,(a1)+
 dbra d2,.copy
 ; Keep the original live-slave marker unique for the benchmark clock locator.
 move.l d0,a0
 move.l #$5033434c,perf_game-slv_base-8(a0)
 move.l #$4f4e4521,perf_game-slv_base-4(a0)
 move.l _resload(pc),a2
 jsr resload_FlushCache(a2)
.done:
 movem.l (sp)+,d0-d2/a0-a2/a6
 rts
.failed:
 illegal
p3_clone_patch:
 ; WHDLoad rejects patch-list destinations outside the loaded slave. Install
 ; its checked original list first, then relocate only those exact operands.
 bsr raster_patch
 movem.l d0-d2/a0-a2,-(sp)
 move.l p3_clone_address(pc),d1
 beq .done
 lea slv_base(pc),a0
 sub.l a0,d1
 lea p3_clone_hooks(pc),a1
.next:
 move.l (a1)+,d0
 bmi .flush
 move.l perf_game(pc),a0
 adda.l d0,a0
 move.w (a0),d0
 and.w #$ffbf,d0
 cmp.w #$4eb9,d0
 bne .failed
 move.l (a1)+,d0
 lea slv_base(pc),a2
 adda.l d0,a2
 cmpa.l 2(a0),a2
 bne .failed
 add.l d1,2(a0)
 bra .next
.flush:
 move.l _resload(pc),a2
 jsr resload_FlushCache(a2)
.done:
 movem.l (sp)+,d0-d2/a0-a2
 rts
.failed:
 illegal
p3_clone_hooks:
 dc.l $21228,raster_bg_enter-slv_base
 dc.l $21ba8,raster_bg_exit-slv_base
 dc.l $347b0,raster_bg_rect-slv_base
 dc.l $32242,raster_bg_bitmap-slv_base
 dc.l $323a6,raster_bg_bitmap_end-slv_base
 dc.l $ab86,raster_draw_enter-slv_base
 dc.l $aed0,raster_draw_exit-slv_base
 dc.l $3980e,raster_own_blitter-slv_base
 dc.l $39800,perf_disown_blitter-slv_base
 dc.l $2c6d6,raster_solid-slv_base
 dc.l $2bf5c,raster_two-slv_base
 dc.l $2cd44,raster_solid_end-slv_base
 dc.l $2c632,raster_two_end-slv_base
 dc.l $2cdca,raster_degenerate-slv_base
 dc.l $339c4,raster_line_hook-slv_base
 dc.l $33aa8,raster_line_end-slv_base
 dc.l -1
 even
p3_clone_address: dc.l 0
'''.replace('MEMF_BANK','MEMF_CHIP' if bank=='chip' else 'MEMF_FAST')
 p.write_text(s)
