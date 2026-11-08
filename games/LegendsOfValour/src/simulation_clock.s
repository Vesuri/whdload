; The saved game clock remains VBL-driven, including deliberate rest/time jumps.
; Gameplay readers see that clock less outstanding active simulation fields.
; ADDA/SUBA preserve X, unlike arithmetic in data registers; original MOVE/BTST
; readers must not accidentally acquire a changed extend bit from this adapter.
_sim_clock_read
        movem.l d1/a0-a1,-(sp)
        move.l (_h11,pc),a0
        move.l (h11_004d6,a0),d0
        move.w (_sim_started,pc),d1
        beq .done
        move.w (_sim_suspended,pc),d1
        bne .done
        move.l (_h12,pc),a1
        adda.l #h12_0a0c3,a1
        tst.b (a1)
        beq .done
.retry  move.l (_sim_fields,pc),d1
        move.l (h11_004d6,a0),d0
        cmp.l (_sim_fields,pc),d1
        bne .retry
        move.l (_sim_consumed,pc),a1
        suba.l d1,a1
        adda.l d0,a1
        move.l a1,d0
.done   lea (_sim_tick_clock,pc),a0
        move.l d0,(a0)
        movem.l (sp)+,d1/a0-a1
        tst.l d0
        rts

_sim_clock_check
        move.l (_hunks+4,pc),a2
        cmp.l #$4a6c8006,(h1_0265a,a2)
        bne .bad
        cmp.w #$6710,(h1_0265e,a2)
        bne .bad
        cmp.l #$b0ac84d6,(h1_01112,a2)
        bne .bad
        cmp.w #$6e3a,(h1_01116,a2)
        bne .bad
        cmp.l #$d0ac84d6,(h1_01140,a2)
        bne .bad
        cmp.l #$29400000+((h11_06028-$8000)&$ffff),(h1_01144,a2)
        bne .bad
        move.l (_hunks+5*4,pc),a2
        cmp.l #$202c84d6,(h5_01a1a,a2)
        bne .bad
        cmp.l #$b0ac0000+((h11_00f10-$8000)&$ffff),(h5_01a1e,a2)
        bne .bad
        cmp.w #$6d4a,(h5_01a22,a2)
        bne .bad
        move.l (_hunks+2*4,pc),a2
        cmp.l #$082c0007,(h2_03a8c,a2)
        bne .bad
        cmp.w #$84d8,(h2_03a90,a2)
        bne .bad
        cmp.w #$660e,(h2_03a92,a2)
        bne .bad
        move.l (_h12,pc),a2
        adda.l #h12_173b2,a2
        cmp.w #$3e39,(a2)
        bne .bad
        move.l (_h11,pc),a0
        lea (h11_004d6,a0),a0
        cmp.l (2,a2),a0
        bne .bad
        cmp.w #$3e39,($12,a2)
        bne .bad
        addq.l #2,a0
        cmp.l ($14,a2),a0
        bne .bad
        cmp.w #$3039,($26,a2)
        bne .bad
        cmp.l ($28,a2),a0
        bne .bad
        rts
.bad    lea (_sim_bad,pc),a0
        bra _c2p_abort

