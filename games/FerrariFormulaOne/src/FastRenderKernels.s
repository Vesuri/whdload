; FR6 kernels (FASTRAM_PLAN.md FR6): register-resident loops for the blit
; shapes the FR1 census found during driving. Each kernel gives the same
; memory contents and end state as the generic paths in FastRenderBlit.s;
; any other shape returns d0 = 1 and the generic path runs.
;
; Entry (FRBFast, from FastRenderBlit): a0 = image, a6 = FastRenderBlit's
; frame with FRBL_H/FRBL_V set, d7 = BLTCON0, d6 = BLTCON1, d5 = minterm.
; Kernels may use every register except a0 and a6.
;
; Area kernel registers:
;   a1-a4 A, B, C, D pointers. Descending pointers are biased by +2 so that
;         -(an) reads the current word; FRKEnd removes the bias.
;   a5    ADAT (the A word when A is disabled)
;   d2    A history: ascending (old:new), descending (new:old)
;   d3    B history, the same way
;   d4    A shift (ascending ASH, descending 16 - ASH)
;   d5    B shift, the same way
;   d6    word counter, d7 C word, d0/d1 work

FRK_NS set 0                    ; 1 while expanding the ASH = BSH = 0 kernels

FRK_KEY macro                   ; \1 = channels (BLTCON0 bits 11-8), \2 = minterm
 dc.w (\1)<<8|(\2)
 endm

; Minterms: A in d0, B in d1, C in d7 -> d0 (d1 may be used).
FRK_MT_CA macro                 ; A ? B : C
 and.w d0,d1
 not.w d0
 and.w d7,d0
 or.w d1,d0
 endm
FRK_MT_0A macro                 ; ~A & C
 not.w d0
 and.w d7,d0
 endm
FRK_MT_FA macro                 ; A | C
 or.w d7,d0
 endm
FRK_MT_3A macro                 ; A ? ~B : C
 not.w d1
 and.w d0,d1
 not.w d0
 and.w d7,d0
 or.w d1,d0
 endm
FRK_MT_FC macro                 ; A | B
 or.w d1,d0
 endm
FRK_MT_C0 macro                 ; A & B
 and.w d1,d0
 endm
FRK_MT_30 macro                 ; A & ~B
 not.w d1
 and.w d1,d0
 endm
FRK_MT_00 macro
 moveq #0,d0
 endm
FRK_MT_FF macro
 moveq #-1,d0
 endm

; One word. \1 A on, \2 B on, \3 C on, \4 descending, \5 minterm macro,
; \6 position: 0 middle, 1 first, 2 last, 3 single (first and last).
; \7, \8, \9 = 1 when the minterm reads A, B, C.
FRK_WORD macro
 if \7
 if \1
 if \4
 move.w -(a1),d1
 else
 move.w (a1)+,d1
 endif
 if (\6)&2
 move.w d1,FRBL_ADAT(a6)
 endif
 else
 move.w a5,d1
 endif
 if (\6)&1
 and.w FRB_AFWM(a0),d1
 endif
 if (\6)&2
 and.w FRB_ALWM(a0),d1
 endif
 if FRK_NS
 move.w d1,d0
 else
 if \4
 move.w d1,d2
 swap d2
 else
 swap d2
 move.w d1,d2
 endif
 move.l d2,d0
 lsr.l d4,d0
 endif
 else
 if \1
 if \4
 move.w -(a1),d1
 else
 move.w (a1)+,d1
 endif
 if (\6)&2
 move.w d1,FRBL_ADAT(a6)
 endif
 endif
 endif
 if \2
 if \4
 move.w -(a2),d1
 else
 move.w (a2)+,d1
 endif
 if (\6)&2
 move.w d1,FRBL_BDAT(a6)
 move.w d1,FRBL_BOLD(a6)
 endif
 if FRK_NS=0
 if \4
 move.w d1,d3
 swap d3
 else
 swap d3
 move.w d1,d3
 endif
 move.l d3,d1
 lsr.l d5,d1
 endif
 if (\6)&2
 move.w d1,FRBL_BHOLD(a6)
 endif
 else
 if \8
 move.w FRBL_BHOLD(a6),d1
 endif
 endif
 if \3
 if \4
 move.w -(a3),d7
 else
 move.w (a3)+,d7
 endif
 if (\6)&2
 move.w d7,FRBL_CDAT(a6)
 endif
 else
 if \9
 move.w FRBL_CDAT(a6),d7
 endif
 endif
 \5
 if \4
 move.w d0,-(a4)
 else
 move.w d0,(a4)+
 endif
 endm

