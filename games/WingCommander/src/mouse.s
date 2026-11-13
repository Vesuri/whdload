; Mouse pointer in rooms and menus, every mode. Shared by both release slaves.
; The room pointer is an OS SimpleSprite that the native room routine steps by
; 5/3 pixels from digital input. Port-0 mouse motion now reaches it through the
; game input handler's unused RAWMOUSE slot: each relative event moves a
; half-pixel position clamped to the room rectangle and moves the sprite at
; once. The room routine takes that position when the mouse has moved since its
; last call, and the stick or keys still step it otherwise. The callback acts
; only between the room routine's first call and the room exit, and only while
; the pointer is not hidden. The variant supplies the left button as port-1
; fire and calls mouse_init with its parameter table and game H0 base.

MP_POS = 0                      ; A4 offset: native pointer x.w, y.w
MP_RECT = 2                     ; A4 offset: room rectangle pointer (+24..+30)
MP_SLOT = 4                     ; A4 offset: input handler RAWMOUSE slot
MP_HIDE = 6                     ; A4 offset: pointer hide counter (0 = shown)
MP_MOVE = 8                     ; H0 offset: native sprite move (x.w, y.w)

; a0 = parameter table, d0 = game H0 base.
mouse_init:
        move.l  a1,-(sp)
        lea     mouse_params(pc),a1
        move.l  a0,(a1)
        add.l   MP_MOVE(a0),d0
        lea     mouse_move(pc),a1
        move.l  d0,(a1)
        lea     mouse_active(pc),a1
        clr.w   (a1)
        movea.l (sp)+,a1
        rts

; Replaces the room routine's two position stores (8 bytes; a 6-byte call).
; d2/d3 hold the native stepped and clamped position.
mouse_room:
        movem.l d0-d1/a0-a1,-(sp)
        lea     mouse_a4(pc),a0
        move.l  a4,(a0)
        movea.l mouse_params(pc),a1
        move.w  MP_SLOT(a1),d0
        lea     mouse_event(pc),a0
        move.l  a0,(a4,d0.w)
        move.w  MP_POS(a1),d0
        move.w  mouse_seq(pc),d1
        lea     mouse_active(pc),a0     ; 68000: no tst d16(pc)
        tst.w   (a0)
        beq.s   .native                 ; first call in this room
        cmp.w   mouse_seen(pc),d1
        bne.s   .mouse
        cmp.w   (a4,d0.w),d2
        bne.s   .native                 ; stick or keys moved it
        cmp.w   2(a4,d0.w),d3
        beq.s   .store
.native:
        lea     mouse_seen(pc),a0
        move.w  d1,(a0)
        lea     mouse_x(pc),a0
        move.w  d2,d1
        add.w   d1,d1
        move.w  d1,(a0)+
        move.w  d3,d1
        add.w   d1,d1
        move.w  d1,(a0)
        lea     mouse_active(pc),a0
        move.w  #1,(a0)
        bra.s   .store
.mouse:
        lea     mouse_seen(pc),a0
        move.w  d1,(a0)
        move.w  mouse_x(pc),d2
        asr.w   #1,d2
        move.w  mouse_y(pc),d3
        asr.w   #1,d3
.store:
        move.w  d2,(a4,d0.w)
        move.w  d3,2(a4,d0.w)
        movem.l (sp)+,d0-d1/a0-a1
        addq.l  #2,(sp)                 ; past the displaced store's last word
        rts

; Replaces the room exit's native sprite move call (arguments on the stack).
mouse_exit:
        move.l  a0,-(sp)
        lea     mouse_active(pc),a0
        clr.w   (a0)
        movea.l (sp)+,a0
        move.l  mouse_move(pc),-(sp)
        rts

; RAWMOUSE slot, called from the game's input handler with a3 = event.
; The handler keeps d2/a2/a3 only: preserve everything except d0-d1/a0-a1.
mouse_event:
        lea     mouse_active(pc),a0
        tst.w   (a0)
        beq.s   .out
        tst.b   8(a3)                   ; IEQUALIFIER_RELATIVEMOUSE
        bpl.s   .out
        move.w  10(a3),d0
        or.w    12(a3),d0
        beq.s   .out
        movem.l d2-d3/a2/a4/a6,-(sp)
        movea.l mouse_a4(pc),a4
        movea.l mouse_params(pc),a2
        move.w  MP_HIDE(a2),d0
        tst.w   (a4,d0.w)
        bne.s   .done
        move.w  MP_RECT(a2),d0
        move.l  (a4,d0.w),d0
        beq.s   .done
        movea.l d0,a0
        lea     mouse_x(pc),a1
        move.w  10(a3),d0
        moveq   #24,d1
        bsr.s   .axis
        move.w  12(a3),d0
        moveq   #26,d1
        bsr.s   .axis
        addq.w  #1,(a1)                 ; mouse_seq
        move.w  -(a1),d0
        asr.w   #1,d0
        move.w  d0,-(sp)
        move.w  -(a1),d0
        asr.w   #1,d0
        move.w  d0,-(sp)
        movea.l mouse_move(pc),a0
        jsr     (a0)
        addq.l  #4,sp
.done:
        movem.l (sp)+,d2-d3/a2/a4/a6
.out:
        rts
; (a1)+ = half-pixel coordinate + d0, clamped to rectangle words d1(a0), d1+4(a0).
.axis:
        add.w   (a1),d0
        move.w  (a0,d1.w),d2
        add.w   d2,d2
        cmp.w   d2,d0
        bge.s   .low
        move.w  d2,d0
.low:
        move.w  4(a0,d1.w),d2
        add.w   d2,d2
        addq.w  #1,d2
        cmp.w   d2,d0
        ble.s   .high
        move.w  d2,d0
.high:
        move.w  d0,(a1)+
        rts

        cnop    0,4
mouse_a4:       dc.l 0
mouse_params:   dc.l 0
mouse_move:     dc.l 0
mouse_x:        dc.w 0                  ; half pixels; mouse_y and mouse_seq follow
mouse_y:        dc.w 0
mouse_seq:      dc.w 0
mouse_seen:     dc.w 0
mouse_active:   dc.w 0
        even
