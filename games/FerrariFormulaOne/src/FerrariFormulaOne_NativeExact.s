; SPS 0481 native arithmetic candidate, 68020 only, default off.
; Host installs after conversion hooks and flushes instruction caches afterward.
; Every site has a straight-line proof below: all XNZVC bits are overwritten
; before a branch/call/return or any flag consumer. No CCR equivalence claimed.
; Positive immediate divisors cannot divide by zero or overflow signed 32-bit.
; Variable divisors use FF1NativeDivide, preserving native zero and wrap results.
; Signatures include the complete flag-killing sequence and constant load.
 ifnd FF1_NATIVE_EXACT
FF1_NATIVE_EXACT equ 0
 endc
 ifgt FF1_NATIVE_EXACT
FF1InstallNativeExact:
 movem.l d0-d2/a0-a2,-(sp)
 ifgt FF1_NATIVE_EXACT-2
 lea FF1TrackSignature(pc),a0
 lea $6977a,a1
 move.w #136,d1
.track_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.track_check
 lea $67514,a1
 moveq #10,d1
.caller_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.caller_check
 endc
 ifgt FF1_NATIVE_EXACT-3
 lea FF1TrigSignature(pc),a0
 lea $24fe0,a1
 moveq #31,d1
.trig_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.trig_check
 endc
 ifgt FF1_NATIVE_EXACT-4
 lea FF1MultiplySignature(pc),a0
 lea $29500,a1
 moveq #32,d1
.multiply_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.multiply_check
 endc
 lea FF1NativeSites(pc),a0
.check:
 move.l (a0)+,d0
 beq.b .checked
 move.l d0,a1
 move.w (a0)+,d1
 addq.l #2,a0
 subq.w #1,d1
.bytes:
 move.b (a0)+,d2
 cmp.b (a1)+,d2
 bne.w .bad
 dbra d1,.bytes
 bra.b .check
.checked:
 lea FF1NativeSites(pc),a0
.patch:
 move.l (a0)+,d0
 beq.w .complete
 move.l d0,a1
 move.w (a0)+,d1
 move.w (a0)+,d2
 adda.w d1,a0
 ; D2 = call offset from signature start, bit15 selects guarded call.
 btst #13,d2              ; guard-only proof fragment
 bne.b .patch
 tst.w d2
 bmi.b .guarded
 btst #14,d2
 bne.b .multiply
 adda.w d2,a1
 move.l #$4c410801,(a1)       ; divsl.l d1,d1:d0 (32-bit dividend)
 move.w #$4e71,4(a1)
 bra.b .patch
.guarded:
 andi.w #$7fff,d2
 adda.w d2,a1
 lea FF1NativeDivide(pc),a2
 move.l a2,2(a1)            ; keep JSR opcode
 bra.b .patch
.multiply:
 andi.w #$3fff,d2
 adda.w d2,a1
 move.l #$4c010800,(a1)       ; muls.l d1,d0 (low signed product)
 move.w #$4e71,4(a1)
 bra.b .patch
.complete:
 ifgt FF1_NATIVE_EXACT-4
 lea FF1NativeMultiply(pc),a0
 move.w #$4ef9,$29500
 move.l a0,$29502
 endc
 ifgt FF1_NATIVE_EXACT-3
 lea FF1TrigReplacement(pc),a0
 lea $24fe0,a1
 moveq #15,d1
.trig_copy:
 move.l (a0)+,(a1)+
 dbra d1,.trig_copy
 endc
 ifgt FF1_NATIVE_EXACT-2
 lea FF1NativeLookahead(pc),a0
 move.w #$4ef9,$6977a
 move.l a0,$6977c
 move.w #$4e71,$69780
 endc
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #39,(a0)
.done:
 movem.l (sp)+,d0-d2/a0-a2
 rts

; D0 dividend -> quotient, D1 divisor -> remainder. Everything else preserved.
; Zero divisor returns 0,0; INT_MIN/-1 returns INT_MIN,0, like native.
FF1NativeDivide:
 tst.l d1
 beq.b .zero_divisor
 divsl.l d1,d1:d0
 bvs.b .overflow
 rts
.overflow:
 move.l #$80000000,d0
.zero:
 clr.l d1
 rts
.zero_divisor:
 clr.l d0
 clr.l d1
 rts

 ifgt FF1_NATIVE_EXACT-2
; Only native caller $67514: drops argument, consumes D0, overwrites A0 and
; XNZVC by $67528, overwrites D1 at $6755e on both intervening branch paths.
; The native argument-slot mutation and D1/A0 scratch outputs are dead there.
FF1NativeLookahead:
 tst.w $1ed8a
 bne.b .native
 moveq #0,d1
 move.w $2268c,d1
 cmpi.w #12,d1
 blo.b .native
 ; At count 32767 the last segment +2 wraps the native signed word.
 ; Keep native behavior for that whole boundary domain.
 cmpi.w #32766,d1
 bhi.b .native
 move.w 6(sp),d0
 ext.l d0
 bmi.b .native
 cmp.l d1,d0
 bhs.b .native
 lea $1dc24,a0
 bra.w FF1TrackLookaheadNormal
.native:
 link a6,#-8
 clr.l -6(a6)
 jmp $69782
 include "FerrariFormulaOne_Track.s"
FF1TrackSignature:
 dc.w $4e56,$fff8,$42ae,$fffa,$4a79,$0001,$ed8a,$665c,$3d7c,$000a,$fffe,$546e,$000a,$302e,$fffe,$536e,$fffe,$4a40,$6730,$3039,$0002,$268c,$322e,$000a,$b240,$6d04,$916e,$000a,$302e,$000a,$526e,$000a,$48c0,$e380,$2040,$d1fc,$0001,$dc24,$3010,$48c0,$d1ae,$fffa,$60c4,$4aae,$fffa,$6a08,$202e,$fffa,$4480,$6004,$202e,$fffa,$4e5e,$4e75,$3d7c,$0008,$fffe,$3039,$0003,$2fbc,$48c0,$e380,$2040,$d1fc,$0002,$275a,$3010,$0c40,$015e,$6f04,$586e,$000a,$302e,$fffe,$536e,$fffe,$4a40,$676c,$3039,$0002,$268c,$322e,$000a,$b240,$6d04,$916e,$000a,$302e,$000a,$3f40,$0000,$5240,$322f,$0000,$48c1,$e381,$2041,$d1fc,$0001,$dc24,$3210,$3d40,$000a,$4a41,$6a18,$526e,$000a,$48c0,$e380,$2040,$d1fc,$0001,$dc24,$3010,$48c0,$4480,$6018,$302e,$000a,$526e,$000a,$48c0,$e380,$2040,$d1fc,$0001,$dc24,$3010,$48c0,$d1ae,$fffa,$6088,$202e,$fffa,$e380,$4e5e,$4e75
 dc.w $6100,$2264,$588f,$23c0,$0003,$2f8a,$3039,$0003,$2fbc,$48c0,$e380
 endc

 ifgt FF1_NATIVE_EXACT-3
; Direct indexed Q15 table lookup. Unlike the initially proposed CCR-dead-only
; version, keep the two original logical shifts: D0 (including upper bits),
; A0 and all five CCR bits exactly match native for every input. Thus existing
; callers and return flags stay valid, including conversion-hook opponents.
; Only the low argument words matter. Masking the angle word is sufficient
; for the signed word index (0..1023); MULS.W replaces the whole D0 afterward.
FF1TrigReplacement:
FF1NativeSine:
 move.w 6(sp),d0
 andi.w #1023,d0
 lea ($2180c,d0.w*2),a0
 move.w 10(sp),d0
 muls.w (a0),d0
 lsr.l #8,d0
 lsr.l #7,d0
 rts
 dcb.b 32-(*-FF1NativeSine),0
FF1NativeCosine:
 move.w 6(sp),d0
 andi.w #1023,d0
 lea ($21a0c,d0.w*2),a0
 move.w 10(sp),d0
 muls.w (a0),d0
 lsr.l #8,d0
 lsr.l #7,d0
 rts
 dcb.b 32-(*-FF1NativeCosine),0
FF1TrigSignature:
 dc.w $302f,$0006,$0280,$0000,$03ff,$e380,$0680,$0002,$180c,$2040,$302f,$000a,$c1d0,$e088,$ee88,$4e75,$302f,$0006,$0280,$0000,$03ff,$e380,$0680,$0002,$1a0c,$2040,$302f,$000a,$c1d0,$e088,$ee88,$4e75
 endc

 ifgt FF1_NATIVE_EXACT-4
; Exact native multiply ABI, including its unusual CCR contract. This catches
; remaining callers where flags cannot simply be discarded. D1-D3 preserved.
; For same-sign nonzero operands, native X is the carry of its FINAL partial
; product add, not full-product overflow. Reconstruct that carry from the low
; product and H=((abs(A).lo * abs(B).hi) & $ffff)<<16: carry iff result < H.
; Native N/Z then describe A xor B, not the product. Opposite signs use native
; NEG flags; double NEG preserves the hardware product and yields those flags.
; Zero-input cases retain the native incoming-X / normalization behavior.
FF1NativeMultiply:
 movem.l d1-d3,-(sp)
 move.l d0,d2
 beq.b .done
 move.l d0,d3
 eor.l d1,d3
 tst.l d1
 beq.b .zero_b
 muls.l d1,d0
 tst.l d3
 bmi.b .negative
 tst.l d2
 bpl.b .positive
 neg.l d2
 neg.l d1
