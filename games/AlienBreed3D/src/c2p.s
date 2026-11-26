;======================================================================
; Mikael Kalms' c2p1x1_8_c5_030_2 (public domain), from Kalmalyzer/kalms-c2p commit
; d8ecf79a3325615305dd800ae7704b518e0d9dda, normal/c2p1x1_8_c5_030_2.s, as AmigaXDev
; installs it (kalms-c2p/). Changed for a slave, which is one hunk of PC-relative code:
; no exec include and no sections; smcinit and init removed (display.s sets _pixels and
; _fastbuf itself; BPLSIZE is assembled in); the variables are dc.l in the code and read
; PC-relative; _fastbuf is a pointer to the CHUNKYXMAX*CHUNKYYMAX/2 bytes of scratch
; instead of the buffer itself. The instructions are otherwise Kalms'.
;
; a0 = chunky pixels (_pixels bytes, and 4 more are read), a1 = plane 0's first byte;
; the 8 planes BPLSIZE apart. d0-d1/a0-a1 are not preserved.
;
; 2000-04-17
;
; c2p1x1_8_c5_030_2
;
; 1.22vbl [all dma off] on Bliz1230-IV@50
;
; 2000-04-17: added bplsize modifying init (smcinit)
; 1999-01-08: initial version
;
; bplsize must be less than or equal to 16kB!
;

	IFND	BPLX
BPLX	EQU	320
	ENDC
	IFND	BPLY
BPLY	EQU	256
	ENDC
	IFND	BPLSIZE
BPLSIZE	EQU	BPLX*BPLY/8
	ENDC
	IFND	CHUNKYXMAX
CHUNKYXMAX EQU	BPLX
	ENDC
	IFND	CHUNKYYMAX
CHUNKYYMAX EQU	BPLY
	ENDC

; a0	c2pscreen
; a1	bitplanes

c2p1x1_8_c5_030_2
	movem.l	d2-d7/a2-a6,-(sp)

	move.l	#$00ff00ff,a6

	add.w	#BPLSIZE,a1
c2p1x1_8_c5_030_2_smc1 EQU *-2
	add.l	c2p1x1_8_c5_030_2_scroffs(pc),a1

	movea.l	c2p1x1_8_c5_030_2_fastbuf(pc),a3

	move.l	c2p1x1_8_c5_030_2_pixels(pc),a2
	add.l	a0,a2
	cmp.l	a0,a2
	beq	.none

	addq.l	#4,a2
	move.l	a1,-(sp)

	move.l	#$f0f0f0f0,d6

	move.l	(a0)+,d2
	move.l	d2,d7
	lsl.l	#4,d7
	move.l	(a0)+,d0
	move.l	(a0)+,d3
	move.l	(a0)+,d1
	eor.l	d0,d7
	and.l	d6,d7
	eor.l	d7,d0
	lsr.l	#4,d7
	eor.l	d7,d2
	move.l	d3,d7
	lsl.l	#4,d7
	eor.l	d1,d7
	and.l	d6,d7
	eor.l	d7,d1
	move.l	d2,(a3)+
	lsr.l	#4,d7
	eor.l	d7,d3
	move.l	d3,(a3)+

	move.l	(a0)+,d4
	move.l	d4,d7
	lsl.l	#4,d7
	move.l	(a0)+,d2
	move.l	(a0)+,d5
	move.l	(a0)+,d3
	eor.l	d2,d7
	and.l	d6,d7
	eor.l	d7,d2
	lsr.l	#4,d7
	eor.l	d7,d4
	move.l	d5,d7
	lsl.l	#4,d7
	eor.l	d3,d7
	and.l	d6,d7
	eor.l	d7,d3
	move.l	d4,(a3)+
	lsr.l	#4,d7
	eor.l	d7,d5
	move.l	d5,(a3)+

	move.w	d2,d7			; Swap 16x2
	move.w	d0,d2
	swap	d2
	move.w	d2,d0
	move.w	d7,d2

	move.w	d3,d7
	move.w	d1,d3
	swap	d3
	move.w	d3,d1
	move.w	d7,d3

	bra.s	.start1
