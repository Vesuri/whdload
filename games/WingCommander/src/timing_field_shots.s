; Enhanced flight cannon/field contacts. Shared via the verified OCS mapping.
; A completed movement interval is drawn before its collision is committed at
; the next world boundary. Cache only identities/geometry, never damage or RNG.
field_shot_snapshot:
        lea     field_shot_targets(pc),a0
        moveq   #63,d0
.clear:
        move.b  #-1,(a0)+
        dbra    d0,.clear
        tst.w   timing_active(pc)
        beq.w   .done
        tst.w   intro_active(pc)
        bne.w   .done
        moveq   #10,d4
.shot:
        lea     5888(a4),a0
        cmpi.w  #8,(a0,d4.w*2)
        bne.w   .next_shot
        lea     field_shot_effects(pc),a0
        clr.b   (a0,d4.w)
        lea     14954(a4),a0
        tst.b   (a0,d4.w)
        bne.w   .next_shot
        lea     timing_scene_predictable(pc),a0
        tst.b   (a0,d4.w)
        beq.w   .next_shot
        ; Preserve the native priority of non-field endpoint contacts in
        ; both presentation and response, without leaking the query scratch.
        bsr.w   field_native_target
        cmpi.w  #-1,d0
        beq.s   .scan
        lea     5888(a4),a0
        move.w  (a0,d0.w*2),d1
        cmpi.w  #9,d1
        beq.s   .scan
        cmpi.w  #10,d1
        bne.w   .next_shot
        lea     6136(a4),a0
        cmpi.w  #33,(a0,d0.w*2)
        bne.w   .next_shot
.scan:
        lea     field_best(pc),a0
        move.l  #65537,(a0)
        moveq   #0,d5
.target:
        lea     5888(a4),a0
        move.w  (a0,d5.w*2),d0
        cmpi.w  #9,d0
        beq.s   .hazard
        cmpi.w  #10,d0
        bne.w   .next_target
        lea     6136(a4),a0
        cmpi.w  #33,(a0,d5.w*2)   ; class 10 also contains non-mine objects
        bne.w   .next_target
.hazard:
        lea     timing_scene_predictable(pc),a0
        tst.b   (a0,d5.w)
        beq.w   .next_target
        move.w  d4,d0
        mulu.w  #12,d0
        move.w  d5,d1
        mulu.w  #12,d1
        lea     4508(a4),a0
        lea     (a0,d0.w),a1
        adda.w  d1,a0
        lea     7534(a4),a2
        lea     (a2,d0.w),a3
        adda.w  d1,a2
        lea     field_segment(pc),a5
        moveq   #2,d2
.relative:
        move.l  (a1)+,d0
        sub.l   (a0)+,d0
        bvs.w   .next_target
        move.l  (a3)+,d1
        sub.l   (a2)+,d1
        bvs.w   .next_target
        sub.l   d1,d0
        bvs.w   .next_target
        move.l  d0,(a5)
        move.l  d1,12(a5)
        addq.l  #4,a5
        dbra    d2,.relative
        lea     6908(a4),a0
        moveq   #0,d0
        move.w  (a0,d4.w*2),d0
        move.w  (a0,d5.w*2),d1
        add.w   d1,d0
        ble.w   .next_target
        lsl.l   #8,d0
        lea     field_radius(pc),a0
        move.l  d0,(a0)
        bsr.w   field_segment_hit
        tst.l   d0
        bmi.w   .next_target
        cmp.l   field_best(pc),d0
        bhs.w   .next_target
        lea     field_best(pc),a0
        move.l  d0,(a0)
        move.w  d4,d1
        lsl.w   #2,d1
        lea     field_shot_fractions(pc),a0
        move.l  d0,(a0,d1.w)
        lea     field_shot_targets(pc),a0
        move.b  d5,(a0,d4.w)
        bsr.w   field_point
        move.w  d4,d1
        mulu.w  #12,d1
        lea     field_shot_contacts(pc),a0
        adda.w  d1,a0
        lea     field_point_value(pc),a1
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
.next_target:
        addq.w  #1,d5
        cmpi.w  #61,d5
        blo.w   .target
.next_shot:
        addq.w  #1,d4
        cmpi.w  #61,d4
        blo.w   .shot
.done:
        rts

field_native_target:
        movem.l d1-d3/a0-a1/a6,-(sp)
        lea     15162(a4),a0
        move.l  8(a0),-(sp)
        move.l  4(a0),-(sp)
        move.l  (a0),-(sp)
        move.w  d4,-(sp)
        movea.l timing_game(pc),a6
        jsr     $1597e(a6)
        addq.l  #2,sp
        lea     15162(a4),a0
        move.l  (sp)+,(a0)+
        move.l  (sp)+,(a0)+
        move.l  (sp)+,(a0)+
        movem.l (sp)+,d1-d3/a0-a1/a6
        rts

