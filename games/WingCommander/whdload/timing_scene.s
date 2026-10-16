; Equal queued pad samples cannot dispatch an edge at E:19278/19128.
; Defer the first rebuild only if every 16-byte sample matches native current
; pad state. Any transition retains both calls; the queue is still consumed.
timing_edge_geometry:
        ifne BUFFERED
        movem.l d0-d1/a0-a2,-(sp)
        lea     timing_geometry_repeat(pc),a0
        clr.w   (a0)
        move.w  timing_pad_count(pc),d0
        beq.s   .unchanged
        subq.w  #1,d0
        lea     timing_pad_pending(pc),a2
.sample:
        lea     $46ca(a4),a1
        moveq   #3,d1
.compare:
        cmpm.l  (a1)+,(a2)+
        bne.s   .edges
        dbra    d1,.compare
        dbra    d0,.sample
.unchanged:
        move.w  #1,(a0)
        movem.l (sp)+,d0-d1/a0-a2
        rts
.edges:
        movem.l (sp)+,d0-d1/a0-a2
        endif
        bra.w   timing_scene_geometry

; Native E:2a086 copies current range to previous range before rebuilding it.
; Preserve the second call's history effect after a single rebuild. Class 0/7
; are skipped exactly as native; negative classes still participate.
timing_geometry_history:
        ifne BUFFERED
        tst.w   timing_geometry_repeat(pc)
        beq.s   .done
        moveq   #WC_OBJECTS_WORLD_SLOTS-1,d0
.slot:
        move.w  $1700(a4,d0.w*2),d1
        beq.s   .next
        cmpi.w  #7,d1
        beq.s   .next
        move.w  $24de(a4,d0.w*2),$255e(a4,d0.w*2)
.next:
        dbra    d0,.slot
.done:
        endif
        rts
timing_geometry_repeat: dc.w 0

; Refresh geometry before edge commands can use ranges or aiming predicates.
; Rendering may leave screen-space scratch, but gameplay always sees geometry
; rebuilt from restored authoritative poses, including on an ordinary-loop exit.
timing_scene_geometry:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w   timing_player_camera
        move.l  timing_game(pc),a6
        jsr     $2a086(a6)
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Renderer-only prediction. The native arrays are a staging interface: save
; them before drawing and restore them before input, targeting or world work.
; No predicted pose is ever consumed by a simulation call. Rebuild each picture
; from the current authoritative pose; corrections snap at the next world tick.
timing_scene_snapshot:
        movem.l d0-d7/a0-a6,-(sp)
        lea     timing_scene_predictable(pc),a5
        moveq   #0,d4
        moveq   #0,d5
.check:
        clr.b   (a5,d4.w)
        tst.w   timing_scene_valid(pc)
        beq.w   .check_next
        move.w  -18280(a4),d0
        cmp.w   timing_scene_view(pc),d0
        bne.w   .check_next
        ifne BUFFERED
        ; Only an actual completed constructor may bypass old-slot continuity.
        lea     projectile_types(pc),a0
        move.w  (a0,d4.w*2),d0
        beq.s   .old_slot
        lea     5888(a4),a0
        cmp.w   (a0,d4.w*2),d0
        bne.w   .check_next
        lea     projectile_models(pc),a0
        move.w  (a0,d4.w*2),d0
        lea     6136(a4),a0
        cmp.w   (a0,d4.w*2),d0
        bne.w   .check_next
        lea     5888(a4),a0
        cmpi.w  #5,(a0,d4.w*2)     ; effect-script shot has no word lifetime
        beq.w   .accept
        lea     5320(a4),a0
        move.w  (a0,d4.w*2),d0
        bgt.w   .accept
        cmpi.w  #-1,d0
        beq.w   .accept
        bra.w   .check_next