; Row modulos for the enabled channels.
FRK_MODS macro                  ; \1 A, \2 B, \3 C
 if \1
 adda.l FRBL_AMOD(a6),a1
 endif
 if \2
 adda.l FRBL_BMOD(a6),a2
 endif
 if \3
 adda.l FRBL_CMOD(a6),a3
 endif
 adda.l FRBL_DMOD(a6),a4
 endm

; An area kernel with D on. \1 A, \2 B, \3 C, \4 descending, \5 minterm,
; \6, \7, \8 = minterm reads A, B, C.
FRK_AREA macro
 bsr.w FRKSetup
 cmpi.w #1,FRBL_H(a6)
 beq.w .single\@
.row\@:
 FRK_WORD \1,\2,\3,\4,\5,1,\6,\7,\8
 move.w FRBL_MID(a6),d6
 bmi.b .last\@
.mid\@:
 FRK_WORD \1,\2,\3,\4,\5,0,\6,\7,\8
 dbra d6,.mid\@
.last\@:
 FRK_WORD \1,\2,\3,\4,\5,2,\6,\7,\8
 FRK_MODS \1,\2,\3
 subq.w #1,FRBL_V(a6)
 bne.w .row\@
 bra.w FRKEnd
.single\@:
 FRK_WORD \1,\2,\3,\4,\5,3,\6,\7,\8
 FRK_MODS \1,\2,\3
 subq.w #1,FRBL_V(a6)
 bne.w .single\@
 bra.w FRKEnd
 endm

; Area dispatch. Returns d0 = 1 when no kernel takes the blit.
FRBFast:
 move.w d6,d0
 andi.w #$18,d0
 bne.w FRKFill
 move.w d7,d0
 lsr.w #8,d0
 andi.w #$0f,d0
 lsl.w #8,d0
 move.b d5,d0                   ; (channels << 8) | minterm
 lea FRKTab(pc),a1
.find:
 move.w (a1)+,d1
 bmi.b .none
 cmp.w d1,d0
 beq.b .hit
 addq.l #8,a1
 bra.b .find
.hit:
 ifd FRK_COUNT
 move.l a1,-(sp)
 lea FRKHits(pc),a1
 addq.l #1,(a1)
 movea.l (sp)+,a1
 endif
 move.w d7,d0
 or.w d6,d0
 andi.w #$f000,d0
 bne.b .shift
 tst.w 4(a1)                    ; ASH = BSH = 0: the unshifted kernel
 beq.b .shift
 addq.l #4,a1
.shift:
 btst #1,d6
 beq.b .asc
 addq.l #2,a1
.asc:
 move.w (a1),d1
 lea FRKTab(pc),a1
 jmp (a1,d1.w)
.none:
 moveq #1,d0
 rts

