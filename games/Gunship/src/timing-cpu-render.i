 include "timing-offsets.i"
; E1: CPU planar view, enabled only with enhanced flight and
; a 36010-byte MEMF_FAST allocation (view plus cached cockpit art).
; Native clipping/edge-to-span geometry
; is retained. Cockpit and modal rendering remain native chip/blitter work.
CPU_VIEW_BYTES EQU 36010 ; 18000 view + five cached 3602-byte art strips
cpu_render_install:
 movem.l d1-d7/a0-a6,-(sp)
 move.l _renderer(pc),d0
 cmpi.l #1,d0
 beq .disabled
 movea.l RT_HUNKS(a0),a3
 lea cpu_render_h0(pc),a1
 move.l a3,(a1)
 move.l RT_HUNKS+24(a0),4(a1)
 movea.l a3,a1
 adda.l #GS0_85fc,a1
 move.l (a1),d1
 lea cpu_render_pen(pc),a1
 move.l d1,(a1)
 movea.l 4.w,a6
 move.l cpu_render_buffer(pc),d0
 bne .allocated
 move.l #CPU_VIEW_BYTES,d0
 move.l #MEMF_PUBLIC|MEMF_FAST,d1
 jsr _LVOAllocMem(a6)
 tst.l d0
 beq .disabled
 lea cpu_render_buffer(pc),a1
 move.l d0,(a1)
.allocated:
 lea cpu_render_art_ready(pc),a1
 clr.w (a1)
 movea.l a3,a1
 adda.l #GS0_8548,a1
 cmpi.l #$48e701f6,(a1)
 bne .bad
 movea.l a3,a1
 adda.l #GS0_828a,a1
 cmpi.l #$48e73ec0,(a1)
 bne .bad
 movea.l a3,a1
 adda.l #GS0_8818,a1
 cmpi.l #$48e701e2,(a1)
 bne .bad
 movea.l a3,a1
 adda.l #GS0_8b6c,a1
 cmpi.w #$3e39,(a1)
 bne .bad
 movea.l a3,a1
 adda.l #GS0_921c,a1
 cmpi.l #$38026f52,(a1)
 bne .bad
 cmpi.w #$4eb9,GS0_5c5c(a3)
 bne .bad
 move.l a3,d0
 addi.l #GS0_77b8,d0
 cmp.l GS0_5c5e(a3),d0
 bne .bad
 cmpi.w #$4eb9,GS0_5c84(a3)
 bne .bad
 move.l a3,d0
 addi.l #GS0_aa4c,d0
 cmp.l GS0_5c86(a3),d0
 bne .bad
 movea.l a3,a0
 adda.l #GS0_aa80,a0
 cmpi.w #$45f9,(a0)
 bne .bad
 cmpi.l #$6100009c,6(a0)
 bne .bad
 cmpi.l #$6100008a,24(a0)
 bne .bad
 lea cpu_render_art(pc),a1
 move.l 2(a0),4(a1) ; native overlay descriptors
 move.l a0,-(sp)
 movea.l a3,a0
 adda.l #GS0_927a,a0
 move.l (a0),(a1) ; native bitmap table
 movea.l (sp)+,a0
 lea cpu_render_overlay_native(pc),a1
 move.l (a0),(a1)+
 move.w 4(a0),(a1)+
 move.w #$4ef9,(a1)+
 move.l a3,d0
 addi.l #GS0_aa86,d0
 move.l d0,(a1)
 lea cpu_render_native_line(pc),a1
 movea.l a3,a0
 adda.l #GS0_8548,a0
 moveq #4,d0
.copy_line:
 move.w (a0)+,(a1)+
 dbf d0,.copy_line
 move.w #$4ef9,(a1)+
 move.l a0,(a1)
 lea cpu_render_native_pixel(pc),a1
 movea.l a3,a0
 adda.l #GS0_828a,a0
 moveq #4,d0
.copy_pixel:
 move.w (a0)+,(a1)+
 dbf d0,.copy_pixel
 move.w #$4ef9,(a1)+
 move.l a0,(a1)
 lea cpu_render_native_begin(pc),a1
 movea.l a3,a0
 adda.l #GS0_8818,a0
 moveq #3,d0