.old_slot:
        endif
        lea     5888(a4),a0
        lea     timing_scene_types(pc),a1
        move.w  (a0,d4.w*2),d0
        cmp.w   (a1,d4.w*2),d0
        bne.w   .check_next
        lea     6136(a4),a0
        lea     timing_scene_models(pc),a1
        move.w  (a0,d4.w*2),d0
        cmp.w   (a1,d4.w*2),d0
        bne.w   .check_next
        lea     5320(a4),a0
        lea     timing_scene_life(pc),a1
        move.w  (a0,d4.w*2),d0
        cmp.w   (a1,d4.w*2),d0
        ifne BUFFERED
        ble.s   .life_ok
        ; A constructor-certified ship cooldown is not a birth or teleport.
        lea     projectile_cooldown_valid(pc),a0
        tst.b   (a0,d4.w)
        beq.w   .check_next
        lea     projectile_cooldown(pc),a0
        sub.w   (a0,d4.w*2),d0
        beq.s   .life_ok
        cmpi.w  #-1,d0            ; player input precedes native countdown
        bne.w   .check_next
.life_ok:
        else
        bgt.w   .check_next       ; lifetime reload/new object
        endif
        cmpi.w  #10,d4
        bhs.s   .position
        lea     5478(a4),a0
        lea     timing_scene_actions(pc),a1
        move.w  (a0,d4.w*2),d0
        cmp.w   (a1,d4.w*2),d0
        bne.w   .check_next
.position:
        lea     4508(a4),a0
        adda.w  d5,a0
        lea     timing_scene_positions(pc),a1
        adda.w  d5,a1
        lea     timing_scene_velocities(pc),a2
        adda.w  d5,a2
        moveq   #2,d3
.check_axis:
        move.l  (a0)+,d0
        sub.l   (a1)+,d0
        bvs.s   .check_next
        sub.l   (a2),d0
        bvs.s   .check_next
        bpl.s   .positive
        neg.l   d0
        bvs.s   .check_next
.positive:
        move.l  (a2)+,d1
        bpl.s   .speed
        neg.l   d1
        bvs.s   .check_next
.speed:
        ; More than four previous displacements plus 100 km is a jump.
        cmpi.l  #$10000000,d1
        bhs.s   .check_next
        lsl.l   #2,d1
        addi.l  #25600,d1
        cmp.l   d1,d0
        bhi.s   .check_next
        dbra    d3,.check_axis
.accept:
        move.b  #1,(a5,d4.w)
.check_next:
        addq.w  #1,d4
        addi.w  #12,d5
        cmpi.w  #61,d4
        blo.w   .check
        ifne BUFFERED
        tst.w   intro_active(pc)
        beq.s   .checked
        cmpi.w  #62,d4
        blo.w   .check
.checked:
        endif
        ifne BUFFERED
        bsr.w   projectile_reset
        endif
        lea     timing_scene_snapshot_data(pc),a1
        lea     timing_scene_snapshot_ranges(pc),a2
        moveq   #8,d2
.range:
        move.w  (a2)+,d0
        lea     (a4,d0.w),a0
        move.w  (a2)+,d1
.copy:
        move.w  (a0)+,(a1)+
        dbra    d1,.copy
        dbra    d2,.range
        lea     timing_scene_valid(pc),a0
        move.w  #1,(a0)
        move.w  -18280(a4),2(a0)
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Cosmetic regeneration used to mutate objects from the draw path. Once per
; world boundary, project authoritative geometry then run its native routine
; with the private rendering RNG. Drawing only consumes the resulting objects.
timing_scene_tick:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w   timing_player_camera
        move.l  timing_game(pc),a6
        jsr     $2a086(a6)
        move.l  -4326(a4),-(sp)
        move.l  timing_render_seed(pc),-4326(a4)
        moveq   #0,d0
        tst.l   4470(a4)
        beq.s   .arg
        moveq   #1,d0
.arg:
        move.w  d0,-(sp)
        bsr.w   timing_debris_original
        addq.l  #2,sp
        lea     timing_render_seed(pc),a0
        move.l  -4326(a4),(a0)
        move.l  (sp)+,-4326(a4)
        bsr.w   timing_scene_snapshot
        movem.l (sp)+,d0-d7/a0-a6
        rts

timing_debris_draw:
        ifne BUFFERED
        tst.w   intro_active(pc)
        bne.s   .done
        endif
        tst.w   timing_active(pc)
        bne.s   .done
        bra.w   timing_debris_original
