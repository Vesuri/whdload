; H4: batch the fixed driving-demo label into one bitmap operation per buffer.
; Rebuild from the live font on every draw: no stale glyph or destination cache,
; and no unchanged-value suppression across clears, swaps, or native menus.
; CPU composition lives in public memory. Only the existing Chip colour scratch
; is read by DMA. Its sole native consumer is the completed sprite cookie-cut;
; wait before borrowing it and before returning it to native ownership.
FF1RenderDemoText:
 tst.w FF1RenderTextControl(pc)
 beq.w .native
 tst.w $1c1e8
 beq.w .native
 cmpi.l #38,8(sp)
 bne.w .native
 cmpi.l #20,12(sp)
 bne.w .native
 cmpi.l #1,$23bb0
 bne.w .native
 cmpi.w #8,$2178e
 bne.w .native
 cmpi.w #13,$2178c
 blo.w .native
 tst.l $1c1b8
 beq.w .native
 movem.l d0-d7/a0-a6,-(sp)
 move.l 64(sp),a0
 lea FF1RenderDemoString(pc),a1
 moveq #21,d0
.check:
 cmpm.b (a0)+,(a1)+
 bne.w .fallback
 dbra d0,.check
 ; Predecoded byte columns; -1 denotes a solid background space.
 move.l $21798,a2
 moveq #0,d6
 move.w $2178c,d6
 add.w d6,d6
 lea FF1RenderTextPixels(pc),a3
 moveq #7,d7
.row:
 lea FF1RenderDemoColumns(pc),a0
 moveq #20,d5
.glyph:
 moveq #0,d0
 move.b (a0)+,d0
 bmi.b .space
 move.b (a2,d0.w),(a3)+
 bra.b .next
.space:
 clr.b (a3)+
.next:
 dbra d5,.glyph
 clr.b (a3)+
 clr.w (a3)+                 ; safe extra source word for shifted blits
 adda.w d6,a2
 dbra d7,.row
 jsr $2a130
 lea FF1RenderTextPixels(pc),a0
 move.l $1c1b8,a1
 IFD FF1_FAST_RENDER
 exg a0,a1
 bsr.l FF1FastRenderTarget
 exg a0,a1
 ENDC
 moveq #47,d0
.copy:
 move.l (a0)+,(a1)+
 dbra d0,.copy
 ; Native bitmap routine retains shifts, edge masks and plane minterms.
 ; Preserve the original first-buffer then second-buffer ordering.
 move.l $226ae,d0
 bsr.w .draw
 move.l $226b2,d0
 bsr.w .draw
 jsr $2a130
 movem.l (sp)+,d0-d7/a0-a6
 rts
.draw:
 pea 1.w                    ; background
 clr.l -(sp)                ; foreground
 pea 3.w                    ; planes
 pea 8.w                    ; height
 pea 168.w                  ; twenty-one 8-pixel glyphs
 pea 24.w                   ; destination words per row
 pea 20.w                   ; destination y
 pea 38.w                   ; destination x
 move.l d0,-(sp)
 pea 12.w                   ; source words per row including padding
 clr.l -(sp)                ; source y
 clr.l -(sp)                ; source x
 move.l $1c1b8,-(sp)
 jsr $24ae0
 lea 52(sp),sp
 rts
.fallback:
 movem.l (sp)+,d0-d7/a0-a6
.native:
 jmp $239a0
FF1RenderTextControl: dc.w 1
FF1RenderDemoString: dc.b "hit a key to end demo",0
FF1RenderDemoColumns:
 dc.b 7,8,19,-1,0,-1,10,4,24,-1,19,14,-1,4,13,3,-1,3,4,12,14
 even
FF1RenderTextPixels: ds.b 192

; H3 aliases both HUD pointer views to the current back buffer. Native $23288
; -> $23946 -> $23a6a then overwrites each digit twice with identical source,
; coordinates and foreground/background. The second masked overwrite is
; idempotent and has no intervening writer. Elide only that immediate duplicate,
; never a later frame's draw. Different destinations keep the native routine.
FF1RenderClockDigit:
 tst.w FF1RenderTextControl(pc)
 beq.w .native
 tst.w $1c1e8
 beq.w .native
 move.l a0,-(sp)
 move.l $226ae,a0
 cmpa.l $226b2,a0
 move.l (sp)+,a0
 bne.w .native
 tst.w $235c8
 bne.w .done
 link a6,#0
 movem.l d0-d7/a0-a5,-(sp)
 move.w 10(a6),d0
 ext.l d0
 asl.l #3,d0
 move.w 14(a6),d1
 ext.l d1
 asl.l #3,d1
 move.w 18(a6),d2
 ext.l d2
 asl.l #3,d2
 move.w $23bb0,d3
 ext.l d3
 move.w $23bb2,d4
 ext.l d4
 move.w $2178c,d5
 ext.l d5
 move.l d4,-(sp)
 move.l d3,-(sp)
 pea 3.w
 pea 8.w
 pea 8.w
 pea 24.w
 move.l d2,-(sp)
 move.l d1,-(sp)
 move.l $226ae,-(sp)
 move.l d5,-(sp)
 clr.l -(sp)
 move.l d0,-(sp)
 move.l $216d8,-(sp)
 jsr $24ae0
 lea 52(sp),sp
 movem.l (sp)+,d0-d7/a0-a5
 unlk a6
.done:
 rts
.native:
 jmp $23288