.copy_begin:
 move.w (a0)+,(a1)+
 dbf d0,.copy_begin
 move.w #$4ef9,(a1)+
 move.l a0,(a1)
 lea cpu_render_native_poly(pc),a1
 movea.l a3,a0
 adda.l #GS0_8b6c,a0
 moveq #2,d0
.copy_poly:
 move.w (a0)+,(a1)+
 dbf d0,.copy_poly
 move.w #$4ef9,(a1)+
 move.l a0,(a1)
 movea.l a3,a1
 lea .patches(pc),a0
 jsr resload_Patch(a2)
.disabled:
 moveq #0,d0
 bra .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d7/a0-a6
 rts
.patches:
 PL_START
 PL_PS GS0_5c5c,cpu_render_start
 PL_PS GS0_5c84,cpu_render_finish
 PL_P GS0_8548,cpu_render_line
 PL_P GS0_828a,cpu_render_pixel
 PL_P GS0_8818,cpu_render_begin
 PL_P GS0_8b6c,cpu_render_poly
 PL_P GS0_921c,cpu_render_band
 PL_P GS0_aa80,cpu_render_overlay
 PL_END

cpu_render_release:
 movem.l d0-d1/a0-a1/a6,-(sp)
 lea cpu_render_buffer(pc),a0
 move.l (a0),d0
 beq .done
 clr.l (a0)
 movea.l d0,a1
 move.l #CPU_VIEW_BYTES,d0
 movea.l 4.w,a6
 jsr _LVOFreeMem(a6)
.done:
 movem.l (sp)+,d0-d1/a0-a1/a6
 rts

cpu_render_start:
 movem.l d0/a0,-(sp)
 movea.l timing_runtime_arena(pc),a0
 moveq #0,d0
 cmpi.w #1,RT_CAPTURE_OWNER(a0)
 bne .state
 tst.w RT_BOUNDARY_PHASE(a0)
 bne .state
 moveq #1,d0
.state:
 lea cpu_render_active(pc),a0
 move.w d0,(a0)
 clr.w cpu_render_overlay_ready-cpu_render_active(a0)
 move.w #1,2(a0) ; previous native mask may be dirty
 movem.l (sp)+,d0/a0
 move.l a0,-(sp)
 movea.l cpu_render_h0(pc),a0
 adda.l #GS0_77b8,a0
 move.l a0,-(sp)
 movea.l 4(sp),a0
 move.l (sp),4(sp)
 addq.l #4,sp
 rts

cpu_render_finish:
 movem.l d0-d7/a0-a6,-(sp)
 move.w cpu_render_active(pc),d0
 beq .done
 lea cpu_render_active(pc),a0
 clr.w (a0)
 movea.l cpu_render_h6(pc),a0
 movea.l $47c4(a0),a2
 lea 8(a2),a2
 ; Finish any preceding native blit before touching its chip destination.
 movea.l cpu_render_h0(pc),a0
 adda.l #GS0_867e,a0
 movea.l (a0),a6
 movea.l (a6),a6
 jsr -228(a6)
 lea cpu_render_art_ready(pc),a0
 tst.w (a0)
 bne .art_ready
 move.w #1,(a0)
 movea.l cpu_render_art(pc),a3
 lea 128(a3),a3
 movea.l cpu_render_buffer(pc),a5
 adda.l #18000,a5
 moveq #4,d7
.cache_plane:
 movea.l (a3)+,a0
 move.w #1800,d6
.cache_word:
 move.w (a0)+,(a5)+
 dbf d6,.cache_word
 dbf d7,.cache_plane
.art_ready:
 movea.l cpu_render_buffer(pc),a5
 adda.l #18000,a5
 movea.l a5,a4
 adda.l #14408,a4 ; plane 4 is the cockpit's opaque mask
 movea.l cpu_render_buffer(pc),a0
 moveq #4,d7
