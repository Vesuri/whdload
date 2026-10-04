; v1 CUSTOM2 bit 3: draw duel:0f114 shapes with the CPU on 68020+.
; The game's own clip routine (duel:0efc6) still computes every blitter
; parameter. Each original blit (clear, set and cookie-cut planes, in the
; original order) is then reproduced word for word: the same ASH/BSH barrel
; shifts with previous-word carries, first/last word masks, modulos and
; minterm $CA. Disabled channels read their constant data from rows in the
; slave (WHDLoad's memory, fast RAM on these machines).
; The blitter is idle on exit, as after the original routine.

RCPU_MAXW = 64                  ; BLTSIZE width limit in words

render_cpu_init:
    movem.l d0-d1/a0-a2/a6,-(sp)
    move.l render_options(pc),d0
    btst #3,d0
    beq .done
    lea render_cpu_tags(pc),a0
    move.l _resload(pc),a2
    jsr (resload_Control,a2)
    move.l render_cpu_attn(pc),d0
    btst #1,d0                  ; AFB_68020
    beq .done
    lea render_cpu_rowbuf(pc),a0 ; zero, then three $FFFF rows
    lea render_cpu_rows(pc),a1
    move.l a0,(a1)
    lea RCPU_MAXW*2(a0),a0
    move.w #RCPU_MAXW*3-1,d1
.ones
    move.w #-1,(a0)+
    dbf d1,.ones
    lea render_cpu_enabled(pc),a0
    st (a0)
.done
    movem.l (sp)+,d0-d1/a0-a2/a6
    rts

; PL_P target at duel:0f114: the CPU path when enabled, else the original
; (its displaced movem/movea, then duel:0f11a).
render_cpu_dispatch:
    move.l a0,-(sp)
    lea render_cpu_enabled(pc),a0
    tst.w (a0)
    movem.l (sp)+,a0            ; movem keeps the flags
    bne.b render_cpu_shape
    movem.l d0-d6/a0-a3/a5,-(sp)
    move.l a0,a5
    move.l -32266(a4),-(sp)
    add.l #$f11a-$e9e2,(sp)
    rts

; Entry replacing duel:0f114. In: a0 shape, a1 mask or 0, d0 x, d1 y,
; a4 globals, a6 custom. Out: carry = clipped away, as the original.
render_cpu_shape:
    movem.l d0-d6/a0-a3/a5,-(sp)
    move.l a0,a5
    move.l -32266(a4),a2        ; RNG jump target = code + $e9e2
    adda.l #$efc6-$e9e2,a2
    jsr (a2)                    ; original clip
    bcs .clipped
    btst #6,2(a6)               ; earlier blits must finish first
.idle
    btst #6,2(a6)
    bne.b .idle
    movem.l d7/a4/a6,-(sp)
    lea render_cpu_blit(pc),a6
    move.l -17220(a4),a0
    move.b 24(a0),d5            ; enabled destination planes
    move.l -12852(a4),a3
    addq.l #8,a3                ; bitmap planes
    move.w -1530(a4),d1         ; BLTSIZE
    move.w d1,d0
    and.w #63,d0
    bne.b .width
    moveq #64,d0
.width
    move.w d0,RB_W(a6)
    lsr.w #6,d1
    bne.b .height
    move.w #1024,d1
.height
    move.w d1,RB_H(a6)
    move.w -1514(a4),RB_FWM(a6)
    move.w -1512(a4),RB_LWM(a6)
    move.w -1524(a4),RB_AMOD(a6)
    move.w -1526(a4),RB_BMOD(a6)
    move.w -1528(a4),RB_CMOD(a6)
    move.w -1528(a4),RB_DMOD(a6)
    move.w -1516(a4),d6
    and.w #15,d6                ; ASH (and BSH for cookie-cut planes)
    move.w -1532(a4),d4         ; destination offset, sign-extended as adda.w
    ext.l d4
    move.l -1540(a4),a0         ; image planes
    move.l -1536(a4),a1         ; mask
    move.w -1522(a4),d7         ; image plane size (adda.w, as the original)
; Channel A: the mask, or constant $FFFF (ADAT) without one.
    move.l a1,RB_APT(a6)
    move.l a1,d0
    bne.b .have_mask
    move.l render_cpu_rows(pc),d0
    add.l #RCPU_MAXW*2,d0
    move.l d0,RB_APT(a6)
    move.w RB_W(a6),d0
    add.w d0,d0
    neg.w d0
    move.w d0,RB_AMOD(a6)       ; reread the constant row
.have_mask
; Channel C: destination, except in the no-mask unshifted D-only mode ($FFFF).
    clr.b RB_CONST_C(a6)
    move.l a1,d0
    bne.b .c_dma
    tst.w d6
    bne.b .c_dma
    st RB_CONST_C(a6)
.c_dma
; Phase 1: clear under the mask (BDAT 0, BSH 0).
    move.b 12(a5),d3
    and.b d5,d3
    beq.b .no_clear
    moveq #0,d2                 ; constant row 0
    bsr render_cpu_planes
.no_clear
; Phase 2: set under the mask (BDAT $FFFF, BSH 0).
    move.b 13(a5),d3
    and.b d5,d3
    beq.b .no_set
    moveq #1,d2
    bsr render_cpu_planes
.no_set
; Phase 3: cookie-cut each image plane into its destination planes.
    lea 14(a5),a5
.image
    move.b (a5)+,d3
    beq.b .done
    and.b d5,d3
    beq.b .next_image
    moveq #-1,d2                ; B from image plane a0, BSH = ASH
    bsr render_cpu_planes
.next_image
    adda.w d7,a0
    bra.b .image
.done
    movem.l (sp)+,d7/a4/a6
    andi.b #$fe,ccr
.clipped
    movem.l (sp)+,d0-d6/a0-a3/a5
    rts

; d3 plane bits, d2 = 0/1 constant B row or -1 image, a0 image plane,
; a3 plane table, d4 destination offset, d6 shift, a6 parameters.
render_cpu_planes:
    movem.l d3/a3,-(sp)
.plane
    lsr.b #1,d3
    bcc.b .skip
    movem.l d2-d7/a0-a3/a5,-(sp)
    move.l (a3),a2
    adda.l d4,a2                ; C = D
    move.l a2,a3
    tst.b RB_CONST_C(a6)
    beq.b .c_real
    move.l render_cpu_rows(pc),a2
    lea RCPU_MAXW*4(a2),a2      ; constant $FFFF row
.c_real
    move.l RB_APT(a6),a1        ; A
    tst.l d2
    bmi.b .b_image
    move.l render_cpu_rows(pc),a0
    tst.w d2
    beq.b .b_const
    lea RCPU_MAXW*6(a0),a0
.b_const
    move.w RB_W(a6),d0
    add.w d0,d0
    neg.w d0
    move.w d0,RB_BUSE(a6)
    moveq #0,d7                 ; BSH 0 for constant BDAT
    bra.b .b_ready
.b_image
    move.w RB_BMOD(a6),RB_BUSE(a6)
    move.w d6,d7
.b_ready
    bsr render_cpu_blit_rect
    movem.l (sp)+,d2-d7/a0-a3/a5
.skip
    addq.l #4,a3
    tst.b d3
    bne.b .plane
    movem.l (sp)+,d3/a3
    rts

; One ascending blit, D = (A & B) | (~A & C) with shifted A and B.
; a1 A, a0 B, a2 C, a3 D, d6 ASH, d7 BSH. A/B previous words start at 0.
; d0/d1 hold A/B as old:new longs; the masked A word enters d0.w.
RCPU_WORD MACRO
    move.l d0,d2
    lsr.l d6,d2                 ; shifted A
    swap d0
    move.w (a0)+,d1
    move.l d1,d3
    lsr.l d7,d3                 ; shifted B
    swap d1
    and.w d2,d3                 ; A & B
    not.w d2
    and.w (a2)+,d2              ; ~A & C
    or.w d3,d2
    move.w d2,(a3)+
    ENDM
render_cpu_blit_rect:
    moveq #0,d0
    moveq #0,d1
    move.w RB_H(a6),d5
    subq.w #1,d5
.row
    move.w RB_W(a6),d4
    subq.w #1,d4                ; words - 1
    move.w (a1)+,d0
    and.w RB_FWM(a6),d0
    tst.w d4
    bne.b .first
    and.w RB_LWM(a6),d0
.first
    RCPU_WORD
    subq.w #1,d4
    bmi.b .row_end
    beq.b .last
    subq.w #1,d4
.mid
    move.w (a1)+,d0
    RCPU_WORD
    dbf d4,.mid
.last
    move.w (a1)+,d0
    and.w RB_LWM(a6),d0
    RCPU_WORD
.row_end
    adda.w RB_AMOD(a6),a1
    adda.w RB_BUSE(a6),a0
    adda.w RB_DMOD(a6),a3
    tst.b RB_CONST_C(a6)
    bne.b .c_const
    adda.w RB_CMOD(a6),a2
    dbf d5,.row
    rts
.c_const
    move.w RB_W(a6),d2          ; constant C row: rewind it
    add.w d2,d2
    suba.w d2,a2
    dbf d5,.row
    rts

RB_W = 0
RB_H = 2
RB_FWM = 4
RB_LWM = 6
RB_AMOD = 8
RB_BMOD = 10
RB_CMOD = 12
RB_DMOD = 14
RB_BUSE = 16
RB_APT = 18
RB_CONST_C = 22
render_cpu_blit: ds.b 24
render_cpu_rows: dc.l 0
render_cpu_rowbuf: dcb.w RCPU_MAXW*4,0
render_cpu_enabled: dc.w 0
render_cpu_tags:
    dc.l WHDLTAG_ATTNFLAGS_GET
render_cpu_attn: dc.l 0
    dc.l 0
