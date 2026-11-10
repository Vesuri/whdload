; Opponent movement on 20-ms world steps. The native opponent update ($d3d6) stays on
; 90-ms control updates and remains the authority: it runs from the progress its previous
; update produced, so its decisions, random draws, timers, pit, lap and sound work are
; unchanged. Between updates each opponent's track progress ($66) advances every world
; step by the native speed formula for the next update, and the difference between the
; shown progress and the authoritative one is spread over the following 90 ms, never
; moving backwards. Position, heading, segment and player distance ($10..$14, $20, $2,
; $4c) are rebuilt from the shown progress with the native node blend ($d626..$d69a,
; $d724..$d750). The table lives in the fast arena; timing is only selected with it.
TIMING_OPPONENT_ARENA = $9600          ; free after the edge table, inside the $9800 minimum
TIMING_OPPONENT_SLOTS = 16
TIMING_OPPONENT_SNAP = 1024            ; larger gaps (repositioning) are applied at once
OPM_A = 0                              ; authoritative progress after the last native update
OPM_P = 4                              ; shown progress (old-lap units while a wrap is pending)
OPM_WRITTEN = 8                        ; value last written to $66
OPM_V = 12                             ; predicted native advance per 90 ms
OPM_REM = 14                           ; remainder of V*4/18
OPM_LEFT = 16                          ; gap still to spread
OPM_CORR = 20                          ; gap spread per world step
OPM_FLAGS = 24                         ; bit 0 valid, 1 lap wrap pending, 2 moved this step
OPM_GRID = 28                          ; native update count of this record's last grid view
OPM_SIZE = 32

timing_opponent_motion_reset
 movem.l d0/a1,-(sp)
 move.l perf_arena(pc),d0
 beq.s .done
 movea.l d0,a1
 adda.l #TIMING_OPPONENT_ARENA,a1
 move.w #TIMING_OPPONENT_SLOTS*OPM_SIZE/4-1,d0
.clear
 clr.l (a1)+
 dbf d0,.clear
.done
 movem.l (sp)+,d0/a1
 rts

; D7 = opponents-1, A5 = first record, A1 = first slot. Z set when there is nothing to do.
timing_opponent_motion_first
 move.l perf_arena(pc),d7
 beq.s .none
 movea.l d7,a1
 adda.l #TIMING_OPPONENT_ARENA,a1
 move.w $340(a6),d7
 bmi.s .none
 cmp.w #TIMING_OPPONENT_SLOTS,d7
 bhs.s .none
 movea.l $342(a6),a5
 move #0,ccr
 rts
.none
 move #4,ccr
 rts

; Before a native update: give it the authoritative progress.
timing_opponent_motion_restore
 movem.l d0/d7/a1/a5,-(sp)
 bsr timing_opponent_motion_first
 beq.s .done
.loop
 btst #0,OPM_FLAGS+1(a1)
 beq.s .next
 move.l $66(a5),d0
 cmp.l OPM_WRITTEN(a1),d0
 bne.s .next
 move.l OPM_A(a1),$66(a5)
.next
 adda.w #$be,a5
 lea OPM_SIZE(a1),a1
 dbf d7,.loop
.done
 movem.l (sp)+,d0/d7/a1/a5
 rts

; After a native update: record its result and plan the next 90 ms.
timing_opponent_motion_capture
 movem.l d0-d3/d7/a0-a1/a5,-(sp)
 bsr timing_opponent_motion_first
 beq.w .done
 moveq #0,d3
 move.w $368(a6),d3
 lsl.l #4,d3                           ; lap length in progress units
 lea timing_opponent_motion_state(pc),a0
.loop
 move.l $66(a5),d0
 btst #0,OPM_FLAGS+1(a1)
 bne.s .tracked
 move.w #1,OPM_FLAGS(a1)
 move.l d0,OPM_P(a1)
 clr.w OPM_REM(a1)
 moveq #0,d1
 bra.s .planned
.tracked
 btst #1,OPM_FLAGS+1(a1)
 bne.s .old_lap
 cmp.l OPM_A(a1),d0
 bge.s .forward
 ; Progress fell: a lap wrap (second half to first half) or a reposition.
 move.l d3,d1
 lsr.l #1,d1
 cmp.l d1,d0
 bge.s .snap
 cmp.l OPM_A(a1),d1
 bgt.s .snap
 bset #1,OPM_FLAGS+1(a1)
 addq.l #1,8(a0)
