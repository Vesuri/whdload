; Fixed-step timing prototype, explicitly enabled by CUSTOM1.
; Keep every native simulation pass, including star updates and projection used
; by collision/targeting. Omit mesh rasterization/presentation when catching up.
; Extra interpolated pictures are deliberately a separate future change.
timing_install:
        move.l d7,a1
        add.l a1,a1
        add.l a1,a1
        addq.l #4,a1
        lea (timing_code,pc),a0
        move.l a1,(a0)
        ; Guard unrelocated opcodes/displacements; relocated operands are not
        ; compared to file addresses. The loader already checked the file CRC.
        cmp.w #$4a39,($2af6,a1)
        bne timing_bad
        ; Only the opcode is invariant after LoadSeg.
        cmp.w #$2039,($2b96,a1)
        bne timing_bad
        cmp.l #$b0adffea,($2b9c,a1)
        bne timing_bad
        cmp.l #$67f4426d,($2ba0,a1)
        bne timing_bad
        cmp.l #$ff200c6d,($2ba4,a1)
        bne timing_bad
        cmp.l #$02eeff20,($2ba8,a1)
        bne timing_bad
        cmp.l #$6c06526d,($2bac,a1)
        bne timing_bad
        cmp.l #$ff2060f2,($2bb0,a1)
        bne timing_bad
        cmp.l #$4eba3df2,($2c16,a1)
        bne timing_bad
        cmp.w #$2b79,($2c1a,a1)
        bne timing_bad
        cmp.w #$ffea,($2c20,a1)
        bne timing_bad
        cmp.w #$4279,($313e,a1)
        bne timing_bad
        move.l a1,a0
        adda.l #$10000,a0
        cmp.l #$48e72110,($32b2,a0)
        bne timing_bad
        cmp.l #$266f0010,($32b6,a0)
        bne timing_bad
        lea (timing_hz,pc),a0
        move.l (_custom2,pc),d0
        bne .rate
        moveq #5,d0
.rate:  cmp.l #25,d0
        bhi timing_bad
        move.w d0,(a0)
        lea (timing_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
timing_bad:
        pea (TDREASON_WRONGVER).w
        jmp (resload_Abort,a2)
timing_patches:
        PL_START
        PL_PS $2af6,timing_entry
        PL_PSS $2b96,timing_draw,24
        PL_PSS $2c16,timing_swap,6
        PL_PS $313e,timing_resume
        PL_P $132b2,timing_mesh
        PL_NOP $132b8,2
        PL_END

; Read-only debugger ABI: patched JSR target +4 = magic, +8 = state.
; State: last field, credit, steps, presents, skipped (longs),
; hz, field rate, last frame, draw flag, draw countdown (words).
timing_entry:
        bra.w timing_step
        dc.b 'S7TM'
timing_last: dc.l 0
timing_credit: dc.l 0
timing_steps: dc.l 0
timing_presents: dc.l 0
timing_skipped: dc.l 0
timing_hz: dc.w 5
timing_fields: dc.w 50
timing_frame: dc.w -1
timing_render: dc.w 1
timing_countdown: dc.w 0
timing_code: dc.l 0

timing_step:
        movem.l d0-d2/a0-a1,-(sp)
        lea (timing_last,pc),a0
        tst.b ($1e53-$8000,a4)
        beq .reset
        move.w ($1e96-$8000,a4),d1
        cmp.w (timing_frame-timing_last,a0),d1
        bls .reset
.wait:  move.l ($24a8-$8000,a4),d0
        sub.l (a0),d0
        beq .credit
        add.l d0,(a0)
        mulu (timing_hz-timing_last,a0),d0
        add.l d0,(timing_credit-timing_last,a0)
.credit:
        moveq #0,d0
        move.w (timing_fields-timing_last,a0),d0
        cmp.l (timing_credit-timing_last,a0),d0
        bhi .wait
        sub.l d0,(timing_credit-timing_last,a0)
        bra .ready
.reset:
        move.l ($24a8-$8000,a4),(a0)
        clr.l (timing_credit-timing_last,a0)
        move.l ($4).w,a1
        moveq #0,d0
        move.b (VBlankFrequency,a1),d0
        cmp.w #50,d0
        beq .freq
        cmp.w #60,d0
        bne .ready
.freq:  move.w d0,(timing_fields-timing_last,a0)
.ready:
        move.w ($1e96-$8000,a4),(timing_frame-timing_last,a0)
        addq.l #1,(timing_steps-timing_last,a0)
        movem.l (sp)+,d0-d2/a0-a1
        tst.b ($1e53-$8000,a4) ; original condition for the following BEQ
        rts

timing_draw:
        movem.l d0/a0,-(sp)
        lea (timing_last,pc),a0
        move.w #1,(timing_render-timing_last,a0)
        moveq #0,d0
        move.w (timing_fields-timing_last,a0),d0
        cmp.l (timing_credit-timing_last,a0),d0
        bls .skip
        IFD VERIFY
        move.l (_custom4,pc),d0
        cmp.l #1,d0
        bls .done
        subq.w #1,(timing_countdown-timing_last,a0)
        bpl .skip
        subq.w #1,d0
        move.w d0,(timing_countdown-timing_last,a0)
        ENDC
        bra .done
.skip:  clr.w (timing_render-timing_last,a0)
.done:
        IFD VERIFY
        IFD SLOW_DRAW
        tst.w (timing_render-timing_last,a0)
        beq .nodelay
        move.l ($24a8-$8000,a4),d0
        add.l #SLOW_DRAW,d0
.delay: cmp.l ($24a8-$8000,a4),d0
        bgt .delay
.nodelay:
        ENDC
        ENDC
        movem.l (sp)+,d0/a0
        rts

timing_mesh:
        move.l d0,-(sp)
        move.w (timing_render,pc),d0
        beq .skip
        move.l (sp)+,d0
        ; Replay both whole displaced instructions with the original SP.
        movem.l d2/d7/a3,-(sp)
        move.l (16,sp),a3
        move.l a0,-(sp)
        move.l (timing_code,pc),a0
        adda.l #$132ba,a0
        move.l a0,-(sp)
        move.l (4,sp),a0
        move.l (sp),(4,sp)
        addq.l #4,sp
        rts
.skip:  move.l (sp)+,d0
        rts

timing_swap:
        ; Preserve original word argument across the extra wrapper return PC.
        move.l a0,-(sp)
        move.w (timing_render,pc),d0
        beq .skip
        move.w (8,sp),-(sp)
        move.l (timing_code,pc),a0
        jsr ($6a0a,a0)
        addq.l #2,sp
        lea (timing_presents,pc),a0
        addq.l #1,(a0)
        bra .done
.skip:  lea (timing_skipped,pc),a0
        addq.l #1,(a0)
.done:  lea (timing_render,pc),a0
        move.w #1,(a0) ; menus and non-gameplay drawing always render
        move.l (sp)+,a0
        move.l ($24a8-$8000,a4),(-22,a5)
        rts

timing_resume:
        ; Native Permit path after pause, preferences and modal input. This
        ; excludes modal time explicitly, without mistaking slow firing for pause.
        move.l a0,-(sp)
        lea (timing_last,pc),a0
        move.l ($24a8-$8000,a4),(a0)
        clr.l (timing_credit-timing_last,a0)
        move.l (sp)+,a0
        clr.w ($0310-$8000,a4)
        rts
