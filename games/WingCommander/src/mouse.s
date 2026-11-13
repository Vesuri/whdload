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
;
; Mouse flight: a virtual stick. The flight controller's ramp stores call
; mouse_steer, which adds the mouse motion since its last call to a stick
; position and sets the pitch and yaw ramps in proportion to it, as a held
; stick does; the ship keeps turning while the mouse is held off centre. The
; pointer sprite shows that position around the gunsight in the forward view.
; The stick or keys steering, the external view and a new flight re-centre it.
; The pointer appears only once the mouse moves and hides after 10 seconds
; without motion; the variant's VBL hook calls mouse_vbl, which also hides it
; once the controller has stopped running.

MP_POS = 0                      ; A4 offset: native pointer x.w, y.w
MP_RECT = 2                     ; A4 offset: room rectangle pointer (+24..+30)
MP_SLOT = 4                     ; A4 offset: input handler RAWMOUSE slot
MP_HIDE = 6                     ; A4 offset: pointer hide counter (0 = shown)
MP_MOVE = 8                     ; H0 offset: native sprite move (x.w, y.w)
MP_RAMP = 12                    ; A4 offset: pitch ramp; the yaw ramp follows
MP_VIEW = 14                    ; A4 offset: camera view (0 forward, 8 external)
MP_FLAGS = 16                   ; A4 offset: left, right, up, down, modifier bytes
MP_SPRITE = 18                  ; A4 offset: pointer SimpleSprite (posctldata.l)
MP_CENTRE = 20                  ; pointer centre x.w, y.w (sprite move coordinates)

STICK_RANGE = 72                ; mouse counts from centre to full deflection
STICK_STEP = 8                  ; counts per ramp step: ramps reach +-9
FLIGHT_GAP = 50                 ; fields without a controller call: a new flight
HIDE_GAP = 25                   ; fields without one before the pointer hides
IDLE_GAP = 500                  ; fields without motion before it hides (10 s PAL)

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
        ; The flight pointer: its own Chip image, bound only while shown (the
        ; room images belong to their rooms). Without it the mouse still steers.
        movem.l d0-d1/a0-a2/a6,-(sp)
        move.l  stick_image(pc),d0      ; 68000: no tst d16(pc)
        bne.s   .ready
        movea.l 4.w,a6
        lea     .graphics(pc),a1
        moveq   #0,d0
        jsr     -552(a6)                ; OpenLibrary
        lea     stick_gfx(pc),a1
        move.l  d0,(a1)
        beq.s   .ready
        moveq   #POINTER_SIZE,d0
        move.l  #$10002,d1              ; MEMF_CHIP!MEMF_CLEAR
        jsr     -198(a6)                ; AllocMem
        tst.l   d0
        beq.s   .ready
        movea.l d0,a1
        addq.l  #4,a1                   ; control words stay clear: hidden
        lea     pointer_lines(pc),a0
        moveq   #POINTER_H-1,d1
.line:
        move.w  (a0)+,(a1)+
        move.w  (a0)+,(a1)+
        dbf     d1,.line
        lea     stick_image(pc),a1
        move.l  d0,(a1)
.ready:
        movem.l (sp)+,d0-d1/a0-a2/a6
        rts
.graphics:
        dc.b    'graphics.library',0
        even

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

; RAWMOUSE slot, called from the game's input handler with a3 = event. Every
; relative event also adds to mouse_sum_x/y, which only their reader consumes.
; The handler keeps d2/a2/a3 only: preserve everything except d0-d1/a0-a1.
mouse_event:
        tst.b   8(a3)                   ; IEQUALIFIER_RELATIVEMOUSE
        bpl.s   .out
        move.w  10(a3),d0
        or.w    12(a3),d0
        beq.s   .out
        lea     mouse_sum_x(pc),a0      ; running counts for a variant's grid screens
        move.w  10(a3),d0
        add.w   d0,(a0)+
        move.w  12(a3),d0
        add.w   d0,(a0)
        lea     mouse_active(pc),a0
        tst.w   (a0)
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

