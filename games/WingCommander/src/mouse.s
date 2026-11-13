; Mouse pointer in rooms and menus, every mode. Shared by both release slaves.
; The room pointer is an OS SimpleSprite that the native room routine steps by
; 5/3 pixels from digital input. Port-0 mouse motion now reaches it through the
; game input handler's unused RAWMOUSE slot: each relative event moves a
; half-pixel position clamped to the room rectangle and moves the sprite at
; once. The room routine takes that position when the mouse has moved since its
; last call, and the stick or keys still step it otherwise. When the game
; places the pointer itself (a new screen centres it without a room exit), the
; mouse continues from there. The callback acts
; only between the room routine's first call and the room exit, and only while
; the pointer is not hidden. The variant supplies the left button as port-1
; fire and calls mouse_init with its parameter table and game H0 base.
;
; Mouse flight: the PC version's pointer and stick. The flight controller's
; ramp stores call mouse_steer, which moves the pointer by the mouse motion
; since its last call, two counts a pixel as in the rooms (and as the PC's
; default mouse driver), anywhere on the screen. It starts on the gunsight,
; the centre of the cockpit aperture, and the pitch and yaw ramps follow from
; its place as the PC sets its stick: its distance from the gunsight on each
; axis, in the PC's steps, gives 0 to 5 steps, and within 4 pixels of the
; aperture's edges or past them full deflection; the ship keeps turning while
; the pointer is off centre. (The PC measures from the middle of a window
; that it places at the screen's top left; here it is the aperture, so that
; the gunsight is the centre in the cockpit and in the Training Simulator.)
; The pointer, the PC version's 9x9 one, shows in the
; forward view. It is sprite 7 with its own images, behind the cockpit: the
; two calls of the native aperture scan also copy the cockpit's transparent
; pixels into a mask, and the pointer image keeps only the pixels over them.
; Sprite 7's colour 3 is colour 31, white on OCS; on CD32 the slave moves the
; odd sprites' colour bank in the flight copper lists to 192, which makes it
; colour 207, the PC pointer's own (243,255,235).
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
MP_APERTURE = 18                ; A4 offset: aperture width, height, centre x, y, left, top
MP_COPPER = 20                  ; A4 offset: the two flight copper lists (0: no colour bank)
MP_SCAN = 22                    ; H0 offset: native aperture scan (long)

STICK_LEVEL = 9                 ; stick units per PC step: steps 1-5 and 8 give ramps 1-5 and 9
STICK_STEP = 8                  ; stick units per ramp step: ramps reach +-9
FLIGHT_GAP = 50                 ; fields without a controller call: a new flight
HIDE_GAP = 25                   ; fields without one before the pointer hides
IDLE_GAP = 500                  ; fields without motion before it hides (10 s PAL)
POINTER_SPRITE = 7              ; odd: its colour bank leaves sprites 0-6 alone
SPRITE_BANK = 12                ; odd sprites' colours from 192: sprite 7 colour 3 is 207
MASK_STRIDE = 44                ; bytes per mask row: a pad byte, 40, three pad bytes
MASK_SIZE = 200*MASK_STRIDE     ; the aperture's rows at most
SS_SIZE = 12                    ; SimpleSprite: posctldata.l, height, x, y, num

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
        movem.l d0-d1/a0-a2/a6,-(sp)
        sub.l   MP_MOVE(a0),d0          ; H0
        add.l   MP_SCAN(a0),d0
        lea     mouse_scan_native(pc),a1
        move.l  d0,(a1)
        ; The flight pointer: its own cleared Chip image (hidden: no control
        ; words), and a SimpleSprite and the cockpit mask in any memory. The
        ; sprite is allocated at its first showing. Without them the mouse
        ; still steers.
        move.l  stick_image(pc),d0      ; 68000: no tst d16(pc)
        bne.s   .ready
        movea.l 4.w,a6
        lea     .graphics(pc),a1
        moveq   #0,d0
        jsr     -552(a6)                ; OpenLibrary
        lea     stick_gfx(pc),a1
        move.l  d0,(a1)
        beq.s   .ready
        move.l  #SS_SIZE+MASK_SIZE,d0
        move.l  #$10000,d1              ; MEMF_CLEAR
        jsr     -198(a6)                ; AllocMem
        lea     stick_ss(pc),a1
        move.l  d0,(a1)
        beq.s   .ready
        moveq   #POINTER_SIZE,d0
        move.l  #$10002,d1              ; MEMF_CHIP!MEMF_CLEAR
        jsr     -198(a6)                ; AllocMem
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
        movea.l (a4,d0.w),a1
        cmpa.l  mouse_last(pc),a1
        bne.s   .native                 ; the game placed it (a new screen)
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
        lea     mouse_last(pc),a0
        move.w  d2,(a0)+
        move.w  d3,(a0)
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
        bpl.w   .out
        move.w  10(a3),d0
        or.w    12(a3),d0
        beq.w   .out
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
        move.w  MP_POS(a2),d0
        move.l  (a4,d0.w),d1
        lea     mouse_last(pc),a1
        cmp.l   (a1),d1
        beq.s   .synced
        move.l  d1,(a1)                 ; the game placed the pointer: start there
        lea     mouse_y(pc),a1
        add.w   d1,d1
        move.w  d1,(a1)
        swap    d1
        add.w   d1,d1
        move.w  d1,-(a1)
