; START's sound effects counted from a clean interrupt request, for both slaves
; (docs/internals.md, "Sound effects"). START queues a sample with the channel's audio
; interrupt disabled and, three VBLs later in its VBL routine, disables it again, turns the
; channel's DMA on and enables the interrupt. Its level 4 routine counts the channel's
; interrupts from repeats + 1 and stops the channel at 0: one interrupt as Paula starts
; the sample, one per pass through it. It never clears the channel's request bit, which
; Paula sets on every reload while the interrupt is disabled (the channels that run with it
; disabled always have it set). A request already pending then counts as the start, the
; real start ends the count, and the channel stops a word or two in: a pop instead of the
; sample. The disable before DMA on, move.w d0,INTENA (33c0 00df f09a, the bytes around it
; checked first), becomes jsr _audclr, which clears the request bit too. Paula's own start
; request comes after it, once DMA is on. Every CPU, also without Enhanced framerate;
; assembled for the 68000. Test define: AUDINT_OFF leaves START as it is.
;
; _audpatch: d0 the hunk 0 offset of START's move.w d0,INTENA; needs _hunk0 and _resload.
; All registers kept.

_audpatch
        movem.l d0-d1/a0-a2,-(a7)
        move.l  _hunk0(pc),a0
        add.l   d0,a0
        cmp.l   #$303c0001,-8(a0)       ; move.w #1,d0
        bne     .x
        cmp.l   #$e760ef40,-4(a0)       ; asl.w d3,d0 / asl.w #7,d0
        bne     .x
        cmp.l   #$33c000df,(a0)         ; move.w d0,INTENA
        bne     .x
        cmp.w   #$f09a,4(a0)
        bne     .x
        cmp.l   #$06408200,12(a0)       ; addi.w #$8200,d0 (DMACON on next)
        bne     .x
        IFND AUDINT_OFF
        move.w  #$4eb9,(a0)+            ; jsr _audclr
        pea     _audclr(pc)
        move.l  (a7)+,(a0)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
        ENDC
.x      movem.l (a7)+,d0-d1/a0-a2
        rts

; d0 the channel's bit << 7 (no SET bit): its interrupt disabled and its request cleared.
_audclr move.w  d0,$dff09a
        move.w  d0,$dff09c
        rts