; Key; ascending and descending kernels; the same for ASH = BSH = 0, or 0.
FRKTab:
 FRK_KEY %0111,$ca
 dc.w FRK_BCD_CA-FRKTab,FRK_BCD_CA_D-FRKTab,0,0
 FRK_KEY %0111,$0a
 dc.w FRK_BCD_0A-FRKTab,FRK_BCD_0A_D-FRKTab,0,0
 FRK_KEY %0111,$fa
 dc.w FRK_BCD_FA-FRKTab,FRK_BCD_FA_D-FRKTab,0,0
 FRK_KEY %0111,$3a
 dc.w FRK_BCD_3A-FRKTab,FRK_BCD_3A_D-FRKTab,0,0
 FRK_KEY %1111,$ca
 dc.w FRK_ABCD_CA-FRKTab,FRK_ABCD_CA_D-FRKTab,FRK_ABCD_CA_N-FRKTab,FRK_ABCD_CA_ND-FRKTab
 FRK_KEY %1011,$0a
 dc.w FRK_ACD_0A-FRKTab,FRK_ACD_0A_D-FRKTab,FRK_ACD_0A_N-FRKTab,FRK_ACD_0A_ND-FRKTab
 FRK_KEY %1101,$fc
 dc.w FRK_ABD_FC-FRKTab,FRK_ABD_FC_D-FRKTab,FRK_ABD_FC_N-FRKTab,FRK_ABD_FC_ND-FRKTab
 FRK_KEY %1101,$c0
 dc.w FRK_ABD_C0-FRKTab,FRK_ABD_C0_D-FRKTab,FRK_ABD_C0_N-FRKTab,FRK_ABD_C0_ND-FRKTab
 FRK_KEY %1101,$30
 dc.w FRK_ABD_30-FRKTab,FRK_ABD_30_D-FRKTab,FRK_ABD_30_N-FRKTab,FRK_ABD_30_ND-FRKTab
 FRK_KEY %0001,$00
 dc.w FRK_D_00-FRKTab,FRK_D_00_D-FRKTab,0,0
 FRK_KEY %0001,$ff
 dc.w FRK_D_FF-FRKTab,FRK_D_FF_D-FRKTab,0,0
 dc.w -1

FRK_BCD_CA: FRK_AREA 0,1,1,0,FRK_MT_CA,1,1,1
FRK_BCD_CA_D: FRK_AREA 0,1,1,1,FRK_MT_CA,1,1,1
FRK_BCD_0A: FRK_AREA 0,1,1,0,FRK_MT_0A,1,0,1
FRK_BCD_0A_D: FRK_AREA 0,1,1,1,FRK_MT_0A,1,0,1
FRK_BCD_FA: FRK_AREA 0,1,1,0,FRK_MT_FA,1,0,1
FRK_BCD_FA_D: FRK_AREA 0,1,1,1,FRK_MT_FA,1,0,1
FRK_BCD_3A: FRK_AREA 0,1,1,0,FRK_MT_3A,1,1,1
FRK_BCD_3A_D: FRK_AREA 0,1,1,1,FRK_MT_3A,1,1,1
FRK_ABCD_CA: FRK_AREA 1,1,1,0,FRK_MT_CA,1,1,1
FRK_ABCD_CA_D: FRK_AREA 1,1,1,1,FRK_MT_CA,1,1,1
FRK_ACD_0A: FRK_AREA 1,0,1,0,FRK_MT_0A,1,0,1
FRK_ACD_0A_D: FRK_AREA 1,0,1,1,FRK_MT_0A,1,0,1
FRK_ABD_FC: FRK_AREA 1,1,0,0,FRK_MT_FC,1,1,0
FRK_ABD_FC_D: FRK_AREA 1,1,0,1,FRK_MT_FC,1,1,0
FRK_ABD_C0: FRK_AREA 1,1,0,0,FRK_MT_C0,1,1,0
FRK_ABD_C0_D: FRK_AREA 1,1,0,1,FRK_MT_C0,1,1,0
FRK_ABD_30: FRK_AREA 1,1,0,0,FRK_MT_30,1,1,0
FRK_ABD_30_D: FRK_AREA 1,1,0,1,FRK_MT_30,1,1,0
FRK_D_00: FRK_AREA 0,0,0,0,FRK_MT_00,0,0,0
FRK_D_00_D: FRK_AREA 0,0,0,1,FRK_MT_00,0,0,0
FRK_D_FF: FRK_AREA 0,0,0,0,FRK_MT_FF,0,0,0
FRK_D_FF_D: FRK_AREA 0,0,0,1,FRK_MT_FF,0,0,0
FRK_NS set 1
FRK_ABCD_CA_N: FRK_AREA 1,1,1,0,FRK_MT_CA,1,1,1
FRK_ABCD_CA_ND: FRK_AREA 1,1,1,1,FRK_MT_CA,1,1,1
FRK_ACD_0A_N: FRK_AREA 1,0,1,0,FRK_MT_0A,1,0,1
FRK_ACD_0A_ND: FRK_AREA 1,0,1,1,FRK_MT_0A,1,0,1
FRK_ABD_FC_N: FRK_AREA 1,1,0,0,FRK_MT_FC,1,1,0
FRK_ABD_FC_ND: FRK_AREA 1,1,0,1,FRK_MT_FC,1,1,0
FRK_ABD_C0_N: FRK_AREA 1,1,0,0,FRK_MT_C0,1,1,0
FRK_ABD_C0_ND: FRK_AREA 1,1,0,1,FRK_MT_C0,1,1,0
FRK_ABD_30_N: FRK_AREA 1,1,0,0,FRK_MT_30,1,1,0
FRK_ABD_30_ND: FRK_AREA 1,1,0,1,FRK_MT_30,1,1,0
FRK_NS set 0