.positive:
 swap d1
 mulu.w d2,d1
 swap d1
 clr.w d1
 move.l d0,d2
 sub.l d1,d2
 tst.l d3
 bra.b .done
.negative:
 neg.l d0
 neg.l d0
 bra.b .done
.zero_b:
 tst.l d2
 bpl.b .zero
 neg.l d2
.zero:
 clr.l d0
.done:
 movem.l (sp)+,d1-d3
 rts
FF1MultiplySignature:
 dc.w $48e7,$7800,$2800,$b384,$4a80,$6730,$6a02,$4480,$2400,$4a81,$6604,$4280,$6022,$6a02,$4481,$2600,$c6c1,$4842,$c4c1,$4842,$4242,$d682,$4841,$c0c1,$4840,$4240,$d083,$4a84,$6a02,$4480,$4cdf,$001e,$4e75
 endc

FF1NativeSites:
; $22fe0: $22fe6 move.w $2360c.l, d1; $22fec ext.l d1; $22fee addq.l #$3, d1
 dc.l $22fde
 dc.w 18,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$32,$39,$00,$02,$36,$0c,$48,$c1,$56,$81
; $23014: $2301a move.w $2360c.l, d0; $23020 ext.l d0; $23022 addq.l #$4, d0
 dc.l $23012
 dc.w 18,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$30,$39,$00,$02,$36,$0c,$48,$c0,$58,$80
; $230dc: $230e2 move.w $2360c.l, d0; $230e8 ext.l d0; $230ea addq.l #$1, d0
 dc.l $230da
 dc.w 18,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$30,$39,$00,$02,$36,$0c,$48,$c0,$52,$80
; $23172: $23178 move.w $2360c.l, d1; $2317e ext.l d1; $23180 addq.l #$6, d1
 dc.l $23170
 dc.w 18,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$32,$39,$00,$02,$36,$0c,$48,$c1,$5c,$81
; $231a4: $231aa move.w $2360c.l, d0; $231b0 ext.l d0; $231b2 addq.l #$7, d0
 dc.l $231a2
 dc.w 18,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$30,$39,$00,$02,$36,$0c,$48,$c0,$5e,$80
; $25eac: $25eb2 move.l $8(a7), d1; $25eb6 asl.l #$1, d1
 dc.l $25eaa
 dc.w 14,$0002
 dc.b $72,$0c,$4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$08,$e3,$81
; $25ece: $25ed4 move.b d1, -$3(a6); $25ed8 ext.w d1; $25eda ext.l d1; $25edc asl.l #$2, d1
 dc.l $25ecc
 dc.w 18,$0002
 dc.b $72,$0c,$4e,$b9,$00,$02,$93,$d0,$1d,$41,$ff,$fd,$48,$81,$48,$c1,$e5,$81
; $25efe: $25f04 subq.b #$1, -$5(a6)
 dc.l $25efc
 dc.w 12,$0002
 dc.b $72,$02,$4e,$b9,$00,$02,$93,$d0,$53,$2e,$ff,$fb
; $278a0: $278a6 move.l d0, -$1c(a6); $278aa asl.l #$3, d0
 dc.l $2789e
 dc.w 14,$0002
 dc.b $72,$08,$4e,$b9,$00,$02,$93,$d0,$2d,$40,$ff,$e4,$e7,$80
; $28c38: $28c3e addi.l #$30, d1
 dc.l $28c36
 dc.w 14,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$06,$81,$00,$00,$00,$30
; $650ea: $650f0 subq.l #$3, d0
 dc.l $650ea
 dc.w 8,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$57,$80
; $65d16: $65d1c addq.l #$8, d0
 dc.l $65d14
 dc.w 10,$0002
 dc.b $72,$20,$4e,$b9,$00,$02,$93,$d0,$50,$80
; $66a7a: $66a80 addi.l #$19, d0
 dc.l $66a74
 dc.w 18,$0006
 dc.b $22,$3c,$00,$39,$73,$08,$4e,$b9,$00,$02,$93,$d0,$06,$80,$00,$00,$00,$19
; $67610: $67616 move.l $10(a7), d1; $6761a asl.l #$1, d1
 dc.l $67610
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$10,$e3,$81
; $67a92: $67a98 move.w $32fc4.l, d1; $67a9e ext.l d1; $67aa0 add.l d1, d0
 dc.l $67a92
 dc.w 16,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$32,$39,$00,$03,$2f,$c4,$48,$c1,$d0,$81
; $686aa: $686b0 moveq #$4, d1; $686b2 sub.l d0, d1
 dc.l $686aa
 dc.w 10,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$72,$04,$92,$80
; $68706: $6870c moveq #$4, d1; $6870e sub.l d0, d1
 dc.l $68706
 dc.w 10,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$72,$04,$92,$80
; $69418: $6941e move.w (a0), d1; $69420 ext.l d1; $69422 add.l d0, d1
 dc.l $69418
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$32,$10,$48,$c1,$d2,$80
; $69460: $69466 moveq #$d, d1; $69468 asl.l d1, d0
 dc.l $69460
 dc.w 10,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$72,$0d,$e3,$a0
; $69964: $6996a move.l $4(a7), d1; $6996e sub.l d0, d1
 dc.l $69964
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$04,$92,$80
; $6997e: $69984 move.w $32f96.l, d1; $6998a ext.l d1; $6998c sub.l d0, d1
 dc.l $6997e
 dc.w 16,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$32,$39,$00,$03,$2f,$96,$48,$c1,$92,$80
; $69a36: $69a3c move.l $4(a7), d1; $69a40 sub.l d0, d1
 dc.l $69a36
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$04,$92,$80
; $69a4e: $69a54 move.w $32f96.l, d1; $69a5a ext.l d1; $69a5c sub.l d0, d1
 dc.l $69a4e
 dc.w 16,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$32,$39,$00,$03,$2f,$96,$48,$c1,$92,$80
; $69c24: $69c2a addi.l #$c0, d0
 dc.l $69c24
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$06,$80,$00,$00,$00,$c0
; $69c6a: $69c70 addi.l #$64, d0
 dc.l $69c6a
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$06,$80,$00,$00,$00,$64
; $69c90: $69c96 addi.l #$64, d0
 dc.l $69c90
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$06,$80,$00,$00,$00,$64
; $69e6a: $69e70 asl.l #$5, d0
 dc.l $69e68
 dc.w 10,$0002
 dc.b $72,$03,$4e,$b9,$00,$02,$93,$d0,$eb,$80
; $6a73e: $6a744 move.w d0, -$2(a6); $6a748 addq.w #$1, -$4(a6)
 dc.l $6a73c
 dc.w 16,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$3d,$40,$ff,$fe,$52,$6e,$ff,$fc
; $6c83a: $6c840 add.l d0, d3
 dc.l $6c83a
 dc.w 8,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$d6,$80
; $6c84c: $6c852 addq.l #$4, d0
 dc.l $6c84c
 dc.w 8,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$58,$80
; $6ccb4: $6ccba move.w -$10(a6), d1; $6ccbe ext.l d1; $6ccc0 add.l d0, d1
 dc.l $6ccb4
 dc.w 14,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$32,$2e,$ff,$f0,$48,$c1,$d2,$80
; $6ce3a: $6ce40 move.l $4(a7), d1; $6ce44 sub.l d0, d1
 dc.l $6ce38
 dc.w 14,$0002
 dc.b $72,$14,$4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$04,$92,$80
; $6ce74: $6ce7a move.l $4(a7), d1; $6ce7e add.l d0, d1
 dc.l $6ce72
 dc.w 14,$0002
 dc.b $72,$14,$4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$04,$d2,$80
; $6d09a: $6d0a0 move.w #$1, $6f138.l; $6d0a8 move.w $4(a7), d1; $6d0ac ext.l d1; $6d0ae asl.l #$1, d1
 dc.l $6d09a
 dc.w 22,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$33,$fc,$00,$01,$00,$06,$f1,$38,$32,$2f,$00,$04,$48,$c1,$e3,$81
; $6d14e: $6d154 move.w $4(a7), d1; $6d158 ext.l d1; $6d15a asl.l #$2, d1
 dc.l $6d14e
 dc.w 14,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$32,$2f,$00,$04,$48,$c1,$e5,$81
; $6d980: $6d986 asl.l #$7, d0
 dc.l $6d980
 dc.w 8,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$ef,$80
; $6d998: $6d99e moveq #$c, d1; $6d9a0 asl.l d1, d0
 dc.l $6d998
 dc.w 10,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$72,$0c,$e3,$a0
; $6d9c4: $6d9ca move.w $6ef66.l, d1; $6d9d0 ext.l d1; $6d9d2 add.l d0, d1
 dc.l $6d9c4
 dc.w 16,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$32,$39,$00,$06,$ef,$66,$48,$c1,$d2,$80
; $6da06: $6da0c moveq #$3f, d1; $6da0e sub.l d0, d1
 dc.l $6da06
 dc.w 10,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$72,$3f,$92,$80
; $6da5c: $6da62 move.w $0(a7), d1; $6da66 ext.l d1; $6da68 asl.l #$2, d1
 dc.l $6da5c
 dc.w 14,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$32,$2f,$00,$00,$48,$c1,$e5,$81
; $6db04: $6db0a asl.l #$1, d0
 dc.l $6db02
 dc.w 10,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$e3,$80
; $6db86: $6db8c move.l $4(a7), d1; $6db90 sub.l d0, d1
 dc.l $6db86
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$04,$92,$80
; $6dba4: $6dbaa asl.l #$1, d0
 dc.l $6dba2
 dc.w 10,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$e3,$80
