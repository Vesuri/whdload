; The player's movement speed, an option for both games on every CPU (docs/internals.md,
; "Movement speed"; the splash window's "Movement speed", CUSTOM1: 0 Original, 1 1X (ECS),
; 2 2X (AGA)).
;
; The AGA game moves the player twice as far a run of its program (heros) as the ECS game,
; in every mode, the ECS's sub-steps taken twice: walking, heros' step routine (from its
; header +$267 in the ECS game) runs again from its end (the AGA's +$901, while MAIN's mode
; byte $184c is 5, walking); running (mode 6), two more of the routine's own repeats (the
; AGA's +$7d8 and +$897); crawling and the other slow modes, yoda (slot 3), which sets the
; player's speed in MAIN's $1a90 by mode, sets 16, 16 and 8 for the ECS's 8, 8 and 4. The
; AGA's additions are taken only while MAIN's $e71 is 0, a flag of another platform's
; settings (START's platform number, 6000 in the AGA game and 3000 in the ECS, picks them),
; so it is not a switch for the AGA game.
;
; 1X in the AGA game: those three branches never taken and the three speeds halved. 2X in
; the ECS game: the three speeds doubled, and walking and running heros' call of its step
; routine (its header +$195) made twice, the player's speed (frame bytes 52 and 56, which
; the routine clears at its end) put back for the second, as the AGA's pass keeps it. The
; programs are patched as the script's load op (45) loads them (START hunk 1, ECS +$15ac,
; AGA +$2e14): after the loader, the program found by its slot (the loader's own lookup,
; ECS +$7a92, AGA +$94b2) and each byte changed only when its neighbours are the game's.
; The call op (07, ECS +$dd6) is START's but for the check of its call site. Original, and
; the game's own speed (1X in the ECS game, 2X in the AGA), patch nothing.
;
; The including source sets SPD_LOAD (the load op's bsr to the loader), SPD_LOOKUP,
; SPD_CALL (the call op), SPD_MAIN (MAIN's frame pointer), all hunk 1 offsets, and SPD_AGA
; in the AGA slave.

; _speedpatch: all registers kept
_speedpatch
        movem.l d0-d1/a0-a2,-(a7)
        lea     _spdtags(pc),a0
        move.l  _resload(pc),a2
        jsr     resload_Control(a2)
        move.l  _spdopt(pc),d0
        IFD SPD_AGA
        subq.l  #1,d0                   ; 1X
        ELSE
        subq.l  #2,d0                   ; 2X
        ENDC
        bne     .no
        move.l  _hunk1(pc),a0
        lea     SPD_LOAD(a0),a1         ; bsr.w <the loader>
        cmp.l   #$204b6100,-2(a1)       ; movea.l a3,a0
        bne     .no
        cmp.l   #$4a1b66fc,4(a1)        ; tst.b (a3)+, bne.s, rts: the name skipped
        bne     .no
        cmp.w   #$4e75,8(a1)
        bne     .no
        move.w  2(a1),d0
        lea     2(a1,d0.w),a2           ; the loader
        cmp.l   #$123c0046,(a2)         ; move.b #'F',d1
        bne     .no
        lea     _spdldr(pc),a1
        move.l  a2,(a1)
        move.l  a0,a2
        add.l   #SPD_LOOKUP,a2          ; past a 16-bit displacement
        cmp.l   #$48e77880,(a2)         ; movem.l d1-d4/a0,-(sp)
        bne     .no
        cmp.w   #$2079,4(a2)            ; movea.l <the program table>,a0
        bne     .no
        lea     _spdlook(pc),a1
        move.l  a2,(a1)
        IFND SPD_AGA
        lea     SPD_CALL(a0),a2
        lea     .call(pc),a1
        moveq   #.calle-.call-1,d0
.cc     cmpm.b  (a1)+,(a2)+
        bne     .no
        dbf     d0,.cc
        move.l  a0,a1
        add.l   #SPD_MAIN,a1
        lea     _spdmain(pc),a2
        move.l  a1,(a2)
        lea     SPD_CALL(a0),a2
        move.w  #$4ef9,(a2)             ; jmp _spdcall
        pea     _spdcall(pc)
        move.l  (a7)+,2(a2)
        ENDC
        lea     SPD_LOAD(a0),a1
        move.w  #$4ef9,(a1)             ; jmp _spdload, over the bsr and the first tst.b
        pea     _spdload(pc)
        move.l  (a7)+,2(a1)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     movem.l (a7)+,d0-d1/a0-a2
        rts
        IFND SPD_AGA
; START's call op: a 24-bit offset; the return pushed on the frame's stack (d4)
.call   dc.w    $101b,$4880,$4840,$101b,$e140,$101b,$5944,$2d8b,$4000,$d7c0,$4e75
.calle
        ENDC

_spdtags        dc.l    WHDLTAG_CUSTOM1_GET
_spdopt         dc.l    0
                dc.l    0
_spdldr         dc.l    0               ; START's loader
_spdlook        dc.l    0               ; its lookup: d2 a slot; Z set and a1 the header, if loaded

; The load op after its slot (d2) and name (a3, a0): the loader, then this program's bytes
; changed; the name skipped as START does
_spdload
        move.w  d2,-(a7)
        pea     .back(pc)
        move.l  _spdldr(pc),-(a7)
        rts
.back   movem.l d0-d4/a0-a2,-(a7)
        move.w  8*4(a7),d2
        move.l  _spdlook(pc),a0
        jsr     (a0)
        bne     .x
        lea     _spdtab(pc),a0
.e      move.w  (a0)+,d0                ; the slot; -1 the end
        bmi     .end
        move.w  (a0)+,d1                ; the byte's offset from the header
        move.b  (a0)+,d3                ; its new value
        moveq   #0,d4
        move.b  (a0)+,d4                ; the bytes checked start this far before it
        lea     (a1,d1.w),a2
        suba.w  d4,a2
        move.b  (a0)+,d4                ; and are this long
        cmp.w   d0,d2
        bne     .skip
        bsr     _spdcmp
        bne     .next
        move.b  d3,(a1,d1.w)
        bra     .next
.skip   adda.w  d4,a0
.next   move.l  a0,d0
        addq.l  #1,d0
        and.b   #$fe,d0
        move.l  d0,a0
        bra     .e
.end
        IFND SPD_AGA
        cmp.w   #15,d2                  ; heros: its step routine's call, start and end
        bne     .x
        lea     _spdsite(pc),a2
        clr.l   (a2)
        clr.b   _spdtog-_spdsite(a2)
        lea     .hcall(pc),a0
        lea     $195(a1),a2
        moveq   #8,d4
        bsr     _spdcmp
        bne     .x
        lea     $267(a1),a2
        moveq   #8,d4
        bsr     _spdcmp
        bne     .x
        lea     $7b6(a1),a2
        moveq   #11,d4
        bsr     _spdcmp
        bne     .x
        lea     $199(a1),a1             ; the call's return
        lea     _spdsite(pc),a2
        move.l  a1,(a2)
        ENDC
.x      movem.l (a7)+,d0-d4/a0-a2
        addq.l  #2,a7
.s      tst.b   (a3)+
        bne.b   .s
        rts
        IFND SPD_AGA
.hcall  dc.b    $07,$00,$00,$ce,$0a,$00,$00,$b9 ; call +$267, branch on
        dc.b    $1f,$38,$1e,$29,$eb,$4a,$00,$00 ; the routine's start
        dc.b    $1e,$00,$00,$12,$34,$1e,$00,$00,$12,$38,$11 ; its end: the speed cleared, return
        EVEN
        ENDC

; a0 the bytes, a2 the program's, d4 their count: Z set if the same; a0 past them
_spdcmp movem.l d4/a2,-(a7)
        subq.w  #1,d4
        moveq   #0,d0                   ; Z
.c      cmpm.b  (a0)+,(a2)+
        beq.b   .n
        moveq   #1,d0
.n      dbf     d4,.c
        movem.l (a7)+,d4/a2
        tst.w   d0
        rts

        IFND SPD_AGA
_spdmain        dc.l    0               ; MAIN's frame pointer
_spdsite        dc.l    0               ; heros' step call's return, once checked
_spdtog         dc.b    0               ; set between the step routine's two calls
_spdv52         dc.b    0               ; the player's speed (frame bytes 52 and 56) for the
_spdv56         dc.b    0               ; second
        EVEN

; START's call op (07), with heros' step call made twice walking and running (MAIN's
; $184c 5 or 6): the first returns to the call itself
_spdcall
        move.b  (a3)+,d0
        ext.w   d0
        swap    d0
        move.b  (a3)+,d0
        asl.w   #8,d0
        move.b  (a3)+,d0
        cmp.l   _spdsite(pc),a3
        beq.b   .site
.call   subq.w  #4,d4
        move.l  a3,(0,a6,d4.w)
        adda.l  d0,a3
        rts
.site   move.l  -20(a6),a0              ; this object's program: heros, and its call
        cmp.w   #15,(a0)
        bne.b   .call
        lea     _spdtog(pc),a0
        tst.b   (a0)
        bne.b   .two
        move.l  _spdmain(pc),a0
        move.l  (a0),a0
        cmp.b   #5,$184c(a0)            ; walking
        beq.b   .one
        cmp.b   #6,$184c(a0)            ; running
        bne.b   .call
.one    lea     _spdtog(pc),a0
        st      (a0)+
        move.b  52(a6),(a0)+
        move.b  56(a6),(a0)
        subq.w  #4,d4
        lea     -4(a3),a0               ; back to this call
        move.l  a0,(0,a6,d4.w)
        adda.l  d0,a3
        rts
.two    sf      (a0)+
        move.b  (a0)+,52(a6)
        move.b  (a0),56(a6)
        bra.b   .call
        ENDC

; the programs' bytes: slot, offset of the byte from the header; its new value, how far
; before it the checked bytes start, their count, the bytes
_spdtab
        IFD SPD_AGA
        dc.w    15,$901                 ; heros: the second walking pass never
        dc.b    $0a,9,14,$36,$3a,$14,$00,$00,$18,$1f,$12,$5f,$14,$00,$00,$0c,$1e
        EVEN
        dc.w    15,$7d8                 ; heros: a running repeat never
        dc.b    $0a,9,16,$1f,$38,$1e,$0e,$71,$4a,$00,$00,$3a,$14,$00,$00,$10,$1f,$38,$1e
        EVEN
        dc.w    15,$897                 ; heros: the other
        dc.b    $0a,9,16,$1f,$38,$1e,$0e,$71,$4a,$00,$00,$3a,$14,$00,$00,$10,$1f,$38,$1e
        EVEN
        dc.w    3,$2fba                 ; yoda: 16 to 8
        dc.b    $08,12,18,$1e,$00,$08,$1e,$1a,$90,$0a,$00,$00,$06,$1e,$00,$10,$1e,$1a,$90,$1e,$00
        EVEN
        dc.w    3,$2fdc                 ; yoda: 16 to 8
        dc.b    $08,12,18,$1e,$00,$08,$1e,$1a,$90,$0a,$00,$00,$06,$1e,$00,$10,$1e,$1a,$90,$1e,$00
        EVEN
        dc.w    3,$2ffe                 ; yoda: 8 to 4
        dc.b    $04,12,18,$1e,$00,$04,$1e,$1a,$90,$0a,$00,$00,$06,$1e,$00,$08,$1e,$1a,$90,$1e,$00
        EVEN
        ELSE
        dc.w    3,$2f80                 ; yoda: 8 to 16
        dc.b    $10,8,14,$1a,$94,$0a,$00,$01,$13,$1e,$00,$08,$1e,$1a,$90,$0a,$00
        EVEN
        dc.w    3,$2f8a                 ; yoda: 8 to 16
        dc.b    $10,8,14,$1a,$90,$0a,$00,$01,$09,$1e,$00,$08,$1e,$1a,$90,$0a,$00
        EVEN
        dc.w    3,$2f94                 ; yoda: 4 to 8
        dc.b    $08,8,14,$1a,$90,$0a,$00,$00,$ff,$1e,$00,$04,$1e,$1a,$90,$1f,$1e
        EVEN
        ENDC
        dc.w    -1
