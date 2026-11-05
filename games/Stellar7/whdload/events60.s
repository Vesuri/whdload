; Discrete native timers keep their original time units. Geometry and collision
; are evaluated every tick, while countdowns advance once per N ticks.
s60_events_install:
        bsr s60_friction_install
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$eeb2,a0
        cmp.l #$2f0b4e91,(a0)
        bne s60_bad
        cmp.w #$584f,(4,a0)
        bne s60_bad
        cmp.l #$532b0055,($3232,a1)
        bne s60_bad
        cmp.l #$0cabffff,($3236,a1)
        bne s60_bad
        cmp.l #$fed40010,($323a,a1)
        bne s60_bad
        cmp.w #$5379,($36f8,a1)
        bne s60_bad
        cmp.l #$600000a6,($36fe,a1)
        bne s60_bad
        IFD VERIFY
        IFD TERRAIN_TEST
        lea (s60_terrain_native,pc),a0
        move.l ($36f8,a1),(a0)
        move.w ($36fc,a1),(4,a0)
        move.w #$4e75,(6,a0)
        ENDC
        ENDC
        cmp.l #$2f0b266f,($394c,a1)
        bne s60_bad
        cmp.w #8,($3950,a1)
        bne s60_bad
        move.l (s60_code,pc),a0
        adda.l #$ece4,a0
        cmp.w #$3039,(a0)
        bne s60_bad
        cmp.w #$660e,(6,a0)
        bne s60_bad
        cmp.l #$117c0005,($339c,a1)
        bne s60_bad
        cmp.w #$0061,($33a0,a1)
        bne s60_bad
        cmp.l #$117c0009,($345a,a1)
        bne s60_bad
        cmp.w #$0061,($345e,a1)
        bne s60_bad
        cmp.l #$137c0020,($3448,a1)
        bne s60_bad
        cmp.w #$0062,($344c,a1)
        bne s60_bad
        cmp.w #$2079,($2ce6,a1)
        bne s60_bad
        move.l (s60_code,pc),a0
        adda.l #$8000,a0
        cmp.l #$157c0001,($12b6,a0)
        bne s60_bad
        cmp.l #$0059157c,($12ba,a0)
        bne s60_bad
        cmp.l #$00020056,($12be,a0)
        bne s60_bad
        lea (s60_events_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_events_patches:
        PL_START
        PL_PS $eeb2,s60_ai
        PL_PSS $3232,s60_projectile_timer,6
        PL_PS $36f8,s60_terrain_damage
        PL_PSS $92b6,s60_oscillator_start,6
        PL_P $394c,s60_oscillator
        PL_P $ece4,s60_jump_dispatch
        PL_PS $339c,s60_cooldown5
        PL_PS $345a,s60_cooldown9
        PL_PS $3448,s60_weapon32
        PL_P $2ce6,s60_cooldown_dispatch
        PL_END
s60_event_due:
        move.w (s60_running,pc),d0
        beq .yes
        move.w (s60_logic,pc),d0
        rts
.yes:   moveq #1,d0
        rts
s60_ai:
        move.w (s60_running,pc),d0
        beq .native
        move.l a1,d0
        sub.l (s60_code,pc),d0
        cmp.l #$f328,d0
        beq s60_special_ai
        cmp.l #$f192,d0
        beq s60_flying_ai
        cmp.l #$10904,d0
        beq s60_boss_ai
        bsr s60_event_due
        beq .done
.native:
        move.l a3,-(sp)
        jsr (a1)
        addq.l #4,sp
.done:  rts
s60_projectile_timer:
        movem.l d0-d1/a0/a6,-(sp)
        move.w (s60_running,pc),d0
        beq .decrement
        bsr s60_motion_record
        tst.w (4,a6)
        bne .count
        move.w #S60_LEGACY_DIV,(4,a6)
.count: subq.w #1,(4,a6)
        bne .compare
.decrement:
        subq.b #1,($55,a3)
.compare:
        movem.l (sp)+,d0-d1/a0/a6
        cmp.l #-300,($10,a3)
        rts
s60_terrain_state:
        dc.w 0,0 ; valid, padding
        dc.l 0 ; last active simulation tick that caused terrain damage
s60_terrain_reset:
        lea (s60_terrain_state,pc),a0
        clr.l (a0)
        clr.l (4,a0)
        rts
s60_terrain_damage:
        movem.l d0/a0,-(sp)
        move.w (s60_running,pc),d0
        beq .damage ; preserve native inactive behavior without consuming a clock
        move.w (s60_rendering,pc),d0
        bne .done
        lea (s60_terrain_state,pc),a0
        tst.w (a0)
        beq .accept
        move.l (s60_ticks,pc),d0
        sub.l (4,a0),d0
        cmp.l #S60_LEGACY_DIV,d0
        bcs .done
.accept:
        move.w #1,(a0)
        move.l (s60_ticks,pc),(4,a0)
.damage:
        subq.w #1,($46c4-S60_DATA,a4)
.done:  movem.l (sp)+,d0/a0
        rts
s60_oscillator:
        move.l d0,-(sp)
        move.w (s60_running,pc),d0
        beq .native
        move.w (s60_rendering,pc),d0
        bne .skip
        moveq #2,d0
        bsr s60_animation_due
        beq .skip
.native:
        move.l (sp)+,d0
        bra s60_oscillator_native
.skip:  move.l (sp)+,d0
        rts
s60_oscillator_native:
        move.l a3,-(sp)
        move.l (8,sp),a3
        S60_TAIL $3952

; Jump state: active, last native velocity, velocity*N, position remainder,
; reserved. Integer integration of the parabola through the original 5 Hz
; samples. At tick k, y(k)=y(0)+(225*N*k-5*k*k)/(N*N) for a native 220 launch.
s60_jump_state:
s60_jump_active: dc.w 0
s60_jump_last: dc.w 0
s60_jump_velocity: dc.l 0
s60_jump_remainder: dc.w 0
        dc.w 0
s60_jump_state_end:
s60_events_reset:
        bsr s60_friction_reset
        bsr s60_terrain_reset
        lea (s60_jump_state,pc),a0
        clr.l (a0)+
        clr.l (a0)+
        clr.l (a0)+
        lea (s60_cooldown_state,pc),a0
        clr.l (a0)+
        clr.l (a0)+
        clr.l (a0)+
        rts
s60_jump_dispatch:
        move.l d1,-(sp)
        move.w (s60_running,pc),d1
        beq .native
        move.l (sp)+,d1
        S60_TAIL $ed30
.native:
        move.l (sp)+,d1
        move.l (s60_code,pc),-(sp)
        add.l #$ecea,(sp)
        move.w ($1ea0-S60_DATA,a4),d0 ; preserve MOVE's flags for native BNE
        rts
s60_jump_update:
        movem.l d2-d3/a2-a3,-(sp)
        lea (s60_jump_state,pc),a2
        move.l ($43c0-S60_DATA,a4),a3
        move.w ($1ea0-S60_DATA,a4),d0
        tst.w (a2)
        beq .start
        cmp.w (2,a2),d0
        beq .integrate
.start: tst.w d0
        bne .launch
        tst.l ($10,a3)
        bgt .launch
        bra .done
.launch:
        ext.l d0
        muls #S60_LEGACY_DIV,d0
        move.l d0,(4,a2)
        clr.w (8,a2)
        move.w #1,(a2)
.integrate:
        move.l (4,a2),d2
        add.l #5*(S60_SUBSTEPS-1),d2 ; native gravity*(N-1)/2
        move.w (8,a2),d0
        ext.l d0
        add.l d0,d2
        divs #S60_SUBSTEPS*S60_SUBSTEPS,d2
        move.w d2,d3
        ext.l d3
        add.l d3,($10,a3)
        swap d2
        move.w d2,(8,a2)
        sub.l #10,(4,a2)
        move.l (4,a2),d0
        divs #S60_LEGACY_DIV,d0
        move.w d0,(2,a2)
        move.w d0,($1ea0-S60_DATA,a4)
        tst.l ($10,a3)
        bgt .done
        clr.l ($10,a3)
        clr.w ($1ea0-S60_DATA,a4)
        clr.l (a2)
        clr.l (4,a2)
        clr.l (8,a2)
        move.w #2,-(sp)
        S60_CALL $e948 ; original landing notification/power refresh
        addq.l #2,sp
.done:  movem.l (sp)+,d2-d3/a2-a3
        rts

; Three player timers: remaining simulation ticks, last published native byte, pad.
; Reset at the actual native setter, including a refresh to the same value.
s60_cooldown_state: ds.b 12
s60_cooldown5:
        move.b #5,($61,a0)
        movem.l d0/a0,-(sp)
        moveq #5,d0
        lea (s60_cooldown_state,pc),a0
        bra s60_cooldown_set
s60_cooldown9:
        move.b #9,($61,a0)
        movem.l d0/a0,-(sp)
        moveq #9,d0
        lea (s60_cooldown_state,pc),a0
        bra s60_cooldown_set
s60_weapon32:
        move.b #32,($62,a1)
        movem.l d0/a0,-(sp)
        move.w d7,d0
        lsl.w #2,d0
        lea (s60_cooldown_state+4,pc),a0
        adda.w d0,a0
        moveq #32,d0
s60_cooldown_set:
        move.b d0,(2,a0)
        mulu #S60_LEGACY_DIV,d0
        move.w d0,(a0)
        movem.l (sp)+,d0/a0
        rts
s60_cooldown_dispatch:
        move.l d0,-(sp)
        move.w (s60_running,pc),d0
        beq .native
        move.w (s60_logic,pc),d0
        beq .no_frame
        move.l (sp)+,d0
        S60_TAIL $2d4e
.no_frame:
        move.l (sp)+,d0
        rts
.native:
        move.l (sp)+,d0
        move.l ($43c0-S60_DATA,a4),a0
        S60_TAIL $2cec
s60_cooldowns_update:
        movem.l d2-d3/a2-a3,-(sp)
        lea (s60_cooldown_state,pc),a2
        move.l ($43c0-S60_DATA,a4),a3
        adda.w #$61,a3
        moveq #2,d2
        moveq #0,d3
.loop:  moveq #0,d0
        move.b (a3),d0
        beq .inactive
        cmp.b (2,a2),d0
        beq .count
        mulu #S60_LEGACY_DIV,d0 ; initialization outside the normal setters
        move.w d0,(a2)
.count: tst.w (a2)
        beq .inactive
        subq.w #1,(a2)
        moveq #0,d0
        move.w (a2),d0
        bne .publish
        moveq #1,d3
.publish:
        add.l #S60_LEGACY_DIV-1,d0
        divu #S60_LEGACY_DIV,d0
        move.b d0,(a3)
        move.b d0,(2,a2)
        bra .next
.inactive:
        clr.l (a2)
.next:  addq.l #1,a3
        addq.l #4,a2
        dbf d2,.loop
        tst.w d3
        beq .done
        move.l ($43c0-S60_DATA,a4),a0
        tst.b ($61,a0)
        bne .done
        tst.b ($62,a0)
        beq .ready
        tst.b ($63,a0)
        bne .done
.ready: move.w #1,-(sp)
        S60_CALL $414e
        addq.l #2,sp
.done:  movem.l (sp)+,d2-d3/a2-a3
        rts

        include "terrain_friction60.s"
