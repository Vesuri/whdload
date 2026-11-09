; Split native opponent motion/contact/effect generation from projection.
; Six 20-ms world ticks own each persistent update (120 ms). Projection
; still executes for each rendered view. Native mode paths outside human flight
; retain their original behavior until their own timing contracts are audited.
timing_opponent_effects_enabled
 move.l d0,-(sp)
 move.w timing_started(pc),d0
 beq.s .done
 tst.w $be(a6)
 bne.s .no
 tst.w $b6(a6)
 bne.s .no
 tst.w $43a(a6)
 bpl.s .no
 moveq #1,d0
 bra.s .done
.no
 moveq #0,d0
.done
 ; MOVEM preserves the eligibility flags while restoring the caller's D0.
 tst.w d0
 movem.l (sp)+,d0
 rts

timing_opponent_effects_initialize
 IFNE TIMING_OPPONENT_MOTION
 bsr timing_opponent_motion_reset
 ENDC
 move.l a0,-(sp)
 lea timing_opponent_effects_state(pc),a0
 clr.w 10(a0)
 clr.l 28(a0)
 movea.l (sp)+,a0
 rts

timing_opponent_effects_tick
 movem.l d0-d7/a0-a6,-(sp)
 bsr timing_opponent_effects_enabled
 beq.w .done
 move.w timing_world_state+8(pc),d0
 beq.w .done
 move.w timing_pit_state+8(pc),d0
 bne.w .done
 ; Advance once per sixth completed world step, independent of drawing.
 lea timing_opponent_effects_state(pc),a0
 addq.w #1,10(a0)
 cmp.w #6,10(a0)
 blo.w .done
 clr.w 10(a0)
 addq.l #1,28(a0)
 tst.w $172(a6)
 bne.w .done
 tst.w $aa(a6)
 bne.w .done
 lea timing_opponent_effects_state(pc),a0
 move.w #1,8(a0)
 addq.l #1,12(a0)
 move.l timing_world20_clock(pc),24(a0)
 move.l $5e(a6),-(sp)
 move.l 28(a0),$5e(a6)
 movea.l $342(a6),a5
 move.w $340(a6),d7
 bmi.s .finished
 move.w $11e(a6),d6
 move.w $200(a6),d5
.next
 tst.w $56(a5)
 bne.s .skip
 move.w $2(a5),d4
 cmp.w d6,d5
 bge.s .linear
 cmp.w d6,d4
 bge.s .visible
 cmp.w d5,d4
 bgt.s .skip
 bra.s .visible
.linear
 cmp.w d6,d4
 blt.s .skip
 cmp.w d5,d4
 bgt.s .skip
.visible
 lea timing_opponent_effects_state(pc),a0
 addq.l #1,16(a0)
 bsr timing_opponent_effects_native
.skip
 adda.w #190,a5
 dbra d7,.next
.finished
 move.l (sp)+,$5e(a6)
 lea timing_opponent_effects_state(pc),a0
 clr.w 8(a0)
.done
 movem.l (sp)+,d0-d7/a0-a6
 rts

; Replacement for the scene's JSR 9950. Its register-save frame must match
; the native projection tail, which restores it at A268.
timing_opponent_effects_render
 bsr timing_opponent_effects_enabled
 beq.w timing_opponent_effects_native
 movem.l d0-d7/a0-a4,-(sp)
 move.l a0,-(sp)
 lea timing_opponent_effects_state(pc),a0
 addq.l #1,20(a0)
 movea.l (sp)+,a0
 bra.w timing_opponent_projection

; Native 9D9E is NOP followed by MOVE.W 20(A5),D0. A logical update returns
; before model projection; a rendered view replays those native instructions.
timing_opponent_projection
 move.l a0,-(sp)
 lea timing_opponent_effects_state(pc),a0
 tst.w 8(a0)
 movea.l (sp)+,a0
 bne.w timing_opponent_effects_exit
 move.w $20(a5),d0
 bra.w timing_opponent_projection_continue

timing_opponent_effects_native dc.w $4ef9
 dc.l 0
timing_opponent_effects_exit dc.w $4ef9
 dc.l 0
timing_opponent_projection_continue dc.w $4ef9
 dc.l 0

timing_opponent_effects_state dc.b 'PDANIM01'
 dc.w 0,0 ; logical preparation active, world-step phase 0..5
 dc.l 0 ; eligible logical opponent ticks
 dc.l 0 ; visible opponent updates
 dc.l 0 ; projection-only render calls
 dc.l 0 ; most recent eligible logical world time
 dc.l 0 ; elapsed 120-ms effect phases, including invisible intervals
