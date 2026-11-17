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
; The mouse option (CUSTOM5 bits 4-6, mouse_option) scales every count in
; mouse_event, so all uses below move alike; off makes the variant install
; none of the mouse hooks.
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
; Each move stages the masked lines and the control words, and the VBL
; (stick_commit) writes them to the image together, so the pointer's place
; and the mask under it change in the same field.
; The stick or keys steering, the external view and a new flight re-centre it.
; The pointer appears only once the mouse moves and hides after 10 seconds
; without motion; the variant's VBL hook calls mouse_vbl, which also hides it
; once the controller has stopped running.
;
; The other buttons in flight, as the PC version's reference card: the right
; button held makes mouse motion the stick with fire held (forward and back
; change speed, left and right roll) and holds the pointer still; a double
; click of the right button, held, is the afterburner; both buttons at once,
; or the middle button, fire the selected missile. mouse_vbl reads the
; buttons every field; mouse_poll, after the native flight poll, sets its
; direction and modifier flags and queues the native keys (Tab, Enter).

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
                                ; 26-37: the variant's own (CD32 name entry)
MP_KEYS = 38                    ; A4 offset: key FIFO read index; the write index follows
MP_KEYBUF_A4 = 40               ; A4 offset: the FIFO's 64 bytes, when MP_KEYBUF is 0
MP_KEYBUF = 42                  ; H0 offset: the FIFO's 64 bytes (long), or 0
MP_KEYREAD = 46                 ; H0 offset: the native key read (long)

STICK_LEVEL = 9                 ; stick units per PC step: steps 1-5 and 8 give ramps 1-5 and 9
STICK_STEP = 8                  ; stick units per ramp step: ramps reach +-9
FLIGHT_GAP = 50                 ; fields without a controller call: a new flight
HIDE_GAP = 25                   ; fields without one before the pointer hides
IDLE_GAP = 500                  ; fields without motion before it hides (10 s PAL)
POINTER_SPRITE = 7              ; odd: its colour bank leaves sprites 0-6 alone
SPRITE_BANK = 12                ; odd sprites' colours from 192: sprite 7 colour 3 is 207
MASK_STRIDE = 44                ; bytes per mask row: a pad byte, 40, three pad bytes
MASK_SIZE = 200*MASK_STRIDE     ; the aperture's rows at most
STAGE = SS_SIZE+MASK_SIZE       ; stick_ss offset: the next image's control words and lines
STAGE_SIZE = 4+9*4              ; (POINTER_H lines), copied to the Chip image in the VBL
SS_SIZE = 12                    ; SimpleSprite: posctldata.l, height, x, y, num

; BANK_DIAG (a diagnostic build, never released): counts how the CD32 flight
; pointer's colour bank fares, and with the pointer shown for 250, 1500 and
; 3000 fields saves a snapshot as WCBank1-3 (tools/bank_diag.py reads them).
    ifd BANK_DIAG
D_MAGIC = 0                     ; 'WCBD'
D_VERSION = 4                   ; 1
D_CALLS = 8                     ; stick_bank calls
D_FOUND = 12                    ; BPLCON4 moves found by a search
D_NOTFOUND = 16                 ; searches without one
D_UNDONE = 20                   ; a known move no longer had our bank
D_SHOWN = 24                    ; VBLs with the pointer shown
D_LOF0 = 28                     ; ... GfxBase LOFlist was list 0's start
D_LOF1 = 32                     ; ... list 1's
D_LOFOTHER = 36                 ; ... neither
D_PATCHED = 40                  ; ... that list's BPLCON4 move had our bank
D_UNPATCHED = 44                ; ... it had not
D_ATTACH = 48                   ; ... SPR7CTL had ATTACH
D_INDEX = 52                    ; snapshot number
D_FIELD = 56                    ; mouse_fields
D_GFX = 60                      ; GfxBase LOFlist, SHFlist, copinit
D_TABLE = 72                    ; the game's two cprlist pointers
D_STARTS = 80                   ; their starts
D_BANK = 88                     ; bank_lists (16 bytes)
D_IMAGE = 104                   ; the sprite image's control words, then line 0
D_LASTCON4 = 116                ; last BPLCON4 value seen in the VBL (word)
D_BADCON4 = 118                 ; last value without our bank (word)
D_MAXCOUNT = 120                ; the cprlists' MaxCount words
D_HEADER = 128
D_LIST_SIZE = 4096
D_COPINIT_SIZE = 1024
DIAG_SIZE = D_HEADER+2*D_LIST_SIZE+D_COPINIT_SIZE
    endc

