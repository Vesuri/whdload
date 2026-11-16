; The mouse pointer hidden at once, for both games on the 68020 and up (docs/internals.md,
; "AGA improvements", item 18, and "ECS improvements", item 10).
;
; START draws the pointer in software at each VBL (ECS hunk 1 +$80aa, AGA +$9aa6) into the
; shown screen, keeping the background under it (hunk 2 +$2ac, AGA +$2c4). Its state byte
; (ECS +$d3ed, AGA +$ed97): -1 off, 0 to be hidden, 1 on, 2 to be drawn without putting the
; background back; +1 the lock, +2 set while the pointer is still on the old screen after
; a swap, +7 its last position. The scripts' op $85 (ECS +$5fac, AGA +$78c6) hides it by
; setting 0, and the next VBL puts the background back (+$8138, AGA +$9b34) and sets -1.
; But the frame's block (+$30ce, AGA +$4a0a; _bblock) also takes a 0: it puts the
; background back into the back screen only, for the pointer it has just copied there, and
; sets -1, so the arrow stays in the shown screen. Op $84 (+$5f86, AGA +$78a0) takes a 0
; too: it sets 2, and the VBL then draws the new image without putting back the old one.
; Either way part of the arrow stays in one screen where the new image does not cover it,
; and below the 3D view, which nothing redraws, it flickers there every other frame (seen
; picking up an object). In START a VBL nearly always comes between op $85 and the frame or
; op $84; with the frames between world passes and the swap without the beam wait it often
; does not.
;
; Here op $85's clr.b <state> (ECS +$5fcc, AGA +$78e6) becomes jsr _phide, which hides the
; pointer as the VBL does, at once: the state set to -1 first (the VBL then leaves the
; pointer alone; the frame's block and the scripts are both the main program's), the
; background put back where the pointer was drawn (the restore picks the old screen while
; +2 is set), +2 cleared and the position forgotten. So no 0 is left to take. Checked
; first. PTR_OFF (a test define): not patched.

        MC68020

; _ptrpatch: a1 op $85's clr.b (ECS +$5fcc, AGA +$78e6), d1 the state (+$d3ed, +$ed97),
; both offsets in hunk 1, a2 the restore (hunk 2 +$2aa, +$4ec), an address; all registers
; kept
_ptrpatch
        IFND PTR_OFF
        movem.l d0-d1/a0-a3,-(a7)
        move.l  _hunk1(pc),a0
        add.l   a0,a1
        add.l   a0,d1                   ; the state's address
        cmp.w   #$4239,(a1)             ; clr.b <state>
        bne     .no
        cmp.l   2(a1),d1
        bne     .no
        cmp.w   #$4e75,6(a1)            ; rts
        bne     .no
        cmp.w   #$2c79,(a2)             ; the restore: movea.l <+$c>,a6
        bne     .no
        lea     $c(a0),a3
        cmp.l   2(a2),a3
        bne     .no
        cmp.w   #$4a39,6(a2)            ; tst.b <state +2>
        bne     .no
        move.l  d1,d0
        addq.l  #2,d0
        cmp.l   8(a2),d0
        bne     .no
        lea     _pstate(pc),a3
        move.l  d1,(a3)+
        move.l  a2,(a3)
        move.w  #$4eb9,(a1)
        pea     _phide(pc)
        move.l  (a7)+,2(a1)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     movem.l (a7)+,d0-d1/a0-a3
        ENDC
        rts

_pstate dc.l    0                       ; the pointer's state byte
_prest  dc.l    0                       ; the restore

; op $85 with the pointer on (state 1): hidden now, as the VBL's +$8138 does
_phide  movem.l d0-d7/a0-a6,-(a7)
        move.l  _pstate(pc),a5
        st      (a5)                    ; off: the VBL leaves it alone
        move.l  _prest(pc),a0
        jsr     (a0)                    ; it keeps no registers
        move.l  _pstate(pc),a5
        clr.b   2(a5)                   ; not on the old screen
        move.l  #-1,7(a5)               ; no position: the next show draws it
        movem.l (a7)+,d0-d7/a0-a6
        rts