; Line kernel: the FR1 form (width 2, B off, A and C on, minterm $4A), as
; FRBLine draws it. One axis steps every pixel; the other steps when SIGN
; is clear. Registers: d2 error term (APT), d3 ASH, d4 BSH, d5 SIGN (byte),
; ONEDOT (bit 8) and the SING write flag (bit 9), d6 X direction (+-1),
; d7 C, a1 AMOD, a2 BMOD, a3 C pointer, a4 D pointer, a5 Y step (+-CMOD).
; Locals: FRBL_ADAT = ADAT & AFWM, FRBL_STEP = the word step of X (+-2).
; Returns d0 = 1 for any other form.
FRKLine:
 cmpi.w #2,FRBL_H(a6)
 bne.w .other
 move.w d7,d0
 andi.w #$0fff,d0
 cmpi.w #$0b4a,d0               ; A, C, D on; B off; minterm $4A
 bne.w .other
 ifd FRK_COUNT
 lea FRKHits(pc),a1
 addq.l #1,(a1)
 endif
 move.w FRB_AMOD(a0),d0
 andi.w #$fffe,d0
 ext.l d0
 movea.l d0,a1
 move.w FRB_BMOD(a0),d0
 andi.w #$fffe,d0
 ext.l d0
 movea.l d0,a2
 move.w FRB_CMOD(a0),d0
 andi.w #$fffe,d0
 ext.l d0
 movea.l d0,a5                  ; +CMOD
 move.w d7,d3
 lsr.w #8,d3
 lsr.w #4,d3                    ; ASH
 move.w d6,d4
 lsr.w #8,d4
 lsr.w #4,d4                    ; BSH
 move.l FRB_APT(a0),d2
 move.l FRB_CPT(a0),d0
 bclr #0,d0
 movea.l d0,a3
 move.l FRB_DPT(a0),d0
 bclr #0,d0
 movea.l d0,a4
 move.w FRB_ADAT(a0),d0
 and.w FRB_AFWM(a0),d0
 move.w d0,FRBL_ADAT(a6)
 ; Directions: Y-major (SUD clear) steps Y by AUL and X by SUL; X-major
 ; (SUD set) steps X by AUL and Y by SUL. A set bit steps down.
 moveq #2,d0                    ; AUL
 moveq #3,d1                    ; SUL
 btst #4,d6
 beq.b .ymaj
 exg d0,d1                      ; X-major: X by AUL, Y by SUL
.ymaj:
 moveq #1,d7
 btst d1,d6                     ; X direction
 beq.b .xinc
 moveq #-1,d7
.xinc:
 btst d0,d6                     ; Y direction
 beq.b .yinc
 move.l a5,d0
 neg.l d0
 movea.l d0,a5
.yinc:
 move.w d7,d0
 ext.l d0
 add.l d0,d0
 move.l d0,FRBL_STEP(a6)
 moveq #0,d5
 move.w d6,d1
 move.w d7,d6                   ; X direction
 btst #4,d1
 bne.b .xmajor
 btst #1,d1
 bne.w FRKLineYS
 bra.w FRKLineY