.synced:
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
        move.w  d0,d6
        or.w    d4,d6                   ; moved at all
        beq.s   .still
        move.w  #1,ST_USED(a2)
        move.w  mouse_fields(pc),ST_MOVED(a2)
.still:
        tst.w   ST_USED(a2)
        beq.w   .store                  ; not used this flight: native ramps
        move.w  MP_APERTURE(a1),d1
        lea     (a4,d1.w),a0            ; width, height, centre x, y, left, top
        movea.w d4,a6                   ; y motion
        move.w  4(a0),d5                ; x: centre, the screen's last column,
        move.w  #319,d7
        move.w  8(a0),d4                ; the aperture's first and last
        movea.w d4,a5
        adda.w  (a0),a5
        subq.w  #1,a5
        lea     steps_x(pc),a3
        move.w  ST_PTR(a2),d1
        bsr.w   .axis
        move.w  d1,ST_PTR(a2)
        move.w  d0,(a2)
        ext.l   d0
        divs.w  #STICK_STEP,d0
        move.w  d0,d3                   ; yaw
        move.w  6(a0),d5                ; y: centre, the screen's last row,
        move.w  #199,d7
        move.w  10(a0),d4               ; the aperture's first and last
        movea.w d4,a5
        adda.w  2(a0),a5
        subq.w  #1,a5
        lea     steps_y(pc),a3
        move.w  ST_PTR+2(a2),d1
        move.w  a6,d0
        bsr.w   .axis
        move.w  d1,ST_PTR+2(a2)
        move.w  d0,2(a2)
        ext.l   d0
        divs.w  #STICK_STEP,d0
        neg.w   d0
        move.w  d0,d2                   ; pitch
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
        bsr.w   stick_show
        bra.s   .store
