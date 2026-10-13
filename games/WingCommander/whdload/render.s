; Experimental English-only renderer: CUSTOM1=2. CUSTOM1=0/1 keeps original.
; Each generated converter has immutable geometry: no SMC or private workspace.
; Entry replaces only S:178a's MOVEM; all other original offsets stay fixed.
; Long PC-relative transfers keep diagnostic builds within branch reach.
render_entry:
        movem.l d0-a6,-(sp)
        move.l  slave+$1de4(pc),d7
        cmpi.l  #2,d7
        bne.l   slave+$178e
        move.l  slave+$1e04(pc),d7
        subq.l  #1,d7
        beq.s   .convert
        bsr.w   slave+$17b8
.convert:
        cmpi.w  #320,d0
        bne.w   render_bad
        move.w  render_selected(pc),d7
        cmpi.w  #30,d7
        beq.s   .early
        cmpi.w  #40,d7
        beq.w   .later
        cmpi.w  #128,d3
        beq.s   .original128
        cmpi.w  #166,d3
        beq.s   .original166
        cmpi.w  #200,d3
        bne.w   render_bad
        bsr.w   slave+$1ac6
        bra.w   render_converted
.original128:
        bsr.l   slave+$17f6
        bra.w   render_converted
.original166:
        bsr.w   slave+$195e
        bra.w   render_converted
.early:
        cmpi.w  #128,d3
        beq.w   .early128
        cmpi.w  #166,d3
        beq.w   .early166
        cmpi.w  #200,d3
        bne.w   render_bad
        bsr.w   kalms_030_200
        bra.s   render_converted
.early128:
        bsr.w   kalms_030_128
        bra.s   render_converted
.early166:
        bsr.w   kalms_030_166
        bra.s   render_converted
.later:
        cmpi.w  #128,d3
        beq.s   .late128
        cmpi.w  #166,d3
        beq.s   .late166
        cmpi.w  #200,d3
        bne.w   render_bad
        bsr.w   kalms_040_200
        bra.s   render_converted
.late128:
        bsr.w   kalms_040_128
        bra.s   render_converted
.late166:
        bsr.w   kalms_040_166
render_converted:
        ifne RENDER_VERIFY
        ; Original inputs remain in the outer saved register frame.
        move.l  32(sp),a0
        move.l  render_scratch(pc),a1
        move.l  12(sp),d3
        cmpi.w  #128,d3
        beq.s   .ref128
        cmpi.w  #166,d3
        beq.s   .ref166
        bsr.w   slave+$1ac6
        bra.s   .compare
.ref128:
        bsr.l   slave+$17f6
        bra.s   .compare
.ref166:
        bsr.w   slave+$195e
.compare:
        move.l  36(sp),a0
        move.l  render_scratch(pc),a1
        move.l  12(sp),d0
        mulu.w  #80,d0
        subq.l  #1,d0
.check:
        cmpm.l  (a0)+,(a1)+
        bne.w   render_bad
        dbf     d0,.check
        lea     render_verified(pc),a0
        addq.l  #1,(a0)
        endif
        ; The next render reuses the old front buffer. Finish the visible scan
        ; before returning to the original single publication/swap sequence.
render_wait:
        move.l  48(sp),a4
        lea     -660(a4),a0
        move.l  -778(a4),a6
        jsr     -402(a6)              ; graphics.library WaitBOVP
render_wait_done:
        movem.l (sp)+,d0-a6
        rts

; Preserve the original cache request when disabled. Enabled renderer leaves
; WHDLoad's cache choices alone; it never flushes per frame or changes CACR.
render_setcpu:
        move.l  d2,-(sp)
        move.l  slave+$1de4(pc),d2
        cmpi.l  #2,d2
        movem.l (sp)+,d2
        beq.s   .keep
        jmp     96(a2)
.keep:
        ; Query only: zero change mask. WHDLoad reports effective cache policy,
        ; including NoCache. Never change CACR to suit a converter.
        movem.l d0-d1/a0-a1/a6,-(sp)
        moveq   #0,d0
        moveq   #0,d1
        jsr     96(a2)
        lea     render_selected(pc),a0
        clr.w   (a0)
        ifeq RENDER_FAMILY
        btst    #8,d0                ; WCPUF_IC
        else
        ori.w   #256,d0              ; same-size diagnostic override
        endif
        beq.s   .selected
        move.l  $4.w,a6
        move.w  296(a6),d0
        ifeq RENDER_FAMILY
        andi.w  #$0088,d0            ; 040/060: measured original is faster
        else
        andi.w  #0,d0
        endif
        bne.s   .selected
        ifeq RENDER_FAMILY
        move.w  #30,(a0)
        else
        move.w  #RENDER_FAMILY,(a0)
        endif
.selected:
        movem.l (sp)+,d0-d1/a0-a1/a6
        ifne RENDER_VERIFY
        movem.l d0-d1/a0-a1/a6,-(sp)
        move.l  #64000,d0
        move.l  #$10005,d1
        move.l  $4.w,a6
        jsr     -198(a6)
        tst.l   d0
        beq.w   render_bad
        lea     render_scratch(pc),a0
        move.l  d0,(a0)
        movem.l (sp)+,d0-d1/a0-a1/a6
        endif
        movem.l d0,-(sp)
        move.l  slave+$1e04(pc),d0
        cmpi.l  #4,d0
        bcc.w   render_bad            ; original blitter path is unsupported here
        movem.l (sp)+,d0
        rts

render_bad:
        move.l  slave+$121e(pc),a2
        pea     9
        jmp     4(a2)

        ifne RENDER_VERIFY
render_scratch: dc.l 0
render_verified: dc.l 0
        endif

render_selected:
        dc.w    0                    ; 0 existing slave, 30 Kalms 030, 40 Kalms 040
