; v1 CUSTOM2 bit 3 (CPUSHAPES experiment): draw duel:0f114 shapes with the
; CPU on 68020+. The game's own clip routine (duel:0efc6) still computes every
; blitter parameter. Every blit of one shape shares the same A channel (mask
; or ADAT $FFFF, ASH, FWM/LWM, modulo), and D = A ? B : C, so a destination
; plane's result is A ? (its last B) : (its original C). Per shape:
; 1. build the shifted A and each needed image plane's shifted B, all rows, in
;    fast buffers with the blitter's exact previous-word carries; chip sources
;    are read as aligned longs;
; 2. combine each destination plane once over all rows, with aligned long
;    chip reads/writes. Buffer rows keep the destination's long phase.
; Clear/set phases use constant B rows; the no-mask unshifted D-only mode uses
; constant C $FFFF. The blitter is idle on exit, as after the original.

RCPU_MAXW = 64                  ; BLTSIZE width limit in words
RCPU_ROW = (RCPU_MAXW+2)*2      ; one buffer row, room for a leading pad word
RCPU_IMAGES = 8
RCPU_BUF = 8192                 ; bytes per full-shape buffer; larger shapes use the blitter

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
    move.l #RCPU_ROW*2+RCPU_BUF*(1+RCPU_IMAGES),d0
    move.l #$10001,d1           ; MEMF_PUBLIC|MEMF_CLEAR, fast first
    move.l $4.w,a6
    jsr -198(a6)                ; AllocMem
    tst.l d0
    beq .done
    lea render_cpu_buffers(pc),a0
    move.l d0,(a0)
    move.l d0,a0
    lea RCPU_ROW(a0),a0         ; row 0 zero, row 1 $FFFF, then buffers
    move.w #RCPU_ROW/2-1,d1
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
    lea 14(a5),a2               ; more image planes than buffers: original
    moveq #RCPU_IMAGES,d2
.count
    tst.b (a2)+
    beq.b .counted
    dbf d2,.count
    bra .original
.counted
    move.l -32266(a4),a2        ; RNG jump target = code + $e9e2
    adda.l #$efc6-$e9e2,a2
    jsr (a2)                    ; original clip
    bcs .clipped
    move.w -1530(a4),d1         ; BLTSIZE
    move.w d1,d0
    and.w #63,d0
    bne.b .width
    moveq #64,d0
.width
    lsr.w #6,d1
    bne.b .height
    move.w #1024,d1
.height
    move.w d0,d2
    addq.w #1,d2
    and.w #-2,d2
    add.w d2,d2                 ; buffer row stride: even words, keeps long phase
    move.w d2,d3
    mulu.w d1,d3
    cmp.l #RCPU_BUF-4,d3
    bhi .original               ; too large for the buffers (clip is idempotent)
    btst #6,2(a6)               ; earlier blits must finish first
.idle
    btst #6,2(a6)
    bne.b .idle
    movem.l d7/a4/a6,-(sp)
    lea render_cpu_state(pc),a6
    move.w d0,RS_W(a6)
    move.w d1,RS_H(a6)
    move.w d2,RS_STRIDE(a6)
    add.w d0,d0
    sub.w d0,d2
    move.w d2,RS_BUFSKIP(a6)    ; stride - 2w
    neg.w d0
    move.w d0,RS_CONSTSKIP(a6)  ; -2w: constant rows are reread
    move.w -1528(a4),RS_DMOD(a6)
    move.w -1514(a4),RS_FWM(a6)
    move.w -1512(a4),RS_LWM(a6)
    move.w -1524(a4),RS_AMOD(a6)
    move.w -1526(a4),RS_BMOD(a6)
    move.w -1522(a4),RS_PSIZE(a6)
    move.l -1540(a4),RS_IMG0(a6)
    move.l -12852(a4),a0
    addq.l #8,a0
    move.l a0,RS_PLANES(a6)     ; bitmap planes
    move.w -1516(a4),d0
    and.w #15,d0
    move.w d0,RS_SH(a6)
    moveq #32,d1
    sub.w d0,d1
    move.w d1,RS_SHC(a6)
    move.w -1532(a4),d4         ; destination offset, sign-extended as adda.w
    ext.l d4
    move.l d4,RS_DOFF(a6)
    moveq #2,d0
    and.w d4,d0
    move.w d0,RS_ALIGN(a6)      ; buffers start at the destination's long phase
    move.l render_cpu_buffers(pc),a0
    adda.w d0,a0
    move.l a0,RS_ZERO(a6)
    lea RCPU_ROW(a0),a1
    move.l a1,RS_ONES(a6)
    lea RCPU_ROW*2(a0),a1
    move.l a1,RS_ABUF(a6)
; A: the mask, or constant ADAT $FFFF reread every row. C: the destination,
; except in the no-mask unshifted D-only mode (constant $FFFF).
    clr.b RS_CONSTC(a6)
    move.l -1536(a4),d1
    move.l d1,RS_ASRC(a6)
    move.w RS_AMOD(a6),RS_ASRCMOD(a6)
    tst.l d1
    bne.b .have_mask
    move.l RS_ONES(a6),a0
    suba.w RS_ALIGN(a6),a0
    move.l a0,RS_ASRC(a6)
    move.w RS_CONSTSKIP(a6),RS_ASRCMOD(a6)
    tst.w RS_SH(a6)
    bne.b .have_mask
    st RS_CONSTC(a6)