DIAGINC macro
    ifd BANK_DIAG
        move.l  a3,-(sp)
        move.l  diag_buf(pc),-(sp)
        beq.s   .di\@
        movea.l (sp),a3
        addq.l  #1,\1(a3)
.di\@:
        addq.l  #4,sp
        movea.l (sp)+,a3
    endc
    endm
RIGHT_STEP = 4                  ; counts in the last four fields: a direction
CLICK_MAX = 15                  ; fields: a shorter right press is a click
DCLICK_GAP = 15                 ; fields from a click's release to a double click
BURN_REPEAT = 5                 ; fields between the afterburner's Tabs (key repeat)
ESC_AGE = 50                    ; fields: a right press this recent is Esc in a cutscene wait
ROLL_SCALE = 4                  ; the right button's roll: native ramp steps, decay and cap times this

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
        move.l  MP_KEYBUF(a0),d1
        beq.s   .keybuf
        add.l   d0,d1
.keybuf:
        lea     mouse_keybuf(pc),a1
        move.l  d1,(a1)
        move.l  MP_KEYREAD(a0),d1
        add.l   d0,d1
        lea     mouse_keyread(pc),a1
        move.l  d1,(a1)
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
    ifd BANK_DIAG
        move.l  #DIAG_SIZE,d0
        moveq   #0,d1                   ; any memory, uncleared: header set at saving
        jsr     -198(a6)                ; AllocMem
        lea     diag_buf(pc),a1
        move.l  d0,(a1)
        beq.s   .ready
        movea.l d0,a1
        moveq   #D_HEADER/4-1,d1
.clear:
        clr.l   (a1)+
        dbf     d1,.clear
    endc
        move.l  #SS_SIZE+MASK_SIZE+STAGE_SIZE,d0
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
        lea     btn(pc),a0
        clr.w   BT_ESC(a0)              ; room presses are not Esc
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

; The mouse speed option, from the variant's option code before mouse_init:
; d0 = 0 normal, 1 off, 2-7 0.5x, 0.75x, 1.5x, 2x, 3x, 4x (other bits ignored).
; Returns d0 = mouse_speed and Z set when off, which the variant takes as
; "install no mouse patch". Every other register is kept.
mouse_option:
        move.l  a0,-(sp)
        andi.w  #7,d0
        move.b  .speeds(pc,d0.w),d0
        ext.w   d0
        lea     mouse_speed(pc),a0
        move.w  d0,(a0)
        movea.l (sp)+,a0
        tst.w   d0
        rts
.speeds:
        dc.b    4,0,2,3,6,8,12,16       ; quarter counts per mouse count

; RAWMOUSE slot, called from the game's input handler with a3 = event. Each
; relative event's counts are first scaled by mouse_speed, in quarters, the
; remainder carried to the next event; everything below sees only the scaled
; counts. Every relative event also adds to mouse_sum_x/y, which only their
; reader consumes.
; The handler keeps d2/a2/a3 only: preserve everything except d0-d1/a0-a1.
mouse_event:
        tst.b   8(a3)                   ; IEQUALIFIER_RELATIVEMOUSE
        bpl.w   .out
        move.w  10(a3),d0
        or.w    12(a3),d0
        beq.w   .out
        movem.l d2-d3/a2/a4/a6,-(sp)
        move.w  10(a3),d2
        move.w  12(a3),d3
        move.w  mouse_speed(pc),d0
        cmpi.w  #4,d0
        beq.s   .scaled                 ; normal: the counts as they are
        lea     mouse_rem(pc),a0
        muls.w  d0,d2
        add.w   (a0),d2
        moveq   #3,d1
        and.w   d2,d1
        move.w  d1,(a0)+
        asr.w   #2,d2
        muls.w  d0,d3
        add.w   (a0),d3
        moveq   #3,d1
        and.w   d3,d1
        move.w  d1,(a0)
        asr.w   #2,d3
        move.w  d2,d0
        or.w    d3,d0
        beq.w   .done                   ; less than a count so far
.scaled:
        lea     mouse_sum_x(pc),a0      ; running counts for a variant's grid screens
        add.w   d2,(a0)+
        add.w   d3,(a0)
        lea     mouse_active(pc),a0
        tst.w   (a0)
        beq.w   .done
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
        move.w  d2,d0
        moveq   #24,d1
        bsr.s   .axis
        move.w  d3,d0
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
; back (pitch -). While the right button rolls, and until the roll ramp
; settles after it, the roll ramp (d4, which the controller stores next) is
; the native ramp with ROLL_SCALE times its steps, decay and cap, from the
; controller's roll flags in d5 (left) and d6 (right): ROLL_SCALE times the
; roll for the same motion. Every register except d2-d4 is kept.
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
        move.w  btn(pc),d6
        btst    #BT_RIGHT,d6
        beq.s   .free
        moveq   #0,d0                   ; the right button: the motion throttles
        moveq   #0,d4                   ; and rolls, the pointer holds
