; Field-stamped input history. Producer is the existing game VBL callback tail;
; it reads native RAM only, after the original clock/music work. No OS calls.
; Record: clock.l, pad[16], keys[128], keyboard producer.w, padding.w (152 bytes).
; A single producer publishes head only after a whole record. The consumer owns
; tail. A full ring never overwrites unread history: recovery is explicit.
TI_RECORD = 152
TI_MASK = 63

timing_record_input:
        movem.l d0-d3/a0-a2,-(sp)
        move.w  ccr,-(sp)
        tst.w   timing_active(pc)
        beq.w   .done
        moveq   #0,d0
        move.w  timing_input_head(pc),d0
        move.w  d0,d1
        addq.w  #1,d1
        andi.w  #TI_MASK,d1
        cmp.w   timing_input_tail(pc),d1
        beq.s   .full
        mulu.w  #TI_RECORD,d0
        lea     timing_input_ring(pc),a0
        adda.l  d0,a0
        move.l  timing_data(pc),a2
        move.l  $7f02(a2),(a0)+
        lea     $7e06(a2),a1
        moveq   #14,d2
.pad:
        move.b  (a1)+,(a0)+
        dbf     d2,.pad
        clr.b   (a0)+
        ; Native read clears these event latches. Sampling now transfers their
        ; ownership to the history; the consumer must carry them to its tick.
        clr.b   $7e0c(a2)
        clr.b   $7e0d(a2)
        lea     $7f58(a2),a1
        moveq   #31,d2
.keys:
        move.l  (a1)+,(a0)+
        dbf     d2,.keys
        move.w  $805e(a2),(a0)+
        clr.w   (a0)+
        lea     timing_input_head(pc),a0
        move.w  d1,(a0)
        bra.s   .done
.full:
        lea     timing_input_overflows(pc),a0
        addq.l  #1,(a0)
        lea     timing_input_lost(pc),a0
        move.w  #1,(a0)
.done:
        move.w  (sp)+,ccr
        movem.l (sp)+,d0-d3/a0-a2
        lea     $dff000,a0           ; displaced VBL tail instruction
        rts

; Native input and preview use the immutable sample selected by the scheduler.
; Modal input reads go through the original device functions when replay is off.
timing_pad_read:
        tst.w   timing_replay(pc)
        beq.s   .native
        lea     timing_sample_pad(pc),a0
        move.l  6(sp),a1
        moveq   #14,d0
.copy:
        move.b  (a0)+,(a1)+
        dbf     d0,.copy
        rts
.native:
        move.l  timing_game(pc),-(sp)
        addi.l  #$33dfc,(sp)
        rts

timing_keys_read:
        tst.w   timing_replay(pc)
        beq.s   .native
        lea     timing_sample_keys(pc),a0
        move.l  4(sp),a1
        moveq   #31,d0
.copy:
        move.l  (a0)+,(a1)+
        dbf     d0,.copy
        rts
.native:
        move.l  timing_game(pc),-(sp)
        addi.l  #$34376,(sp)
        rts

; Stop ordinary command draining at the producer cursor captured for this field.
; Commands remain in the native FIFO; modal readers retain their native path.
timing_key_command:
        tst.w   timing_replay(pc)
        beq.s   .native
        move.w  94(a4),d0
        cmp.w   timing_sample_producer(pc),d0
        bne.s   .native
        moveq   #-1,d0
        rts
.native:
        move.l  timing_game(pc),-(sp)
        addi.l  #$34318,(sp)
        rts
        cnop    0,4
timing_data: dc.l 0
timing_replay: dc.w 0
timing_input_head: dc.w 0
timing_input_tail: dc.w 0
timing_input_lost: dc.w 0
timing_input_overflows: dc.l 0
timing_sample_clock: dc.l 0
timing_sample_pad: dcb.b 16,0
timing_sample_keys: dcb.b 128,0
timing_sample_producer: dc.w 0
        cnop    0,4
timing_input_ring: dcb.b TI_RECORD*64,0

; Consume one completely published field. Interrupt producer cannot overwrite
; this slot until tail is advanced after copying all 152 bytes.
timing_take_sample:
        movem.l d1-d2/a0-a1,-(sp)
        moveq   #0,d0
        move.w  timing_input_tail(pc),d0
        cmp.w   timing_input_head(pc),d0
        beq.s   .empty
        move.w  d0,d2
        mulu.w  #TI_RECORD,d0
        lea     timing_input_ring(pc),a0
        adda.l  d0,a0
        lea     timing_sample_clock(pc),a1
        moveq   #37,d1
.copy:
        move.l  (a0)+,(a1)+
        dbf     d1,.copy
        addq.w  #1,d2
        andi.w  #TI_MASK,d2
        lea     timing_input_tail(pc),a0
        move.w  d2,(a0)
        moveq   #1,d0
        bra.s   .done
.empty:
        moveq   #0,d0
.done:
        movem.l (sp)+,d1-d2/a0-a1
        rts

; Preserve every sampled pad transition until the next world tick. Eight slots
; cover the six fields of a 60 Hz tick; overflow is a counted recovery condition.
timing_queue_pad:
        movem.l d0/a0-a1,-(sp)
        moveq   #0,d0
        move.w  timing_pad_count(pc),d0
        cmpi.w  #8,d0
        bcc.s   .full
        lsl.w   #4,d0
        lea     timing_pad_pending(pc),a0
        adda.w  d0,a0
        lea     timing_sample_pad(pc),a1
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        lea     timing_pad_count(pc),a0
        addq.w  #1,(a0)
        lea     timing_pad_pulses(pc),a0
        move.w  timing_sample_pad+6(pc),d0
        or.w    d0,(a0)
        bra.s   .done
.full:
        lea     timing_input_overflows(pc),a0
        addq.l  #1,(a0)
        lea     timing_input_lost(pc),a0
        move.w  #1,(a0)
.done:
        movem.l (sp)+,d0/a0-a1
        rts

; Run only native edge dispatch for each saved transition, without repeating
; steering ramps, throttle changes or held-fire work. Full input runs once after.
timing_pad_edges:
        movem.l d2-d3/a2/a6,-(sp)
        moveq   #0,d2
        move.w  timing_pad_count(pc),d2
        lea     timing_pad_pending(pc),a2
.loop:
        tst.w   d2
        beq.s   .done
        lea     18122(a4),a0
        lea     18138(a4),a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        lea     18122(a4),a0
        move.l  (a2)+,(a0)+
        move.l  (a2)+,(a0)+
        move.l  (a2)+,(a0)+
        move.l  (a2)+,(a0)+
        move.l  timing_game(pc),a6
        jsr     $19278(a6)
        tst.w   d0
        beq.s   .next
        move.w  #5,-32628(a4)
        bra.s   .done
.next:
        tst.w   timing_abort(pc)
        bne.s   .done
        subq.w  #1,d2
        bra.s   .loop
.done:
        lea     timing_pad_count(pc),a0
        clr.w   (a0)
        lea     timing_sample_pad+6(pc),a0
        move.w  timing_pad_pulses(pc),d0
        or.w    d0,(a0)
        lea     timing_pad_pulses(pc),a0
        clr.w   (a0)
        movem.l (sp)+,d2-d3/a2/a6
        rts
        cnop    0,4
timing_pad_count: dc.w 0
timing_pad_pulses: dc.w 0
timing_pad_pending: dcb.b 128,0
timing_input_recoveries: dc.l 0

timing_input_dropped_fields: dc.l 0