.plane:
 movea.l (a2)+,a1
 movea.l a4,a6
 ; Top five rows: the cockpit frame and pillar tops. The native top-strip
 ; restore is skipped, and a native fill still reaches these rows in chip,
 ; so compose them from the cached art and mask every frame.
 moveq #99,d6
.top:
 move.w (a6)+,d1
 move.w (a5)+,d0
 and.w d1,d0
 not.w d1
 and.w (a0)+,d1
 or.w d1,d0
 move.w d0,(a1)+
 dbf d6,.top
 moveq #84,d6 ; remaining 85 view rows
.row:
 ; Native right strip wraps one word into the next row. Compose both
 ; edges; row 90 is never overwritten.
 move.w (a6)+,d1
 move.w (a5)+,d0
 and.w d1,d0
 not.w d1
 and.w (a0)+,d1
 or.w d1,d0
 move.w d0,(a1)+
 movem.l (a0)+,d0-d5
 movem.l d0-d5,(a1)
 movem.l (a0)+,d0-d2
 movem.l d0-d2,24(a1)
 adda.w #36,a1
 adda.w #36,a5
 adda.w #36,a6
 move.w (a6)+,d1
 move.w (a5)+,d0
 and.w d1,d0
 not.w d1
 and.w (a0)+,d1
 or.w d1,d0
 move.w d0,(a1)+
 dbf d6,.row
 addq.l #2,a5 ; row 90 is outside the view and remains untouched
 dbf d7,.plane
 lea cpu_render_overlay_ready(pc),a0
 move.w #1,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 move.l a0,-(sp)
 movea.l cpu_render_h0(pc),a0
 adda.l #GS0_aa4c,a0
 move.l a0,-(sp)
 movea.l 4(sp),a0
 move.l (sp),4(sp)
 addq.l #4,sp
 rts

cpu_render_overlay:
 bsr cockpit_check_restores
 move.l a0,-(sp)
 movea.l timing_runtime_arena(pc),a0
 cmpi.w #1,RT_CAPTURE_OWNER(a0)
 bne .native
 tst.w RT_BOUNDARY_PHASE(a0)
 bne .native
 lea cpu_render_overlay_ready(pc),a0
 tst.w (a0)
 beq .native
 movem.l (sp)+,a0
 move.l a0,-(sp)
 movea.l cpu_render_h0(pc),a0
 movea.l cpu_render_rects(pc),a2
 adda.w #24,a2 ; retain the third (attitude instrument) restore
 adda.l #GS0_aa98,a0
 move.l a0,-(sp)
 movea.l 4(sp),a0
 move.l (sp),4(sp)
 addq.l #4,sp
 rts
.native:
 movea.l (sp)+,a0
 bra cpu_render_overlay_native

; The target panel painter (+468C) runs between the view render and the
; copy at +AA4C. Its 3D target and text use the same primitives in panel
; coordinates, which the CPU path would draw into the view buffer: keep the
; panel native. Its native begin/fill leaves the mask and bbox in use, so the
; next CPU begin clears them natively first. Preserve all registers.
cpu_render_suspend:
 move.l a0,-(sp)
 lea cpu_render_active(pc),a0
 move.w (a0),cpu_render_suspended-cpu_render_active(a0)
 clr.w (a0)
 movea.l (sp)+,a0
 rts

cpu_render_resume:
 move.l a0,-(sp)
 lea cpu_render_active(pc),a0
 move.w cpu_render_suspended-cpu_render_active(a0),(a0)
 beq .done
 move.w #1,cpu_render_mask_dirty-cpu_render_active(a0)
.done:
 movea.l (sp)+,a0
 rts

; Plot one pixel into all requested planes. d0=x,d1=y,d6=last plane,
; d7=pen. Preserve coordinates and line/span state.
cpu_render_dot:
 movem.l d0-d3/d6-d7/a0,-(sp)
 mulu #40,d1
 move.w d0,d2
 lsr.w #3,d2
 add.w d2,d1
 andi.w #7,d0
 eori.w #7,d0
 movea.l cpu_render_buffer(pc),a0
 adda.w d1,a0
.plane:
 lsr.w #1,d7
 bcc .clear
 bset d0,(a0)
 bra .next
.clear:
 bclr d0,(a0)