.free:
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
        lea     roll_mouse(pc),a0
        move.w  btn+BT_NOW(pc),d0
        btst    #BT_RIGHT,d0
        beq.s   .free_roll
        move.w  #1,(a0)                 ; the right button rolls: scaled
        bra.s   .roll
.free_roll:
        tst.w   (a0)
        beq.s   .native_roll
        tst.w   4(a4,d1.w)
        bne.s   .roll
        clr.w   (a0)                    ; released and settled: native again
        bra.s   .native_roll
.roll:
        move.w  4(a4,d1.w),d0           ; the roll ramp before this call
        tst.b   15(sp)                  ; the controller's roll flags: d5 left,
        beq.s   .not_left
        tst.w   d0                      ; d6 right (both: neither)
        ble.s   .roll_left
        moveq   #0,d0
.roll_left:
        subq.w  #ROLL_SCALE,d0
        cmpi.w  #-9*ROLL_SCALE,d0
        bge.s   .roll_store
        moveq   #-9*ROLL_SCALE,d0
        bra.s   .roll_store
.not_left:
        tst.b   19(sp)
        beq.s   .decay
        tst.w   d0
        bge.s   .roll_right
        moveq   #0,d0
.roll_right:
        addq.w  #ROLL_SCALE,d0
        cmpi.w  #9*ROLL_SCALE,d0
        ble.s   .roll_store
        moveq   #9*ROLL_SCALE,d0
        bra.s   .roll_store
.decay:
        cmpi.w  #-2*ROLL_SCALE,d0
        bge.s   .decay_low
        addq.w  #2*ROLL_SCALE,d0
        bra.s   .roll_store
.decay_low:
        cmpi.w  #2*ROLL_SCALE,d0
        ble.s   .settled
        subq.w  #2*ROLL_SCALE,d0
        bra.s   .roll_store
.settled:
        moveq   #0,d0
.roll_store:
        move.w  d0,10(sp)               ; d4: the controller stores it next
.native_roll:
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
        bsr.w   stick_commit
        movem.l d0/a0,-(sp)
        lea     mouse_fields(pc),a0
        addq.w  #1,(a0)
        bsr.w   mouse_buttons
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
        bsr.w   stick_hide
.done:
        movem.l (sp)+,d0/a0
        rts

; Left button in flight: fire while it is held, as the PC's. The game decodes
; its one fire button per field (OCS O:33fa4, CD32 E:33e9e): a click fires
; once at its release, a click and then a hold within the double-click window
; fires while held, and a hold alone is the modifier (directions throttle and
; roll) after the hold threshold (15 fields). So the left button held after a
; pause never fired. From the variant's port-1 sampler, before the native
; decode: a0 = the port-1 record, a1 = its offsets (bytes: double-click flag,
; click counter, hold threshold), d1.b bit 6 = left button down, bit 7 = the
; native button (pad red, stick fire) down. A left button press while the
; flight controller runs, with the native button up, is decoded as the second
; press of a double click, with held fire at once; the hold keeps the counter
; at the threshold, so it fires and is never the modifier. A release before
; the threshold also latches the click, so a short click that falls between
; two world ticks still fires. Without a flight, or with the native button,
; the native decode is unchanged. Keeps every register.
mouse_flight_fire:
        movem.l d0/d2-d3/a2,-(sp)
        moveq   #0,d2
        move.b  1(a1),d2                ; click counter
        moveq   #0,d3
        move.b  2(a1),d3
        move.w  (a0,d3.w),d3            ; hold threshold
        lea     fire_held(pc),a2
        tst.w   (a2)
        bne.s   .forced
        btst    #7,d1
        bne.s   .done                   ; the native button: its own scheme
        btst    #6,d1
        beq.s   .done
        tst.b   4(a0)
        bne.s   .done                   ; held since before: native
        move.w  mouse_fields(pc),d0
        sub.w   stick_field(pc),d0
        cmpi.w  #HIDE_GAP,d0
        bhi.s   .done                   ; no flight
        tst.w   (a0,d2.w)
        bmi.s   .done                   ; the screen's release guard
        move.w  #1,(a0,d2.w)            ; the second press of a double click
        st      8(a0)                   ; held fire now
        move.w  #1,(a2)                 ; fields held, counting this one
        bra.s   .done
