; Field-indexed controls. Keep the native interrupt producers and key queue.
; Main-context readers select a private historical copy; modal readers stay live.
; The native 32-byte LIFO queue keeps its capacity, decoding and drop policy.
; Each accepted press carries the first field in which it can be consumed.
        IFND S60_HISTORY_COUNT
S60_HISTORY_COUNT EQU 256
        ENDC
        IFNE S60_HISTORY_COUNT&(S60_HISTORY_COUNT-1)
        FAIL "S60_HISTORY_COUNT must be a power of two"
        ENDC
        IFLT S60_HISTORY_COUNT-2
        FAIL "S60_HISTORY_COUNT must be at least two"
        ENDC
        IFGT S60_HISTORY_COUNT-256
        FAIL "S60_HISTORY_COUNT must not exceed 256"
        ENDC
S60_HISTORY_STRIDE EQU 144
s60_history_state:
        dc.b 'IH60'
s60_history_buffer: dc.l 0
s60_history_produced: dc.l 0
s60_history_cursor: dc.l 0
s60_history_fraction: dc.w 0
s60_history_capacity: dc.w S60_HISTORY_COUNT
s60_history_missing: dc.l 0
s60_history_queue_drops: dc.l 0
s60_history_selected: dc.l 0
s60_history_state_end:
s60_history_current: ds.b S60_HISTORY_STRIDE
s60_history_stamps: ds.l 32
s60_history_key_native: ds.b 12
s60_history_joy_native: ds.b 14
s60_history_pop_native: ds.b 14

s60_history_install:
        move.l (s60_code,pc),a1
        ; Validate complete displaced instructions before installing any hook.
        lea (s60_history_guards,pc),a0
.guard: move.l (a0)+,d0
        beq .allocate
        move.l a1,a3
        adda.l d0,a3
        move.l (a0)+,d0
        cmp.l (a3),d0
        bne s60_bad
        bra .guard
.allocate:
        move.l a1,a3
        adda.l #$1d2ee,a3
        cmp.w #$2079,(a3)
        bne s60_bad
        move.l (14,a1),d0
        sub.l #S60_DATA-$32f0,d0
        cmp.l (2,a3),d0
        bne s60_bad
        movem.l d7/a1-a2/a6,-(sp)
        move.l #S60_HISTORY_COUNT*S60_HISTORY_STRIDE,d0
        move.l #$10001,d1 ; MEMF_PUBLIC|MEMF_CLEAR, never an interrupt allocation
        move.l ($4).w,a6
        jsr (_LVOAllocMem,a6)
        movem.l (sp)+,d7/a1-a2/a6
        tst.l d0
        bne .allocated
        pea (s60_history_no_memory,pc)
        pea (TDREASON_FAILMSG).w
        jmp (resload_Abort,a2)