.xmajor:
 btst #1,d1
 bne.w FRKLineXS
 bra.w FRKLineX
.other:
 moveq #1,d0
 rts

; One line. \1 = 1 X-major, \2 = 1 SING.
FRK_LINE macro
.pix\@:
 if \2
 bclr #9,d5
 btst #8,d5
 bne.b .one\@
 bset #9,d5                     ; first dot of this row: write it
.one\@:
 bset #8,d5
 endif
 tst.w d2
 smi d5                         ; SIGN
 bmi.b .neg\@
 add.l a1,d2
 bra.b .err\@
.neg\@:
 add.l a2,d2
.err\@:
 move.w (a3),d7                 ; C
 move.w FRBL_ADAT(a6),d0
 lsr.w d3,d0                    ; A
 move.w FRB_BDAT(a0),d1
 btst d4,d1                     ; B: texture bit BSH
 sne d1
 ext.w d1
 and.w d0,d1                    ; $4A = ((A & B) | C) & ~(A & C)
 or.w d7,d1
 and.w d7,d0
 not.w d0
 and.w d1,d0
 if \1
 add.w d6,d3                    ; X every pixel
 btst #4,d3
 beq.b .x\@
 adda.l FRBL_STEP(a6),a3
 andi.w #15,d3
.x\@:
 tst.b d5
 bne.b .y\@
 adda.l a5,a3                   ; Y when SIGN is clear
 if \2
 bclr #8,d5
 endif
.y\@:
 else
 tst.b d5
 bne.b .x\@
 add.w d6,d3                    ; X when SIGN is clear
 btst #4,d3
 beq.b .x\@
 adda.l FRBL_STEP(a6),a3
 andi.w #15,d3
.x\@:
 adda.l a5,a3                   ; Y every pixel
 if \2
 bclr #8,d5
 endif
 endif
 subq.w #1,d4
 andi.w #15,d4
 if \2
 btst #9,d5
 beq.b .w\@
 endif
 move.w d0,(a4)
.w\@:
 movea.l a3,a4
 subq.w #1,FRBL_V(a6)
 bne.w .pix\@
 bra.w FRKLineEnd
 endm

FRKLineY: FRK_LINE 0,0
FRKLineYS: FRK_LINE 0,1
FRKLineX: FRK_LINE 1,0

; X-major with SING (FR12): only the first dot of each row is written, so the
; other pixels skip the C minterm. C is still read at each pixel for the end
; state (CDAT).
FRK_LINE_STEP macro             ; error term, C, X and Y steps, B shift
 tst.w d2
 smi d5                         ; SIGN
 bmi.b .neg\@
 add.l a1,d2
 bra.b .err\@
.neg\@:
 add.l a2,d2
.err\@:
 move.w (a3),d7                 ; C
 endm
FRK_LINE_MOVE macro
 add.w d6,d3                    ; X every pixel
 btst #4,d3
 beq.b .x\@
 adda.l FRBL_STEP(a6),a3
 andi.w #15,d3
.x\@:
 tst.b d5
 bne.b .y\@
 adda.l a5,a3                   ; Y when SIGN is clear
 bclr #8,d5
.y\@:
 subq.w #1,d4
 andi.w #15,d4
 endm
FRKLineXS:
.pix:
 btst #8,d5
 bne.w .skip
 bset #8,d5                     ; the first dot of this row
 FRK_LINE_STEP
 move.w FRBL_ADAT(a6),d0
 lsr.w d3,d0                    ; A
 move.w FRB_BDAT(a0),d1
 btst d4,d1                     ; B: texture bit BSH
 sne d1
 ext.w d1
 and.w d0,d1                    ; $4A = ((A & B) | C) & ~(A & C)
 or.w d7,d1
 and.w d7,d0
 not.w d0
 and.w d1,d0
 FRK_LINE_MOVE
 move.w d0,(a4)
 movea.l a3,a4
 subq.w #1,FRBL_V(a6)
 bne.w .pix
 bra.w FRKLineEnd
