; FR0g: CPU replay of every blit of one captured dense frame on a Fast RAM
; image (sources, masks, colour scratch and back buffer all in Fast RAM).
; Diagnostic only; included into tmp/build/fr0-replay-* by tools/fr0_build.py.
; Each frame: FR0Restore resets the image (not part of drawing), then
; FR0ReplayRun executes the 44-byte records in order. A real software blitter
; would take the same register values; classification happens at run time.
; Specialized ascending loops for the minterms present; exact generic path for
; everything else. Semantics follow the verified tools/fr0_blits.py.
R_CON0 = 0
R_CON1 = 2
R_AFWM = 4
R_ALWM = 6
R_APT = 8
R_BPT = 12
R_CPT = 16
R_DPT = 20
R_AMOD = 24
R_BMOD = 26
R_CMOD = 28
R_DMOD = 30
R_ADAT = 32
R_BDAT = 34
R_CDAT = 36
R_H = 38
R_V = 40
R_SIZE = 44

FR0Replay:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w FR0Restore
 bsr.w FR0ReplayRun
 lea (FR0ReplayFrames.l,pc),a0
 addq.l #1,(a0)
FR0ReplayDone:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts

FR0Restore:
 lea (FR0BlobInit.l,pc),a0
 lea (FR0Blob.l,pc),a1
 move.l #(FR0BlobInitEnd-FR0BlobInit)/16-1,d0
.l:
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 subq.l #1,d0
 bpl.b .l
 rts

FR0ReplayRun:
 lea (FR0BlitTab.l,pc),a6
.next:
 lea (FR0Blob.l,pc),a5
 bsr.w FR0Dispatch
 lea R_SIZE(a6),a6
 lea (FR0BlitTabEnd.l,pc),a0
 cmpa.l a0,a6
 blo.b .next
 rts

; a6 = record, a5 = image base. May use d0-d7/a0-a4.
FR0Dispatch:
 move.w R_CON1(a6),d0
 btst #0,d0
 bne.w FR0LineFast
 btst #1,d0
 beq.w FR0Area
 move.w d0,d1
 andi.w #$18,d1
 beq.w FR0Generic
 move.w R_CON0(a6),d1
 andi.w #$0fff,d1
 cmpi.w #$03aa,d1              ; C and D only, D = C
 bne.w FR0Generic
 bra.w FR0Fill

; ---- ascending area blits ----
; needs: bit0 A, bit1 B, bit2 C
FR0AreaTab:
 dc.w $ca,7,FR0Area_CA-FR0AreaTab
 dc.w $0a,5,FR0Area_0A-FR0AreaTab
 dc.w $fa,5,FR0Area_FA-FR0AreaTab
 dc.w $3a,7,FR0Area_3A-FR0AreaTab
 dc.w $fc,3,FR0Area_FC-FR0AreaTab
 dc.w $c0,3,FR0Area_C0-FR0AreaTab
 dc.w $30,3,FR0Area_30-FR0AreaTab
 dc.w $00,0,FR0Area_K-FR0AreaTab
 dc.w $ff,0,FR0Area_K-FR0AreaTab
 dc.w -1

FR0Area:
 move.w R_CON0(a6),d7
 btst #8,d7                    ; D must be enabled
 beq.w FR0Generic
 move.w R_CON1(a6),d0
 andi.w #$18,d0
 bne.w FR0Generic
 bsr.w FR0AreaSpecial          ; handled -> d0 = 1
 tst.w d0
 bne.w .done
 move.w R_CON0(a6),d7
 lea FR0AreaTab(pc),a0
 moveq #0,d1
 move.b d7,d1                  ; minterm
.find:
 move.w (a0)+,d2
 bmi.w FR0Generic
 move.w (a0)+,d3               ; needs
 move.w (a0)+,d4               ; routine offset
 cmp.w d1,d2
 bne.b .find
 lea FR0AreaTab(pc),a4
 adda.w d4,a4                  ; routine
 move.w R_H(a6),d6
 ; channel checks
 btst #0,d3
 beq.b .noA
 btst #11,d7
 bne.b .aon
 move.w R_CON0(a6),d0
 andi.w #$f000,d0
 bne.w FR0Generic              ; constant A with shift: generic
 lea (FR0ConstA.l,pc),a0
 move.w R_ADAT(a6),d0
 bsr.w FR0FillConst
 move.w d6,d0
 add.w d0,d0
 neg.w d0
 lea (FR0AM.l,pc),a1
 move.w d0,(a1)
 bra.b .noA
