; 68000 compile-time arithmetic used by shared_cpu.py. Never installed by itself.
; MUL: low 32 bits of signed/unsigned long * positive unsigned word (0..80).
; DIV: signed long / positive D7.w (50/60), truncate toward zero, INT_MIN valid.
; D4/D5 and all other non-destination registers preserved. CCR scratch.
; No native math ABI and no divide-by-zero/INT_MIN/-1 contract is borrowed.
WC_MUL_SMALL macro
        movem.l d4-d5,-(sp)
        move.l  \2,d4
        swap    d4
        mulu.w  \1,d4
        swap    d4
        clr.w   d4
        mulu.w  \1,\2
        add.l   d4,\2
        movem.l (sp)+,d4-d5
        endm

WC_DIV_RATE macro
        movem.l d4-d5,-(sp)
        move.l  \2,-(sp)       ; retain sign, including INT_MIN
        tst.l   \2
        bpl.w   .positive\@
        neg.l   \2
.positive\@:
        move.l  \2,d4
        swap    d4
        andi.l  #$ffff,d4
        divu.w  \1,d4          ; quotient high word, remainder high half
        move.l  d4,d5
        andi.l  #$ffff0000,d4
        move.w  \2,d4
        divu.w  \1,d4          ; remainder < divisor guarantees word quotient
        swap    d5
        move.w  d4,d5
        move.l  d5,\2
        tst.l   (sp)+
        bpl.w   .done\@
        neg.l   \2
.done\@:
        movem.l (sp)+,d4-d5
        endm

; Push exactly XNZVC, preserving registers AND the incoming flags. Scc does not
; change flags; MOVEQ preserves X, then ROXL captures it. No MOVE SR: this same
; baseline code remains legal in user mode on 68010/020+.
WC_PUSH_CCR macro
        lea     -2(sp),sp
        movem.l d0,-(sp)
        lea     -4(sp),sp
        scs     (sp)
        svs     1(sp)
        seq     2(sp)
        smi     3(sp)
        moveq   #0,d0
        roxl.w  #1,d0
        lsl.w   #4,d0
        tst.b   (sp)
        beq.w   .noc\@
        ori.w   #1,d0
.noc\@:
        tst.b   1(sp)
        beq.w   .nov\@
        ori.w   #2,d0
.nov\@:
        tst.b   2(sp)
        beq.w   .noz\@
        ori.w   #4,d0
.noz\@:
        tst.b   3(sp)
        beq.w   .non\@
        ori.w   #8,d0
.non\@:
        move.w  d0,8(sp)
        movem.l 4(sp),d0
        lea     8(sp),sp
        move.w  (sp),ccr
        endm
