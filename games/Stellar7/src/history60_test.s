; Deterministic device samples indexed by elapsed active fields, never ticks.
; CUSTOM3 must be off: exercise the real gameplay input readers.
        IFD VERIFY
        IFD HISTORY_TEST
s60_history_test_results:
        dc.b 'HT60'
        dc.w 200,24
        ds.b 200*24 ; tick, selected field, consumption field, joy, fire, presentation field
s60_history_test_presented: dc.l 0
s60_test_history_sample:
        movem.l d0-d1/a0-a1,-(sp)
        move.l (a0),d1
        clr.l (4,a0)
        move.b #$ff,(8,a0)
        lea (12,a0),a1
        moveq #31,d0
.clear: clr.l (a1)+
        dbf d0,.clear
        cmp.l #20,d1
        bcs .done
        cmp.l #40,d1
        bcc .right
        move.b #1,(12+$4e,a0)
        bra .done
.right: cmp.l #60,d1
        bcs .done
        cmp.l #80,d1
        bcc .joy
        move.b #1,(12+$4f,a0)
        bra .done
.joy:   cmp.l #100,d1
        bcs .done
        cmp.l #120,d1
        bcc .fire
        move.w #1,(6,a0)
        bra .done
.fire:  cmp.l #140,d1
        bcs .done
        cmp.l #160,d1
        bcc .done
        move.b #1,(12+$40,a0)
.done:  movem.l (sp)+,d0-d1/a0-a1
        rts
s60_test_history_consumed:
        movem.l d0-d2/a0-a1,-(sp)
        move.l (s60_ticks,pc),d2
        cmp.l #200,d2
        bcc .done
        move.w d2,d0
        mulu.w #24,d0
        lea (s60_history_test_results+8,pc),a1
        adda.l d0,a1
        addq.l #1,d2
        move.l d2,(a1)+
        move.l (s60_history_selected,pc),(a1)+
        move.l (s60_history_produced,pc),(a1)+
        move.l a1,-(sp)
        S60_CALL $22746
        move.l (sp)+,a1
        move.l d0,(a1)+
        move.l a1,-(sp)
        move.w #$40,-(sp)
        S60_CALL $22730
        addq.l #2,sp
        move.l (sp)+,a1
        move.l d0,(a1)
.done:  movem.l (sp)+,d0-d2/a0-a1
        rts
s60_test_history_presented:
        movem.l d0-d2/a0-a1,-(sp)
        move.l (s60_history_test_presented,pc),d1
        move.l (s60_ticks,pc),d2
        cmp.l #200,d2
        bls .limit
        move.l #200,d2
.limit: cmp.l d2,d1
        bcc .done
        move.w d1,d0
        mulu.w #24,d0
        lea (s60_history_test_results+8+20,pc),a0
        adda.l d0,a0
        move.l (s60_history_produced,pc),d0
.loop:  move.l d0,(a0)
        adda.w #24,a0
        addq.l #1,d1
        cmp.l d2,d1
        bcs .loop
        lea (s60_history_test_presented,pc),a0
        move.l d1,(a0)
.done:  movem.l (sp)+,d0-d2/a0-a1
        rts
        ENDC
        ENDC

        IFD VERIFY
        IFD HISTORY_QUEUE_TEST
; Private test uses the native accepted-press tail after CIA decoding. It runs
; with interrupts disabled, restores all native queue bytes and private stamps,
; and never injects a gameplay command. Tests LIFO, future entries, capacity,
; overflow, modal ownership and historical held-key selection.
s60_history_queue_results:
        dc.b 'HQ60'
        dc.l 0,0,0 ; completed, failures, assertions
s60_history_queue_saved: ds.b 34+128+128+4+4+4+144
s60_test_history_queue:
        movem.l d0-d7/a0-a6,-(sp)
        lea (s60_history_queue_saved,pc),a1
        lea ($6704-S60_DATA,a4),a0
        move.w #34+128-1,d0
.save:  move.b (a0)+,(a1)+
        dbf d0,.save
        lea (s60_history_stamps,pc),a0
        moveq #31,d0
.stamps: move.l (a0)+,(a1)+
        dbf d0,.stamps
        move.l (s60_history_produced,pc),(a1)+
        move.l (s60_history_selected,pc),(a1)+
        move.l (s60_history_queue_drops,pc),(a1)+
        lea (s60_history_current,pc),a0
        moveq #35,d0
