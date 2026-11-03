; FR2 exact software blitter (reference; FASTRAM_PLAN.md FR2). 68020+.
; FastRenderBlit executes one blit from a register image, the way the
; blitter would, on memory the CPU addresses directly (Fast RAM shadows).
; Speed is not a goal: this is the oracle for the FR6 kernels.
;
; The image mirrors custom registers $040-$075 (offset = register - $40), so
; a redirected site can write it with its usual register offsets. Two words
; of internal blitter state follow. Semantics are the emulator's cycle-exact
; blitter, checked against the hardware blitter by the FR2 oracle fixture:
; - BLTSIZE: width bits 0-5 (0 = 64 words), height bits 6-15 (0 = 1024).
; - Pointer and modulo bit 0 is ignored.
; - The A and B shift history is cleared at blit start. A disabled B channel
;   supplies the B hold of the last BLTBDAT write (FastRenderBDAT) or B read.
; - The fill carry restarts from FCI on every row; IFE with EFE acts as EFE.
; - Line mode needs width 2 and B off (the only form in use; otherwise d0 = 1
;   and nothing is written). ASH, BSH, SIGN and the pointers are written back.
; - Afterwards the image holds the hardware's end state: pointers, the last
;   words read into ADAT/BDAT/CDAT, and the B shift state.
; BZERO is not produced: FR1 found no reader.
FRB_CON0 equ $00
FRB_CON1 equ $02
FRB_AFWM equ $04
FRB_ALWM equ $06
FRB_CPT equ $08
FRB_BPT equ $0c
FRB_APT equ $10
FRB_DPT equ $14
FRB_SIZE equ $18
FRB_CMOD equ $20
FRB_BMOD equ $22
FRB_AMOD equ $24
FRB_DMOD equ $26
FRB_CDAT equ $30
FRB_BDAT equ $32
FRB_ADAT equ $34
FRB_BOLD equ $36                ; internal: previous B word
FRB_BHOLD equ $38               ; internal: shifted B word
FRB_IMAGE equ $3c

; Locals (link a6).
FRBL_STEP equ -4
FRBL_AMOD equ -8
FRBL_BMOD equ -12
FRBL_CMOD equ -16
FRBL_DMOD equ -20
FRBL_H equ -22
FRBL_V equ -24
FRBL_ASHL equ -26               ; area: A combine shift; line: ASH
FRBL_BSHL equ -28               ; area: B combine shift; line: BSH
FRBL_AOLD equ -30
FRBL_BOLD equ -32
FRBL_ADAT equ -34
FRBL_BDAT equ -36
FRBL_CDAT equ -38
FRBL_BHOLD equ -40
FRBL_FC equ -42
FRBL_I equ -44
FRBL_ONEDOT equ -46
FRBL_PIXEL equ -48
FRBL_D equ -50
FRBL_APT equ -56                ; line: error term
FRBL_SIZE equ -56

; a0 = image, d0.w = value written to BLTBDAT. Uses BLTCON1 as written.
FastRenderBDAT:
 movem.l d1-d2,-(sp)
 move.w FRB_CON1(a0),d2
 lsr.w #8,d2
 lsr.w #4,d2
 btst #1,FRB_CON1+1(a0)
 bne.b .desc
 move.w FRB_BOLD(a0),d1         ; (old:new) >> shift
 swap d1
 move.w d0,d1
 bra.b .shift
.desc:
 move.w d0,d1                   ; (new:old) >> (16 - shift)
 swap d1
 move.w FRB_BOLD(a0),d1
 neg.w d2
 add.w #16,d2
.shift:
 lsr.l d2,d1
 move.w d1,FRB_BHOLD(a0)
 move.w d0,FRB_BDAT(a0)
 move.w d0,FRB_BOLD(a0)
 movem.l (sp)+,d1-d2
 rts

; a0 = image with BLTSIZE in FRB_SIZE. Returns d0.l = 0, or 1 if the blit
; is outside the supported line form. Other registers are preserved.
FastRenderBlit:
 movem.l d1-d7/a1-a6,-(sp)
 link a6,#FRBL_SIZE
 move.w FRB_CON0(a0),d7
 move.w FRB_CON1(a0),d6
 moveq #0,d5
 move.b d7,d5                   ; minterm
 bsr.w FRBMinterm               ; -> a5
 move.w FRB_SIZE(a0),d0
 move.w d0,d1
 andi.w #$3f,d0
 bne.b .h
 moveq #64,d0
