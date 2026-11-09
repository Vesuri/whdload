;*---------------------------------------------------------------------------
; Enhanced framerate (CUSTOM2=1 only): rendering (plan step 4, docs/open-work.md).
;
; bh:16bca, the point transform, cull and screen position (C entry: x, y, z longs on the
; stack; ~17 calls per frame per object).  The arithmetic of Their Finest Hour's bob:2f4ae
; and its projection, in one routine that kept every difference, sign and partial sum in
; data-hunk globals.  This version keeps them in registers, with the same arithmetic and
; therefore the same results.  Of its globals only 568, 570, 572 and 576 are read outside
; it (bh:7248..7590, bh:16ab4); 560..564 are written before they are read by bh:167ba and
; by bh:16f6e, its perspective divide, which is still called (it reads 544 and 566 and may
; set 576).  On a 68020, 68030 or 68040 each of the eight matrix terms is one mulu.l (the
; 64-bit product's bits 16-47 equal the two mulu.w halves' sum, which cannot carry out of 32
; bits); the 68060 has no 64-bit mulu.l in hardware and takes the 68000 version.
;
;   x, y, z     the point minus the camera (460/464/468), each as sign and magnitude
;   T(d, m)     floor(|d| * m / 65536), m the matrix magnitude, negated by the signs
;   depth  544  T(x,428) + T(y,434) + T(z,426)    culled if < 0 or >= $e0000 (582 = 0)
;   h      536  T(x,420) + T(y,422)               culled if |h| >= $e0000
;   v      540  T(x,430) + T(y,432) + T(z,424)
;   h', v'      bh:16f6e of h and v (v' - 2 when 582 = 0 and 5830 set)
;   568         R(h',454) + R(v',452) + (-6062)/2, R(a,m) = round(|a| * m / 65536) signed
;   570         S(h',452,-142(a4)) + S(v',454,233) + (-6052)/2 - 16
;   576         the depth's shade from the tables 5552/5809, or -1 when culled
; The matrix terms' sign rules (which sign pairs negate) are the original's, term by term.
;
; bh:160ba and the loop body bh:15ea2..15ece of bh:15cb6, the sky and sea fill of a row
; that the horizon crosses: D2>>3 longs of D0 (move.l/dbf), the split long from the
; table at A3 (D2 & 7), then D6 - D2>>3 - 1 longs of D1.  Here each run is a jump into
; 32 move.l, the dbf gone; longer runs (none in a 32-long row) take the original loop.
; The registers are left as the original's (D3.w its last count, D5 = D2>>3).
;
; bh:161ec draws a run-length image into the chunky buffer -6066(a4) (C entry: the data,
; x, row; 4-bit pixels, the left one in the high nibble).  Per code byte: below $fd a
; colour c and a length byte (n+1 pixels), $fd a skip of n+1 pixels, $fe the next row
; (the row offsets at -4642(a4)), $ff the end.  The original merged every pixel into its
; byte: and.b #$0f + or.b c<<4 for a left pixel, and.b #$f0 + or.b c for a right one.  A
; byte whose two pixels are both in the run therefore ends as c<<4 | c whatever it held,
; so here the run's whole bytes are one move.b each and only an odd first (right) or
; last (left) pixel is merged, with the original's operations.
;---------------------------------------------------------------------------

; < A2: resload, D7: seglist (BPTR); after timing.s's own list
render_patch	move.l	d7,d0
		lsl.l	#2,d0
		addq.l	#4,d0			;hunk 0 starts after the BPTR link
		add.l	#$16f6e,d0
		lea	(xf_16f6e,pc),a0
		move.l	d0,(a0)
		lea	(_pl_render,pc),a0
		move.l	(_attnflags,pc),d0
		btst	#AFB_68020,d0
		beq.b	.patch
		btst	#7,d0			;AFB_68060 (not in 1.3's includes): its 64-bit mulu.l traps
		bne.b	.patch
		lea	(_pl_render20,pc),a0
.patch		move.l	d7,a1
		jmp	(resload_PatchSeg,a2)

_pl_render	PL_START
		PL_P	$16bca,xform
		PL_NEXT	_pl_fill

_pl_render20	PL_START
		PL_P	$16bca,xform20
		PL_NEXT	_pl_fill

_pl_fill	PL_START
		PL_PS	$15ea2,fill_a0		;move.w (a0),d2 and the row, to bh:15ece
		PL_S	$15ea8,$15ece-$15ea8
		PL_P	$160ba,fill_row
		PL_P	$161ec,overlay
		PL_END

xf_16f6e	dc.l	0			;bh:16f6e

; the point minus the camera: \1 < the point, > |difference|; \2 sign word (0 or $8000)
XF_DIFF	MACRO	;register, camera offset, sign register
		moveq	#0,\3
		sub.l	(\2,a4),\1
		bpl.b	.p\@
		neg.l	\1
		move.w	#$8000,\3
.p\@
		ENDM

; D4 = floor(|d| * m / 65536) with the term's sign: negated unless the signs' eor is zero
; (XF_NEQ: the original's beq over its neg.l) or nonzero (XF_NNE: its bne).  D3 scratch.
XF_T	MACRO	;magnitude register, matrix offset, sign register, matrix sign offset, beq/bne
		move.w	\1,d3
		mulu.w	(\2,a4),d3
		clr.w	d3
		swap	d3
		move.l	\1,d4
		swap	d4
		mulu.w	(\2,a4),d4
		add.l	d3,d4
		move.w	(\4,a4),d3
		eor.w	\3,d3
		\5.b	.s\@
		neg.l	d4
.s\@
		ENDM

XF_T20	MACRO	;as XF_T: one mulu.l, bits 16-47 of the product
		moveq	#0,d4
		move.w	(\2,a4),d4
		mulu.l	\1,d3:d4
		move.w	d3,d4
		swap	d4
		move.w	(\4,a4),d3
		eor.w	\3,d3
		\5.b	.s\@
		neg.l	d4
.s\@
		ENDM

; The body, for both CPUs.  \1: XF_T or XF_T20.  Registers: D0-D2 |x|, |y|, |z|, D5-D7
; their signs, A0 depth, A1 h, A2 v.
XF_BODY	MACRO
		move.l	a5,(6626,a4)		;as the original's frame
		movem.l	d0-a3/a5/a6,-(a7)
		clr.w	(576,a4)
		move.l	(4+56,a7),d0
		XF_DIFF	d0,460,d5
		move.l	(8+56,a7),d1
		XF_DIFF	d1,464,d6
		move.l	(12+56,a7),d2
		XF_DIFF	d2,468,d7
	; depth
		\1	d0,428,d5,444,beq
		move.l	d4,a0
		\1	d1,434,d6,450,beq
		add.l	d4,a0
		\1	d2,426,d7,442,beq
		add.l	d4,a0
		tst.w	(582,a4)
		bne.b	.h\@
		move.l	a0,d4
		bmi.w	xf_cull
		cmp.l	#$e0000,d4
		bhs.w	xf_cull
.h\@	; h
		\1	d0,420,d5,436,beq
		move.l	d4,a1
		\1	d1,422,d6,438,bne
		add.l	d4,a1
		move.l	a1,d4
		bpl.b	.ha\@
		neg.l	d4
.ha\@		cmp.l	#$e0000,d4
		bhs.w	xf_cull
	; v
		\1	d0,430,d5,446,bne
		move.l	d4,a2
		\1	d1,432,d6,448,bne
		add.l	d4,a2
		\1	d2,424,d7,440,beq
		add.l	d4,a2
		bra.w	xf_screen
		ENDM

xform		XF_BODY	XF_T
	MACHINE	68020
xform20		XF_BODY	XF_T20
	MACHINE	68000

; A0 depth, A1 h, A2 v: the perspective divide, the screen position and the depth's shade
xf_screen	move.l	a0,(544,a4)		;read by bh:16f6e
		move.l	a0,(572,a4)
		move.w	#160,(566,a4)
		move.l	(xf_16f6e,pc),a3
		move.l	a1,d0
		jsr	(a3)			;D0-D3
		move.w	d0,d6			;h'
		move.l	a2,d0
		jsr	(a3)
		tst.w	(582,a4)
		bne.b	.v
		tst.w	(5830,a4)
		beq.b	.v
		subq.w	#2,d0
.v		move.w	d0,d2			;v'
		move.w	d6,d0
	; D0 |h'|, D2 |v'|; D6, D7 their signs
		move.w	d0,d6
		and.w	#$8000,d6
		beq.b	.hp
		neg.w	d0
.hp		move.w	d2,d7
		and.w	#$8000,d7
		beq.b	.vp
		neg.w	d2
.vp	; 568
		move.w	d0,d1
		mulu.w	(454,a4),d1
		add.l	#$8000,d1
		swap	d1
		move.w	(458,a4),d4
		eor.w	d6,d4
		beq.b	.n1
		neg.w	d1
.n1		move.w	d1,d5
		move.w	d2,d1
		mulu.w	(452,a4),d1
		add.l	#$8000,d1
		swap	d1
		move.w	(456,a4),d4
		eor.w	d7,d4
		bne.b	.n2
		neg.w	d1
.n2		add.w	d1,d5
		move.w	(-6062,a4),d1
		lsr.w	#1,d1
		add.w	d1,d5
		move.w	d5,(568,a4)
		tst.w	(582,a4)
		bne.b	.s570
		move.w	d5,d4
		bpl.b	.c1
		neg.w	d5
		cmp.w	(-6058,a4),d5
		bhs.w	xf_cull
		bra.b	.s570
.c1		move.w	(-6062,a4),d4
		lsr.w	#1,d4
		add.w	(-6062,a4),d4
		cmp.w	d4,d5
		bhs.w	xf_cull
.s570		move.w	d0,d1
		mulu.w	(452,a4),d1
		add.l	#$8000,d1
		swap	d1
		mulu.w	(-142,a4),d1
		add.l	#128,d1
		lsr.l	#8,d1
		move.w	(456,a4),d4
		eor.w	d6,d4
		beq.b	.n3
		neg.w	d1
.n3		move.w	d1,d5
		move.w	d2,d1
		mulu.w	(454,a4),d1
		add.l	#$8000,d1
		swap	d1
		mulu.w	#233,d1
		add.l	#128,d1
		lsr.l	#8,d1
		move.w	(458,a4),d4
		eor.w	d7,d4
		beq.b	.n4
		neg.w	d1
.n4		add.w	d1,d5
		move.w	(-6052,a4),d1
		lsr.w	#1,d1
		add.w	d1,d5
		sub.w	#16,d5
		move.w	d5,(570,a4)
		move.w	d5,d4
		bpl.b	.c2
		neg.w	d5
		cmp.w	d1,d5
		bhs.w	xf_cull
		bra.b	.shade
.c2		add.w	(-6052,a4),d1
		cmp.w	d1,d5
		bhs.w	xf_cull
.shade		tst.w	(576,a4)		;bh:16f6e's overflow
		bmi.b	xf_done
		move.l	a0,d0
		move.l	d0,d1
		swap	d1
		tst.w	d1
		bne.b	.far
		lea	(5552,a4),a6
		swap	d1
		lsr.w	#8,d1
		moveq	#0,d5
		move.b	(0,a6,d1.w),d5
		move.w	d5,d4
		sub.b	(1,a6,d1.w),d4
		lsr.w	#8,d0
		mulu.w	d0,d4
		lsr.w	#8,d4
		sub.w	d4,d5
		bra.b	.store
.far		lea	(5809,a4),a6
		moveq	#0,d5
		move.b	(-1,a6,d1.w),d5
		move.w	d5,d4
		sub.b	(1,a6,d1.w),d4
		mulu.w	d0,d4
		swap	d4
		sub.w	d4,d5
.store		lsl.w	#2,d5
		move.w	d5,(576,a4)
		bra.b	xf_done
xf_cull		move.w	#-1,(576,a4)
xf_done		movem.l	(a7)+,d0-a3/a5/a6
		rts

FILL_MAX	= 32			;longs in the unrolled runs (a row: -6054(a4) = 32)

; bh:160ba, a row; then the next row (bh:160e4)
fill_row	bsr.b	fill_core
		tst.w	(-5962,a4)
		bne.b	.r
		suba.w	(-6056,a4),a1
		suba.w	(-6056,a4),a1
.r		rts

; bh:15ea2, the same row in bh:15cb6's loop
fill_a0		move.w	(a0),d2
; < D2 split x, D0/D1 left/right long, A3 split longs, A1 row, D6 longs per row
fill_core	move.w	d2,d3
		lsr.w	#3,d3
		move.w	d3,d5
		cmp.w	#FILL_MAX,d3
		bhi.b	.longl
		add.w	d3,d3
		neg.w	d3
		jmp	(.lend,pc,d3.w)
.longl		bra.b	.ld			;as the original
.ll		move.l	d0,(a1)+
.ld		dbf	d3,.ll
		bra.b	.lend
		REPT	FILL_MAX
		move.l	d0,(a1)+
		ENDR
.lend		move.w	d2,d3
		and.w	#7,d3
		add.w	d3,d3
		add.w	d3,d3
		move.l	(0,a3,d3.w),(a1)+
		move.w	d6,d3
		sub.w	d5,d3
		subq.w	#2,d3
		bmi.b	.done			;D3.w as the original's
		cmp.w	#FILL_MAX-1,d3
		bhi.b	.longr
		add.w	d3,d3
		neg.w	d3
		jmp	(.rend-2,pc,d3.w)	;D3+1 longs
.longr
.rl		move.l	d1,(a1)+
		dbf	d3,.rl
		rts
		REPT	FILL_MAX
		move.l	d1,(a1)+
		ENDR
.rend		move.w	#-1,d3			;as the original's dbf leaves it
.done		rts

; bh:161ec
overlay		move.l	a5,(6626,a4)		;as the original's frame
		movem.l	d0-a3/a5/a6,-(a7)
		move.l	(4+56,a7),a0		;the image
		move.w	(10+56,a7),d0		;x
		move.w	(12+56,a7),d1		;row
		lea	(-4642,a4),a6
		add.w	d1,d1
		adda.w	d1,a6
		move.l	(-6066,a4),a1
		moveq	#$0f,d6
		moveq	#-16,d7			;$f0
.row		move.l	a1,a2
		adda.w	(a6),a2
		move.w	d0,d5
		lsr.w	#1,d5
		adda.w	d5,a2
		move.w	d0,d1
.next		move.b	(a0)+,d3
		cmp.b	#$fe,d3
		blo.b	.run
		bne.b	.end
		addq.l	#2,a6			;$fe: the next row
		bra.b	.row
.run		moveq	#0,d4
		move.b	(a0)+,d4
		addq.w	#1,d4			;pixels
		move.w	d1,d2
		add.w	d4,d1
		cmp.b	#$fd,d3
		beq.b	.skip
		move.b	d3,d5
		lsl.b	#4,d5			;c << 4
		lsr.w	#1,d2
		bcc.b	.even
		and.b	d7,(a2)			;a right pixel first
		or.b	d3,(a2)+
		subq.w	#1,d4
		beq.b	.next
.even		lsr.w	#1,d4			;whole bytes
		bcc.b	.whole
		and.b	d6,(0,a2,d4.w)		;and a left pixel last
		or.b	d5,(0,a2,d4.w)
.whole		or.b	d3,d5			;c << 4 | c
		bra.b	.bd
.bl		move.b	d5,(a2)+
.bd		dbf	d4,.bl
		bra.b	.next
.skip		move.w	d4,d3			;as the original
		lsr.w	#1,d3
		lsr.w	#1,d2
		bcc.b	.sk
		lsr.w	#1,d4
		bcc.b	.sk
		addq.l	#1,a2
.sk		adda.w	d3,a2
		bra.b	.next
.end		movem.l	(a7)+,d0-a3/a5/a6
		rts
