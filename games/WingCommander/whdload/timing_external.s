; F5/F6/F7/F8/F9 select native modes 4/14/7/6/4 (8 for capitals).
; The dispatcher also advances chase controllers, missile expiry and view
; changes. Sample completed camera poses instead of executing it at draw rate.
timing_external_allowed:
        move.w  -18280(a4),d0
        cmpi.w  #4,d0
        beq.s   .yes
        cmpi.w  #6,d0
        beq.s   .yes
        cmpi.w  #7,d0
        beq.s   .yes
        cmpi.w  #8,d0
        beq.s   .yes
        cmpi.w  #14,d0
        beq.s   .yes
        moveq   #0,d0
        rts
.yes:
        moveq   #1,d0
        rts

; Identity includes each native selector; changing a subject within mode 4
; must cut history just as changing the view does.
timing_external_identity:
        lea     external_identity(pc),a0
        move.w  -18280(a4),(a0)+
        move.w  -18296(a4),(a0)+
        move.w  -18278(a4),(a0)+
        move.b  5468(a4),(a0)+
        move.b  -32109(a4),(a0)+
        rts

timing_external_snapshot:
        lea     external_valid(pc),a0
        clr.w   (a0)
        bsr.s   timing_external_allowed
        tst.w   d0
        beq.w   .reset
        tst.w   intro_active(pc)
        bne.w   .reset
        tst.w   -29978(a4)
        bne.w   .reset
        move.l  external_identity(pc),d4
        move.l  external_identity+4(pc),d5
        bsr.s   timing_external_identity
        moveq   #1,d6
        cmp.l   external_identity(pc),d4
        bne.s   .cut
        cmp.l   external_identity+4(pc),d5
        bne.s   .cut
        tst.w   timing_scene_valid(pc)
        beq.s   .cut
        tst.w   external_seen(pc)
        bne.s   .copy
.cut:
        moveq   #0,d6
.copy:
        lea     external_pose(pc),a1
        lea     external_delta(pc),a2
        lea     external_offsets(pc),a3
        moveq   #3,d4
.vector:
        move.w  (a3)+,d0
        lea     (a4,d0.w),a0
        moveq   #2,d3
.component:
        move.l  (a0)+,d0
        move.l  d0,d1
        sub.l   (a1),d1
        bvs.s   .unsafe
        move.l  d1,d2
        bpl.s   .positive
        neg.l   d2
.positive:
        ; Reject camera teleports and basis flips, never carry them forward.
        cmpi.w  #3,d4
        bne.s   .basis
        cmpi.l  #$100000,d2
        bhi.s   .unsafe
        bra.s   .store
.basis:
        cmpi.l  #256,d2
        bls.s   .store
.unsafe:
        moveq   #0,d6
.store:
        move.l  d0,(a1)+
        move.l  d1,(a2)+
        dbra    d3,.component
        dbra    d4,.vector
        lea     external_valid(pc),a0
        move.w  d6,(a0)
        lea     external_seen(pc),a0
        move.w  #1,(a0)
        rts
.reset:
        lea     external_seen(pc),a0
        clr.w   (a0)
        rts

; Called only inside the saved render pose, after all world objects are staged.
; Rebuild from the snapshot each time. The ordinary slot-61 backup restores it.
timing_external_camera:
        tst.w   intro_active(pc)
        bne.w   .done
        tst.w   external_valid(pc)
        beq.w   .done
        tst.w   timing_scene_valid(pc)
        beq.w   .done
        bsr.w   timing_external_allowed
        tst.w   d0
        beq.w   .done
        move.l  external_identity(pc),d4
        move.l  external_identity+4(pc),d5
        bsr.w   timing_external_identity
        cmp.l   external_identity(pc),d4
        bne.w   .invalidate
        cmp.l   external_identity+4(pc),d5
        bne.w   .invalidate
        ; A pose modified outside its sampled tick is a camera cut.
        lea     external_pose(pc),a1
        lea     external_offsets(pc),a3
        moveq   #3,d4
.check_vector:
        move.w  (a3)+,d0
        lea     (a4,d0.w),a0
        moveq   #2,d3
.check:
        move.l  (a0)+,d0
        cmp.l   (a1)+,d0
        bne.s   .invalidate
        dbra    d3,.check
        dbra    d4,.check_vector
        move.l  timing_scene_fraction(pc),d6
        move.l  timing_hz(pc),d7
        ; Match the world render horizon, including its bounded display lead.
        lea     external_delta(pc),a1
        lea     external_offsets(pc),a3
        moveq   #3,d4
.draw_vector:
        move.w  (a3)+,d0
        lea     (a4,d0.w),a2
        moveq   #2,d3
.draw:
        move.l  (a1)+,d0
        bsr.w   timing_scene_scale
        add.l   d0,(a2)+
        dbra    d3,.draw
        dbra    d4,.draw_vector
.done:
        rts
.invalidate:
        lea     external_valid(pc),a0
        clr.w   (a0)
        lea     external_seen(pc),a0
        clr.w   (a0)
        rts
        cnop 0,4
external_seen: dc.w 0
external_valid: dc.w 0
external_identity: dcb.l 2,0
external_pose: dcb.l 12,0
external_delta: dcb.l 12,0
external_offsets: dc.w $1478,$2426,$372e,$3a2e
