        IFD VERIFY
        IFD PROJECT_TEST
        IFEQ PROJECT_SKIP
        FAIL "PROJECT_TEST requires PROJECT_SKIP=1"
        ENDC
; Test native geometry, stopping at the callback boundary. The unknown callback
; consumer runs there on both paths. Mesh animation remains covered by real runs.
s60_project_test_results: dc.b 'J762'
        dc.w 0,0,0,$ffff ; cases, failures, busy, first failing case
s60_project_test_view: dc.l 0
s60_project_test_mode: dc.w 0
s60_project_test_count: dc.w 0
s60_project_test_list: ds.l 256
s60_project_test_work: ds.b 330
s60_project_test_expected: ds.b 330
s60_project_test_saved: ds.b 170
s60_project_test_final: ds.b 170
s60_project_test_flush:
        movem.l d0-d1/a0-a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
s60_test_project:
        movem.l d0-d7/a0-a6,-(sp)
        move.w (s60_project_test_results+4,pc),d0
        bne .done
        move.w (s60_project_test_results+8,pc),d0
        bne .done
        move.l (s60_ticks,pc),d0
        cmp.l #PROJECT_TEST,d0
        bne .done
        lea (s60_project_test_results,pc),a1
        move.w #1,(8,a1)
        lea (s60_project_test_view,pc),a1
        move.l a0,(a1)
        move.w (s60_running,pc),-(sp)
        move.w (s60_rendering,pc),-(sp)
        lea ($5d98-S60_DATA,a4),a0
        lea (s60_project_test_saved,pc),a1
        bsr .copy_scratch
        move.l (s60_code,pc),a0
        adda.l #$12bfc,a0
        cmp.l #$202b001a,(a0)
        bne .bad
        move.w #$4e75,(a0)
        bsr s60_project_test_flush
        moveq #0,d5
.case:
        lea (s60_project_test_mode,pc),a0
        clr.w (a0)
        bsr .reset
        bsr .run
        lea (s60_project_test_work,pc),a0
        lea (s60_project_test_expected,pc),a1
        move.w #164,d0
.save_actor: move.w (a0)+,(a1)+
        dbf d0,.save_actor
        lea ($5d98-S60_DATA,a4),a0
        lea (s60_project_test_final,pc),a1
        bsr .copy_scratch
        lea (s60_project_test_mode,pc),a0
        move.w #1,(a0)
        bsr .reset
        bsr .run
        lea (s60_project_test_work,pc),a0
        lea (s60_project_test_expected,pc),a1
        move.w #164,d0
.actor: cmpm.w (a0)+,(a1)+
        bne .error
        dbf d0,.actor
        lea ($5d98-S60_DATA,a4),a0
        lea (s60_project_test_final,pc),a1
        moveq #84,d0
.scratch: cmpm.w (a0)+,(a1)+
        bne .error
        dbf d0,.scratch
        bra .next
.error: lea (s60_project_test_results,pc),a0
        addq.w #1,(6,a0)
        cmp.w #$ffff,(10,a0)
        bne .next
        move.w d5,(10,a0)
.next:  lea (s60_project_test_results,pc),a0
        addq.w #1,(4,a0)
        addq.w #1,d5
        cmp.w #240,d5
        bne .case
        lea (s60_project_test_saved,pc),a0
        lea ($5d98-S60_DATA,a4),a1
        bsr .copy_scratch
        move.l (s60_code,pc),a0
        adda.l #$12bfc,a0
        move.w #$202b,(a0)
        bsr s60_project_test_flush
        lea (s60_rendering,pc),a0
        move.w (sp)+,(a0)
        lea (s60_running,pc),a0
        move.w (sp)+,(a0)
        lea (s60_project_test_results,pc),a0
        clr.w (8,a0)
.done:  movem.l (sp)+,d0-d7/a0-a6
        rts
.bad:   move.l (_resload,pc),a2
        bra s60_bad
.copy_scratch:
        moveq #84,d0
.copy:  move.w (a0)+,(a1)+
        dbf d0,.copy
        rts
