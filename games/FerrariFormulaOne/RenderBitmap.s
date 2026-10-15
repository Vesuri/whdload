; H5: bounded CPU path for an aligned 8x8 live-font glyph. The native
; general bitmap operation remains the fallback, including shifted, clipped,
; overlapping, multicolour and larger rectangles. No inter-frame pixel cache.
FF1RenderInstallBitmap:
 cmpi.w #$4a79,$24ae0
 bne.l FF1ProductionFault
 cmpi.l #$1c1b4,$24ae2
 bne.l FF1ProductionFault
 ; The equal-layout control validates the same signature but leaves the
 ; original entry untouched, so measured gains include all new dispatch cost.
 tst.w FF1RenderBitmapControl(pc)
 beq.b .done
 lea FF1RenderBitmap(pc),a0
 move.w #$4ef9,$24ae0
 move.l a0,$24ae2
.done:
 rts
FF1RenderBitmap:
 tst.w FF1RenderBitmapControl(pc)
 beq.w .native
 cmpi.w #8,38(sp)             ; width
 bne.w .native
 cmpi.w #8,42(sp)             ; height
 bne.w .native
 cmpi.w #3,46(sp)
 bne.w .native
 cmpi.w #24,34(sp)            ; destination words/row
 bne.w .native
 tst.w 50(sp)                ; negative foreground selects separate source planes
 bmi.w .native
 tst.w 14(sp)                ; source y must be zero
 bne.w .native
 tst.w $1c1e8
 beq.w .native
 movem.l d0-d7/a0-a6,-(sp)
 lea 60(sp),a6
 move.w 10(a6),d0
 move.w 26(a6),d1
 move.w 30(a6),d2
 move.w d0,d3
 or.w d1,d3
 andi.w #7,d3
 bne.w .fallback
 cmpi.w #376,d1              ; unsigned checks also reject negative coordinates
 bhi.w .fallback
 cmpi.w #248,d2
 bhi.w .fallback
 moveq #0,d4
 move.w 18(a6),d4
 cmpi.w #64,d4
 bhi.w .fallback
 add.w d4,d4                ; source row bytes
 move.w d0,d3
 lsr.w #3,d3
 cmp.w d4,d3
 bhs.w .fallback
 move.l 4(a6),a0
 cmpa.l $216d8,a0
 beq.b .font
 cmpa.l $21798,a0
 bne.w .fallback
.font:
 move.l 20(a6),a2
 cmpa.l $226ae,a2
 beq.b .destination
 cmpa.l $226b2,a2
 bne.w .fallback
.destination:
 ; Native ownership is acquired before the wait. Synchronize all earlier DMA
 ; before reading the live font or writing any destination plane.
 tst.w $1c1b4
 bne.b .owned
 jsr $2a260
.owned:
 jsr $2a130
 adda.w d3,a0
 moveq #0,d5
 moveq #0,d6
 rept 4
 rol.l #8,d5
 move.b (a0),d5
 adda.w d4,a0
 endr
 rept 4
 rol.l #8,d6
 move.b (a0),d6
 adda.w d4,a0
 endr
 lsr.w #3,d1
 mulu.w #48,d2
 add.w d1,d2                ; bounded destination byte offset
 move.w 50(a6),d3
 move.w 54(a6),d4
 moveq #2,d7
.plane:
 move.l (a2)+,a1
 adda.w d2,a1
 move.l d5,d0
 move.l d6,d1
 btst #0,d3
 beq.b .foreground_zero
 btst #0,d4
 beq.b .write
 moveq #-1,d0
 moveq #-1,d1
 bra.b .write
.foreground_zero:
 btst #0,d4
 beq.b .zero
 not.l d0
 not.l d1
 bra.b .write
.zero:
 moveq #0,d0
 moveq #0,d1
.write:
 rol.l #8,d0
 move.b d0,(a1)
 rol.l #8,d0
 move.b d0,48(a1)
 rol.l #8,d0
 move.b d0,96(a1)
 rol.l #8,d0
 move.b d0,144(a1)
 rol.l #8,d1
 move.b d1,192(a1)
 rol.l #8,d1
 move.b d1,240(a1)
 rol.l #8,d1
 move.b d1,288(a1)
 rol.l #8,d1
 move.b d1,336(a1)
 lsr.w #1,d3
 lsr.w #1,d4
 dbra d7,.plane
 movem.l (sp)+,d0-d7/a0-a6
 andi #$ef,ccr              ; native final plane SUBI leaves X clear
 jmp $24d70                 ; native conditional DisownBlitter and return
.fallback:
 movem.l (sp)+,d0-d7/a0-a6
.native:
 tst.w $1c1b4               ; displaced entry; preserve its branch flags
 jmp $24ae6
FF1RenderBitmapControl: dc.w 1