.h:
 move.w d0,FRBL_H(a6)
 lsr.w #6,d1
 bne.b .v
 move.w #1024,d1
.v:
 move.w d1,FRBL_V(a6)
 btst #0,d6
 bne.w FRBLine
 bsr.w FRBArea
 moveq #0,d0
FRBExit:
 unlk a6
 movem.l (sp)+,d1-d7/a1-a6
 rts

; d5 = minterm -> a5 = evaluator (d2 A, d3 B, d4 C -> d0; may use d1).
FRBMinterm:
 lea FRBMtTab(pc),a1
.find:
 move.w (a1)+,d0
 bmi.b .generic
 move.w (a1)+,d1
 cmp.w d0,d5
 bne.b .find
 lea FRBMtTab(pc),a5
 adda.w d1,a5
 rts
.generic:
 lea FRBMtGeneric(pc),a5
 rts

; Direct evaluators for the minterms FR1 found during driving.
FRBMtTab:
 dc.w $ca,FRBMt_CA-FRBMtTab
 dc.w $0a,FRBMt_0A-FRBMtTab
 dc.w $fa,FRBMt_FA-FRBMtTab
 dc.w $3a,FRBMt_3A-FRBMtTab
 dc.w $fc,FRBMt_FC-FRBMtTab
 dc.w $c0,FRBMt_C0-FRBMtTab
 dc.w $30,FRBMt_30-FRBMtTab
 dc.w $4a,FRBMt_4A-FRBMtTab
 dc.w $aa,FRBMt_AA-FRBMtTab
 dc.w $ea,FRBMt_EA-FRBMtTab
 dc.w $2a,FRBMt_2A-FRBMtTab
 dc.w $00,FRBMt_00-FRBMtTab
 dc.w $ff,FRBMt_FF-FRBMtTab
 dc.w -1

FRBMt_CA:                       ; A ? B : C
 move.w d2,d0
 and.w d3,d0
 move.w d2,d1
 not.w d1
 and.w d4,d1
 or.w d1,d0
 rts
FRBMt_0A:                       ; ~A & C
 move.w d2,d0
 not.w d0
 and.w d4,d0
 rts
FRBMt_FA:                       ; A | C
 move.w d2,d0
 or.w d4,d0
 rts
FRBMt_3A:                       ; A ? ~B : C
 move.w d3,d0
 not.w d0
 and.w d2,d0
 move.w d2,d1
 not.w d1
 and.w d4,d1
 or.w d1,d0
 rts
FRBMt_FC:                       ; A | B
 move.w d2,d0
 or.w d3,d0
 rts
FRBMt_C0:                       ; A & B
 move.w d2,d0
 and.w d3,d0
 rts
FRBMt_30:                       ; A & ~B
 move.w d3,d0
 not.w d0
 and.w d2,d0
 rts
FRBMt_4A:                       ; A ? (B & ~C) : C
 move.w d4,d0
 not.w d0
 and.w d3,d0
 and.w d2,d0
 move.w d2,d1
 not.w d1
 and.w d4,d1
 or.w d1,d0
 rts
FRBMt_AA:                       ; C
 move.w d4,d0
 rts
FRBMt_EA:                       ; C | (A & B)
 move.w d2,d0
 and.w d3,d0
 or.w d4,d0
 rts
FRBMt_2A:                       ; C & ~(A & B)
 move.w d2,d0
 and.w d3,d0
 not.w d0
 and.w d4,d0
 rts
FRBMt_00:
 moveq #0,d0
 rts
FRBMt_FF:
 moveq #-1,d0
 rts

; Any minterm: OR of the selected products of A/~A, B/~B and C/~C.
FRBMtGeneric:
 movem.l d6-d7,-(sp)
 moveq #0,d0
 moveq #7,d7
.term:
 btst d7,d5
 beq.b .next
 move.w d2,d1
 btst #2,d7
 bne.b .a
 not.w d1
.a:
 move.w d3,d6
 btst #1,d7
 bne.b .b
 not.w d6
.b:
 and.w d6,d1
 move.w d4,d6
 btst #0,d7
 bne.b .c
 not.w d6
.c:
 and.w d6,d1
 or.w d1,d0
.next:
 dbra d7,.term
 movem.l (sp)+,d6-d7
 rts

