; H2 fine-path exact elision of the zero and Q sprite colour intermediates.
; Native $32e12 still waits before every plane's register setup. Mixed Q&P
; and Q&~P planes keep the original colour blit and following wait.
; The cookie-cut is the only consumer of colour scratch contents ($1c1b8).
; Q uses the same interior words/row stride directly. The zero A last-word
; mask hides the extra B edge word and its carry into the following row.
; Zero disables B and uses D = ~A&C. First/last masks, shifts, clipping and
; native final BLTSIZE remain.
; No extra DMA storage. Existing hunk ledger owns installation/restoration.
FF1RenderInstallColourElide:
 lea FF1RenderColourSignature(pc),a0
 lea $32d48,a1
 move.w #227,d0
.check:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.l FF1ProductionFault
 dbra d0,.check
 ; Both equal-layout arms validate the complete native routine first.
 tst.w FF1RenderColourControl(pc)
 beq.w .done
 lea FF1RenderColourPlane(pc),a0
 move.w #$4ef9,$32e34
 move.l a0,$32e36
.done:
 rts
FF1RenderColourPlane:
 tst.w d0
 beq.b .zero
 cmpi.w #6,d0
 beq.b .q
 ; Displaced native instruction; D0 still indexes the native minterm table.
 move.w (a2,d0.w),$40(a1)
 jmp $32e3a
.zero:
 moveq #-1,d0
 move.w d5,d0
 addi.w #$0b0a,d0
 move.w d0,$40(a1)
 move.l $1c1b8,a5
 bra.b .cookie
.q:
 moveq #-1,d0
 move.w d5,d0
 addi.w #$0fca,d0
 move.w d0,$40(a1)
 move.l $10(a0),a5
.cookie:
 ; B is ready before A5 becomes the mask/screen pointer. Preserve the native
 ; D0 high word (-1 from the colour setup), not just its low-word outputs.
 adda.w d4,a5
 adda.w d4,a5
 move.l a5,$4c(a1)
 move.w #$ffff,$44(a1)
 tst.w d4
 beq.b .first_mask
 clr.w $44(a1)
.first_mask:
 clr.w $46(a1)
 move.w d5,$42(a1)
 move.w d3,d0
 add.w d4,d0
 subq.l #1,d0
 lsl.w #1,d0
 move.w d0,$64(a1)
 move.w d0,$62(a1)
 sub.w $0(a0),d0
 sub.w $0(a0),d0
 addi.w #$30,d0
 move.w d0,$60(a1)
 move.w d0,$66(a1)
 move.l $1c1bc,a5
 adda.w d4,a5
 adda.w d4,a5
 move.l a5,$50(a1)
 move.w a3,d0
 lsl.w #2,d0
 move.l $226ae,a5
 move.l (a5,d0.w),a5
 move.w d4,d0
 add.w d7,d0
 add.w d6,d0
 lsl.w #1,d0
 adda.w d0,a5
 move.l a5,$48(a1)
 move.l a5,$54(a1)
 jmp $32ef6
; Immutable preset; excluded from zero-initialized lifecycle state.
FF1RenderColourControl: dc.w 1
FF1RenderColourSignature:
 dc.b $01,$00,$0d,$c0,$0d,$30,$09,$f0,$20,$6f,$00,$04,$3c,$2f,$00,$0a
 dc.b $3e,$2f,$00,$0e,$34,$28,$00,$00,$9c,$68,$00,$04,$9e,$68,$00,$06
 dc.b $0c,$46,$01,$80,$6c,$00,$01,$a0,$30,$02,$e9,$40,$d0,$46,$6f,$00
 dc.b $01,$96,$0c,$40,$01,$80,$6d,$00,$00,$10,$36,$06,$e8,$43,$04,$43
 dc.b $00,$19,$d6,$42,$60,$00,$00,$04,$42,$43,$4a,$46,$6a,$00,$00,$0e
 dc.b $38,$06,$44,$44,$e8,$44,$52,$84,$60,$00,$00,$04,$42,$44,$3a,$06
 dc.b $02,$45,$00,$0f,$e8,$5d,$4e,$b9,$00,$02,$a1,$30,$22,$7c,$00,$df
 dc.b $f0,$00,$33,$7c,$0d,$fc,$00,$40,$70,$ff,$33,$40,$00,$46,$33,$40
 dc.b $00,$44,$42,$69,$00,$42,$42,$69,$00,$64,$42,$69,$00,$62,$42,$69
 dc.b $00,$66,$23,$68,$00,$0c,$00,$50,$23,$68,$00,$10,$00,$4c,$23,$79
 dc.b $00,$01,$c1,$bc,$00,$54,$30,$28,$00,$02,$ed,$40,$d0,$42,$33,$40
 dc.b $00,$58,$38,$40,$30,$07,$e3,$4f,$de,$40,$e7,$4f,$97,$cb,$24,$7c
 dc.b $00,$03,$2d,$48,$e8,$46,$e3,$ef,$00,$12,$4e,$b9,$00,$02,$a1,$30
 dc.b $30,$2f,$00,$12,$32,$2f,$00,$16,$e2,$ef,$00,$12,$e2,$ef,$00,$16
 dc.b $02,$40,$00,$02,$02,$41,$00,$01,$80,$41,$e3,$40,$33,$72,$00,$00
 dc.b $00,$40,$70,$ff,$33,$40,$00,$44,$33,$40,$00,$46,$42,$69,$00,$42
 dc.b $42,$69,$00,$64,$42,$69,$00,$62,$42,$69,$00,$66,$23,$68,$00,$0c
 dc.b $00,$4c,$23,$68,$00,$10,$00,$50,$23,$79,$00,$01,$c1,$b8,$00,$54
 dc.b $33,$4c,$00,$58,$4e,$b9,$00,$02,$a1,$30,$4a,$44,$67,$00,$00,$0a
 dc.b $42,$69,$00,$44,$60,$00,$00,$06,$33,$40,$00,$44,$42,$69,$00,$46
 dc.b $30,$05,$06,$40,$0f,$ca,$33,$40,$00,$40,$33,$45,$00,$42,$30,$03
 dc.b $d0,$44,$53,$80,$e3,$48,$33,$40,$00,$64,$33,$40,$00,$62,$90,$68
 dc.b $00,$00,$90,$68,$00,$00,$06,$40,$00,$30,$33,$40,$00,$60,$33,$40
 dc.b $00,$66,$2a,$79,$00,$01,$c1,$bc,$da,$c4,$da,$c4,$23,$4d,$00,$50
 dc.b $2a,$79,$00,$01,$c1,$b8,$da,$c4,$da,$c4,$23,$4d,$00,$4c,$30,$0b
 dc.b $e5,$48,$2a,$79,$00,$02,$26,$ae,$2a,$75,$00,$00,$30,$04,$d0,$47
 dc.b $d0,$46,$e3,$48,$da,$c0,$23,$4d,$00,$48,$23,$4d,$00,$54,$30,$0c
 dc.b $52,$80,$90,$43,$90,$44,$33,$40,$00,$58,$d6,$fc,$00,$01,$b6,$fc
 dc.b $00,$03,$66,$00,$ff,$06,$4e,$75
