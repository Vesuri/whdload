; Preview the next native control step without committing throttle/fire or
; advancing the native ramp. This supplies a responsive angular rate between
; world ticks; only the real tick commits the original input/action routine.
; Free-camera/script/death modes retain their native world path for now.
timing_preview_controls:
        movem.l d0-d7/a0-a6,-(sp)
        lea     timing_angles(pc),a0
        clr.l   (a0)
        clr.w   4(a0)
        cmpi.w  #12,5888(a4)
        bne.w   .inactive
        cmpi.w  #-1,5478(a4)
        bne.w   .inactive
        cmpi.w  #8,-18280(a4)
        beq.w   .inactive
        move.l  5882(a4),-(sp)
        move.w  5886(a4),-(sp)
        move.w  5498(a4),-(sp)
        move.w  5626(a4),-(sp)
        move.w  5754(a4),-(sp)
        lea     timing_preview(pc),a0
        move.w  #1,(a0)
        move.l  timing_game(pc),a6
        jsr     $18daa(a6)
        move.l  timing_game(pc),a6
        jsr     $742(a6)
        lea     timing_angles(pc),a0
        move.w  5626(a4),(a0)
        move.w  5498(a4),2(a0)
        move.w  5754(a4),4(a0)
        lea     timing_preview(pc),a0
        clr.w   (a0)
        move.w  (sp)+,5754(a4)
        move.w  (sp)+,5626(a4)
        move.w  (sp)+,5498(a4)
        move.w  (sp)+,5886(a4)
        move.l  (sp)+,5882(a4)
        bra.s   .done
.inactive:
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
        addi.l  #$6fe,(sp)
        rts
.done:
        rts

timing_throttle_gate:
        tst.w   timing_preview(pc)
        bne.s   .done
        move.l  timing_game(pc),-(sp)
        addi.l  #$ccda,(sp)
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
        cmpi.w  #12,5888(a4)
        bne.s   .native
        cmpi.w  #-1,5478(a4)
        bne.s   .native
        cmpi.w  #8,-18280(a4)
        beq.s   .native
        bra.s   .compare
.native:
        move.l  a6,-(sp)
        move.w  8(sp),-(sp)
        move.l  timing_game(pc),a6
        jsr     $7c86(a6)
        addq.l  #2,sp
        move.l  (sp)+,a6
.compare:
        cmpi.w  #10,d2
        rts

; Advance one elapsed field, carrying signed sub-angle remainders. All native
; rotations run in original axis order and rebuild the orthogonal basis.
; Repeating one-field substeps makes grouping by render frame irrelevant.
timing_player_field:
        movem.l d0-d7/a0-a6,-(sp)
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
        clr.w   -(sp)                ; player object zero
        move.w  d0,-(sp)
        move.l  timing_game(pc),a6
        tst.w   d4
        bne.s   .yaw
        jsr     $2acb2(a6)
        bra.s   .pop
.yaw:
        cmpi.w  #1,d4
        bne.s   .roll
        jsr     $2acf2(a6)
        bra.s   .pop
.roll:
        jsr     $2ad32(a6)
.pop:
        addq.l  #4,sp
.next:
        addq.w  #1,d4
        cmpi.w  #3,d4
        bne.s   .axis
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
        cmpi.w  #3,-18280(a4)
        bhi.s   .done
        tst.w   -29978(a4)
        bne.s   .done
        move.l  timing_game(pc),a6
        jsr     $680e(a6)
.done:
        rts
        cnop    0,4
timing_preview: dc.w 0
timing_in_world: dc.w 0
timing_angles: dcb.w 3,0
        cnop    0,4
timing_angle_remainder: dcb.l 3,0
timing_player_fields: dc.l 0