.done:
        rts

; D0 * fraction / rate, truncating toward zero. Split quotient/remainder
; avoids a 64-bit division (not native on 040). Buffered release prediction
; permits one tick plus two display fields; signed results wrap as native longs.
timing_scene_scale:
        move.l  d0,d2
        divs.l  d7,d0
        move.l  d0,d1
        muls.l  d7,d1
        sub.l   d1,d2
        muls.l  d6,d0
        muls.l  d6,d2
        divs.l  d7,d2
        add.l   d2,d0
        rts

timing_scene_begin:
        movem.l d0-d7/a0-a6,-(sp)
        lea     timing_scene_staged(pc),a0
        clr.w   (a0)
        lea     timing_scene_fraction(pc),a0
        clr.l   (a0)
        tst.w   timing_active(pc)
        ifne BUFFERED
        bne.s   .enabled
        tst.w   intro_active(pc)
.enabled:
        endif
        beq.w   .done
        ifne BUFFERED
        bsr.w   timing_scene_save_active
        else
        ; Back up all 64 poses, including camera/scratch slots 61..63, plus
        ; native allocation and projection fields used by render attachments.
        lea     timing_scene_saved(pc),a1
        lea     timing_scene_pose_ranges(pc),a2
        moveq   #24,d2
.save_range:
        move.w  (a2)+,d0
        lea     (a4,d0.w),a0
        move.w  (a2)+,d1
.save:
        move.l  (a0)+,(a1)+
        dbra    d1,.save
        dbra    d2,.save_range
        endif
        lea     timing_scene_staged(pc),a0
        move.w  #1,(a0)
        ifne BUFFERED
        bsr.w   release_predict
        else
        move.l  timing_clock+4(pc),d6
        move.l  timing_hz(pc),d7
        cmp.l   d7,d6
        bls.s   .bounded
        move.l  d7,d6
.bounded:
        endif
        tst.w   timing_scene_valid(pc)
        beq.w   .camera
        move.w  -18280(a4),d0
        cmp.w   timing_scene_view(pc),d0
        bne.w   .cut
        ifne BUFFERED
        tst.w   intro_active(pc)
        bne.s   .intro_view
        endif
        cmpi.w  #3,d0
        bhi.w   .cut
        tst.w   -29978(a4)
        bne.w   .cut
        cmpi.w  #12,5888(a4)
        bne.w   .cut
        cmpi.w  #-1,5478(a4)
        bne.w   .cut
        ifne BUFFERED
.intro_view:
        endif
        lea     timing_scene_fraction(pc),a0
        move.l  d6,(a0)
        tst.l   d6
        beq.w   .camera
        ifne BUFFERED
        tst.w   intro_active(pc)
        bne.s   .objects
        endif
        tst.b   timing_scene_predictable(pc)
        beq.w   .camera           ; player jump cuts the entire camera interval
        ifne BUFFERED
.objects:
        endif
        moveq   #0,d4
        moveq   #0,d5
.object:
        ifne BUFFERED
        bsr.w   timing_scene_effect_size
        endif
        ; Stars are directions, not world positions. Empty/hidden slots stay
        ; native. Effect images and lifetime retain their native tick transitions.
        lea     timing_scene_predictable(pc),a0
        tst.b   (a0,d4.w)
        beq.w   .next
        lea     5888(a4),a0
        move.w  (a0,d4.w*2),d0
        ifne BUFFERED
        cmpi.w  #61,d4
        beq.s   .camera_slot
        endif
        cmpi.w  #3,d0
        blo.w   .next
        cmpi.w  #7,d0
        beq.w   .next
        ifne BUFFERED
.camera_slot:
        endif
        lea     timing_scene_types(pc),a1
        cmp.w   (a1,d4.w*2),d0
        bne.w   .next
        lea     6136(a4),a0
        lea     timing_scene_models(pc),a1
        move.w  (a0,d4.w*2),d0
        cmp.w   (a1,d4.w*2),d0
        bne.w   .next
        lea     4508(a4),a2
        adda.w  d5,a2
        lea     timing_scene_positions(pc),a3
        adda.w  d5,a3
        ifne BUFFERED
        tst.w   d4
        bne.s   .world_pose
        tst.w   translation_active(pc)
        bne.w   .player_pose