; $6dc26: $6dc2c move.l $4(a7), d1; $6dc30 sub.l d0, d1
 dc.l $6dc26
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$04,$92,$80
; $6dd5c: $6dd62 asl.l #$2, d0
 dc.l $6dd5a
 dc.w 10,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$e5,$80
; $6df78: $6df7e asl.l #$2, d0
 dc.l $6df76
 dc.w 10,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$e5,$80
; $6e1b0: $6e1b6 moveq #$12, d1; $6e1b8 asl.l d1, d0
 dc.l $6e1b0
 dc.w 10,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$72,$12,$e3,$a0
; $6e462: $6e468 addq.l #$1, d0
 dc.l $6e45c
 dc.w 14,$0006
 dc.b $22,$3c,$00,$04,$bb,$89,$4e,$b9,$00,$02,$93,$d0,$52,$80
; $6e4c6: $6e4cc move.l d0, (a0); $6e4ce addq.l #$1, -$4(a6)
 dc.l $6e4c0
 dc.w 18,$0006
 dc.b $22,$3c,$00,$00,$01,$45,$4e,$b9,$00,$02,$93,$d0,$20,$80,$52,$ae,$ff,$fc
; $6e518: $6e51e move.l -$4(a6), d1; $6e522 asl.l #$2, d1
 dc.l $6e518
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$22,$2e,$ff,$fc,$e5,$81
; $6e5c4: $6e5ca move.w d0, (a0); $6e5cc movea.l $10(a7), a0; $6e5d0 adda.l #$6f1a4, a0; $6e5d6 move.w $18(a7), d0; $6e5da ext.l d0; $6e5dc asl.l #$2, d0
 dc.l $6e5be
 dc.w 32,$0006
 dc.b $22,$3c,$00,$00,$02,$bc,$4e,$b9,$00,$02,$93,$d0,$30,$80,$20,$6f,$00,$10,$d1,$fc,$00,$06,$f1,$a4,$30,$2f,$00,$18,$48,$c0,$e5,$80
; $6e600: $6e606 move.w d0, (a0); $6e608 addq.l #$1, -$4(a6)
 dc.l $6e5fa
 dc.w 18,$0006
 dc.b $22,$3c,$00,$00,$03,$b9,$4e,$b9,$00,$02,$93,$d0,$30,$80,$52,$ae,$ff,$fc
; $6e794: $6e79a addq.l #$1, d0
 dc.l $6e78e
 dc.w 14,$0006
 dc.b $22,$3c,$00,$04,$bb,$89,$4e,$b9,$00,$02,$93,$d0,$52,$80
; $6e7f8: $6e7fe move.l d0, (a0); $6e800 addq.l #$1, -$4(a6)
 dc.l $6e7f2
 dc.w 18,$0006
 dc.b $22,$3c,$00,$00,$01,$45,$4e,$b9,$00,$02,$93,$d0,$20,$80,$52,$ae,$ff,$fc
; $6e84a: $6e850 move.l -$4(a6), d1; $6e854 asl.l #$2, d1
 dc.l $6e84a
 dc.w 12,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$22,$2e,$ff,$fc,$e5,$81
; $6e89a: $6e8a0 move.w d0, (a0); $6e8a2 movea.l $10(a7), a0; $6e8a6 adda.l #$6f198, a0; $6e8ac move.w $18(a7), d0; $6e8b0 ext.l d0; $6e8b2 asl.l #$2, d0
 dc.l $6e89a
 dc.w 26,$8000
 dc.b $4e,$b9,$00,$02,$93,$d0,$30,$80,$20,$6f,$00,$10,$d1,$fc,$00,$06,$f1,$98,$30,$2f,$00,$18,$48,$c0,$e5,$80
; $6e932: $6e938 move.w d0, (a0); $6e93a addq.l #$1, -$4(a6)
 dc.l $6e92c
 dc.w 18,$0006
 dc.b $22,$3c,$00,$00,$03,$b9,$4e,$b9,$00,$02,$93,$d0,$30,$80,$52,$ae,$ff,$fc
; $6e9b8: $6e9be asl.l #$2, d0
 dc.l $6e9b6
 dc.w 10,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$e5,$80
; $6ea10: $6ea16 asl.l #$2, d0
 dc.l $6ea0e
 dc.w 10,$0002
 dc.b $72,$0a,$4e,$b9,$00,$02,$93,$d0,$e5,$80
; $6ea98: $6ea9e move.l d0, $6f0f0.l; $6eaa4 move.l #$3fffff, d0; $6eaaa sub.l $66c3e.l, d0
 dc.l $6ea92
 dc.w 30,$0006
 dc.b $22,$3c,$00,$00,$01,$31,$4e,$b9,$00,$02,$93,$d0,$23,$c0,$00,$06,$f0,$f0,$20,$3c,$00,$3f,$ff,$ff,$90,$b9,$00,$06,$6c,$3e
 ifgt FF1_NATIVE_EXACT-1
; Additional multiply sites. Intervening $29500/$293d0 calls do not
; read incoming flags; the recorded arithmetic instruction kills XNZVC.
; $1bbac: $1bbb2 movea.l d0, a0; $1bbb4 adda.l #$1ecd4, a0; $1bbba move.l $0(a7), d0; $1bbbe addq.l #$1, d0
 dc.l $1bbac
 dc.w 20,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$40,$d1,$fc,$00,$01,$ec,$d4,$20,$2f,$00,$00,$52,$80
; $1bc0c: $1bc12 movea.l d0, a0; $1bc14 adda.l #$1ecd4, a0; $1bc1a move.l $0(a7), d0; $1bc1e addq.l #$1, d0
 dc.l $1bc0c
 dc.w 20,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$40,$d1,$fc,$00,$01,$ec,$d4,$20,$2f,$00,$00,$52,$80
; $231e4: $231ea move.b $4(a0), d1; $231ee ext.w d1; $231f0 ext.l d1; $231f2 add.l d0, d1
 dc.l $231e4
 dc.w 16,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$12,$28,$00,$04,$48,$81,$48,$c1,$d2,$80
; $23264: $2326a move.l $0(a7), d1; $2326e sub.l d0, d1
 dc.l $23264
 dc.w 12,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$2f,$00,$00,$92,$80
; $259e6: $259ec movea.l d0, a1; $259ee adda.l #$2603a, a1; $259f4 move.w $2(a1), (a0); $259f8 movea.l d0, a0; $259fa adda.l #$2603a, a0; $25a00 move.w $4(a0), $2620c.l; $25a08 movea.l d0, a0; $25a0a adda.l #$2603a, a0; $25a10 move.w $6(a0), $2620e.l; $25a18 movea.l d0, a0; $25a1a adda.l #$2603a, a0; $25a20 move.l a0, $26210.l; $25a26 move.l -$4(a6), d0; $25a2a moveq #$3e, d1; $25a2c jsr $29500.l; $25a32 movea.l d0, a0; $25a34 adda.l #$2603a, a0; $25a3a move.w (a0), d0; $25a3c move.w d0, $4(a7); $25a40 subq.w #$1, d0
 dc.l $259e6
 dc.w 92,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$40,$d3,$fc,$00,$02,$60,$3a,$30,$a9,$00,$02,$20,$40,$d1,$fc,$00,$02,$60,$3a,$33,$e8,$00,$04,$00,$02,$62,$0c,$20,$40,$d1,$fc,$00,$02,$60,$3a,$33,$e8,$00,$06,$00,$02,$62,$0e,$20,$40,$d1,$fc,$00,$02,$60,$3a,$23,$c8,$00,$02,$62,$10,$20,$2e,$ff,$fc,$72,$3e,$4e,$b9,$00,$02,$95,$00,$20,$40,$d1,$fc,$00,$02,$60,$3a,$30,$10,$3f,$40,$00,$04,$53,$40
; $25a2c: $25a32 movea.l d0, a0; $25a34 adda.l #$2603a, a0; $25a3a move.w (a0), d0; $25a3c move.w d0, $4(a7); $25a40 subq.w #$1, d0
 dc.l $25a2c
 dc.w 22,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$40,$d1,$fc,$00,$02,$60,$3a,$30,$10,$3f,$40,$00,$04,$53,$40
; $28508: $2850e moveq #$0, d1; $28510 move.b (a0), d1; $28512 addq.l #$1, $8(a6)
 dc.l $28508
 dc.w 14,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$72,$00,$12,$10,$52,$ae,$00,$08
; $28558: $2855e moveq #$0, d1; $28560 move.b (a0), d1; $28562 addq.l #$1, $8(a6)
 dc.l $28558
 dc.w 14,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$72,$00,$12,$10,$52,$ae,$00,$08
; $28d66: $28d6c moveq #$0, d1; $28d6e movea.l $8(a6), a0; $28d72 move.b (a0), d1; $28d74 addq.l #$1, $8(a6)
 dc.l $28d66
 dc.w 18,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$72,$00,$20,$6e,$00,$08,$12,$10,$52,$ae,$00,$08
; $28ecc: $28ed2 move.l -$4(a6), d1; $28ed6 andi.l #$f, d1; $28edc add.l d1, d0
 dc.l $28ecc
 dc.w 18,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$2e,$ff,$fc,$02,$81,$00,$00,$00,$0f,$d0,$81
; $291ae: $291b4 move.l -$4(a6), d1; $291b8 andi.l #$f, d1; $291be add.l d1, d0
 dc.l $291ae
 dc.w 18,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$2e,$ff,$fc,$02,$81,$00,$00,$00,$0f,$d0,$81
