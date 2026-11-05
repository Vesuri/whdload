; Ferrari Formula One: candidate exact-output 68020 square-root helper.
; Not installed by the slave. The native routine searches a bounded 0..1023
; result. Replace only its repeated squaring with a table; retain its search,
; upper-word behavior, D0-D3 outputs and CCR, including early perfect squares.
; The scaled word index is a 68020 instruction. Other registers are untouched.
FF1SquareRoot020:
        move.w  #512,d2
        move.w  #256,d3
        move.l  4(sp),d0
.loop:  move.l  FF1Squares(pc,d2.w*4),d1
        cmp.l   d1,d0
        bls.b   .lower
        add.w   d3,d2
        bra.b   .check
.lower: beq.b   .done
        sub.w   d3,d2
.check: tst.w   d3
        bne.b   .halve
        cmp.l   d1,d0
        bhi.b   .done
        subq.l  #1,d2
        bra.b   .done
.halve: lsr.w   #1,d3
        bra.b   .loop
.done:  move.w  d2,d0
        rts
FF1Squares:
FF1SquareValue set 0
        rept 1024
        dc.l FF1SquareValue*FF1SquareValue
FF1SquareValue set FF1SquareValue+1
        endr

; Exact floor square root over the full unsigned 32-bit input domain.
; D0.l input/result (0..65535); all other registers preserved, CCR scratch.
; Default implementation is 68000-safe; FF1_HELPERS_020 selects the 020 seed
; path. Neither implementation alters the native bounded helper above.
        ifd FF1_HELPERS_020
; A shared 1024-word table stores floor(sqrt(k)*2048). U32 uses exact
; lookup below 1024, otherwise an upper bucket seed and one Newton step.
; U64 normalizes to [2^62,2^64), interpolates a 32-bit seed and adds 131072
; before one unsigned Newton step. Interpolation error is < 69633 normalized
; root units, so this bias guarantees an upper seed. Full-width square checks
; then correct integer rounding; no approximate result reaches the caller.
FF1SquareRootU32:
        cmpi.l  #1024,d0
        bhs.b   .wide
        ; The same seed table gives exact small roots without division.
        move.w  FF1RootSeeds(pc,d0.w*2),d0
        lsr.l   #8,d0
        lsr.l   #3,d0
        rts
.wide:
        movem.l d1-d4,-(sp)
        move.l  d0,d4
        beq.b   .done
        bfffo   d0{0:32},d3
        andi.l  #30,d3
        lsl.l   d3,d0
        move.l  d0,d1
        moveq   #22,d2
        lsr.l   d2,d1
        move.l  #65536,d2
        cmpi.w  #1023,d1
        beq.b   .upper
        moveq   #0,d2
        move.w  FF1RootSeeds+2(pc,d1.w*2),d2
.upper:
        ; Upper bucket root is within 65 units in the normalized U32 domain.
        lsr.l   #1,d3
        beq.b   .divide
        lsr.l   d3,d2
        addq.l  #1,d2
.divide:
        move.l  d4,d0
        divu.l  d2,d0
        add.l   d2,d0
        lsr.l   #1,d0
        move.l  d0,d2
.correct:
        mulu.w  d0,d0
        cmp.l   d4,d0
        bls.b   .answer
        subq.l  #1,d2
        move.l  d2,d0
        bra.b   .correct
.answer:
        move.l  d2,d0
.done:
        movem.l (sp)+,d1-d4
        rts
FF1SquareRootU64:
        movem.l d1-d7,-(sp)
        move.l  d1,d6
        move.l  d0,d7
        move.l  d1,d2
        or.l    d0,d2
        beq.w   .zero
        moveq   #0,d3
        tst.l   d1
        bne.b   .high
        move.l  d0,d1
        moveq   #0,d0
        moveq   #16,d3
.high:
        bfffo   d1{0:32},d4
        andi.l  #30,d4
        beq.b   .seed
        moveq   #32,d5
        sub.l   d4,d5
        move.l  d0,d2
        lsr.l   d5,d2
        lsl.l   d4,d1
        or.l    d2,d1
        ; Only normalized bits 63..38 are needed for seed interpolation.
        lsr.l   #1,d4
        add.l   d4,d3