.world_pose:
        endif
        ; A pose changed outside the update snapshot is a cut, not a velocity.
        move.l  (a2),d0
        cmp.l   (a3),d0
        bne.w   .next
        move.l  4(a2),d0
        cmp.l   4(a3),d0
        bne.w   .next
        move.l  8(a2),d0
        cmp.l   8(a3),d0
        bne.w   .next
        ifne BUFFERED
        tst.w   intro_active(pc)
        bne.s   .rotate
        endif
        tst.w   d4
        beq.w   .translate       ; player orientation already elapsed-field
        ; Native axis rotations rebuild an orthogonal fixed-point basis.
        ; Angular steps are snapshots, not a second AI/controller invocation.
        ifne BUFFERED
.rotate:
        cmpi.w  #61,d4
        bne.s   .object_rotation
        bsr.w   timing_intro_camera_rotate
        bra.w   .translate
.object_rotation:
        endif
        moveq   #0,d3
.axis:
        lea     timing_scene_angles(pc),a2
        move.w  d3,d0
        mulu.w  #128,d0
        adda.w  d0,a2
        move.w  (a2,d4.w*2),d0
        ext.l   d0
        bsr.w   timing_scene_scale
        tst.w   d0
        beq.s   .axis_next
        move.w  d4,-(sp)
        move.w  d0,-(sp)
        move.l  timing_game(pc),a6
        tst.w   d3
        bne.s   .yaw
        jsr     $2acb2(a6)
        bra.s   .axis_pop
.yaw:
        cmpi.w  #1,d3
        bne.s   .roll
        jsr     $2acf2(a6)
        bra.s   .axis_pop
.roll:
        jsr     $2ad32(a6)
.axis_pop:
        addq.l  #4,sp
.axis_next:
        addq.w  #1,d3
        cmpi.w  #3,d3
        bne.s   .axis
        ifne BUFFERED
        cmpi.w  #61,d4
        beq.s   .translate
        bsr.w   timing_scene_velocity
        endif
.translate:
        lea     4508(a4),a2
        adda.w  d5,a2
        ifne BUFFERED
        lea     7534(a4),a3
        else
        lea     timing_scene_velocities(pc),a3
        endif
        adda.w  d5,a3
        moveq   #2,d3
.xyz:
        move.l  (a3)+,d0
        bsr.w   timing_scene_scale
        add.l   d0,(a2)+
        dbra    d3,.xyz
        ifne BUFFERED
        bra.s   .next
.player_pose:
        ; Player state already includes every consumed field. Only forecast
        ; the remaining display lead, using current rather than tick velocity.
        move.l  d6,-(sp)
        move.l  release_render_time(pc),d6
        sub.l   timing_clock(pc),d6
        mulu.l  #10,d6
        cmpi.l  #20,d6
        bls.s   .player_bounded
        moveq   #20,d6
.player_bounded:
        lea     7534(a4),a3
        moveq   #2,d3
.player_axis:
        move.l  (a3)+,d0
        bsr.w   timing_scene_scale
        add.l   d0,(a2)+
        dbra    d3,.player_axis
        move.l  (sp)+,d6
        endif
.next:
        addq.w  #1,d4
        addi.w  #12,d5
        cmpi.w  #61,d4
        blo.w   .object
        ifne BUFFERED
        tst.w   intro_active(pc)
        beq.s   .objects_done
        cmpi.w  #62,d4
        blo.w   .object
.objects_done:
        endif
        bra.s   .camera
.cut:
        lea     timing_scene_valid(pc),a0
        clr.w   (a0)              ; remain snapped until a new world snapshot
.camera:
        bsr.w   timing_player_camera
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