.aon:
 move.l a5,a0
 adda.l R_APT(a6),a0
 lea (FR0AM.l,pc),a1
 move.w R_AMOD(a6),(a1)
.noA:
 move.l a0,-(sp)               ; A pointer
 btst #1,d3
 beq.b .noB
 btst #10,d7
 beq.w .generic_pop1           ; B needed but disabled
 move.l a5,a1
 adda.l R_BPT(a6),a1
 lea (FR0BM.l,pc),a2
 move.w R_BMOD(a6),(a2)
.noB:
 move.l a1,-(sp)               ; B pointer
 btst #2,d3
 beq.b .noC
 btst #9,d7
 bne.b .con
 lea (FR0ConstC.l,pc),a0
 move.w R_CDAT(a6),d0
 bsr.w FR0FillConst
 move.l a0,a2
 move.w d6,d0
 add.w d0,d0
 neg.w d0
 lea (FR0CM.l,pc),a3
 move.w d0,(a3)
 bra.b .noC
.con:
 move.l a5,a2
 adda.l R_CPT(a6),a2
 lea (FR0CM.l,pc),a3
 move.w R_CMOD(a6),(a3)
.noC:
 move.l a5,a3
 adda.l R_DPT(a6),a3
 lea (FR0DM.l,pc),a0
 move.w R_DMOD(a6),(a0)
 ; mask table
 lea (FR0Mask.l,pc),a0
 move.w d6,d0
 subq.w #1,d0
.m:
 move.w #-1,(a0)+
 dbra d0,.m
 lea (FR0Mask.l,pc),a0
 move.w R_AFWM(a6),(a0)
 move.w R_ALWM(a6),d0
 and.w d0,-2(a0,d6.w*2)
 lea (FR0W.l,pc),a0
 subq.w #1,d6
 move.w d6,(a0)
 move.l (sp)+,a1
 move.l (sp)+,a0
 move.w R_CON0(a6),d5
 lsr.w #8,d5
 lsr.w #4,d5                   ; ash
 move.w R_CON1(a6),d4
 lsr.w #8,d4
 lsr.w #4,d4                   ; bsh
 moveq #0,d0
 moveq #0,d2
 move.w R_V(a6),-(sp)
 jsr (a4)
 addq.l #2,sp
.done:
 rts
.generic_pop1:
 addq.l #4,sp
 bra.w FR0Generic

; a0 = buffer, d0 = value, d6 = words
FR0FillConst:
 move.l a0,a1
 move.w d6,d1
 subq.w #1,d1
.f:
 move.w d0,(a1)+
 dbra d1,.f
 rts

; Loop body registers: d0 A prev:cur, d1 A shifted, d2 B prev:cur, d3 B shifted,
; d4 bsh, d5 ash, d6 words, d7 C. a0-a3 channel pointers, a4 masks.
; Rows remaining at 4(sp). Result stored to (a3)+.
FR0AREA macro
FR0Area_\1:
.row:
 lea (FR0Mask.l,pc),a4
 move.w FR0W(pc),d6
