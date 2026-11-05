        IFD VERIFY
        IFD BATCH_TEST
        IFEQ RECORD_CACHE
        FAIL "BATCH_TEST requires RECORD_CACHE=1"
        ENDC
        IFEQ PROJECT_BATCH
        FAIL "BATCH_TEST requires PROJECT_BATCH=1"
        ENDC
; Whole native pass versus s60_project. Private actors/records/frame arrays;
; mesh rasterization is temporarily suppressed on both sides. Shared scratch
; must match on fallback; accepted passes may defer it. No live actors mutate.
s60_batch_results: dc.b 'Q760'
        dc.w 0,0,0,0,0,0 ; cases, actors, records, scratch, path, busy
s60_batch_path: dc.w 0
s60_batch_case: dc.w 0
s60_batch_expected_path: dc.w 0
s60_batch_saved_table: dc.l 0
s60_batch_saved_modes: dc.l 0
s60_batch_saved_mesh: dc.w 0
s60_batch_saved_cache: ds.l RECORD_CACHE_SLOTS
s60_batch_saved_list: ds.b 1026
s60_batch_saved_hooks: ds.b 8
s60_batch_saved_scratch: ds.b 178
s60_batch_expected_scratch: ds.b 178
s60_batch_actors: ds.b 220
s60_batch_frames: ds.b 512
s60_batch_observed: ds.b 16
s60_batch_expected: ds.b 748
; Both private actors have preseeded records, so no allocation or full-table
; miss scan is possible; the third record is a compared zero sentinel.
s60_batch_records: ds.b 3*S60_REC
s60_batch_expected_records: ds.b 3*S60_REC

s60_test_batch:
        movem.l d0-d7/a0-a6,-(sp)
        move.w (s60_batch_results+4,pc),d0
        bne .done
        move.l (s60_ticks,pc),d0
        cmp.l #BATCH_TEST,d0
        bne .done
        lea (s60_batch_results,pc),a0
        move.w #1,(14,a0)
        lea ($3fb2-S60_DATA,a4),a0
        lea (s60_batch_saved_list,pc),a1
        move.w #512,d0
        bsr s60_batch_copy
        lea ($278a-S60_DATA,a4),a0
        lea (s60_batch_saved_hooks,pc),a1
        moveq #3,d0
        bsr s60_batch_copy
        lea ($5d90-S60_DATA,a4),a0
        lea (s60_batch_saved_scratch,pc),a1
        moveq #88,d0
        bsr s60_batch_copy
        lea (s60_record_cache,pc),a0
        lea (s60_batch_saved_cache,pc),a1
        move.w #RECORD_CACHE_SLOTS*2-1,d0
        bsr s60_batch_copy
        lea (s60_batch_saved_table,pc),a0
        move.l (s60_motion_table,pc),(a0)
        lea (s60_motion_table,pc),a0
        lea (s60_batch_records,pc),a1
        move.l a1,(a0)
        lea (s60_batch_saved_modes,pc),a0
        move.w (s60_running,pc),(a0)+
        move.w (s60_rendering,pc),(a0)
        move.l (s60_code,pc),a0
        adda.l #$132b2,a0
        lea (s60_batch_saved_mesh,pc),a1
        move.w (a0),(a1)
        move.w #$4e75,(a0)
        bsr s60_batch_flush
        lea (s60_batch_case,pc),a0
        clr.w (a0)
.case:  bsr s60_batch_seed
        bsr s60_batch_native
        lea (s60_batch_actors,pc),a0
        lea (s60_batch_expected,pc),a1
        move.w #373,d0
        bsr s60_batch_copy
        lea (s60_batch_records,pc),a0
        lea (s60_batch_expected_records,pc),a1
        move.w #3*S60_REC/2-1,d0
        bsr s60_batch_copy
        lea ($5d90-S60_DATA,a4),a0
        lea (s60_batch_expected_scratch,pc),a1
        moveq #88,d0
        bsr s60_batch_copy
        bsr s60_batch_seed
        bsr s60_project
        lea (s60_batch_results,pc),a2
        lea (s60_batch_actors,pc),a0
        lea (s60_batch_expected,pc),a1
        move.w #373,d0
        bsr s60_batch_compare
        beq .records
        addq.w #1,(6,a2)
