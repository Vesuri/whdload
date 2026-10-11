        IFD VERIFY
        IFD FRICTION_TEST
s60_friction_results:
        dc.b 'TF60'
        dc.l 0,0 ; checked native fragments, mismatches
s60_friction_actor: ds.b 112
s60_friction_view: dc.l 0
s60_friction_fragment: ds.b 48
; Independent compile-time event schedule. Rendering/contact gaps suppress
; clock consumption; the inactive native call does not consume its clock.
s60_friction_expected:
s60_friction_tick SET 0
s60_friction_last SET -S60_SUBSTEPS
        REPT 9*S60_SUBSTEPS
s60_friction_contact SET 1
        IFGE s60_friction_tick-3*S60_SUBSTEPS
        IFLT s60_friction_tick-11*S60_SUBSTEPS/3
s60_friction_contact SET 0
        ENDC
        ENDC
        IFGE s60_friction_tick-6*S60_SUBSTEPS
        IFLT s60_friction_tick-19*S60_SUBSTEPS/3
s60_friction_contact SET 0
        ENDC
        ENDC
s60_friction_emit SET 0
        IFEQ s60_friction_tick-8*S60_SUBSTEPS
s60_friction_emit SET 1
        ELSE
        IFNE s60_friction_tick-S60_SUBSTEPS
        IFNE s60_friction_contact
        IFGE s60_friction_tick-s60_friction_last-S60_SUBSTEPS
s60_friction_emit SET 1
s60_friction_last SET s60_friction_tick
        ENDC
        ENDC
        ENDC
        ENDC
        IFNE s60_friction_emit
        dc.w s60_friction_tick
        ENDC
s60_friction_tick SET s60_friction_tick+1
        ENDR
        dc.w -1
s60_test_friction:
        move.l (s60_ticks,pc),d0
        cmp.l #FRICTION_TEST,d0
        bne .done
        move.l (s60_friction_results+4,pc),d0
        bne .done
        movem.l d0-d7/a0-a6,-(sp)
        move.l (s60_ticks,pc),-(sp)
        move.w (s60_running,pc),-(sp)
        move.w (s60_rendering,pc),-(sp)
        move.w ($46d8-S60_DATA,a4),-(sp)
        lea (s60_friction_state,pc),a0
        move.l (a0),-(sp)
        move.l (4,a0),-(sp)
        lea (s60_friction_actor,pc),a3
        lea (s60_friction_view,pc),a0
        move.l a3,(a0)
        move.l (s60_code,pc),a0
        adda.l #$100a8,a0
        cmp.w #$4eb9,(a0)
        bne s60_bad
        cmp.w #$6726,(6,a0)
        bne s60_bad
        lea (s60_friction_fragment,pc),a1
        moveq #22,d0
.copy:  move.w (a0)+,(a1)+
        dbf d0,.copy
        move.w #$4e75,(a1)
        lea (s60_friction_fragment,pc),a1
        lea (s60_friction_view,pc),a0
        move.l a0,(10,a1)
        move.l a0,(22,a1)
        move.l a0,(38,a1)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        moveq #0,d5
.case:
        bsr s60_friction_reset
        lea (s60_friction_expected,pc),a5
        move.l d5,d4
        cmp.w #S60_SUBSTEPS,d5
        bcs .base
        sub.l #S60_SUBSTEPS+8,d4 ; exercise unsigned tick rollover
.base:  moveq #0,d6
.step:
        lea (s60_ticks,pc),a0
        move.l d4,d0
        add.l d6,d0
        move.l d0,(a0)
        lea (s60_running,pc),a0
        move.w #1,(a0)
        lea (s60_rendering,pc),a0
        clr.w (a0)
        cmp.w #S60_SUBSTEPS,d6
        bne .render_ready
        move.w #1,(a0)
.render_ready:
        cmp.w #8*S60_SUBSTEPS,d6
        bne .active_ready
        move.w #1,(a0) ; inactive native path ignores rendering and clock
        lea (s60_running,pc),a0
        clr.w (a0)
.active_ready:
        move.w #1,($46d8-S60_DATA,a4)
        cmp.w #3*S60_SUBSTEPS,d6
        bcs .contact_ready
        cmp.w #11*S60_SUBSTEPS/3,d6
        bcs .no_contact
        cmp.w #6*S60_SUBSTEPS,d6
        bcs .contact_ready
        cmp.w #19*S60_SUBSTEPS/3,d6
        bcc .contact_ready
.no_contact:
        clr.w ($46d8-S60_DATA,a4)
.contact_ready:
        move.w #511,(56,a3)
        move.w #-511,(64,a3)
        move.w #511,d2
        move.w #-511,d3
        cmp.w (a5),d6
        bne .expected_ready
        addq.l #2,a5
        move.w #127,d2
        move.w #-128,d3
.expected_ready:
        bsr s60_friction_fragment
        lea (s60_friction_results,pc),a6
        cmp.w (56,a3),d2
        bne .bad
        cmp.w (64,a3),d3
        beq .passed
.bad:   addq.l #1,(8,a6)
.passed:
        addq.l #1,(4,a6)
        addq.w #1,d6
        cmp.w #9*S60_SUBSTEPS,d6
        bcs .step
        addq.w #1,d5
        cmp.w #2*S60_SUBSTEPS,d5
        bcs .case
        lea (s60_friction_state,pc),a0
        move.l (sp)+,(4,a0)
        move.l (sp)+,(a0)
        move.w (sp)+,($46d8-S60_DATA,a4)
        lea (s60_rendering,pc),a0
        move.w (sp)+,(a0)
        lea (s60_running,pc),a0
        move.w (sp)+,(a0)
        lea (s60_ticks,pc),a0
        move.l (sp)+,(a0)
        movem.l (sp)+,d0-d7/a0-a6
.done:  rts
        ENDC
        ENDC