.next:
 adda.w #3600,a0
 dbf d6,.plane
 movem.l (sp)+,d0-d3/d6-d7/a0
 rts

cpu_render_pixel:
 move.l a0,-(sp)
 lea cpu_render_active(pc),a0
 tst.w (a0)
 movem.l (sp)+,a0
 beq cpu_render_native_pixel
 cmpi.w #90,d1
 bhs cpu_render_native_pixel
 movem.l d1-d7/a0-a6,-(sp)
 movea.l cpu_render_pen(pc),a0
 moveq #0,d7
 move.b (a0),d7
 moveq #4,d6
 bsr cpu_render_dot
 move.l d7,d0
 movem.l (sp)+,d1-d7/a0-a6
 rts

cpu_render_line:
 move.l a0,-(sp)
 lea cpu_render_active(pc),a0
 tst.w (a0)
 movem.l (sp)+,a0
 beq cpu_render_native_line
 cmpi.w #90,8(a5)
 bhs cpu_render_native_line
 cmpi.w #90,12(a5)
 bhs cpu_render_native_line
 movem.l d0-d7/a0-a6,-(sp)
 movem.w 6(a5),d0-d3
 sub.w d0,d2
 sub.w d1,d3
 moveq #1,d4
 tst.w d2
 bpl .dx
 neg.w d2
 moveq #-1,d4
.dx:
 moveq #1,d5
 tst.w d3
 bpl .dy
 neg.w d3
 moveq #-1,d5
.dy:
 movea.w d4,a3 ; sx
 movea.w d5,a4 ; sy
 movea.l cpu_render_h0(pc),a0
 adda.l #GS0_8524,a0
 move.w (a0),d6
 move.w d2,d0
 or.w d3,d0
 bne .nonzero
 moveq #4,d6
.nonzero:
 move.w 6(a5),d0
 movea.l cpu_render_pen(pc),a0
 moveq #0,d7
 move.b (a0),d7
 lea cpu_render_line4(pc),a2
 cmpi.w #3,d6
 beq .four
 lea cpu_render_line5(pc),a2
 mulu #20,d7
 bra .pen_ready
.four:
 lsl.w #4,d7
.pen_ready:
 adda.w d7,a2
 cmp.w d3,d2
 blt .ymajor
 move.w d3,d4
 add.w d4,d4
 sub.w d2,d4 ; error=2minor-major
 move.w d2,d5
.xloop:
 bsr cpu_render_line_dot
 tst.w d4
 bmi .xskip
 add.w a4,d1
 sub.w d2,d4
 sub.w d2,d4
.xskip:
 add.w d3,d4
 add.w d3,d4
 add.w a3,d0
 dbf d5,.xloop
 bra .done
.ymajor:
 move.w d2,d4
 add.w d4,d4
 sub.w d3,d4
 move.w d3,d5
.yloop:
 bsr cpu_render_line_dot
 tst.w d4
 bmi .yskip
 add.w a3,d0
 sub.w d3,d4
 sub.w d3,d4
.yskip:
 add.w d2,d4
 add.w d2,d4
 add.w a4,d1
 dbf d5,.yloop
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts

 ; The pen selects an unrolled four/five-plane operation once per line.
 ; Scratch d6/d7/a0 are private to the line rasterizer; no per-pixel MOVEM.
cpu_render_line_dot:
 move.w d1,d7
 mulu #40,d7
 move.w d0,d6
 lsr.w #3,d6
 add.w d6,d7
 movea.l cpu_render_buffer(pc),a0
 adda.w d7,a0
 move.w d0,d6
 andi.w #7,d6
 eori.w #7,d6
 jmp (a2)

cpu_render_band:
 move.l a0,-(sp)
 lea cpu_render_active(pc),a0
 tst.w (a0)
 movem.l (sp)+,a0
 beq .native
 cmpi.w #90,d1
 bhs .native
 movem.l d0-d7/a0-a6,-(sp)
 tst.w d2
 ble .done
 move.w d1,d0
 add.w d2,d0
 cmpi.w #90,d0
 bhi .fallback
 mulu #40,d1
 subq.w #1,d2 ; rows
 movea.l cpu_render_pen(pc),a0
 move.b (a0),d7
 movea.l cpu_render_buffer(pc),a1
 adda.w d1,a1
 movea.w d2,a3
 moveq #4,d6
