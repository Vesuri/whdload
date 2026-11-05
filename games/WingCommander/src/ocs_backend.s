; P13C3 conservative OCS backend selection; base 68000 ISA.
; D0.L: option 0 auto / 1 native / 2 CPU.
; D1.L: CPU 0/10/20/30/40/60. D2.L: measured profile (1 C2 PAL 020/Fast).
; D3.L: readiness 7 = owned true-Fast storage, retired native queue, valid
; Chip destination with native fallback intact. Caller certifies these facts.
; Result D0: 0 native / 1 word CPU / 2 longword CPU; other registers unchanged.
; CPU flags alone do not certify a measured profile. Unknown defaults native.
ocs_backend_choose:
        cmpi.l  #7,d3
        bne.s   .native
        cmpi.l  #2,d0
        beq.s   .forced
        tst.l   d0
        bne.s   .native
        cmpi.l  #1,d2
        bne.s   .native
        cmpi.l  #20,d1
        bne.s   .native
        bra.s   .long
.forced:
        tst.l   d1
        beq.s   .word
        cmpi.l  #10,d1
        beq.s   .word
        cmpi.l  #20,d1
        beq.s   .long
        cmpi.l  #30,d1
        beq.s   .long
        cmpi.l  #40,d1
        beq.s   .long
        cmpi.l  #60,d1
        bne.s   .native
.long:
        moveq   #2,d0
        rts
.word:
        moveq   #1,d0
        rts
.native:
        moveq   #0,d0
        rts

; Task-only initializer. A0 points to zeroed owned state (magic, selection);
; A1 is a resload_FlushCache-compatible callback. No SetCPU or CACR writes.
; Call after installing patches and before dispatch. Repeated calls retain
; the selected backend; ownership must remain valid for its entire lifetime.
ocs_backend_init:
        cmpi.l  #$4f435333,(a0)
        beq.s   .ready
        movem.l d1-d7/a0-a6,-(sp)
        bsr.w   ocs_backend_choose
        move.l  d0,-(sp)
        jsr     (a1)
        move.l  (sp)+,d0
        movem.l (sp)+,d1-d7/a0-a6
        move.l  d0,4(a0)
        move.l  #$4f435333,(a0)
.ready:
        move.l  4(a0),d0
        rts
