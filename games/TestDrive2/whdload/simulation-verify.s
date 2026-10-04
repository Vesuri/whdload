; VERIFY + v1 CUSTOM5: independent time/rate invariants on private dummy data.
; Runs before entering the game, with no debugger writes or game-state mutation.
verify_simulation_units:
    movem.l d0-a6,-(sp)
    lea verify_unit_results(pc),a0
    clr.l (a0)+
    clr.l (a0)
    move.l #32768,d0
    move.l #$10001,d1        ; MEMF_PUBLIC | MEMF_CLEAR
    move.l $4.w,a6
    jsr -198(a6)            ; AllocMem
    tst.l d0
    bne.b .allocated
    lea verify_unit_results(pc),a0
    move.l #1,(a0)
    bra .done
.allocated
    move.l d0,a4
    adda.l #32766,a4
    lea -64(a4),a5
    lea sim_phase(pc),a3

    ; Signed rounding: both extrema and odd negative steering preserve totals.
    clr.w (a3)
    move.w #32767,d0
    bsr sim_half_word
    ext.l d0
    move.l #16384,d1
    bsr verify_equal
    move.w #1,(a3)
    move.w #32767,d0
    bsr sim_half_word
    ext.l d0
    move.l #16383,d1
    bsr verify_equal
    clr.w (a3)
    move.w #-63,d0
    bsr sim_half_word
    ext.l d0
    moveq #-31,d1
    bsr verify_equal
    move.w #1,(a3)
    move.w #-63,d0
    bsr sim_half_word
    ext.l d0
    moveq #-32,d1
    bsr verify_equal
    clr.w (a3)
    move.w #-32768,d0
    bsr sim_half_word
    ext.l d0
    move.l #-16384,d1
    bsr verify_equal

    ; Two half steps with a constant heat rate add exactly one original rate.
    move.w #100,-24718(a4)
    moveq #3,d1
    bsr sim_heat_add
    move.w #1,(a3)
    moveq #3,d1
    bsr sim_heat_add
    moveq #0,d0
    move.w -24718(a4),d0
    moveq #103,d1
    bsr verify_equal

    ; Clock: 500 three-field ticks are 30 PAL seconds, not 50 nominal seconds.
    lea sim_fractions(pc),a0
    clr.l (a0)+
    clr.l (a0)
    move.l #1,-10146(a4)
    moveq #100,d0
    move.w #499,d7
.clock
    bsr sim_player_time
    dbf d7,.clock
    move.l -10146(a4),d0
    move.l #301,d1
    bsr verify_equal
    move.l -7674(a4),d0
    move.l #30000,d1
    bsr verify_equal

    ; Police and crash scripts retain six-field counter units at the new rate.
    move.w #1,16(a5)
    move.w #1,-12980(a4)
    move.w #10,-7642(a4)
    move.l #500000,2(a5)
    move.l #10000,10(a5)
    moveq #1,d7
.timers
    move.w d7,d0
    eori.w #1,d0
    move.w d0,(a3)
    bsr sim_crash_timer
    bsr sim_police_timer
    bsr sim_police_time_motion
    move.l d0,2(a5)
    dbf d7,.timers
    moveq #0,d0
    move.w 16(a5),d0
    moveq #2,d1
    bsr verify_equal
    moveq #0,d0
    move.w -12980(a4),d0
    bsr verify_equal
    moveq #0,d0
    move.w -7642(a4),d0
    moveq #11,d1
    bsr verify_equal
    move.l 2(a5),d0
    move.l #510000,d1
    bsr verify_equal

    ; Shared clamp-entry hooks: update once per six fields and retain d1 -> d2.
    move.w #10,-7642(a4)
    clr.w (a3)
    moveq #21,d1
    bsr sim_police_limit
    moveq #0,d0
    move.w d2,d0
    bsr verify_equal
    move.w #1,(a3)
    bsr sim_police_limit
    moveq #0,d0
    move.w -7642(a4),d0
    moveq #9,d1
    bsr verify_equal
    clr.w (a3)
    bsr sim_police_limit_branch
    REPT 6                  ; helper's displaced short-branch return adjustment
    nop
    ENDR
    move.w #1,(a3)
    bsr sim_police_limit_branch
    REPT 6
    nop
    ENDR
    moveq #0,d0
    move.w -7642(a4),d0
    moveq #8,d1
    bsr verify_equal

    ; Traffic increments and continuous lane change retain their per-pair total.
    moveq #1,d7
    clr.l -13470(a4)
    move.l #100000,-13466(a4)
    move.l #30000,-7652(a4)
    move.w #200,6(a5)
.traffic
    move.w d7,d0
    eori.w #1,d0
    move.w d0,(a3)
    move.l #61440,d0
    bsr sim_traffic_forward
    bsr sim_traffic_oncoming
    bsr sim_police_return_lane
    dbf d7,.traffic
    move.l -13470(a4),d0
    move.l #61440,d1
    bsr verify_equal
    move.l -13466(a4),d0
    move.l #70000,d1
    bsr verify_equal
    moveq #0,d0
    move.w 6(a5),d0
    move.l #159,d1
    bsr verify_equal

    move.l a4,a1
    suba.l #32766,a1
    move.l #32768,d0
    move.l $4.w,a6
    jsr -210(a6)            ; FreeMem
.done
    movem.l (sp)+,d0-a6
    rts

verify_equal:
    move.l a0,-(sp)
    lea verify_unit_results(pc),a0
    addq.l #1,4(a0)
    cmp.l d1,d0
    beq.b .equal
    addq.l #1,(a0)
.equal
    movem.l (sp)+,a0
    rts

    dc.b "TD2RATECHECK",0
    even
verify_unit_results:
    dc.l 0                  ; failures
    dc.l 0                  ; cases
