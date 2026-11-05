; Optional C6 CPU-only 32-pixel changed-block adapter, base 68000 ISA.
; Same input/return ABI as ocs_c2p_word/long. Two raw source histories belong
; to the slave's Fast reservation; metadata commits only after conversion.
; Palette changes do not change pixel indices: never suppress publication.
        section code,code
ocs_changed_word:
        movem.l d1-d7/a0-a6,-(sp)
        lea     c2p1x1_4_c5_bm_word(pc),a6
        bra.s   ocs_changed_common
ocs_changed_long:
        movem.l d1-d7/a0-a6,-(sp)
        lea     c2p1x1_4_c5_bm(pc),a6
ocs_changed_common:
        ; Only audited native geometries; other callers use the full adapter.
        cmpi.l  #320,d0
        bne.w   .invalid
        cmpi.l  #16,d1
        blo.w   .invalid
        cmpi.l  #200,d1
        bhi.w   .invalid
        btst    #0,d1
        bne.w   .invalid
        lea     ocs_changed_meta(pc),a2
        lea     ocs_changed_history(pc),a3
        cmpa.l  (a2),a1
        beq.s   .slot
        lea     16(a2),a2
        adda.l  #64000,a3
        cmpa.l  (a2),a1
        beq.s   .slot
        ; Alternate slots for new destinations, invalidating overwritten owner.
        lea     ocs_changed_next(pc),a4
        eori.w  #1,(a4)
        tst.w   (a4)
        bne.s   .new
        lea     -16(a2),a2
        suba.l  #64000,a3
.new:
        clr.l   (a2)
.slot:
        lea     -128(sp),sp
        movea.l sp,a5
        move.l  a2,80(a5)       ; owner metadata
        move.l  a3,84(a5)       ; history cursor
        move.l  a0,88(a5)       ; source cursor
        move.l  a1,92(a5)       ; destination
        move.l  d1,96(a5)       ; height
        clr.w   100(a5)         ; y
        clr.w   102(a5)         ; x
        move.l  a0,108(a5)      ; source identity
        clr.w   104(a5)         ; history-valid flag
        cmpa.l  (a2),a1
        bne.s   .metadata
        cmp.l   4(a2),d1
        bne.s   .metadata
        cmpa.l  8(a2),a0
        bne.s   .metadata
        move.w  #1,104(a5)
.metadata:
        move.w  #40,32(a5)      ; private BitMap
        move.w  d1,34(a5)
        move.l  #$00040000,36(a5)
        addq.w  #2,d1
        mulu.w  #40,d1
        lea     40(a5),a2
        moveq   #3,d2
.planes:
        move.l  a1,(a2)+
        adda.l  d1,a1
        dbra    d2,.planes
.block:
        movea.l 88(a5),a0
        movea.l 84(a5),a1
        tst.w   104(a5)
        beq.s   .changed
        moveq   #7,d2
.compare:
        cmpm.l  (a0)+,(a1)+
        dbne    d2,.compare
        bne.s   .changed
        bra.w   .advance
.changed:
        movea.l 88(a5),a0
        movea.l 84(a5),a1
        movea.l a5,a2
        move.l  #$0f000f00,d2
        move.l  #$000f000f,d3
        btst    #0,101(a5)
        beq.s   .even
        exg     d2,d3
.even:
        moveq   #7,d4
.select:
        move.l  (a0)+,d0
        move.l  d0,(a1)+        ; refresh only changed raw blocks
        move.l  d0,d1
        lsr.l   #4,d1
        and.l   d2,d1
        and.l   d3,d0
        or.l    d1,d0
        move.l  d0,(a2)+
        dbra    d4,.select
        tst.w   102(a5)
        bne.s   .convert
        cmpi.w  #1,100(a5)
        bne.s   .convert
        clr.b   1(a5)
        clr.b   3(a5)
        clr.b   9(a5)
        clr.b   11(a5)
.convert:
        movea.l a5,a0
        lea     32(a5),a1
        moveq   #32,d0
        moveq   #1,d1
        moveq   #0,d2
        move.w  102(a5),d2
        moveq   #0,d3
        move.w  100(a5),d3
        addq.w  #2,d3
        jsr     (a6)
.advance:
        addi.l  #32,88(a5)
        addi.l  #32,84(a5)
        addi.w  #32,102(a5)
        cmpi.w  #320,102(a5)
        bne.w   .block
        clr.w   102(a5)
        addq.w  #1,100(a5)
        move.w  98(a5),d0
        subq.w  #1,d0
        cmp.w   100(a5),d0
        bne.w   .block
        movea.l 80(a5),a2
        move.l  96(a5),4(a2)
        move.l  108(a5),8(a2)
        move.l  92(a5),(a2)     ; commit owner last
        lea     128(sp),sp
        moveq   #0,d0
        bra.s   .done
.invalid:
        moveq   #2,d0
.done:
        movem.l (sp)+,d1-d7/a0-a6
        rts

ocs_changed_invalidate:
        move.l  a0,-(sp)
        lea     ocs_changed_meta(pc),a0
        clr.l   (a0)
        clr.l   16(a0)
        movea.l (sp)+,a0
        rts
ocs_changed_meta: ds.b 32
ocs_changed_next: dc.w 0
        even
