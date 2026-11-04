; H11: prepare the seven live session-clock glyphs in public Fast memory
; while the sky blit runs. Commit them after the original flag and its wait.
; This keeps every screen writer in native order: road, cars, cockpit and
; pit messages cannot invalidate an early clock. No DMA reads this workspace.
FF1RenderPrepareClock:
 move.w ccr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 lea FF1RenderClockReady(pc),a0
 clr.w (a0)
 tst.w FF1RenderOverlapControl(pc)
 beq.w .done
 lea start(pc),a0
 suba.l #FF1_HOST_CODE_SIZE,a0
 move.l FF1_HOST_ATTN(a0),d0
 andi.l #$8c,d0
 beq.w .done
 tst.w FF1RenderRoadControl(pc)
 beq.w .done
 tst.w $1c1e8
 beq.w .done
 ; The native session clock is seven 8x8 glyphs, colour 7 on colour 0,
 ; at byte columns 32,33,35,36,38,39,41 and pixel rows 24..31.
 cmpi.l #$00070000,$23608
 bne.w .done
 cmpi.w #32,$23610
 bne.w .done
 cmpi.w #3,$23612
 bne.w .done
 moveq #0,d6
 move.w $2178c,d6
 beq.w .done
 cmpi.w #64,d6
 bhi.w .done
 add.w d6,d6
 move.l $216d8,a2
 move.l a2,d0
 beq.w .done
 lea $226cd,a3                 ; session clock bytes 3..9, native font indices
 moveq #6,d7
.check:
 moveq #0,d0
 move.b (a3)+,d0
 cmp.w d6,d0
 bhs.b .done
 dbra d7,.check
 lea $226cd,a3
 lea FF1RenderClockPixels(pc),a4
 moveq #6,d7
.glyph:
 moveq #0,d0
 move.b (a3)+,d0
 lea (a2,d0.w),a0
 move.l a4,a1
 rept 8
 move.b (a0),(a1)
 adda.w d6,a0
 addq.l #7,a1
 endr
 addq.l #1,a4
 dbra d7,.glyph
 lea FF1RenderClockReady(pc),a0
 move.w #1,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 rts
FF1RenderOverlapHUD:
 tst.w FF1RenderClockReady(pc)
 beq.w FF1RenderPresentHUD
 move.l $226b2,-(sp)
 move.l $226ae,$226b2
 bsr.l FF1PresentFlag
 ; The flag overlaps the first clock glyph: preserve the native boundary.
 jsr $2a130
 movem.l d0-d7/a0-a6,-(sp)
 move.l $226ae,a2
 moveq #2,d7
.plane:
 move.l (a2)+,a1
 adda.w #24*48+32,a1
 IFD FF1_FAST_RENDER
 exg a0,a1
 bsr.l FF1FastRenderTarget
 exg a0,a1
 ENDC
 lea FF1RenderClockPixels(pc),a0
 moveq #7,d6
.row:
 move.b (a0)+,(a1)
 move.b (a0)+,1(a1)
 move.b (a0)+,3(a1)
 move.b (a0)+,4(a1)
 move.b (a0)+,6(a1)
 move.b (a0)+,7(a1)
 move.b (a0)+,9(a1)
 lea 48(a1),a1
 dbra d6,.row
 dbra d7,.plane
 lea FF1RenderClockReady(pc),a0
 clr.w (a0)
 movem.l (sp)+,d0-d7/a0-a6
 move.l (sp)+,$226b2
 rts
; Immutable equal-layout preset, with transient data owned by lifecycle reset.
FF1RenderOverlapControl: dc.w 1
FF1RenderClockReady: dc.w 0
FF1RenderClockPixels: ds.b 56
