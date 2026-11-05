; Opt-in simulation-only pass for lists whose geometry has no actor-state
; outputs and whose callbacks do not consume projection scratch or mutate the
; list. Render calls retain native projection. Unknown cases fall back before
; any callback runs. Derived shared geometry scratch is intentionally deferred.
        IFNE PROJECT_BATCH
s60_project_batch:
        movem.l d1-d7/a0-a6,-(sp)
        move.w (s60_running,pc),d0
        beq .fallback
        move.w (s60_rendering,pc),d0
        bne .fallback
        tst.l ($278a-S60_DATA,a4) ; native pre-list callback
        bne .fallback
        tst.l ($278e-S60_DATA,a4) ; native post-list callback
        bne .fallback
        move.w ($43b2-S60_DATA,a4),d7
        ble .fallback
        cmp.w #256,d7
        bhi .fallback
        move.l ($5d90-S60_DATA,a4),a0
        move.l (2,a0),a6 ; native view actor is skipped
        move.l (s60_code,pc),a5
        adda.l #$42b0,a5 ; audited mesh animation: no geometry/list writes
        lea ($3fb2-S60_DATA,a4),a2
        move.w d7,d2
        subq.w #1,d2
.guard: move.l (a2)+,a3
        cmpa.l a6,a3
        beq .guard_next
        btst #3,(a3)
        IFD VERIFY
        IFD BATCH_BAD_VISIBILITY
        nop ; deliberate negative control: fixture must reject missing guard
        nop
        ELSE
        bne .fallback ; native visibility/projected coordinates must update
        ENDC
        ELSE
        bne .fallback ; native visibility/projected coordinates must update
        ENDC
        move.l (26,a3),d0
        beq .guard_next
        cmp.l a5,d0
        bne .fallback
.guard_next:
        dbf d2,.guard
        lea ($3fb2-S60_DATA,a4),a2
        moveq #0,d6
.loop:  move.l (a2)+,a3
        cmpa.l a6,a3
        beq .next
        tst.l (26,a3)
        beq .next
        ; Native calls once, before/after its mesh draw depending on bit 1.
        ; The mesh wrapper has no simulation side effects, so preserve the
        ; actor order and the original argument values without that draw call.
        move.w d6,-(sp)
        move.l a3,-(sp)
        jsr (a5) ; installed per-actor animation clock remains authoritative
        addq.l #6,sp
.next:  addq.w #1,d6
        cmp.w d7,d6
        bcs .loop
        IFD VERIFY
        IFD BATCH_TEST
        lea (s60_batch_path,pc),a0
        move.w #1,(a0)
        ENDC
        ENDC
        movem.l (sp)+,d1-d7/a0-a6
        moveq #1,d0
        rts
.fallback:
        IFD VERIFY
        IFD BATCH_TEST
        lea (s60_batch_path,pc),a0
        clr.w (a0)
        ENDC
        ENDC
        movem.l (sp)+,d1-d7/a0-a6
        moveq #0,d0
        rts
        ENDC
