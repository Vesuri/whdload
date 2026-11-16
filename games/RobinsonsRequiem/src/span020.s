; The landscape's spans clipped at the view's left edge, for both games on the 68020 and up
; (docs/internals.md, "AGA improvements", item 17, and "ECS improvements", item 9).
;
; START's span drawing (AGA hunk 1 +$b6ea, ECS +$9d54) fills a span's rows through two jump
; tables (AGA +$ccf0 and +$d302, ECS +$b346 and +$b958): a row's left edge x, relative to
; the clipped left, picks the entry, and the entry the point in an unrolled run of stores to
; jump to, which comes back through a5. Left of the clip all entries are the same, but there
; are only 129 of them (the table set-up, AGA +$c1f6 and +$c25e, ECS +$a84c and +$a8b4), so
; an edge more than 129 pixels left reads past them and jumps into the table itself (an
; Illegal Instruction). The game's own camera keeps its edges inside that, but the staged
; camera between the player's runs (_view) can take one further out: turning left from the
; direct start, an edge at -132.
;
; The left-clipped spans run in two blocks of two loops (ECS +$a254 and +$a360, AGA +$bbf4
; and +$bd00, $78 bytes each, the same bytes but for the relocated return addresses and
; the odd loop's move.b d4,-(a0) or (a0)+): the even address's loop (0,a6,d7.w), then the
; odd address's (-2,a6,d7.w), both leaving at the block's +$78. Each loop's first
; instruction, movea.l #<its return>,a5, becomes a jmp to a copy of the loop here that takes
; x no further left than the table's first entry (-129, or -128 with the -2): the same
; entry, as if the table went on. A row pays a compare and a branch. Both blocks are
; checked first, word for word. SPAN_OFF (a test define): not patched.

        MC68020

; _spanpatch: a1 the first block (ECS +$a254, AGA +$bbf4), an offset in hunk 1, the second
; block $10c after it; all registers kept
_spanpatch
        IFND SPAN_OFF
        movem.l d0-d2/a0-a3,-(a7)
        add.l   _hunk1(pc),a1
        move.l  a1,a3
        move.w  #$1104,d2               ; the first block's move.b d4,-(a0)
        bsr     .chk
        bne     .no
        lea     $10c(a3),a1
        move.w  #$10c4,d2               ; the second's move.b d4,(a0)+
        bsr     .chk
        bne     .no
        lea     _sexit0(pc),a2          ; the blocks' ends
        lea     $78(a3),a0
        move.l  a0,(a2)+
        lea     $10c+$78(a3),a0
        move.l  a0,(a2)
        move.w  #$4ef9,d0               ; jmp abs.l
        lea     _sp0e(pc),a0
        move.w  d0,(a3)
        move.l  a0,2(a3)
        lea     _sp0o(pc),a0
        move.w  d0,$36(a3)
        move.l  a0,$38(a3)
        lea     _sp1e(pc),a0
        move.w  d0,$10c(a3)
        move.l  a0,$10e(a3)
        lea     _sp1o(pc),a0
        move.w  d0,$10c+$36(a3)
        move.l  a0,$10c+$38(a3)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     movem.l (a7)+,d0-d2/a0-a3
        ENDC
        rts
; a1 a block, d2 its odd loop's move.b: Z set if it is the game's
.chk    lea     .blk(pc),a0
        moveq   #$78/2-1,d0
        move.l  a1,a2
.cw     move.w  (a0)+,d1
        beq     .cn                     ; checked below
        cmp.w   (a2),d1
        bne     .cx
.cn     addq.l  #2,a2
        dbf     d0,.cw
        cmp.w   $36+$16(a1),d2
        bne     .cx
        lea     $1a(a1),a0              ; the even loop's return
        cmp.l   2(a1),a0
        bne     .cx
        lea     $36+$1c(a1),a0          ; the odd loop's
        cmp.l   $38(a1),a0
.cx     rts
; a block's words, 0 for the relocated longs and the move.b, checked on their own
.blk    dc.w    $2a7c,0,0,$5245,$2e03,$4847,$6000,$0018         ; +$00 movea.l #,a5 ...
        dc.w    $de47,$3e36,$7000,$4ef6,$7000,$c344,$d682,$d4c0 ; +$10
        dc.w    $204a,$2e03,$4847,$be46,$5ecd,$ffe6,$4a45,$6b00 ; +$20
        dc.w    $0048,$3e06,$60f0                               ; +$30
        dc.w    $2a7c,0,0,$5245,$2e03,$4847,$6000,$001a         ; +$36 the odd loop
        dc.w    $de47,$3e36,$70fe,0,$4ef6,$7000,$c344,$d682     ; +$46
        dc.w    $d4c0,$204a,$2e03,$4847,$be46,$52cd,$ffe4,$4a45 ; +$56
        dc.w    $6b00,$0010,$4a47,$6b00,$0006,$3e06,$60ea,$51cd ; +$66
        dc.w    $ffdc                                           ; +$76

_sexit0 dc.l    0                       ; the first block's end (+$78)
_sexit1 dc.l    0                       ; the second's

; The loops as START's but for the clamp. d3 the edge (16.16), d2 its step a row, d5 the
; rows less one, d6 the right end, d0 the row's bytes, a2 the row, a6 the table.
SPANE   macro                           ; the even address's loop; \1 the exit
        lea     .c\@(pc),a5
        addq.w  #1,d5
        move.l  d3,d7
        swap    d7
        bra.b   .t\@
.l\@    cmp.w   #-129,d7
        bge.b   .i\@
        move.w  #-129,d7
.i\@    move.w  (a6,d7.w*2),d7
        jmp     (a6,d7.w)
.c\@    exg     d1,d4
        add.l   d2,d3
        adda.w  d0,a2
        movea.l a2,a0
        move.l  d3,d7
        swap    d7
.t\@    cmp.w   d6,d7
        dbgt    d5,.l\@
        tst.w   d5
        bmi.b   .x\@
        move.w  d6,d7
        bra.b   .t\@
.x\@    jmp     ([\1,pc])
        endm

SPANO   macro                           ; the odd address's; \1 the exit, \2 the store
        lea     .c\@(pc),a5
        addq.w  #1,d5
        move.l  d3,d7
        swap    d7
        bra.b   .t\@
.l\@    cmp.w   #-128,d7
        bge.b   .i\@
        move.w  #-128,d7
.i\@    move.w  (-2,a6,d7.w*2),d7
        move.b  d4,\2
        jmp     (a6,d7.w)
.c\@    exg     d1,d4
        add.l   d2,d3
        adda.w  d0,a2
        movea.l a2,a0
        move.l  d3,d7
        swap    d7
.t\@    cmp.w   d6,d7
        dbhi    d5,.l\@
        tst.w   d5
        bmi.b   .x\@
        tst.w   d7
        bmi.b   .n\@
        move.w  d6,d7
        bra.b   .t\@
.n\@    dbf     d5,.c\@
.x\@    jmp     ([\1,pc])
        endm

_sp0e   SPANE   _sexit0
_sp0o   SPANO   _sexit0,-(a0)
_sp1e   SPANE   _sexit1
_sp1o   SPANO   _sexit1,(a0)+
