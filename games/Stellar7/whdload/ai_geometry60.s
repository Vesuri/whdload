; Optional fused setup for native enemy distance and target heading.
; No cache: current target/actor coordinates are read on every invocation.
        IFNE AI_GEOMETRY_FUSED
s60_geometry_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$ee44,a0
        cmp.w #$2079,(a0)
        bne s60_bad
        cmp.l #$508843eb,(6,a0)
        bne s60_bad
        cmp.l #$00082f09,(10,a0)
        bne s60_bad
        cmp.l #$2f084eba,(14,a0)
        bne s60_bad
        cmp.l #$0baa2740,(18,a0)
        bne s60_bad
        cmp.l #$00502079,(22,a0)
        bne s60_bad
        cmp.l #$20280008,(30,a0)
        bne s60_bad
        cmp.l #$90ab0008,(34,a0)
        bne s60_bad
        cmp.l #$2c002028,(38,a0)
        bne s60_bad
        cmp.l #$000c90ab,(42,a0)
        bne s60_bad
        cmp.l #$000c2a00,(46,a0)
        bne s60_bad
        cmp.l #$200648c0,(50,a0)
        bne s60_bad
        cmp.l #$220548c1,(54,a0)
        bne s60_bad
        cmp.l #$2e812f00,(58,a0)
        bne s60_bad
        cmp.l #$4eba9ab6,(62,a0)
        bne s60_bad
        cmp.l #$4fef000c,(66,a0)
        bne s60_bad
        cmp.l #$3740005e,(70,a0)
        bne s60_bad
        move.l (2,a0),d0
        cmp.l (26,a0),d0
        bne s60_bad
        lea (s60_geometry_view+2,pc),a3
        move.l d0,(a3)
        IFD VERIFY
        IFD GEOMETRY_TWIN
        lea (s60_geometry_ref_view+2,pc),a3
        move.l d0,(a3)
        lea (s60_geometry_ref_view2+2,pc),a3
        move.l d0,(a3)
        move.l a1,d0
        add.l #$fa00,d0
        lea (s60_geometry_ref_distance+2,pc),a3
        move.l d0,(a3)
        ENDC
        ENDC
        move.l a1,d0
        add.l #$893a,d0
        lea (s60_geometry_heading+2,pc),a3
        move.l d0,(a3)
        IFD VERIFY
        IFD GEOMETRY_TWIN
        lea (s60_geometry_ref_heading+2,pc),a3
        move.l d0,(a3)
        ENDC
        ENDC
        move.l a1,d0
        add.l #$ee8e,d0
        lea (s60_geometry_continue+2,pc),a3
        move.l d0,(a3)
        lea (s60_geometry_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_geometry_patches:
        PL_START
        IFD VERIFY
        IFD GEOMETRY_TWIN
        PL_P $ee44,s60_geometry_twin
        ELSE
        PL_P $ee44,s60_geometry
        ENDC
        ELSE
        PL_P $ee44,s60_geometry
        ENDC
        PL_END
s60_geometry:
        bsr s60_geometry_compute
s60_geometry_continue:
        jmp $00000000.l ; installed native continuation; preserve CCR
s60_geometry_compute:
s60_geometry_view:
        move.l $00000000.l,a0 ; installed original absolute view-pointer operand
        move.l (8,a0),d6
        sub.l (8,a3),d6
        move.l (12,a0),d5
        sub.l (12,a3),d5
        move.l d2,-(sp)
        move.l d6,d0
        bpl .x_abs
        neg.l d0
.x_abs: move.l d5,d1
        bpl .z_abs
        neg.l d1
.z_abs: cmp.l d1,d0
        ble .ordered
        exg d0,d1
.ordered:
        move.l d0,d2
        add.l d0,d0
        add.l d2,d0
        asr.l #3,d0
        add.l d0,d1
        move.l d1,(80,a3)
        IFD VERIFY
        IFD GEOMETRY_BAD
        eor.l #1,(80,a3) ; negative control, never a release instruction
        ENDC
        ENDC
        move.l (sp)+,d2
        lea (8,a3),a1
        move.l d6,d0
        ext.l d0
        move.l d5,d1
        ext.l d1
        move.l d1,-(sp)
        move.l d0,-(sp)
s60_geometry_heading:
        jsr $00000000.l
        lea (8,sp),sp
        move.w d0,(94,a3)
        rts
        IFD VERIFY
        IFD GEOMETRY_TWIN
s60_geometry_results: dc.b 'AG61'
        dc.l 0,0 ; completed comparisons, mismatches
s60_geometry_cases: dc.w 0
s60_geometry_reference:
s60_geometry_ref_view:
        move.l $00000000.l,a0
        addq.l #8,a0
        lea (8,a3),a1
        move.l a1,-(sp)
        move.l a0,-(sp)
s60_geometry_ref_distance:
        jsr $00000000.l
        move.l d0,(80,a3)
s60_geometry_ref_view2:
        move.l $00000000.l,a0
        move.l (8,a0),d0
        sub.l (8,a3),d0
        move.l d0,d6
        move.l (12,a0),d0
        sub.l (12,a3),d0
        move.l d0,d5
        move.l d6,d0
        ext.l d0
        move.l d5,d1
        ext.l d1
        move.l d1,(sp)
        move.l d0,-(sp)
s60_geometry_ref_heading:
        jsr $00000000.l
        lea (12,sp),sp
        move.w d0,(94,a3)
        rts
s60_geometry_twin:
        bsr s60_geometry_compare
        bra s60_geometry_continue
s60_geometry_compare:
        move.w sr,-(sp)
        movem.l d0-d7/a0-a6,-(sp)
        bsr s60_geometry_reference
        move.w sr,-(sp)
        movem.l d0-d7/a0-a6,-(sp)
        move.l (80,a3),-(sp)
        move.w (94,a3),-(sp)
        movem.l (68,sp),d0-d7/a0-a6
        move.w (128,sp),ccr
        bsr s60_geometry_compute
        move.w sr,-(sp)
        movem.l d0-d7/a0-a6,-(sp)
        moveq #0,d2
        move.l sp,a0
        lea (68,sp),a1
        moveq #14,d0
.compare:
        move.l (a0)+,d1
        cmp.l (a1)+,d1
        beq .same
        moveq #1,d2
.same:  dbf d0,.compare
        move.w (60,sp),d0
        move.w (128,sp),d1
        eor.w d1,d0
        and.w #31,d0
        beq .flags_ok
        moveq #1,d2
.flags_ok:
        move.l (44,sp),a2
        move.l (64,sp),d0
        cmp.l (80,a2),d0
        bne .bad
        move.w (62,sp),d0
        cmp.w (94,a2),d0
        beq .record
.bad:   moveq #1,d2
.record:
        lea (s60_geometry_results,pc),a0
        addq.l #1,(4,a0)
        add.l d2,(8,a0)
        movem.l (sp),d0-d7/a0-a6
        move.w (60,sp),ccr
        lea (192,sp),sp
        rts
        IFD GEOMETRY_TEST
s60_geometry_values:
        dc.l 0,1,-1,32767,32768,-32768,$7fffffff,$80000000
s60_geometry_actor: ds.b 112
s60_geometry_view_actor: ds.b 112
s60_test_geometry:
        move.l (s60_ticks,pc),d0
        cmp.l #GEOMETRY_TEST,d0
        bne .done
        move.w (s60_geometry_cases,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.l (s60_geometry_view+2,pc),a2
        move.l (a2),-(sp)
        lea (s60_geometry_view_actor,pc),a0
        move.l a0,(a2)
        moveq #0,d5
.mode:  move.l (a2),a0
        clr.l (8,a0)
        clr.l (12,a0)
        tst.w d5
        beq .origin
        move.l #$7fffffff,(8,a0)
        move.l #$80000000,(12,a0)
.origin:
        moveq #0,d6
.x:     moveq #0,d7
.z:     lea (s60_geometry_actor,pc),a3
        lea (s60_geometry_values,pc),a0
        move.l (a0,d6.w),(8,a3)
        move.l (a0,d7.w),(12,a3)
        movem.l d5-d7/a2,-(sp)
        move.l #$a55a1234,d2
        move.l #$5aa54321,d3
        move.l #$98765432,d4
        move.w d5,d0
        lsl.w #4,d0
        move.w d0,ccr
        bsr s60_geometry_compare
        movem.l (sp)+,d5-d7/a2
        lea (s60_geometry_cases,pc),a0
        addq.w #1,(a0)
        addq.w #4,d7
        cmp.w #32,d7
        bne .z
        addq.w #4,d6
        cmp.w #32,d6
        bne .x
        addq.w #1,d5
        cmp.w #2,d5
        bne .mode
        move.l (sp)+,(a2)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
        ENDC
        ENDC
