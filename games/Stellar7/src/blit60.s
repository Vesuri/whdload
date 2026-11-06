; Blitter interrupt while Kickstart's blit queue is idle (BLIT_IRQ_IDLE, 68000
; target). Kickstart 1.3 graphics.library enables INTENA BLIT itself whenever it
; queues work (QBlit kick $fc5916, QBSBlit $fc641e, DisownBlitter with a queue
; $fc6508) and disables it when its queue empties ($fc6e76). With an empty queue
; its handler ($fc6dfa) only clears the request. WaitBlit polls DMACONR, and the
; game installs no BLIT handler of its own, so outside a queued blit every BLIT
; interrupt is dispatch cost only (docs/internals.md, "Blitter and frame
; interrupts"). The field callback masks the enable whenever it finds it set
; with both queues empty and no QBlit in progress, then rechecks: work queued in
; between (only possible from a level-6 QBSBlit timer) gets its enable back, and
; the request still pending makes the interrupt run. Requests are never cleared.

S60_GFX_QUEUE = 58 ; GfxBase blthd
S60_GFX_BEAM = 66 ; bsblthd
S60_GFX_FLAGS = 169 ; bit 1: QBlit running its first blit in the caller
s60_blit_gfx: dc.l 0
        IFD VERIFY
s60_test_blit_record:
        dc.b 'BI60'
s60_test_blit_fields: dc.l 0 ; field callbacks checked
s60_test_blit_masks: dc.l 0 ; enable found set and masked
s60_test_blit_busy: dc.l 0 ; enable left set: a queue or QBlit was active
s60_test_blit_restored: dc.l 0 ; masked, then work found queued: enable restored
        ENDC

s60_blit_install:
        move.l a6,-(sp)
        move.l ($4).w,a6
        lea (s60_blit_gfx_name,pc),a1
        jsr (_LVOOldOpenLibrary,a6)
        move.l (sp)+,a6
        tst.l d0
        beq s60_bad
        move.l d0,a0
        cmp.w #34,(LIB_VERSION,a0)
        bne s60_bad
        ; The queue fields used here, as the 1.3 entries themselves test them.
        cmp.w #$4ef9,(-276,a0) ; QBlit
        bne s60_bad
        move.l (-274,a0),a1
        cmp.l #$4aae003a,($16,a1) ; TST.L 58(a6)
        bne s60_bad
        cmp.l #$006e0002,($46,a1) ; ORI.W #2,168(a6)
        bne s60_bad
        cmp.w #$00a8,($4a,a1)
        bne s60_bad
        cmp.w #$4ef9,(-294,a0) ; QBSBlit
        bne s60_bad
        move.l (-292,a0),a1
        cmp.l #$4aae0042,($38,a1) ; TST.L 66(a6)
        bne s60_bad
        cmp.l #$4aae003a,($40,a1)
        bne s60_bad
        lea (s60_blit_gfx,pc),a1
        move.l a0,(a1)
        rts
s60_blit_gfx_name:
        dc.b "graphics.library",0
        EVEN

; Called first in the native field callback (frame interrupt). D0/A0 free.
s60_blit_idle:
        IFD VERIFY
        lea (s60_test_blit_fields,pc),a0
        addq.l #1,(a0)
        ENDC
        btst #6,$dff01d ; INTENAR BLIT
        beq.s .done
        move.l (s60_blit_gfx,pc),a0
        move.l (S60_GFX_QUEUE,a0),d0
        or.l (S60_GFX_BEAM,a0),d0
        bne.s .busy
        btst #1,(S60_GFX_FLAGS,a0)
        bne.s .busy
        move.w #$0040,$dff09a
        IFD VERIFY
        lea (s60_test_blit_masks,pc),a0
        addq.l #1,(a0)
        move.l (s60_blit_gfx,pc),a0
        ENDC
        move.l (S60_GFX_QUEUE,a0),d0
        or.l (S60_GFX_BEAM,a0),d0
        bne.s .restore
        btst #1,(S60_GFX_FLAGS,a0)
        bne.s .restore
.done:  rts
.restore:
        move.w #$8040,$dff09a
        IFD VERIFY
        lea (s60_test_blit_restored,pc),a0
        addq.l #1,(a0)
        ENDC
        rts
.busy:
        IFD VERIFY
        lea (s60_test_blit_busy,pc),a0
        addq.l #1,(a0)
        ENDC
        rts
