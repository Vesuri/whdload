; Pit arrival rise $1459a..$145bc: 15 native steps over table $144ae (x=160). Natively each
; step lasts as long as its drawing, five PAL fields on the A500 and three on an A1200-class
; machine. Pace every step to the A500's 100 ms and, while the time allows, present extra
; frames with the ship blended towards the next table height for the time they are shown.
; Deadlines retain overruns. Extra frames run the native body with the pit frame's service
; part reduced to the HUD clock (timing_repair_service_gate), so presentation never advances
; the frame counter, keyboard or opponents. The flags at both hook sites are dead.
TIMING_RISE_PERIOD = 20
TIMING_RISE_X = 160

; Replaces MOVE.W #160,d0 / MOVE.W (a0)+,d1, the loop head and only DBF target.
timing_rise_step
 cmp.w #14,d7
 bne.s .ready
 movem.l d0-d1/a0-a1,-(sp)
 bsr timing_clock
 move.l perf_game(pc),a0
 lea timing_rise_state(pc),a1
 move.l $f96(a0),8(a1)
 addq.l #1,24(a1)
 movem.l (sp)+,d0-d1/a0-a1
.ready
 move.w #TIMING_RISE_X,d0
 move.w (a0)+,d1
 bra.w timing_rise_continue

; Replaces MOVEM.L (sp)+,d7-a0 / DBF d7,$1459a. The step's native frame has just been
; presented; a0 points at the next table height.
timing_rise_end
 movem.l (sp)+,d7/a0
 movem.l d0-d7/a0-a5,-(sp)
 move.l perf_game(pc),a5
 lea timing_rise_state(pc),a4
 add.l #TIMING_RISE_PERIOD,8(a4)
 bsr timing_clock
 move.l $f96(a5),d5             ; when this step's frame was shown
 move.w -2(a0),d3               ; its height
 moveq #0,d4
 tst.w d7
 beq.s .wait                    ; the last step has nothing to blend towards
 move.w (a0),d4
 sub.w d3,d4                    ; height still to travel
.frame
 bsr timing_clock
 move.l $f96(a5),d0
 move.l 8(a4),d1
 sub.l d0,d1                    ; time to the deadline
 ble.s .due
 move.l 4(a4),d2                ; cost of one extra frame
 move.l d2,d6
 lsr.l #1,d6
 add.l d6,d1
 cmp.l d2,d1                    ; shown by deadline + cost/2?
 blt.s .wait
 ; f = (now + cost - shown) / (deadline + cost - shown), the native next step's arrival.
 move.l d0,d1
 add.l d2,d1
 sub.l d5,d1
 move.l 8(a4),d6
 add.l d2,d6
 sub.l d5,d6
 ble.s .wait
 cmp.l d6,d1
 bge.s .wait
 move.w d4,d0
 muls.w d1,d0
 divs.w d6,d0
 add.w d3,d0
 cmp.w 2(a4),d0                 ; no new height, no new frame
 beq.s .wait
 move.w d0,2(a4)
 move.l $f96(a5),d6
 bsr.s timing_rise_draw
 bsr timing_clock
 move.l $f96(a5),d0
 sub.l d6,d0
 move.l d0,4(a4)
 addq.l #1,12(a4)
 bra.s .frame
.wait
 bsr timing_clock
 move.l 8(a4),d1
 sub.l $f96(a5),d1
 bgt.s .wait
.due
 move.w #$8000,2(a4)            ; no height drawn yet in the next step
 movem.l (sp)+,d0-d7/a0-a5
 dbra d7,.again
 bra.w timing_rise_return
.again
 bra.w timing_rise_loop

; The native loop body for the height in 2(a4): sprite, ship pieces, pit frame.
timing_rise_draw
 movem.l d0-d7/a0-a6,-(sp)
 move.w #1,(a4)
 move.w #TIMING_RISE_X,d0
 move.w 2(a4),d1
 movem.l d0-d1/d7-a0,-(sp)
 bsr timing_rise_sprite
 movem.l (sp)+,d0-d1/d7-a0
 bsr timing_rise_ship
 bsr timing_rise_frame
 movem.l (sp)+,d0-d7/a0-a6
 clr.w timing_rise_state-timing_rise_state(a4)
 rts

; From timing_repair_service_gate: an extra frame draws the HUD clock in this buffer too,
; then leaves the pit frame without its service part.
timing_rise_service
 tst.w $da(a6)
 beq.w timing_repair_service_return
 bsr timing_rise_hud
 bra.w timing_repair_service_return

timing_rise_loop dc.w $4ef9
 dc.l 0
timing_rise_continue dc.w $4ef9
 dc.l 0
timing_rise_return dc.w $4ef9
 dc.l 0
timing_rise_sprite dc.w $4ef9
 dc.l 0
timing_rise_ship dc.w $4ef9
 dc.l 0
timing_rise_frame dc.w $4ef9
 dc.l 0
timing_rise_hud dc.w $4ef9
 dc.l 0

timing_rise_tag dc.b 'PDRISE01'
timing_rise_state
 dc.w 0                         ; +0 drawing an extra frame
 dc.w $8000                     ; +2 last extra height drawn in this step
 dc.l 12                        ; +4 clock units per extra frame (starts at three fields)
 dc.l 0                         ; +8 deadline
 dc.l 0                         ; +12 extra frames presented
 dc.l 0                         ; +16 reserved
 dc.l 0                         ; +20 reserved
 dc.l 0                         ; +24 rises