.have_mask
; Final operation per destination plane: 0 none, 1 clear, 2 set, 3+j image j.
    move.l -17220(a4),a0
    move.b 24(a0),d5            ; enabled destination planes
    lea RS_OPS(a6),a0
    clr.l (a0)
    clr.l 4(a0)
    move.b 12(a5),d0
    moveq #1,d1
    bsr .mark
    move.b 13(a5),d0
    moveq #2,d1
    bsr .mark
    lea 14(a5),a1
    moveq #3,d1
.images
    move.b (a1)+,d0
    beq.b .marked
    bsr .mark
    addq.b #1,d1
    bra.b .images
.marked
; From here a4 is scratch. Build A, then each image plane some destination
; ends with (B: BSH = ASH, no masks).
    move.l RS_ASRC(a6),a0
    move.l RS_ABUF(a6),a1
    move.w RS_ASRCMOD(a6),RS_SRCMOD(a6)
    move.w RS_FWM(a6),d3
    move.w RS_LWM(a6),d4
    bsr render_cpu_build
    move.l RS_IMG0(a6),a5
    move.l RS_ABUF(a6),a3
    move.w RS_BMOD(a6),RS_SRCMOD(a6)
    moveq #3,d6
.need
    cmp.b #3+RCPU_IMAGES,d6
    bcc.b .needed
    lea RS_OPS(a6),a0
    moveq #7,d2
.find
    cmp.b (a0)+,d6
    dbeq d2,.find
    bne.b .next_need
    adda.l #RCPU_BUF,a3
    moveq #0,d0
    move.w d6,d0
    subq.w #3,d0
    lsl.w #2,d0
    move.l a3,RS_IMGBUF(a6,d0.w)
    move.l a5,a0
    move.l a3,a1
    moveq #-1,d3
    moveq #-1,d4
    movem.l d6/a3/a5,-(sp)
    bsr render_cpu_build
    movem.l (sp)+,d6/a3/a5
.next_need
    adda.w RS_PSIZE(a6),a5
    addq.b #1,d6
    bra.b .need
.needed
; Combine each destination plane with its final B over all rows.
    move.l RS_PLANES(a6),a5
    lea RS_OPS(a6),a4
    moveq #7,d7
.job
    moveq #0,d0
    move.b (a4)+,d0
    beq.b .next_job
    move.l (a5),a3
    adda.l RS_DOFF(a6),a3       ; D
    move.l a3,a2                ; C = D
    move.w RS_DMOD(a6),RS_CSKIP(a6)
    tst.b RS_CONSTC(a6)
    beq.b .c_real
    move.l RS_ONES(a6),a2
    move.w RS_CONSTSKIP(a6),RS_CSKIP(a6)
.c_real
    move.w RS_CONSTSKIP(a6),RS_VSKIP(a6)
    move.l RS_ZERO(a6),a1
    cmp.w #1,d0
    beq.b .b_ready              ; clear
    move.l RS_ONES(a6),a1
    cmp.w #2,d0
    beq.b .b_ready              ; set
    subq.w #3,d0
    lsl.w #2,d0
    move.l RS_IMGBUF(a6,d0.w),a1
    move.w RS_BUFSKIP(a6),RS_VSKIP(a6)
.b_ready
    move.l RS_ABUF(a6),a0
    movem.l d7/a4/a5,-(sp)
    bsr render_cpu_combine
    movem.l (sp)+,d7/a4/a5
.next_job
    addq.l #4,a5
    dbf d7,.job
.done
    movem.l (sp)+,d7/a4/a6
    andi.b #$fe,ccr
.clipped
    movem.l (sp)+,d0-d6/a0-a3/a5
    rts
.original
    movem.l (sp)+,d0-d6/a0-a3/a5
    bra render_cpu_original
; d0 plane bits, d1 operation; d5 enabled planes, a6 state
.mark
    and.b d5,d0
    lea RS_OPS(a6),a0
.mark_bit
    lsr.b #1,d0
    bcc.b .mark_skip
    move.b d1,(a0)
.mark_skip
    addq.l #1,a0
    tst.b d0
    bne.b .mark_bit
    rts

render_cpu_original:
    movem.l d0-d6/a0-a3/a5,-(sp)
    move.l a0,a5
    move.l -32266(a4),-(sp)
    add.l #$f11a-$e9e2,(sp)
    rts

RCPU_SHIFT_WORD MACRO
    swap d0                     ; d0 = carry:new
    move.w d1,d0
    lsr.l d6,d0
    move.w d0,(a1)+
    moveq #0,d0
    move.w d1,d0                ; carry = new
    ENDM

