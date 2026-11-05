; English ship/title and asteroid-credit world. Native E:02a8 runs at 10 Hz;
; rendering uses the same bounded display-time prediction and queue as flight.
; A separate flag avoids enabling flight input/player/control adapters.
intro_start:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w   timing_rebase
        lea     intro_active(pc),a0
        move.w  #1,(a0)
        bsr.w   timing_scene_snapshot
        ifne FRAME_STATS
        bsr.w   frame_stats_intro_begin
        endif
        movem.l (sp)+,d0-d7/a0-a6
        rts

intro_stop:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w   timing_scene_end
        bsr.w   release_buffer_wait
        lea     intro_active(pc),a0
        clr.w   (a0)
        bsr.w   timing_rebase
        movem.l (sp)+,d0-d7/a0-a6
        rts

; D0 due ticks (0..4); the common clock bounds/discards excessive stall debt.
intro_due:
        movem.l d1-d3/a0,-(sp)
        FSTAT   1
        ifne FRAME_STATS
        bsr.w   frame_stats_flush
        endif
        move.l  WC_A4_FIELD_CLOCK(a4),d0
        move.l  timing_hz(pc),d1
        moveq   #1,d2
        lea     timing_clock(pc),a0
        bsr.w   timing_advance
        movem.l (sp)+,d1-d3/a0
        rts

intro_world:
        movem.l d0-d7/a0-a6,-(sp)
        FSTAT   2
        move.l  timing_game(pc),a6
        jsr     WC_NATIVE_WORLD(a6)
        move.l  timing_game(pc),a6
        jsr     $15fb4(a6)       ; background flash countdown is tick-owned
        ; Asteroid generation/cleanup also lived inside E:02e4 drawing.
        ; Rebuild native visibility first, and use the world counter for its
        ; one-in-twenty cleanup slot. New asteroids persist into the snapshot.
        tst.l   4470(a4)
        beq.s   .no_asteroids
        move.l  timing_game(pc),a6
        jsr     $2a086(a6)
        bsr.w   intro_field_world
.no_asteroids:
        bsr.w   timing_scene_tick
        lea     timing_completed(pc),a0
        addq.l  #1,(a0)
        FSTAT   3
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Shared flight/intro field maintenance, after authoritative geometry.
intro_field_world:
        tst.l   4470(a4)
        beq.s   .done
        move.w  WC_A4_DRAW_COUNT(a4),-(sp)
        move.w  WC_A4_WORLD_COUNT(a4),WC_A4_DRAW_COUNT(a4)
        move.l  timing_game(pc),a6
        jsr     WC_NATIVE_ASTEROIDS(a6)
        move.w  (sp)+,WC_A4_DRAW_COUNT(a4)
.done:
        rts

intro_asteroids_draw:
        tst.w   timing_active(pc)
        bne.s   .done
        tst.w   intro_active(pc)
        bne.s   .done
        move.l  timing_game(pc),-(sp)
        addi.l  #WC_NATIVE_ASTEROIDS,(sp)
.done:
        rts

intro_flash_draw:
        tst.w   intro_active(pc)
        bne.s   .done
        move.l  timing_game(pc),-(sp)
        addi.l  #$15fb4,(sp)
.done:
        rts

intro_draw:
        movem.l d0-d7/a0-a6,-(sp)
        FSTAT   4
        bsr.w   timing_scene_begin
        FSTAT   5
        ; Render-only attachment randomness cannot change the next world tick.
        lea     intro_game_seed(pc),a0
        move.l  -4326(a4),(a0)
        move.l  timing_render_seed(pc),-4326(a4)
        move.l  timing_game(pc),a6
        move.w  #1,-32624(a4)
        jsr     WC_NATIVE_DRAW(a6)
        FSTAT   6
        movem.l (sp)+,d0-d7/a0-a6
        rts

intro_finish:
        movem.l d0-d7/a0-a6,-(sp)
        FSTAT   7
        move.l  timing_game(pc),a6
        jsr     WC_NATIVE_FINISH(a6)
        lea     timing_render_seed(pc),a0
        move.l  -4326(a4),(a0)
        move.l  intro_game_seed(pc),-4326(a4)
        bsr.w   timing_scene_end
        FSTAT   8
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Replaces E:1fd00..1fd8e's frame-coupled loop. Native script index D2 and
; title geometry advance once per world tick. Render arguments are sampled
; between ticks without modifying D6 or the native local rotation angle.
; A5/D3/D7 and the surrounding native function's stack remain its own.
intro_title:
        bsr.w   intro_start
.loop:
        bsr.w   intro_due
        move.w  d0,d4