; $64abe: $64ac4 move.l d0, $66c42.l; $64aca move.w $1c0da.l, d0; $64ad0 ext.l d0; $64ad2 moveq #$e, d1; $64ad4 asl.l d1, d0
 dc.l $64abe
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$23,$c0,$00,$06,$6c,$42,$30,$39,$00,$01,$c0,$da,$48,$c0,$72,$0e,$e3,$a0
; $650d6: $650dc move.w $66c8c.l, d1; $650e2 ext.l d1; $650e4 addi.l #$64, d1
 dc.l $650d6
 dc.w 20,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$32,$39,$00,$06,$6c,$8c,$48,$c1,$06,$81,$00,$00,$00,$64
; $66a6e: $66a74 move.l #$397308, d1; $66a7a jsr $293d0.l; $66a80 addi.l #$19, d0
 dc.l $66a6e
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$39,$73,$08,$4e,$b9,$00,$02,$93,$d0,$06,$80,$00,$00,$00,$19
; $67564: $6756a move.l $10(a7), d1; $6756e jsr $29500.l; $67574 move.w $32fbc.l, d2; $6757a move.w d2, $18(a7); $6757e ext.l d2; $67580 asl.l #$1, d2
 dc.l $67564
 dc.w 30,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$2f,$00,$10,$4e,$b9,$00,$02,$95,$00,$34,$39,$00,$03,$2f,$bc,$3f,$42,$00,$18,$48,$c2,$e3,$82
; $6756e: $67574 move.w $32fbc.l, d2; $6757a move.w d2, $18(a7); $6757e ext.l d2; $67580 asl.l #$1, d2
 dc.l $6756e
 dc.w 20,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$34,$39,$00,$03,$2f,$bc,$3f,$42,$00,$18,$48,$c2,$e3,$82
; $69716: $6971c movea.l $0(a7), a0; $69720 adda.l #$2276a, a0; $69726 move.b (a0), d1; $69728 ext.w d1; $6972a ext.l d1; $6972c add.l d1, d0
 dc.l $69716
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$6f,$00,$00,$d1,$fc,$00,$02,$27,$6a,$12,$10,$48,$81,$48,$c1,$d0,$81
; $6974c: $69752 movea.l $0(a7), a0; $69756 adda.l #$2276a, a0; $6975c move.b (a0), d1; $6975e ext.w d1; $69760 ext.l d1; $69762 add.l d1, d0
 dc.l $6974c
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$6f,$00,$00,$d1,$fc,$00,$02,$27,$6a,$12,$10,$48,$81,$48,$c1,$d0,$81
; $69c16: $69c1c move.l d1, -$8(a6); $69c20 move.l -$4(a6), d1; $69c24 jsr $293d0.l; $69c2a addi.l #$c0, d0
 dc.l $69c16
 dc.w 26,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$2d,$41,$ff,$f8,$22,$2e,$ff,$fc,$4e,$b9,$00,$02,$93,$d0,$06,$80,$00,$00,$00,$c0
; $6a00a: $6a010 movea.l d0, a0; $6a012 adda.l #$6a210, a0; $6a018 move.w $16(a6), d0; $6a01c ext.l d0; $6a01e asl.l #$2, d0
 dc.l $6a00a
 dc.w 22,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$40,$d1,$fc,$00,$06,$a2,$10,$30,$2e,$00,$16,$48,$c0,$e5,$80
; $6a05e: $6a064 movea.l d0, a0; $6a066 adda.l #$6a210, a0; $6a06c move.w $16(a6), d0; $6a070 ext.l d0; $6a072 move.l d0, $18(a7); $6a076 asl.l #$2, d0
 dc.l $6a05e
 dc.w 26,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$40,$d1,$fc,$00,$06,$a2,$10,$30,$2e,$00,$16,$48,$c0,$2f,$40,$00,$18,$e5,$80
; $6a0b2: $6a0b8 movea.l d0, a0; $6a0ba adda.l #$6a210, a0; $6a0c0 move.l $1c(a7), d0; $6a0c4 adda.l d0, a0; $6a0c6 move.w -$2(a6), d0; $6a0ca ext.l d0; $6a0cc asl.l #$1, d0
 dc.l $6a0b2
 dc.w 28,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$40,$d1,$fc,$00,$06,$a2,$10,$20,$2f,$00,$1c,$d1,$c0,$30,$2e,$ff,$fe,$48,$c0,$e3,$80
; $6a15e: $6a164 movea.l d0, a0; $6a166 adda.l #$6a1e8, a0; $6a16c move.w $16(a6), d0; $6a170 ext.l d0; $6a172 adda.l d0, a0; $6a174 move.b (a0), d0; $6a176 ext.w d0; $6a178 ext.l d0; $6a17a asl.l #$5, d0
 dc.l $6a15e
 dc.w 30,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$20,$40,$d1,$fc,$00,$06,$a1,$e8,$30,$2e,$00,$16,$48,$c0,$d1,$c0,$10,$10,$48,$80,$48,$c0,$eb,$80
; $6aafa: $6ab00 move.l $0(a7), d1; $6ab04 sub.l d0, d1
 dc.l $6aafa
 dc.w 12,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$2f,$00,$00,$92,$80
; $6c830: $6c836 move.l -$e(a6), d1; $6c83a jsr $293d0.l; $6c840 add.l d0, d3
 dc.l $6c830
 dc.w 18,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$2e,$ff,$f2,$4e,$b9,$00,$02,$93,$d0,$d6,$80
; $6cca8: $6ccae move.l $6ccdc.l, d1; $6ccb4 jsr $293d0.l; $6ccba move.w -$10(a6), d1; $6ccbe ext.l d1; $6ccc0 add.l d0, d1
 dc.l $6cca8
 dc.w 26,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$39,$00,$06,$cc,$dc,$4e,$b9,$00,$02,$93,$d0,$32,$2e,$ff,$f0,$48,$c1,$d2,$80
; $6ce32: $6ce38 moveq #$14, d1; $6ce3a jsr $293d0.l; $6ce40 move.l $4(a7), d1; $6ce44 sub.l d0, d1
 dc.l $6ce32
 dc.w 20,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$72,$14,$4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$04,$92,$80
; $6ce6c: $6ce72 moveq #$14, d1; $6ce74 jsr $293d0.l; $6ce7a move.l $4(a7), d1; $6ce7e add.l d0, d1
 dc.l $6ce6c
 dc.w 20,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$72,$14,$4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$04,$d2,$80
; $6d104: $6d10a move.l d0, -$4(a6); $6d10e move.w $32fbc.l, d0; $6d114 move.w d0, $4(a7); $6d118 ext.l d0; $6d11a asl.l #$1, d0
 dc.l $6d104
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$2d,$40,$ff,$fc,$30,$39,$00,$03,$2f,$bc,$3f,$40,$00,$04,$48,$c0,$e3,$80
; $6d12e: $6d134 move.w $1c1c4.l, d1; $6d13a ext.l d1; $6d13c subq.l #$1, d1
 dc.l $6d12e
 dc.w 16,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$32,$39,$00,$01,$c1,$c4,$48,$c1,$53,$81
; $6e44a: $6e450 jsr $29500.l; $6e456 jsr $29500.l; $6e45c move.l #$4bb89, d1; $6e462 jsr $293d0.l; $6e468 addq.l #$1, d0
 dc.l $6e44a
 dc.w 32,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$4e,$b9,$00,$02,$95,$00,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$04,$bb,$89,$4e,$b9,$00,$02,$93,$d0,$52,$80
; $6e450: $6e456 jsr $29500.l; $6e45c move.l #$4bb89, d1; $6e462 jsr $293d0.l; $6e468 addq.l #$1, d0
 dc.l $6e450
 dc.w 26,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$04,$bb,$89,$4e,$b9,$00,$02,$93,$d0,$52,$80
; $6e456: $6e45c move.l #$4bb89, d1; $6e462 jsr $293d0.l; $6e468 addq.l #$1, d0
 dc.l $6e456
 dc.w 20,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$04,$bb,$89,$4e,$b9,$00,$02,$93,$d0,$52,$80
; $6e4b4: $6e4ba jsr $29500.l; $6e4c0 move.l #$145, d1; $6e4c6 jsr $293d0.l; $6e4cc move.l d0, (a0); $6e4ce addq.l #$1, -$4(a6)
 dc.l $6e4b4
 dc.w 30,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$45,$4e,$b9,$00,$02,$93,$d0,$20,$80,$52,$ae,$ff,$fc
; $6e4ba: $6e4c0 move.l #$145, d1; $6e4c6 jsr $293d0.l; $6e4cc move.l d0, (a0); $6e4ce addq.l #$1, -$4(a6)
 dc.l $6e4ba
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$45,$4e,$b9,$00,$02,$93,$d0,$20,$80,$52,$ae,$ff,$fc
; $6e592: $6e598 move.w $1c0b4.l, d1; $6e59e ext.l d1; $6e5a0 asl.l #$2, d1
 dc.l $6e592
 dc.w 16,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$32,$39,$00,$01,$c0,$b4,$48,$c1,$e5,$81
; $6e5ac: $6e5b2 move.l #$1194, d1; $6e5b8 jsr $293d0.l; $6e5be move.l #$2bc, d1; $6e5c4 jsr $293d0.l; $6e5ca move.w d0, (a0); $6e5cc movea.l $10(a7), a0; $6e5d0 adda.l #$6f1a4, a0; $6e5d6 move.w $18(a7), d0; $6e5da ext.l d0; $6e5dc asl.l #$2, d0
 dc.l $6e5ac
 dc.w 50,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$11,$94,$4e,$b9,$00,$02,$93,$d0,$22,$3c,$00,$00,$02,$bc,$4e,$b9,$00,$02,$93,$d0,$30,$80,$20,$6f,$00,$10,$d1,$fc,$00,$06,$f1,$a4,$30,$2f,$00,$18,$48,$c0,$e5,$80
