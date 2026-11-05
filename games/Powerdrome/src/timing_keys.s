; WORLD20 centering commands. Native key publication timestamps logical effects;
; the native post-render handlers no longer mutate state or emit feedback. Other keys retain
; their existing handlers pending the wider mode/input extraction.
TIMING_KEY_MASK = 2040

timing_world_input_initialize
 movem.l d0/a0,-(sp)
 lea timing_key_state(pc),a0
 moveq #6,d0
.clear
 clr.l (a0)+
 dbra d0,.clear
 ; The diagnostic tag precedes state, so it is not cleared.
 lea timing_key_state(pc),a0
 move.w #1,(a0)
 move.w timing_input_current+2(pc),6(a0)
 movem.l (sp)+,d0/a0
 rts

timing_world_input_disable
 move.l a0,-(sp)
 lea timing_key_state(pc),a0
 clr.w (a0)
 clr.w 2(a0)
 movem.l (sp)+,a0
 rts

; Called by the hardware keyboard producer before replaying its publication.
timing_key_publish
 move.w sr,-(sp)
 movem.l d0-d1/a0,-(sp)
 move.l perf_game(pc),a0
 move.l $48fe(a0),d1
 ; Publish at the next PAL boundary, never into an already executed world step.
 addq.l #1,d1
 bsr timing_key_enqueue
 movem.l (sp)+,d0-d1/a0
 move.w (sp)+,ccr
 ; Original MOVE.W D1,game+$461a; preserve its flags and all input registers.
 move.l a0,-(sp)
 move.l perf_game(pc),a0
 move.w d1,$461a(a0)
 movea.l (sp)+,a0
 rts

; d0.b ASCII, d1.l VBL count at publication. Producer never changes game state.
; The fixture uses the same entry with the count of the VBL it is publishing in.
timing_key_enqueue
 movem.l d0-d4/a0-a1,-(sp)
 lea timing_key_state(pc),a0
 tst.w (a0)
 beq.w .done
 move.w timing_input_paused(pc),d2
 bne.w .done
 and.w #255,d0
 cmp.w #'A',d0
 blo.s .normalized
 cmp.w #'Z',d0
 bhi.s .normalized
 add.w #32,d0
.normalized
 cmp.w #'c',d0
 beq.s .wanted
 cmp.w #'x',d0
 beq.s .wanted
 cmp.w #'z',d0
 bne.s .done
.wanted
 sub.l timing_input_paused_fields(pc),d1
 lsl.l #2,d1
 move.w 10(a0),d2
 move.w d2,d3
 addq.w #8,d3
 and.w #TIMING_KEY_MASK,d3
 cmp.w 8(a0),d3
 beq.s .full
 lea timing_key_queue(pc),a1
 adda.w d2,a1
 move.l d1,(a1)
 move.w d0,4(a1)
 clr.w 6(a1)
 addq.l #1,12(a0)
 move.w d3,10(a0) ; publish after timestamp/key contents
 bra.s .done
.full
 addq.l #1,20(a0)
.done
 movem.l (sp)+,d0-d4/a0-a1
 rts

; The world reader precedes the control reader. Input slots cannot be released by
; controls before movement has consumed their modifier history at the later time.
timing_input_for_world
 movem.l d0-d3/a0-a1,-(sp)
 lea timing_key_state(pc),a1
.inputs
 move.w 4(a1),d0
 cmp.w timing_input_write(pc),d0
 beq.s .keys
 lea timing_input_queue(pc),a0
 adda.w d0,a0
 move.l timing_world20_clock(pc),d1
 sub.l (a0),d1
 bmi.s .keys
 move.w 6(a0),6(a1)
 add.w #16,d0
 and.w #TIMING_INPUT_MASK,d0
 move.w d0,4(a1)
 bra.s .inputs
.keys
 move.w 8(a1),d0
 cmp.w 10(a1),d0
 beq.s .done
 lea timing_key_queue(pc),a0
 adda.w d0,a0
 move.l timing_world20_clock(pc),d1
 sub.l (a0),d1
 bmi.s .done
 move.w $d4(a6),d2
 move.w 4(a0),d3
 cmp.w #'c',d3
 bne.s .decrease
 add.w #40,d2
 cmp.w #360,d2
 ble.s .store
 move.w #360,d2
 bra.s .store
.decrease
 sub.w #40,d2
 cmp.w #'z',d3
 beq.s .off
 tst.w d2
 bgt.s .store
.off
 moveq #0,d2
.store
 move.w d2,$d4(a6)
 sne $d2(a6)
 sne $d3(a6)
 move.w #1,2(a1) ; coalesce text feedback until presentation
 move.l (a0),24(a1)
 addq.l #1,16(a1)
 addq.w #8,d0
 and.w #TIMING_KEY_MASK,d0
 move.w d0,8(a1)
 bra.s .keys
.done
 movem.l (sp)+,d0-d3/a0-a1
 rts

; Native BTST changes only Z. Restore all incoming flags before testing the
; historical value; MOVEM and arithmetic on SP preserve the resulting flags.
timing_world_shift_test
 move.w sr,-(sp)
 move.l d0,-(sp)
 move.w timing_key_modifiers(pc),d0
 move.w 4(sp),ccr
 btst #0,d0
 movem.l (sp)+,d0
 addq.l #2,sp
 rts

; Only the outer drawing path calls the native text helper; no physics mutation.
timing_center_present
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 lea timing_key_state(pc),a0
 tst.w 2(a0)
 beq.s .done
 clr.w 2(a0)
 move.l perf_game(pc),a0
 lea $3bea(a0),a3
 moveq #0,d0
 move.w $d4(a6),d0
 beq.s .show
 divu.w #40,d0
 add.b #'0',d0
 move.b d0,$3c17(a0)
 lea $3bfe(a0),a3
.show
 bsr timing_center_message
.done
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 rts

timing_center_message dc.w $4ef9
 dc.l 0
timing_center_skip dc.w $4ef9
 dc.l 0

timing_key_tag dc.b 'PDKEY001'
timing_key_state
 dc.w 0 ; +8 enabled
 dc.w 0 ; +10 presentation pending
 dc.w 0 ; +12 movement's input-history cursor
timing_key_modifiers dc.w 0 ; +14 historical Shift
timing_key_read dc.w 0 ; +16 key queue read
timing_key_write dc.w 0 ; +18 key queue write
 dc.l 0 ; +20 produced
 dc.l 0 ; +24 consumed
 dc.l 0 ; +28 overflow
 dc.l 0 ; +32 last applied key timestamp
timing_key_queue ds.b 2048