.records:
        lea (s60_batch_records,pc),a0
        lea (s60_batch_expected_records,pc),a1
        move.w #3*S60_REC/2-1,d0
        bsr s60_batch_compare
        beq .scratch
        addq.w #1,(8,a2)
.scratch:
        move.w (s60_batch_expected_path,pc),d0
        bne .path
        lea ($5d90-S60_DATA,a4),a0
        lea (s60_batch_expected_scratch,pc),a1
        moveq #88,d0
        bsr s60_batch_compare
        beq .path
        addq.w #1,(10,a2)
.path:  move.w (s60_batch_path,pc),d0
        cmp.w (s60_batch_expected_path,pc),d0
        beq .next
        addq.w #1,(12,a2)
.next:  addq.w #1,(4,a2)
        lea (s60_batch_case,pc),a0
        addq.w #1,(a0)
        cmp.w #64,(a0)
        bne .case
        lea (s60_batch_saved_list,pc),a0
        lea ($3fb2-S60_DATA,a4),a1
        move.w #512,d0
        bsr s60_batch_copy
        lea (s60_batch_saved_hooks,pc),a0
        lea ($278a-S60_DATA,a4),a1
        moveq #3,d0
        bsr s60_batch_copy
        lea (s60_batch_saved_scratch,pc),a0
        lea ($5d90-S60_DATA,a4),a1
        moveq #88,d0
        bsr s60_batch_copy
        lea (s60_batch_saved_cache,pc),a0
        lea (s60_record_cache,pc),a1
        move.w #RECORD_CACHE_SLOTS*2-1,d0
        bsr s60_batch_copy
        lea (s60_motion_table,pc),a0
        move.l (s60_batch_saved_table,pc),(a0)
        lea (s60_running,pc),a0
        move.w (s60_batch_saved_modes,pc),(a0)
        lea (s60_rendering,pc),a0
        move.w (s60_batch_saved_modes+2,pc),(a0)
        move.l (s60_code,pc),a0
        adda.l #$132b2,a0
        move.w (s60_batch_saved_mesh,pc),(a0)
        bsr s60_batch_flush
        lea (s60_batch_results,pc),a0
        clr.w (14,a0)
.done:  movem.l (sp)+,d0-d7/a0-a6
        rts
s60_batch_copy:
        move.w (a0)+,(a1)+
        dbf d0,s60_batch_copy
        rts
s60_batch_compare:
        cmpm.w (a0)+,(a1)+
        bne .done
        dbf d0,s60_batch_compare
.done:  rts
s60_batch_flush:
        movem.l d0-d1/a0-a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
s60_batch_native:
        move.w ($43b2-S60_DATA,a4),-(sp)
        pea ($3fb2-S60_DATA,a4)
        move.l ($5d90-S60_DATA,a4),-(sp)
        S60_CALL $12aa4
        lea (10,sp),sp
        rts

s60_batch_seed:
        lea (s60_batch_saved_scratch,pc),a0
        lea ($5d90-S60_DATA,a4),a1
        moveq #88,d0
        bsr s60_batch_copy
        lea (s60_running,pc),a0
        move.w #1,(a0)
        lea (s60_rendering,pc),a0
        clr.w (a0)
        clr.l ($278a-S60_DATA,a4)
        clr.l ($278e-S60_DATA,a4)
        lea (s60_record_cache,pc),a0
        moveq #RECORD_CACHE_SLOTS-1,d0
.cache: clr.l (a0)+
        dbf d0,.cache
        lea (s60_batch_actors,pc),a0
        move.w #373,d0
.zero:  clr.w (a0)+
        dbf d0,.zero
        lea (s60_batch_records,pc),a0
        move.w #3*S60_REC/2-1,d0
.recs:  clr.w (a0)+
        dbf d0,.recs
        move.w (s60_batch_case,pc),d5
        lea (s60_batch_actors,pc),a3
        lea (s60_batch_records,pc),a2
        lea (s60_batch_frames,pc),a1
        moveq #1,d6
.actor: move.l a3,(a2)
        btst #5,d5
        beq .clock
        move.b #2,(136,a2)
        move.l (s60_ticks,pc),(132,a2)