; $6e5f4: $6e5fa move.l #$3b9, d1; $6e600 jsr $293d0.l; $6e606 move.w d0, (a0); $6e608 addq.l #$1, -$4(a6)
 dc.l $6e5f4
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$03,$b9,$4e,$b9,$00,$02,$93,$d0,$30,$80,$52,$ae,$ff,$fc
; $6e77c: $6e782 jsr $29500.l; $6e788 jsr $29500.l; $6e78e move.l #$4bb89, d1; $6e794 jsr $293d0.l; $6e79a addq.l #$1, d0
 dc.l $6e77c
 dc.w 32,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$4e,$b9,$00,$02,$95,$00,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$04,$bb,$89,$4e,$b9,$00,$02,$93,$d0,$52,$80
; $6e782: $6e788 jsr $29500.l; $6e78e move.l #$4bb89, d1; $6e794 jsr $293d0.l; $6e79a addq.l #$1, d0
 dc.l $6e782
 dc.w 26,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$04,$bb,$89,$4e,$b9,$00,$02,$93,$d0,$52,$80
; $6e788: $6e78e move.l #$4bb89, d1; $6e794 jsr $293d0.l; $6e79a addq.l #$1, d0
 dc.l $6e788
 dc.w 20,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$04,$bb,$89,$4e,$b9,$00,$02,$93,$d0,$52,$80
; $6e7e6: $6e7ec jsr $29500.l; $6e7f2 move.l #$145, d1; $6e7f8 jsr $293d0.l; $6e7fe move.l d0, (a0); $6e800 addq.l #$1, -$4(a6)
 dc.l $6e7e6
 dc.w 30,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$45,$4e,$b9,$00,$02,$93,$d0,$20,$80,$52,$ae,$ff,$fc
; $6e7ec: $6e7f2 move.l #$145, d1; $6e7f8 jsr $293d0.l; $6e7fe move.l d0, (a0); $6e800 addq.l #$1, -$4(a6)
 dc.l $6e7ec
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$45,$4e,$b9,$00,$02,$93,$d0,$20,$80,$52,$ae,$ff,$fc
; $6e8ca: $6e8d0 move.w $1ed36.l, d1; $6e8d6 ext.l d1; $6e8d8 asl.l #$2, d1
 dc.l $6e8ca
 dc.w 16,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$32,$39,$00,$01,$ed,$36,$48,$c1,$e5,$81
; $6e8e4: $6e8ea move.l #$1194, d1; $6e8f0 jsr $293d0.l; $6e8f6 move.l #$2bc, d1; $6e8fc jsr $293d0.l; $6e902 move.w d0, (a0); $6e904 movea.l $10(a7), a0; $6e908 adda.l #$6f20a, a0; $6e90e movea.l $1c(a7), a1; $6e912 adda.l #$6f09a, a1; $6e918 movea.l $24(a7), a2; $6e91c adda.l #$6f082, a2; $6e922 move.l (a1), d0; $6e924 move.l (a2), d1; $6e926 jsr $29500.l; $6e92c move.l #$3b9, d1; $6e932 jsr $293d0.l; $6e938 move.w d0, (a0); $6e93a addq.l #$1, -$4(a6)
 dc.l $6e8e4
 dc.w 90,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$11,$94,$4e,$b9,$00,$02,$93,$d0,$22,$3c,$00,$00,$02,$bc,$4e,$b9,$00,$02,$93,$d0,$30,$80,$20,$6f,$00,$10,$d1,$fc,$00,$06,$f2,$0a,$22,$6f,$00,$1c,$d3,$fc,$00,$06,$f0,$9a,$24,$6f,$00,$24,$d5,$fc,$00,$06,$f0,$82,$20,$11,$22,$12,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$03,$b9,$4e,$b9,$00,$02,$93,$d0,$30,$80,$52,$ae,$ff,$fc
; $6e926: $6e92c move.l #$3b9, d1; $6e932 jsr $293d0.l; $6e938 move.w d0, (a0); $6e93a addq.l #$1, -$4(a6)
 dc.l $6e926
 dc.w 24,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$03,$b9,$4e,$b9,$00,$02,$93,$d0,$30,$80,$52,$ae,$ff,$fc
; $6ea60: $6ea66 move.l #$10e, d1; $6ea6c jsr $293d0.l; $6ea72 move.l $8(a7), d1; $6ea76 jsr $29500.l; $6ea7c move.l #$10e, d1; $6ea82 jsr $293d0.l; $6ea88 move.l $8(a7), d1; $6ea8c jsr $29500.l; $6ea92 move.l #$131, d1; $6ea98 jsr $293d0.l; $6ea9e move.l d0, $6f0f0.l; $6eaa4 move.l #$3fffff, d0; $6eaaa sub.l $66c3e.l, d0
 dc.l $6ea60
 dc.w 80,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$0e,$4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$08,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$0e,$4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$08,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$31,$4e,$b9,$00,$02,$93,$d0,$23,$c0,$00,$06,$f0,$f0,$20,$3c,$00,$3f,$ff,$ff,$90,$b9,$00,$06,$6c,$3e
; $6ea76: $6ea7c move.l #$10e, d1; $6ea82 jsr $293d0.l; $6ea88 move.l $8(a7), d1; $6ea8c jsr $29500.l; $6ea92 move.l #$131, d1; $6ea98 jsr $293d0.l; $6ea9e move.l d0, $6f0f0.l; $6eaa4 move.l #$3fffff, d0; $6eaaa sub.l $66c3e.l, d0
 dc.l $6ea76
 dc.w 58,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$0e,$4e,$b9,$00,$02,$93,$d0,$22,$2f,$00,$08,$4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$31,$4e,$b9,$00,$02,$93,$d0,$23,$c0,$00,$06,$f0,$f0,$20,$3c,$00,$3f,$ff,$ff,$90,$b9,$00,$06,$6c,$3e
; $6ea8c: $6ea92 move.l #$131, d1; $6ea98 jsr $293d0.l; $6ea9e move.l d0, $6f0f0.l; $6eaa4 move.l #$3fffff, d0; $6eaaa sub.l $66c3e.l, d0
 dc.l $6ea8c
 dc.w 36,$4000
 dc.b $4e,$b9,$00,$02,$95,$00,$22,$3c,$00,$00,$01,$31,$4e,$b9,$00,$02,$93,$d0,$23,$c0,$00,$06,$f0,$f0,$20,$3c,$00,$3f,$ff,$ff,$90,$b9,$00,$06,$6c,$3e
 endc
 ifgt FF1_NATIVE_EXACT-4
; Additional sites with BOTH paths of conditional branches audited. Guard-only
; fragments cover every visited instruction through the final XNZVC kill.
; $23250 division: CFG proof fragments below.
 dc.l $23250
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $2864e division: CFG proof fragments below.
 dc.l $2864e
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $2867c division: CFG proof fragments below.
 dc.l $2867c
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $689e0 division: CFG proof fragments below.
 dc.l $689e0
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $689f8 division: CFG proof fragments below.
 dc.l $689f8
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $693b8 multiply: CFG proof fragments below.
 dc.l $693b8
 dc.w 6,$4000
 dc.w $4eb9,$0002,$9500
; $693cc division: CFG proof fragments below.
 dc.l $693cc
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6a730 division: CFG proof fragments below.
 dc.l $6a730
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6aae4 division: CFG proof fragments below.
 dc.l $6aae4
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6cc2a division: CFG proof fragments below.
 dc.l $6cc2a
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6cc3e division: CFG proof fragments below.
 dc.l $6cc3e
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6cc62 multiply: CFG proof fragments below.
 dc.l $6cc62
 dc.w 6,$4000
 dc.w $4eb9,$0002,$9500
; $6cc84 multiply: CFG proof fragments below.
 dc.l $6cc84
 dc.w 6,$4000
 dc.w $4eb9,$0002,$9500
; $6d0e0 multiply: CFG proof fragments below.
 dc.l $6d0e0
 dc.w 6,$4000
 dc.w $4eb9,$0002,$9500
; $6db40 multiply: CFG proof fragments below.
 dc.l $6db40
 dc.w 6,$4000
 dc.w $4eb9,$0002,$9500
; $6dbe0 multiply: CFG proof fragments below.
 dc.l $6dbe0
 dc.w 6,$4000
 dc.w $4eb9,$0002,$9500
; $6e532 division: CFG proof fragments below.
 dc.l $6e532
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6e556 division: CFG proof fragments below.
 dc.l $6e556
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6e568 division: CFG proof fragments below.
 dc.l $6e568
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6e5b8 division: CFG proof fragments below.
 dc.l $6e5b8
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6e864 division: CFG proof fragments below.
 dc.l $6e864
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6e888 division: CFG proof fragments below.
 dc.l $6e888
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6e8f0 division: CFG proof fragments below.
 dc.l $6e8f0
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6e8fc division: CFG proof fragments below.
 dc.l $6e8fc
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6ea6c division: CFG proof fragments below.
 dc.l $6ea6c
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $6ea82 division: CFG proof fragments below.
 dc.l $6ea82
 dc.w 6,$8000
 dc.w $4eb9,$0002,$93d0
