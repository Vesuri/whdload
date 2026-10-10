; End a gameplay session before menus/setup can publish more timed input.
; Called after the native result animation, before returning to menus; never at pause.
timing_session_finish
 bsr timing_session_end
 bra.w timing_session_native_cleanup
timing_session_native_cleanup dc.w $4ef9
 dc.l 0
timing_session_end
 move.w sr,-(sp)
 movem.l d0/a0-a1,-(sp)
 IFNE TIMING_WORLD20
 bsr timing_pit_abort
 lea timing_pit_state(pc),a0
 clr.w 60(a0)
 ENDC
 bsr timing_world_restore
 lea timing_state(pc),a1
 tst.w timing_started-timing_state(a1)
 beq.w .done
 ; Stop the VBL producer before touching queue ownership.
 clr.w timing_started-timing_state(a1)
 lea timing_session_state(pc),a0
 addq.l #1,12(a0)
 moveq #0,d0
 move.w timing_orientation_left-timing_state(a1),d0
 add.l d0,16(a0)
 move.l timing_phase-timing_state(a1),d0
 add.l d0,20(a0)
 move.w timing_input_write-timing_state(a1),d0
 sub.w timing_input_read-timing_state(a1),d0
 and.l #TIMING_INPUT_MASK,d0
 lsr.l #4,d0
 add.l d0,24(a0)
 moveq #0,d0
 move.w timing_engine_count-timing_state(a1),d0
 sub.w timing_engine_read-timing_state(a1),d0
 add.l d0,32(a0)
 move.l timing_last-timing_state(a1),36(a0)
 IFNE TIMING_WORLD20
 bsr timing_world_input_disable
 moveq #0,d0
 move.w timing_key_write(pc),d0
 sub.w timing_key_read(pc),d0
 and.w #TIMING_KEY_MASK,d0
 lsr.w #3,d0
 add.l d0,28(a0)
 ENDC
 bsr timing_session_clear_work
.done
 movem.l (sp)+,d0/a0-a1
 move.w (sp)+,ccr
 rts

; Caller owns saved registers/CCR; producer must already be stopped.
timing_session_clear_work
 clr.w timing_due-timing_state(a1)
 clr.l timing_phase-timing_state(a1)
 clr.w timing_control_left-timing_state(a1)
 clr.w timing_resource_left-timing_state(a1)
 clr.w timing_orientation_left-timing_state(a1)
 clr.l timing_input_read-timing_state(a1)
 clr.w timing_input_control_active-timing_state(a1)
 clr.w timing_input_paused-timing_state(a1)
 clr.w timing_brake_active-timing_state(a1)
 clr.l timing_brake_phase-timing_state(a1)
 clr.l timing_brake_pending-timing_state(a1)
 clr.l timing_brake_read-timing_state(a1)
 clr.l timing_engine_active-timing_state(a1)
 clr.l timing_engine_count-timing_state(a1)
 rts

timing_session_state dc.b 'PDSESS01'
 dc.l 0 ; player timing epochs initialized
 dc.l 0 ; active sessions explicitly closed
 dc.l 0 ; assigned unfinished world steps discarded at exit
 dc.l 0 ; unassigned time debt discarded (native clock units)
 dc.l 0 ; unconsumed input events discarded
 dc.l 0 ; unconsumed centering keys discarded
 dc.l 0 ; unpresented engine events discarded
 dc.l 0 ; scheduler timestamp at last explicit exit