; Replaces the flight controller's pitch and yaw ramp stores (8 bytes; a
; 6-byte call), with d2 = pitch and d3 = yaw ramp as the native code left them.
; Native ramps step by one per call to +-9 and decay by two; the mouse sets
; them at once. Mouse right is the stick right (yaw +); mouse down is the stick
; back (pitch -). Every register except d2/d3 is kept.
mouse_steer:
        movem.l d0-d1/d4-d7/a0-a3/a5-a6,-(sp)
        lea     mouse_a4(pc),a0
        move.l  a4,(a0)
        movea.l mouse_params(pc),a1
        move.w  MP_SLOT(a1),d0
        lea     mouse_event(pc),a0
        move.l  a0,(a4,d0.w)
        lea     stick_x(pc),a2
        move.w  mouse_fields(pc),d0
        move.w  d0,d1
        sub.w   ST_FIELD(a2),d1         ; fields since the last call
        move.w  d0,ST_FIELD(a2)
        move.w  mouse_sum_x(pc),d0      ; motion since the last call
        sub.w   ST_LAST(a2),d0
        add.w   d0,ST_LAST(a2)
        move.w  mouse_sum_y(pc),d4
        sub.w   ST_LAST+2(a2),d4
        add.w   d4,ST_LAST+2(a2)
        cmpi.w  #FLIGHT_GAP,d1
        bhi.w   .centre                 ; a new flight
        move.w  MP_VIEW(a1),d1
        cmpi.w  #8,(a4,d1.w)
        beq.w   .centre                 ; the stick turns the external camera
        move.w  MP_FLAGS(a1),d1
        tst.b   4(a4,d1.w)
        bne.s   .mouse                  ; directions throttle and roll instead
        tst.l   (a4,d1.w)
        bne.w   .centre                 ; the stick or keys steer
.mouse:
        move.w  d0,d5
        or.w    d4,d5
        beq.s   .still
        move.w  #1,ST_USED(a2)
        move.w  mouse_fields(pc),ST_MOVED(a2)
.still:
        tst.w   ST_USED(a2)
        beq.w   .store                  ; not used this flight: native ramps
        move.w  (a2),d1
        bsr.w   .add
        move.w  d1,(a2)
        ext.l   d1
        divs.w  #STICK_STEP,d1
        move.w  d1,d3
        move.w  d0,d6                   ; x moved
        move.w  2(a2),d1
        move.w  d4,d0
        bsr.w   .add
        move.w  d1,2(a2)
        ext.l   d1
        divs.w  #STICK_STEP,d1
        neg.w   d1
        move.w  d1,d2
        or.w    d4,d6                   ; moved at all
        move.w  MP_VIEW(a1),d1
        tst.w   (a4,d1.w)
        bne.s   .hide                   ; the pointer is for the forward view
        tst.w   d6
        bne.s   .show                   ; moved: show it
        tst.w   ST_SHOWN(a2)
        bne.s   .store
        move.w  mouse_fields(pc),d0     ; hidden by a pause: show it again
        sub.w   ST_MOVED(a2),d0         ; unless the mouse has been idle
        cmpi.w  #IDLE_GAP,d0
        bhi.s   .store
.show:
        movea.l stick_image(pc),a3
        move.l  a3,d0
        beq.s   .store
        movea.l stick_gfx(pc),a6
        move.w  MP_SPRITE(a1),d0
        lea     (a4,d0.w),a5            ; SimpleSprite
        cmpa.l  (a5),a3
        beq.s   .bound
        move.w  #POINTER_H,4(a5)
        suba.l  a0,a0
        movea.l a5,a1
        movea.l a3,a2
        jsr     -420(a6)                ; ChangeSprite
        lea     stick_x(pc),a2
.bound:
        move.w  #1,ST_SHOWN(a2)
        movea.l mouse_params(pc),a1
        move.w  (a2),d0
        asr.w   #1,d0
        add.w   MP_CENTRE(a1),d0
        move.w  2(a2),d1
        asr.w   #1,d1
        add.w   MP_CENTRE+2(a1),d1
        suba.l  a0,a0
        movea.l a5,a1
        jsr     -426(a6)                ; MoveSprite
        bra.s   .store
.centre:
        clr.l   (a2)
        clr.w   ST_USED(a2)
.hide:
        bsr.w   stick_hide
