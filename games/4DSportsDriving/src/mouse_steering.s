; Finer mouse steering.
;
; The game turns the mouse into a target wheel angle and then, once per simulation
; step, into a digital left/right/neutral decision that the replay history records
; (h0:9020). The steering itself only ever sees those bits, so replays and the
; simulation are unchanged; only how the live mouse picks the bits is.
;
; Native behaviour, and why it felt coarse:
; - The mouse counter ($20f8(a4), 4 counts per pixel) gives x; (x-160)/2 indexes the
;   table at -$7514(a4), which is 0 for the first 7 entries: 56 counts of dead zone,
;   then 1 angle unit per 8 counts.
; - h0:9020 presses right only when the target is at least one whole step (the car
;   table's byte 1, 1..8 units by speed, times 4 when countersteering) past the
;   wheel, else it leaves the wheel neutral, which centres it by twice that step.
;   A small target never steers; a larger one gives a sawtooth well below it.
;
; Here the target loses the dead zone and is interpolated between table entries,
; and the decision picks whichever of right, left or neutral leaves the wheel
; nearest the target, carrying the remaining error into the next step so the
; wheel's average follows the mouse. In A4000 mode there is a fourth choice, hold
; (bit 6, which the game never reads; sim_a4000_steering keeps the wheel), so the
; wheel moves to the target and stays there instead of averaging around it.

; d0.b <- signed target angle (-127..127) from the mouse counter. Others preserved.
mouse_steer_target:
 movem.l d1-d2/a0,-(sp)
 move.w $20f8(a4),d0       ; x counter, x << shift plus the sub-pixel counts
 ext.l d0
 asl.l #2,d0
 moveq #0,d1
 move.b $20f3(a4),d1       ; x shift (2)
 asr.l d1,d0
 sub.w #160*4,d0            ; counts from the centre that h0:8fdc sets
 move.w d0,-(sp)
 bpl.s .abs
 neg.w d0
.abs:
 move.w d0,d1
 and.w #7,d1                ; fraction between table entries
 lsr.w #3,d0
 addq.w #7,d0               ; skip the native dead zone (entries 0..6 are 0)
 cmp.w #61,d0
 blo.s .interp
 moveq #127,d0              ; table entry 61 onwards is the 127 limit
 bra.s .sign
.interp:
 lea -$7514(a4),a0
 moveq #0,d2
 move.b 1(a0,d0.w),d2
 move.b (a0,d0.w),d0
 and.w #$ff,d0
 sub.w d0,d2
 mulu d1,d2
 addq.w #4,d2
 lsr.w #3,d2
 add.w d2,d0
.sign:
 tst.w (sp)+
 bpl.s .done
 neg.w d0
.done:
 movem.l (sp)+,d1-d2/a0
 rts

; PL_PS h0:7b08 then PL_S over the native conversion to h0:7b4e. Pops the three
; arguments of the native mouse read before it, as h0:7b1a did.
mouse_steer_native:
 move.l (sp)+,a0
 lea 12(sp),sp
 move.l a0,-(sp)
 bsr mouse_steer_target
 move.b d0,-$2f0c(a4)
 rts

; Replaces h0:9020 (PL_P). For history slot -$940(a4): when the steering ring at
; $ab0(a4) has a target (flag at $af0(a4)), OR right (4) or left (8) into the
; history byte at -$1770(a4) and clear the flag. The outcomes follow h0:1033a and,
; at 50 Hz, sim_steering_50 (two fifths of each step); all in fifths of a unit.
mouse_steer_decide:
 movem.l d0-d7/a0-a1,-(sp)
 ; The carried error belongs to the step just decided. Any other history slot
 ; (a restart, a replay, keyboard steps in between) starts again from none.
 lea mouse_steer_slot(pc),a0
 move.w -$940(a4),d7
 move.w (a0),d0
 addq.w #1,d0
 cmp.w d0,d7
 beq.s .next
 lea mouse_steer_error(pc),a1
 clr.w (a1)
.next:
 move.w d7,(a0)
 and.w #63,d7
 lea $af0(a4),a0
 tst.b (a0,d7.w)
 beq .return
 clr.b (a0,d7.w)
 lea $ab0(a4),a0
 move.b (a0,d7.w),d6
 ext.w d6
 muls #5,d6                ; d6 = target in fifths
 moveq #5,d5               ; d5 = fifths applied per native step
 cmp.w #50,-$15fa(a4)
 bne.s .rate
 moveq #2,d5
.rate:
 move.w -$902(a4),d0       ; speed
 moveq #10,d1
 lsr.w d1,d0
 and.w #$fffc,d0
 ext.w d0                   ; the native signed-byte row index
 move.l -$b8(a4),a0
 adda.w d0,a0
 move.w -$90e(a4),d4       ; wheel angle
 move.w d4,d3
 muls #5,d3                ; d3 = angle in fifths
 ; d0 = right outcome
 move.b 1(a0),d0
 ext.w d0
 cmp.w #-1,d4
 bge.s .right
 asl.w #2,d0
.right:
 muls d5,d0
 add.w d3,d0
 ; d1 = left outcome
 move.b 2(a0),d1
 ext.w d1
 cmp.w #1,d4
 ble.s .left
 asl.w #2,d1
.left:
 muls d5,d1
 add.w d3,d1
 ; d2 = neutral outcome: centring by twice the step while moving, then the
 ; native +/-8 neutral zone
 move.w d3,d2
 tst.w -$902(a4)
 beq.s .zone
 move.b 1(a0),d4
 ext.w d4
 add.w d4,d4
 muls d5,d4
 tst.w d2
 bmi.s .from_left
 sub.w d4,d2
 bpl.s .zone
 moveq #0,d2
 bra.s .zone
.from_left:
 add.w d4,d2
 bmi.s .zone
 moveq #0,d2
.zone:
 cmp.w #8*5,d2
 bge.s .clamp
 cmp.w #-8*5,d2
 ble.s .clamp
 moveq #0,d2
.clamp:
 move.w #240*5,d4
 cmp.w d4,d0
 ble.s .r_ok
 move.w d4,d0
.r_ok:
 neg.w d4
 cmp.w d4,d1
 bge.s .l_ok
 move.w d4,d1
.l_ok:
 lea mouse_steer_error(pc),a1
 ; A target the wheel cannot reach this step: steer flat out, no carried error.
 cmp.w d0,d6
 bge .go_right
 cmp.w d1,d6
 ble .go_left
 move.w d6,d3
 add.w (a1),d3             ; d3 = target plus carried error
 ; Bound the carried error by the larger gap between neighbouring outcomes:
 ; enough to average any target in reach, little left to overshoot with.
 move.w d0,d6
 sub.w d2,d6
 move.w d2,d4
 sub.w d1,d4
 cmp.w d4,d6
 bhs.s .bound
 move.w d4,d6
.bound:
 ; nearest outcome, neutral on a tie
 move.w d3,d4
 sub.w d2,d4
 bpl.s .n_abs
 neg.w d4
.n_abs:
 moveq #0,d7               ; bits
 move.w d2,a0              ; chosen outcome
 move.w d0,d5
 sub.w d3,d5
 bpl.s .r_abs
 neg.w d5
.r_abs:
 cmp.w d4,d5
 bhs.s .try_left
 move.w d5,d4
 moveq #4,d7
 move.w d0,a0
.try_left:
 move.w d3,d5
 sub.w d1,d5
 bpl.s .l_abs
 neg.w d5
.l_abs:
 cmp.w d4,d5
 bhs.s .chosen
 move.w d5,d4
 moveq #8,d7
 move.w d1,a0
.chosen:
 cmp.w #50,-$15fa(a4)
 bne.s .carry
 ; A4000: holding the wheel (bit 6, sim_a4000_steering) when that is nearer still.
 ; It is never needed to average, so nothing is carried.
 move.w -$90e(a4),d0
 muls #5,d0
 sub.w d3,d0
 bpl.s .h_abs
 neg.w d0
.h_abs:
 cmp.w d4,d0
 bhs.s .no_hold
 moveq #$40,d7
.no_hold:
 clr.w (a1)
 bra.s .publish
.carry:
 move.w a0,d0
 sub.w d0,d3               ; the error left after this step
 move.w d6,d4
 cmp.w d4,d3
 ble.s .e_hi
 move.w d4,d3
.e_hi:
 neg.w d4
 cmp.w d4,d3
 bge.s .e_lo
 move.w d4,d3
.e_lo:
 move.w d3,(a1)
 bra.s .publish
.go_right:
 moveq #4,d7
 clr.w (a1)
 bra.s .publish
.go_left:
 moveq #8,d7
 clr.w (a1)
.publish:
 tst.w d7
 beq.s .return
 moveq #0,d0
 move.w -$940(a4),d0
 move.l -$1770(a4),a0
 or.b d7,(a0,d0.l)
.return:
 movem.l (sp)+,d0-d7/a0-a1
 rts

; PL_PSS h0:8ffc,2: the game centres the mouse (h0:8fdc, at race start, on M and
; around its dialogs): push the x argument and call the native setter as h0:8ffc and
; h0:9000 did, leaving both arguments for the caller's pop, then forget the carried
; error. The main task is the only caller.
mouse_steer_centre:
 move.l a0,-(sp)
 lea mouse_steer_return(pc),a0
 move.l 4(sp),(a0)
 move.l (sp)+,a0
 addq.l #4,sp
 move.w #160,-(sp)
 jsr -31782(a4)
 move.l a0,-(sp)
 lea mouse_steer_error(pc),a0
 clr.w (a0)
 move.l mouse_steer_return(pc),a0
 move.l a0,-(sp)
 move.l 4(sp),a0
 move.l (sp)+,(sp)
 rts

mouse_steer_error: dc.w 0  ; fifths of a unit still owed to the target
mouse_steer_slot: dc.w -2  ; history slot of the last decision
mouse_steer_return: dc.l 0
