; C4-only inlining of the three measured native multiply call sites.
; Patch extents include the following overwrite of D1. That is the exact ABI
; boundary: all other registers, stack, low-32 product and XNZVC agree there.
; Nonpositive/range-miss operands retain the native multiply implementation.
FF1C4InstallMulSites:
 lea FF1C4MulSiteSignature1(pc),a0
 lea $6759a,a1
 moveq #10,d0
.check1:
 cmpm.w (a0)+,(a1)+
 bne.w C1Fault
 dbra d0,.check1
 lea FF1C4MulSiteSignature2(pc),a0
 lea $6ea2c,a1
 moveq #5,d0
.check2:
 cmpm.w (a0)+,(a1)+
 bne.w C1Fault
 dbra d0,.check2
 lea FF1C4MulSiteSignature3(pc),a0
 lea $6cd54,a1
 moveq #7,d0
.check3:
 cmpm.w (a0)+,(a1)+
 bne.w C1Fault
 dbra d0,.check3
 move.w FF1C4MulSitesControl(pc),d0
 bne.b .done
 lea FF1C4MulSite1(pc),a0
 move.w #$4ef9,$675a6
 move.l a0,$675a8
 move.l #$4e714e71,$675ac
 lea FF1C4MulSite2(pc),a0
 move.w #$4ef9,$6ea30
 move.l a0,$6ea32
 move.w #$4e71,$6ea36
 lea FF1C4MulSite3(pc),a0
 move.w #$4ef9,$6cd5c
 move.l a0,$6cd5e
 move.w #$4e71,$6cd62
.done:
 rts

FF1C4MulSite1:
 ; Native normally supplies D0=D2, signed word. Guard the full contract
 ; as well so any alternate entry retains native semantics.
 tst.l d0
 ble.b .fallback
 cmpi.l #$ffff,d0
 bhi.b .fallback
 cmp.l d2,d0
 bne.b .fallback
 tst.l d1
 ble.b .fallback
 mulu.w d1,d0
 swap d1
 mulu.w d2,d1
 swap d1
 clr.w d1
 ; This is native's final cross-product ADD, including its carry into X.
 add.l d1,d0
 bra.b .post
.fallback:
 IFD FF1_C4_MUL_SITES_TEST
 bsr.w FF1C4MulSiteOriginal
 ELSE
 jsr $29500
 ENDC
.post:
 move.l $14(sp),d1
 IFD FF1_C4_MUL_SITES_TEST
 rts
 ELSE
 jmp $675b0
 ENDC

FF1C4MulSite2:
 ; Unlike site 1, the input loaded from the local frame has no word proof.
 tst.l d0
 ble.b .fallback
 cmpi.l #$ffff,d0
 bhi.b .fallback
 tst.l d1
 ble.b .fallback
 move.l d2,-(sp)
 move.l d0,d2
 mulu.w d1,d0
 swap d1
 mulu.w d2,d1
 swap d1
 clr.w d1
 add.l d1,d0
 move.l (sp)+,d2
 bra.b .post
.fallback:
 IFD FF1_C4_MUL_SITES_TEST
 bsr.w FF1C4MulSiteOriginal
 ELSE
 jsr $29500
 ENDC
.post:
 moveq #18,d1
 IFD FF1_C4_MUL_SITES_TEST
 rts
 ELSE
 jmp $6ea38
 ENDC

FF1C4MulSite3:
 ; Native supplies a sign-extended word; keep the full range guard too.
 tst.l d0
 ble.b .fallback
 tst.l d1
 ble.b .fallback
 cmpi.l #$ffff,d1
 bhi.b .fallback
 move.l d2,-(sp)
 move.l d0,d2
 mulu.w d1,d0
 swap d2
 mulu.w d1,d2
 swap d2
 clr.w d2
 add.l d2,d0
 move.l (sp)+,d2
 ; Native B.high=0 means its final ADD uses zero and clears X, even if
 ; the earlier A.high cross-product ADD carried. D1 is dead at this boundary.
 moveq #0,d1
 add.l d1,d0
 bra.b .post
.fallback:
 IFD FF1_C4_MUL_SITES_TEST
 bsr.w FF1C4MulSiteOriginal
 ELSE
 jsr $29500
 ENDC
.post:
 moveq #19,d1
 IFD FF1_C4_MUL_SITES_TEST
 rts
 ELSE
 jmp $6cd64
 ENDC

FF1C4MulSitesControl: dc.w 1
FF1C4MulSiteSignature1:
 dc.b $34,$10,$48,$c2,$2f,$40,$00,$14,$20,$02,$22,$11,$4e,$b9,$00,$02,$95,$00,$22,$2f,$00,$14
FF1C4MulSiteSignature2:
 dc.b $20,$2e,$ff,$f8,$4e,$b9,$00,$02,$95,$00,$72,$12
FF1C4MulSiteSignature3:
 dc.b $32,$39,$00,$06,$f2,$76,$48,$c1,$4e,$b9,$00,$02,$95,$00,$72,$13