.old_lap
 move.l d0,d1
 add.l d3,d1
 sub.l OPM_P(a1),d1
 bra.s .gap
.forward
 move.l d0,d1
 sub.l OPM_P(a1),d1
.gap
 move.l d1,d2
 bpl.s .abs
 neg.l d2
.abs
 cmp.l #TIMING_OPPONENT_SNAP,d2
 ble.s .planned
.snap
 addq.l #1,12(a0)
 move.l d0,OPM_P(a1)
 bclr #1,OPM_FLAGS+1(a1)
 moveq #0,d1
.planned
 move.l d1,OPM_LEFT(a1)
 move.l d1,d2
 asl.l #2,d2
 divs.w #TIMING_PERIOD,d2
 ext.l d2
 bne.s .corr
 tst.l d1
 beq.s .corr
 moveq #1,d2
 tst.l d1
 bpl.s .corr
 moveq #-1,d2
.corr
 move.l d2,OPM_CORR(a1)
 move.l d0,OPM_A(a1)
 move.l d0,OPM_WRITTEN(a1)
 bsr timing_opponent_motion_predict
 adda.w #$be,a5
 lea OPM_SIZE(a1),a1
 dbf d7,.loop
.done
 movem.l (sp)+,d0-d3/d7/a0-a1/a5
 rts

; The native $d558..$d5c0 advance for the next update, without its random +-40
; (spread later as part of the gap). A5 = record, A1 = slot.
timing_opponent_motion_predict
 movem.l d0-d1,-(sp)
 move.w $16(a5),d0
 tst.w $48(a5)
 bpl.s .fuel
 asr.w #1,d0
.fuel
 muls.w #TIMING_PERIOD,d0
 divs.w #26,d0
 tst.l $4b8(a6)
 bmi.s .mode
 asr.w #1,d0
.mode
 move.w $64(a5),d1
 ble.s .floor
 subq.w #1,d1                          ; the next update decrements before testing
 cmp.w #8,d1
 bgt.s .stopped
 tst.w d1
 ble.s .floor
 neg.w d1
 addq.w #8,d1
 muls.w d1,d0
 asr.l #3,d0
 bra.s .hold
.floor
 cmp.w #40,d0
 bge.s .hold
 moveq #40,d0
.hold
 tst.w $1e(a5)
 bpl.s .clamp
 sub.w $16(a5),d0
.clamp
 tst.w d0
 bpl.s .store
.stopped
 moveq #0,d0
.store
 move.w d0,OPM_V(a1)
 movem.l (sp)+,d0-d1
 rts

; Gate shared by the world-step routines: human race flight, outside pit/modal work.
; Z set when opponent movement must stay native.
timing_opponent_motion_active
 move.l d0,-(sp)
 bsr timing_opponent_effects_enabled
 beq.s .no                             ; its result is in the flags; D0 is the caller's
 move.w timing_world_state+8(pc),d0
 beq.s .done
 move.w timing_pit_state+8(pc),d0
 bne.s .no
 tst.w $2e8(a6)
 bne.s .no
 moveq #1,d0
 bra.s .done
.no
 moveq #0,d0
.done
 tst.w d0
 movem.l (sp)+,d0
 rts

; One 20-ms world step, before the opponent effect tick.
timing_opponent_motion_step
 movem.l d0-d7/a0-a1/a4-a5,-(sp)
 lea timing_opponent_motion_state(pc),a0
 move.l timing_opponent_effects_state+12(pc),16(a0)
 bsr timing_opponent_motion_active
 beq.w .done
 bsr timing_opponent_motion_first
 beq.w .done
 addq.l #1,20(a0)
 moveq #0,d3
 move.w $368(a6),d3
 lsl.l #4,d3
 move.l perf_game(pc),a4
 movea.l $682(a4),a4                   ; path nodes
.loop
 bclr #2,OPM_FLAGS+1(a1)
 btst #0,OPM_FLAGS+1(a1)
 beq.w .next
 move.l $66(a5),d0
 cmp.l OPM_WRITTEN(a1),d0
 beq.s .ours
 ; Native code outside the scheduled update moved it: follow.
 addq.l #1,24(a0)
 move.l d0,OPM_A(a1)
 move.l d0,OPM_P(a1)
 move.l d0,OPM_WRITTEN(a1)
 clr.l OPM_LEFT(a1)
 bclr #1,OPM_FLAGS+1(a1)
 bra.w .next
