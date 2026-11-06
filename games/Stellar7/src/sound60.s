; 68000 sound-timer channel pass (open-work step 6), SOUND_FAST: on for the
; 68000 target, which retains it together with BLIT_IRQ_IDLE (blit60.s). It is
; exact (SOUND_TWIN; docs/internals.md, "A500 interrupts and the sound timer").
;
; The Sonix driver's CIA-B timer A handler at hunk $1126 (through cia.resource)
; ends with BSR $134c, its only caller. $134c updates each of four 84-byte
; channel records at driver+522 through the instrument class vtable (12(a4)),
; then writes Paula through 16(a4) and DMACON once. For the sampled-instrument
; class at hunk $2084, those methods are $22d4 (steady tail $23fa, helpers $cec,
; $d20, $ccc) and $c4a. This replacement keeps the same loops, record fields,
; status transitions and Paula write order, inlines that class's steady tail and
; Paula method, and keeps each channel's $d20 decrement keyed by its exact
; inputs (divisor, tempo), so a repeated divu/mulu is not recomputed. The
; volume is 0 at level 0 and otherwise keyed by its three inputs (channel
; volume, note volume, level). Loop 2 skips the class lookup when no native
; method ran in loop 1. Note starts (status 1) and every other class still call
; the native methods.
; Native code writes nothing outside the channel records and Paula on these paths.

S60_SOUND_RECORD = 84
S60_SOUND_CACHE = 16 ; divisor.w, tempo.w, decrement.l; channel volume.w, volume.w, level.w, result.w
s60_sound_class: dc.l 0
s60_sound_table: dc.l 0
s60_sound_cache: ds.b 4*S60_SOUND_CACHE
        IFD VERIFY
        IFD SOUND_TWIN
        INCLUDE sound60_test.s
        ENDC
        ENDC

s60_sound_install:
        move.l (s60_code,pc),a1
        cmp.l #$61000206,($1144,a1) ; the only caller: BSR.W $134c
        bne s60_bad
        cmp.l #$43ee020a,($134c,a1) ; LEA 522(a6),a1
        bne s60_bad
        cmp.l #$7e004a29,($1350,a1) ; MOVEQ #0,d7 (displaced)
        bne s60_bad
        cmp.l #$45f900df,($13a4,a1) ; LEA $dff0a0,a2
        bne s60_bad
        cmp.l #$f0a04247,($13a8,a1)
        bne s60_bad
        cmp.l #$33c600df,($13d4,a1) ; MOVE.W d6,$dff096; RTS
        bne s60_bad
        cmp.l #$f0964e75,($13d8,a1)
        bne s60_bad
        move.l a1,a0
        adda.l #$2090,a0
        cmp.l #$60000242,(a0)+ ; class 12(a4): BRA $22d4
        bne s60_bad
        cmp.l #$6000ebb4,(a0) ; class 16(a4): BRA $c4a
        bne s60_bad
        move.l a1,a0
        adda.l #$22d4,a0
        cmp.l #$26690004,(a0)
        bne s60_bad
        cmp.l #$303c1080,($23fa-$22d4,a0)
        bne s60_bad
        cmp.l #$2029000c,($c4a,a1)
        bne s60_bad
        cmp.l #$c24dbfc8,($d76,a1) ; $cec's bend table
        bne s60_bad
        lea (s60_sound_class,pc),a0
        move.l a1,d0
        add.l #$2084,d0
        move.l d0,(a0)+
        sub.l #$2084-$d76,d0
        move.l d0,(a0)
        IFD VERIFY
        IFD SOUND_TWIN
        bsr s60_test_sound_install
        ENDC
        ENDC
        lea (s60_sound_patches,pc),a0
        jmp (resload_Patch,a2)
s60_sound_patches:
        PL_START
        IFD VERIFY
        IFD SOUND_TWIN
        PL_P $134c,s60_test_sound_channels
        ELSE
        PL_P $134c,s60_sound_channels
        ENDC
        ELSE
        PL_P $134c,s60_sound_channels
        ENDC
        PL_END

; Entry from the timer handler with A6 = driver. The caller saves and restores
; D0-A6, so only A6 and the stack need preserving, as for the native routine.
s60_sound_channels:
        move.l #$dff0a0,d5
; D5 = Paula AUD0LCH (DMACON at -10); the twin passes a shadow block instead.
s60_sound_core:
        lea (522,a6),a1
        lea (s60_sound_cache,pc),a5
        move.l (s60_sound_class,pc),a3
        moveq #0,d7
        moveq #0,d6 ; nonzero once any native method has run
.status:
        tst.b (a1)
        bne .active
        tst.b (1,a1)
        beq .next
.active:
        move.l (4,a1),d0
        beq .none
        move.l d0,a4
        move.l (a4),a4
        cmpa.l a3,a4
        bne .method
        move.b (a1),d4 ; status, unchanged by the steady path
        cmp.b #1,d4
        beq .method
        cmp.b #2,d4
        bne .steady
        clr.b (10,a1)
; $23fa: period, sample countdown, envelope and volume (A2 = A1+76 natively).
.steady:
        move.w #$1080,d0
        sub.w (2,a6),d0
        mulu.w (76,a1),d0
        asl.l #4,d0
        swap d0
        ; $cec: per-channel override, else optional bend table.
        move.w d7,d1
        add.w d1,d1
        add.w d1,d1
        move.w (72,a6,d1.w),d2
        beq .bend
        move.w d2,d0
        bra .period
