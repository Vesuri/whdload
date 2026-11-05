; H9: exact right-edge narrowing of the two descending road fills.
; Each 16-row band scans only words to the right of its current bound. A
; zero band needs no DMA. Keep the left edge: odd fill carry is then exact
; too, without assuming closed polygons or interpreting projected geometry.
; Reads are synchronized with the preceding line blits. Subsequent scans
; touch the next, disjoint band while the previous fill can run. No DMA or
; persistent scratch allocation; mirrors do not call this native fill entry.
FF1RenderInstallFill:
 cmpi.l #$4eb90002,$6abc6
 bne.l FF1ProductionFault
 cmpi.w #$a130,$6abca
 bne.l FF1ProductionFault
 tst.w FF1RenderFillControl(pc)
 beq.b .done
 lea FF1RenderFill(pc),a0
 move.w #$4ef9,$6abc6
 move.l a0,$6abc8
.done:
 rts
FF1RenderFill:
 jsr $2a130
 movem.l d0-d7/a0-a6,-(sp)
 move.w $66c8c,d5
 addi.w #100,d5
 ; Retain native behavior for any unexpected extent, without reading beyond
 ; its plane. The qualified native view is 384 by 200 pixels.
 cmpi.w #200,d5
 bhi.w .native
 tst.w d5
 beq.w .native
 move.l $226ae,a5
 moveq #1,d7
 IFD FF1_FAST_RENDER
 ; FR4: the register base is the image while redirected, and the scan reads
 ; the Fast bank (D4 = Fast - Chip, 0 otherwise); BLTSIZE goes through FR4.
 move.l FF1FastRenderRegs(pc),a0
 move.l #$03aa0012,$40(a0)
 move.l #-1,$44(a0)
 ELSE
 move.l #$03aa0012,$dff040
 move.l #-1,$dff044
 ENDC
.plane:
 move.l (a5)+,a2
 IFD FF1_FAST_RENDER
 ; The scan reads rows 200 - (extent) to 199 of the plane; FR5b tracks them.
 move.l a2,d1
 addi.l #9600,d1
 moveq #0,d0
 move.w $66c8c,d0
 addi.w #100,d0
 mulu.w #48,d0
 neg.l d0
 add.l d1,d0
 move.l a2,a0
 bsr.l FF1FastRenderTargetScan
 move.l a0,d4
 sub.l a2,d4
 ENDC
 adda.l #9598,a2
 move.w $66c8c,d5
 addi.w #100,d5
.band:
 moveq #16,d6
 cmp.w d6,d5
 bhs.b .height
 move.w d5,d6
.height:
 move.l a2,a3
 move.w d6,d3
 subq.w #1,d3
 moveq #0,d2
.row:
 IFD FF1_FAST_RENDER
 lea 2(a3,d4.l),a4
 ELSE
 lea 2(a3),a4
 ENDC
 moveq #24,d0
.scan:
 cmp.w d2,d0
 bls.b .nextrow
 tst.l -(a4)
 bne.b .bound
 subq.w #2,d0
 bra.b .scan
.bound:
 move.w d0,d2
 cmpi.w #24,d2
 beq.b .scanned
.nextrow:
 suba.w #48,a3
 dbra d3,.row
.scanned:
 tst.w d2
 beq.b .advance
 jsr $2a130
 moveq #24,d0
 sub.w d2,d0
 add.w d0,d0
 move.l a2,a3
 suba.w d0,a3
 IFD FF1_FAST_RENDER
 move.l FF1FastRenderRegs(pc),a0
 ELSE
 lea $dff000,a0
 ENDC
 move.w d0,$60(a0)
 move.w d0,$66(a0)
 move.l a3,$48(a0)
 move.l a3,$54(a0)
 move.w d6,d0
 lsl.w #6,d0
 or.w d2,d0
 IFD FF1_FAST_RENDER
 moveq #FRSITE_FILL,d1
 bsr.l FF1FastRenderSize
 ELSE
 move.w d0,$58(a0)
 ENDC
.advance:
 move.w d6,d0
 mulu.w #48,d0
 suba.l d0,a2
 sub.w d6,d5
 bne.b .band
 ; Wait before moving to the other plane, and before returning ownership.
 jsr $2a130
 dbra d7,.plane
 IFD FF1_FAST_RENDER
 move.l FF1FastRenderRegs(pc),a0
 clr.w $60(a0)
 clr.w $66(a0)
 ELSE
 clr.w $dff060
 clr.w $dff066
 ENDC
 movem.l (sp)+,d0-d7/a0-a6
 ; Match native CPU outputs and the final WaitBlit boundary.
 move.l $226ae,a1
 addq.l #4,a1
 lea $dff000,a0
 move.l (a1),d0
 addi.l #9598,d0
 move.w $66c8c,d0
 lsl.w #6,d0
 addi.w #$1918,d0
 jmp $2a130
.native:
 IFD FF1_FAST_RENDER
 bsr.l FF1FastRenderNativeGuard
 ENDC
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6abcc
; Immutable equal-layout A/B preset; excluded from lifecycle zero ranges.
FF1RenderFillControl: dc.w 1
