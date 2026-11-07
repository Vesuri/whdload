; Click-input hooks, installed by clicks.s. They reference only their own state, so
; they can sit after the VERIFY instruments.

; In: D0 = CUSTOM2, A2/A3/A4 = hunks 1/6/9. Out: A0 = 0 when installed, else the reason.
_click_patch
        cmp.l #$3940e03a,($1ba8,a2)	;h1:01ba8 move.w d0,-8134(a4)
        bne .bad
        cmp.w #$4e75,($1bac,a2)		;rts
        bne .bad
        cmp.l #$bfecde40,($7da,a3)	;h6:007da cmpa.l -8640(a4),sp
        bne .bad
        cmp.l #$650000f0,($7de,a3)	;bcs.w h6:008d0
        bne .bad
        cmp.l #$4eba024e,($404,a4)	;h9:00404 jsr h9:00654 (the live reader)
        bne .bad
        lea (_click_targets,pc),a0
        lea ($7e2,a3),a1
        move.l a1,(a0)+			;_click_hit_continue
        lea ($8d0,a3),a1
        move.l a1,(a0)+			;_click_hit_overflow
        sub.l a1,a1
        btst #6,d0			;combat replays history only with the timing
        beq .skip
        lea ($408,a4),a1
.skip   move.l a1,(a0)			;_click_skip_return
        ; PERF_RANGE h1:01ba8 6 bit=8
        move.w #$4ef9,($1ba8,a2)
        lea (_click_reader,pc),a0
        move.l a0,($1baa,a2)
        ; PERF_RANGE h6:007da 8 bit=8
        move.w #$4ef9,($7da,a3)
        lea (_click_hit,pc),a0
        move.l a0,($7dc,a3)
        move.w #$4e71,($7e0,a3)
        lea (_click_state+6,pc),a0
        move.w #1,(a0)
        sub.l a0,a0
        rts
.bad    lea (_click_bad,pc),a0
        rts

; h1:01ba8, the end of the live reader: D0 = the buttons from h12:05288. Ends with the
; original store and RTS, so the caller sees the same CCR and D0.
_click_reader
        move.l a0,-(sp)
        move.l (_click_skip_return,pc),a0
        cmpa.l (4,sp),a0		;combat's live read under the timing
        movea.l (sp)+,a0
        beq .store
        bsr _click_filter
.store  move.w d0,(-8134,a4)
        rts

; D0.w = buttons, out D0 = buttons as press events. All other registers kept.
; Any button counts: the screens' click-outside tests the whole word.
_click_filter
        move.l a0,-(sp)
        lea (_click_state,pc),a0
        tst.w (6,a0)			;enabled
        beq .done
        clr.w (4,a0)			;not the first poll of a press
        tst.w d0
        bne .down
        move.w #1,(a0)			;released: the next press passes
        clr.w (2,a0)
        bra .done
.down   tst.w (a0)
        beq .held
        clr.w (a0)			;a new press
        move.w #1,(4,a0)
        bra .done
.held   tst.w (2,a0)
        bne .done			;held on a movement gadget
        moveq #0,d0
.done   movea.l (sp)+,a0
        rts

; h6:007da, the button hit test (list, x, y): returns the gadget id, 0 for none.
_click_hit
        cmpa.l (-8640,a4),sp
        bcs .overflow
        move.l (12,sp),-(sp)
        move.l (12,sp),-(sp)
        move.l (12,sp),-(sp)
        bsr .original
        lea (12,sp),sp
        tst.l d0
        beq .out
        movem.l d1/a0,-(sp)
        lea (_click_state,pc),a0
        move.l (12,sp),d1		;the list
        cmp.l (CLICK_MAIN_LIST,a4),d1
        bne .click
        moveq #13,d1
        cmp.l d1,d0
        blt .click
        moveq #0,d1			;the dispatcher's index (h5:01aea)
        move.b d0,d1
        cmp.w #17,d1			;turn left, forward, turn right,
        blo .click			;strafe, run, strafe
        cmp.w #22,d1
        bls .hold
        cmp.w #24,d1			;back (23 is the U-turn)
        beq .hold
        cmp.w #38,d1			;the compass ring sets a heading
        blo .click
        cmp.w #61,d1
        bhi .click
.hold   move.w #1,(2,a0)
        bra .ok
.click  clr.w (2,a0)
        tst.w (4,a0)
        bne .ok
        ; Dragged off a movement gadget: no click and no click outside.
        moveq #0,d0
        clr.w (-8134,a4)
.ok     movem.l (sp)+,d1/a0
.out    tst.l d0
        rts
.original
        move.l (_click_hit_continue,pc),-(sp)
        rts
.overflow
        move.l (_click_hit_overflow,pc),-(sp)
        rts

_click_state dc.w 1,0,0,0		;armed, holding a movement gadget, first poll, enabled
        CNOP 0,4
_click_targets
_click_hit_continue dc.l 0
_click_hit_overflow dc.l 0
_click_skip_return dc.l 0

_click_bad dc.b "Click inputs: unexpected game code",0
        EVEN
