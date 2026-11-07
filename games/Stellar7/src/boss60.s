; Boss decisions execute once per N active callback ticks. Only audited
; continuous increments are distributed: bank, level-2 ascent/descent,
; level-4 sideways X/Z, type-7 exit pitch. Clamps, temporary collision positions,
; spawn placement, discrete speed assignments and state transitions remain native.
; Type-7 states 1/4 distribute -5/+50 speed changes, with a forward-Euler
; movement correction because the native loop moves before its AI callback.
; Record 4 phase, 6/62 Y delta/remainder, 64/66 bank delta/remainder,
; 92/94 X/Z deltas, 96/98 X/Z remainders, 100/102 pitch delta/remainder.
s60_boss_install:
        move.l (s60_code,pc),a0
        adda.l #$10904,a0
        cmp.l #$2f0b266f,(a0)
        bne s60_bad
        cmp.l #$00087007,(4,a0)
        bne s60_bad
        rts
s60_boss_ai:
        movem.l d2-d7/a2-a3/a6,-(sp)
        bsr s60_motion_record
        tst.w (4,a6)
        bne .integrate
        move.w #S60_LEGACY_DIV,(4,a6)
        clr.w (6,a6)
        clr.l (92,a6)
        clr.w (100,a6)
        clr.w (104,a6)
        moveq #0,d7 ; bit 0 Y, bit 1 X/Z, bit 2 pitch, bit 3 acceleration
        cmp.w #7,(2,a3)
        bne .level
        cmp.b #1,($59,a3)
        bne .exit_state
        moveq #8,d7
        bra .sample
.exit_state:
        cmp.b #4,($59,a3)
        bne .sample
        moveq #(1<<2)|(1<<3),d7 ; pitch and acceleration flags, independent of N
        bra .sample
.level: cmp.w #4,($46a0-S60_DATA,a4)
        bne .height
        moveq #2,d7
        bra .sample
.height:
        cmp.w #2,($46a0-S60_DATA,a4)
        bne .sample
        cmp.b #1,($59,a3)
        beq .height_yes
        cmp.b #2,($59,a3)
        bne .sample
.height_yes:
        moveq #1,d7
.sample:
        move.l (8,a3),d2
        move.l (12,a3),d3
        move.l (16,a3),d4
        move.w (22,a3),d5
        move.w (20,a3),d6
        ; Native library stubs (e.g. $876, reached through sound starts) load
        ; arguments into D2-D4 without restoring them: keep the samples on the stack.
        movem.l d2-d7,-(sp)
        move.w ($40,a3),-(sp)
        move.l a3,-(sp)
        S60_CALL $10904
        addq.l #4,sp
        move.w (sp)+,d1
        movem.l (sp)+,d2-d7
        cmp.l (a6),a3 ; native removal invalidates the record
        bne .done
        btst #3,d7
        beq .bank
        move.w ($40,a3),d0
        sub.w d1,d0
        move.w d0,(104,a6)
        move.w d1,($40,a3)
.bank:  move.w (22,a3),d0
        sub.w d5,d0
        move.w d0,(64,a6)
        move.w d5,(22,a3)
        btst #0,d7
        beq .xz
        move.l (16,a3),d0
        sub.l d4,d0
        move.w d0,(6,a6)
        move.l d4,(16,a3)
.xz:    btst #1,d7
        beq .pitch
        move.l (8,a3),d0
        sub.l d2,d0
        move.w d0,(92,a6)
        move.l d2,(8,a3)
        move.l (12,a3),d0
        sub.l d3,d0
        move.w d0,(94,a6)
        move.l d3,(12,a3)
.pitch: btst #2,d7
        beq .integrate
        move.w (20,a3),d0
        sub.w d6,d0
        move.w d0,(100,a6)
        move.w d6,(20,a3)
.integrate:
        move.w (6,a6),d0
        move.w (62,a6),d1
        bsr s60_boss_fraction
        move.w d1,(62,a6)
        add.l d0,(16,a3)
        move.w (92,a6),d0
        move.w (96,a6),d1
        bsr s60_boss_fraction
        move.w d1,(96,a6)
        add.l d0,(8,a3)
        move.w (94,a6),d0
        move.w (98,a6),d1
        bsr s60_boss_fraction
        move.w d1,(98,a6)
        add.l d0,(12,a3)
        move.w (64,a6),d0
        move.w (66,a6),d1
        bsr s60_boss_fraction
        move.w d1,(66,a6)
        add.w d0,(22,a3)
        move.w (100,a6),d0
        move.w (102,a6),d1
        bsr s60_boss_fraction
        move.w d1,(102,a6)
        add.w d0,(20,a3)
        move.w (104,a6),d0
        move.w (108,a6),d1
        bsr s60_boss_fraction
        move.w d1,(108,a6)
        add.w d0,($40,a3)
        subq.w #1,(4,a6)