.w:
 IFNE \2
 swap d0
 move.w (a0)+,d0
 and.w (a4)+,d0
 move.l d0,d1
 lsr.l d5,d1
 ENDC
 IFNE \3
 swap d2
 move.w (a1)+,d2
 move.l d2,d3
 lsr.l d4,d3
 ENDC
 IFNE \4
 move.w (a2)+,d7
 ENDC
 IFEQ \5-1                     ; CA: A ? B : C
 eor.w d7,d3
 and.w d1,d3
 eor.w d7,d3
 move.w d3,(a3)+
 ENDC
 IFEQ \5-2                     ; 0A: ~A & C
 not.w d1
 and.w d7,d1
 move.w d1,(a3)+
 ENDC
 IFEQ \5-3                     ; FA: A | C
 or.w d7,d1
 move.w d1,(a3)+
 ENDC
 IFEQ \5-4                     ; 3A: A ? ~B : C
 not.w d3
 eor.w d7,d3
 and.w d1,d3
 eor.w d7,d3
 move.w d3,(a3)+
 ENDC
 IFEQ \5-5                     ; FC: A | B
 or.w d1,d3
 move.w d3,(a3)+
 ENDC
 IFEQ \5-6                     ; C0: A & B
 and.w d1,d3
 move.w d3,(a3)+
 ENDC
 IFEQ \5-7                     ; 30: A & ~B
 not.w d3
 and.w d1,d3
 move.w d3,(a3)+
 ENDC
 dbra d6,.w
 IFNE \2
 adda.w FR0AM(pc),a0
 ENDC
 IFNE \3
 adda.w FR0BM(pc),a1
 ENDC
 IFNE \4
 adda.w FR0CM(pc),a2
 ENDC
 adda.w FR0DM(pc),a3
 subq.w #1,4(sp)
 bne.w .row
 rts
 endm

 FR0AREA CA,1,1,1,1
 FR0AREA 0A,1,0,1,2
 FR0AREA FA,1,0,1,3
 FR0AREA 3A,1,1,1,4
 FR0AREA FC,1,1,0,5
 FR0AREA C0,1,1,0,6
 FR0AREA 30,1,1,0,7

; D-only constant ($00/$FF).
FR0Area_K:
 moveq #0,d7
 tst.b R_CON0+1(a6)
 beq.b .row
 moveq #-1,d7
.row:
 move.w FR0W(pc),d6
.w:
 move.w d7,(a3)+
 dbra d6,.w
 adda.w FR0DM(pc),a3
 subq.w #1,4(sp)
 bne.b .row
 rts

; ---- descending C->D fill ($AA) ----
FR0Fill:
 move.l a5,a2
 adda.l R_CPT(a6),a2
 addq.l #2,a2
 move.l a5,a3
 adda.l R_DPT(a6),a3
 addq.l #2,a3
 lea (FR0FillTab.l,pc),a4
 btst #3,R_CON1+1(a6)          ; IFE: inclusive table
 beq.b .exc
 lea 1024(a4),a4
.exc:
 move.w R_V(a6),-(sp)
.row:
 moveq #0,d4
 btst #2,R_CON1+1(a6)          ; FCI
 beq.b .fc0
 move.w #$100,d4
.fc0:
 move.w R_H(a6),d6
 subq.w #1,d6
.w:
 move.w -(a2),d0
 bne.b .nz
 move.w d4,d3                  ; zero word: all fc
 beq.b .st
 moveq #-1,d3
 bra.b .st
.nz:
 moveq #0,d1
 move.b d0,d1
 or.w d4,d1
 move.w (a4,d1.w*2),d2         ; out<<8 | newfc
 move.w d2,d3
 lsr.w #8,d3
 moveq #0,d1
 move.w d0,d1
 lsr.w #8,d1
 btst #0,d2
 beq.b .h0
 ori.w #$100,d1
.h0:
 move.w (a4,d1.w*2),d2
 move.w d2,d1
 andi.w #$ff00,d1
 or.w d1,d3
 moveq #0,d4
 btst #0,d2
 beq.b .st
 move.w #$100,d4
.st:
 move.w d3,-(a3)
 dbra d6,.w
 suba.w R_CMOD(a6),a2
 suba.w R_DMOD(a6),a3
 subq.w #1,(sp)
 bne.b .row
 addq.l #2,sp
 rts

; ---- line mode, minterm $4A only (D = C ^ (A & (B | C))) ----
FR0Line:
 cmpi.b #$4a,R_CON0+1(a6)
 bne.w FR0Unsupported
 move.w R_APT+2(a6),d0         ; error term (16 bit)
 move.w R_CON1(a6),d1
 move.w R_CON0(a6),d2
 lsr.w #8,d2
 lsr.w #4,d2                   ; ash
 move.w d1,d3
 lsr.w #8,d3
 lsr.w #4,d3                   ; bsh
 move.l a5,a2
 adda.l R_CPT(a6),a2
 move.l a5,a3
 adda.l R_DPT(a6),a3
 move.w R_CMOD(a6),a1          ; sign-extended row step
 move.w R_V(a6),d6
 subq.w #1,d6
 moveq #0,d5                   ; bit0 onedot, bit1 pixel