; Shift all rows as the blitter's A/B barrel shifter does: out[i] =
; (in[i-1]:in[i]) >> sh, with in[-1] carried from the previous row (0 first).
; a0 source, a1 buffer, d3/d4 first/last word masks, RS_SRCMOD source modulo.
; Middle words are read as aligned longs. Uses d0-d7/a0/a1/a4.
render_cpu_build:
    move.w RS_SH(a6),d6
    move.w RS_SHC(a6),d7
    moveq #0,d0                 ; carry
    move.w RS_H(a6),d5
    subq.w #1,d5
    swap d5                     ; row counter in the high word
.row
    move.w RS_W(a6),d2
    move.w (a0)+,d1
    and.w d3,d1
    subq.w #1,d2
    bne.b .first
    and.w d4,d1                 ; one word: both masks
.first
    RCPU_SHIFT_WORD
    subq.w #1,d2                ; d2 = middle words
    bmi.b .row_end
    beq.b .last
    move.l a0,d1
    btst #1,d1
    beq.b .aligned
    move.w (a0)+,d1
    RCPU_SHIFT_WORD
    subq.w #1,d2
    beq.b .last
.aligned
    move.w d2,d5
    lsr.w #1,d5
    beq.b .tail
    subq.w #1,d5
.pair
    move.l (a0)+,d1
    move.l d1,a4
    lsr.l d6,d1
    lsl.l d7,d0                 ; carry << (32-sh); a count of 32 gives 0
    or.l d0,d1
    move.l d1,(a1)+
    move.l a4,d0
    swap d0
    clr.w d0
    swap d0                     ; carry = low word
    dbf d5,.pair
.tail
    btst #0,d2
    beq.b .last
    move.w (a0)+,d1
    RCPU_SHIFT_WORD
.last
    move.w (a0)+,d1
    and.w d4,d1
    RCPU_SHIFT_WORD
.row_end
    adda.w RS_SRCMOD(a6),a0
    adda.w RS_BUFSKIP(a6),a1
    swap d5
    dbf d5,.next_row
    rts
.next_row
    swap d5
    bra .row

RCPU_COMBINE_WORD MACRO
    move.w (a0)+,d3
    move.w (a1)+,d4
    move.w (a2)+,d0
    eor.w d0,d4
    and.w d3,d4
    eor.w d0,d4
    move.w d4,(a3)+
    ENDM

; D = (A & B) | (~A & C) over all rows: a0 A, a1 B, a2 C, a3 D; row skips
; RS_BUFSKIP (A), RS_VSKIP (B), RS_CSKIP (C), RS_DMOD (D). Every destination
; row has the same long phase (even modulo), so the word/long split is fixed.
render_cpu_combine:
    move.w RS_W(a6),d2
    moveq #0,d6                 ; leading word to reach a long boundary
    move.l a3,d0
    btst #1,d0
    beq.b .phase
    moveq #1,d6
    subq.w #1,d2
.phase
    moveq #1,d7
    and.w d2,d7                 ; trailing word
    lsr.w #1,d2                 ; longs
    move.w RS_H(a6),d5
    subq.w #1,d5
.row
    tst.w d6
    beq.b .longs
    RCPU_COMBINE_WORD
.longs
    move.w d2,d1
    subq.w #1,d1
    bmi.b .tail
.long
    move.l (a0)+,d3
    move.l (a1)+,d4
    move.l (a2)+,d0
    eor.l d0,d4
    and.l d3,d4
    eor.l d0,d4
    move.l d4,(a3)+
    dbf d1,.long
.tail
    tst.w d7
    beq.b .row_end
    RCPU_COMBINE_WORD
.row_end
    adda.w RS_BUFSKIP(a6),a0
    adda.w RS_VSKIP(a6),a1
    adda.w RS_CSKIP(a6),a2
    adda.w RS_DMOD(a6),a3
    dbf d5,.row
    rts

RS_W = 0
RS_H = 2
RS_FWM = 4
RS_LWM = 6
RS_AMOD = 8
RS_BMOD = 10
RS_DMOD = 12
RS_SH = 14
RS_SHC = 16
RS_ALIGN = 18
RS_CONSTC = 20
RS_STRIDE = 22
RS_BUFSKIP = 24
RS_CONSTSKIP = 26
RS_SRCMOD = 28
RS_ASRCMOD = 30
RS_CSKIP = 32
RS_VSKIP = 34
RS_PSIZE = 36
RS_DOFF = 38
RS_IMG0 = 42
RS_PLANES = 46
RS_ASRC = 50
RS_ZERO = 54
RS_ONES = 58
RS_ABUF = 62
RS_OPS = 66                     ; 8 bytes
RS_IMGBUF = 74                  ; RCPU_IMAGES longs: image j -> buffer
RS_SIZE = RS_IMGBUF+RCPU_IMAGES*4
    cnop 0,4
render_cpu_state: ds.b RS_SIZE
render_cpu_buffers: dc.l 0      ; zero row, $FFFF row, A, images (AllocMem)
render_cpu_enabled: dc.w 0
render_cpu_tags:
    dc.l WHDLTAG_ATTNFLAGS_GET
render_cpu_attn: dc.l 0
    dc.l 0
