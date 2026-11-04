; H10: CPU solid background rectangles on WHDLoad-selected 030/040/060.
; Keep the native geometry, colours, loop, ownership and WaitBlit boundaries.
; Each row is 48 bytes in the existing Chip planes. No DMA-visible allocation.
FF1RenderInstallClear:
 lea start(pc),a0
 suba.l #FF1_HOST_CODE_SIZE,a0
 move.l FF1_HOST_ATTN(a0),d0
 andi.l #$8c,d0             ; AFF_68030 | AFF_68040 | AFF_68060
 beq.b .done
 cmpi.w #$33c0,$6b0e4
 bne.l FF1ProductionFault
 cmpi.l #$00dff058,$6b0e6
 bne.l FF1ProductionFault
 cmpi.l #$33fc0458,$6b138
 bne.l FF1ProductionFault
 cmpi.l #$00dff058,$6b13c
 bne.l FF1ProductionFault
 tst.w FF1RenderClearControl(pc)
 beq.b .done
 lea FF1RenderClearBottom(pc),a0
 move.w #$4eb9,$6b0e4
 move.l a0,$6b0e6
 lea FF1RenderClearTop(pc),a0
 move.w #$4eb9,$6b138
 move.l a0,$6b13a
 move.w #$4e71,$6b13e
.done:
 rts
FF1RenderClearBottom:
 move.w ccr,-(sp)
 movem.l d0-d7/a0-a5,-(sp)
 move.w d0,d7
 lsr.w #6,d7
 ; Zero encodes 1024 rows to the blitter. Leave unexpected extents native.
 tst.w d7
 beq.b .native
 cmpi.w #200,d7
 bhi.b .native
 moveq #0,d0
 cmpi.w #2,-2(a6)
 bne.b .fill
 moveq #-1,d0
.fill:
 IFD FF1_FAST_RENDER
 exg a0,a1
 bsr.l FF1FastRenderTarget
 exg a0,a1
 ENDC
 bsr.b FF1RenderClearRows
 movem.l (sp)+,d0-d7/a0-a5
 move.w (sp)+,ccr
 tst.w d0                  ; displaced MOVE's NZVC, preserving X
 rts
.native:
 IFD FF1_FAST_RENDER
 bsr.l FF1FastRenderNativeGuard
 ENDC
 movem.l (sp)+,d0-d7/a0-a5
 move.w (sp)+,ccr
 move.w d0,$dff058
 rts
FF1RenderClearTop:
 move.w ccr,-(sp)
 movem.l d0-d7/a0-a5,-(sp)
 moveq #17,d7
 moveq #0,d0
 tst.w -2(a6)
 bne.b .fill
 moveq #-1,d0
.fill:
 IFD FF1_FAST_RENDER
 exg a0,a1
 bsr.l FF1FastRenderTarget
 exg a0,a1
 ENDC
 bsr.b FF1RenderClearRows
 movem.l (sp)+,d0-d7/a0-a5
 move.w (sp)+,ccr
 andi #$10,ccr             ; displaced MOVE #$458's NZVC, preserving X
 rts
FF1RenderClearRows:
 move.l a1,a5
 move.l d0,d1
 move.l d0,d2
 move.l d0,d3
 move.l d0,d4
 move.l d0,d5
 move.l d0,d6
 move.l d0,a0
 move.l d0,a1
 move.l d0,a2
 move.l d0,a3
 move.l d0,a4
 subq.w #1,d7
.row:
 movem.l d0-d6/a0-a4,(a5)
 lea 48(a5),a5
 dbra d7,.row
 rts
; Immutable equal-layout A/B preset, outside lifecycle zero ranges.
FF1RenderClearControl: dc.w 1