.px:
 bclr #1,d5                    ; pixel = !SING || !onedot
 btst #1,d1
 beq.b .p1
 btst #0,d5
 bne.b .p0
.p1:
 bset #1,d5
.p0:
 bset #0,d5
 bclr #6,d1                    ; SIGN from the error term
 tst.w d0
 bpl.b .s0
 bset #6,d1
.s0:
 btst #3,R_CON0(a6)            ; USEA (bit 11)
 beq.b .na
 btst #6,d1
 beq.b .am
 add.w R_BMOD(a6),d0
 bra.b .na
.am:
 add.w R_AMOD(a6),d0
.na:
 move.w R_ADAT(a6),d7          ; A = (adat & afwm) >> ash
 and.w R_AFWM(a6),d7
 lsr.w d2,d7
 move.w R_BDAT(a6),d4          ; B = bdat bit bsh, replicated
 btst d3,d4
 sne d4
 ext.w d4
 or.w (a2),d4                  ; B | C
 and.w d7,d4
 move.w (a2),d7
 eor.w d7,d4                   ; D = C ^ (A & (B | C))
 move.w d4,a4
 ; x step: !SIGN && !SUD -> SUL ? decx : incx ; SUD -> AUL ? decx : incx
 moveq #0,d4                   ; overflow
 btst #4,d1
 bne.b .xsud
 btst #6,d1
 bne.b .xdone
 btst #3,d1
 bra.b .xdo
.xsud:
 btst #2,d1
.xdo:
 bne.b .decx
 moveq #1,d4                   ; incx
 cmpi.w #15,d2
 bne.b .xdone
 addq.l #2,a2
 bra.b .xdone
.decx:
 moveq #-1,d4
 tst.w d2
 bne.b .xdone
 subq.l #2,a2
.xdone:
 add.w d4,d2
 andi.w #15,d2
 ; y step: !SIGN && SUD -> SUL ? decy : incy ; !SUD -> AUL ? decy : incy
 btst #4,d1
 beq.b .ynsud
 btst #6,d1
 bne.b .ydone
 btst #3,d1
 bra.b .ydo
.ynsud:
 btst #2,d1
.ydo:
 bne.b .decy
 adda.l a1,a2
 bclr #0,d5
 bra.b .ydone
.decy:
 suba.l a1,a2
 bclr #0,d5
.ydone:
 subq.w #1,d3
 andi.w #15,d3
 btst #1,d5
 beq.b .nw
 move.w a4,(a3)
.nw:
 move.l a2,a3
 dbra d6,.px
 rts

FR0Unsupported:
 lea (FR0UnsupportedCount.l,pc),a0
 addq.l #1,(a0)
 rts

; ---- exact generic path (any channels, asc/desc, fill, any minterm) ----
FR0Generic:
 lea (FR0GenericCount.l,pc),a0
 addq.l #1,(a0)
 move.w R_CON0(a6),d7
 btst #8,d7
 beq.w FR0Unsupported          ; D disabled: nothing visible (none in the frame)
 moveq #2,d6                   ; step
 btst #1,R_CON1+1(a6)
 beq.b .asc
 moveq #-2,d6
.asc:
 lea (FR0G.l,pc),a4            ; state block
 move.l a5,d0
 add.l R_APT(a6),d0
 move.l d0,0(a4)               ; pa
 move.l a5,d0
 add.l R_BPT(a6),d0
 move.l d0,4(a4)               ; pb
 move.l a5,d0
 add.l R_CPT(a6),d0
 move.l d0,8(a4)               ; pc
 move.l a5,d0
 add.l R_DPT(a6),d0
 move.l d0,12(a4)              ; pd
 clr.w 16(a4)                  ; aold
 clr.w 18(a4)                  ; bold
 move.w R_ADAT(a6),20(a4)      ; adat
 move.w R_CDAT(a6),22(a4)      ; cdat
 move.w R_BDAT(a6),d0          ; bhold for disabled B: bdat >> bsh
 move.w R_CON1(a6),d1
 lsr.w #8,d1
 lsr.w #4,d1
 lsr.w d1,d0
 move.w d0,24(a4)              ; bhold
 move.w R_V(a6),26(a4)         ; rows