.ours
 tst.w $56(a5)
 bne.s .native
 tst.w $8(a5)
 beq.s .advance
.native
 ; Pit or retired: the native update owns the record. Keep its progress.
 move.l OPM_A(a1),d0
 move.l d0,OPM_P(a1)
 move.l d0,OPM_WRITTEN(a1)
 move.l d0,$66(a5)
 clr.l OPM_LEFT(a1)
 bclr #1,OPM_FLAGS+1(a1)
 bra.w .next
.advance
 moveq #0,d0
 move.w OPM_V(a1),d0
 lsl.l #2,d0
 moveq #0,d1
 move.w OPM_REM(a1),d1
 add.l d1,d0
 divu.w #TIMING_PERIOD,d0
 swap d0
 move.w d0,OPM_REM(a1)
 clr.w d0
 swap d0                               ; whole units this step
 move.l OPM_LEFT(a1),d2
 move.l OPM_CORR(a1),d1
 tst.l d2
 bne.s .limit
 moveq #0,d1
 bra.s .apply
.limit
 bmi.s .behind
 cmp.l d2,d1
 ble.s .apply
 move.l d2,d1
 bra.s .apply
.behind
 cmp.l d2,d1
 bge.s .apply
 move.l d2,d1
.apply
 move.l d0,d4
 add.l d1,d4
 bpl.s .moved
 move.l d0,d1
 neg.l d1
 moveq #0,d4
.moved
 sub.l d1,d2
 move.l d2,OPM_LEFT(a1)
 move.l OPM_P(a1),d0
 add.l d4,d0
 cmp.l d3,d0
 blt.s .in_lap
 btst #1,OPM_FLAGS+1(a1)
 beq.s .line
 sub.l d3,d0                           ; the native update has already counted the lap
 bclr #1,OPM_FLAGS+1(a1)
 bra.s .in_lap
.line
 move.l d3,d0                          ; the lap line belongs to the native update
 subq.l #1,d0
.in_lap
 move.l d0,OPM_P(a1)
 move.l d0,OPM_WRITTEN(a1)
 move.l d0,$66(a5)
 bsr timing_opponent_motion_place
 bset #2,OPM_FLAGS+1(a1)
.next
 adda.w #$be,a5
 lea OPM_SIZE(a1),a1
 dbf d7,.loop
.done
 movem.l (sp)+,d0-d7/a0-a1/a4-a5
 rts

; Native $d5d2..$d64a and $d64c..$d69a for progress D0 (below the lap length), then the
; player distance of $d724..$d756. A4 = path nodes, A5 = record.
timing_opponent_motion_place
 movem.l d0-d6,-(sp)
 move.l d0,d6
 asr.l #7,d6
 move.l d6,d5
 asl.l #7,d5
 neg.l d5
 add.l d0,d5                           ; fraction 0..127
 asl.l #3,d6                           ; node offset
 move.w (a4,d6.w),$10(a5)
 move.w 2(a4,d6.w),$12(a5)
 move.w 4(a4,d6.w),$14(a5)
 move.b 6(a4,d6.w),d4
 ext.w d4
 move.w d4,$20(a5)
 moveq #0,d4
 move.b 7(a4,d6.w),d4
 move.w d4,$2(a5)
 move.w $368(a6),d4
 subq.w #8,d4
 cmp.w d4,d6
 blt.s .blend
 move.w #-8,d6
.blend
 move.b $e(a4,d6.w),d4
 ext.w d4
 sub.w $20(a5),d4
 muls.w d5,d4
 asr.l #7,d4
 add.w d4,$20(a5)
 move.w 8(a4,d6.w),d4
 sub.w $10(a5),d4
 muls.w d5,d4
 asr.l #7,d4
 add.w d4,$10(a5)
 move.w $a(a4,d6.w),d4
 sub.w $12(a5),d4
 muls.w d5,d4
 asr.l #7,d4
 add.w d4,$12(a5)
 move.w $c(a4,d6.w),d4
 sub.w $14(a5),d4
 muls.w d5,d4
 asr.l #7,d4
 add.w d4,$14(a5)
 move.w $10(a5),d5
 sub.w $12c(a6),d5
 bpl.s .x
 neg.w d5