.sample: move.l (a0)+,(a1)+
        dbf d0,.sample
        lea (s60_history_produced,pc),a5
        lea (s60_history_selected,pc),a6
        clr.w ($6704-S60_DATA,a4)
        move.l #10,(a5)
        move.l #10,(a6)
        moveq #1,d0
        bsr s60_test_history_enqueue
        moveq #0,d4
        bsr .pop
        move.l #11,(a6)
        moveq #2,d0
        bsr s60_test_history_enqueue
        moveq #3,d0
        bsr s60_test_history_enqueue
        moveq #3,d4
        bsr .pop
        moveq #2,d4
        bsr .pop
        moveq #1,d4
        bsr .pop
        moveq #0,d4
        bsr .pop
        move.l #10,(a5)
        moveq #5,d0
        bsr s60_test_history_enqueue
        move.l #20,(a5)
        moveq #4,d0
        bsr s60_test_history_enqueue
        moveq #5,d4
        bsr .pop
        moveq #0,d4
        bsr .pop
        move.l #21,(a6)
        moveq #4,d4
        bsr .pop
        move.l #30,(a5)
        move.l #31,(a6)
        moveq #1,d5
.fill:  move.l d5,d0
        bsr s60_test_history_enqueue
        addq.w #1,d5
        cmp.w #34,d5
        bcs .fill
        move.l (s60_history_queue_drops,pc),d0
        sub.l (s60_history_queue_saved+34+128+128+8,pc),d0
        cmp.l #1,d0
        bsr s60_test_history_check
        moveq #32,d4
.drain: bsr .pop
        subq.w #1,d4
        bne .drain
        bsr .pop
        ; A modal sees the native queue immediately, irrespective of tick time.
        move.l #40,(a5)
        clr.l (a6)
        moveq #9,d0
        bsr s60_test_history_enqueue
        lea (s60_modal_depth,pc),a0
        move.w #1,(a0)
        moveq #9,d4
        bsr .pop
        lea (s60_modal_depth,pc),a0
        clr.w (a0)
        ; Held-key API: past gameplay sample and live modal state are separate.
        clr.b ($6766-S60_DATA,a4)
        lea (s60_history_current+12+$40,pc),a0
        move.b #1,(a0)
        move.w #$40,-(sp)
        bsr s60_history_key
        addq.w #2,sp
        cmp.l #1,d0
        bsr s60_test_history_check
        lea (s60_modal_depth,pc),a0
        move.w #1,(a0)
        move.w #$40,-(sp)
        bsr s60_history_key
        addq.w #2,sp
        tst.l d0
        bsr s60_test_history_check
        lea (s60_modal_depth,pc),a0
        clr.w (a0)
        bsr s60_test_history_decode
        bsr s60_test_history_joystick
        bsr s60_test_history_button_cases
        lea (s60_history_queue_saved,pc),a1
        lea ($6704-S60_DATA,a4),a0
        move.w #34+128-1,d0
.restore: move.b (a1)+,(a0)+
        dbf d0,.restore
        lea (s60_history_stamps,pc),a0
        moveq #31,d0
.rstamps: move.l (a1)+,(a0)+
        dbf d0,.rstamps
        move.l (a1)+,(a5)
        move.l (a1)+,(a6)
        lea (s60_history_queue_drops,pc),a0
        move.l (a1)+,(a0)
        lea (s60_history_current,pc),a0
        moveq #35,d0
.rsample: move.l (a1)+,(a0)+
        dbf d0,.rsample
        lea (s60_history_queue_results+4,pc),a0
        addq.l #1,(a0)
        movem.l (sp)+,d0-d7/a0-a6
        rts
.pop:   move.l a4,-(sp)
        suba.l a4,a4 ; native queue API does not require caller A4
        bsr s60_history_pop
        move.l (sp)+,a4
        cmp.l d4,d0
s60_test_history_check:
        beq .pass
        move.l a0,-(sp)
        lea (s60_history_queue_results+8,pc),a0
        addq.l #1,(a0)
        move.l (sp)+,a0
.pass:  move.l a0,-(sp)
        lea (s60_history_queue_results+12,pc),a0
        addq.l #1,(a0)
        move.l (sp)+,a0
        rts
s60_test_history_enqueue:
        ; Native interrupt epilogue expects these saved registers below its return.
        movem.l d2/d6-d7/a4,-(sp)
        move.l d0,d7
        move.l (s60_code,pc),-(sp)
        add.l #$194f4,(sp)
        rts
        ENDC
        ENDC

        IFD VERIFY
        IFD HISTORY_QUEUE_TEST
s60_test_history_joy_keys: dc.b $4e,$2f,$4f,$2d,$4d,$1e,$4c,$3e,$3d,$3f,$1d,$1f
        EVEN
s60_test_history_joystick:
        move.w ($1e76-S60_DATA,a4),-(sp)
        move.w #1,($1e76-S60_DATA,a4)
        moveq #0,d5