.row:
 moveq #0,d5                   ; fc
 btst #2,R_CON1+1(a6)
 beq.b .f0
 moveq #1,d5
.f0:
 moveq #0,d4                   ; word index
.word:
 ; A
 btst #11,d7
 beq.b .ad
 move.l 0(a4),a0
 move.w (a0),20(a4)
 adda.w d6,a0
 move.l a0,0(a4)
.ad:
 move.w 20(a4),d0
 tst.w d4
 bne.b .nf
 and.w R_AFWM(a6),d0
.nf:
 move.w R_H(a6),d1
 subq.w #1,d1
 cmp.w d4,d1
 bne.b .nl
 and.w R_ALWM(a6),d0
.nl:
 move.w R_CON0(a6),d1
 lsr.w #8,d1
 lsr.w #4,d1                   ; ash
 bsr.w FR0GShift               ; d0 = new, 16(a4) = old -> d0 shifted
 move.w d0,d2                  ; A
 ; B
 btst #10,d7
 beq.b .bd
 move.l 4(a4),a0
 move.w (a0),d0
 adda.w d6,a0
 move.l a0,4(a4)
 move.w R_CON1(a6),d1
 lsr.w #8,d1
 lsr.w #4,d1
 lea 18(a4),a1
 bsr.w FR0GShiftB
 move.w d0,24(a4)
.bd:
 move.w 24(a4),d3              ; B
 ; C
 btst #9,d7
 beq.b .cd
 move.l 8(a4),a0
 move.w (a0),22(a4)
 adda.w d6,a0
 move.l a0,8(a4)
.cd:
 move.w 22(a4),d1              ; C
 bsr.w FR0GMinterm             ; d2 A, d3 B, d1 C -> d0
 move.w R_CON1(a6),d1
 andi.w #$18,d1
 beq.b .nofill
 bsr.w FR0GFill                ; d0, d5 fc
.nofill:
 move.l 12(a4),a0
 move.w d0,(a0)
 adda.w d6,a0
 move.l a0,12(a4)
 addq.w #1,d4
 cmp.w R_H(a6),d4
 blo.w .word
 ; modulos (subtracted when descending)
 lea R_AMOD(a6),a1
 moveq #4-1,d3
 lea (a4),a0
.mods:
 move.w (a1)+,d0
 ext.l d0
 tst.w d6
 bpl.b .mp
 neg.l d0
.mp:
 add.l d0,(a0)+
 dbra d3,.mods
 subq.w #1,26(a4)
 bne.w .row
 rts

; d0 = new word, (a1) = previous word, d1 = shift -> d0 shifted; (a1) = new.
; Asc: (old:new) >> sh. Desc: (new:old) >> (16 - sh).
FR0GShift:
 lea 16(a4),a1
FR0GShiftB:
 move.l d2,-(sp)
 move.w (a1),d2
 move.w d0,(a1)
 tst.w d6
 bmi.b .desc
 swap d2
 move.w d0,d2
 lsr.l d1,d2
 move.w d2,d0
 move.l (sp)+,d2
 rts
.desc:
 swap d0
 move.w d2,d0
 moveq #16,d2
 sub.w d1,d2
 lsr.l d2,d0
 move.l (sp)+,d2
 rts

; d2 = A, d3 = B, d1 = C, minterm in con0 low byte -> d0
FR0GMinterm:
 moveq #0,d0
 movem.l d4-d6,-(sp)
 move.b R_CON0+1(a6),d4
 moveq #7,d5
.t:
 btst d5,d4
 beq.b .n
 move.w #-1,d6
 btst #2,d5
 bne.b .a1
 move.w d2,-(sp)
 not.w (sp)
 and.w (sp)+,d6
 bra.b .a2
.a1:
 and.w d2,d6
.a2:
 btst #1,d5
 bne.b .b1
 move.w d3,-(sp)
 not.w (sp)
 and.w (sp)+,d6
 bra.b .b2
.b1:
 and.w d3,d6
.b2:
 btst #0,d5
 bne.b .c1
 move.w d1,-(sp)
 not.w (sp)
 and.w (sp)+,d6
 bra.b .c2
.c1:
 and.w d1,d6
