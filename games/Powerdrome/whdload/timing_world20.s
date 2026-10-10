; Development stage: 20-ms movement with 90-ms controls/orientation/resources.
; Falling and impulse integration is in timing_forces.s.
timing_world20_begin
 movem.l d0-d1/a0,-(sp)
 lea timing_world20_state(pc),a0
 tst.w 8(a0)
 bne.s .clock_ready
 move.w #1,8(a0)
 move.l timing_input_clock(pc),12(a0)
.clock_ready
 bsr timing_input_for_world
 addq.l #1,16(a0)
 clr.w 10(a0)
 move.l 12(a0),d0
 sub.l timing_input_clock(pc),d0
 bmi.s .done
 move.w #1,10(a0)
 addq.l #1,20(a0)
.done
 movem.l (sp)+,d0-d1/a0
 rts

timing_world20_age
 bsr timing_world20_test_control
 beq.w timing_world20_skip_age
 addq.w #1,$288(a6)
 move.w $288(a6),d0
 bra.w timing_world20_after_age

timing_world20_contact
 bsr timing_world20_test_control
 beq.s .done
 move.w d0,-(sp)
 bsr timing_world20_contact_sound
 bra.w timing_world20_contact_continue
.done
 rts

timing_world20_damage
 bsr timing_world20_test_control
 beq.s .done
 addq.w #1,$286(a6)
 move.w $286(a6),d7
 bra.w timing_world20_damage_continue
.done
 rts

timing_world20_after_age dc.w $4ef9
 dc.l 0
timing_world20_skip_age dc.w $4ef9
 dc.l 0
timing_world20_contact_sound dc.w $4ef9
 dc.l 0
timing_world20_contact_continue dc.w $4ef9
 dc.l 0
timing_world20_damage_continue dc.w $4ef9
 dc.l 0

timing_world20_state dc.b 'PDW20T01'
timing_world20_initialized dc.w 0
timing_world20_control_due dc.w 0
timing_world20_clock dc.l 0
 dc.l 0 ; fast steps started
 dc.l 0 ; slow updates started

; TST with PC-relative addressing is not available on 68000.
timing_world20_test_control
 move.l d0,-(sp)
 move.w timing_world20_control_due(pc),d0
 movem.l (sp)+,d0
 rts

; DIVS uses truncation toward zero. Preserve its signed remainder across steps.
; Save the incoming X flag; the displaced TST will define the other flags.
timing_world20_divide
 move.w sr,-(sp)
 movem.l d0/a0,-(sp)
 lea timing_world20_scalar_remainder(pc),a0
 move.w (a0),d0
 ext.l d0
 add.l d0,d4
 divs.w #24,d4
 move.l d4,d0
 swap d0
 move.w d0,(a0)
 movem.l (sp)+,d0/a0
 move.w (sp)+,ccr
 tst.w $240(a6)
 bra.w timing_world20_after_divide

; ASR rounds down. A remainder in 0..4095 preserves that signed convention.
timing_world20_vectors
 movem.l d0/a0,-(sp)
 lea timing_world20_vector_remainders(pc),a0
 moveq #12,d3
 add.l (a0),d5
 move.l d5,d0
 and.l #$fff,d0
 move.l d0,(a0)+
 asr.l d3,d5
 add.l (a0),d6
 move.l d6,d0
 and.l #$fff,d0
 move.l d0,(a0)+
 asr.l d3,d6
 add.l (a0),d7
 move.l d7,d0
 and.l #$fff,d0
 move.l d0,(a0)
 asr.l d3,d7
 movem.l (sp)+,d0/a0
 bra.w timing_world20_after_vectors

timing_world20_after_divide dc.w $4ef9
 dc.l 0
timing_world20_after_vectors dc.w $4ef9
 dc.l 0

timing_world20_integrator dc.b 'PDW20I01'
timing_world20_scalar_remainder dc.w 0
 dc.w 0
timing_world20_vector_remainders ds.l 3

 INCLUDE timing_forces.s

 INCLUDE timing_keys.s