; d0 = minterm output, FRBL_FC = carry -> d0 filled, carry updated.
; Bit 0 (rightmost) first, as the blitter fills right to left.
FRBFill:
 movem.l d1-d4,-(sp)
 move.w d0,d1
 move.w FRBL_FC(a6),d2
 move.w d6,d4
 andi.w #$18,d4                 ; $08 = inclusive only
 moveq #0,d3
.bit:
 tst.w d2
 beq.b .carry
 cmpi.w #$08,d4
 bne.b .exclusive
 bset d3,d0
 bra.b .carry
.exclusive:
 bchg d3,d0
.carry:
 btst d3,d1
 beq.b .same
 eori.w #1,d2
.same:
 addq.w #1,d3
 cmpi.w #16,d3
 blo.b .bit
 move.w d2,FRBL_FC(a6)
 movem.l (sp)+,d1-d4
 rts

; Load a modulo: bit 0 cleared, sign-extended, negated when descending.
FRBMOD macro
 move.w \1(a0),d0
 andi.w #$fffe,d0
 ext.l d0
 btst #1,d6
 beq.b .m\@
 neg.l d0
.m\@:
 move.l d0,\2(a6)
 endm

; Area mode. d7 = BLTCON0, d6 = BLTCON1, a5 = minterm evaluator.
FRBArea:
 moveq #2,d0
 btst #1,d6
 beq.b .asc
 moveq #-2,d0
.asc:
 move.l d0,FRBL_STEP(a6)
 FRBMOD FRB_AMOD,FRBL_AMOD
 FRBMOD FRB_BMOD,FRBL_BMOD
 FRBMOD FRB_CMOD,FRBL_CMOD
 FRBMOD FRB_DMOD,FRBL_DMOD
 move.w d7,d0
 lsr.w #8,d0
 lsr.w #4,d0                    ; ASH
 move.w d6,d1
 lsr.w #8,d1
 lsr.w #4,d1                    ; BSH
 btst #1,d6
 beq.b .shifts
 neg.w d0
 add.w #16,d0
 neg.w d1
 add.w #16,d1
.shifts:
 move.w d0,FRBL_ASHL(a6)
 move.w d1,FRBL_BSHL(a6)
 clr.w FRBL_AOLD(a6)
 clr.w FRBL_BOLD(a6)
 move.w FRB_ADAT(a0),FRBL_ADAT(a6)
 move.w FRB_BDAT(a0),FRBL_BDAT(a6)
 move.w FRB_CDAT(a0),FRBL_CDAT(a6)
 move.w FRB_BHOLD(a0),FRBL_BHOLD(a6)
 move.l FRB_APT(a0),d0
 bclr #0,d0
 move.l d0,a1
 move.l FRB_BPT(a0),d0
 bclr #0,d0
 move.l d0,a2
 move.l FRB_CPT(a0),d0
 bclr #0,d0
 move.l d0,a3
 move.l FRB_DPT(a0),d0
 bclr #0,d0
 move.l d0,a4
.row:
 clr.w FRBL_I(a6)
 moveq #0,d0
 btst #2,d6                     ; FCI
 beq.b .fc
 moveq #1,d0
.fc:
 move.w d0,FRBL_FC(a6)
.word:
 btst #11,d7                    ; A
 beq.b .anone
 move.w (a1),FRBL_ADAT(a6)
 adda.l FRBL_STEP(a6),a1
.anone:
 move.w FRBL_ADAT(a6),d0
 tst.w FRBL_I(a6)
 bne.b .notfirst
 and.w FRB_AFWM(a0),d0
.notfirst:
 move.w FRBL_I(a6),d1
 addq.w #1,d1
 cmp.w FRBL_H(a6),d1
 bne.b .notlast
 and.w FRB_ALWM(a0),d0
.notlast:
 move.w FRBL_ASHL(a6),d3
 btst #1,d6
 bne.b .adesc
 move.w FRBL_AOLD(a6),d2        ; (old:new) >> ASH
 swap d2
 move.w d0,d2
 bra.b .ashift
.adesc:
 move.w d0,d2                   ; (new:old) >> (16 - ASH)
 swap d2
 move.w FRBL_AOLD(a6),d2
.ashift:
 lsr.l d3,d2                    ; d2.w = A
 move.w d0,FRBL_AOLD(a6)
 btst #10,d7                    ; B
 beq.b .bnone
 move.w (a2),d0
 adda.l FRBL_STEP(a6),a2
 move.w d0,FRBL_BDAT(a6)
 move.w FRBL_BSHL(a6),d3
 btst #1,d6
 bne.b .bdesc
 move.w FRBL_BOLD(a6),d1
 swap d1
 move.w d0,d1
 bra.b .bshift
