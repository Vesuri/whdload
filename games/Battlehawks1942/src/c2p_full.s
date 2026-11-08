; VERIFY-only experiment (make build BUILD=c2pfull): replace the game's delta chunky-to-planar pass
; (bh:1a2c2) with a full-frame merge c2p in the style of Mikael Kalms' c2p1x1_4_c5, to measure
; whether converting every pixel with bit exchanges beats comparing and converting only the
; changed longs (docs/c2p.md).
;
; The game's chunky buffer is 4 bits per pixel, 8 pixels per long, leftmost pixel in the
; top nibble (the original's first swap brings the high word into the low half). Kalms'
; routines take a byte per pixel and start by merging bytes into nibbles; here the nibbles
; already exist in sequential order, so the plan differs: six exchanges per 32 pixels (found
; by search, docs/c2p.md), the cheapest being the two 16-bit ones done with word moves.
; Output order: d3 = plane 0, d2 = 1, d1 = 2, d0 = 3.
;
; Called like the original: 4(sp) = new chunky frame, 8(sp) = previous one (unused: every
; long is converted). a4 = the game's small-data base. Preserves all registers.

C2P_ROWS	= -6052			;(a4).w rows
C2P_LONGS	= -6054			;(a4).w chunky longs per row (multiple of 4)
C2P_OFFSET	= -6048			;(a4).w byte offset of the view in each bitplane
C2P_PLANES	= 26224			;(a4) 4 bitplane pointers
C2P_STRIDE	= 40			;bytes per bitplane row

c2p_full:
	movem.l	d0-a6,-(sp)
	move.l	64(sp),a0
	move.w	C2P_OFFSET(a4),d0
	movem.l	C2P_PLANES(a4),a1-a3/a5
	adda.w	d0,a1
	adda.w	d0,a2
	adda.w	d0,a3
	adda.w	d0,a5
	moveq	#C2P_STRIDE,d0
	sub.w	C2P_LONGS(a4),d0	;row modulo: one byte per plane per chunky long
	move.w	d0,-(sp)
	move.w	C2P_LONGS(a4),d0
	lsr.w	#2,d0
	subq.w	#1,d0
	move.w	d0,-(sp)		;groups of 4 longs per row, -1
	move.w	C2P_ROWS(a4),-(sp)
	move.l	#$55555555,a4
	move.l	#$33333333,a6
.row:	move.w	2(sp),d7
.group:	movem.l	(a0)+,d0-d3
	swap	d1			;exchange 16 (d0,d1) (d2,d3)
	move.w	d1,d4
	move.w	d0,d1
	move.w	d4,d0
	swap	d1
	swap	d3
	move.w	d3,d4
	move.w	d2,d3
	move.w	d4,d2
	swap	d3
	swap	d2			;exchange 16 (d0,d2) (d1,d3)
	move.w	d2,d4
	move.w	d0,d2
	move.w	d4,d0
	swap	d2
	swap	d3
	move.w	d3,d4
	move.w	d1,d3
	move.w	d4,d1
	swap	d3
	move.l	#$0f0f0f0f,d6		;exchange 4 (d0,d1) (d2,d3)
	move.l	d1,d4
	move.l	d3,d5
	lsr.l	#4,d4
	lsr.l	#4,d5
	eor.l	d0,d4
	eor.l	d2,d5
	and.l	d6,d4
	and.l	d6,d5
	eor.l	d4,d0
	eor.l	d5,d2
	lsl.l	#4,d4
	lsl.l	#4,d5
	eor.l	d4,d1
	eor.l	d5,d3
	move.l	a4,d6			;exchange 1 (d0,d1) (d2,d3)
	move.l	d1,d4
	move.l	d3,d5
	lsr.l	#1,d4
	lsr.l	#1,d5
	eor.l	d0,d4
	eor.l	d2,d5
	and.l	d6,d4
	and.l	d6,d5
	eor.l	d4,d0
	eor.l	d5,d2
	add.l	d4,d4
	add.l	d5,d5
	eor.l	d4,d1
	eor.l	d5,d3
	move.l	#$00ff00ff,d6		;exchange 8 (d0,d2) (d1,d3)
	move.l	d2,d4
	move.l	d3,d5
	lsr.l	#8,d4
	lsr.l	#8,d5
	eor.l	d0,d4
	eor.l	d1,d5
	and.l	d6,d4
	and.l	d6,d5
	eor.l	d4,d0
	eor.l	d5,d1
	lsl.l	#8,d4
	lsl.l	#8,d5
	eor.l	d4,d2
	eor.l	d5,d3
	move.l	a6,d6			;exchange 2 (d0,d2) (d1,d3)
	move.l	d2,d4
	move.l	d3,d5
	lsr.l	#2,d4
	lsr.l	#2,d5
	eor.l	d0,d4
	eor.l	d1,d5
	and.l	d6,d4
	and.l	d6,d5
	eor.l	d4,d0
	eor.l	d5,d1
	lsl.l	#2,d4
	lsl.l	#2,d5
	eor.l	d4,d2
	eor.l	d5,d3
	move.l	d3,(a1)+
	move.l	d2,(a2)+
	move.l	d1,(a3)+
	move.l	d0,(a5)+
	dbf	d7,.group
	move.w	4(sp),d0
	adda.w	d0,a1
	adda.w	d0,a2
	adda.w	d0,a3
	adda.w	d0,a5
	subq.w	#1,(sp)
	bne	.row
	addq.w	#6,sp
	movem.l	(sp)+,d0-a6
	rts