.ticks:
        tst.w   d4
        beq.s   .draw
        bsr.w   intro_world
        cmpi.w  #WC_SCENE_APPROACH,d2
        blt.s   .next
        cmpi.w  #WC_SCENE_DEPARTURE,d2
        bge.s   .departure
        cmpi.w  #16,d6
        ble.s   .next
        subq.w  #4,d6
        bra.s   .next
.departure:
        addq.w  #2,d6
        addq.w  #6,-2(a5)
.next:
        addq.w  #1,d2
        cmpi.w  #WC_SCENE_TITLE_UPDATES,d2
        bge.w   .exit
        subq.w  #1,d4
        bra.s   .ticks
.draw:
        bsr.w   intro_draw
        move.l  timing_game(pc),a6
        cmpi.w  #35,d2
        bge.s   .title
        move.l  -22652(a4),-(sp)
        move.w  #50,-(sp)
        pea     4438(a4)
        jsr     $13f50(a6)
        lea     10(sp),sp
.title:
        bsr.w   intro_title_sample
        cmpi.w  #WC_SCENE_APPROACH,d2
        blt.s   .finish
        cmpi.w  #WC_SCENE_DEPARTURE,d2
        bge.s   .depart_draw
        move.w  d0,-(sp)        ; projected scale, with fractional depth retained
        clr.w   -(sp)
        move.l  -22256(a4),-(sp)
        move.w  a3,-(sp)
        move.w  -4314(a4),-(sp)
        pea     4438(a4)
        jsr     $2ec98(a6)
        lea     16(sp),sp
        bra.s   .finish
.depart_draw:
        clr.w   -(sp)
        move.w  d0,-(sp)
        move.w  d1,-(sp)
        clr.w   -(sp)
        move.l  -22256(a4),-(sp)
        move.w  a3,-(sp)
        move.w  -4314(a4),-(sp)
        pea     4438(a4)
        jsr     $2d746(a6)
        lea     20(sp),sp
.finish:
        bsr.w   intro_finish
        move.l  timing_game(pc),a6
        jsr     $1898a(a6)
        tst.w   d0
        beq.w   .loop
        addq.b  #1,d7
        addq.b  #1,d3
.exit:
        bsr.w   intro_stop
        move.l  timing_game(pc),-(sp)
        addi.l  #$1fd90,(sp)
        rts

; D0/D1 = render-only projected scale/rotation angle. D2 is the next script tick.
; Include fields spent drawing, but cap preview at one tick: a slow render must
; not advance through unexecuted script phases. Never feed samples back to D6.
intro_title_sample:
        movem.l d3-d5,-(sp)
        moveq   #0,d0
        move.w  d6,d0
        move.w  -2(a5),d1
        move.l  WC_A4_FIELD_CLOCK(a4),d3
        sub.l   timing_clock(pc),d3
        cmpi.l  #6,d3
        bls.s   .elapsed
        moveq   #6,d3
.elapsed:
        mulu.w  #10,d3
        add.l   timing_clock+4(pc),d3
        move.l  timing_hz(pc),d4
        cmp.l   d4,d3
        bls.s   .bounded
        move.l  d4,d3
.bounded:
        mulu.w  d4,d0          ; retain fractional depth through projection
        cmpi.w  #WC_SCENE_APPROACH,d2
        blt.s   .project
        cmpi.w  #WC_SCENE_DEPARTURE,d2
        bge.s   .depart
        cmpi.w  #16,d6
        ble.s   .project
        mulu.w  #4,d3
        sub.l   d3,d0
        bra.s   .project
.depart:
        move.l  d3,d5
        mulu.w  #2,d3
        add.l   d3,d0
        mulu.w  #6,d5
        divu.w  d4,d5
        add.w   d5,d1
.project:
        move.l  d0,d3
        move.l  #4096,d0
        mulu.w  d4,d0
        divu.w  d3,d0
        andi.l  #$ffff,d0
.done:
        movem.l (sp)+,d3-d5
        rts

; Native credit loop keeps both the 220-field text and 320-field page tests.
intro_credits_update:
        movem.l d0-d7/a0-a6,-(sp)
        tst.w   intro_active(pc)
        bne.s   .ready
        bsr.w   intro_start
.ready:
        bsr.w   intro_due
        move.w  d0,d4
.loop:
        tst.w   d4
        beq.s   .done
        bsr.w   intro_world
        subq.w  #1,d4
        bra.s   .loop
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

intro_credits_end:
        bsr.w   intro_stop
        tst.b   d3
        beq.s   .repeat
        move.l  timing_game(pc),-(sp)
        addi.l  #$1fe4c,(sp)
        rts
.repeat:
        move.l  timing_game(pc),-(sp)
        addi.l  #$1fc8e,(sp)
        rts
        cnop 0,4
intro_active: dc.w 0
        cnop 0,4
intro_game_seed: dc.l 0