.x
 ext.l d5
 move.w $12(a5),d6
 sub.w $12e(a6),d6
 bpl.s .y
 neg.w d6
.y
 ext.l d6
 add.l d6,d5
 move.w $14(a5),d6
 sub.w $130(a6),d6
 bpl.s .z
 neg.w d6
.z
 ext.l d6
 add.l d6,d5
 move.l d5,$4c(a5)
 movem.l (sp)+,d0-d6
 rts

; After the effect tick. Native frames add a visible opponent's bounce offset ($9982..$99f0)
; to the position its update just rebuilt. On steps where the tick ran it did so itself;
; otherwise add it to the positions rebuilt this step.
timing_opponent_motion_bounce
 movem.l d0/d4-d7/a0-a1/a5,-(sp)
 lea timing_opponent_motion_state(pc),a0
 move.l timing_opponent_effects_state+12(pc),d0
 cmp.l 16(a0),d0
 bne.s .done
 tst.w $2f0(a6)
 bne.s .done
 tst.w $b6(a6)
 bne.s .done
 bsr timing_opponent_motion_active     ; the moved bits are only current while active
 beq.s .done
 bsr timing_opponent_motion_first
 beq.s .done
 move.w $11e(a6),d6
 move.w $200(a6),d5
.loop
 btst #2,OPM_FLAGS+1(a1)
 beq.s .next
 tst.w $3c(a5)
 beq.s .next
 move.w $2(a5),d4
 cmp.w d6,d5
 bge.s .linear
 cmp.w d6,d4
 bge.s .visible
 cmp.w d5,d4
 bgt.s .next
 bra.s .visible
.linear
 cmp.w d6,d4
 blt.s .next
 cmp.w d5,d4
 bgt.s .next
.visible
 move.w $36(a5),d0
 add.w d0,$10(a5)
 move.w $38(a5),d0
 add.w d0,$12(a5)
 move.w $3a(a5),d0
 add.w d0,$14(a5)
.next
 adda.w #$be,a5
 lea OPM_SIZE(a1),a1
 dbf d7,.loop
.done
 movem.l (sp)+,d0/d4-d7/a0-a1/a5
 rts

; A view of one opponent on the starting grid ($43a >= 0), from the scene's JSR $9950.
; The grid branch of $9950 adds a random height and a visible opponent's bounce offset to
; the pose its update placed ($9966..$997c, $99dc..$99f0), once per drawn frame. On the
; A500 one frame is drawn per update; here several views fall between two placements, and
; each native call would add them again until the next placement. Run the native view once
; per native update and only project the pose it produced in the other views.
; Z set: not a grid view (the native call). N set: viewed natively here. Else project only.
timing_opponent_motion_grid
 movem.l d0/a1,-(sp)
 move.w timing_started(pc),d0
 beq.s .not
 tst.w $43a(a6)
 bmi.s .not
 tst.w $be(a6)
 bne.s .not
 tst.w $b6(a6)
 bne.s .not
 move.l perf_arena(pc),d0
 beq.s .not
 movea.l d0,a1
 adda.l #TIMING_OPPONENT_ARENA,a1
 move.l a5,d0
 sub.l $342(a6),d0
 bmi.s .not
 cmp.l #TIMING_OPPONENT_SLOTS*$be,d0
 bhs.s .not
 divu.w #$be,d0
 lsl.w #5,d0                           ; OPM_SIZE
 adda.w d0,a1
 move.l timing_opponent_motion_native(pc),d0
 cmp.l OPM_GRID(a1),d0
 beq.s .project
 move.l d0,OPM_GRID(a1)
 bsr timing_opponent_effects_native    ; returns with D0-A4 restored
 move #8,ccr
 bra.s .done
.project
 move #0,ccr
 bra.s .done
.not
 move #4,ccr
.done
 movem.l (sp)+,d0/a1
 rts

timing_opponent_motion_native dc.l 0    ; native opponent update calls
timing_opponent_motion_state dc.b 'PDOPMOT1'
 dc.l 0 ; +8 lap wraps carried across the line
 dc.l 0 ; +12 gaps applied at once
 dc.l 0 ; +16 effect-tick count before this step
 dc.l 0 ; +20 world steps with opponent movement
 dc.l 0 ; +24 records moved by native code outside the update