.bend:  move.w (56,a6,d1.w),d1
        beq .period
        add.b #$80,d1
        lsr.w #2,d1
        add.w d1,d1
        move.l (s60_sound_table,pc),a0
        move.w (0,a0,d1.w),d1
        mulu.w d1,d0
        add.l d0,d0
        swap d0
.period:
        move.w d0,(24,a1)
        ; $d20: countdown -= ((59659/period)*tempo*2)>>16, floored at zero.
        move.l (28,a1),d2
        ble .countdown_done
        move.w (50,a6),d3
        cmp.w (a5),d0
        bne .divide
        tst.w d0 ; never cached: divide by zero stays native
        beq .divide
        cmp.w (2,a5),d3
        bne .divide
        move.l (4,a5),d1
        bra .subtract
.divide:
        move.l #59659,d1
        divu.w d0,d1
        mulu.w d3,d1
        add.l d1,d1
        clr.w d1
        swap d1
        move.w d0,(a5)
        move.w d3,(2,a5)
        move.l d1,(4,a5)
.subtract:
        sub.l d1,d2
        bge .countdown
        moveq #0,d2
.countdown:
        move.l d2,(28,a1)
.countdown_done:
        move.w (78,a1),d1
        tst.b (10,a1)
        beq .decay
        move.w #-256,d2
        cmp.w d1,d2
        beq .volume
        move.w (80,a1),d0
        mulu.w (50,a6),d0
        add.l d0,d0
        bcs .level
        swap d0
        add.w d0,d1
        bcs .level
        cmp.w d2,d1
        bcc .level
        move.w d1,d2
        bra .level
.decay: clr.w d2
        tst.w d1
        beq .level
        move.w (82,a1),d0
        mulu.w (50,a6),d0
        add.l d0,d0
        bcs .level
        swap d0
        sub.w d0,d1
        bcs .level
        move.w d1,d2
.level: move.w d2,(78,a1)
        bne .volume
        clr.l (28,a1)
        ; $ccc and the native volume scale; D2 = level (78,a1) on every path.
        ; Level 0 gives ((x*0)>>16+1)>>2 = 0 for any channel volume x.
.volume:
        moveq #0,d0
        tst.w d2
        beq .scaled
        move.w d7,d0
        btst d7,(88,a6)
        beq .channel
        addq.w #4,d0
.channel:
        add.w d0,d0
        move.w (90,a6,d0.w),d0
        move.w (8,a1),d1
        cmp.w (8,a5),d0
        bne .scale
        cmp.w (10,a5),d1
        bne .scale
        cmp.w (12,a5),d2
        bne .scale
        move.w (14,a5),d0
        bra .scaled
.scale: move.w d0,(8,a5)
        move.w d1,(10,a5)
        move.w d2,(12,a5)
        addq.w #1,d1
        mulu.w d1,d0
        swap d0
        addq.w #1,d0
        mulu.w d2,d0
        swap d0
        addq.w #1,d0
        lsr.w #2,d0
        move.w d0,(14,a5)
.scaled:
        IFD VERIFY
        IFD SOUND_TWIN_BAD
        addq.w #1,d0
        ENDC
        ENDC
        move.w d0,(26,a1)
        ; Status after the steady path: 2 also sets the allocated byte; a zero
        ; status byte is already clear.
        cmp.b #2,d4
        bne .steady_clear
        move.b d4,(1,a1)
.steady_clear:
        tst.b d4
        beq .next
        clr.b (a1)
        bra .next
.method:
        movem.l d5/d7/a1/a3/a5-a6,-(sp)
        jsr (12,a4)
        movem.l (sp)+,d5/d7/a1/a3/a5-a6
        moveq #1,d6
.after: moveq #1,d0
        cmp.b #1,(a1)
        beq .set
        moveq #2,d0
        cmp.b #2,(a1)
        bne .clear
.set:   move.b d0,(1,a1)
.clear: clr.b (a1)
.next:  lea (S60_SOUND_RECORD,a1),a1
        lea (S60_SOUND_CACHE,a5),a5
        addq.w #1,d7
        cmp.w #4,d7
        bne .status
        bra .paula
.none:  clr.b (1,a1)
        clr.b (a1)
        bra .next
; $13a0: Paula registers for each allocated channel, then DMACON.
.paula: lea (522,a6),a1
        move.l d5,a2
        clr.w d7
        move.w d6,d4
        move.w #$8000,d6
.write: tst.b (1,a1)
        beq .skip
        ; Without a native method in loop 1, every channel still allocated
        ; took the steady path: its class is the sampled one.
        tst.w d4
        beq .c4a
        move.l (4,a1),a4
        move.l (a4),a4
        cmpa.l a3,a4
        bne .write_method
.c4a:   move.l (12,a1),d0 ; $c4a
        beq .loop
        clr.l (12,a1)
        move.w (16,a1),(4,a2)
        move.l d0,(a2)
        bset d7,d6
        bra .pv
.loop:  move.l (18,a1),d1
        beq .pv ; period and volume are written every call
        clr.l (18,a1)
        move.w (22,a1),(4,a2)
        move.l d1,(a2)
.pv:    move.w (24,a1),(6,a2)
        move.w (26,a1),(8,a2)
        bra .skip
.write_method:
        movem.l d5/a3,-(sp)
        jsr (16,a4)
        movem.l (sp)+,d5/a3
.skip:  lea (16,a2),a2
        lea (S60_SOUND_RECORD,a1),a1
        addq.w #1,d7
        cmp.w #4,d7
        bne .write
        move.l d5,a2
        move.w d6,(-10,a2)
        rts
