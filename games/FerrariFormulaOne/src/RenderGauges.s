; H13: bounded one-row monochrome gauge strips on 030/040/060+Fast.
; Two native call sites draw live source pixels into the cockpit's Chip planes.
; Preserve the native ownership boundary and finish through its DisownBlitter.
; All other dimensions, colours and destinations retain the general operation.
FF1RenderInstallGauges:
 lea start(pc),a0
 suba.l #FF1_HOST_CODE_SIZE,a0
 move.l FF1_HOST_ATTN(a0),d0
 andi.l #$8c,d0
 beq.b .done
 cmpi.w #$4eb9,$6bd66
 bne.l FF1ProductionFault
 cmpi.l #$24ae0,$6bd68
 bne.l FF1ProductionFault
 cmpi.w #$4eb9,$6bdb6
 bne.l FF1ProductionFault
 cmpi.l #$24ae0,$6bdb8
 bne.l FF1ProductionFault
 tst.w FF1RenderGaugeControl(pc)
 beq.b .done
 lea FF1RenderGaugeStrip(pc),a0
 move.l a0,$6bd68
 move.l a0,$6bdb8
.done:
 rts
FF1RenderGaugeStrip:
 ; Native stack arguments, including source/target stride, colour and depth.
 cmpi.w #1,42(sp)
 bne.w .native
 cmpi.w #3,46(sp)
 bne.w .native
 cmpi.w #12,34(sp)
 bne.w .native
 cmpi.w #6,50(sp)
 bne.w .native
 tst.w 54(sp)
 bne.w .native
 tst.w 10(sp)
 bne.w .native
 tst.w 14(sp)
 bne.w .native
 tst.w $1c1e8
 beq.w .native
 movem.l d0-d7/a0-a6,-(sp)
 lea 60(sp),a6
 move.l 20(a6),a2
 cmpa.l #$1fdb8,a2
 bne.w .fallback
 move.l 4(a6),a0
 cmpa.l #$255be,a0
 beq.b .source
 cmpa.l #$255da,a0
 bne.w .fallback
.source:
 move.w 38(a6),d0
 cmpi.w #68,d0
 beq.b .width
 cmpi.w #40,d0
 bne.w .fallback
.width:
 move.w 26(a6),d1
 cmpi.w #68,d1
 bhi.w .fallback
 move.w 30(a6),d2
 cmpi.w #23,d2
 bhi.w .fallback
 move.w 18(a6),d3
 lsl.w #4,d3
 cmp.w d0,d3
 blo.w .fallback
 tst.w $1c1b4
 bne.b .owned
 jsr $2a260
.owned:
 jsr $2a130
 move.w d1,d5
 andi.w #15,d5
 lsr.w #4,d1
 add.w d1,d1
 mulu.w #24,d2             ; cockpit: 12 words per row
 add.w d1,d2
 ; D2 destination offset, D5 shift, D6 last-word mask, D7 last word.
 move.w d0,d6
 add.w d5,d6
 subq.w #1,d6
 move.w d6,d7
 lsr.w #4,d7
 andi.w #15,d6
 moveq #15,d4
 sub.w d6,d4
 moveq #-1,d6
 lsl.w d4,d6
 moveq #0,d3                ; foreground 6/background 0: planes 1+2 use source
.plane:
 move.l 4(a6),a0
 move.l (a2)+,a1
 adda.w d2,a1
 IFD FF1_FAST_RENDER
 exg a0,a1
 moveq #0,d0
 move.w d7,d0
 addq.l #1,d0
 add.l d0,d0                ; the words of one row
 bsr.l FF1FastRenderTargetSpan
 exg a0,a1
 ENDC
 moveq #0,d0
 move.w d7,d4
.word:
 swap d0
 move.w (a0)+,d0
 move.l d0,d1
 lsr.l d5,d1
 tst.w d3
 bne.b .colour
 moveq #0,d1
.colour:
 moveq #-1,d0
 cmp.w d7,d4
 bne.b .notfirst
 lsr.w d5,d0
.notfirst:
 tst.w d4
 bne.b .notlast
 and.w d6,d0
.notlast:
 and.w d0,d1
 not.w d0
 and.w (a1),d0
 or.w d0,d1
 move.w d1,(a1)+
 ; Keep the preceding unshifted source word for the next shift.
 moveq #0,d0
 move.w -2(a0),d0
 dbra d4,.word
 addq.w #1,d3
 cmpi.w #3,d3
 bne.b .plane
 movem.l (sp)+,d0-d7/a0-a6
 andi #$ef,ccr
 jmp $24d70
.fallback:
 movem.l (sp)+,d0-d7/a0-a6
.native:
 jmp $24ae0
; Immutable equal-layout preset; the lifecycle must not reset it.
FF1RenderGaugeControl: dc.w 1