.bdesc:
 move.w d0,d1
 swap d1
 move.w FRBL_BOLD(a6),d1
.bshift:
 lsr.l d3,d1
 move.w d1,FRBL_BHOLD(a6)
 move.w d0,FRBL_BOLD(a6)
.bnone:
 move.w FRBL_BHOLD(a6),d3       ; B
 btst #9,d7                     ; C
 beq.b .cnone
 move.w (a3),FRBL_CDAT(a6)
 adda.l FRBL_STEP(a6),a3
.cnone:
 move.w FRBL_CDAT(a6),d4        ; C
 jsr (a5)
 move.w d6,d1
 andi.w #$18,d1
 beq.b .nofill
 bsr.w FRBFill
.nofill:
 btst #8,d7                     ; D
 beq.b .dnone
 move.w d0,(a4)
 adda.l FRBL_STEP(a6),a4
.dnone:
 addq.w #1,FRBL_I(a6)
 move.w FRBL_I(a6),d0
 cmp.w FRBL_H(a6),d0
 blo.w .word
 btst #11,d7
 beq.b .ma
 adda.l FRBL_AMOD(a6),a1
.ma:
 btst #10,d7
 beq.b .mb
 adda.l FRBL_BMOD(a6),a2
.mb:
 btst #9,d7
 beq.b .mc
 adda.l FRBL_CMOD(a6),a3
.mc:
 btst #8,d7
 beq.b .md
 adda.l FRBL_DMOD(a6),a4
.md:
 subq.w #1,FRBL_V(a6)
 bne.w .row
 ; End state.
 btst #11,d7
 beq.b .ea
 move.l a1,FRB_APT(a0)
 move.w FRBL_ADAT(a6),FRB_ADAT(a0)
.ea:
 btst #10,d7
 beq.b .eb
 move.l a2,FRB_BPT(a0)
 move.w FRBL_BDAT(a6),FRB_BDAT(a0)
 move.w FRBL_BHOLD(a6),FRB_BHOLD(a0)
.eb:
 move.w FRBL_BOLD(a6),FRB_BOLD(a0)
 btst #9,d7
 beq.b .ec
 move.l a3,FRB_CPT(a0)
 move.w FRBL_CDAT(a6),FRB_CDAT(a0)
.ec:
 btst #8,d7
 beq.b .ed
 move.l a4,FRB_DPT(a0)
.ed:
 rts

; Line mode. d7 = BLTCON0, d6 = BLTCON1 (SIGN is kept up to date here),
; FRBL_APT = APT (error term), a3 = CPT, a4 = DPT, a5 = minterm evaluator.
FRBLine:
 cmpi.w #2,FRBL_H(a6)
 bne.w .unsupported
 btst #10,d7
 bne.w .unsupported
 move.w FRB_AMOD(a0),d0
 andi.w #$fffe,d0
 ext.l d0
 move.l d0,FRBL_AMOD(a6)
 move.w FRB_BMOD(a0),d0
 andi.w #$fffe,d0
 ext.l d0
 move.l d0,FRBL_BMOD(a6)
 move.w FRB_CMOD(a0),d0
 andi.w #$fffe,d0
 ext.l d0
 move.l d0,FRBL_CMOD(a6)
 move.w d7,d0
 lsr.w #8,d0
 lsr.w #4,d0
 move.w d0,FRBL_ASHL(a6)        ; ASH
 move.w d6,d1
 lsr.w #8,d1
 lsr.w #4,d1
 move.w d1,FRBL_BSHL(a6)        ; BSH
 move.w FRB_BDAT(a0),d0
 ror.w d1,d0
 move.w d0,FRBL_BHOLD(a6)       ; texture word, rotated by BSH
 move.w FRB_CDAT(a0),FRBL_CDAT(a6)
 clr.w FRBL_ONEDOT(a6)
 move.l FRB_APT(a0),FRBL_APT(a6)
 move.l FRB_CPT(a0),d0
 bclr #0,d0
 move.l d0,a3
 move.l FRB_DPT(a0),d0
 bclr #0,d0
 move.l d0,a4
