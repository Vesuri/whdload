 include "timing-offsets.i"
; Enhanced flight only. The native line clipper (+82EC) and polygon edge
; clipper (+8698) take an edge's x and y spans as signed words. A near-plane
; edge of a large ground face can project its ends more than 32767 pixels
; apart; the span then wraps, the border intersection lands on the wrong side
; and the face fills the whole view (sky included) for as long as the camera
; keeps that geometry. Split such an edge at its midpoint, recursively, and
; give each half to the native code: the halves are the same line, so ordinary
; edges are unchanged. Inputs are the native 6(a5)..12(a5) endpoint words.
clip_split_install:
 movem.l d1/a0-a1,-(sp)
 movea.l RT_HUNKS(a0),a1
 lea clip_split_h0(pc),a0
 move.l a1,(a0)
 movea.l a1,a0
 adda.l #GS0_8698,a0
 cmpi.l #$48e706f2,(a0)+ ; movem.l d5-d6/a0-a3/a6,-(sp)
 bne .bad
 cmpi.l #$4e56fff6,(a0) ; link a6,#-10
 bne .bad
 movea.l a1,a0
 adda.l #GS0_8538,a0
 cmpi.w #$4eb9,(a0)+ ; jsr ClipLine
 bne .bad
 move.l a1,d0
 addi.l #GS0_82ec,d0
 cmp.l (a0)+,d0
 bne .bad
 cmpi.l #$6a024e75,(a0) ; bpl.s +8542; rts
 bne .bad
 lea .patches(pc),a0
 jsr resload_Patch(a2)
 moveq #0,d0
 bra .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1/a0-a1
 rts
.patches:
 PL_START
 PL_P GS0_8698,clip_split_edge
 PL_P GS0_8538,clip_split_line
 PL_END

; Polygon edge. Native contract: clobbers d0-d4/d7, preserves the rest.
clip_split_edge:
 bsr clip_split_wide
 beq clip_split_edge_native
 move.l a0,-(sp)
 lea clip_split_edge(pc),a0
 bsr clip_split_halves
 movea.l (sp)+,a0
 rts

; Clipped line. Native contract: clobbers d0-d7/a0-a2, preserves a3-a6.
clip_split_line:
 bsr clip_split_wide
 beq clip_split_line_native
 lea clip_split_line(pc),a0
 bra clip_split_halves

; Z clear when either span overflows a word. Uses d0 only.
clip_split_wide:
 move.w 10(a5),d0
 sub.w 6(a5),d0
 bvs .wide
 move.w 12(a5),d0
 sub.w 8(a5),d0
 bvs .wide
 moveq #0,d0 ; Z set: fits
 rts
.wide:
 moveq #1,d0 ; Z clear
 rts

; a0 = this entry. Draw (x1,y1)-(mid) and (mid)-(x2,y2), each by a0 again.
; The native code rewrites 6(a5)..12(a5) while clipping: keep the originals.
clip_split_halves:
 move.l a0,-(sp)
 move.l 10(a5),-(sp) ; x2,y2
 move.l 6(a5),-(sp) ; x1,y1
 move.w 6(a5),d0
 ext.l d0
 move.w 10(a5),d1
 ext.l d1
 add.l d1,d0
 asr.l #1,d0
 move.w d0,10(a5)
 move.w 8(a5),d0
 ext.l d0
 move.w 12(a5),d1
 ext.l d1
 add.l d1,d0
 asr.l #1,d0
 move.w d0,12(a5)
 move.l 10(a5),-(sp) ; mid
 jsr (a0)
 move.l (sp)+,6(a5) ; mid
 move.l 4(sp),10(a5) ; x2,y2
 movea.l 8(sp),a0
 jsr (a0)
 lea 12(sp),sp
 rts

; Displaced native prologue, then the rest of the native edge clipper.
clip_split_edge_native:
 movem.l d5-d6/a0-a3/a6,-(sp)
 link a6,#-10
 move.l clip_split_h0(pc),-(sp)
 addi.l #GS0_86a0,(sp)
 rts

clip_split_line_native:
 pea .clipped(pc)
 move.l clip_split_h0(pc),-(sp)
 addi.l #GS0_82ec,(sp)
 rts
.clipped:
 bpl .draw
 rts
.draw:
 move.l clip_split_h0(pc),-(sp)
 addi.l #GS0_8542,(sp)
 rts

clip_split_h0: dc.l 0