.clock: move.l #100,(4,a3)
        move.l ($5d90-S60_DATA,a4),a0
        move.l (2,a0),a0
        move.l (8,a0),d0
        add.l #100,d0
        move.l d0,(8,a3)
        move.l (12,a0),d0
        add.l #2000,d0
        move.l d0,(12,a3)
        move.l (16,a0),(16,a3)
        move.l a1,(30,a3)
        move.b #3,(86,a3)
        btst #4,d5
        beq .after
        bset #1,(a3)
.after: move.l (s60_code,pc),d0
        add.l #$42b0,d0
        move.l d0,(26,a3)
        adda.w #110,a3
        adda.w #S60_REC,a2
        adda.w #256,a1
        dbf d6,.actor
        lea ($3fb2-S60_DATA,a4),a0
        lea (s60_batch_actors,pc),a1
        move.w #255,d0
.list:  move.l a1,(a0)+
        dbf d0,.list
        lea ($3fb2-S60_DATA,a4),a0
        lea (s60_batch_actors,pc),a1
        lea (110,a1),a2
        move.l a2,(4,a0)
        move.w #2,($43b2-S60_DATA,a4)
        lea (s60_batch_expected_path,pc),a3
        move.w #1,(a3)
        and.w #15,d5
        beq .null
        cmp.w #1,d5
        beq .done
        cmp.w #2,d5
        beq .unknown_first
        cmp.w #3,d5
        beq .unknown_last
        cmp.w #4,d5
        beq .visible_first
        cmp.w #5,d5
        beq .visible_last
        cmp.w #6,d5
        beq .pre
        cmp.w #7,d5
        beq .post
        cmp.w #8,d5
        beq .empty
        cmp.w #9,d5
        beq .view_only
        cmp.w #10,d5
        beq .full
        cmp.w #11,d5
        beq .inactive
        cmp.w #12,d5
        beq .rendering
        cmp.w #13,d5
        beq .duplicate
        cmp.w #14,d5
        beq .single
        move.w #3,($43b2-S60_DATA,a4)
        move.l ($5d90-S60_DATA,a4),a1
        move.l (2,a1),(8,a0)
        bra .done
.null:  clr.l (26,a1)
        clr.l (26,a2)
        bra .done
.unknown_first:
        lea (s60_batch_consumer,pc),a2
        move.l a2,(26,a1)
        bra .fallback
.unknown_last:
        lea (s60_batch_consumer,pc),a1
        move.l a1,(26,a2)
        bra .fallback
.visible_first:
        bset #3,(a1)
        bra .fallback
.visible_last:
        bset #3,(a2)
        bra .fallback
.pre:   lea (s60_batch_hook,pc),a1
        move.l a1,($278a-S60_DATA,a4)
        bra .fallback
.post:  lea (s60_batch_hook,pc),a1
        move.l a1,($278e-S60_DATA,a4)
        bra .fallback
.empty: clr.w ($43b2-S60_DATA,a4)
        bra .fallback
.view_only:
        move.w #1,($43b2-S60_DATA,a4)
        move.l ($5d90-S60_DATA,a4),a1
        move.l (2,a1),(a0)
        bra .done
.full:  move.w #256,($43b2-S60_DATA,a4)
        move.l ($5d90-S60_DATA,a4),a1
        move.l (2,a1),(1020,a0)
        bra .done
.inactive:
        lea (s60_running,pc),a1
        clr.w (a1)
        bra .fallback
.rendering:
        lea (s60_rendering,pc),a1
        move.w #1,(a1)
        bra .fallback
.duplicate:
        move.l a1,(4,a0)
        bra .done
.single:
        move.w #1,($43b2-S60_DATA,a4)
        bra .done
.fallback:
        clr.w (a3)
.done:  rts
s60_batch_consumer:
        move.l a0,-(sp)
        move.l (8,sp),a0
        move.l ($5da4-S60_DATA,a4),(60,a0)
        move.l ($5da8-S60_DATA,a4),(64,a0)
        move.w (12,sp),(68,a0)
        lea (s60_batch_observed,pc),a0
        addq.l #1,(a0)
        move.l (sp)+,a0
        rts
s60_batch_hook:
        move.l a0,-(sp)
        lea (s60_batch_observed,pc),a0
        addq.l #1,(4,a0)
        move.l ($5dc2-S60_DATA,a4),(8,a0)
        move.l ($5dc6-S60_DATA,a4),(12,a0)
        move.l (sp)+,a0
        rts
        ENDC
        ENDC
