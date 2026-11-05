; FR2 oracle fixture (FASTRAM_PLAN.md FR2). Diagnostic only; included into
; tmp/build/fr2-oracle-* by tools/fr2_build.py, never into production.
; Called from B8Draw in place of the drawing stages (as FR0's no-draw build):
; a0 = native bank table ($66c92). Bank 0 (3 x 10,320 bytes) is the Chip
; scratch; FR2Scratch (payload, Fast) is the software side.
; Each draw runs FR2_BATCH cases from FR2Cases (tools/fr2_cases.py):
;  1. fill Fast scratch from the case's xorshift32 seed and pattern, copy it to
;     Chip; flush caches;
;  2. hardware: a D-only primer blit (clears the B shift history), the case's
;     registers (BLTBDAT after BLTCON1), BLTSIZE, wait; optional second
;     BLTSIZE with nothing else written;
;  3. software: the same through FastRenderBDAT/FastRenderBlit;
;  4. compare the whole case area; record differences per case.
; FR2OracleFinished is reached once, after the last case.
FR2_BATCH equ 32
FR2_PRIMER equ 30958
FR2_REC equ $50

FR2Oracle:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 lea (FR2State.l,pc),a4
 move.l (a0),(a4)               ; Chip scratch: bank 0 plane 0
 lea (FR2Scratch.l,pc),a1
 move.l a1,4(a4)                ; Fast scratch
 moveq #FR2_BATCH-1,d6
.loop:
 move.l 8(a4),d7                ; next case
 cmp.l #(FR2CasesEnd-FR2Cases)/FR2_REC,d7
 bhs.b .finished
 bsr.w FR2RunCase
 addq.l #1,8(a4)
 dbra d6,.loop
 bra.b FR2OracleOut
.finished:
 tst.l 12(a4)
 bne.b FR2OracleOut
 move.l #1,12(a4)
FR2OracleFinished:
 nop
FR2OracleOut:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts

FR2Flush:
 movem.l d0-d1/a0-a2,-(sp)
 lea start(pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 move.l FF1_HOST_RESLOAD(a2),a2
 jsr $20(a2)                    ; resload_FlushCache
 movem.l (sp)+,d0-d1/a0-a2
 rts

FR2WaitBlit:
 tst.w $dff002
.w:
 btst #6,$dff002
 bne.b .w
 tst.w $dff002
.w2:
 btst #6,$dff002
 bne.b .w2
 rts

; d7 = case index, a4 = FR2State.
FR2RunCase:
 lea (FR2Cases.l,pc),a5
 move.l d7,d0
 mulu.l #FR2_REC,d0
 adda.l d0,a5
 ; 1. Contents.
 lea (FR2Seed.l,pc),a0
 move.l $40(a5),(a0)            ; seed
 move.l $44(a5),d5              ; length
 addq.l #3,d5
 lsr.l #2,d5                    ; longs
 move.w $48(a5),d4              ; pattern
 move.l 4(a4),a1
 move.l d5,d3
.fill:
 bsr.w FR2Rand
 move.l d0,d1
 cmpi.w #1,d4
 bne.b .p2
 bsr.w FR2Rand
 and.l d0,d1
 bsr.w FR2Rand
 and.l d0,d1
 bra.b .put
.p2:
 cmpi.w #2,d4
 bne.b .p3
 bsr.w FR2Rand
 or.l d0,d1
 bsr.w FR2Rand
 or.l d0,d1
 bra.b .put
.p3:
 cmpi.w #3,d4
 bne.b .put
 moveq #4-1,d2
.p3l:
 bsr.w FR2Rand
 and.l d0,d1
 dbra d2,.p3l
.put:
 move.l d1,(a1)+
 subq.l #1,d3
 bne.b .fill
 move.l 4(a4),a0
 move.l (a4),a1
 move.l d5,d3
.copy:
 move.l (a0)+,(a1)+
 subq.l #1,d3
 bne.b .copy
 ; Images: hardware (Chip pointers) and software (Fast pointers).
 lea (FR2HwImage.l,pc),a0
 move.l (a4),d0
 bsr.w FR2Image
 lea (FR2SwImage.l,pc),a0
 move.l 4(a4),d0
 bsr.w FR2Image
 bsr.w FR2Flush
 ; 2. Hardware.
 lea $dff000,a6
 bsr.w FR2WaitBlit
 move.l (a4),d0
 add.l #FR2_PRIMER,d0
 move.l d0,$54(a6)
 move.w #$0100,$40(a6)
 clr.w $42(a6)
 clr.w $66(a6)
 move.w #$0041,$58(a6)
 bsr.w FR2WaitBlit
 lea (FR2HwImage.l,pc),a0
 move.w FRB_CON0(a0),$40(a6)
 move.w FRB_CON1(a0),$42(a6)
 move.w FRB_AFWM(a0),$44(a6)
 move.w FRB_ALWM(a0),$46(a6)
 move.l FRB_CPT(a0),$48(a6)
 move.l FRB_BPT(a0),$4c(a6)
 move.l FRB_APT(a0),$50(a6)
 move.l FRB_DPT(a0),$54(a6)
 move.w FRB_CMOD(a0),$60(a6)
 move.w FRB_BMOD(a0),$62(a6)
 move.w FRB_AMOD(a0),$64(a6)
 move.w FRB_DMOD(a0),$66(a6)
 move.w FRB_CDAT(a0),$70(a6)
 move.w FRB_ADAT(a0),$74(a6)
 move.w FRB_BDAT(a0),$72(a6)
 move.w FRB_SIZE(a0),$58(a6)
 bsr.w FR2WaitBlit
 move.w $3c(a5),d0
 beq.b .hw1
 move.w d0,$58(a6)
 bsr.w FR2WaitBlit
.hw1:
 bsr.w FR2Flush
 ; 3. Software.
 lea (FR2SwImage.l,pc),a0
 move.w FRB_BDAT(a0),d0
 bsr.l FastRenderBDAT
 bsr.l FastRenderBlit
 move.l d0,d2
 move.w $3c(a5),d0
 beq.b .sw1
 move.w d0,FRB_SIZE(a0)
 bsr.l FastRenderBlit
 or.l d0,d2
.sw1:
 ; 4. Compare.
 move.l (a4),a0
 move.l 4(a4),a1
 move.l $44(a5),d3
 moveq #0,d1                    ; differing bytes
 moveq #-1,d4                   ; first difference
 moveq #0,d5
.cmp:
 move.b (a0)+,d0
 cmp.b (a1)+,d0
 beq.b .same
 addq.l #1,d1
 tst.l d4
 bpl.b .same
 move.l a0,d4
 sub.l (a4),d4
 subq.l #1,d4
 move.b d0,d5
 lsl.w #8,d5
 move.b -1(a1),d5
.same:
 subq.l #1,d3
 bne.b .cmp
 lea (FR2Results.l,pc),a0
 move.l d7,d0
 mulu.l #12,d0
 adda.l d0,a0
 move.l d1,(a0)+
 move.l d4,(a0)+
 move.w d5,(a0)+
 move.w d2,(a0)+                ; software return code
 tst.l d1
 bne.b .bad
 tst.l d2
 beq.b .ok
.bad:
 addq.l #1,16(a4)
.ok:
 addq.l #1,20(a4)
 rts

; a0 = image, a5 = case, d0 = scratch base.
FR2Image:
 movem.l d1-d2/a1,-(sp)
 lea (a5),a1
 moveq #$3c/4-1,d1
.c2:
 move.l (a1)+,(a0)+
 dbra d1,.c2
 lea -$3c(a0),a0
 clr.l FRB_BOLD(a0)
 move.w $3e(a5),d2
 btst #0,d2
 beq.b .b
 add.l d0,FRB_APT(a0)
.b:
 btst #1,d2
 beq.b .c3
 add.l d0,FRB_BPT(a0)
.c3:
 btst #2,d2
 beq.b .d
 add.l d0,FRB_CPT(a0)
.d:
 btst #3,d2
 beq.b .e
 add.l d0,FRB_DPT(a0)
.e:
 movem.l (sp)+,d1-d2/a1
 rts

; xorshift32 step of FR2Seed -> d0.
FR2Rand:
 movem.l d1/a0,-(sp)
 lea (FR2Seed.l,pc),a0
 move.l (a0),d0
 move.l d0,d1
 lsl.l #8,d1
 lsl.l #5,d1
 eor.l d1,d0
 move.l d0,d1
 lsr.l #8,d1
 lsr.l #8,d1
 lsr.l #1,d1
 eor.l d1,d0
 move.l d0,d1
 lsl.l #5,d1
 eor.l d1,d0
 move.l d0,(a0)
 movem.l (sp)+,d1/a0
 rts

 cnop 0,4
FR2State:
 dc.l 0,0,0,0                   ; chip, fast, next case, finished
 dc.l 0,0                       ; failing cases, cases run
FR2Seed: dc.l 0
FR2HwImage: ds.b FRB_IMAGE
FR2SwImage: ds.b FRB_IMAGE
FR2Cases:
 incbin "FR2Cases.bin"
FR2CasesEnd:
 cnop 0,4
FR2Results: ds.b 12*((FR2CasesEnd-FR2Cases)/FR2_REC)
 cnop 0,4
FR2Scratch: ds.b 30960