.seed:
        move.l  d1,d2
        moveq   #22,d4
        lsr.l   d4,d2
        moveq   #0,d5
        move.w  FF1RootSeeds(pc,d2.w*2),d5
        move.l  #65536,d4
        cmpi.w  #1023,d2
        beq.b   .upper
        moveq   #0,d4
        move.w  FF1RootSeeds+2(pc,d2.w*2),d4
.upper:
        sub.l   d5,d4
        moveq   #6,d2
        lsr.l   d2,d1
        andi.l  #$ffff,d1
        mulu.w  d4,d1
        swap    d5
        add.l   d1,d5
        addi.l  #$20000,d5
        bcc.b   .scale
        moveq   #-1,d5
.scale:
        tst.l   d3
        beq.b   .divide
        lsr.l   d3,d5
        addq.l  #1,d5
.divide:
        ; Only the saturated maximum seed can have high dividend >= seed.
        cmp.l   d5,d6
        bhs.b   .maximum
        move.l  d6,d1
        move.l  d7,d0
        divu.l  d5,d1:d0
        add.l   d5,d0
        roxr.l  #1,d0
        move.l  d0,d2
.correct:
        move.l  d2,d0
        mulu.l  d2,d1:d0
        cmp.l   d6,d1
        bhi.b   .decrement
        blo.b   .answer
        cmp.l   d7,d0
        bls.b   .answer
.decrement:
        subq.l  #1,d2
        bra.b   .correct
.answer:
        move.l  d2,d0
        bra.b   .done
.maximum:
        moveq   #-1,d0
        bra.b   .done
.zero:
        moveq   #0,d0
.done:
        movem.l (sp)+,d1-d7
        rts