; $23250 jsr $293d0.l
 dc.l $23250
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $23256 movea.l $8(a6), a0
 dc.l $23256
 dc.w 4,$2000
 dc.b $20,$6e,$00,$08
; $2325a move.b d0, $3(a0)
 dc.l $2325a
 dc.w 4,$2000
 dc.b $11,$40,$00,$03
; $2325e ext.w d0
 dc.l $2325e
 dc.w 2,$2000
 dc.b $48,$80
; $23260 ext.l d0
 dc.l $23260
 dc.w 2,$2000
 dc.b $48,$c0
; $23262 moveq #$a, d1
 dc.l $23262
 dc.w 2,$2000
 dc.b $72,$0a
; $23264 jsr $29500.l
 dc.l $23264
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $2326a move.l $0(a7), d1
 dc.l $2326a
 dc.w 4,$2000
 dc.b $22,$2f,$00,$00
; $2326e sub.l d0, d1
 dc.l $2326e
 dc.w 2,$2000
 dc.b $92,$80
; $28648 move.l -$34(a6), d0
 dc.l $28648
 dc.w 4,$2000
 dc.b $20,$2e,$ff,$cc
; $2864c moveq #$a, d1
 dc.l $2864c
 dc.w 2,$2000
 dc.b $72,$0a
; $2864e jsr $293d0.l
 dc.l $2864e
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $28654 move.l d1, -$8(a6)
 dc.l $28654
 dc.w 4,$2000
 dc.b $2d,$41,$ff,$f8
; $28658 tst.l d1
 dc.l $28658
 dc.w 2,$2000
 dc.b $4a,$81
; $2865a bpl.b $28660
 dc.l $2865a
 dc.w 2,$2000
 dc.b $6a,$04
; $2865c neg.l -$8(a6)
 dc.l $2865c
 dc.w 4,$2000
 dc.b $44,$ae,$ff,$f8
; $28660 subq.l #$1, -$4(a6)
 dc.l $28660
 dc.w 4,$2000
 dc.b $53,$ae,$ff,$fc
; $2867c jsr $293d0.l
 dc.l $2867c
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $28682 move.l d0, -$34(a6)
 dc.l $28682
 dc.w 4,$2000
 dc.b $2d,$40,$ff,$cc
; $28686 tst.l -$34(a6)
 dc.l $28686
 dc.w 4,$2000
 dc.b $4a,$ae,$ff,$cc
; $2868a bne.b $28648
 dc.l $2868a
 dc.w 2,$2000
 dc.b $66,$bc
; $2868c cmpi.l #$1, -$18(a6)
 dc.l $2868c
 dc.w 8,$2000
 dc.b $0c,$ae,$00,$00,$00,$01,$ff,$e8
; $28694 bne.b $286a4
 dc.l $28694
 dc.w 2,$2000
 dc.b $66,$0e
; $28696 subq.l #$1, -$4(a6)
 dc.l $28696
 dc.w 4,$2000
 dc.b $53,$ae,$ff,$fc
; $286a4 lea.l -$48(a6), a0
 dc.l $286a4
 dc.w 4,$2000
 dc.b $41,$ee,$ff,$b8
; $286a8 move.l -$4(a6), d0
 dc.l $286a8
 dc.w 4,$2000
 dc.b $20,$2e,$ff,$fc
; $286ac adda.l d0, a0
 dc.l $286ac
 dc.w 2,$2000
 dc.b $d1,$c0
; $286ae moveq #$b, d1
 dc.l $286ae
 dc.w 2,$2000
 dc.b $72,$0b
; $286b0 sub.l d0, d1
 dc.l $286b0
 dc.w 2,$2000
 dc.b $92,$80
; $689e0 jsr $293d0.l
 dc.l $689e0
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $689e6 move.b d1, (a0)
 dc.l $689e6
 dc.w 2,$2000
 dc.b $10,$81
; $689e8 movea.l $0(a7), a0
 dc.l $689e8
 dc.w 4,$2000
 dc.b $20,$6f,$00,$00
; $689ec adda.l #$22782, a0
 dc.l $689ec
 dc.w 6,$2000
 dc.b $d1,$fc,$00,$02,$27,$82
; $689f2 move.l $8(a7), d0
 dc.l $689f2
 dc.w 4,$2000
 dc.b $20,$2f,$00,$08
; $689f6 moveq #$a, d1
 dc.l $689f6
 dc.w 2,$2000
 dc.b $72,$0a
; $689f8 jsr $293d0.l
 dc.l $689f8
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $689fe move.b d0, (a0)
 dc.l $689fe
 dc.w 2,$2000
 dc.b $10,$80
; $68a00 tst.w $1ed2c.l
 dc.l $68a00
 dc.w 6,$2000
 dc.b $4a,$79,$00,$01,$ed,$2c
; $68a06 bne.b $68a10
 dc.l $68a06
 dc.w 2,$2000
 dc.b $66,$08
; $68a08 tst.w $32fbc.l
 dc.l $68a08
 dc.w 6,$2000
 dc.b $4a,$79,$00,$03,$2f,$bc
; $68a0e bne.b $68a26
 dc.l $68a0e
 dc.w 2,$2000
 dc.b $66,$16
; $68a10 move.w $32fbc.l, d0
 dc.l $68a10
 dc.w 6,$2000
 dc.b $30,$39,$00,$03,$2f,$bc
; $68a16 ext.l d0
 dc.l $68a16
 dc.w 2,$2000
 dc.b $48,$c0
; $68a18 asl.l #$1, d0
 dc.l $68a18
 dc.w 2,$2000
 dc.b $e3,$80
; $68a26 move.w $32fbc.l, d0
 dc.l $68a26
 dc.w 6,$2000
 dc.b $30,$39,$00,$03,$2f,$bc
; $68a2c ext.l d0
 dc.l $68a2c
 dc.w 2,$2000
 dc.b $48,$c0
; $68a2e asl.l #$1, d0
 dc.l $68a2e
 dc.w 2,$2000
 dc.b $e3,$80
; $693b8 jsr $29500.l
 dc.l $693b8
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $693be move.l d0, $10(a7)
 dc.l $693be
 dc.w 4,$2000
 dc.b $2f,$40,$00,$10
; $693c2 move.l $2aa9c.l, d0
 dc.l $693c2
 dc.w 6,$2000
 dc.b $20,$39,$00,$02,$aa,$9c
; $693c8 move.l $10(a7), d1
 dc.l $693c8
 dc.w 4,$2000
 dc.b $22,$2f,$00,$10
; $693cc jsr $293d0.l
 dc.l $693cc
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $693d2 move.w d0, -$2(a6)
 dc.l $693d2
 dc.w 4,$2000
 dc.b $3d,$40,$ff,$fe
; $693d6 cmpi.w #$3f, d0
 dc.l $693d6
 dc.w 4,$2000
 dc.b $0c,$40,$00,$3f
; $693da ble.b $693e2
 dc.l $693da
 dc.w 2,$2000
 dc.b $6f,$06
; $693dc move.w #$3f, -$2(a6)
 dc.l $693dc
 dc.w 6,$2000
 dc.b $3d,$7c,$00,$3f,$ff,$fe
; $693e2 move.w $32f2a.l, d0
 dc.l $693e2
 dc.w 6,$2000
 dc.b $30,$39,$00,$03,$2f,$2a
; $693e8 move.w d0, $10(a7)
 dc.l $693e8
 dc.w 4,$2000
 dc.b $3f,$40,$00,$10
; $693ec ext.l d0
 dc.l $693ec
 dc.w 2,$2000
 dc.b $48,$c0
; $693ee asl.l #$1, d0
 dc.l $693ee
 dc.w 2,$2000
 dc.b $e3,$80
; $6a730 jsr $293d0.l
 dc.l $6a730
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6a736 move.b d1, (a0)
 dc.l $6a736
 dc.w 2,$2000
 dc.b $10,$81
; $6a738 move.l $10(a7), d0
 dc.l $6a738
 dc.w 4,$2000
 dc.b $20,$2f,$00,$10
; $6a73c moveq #$a, d1
 dc.l $6a73c
 dc.w 2,$2000
 dc.b $72,$0a
; $6a73e jsr $293d0.l
 dc.l $6a73e
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6a744 move.w d0, -$2(a6)
 dc.l $6a744
 dc.w 4,$2000
 dc.b $3d,$40,$ff,$fe
; $6a748 addq.w #$1, -$4(a6)
 dc.l $6a748
 dc.w 4,$2000
 dc.b $52,$6e,$ff,$fc
; $6aae4 jsr $293d0.l
 dc.l $6aae4
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6aaea move.w d0, -$2(a6)
 dc.l $6aaea
 dc.w 4,$2000
 dc.b $3d,$40,$ff,$fe
; $6aaee ext.l d0
 dc.l $6aaee
 dc.w 2,$2000
 dc.b $48,$c0
; $6aaf0 move.l d0, $4(a7)
 dc.l $6aaf0
 dc.w 4,$2000
 dc.b $2f,$40,$00,$04
; $6aaf4 move.l #$258, d1
 dc.l $6aaf4
 dc.w 6,$2000
 dc.b $22,$3c,$00,$00,$02,$58
; $6aafa jsr $29500.l
 dc.l $6aafa
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6ab00 move.l $0(a7), d1
 dc.l $6ab00
 dc.w 4,$2000
 dc.b $22,$2f,$00,$00
; $6ab04 sub.l d0, d1
 dc.l $6ab04
 dc.w 2,$2000
 dc.b $92,$80