.x1
	move.l	(a0)+,d0
	move.l	(a0)+,d3
	move.l	(a0)+,d1
	move.l	d7,BPLSIZE(a1)
c2p1x1_8_c5_030_2_smc2 EQU *-2
	move.l	d2,d7
	lsl.l	#4,d7
	eor.l	d0,d7
	and.l	d6,d7
	eor.l	d7,d0
	lsr.l	#4,d7
	eor.l	d7,d2
	move.l	d3,d7
	lsl.l	#4,d7
	eor.l	d1,d7
	and.l	d6,d7
	eor.l	d7,d1
	move.l	d2,(a3)+
	lsr.l	#4,d7
	eor.l	d7,d3
	move.l	d3,(a3)+
	move.l	d5,a5

	move.l	(a0)+,d4
	move.l	d4,d7
	lsl.l	#4,d7
	move.l	(a0)+,d2
	move.l	(a0)+,d5
	move.l	(a0)+,d3
	move.l	a4,(a1)+
	eor.l	d2,d7
	and.l	d6,d7
	eor.l	d7,d2
	lsr.l	#4,d7
	eor.l	d7,d4
	move.l	d5,d7
	lsl.l	#4,d7
	eor.l	d3,d7
	and.l	d6,d7
	eor.l	d7,d3
	lsr.l	#4,d7
	eor.l	d7,d5

	move.w	d2,d7			; Swap 16x2
	move.w	d0,d2
	swap	d2
	move.w	d2,d0
	move.l	d4,(a3)+
	move.w	d7,d2

	move.w	d3,d7
	move.w	d1,d3
	move.l	d5,(a3)+
	swap	d3
	move.w	d3,d1
	move.w	d7,d3

	move.l	a5,-BPLSIZE-4(a1)
c2p1x1_8_c5_030_2_smc3 EQU *-2
.start1
	move.l	#$33333333,d5

	move.l	d2,d7			; Swap 2x2
	lsr.l	#2,d7
	eor.l	d0,d7
	and.l	d5,d7
	eor.l	d7,d0
	lsl.l	#2,d7
	eor.l	d7,d2

	move.l	d3,d7
	lsr.l	#2,d7
	eor.l	d1,d7
	and.l	d5,d7
	eor.l	d7,d1
	lsl.l	#2,d7
	eor.l	d7,d3

	move.l	a6,d4
	move.l	#$55555555,d5

	move.l	d1,d7
	lsr.l	#8,d7
	eor.l	d0,d7
	and.l	d4,d7
	eor.l	d7,d0
	lsl.l	#8,d7
	eor.l	d7,d1

	move.l	d1,d7
	lsr.l	#1,d7
	eor.l	d0,d7
	and.l	d5,d7
	eor.l	d7,d0
	move.l	d0,BPLSIZE*2(a1)
c2p1x1_8_c5_030_2_smc4 EQU *-2
	add.l	d7,d7
	eor.l	d1,d7

	move.l	d3,d1
	lsr.l	#8,d1
	eor.l	d2,d1
	and.l	d4,d1
	eor.l	d1,d2
	lsl.l	#8,d1
	eor.l	d1,d3

	move.l	d3,d1
	lsr.l	#1,d1
	eor.l	d2,d1
	and.l	d1,d5
	eor.l	d5,d2
	move.l	d2,a4
	move.l	(a0)+,d2
	add.l	d5,d5
	eor.l	d3,d5

	cmpa.l	a0,a2
	bne	.x1
.x1end
	move.l	d7,BPLSIZE(a1)
c2p1x1_8_c5_030_2_smc5 EQU *-2
	move.l	a4,(a1)+
	move.l	d5,-BPLSIZE-4(a1)
c2p1x1_8_c5_030_2_smc6 EQU *-2

	move.l	(sp)+,a1
	add.l	#BPLSIZE*4,a1