.forced:
        tst.w   (a0,d2.w)
        bmi.s   .end                    ; the record was reset: native again
        btst    #6,d1
        beq.s   .release
        addq.w  #1,(a2)
        move.w  d3,(a0,d2.w)            ; held: fire, not the modifier
        bra.s   .done
.release:
        clr.b   5(a0)                   ; the release decode keeps it a field
        cmp.w   (a2),d3
        bls.s   .end
        move.b  #1,7(a0)                ; a short click: its shot is latched
.end:
        clr.w   (a2)
.done:
        movem.l (sp)+,d0/d2-d3/a2
        rts

; The buttons, every field (mouse_vbl): left CIA-A PRA bit 6, right and
; middle POTINP bits 10 and 8, low when down (CD32: Psygore's pad read leaves
; POTGO at $ffff, so both lines are pulled up). The right or middle button
; counts only once its line has read up, so a line that reads low without a
; mouse button on it does nothing. Keeps the last four fields' motion for
; mouse_poll. In flight: a right press within DCLICK_GAP fields of
; a click's release (a press shorter than CLICK_MAX) is the afterburner while
; held; both buttons going down together, or a middle press, is a missile for
; mouse_poll to queue. Keeps every register.
mouse_buttons:
        movem.l d0-d3/a0-a1,-(sp)
        moveq   #0,d0
        btst    #6,$bfe001
        bne.s   .left
        bset    #BT_LEFT,d0
.left:
        move.w  $dff016,d1
        btst    #10,d1
        bne.s   .right
        bset    #BT_RIGHT,d0
.right:
        btst    #8,d1
        bne.s   .middle
        bset    #BT_MIDDLE,d0
.middle:
        lea     btn(pc),a0
        moveq   #6,d1                   ; right and middle seen up: real lines
        eor.w   d0,d1
        and.w   #6,d1
        or.w    d1,BT_SEEN(a0)
        move.w  BT_SEEN(a0),d1
        bset    #BT_LEFT,d1
        and.w   d1,d0                   ; a line never seen up stays up
        move.w  BT_NOW(a0),d1           ; the last field's
        move.w  d0,BT_NOW(a0)
        btst    #BT_RIGHT,d0
        beq.s   .no_esc
        btst    #BT_RIGHT,d1
        bne.s   .no_esc
        move.w  #1,BT_ESC(a0)           ; a right press: Esc for a cutscene wait
        move.w  mouse_fields(pc),BT_ESCAT(a0)
.no_esc:
        move.w  BT_IDX(a0),d2
        addq.w  #2,d2
        andi.w  #6,d2
        move.w  d2,BT_IDX(a0)
        lea     BT_DX(a0,d2.w),a1
        move.w  mouse_sum_x(pc),d3      ; this field's motion
        sub.w   BT_LAST(a0),d3
        add.w   d3,BT_LAST(a0)
        move.w  d3,(a1)
        move.w  mouse_sum_y(pc),d3
        sub.w   BT_LAST+2(a0),d3
        add.w   d3,BT_LAST+2(a0)
        move.w  d3,BT_DY-BT_DX(a1)
        move.w  mouse_fields(pc),d3
        sub.w   stick_field(pc),d3
        cmpi.w  #HIDE_GAP,d3
        bls.s   .flight
        clr.w   BT_BURN(a0)             ; no flight
        clr.w   BT_MISSILE(a0)
        clr.w   BT_SHORT(a0)
        bra.w   .done
.flight:
        btst    #BT_RIGHT,d0
        beq.s   .up
        btst    #BT_RIGHT,d1
        bne.s   .held
        clr.w   BT_HELD(a0)             ; pressed
        tst.w   BT_SHORT(a0)
        beq.s   .held
        cmpi.w  #DCLICK_GAP,BT_GAP(a0)
        bhi.s   .held
        move.w  #1,BT_BURN(a0)          ; a double click
.held:
        cmpi.w  #CLICK_MAX,BT_HELD(a0)
        bhs.s   .missile
        addq.w  #1,BT_HELD(a0)
        bra.s   .missile
.up:
        btst    #BT_RIGHT,d1
        beq.s   .gap
        clr.w   BT_SHORT(a0)            ; released
        clr.w   BT_GAP(a0)
        tst.w   BT_HELD(a0)
        beq.s   .long                   ; no press seen (the first field)
        cmpi.w  #CLICK_MAX,BT_HELD(a0)
        bhs.s   .long
        tst.w   BT_BURN(a0)
        bne.s   .long                   ; a double click's second press
        move.w  #1,BT_SHORT(a0)
