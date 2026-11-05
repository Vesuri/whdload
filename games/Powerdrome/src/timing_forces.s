; WORLD20: native fall/impulse vectors denote displacement per 90-ms epoch.
; Integrate every 20 ms, splitting exactly at each effect's 90-ms boundary.
; No native calls or nonlocal exits occur inside these wrappers.
timing_forces_initialize
 movem.l d0/a0,-(sp)
 lea timing_force_state+8(pc),a0
 moveq #7,d0
.clear
 clr.l (a0)+
 dbra d0,.clear
 movem.l (sp)+,d0/a0
 rts

; d0 = signed word displacement per epoch, d2 = elapsed units (1..4).
; a1 = signed remainder word, advanced to the next axis. d1 is scratch.
timing_force_fraction
 muls.w d2,d0
 move.w (a1),d1
 ext.l d1
 add.l d1,d0
 divs.w #18,d0
 move.l d0,d1
 swap d1
 move.w d1,(a1)+
 rts

timing_fall_step
 movem.l d0-d4/a0-a1,-(sp)
 move.w (a0),d3 ; native eligibility: negative permits age above 50
 lea timing_force_state(pc),a0
 addq.l #1,24(a0)
 moveq #4,d4
.part
 moveq #18,d2
 sub.w 8(a0),d2
 cmp.w d4,d2
 bls.s .chunk
 move.w d4,d2
.chunk
 move.w $1a4(a6),d0 ; low word of the native long age
 add.w d0,d0 ; preserve native word overflow before signed scaling
 lea 10(a0),a1
 bsr timing_force_fraction
 sub.w d0,d6
 add.w d2,8(a0)
 sub.w d2,d4
 cmp.w #18,8(a0)
 bne.s .done
 clr.w 8(a0)
 addq.l #1,$1a2(a6)
 addq.l #1,28(a0)
 tst.w d4
 beq.s .done
 tst.w d3
 bmi.s .part
 cmp.l #50,$1a2(a6)
 ble.s .part
.done
 movem.l (sp)+,d0-d4/a0-a1
 asl.w #1,d0 ; native scratch result; following TST defines branch flags
 bra.w timing_fall_continue

; Reset the local fraction whenever native code resets the age, including repair.
timing_fall_reset
 move.l a0,-(sp)
 lea timing_force_state(pc),a0
 clr.l 8(a0)
 movem.l (sp)+,a0
 move.l #0,$1a2(a6)
 rts

timing_impulse_step
 movem.l d0-d4/a0-a1,-(sp)
 lea timing_force_state(pc),a0
 addq.l #1,32(a0)
 moveq #4,d4
.part
 moveq #18,d2
 sub.w 12(a0),d2
 cmp.w d4,d2
 bls.s .chunk
 move.w d4,d2
.chunk
 lea 14(a0),a1
 move.w $1da(a6),d0
 bsr timing_force_fraction
 add.w d0,d5
 move.w $1dc(a6),d0
 bsr timing_force_fraction
 add.w d0,d6
 move.w $1de(a6),d0
 bsr timing_force_fraction
 add.w d0,d7
 add.w d2,12(a0)
 sub.w d2,d4
 cmp.w #18,12(a0)
 bne.s .done
 clr.w 12(a0)
 move.w $1e6(a6),d0
 addq.w #1,d0
 cmp.w $1e4(a6),d0
 blt.s .active
 move.w #0,$1e0(a6)
.active
 move.w d0,$1e6(a6)
 asr.w $1da(a6)
 asr.w $1dc(a6)
 asr.w $1de(a6)
 addq.l #1,36(a0)
 tst.w $1e0(a6)
 beq.s .done
 tst.w d4
 bne.s .part
.done
 movem.l (sp)+,d0-d4/a0-a1
 ; Native successor stores positions, then NEG defines X before any consumer.
 bra.w timing_impulse_continue

timing_impulse_reset
 move.l a0,-(sp)
 lea timing_force_state(pc),a0
 clr.l 12(a0)
 clr.l 16(a0)
 addq.l #1,20(a0)
 movem.l (sp)+,a0
 rts

timing_impulse_random_start
 bsr timing_impulse_reset
 move.w #0,$1e6(a6)
 rts

timing_impulse_field_start
 bsr timing_impulse_reset
 move.w #-1,$1e0(a6)
 rts

timing_fall_continue dc.w $4ef9
 dc.l 0
timing_impulse_continue dc.w $4ef9
 dc.l 0

timing_force_state dc.b 'PDW20F01'
 dc.w 0 ; +8 fall phase (0..17)
 dc.w 0 ; +10 signed fall remainder
 dc.w 0 ; +12 impulse phase (0..17)
 ds.w 3 ; +14 three signed impulse remainders
 dc.l 0 ; +20 native impulse initializations
 dc.l 0 ; +24 fall step calls
 dc.l 0 ; +28 fall age advances
 dc.l 0 ; +32 impulse step calls
 dc.l 0 ; +36 impulse decay advances