c2p1x1_8_c5_030_2_smc7 EQU *-4

	move.l	c2p1x1_8_c5_030_2_pixels(pc),d0
	lsr.l	#1,d0
	movea.l	c2p1x1_8_c5_030_2_fastbuf(pc),a0
	lea	4(a0,d0.l),a2

	move.l	(a0)+,d0
	move.l	#$55555555,d4
	move.l	#$33333333,d5
	move.l	#$00ff00ff,d6
	move.l	(a0)+,d1
	move.l	(a0)+,d2
	move.l	(a0)+,d3

	move.w	d2,d7			; Swap 16x2
	move.w	d0,d2
	swap	d2
	move.w	d2,d0
	move.w	d7,d2

	move.w	d3,d7
	move.w	d1,d3
	swap	d3
	move.w	d3,d1
	move.w	d7,d3

	move.l	d2,d7			; Swap 2x2
	lsr.l	#2,d7
	eor.l	d0,d7
	and.l	d5,d7
	eor.l	d7,d0
	lsl.l	#2,d7
	eor.l	d7,d2

	move.l	d3,d7
	lsr.l	#2,d7
	eor.l	d1,d7
	and.l	d5,d7
	eor.l	d7,d1
	lsl.l	#2,d7
	eor.l	d7,d3

	move.l	d1,d7
	lsr.l	#8,d7
	bra.s	.start2
.x2
	move.l	(a0)+,d1
	move.l	(a0)+,d2
	move.l	(a0)+,d3
	move.l	d7,BPLSIZE(a1)
c2p1x1_8_c5_030_2_smc8 EQU *-2
	move.w	d2,d7			; Swap 16x2
	move.w	d0,d2
	swap	d2
	move.w	d2,d0
	move.w	d7,d2

	move.w	d3,d7
	move.w	d1,d3
	swap	d3
	move.w	d3,d1
	move.w	d7,d3

	move.l	d2,d7			; Swap 2x2
	lsr.l	#2,d7
	eor.l	d0,d7
	move.l	a4,(a1)+
	and.l	d5,d7
	eor.l	d7,d0
	lsl.l	#2,d7
	eor.l	d7,d2

	move.l	d3,d7
	lsr.l	#2,d7
	eor.l	d1,d7
	and.l	d5,d7
	eor.l	d7,d1
	lsl.l	#2,d7
	eor.l	d7,d3

	move.l	d1,d7
	lsr.l	#8,d7
	move.l	a5,-BPLSIZE-4(a1)
c2p1x1_8_c5_030_2_smc9 EQU *-2
.start2

	eor.l	d0,d7
	and.l	d6,d7
	eor.l	d7,d0
	lsl.l	#8,d7
	eor.l	d7,d1

	move.l	d1,d7
	lsr.l	#1,d7
	eor.l	d0,d7
	and.l	d4,d7
	eor.l	d7,d0
	add.l	d7,d7
	eor.l	d1,d7

	move.l	d3,d1
	move.l	d0,BPLSIZE*2(a1)
c2p1x1_8_c5_030_2_smc10 EQU *-2
	lsr.l	#8,d1
	eor.l	d2,d1
	and.l	d6,d1
	eor.l	d1,d2
	lsl.l	#8,d1
	eor.l	d1,d3

	move.l	d3,d1
	lsr.l	#1,d1
	eor.l	d2,d1
	and.l	d4,d1
	eor.l	d1,d2
	add.l	d1,d1
	eor.l	d1,d3

	move.l	(a0)+,d0
	move.l	d2,a4
	move.l	d3,a5

	cmpa.l	a0,a2
	bne	.x2

	move.l	d7,BPLSIZE(a1)
c2p1x1_8_c5_030_2_smc11 EQU *-2
	move.l	a4,(a1)+
	move.l	a5,-BPLSIZE-4(a1)
c2p1x1_8_c5_030_2_smc12 EQU *-2

.none
	movem.l	(sp)+,d2-d7/a2-a6
	rts

c2p1x1_8_c5_030_2_scroffs	dc.l	0
c2p1x1_8_c5_030_2_pixels	dc.l	0

c2p1x1_8_c5_030_2_fastbuf	dc.l	0	;CHUNKYXMAX*CHUNKYYMAX/2 bytes
