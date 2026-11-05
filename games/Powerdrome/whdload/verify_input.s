; Shared input-only fixtures for development and original-loader verification.
; Fixture submits an empty pilot name through the native text-entry path.
; Only the two six-byte JSRs are replaced; normal builds have neither patch.
pl_verify PL_START
 PL_PS $13772,key_ready
 PL_PS $1377c,key_return
 PL_END
key_ready moveq #-1,d0
 rts
key_return moveq #13,d0
 rts
; Whole six-byte input JSRs. Installed for CUSTOM5=2 and the coverage routes.
; Key 3 selects the same menu item as the top-middle Practice button.
pl_practice PL_START
 PL_PS $12f6a,practice_ready
 PL_PS $130a4,practice_key
 PL_PS $13c50,pit_ready
 PL_PS $13cde,pit_key
 PL_END
practice_ready
 IFD COVERAGE_INPUT
 move.l custom5(pc),d0
 cmp.l #9,d0
 beq.w coverage_joystick_menu_ready
 cmp.l #6,d0
 beq.w coverage_menu_ready
 ENDC
 moveq #0,d0
 move.w practice_sent(pc),d0
 subq.w #1,d0
 rts
practice_key
 IFD COVERAGE_INPUT
 move.l custom5(pc),d0
 cmp.l #9,d0
 beq.w coverage_joystick_menu_key
 cmp.l #6,d0
 beq.w coverage_menu_key
 ENDC
 move.l a0,-(sp)
 lea practice_sent(pc),a0
 move.w #1,(a0)
 move.l (sp)+,a0
 IFD COVERAGE_INPUT
 move.l custom5(pc),d0
 cmp.l #14,d0
 beq.s .practice_timing
 cmp.l #12,d0
 beq.s .practice_timing
 cmp.l #11,d0
 bne.s .default_route
.practice_timing
 moveq #'3',d0
 rts
.default_route
 cmp.l #4,d0
 shs d0
 andi.l #1,d0
 add.l #$33,d0
 ELSE
 moveq #$33,d0
 ENDC
 rts
pit_ready
 IFD COVERAGE_INPUT
 move.w cov_started(pc),d0
 bne.w coverage_pit_ready
 ENDC
 moveq #0,d0
 move.w pit_sent(pc),d0
 subq.w #1,d0
 rts
pit_key
 IFD COVERAGE_INPUT
 move.w cov_started(pc),d0
 bne.w coverage_pit_key
 ENDC
 move.l a0,-(sp)
 lea pit_sent(pc),a0
 move.w #1,(a0)
 move.l (sp)+,a0
 moveq #32,d0
 rts
practice_sent dc.w 0
pit_sent dc.w 0