; Segment R + t*D, t in [0,65536]. Broad phase rejects separated axis ranges.
; Closest Euclidean point uses a common power-of-two normalization for 16x16
; products. The native radius predicate accepts the point; binary search finds
; its entry boundary. No widened radius or changed native target classification.
field_segment_hit:
        movem.l d4-d7/a0-a3/a5-a6,-(sp)
        lea     field_segment(pc),a0
        lea     field_normal(pc),a1
        move.l  field_radius(pc),d6
        moveq   #2,d3
.bounds:
        move.l  (a0),d0
        move.l  12(a0),d1
        move.l  d0,(a1)
        move.l  d1,12(a1)
        add.l   d0,d1
        bvs.w   .miss
        cmp.l   d6,d0
        blt.s   .negative
        cmp.l   d6,d1
        bge.w   .miss
.negative:
        neg.l   d6
        cmp.l   d6,d0
        bgt.s   .axis_done
        cmp.l   d6,d1
        ble.w   .miss
.axis_done:
        neg.l   d6
        addq.l  #4,a0
        addq.l  #4,a1
        dbra    d3,.bounds
.normalize:
        lea     field_normal(pc),a0
        moveq   #5,d3
.maximum:
        move.l  (a0)+,d0
        cmpi.l  #16383,d0
        bgt.s   .shift
        cmpi.l  #-16383,d0
        blt.s   .shift
        dbra    d3,.maximum
        bra.s   .dot
.shift:
        lea     field_normal(pc),a0
        moveq   #5,d3
.shift_axis:
        move.l  (a0),d0
        asr.l   #1,d0
        move.l  d0,(a0)
        addq.l  #4,a0
        dbra    d3,.shift_axis
        bra.s   .normalize
.dot:
        lea     field_normal(pc),a0
        moveq   #0,d1
        moveq   #0,d2
        moveq   #2,d3
.dot_axis:
        move.l  12(a0),d0
        muls.w  2(a0),d0
        sub.l   d0,d1
        move.l  12(a0),d0
        muls.w  14(a0),d0
        add.l   d0,d2
        addq.l  #4,a0
        dbra    d3,.dot_axis
        moveq   #0,d0
        tst.l   d1
        ble.s   .closest
        move.l  #65536,d0
        cmp.l   d2,d1
        bhs.s   .closest
        moveq   #0,d0
        moveq   #15,d3
.ratio:
        add.l   d0,d0
        add.l   d1,d1
        cmp.l   d2,d1
        blo.s   .ratio_next
        sub.l   d2,d1
        addq.l  #1,d0
.ratio_next:
        dbra    d3,.ratio
.closest:
        move.l  d0,d7
        bsr.w   field_inside
        tst.w   d0
        beq.s   .miss
        moveq   #0,d0
        bsr.w   field_inside
        tst.w   d0
        bne.s   .zero
        moveq   #0,d6
        moveq   #15,d5
.bisect:
        move.l  d6,d0
        add.l   d7,d0
        lsr.l   #1,d0
        move.l  d0,d4
        bsr.w   field_inside
        tst.w   d0
        beq.s   .outside
        move.l  d4,d7
        bra.s   .bisect_next
.outside:
        move.l  d4,d6
.bisect_next:
        dbra    d5,.bisect
        move.l  d7,d0
        bra.s   .return
.zero:
        moveq   #0,d0
        bra.s   .return
.miss:
        moveq   #-1,d0
.return:
        movem.l (sp)+,d4-d7/a0-a3/a5-a6
        rts

field_inside:
        bsr.w   field_point
        move.l  field_radius(pc),d0
        lsr.l   #8,d0
        move.l  d0,-(sp)
        pea     field_point_value(pc)
        movea.l timing_game(pc),a6
        jsr     $2c8dc(a6)
        addq.l  #8,sp
        rts

; Exact signed scaling by an unsigned Q16 fraction without a 64-bit instruction.
; D0 signed value, D1 fraction (0..65536), result D0; scratch D2/D3.
field_scale:
        cmpi.l  #65536,d1
        beq.s   .done
        move.l  d0,-(sp)
        tst.l   d0
        bpl.s   .positive
        neg.l   d0
.positive:
        move.l  d0,d2
        mulu.w  d1,d2
        swap    d2
        andi.l  #65535,d2
        swap    d0
        mulu.w  d1,d0
        add.l   d2,d0
        tst.l   (sp)+
        bpl.s   .done
        neg.l   d0
.done:
        rts

field_point:
        movem.l d4/a0-a1,-(sp)
        move.l  d0,d1
        lea     field_segment(pc),a0
        lea     field_point_value(pc),a1
        moveq   #2,d4
.axis:
        move.l  12(a0),d0
        bsr.s   field_scale
        add.l   (a0)+,d0
        move.l  d0,(a1)+
        dbra    d4,.axis
        movem.l (sp)+,d4/a0-a1
        rts

