; Flight ownership boundary, not a pause, view change or clock recovery.
; Discard old control inertia while retaining the new scene's authored pose,
; velocity and throttle. Fresh held input is sampled normally after entry.
timing_player_reset:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w   timing_prediction_reset
        clr.l   A_5882(a4)
        clr.w   A_5886(a4)
        clr.w   A_5498(a4)
        clr.w   A_5626(a4)
        clr.w   A_5754(a4)
        lea     timing_angles(pc),a0
        clr.l   (a0)
        clr.w   4(a0)
        lea     timing_angle_remainder(pc),a0
        clr.l   (a0)+
        clr.l   (a0)+
        clr.l   (a0)
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Preview the next native control step without committing throttle/fire or
; advancing the native ramp. This supplies a responsive angular rate between
; world ticks; only the real tick commits the original input/action routine.
; Enhanced normal/afterburn/braking steering has the same field owner.
; Free-camera/script/death modes retain their native world path for now.
timing_preview_controls:
        movem.l d0-d7/a0-a6,-(sp)
        lea     timing_angles(pc),a0
        clr.l   (a0)
        clr.w   4(a0)
        cmpi.w  #12,A_5888(a4)
        bne.w   .inactive
        cmpi.w  #-1,A_5478(a4)
        ifne BUFFERED
        beq.s   .thrust
        cmpi.w  #1,A_5478(a4)
        beq.s   .thrust
        cmpi.w  #3,A_5478(a4)
        endif
        bne.w   .inactive
.thrust:
        cmpi.w  #8,A_m18280(a4)
        beq.w   .inactive
        move.l  A_5882(a4),-(sp)
        move.w  A_5886(a4),-(sp)
        move.w  A_5498(a4),-(sp)
        move.w  A_5626(a4),-(sp)
        move.w  A_5754(a4),-(sp)
        lea     timing_preview(pc),a0
        move.w  #1,(a0)
        move.l  timing_game(pc),a6
        jsr     E_18daa(a6)
        move.l  timing_game(pc),a6
        jsr     E_742(a6)
        lea     timing_angles(pc),a0
        move.w  A_5626(a4),(a0)
        move.w  A_5498(a4),2(a0)
        move.w  A_5754(a4),4(a0)
        lea     timing_preview(pc),a0
        clr.w   (a0)
        move.w  (sp)+,A_5754(a4)
        move.w  (sp)+,A_5626(a4)
        move.w  (sp)+,A_5498(a4)
        move.w  (sp)+,A_5886(a4)
        move.l  (sp)+,A_5882(a4)
        bra.s   .done
.inactive:
        bsr.w   player_basis_reset
        lea     timing_angle_remainder(pc),a0
        clr.l   (a0)+
        clr.l   (a0)+
        clr.l   (a0)
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

timing_fire_gate:
        tst.w   timing_preview(pc)
        bne.s   .done
        move.l  timing_game(pc),-(sp)
        addi.l  #E_6fe,(sp)
        rts
.done:
        rts

timing_throttle_gate:
        tst.w   timing_preview(pc)
        bne.s   .done
        move.l  timing_game(pc),-(sp)
        addi.l  #E_ccda,(sp)
        rts
.done:
        rts

; Replace the player-only rotation in the ordinary scheduled world. Other
; objects and modal/native updates retain their original rotation and damping.
; This replaces the call plus following CMP #10,D2 (8 bytes).
timing_world_rotation:
        tst.w   timing_in_world(pc)
        beq.s   .native
        tst.w   d2
        bne.s   .native
        cmpi.w  #12,A_5888(a4)
        bne.s   .native
        cmpi.w  #-1,A_5478(a4)
        ifne BUFFERED
        beq.s   .thrust
        cmpi.w  #1,A_5478(a4)
        beq.s   .thrust
        cmpi.w  #3,A_5478(a4)
        endif
        bne.s   .native
.thrust:
        cmpi.w  #8,A_m18280(a4)
        beq.s   .native
        bra.s   .compare
.native:
        move.l  a6,-(sp)
        move.w  8(sp),-(sp)
        move.l  timing_game(pc),a6
        jsr     E_7c86(a6)
        addq.l  #2,sp
        move.l  (sp)+,a6
.compare:
        cmpi.w  #10,d2
        rts

; Advance one elapsed field, carrying signed sub-angle remainders. Q14
; rotations retain native axis order without repeated Q8 rounding drift.
; Repeating one-field substeps makes grouping by render frame irrelevant.
timing_player_field:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w   player_basis_sync
        moveq   #0,d5
        lea     timing_angles(pc),a2
        lea     timing_angle_remainder(pc),a3
        moveq   #0,d4
.axis:
        move.w  (a2)+,d0
        muls.w  #10,d0
        add.l   (a3),d0
        divs.w  timing_hz+2(pc),d0
        move.l  d0,d1
        swap    d1
        ext.l   d1
        move.l  d1,(a3)+
        tst.w   d0
        beq.s   .next
        bsr.w   player_basis_rotate
        moveq   #1,d5
.next:
        addq.w  #1,d4
        cmpi.w  #3,d4
        bne.s   .axis
        tst.w   d5
        beq.s   .no_rotation
        bsr.w   player_basis_publish
.no_rotation:
        ifne BUFFERED
        bsr.w   translation_field
        endif
        lea     timing_player_fields(pc),a0
        addq.l  #1,(a0)
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Rebuild ordinary forward/side/rear camera poses from the new player basis.
; Script and external-camera state machines must not advance on extra renders.
timing_player_camera:
        ; Ready uses ordinary mode 0 under the modal clock. Rebuild from
        ; the staged player here too; old intro camera rates are not its owner.
        cmpi.w  #3,A_m18280(a4)
        bhi.s   .done
        tst.w   A_m29978(a4)
        bne.s   .done
        move.l  timing_game(pc),a6
        jsr     E_680e(a6)
.done:
        rts
        cnop    0,4
timing_preview: dc.w 0
timing_in_world: dc.w 0
timing_angles: dcb.w 3,0
        cnop    0,4
timing_angle_remainder: dcb.l 3,0
timing_player_fields: dc.l 0