; $6cc2a jsr $293d0.l
 dc.l $6cc2a
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6cc30 move.l d0, -$8(a6)
 dc.l $6cc30
 dc.w 4,$2000
 dc.b $2d,$40,$ff,$f8
; $6cc34 move.l $6cce0.l, d0
 dc.l $6cc34
 dc.w 6,$2000
 dc.b $20,$39,$00,$06,$cc,$e0
; $6cc3a move.l -$4(a6), d1
 dc.l $6cc3a
 dc.w 4,$2000
 dc.b $22,$2e,$ff,$fc
; $6cc3e jsr $293d0.l
 dc.l $6cc3e
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6cc44 clr.w -$10(a6)
 dc.l $6cc44
 dc.w 4,$2000
 dc.b $42,$6e,$ff,$f0
; $6cc48 move.w -$e(a6), d1
 dc.l $6cc48
 dc.w 4,$2000
 dc.b $32,$2e,$ff,$f2
; $6cc4c ext.l d1
 dc.l $6cc4c
 dc.w 2,$2000
 dc.b $48,$c1
; $6cc4e move.l d0, -$4(a6)
 dc.l $6cc4e
 dc.w 4,$2000
 dc.b $2d,$40,$ff,$fc
; $6cc52 cmpi.l #$5, d1
 dc.l $6cc52
 dc.w 6,$2000
 dc.b $0c,$81,$00,$00,$00,$05
; $6cc58 ble.b $6cc6e
 dc.l $6cc58
 dc.w 2,$2000
 dc.b $6f,$14
; $6cc5a move.l -$8(a6), d0
 dc.l $6cc5a
 dc.w 4,$2000
 dc.b $20,$2e,$ff,$f8
; $6cc5e neg.l d0
 dc.l $6cc5e
 dc.w 2,$2000
 dc.b $44,$80
; $6cc62 jsr $29500.l
 dc.l $6cc62
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6cc68 move.w d0, -$10(a6)
 dc.l $6cc68
 dc.w 4,$2000
 dc.b $3d,$40,$ff,$f0
; $6cc6c bra.b $6cc9c
 dc.l $6cc6c
 dc.w 2,$2000
 dc.b $60,$2e
; $6cc6e move.w -$e(a6), d0
 dc.l $6cc6e
 dc.w 4,$2000
 dc.b $30,$2e,$ff,$f2
; $6cc72 ext.l d0
 dc.l $6cc72
 dc.w 2,$2000
 dc.b $48,$c0
; $6cc74 cmpi.l #$fffffffb, d0
 dc.l $6cc74
 dc.w 6,$2000
 dc.b $0c,$80,$ff,$ff,$ff,$fb
; $6cc7a bge.b $6cc90
 dc.l $6cc7a
 dc.w 2,$2000
 dc.b $6c,$14
; $6cc7c moveq #$fb, d1
 dc.l $6cc7c
 dc.w 2,$2000
 dc.b $72,$fb
; $6cc7e sub.l d0, d1
 dc.l $6cc7e
 dc.w 2,$2000
 dc.b $92,$80
; $6cc84 jsr $29500.l
 dc.l $6cc84
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6cc8a move.w d0, -$10(a6)
 dc.l $6cc8a
 dc.w 4,$2000
 dc.b $3d,$40,$ff,$f0
; $6cc8e bra.b $6cc9c
 dc.l $6cc8e
 dc.w 2,$2000
 dc.b $60,$0c
; $6cc90 move.l -$4(a6), d0
 dc.l $6cc90
 dc.w 4,$2000
 dc.b $20,$2e,$ff,$fc
; $6cc94 sub.l -$8(a6), d0
 dc.l $6cc94
 dc.w 4,$2000
 dc.b $90,$ae,$ff,$f8
; $6cc9c move.w -$a(a6), d0
 dc.l $6cc9c
 dc.w 4,$2000
 dc.b $30,$2e,$ff,$f6
; $6cca0 ext.l d0
 dc.l $6cca0
 dc.w 2,$2000
 dc.b $48,$c0
; $6cca2 move.l $6ccd8.l, d1
 dc.l $6cca2
 dc.w 6,$2000
 dc.b $22,$39,$00,$06,$cc,$d8
; $6cca8 jsr $29500.l
 dc.l $6cca8
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6ccae move.l $6ccdc.l, d1
 dc.l $6ccae
 dc.w 6,$2000
 dc.b $22,$39,$00,$06,$cc,$dc
; $6ccb4 jsr $293d0.l
 dc.l $6ccb4
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6ccba move.w -$10(a6), d1
 dc.l $6ccba
 dc.w 4,$2000
 dc.b $32,$2e,$ff,$f0
; $6ccbe ext.l d1
 dc.l $6ccbe
 dc.w 2,$2000
 dc.b $48,$c1
; $6ccc0 add.l d0, d1
 dc.l $6ccc0
 dc.w 2,$2000
 dc.b $d2,$80
; $6d0e0 jsr $29500.l
 dc.l $6d0e0
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6d0e6 move.l d0, -$4(a6)
 dc.l $6d0e6
 dc.w 4,$2000
 dc.b $2d,$40,$ff,$fc
; $6d0ea bra.b $6d10e
 dc.l $6d0ea
 dc.w 2,$2000
 dc.b $60,$22
; $6d10e move.w $32fbc.l, d0
 dc.l $6d10e
 dc.w 6,$2000
 dc.b $30,$39,$00,$03,$2f,$bc
; $6d114 move.w d0, $4(a7)
 dc.l $6d114
 dc.w 4,$2000
 dc.b $3f,$40,$00,$04
; $6d118 ext.l d0
 dc.l $6d118
 dc.w 2,$2000
 dc.b $48,$c0
; $6d11a asl.l #$1, d0
 dc.l $6d11a
 dc.w 2,$2000
 dc.b $e3,$80
; $6db40 jsr $29500.l
 dc.l $6db40
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6db46 tst.l d0
 dc.l $6db46
 dc.w 2,$2000
 dc.b $4a,$80
; $6db48 bpl.b $6db68
 dc.l $6db48
 dc.w 2,$2000
 dc.b $6a,$1e
; $6db4a move.w $8(a7), d0
 dc.l $6db4a
 dc.w 4,$2000
 dc.b $30,$2f,$00,$08
; $6db4e ext.l d0
 dc.l $6db4e
 dc.w 2,$2000
 dc.b $48,$c0
; $6db50 asl.l #$1, d0
 dc.l $6db50
 dc.w 2,$2000
 dc.b $e3,$80
; $6db68 move.w $32fbc.l, d0
 dc.l $6db68
 dc.w 6,$2000
 dc.b $30,$39,$00,$03,$2f,$bc
; $6db6e ext.l d0
 dc.l $6db6e
 dc.w 2,$2000
 dc.b $48,$c0
; $6db70 asl.l #$1, d0
 dc.l $6db70
 dc.w 2,$2000
 dc.b $e3,$80
; $6dbe0 jsr $29500.l
 dc.l $6dbe0
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6dbe6 tst.l d0
 dc.l $6dbe6
 dc.w 2,$2000
 dc.b $4a,$80
; $6dbe8 bpl.b $6dc08
 dc.l $6dbe8
 dc.w 2,$2000
 dc.b $6a,$1e
; $6dbea move.w $8(a7), d0
 dc.l $6dbea
 dc.w 4,$2000
 dc.b $30,$2f,$00,$08
; $6dbee ext.l d0
 dc.l $6dbee
 dc.w 2,$2000
 dc.b $48,$c0
; $6dbf0 asl.l #$1, d0
 dc.l $6dbf0
 dc.w 2,$2000
 dc.b $e3,$80
; $6dc08 move.w $32fbc.l, d0
 dc.l $6dc08
 dc.w 6,$2000
 dc.b $30,$39,$00,$03,$2f,$bc
; $6dc0e ext.l d0
 dc.l $6dc0e
 dc.w 2,$2000
 dc.b $48,$c0
; $6dc10 asl.l #$1, d0
 dc.l $6dc10
 dc.w 2,$2000
 dc.b $e3,$80
; $6e532 jsr $293d0.l
 dc.l $6e532
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e538 move.w d0, (a0)
 dc.l $6e538
 dc.w 2,$2000
 dc.b $30,$80
; $6e53a movea.l $10(a7), a0
 dc.l $6e53a
 dc.w 4,$2000
 dc.b $20,$6f,$00,$10
; $6e53e adda.l #$6f168, a0
 dc.l $6e53e
 dc.w 6,$2000
 dc.b $d1,$fc,$00,$06,$f1,$68
; $6e544 movea.l $1c(a7), a1
 dc.l $6e544
 dc.w 4,$2000
 dc.b $22,$6f,$00,$1c
; $6e548 adda.l #$6f09a, a1
 dc.l $6e548
 dc.w 6,$2000
 dc.b $d3,$fc,$00,$06,$f0,$9a
; $6e54e move.l #$ae7fe0, d0
 dc.l $6e54e
 dc.w 6,$2000
 dc.b $20,$3c,$00,$ae,$7f,$e0
; $6e554 move.l (a1), d1
 dc.l $6e554
 dc.w 2,$2000
 dc.b $22,$11
; $6e556 jsr $293d0.l
 dc.l $6e556
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e55c movea.l $24(a7), a1
 dc.l $6e55c
 dc.w 4,$2000
 dc.b $22,$6f,$00,$24
; $6e560 adda.l #$6f082, a1
 dc.l $6e560
 dc.w 6,$2000
 dc.b $d3,$fc,$00,$06,$f0,$82