.centre:
        clr.l   (a2)
        clr.l   ST_PTR(a2)
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
; One axis, as the PC version: d1 = pointer offset from the centre d5 in half
; pixels, + d0, clamped so that the pointer stays on screen pixels 0..d7.
; d0 = the stick: STICK_LEVEL times the step of the pointer's distance from
; the centre in table a3, or 8 steps within 4 pixels of the aperture's first
; pixel d4 or last a5 (the PC's edge rule; past them too). Uses d4/d7/a3.
.axis:
        add.w   d0,d1
        move.w  d5,d0
        add.w   d0,d0
        neg.w   d0                      ; -2 * centre: pixel 0
        cmp.w   d0,d1
        bge.s   .low
        move.w  d0,d1
.low:
        move.w  d7,d0
        sub.w   d5,d0
        add.w   d0,d0
        addq.w  #1,d0                   ; the screen's last pixel
        cmp.w   d0,d1
        ble.s   .high
        move.w  d0,d1
.high:
        move.w  d1,d0
        asr.w   #1,d0
        add.w   d5,d0                   ; the pointer's pixel
        move.w  d0,d7
        subq.w  #4,d7
        cmp.w   d4,d7
        bgt.s   .first
        move.w  #-8*STICK_LEVEL,d0
        rts
.first:
        addq.w  #8,d7
        cmp.w   a5,d7
        blt.s   .last
        move.w  #8*STICK_LEVEL,d0
        rts
.last:
        sub.w   d5,d0                   ; pixels from the centre
        move.w  d0,d7
        bpl.s   .abs
        neg.w   d7
.abs:
        moveq   #0,d4
.step:
        cmp.w   (a3)+,d7
        blt.s   .stepped
        addq.w  #1,d4
        bra.s   .step
.stepped:
        mulu.w  #STICK_LEVEL,d4
        tst.w   d0
        bpl.s   .right
        neg.w   d4
.right:
        move.w  d4,d0
        rts
; The PC version's steps (WC.EXE data): a step more from each distance.
steps_x:        dc.w 10,37,52,57,62,$7fff
steps_y:        dc.w 5,18,27,35,38,$7fff

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
; library call. Keeps every register.
stick_hide:
        movem.l d0/a0,-(sp)
        lea     stick_shown(pc),a0
        clr.w   (a0)
        move.l  stick_image(pc),d0
        beq.s   .done
        movea.l d0,a0
        clr.l   (a0)
.done:
        movem.l (sp)+,d0/a0
        rts

; Show the flight pointer at its position (from mouse_steer, a4 = game
; A4). The first showing allocates sprite 7 and binds the image, still blank;
; without the sprite there is no pointer. Keeps every register.
stick_show:
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        move.l  stick_image(pc),d0
        beq.w   .done
        movea.l d0,a3
        movea.l stick_ss(pc),a5
        movea.l stick_gfx(pc),a6
        lea     stick_owned(pc),a0
        tst.w   (a0)
        bgt.s   .owned
        bmi.w   .done                   ; sprite 7 was taken
        move.w  #-1,(a0)
        movea.l a5,a0
        moveq   #POINTER_SPRITE,d0
        jsr     -408(a6)                ; GetSprite
        tst.w   d0
        bmi.w   .done
        lea     stick_owned(pc),a0
        move.w  #1,(a0)
        move.w  #POINTER_H,4(a5)
        suba.l  a0,a0
        movea.l a5,a1
        movea.l a3,a2
        jsr     -420(a6)                ; ChangeSprite
.owned:
        bsr.w   stick_bank
        ; The gunsight plus the pointer offset.
        movea.l mouse_params(pc),a1
        move.w  MP_APERTURE(a1),d0
        lea     (a4,d0.w),a0            ; width, height, centre x, y, left, top
        lea     stick_ptr(pc),a2
        move.w  (a2)+,d4
        asr.w   #1,d4
        add.w   4(a0),d4                ; pointer centre x
        move.w  (a2),d5
        asr.w   #1,d5
        add.w   6(a0),d5                ; pointer centre y
        tst.w   d4
        bpl.s   .xlow
        moveq   #0,d4
.xlow:
        cmpi.w  #319,d4
        ble.s   .xhigh
        move.w  #319,d4
.xhigh:
        tst.w   d5
        bpl.s   .ylow
        moveq   #0,d5
.ylow:
        cmpi.w  #199,d5
        ble.s   .yhigh
        move.w  #199,d5
.yhigh:
        ; Each line keeps the pixels over the aperture: mask bits from the
        ; image's left pixel (x-4, bit x+4 of the row with its pad byte).
        lea     4(a3),a1
        lea     pointer_lines(pc),a2
        lea     SS_SIZE(a5),a0          ; mask
        move.w  d5,d6
        subq.w  #4,d6
        sub.w   mask_top(pc),d6         ; mask row of the first line
        move.w  d4,d7
        addq.w  #4,d7
        move.w  d7,d3
        lsr.w   #3,d3                   ; byte
        andi.w  #7,d7                   ; bit
        moveq   #POINTER_H-1,d2
.line:
        moveq   #0,d0
        cmp.w   mask_rows(pc),d6
        bhs.s   .put                    ; outside the mask rows: hidden
        move.w  d6,d1
        mulu.w  #MASK_STRIDE,d1
        add.w   d3,d1
        move.b  (a0,d1.l),d0
        lsl.l   #8,d0
        move.b  1(a0,d1.l),d0
        lsl.l   #8,d0
        move.b  2(a0,d1.l),d0
        lsl.l   d7,d0
        lsr.l   #8,d0
        and.w   (a2),d0
.put:
        move.w  d0,(a1)+                ; colour 3: both planes
        move.w  d0,(a1)+
        addq.l  #2,a2
        addq.w  #1,d6
        dbf     d2,.line
        lea     stick_shown(pc),a0
        move.w  #1,(a0)
        move.w  d4,d0
        subq.w  #5,d0                   ; sprite pixel 0 is at MoveSprite x+1
        move.w  d5,d1
        subq.w  #4,d1
        suba.l  a0,a0
        movea.l a5,a1
        jsr     -426(a6)                ; MoveSprite
.done:
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        rts

; CD32: the odd sprites' colour bank in each of the game's two flight copper
; lists (their BPLCON4 move, found once per list). OCS has no bank (0).
; a4 = game A4; uses d0-d3/a0-a2.
BANK_SEARCH = 1024              ; copper moves searched for BPLCON4
stick_bank:
        movea.l mouse_params(pc),a1
        move.w  MP_COPPER(a1),d0
        beq.s   .done
        lea     (a4,d0.w),a1            ; two cprlist pointers
        lea     bank_lists(pc),a2       ; per list: start.l, offset.w, pad
        moveq   #2-1,d1
.list:
        move.l  (a1)+,d0
        beq.s   .next
        movea.l d0,a0
        move.l  4(a0),d0                ; cprlist start
        beq.s   .next
        movea.l d0,a0
        cmp.l   (a2),d0
        bne.s   .find
        move.w  4(a2),d2
        cmpi.w  #$010c,(a0,d2.w)
        beq.s   .set
.find:
        clr.l   (a2)
        moveq   #0,d2
        move.w  #BANK_SEARCH-1,d3
.search:
        cmpi.w  #$010c,(a0,d2.w)
        beq.s   .found
        cmpi.l  #$fffffffe,(a0,d2.w)
        beq.s   .next                   ; no BPLCON4: search again next time
        addq.w  #4,d2
        dbf     d3,.search
        bra.s   .next
.found:
        move.l  a0,(a2)
        move.w  d2,4(a2)
.set:
        move.b  3(a0,d2.w),d0
        andi.b  #$f0,d0
        ori.b   #SPRITE_BANK,d0
        move.b  d0,3(a0,d2.w)
.next:
        addq.l  #8,a2
        dbf     d1,.list
.done:
        rts

; Replaces both calls of the native cockpit aperture scan (a 6-byte jsr; on
; the stack the surface, the span output and the transparent key byte; a4 =
; game A4). Before the scan, which redirects the surface's aperture rows to
; new scratch rows, copies the key pixels of the rows from the first to the
; last with a key pixel into the pointer mask: a bit is set where the view
; shows through. Then runs the scan with the caller's stack. Keeps d2-d7/a2-a6
; as a C call.
mouse_scan:
        movem.l d0-d7/a0-a3,-(sp)       ; arguments from 52(sp)
        move.l  stick_ss(pc),d0
        beq.w   .native
        movea.l d0,a1
        lea     SS_SIZE+1(a1),a1        ; mask, pixel 0 of the first row
        movea.l 52(sp),a2               ; surface: row table; x0, y0, x1, y1 at +24
        move.b  60(sp),d1               ; key
        move.w  26(a2),d6
.first:
        cmp.w   30(a2),d6
        bgt.s   .none                   ; no key pixel: no aperture
        move.w  d6,d0
        bsr.w   .haskey
        beq.s   .top
        addq.w  #1,d6
        bra.s   .first
.top:
        move.w  30(a2),d7
.last:
        move.w  d7,d0
        bsr.w   .haskey
        beq.s   .bottom
        subq.w  #1,d7
        bra.s   .last
.none:
        lea     mask_rows(pc),a0        ; every pointer line outside the mask
        clr.w   (a0)
        bra.w   .native
.bottom:
        lea     mask_top(pc),a0
        move.w  d6,(a0)+
        sub.w   d6,d7                   ; rows - 1
        move.w  d7,(a0)
        addq.w  #1,(a0)                 ; mask_rows
.row:
        movea.l a1,a3
        moveq   #40-1,d2
        movea.l (a2),a0
        move.w  d6,d0
        lsl.w   #2,d0
        movea.l (a0,d0.w),a0            ; the row's pixel 0
        tst.w   24(a2)
        bgt.s   .bounded
        cmpi.w  #319,28(a2)
        blt.s   .bounded
.byte:                                  ; the row spans the screen
        moveq   #8-1,d5
.pixel:
        cmp.b   (a0)+,d1
        seq     d0
        add.b   d0,d0
        addx.b  d4,d4
        dbf     d5,.pixel
        move.b  d4,(a3)+
        dbf     d2,.byte
        bra.s   .next
.bounded:
        moveq   #0,d3                   ; x
.bbyte:
        moveq   #8-1,d5
.bpixel:
        moveq   #0,d0
        cmp.w   24(a2),d3
        blt.s   .bit
        cmp.w   28(a2),d3
        bgt.s   .bit
        cmp.b   (a0,d3.w),d1
        seq     d0
.bit:
        add.b   d0,d0
        addx.b  d4,d4
        addq.w  #1,d3
        dbf     d5,.bpixel
        move.b  d4,(a3)+
        dbf     d2,.bbyte
.next:
        lea     MASK_STRIDE(a1),a1
        addq.w  #1,d6
        dbf     d7,.row
.native:
        movem.l (sp)+,d0-d7/a0-a3
        move.l  mouse_scan_native(pc),-(sp)
        rts                             ; the scan returns to the caller
; Z set if row d0 has a key pixel d1 within x0..x1 of surface a2. Uses d0/d2/a0.
.haskey:
        movea.l (a2),a0
        lsl.w   #2,d0
        movea.l (a0,d0.w),a0
        adda.w  24(a2),a0
        move.w  28(a2),d2
        sub.w   24(a2),d2
.search:
        cmp.b   (a0)+,d1
        dbeq    d2,.search
        rts

; The pointer image: the PC version's ring with four ticks, colour 3.
POINTER_H = 9
POINTER_SIZE = 4+POINTER_H*4+4
pointer_lines:
        dc.w    $1c00                   ; ...###...
        dc.w    $6b00                   ; .##.#.##.
        dc.w    $4900                   ; .#..#..#.
        dc.w    $8080                   ; #.......#
        dc.w    $eb80                   ; ###.#.###
        dc.w    $8080
        dc.w    $4900
        dc.w    $6b00
        dc.w    $1c00

ST_LAST = 4                     ; stick record: x.w, y.w, then these
ST_FIELD = 8
ST_USED = 10
ST_SHOWN = 12
ST_MOVED = 14
ST_PTR = 16                     ; pointer offset from the gunsight, half pixels: x.w, y.w

        cnop    0,4
mouse_a4:       dc.l 0
mouse_params:   dc.l 0
mouse_move:     dc.l 0
mouse_x:        dc.w 0                  ; half pixels; mouse_y and mouse_seq follow
mouse_y:        dc.w 0
mouse_seq:      dc.w 0
mouse_seen:     dc.w 0
mouse_last:     dc.w 0,0                ; position the room routine last stored
mouse_active:   dc.w 0
mouse_sum_x:    dc.w 0                  ; counts, wrapping; mouse_sum_y follows
mouse_sum_y:    dc.w 0
mouse_fields:   dc.w 0                  ; VBL fields (mouse_vbl)
stick_x:        dc.w 0                  ; stick units (+-8 steps); stick_y follows
stick_y:        dc.w 0
stick_last:     dc.w 0,0                ; mouse_sum_x/y at the last call
stick_field:    dc.w 0                  ; mouse_fields at the last call
stick_used:     dc.w 0                  ; the mouse has steered this flight
stick_shown:    dc.w 0                  ; the pointer is on screen
stick_moved:    dc.w 0                  ; mouse_fields at the last motion
stick_ptr:      dc.w 0,0                ; pointer offset from the gunsight, half pixels
stick_owned:    dc.w 0                  ; sprite 7: 0 not yet, 1 ours, -1 taken
mask_top:       dc.w 0                  ; screen row of the mask's first row
mask_rows:      dc.w 0                  ; mask rows (0: no aperture)
        cnop    0,4
stick_image:    dc.l 0                  ; Chip pointer image, 0 without one
stick_ss:       dc.l 0                  ; SimpleSprite, then the mask
stick_gfx:      dc.l 0                  ; GfxBase
mouse_scan_native: dc.l 0               ; H0 aperture scan
bank_lists:     dc.l 0,0,0,0            ; per copper list: start, BPLCON4 offset
        even