.c2:
 or.w d6,d0
.n:
 dbra d5,.t
 movem.l (sp)+,d4-d6
 rts

; d0 = word, d5 = fc (0/1) -> d0 filled, d5 updated
FR0GFill:
 movem.l d1-d3/a0,-(sp)
 lea (FR0FillTab.l,pc),a0
 btst #3,R_CON1+1(a6)
 beq.b .x
 lea 1024(a0),a0
.x:
 moveq #0,d1
 move.b d0,d1
 tst.w d5
 beq.b .l0
 ori.w #$100,d1
.l0:
 move.w (a0,d1.w*2),d2
 move.w d2,d3
 lsr.w #8,d3
 moveq #0,d1
 move.w d0,d1
 lsr.w #8,d1
 btst #0,d2
 beq.b .h0
 ori.w #$100,d1
.h0:
 move.w (a0,d1.w*2),d2
 move.w d2,d1
 andi.w #$ff00,d1
 or.w d1,d3
 moveq #0,d5
 btst #0,d2
 beq.b .d
 moveq #1,d5
.d:
 move.w d3,d0
 movem.l (sp)+,d1-d3/a0
 rts

; ---- specializations (exact under their conditions) ----
; Returns d0 = 1 when the blit was executed here.
FR0AreaSpecial:
 move.w R_CON0(a6),d7
 move.w d7,d0
 andi.w #$f000,d0
 bne.w FR0Cookie               ; shifted: cookie-cut candidate
 move.w R_CON1(a6),d0
 andi.w #$f000,d0
 bne.w .no
 cmpi.l #$ffffffff,R_AFWM(a6)  ; both masks open
 bne.w .no
 move.w d7,d0
 andi.w #$0d00,d0              ; A, B, D (C ignored by these minterms)
 cmpi.w #$0d00,d0
 bne.w .no
 cmpi.b #$fc,d7
 beq.w FR0Abd_FC
 cmpi.b #$c0,d7
 beq.w FR0Abd_C0
 cmpi.b #$30,d7
 beq.w FR0Abd_30
.no:
 moveq #0,d0
 rts

; Unshifted ABD with open masks: longs, then the odd word.
FR0ABD macro
FR0Abd_\1:
 move.l a5,a0
 adda.l R_APT(a6),a0
 move.l a5,a1
 adda.l R_BPT(a6),a1
 move.l a5,a3
 adda.l R_DPT(a6),a3
 move.w R_H(a6),d5
 move.w R_V(a6),d4
 subq.w #1,d4
.row:
 move.w d5,d6
 lsr.w #1,d6
 subq.w #1,d6
 bmi.b .odd
.l:
 move.l (a0)+,d0
 move.l (a1)+,d1
 IFEQ \2-1
 or.l d1,d0
 ENDC
 IFEQ \2-2
 and.l d1,d0
 ENDC
 IFEQ \2-3
 not.l d1
 and.l d1,d0
 ENDC
 move.l d0,(a3)+
 dbra d6,.l
.odd:
 btst #0,d5
 beq.b .ev
 move.w (a0)+,d0
 move.w (a1)+,d1
 IFEQ \2-1
 or.w d1,d0
 ENDC
 IFEQ \2-2
 and.w d1,d0
 ENDC
 IFEQ \2-3
 not.w d1
 and.w d1,d0
 ENDC
 move.w d0,(a3)+
.ev:
 adda.w R_AMOD(a6),a0
 adda.w R_BMOD(a6),a1
 adda.w R_DMOD(a6),a3
 dbra d4,.row
 moveq #1,d0
 rts
 endm
 FR0ABD FC,1
 FR0ABD C0,2
 FR0ABD 30,3

