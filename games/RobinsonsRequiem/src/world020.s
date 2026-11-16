; The world on the cap's grid, frames between the player's runs and frames between world
; passes for the ECS game on the 68020 and up (docs/performance.md, ECS plan steps 9 and 10;
; docs/internals.md, "ECS improvements", items 5 and 6): the AGA slave's plan steps 7, 8, 9,
; 10.1, 10.4 and 11 (RobinSonSRequiemAga.asm, _worldpatch, _swappatch and _prespatch;
; docs/internals.md, "AGA improvements", items 6-8, 11 and 12) at the ECS sites ("The AGA's
; sites in the ECS game"). RobinsonSRequiemEcs.asm includes it and calls _worldpatch,
; _swappatch and _prespatch when WHDLoad's AttnFlags have the 68020 bit; the 68000 keeps
; START's own pacing. The ECS frame routine and MAIN loop are the AGA's instruction for
; instruction, their hunk 1 variables $19aa lower and the frame routine $193c lower; the 3D
; view, the objects' frames and the element table have the AGA's layout. Assembled for the
; 68020: hunk 1 offsets above $7fff are base displacements.

        MC68020

**********************************************
; The world on the cap's grid (the AGA's plan step 7). MAIN runs the due script objects,
; then the frame routine (hunk 1 +$3076: the cap wait, the drawing, the swap), and again;
; an object is due once the VBL count (+$d4c2) passes its next run (-62(a6)), its last
; run's count plus its period (-58(a6)). In 3D mode (+$d459) a world count W takes the VBL
; count's place: W goes up by the cap (+$d4c0, 3 fields) per pass, each pass waits at its
; end for the VBL count to reach W, and while W is a pass or more behind at the list's end
; MAIN goes round the list again without the frame routine, at most twice in a row; three
; passes or more behind (a load, a pause) W is set to the count.
; - hunk 1 +$d22 movea.l <+$d4c2>,a3 (the scheduler's due test) becomes jsr _wa3
; - +$4b44 movea.l <+$d4c2>,a0 (op $36, the period) becomes jsr _wa0
; - +$cb2 bsr.w +$3076, bra.s +$cbe (the list's end) becomes jsr _listend
; - +$30ac move.b <+$d4c0>,d0 (the cap, for the wait at +$30b2) becomes jsr _capwait
; - +$3218 movem.l (sp)+,d0-a6 and rts (the frame routine's end) become jmp _passend, which
;   waits for W (the AGA's plan step 10.1: the wait at the pass's end)
; and, when they check:
; - +$3252 jsr +$8a10 (the 3D view's drawing) becomes jsr _view (the AGA's plan step 8)
; - +$2f44 movea.l <+$d3dc>,a1 (an object's elements moved) becomes jsr _emove (step 9)

_worldpatch
        move.l  _hunk1(pc),a0
        lea     .sites(pc),a2
.chk    move.l  (a2)+,d0
        beq     .ok
        move.w  (a2)+,d2
        move.l  (a2)+,d3
        add.l   a0,d3                   ; the absolute operand
        cmp.w   (a0,d0.l),d2
        bne     .no
        cmp.l   2(a0,d0.l),d3
        bne     .no
        bra     .chk
.ok     lea     $cb2(a0),a1
        cmp.l   #$610023c2,(a1)         ; bsr.w +$3076
        bne     .no
        cmp.w   #$6006,4(a1)            ; bra.s +$cbe
        bne     .no
        cmp.l   #$4cdf7fff,$3218(a0)    ; movem.l (sp)+,d0-a6, rts: the frame routine's end
        bne     .no
        cmp.w   #$4e75,$321c(a0)
        bne     .no
        cmp.w   #$4a39,$3086(a0)        ; the frame routine's tst.b <+$d459>
        bne     .no
        lea     H1_3D(a0),a3
        cmp.l   $3088(a0),a3
        bne     .no
        lea     _wvars(pc),a2
        lea     H1_VBL(a0),a3
        move.l  a3,W_VBL(a2)
        move.l  a3,W_PTR(a2)
        lea     H1_CAP(a0),a3
        move.l  a3,W_CAP(a2)
        lea     H1_3D(a0),a3
        move.l  a3,W_3D(a2)
        lea     $3076(a0),a3
        move.l  a3,W_FRAME(a2)
        lea     H1_OBJTAB(a0),a3
        move.l  a3,W_OBJTAB(a2)
        lea     H1_VFLAGS(a0),a3
        move.l  a3,W_FLAGS(a2)
        lea     $3252(a0),a3
        cmp.w   #$4eb9,(a3)
        bne     .noview
        lea     $8a10(a0),a4
        cmp.l   2(a3),a4
        bne     .noview
        move.l  a4,W_DRAW(a2)
        move.w  #$4eb9,(a3)
        pea     _view(pc)
        move.l  (a7)+,2(a3)
.noview
        move.w  #$4eb9,d1
        move.w  d1,(a1)
        pea     _listend(pc)
        move.l  (a7)+,2(a1)
        lea     $d22(a0),a1
        move.w  d1,(a1)
        pea     _wa3(pc)
        move.l  (a7)+,2(a1)
        lea     $4b44(a0),a1
        move.w  d1,(a1)
        pea     _wa0(pc)
        move.l  (a7)+,2(a1)
        lea     $30ac(a0),a1
        move.w  d1,(a1)
        pea     _capwait(pc)
        move.l  (a7)+,2(a1)
        lea     $3218(a0),a1
        move.w  #$4ef9,(a1)
        pea     _passend(pc)
        move.l  (a7)+,2(a1)
        lea     $2f44(a0),a3            ; step 9, when it checks and its table is allocated
        cmp.w   #$2279,(a3)
        bne     .noelem
        lea     H1_ELEM(a0),a4
        cmp.l   2(a3),a4
        bne     .noelem
        move.l  a4,W_ELEM(a2)
        lea     H1_PREVH(a0),a4
        move.l  a4,W_PREVH(a2)
        movem.l d1/a0-a1/a6,-(a7)
        move.l  #ESLOTS*ESIZE,d0
        move.l  #MEMF_PUBLIC|MEMF_CLEAR,d1
        move.l  4.w,a6
        jsr     _LVOAllocMem(a6)
        movem.l (a7)+,d1/a0-a1/a6
        move.l  d0,W_ETAB(a2)
        beq     .noelem
        move.w  #$4eb9,(a3)
        pea     _emove(pc)
        move.l  (a7)+,2(a3)
.noelem
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts
.sites  dc.l    $d22
        dc.w    $2679
        dc.l    H1_VBL
        dc.l    $4b44
        dc.w    $2079
        dc.l    H1_VBL
        dc.l    $30ac
        dc.w    $1039
        dc.l    H1_CAP
        dc.l    0

; hunk 1 variables (the AGA's less $19aa)
H1_VBL          = $d4c2                 ; the VBL count
H1_CAP          = $d4c0                 ; the cap; +1 the fields since the frame routine's start
H1_3D           = $d459                 ; 3D mode
H1_OBJTAB       = $d3c2                 ; MAIN's object table
H1_ELEM         = $d3dc                 ; the 3D elements' table
H1_PREVH        = $d40e                 ; the heading before an object's run
H1_VFLAGS       = $d54b                 ; per-frame flags: +$d54b, +$d581, +$d580 (countdown)
H1_CDOWN        = $d580                 ; the scripts' countdown
H1_RECTLIST     = $d45e                 ; the rectangle list's end
H1_RECT         = $d430                 ; the drawing's rectangle, +$d430-+$d439
H1_PTRSTATE     = $d3ed                 ; the pointer: +$d3ed state, +$d3ee, +$d3ef redraw
H1_SWAPNOW      = $d426                 ; the wait and the block at the pass's start
H1_VIEWS        = $d425                 ; cleared at the views' end

; the count the objects run by: W in 3D mode, the VBL count otherwise
_wa3    move.l  _wvars+W_PTR(pc),a3
        move.l  (a3),a3
        rts
_wa0    move.l  _wvars+W_PTR(pc),a0
        move.l  (a0),a0
        rts

; the list's end: a catch-up pass (back to +$cbe without the frame routine) while W is a
; pass or more behind, at most twice in a row; the frame routine otherwise
_listend
        addq.l  #6,(a7)                 ; +$cb8 -> +$cbe
        bsr     _isample
        movem.l d0-d2/a0-a1,-(a7)
        lea     _wvars(pc),a1
        tst.b   W_ON(a1)
        beq     .frame
        move.l  W_3D(a1),a0
        tst.b   (a0)
        beq     .frame
        move.l  W_CAP(a1),a0
        moveq   #0,d1
        move.b  (a0),d1
        beq     .frame
        move.l  W_VBL(a1),a0
        move.l  (a0),d0
        sub.l   W_W(a1),d0              ; fields behind
        cmp.l   d1,d0
        blt     .frame                  ; less than a pass
        move.l  d1,d2
        add.l   d2,d2
        add.l   d1,d2
        cmp.l   d2,d0
        bge     .rebase
        cmp.b   #2,W_CATCH(a1)
        bhs     .frame
        addq.b  #1,W_CATCH(a1)
        add.l   d1,W_W(a1)
        movem.l (a7)+,d0-d2/a0-a1
        rts
.rebase move.l  (a0),d0                 ; W = the count less the cap, which the frame
        sub.l   d1,d0                   ; routine's end adds back
        move.l  d0,W_W(a1)
.frame  clr.b   W_CATCH(a1)
        movem.l (a7)+,d0-d2/a0-a1
        move.l  _wvars+W_FRAME(pc),-(a7)
        rts

; d0.b the cap for the wait at +$30b2, as START's move.b (the rest of d0 kept); in 3D mode
; 0 (no wait: the wait for W is at the pass's end, _passend) and the drawing's time, W plus
; the cap
_capwait
        movem.l d1/a0-a1,-(a7)
        lea     _wvars(pc),a1
        move.l  W_CAP(a1),a0
        move.b  (a0),d0
        beq     .off
        move.l  W_3D(a1),a0
        tst.b   (a0)
        beq     .off
        move.l  W_VBL(a1),a0
        tst.b   W_ON(a1)
        bne     .on
.start  cmp.b   -1(a0),d0               ; 3D starts: START's cap wait (+$d4c1), then W
        bhi     .start                  ; from the count
        move.l  (a0),W_W(a1)
        st      W_ON(a1)
        lea     W_W(a1),a0
        move.l  a0,W_PTR(a1)
.on     moveq   #0,d1
        move.b  d0,d1
        add.l   W_W(a1),d1
        IFND PRESENT_OFF
        tst.b   _pvars+P_ON(pc)         ; the AGA's plan step 11: the field the frame shows
        beq     .t                      ; in, at most W plus the cap (W, the next pass's
        movem.l d0/d2/a0,-(a7)          ; count, in a presentation frame)
        lea     _pvars(pc),a0
        move.l  d1,d2
        tst.b   P_IN(a0)
        beq     .t1
        move.l  W_W(a1),d2
.t1     bsr     _now
        move.l  d0,P_T0(a0)
        st      P_TIMED(a0)
        sf      P_ACC(a0)
        bsr     _pwhen
        move.l  d2,d1
        movem.l (a7)+,d0/d2/a0
.t
        ENDC
        move.l  d1,W_DRAWT(a1)
        clr.b   d0
        movem.l (a7)+,d1/a0-a1
        rts
.off    sf      W_ON(a1)
        move.l  W_VBL(a1),W_PTR(a1)
        movem.l (a7)+,d1/a0-a1
        rts

; the frame routine's end (+$3218): in 3D mode W goes up by the cap and the pass waits for
; the count to reach it, so the next list runs at its time and the next drawing starts as
; soon as that list has run
_passend
        movem.l (a7)+,d0-a6
        tst.b   _pvars+P_IN(pc)
        bne     .pres                   ; a presentation frame's end: back to _present
        movem.l d1/a0-a1,-(a7)
        lea     _wvars(pc),a1
        tst.b   W_ON(a1)
        beq     .out
        move.l  W_3D(a1),a0
        tst.b   (a0)
        beq     .out
        move.l  W_CAP(a1),a0
        moveq   #0,d1
        move.b  (a0),d1
        beq     .out
        add.l   W_W(a1),d1
        move.l  d1,W_W(a1)
        bsr     _present                ; the AGA's plan step 11: frames while there is time
        move.l  W_VBL(a1),a0
.wait   cmp.l   (a0),d1                 ; until the count reaches W
        bhi     .wait
.out    movem.l (a7)+,d1/a0-a1
.pres   rts

**********************************************
; Frames between world passes (the AGA's plan step 11). After a world pass's frame, while
; the next pass is not due, _passend draws again: START's frame routine from +$3086 (past
; +$3076's operand reads from the list's script stream), as on a pass on which no object
; was due, with the camera and the staged elements at the field the frame will show in.
; Per-pass work stays on world passes: the scripts' countdown (+$329a subq.b #1,<+$d580>,
; checked first, becomes jsr _cdown, which skips it in a presentation frame; _view skips it
; too), the view's velocity (+$3044, on the game's own changes only) and the objects'
; sampling (_listend). A presentation frame is drawn only when the last frame drawn was
; staged (the camera, or an element), when its field is later than the last frame's, and
; when it is expected to swap before the next pass is due; one that did not swap ends them
; for that pass.
;
; Times are in lines: the VBL count x 313 + the beam's line. The frame's field is
; estimated from the last frame drawn (its start to its first access to the back screen,
; and from after that access's wait to its swap): the access waits for the last swap to
; show. PRESENT_OFF (a test define): no presentation frames, the frames those of ECS plan
; step 9.

P_LINES equ     313
P_MARGIN equ    P_LINES/8               ; lines to spare before the next pass is due

; d0 the time in lines. START's VBL routine counts the field first thing; in the field's
; first half with VERTB still requested it has not run yet for this field
_now    movem.l d1-d2/a0,-(a7)
        move.l  _wvars+W_VBL(pc),a0
.r      move.l  (a0),d1
        move.l  $dff004,d0
        move.w  $dff01e,d2
        cmp.l   (a0),d1
        bne     .r
        lsr.l   #8,d0
        and.l   #$1ff,d0
        btst    #5,d2
        beq     .t
        cmp.w   #P_LINES/2,d0
        bhs     .t
        addq.l  #1,d1
.t      mulu.l  #P_LINES,d1
        add.l   d1,d0
        movem.l (a7)+,d1-d2/a0
        rts

; d0 the time now, d2 the latest field: d1 the frame's expected swap (lines), d2 the field
; it shows in, at most the given one
_pwhen  movem.l d0/d3,-(a7)
        add.l   _pvars+P_PRE(pc),d0     ; to its first access to the back screen
        move.l  _bvars+B_SVBL(pc),d3
        addq.l  #1,d3                   ; the field the last swap shows in, which the
        mulu.l  #P_LINES,d3             ; access waits for
        cmp.l   d3,d0
        bhs     .w
        move.l  d3,d0
.w      add.l   _pvars+P_TAIL(pc),d0
        move.l  d0,d1
        divu.l  #P_LINES,d0
        addq.l  #1,d0                   ; shown from the next field
        cmp.l   d2,d0
        bhs     .x
        move.l  d0,d2
.x      movem.l (a7)+,d0/d3
        rts

; from _passend, a1 _wvars, W the next pass's count
_present
        IFND PRESENT_OFF
        movem.l d0-a6,-(a7)
        lea     _pvars(pc),a4
        tst.b   P_ON(a4)
        beq     .out
.loop   bsr     _pneed
        beq     .out
        bsr     _now
        move.l  _wvars+W_W(pc),d2
        bsr     _pwhen
        cmp.l   P_LASTT(a4),d2
        bls     .out                    ; no later field than the last frame's
        add.l   #P_MARGIN,d1
        move.l  _wvars+W_W(pc),d0
        mulu.l  #P_LINES,d0
        cmp.l   d0,d1
        bhs     .out                    ; it would end after the next pass is due
        st      P_IN(a4)
        sf      P_SWAP(a4)
        move.l  _hunk1(pc),a0
        jsr     $3086(a0)
        lea     _pvars(pc),a4
        sf      P_IN(a4)
        tst.b   P_SWAP(a4)
        beq     .out
        addq.l  #1,P_FRAMES(a4)
        bra     .loop
.out    movem.l (a7)+,d0-a6
        ENDC
        rts

; Z clear when the last frame drawn was staged: the camera, or an element (step 9's slots)
_pneed  movem.l d0/d7/a3,-(a7)
        tst.b   _ivars+I_STAGED(pc)
        bne     .yes
        move.l  _wvars+W_ETAB(pc),d0
        beq     .no
        move.l  d0,a3
        moveq   #ESLOTS-1,d7
.s      tst.l   (a3)
        beq     .n
        tst.b   22(a3)
        bne     .yes
.n      lea     ESIZE(a3),a3
        dbf     d7,.s
.no     moveq   #0,d0
        bra     .x
.yes    moveq   #1,d0
.x      movem.l (a7)+,d0/d7/a3
        rts

; +$329a, the countdown of a view with bit 5 set: not in a presentation frame (Z clear: the
; bne.w after it taken, as for a count not yet out)
_cdown  tst.b   _pvars+P_IN(pc)
        bne     .x
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        subq.b  #1,(H1_CDOWN,a0)
        movea.l (a7)+,a0
.x      rts

; the frame's timing: at its first access to the back screen (_bflush, before and after the
; wait for the last swap) and at its swap
_ptacc  movem.l d0/a0,-(a7)
        lea     _pvars(pc),a0
        tst.b   P_TIMED(a0)
        beq     .x
        tst.b   P_ACC(a0)
        bne     .x
        bsr     _now
        move.l  d0,P_TA(a0)
.x      movem.l (a7)+,d0/a0
        rts
_ptwait movem.l d0/a0,-(a7)
        lea     _pvars(pc),a0
        tst.b   P_TIMED(a0)
        beq     .x
        tst.b   P_ACC(a0)
        bne     .x
        st      P_ACC(a0)
        bsr     _now
        move.l  d0,P_TB(a0)
.x      movem.l (a7)+,d0/a0
        rts
_ptswap movem.l d0-d1/a0,-(a7)
        lea     _pvars(pc),a0
        st      P_SWAP(a0)
        tst.b   P_TIMED(a0)
        beq     .x
        sf      P_TIMED(a0)
        move.l  _wvars+W_DRAWT(pc),P_LASTT(a0)
        bsr     _now
        tst.b   P_ACC(a0)
        bne     .acc
        sub.l   P_T0(a0),d0             ; no access noted: all of it before
        move.l  d0,P_PRE(a0)
        clr.l   P_TAIL(a0)
        bra     .x
.acc    sub.l   P_TB(a0),d0
        move.l  d0,P_TAIL(a0)
        move.l  P_TA(a0),d0
        sub.l   P_T0(a0),d0
        move.l  d0,P_PRE(a0)
.x      movem.l (a7)+,d0-d1/a0
        rts

_pvars
_pt0            dc.l    0               ; the frame's start
_pta            dc.l    0               ; its first access to the back screen
_ptb            dc.l    0               ; after that access's wait
_ppre           dc.l    0               ; the last frame drawn: its start to its access
_ptail          dc.l    0               ; and after the wait to its swap
_plastt         dc.l    0               ; its field (W_DRAWT)
_pframes        dc.l    0               ; presentation frames drawn
_pon            dc.b    0               ; patched
_pin            dc.b    0               ; in a presentation frame
_ptimed         dc.b    0               ; the frame timed (3D, W in use)
_pacc           dc.b    0               ; its access noted
_pswap          dc.b    0               ; a swap in the presentation frame
        even
P_T0    equ     _pt0-_pvars
P_TA    equ     _pta-_pvars
P_TB    equ     _ptb-_pvars
P_PRE   equ     _ppre-_pvars
P_TAIL  equ     _ptail-_pvars
P_LASTT equ     _plastt-_pvars
P_FRAMES equ    _pframes-_pvars
P_ON    equ     _pon-_pvars
P_IN    equ     _pin-_pvars
P_TIMED equ     _ptimed-_pvars
P_ACC   equ     _pacc-_pvars
P_SWAP  equ     _pswap-_pvars

**********************************************
; The camera between the followed object's runs (the AGA's plan step 8). The 3D view (its
; camera at +22/24/26, its angles at +52/54/56) follows an object (+96; flags +132, bit 0
; the position, bit 1 the angles): hunk 1 +$2f7c sets the camera from the object's pose and
; marks the view changed (bit 7 of +0), so it changes only when that object has run, every
; 9 fields for the player. At each list's end (_listend) _isample reads the object's pose as
; +$2f7c does (the position words +0/+8/+16, the angles +24/+32/+40 plus +64/+68/+72); a
; new pose keeps the one before it and the world count W of the change. Before the drawing
; (+$3252 jsr +$8a10 becomes jsr _view) the camera is moved back by (cur - prev) x
; (1 - alpha), alpha = (W - W of cur) / the change's interval (at most the object's period
; on the cap's grid), angles the short way round; when that camera differs from the last
; one drawn the view is marked changed, its elements marked to be projected again, it is
; drawn, and the camera is put back. A frame drawn only for the staging takes the changed
; path after the drawing (+$3258: the other views and the swap), so the unchanged path's
; per-frame flags and countdown (+$326c-+$32aa: +$d54b, +$d581, +$d580) are done here for
; it. No interpolation across a jump (a position step over I_JUMP or an angle over 45
; degrees), for a new view or followed object, or outside 3D mode (W not in use).
; INTERP_OFF (a test define): alpha always 1.

I_JUMP  equ     128

; a2 the view, a1 START's element table (+$d3dc)
_view   movem.l d0-d7/a0-a1/a3-a4,-(a7)
        lea     _ivars(pc),a3
        lea     .cam(pc),a1
        lea     I_OFF(a3),a4
        clr.l   (a4)+
        clr.l   (a4)+
        clr.l   (a4)+
        clr.l   (a4)
        cmp.l   I_VIEW(a3),a2
        beq     .same
        move.l  a2,I_VIEW(a3)
        sf      I_VALID(a3)
        sf      I_DRAWN(a3)
        sf      I_STAGED(a3)
        bra     .staged
.same   lea     _wvars(pc),a0
        tst.b   W_ON(a0)
        beq     .staged
        tst.b   I_VALID(a3)
        beq     .staged
        IFND INTERP_OFF
        move.w  96(a2),d0
        bmi     .staged
        move.l  _wvars+W_OBJTAB(pc),a0
        move.l  (a0),a0
        move.l  (a0,d0.w),d0
        cmp.l   I_OBJ(a3),d0
        bne     .staged
        move.l  _wvars+W_DRAWT(pc),d6
        sub.l   I_WR(a3),d6             ; alpha's numerator
        move.l  I_DEN(a3),d7
        cmp.l   d7,d6
        bhs     .staged                 ; alpha 1 (or before the change: none)
        moveq   #0,d5
.off    move.w  I_CUR(a3,d5.w),d0
        sub.w   I_PREV(a3,d5.w),d0      ; the step
        cmp.w   #6,d5
        blo     .pos
        cmp.w   #180,d0
        ble     .a1
        sub.w   #360,d0
.a1     cmp.w   #-180,d0
        bge     .a2
        add.w   #360,d0
.a2     btst    #1,132(a2)
        bra     .part
.pos    btst    #0,132(a2)
.part   beq     .next
        move.w  d0,d1
        muls.w  d6,d1
        divs.w  d7,d1
        sub.w   d0,d1                   ; step x alpha - step
        move.w  d1,I_OFF(a3,d5.w)
.next   addq.w  #2,d5
        cmp.w   #12,d5
        blo     .off
        ENDC
.staged moveq   #0,d4                   ; the staged camera: d4 differs from the last drawn
        moveq   #0,d3                   ; d3 offsets
        moveq   #0,d5
.stage  move.w  (a1,d5.w),d0
        move.w  (a2,d0.w),d1
        move.w  d1,I_SAVE(a3,d5.w)
        move.w  I_OFF(a3,d5.w),d2
        or.w    d2,d3
        add.w   d1,d2
        cmp.w   #6,d5
        blo     .spos
        cmp.w   #360,d2
        ble     .s1
        sub.w   #360,d2
.s1     cmp.w   #-360,d2
        bge     .spos
        add.w   #360,d2
.spos   move.w  d2,I_NEW(a3,d5.w)
        cmp.w   I_DRAWV(a3,d5.w),d2
        sne     d0
        or.b    d0,d4
        addq.w  #2,d5
        cmp.w   #12,d5
        blo     .stage
        tst.b   I_DRAWN(a3)
        bne     .known
        st      d4
.known  tst.w   d3                      ; staged now, or the last drawn was
        bne     .need
        tst.b   I_STAGED(a3)
        bne     .need
        moveq   #0,d4
.need   bsr     _eplan                  ; the other moving objects (step 9)
        beq     .eno
        st      d4
.eno    moveq   #0,d6                   ; d6 a frame only for the staging
        tst.b   (a2)
        bmi     .set
        tst.b   d4
        beq     .draw                   ; unchanged: as START
        bset    #7,(a2)
        moveq   #1,d6
        move.w  14(a7),d0               ; d3 at entry: the view's element chain
        move.l  36(a7),a0               ; a1 at entry: START's element table
        bsr     _emark
.set    moveq   #0,d5                   ; the staged camera in, and drawn
.put    move.w  (a1,d5.w),d0
        move.w  I_NEW(a3,d5.w),d1
        move.w  d1,(a2,d0.w)
        move.w  d1,I_DRAWV(a3,d5.w)
        addq.w  #2,d5
        cmp.w   #12,d5
        blo     .put
        st      I_DRAWN(a3)
        tst.w   d3
        sne     I_STAGED(a3)
        bsr     _eapply
        move.l  _wvars+W_DRAW(pc),a0
        jsr     (a0)
        bsr     _eundo
        moveq   #0,d5                   ; the camera back
.back   move.w  (a1,d5.w),d0
        move.w  I_SAVE(a3,d5.w),(a2,d0.w)
        addq.w  #2,d5
        cmp.w   #12,d5
        blo     .back
        tst.b   d6
        beq     .out
        move.l  _wvars+W_FLAGS(pc),a0   ; +$d54b, +$d581, +$d580 as +$326c-+$32aa
        sf      (a0)
        btst    #2,1(a2)
        beq     .f1
        move.b  #1,(a0)
.f1     sf      $d581-$d54b(a0)
        btst    #5,(a2)
        beq     .out
        move.b  #1,$d581-$d54b(a0)
        tst.b   _pvars+P_IN(pc)         ; the AGA's plan step 11: per world pass
        bne     .out
        subq.b  #1,$d580-$d54b(a0)
        bne     .out
        st      $d581-$d54b(a0)
.out    bsr     _bflush                 ; the AGA's plan step 10.4: the screen brought up
        movem.l (a7)+,d0-d7/a0-a1/a3-a4 ; to date
        rts
.draw   move.l  _wvars+W_DRAW(pc),a0
        jsr     (a0)
        bra     .out
.cam    dc.w    22,24,26,52,54,56

; the view's elements to be projected again, as +$3056-+$3072 on the game's own changes
; (an element is projected only in state 2, so one left in state 0 keeps its screen
; position from the last change): each in state 0 with byte +33 not negative set to 2.
; d0 the view's chain (its offset in the table), a0 START's element table
_emark  move.w  6(a0,d0.w),d0
        beq     .out
        tst.b   33(a0,d0.w)
        bmi     _emark
        tst.b   (a0,d0.w)
        bne     _emark
        move.b  #2,(a0,d0.w)
        bra     _emark
.out    rts

; at each list's end, W the list's count: the followed object's pose, kept with the one
; before it when it changes
_isample
        movem.l d0-d7/a0-a3,-(a7)
        lea     _ivars(pc),a3
        lea     _wvars(pc),a1
        move.l  I_VIEW(a3),d0
        beq     .out
        move.l  d0,a2
        tst.b   W_ON(a1)
        beq     .none
        tst.b   132(a2)
        beq     .none
        move.w  96(a2),d0
        bmi     .none
        move.l  W_OBJTAB(a1),a0
        move.l  (a0),a0
        move.l  (a0,d0.w),d0
        beq     .none
        move.l  d0,a0
        lea     I_POSE(a3),a2           ; the pose as +$2f7c reads it
        move.w  (a0),(a2)+
        move.w  8(a0),(a2)+
        move.w  16(a0),(a2)+
        move.w  24(a0),d0
        add.w   64(a0),d0
        move.w  d0,(a2)+
        move.w  32(a0),d0
        add.w   68(a0),d0
        move.w  d0,(a2)+
        move.w  40(a0),d0
        add.w   72(a0),d0
        move.w  d0,(a2)
        move.l  W_W(a1),d7
        tst.b   I_VALID(a3)
        beq     .snap
        cmp.l   I_OBJ(a3),a0
        bne     .snap
        moveq   #0,d4                   ; moved
        moveq   #0,d5
.cmp    move.w  I_POSE(a3,d5.w),d0
        sub.w   I_CUR(a3,d5.w),d0
        beq     .cnext
        moveq   #1,d4
        cmp.w   #6,d5
        blo     .cpos
        cmp.w   #180,d0                 ; an angle the short way round
        ble     .c1
        sub.w   #360,d0
.c1     cmp.w   #-180,d0
        bge     .c2
        add.w   #360,d0
.c2     bsr     .abs
        cmp.w   #45,d0
        bhi     .snap
        bra     .cnext
.cpos   bsr     .abs
        cmp.w   #I_JUMP,d0
        bhi     .snap
.cnext  addq.w  #2,d5
        cmp.w   #12,d5
        blo     .cmp
        tst.b   d4
        beq     .out
        move.l  I_CUR(a3),I_PREV(a3)
        move.l  I_CUR+4(a3),I_PREV+4(a3)
        move.l  I_CUR+8(a3),I_PREV+8(a3)
        move.l  d7,d0                   ; the interval: since the last change, at most
        sub.l   I_WR(a3),d0             ; the period on the cap's grid
        move.l  W_CAP(a1),a2
        moveq   #0,d1
        move.b  (a2),d1
        beq     .none
        moveq   #0,d2
        move.w  -58(a0),d2              ; period + 1 rounded up to the cap
        addq.l  #1,d2
        add.l   d1,d2
        subq.l  #1,d2
        divu.w  d1,d2
        mulu.w  d1,d2
        tst.l   d0
        ble     .grid
        cmp.l   d2,d0
        bls     .den
.grid   move.l  d2,d0
.den    move.l  d0,I_DEN(a3)
        bra     .keep
.snap   move.l  a0,I_OBJ(a3)            ; a jump, or a new object: no interpolation
        st      I_VALID(a3)
        move.l  I_POSE(a3),I_PREV(a3)
        move.l  I_POSE+4(a3),I_PREV+4(a3)
        move.l  I_POSE+8(a3),I_PREV+8(a3)
.keep   move.l  I_POSE(a3),I_CUR(a3)
        move.l  I_POSE+4(a3),I_CUR+4(a3)
        move.l  I_POSE+8(a3),I_CUR+8(a3)
        move.l  d7,I_WR(a3)
.out    movem.l (a7)+,d0-d7/a0-a3
        rts
.none   sf      I_VALID(a3)
        bra     .out
.abs    tst.w   d0
        bpl     .abs1
        neg.w   d0
.abs1   rts

**********************************************
; The other moving objects between their runs (the AGA's plan step 9). After an object's
; run +$2e56 moves its 3D elements (+$d3dc's table, chained from -24(a6) through +4) by
; the pose's difference and sets their heading (+36) to the object's (+40): hunk 1 +$2f44
; movea.l <+$d3dc>,a1, reached only when the object moved or turned (d4-d6 the position's
; step, d7 the heading, +$d40e the heading before the run), becomes jsr _emove, which keeps
; the step, the world count and the interval (as _isample's) for up to ESLOTS objects.
; _view stages them for the drawing (_eplan, _eapply, _eundo): each element moved back by
; step x (1 - alpha), its heading too where it is the object's, and put back after it.
; While the camera stays, a frame is drawn for the staging only when a staged element's
; screen box (+12/+14, size +40/+42, +16 negative when not projected) meets the view's
; (+14/+16, size +18/+20); the game's own redraw of a moved element's region (+$32ac,
; +$3758) stays for the rest. A slot's object is looked up in MAIN's object table at each
; drawing, so a freed object is dropped. No interpolation across a jump (as _isample's).

ESLOTS  equ     8
ESIZE   equ     36
; a slot: +0 the object (0 free), +4 W of the move, +8 the interval, +12/14/16 the position's
; step, +18 the heading's, +20 the heading after it, +22 staged in the last frame drawn,
; +24/26/28/30 the offsets (position, heading), +32 the staged heading

; at +$2f44: a6 the object, d4-d6 the step, d7 the heading; a1 START's element table out
_emove  move.l  _wvars+W_ELEM(pc),a1
        move.l  (a1),a1
        movem.l d0-d3/a0/a2-a3,-(a7)
        lea     _wvars(pc),a0
        tst.b   W_ON(a0)
        beq     .out
        move.l  W_ETAB(a0),d0
        beq     .out
        tst.w   -24(a6)
        beq     .out
        move.l  d0,a3
        move.l  W_PREVH(a0),a2
        move.w  d7,d3
        sub.w   (a2),d3                 ; the heading's step, the short way round
        cmp.w   #180,d3
        ble     .h1
        sub.w   #360,d3
.h1     cmp.w   #-180,d3
        bge     .h2
        add.w   #360,d3
.h2     moveq   #0,d2                   ; d2 a jump
        move.w  d4,d0
        bsr     .big
        move.w  d5,d0
        bsr     .big
        move.w  d6,d0
        bsr     .big
        move.w  d3,d0
        bpl     .h3
        neg.w   d0
.h3     cmp.w   #45,d0
        shi     d0
        or.b    d0,d2
        sub.l   a2,a2                   ; a2 the object's slot, a1 kept: a free one
        moveq   #ESLOTS-1,d1
.find   cmp.l   (a3),a6
        beq     .found
        tst.l   (a3)
        bne     .nf
        move.l  a2,d0
        bne     .nf
        move.l  a3,a2
.nf     lea     ESIZE(a3),a3
        dbf     d1,.find
        tst.b   d2
        bne     .out
        move.l  a2,d0
        beq     .out                    ; no room: drawn as moved
        move.l  d0,a3
        clr.w   22(a3)
        move.l  W_W(a0),d0
        bsr     .grid
        move.l  d1,d0
        bra     .set
.found  tst.b   d2
        beq     .again
        clr.l   (a3)                    ; a jump: as moved, and put back if it was staged
        bra     .out
.again  move.l  W_W(a0),d0
        sub.l   4(a3),d0                ; since the last move, at most the grid
        bsr     .grid
        tst.l   d0
        ble     .g
        cmp.l   d1,d0
        bls     .set
.g      move.l  d1,d0
.set    move.l  a6,(a3)
        move.l  W_W(a0),4(a3)
        move.l  d0,8(a3)
        movem.w d4-d6,12(a3)
        move.w  d3,18(a3)
        move.w  d7,20(a3)
.out    movem.l (a7)+,d0-d3/a0/a2-a3
        rts
; d0 a step: d2 set when it is a jump
.big    tst.w   d0
        bpl     .b1
        neg.w   d0
.b1     cmp.w   #I_JUMP,d0
        shi     d0
        or.b    d0,d2
        rts
; d1 the object's period on the cap's grid (a0 _wvars, a6 the object)
.grid   movem.l d0/a1,-(a7)
        move.l  W_CAP(a0),a1
        moveq   #0,d0
        move.b  (a1),d0
        bne     .g1
        moveq   #1,d0
.g1     moveq   #0,d1
        move.w  -58(a6),d1
        addq.l  #1,d1
        add.l   d0,d1
        subq.l  #1,d1
        divu.w  d0,d1
        mulu.w  d0,d1
        movem.l (a7)+,d0/a1
        rts

; a2 the view: the slots' offsets for this drawing; d0.b set when a frame is needed for
; them (a staged element in view, or the last frame drawn staged and the move now done)
_eplan  movem.l d1-d7/a0-a1/a3-a4,-(a7)
        moveq   #0,d0
        lea     _wvars(pc),a0
        move.l  W_ETAB(a0),d1
        beq     .out
        move.l  d1,a3
        move.l  W_ELEM(a0),a1
        move.l  (a1),a1
        moveq   #ESLOTS-1,d7
.slot   move.l  (a3),d1
        beq     .next
        bsr     _elive
        bne     .free
        clr.l   24(a3)
        clr.l   28(a3)
        clr.w   32(a3)
        tst.b   W_ON(a0)
        beq     .done
        move.l  W_DRAWT(a0),d5
        sub.l   4(a3),d5                ; alpha's numerator
        move.l  8(a3),d6
        cmp.l   d6,d5
        bhs     .done
        moveq   #0,d3                   ; any offset
        moveq   #0,d2
.off    move.w  12(a3,d2.w),d1
        move.w  d1,d4
        muls.w  d5,d4
        divs.w  d6,d4
        sub.w   d1,d4                   ; step x alpha - step
        move.w  d4,24(a3,d2.w)
        or.w    d4,d3
        addq.w  #2,d2
        cmp.w   #8,d2
        blo     .off
        tst.w   d3
        beq     .done
        bsr     _evis
        beq     .next
        st      d0
        bra     .next
.done   tst.b   22(a3)                  ; the move done: a last frame if it was staged
        beq     .free
        bsr     _evis
        beq     .free
        st      d0
        bra     .next
.free   clr.l   (a3)
.next   lea     ESIZE(a3),a3
        dbf     d7,.slot
.out    movem.l (a7)+,d1-d7/a0-a1/a3-a4
        tst.b   d0
        rts

; a3 a slot (its object live): Z clear when one of its elements' screen box meets the view's
; (a2), a1 START's element table
_evis   movem.l d0-d5/a4,-(a7)
        move.l  (a3),a4
        move.w  -24(a4),d1
.el     beq     .no
        tst.w   16(a1,d1.w)
        bmi     .nx
        move.w  12(a1,d1.w),d2          ; x
        move.w  d2,d3
        add.w   40(a1,d1.w),d3
        move.w  14(a2),d4
        cmp.w   d4,d3
        blt     .nx
        add.w   18(a2),d4
        cmp.w   d4,d2
        bgt     .nx
        move.w  14(a1,d1.w),d2          ; y
        move.w  d2,d3
        add.w   42(a1,d1.w),d3
        move.w  16(a2),d4
        cmp.w   d4,d3
        blt     .nx
        add.w   20(a2),d4
        cmp.w   d4,d2
        bgt     .nx
        moveq   #1,d0
        bra     .ret
.nx     move.w  4(a1,d1.w),d1
        bra     .el
.no     moveq   #0,d0
.ret    movem.l (a7)+,d0-d5/a4
        rts

; d1 an object frame: Z set when it is in MAIN's object table
_elive  movem.l d0/a0,-(a7)
        move.l  _wvars+W_OBJTAB(pc),a0
        move.l  (a0),a0
        moveq   #0,d0
.e      cmp.l   (a0,d0.w),d1
        beq     .ret
        move.w  4(a0,d0.w),d0
        bne     .e
        moveq   #1,d0                   ; Z clear
.ret    movem.l (a7)+,d0/a0
        rts

; the offsets in (d0 0) or out (d0 1) for the slots _eplan gave offsets
_eapply moveq   #0,d0
        bra     _estage
_eundo  moveq   #1,d0
_estage movem.l d0-d7/a0-a1/a3-a4,-(a7)
        lea     _wvars(pc),a0
        move.l  W_ETAB(a0),d1
        beq     .out
        move.l  d1,a3
        move.l  W_ELEM(a0),a1
        move.l  (a1),a1
        moveq   #ESLOTS-1,d7
.slot   tst.l   (a3)
        beq     .next
        movem.w 24(a3),d2-d5            ; the offsets
        move.w  d2,d6
        or.w    d3,d6
        or.w    d4,d6
        or.w    d5,d6
        bne     .some
        tst.b   d0                      ; none: after the drawing, a done move's slot freed
        beq     .clr
        move.l  W_DRAWT(a0),d6
        sub.l   4(a3),d6
        cmp.l   8(a3),d6
        blo     .next
        clr.l   (a3)
        bra     .next
.clr    sf      22(a3)
        bra     .next
.some   tst.b   d0
        bne     .neg
        st      22(a3)
        move.w  20(a3),d6               ; the staged heading
        add.w   d5,d6
        cmp.w   #360,d6
        ble     .n1
        sub.w   #360,d6
.n1     cmp.w   #-360,d6
        bge     .n2
        add.w   #360,d6
.n2     move.w  d6,32(a3)
        bra     .walk
.neg    neg.w   d2
        neg.w   d3
        neg.w   d4
.walk   move.l  (a3),a4
        move.w  -24(a4),d1
.el     beq     .next
        add.w   d2,22(a1,d1.w)
        add.w   d3,24(a1,d1.w)
        add.w   d4,26(a1,d1.w)
        tst.w   d5
        beq     .nx
        move.w  36(a1,d1.w),d6
        tst.b   d0
        bne     .hb
        cmp.w   20(a3),d6
        bne     .nx
        move.w  32(a3),36(a1,d1.w)
        bra     .nx
.hb     cmp.w   32(a3),d6
        bne     .nx
        move.w  20(a3),36(a1,d1.w)
.nx     move.w  4(a1,d1.w),d1
        bra     .el
.next   lea     ESIZE(a3),a3
        dbf     d7,.slot
.out    movem.l (a7)+,d0-d7/a0-a1/a3-a4
        rts

**********************************************
; The swap without the beam wait (the AGA's plan step 10.4). START's 3D swap (hunk 1 +$31f4
; jsr <hunk 0 +$cbe>) waits for line 256 (+$cac), writes the plane pointers at the copper
; list's start (+$cd4) and clears INTENA's COPER bit, which the list's next move after the
; pointers sets again: a pass's start (+$3090 jsr <hunk 0 +$c9e>) waits for that bit, the
; new screen shown, and then (+$30ce-+$3140) for the VBL's pointer redraw on it (+$30d8,
; <+$d3ef>), copies last pass's rectangles from the shown screen into the back one
; (+$391e), puts back the background under the pointer there (hunk 2 +$2aa) and empties
; the rectangle list (+$313a). The copper takes the pointers at the field's start, so the
; line does not change the field the frame shows in; the passes' waits only kept the next
; drawing from starting. Here:
; - +$31f4 becomes jsr _swap: the pointers written at once, the bit cleared, except within
;   the lines where the copper takes them (310 to 1)
; - +$3090 becomes jsr _pstart: the wait and the block put off (<+$d426> set: both as before)
; - +$30ce tst.b <+$d3ed> becomes jmp _pblock: the block, unless put off, then +$3144
; - the block put off (_bflush) runs before the pass's first access to the back screen: the
;   conversion's (hunk 2 +$19ea movea.l <+$10>,a1 becomes jsr _c2pld), a 2D view's (+$3222
;   movea.l <+$d3dc>,a1 becomes jsr _viewent), the 3D view's drawing's end (_view), the
;   views' end (+$319e clr.b <+$d425> becomes jsr _vend)
; - the other loads of the back screen (<+$10>) in hunks 0 and 2 that draw into it (text,
;   rectangles, blits: _gsites) wait for the swap to show first (_bshow), so nothing the
;   scripts draw between the swap and the field's start shows on the old screen; not
;   hunk 2 +$2ba, the VBL's pointer, which runs at the field's start.
; All checked first; with _worldpatch's _view.

_swappatch
        move.l  _hunk1(pc),a0
        move.l  _hunk2(pc),a3
        lea     _bvars(pc),a2
        tst.l   _wvars+W_DRAW(pc)
        beq     .no
        move.l  _hunk0(pc),a1
        cmp.w   #$4eb9,$3090(a0)
        bne     .no
        lea     $c9e(a1),a5
        cmp.l   $3092(a0),a5
        bne     .no
        move.l  a5,B_WAIT(a2)
        cmp.l   #$08390004,(a5)         ; btst #4,$dff01d
        bne     .no
        cmp.l   #$00dff01d,4(a5)
        bne     .no
        lea     $cbe(a1),a4             ; the swap: jsr +$cac, jsr +$cd4, move.w #$10,$dff09a
        cmp.w   #$4eb9,(a4)
        bne     .no
        lea     $cac(a1),a5
        cmp.l   2(a4),a5
        bne     .no
        cmp.w   #$4eb9,6(a4)
        bne     .no
        lea     $cd4(a1),a5
        cmp.l   8(a4),a5
        bne     .no
        move.l  a5,B_PTRS(a2)
        cmp.l   #$33fc0010,12(a4)
        bne     .no
        cmp.l   #$00dff09a,16(a4)
        bne     .no
        cmp.w   #$4eb9,$31f4(a0)        ; the 3D swap
        bne     .no
        cmp.l   $31f6(a0),a4
        bne     .no
        lea     .h1(pc),a4              ; hunk 1's sites: offset, opcode, operand in hunk 1
.c1     move.l  (a4)+,d0
        beq     .c1end
        move.w  (a4)+,d1
        move.l  (a4)+,d2
        add.l   a0,d2
        cmp.w   (a0,d0.l),d1
        bne     .no
        cmp.l   2(a0,d0.l),d2
        bne     .no
        bra     .c1
.c1end  cmp.w   #$4eb9,$30f0(a0)        ; jsr +$391e
        bne     .no
        lea     $391e(a0),a5
        cmp.l   $30f2(a0),a5
        bne     .no
        move.l  a5,B_RECTS(a2)
        cmp.w   #$4eb9,$310a(a0)        ; jsr <hunk 2 +$2aa>
        bne     .no
        lea     $2aa(a3),a5
        cmp.l   $310c(a0),a5
        bne     .no
        move.l  a5,B_PTRBG(a2)
        cmp.w   #$23fc,$313a(a0)        ; move.l #<the rectangle list>,<+$d45e>
        bne     .no
        lea     H1_RECTLIST(a0),a5
        cmp.l   $3140(a0),a5
        bne     .no
        move.l  $313c(a0),B_LIST(a2)
        cmp.l   #$66f85239,$30de(a0)    ; bne.s +$30d8, addq.b #1,<+$d3ee>
        bne     .no
        cmp.w   #$2279,$19ea(a3)        ; movea.l <+$10>,a1: the conversion
        bne     .no
        lea     $10(a0),a5
        cmp.l   $19ec(a3),a5
        bne     .no
        lea     _gsites(pc),a4          ; the back screen's other loads
.cg     move.w  (a4)+,d0
        bmi     .cgend
        move.w  (a4)+,d1
        move.w  (a4)+,d2
        bsr     .site
        cmp.w   (a1),d2
        bne     .no
        cmp.l   2(a1),a5
        bne     .no
        bra     .cg
.cgend  move.w  #$4eb9,d1               ; all checked: the patches
        lea     $3090(a0),a1
        lea     _pstart(pc),a4
        bsr     .jsr
        lea     $319e(a0),a1
        lea     _vend(pc),a4
        bsr     .jsr
        lea     $31f4(a0),a1
        lea     _swap(pc),a4
        bsr     .jsr
        lea     $3222(a0),a1
        lea     _viewent(pc),a4
        bsr     .jsr
        lea     $19ea(a3),a1
        lea     _c2pld(pc),a4
        bsr     .jsr
        lea     $30ce(a0),a1
        lea     _pblock(pc),a4
        move.w  #$4ef9,(a1)
        move.l  a4,2(a1)
        lea     _gsites(pc),a4
.pg     move.w  (a4)+,d0
        bmi     .pgend
        move.w  (a4)+,d1
        move.w  (a4)+,d2
        bsr     .site
        rol.w   #7,d2
        and.w   #7,d2                   ; the register
        mulu.w  #_g10a1-_g10a0,d2
        move.w  #$4eb9,(a1)
        lea     _g10a0(pc,d2.w),a6
        move.l  a6,2(a1)
        bra     .pg
.pgend  st      B_ON(a2)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts
; d0 the hunk, d1 the offset: a1 the site
.site   move.l  _hunk0(pc),a1
        tst.w   d0
        beq     .s
        move.l  a0,a1
        cmp.w   #1,d0
        beq     .s
        move.l  a3,a1
.s      add.w   d1,a1                   ; the offsets are below $8000
        rts
.jsr    move.w  d1,(a1)
        move.l  a4,2(a1)
        rts
.h1     dc.l    $30ce
        dc.w    $4a39
        dc.l    H1_PTRSTATE
        dc.l    $30d8
        dc.w    $4a39
        dc.l    H1_PTRSTATE+2
        dc.l    $3144
        dc.w    $4239
        dc.l    $d45b
        dc.l    $319e
        dc.w    $4239
        dc.l    H1_VIEWS
        dc.l    $3222
        dc.w    $2279
        dc.l    H1_ELEM
        dc.l    0

; the AGA's plan step 11, with _view, step 9's slots and the swap patched: +$329a
; subq.b #1,<+$d580> becomes jsr _cdown, and frames between world passes are drawn
_prespatch
        IFND PRESENT_OFF
        tst.b   _bvars+B_ON(pc)
        beq     .no
        tst.l   _wvars+W_DRAW(pc)
        beq     .no
        tst.l   _wvars+W_ETAB(pc)
        beq     .no
        move.l  _hunk1(pc),a0
        lea     $329a(a0),a1
        cmp.w   #$5339,(a1)
        bne     .no
        lea     H1_CDOWN(a0),a2
        cmp.l   2(a1),a2
        bne     .no
        cmp.l   #$6600000a,6(a1)        ; bne.w +$32ac
        bne     .no
        move.w  #$4eb9,(a1)
        pea     _cdown(pc)
        move.l  (a7)+,2(a1)
        lea     _pvars(pc),a2
        st      P_ON(a2)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no
        ENDC
        rts

; hunk, offset, movea.l <+$10>,An (docs/internals.md, "The AGA's sites in the ECS game",
; item 11's back screen loads)
_gsites dc.w    0,$1104,$2c79,0,$114c,$2c79,0,$1232,$2879,0,$12a4,$2879,0,$1366,$2879
        dc.w    0,$13d0,$2879,0,$1404,$2879
        dc.w    2,$4c,$2679,2,$3b0,$2079,2,$416,$2079,2,$584,$2c79,2,$6b6,$2c79
        dc.w    2,$786,$2c79
        dc.w    -1

; +$31f4: the 3D swap without the beam wait
_swap   movem.l d0/a0,-(a7)
.wait   move.l  $dff004,d0              ; not while the copper takes the pointers
        lsr.l   #8,d0
        and.w   #$1ff,d0
        cmp.w   #2,d0
        blo     .wait
        cmp.w   #310,d0
        bhs     .wait
        move.l  _bvars+B_PTRS(pc),a0
        jsr     (a0)
        move.w  #$10,$dff09a
        lea     _bvars(pc),a0
        st      B_UNSHOWN(a0)
        move.l  _wvars+W_VBL(pc),d0
        move.l  d0,a0
        move.l  (a0),d0
        lea     _bvars(pc),a0
        move.l  d0,B_SVBL(a0)
        bsr     _ptswap
        movem.l (a7)+,d0/a0
        rts

; +$3090 in 3D mode: the wait for the swap and the block put off, both now with <+$d426>
_pstart movem.l a0-a1,-(a7)
        lea     _bvars(pc),a1
        move.l  _hunk1(pc),a0
        tst.b   (H1_SWAPNOW,a0)
        bne     .now
        st      B_PEND(a1)
        movem.l (a7)+,a0-a1
        rts
.now    sf      B_PEND(a1)
        move.l  B_WAIT(a1),a0
        jsr     (a0)
        sf      B_UNSHOWN(a1)
        movem.l (a7)+,a0-a1
        rts

; +$30ce: the block now when not put off; on at +$3144
_pblock tst.b   _bvars+B_PEND(pc)
        bne     .on
        bsr     _bblock
.on     move.l  _hunk1(pc),-(a7)
        add.l   #$3144,(a7)
        rts

; +$319e: the views' end
_vend   bsr     _bflush
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        clr.b   (H1_VIEWS,a0)
        move.l  (a7)+,a0
        rts

; +$3222, a view's drawing: a2 the view; a 2D view (bit 1 of +1 clear) draws into the screen
_viewent
        btst    #1,1(a2)
        bne     .v
        bsr     _bflush
.v      move.l  _hunk1(pc),a1
        move.l  (H1_ELEM,a1),a1
        rts

; hunk 2 +$19ea, the conversion
_c2pld  bsr     _bflush
        move.l  _hunk1(pc),a1
        move.l  $10(a1),a1
        rts

; the block put off, if it is: the wait for the swap (+$c9e) and the block, the drawing's
; rectangle (+$d430-+$d439, which +$391e leaves at the last one it copies) kept
_bflush tst.b   _bvars+B_PEND(pc)
        beq     .x
        movem.l d0-d2/a0-a1,-(a7)
        lea     _bvars(pc),a1
        sf      B_PEND(a1)
        bsr     _ptacc
        move.l  B_WAIT(a1),a0
        jsr     (a0)
        bsr     _ptwait
        sf      B_UNSHOWN(a1)
        move.l  _hunk1(pc),a0
        move.l  (H1_RECT,a0),d0
        move.l  (H1_RECT+4,a0),d1
        move.w  (H1_RECT+8,a0),d2
        bsr     _bblock
        move.l  _hunk1(pc),a0
        move.l  d0,(H1_RECT,a0)
        move.l  d1,(H1_RECT+4,a0)
        move.w  d2,(H1_RECT+8,a0)
        movem.l (a7)+,d0-d2/a0-a1
.x      rts

; START's +$30ce-+$3140; a5 the pointer's state (+$d3ed, +$d3ee, +$d3ef)
_bblock movem.l d0-d7/a0-a6,-(a7)
        move.l  _hunk1(pc),a5
        add.l   #H1_PTRSTATE,a5
        tst.b   (a5)
        bmi     .neg
.pwait  tst.b   2(a5)                   ; the VBL's pointer redraw
        bne     .pwait
        addq.b  #1,1(a5)
        beq     .l
        subq.b  #1,1(a5)
.l      move.l  _bvars+B_RECTS(pc),a0
        jsr     (a0)
        move.b  #1,2(a5)
        cmpi.b  #2,(a5)
        beq     .s
        move.l  _bvars+B_PTRBG(pc),a0
        jsr     (a0)                    ; it keeps no registers
        move.l  _hunk1(pc),a5
        add.l   #H1_PTRSTATE,a5
.s      clr.b   2(a5)
        st      1(a5)
        tst.b   (a5)
        bne     .end
        st      (a5)
        bra     .end
.neg    move.l  _bvars+B_RECTS(pc),a0
        jsr     (a0)
.end    move.l  _hunk1(pc),a5
        move.l  _bvars+B_LIST(pc),(H1_RECTLIST,a5)
        movem.l (a7)+,d0-d7/a0-a6
        rts

; the back screen loaded, after the swap shows (INTREQ's COPER bit set again, or two
; fields since the swap); no wait when none is pending
_bshow  move.w  ccr,-(a7)
        tst.b   _bvars+B_UNSHOWN(pc)
        beq     .x
        movem.l d0-d1/a0-a1,-(a7)
        lea     _bvars(pc),a1
        move.l  _wvars+W_VBL(pc),a0
        move.l  #200000,d1
.wait   btst    #4,$dff01d
        bne     .shown
        move.l  (a0),d0
        sub.l   B_SVBL(a1),d0
        cmp.l   #2,d0
        bge     .shown
        subq.l  #1,d1
        bne     .wait
.shown  sf      B_UNSHOWN(a1)
        movem.l (a7)+,d0-d1/a0-a1
.x      move.w  (a7)+,ccr
        rts
_g10a0  bsr.w   _bshow
        move.l  _hunk1(pc),a0
        move.l  $10(a0),a0
        rts
_g10a1  bsr.w   _bshow
        move.l  _hunk1(pc),a1
        move.l  $10(a1),a1
        rts
_g10a2  bsr.w   _bshow
        move.l  _hunk1(pc),a2
        move.l  $10(a2),a2
        rts
_g10a3  bsr.w   _bshow
        move.l  _hunk1(pc),a3
        move.l  $10(a3),a3
        rts
_g10a4  bsr.w   _bshow
        move.l  _hunk1(pc),a4
        move.l  $10(a4),a4
        rts
_g10a5  bsr.w   _bshow
        move.l  _hunk1(pc),a5
        move.l  $10(a5),a5
        rts
_g10a6  bsr.w   _bshow
        move.l  _hunk1(pc),a6
        move.l  $10(a6),a6
        rts

_bvars
_bwait          dc.l    0               ; hunk 0 +$c9e, the wait for the swap
_bptrs          dc.l    0               ; hunk 0 +$cd4, the plane pointers
_brects         dc.l    0               ; hunk 1 +$391e, the rectangles' copy
_bptrbg         dc.l    0               ; hunk 2 +$2aa, the pointer's background
_blist          dc.l    0               ; the rectangle list's start
_bsvbl          dc.l    0               ; the VBL count at the swap
_bpend          dc.b    0               ; the wait and the block put off
_bunshown       dc.b    0               ; a swap not yet shown
_bon            dc.b    0               ; patched
        even
B_WAIT  equ     _bwait-_bvars
B_PTRS  equ     _bptrs-_bvars
B_RECTS equ     _brects-_bvars
B_PTRBG equ     _bptrbg-_bvars
B_LIST  equ     _blist-_bvars
B_SVBL  equ     _bsvbl-_bvars
B_PEND  equ     _bpend-_bvars
B_UNSHOWN equ   _bunshown-_bvars
B_ON    equ     _bon-_bvars

_ivars
_iview          dc.l    0               ; the view
_iobj           dc.l    0               ; the object it follows
_iwr            dc.l    0               ; W of the pose's change
_iden           dc.l    0               ; the change's interval
_ipose          dc.w    0,0,0,0,0,0     ; the pose sampled
_icur           dc.w    0,0,0,0,0,0     ; the pose (camera order: x, y, z, three angles)
_iprev          dc.w    0,0,0,0,0,0     ; the pose before it
_ioff           dc.w    0,0,0,0,0,0     ; the staging's offsets
_isave          dc.w    0,0,0,0,0,0     ; the camera
_inew           dc.w    0,0,0,0,0,0     ; the staged camera
_idrawv         dc.w    0,0,0,0,0,0     ; the last camera drawn
_ivalid         dc.b    0               ; a pose sampled
_idrawn         dc.b    0               ; a camera drawn
_istaged        dc.b    0               ; the last camera drawn was staged
        even
I_VIEW  equ     _iview-_ivars
I_OBJ   equ     _iobj-_ivars
I_WR    equ     _iwr-_ivars
I_DEN   equ     _iden-_ivars
I_POSE  equ     _ipose-_ivars
I_CUR   equ     _icur-_ivars
I_PREV  equ     _iprev-_ivars
I_OFF   equ     _ioff-_ivars
I_SAVE  equ     _isave-_ivars
I_NEW   equ     _inew-_ivars
I_DRAWV equ     _idrawv-_ivars
I_VALID equ     _ivalid-_ivars
I_DRAWN equ     _idrawn-_ivars
I_STAGED equ    _istaged-_ivars

_wvars
_ww             dc.l    0               ; W
_wdrawt         dc.l    0               ; the drawing's time: W plus the cap
_wptr           dc.l    0               ; the count the objects run by: +$d4c2 or W
_wvbl           dc.l    0               ; +$d4c2
_wcap           dc.l    0               ; +$d4c0
_w3d            dc.l    0               ; +$d459
_wframe         dc.l    0               ; +$3076
_wobjtab        dc.l    0               ; +$d3c2
_wdraw          dc.l    0               ; +$8a10
_wflags         dc.l    0               ; +$d54b
_welem          dc.l    0               ; +$d3dc
_wprevh         dc.l    0               ; +$d40e
_wetab          dc.l    0               ; step 9's slots (allocated)
_wcatch         dc.b    0               ; catch-up passes in a row
_won            dc.b    0               ; W in use
        even
W_W     equ     _ww-_wvars
W_DRAWT equ     _wdrawt-_wvars
W_PTR   equ     _wptr-_wvars
W_VBL   equ     _wvbl-_wvars
W_CAP   equ     _wcap-_wvars
W_3D    equ     _w3d-_wvars
W_FRAME equ     _wframe-_wvars
W_OBJTAB equ    _wobjtab-_wvars
W_DRAW  equ     _wdraw-_wvars
W_FLAGS equ     _wflags-_wvars
W_ELEM  equ     _welem-_wvars
W_PREVH equ     _wprevh-_wvars
W_ETAB  equ     _wetab-_wvars
W_CATCH equ     _wcatch-_wvars
W_ON    equ     _won-_wvars

        MC68000