; Native response calls this in place of its query. Non-field native contacts
; retain priority. A valid cache is consumed once; all response/effect work is
; still native. Input/reuse/teleport invalidation compares snapshot identities.
field_shot_query:
        movem.l d1-d7/a0-a6,-(sp)
        move.w  60(sp),d4
        move.w  d4,-(sp)
        movea.l timing_game(pc),a6
        jsr     $1597e(a6)
        addq.l  #2,sp
        move.l  d0,d7
        tst.w   timing_active(pc)
        beq.w   .return
        tst.w   intro_active(pc)
        bne.w   .return
        cmpi.w  #60,d4
        bhi.w   .return
        lea     5888(a4),a0
        cmpi.w  #8,(a0,d4.w*2)
        bne.w   .return
        lea     14954(a4),a0
        tst.b   (a0,d4.w)
        bne.w   .return
        cmpi.w  #-1,d7
        beq.s   .cached
        lea     5888(a4),a0
        move.w  (a0,d7.w*2),d0
        cmpi.w  #9,d0
        beq.s   .native_field
        cmpi.w  #10,d0
        bne.w   .return
        lea     6136(a4),a0
        cmpi.w  #33,(a0,d7.w*2)
        bne.w   .return
.native_field:
        lea     field_shot_effects(pc),a0
        move.b  #1,(a0,d4.w)     ; native endpoint hit, even on a cold interval
.cached:
        tst.w   timing_scene_valid(pc)
        beq.w   .return
        lea     field_shot_targets(pc),a0
        moveq   #0,d5
        move.b  (a0,d4.w),d5
        bmi.w   .return
        move.w  d4,d0
        bsr.w   field_identity
        tst.w   d0
        beq.w   .return
        move.w  d5,d0
        bsr.w   field_identity
        tst.w   d0
        beq.w   .return
        move.w  d5,d7
        lea     field_shot_targets(pc),a0
        move.b  #-1,(a0,d4.w)
        lea     field_shot_effects(pc),a0
        move.b  #1,(a0,d4.w)
        move.w  d4,d0
        mulu.w  #12,d0
        move.w  d5,d1
        mulu.w  #12,d1
        lea     field_shot_contacts(pc),a0
        adda.w  d0,a0
        lea     4508(a4),a1
        lea     (a1,d0.w),a2
        adda.w  d1,a1
        lea     15162(a4),a3
        moveq   #2,d2
.contact:
        move.l  (a0)+,d0
        move.l  d0,(a3)+
        add.l   (a1)+,d0
        move.l  d0,(a2)+
        dbra    d2,.contact
.return:
        move.l  d7,d0
        movem.l (sp)+,d1-d7/a0-a6
        rts

field_identity:
        lea     5888(a4),a0
        lea     timing_scene_types(pc),a1
        move.w  (a0,d0.w*2),d1
        cmp.w   (a1,d0.w*2),d1
        bne.s   .bad
        lea     6136(a4),a0
        lea     timing_scene_models(pc),a1
        move.w  (a0,d0.w*2),d1
        cmp.w   (a1,d0.w*2),d1
        bne.s   .bad
        mulu.w  #12,d0
        lea     4508(a4),a0
        lea     timing_scene_positions(pc),a1
        adda.w  d0,a0
        adda.w  d0,a1
        moveq   #2,d1
.axis:
        cmpm.l  (a0)+,(a1)+
        bne.s   .bad
        dbra    d1,.axis
        moveq   #1,d0
        rts
.bad:
        moveq   #0,d0
        rts

; Called after all displayed targets have been positioned. Clamp relative to
; the displayed target only after the cached swept contact fraction is reached.
field_shot_limit:
        tst.w   timing_active(pc)
        beq.w   .done
        tst.w   intro_active(pc)
        bne.w   .done
        moveq   #10,d4
.slot:
        lea     field_shot_targets(pc),a0
        moveq   #0,d5
        move.b  (a0,d4.w),d5
        bmi.s   .next
        move.w  d4,d0
        lsl.w   #2,d0
        lea     field_shot_fractions(pc),a0
        move.l  (a0,d0.w),d0
        ; Q16 contact * field rate versus display fraction * 65536.
        move.l  d0,d1
        mulu.w  d7,d1
        cmpi.l  #65536,d0
        bne.s   .fraction
        move.l  d7,d1
        swap    d1
.fraction:
        move.l  d6,d0
        swap    d0
        clr.w   d0
        cmp.l   d1,d0
        blo.s   .next
        move.w  d4,d0
        mulu.w  #12,d0
        move.w  d5,d1
        mulu.w  #12,d1
        lea     4508(a4),a0
        lea     (a0,d0.w),a1
        adda.w  d1,a0
        lea     field_shot_contacts(pc),a2
        adda.w  d0,a2
        moveq   #2,d2
.axis:
        move.l  (a0)+,d0
        add.l   (a2)+,d0
        move.l  d0,(a1)+
        dbra    d2,.axis
.next:
        addq.w  #1,d4
        cmpi.w  #61,d4
        blo.w   .slot
.done:
        rts

field_shot_targets: dcb.b 64,-1
field_shot_effects: dcb.b 64,0
field_shot_fractions: dcb.l 64,0
field_shot_contacts: dcb.l 192,0
field_best: dc.l 0
field_radius: dc.l 0
field_segment: dcb.l 6,0
field_normal: dcb.l 6,0
field_point_value: dcb.l 3,0
