; VERIFY only: work timer at the game's paced waits (SPS 0403).
;
; Each of the four paced loops clears the frame counter (-26430(a4), counted by the
; game's vertical blank server) at its start and busy waits at its end until the
; counter reaches the threshold. The probe replaces the wait (cmpi.w #N,-26430(a4);
; bge.s; bra.s: 10 bytes) and records, per site, the work since the previous wait at
; that site ended: frames x 313 + the beam line now - the beam line then, in raster
; lines. Then it waits as the original did, with the threshold the build selects.
;
; Record per site (PRB_SIZE bytes) at probe_buf + site x PRB_SIZE:
;   +0  passes (long), +4 sum of lines (long), +8 max lines (long),
;   +12 frames-at-entry histogram 0..7 (8 longs), +44 line histogram in 32-line
;   buckets 0..31 (32 longs; the last bucket takes everything above),
;   +172 beam line at the last exit (word), +174 valid flag (word)
; The harness finds probe_buf (in the main source, after the tag "SWPB") by searching
; back from the jsr target the patch writes at site 0.

PRB_SIZE	= 176
PRB_SITES	= 4

; d0.w: site, d1.w: threshold
ProbeWait
	movem.l	d0-d4/a0,-(a7)
	move.l	probe_buf(pc),d2
	beq.b	.wait
	move.l	d2,a0
	mulu	#PRB_SIZE,d0
	add.l	d0,a0
	bsr.b	.line
	move.w	-26430(a4),d3		; frames since the loop cleared the counter
	tst.w	174(a0)
	beq.b	.wait
	moveq	#0,d4
	move.w	d3,d4
	mulu	#313,d4
	add.l	d2,d4
	moveq	#0,d2
	move.w	172(a0),d2
	sub.l	d2,d4
	bpl.b	.pos
	moveq	#0,d4
.pos	addq.l	#1,(a0)
	add.l	d4,4(a0)
	cmp.l	8(a0),d4
	bls.b	.nomax
	move.l	d4,8(a0)
.nomax	cmp.w	#7,d3
	bls.b	.f
	moveq	#7,d3
.f	lsl.w	#2,d3
	addq.l	#1,12(a0,d3.w)
	lsr.l	#5,d4
	cmp.l	#31,d4
	bls.b	.b
	moveq	#31,d4
.b	lsl.w	#2,d4
	addq.l	#1,44(a0,d4.w)
.wait	cmp.w	-26430(a4),d1
	bgt.b	.wait
	move.l	probe_buf(pc),d2
	beq.b	.out
	bsr.b	.line
	move.w	d2,172(a0)
	st	174(a0)
.out	movem.l	(a7)+,d0-d4/a0
	rts

; d2.l: the current beam line (0..312)
.line	move.l	$dff004,d2
	lsr.l	#8,d2
	and.l	#$1ff,d2
	rts

ProbeAlloc
	move.l	#PRB_SIZE*PRB_SITES,d0
	move.l	#MEMF_PUBLIC|MEMF_CLEAR,d1
	move.l	$4.w,a6
	jsr	_LVOAllocMem(a6)
	lea	probe_buf(pc),a0
	move.l	d0,(a0)
	rts