.long:
        clr.w   BT_BURN(a0)
.gap:
        cmpi.w  #DCLICK_GAP,BT_GAP(a0)
        bhi.s   .missile
        addq.w  #1,BT_GAP(a0)
.missile:
        moveq   #3,d2                   ; left and right
        and.w   d0,d2
        subq.w  #3,d2
        bne.s   .mid
        moveq   #3,d2
        and.w   d1,d2
        subq.w  #3,d2
        beq.s   .mid
        move.w  #1,BT_MISSILE(a0)       ; both down now, not before
.mid:
        btst    #BT_MIDDLE,d0
        beq.s   .done
        btst    #BT_MIDDLE,d1
        bne.s   .done
        move.w  #1,BT_MISSILE(a0)
.done:
        movem.l (sp)+,d0-d3/a0-a1
        rts

; From the variant's hook after the native flight poll has stored its flags
; (left, right, up, down, modifier, fire; a4 = game A4). In flight, with the
; right button held: the modifier, the mouse's last four fields of motion as
; directions, and no gun fire (the left button is then the missile). Queues
; a pending missile's Enter, and the afterburner's Tab at once and every
; BURN_REPEAT fields while it is held, as a held Tab's key repeat does: the
; native command loop takes them as keys. The poll also runs in the rooms:
; there, and with no flight, it does nothing. Keeps every register.
mouse_poll:
        movem.l d0-d1/a0-a1,-(sp)
        lea     btn(pc),a1
        move.w  mouse_fields(pc),d0
        sub.w   stick_field(pc),d0
        cmpi.w  #HIDE_GAP,d0
        bls.s   .flight
        clr.w   BT_MISSILE(a1)
        bra.w   .done
.flight:
        clr.w   BT_ESC(a1)              ; flight presses are not Esc
        movea.l mouse_params(pc),a0
        move.w  MP_FLAGS(a0),d0
        lea     (a4,d0.w),a0
        btst    #BT_RIGHT,BT_NOW+1(a1)
        beq.s   .keys
        move.b  #1,4(a0)                ; the modifier: throttle and roll
        clr.b   5(a0)
        move.w  BT_DX(a1),d0
        add.w   BT_DX+2(a1),d0
        add.w   BT_DX+4(a1),d0
        add.w   BT_DX+6(a1),d0
        moveq   #0,d1
        bsr.s   .axis
        move.w  BT_DY(a1),d0
        add.w   BT_DY+2(a1),d0
        add.w   BT_DY+4(a1),d0
        add.w   BT_DY+6(a1),d0
        moveq   #2,d1                   ; forward (up) is faster
        bsr.s   .axis
.keys:
        tst.w   BT_MISSILE(a1)
        beq.s   .burn
        clr.w   BT_MISSILE(a1)
        moveq   #13,d0                  ; Enter: the selected missile
        bsr.s   mouse_key
.burn:
        tst.w   BT_BURN(a1)
        bne.s   .burning
        clr.w   BT_SENT(a1)
        bra.s   .done
.burning:
        move.w  mouse_fields(pc),d0
        tst.w   BT_SENT(a1)
        beq.s   .tab
        move.w  d0,d1
        sub.w   BT_TAB(a1),d1
        cmpi.w  #BURN_REPEAT,d1
        blo.s   .done
.tab:
        move.w  #1,BT_SENT(a1)
        move.w  d0,BT_TAB(a1)
        moveq   #9,d0                   ; Tab: the afterburner
        bsr.s   mouse_key
.done:
        movem.l (sp)+,d0-d1/a0-a1
        rts
; Flag d1(a0) (negative) or d1+1(a0) (positive) for the motion d0.
.axis:
        cmpi.w  #-RIGHT_STEP,d0
        bgt.s   .plus
        move.b  #1,(a0,d1.w)
.plus:
        cmpi.w  #RIGHT_STEP,d0
        blt.s   .none
        move.b  #1,1(a0,d1.w)
.none:
        rts

; Queue key d0.b in the game's key FIFO as its input handler does (OCS
; O:344fa, CD32 E:342a6): the byte at the write index, which then advances
; unless the FIFO is full. The handler runs in input.device's task, so
; Forbid keeps it out. a4 = game A4. Keeps every register.
mouse_key:
        movem.l d0-d2/a0-a1/a6,-(sp)
        movea.l mouse_params(pc),a0
        move.w  MP_KEYS(a0),d1
        lea     (a4,d1.w),a1            ; read index, write index
        move.l  mouse_keybuf(pc),d2
        bne.s   .buffer
        move.w  MP_KEYBUF_A4(a0),d2
        lea     (a4,d2.w),a0
        bra.s   .queue