.store:
        movea.l mouse_params(pc),a1
        move.w  MP_RAMP(a1),d1
        move.w  d2,(a4,d1.w)
        move.w  d3,2(a4,d1.w)
        movem.l (sp)+,d0-d1/d4-d7/a0-a3/a5-a6
        addq.l  #2,(sp)                 ; past the displaced store's last word
        rts
; d1 = stick + d0, clamped to +-STICK_RANGE.
.add:
        add.w   d0,d1
        cmpi.w  #-STICK_RANGE,d1
        bge.s   .low
        moveq   #-STICK_RANGE,d1
.low:
        cmpi.w  #STICK_RANGE,d1
        ble.s   .high
        moveq   #STICK_RANGE,d1
.high:
        rts

; From the variant's VBL hook, every field: counts fields and hides a shown
; flight pointer once the controller has stopped (pause, map, flight over) or
; the mouse has been idle for IDLE_GAP fields; the next motion shows it.
; Keeps every register.
mouse_vbl:
        movem.l d0/a0,-(sp)
        lea     mouse_fields(pc),a0
        addq.w  #1,(a0)
        lea     stick_x(pc),a0
        tst.w   ST_SHOWN(a0)
        beq.s   .done
        move.w  mouse_fields(pc),d0
        sub.w   ST_FIELD(a0),d0
        cmpi.w  #HIDE_GAP,d0
        bhi.s   .hide
        move.w  mouse_fields(pc),d0
        sub.w   ST_MOVED(a0),d0
        cmpi.w  #IDLE_GAP,d0
        bls.s   .done
.hide:
        bsr.s   stick_hide
.done:
        movem.l (sp)+,d0/a0
        rts

; Hide the flight pointer by clearing its image's control words, with no
; library call, while the sprite is still bound to it; a room rebinds its own
; image on entry. Keeps every register.
stick_hide:
        movem.l d0/a0-a1,-(sp)
        lea     stick_shown(pc),a0
        clr.w   (a0)
        move.l  stick_image(pc),d0
        beq.s   .done
        movea.l mouse_params(pc),a1
        move.w  MP_SPRITE(a1),d0
        movea.l mouse_a4(pc),a1
        movea.l (a1,d0.w),a1            ; posctldata
        cmpa.l  stick_image(pc),a1
        bne.s   .done
        clr.l   (a1)
.done:
        movem.l (sp)+,d0/a0-a1
        rts

; The pointer image: a small cross with an open centre, colour 3.
POINTER_H = 7
POINTER_SIZE = 4+POINTER_H*4+4
pointer_lines:
        dc.w    $1000,$1000
        dc.w    $1000,$1000
        dc.w    $0000,$0000
        dc.w    $c600,$c600
        dc.w    $0000,$0000
        dc.w    $1000,$1000
        dc.w    $1000,$1000

ST_LAST = 4                     ; stick record: x.w, y.w, then these
ST_FIELD = 8
ST_USED = 10
ST_SHOWN = 12
ST_MOVED = 14

        cnop    0,4
mouse_a4:       dc.l 0
mouse_params:   dc.l 0
mouse_move:     dc.l 0
mouse_x:        dc.w 0                  ; half pixels; mouse_y and mouse_seq follow
mouse_y:        dc.w 0
mouse_seq:      dc.w 0
mouse_seen:     dc.w 0
mouse_active:   dc.w 0
mouse_sum_x:    dc.w 0                  ; counts, wrapping; mouse_sum_y follows
mouse_sum_y:    dc.w 0
mouse_fields:   dc.w 0                  ; VBL fields (mouse_vbl)
stick_x:        dc.w 0                  ; counts from centre; stick_y follows
stick_y:        dc.w 0
stick_last:     dc.w 0,0                ; mouse_sum_x/y at the last call
stick_field:    dc.w 0                  ; mouse_fields at the last call
stick_used:     dc.w 0                  ; the mouse has steered this flight
stick_shown:    dc.w 0                  ; the pointer is on screen
stick_moved:    dc.w 0                  ; mouse_fields at the last motion
        cnop    0,4
stick_image:    dc.l 0                  ; Chip pointer image, 0 without one
stick_gfx:      dc.l 0                  ; GfxBase
        even