.allocated:
        lea (s60_history_buffer,pc),a0
        move.l d0,(a0)
        lea (s60_history_key_native,pc),a3
        move.l a1,a0
        adda.l #$22730,a0
        move.l (a0)+,(a3)+
        move.w (a0)+,(a3)+
        move.w #$4ef9,(a3)+
        move.l a0,(a3)
        lea (s60_history_joy_native,pc),a3
        move.l a1,a0
        adda.l #$22746,a0
        move.l (a0)+,(a3)+
        move.l (a0)+,(a3)+
        move.w #$4ef9,(a3)+
        move.l a0,(a3)
        lea (s60_history_pop_native,pc),a3
        move.l a1,a0
        adda.l #$195c8,a0
        move.l (a0)+,(a3)+
        move.l (a0)+,(a3)+
        move.w #$4ef9,(a3)+
        move.l a0,(a3)
        lea (s60_history_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_history_no_memory:
        dc.b "Not enough memory for SIM60 input history.",0
        EVEN
s60_history_guards:
        dc.l $11748,$2f0c49f9
        dc.l $11750,$52aca4a8
        dc.l $22730,$2f073e2f
        dc.l $22746,$4e55fffc
        dc.l $195c8,$2f0c49f9
        dc.l $19506,$41ece706
        dc.l $194fa,$b0416c10
        dc.l $19600,$102ce788
        dc.l $19606,$122ce786
        dc.l $1960e,$122ce787
        dc.l $1d20e,$266f0010
        dc.l 0
s60_history_patches:
        PL_START
        PL_P $11748,s60_history_field
        PL_NOP $1174e,2
        PL_P $22730,s60_history_key
        PL_P $22746,s60_history_joy
        PL_NOP $2274c,2
        PL_P $195c8,s60_history_pop
        PL_NOP $195ce,2
        PL_PS $19506,s60_history_press
        PL_NOP $1950c,2
        PL_PS $194f4,s60_history_queue_size
        PL_PS $19600,s60_history_modifier0
        PL_PS $19606,s60_history_modifier1
        PL_PS $1960e,s60_history_modifier2
        PL_PS $1d20e,s60_history_port
        PL_PS $1d2ee,s60_history_buttons
        PL_END

; Exec Disable/Enable nest correctly with the native interrupt discipline.
s60_history_lock:
        movem.l d0-d1/a0-a1/a6,-(sp)
        move.l ($4).w,a6
        jsr (_LVODisable,a6)
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts
s60_history_unlock:
        movem.l d0-d1/a0-a1/a6,-(sp)
        move.l ($4).w,a6
        jsr (_LVOEnable,a6)
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts

s60_history_reset:
        movem.l d0-d2/a0-a1,-(sp)
        bsr s60_history_lock
        lea (s60_history_produced,pc),a0
        moveq #5,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_history_capacity,pc),a0
        move.w #S60_HISTORY_COUNT,(a0)
        lea (s60_history_stamps,pc),a0
        moveq #31,d0
.stamps: clr.l (a0)+
        dbf d0,.stamps
        move.l (s60_history_buffer,pc),a0
        clr.l (a0)
        bsr s60_history_sample
        move.l ($24a8-S60_DATA,a4),(s60_last-s60_last,a2)
        IFD VERIFY
        IFD HISTORY_QUEUE_TEST
        bsr s60_test_history_queue
        ENDC
        ENDC
        bsr s60_history_unlock
        movem.l (sp)+,d0-d2/a0-a1
        rts

; The native callback changes only A4 temporarily and increments the field clock.
; Publish a complete sample before advancing that same clock. Modal fields do
; not advance the private active-field sequence, matching s60_modal_return.
s60_history_field:
        movem.l d0-d2/a0-a2/a4,-(sp)
        IFNE BLIT_IRQ_IDLE
        bsr s60_blit_idle
        ENDC
        move.l (s60_code,pc),a0
        move.l (14,a0),a4
        move.w (s60_running,pc),d0
        beq .done
        move.w (s60_modal_depth,pc),d0
        bne .done
        move.l (s60_history_produced,pc),d2
        addq.l #1,d2
        move.l d2,d0
        and.l #S60_HISTORY_COUNT-1,d0
        mulu.w #S60_HISTORY_STRIDE,d0
        move.l (s60_history_buffer,pc),a0
        adda.l d0,a0
        move.l d2,(a0)
        bsr s60_history_sample
        lea (s60_history_produced,pc),a0
        move.l d2,(a0)
.done:  addq.l #1,($24a8-S60_DATA,a4)
        movem.l (sp)+,d0-d2/a0-a2/a4
        rts
s60_history_sample:
        move.l a0,-(sp)
        move.w $dff00a,(4,a0)
        move.w $dff00c,(6,a0)
        move.b $bfe001,(8,a0)
        lea ($6726-S60_DATA,a4),a1
        lea (12,a0),a0
        moveq #31,d0
.copy: move.l (a1)+,(a0)+
        dbf d0,.copy
        move.l (sp)+,a0
        IFD VERIFY
        IFD HISTORY_TEST
        bsr s60_test_history_sample
        ENDC
        ENDC
        rts

s60_history_select:
        movem.l d0-d2/a0-a1,-(sp)
        bsr s60_history_lock
        move.l (s60_history_cursor,pc),d1
        IFD VERIFY
        IFD HISTORY_LIVE_TEST
        move.l (s60_history_produced,pc),d1
        ENDC
        ENDC
        lea (s60_history_selected,pc),a0
        move.l d1,(a0)
        move.l (s60_history_produced,pc),d0
        sub.l d1,d0
        cmp.l #S60_HISTORY_COUNT,d0
        bcc .missing
        move.l d1,d0
        and.l #S60_HISTORY_COUNT-1,d0
        mulu.w #S60_HISTORY_STRIDE,d0
        move.l (s60_history_buffer,pc),a0
        adda.l d0,a0
        lea (s60_history_current,pc),a1
        moveq #S60_HISTORY_STRIDE/4-1,d0
.copy: move.l (a0)+,(a1)+
        dbf d0,.copy
        bra .advance
.missing:
        ; Never apply present input to missing past fields, skip ticks or abort.
        ; Neutral controls recover releases; expose every affected tick.
        lea (s60_history_missing,pc),a0
        addq.l #1,(a0)
        lea (s60_history_current,pc),a0
        moveq #S60_HISTORY_STRIDE/4-1,d0
.zero: clr.l (a0)+
        dbf d0,.zero
        lea (s60_history_current,pc),a0
        move.l d1,(a0)
        move.b #$ff,(8,a0)
.advance:
        lea (s60_history_fraction,pc),a0
        move.w (a0),d0
        add.w (s60_field_hz,pc),d0
.next:  cmp.w #S60_RATE,d0
        bcs .fraction
        sub.w #S60_RATE,d0
        addq.l #1,d1
        bra .next
.fraction:
        move.w d0,(a0)
        lea (s60_history_cursor,pc),a0
        move.l d1,(a0)
        bsr s60_history_unlock
        movem.l (sp)+,d0-d2/a0-a1
        rts

; D0=1 only while world logic owns input. Rendering and all modal paths use live
; native state, including mouse coordinates/deltas managed by input.device.
s60_history_owned:
        moveq #0,d0
        move.w (s60_running,pc),d0
        beq .inactive
        move.w (s60_modal_depth,pc),d0
        bne .inactive
        move.w (s60_rendering,pc),d0
        bne .inactive
        moveq #1,d0
        rts
.inactive: moveq #0,d0
        rts
s60_history_key:
        bsr s60_history_owned
        tst.w d0
        beq s60_history_key_native
        move.l d7,-(sp)
        move.w (8,sp),d7
        lea (s60_history_current+12,pc),a0
        adda.w d7,a0
        moveq #0,d0
        move.b (a0),d0
        move.l (sp)+,d7
        rts

s60_history_joy:
        bsr s60_history_owned
        tst.w d0
        beq s60_history_joy_native
        movem.l d6-d7,-(sp)
        moveq #0,d6
        move.w (s60_history_current+6,pc),d7
        move.l (s60_code,pc),a0
        move.l (14,a0),a0
        tst.w ($1e76-S60_DATA,a0)
        beq .keys
        btst #1,d7
        beq .right
        bset #3,d6
.right: btst #9,d7
        beq .vertical
        bset #2,d6
.vertical:
        move.w d7,d0
        lsr.w #1,d0
        eor.w d7,d0
        btst #0,d0
        beq .up
        bset #1,d6
.up:    btst #8,d0
        beq .keys
        bset #0,d6
.keys:  lea (s60_history_current+12,pc),a0
        tst.b ($4e,a0)
        bne .leftkey
        tst.b ($2f,a0)
        beq .rightkey
.leftkey: bset #3,d6
.rightkey:
        tst.b ($4f,a0)
        bne .rightset
        tst.b ($2d,a0)
        beq .downkey
.rightset: bset #2,d6
.downkey:
        tst.b ($4d,a0)
        bne .downset
        tst.b ($1e,a0)
        beq .upkey
.downset: bset #1,d6
.upkey: tst.b ($4c,a0)
        bne .upset
        tst.b ($3e,a0)
        beq .diagonal
.upset: bset #0,d6
.diagonal:
        tst.b ($3d,a0)
        beq .d2
        moveq #5,d6
.d2:    tst.b ($3f,a0)
        beq .d3
        moveq #9,d6
.d3:    tst.b ($1d,a0)
        beq .d4
        moveq #6,d6
.d4:    tst.b ($1f,a0)
        beq .done
        moveq #10,d6
.done:  move.l d6,d0
        movem.l (sp)+,d6-d7
        rts

; Accepted native press: D0 is its slot, the count is already incremented.
s60_history_press:
        movem.l d1/a1,-(sp)
        move.l d0,d1
        lsl.w #2,d1
        lea (s60_history_stamps,pc),a1
        move.l (s60_history_produced,pc),(0,a1,d1.w)
        addq.l #1,(0,a1,d1.w)
        movem.l (sp)+,d1/a1
        lea ($6706-S60_DATA,a4),a0
        move.b d7,(0,a0,d0.w)
        rts
s60_history_queue_size:
        move.w ($6704-S60_DATA,a4),d0
        moveq #32,d1
        cmp.w d1,d0
        blt .done
        move.l a0,-(sp)
        lea (s60_history_queue_drops,pc),a0
        addq.l #1,(a0)
        move.l (sp)+,a0
.done:  rts

s60_history_pop:
        bsr s60_history_owned
        tst.w d0
        beq s60_history_pop_native
        movem.l d1-d3/a0-a2/a4,-(sp)
        move.l (s60_code,pc),a0
        move.l (14,a0),a4
        bsr s60_history_lock
        move.w ($6704-S60_DATA,a4),d1
        move.w d1,d3
        lea (s60_history_stamps,pc),a1
        lea ($6706-S60_DATA,a4),a0
        move.l (s60_history_selected,pc),d2
.search:
        subq.w #1,d1
        bmi .empty
        move.w d1,d0
        lsl.w #2,d0
        cmp.l (0,a1,d0.w),d2
        bcs .search
        moveq #0,d2
        move.b (0,a0,d1.w),d2
        ; Remove newest eligible entry, preserving newer (future) LIFO entries.
        adda.w d1,a0
        adda.w d0,a1
        subq.w #1,d3
        move.w d3,($6704-S60_DATA,a4)
.shift: cmp.w d3,d1
        bcc .value
        move.b (1,a0),(a0)+
        move.l (4,a1),(a1)+
        addq.w #1,d1
        bra .shift
.empty: moveq #0,d2
.value: bsr s60_history_unlock
        move.l d2,d0
        movem.l (sp)+,d1-d3/a0-a2/a4
        rts

s60_history_modifier0:
        bsr s60_history_modifier_base
        move.b ($62,a0),d0
        moveq #0,d1
        rts
s60_history_modifier1:
        move.l d0,-(sp)
        bsr s60_history_modifier_base
        move.b ($60,a0),d1
        move.l (sp)+,d0
        or.l d1,d0
        rts
s60_history_modifier2:
        move.l d0,-(sp)
        bsr s60_history_modifier_base
        move.b ($61,a0),d1
        move.l (sp)+,d0
        or.l d1,d0
        rts
s60_history_modifier_base:
        bsr s60_history_owned
        tst.w d0
        lea ($6726-S60_DATA,a4),a0
        beq .done
        lea (s60_history_current+12,pc),a0
.done:  rts

s60_history_port:
        move.l d0,-(sp)
        move.l (24,sp),a3 ; native SP+16 plus hook return and saved D0
        bsr s60_history_owned
        tst.w d0
        beq .live
        cmpa.l #$dff00a,a3
        beq .port0
        cmpa.l #$dff00c,a3
        bne .live
        move.w (s60_history_current+6,pc),d7
        bra .done
.port0: move.w (s60_history_current+4,pc),d7
        bra .done
.live:  move.w (a3),d7
.done:  move.l (sp)+,d0
        rts
s60_history_buttons:
        move.l d0,-(sp)
        bsr s60_history_owned
        tst.w d0
        beq .live
        lea (s60_history_current+8,pc),a0
        bra .done
.live:  move.l (s60_code,pc),a0
        move.l (14,a0),a0
        move.l ($32f0-S60_DATA,a0),a0
.done:  move.l (sp)+,d0
        rts