FF1RootSeeds:
; Entry k = isqrt(k << 22), k=0..1023. The endpoint k=1024 is
; exactly 65536 and handled in code. Integer generation avoids rounding.
        dc.w $0000,$0800,$0b50,$0ddb,$1000,$11e3,$1398,$152a
        dc.w $16a0,$1800,$194c,$1a88,$1bb6,$1cd8,$1dee,$1efb
        dc.w $2000,$20fc,$21f0,$22df,$23c6,$24a9,$2585,$265d
        dc.w $2731,$2800,$28ca,$2991,$2a54,$2b14,$2bd1,$2c8a
        dc.w $2d41,$2df4,$2ea5,$2f54,$3000,$30a9,$3150,$31f5
        dc.w $3298,$3339,$33d8,$3475,$3510,$35aa,$3642,$36d8
        dc.w $376c,$3800,$3891,$3921,$39b0,$3a3d,$3ac9,$3b54
        dc.w $3bdd,$3c66,$3ced,$3d72,$3df7,$3e7b,$3efd,$3f7f
        dc.w $4000,$407f,$40fe,$417b,$41f8,$4273,$42ee,$4368
        dc.w $43e1,$445a,$44d1,$4548,$45be,$4633,$46a7,$471b
        dc.w $478d,$4800,$4871,$48e2,$4952,$49c1,$4a30,$4a9e
        dc.w $4b0b,$4b78,$4be5,$4c50,$4cbb,$4d26,$4d90,$4df9
        dc.w $4e62,$4eca,$4f32,$4f99,$5000,$5066,$50cb,$5130
        dc.w $5195,$51f9,$525d,$52c0,$5323,$5385,$53e7,$5449
        dc.w $54a9,$550a,$556a,$55ca,$5629,$5688,$56e6,$5745
        dc.w $57a2,$5800,$585c,$58b9,$5915,$5971,$59cc,$5a27
        dc.w $5a82,$5adc,$5b36,$5b90,$5be9,$5c42,$5c9b,$5cf3
        dc.w $5d4b,$5da3,$5dfa,$5e51,$5ea8,$5efe,$5f54,$5faa
        dc.w $6000,$6055,$60aa,$60fe,$6152,$61a7,$61fa,$624e
        dc.w $62a1,$62f4,$6347,$6399,$63eb,$643d,$648e,$64e0
        dc.w $6531,$6582,$65d2,$6623,$6673,$66c3,$6712,$6761
        dc.w $67b1,$6800,$684e,$689d,$68eb,$6939,$6986,$69d4
        dc.w $6a21,$6a6e,$6abb,$6b08,$6b54,$6ba1,$6bed,$6c38
        dc.w $6c84,$6ccf,$6d1a,$6d65,$6db0,$6dfb,$6e45,$6e8f
        dc.w $6ed9,$6f23,$6f6d,$6fb6,$7000,$7049,$7091,$70da
        dc.w $7123,$716b,$71b3,$71fb,$7243,$728a,$72d2,$7319
        dc.w $7360,$73a7,$73ee,$7434,$747b,$74c1,$7507,$754d
        dc.w $7593,$75d8,$761e,$7663,$76a8,$76ed,$7732,$7777
        dc.w $77bb,$7800,$7844,$7888,$78cc,$790f,$7953,$7996
        dc.w $79da,$7a1d,$7a60,$7aa3,$7ae5,$7b28,$7b6b,$7bad
        dc.w $7bef,$7c31,$7c73,$7cb5,$7cf6,$7d38,$7d79,$7dba
        dc.w $7dfb,$7e3c,$7e7d,$7ebe,$7efe,$7f3f,$7f7f,$7fbf
        dc.w $8000,$803f,$807f,$80bf,$80ff,$813e,$817d,$81bc
        dc.w $81fc,$823b,$8279,$82b8,$82f7,$8335,$8374,$83b2
        dc.w $83f0,$842e,$846c,$84aa,$84e7,$8525,$8562,$85a0
        dc.w $85dd,$861a,$8657,$8694,$86d1,$870e,$874a,$8787
        dc.w $87c3,$8800,$883c,$8878,$88b4,$88f0,$892b,$8967
        dc.w $89a3,$89de,$8a19,$8a55,$8a90,$8acb,$8b06,$8b41
        dc.w $8b7c,$8bb6,$8bf1,$8c2b,$8c66,$8ca0,$8cda,$8d14
        dc.w $8d4e,$8d88,$8dc2,$8dfc,$8e36,$8e6f,$8ea9,$8ee2
        dc.w $8f1b,$8f54,$8f8e,$8fc7,$9000,$9038,$9071,$90aa
        dc.w $90e2,$911b,$9153,$918c,$91c4,$91fc,$9234,$926c
        dc.w $92a4,$92dc,$9314,$934b,$9383,$93ba,$93f2,$9429
        dc.w $9460,$9497,$94cf,$9506,$953c,$9573,$95aa,$95e1
        dc.w $9617,$964e,$9684,$96bb,$96f1,$9727,$975d,$9794
        dc.w $97ca,$9800,$9835,$986b,$98a1,$98d6,$990c,$9942
        dc.w $9977,$99ac,$99e2,$9a17,$9a4c,$9a81,$9ab6,$9aeb
        dc.w $9b20,$9b54,$9b89,$9bbe,$9bf2,$9c27,$9c5b,$9c90
        dc.w $9cc4,$9cf8,$9d2c,$9d60,$9d94,$9dc8,$9dfc,$9e30
        dc.w $9e64,$9e98,$9ecb,$9eff,$9f32,$9f66,$9f99,$9fcc
        dc.w $a000,$a033,$a066,$a099,$a0cc,$a0ff,$a132,$a164
        dc.w $a197,$a1ca,$a1fc,$a22f,$a261,$a294,$a2c6,$a2f8
        dc.w $a32b,$a35d,$a38f,$a3c1,$a3f3,$a425,$a457,$a489
        dc.w $a4ba,$a4ec,$a51e,$a54f,$a581,$a5b2,$a5e4,$a615
        dc.w $a646,$a678,$a6a9,$a6da,$a70b,$a73c,$a76d,$a79e
        dc.w $a7cf,$a800,$a830,$a861,$a892,$a8c2,$a8f3,$a923
        dc.w $a953,$a984,$a9b4,$a9e4,$aa15,$aa45,$aa75,$aaa5
        dc.w $aad5,$ab05,$ab35,$ab64,$ab94,$abc4,$abf4,$ac23
        dc.w $ac53,$ac82,$acb2,$ace1,$ad11,$ad40,$ad6f,$ad9e
        dc.w $adcd,$adfd,$ae2c,$ae5b,$ae8a,$aeb8,$aee7,$af16
        dc.w $af45,$af74,$afa2,$afd1,$b000,$b02e,$b05c,$b08b
        dc.w $b0b9,$b0e8,$b116,$b144,$b172,$b1a0,$b1cf,$b1fd
        dc.w $b22b,$b259,$b286,$b2b4,$b2e2,$b310,$b33e,$b36b
        dc.w $b399,$b3c7,$b3f4,$b422,$b44f,$b47c,$b4aa,$b4d7
        dc.w $b504,$b532,$b55f,$b58c,$b5b9,$b5e6,$b613,$b640
        dc.w $b66d,$b69a,$b6c7,$b6f4,$b720,$b74d,$b77a,$b7a6
        dc.w $b7d3,$b800,$b82c,$b858,$b885,$b8b1,$b8de,$b90a
        dc.w $b936,$b962,$b98f,$b9bb,$b9e7,$ba13,$ba3f,$ba6b
        dc.w $ba97,$bac3,$baee,$bb1a,$bb46,$bb72,$bb9d,$bbc9
        dc.w $bbf5,$bc20,$bc4c,$bc77,$bca3,$bcce,$bcf9,$bd25
        dc.w $bd50,$bd7b,$bda6,$bdd2,$bdfd,$be28,$be53,$be7e
        dc.w $bea9,$bed4,$beff,$bf2a,$bf55,$bf7f,$bfaa,$bfd5
        dc.w $c000,$c02a,$c055,$c07f,$c0aa,$c0d4,$c0ff,$c129
        dc.w $c154,$c17e,$c1a8,$c1d3,$c1fd,$c227,$c251,$c27b
        dc.w $c2a5,$c2d0,$c2fa,$c324,$c34e,$c377,$c3a1,$c3cb
        dc.w $c3f5,$c41f,$c449,$c472,$c49c,$c4c6,$c4ef,$c519
        dc.w $c542,$c56c,$c595,$c5bf,$c5e8,$c612,$c63b,$c664
        dc.w $c68e,$c6b7,$c6e0,$c709,$c732,$c75b,$c784,$c7ae
        dc.w $c7d7,$c800,$c828,$c851,$c87a,$c8a3,$c8cc,$c8f5
        dc.w $c91d,$c946,$c96f,$c997,$c9c0,$c9e9,$ca11,$ca3a
        dc.w $ca62,$ca8b,$cab3,$cadc,$cb04,$cb2c,$cb55,$cb7d
        dc.w $cba5,$cbcd,$cbf5,$cc1e,$cc46,$cc6e,$cc96,$ccbe
        dc.w $cce6,$cd0e,$cd36,$cd5e,$cd86,$cdad,$cdd5,$cdfd
        dc.w $ce25,$ce4c,$ce74,$ce9c,$cec3,$ceeb,$cf13,$cf3a
        dc.w $cf62,$cf89,$cfb1,$cfd8,$d000,$d027,$d04e,$d076
        dc.w $d09d,$d0c4,$d0eb,$d112,$d13a,$d161,$d188,$d1af
        dc.w $d1d6,$d1fd,$d224,$d24b,$d272,$d299,$d2c0,$d2e7
        dc.w $d30d,$d334,$d35b,$d382,$d3a8,$d3cf,$d3f6,$d41c
        dc.w $d443,$d46a,$d490,$d4b7,$d4dd,$d504,$d52a,$d551
        dc.w $d577,$d59d,$d5c4,$d5ea,$d610,$d637,$d65d,$d683
        dc.w $d6a9,$d6cf,$d6f5,$d71b,$d742,$d768,$d78e,$d7b4
        dc.w $d7da,$d800,$d825,$d84b,$d871,$d897,$d8bd,$d8e3
        dc.w $d908,$d92e,$d954,$d979,$d99f,$d9c5,$d9ea,$da10
        dc.w $da35,$da5b,$da81,$daa6,$dacb,$daf1,$db16,$db3c
        dc.w $db61,$db86,$dbac,$dbd1,$dbf6,$dc1b,$dc41,$dc66
        dc.w $dc8b,$dcb0,$dcd5,$dcfa,$dd1f,$dd44,$dd69,$dd8e
        dc.w $ddb3,$ddd8,$ddfd,$de22,$de47,$de6c,$de91,$deb5
        dc.w $deda,$deff,$df24,$df48,$df6d,$df92,$dfb6,$dfdb
        dc.w $e000,$e024,$e049,$e06d,$e092,$e0b6,$e0db,$e0ff
        dc.w $e123,$e148,$e16c,$e190,$e1b5,$e1d9,$e1fd,$e221
        dc.w $e246,$e26a,$e28e,$e2b2,$e2d6,$e2fa,$e31f,$e343
        dc.w $e367,$e38b,$e3af,$e3d3,$e3f7,$e41a,$e43e,$e462
        dc.w $e486,$e4aa,$e4ce,$e4f2,$e515,$e539,$e55d,$e580
        dc.w $e5a4,$e5c8,$e5eb,$e60f,$e633,$e656,$e67a,$e69d
        dc.w $e6c1,$e6e4,$e708,$e72b,$e74f,$e772,$e795,$e7b9
        dc.w $e7dc,$e800,$e823,$e846,$e869,$e88d,$e8b0,$e8d3
        dc.w $e8f6,$e919,$e93c,$e960,$e983,$e9a6,$e9c9,$e9ec
        dc.w $ea0f,$ea32,$ea55,$ea78,$ea9b,$eabe,$eae0,$eb03
        dc.w $eb26,$eb49,$eb6c,$eb8f,$ebb1,$ebd4,$ebf7,$ec1a
        dc.w $ec3c,$ec5f,$ec82,$eca4,$ecc7,$ece9,$ed0c,$ed2e
        dc.w $ed51,$ed74,$ed96,$edb8,$eddb,$edfd,$ee20,$ee42
        dc.w $ee65,$ee87,$eea9,$eecc,$eeee,$ef10,$ef32,$ef55
        dc.w $ef77,$ef99,$efbb,$efdd,$f000,$f022,$f044,$f066
        dc.w $f088,$f0aa,$f0cc,$f0ee,$f110,$f132,$f154,$f176
        dc.w $f198,$f1ba,$f1dc,$f1fd,$f21f,$f241,$f263,$f285
        dc.w $f2a6,$f2c8,$f2ea,$f30c,$f32d,$f34f,$f371,$f392
        dc.w $f3b4,$f3d6,$f3f7,$f419,$f43a,$f45c,$f47d,$f49f
        dc.w $f4c0,$f4e2,$f503,$f525,$f546,$f567,$f589,$f5aa
        dc.w $f5cb,$f5ed,$f60e,$f62f,$f651,$f672,$f693,$f6b4
        dc.w $f6d6,$f6f7,$f718,$f739,$f75a,$f77b,$f79c,$f7bd
        dc.w $f7de,$f800,$f821,$f842,$f863,$f883,$f8a4,$f8c5
        dc.w $f8e6,$f907,$f928,$f949,$f96a,$f98b,$f9ab,$f9cc
        dc.w $f9ed,$fa0e,$fa2f,$fa4f,$fa70,$fa91,$fab1,$fad2
        dc.w $faf3,$fb13,$fb34,$fb55,$fb75,$fb96,$fbb6,$fbd7
        dc.w $fbf7,$fc18,$fc38,$fc59,$fc79,$fc9a,$fcba,$fcdb
        dc.w $fcfb,$fd1b,$fd3c,$fd5c,$fd7c,$fd9d,$fdbd,$fddd
        dc.w $fdfd,$fe1e,$fe3e,$fe5e,$fe7e,$fe9f,$febf,$fedf
        dc.w $feff,$ff1f,$ff3f,$ff5f,$ff7f,$ff9f,$ffbf,$ffdf
        else