.skip:
 FRK_LINE_STEP
 FRK_LINE_MOVE
 movea.l a3,a4
 subq.w #1,FRBL_V(a6)
 bne.w .pix
 bra.w FRKLineEnd

; End state, as FRBLine leaves it.
FRKLineEnd:
 move.w FRB_CON0(a0),d0
 andi.w #$0fff,d0
 move.w d3,d1
 ror.w #4,d1
 or.w d1,d0
 move.w d0,FRB_CON0(a0)
 move.w FRB_CON1(a0),d0
 andi.w #$0fbf,d0
 tst.b d5
 beq.b .sign
 bset #6,d0
.sign:
 move.w d4,d1
 ror.w #4,d1
 or.w d1,d0
 move.w d0,FRB_CON1(a0)
 move.l d2,FRB_APT(a0)
 move.l a3,FRB_CPT(a0)
 move.l a4,FRB_DPT(a0)
 move.w d7,FRB_CDAT(a0)
 moveq #0,d0
 move.w FRB_BDAT(a0),d1
 btst d4,d1
 beq.b .hold
 moveq #-1,d0
.hold:
 move.w d0,FRB_BHOLD(a0)
 clr.w FRB_BOLD(a0)
 moveq #0,d0
 rts

; Common setup: modulos, shifts, pointers (descending ones biased), the
; channel data locals, and the middle-word count. d6 = BLTCON1 on entry.
FRKSetup:
 FRBMOD FRB_AMOD,FRBL_AMOD
 FRBMOD FRB_BMOD,FRBL_BMOD
 FRBMOD FRB_CMOD,FRBL_CMOD
 FRBMOD FRB_DMOD,FRBL_DMOD
 move.w FRB_CON0(a0),d4
 lsr.w #8,d4
 lsr.w #4,d4                    ; ASH
 move.w d6,d5
 lsr.w #8,d5
 lsr.w #4,d5                    ; BSH
 movea.l FRB_APT(a0),a1
 movea.l FRB_BPT(a0),a2
 movea.l FRB_CPT(a0),a3
 movea.l FRB_DPT(a0),a4
 move.l a1,d0
 bclr #0,d0
 movea.l d0,a1
 move.l a2,d0
 bclr #0,d0
 movea.l d0,a2
 move.l a3,d0
 bclr #0,d0
 movea.l d0,a3
 move.l a4,d0
 bclr #0,d0
 movea.l d0,a4
 btst #1,d6
 beq.b .asc
 neg.w d4
 add.w #16,d4
 neg.w d5
 add.w #16,d5
 addq.l #2,a1
 addq.l #2,a2
 addq.l #2,a3
 addq.l #2,a4
.asc:
 move.w FRB_ADAT(a0),FRBL_ADAT(a6)
 move.w FRB_BDAT(a0),FRBL_BDAT(a6)
 move.w FRB_CDAT(a0),FRBL_CDAT(a6)
 move.w FRB_BHOLD(a0),FRBL_BHOLD(a6)
 clr.w FRBL_BOLD(a6)
 movea.w FRB_ADAT(a0),a5
 move.w FRBL_H(a6),d0
 subq.w #3,d0
 move.w d0,FRBL_MID(a6)
 moveq #0,d2
 moveq #0,d3
 rts

; Common end state, as FRBArea leaves it.
FRKEnd:
 move.w FRB_CON0(a0),d7
 btst #1,FRB_CON1+1(a0)
 beq.b .asc
 subq.l #2,a1
 subq.l #2,a2
 subq.l #2,a3
 subq.l #2,a4
.asc:
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
 moveq #0,d0
 rts

; d7 = word, d3 = carry offset (0/256), a5 = table -> d0 filled, d3 updated.
; Table entry = carry out * 256 + filled byte.
FRK_FILLWORD macro
 moveq #0,d1
 move.b d7,d1
 add.w d3,d1
 move.w (a5,d1.w*2),d0          ; low byte
 move.w d0,d3
 clr.b d3
 move.w d7,d1
 lsr.w #8,d1
 add.w d3,d1
 move.w (a5,d1.w*2),d1          ; high byte
 move.w d1,d3
 clr.b d3
 lsl.w #8,d1
 move.b d0,d1
 move.w d1,d0
 endm