.plane:
 movea.l a1,a0
 move.w a3,d5
 moveq #0,d0
 lsr.b #1,d7
 bcc .fill
 moveq #-1,d0
.fill:
 move.l d0,d1
 move.l d0,d2
 move.l d0,d3
 move.l d0,d4
.rowfill:
 movem.l d0-d4,(a0)
 movem.l d0-d4,20(a0)
 adda.w #40,a0
 dbf d5,.rowfill
 adda.w #3600,a1
 dbf d6,.plane
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
.fallback:
 movem.l (sp)+,d0-d7/a0-a6
.native:
 move.w d2,d4
 ble .return
 move.l a0,-(sp)
 movea.l cpu_render_h0(pc),a0
 asl.w #6,d4
 adda.l #GS0_9222,a0
 move.l a0,-(sp)
 movea.l 4(sp),a0
 move.l (sp),4(sp)
 addq.l #4,sp
.return:
 rts

cpu_render_begin:
 move.l a0,-(sp)
 lea cpu_render_active(pc),a0
 tst.w (a0)
 beq .native
 tst.w 2(a0)
 beq .cpu
 clr.w 2(a0)
.native:
 movea.l (sp)+,a0
 bra cpu_render_native_begin
.cpu:
 movea.l (sp)+,a0
 movem.l d0-d2/a0-a1,-(sp)
 bsr draw_overhead_clear_spans
 movea.l cpu_render_h0(pc),a1
 adda.l #GS0_8d88,a1
 ; Native bbox reset; prior mask is already clean and CPU spans do not use it.
 move.w #-1,GS0_90ac-GS0_8d88(a1)
 move.w #-1,GS0_90ae-GS0_8d88(a1)
 move.w #320,GS0_90a8-GS0_8d88(a1)
 move.w #200,GS0_90aa-GS0_8d88(a1)
 movem.l (sp)+,d0-d2/a0-a1
 rts

cpu_render_poly:
 move.l a0,-(sp)
 lea cpu_render_active(pc),a0
 tst.w (a0)
 beq .native
 movea.l cpu_render_h0(pc),a0
 adda.l #GS0_90a8,a0
 cmpi.w #90,6(a0)
 bhs .dirty
 movem.l (sp)+,a0
 movem.l d0-d7/a0-a6,-(sp)
 movea.l cpu_render_h0(pc),a2
 adda.l #GS0_90a8,a2
 move.w 4(a2),d0
 cmp.w (a2),d0
 blt .done
 beq .line
 move.w 6(a2),d1
 cmp.w 2(a2),d1
 blt .done
 beq .line
 movea.l cpu_render_h0(pc),a3
 adda.l #GS0_8d88,a3
 move.w 2(a2),d1
 move.w d1,d0
 lsl.w #2,d0
 adda.w d0,a3
 move.w 6(a2),d5
 sub.w d1,d5
 ; Match native mask-to-plane BLTSIZE, including its right-edge quirk:
 ; xmax on a word boundary is excluded unless the bbox is only one word.
 move.w 4(a2),d4
 addi.w #15,d4
 andi.w #$fff0,d4
 move.w (a2),d0
 andi.w #$fff0,d0
 cmp.w d0,d4
 bne .right_bound
 addi.w #16,d4
.right_bound:
 subq.w #1,d4
 movea.l cpu_render_h0(pc),a0
 adda.l #GS0_8524,a0
 move.w (a0),d6
 movea.l cpu_render_pen(pc),a0
 moveq #0,d7
 move.b (a0),d7
.row:
 move.w (a3)+,d0
 move.w (a3)+,d2
 cmp.w d0,d2
 blo .next
 bne .span
 tst.w d2
 beq .next
 cmpi.w #319,d2
 beq .next
.span:
 cmp.w d4,d2
 bls .clamped
 move.w d4,d2