.reset:
        lea (s60_project_test_saved,pc),a0
        lea ($5d98-S60_DATA,a4),a1
        bsr .copy_scratch
        move.w d5,d0
        and.w #1,d0
        lea (s60_running,pc),a0
        move.w d0,(a0)
        move.w d5,d0
        lsr.w #1,d0
        and.w #1,d0
        lea (s60_rendering,pc),a0
        move.w d0,(a0)
        moveq #0,d0
        move.w d5,d0
        lsr.w #4,d0
        divu #3,d0
        lea (s60_project_test_count,pc),a0
        move.w d0,(a0) ; counts 0/1/2/3/256, exercising the full list stride
        cmp.w #4,(a0)
        bne .count_ready
        move.w #256,(a0)
.count_ready:
        swap d0
        move.w d0,d3 ; callback 0 none, 1 animation, 2 scratch consumer
        lea (s60_project_test_work,pc),a0
        move.w #164,d0
.clear: clr.w (a0)+
        dbf d0,.clear
        lea (s60_project_test_work,pc),a3
        lea (s60_project_test_list,pc),a2
        moveq #0,d2
.seed:  move.l a3,(a2)+
        btst #2,d5
        beq .no_visibility
        move.b #8,(a3)
.no_visibility:
        move.l #100,(4,a3)
        move.l ($5dc2-S60_DATA,a4),d0
        add.l #100,d0
        add.l d2,d0
        move.l d0,(8,a3)
        move.l ($5dc6-S60_DATA,a4),d0
        add.l #2000,d0
        add.l d2,d0
        move.l d0,(12,a3)
        move.l ($5dca-S60_DATA,a4),(16,a3)
        tst.w d3
        beq .seed_next
        move.l (s60_code,pc),d0
        add.l #$42b0,d0
        cmp.w #1,d3
        beq .callback
        lea (s60_project_test_consumer,pc),a0
        move.l a0,d0
.callback: move.l d0,(26,a3)
.seed_next:
        adda.w #110,a3
        addq.w #1,d2
        cmp.w #3,d2
        bne .seed
        lea (s60_project_test_work,pc),a3
        moveq #0,d1
.fill_list:
        move.l a3,(a2)+
        adda.w #110,a3
        addq.w #1,d1
        cmp.w #3,d1
        bne .fill_next
        lea (s60_project_test_work,pc),a3
        moveq #0,d1
.fill_next:
        addq.w #1,d2
        cmp.w #256,d2
        bne .fill_list
        btst #3,d5
        beq .ready
        move.w (s60_project_test_count,pc),d0
        beq .ready
        subq.w #1,d0
        lsl.w #2,d0
        lea (s60_project_test_list,pc),a0
        move.l (s60_project_test_view,pc),a1
        move.l (2,a1),(a0,d0.w)
.ready: rts
.run:
        moveq #0,d6
        move.w (s60_project_test_count,pc),d7
        lea (s60_project_test_list,pc),a2
.loop:  cmp.w d7,d6
        bge .return
        move.l (a2),a3
        move.l (s60_project_test_view,pc),a0
        cmp.l (2,a0),a3
        beq .advance
        move.w (s60_project_test_mode,pc),d0
        beq .native
        bsr s60_project_actor
        bra .consume
.native: bsr s60_project_actor_native
.consume:
        ; Rendering and inactive-game paths need intermediate geometry even
        ; without callbacks. Model a consumer at every such actor boundary.
        move.w (s60_running,pc),d0
        beq .consumer
        move.w (s60_rendering,pc),d0
        bne .consumer
        lea (s60_project_test_consumer,pc),a0
        cmp.l (26,a3),a0
        bne .advance
.consumer: bsr s60_project_test_consumer
.advance:
        addq.w #1,d6
        addq.l #4,a2
        bra .loop
.return: rts
s60_project_test_consumer:
        move.l ($5da4-S60_DATA,a4),(84,a3)
        move.l ($5da8-S60_DATA,a4),(88,a3)
        rts
        ENDC
        ENDC