.buffer:
        movea.l d2,a0
.queue:
        movea.l 4.w,a6
        jsr     -132(a6)                ; Forbid
        move.w  2(a1),d1
        move.w  d1,d2
        addq.w  #1,d2
        andi.w  #63,d2
        cmp.w   (a1),d2
        beq.s   .full
        move.b  d0,(a0,d1.w)
        move.w  d2,2(a1)
.full:
        jsr     -138(a6)                ; Permit
        movem.l (sp)+,d0-d2/a0-a1/a6
        rts

; Replaces the native key read call (6 bytes) in the cutscene waits that
; turn Esc into the game's abort flag: the key-or-fire wait (OCS O:180ce,
; CD32 E:18990, G:18a4a) and the timed wait (O:1814c, E:18a90, G:18b4a).
; A right press in the last ESC_AGE fields reads as Esc (27), once; else the
; native read. Flight, the rooms and the name entry drop their presses, so
; the right button is Esc only here. Returns d0 as the native read does.
mouse_esc:
        move.l  a0,-(sp)
        lea     btn(pc),a0
        tst.w   BT_ESC(a0)
        beq.s   .native
        clr.w   BT_ESC(a0)
        move.w  mouse_fields(pc),d0
        sub.w   BT_ESCAT(a0),d0
        cmpi.w  #ESC_AGE,d0
        bhi.s   .native                 ; stale
        movea.l (sp)+,a0
        moveq   #27,d0
        rts
.native:
        movea.l (sp)+,a0
        move.l  mouse_keyread(pc),-(sp)
        rts