.case:  lea ($6726-S60_DATA,a4),a0
        lea (s60_history_current+12,pc),a1
        moveq #31,d0
.clear: clr.l (a0)+
        clr.l (a1)+
        dbf d0,.clear
        lea (s60_history_current+6,pc),a0
        move.w $dff00c,(a0)
        cmp.w #12,d5
        bcc .all
        lea (s60_test_history_joy_keys,pc),a0
        moveq #0,d0
        move.b (0,a0,d5.w),d0
        lea ($6726-S60_DATA,a4),a0
        move.b #1,(0,a0,d0.w)
        lea (s60_history_current+12,pc),a0
        move.b #1,(0,a0,d0.w)
        bra .compare
.all:   cmp.w #12,d5
        bne .compare
        lea ($6726-S60_DATA,a4),a0
        lea (s60_history_current+12,pc),a1
        moveq #31,d0
.ones:  move.l #$01010101,(a0)+
        move.l #$01010101,(a1)+
        dbf d0,.ones
.compare:
        move.l a4,-(sp)
        suba.l a4,a4 ; native joystick API likewise uses absolute globals
        bsr s60_history_joy_native
        move.l d0,d4
        bsr s60_history_joy
        move.l (sp)+,a4
        cmp.l d4,d0
        bsr s60_test_history_check
        addq.w #1,d5
        cmp.w #14,d5
        bcs .case
        ; All sixteen electrical direction combinations against the native
        ; port decoder. A private word exercises both XOR pairs, not hardware.
        moveq #0,d5
.raw:   move.w d5,d0
        and.w #12,d0
        lsl.w #6,d0
        move.w d5,d1
        and.w #3,d1
        or.w d1,d0
        lea (s60_history_current+6,pc),a0
        move.w d0,(a0)
        move.l a0,-(sp)
        S60_CALL $1d20a
        addq.w #4,sp
        and.l #255,d0
        move.l d0,d4
        bsr s60_history_joy
        cmp.l d4,d0
        bsr s60_test_history_check
        addq.w #1,d5
        cmp.w #16,d5
        bcs .raw
        move.w (sp)+,($1e76-S60_DATA,a4)
        rts
        ENDC
        ENDC

        IFD VERIFY
        IFD HISTORY_QUEUE_TEST
s60_test_history_decode:
        moveq #0,d5
.case:  lea (s60_history_current+12+$60,pc),a0
        moveq #0,d0
        btst #0,d5
        sne d0
        and.b #1,d0
        move.b d0,(a0)+
        moveq #0,d0
        btst #1,d5
        sne d0
        and.b #1,d0
        move.b d0,(a0)+
        moveq #0,d0
        btst #2,d5
        sne d0
        and.b #1,d0
        move.b d0,(a0)
        move.l #10,(a5)
        move.l #11,(a6)
        moveq #$20,d0
        bsr s60_test_history_enqueue
        moveq #0,d4
        lea ($29d4+$20-S60_DATA,a4),a0
        tst.w d5
        beq .table
        adda.w #128,a0
.table: move.b (a0),d4
        S60_CALL $195ee
        and.l #255,d0
        cmp.l d4,d0
        bsr s60_test_history_check
        addq.w #1,d5
        cmp.w #8,d5
        bcs .case
        ; Shutdown/inactive input returns to the native queue immediately.
        move.l #40,(a5)
        clr.l (a6)
        moveq #7,d0
        bsr s60_test_history_enqueue
        lea (s60_running,pc),a0
        clr.w (a0)
        bsr s60_history_pop
        cmp.l #7,d0
        bsr s60_test_history_check
        lea (s60_running,pc),a0
        move.w #1,(a0)
        rts
        ENDC
        ENDC

        IFD VERIFY
        IFD HISTORY_QUEUE_TEST
s60_test_history_button_cases:
        moveq #0,d5
.case:  move.w d5,d0
        lsl.w #6,d0
        not.b d0
        lea (s60_history_current+8,pc),a0
        move.b d0,(a0)
        moveq #0,d6
.button:
        move.l d5,d4
        cmp.w #2,d6
        beq .first
        lsr.w #1,d4 ; native arguments 0/1 select CIA bit 7
.first: and.l #1,d4
        move.w d6,-(sp)
        S60_CALL $1d2e4
        addq.w #2,sp
        and.l #$ffff,d0
        cmp.l d4,d0
        bsr s60_test_history_check
        addq.w #1,d6
        cmp.w #3,d6
        bcs .button
        addq.w #1,d5
        cmp.w #4,d5
        bcs .case
        rts
        ENDC
        ENDC