; Cookie-cut $CA with A, B, C, D, ash = bsh, C = D (same pointer and modulo):
; transparent mask words leave D untouched, opaque words take B.
FR0Cookie:
 cmpi.b #$ca,d7
 bne.w .no
 move.w d7,d0
 andi.w #$0f00,d0
 cmpi.w #$0f00,d0
 bne.w .no
 move.w R_CON1(a6),d0
 eor.w d7,d0
 andi.w #$f000,d0              ; ash == bsh
 bne.w .no
 move.l R_CPT(a6),d0
 cmp.l R_DPT(a6),d0
 bne.w .no
 move.w R_CMOD(a6),d0
 cmp.w R_DMOD(a6),d0
 bne.w .no
 cmpi.w #$ffff,R_AFWM(a6)
 beq.w FR0Cookie2
 move.l a5,a0
 adda.l R_APT(a6),a0
 move.l a5,a1
 adda.l R_BPT(a6),a1
 move.l a5,a3
 adda.l R_DPT(a6),a3
 move.w d7,d5
 lsr.w #8,d5
 lsr.w #4,d5                   ; shift
 lea (FR0Mask.l,pc),a4         ; first/last masks
 move.w R_H(a6),d6
 move.w d6,d0
 subq.w #1,d0
.m:
 move.w #-1,(a4)+
 dbra d0,.m
 lea (FR0Mask.l,pc),a4
 move.w R_AFWM(a6),(a4)
 move.w R_ALWM(a6),d0
 and.w d0,-2(a4,d6.w*2)
 subq.w #1,d6
 lea (FR0W.l,pc),a2
 move.w d6,(a2)
 moveq #0,d0
 moveq #0,d2
 move.w R_V(a6),d4
 subq.w #1,d4
.row:
 lea (FR0Mask.l,pc),a4
 move.w FR0W(pc),d6
.w:
 swap d0
 move.w (a0)+,d0
 and.w (a4)+,d0
 move.l d0,d1
 lsr.l d5,d1                   ; A
 swap d2
 move.w (a1)+,d2
 move.l d2,d3
 lsr.l d5,d3                   ; B
 tst.w d1
 beq.b .skip
 cmpi.w #-1,d1
 beq.b .opaque
 move.w (a3),d7
 eor.w d7,d3
 and.w d1,d3
 eor.w d7,d3
.opaque:
 move.w d3,(a3)+
 dbra d6,.w
 bra.b .eol
.skip:
 addq.l #2,a3
 dbra d6,.w
.eol:
 adda.w R_AMOD(a6),a0
 adda.w R_BMOD(a6),a1
 adda.w R_DMOD(a6),a3
 dbra d4,.row
 moveq #1,d0
 rts
.no:
 moveq #0,d0
 rts

; ---- line mode, Bresenham with XOR: minterm $4A, A = $8000 open, solid
; texture, A and C enabled, B disabled. Otherwise the exact FR0Line. ----
FR0LineFast:
 move.w R_CON0(a6),d7
 cmpi.b #$4a,d7
 bne.w FR0Line
 andi.w #$0e00,d7
 cmpi.w #$0a00,d7              ; A and C, no B
 bne.w FR0Line
 cmpi.w #$8000,R_ADAT(a6)
 bne.w FR0Line
 cmpi.w #$ffff,R_AFWM(a6)
 bne.w FR0Line
 cmpi.w #$ffff,R_BDAT(a6)
 bne.w FR0Line
 move.w R_APT+2(a6),d0         ; error term
 move.w R_AMOD(a6),d1
 move.w R_BMOD(a6),d2
 move.w R_CON0(a6),d3
 lsr.w #8,d3
 lsr.w #4,d3                   ; bit position from the left
 move.w R_CON1(a6),d7          ; octant bits
 move.l a5,a2
 adda.l R_CPT(a6),a2
 move.w R_CMOD(a6),a1
 move.w R_V(a6),d6
 subq.w #1,d6
 moveq #0,d5                   ; onedot
.px:
 btst #1,d7                    ; SING: first pixel of a row only
 beq.b .draw
 tst.b d5
 bne.b .nodraw
.draw:
 move.w #$8000,d4
 lsr.w d3,d4
 eor.w d4,(a2)
.nodraw:
 st d5
 tst.w d0
 bmi.b .neg
 add.w d1,d0
 ; non-negative: major and minor steps
 btst #4,d7                    ; SUD
 beq.b .p_nsud
 bsr.b .stepx_aul
 btst #3,d7                    ; SUL -> y
 bne.b .yup
 adda.l a1,a2
 sf d5
 dbra d6,.px
 rts
.yup:
 suba.l a1,a2
 sf d5
 dbra d6,.px
 rts