_sim_clock_install
        move.l (_hunks+4,pc),a2
        lea (_sim_clock_days_go,pc),a0
        lea (h1_02660,a2),a1
        move.l a1,(a0)+
        lea (h1_02670,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h1:0265a 6 bit=6
        lea (h1_0265a,a2),a0
        lea (_sim_clock_days,pc),a1
        bsr .jump
        lea (_sim_clock_weapon_skip,pc),a0
        lea (h1_01152,a2),a1
        move.l a1,(a0)+
        lea (h1_01118,a2),a1
        move.l a1,(a0)+
        lea (h1_01148,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h1:01112 6 bit=6
        lea (h1_01112,a2),a0
        lea (_sim_clock_weapon_due,pc),a1
        bsr .jump
        ; PERF_RANGE h1:01140 8 bit=6
        lea (h1_01140,a2),a0
        lea (_sim_clock_weapon_next,pc),a1
        bsr .jump
        move.w #$4e71,(h1_01146,a2)
        move.l (_hunks+5*4,pc),a2
        lea (_sim_clock_shot_skip,pc),a0
        lea (h5_01a6e,a2),a1
        move.l a1,(a0)+
        lea (h5_01a24,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h5:01a1a 8 bit=6
        lea (h5_01a1a,a2),a0
        lea (_sim_clock_shot,pc),a1
        bsr .jump
        move.w #$4e71,(h5_01a20,a2)
        move.l (_hunks+2*4,pc),a2
        lea (_sim_clock_night_yes,pc),a0
        lea (h2_03aa2,a2),a1
        move.l a1,(a0)+
        lea (h2_03a94,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h2:03a8c 6 bit=6
        lea (h2_03a8c,a2),a0
        lea (_sim_clock_night,pc),a1
        bsr .jump
        move.l (_h12,pc),a2
        adda.l #h12_173b2,a2
        lea (_sim_clock_day_done,pc),a0
        lea (6,a2),a1
        move.l a1,(a0)+
        lea ($18,a2),a1
        move.l a1,(a0)+
        lea ($2c,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h12:173b2 6 bit=6
        move.l a2,a0
        lea (_sim_clock_day,pc),a1
        bsr .jump
        ; PERF_RANGE h12:173c4 6 bit=6
        lea ($12,a2),a0
        lea (_sim_clock_time,pc),a1
        bsr .jump
        ; PERF_RANGE h12:173d8 6 bit=6
        lea ($26,a2),a0
        lea (_sim_clock_periodic,pc),a1
        bsr .jump
        rts
.jump   move.w #$4ef9,(a0)+
        move.l a1,(a0)
        rts

; Leave the original VBL-produced pending-day count available to modal loops.
; The main loop can consume only pending days at or before its logical time.
; Repeat if a VBL changed the clock while reading its pending count. The
; difference of the upper words is modulo 65536, including full clock wrap.
; SUBA keeps X unchanged, as did the original TST/BEQ pair.
_sim_clock_days
        movem.l d0-d2/a0,-(sp)
        move.l (_h11,pc),a0
.retry  move.l (h11_004d6,a0),d2
        bsr _sim_clock_read
        move.l d0,d1
        move.w (6,a0),d0
        cmp.l (h11_004d6,a0),d2
        bne .retry
        swap d1
        swap d2
        move.l d2,a0
        suba.l d1,a0
        move.l a0,d2
        cmp.w d2,d0
        bhi .due
        movem.l (sp)+,d0-d2/a0
        move.l (_sim_clock_days_skip,pc),-(sp)
        rts
.due    movem.l (sp)+,d0-d2/a0
        move.l (_sim_clock_days_go,pc),-(sp)
        rts

_sim_clock_weapon_due
        move.l d0,-(sp)
        bsr _sim_clock_read
        move.l (sp)+,d0
        cmp.l (_sim_tick_clock,pc),d0
        bgt .skip
        move.l (_sim_clock_weapon_go,pc),-(sp)
        bra .flags
.skip   move.l (_sim_clock_weapon_skip,pc),-(sp)
.flags  cmp.l (_sim_tick_clock,pc),d0
        rts

_sim_clock_weapon_next
        move.l d0,-(sp)
        bsr _sim_clock_read
        move.l (sp)+,d0
        move.l (_sim_clock_weapon_next_done,pc),-(sp)
        add.l (_sim_tick_clock,pc),d0
        move.l d0,(h11_06028-$8000,a4)
        rts

_sim_clock_shot
        bsr _sim_clock_read
        cmp.l (h11_00f10-$8000,a4),d0
        blt .skip
        move.l (_sim_clock_shot_go,pc),-(sp)
        bra .flags
.skip   move.l (_sim_clock_shot_skip,pc),-(sp)
.flags  cmp.l (h11_00f10-$8000,a4),d0
        rts

_sim_clock_night
        move.l d0,-(sp)
        bsr _sim_clock_read
        btst #15,d0
        beq .no
        move.l (sp)+,d0
        move.l (_sim_clock_night_yes,pc),-(sp)
        rts
.no     move.l (sp)+,d0
        move.l (_sim_clock_night_no,pc),-(sp)
        rts

_sim_clock_day
        move.l d0,-(sp)
        bsr _sim_clock_read
        swap d0
        move.w d0,d7
        move.l (sp)+,d0
        move.l (_sim_clock_day_done,pc),-(sp)
        tst.w d7
        rts
_sim_clock_time
        move.l d0,-(sp)
        bsr _sim_clock_read
        move.w d0,d7
        move.l (sp)+,d0
        move.l (_sim_clock_time_done,pc),-(sp)
        tst.w d7
        rts
_sim_clock_periodic
        move.l d1,-(sp)
        move.l d0,-(sp)
        bsr _sim_clock_read
        move.w d0,d1
        move.l (sp)+,d0
        move.w d1,d0
        move.l (sp)+,d1
        move.l (_sim_clock_periodic_done,pc),-(sp)
        tst.w d0
        rts

        CNOP 0,4
_sim_tick_clock dc.l 0
_sim_clock_weapon_skip dc.l 0
_sim_clock_weapon_go dc.l 0
_sim_clock_weapon_next_done dc.l 0
_sim_clock_shot_skip dc.l 0
_sim_clock_shot_go dc.l 0
_sim_clock_night_yes dc.l 0
_sim_clock_night_no dc.l 0
_sim_clock_day_done dc.l 0
_sim_clock_time_done dc.l 0
_sim_clock_periodic_done dc.l 0
_sim_clock_days_go dc.l 0
_sim_clock_days_skip dc.l 0
