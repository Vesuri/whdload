; P13C1 experimental synchronous CPU conversion seam, NOT a game hook.
; A0 = dense W*H native chunky bytes; A1 = four contiguous Chip planes.
; D0.L = W (16..320, multiple of 16); D1.L = H (16..200, even).
; Native layout: R=W/8, P=R*(H+2), visible rows [2,H+1).
; Both pointers must be nonzero/even, valid disjoint extents; caller owns them.
; Caller must retire QBlit and own a nondisplayed destination before entry.
; Return D0=0 converted, 1 request unchanged native QBlit, 2 invalid contract.
; All other registers preserved; CCR is a result-clobber. No OS/MMIO/state.
; Native request is deliberately NOT synchronous completion: caller must use
; original submission/completion/publication protocol. No automatic selection.
; Stack must have 512 free bytes, preferably Fast; a shared 320-byte row staging
; pass selects checkerboard nibbles. Include staging and calls in C2 costs.
; Only visible pixels written: leading rows and final invisible row untouched.

        section code,code

ocs_c2p_native:
        moveq   #1,d0
        rts
ocs_c2p_word:
        movem.l d1-d7/a0-a6,-(sp)
        lea     c2p1x1_4_c5_bm_word(pc),a6
        bra.w   ocs_c2p_common
ocs_c2p_long:
        movem.l d1-d7/a0-a6,-(sp)
        lea     c2p1x1_4_c5_bm(pc),a6
ocs_c2p_common:
        cmpi.l  #16,d0
        blo.w   .invalid
        cmpi.l  #320,d0
        bhi.w   .invalid
        move.l  d0,d2
        andi.l  #15,d2
        bne.w   .invalid
        cmpi.l  #16,d1
        blo.w   .invalid
        cmpi.l  #200,d1
        bhi.w   .invalid
        btst    #0,d1
        bne.w   .invalid
        move.l  a0,d2
        beq.w   .invalid
        btst    #0,d2
        bne.w   .invalid
        move.l  a1,d2
        beq.w   .invalid
        btst    #0,d2
        bne.w   .invalid
        btst    #4,d0
        bne.w   .native

        lea     -384(sp),sp
        move.l  sp,a5
        move.w  d0,360(a5)        ; width
        move.w  d1,362(a5)        ; height
        clr.w   364(a5)           ; logical y
        move.l  a0,372(a5)        ; next source row
        move.l  a1,376(a5)        ; destination region
        lsr.w   #3,d0
        move.w  d0,366(a5)        ; row bytes
        addq.w  #2,d1
        mulu.w  d0,d1
        move.l  d1,368(a5)        ; plane bytes
        move.w  d0,320(a5)        ; private BitMap.BytesPerRow
        move.w  362(a5),322(a5)   ; Rows
        move.l  #$00040000,324(a5) ; Flags=0, Depth=4, pad=0
        lea     328(a5),a2
        moveq   #3,d2
.planes:
        move.l  a1,(a2)+
        adda.l  d1,a1
        dbra    d2,.planes
.row:
        move.l  372(a5),a0
        move.l  a5,a1
        move.l  #$0f000f00,d2     ; high nibble at even x on even rows
        move.l  #$000f000f,d3
        btst    #0,365(a5)
        beq.s   .even
        exg     d2,d3
.even:
        move.w  360(a5),d4
        lsr.w   #2,d4
        subq.w  #1,d4
.select:
        move.l  (a0)+,d0
        move.l  d0,d1
        lsr.l   #4,d1
        and.l   d2,d1
        and.l   d3,d0
        or.l    d1,d0
        move.l  d0,(a1)+
        dbra    d4,.select
        move.l  a0,372(a5)
        cmpi.w  #1,364(a5)
        bne.s   .convert
        clr.b   1(a5)            ; retain native four black edge pixels
        clr.b   3(a5)
        clr.b   9(a5)
        clr.b   11(a5)
.convert:
        move.l  a5,a0
        lea     320(a5),a1
        moveq   #0,d0
        move.w  360(a5),d0
        moveq   #1,d1
        moveq   #0,d2
        moveq   #0,d3
        move.w  364(a5),d3
        addq.w  #2,d3
        jsr     (a6)
        addq.w  #1,364(a5)
        move.w  362(a5),d0
        subq.w  #1,d0
        cmp.w   364(a5),d0
        bne.w   .row
        lea     384(sp),sp
        moveq   #0,d0
        bra.s   .exit
.native:
        moveq   #1,d0
        bra.s   .exit
.invalid:
        moveq   #2,d0
.exit:
        movem.l (sp)+,d1-d7/a0-a6
        rts
