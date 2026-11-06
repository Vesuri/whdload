; Presentation isolation for the fixed-step loop. Native projection still runs
; during simulation because collisions/targeting use its visibility fields.
S60_TAIL MACRO
        move.l (s60_code,pc),-(sp)
        add.l #\1,(sp)
        rts
        ENDM
s60_explosion_native: ds.b 14
s60_animation_native: ds.b 14
s60_beam_native: ds.b 14
s60_respawn_native: ds.b 14
s60_star_remainders: ds.w 100
s60_saved_rng: ds.b 116

; Copy guarded, position-independent prologues to trampolines.
; a0 = source, a3 = destination; d0/d1 = expected first eight bytes.
s60_draw_trampoline:
        cmp.l (a0),d0
        bne s60_bad
        cmp.l (4,a0),d1
        bne s60_bad
        move.l (a0)+,(a3)+
        move.l (a0)+,(a3)+
        move.w #$4ef9,(a3)+
        move.l a0,(a3)
        rts
s60_draw_install:
        move.l (s60_code,pc),a1
        lea ($397e,a1),a0
        lea (s60_explosion_native,pc),a3
        move.l #$4e55fff4,d0
        move.l #$48e70730,d1
        bsr s60_draw_trampoline
        lea ($42b0,a1),a0
        lea (s60_animation_native,pc),a3
        move.l #$48e70730,d0
        move.l #$266f0018,d1
        bsr s60_draw_trampoline
        move.l a1,a0
        adda.l #$115e8,a0
        lea (s60_beam_native,pc),a3
        move.l #$4e55fff8,d0
        move.l #$48e70f00,d1
        bsr s60_draw_trampoline
        move.l a1,a0
        adda.l #$9bd4,a0
        lea (s60_respawn_native,pc),a3
        move.l #$48e70110,d0
        move.l #$3e2f000c,d1
        bsr s60_draw_trampoline
        move.l a1,a0
        adda.l #$132b2,a0
        cmp.l #$48e72110,(a0)
        bne s60_bad
        cmp.l #$266f0010,(4,a0)
        bne s60_bad
        cmp.l #$4eba6e52,($2bd6,a1)
        bne s60_bad
        cmp.w #$3eb9,($2bda,a1)
        bne s60_bad
        cmp.l #$610014a4,($2c08,a1)
        bne s60_bad
        move.l a1,a0
        adda.l #$9c18,a0
        cmp.w #$4ef9,(a0)
        bne s60_bad
        move.l (2,a0),d0
        sub.l a1,d0
        cmp.l #$19eb0,d0
        bne s60_bad
        cmp.l #$41faff7a,($4334,a1)
        bne s60_bad
        cmp.l #$2748001a,($4338,a1)
        bne s60_bad
        cmp.l #$41faff36,($3a46,a1)
        bne s60_bad
        cmp.l #$2548001a,($3a4a,a1)
        bne s60_bad
        IFNE POLYGON_BLIT_IRQ
        ; The replacement is valid only inside this exact native ownership
        ; sequence: WaitBlit, OwnBlitter, polygon, DisownBlitter.
        move.l a1,a0
        adda.l #$14c50,a0
        cmp.w #$4eb9,(a0)
        bne s60_bad
        move.l (2,a0),d0
        sub.l a1,d0
        cmp.l #$2510c,d0
        bne s60_bad
        cmp.w #$4eb9,(6,a0)
        bne s60_bad
        move.l (8,a0),d0
        sub.l a1,d0
        cmp.l #$25288,d0
        bne s60_bad
        cmp.w #$4eb9,(12,a0)
        bne s60_bad
        move.l (14,a0),d0
        sub.l a1,d0
        cmp.l #$17e88,d0
        bne s60_bad
        cmp.w #$4eb9,(18,a0)
        bne s60_bad
        move.l (20,a0),d0
        sub.l a1,d0
        cmp.l #$25298,d0
        bne s60_bad
        ENDC
        lea (s60_draw_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_draw_patches:
        PL_START
        IFNE POLYGON_BLIT_IRQ
        IFEQ BLIT_IRQ_IDLE ; superseded: BLIT is already masked during the polygon
        PL_PS $14c5c,s60_polygon
        ENDC
        ENDC
        PL_P $132b2,s60_mesh
        PL_NOP $132b8,2
        PL_P $397e,s60_explosion
        PL_NOP $3984,2
        PL_PSS $4334,s60_animation_start,2
        PL_PSS $3a46,s60_explosion_start,2
        PL_P $42b0,s60_animation
        PL_NOP $42b6,2
        PL_P $115e8,s60_beam
        PL_NOP $115ee,2
        PL_P $9bd4,s60_respawn
        PL_NOP $9bda,2
        PL_P $9c18,s60_sprite
        PL_PSS $2bd6,s60_stars_draw,4
        PL_NOP $2c08,4 ; damage shake is clocked by simulation
        PL_END

s60_render:
        ; Beam effects use the native RNG. Restore the gameplay stream after
        ; presentation so neither extra nor omitted pictures changes AI RNG.
        movem.l d2/a2-a3,-(sp)
        lea ($2434-S60_DATA,a4),a2
        lea (s60_saved_rng,pc),a3
        moveq #28,d2
.save:  move.l (a2)+,(a3)+
        dbf d2,.save
        IFNE PROJECT_BATCH
        ; Simulation may have left the camera scratch unchanged. Prepare it
        ; before any background drawing; the native actor pass still projects
        ; every object normally and suppresses animation advancement here.
        move.l ($5d90-S60_DATA,a4),-(sp)
        S60_CALL $12920
        addq.l #4,sp
        ENDC
        S60_CALL $2bb4
        lea ($2434-S60_DATA,a4),a2
        lea (s60_saved_rng,pc),a3
        moveq #28,d2
.load:  move.l (a3)+,(a2)+
        dbf d2,.load
        movem.l (sp)+,d2/a2-a3
        rts

; Return Z when a running simulation pass must omit drawing. Outside gameplay
; the original renderer remains available for menus and scripted sequences.
s60_can_draw:
        move.w (s60_running,pc),d0
        beq .yes
        move.w (s60_rendering,pc),d0
        rts
.yes:   moveq #1,d0
        rts
s60_mesh:
        move.l d0,-(sp)
        bsr s60_can_draw
        beq .skip
        move.l (sp)+,d0
        movem.l d2/d7/a3,-(sp)
        move.l (16,sp),a3
        S60_TAIL $132ba
.skip:  move.l (sp)+,d0
        rts
s60_sprite:
        move.l d0,-(sp)
        bsr s60_can_draw
        beq .skip
        move.l (sp)+,d0
        S60_TAIL $19eb0
.skip:  move.l (sp)+,d0
        rts
s60_beam:
        move.l d0,-(sp)
        bsr s60_can_draw
        beq .skip
        move.l (sp)+,d0
        bra s60_beam_native
.skip:  move.l (sp)+,d0
        rts
s60_animation:
        move.l d0,-(sp)
        move.w (s60_running,pc),d0
        beq .native
        move.w (s60_rendering,pc),d0
        bne .skip
        moveq #1,d0
        bsr s60_animation_due
        beq .skip
.native:
        move.l (sp)+,d0
        bra s60_animation_native
.skip:  move.l (sp)+,d0
        rts
s60_explosion:
        move.l d0,-(sp)
        move.w (s60_running,pc),d0
        beq .native
        move.w (s60_rendering,pc),d0
        bne .draw
        moveq #0,d0
        bsr s60_animation_due
        beq .skip
.native:
        move.l (sp)+,d0
        bra s60_explosion_native
.skip:  move.l (sp)+,d0
        rts
.draw:  move.l (sp)+,d0
        movem.l d2-d7/a2-a3,-(sp)
        move.l (36,sp),a3
        tst.b ($1e51-S60_DATA,a4)
        bne .done
        btst #2,(a3)
        beq .done
        moveq #0,d7
        move.b ($55,a3),d7
        beq .index
        subq.w #1,d7
.index: lsl.w #2,d7
        move.l ($1e6a-S60_DATA,a4),a0
        move.l (a0,d7.w),a2
        move.w ($22,a3),d6
        move.w ($24,a3),d5
        move.w (10,a2),d0
        asr.w #1,d0
        sub.w d0,d6
        sub.w d0,d5
        move.w #1,($291e-S60_DATA,a4)
        clr.w -(sp)
        move.w d5,-(sp)
        move.w d6,-(sp)
        move.l a2,-(sp)
        S60_CALL $9c18
        lea (10,sp),sp
        clr.w ($291e-S60_DATA,a4)
.done:  movem.l (sp)+,d2-d7/a2-a3
        rts

s60_respawn:
        move.l d0,-(sp)
        move.w (s60_running,pc),d0
        beq .native
        move.w (s60_rendering,pc),d0
        bne .skip
.native:
        move.l (sp)+,d0
        bra s60_respawn_native
.skip:  move.l (sp)+,d0
        rts
s60_stars_draw:
        ; Native zero-motion path retains sprite selection and jump parallax.
        clr.l -(sp)
        S60_CALL $9a2a
        addq.l #4,sp
        ; Replay the instruction displaced after the native star call.
        move.w ($43b2-S60_DATA,a4),(4,sp)
        rts

s60_stars_reset:
        lea (s60_star_remainders,pc),a0
        moveq #49,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        rts
s60_stars_update:
        movem.l d2-d7/a2-a3,-(sp)
        move.l ($0ee4-S60_DATA,a4),a3
        lea (s60_star_remainders,pc),a2
        move.l ($43c0-S60_DATA,a4),a0
        move.w ($40,a0),d6
        move.w ($38,a0),d7
        asr.w #4,d7
        IFNE STAR_IDLE
        move.w d6,d4
        or.w d7,d4 ; both effective velocity inputs must be zero
        ENDC
        moveq #0,d5
.loop:  cmp.w ($3b94-S60_DATA,a4),d5
        bge .done
        cmp.w #50,d5 ; native allocation holds at most 50 six-byte stars
        bge .done
        IFNE STAR_IDLE
        tst.w d4
        bne .integrate
        tst.l (a2) ; do not skip accumulated fractions, even unusual values
        beq .bounds
.integrate:
        ENDC
        move.w (a3),d2
        sub.w #5088,d2
        muls d6,d2
        asr.l #8,d2
        asr.l #3,d2
        move.w (2,a3),d3
        sub.w #2720,d3
        muls d6,d3
        asr.l #8,d3
        asr.l #3,d3
        move.w (2,a3),d0
        sub.w #160,d0
        muls d7,d0
        asr.l #8,d0
        asr.l #1,d0
        add.l d0,d2
        move.w (a2),d0
        ext.l d0
        add.l d0,d2
        S60_DIV12 d2
        add.w d2,(a3)
        swap d2
        move.w d2,(a2)
        move.w (2,a2),d0
        ext.l d0
        add.l d0,d3
        S60_DIV12 d3
        add.w d3,(2,a3)
        swap d3
        move.w d3,(2,a2)
.bounds:
        move.w (a3),d0
        asr.w #5,d0
        cmp.w #24,d0
        blt .respawn
        cmp.w #295,d0
        bgt .respawn
        move.w (2,a3),d0
        asr.w #5,d0
        cmp.w #90,d0
        blt .respawn
        cmp.w #146,d0
        ble .next
.respawn:
        move.w d5,-(sp)
        S60_CALL $9bd4
        addq.l #2,sp
        clr.l (a2)
.next:  addq.l #6,a3
        addq.l #4,a2
        addq.w #1,d5
        bra .loop
.done:
        movem.l (sp)+,d2-d7/a2-a3
        rts

; Batch blitter completion notifications only while the native polygon caller
; owns the blitter. VBL and audio interrupt enables are never changed.
        IFNE POLYGON_BLIT_IRQ
        IFEQ BLIT_IRQ_IDLE
s60_polygon:
        subq.l #2,sp
        movem.l d0-d1/a0-a1,-(sp)
        ; OwnBlitter may return before the previous owner's last blit ends.
        S60_CALL $2510c
        move.w $dff01c,d0
        and.w #$0040,d0
        move.w d0,(16,sp)
s60_polygon_mask:
        move.w #$0040,$dff09a
        movem.l (sp)+,d0-d1/a0-a1
        S60_CALL $17e88
        ; Keep the native asynchronous final blit and pending request. Restore
        ; only the saved enable bit before the caller invokes DisownBlitter.
        move.l d0,-(sp)
        move.w (4,sp),d0
        or.w #$8000,d0
s60_polygon_restore:
        move.w d0,$dff09a
        move.l (sp)+,d0
        addq.l #2,sp
        rts
        ENDC
        ENDC