.p_nsud:
 btst #3,d7                    ; SUL -> x
 bne.b .pxd
 bsr.b .incx
 bra.b .p_y
.pxd:
 bsr.b .decx
.p_y:
 bsr.b .stepy_aul
 dbra d6,.px
 rts
.neg:
 add.w d2,d0
 btst #4,d7
 beq.b .n_nsud
 bsr.b .stepx_aul
 dbra d6,.px
 rts
.n_nsud:
 bsr.b .stepy_aul
 dbra d6,.px
 rts
.stepx_aul:
 btst #2,d7
 bne.b .decx
.incx:
 addq.w #1,d3
 cmpi.w #16,d3
 bne.b .r
 moveq #0,d3
 addq.l #2,a2
.r:
 rts
.decx:
 subq.w #1,d3
 bpl.b .r
 moveq #15,d3
 subq.l #2,a2
 rts
.stepy_aul:
 sf d5
 btst #2,d7
 bne.b .ydn
 adda.l a1,a2
 rts
.ydn:
 suba.l a1,a2
 rts

; Cookie-cut, two words per step: 32-bit reads and a funnel shift
; (prev << (32 - sh)) | (cur >> sh). Words 0..h-2 in pairs (+1 single when
; h-1 is odd), then the last word with ALWM. First mask must be $FFFF.
; d2/d5 keep the previous A/B word in their low word (masked, as the blitter's
; old-data latch, carried across rows).
FR0Cookie2:
 move.l a5,a0
 adda.l R_APT(a6),a0
 move.l a5,a1
 adda.l R_BPT(a6),a1
 move.l a5,a3
 adda.l R_DPT(a6),a3
 move.w d7,d6
 lsr.w #8,d6
 lsr.w #4,d6                   ; sh
 moveq #32,d7
 sub.w d6,d7                   ; 32 - sh
 moveq #0,d2
 moveq #0,d5
 move.w R_V(a6),-(sp)          ; rows at 2(sp) after the pair counter push
.row:
 move.w R_H(a6),d0
 subq.w #1,d0                  ; words before the last
 move.w d0,-(sp)               ; remember parity
 lsr.w #1,d0
 move.w d0,-(sp)               ; pairs
 beq.w .single
.pair:
 move.l (a0)+,d0
 move.l d0,d1
 lsr.l d6,d1
 lsl.l d7,d2
 or.l d2,d1                    ; A pair
 move.l d0,d2
 move.l (a1)+,d3
 move.l d3,d4
 lsr.l d6,d4
 lsl.l d7,d5
 or.l d5,d4                    ; B pair
 move.l d3,d5
 tst.l d1
 beq.b .pskip
 cmpi.l #-1,d1
 beq.b .popaque
 move.l (a3),d0
 eor.l d0,d4
 and.l d1,d4
 eor.l d0,d4
.popaque:
 move.l d4,(a3)+
 subq.w #1,(sp)
 bne.b .pair
 bra.b .single
.pskip:
 addq.l #4,a3
 subq.w #1,(sp)
 bne.b .pair
.single:
 addq.l #2,sp
 move.w (sp)+,d0
 btst #0,d0
 beq.b .last
 bsr.b .word
.last:
 swap d2
 move.w (a0)+,d2
 and.w R_ALWM(a6),d2
 move.l d2,d1
 lsr.l d6,d1
 swap d5
 move.w (a1)+,d5
 move.l d5,d4
 lsr.l d6,d4
 bsr.b .combine
 adda.w R_AMOD(a6),a0
 adda.w R_BMOD(a6),a1
 adda.w R_DMOD(a6),a3
 subq.w #1,(sp)
 bne.w .row
 addq.l #2,sp
 moveq #1,d0
 rts
.word:
 swap d2
 move.w (a0)+,d2
 move.l d2,d1
 lsr.l d6,d1
 swap d5
 move.w (a1)+,d5
 move.l d5,d4
 lsr.l d6,d4
.combine:
 tst.w d1
 beq.b .wskip
 cmpi.w #-1,d1
 beq.b .wopaque
 move.w (a3),d0
 eor.w d0,d4
 and.w d1,d4
 eor.w d0,d4
.wopaque:
 move.w d4,(a3)+
 rts
.wskip:
 addq.l #2,a3
 rts