.clamped:
 cmp.w d0,d2
 blo .next
 bsr cpu_render_span
.next:
 addq.w #1,d1
 dbf d5,.row
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
.line:
 move.l (a2),6(a5)
 move.l 4(a2),10(a5)
 movem.l (sp)+,d0-d7/a0-a6
 bra cpu_render_line
.dirty:
 lea cpu_render_mask_dirty(pc),a0
 move.w #1,(a0)
.native:
 movea.l (sp)+,a0
 bra cpu_render_native_poly

; Inclusive horizontal span, same bit ordering as the native mask writer.
; d0=xmin,d2=xmax,d1=y,d6=last plane,d7=pen.
cpu_render_span:
 movem.l d0-d7/a0-a2,-(sp)
 move.w d0,d3
 andi.w #15,d3
 move.w #$ffff,d4
 lsr.w d3,d4 ; first word mask
 move.w d2,d3
 andi.w #15,d3
 move.w #$7fff,d5
 lsr.w d3,d5
 not.w d5 ; last word mask
 lsr.w #4,d0
 lsr.w #4,d2
 sub.w d0,d2 ; distance in words
 add.w d0,d0
 mulu #40,d1
 add.w d0,d1
 movea.l cpu_render_buffer(pc),a2
 adda.w d1,a2
.plane:
 movea.l a2,a0
 move.w d2,d3
 move.w d4,d0
 tst.w d3
 bne .wide
 and.w d5,d0
 lsr.w #1,d7
 bcc .single_clear
 or.w d0,(a0)
 bra .next_plane
.single_clear:
 not.w d0
 and.w d0,(a0)
 bra .next_plane
.wide:
 lsr.w #1,d7
 bcc .clear
 or.w d0,(a0)+
 subq.w #1,d3
 beq .set_last
 moveq #-1,d0
.set_middle:
 move.w d0,(a0)+
 subq.w #1,d3
 bne .set_middle
.set_last:
 or.w d5,(a0)
 bra .next_plane
.clear:
 not.w d0
 and.w d0,(a0)+
 subq.w #1,d3
 beq .clear_last
 moveq #0,d0
.clear_middle:
 move.w d0,(a0)+
 subq.w #1,d3
 bne .clear_middle
.clear_last:
 move.w d5,d0
 not.w d0
 and.w d0,(a0)
.next_plane:
 adda.w #3600,a2
 dbf d6,.plane
 movem.l (sp)+,d0-d7/a0-a2
 rts

 even
cpu_render_h0: dc.l 0
cpu_render_h6: dc.l 0
cpu_render_pen: dc.l 0
cpu_render_buffer: dc.l 0
cpu_render_art: dc.l 0
cpu_render_rects: dc.l 0
cpu_render_overlay_ready: dc.w 0
cpu_render_art_ready: dc.w 0
cpu_render_overlay_native: ds.b 12
cpu_render_active: dc.w 0
cpu_render_mask_dirty: dc.w 1
cpu_render_suspended: dc.w 0
cpu_render_native_line: ds.b 16
cpu_render_native_pixel: ds.b 16
cpu_render_native_begin: ds.b 14
cpu_render_native_poly: ds.b 12

; Assemble fixed-stride routines selected once per line. The first plane
; uses (a0), a two-byte instruction; subsequent planes use word offsets.
CPU_LINE_TABLE MACRO
CPU_PEN SET 0
 REPT 32
CPU_PLANE SET 0
 REPT \1
 IFNE CPU_PEN&(1<<CPU_PLANE)
 IFNE CPU_PLANE
 bset d6,CPU_PLANE*3600(a0)
 ELSE
 bset d6,(a0)
 ENDC
 ELSE
 IFNE CPU_PLANE
 bclr d6,CPU_PLANE*3600(a0)
 ELSE
 bclr d6,(a0)
 ENDC
 ENDC
CPU_PLANE SET CPU_PLANE+1
 ENDR
 rts
CPU_PEN SET CPU_PEN+1
 ENDR
 ENDM
cpu_render_line4:
 CPU_LINE_TABLE 4
cpu_render_line5:
 CPU_LINE_TABLE 5
