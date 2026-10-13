; B8 completion of the S3 split. These native draw-body state writes must run
; even when no frame is drawn. All remain disabled outside the B8 candidate.
 IFD FF1_RENDER_POSES
B8ViewTick:
 ; Native $6574a..$6577c. Recovery uses this flag, so refresh before recovery.
 move.w $6a67a,d0
 add.w $66f96,d0
 andi.w #1023,d0
 moveq #0,d1
 cmpi.w #256,d0
 ble.b .store
 cmpi.w #768,d0
 bge.b .store
 moveq #1,d1
.store:
 move.w d1,$66c7c
 rts

B8NativePresentationTick:
 ; Native $657a6..$657d6, before FF1InstrumentTick advances the phases.
 move.w $1c6a2,d0
 asr.w #5,d0
 move.w d0,d2
 addi.w #32,d0
 move.w $2275a,d1
 muls.w d1,d0
 asr.w #4,d0
 move.w d0,$66c88
 moveq #32,d0
 sub.w d2,d0
 muls.w d0,d1
 asr.w #4,d1
 move.w d1,$66c8a
 ; Native h164 pit-range flags, without its text drawing. These flags feed
 ; movement/contact code. Latch the player message separately for presentation.
 lea $6a60a,a0
 lea $d0dc,a1
 moveq #0,d3
.car:
 move.w (a0)+,d0
 cmp.w $1c1e4,d0
 bge.b .outside
 cmp.w $1c1e2,d0
 ble.b .outside
 tst.b (a1)
 bne.b .next
 move.b #1,(a1)
 tst.w d3
 bne.b .next
 moveq #1,d2
 bra.b .message
.outside:
 tst.b (a1)
 beq.b .next
 clr.b (a1)
 tst.w d3
 bne.b .next
 moveq #2,d2
.message:
 tst.w $1c1c2
 beq.b .next
 IFD FF1_COARSE_STEP
 lea B8PitMessage(pc),a2
 ELSE
 lea (B8PitMessage.l,pc),a2
 ENDC
 move.w d2,(a2)
.next:
 addq.l #1,a1
 addq.w #1,d3
 cmpi.w #8,d3
 blo.b .car
 rts

B8PresentPit:
 movem.l d0-d7/a0-a6,-(sp)
 IFD FF1_COARSE_STEP
 move.w B8PitMessage(pc),-(sp)
 tst.w (sp)+
 ELSE
 tst.w B8PitMessage(pc)
 ENDC
 beq.b .done
 moveq #1,d0
 move.l d0,-(sp)
 clr.l -(sp)
 jsr $670d0
 addq.l #8,sp
 IFD FF1_COARSE_STEP
 move.w B8PitMessage(pc),-(sp)
 cmpi.w #1,(sp)+
 ELSE
 cmpi.w #1,B8PitMessage(pc)
 ENDC
 bne.b .outside
 pea 44.w
 pea 288.w
 pea $d0c0
 jsr $239a0
 lea 12(sp),sp
 pea 44.w
 pea 336.w
 pea 14.w
 jsr $23a6a
 lea 12(sp),sp
 bra.b .restore
.outside:
 pea 44.w
 pea 272.w
 pea $d0c6
 jsr $239a0
 lea 12(sp),sp
.restore:
 jsr $670fc
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
B8PitMessage: dc.w 0
 ENDC