; The scripted intro camera can turn by just one native angular unit per tick.
; Scaling that integer angle rounds every intermediate sample to zero. Compute
; its native next basis, then sample the basis delta at the display fraction.
; This is renderer-only, rebuilt from authoritative state each picture; the
; existing pose backup restores all nine components before any world work.
; Only slot 61 reaches this helper. D6/D7 retain the bounded display fraction.
timing_intro_camera_rotate:
        movem.l d0-d3/a0-a3/a5-a6,-(sp)
        lea     -36(sp),sp
        movea.l sp,a5
        lea     9254(a4),a0
        move.l  (a0)+,0(a5)
        move.l  (a0)+,4(a5)
        move.l  (a0)+,8(a5)
        lea     14126(a4),a0
        move.l  (a0)+,12(a5)
        move.l  (a0)+,16(a5)
        move.l  (a0)+,20(a5)
        lea     14894(a4),a0
        move.l  (a0)+,24(a5)
        move.l  (a0)+,28(a5)
        move.l  (a0)+,32(a5)
        move.w  timing_scene_angles+122(pc),d0
        beq.s   .axis_122
        move.w  #61,-(sp)
        move.w  d0,-(sp)
        move.l  timing_game(pc),a6
        jsr     $2acb2(a6)
        addq.l  #4,sp
.axis_122:
        move.w  timing_scene_angles+250(pc),d0
        beq.s   .axis_250
        move.w  #61,-(sp)
        move.w  d0,-(sp)
        move.l  timing_game(pc),a6
        jsr     $2acf2(a6)
        addq.l  #4,sp
.axis_250:
        move.w  timing_scene_angles+378(pc),d0
        beq.s   .axis_378
        move.w  #61,-(sp)
        move.w  d0,-(sp)
        move.l  timing_game(pc),a6
        jsr     $2ad32(a6)
        addq.l  #4,sp
.axis_378:
        movea.l a5,a3
        lea     9254(a4),a2
        bsr.s   .vector
        lea     14126(a4),a2
        bsr.s   .vector
        lea     14894(a4),a2
        bsr.s   .vector
        lea     36(sp),sp
        movem.l (sp)+,d0-d3/a0-a3/a5-a6
        rts
.vector:
        moveq   #2,d3
.component:
        move.l  (a2),d0
        sub.l   (a3),d0
        bsr.w   timing_scene_scale
        add.l   (a3)+,d0
        move.l  d0,(a2)+
        dbra    d3,.component
        rts

; Preview only the next native effect-script size operation. Image selection,
; script cursor/period, allocation and removal remain owned by world ticks.
; D4=slot, D6/D7=display fraction/rate. The existing slot backup owns size.
timing_scene_effect_size:
        movem.l d0-d3/d5-d6/a0-a2,-(sp)
        lea     5888(a4),a0
        move.w  (a0,d4.w*2),d0
        cmpi.w  #5,d0
        beq.s   .effect
        cmpi.w  #6,d0
        beq.s   .effect
        cmpi.w  #9,d0
        beq.s   .effect
        cmpi.w  #10,d0
        bne.w   .done
.effect:
        lea     6136(a4),a0
        move.w  (a0,d4.w*2),d0
        muls.w  #104,d0
        lea     -11354(a4),a0
        adda.l  d0,a0
        move.w  36(a0),d5
        movea.l 26(a0),a1
        move.l  a1,d0
        beq.w   .done
        lea     16504(a4),a0
        move.w  (a0,d4.w*2),d3
        lea     16632(a4),a0
        move.w  (a0,d4.w*2),d2
        lea     13260(a4),a2
        adda.w  d4,a2
        adda.w  d4,a2
        ; The display predictor can lead by one tick plus two fields. Walk
        ; that first tick locally before sampling the following command;
        ; clamping here would introduce a new kink at growth/dwell boundaries.
        cmp.l   d7,d6
        bls.s   .fraction
        bsr.s   .step
        move.w  d0,(a2)
        sub.l   d7,d6
.fraction:
        bsr.s   .step
        moveq   #0,d1
        move.w  (a2),d1
        sub.l   d1,d0
        bsr.w   timing_scene_scale
        add.w   d0,(a2)
.done:
        movem.l (sp)+,d0-d3/d5-d6/a0-a2
        rts