FF1SquareRootU32:
        movem.l d1-d4,-(sp)
        move.l  d0,d1
        moveq   #0,d2
        move.l  #32768,d3
.loop:
        move.l  d2,d4
        or.l    d3,d4
        move.l  d4,d0
        mulu.w  d0,d0
        cmp.l   d1,d0
        bhi.b   .next
        move.l  d4,d2
.next:
        lsr.l   #1,d3
        bne.b   .loop
        move.l  d2,d0
        movem.l (sp)+,d1-d4
        rts

; Exact floor sqrt of unsigned D1:D0, result D0.l (0..$ffffffff).
; Other registers preserved; CCR scratch. 68020+ full-product multiplication.
FF1SquareRootU64:
        movem.l d1-d7,-(sp)
        move.l  d1,d6
        move.l  d0,d7
        moveq   #0,d2
        move.l  #$80000000,d3
.loop:
        move.l  d2,d4
        or.l    d3,d4
        move.l  d4,d0
        mulu.l  d4,d5:d0
        cmp.l   d6,d5
        bhi.b   .next
        blo.b   .accept
        cmp.l   d7,d0
        bhi.b   .next
.accept:
        move.l  d4,d2
.next:
        lsr.l   #1,d3
        bne.b   .loop
        move.l  d2,d0
        movem.l (sp)+,d1-d7
        rts
        endc