.done:  movem.l (sp)+,d2-d7/a2-a3/a6
        rts
; d0 signed increment, d1 signed remainder -> long quotient, word remainder.
s60_boss_fraction:
        ext.l d0
        ext.l d1
        add.l d1,d0
        divs #S60_LEGACY_DIV,d0
        move.l d0,d1
        swap d1
        ext.l d0
        rts

; Native movement precedes AI. For each axis, project interval speeds V and
; V+A through the untouched native movement routine at the same current angles.
; Integrate [2*N*D(V) + (2*k-N-1)*(D(V+A)-D(V))]/(2*N*N) at k=1..N.
; For a fixed direction, the correction sums to zero and all N substeps
; total exactly D(V), including native trigonometric rounding and signed wraps.
; Record 104 acceleration, 106 interval V, 108 published-speed remainder,
; 110 substep coefficient, 112 saved speed, 114 reserved;
; 116/118/120 axis remainders, 122/124/126 their pre-movement copies.
s60_boss_speed_enter:
        cmp.w #7,(2,a3)
        bne .done
        move.l (116,a6),(122,a6)
        move.w (120,a6),(126,a6)
        move.w ($40,a3),(112,a6)
        tst.w (4,a6)
        bne .phase
        move.w ($40,a3),(106,a6)
        clr.w (104,a6)
        cmp.b #1,($59,a3)
        bne .exit_state
        move.w #-5,(104,a6)
        bra .phase
.exit_state:
        cmp.b #4,($59,a3)
        bne .phase
        move.w #50,(104,a6)
.phase: clr.w (110,a6)
        tst.w (104,a6)
        beq .done
        moveq #1-S60_SUBSTEPS,d0
        tst.w (4,a6)
        beq .adjust
        moveq #S60_SUBSTEPS+1,d0
        sub.w (4,a6),d0
        sub.w (4,a6),d0
.adjust:
        move.w d0,(110,a6)
        move.w (106,a6),($40,a3)
.done:  rts
; First native call has already advanced rotation once at speed V.
; A second call projects V+A without rotating again or committing its position.
s60_boss_move_finish:
        lea (-12,sp),sp
        move.l sp,a2
        move.l (8,a3),d0
        sub.l (32,a6),d0
        move.l d0,(a2)
        move.l (12,a3),d0
        sub.l (36,a6),d0
        move.l d0,(4,a2)
        move.l (16,a3),d0
        sub.l (40,a6),d0
        move.l d0,(8,a2)
        tst.w (104,a6)
        beq .projected
        move.l (32,a6),(8,a3)
        move.l (36,a6),(12,a3)
        move.l (40,a6),(16,a3)
        clr.l (52,a3)
        clr.w (56,a3)
        move.w (106,a6),d0
        add.w (104,a6),d0
        move.w d0,($40,a3)
        move.l a3,-(sp)
        bsr s60_move_native
        addq.l #4,sp
.projected:
        move.w (112,a6),($40,a3)
        move.l (44,a6),(52,a3)
        move.w (48,a6),(56,a3)
        lea (8,a3),a0
        lea (116,a6),a1
        lea (32,a6),a5
        lea (20,a6),a3
        moveq #2,d2
.axis:
        move.l (a0),d3
        sub.l (a5),d3
        sub.l (a2),d3 ; D(V+A)-D(V), potentially wider than signed word
        move.w (110,a6),d4
        bpl .positive
        neg.w d4
        neg.l d3
.positive:
        moveq #0,d0
        subq.w #1,d4
        bmi .base
.multiply:
        add.l d3,d0
        dbf d4,.multiply
.base:  move.l (a2)+,d3
        IFEQ S60_SUBSTEPS-12
        move.l d3,d4
        lsl.l #4,d3
        lsl.l #3,d4
        add.l d3,d0
        add.l d4,d0 ; 2*N*D(V) plus substep correction
        ELSE
        moveq #2*S60_SUBSTEPS-1,d4
.scale: add.l d3,d0
        dbf d4,.scale
        ENDC
        move.w (a1),d1
        ext.l d1
        add.l d1,d0
        IFEQ S60_SUBSTEPS-1
        asr.l #1,d0 ; zero correction/remainder; preserve a full long D(V)
        move.l d0,d1
        swap d0
        clr.w d0
        swap d0
        ELSE
        divs #2*S60_SUBSTEPS*S60_SUBSTEPS,d0
        move.w d0,d1
        ext.l d1
        ENDC
        move.l d1,(a3)+
        add.l (a5)+,d1
        move.l d1,(a0)+
        swap d0
        move.w d0,(a1)+
        dbf d2,.axis
        lea (12,sp),sp
        rts