; $6e566 move.l (a1), d1
 dc.l $6e566
 dc.w 2,$2000
 dc.b $22,$11
; $6e568 jsr $293d0.l
 dc.l $6e568
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e56e move.w d0, (a0)
 dc.l $6e56e
 dc.w 2,$2000
 dc.b $30,$80
; $6e570 movea.l $10(a7), a0
 dc.l $6e570
 dc.w 4,$2000
 dc.b $20,$6f,$00,$10
; $6e574 adda.l #$6f174, a0
 dc.l $6e574
 dc.w 6,$2000
 dc.b $d1,$fc,$00,$06,$f1,$74
; $6e57a movea.l $1c(a7), a1
 dc.l $6e57a
 dc.w 4,$2000
 dc.b $22,$6f,$00,$1c
; $6e57e adda.l #$6f09a, a1
 dc.l $6e57e
 dc.w 6,$2000
 dc.b $d3,$fc,$00,$06,$f0,$9a
; $6e584 movea.l $24(a7), a2
 dc.l $6e584
 dc.w 4,$2000
 dc.b $24,$6f,$00,$24
; $6e588 adda.l #$6f082, a2
 dc.l $6e588
 dc.w 6,$2000
 dc.b $d5,$fc,$00,$06,$f0,$82
; $6e58e move.l (a1), d0
 dc.l $6e58e
 dc.w 2,$2000
 dc.b $20,$11
; $6e590 move.l (a2), d1
 dc.l $6e590
 dc.w 2,$2000
 dc.b $22,$12
; $6e592 jsr $29500.l
 dc.l $6e592
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6e598 move.w $1c0b4.l, d1
 dc.l $6e598
 dc.w 6,$2000
 dc.b $32,$39,$00,$01,$c0,$b4
; $6e59e ext.l d1
 dc.l $6e59e
 dc.w 2,$2000
 dc.b $48,$c1
; $6e5a0 asl.l #$2, d1
 dc.l $6e5a0
 dc.w 2,$2000
 dc.b $e5,$81
; $6e5b8 jsr $293d0.l
 dc.l $6e5b8
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e5be move.l #$2bc, d1
 dc.l $6e5be
 dc.w 6,$2000
 dc.b $22,$3c,$00,$00,$02,$bc
; $6e5c4 jsr $293d0.l
 dc.l $6e5c4
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e5ca move.w d0, (a0)
 dc.l $6e5ca
 dc.w 2,$2000
 dc.b $30,$80
; $6e5cc movea.l $10(a7), a0
 dc.l $6e5cc
 dc.w 4,$2000
 dc.b $20,$6f,$00,$10
; $6e5d0 adda.l #$6f1a4, a0
 dc.l $6e5d0
 dc.w 6,$2000
 dc.b $d1,$fc,$00,$06,$f1,$a4
; $6e5d6 move.w $18(a7), d0
 dc.l $6e5d6
 dc.w 4,$2000
 dc.b $30,$2f,$00,$18
; $6e5da ext.l d0
 dc.l $6e5da
 dc.w 2,$2000
 dc.b $48,$c0
; $6e5dc asl.l #$2, d0
 dc.l $6e5dc
 dc.w 2,$2000
 dc.b $e5,$80
; $6e864 jsr $293d0.l
 dc.l $6e864
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e86a move.w d0, (a0)
 dc.l $6e86a
 dc.w 2,$2000
 dc.b $30,$80
; $6e86c movea.l $10(a7), a0
 dc.l $6e86c
 dc.w 4,$2000
 dc.b $20,$6f,$00,$10
; $6e870 adda.l #$6f18c, a0
 dc.l $6e870
 dc.w 6,$2000
 dc.b $d1,$fc,$00,$06,$f1,$8c
; $6e876 movea.l $1c(a7), a1
 dc.l $6e876
 dc.w 4,$2000
 dc.b $22,$6f,$00,$1c
; $6e87a adda.l #$6f09a, a1
 dc.l $6e87a
 dc.w 6,$2000
 dc.b $d3,$fc,$00,$06,$f0,$9a
; $6e880 move.l #$ae7fe0, d0
 dc.l $6e880
 dc.w 6,$2000
 dc.b $20,$3c,$00,$ae,$7f,$e0
; $6e886 move.l (a1), d1
 dc.l $6e886
 dc.w 2,$2000
 dc.b $22,$11
; $6e888 jsr $293d0.l
 dc.l $6e888
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e88e movea.l $24(a7), a1
 dc.l $6e88e
 dc.w 4,$2000
 dc.b $22,$6f,$00,$24
; $6e892 adda.l #$6f082, a1
 dc.l $6e892
 dc.w 6,$2000
 dc.b $d3,$fc,$00,$06,$f0,$82
; $6e898 move.l (a1), d1
 dc.l $6e898
 dc.w 2,$2000
 dc.b $22,$11
; $6e89a jsr $293d0.l
 dc.l $6e89a
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e8a0 move.w d0, (a0)
 dc.l $6e8a0
 dc.w 2,$2000
 dc.b $30,$80
; $6e8a2 movea.l $10(a7), a0
 dc.l $6e8a2
 dc.w 4,$2000
 dc.b $20,$6f,$00,$10
; $6e8a6 adda.l #$6f198, a0
 dc.l $6e8a6
 dc.w 6,$2000
 dc.b $d1,$fc,$00,$06,$f1,$98
; $6e8ac move.w $18(a7), d0
 dc.l $6e8ac
 dc.w 4,$2000
 dc.b $30,$2f,$00,$18
; $6e8b0 ext.l d0
 dc.l $6e8b0
 dc.w 2,$2000
 dc.b $48,$c0
; $6e8b2 asl.l #$2, d0
 dc.l $6e8b2
 dc.w 2,$2000
 dc.b $e5,$80
; $6e8f0 jsr $293d0.l
 dc.l $6e8f0
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e8f6 move.l #$2bc, d1
 dc.l $6e8f6
 dc.w 6,$2000
 dc.b $22,$3c,$00,$00,$02,$bc
; $6e8fc jsr $293d0.l
 dc.l $6e8fc
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e902 move.w d0, (a0)
 dc.l $6e902
 dc.w 2,$2000
 dc.b $30,$80
; $6e904 movea.l $10(a7), a0
 dc.l $6e904
 dc.w 4,$2000
 dc.b $20,$6f,$00,$10
; $6e908 adda.l #$6f20a, a0
 dc.l $6e908
 dc.w 6,$2000
 dc.b $d1,$fc,$00,$06,$f2,$0a
; $6e90e movea.l $1c(a7), a1
 dc.l $6e90e
 dc.w 4,$2000
 dc.b $22,$6f,$00,$1c
; $6e912 adda.l #$6f09a, a1
 dc.l $6e912
 dc.w 6,$2000
 dc.b $d3,$fc,$00,$06,$f0,$9a
; $6e918 movea.l $24(a7), a2
 dc.l $6e918
 dc.w 4,$2000
 dc.b $24,$6f,$00,$24
; $6e91c adda.l #$6f082, a2
 dc.l $6e91c
 dc.w 6,$2000
 dc.b $d5,$fc,$00,$06,$f0,$82
; $6e922 move.l (a1), d0
 dc.l $6e922
 dc.w 2,$2000
 dc.b $20,$11
; $6e924 move.l (a2), d1
 dc.l $6e924
 dc.w 2,$2000
 dc.b $22,$12
; $6e926 jsr $29500.l
 dc.l $6e926
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6e92c move.l #$3b9, d1
 dc.l $6e92c
 dc.w 6,$2000
 dc.b $22,$3c,$00,$00,$03,$b9
; $6e932 jsr $293d0.l
 dc.l $6e932
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6e938 move.w d0, (a0)
 dc.l $6e938
 dc.w 2,$2000
 dc.b $30,$80
; $6e93a addq.l #$1, -$4(a6)
 dc.l $6e93a
 dc.w 4,$2000
 dc.b $52,$ae,$ff,$fc
; $6ea6c jsr $293d0.l
 dc.l $6ea6c
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6ea72 move.l $8(a7), d1
 dc.l $6ea72
 dc.w 4,$2000
 dc.b $22,$2f,$00,$08
; $6ea76 jsr $29500.l
 dc.l $6ea76
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6ea7c move.l #$10e, d1
 dc.l $6ea7c
 dc.w 6,$2000
 dc.b $22,$3c,$00,$00,$01,$0e
; $6ea82 jsr $293d0.l
 dc.l $6ea82
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6ea88 move.l $8(a7), d1
 dc.l $6ea88
 dc.w 4,$2000
 dc.b $22,$2f,$00,$08
; $6ea8c jsr $29500.l
 dc.l $6ea8c
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$95,$00
; $6ea92 move.l #$131, d1
 dc.l $6ea92
 dc.w 6,$2000
 dc.b $22,$3c,$00,$00,$01,$31
; $6ea98 jsr $293d0.l
 dc.l $6ea98
 dc.w 6,$2000
 dc.b $4e,$b9,$00,$02,$93,$d0
; $6ea9e move.l d0, $6f0f0.l
 dc.l $6ea9e
 dc.w 6,$2000
 dc.b $23,$c0,$00,$06,$f0,$f0
; $6eaa4 move.l #$3fffff, d0
 dc.l $6eaa4
 dc.w 6,$2000
 dc.b $20,$3c,$00,$3f,$ff,$ff
; $6eaaa sub.l $66c3e.l, d0
 dc.l $6eaaa
 dc.w 6,$2000
 dc.b $90,$b9,$00,$06,$6c,$3e
 endc
 dc.l 0
 endc