; A read-only native script step: local cursor D2 and period D3, reset D5.
; Return the unsigned endpoint size in D0. Never select an image or remove.
.step:
        subq.w  #1,d3
        bgt.s   .held
        move.w  d5,d3
        move.w  d2,d0
        ext.l   d0
        add.l   d0,d0
        move.w  (a1,d0.l),d1
        move.w  d1,d0
        lsr.w   #8,d0
        lsr.w   #4,d0
        cmpi.w  #10,d0
        beq.s   .removed
        cmpi.w  #9,d0
        bne.s   .command
        andi.w  #$fff,d1
        move.w  d1,d2
        add.w   d1,d1
        move.w  (a1,d1.w),d1
.command:
        addq.w  #1,d2
        move.w  d1,d0
        andi.w  #$c00,d0
        cmpi.w  #$400,d0
        beq.s   .grow
        cmpi.w  #$800,d0
        bne.s   .held
        bsr.s   .amount
        neg.w   d0
        bra.s   .add
.grow:
        bsr.s   .amount
.add:
        add.w   (a2),d0
        andi.l  #$ffff,d0
        rts
.removed:
        move.w  #32767,d3
.held:
        moveq   #0,d0
        move.w  (a2),d0
        rts
.amount:
        moveq   #0,d0
        move.w  (a2),d0
        lsr.w   #6,d0
        andi.w  #$3f,d1
        mulu.w  d1,d0
        rts

timing_scene_end:
        movem.l d0-d2/a0-a2,-(sp)
        tst.w   timing_scene_staged(pc)
        beq.w   timing_scene_restored
        ifne BUFFERED
        bsr.w   timing_scene_restore_active
        else
        lea     timing_scene_saved(pc),a0
        lea     timing_scene_pose_ranges(pc),a2
        moveq   #24,d2
.range:
        move.w  (a2)+,d0
        lea     (a4,d0.w),a1
        move.w  (a2)+,d1
.copy:
        move.l  (a0)+,(a1)+
        dbra    d1,.copy
        dbra    d2,.range
        endif
        lea     timing_scene_staged(pc),a0
        clr.w   (a0)
timing_scene_restored:
        movem.l (sp)+,d0-d2/a0-a2
        rts
        cnop    0,4
; Save the native class-7 flame allocation fields too. E:2914c creates
; render-only attachments in free slots; none may survive into simulation.
timing_scene_pose_ranges:
        dc.w $119c,191
        dc.w $214a,191
        dc.w $3452,191
        dc.w $3752,191
        dc.w $1d6e,191
        dc.w $1700,31
        dc.w $17f8,31
        dc.w $14c8,31
        dc.w $157a,95
        dc.w $2e6e,63
        dc.w $1afc,31
        dc.w $3e90,31
        dc.w $33cc,31
        dc.w $3fbc,31
        dc.w $18c8,31
        dc.w $2c6e,31
        dc.w $2d6e,31
        dc.w $3a6a,15
        dc.w $3b46,15
        dc.w $4078,63
        dc.w $2dee,31
        dc.w $245e,95
        dc.w $2bea,31
        dc.w $2cee,31
        dc.w $3b86,191

timing_scene_snapshot_ranges:
        dc.w $119c,383,$1d6e,383,$1700,63,$17f8,63
        dc.w $15fa,63,$157a,63,$167a,63,$14c8,63,$1566,9
timing_scene_valid: dc.w 0
timing_scene_view: dc.w 0
timing_scene_staged: dc.w 0
        cnop    0,4
timing_scene_fraction: dc.l 0
timing_scene_snapshot_data:
timing_scene_positions: dcb.b 768,0
timing_scene_velocities: dcb.b 768,0
timing_scene_types: dcb.b 128,0
timing_scene_models: dcb.b 128,0
timing_scene_angles: dcb.b 384,0
timing_scene_life: dcb.b 128,0
timing_scene_actions: dcb.b 20,0
timing_scene_predictable: dcb.b 64,0
timing_scene_saved: dcb.b 7680,0
timing_scene_saved_end:
