; Native landing loops keep their script, effects and cleanup. Each pass owns
; one tenth-second; extra pictures interpolate that pass without committing it.
landing_capture:
        movem.l d0-d1/a0-a1,-(sp)
        lea landing_stage(pc),a0
        move.w d0,(a0)
        tst.w d2
        bne.s .save
        bsr.w landing_rate
        lea landing_fields(pc),a0
        divu.w #10,d0
        move.w d0,(a0)
        lea landing_epoch(pc),a0
        move.l MODAL_FIELD(a4),(a0)
.save:
        lea landing_previous(pc),a0
        bsr.w landing_store
        tst.w landing_stage(pc)
        beq.s .done
        lea EXT_ACTORS(a4),a0
        lea landing_actor_previous(pc),a1
        moveq #29,d0
.actors:
        move.l (a0)+,(a1)+
        dbra d0,.actors
.done:
        movem.l (sp)+,d0-d1/a0-a1
        rts

landing_store:
        move.w d3,(a0)+
        move.w d4,(a0)+
        move.w d5,(a0)+
        move.w d6,(a0)+
        move.l LANDING_SCROLL(a4),(a0)+
        tst.w landing_stage(pc)
        beq.s .done
        move.l -78(a5),(a0)+
.done:  rts

landing_wait:
        movem.l d1-d7/a0-a6,-(sp)
        moveq #0,d7
        move.w d2,d7
        mulu.w landing_fields(pc),d7
        add.l landing_epoch(pc),d7
        lea landing_next(pc),a0
        bsr.w landing_store
        moveq #-1,d6
.loop:
        move.l MODAL_FIELD(a4),d0
        sub.l d7,d0
        cmp.w landing_fields(pc),d0
        bcc.s .done
        cmp.w d6,d0
        beq.s .input
        move.w d0,d6
        lea landing_elapsed(pc),a0
        move.w d0,(a0)
        ; Restore script registers for the sampler; D6/D7 above are wait locals.
        movem.l 8(sp),d3-d5
        bsr.w landing_draw
.input:
        bsr.w modal_input
        tst.w d0
        bne.s .return
        tst.w MODAL_ABORT(a4)
        beq.s .loop
        bra.s .return
.done:
        bsr.w modal_input
.return:
        movem.l (sp)+,d1-d7/a0-a6
        rts

; D0 old, D1 new -> sampled signed word. The fraction is bounded to one tick.
landing_lerp:
        sub.w d0,d1
        muls.w landing_elapsed(pc),d1
        divs.w landing_fields(pc),d1
        add.w d1,d0
        rts

landing_draw:
        movem.l d0-d7/a0-a6,-(sp)
        lea landing_previous(pc),a0
        lea landing_next(pc),a1
        lea landing_sample(pc),a2
        moveq #7,d7
.sample:
        move.w (a0)+,d0
        move.w (a1)+,d1
        bsr.w landing_lerp
        move.w d0,(a2)+
        dbra d7,.sample
        move.l LANDING_SCROLL(a4),-(sp)
        move.l landing_sample+8(pc),LANDING_SCROLL(a4)
        move.w landing_sample(pc),d3
        move.w landing_sample+2(pc),d4
        move.w landing_sample+4(pc),d5
        move.w landing_sample+6(pc),d6
        tst.w landing_stage(pc)
        bne.s .hangar
        bsr.w landing_draw0
        bra.s .restore
.hangar:
        move.l -78(a5),-(sp)
        move.l landing_sample+12(pc),-78(a5)
        lea EXT_ACTORS(a4),a0
        moveq #29,d0
.actors:
        move.l (a0)+,-(sp)
        dbra d0,.actors
        lea EXT_ACTORS(a4),a2
        lea landing_actor_previous(pc),a1
        moveq #4,d7
.actor_pose:
        move.w 4(a2),d0
        muls.w landing_elapsed(pc),d0
        divs.w landing_fields(pc),d0
        sub.w 4(a2),d0
        add.w d0,(a2)
        move.w 6(a2),d0
        muls.w landing_elapsed(pc),d0
        divs.w landing_fields(pc),d0
        sub.w 6(a2),d0
        add.w d0,2(a2)
        ; Replay the same script step from its pre-tick state. Byte 9 is a
        ; script cursor while active, not the image number used when inactive.
        ; The complete post-tick records are restored after this redraw.
        move.l 8(a1),8(a2)
        move.l 12(a1),12(a2)
        move.l 16(a1),16(a2)
        move.l 20(a1),20(a2)
        lea 24(a1),a1
        lea 24(a2),a2
        dbra d7,.actor_pose
        bsr.w landing_draw1
        lea EXT_ACTORS+120(a4),a0
        moveq #29,d0
.unactors:
        move.l (sp)+,-(a0)
        dbra d0,.unactors
        move.l (sp)+,-78(a5)
.restore:
        move.l (sp)+,LANDING_SCROLL(a4)
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Perspective division uses the fractional depth, not a rounded depth word.
landing_scale:
        movem.l d1-d3,-(sp)
        moveq #0,d1
        move.w landing_previous+6(pc),d1
        moveq #0,d3
        move.w landing_next+6(pc),d3
        tst.w landing_stage(pc)
        beq.s .depth
        cmpi.w #34,d2
        blo.s .depth
        move.w d1,d3
.depth:
        sub.w d1,d3
        muls.w landing_elapsed(pc),d3
        mulu.w landing_fields(pc),d1
        add.l d3,d1
        mulu.w landing_fields(pc),d0
        divu.w d1,d0
        andi.l #$ffff,d0
        movem.l (sp)+,d1-d3
        rts
landing_stage: dc.w 0
landing_fields: dc.w 5
landing_elapsed: dc.w 0
landing_epoch: dc.l 0
landing_previous: dcb.w 8,0
landing_next: dcb.w 8,0
landing_sample: dcb.w 8,0
landing_actor_previous: dcb.b 120,0