; Fill kernels: CD with minterm $AA (D = C, then filled), the road fill.
; Each byte is filled through FRKFillTab, right byte first.
FRKFill:
 move.w d7,d0
 andi.w #$0fff,d0
 cmpi.w #$03aa,d0
 beq.b .cd
 moveq #1,d0
 rts
.cd:
 ifd FRK_COUNT
 move.l a1,-(sp)
 lea FRKHits(pc),a1
 addq.l #1,(a1)
 movea.l (sp)+,a1
 endif
 tst.b FRKFillReady(pc)
 bne.b .ready
 bsr.w FRKFillInit
.ready:
 bsr.w FRKSetup
 lea FRKFillTab(pc),a5
 move.w d6,d0
 andi.w #$18,d0
 cmpi.w #$08,d0                 ; IFE alone; IFE with EFE acts as EFE
 bne.b .exclusive
 lea 1024(a5),a5                ; inclusive table
.exclusive:
 moveq #0,d5
 btst #2,d6                     ; FCI
 beq.b .fci
 move.w #256,d5
.fci:
 btst #1,d6
 bne.w FRKFillD
.row:
 move.w d5,d3                   ; carry offset, 0 or 256
 move.w FRBL_H(a6),d6
 subq.w #1,d6
.word:
 move.w (a3)+,d7
 FRK_FILLWORD
 move.w d0,(a4)+
 dbra d6,.word
 adda.l FRBL_CMOD(a6),a3
 adda.l FRBL_DMOD(a6),a4
 subq.w #1,FRBL_V(a6)
 bne.b .row
 move.w d7,FRBL_CDAT(a6)
 bra.w FRKEnd

FRKFillD:
.row:
 move.w d5,d3
 move.w FRBL_H(a6),d6
 subq.w #1,d6
.word:
 move.w -(a3),d7
 FRK_FILLWORD
 move.w d0,-(a4)
 dbra d6,.word
 adda.l FRBL_CMOD(a6),a3
 adda.l FRBL_DMOD(a6),a4
 subq.w #1,FRBL_V(a6)
 bne.b .row
 move.w d7,FRBL_CDAT(a6)
 bra.w FRKEnd

; Build the exclusive (first 512 words) and inclusive fill tables with the
; bit rule of FRBFill.
FRKFillInit:
 movem.l d0-d7/a1,-(sp)
 lea FRKFillTab(pc),a1
 moveq #0,d7                    ; 0 exclusive, 1 inclusive
.mode:
 moveq #0,d6                    ; carry in
.carry:
 moveq #0,d5                    ; byte
.byte:
 move.w d5,d0                   ; output
 move.w d6,d2                   ; carry
 moveq #0,d3                    ; bit
.bit:
 tst.w d2
 beq.b .nocarry
 tst.w d7
 beq.b .excl
 bset d3,d0
 bra.b .nocarry
.excl:
 bchg d3,d0
.nocarry:
 btst d3,d5
 beq.b .same
 eori.w #1,d2
.same:
 addq.w #1,d3
 cmpi.w #8,d3
 blo.b .bit
 andi.w #$ff,d0
 lsl.w #8,d2
 or.w d2,d0
 move.w d0,(a1)+
 addq.w #1,d5
 cmpi.w #256,d5
 blo.b .byte
 addq.w #1,d6
 cmpi.w #2,d6
 blo.b .carry
 addq.w #1,d7
 cmpi.w #2,d7
 blo.b .mode
 lea FRKFillReady(pc),a1
 st (a1)
 movem.l (sp)+,d0-d7/a1
 rts

 even
FRKFillTab: ds.w 1024
FRKFillReady: dc.b 0
 even
 ifd FRK_COUNT
FRKHits: dc.l 0
 endif