.pixel:
 move.w #1,FRBL_PIXEL(a6)       ; SING: one dot per row
 btst #1,d6
 beq.b .dot
 tst.w FRBL_ONEDOT(a6)
 beq.b .dot
 clr.w FRBL_PIXEL(a6)
.dot:
 move.w #1,FRBL_ONEDOT(a6)
 bclr #6,d6                     ; SIGN from the error term
 tst.w FRBL_APT+2(a6)
 bpl.b .sign
 bset #6,d6
.sign:
 btst #11,d7
 beq.b .noa
 move.l FRBL_AMOD(a6),d0
 btst #6,d6
 beq.b .amod
 move.l FRBL_BMOD(a6),d0
.amod:
 add.l d0,FRBL_APT(a6)
.noa:
 btst #9,d7
 beq.b .noc
 move.w (a3),FRBL_CDAT(a6)
.noc:
 move.w FRB_ADAT(a0),d2
 and.w FRB_AFWM(a0),d2
 move.w FRBL_ASHL(a6),d0
 lsr.w d0,d2                    ; A
 moveq #0,d3
 btst #0,FRBL_BHOLD+1(a6)
 beq.b .tex
 moveq #-1,d3                   ; B
.tex:
 move.w FRBL_CDAT(a6),d4        ; C
 jsr (a5)
 move.w d0,FRBL_D(a6)
 ; X step: SUD clear and SIGN clear uses SUL; SUD set uses AUL.
 btst #4,d6
 bne.b .xsud
 btst #6,d6
 bne.b .xdone
 btst #3,d6
 bne.b .decx
 bra.b .incx
.xsud:
 btst #2,d6
 bne.b .decx
.incx:
 cmpi.w #15,FRBL_ASHL(a6)
 bne.b .incx1
 addq.l #2,a3
.incx1:
 addq.w #1,FRBL_ASHL(a6)
 andi.w #15,FRBL_ASHL(a6)
 bra.b .xdone
.decx:
 tst.w FRBL_ASHL(a6)
 bne.b .decx1
 subq.l #2,a3
.decx1:
 subq.w #1,FRBL_ASHL(a6)
 andi.w #15,FRBL_ASHL(a6)
.xdone:
 ; Y step (C enabled): SUD set and SIGN clear uses SUL; SUD clear uses AUL.
 btst #9,d7
 beq.b .ydone
 btst #4,d6
 beq.b .ynosud
 btst #6,d6
 bne.b .ydone
 btst #3,d6
 bne.b .decy
 bra.b .incy
.ynosud:
 btst #2,d6
 bne.b .decy
.incy:
 adda.l FRBL_CMOD(a6),a3
 clr.w FRBL_ONEDOT(a6)
 bra.b .ydone
.decy:
 suba.l FRBL_CMOD(a6),a3
 clr.w FRBL_ONEDOT(a6)
.ydone:
 move.w FRBL_BSHL(a6),d1        ; BSH steps down per pixel
 subq.w #1,d1
 andi.w #15,d1
 move.w d1,FRBL_BSHL(a6)
 move.w FRB_BDAT(a0),d0
 ror.w d1,d0
 move.w d0,FRBL_BHOLD(a6)
 tst.w FRBL_PIXEL(a6)
 beq.b .nowrite
 btst #9,d7
 beq.b .nowrite
 move.w FRBL_D(a6),(a4)
.nowrite:
 move.l a3,a4
 subq.w #1,FRBL_V(a6)
 bne.w .pixel
 ; End state.
 andi.w #$0fff,d7
 move.w FRBL_ASHL(a6),d0
 ror.w #4,d0
 or.w d0,d7
 move.w d7,FRB_CON0(a0)
 andi.w #$0fff,d6
 move.w FRBL_BSHL(a6),d0
 ror.w #4,d0
 or.w d0,d6
 move.w d6,FRB_CON1(a0)
 move.l FRBL_APT(a6),FRB_APT(a0)
 move.l a3,FRB_CPT(a0)
 move.l a4,FRB_DPT(a0)
 move.w FRBL_CDAT(a6),FRB_CDAT(a0)
 moveq #0,d0
 btst #0,FRBL_BHOLD+1(a6)
 beq.b .hold
 moveq #-1,d0
.hold:
 move.w d0,FRB_BHOLD(a0)
 clr.w FRB_BOLD(a0)
 moveq #0,d0
 bra.w FRBExit
.unsupported:
 moveq #1,d0
 bra.w FRBExit