; Hide the flight pointer by clearing its image's control words, with no
; library call. Keeps every register.
stick_hide:
        movem.l d0/a0,-(sp)
        lea     stick_shown(pc),a0
        clr.w   (a0)
        lea     stick_pending(pc),a0
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
        lea     stick_pending(pc),a0    ; the VBL leaves the staging alone
        clr.w   (a0)
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
    ifd BANK_DIAG
        bsr.w   diag_save
    endc
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
        lea     STAGE+4(a5),a1          ; the staging lines
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
        ; MoveSprite writes the control words to the Chip image (posctldata;
        ; it also points the sprite's DMA there): take them to the staging and
        ; put the shown ones back, with the VBL held off.
        movea.l 4.w,a6
        jsr     -120(a6)                ; Disable
        movea.l stick_gfx(pc),a6
        move.l  (a3),-(sp)              ; the shown control words
        suba.l  a0,a0
        movea.l a5,a1
        jsr     -426(a6)                ; MoveSprite
        move.l  (a3),STAGE(a5)
        move.l  (sp)+,(a3)
        lea     stick_pending(pc),a0
        move.w  #1,(a0)
        movea.l 4.w,a6
        jsr     -126(a6)                ; Enable
.done:
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        rts

; From mouse_vbl, first: the pointer's staged control words and lines, which
; stick_show wrote together, to the Chip image, so the position and the mask
; under it change in the same field. Keeps every register.
        if POINTER_SPRITE<>7
        fail    "stick_commit writes sprite 7's registers"
        endif
stick_commit:
        movem.l d0/a0-a1,-(sp)
        lea     stick_pending(pc),a0
        tst.w   (a0)
        beq.s   .done
        clr.w   (a0)
        movea.l stick_ss(pc),a0
        lea     STAGE+STAGE_SIZE(a0),a0
        movea.l stick_image(pc),a1
        lea     STAGE_SIZE(a1),a1
        moveq   #STAGE_SIZE/4-1,d0
.copy:                                  ; backwards: the control words last
        move.l  -(a0),-(a1)
        dbf     d0,.copy
        ; The VBL can end after sprite DMA has fetched this field's control
        ; words (line 25): the same words to the registers, before the
        ; sprite's first line (VSTART 40 at the highest).
        move.l  (a1),$dff178            ; SPR7POS, SPR7CTL
.done:
        movem.l (sp)+,d0/a0-a1
    ifd BANK_DIAG
        bra.w   diag_vbl
    endc
        rts

; CD32: the odd sprites' colour bank in each of the game's two flight copper
; lists (their BPLCON4 move, found once per list). OCS has no bank (0).
; a4 = game A4; uses d0-d3/a0-a2.
BANK_SEARCH = 1024              ; copper moves searched for BPLCON4
    ifd BANK_DIAG
stick_bank:
        DIAGINC D_CALLS
        movea.l mouse_params(pc),a1
        move.w  MP_COPPER(a1),d0
        beq.w   .done
        lea     (a4,d0.w),a1            ; two cprlist pointers
        lea     bank_lists(pc),a2       ; per list: start.l, offset.w, pad
        moveq   #2-1,d1
.list:
        move.l  (a1)+,d0
        beq.w   .next
        movea.l d0,a0
        move.l  4(a0),d0                ; cprlist start
        beq.w   .next
        movea.l d0,a0
        cmp.l   (a2),d0
        bne.w   .find
        move.w  4(a2),d2
        cmpi.w  #$010c,(a0,d2.w)
    ifd BANK_DIAG
        bne.w   .find
        moveq   #$f,d0                  ; still our bank since the last call?
        and.b   3(a0,d2.w),d0
        cmpi.b  #SPRITE_BANK,d0
        beq.w   .set
        DIAGINC D_UNDONE
        bra.w   .set
    else
        beq.w   .set
    endc
.find:
        clr.l   (a2)
        moveq   #0,d2
        move.w  #BANK_SEARCH-1,d3
.search:
        cmpi.w  #$010c,(a0,d2.w)
        beq.s   .found
        cmpi.l  #$fffffffe,(a0,d2.w)
        beq.w   .none                   ; no BPLCON4: search again next time
        addq.w  #4,d2
        dbf     d3,.search
.none:
        DIAGINC D_NOTFOUND
        bra.w   .next
.found:
        DIAGINC D_FOUND
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
    else
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
    endc

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

BT_LEFT = 0                     ; button bits
BT_RIGHT = 1
BT_MIDDLE = 2
BT_NOW = 0                      ; button record: the buttons this field
BT_HELD = 2                     ; fields the right button has been held (to CLICK_MAX)
BT_GAP = 4                      ; fields since its release (to DCLICK_GAP+1)
BT_SHORT = 6                    ; its last press was a click
BT_BURN = 8                     ; the afterburner: a double click's second press, held
BT_MISSILE = 10                 ; a missile press for mouse_poll
BT_SENT = 12                    ; mouse_poll: a Tab queued for this press
BT_TAB = 14                     ; mouse_poll: mouse_fields at the last Tab
BT_IDX = 16                     ; this field's motion slot, 0-6
BT_LAST = 18                    ; mouse_sum_x/y at the last field
BT_DX = 22                      ; the last four fields' x motion
BT_DY = 30                      ; and y motion
BT_SEEN = 38                    ; button bits whose line has read up
BT_ESC = 40                     ; a right press not yet taken (mouse_esc)
BT_ESCAT = 42                   ; mouse_fields at that press

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
mouse_speed:    dc.w 4                  ; quarter counts per mouse count (mouse_option)
mouse_rem:      dc.w 0,0                ; x, y quarters not yet a count
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
stick_pending:  dc.w 0                  ; the staging holds an image for the next VBL
roll_mouse:     dc.w 0                  ; the right button has rolled: scaled until the ramp settles
fire_held:      dc.w 0                  ; left button fire: fields held (0: native)
btn:            dc.w 7                  ; button record (BT_): all down, so no first press
                dcb.w 21,0
        cnop    0,4
mouse_keybuf:   dc.l 0                  ; the key FIFO, 0: at MP_KEYBUF_A4
mouse_keyread:  dc.l 0                  ; the native key read
stick_image:    dc.l 0                  ; Chip pointer image, 0 without one
stick_ss:       dc.l 0                  ; SimpleSprite, then the mask
stick_gfx:      dc.l 0                  ; GfxBase
mouse_scan_native: dc.l 0               ; H0 aperture scan
bank_lists:     dc.l 0,0,0,0            ; per copper list: start, BPLCON4 offset
    ifd BANK_DIAG
diag_buf:       dc.l 0
diag_shown:     dc.w 0                  ; VBLs with the pointer shown
diag_due:       dc.w 0                  ; a snapshot to save at the next show
diag_saved:     dc.w 0
diag_name:      dc.b 'WCBank0',0
        even

; From the VBL, after the commit: where COP2LC points (the game sets GfxBase
; LOFlist with it) and whether that list's BPLCON4 move has our bank.
diag_vbl:
        movem.l d0-d2/a0-a2,-(sp)
        move.l  diag_buf(pc),d0
        beq.w   .done
        movea.l d0,a2
        lea     stick_x(pc),a0
        tst.w   ST_SHOWN(a0)
        beq.w   .done
        addq.l  #1,D_SHOWN(a2)
        movea.l stick_gfx(pc),a0
        move.l  50(a0),d0               ; LOFlist
        lea     bank_lists(pc),a1
        cmp.l   (a1),d0
        beq.s   .list0
        cmp.l   8(a1),d0
        beq.s   .list1
        addq.l  #1,D_LOFOTHER(a2)
        bra.s   .ctl
.list0:
        addq.l  #1,D_LOF0(a2)
        bra.s   .check
.list1:
        addq.l  #1,D_LOF1(a2)
        addq.l  #8,a1
.check:
        movea.l d0,a0
        move.w  4(a1),d1
        move.w  2(a0,d1.w),d2
        move.w  d2,D_LASTCON4(a2)
        moveq   #$f,d1
        and.w   d2,d1
        cmpi.w  #SPRITE_BANK,d1
        bne.s   .unpatched
        addq.l  #1,D_PATCHED(a2)
        bra.s   .ctl
.unpatched:
        addq.l  #1,D_UNPATCHED(a2)
        move.w  d2,D_BADCON4(a2)
.ctl:
        movea.l stick_image(pc),a0
        btst    #7,3(a0)                ; SPR7CTL ATTACH
        beq.s   .count
        addq.l  #1,D_ATTACH(a2)
.count:
        lea     diag_shown(pc),a0
        addq.w  #1,(a0)
        move.w  (a0),d0
        cmpi.w  #250,d0
        beq.s   .due
        cmpi.w  #1500,d0
        beq.s   .due
        cmpi.w  #3000,d0
        bne.s   .done
.due:
        lea     diag_due(pc),a0
        move.w  #1,(a0)
.done:
        movem.l (sp)+,d0-d2/a0-a2
        rts

; From stick_show (the game's main code; a4 = game A4): a due snapshot.
diag_save:
        movem.l d0-d7/a0-a6,-(sp)
        lea     diag_due(pc),a0
        tst.w   (a0)
        beq.w   .done
        clr.w   (a0)
        move.l  diag_buf(pc),d0
        beq.w   .done
        movea.l d0,a2
        move.l  #'WCBD',D_MAGIC(a2)
        moveq   #1,d0
        move.l  d0,D_VERSION(a2)
        lea     diag_saved(pc),a0
        addq.w  #1,(a0)
        moveq   #0,d0
        move.w  (a0),d0
        move.l  d0,D_INDEX(a2)
        lea     diag_name+6(pc),a0
        addi.b  #'0',d0
        move.b  d0,(a0)
        moveq   #0,d0
        move.w  mouse_fields(pc),d0
        move.l  d0,D_FIELD(a2)
        movea.l stick_gfx(pc),a0
        move.l  50(a0),D_GFX(a2)
        move.l  54(a0),D_GFX+4(a2)
        move.l  38(a0),D_GFX+8(a2)
        movea.l mouse_params(pc),a1
        move.w  MP_COPPER(a1),d0
        lea     (a4,d0.w),a1
        lea     D_HEADER(a2),a3         ; list copies
        moveq   #0,d1                   ; list 0, 1
.list:
        move.l  (a1)+,d0
        move.l  d0,D_TABLE(a2,d1.w*4)
        beq.s   .nolist
        movea.l d0,a0
        move.w  8(a0),D_MAXCOUNT(a2,d1.w*2)
        move.l  4(a0),d0
        move.l  d0,D_STARTS(a2,d1.w*4)
        beq.s   .nolist
        movea.l d0,a0
        movea.l a3,a5
        move.w  #D_LIST_SIZE/4-1,d2
.copy:
        move.l  (a0)+,(a5)+
        dbf     d2,.copy
.nolist:
        lea     D_LIST_SIZE(a3),a3
        addq.w  #1,d1
        cmpi.w  #2,d1
        bcs.s   .list
        move.l  D_GFX+8(a2),d0          ; copinit
        beq.s   .bank
        movea.l d0,a0
        move.w  #D_COPINIT_SIZE/4-1,d2
.copinit:
        move.l  (a0)+,(a3)+
        dbf     d2,.copinit
.bank:
        lea     bank_lists(pc),a0
        lea     D_BANK(a2),a1
        moveq   #4-1,d2
.copybank:
        move.l  (a0)+,(a1)+
        dbf     d2,.copybank
        movea.l stick_image(pc),a0
        move.l  (a0)+,D_IMAGE(a2)
        move.l  (a0),D_IMAGE+4(a2)
        move.l  stick_ss(pc),D_IMAGE+8(a2)
        lea     diag_name(pc),a0
        movea.l a2,a1
        move.l  #DIAG_SIZE,d0
        movea.l slave+$121e(pc),a2
        jsr     12(a2)                  ; resload_SaveFile
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts
    endc
        even
