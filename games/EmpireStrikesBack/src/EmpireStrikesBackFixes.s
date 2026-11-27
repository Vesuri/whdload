; Fixes for fast CPUs, always applied. Addresses are the game's ($500 + image offset).
;
; Timing. Every scene ends its frame in the swap at $5dc02, which clears INTREQ's COPER
; bit and waits for the copper to set it again at line $e0: one field at least, and no
; other pacing. The game moves by the frame, so its speed followed the CPU: an A500 plays
; at 2 to 7 fields a frame (mostly 3 or 4) and the wave select at 3, a 68060 at 1. The
; swap now waits until three fields have passed since the last swap (at most 16.7 frames
; a second, PAL), as the Star Wars timing fix does; frames that take longer are not
; delayed. The fields are counted in the VBL server, at its call of the music player.

FixVblCount	lea	_FixFields(pc),a0	; the server saved every register
		addq.w	#1,(a0)
		jmp	$52690			; the original call, returns to the VBL server

; In: nothing; out: d0, a0 trashed (the original leaves them so too).
FixSwapWait	lea	$dff000,a0
.Field		move.w	#$10,$9c(a0)		; clear COPER, wait for line $e0
.Coper		btst	#4,$1f(a0)
		beq.b	.Coper
		move.w	_FixFields(pc),d0
		sub.w	_FixLast(pc),d0
		cmpi.w	#3,d0
		blo.b	.Field
		move.w	_FixFields(pc),d0
		lea	_FixLast(pc),a0
		move.w	d0,(a0)
		rts

_FixFields	dc.w	0
_FixLast	dc.w	0

; Blitter waits. The game polls BBUSY right after writing BLTSIZE (the line drawer at
; $43624 between its planes, the shared wait $3f732 that most blits call after theirs,
; the clear $3f742, the blits at $47e40). A fast CPU can read DMACONR before Agnus has
; set the bit, and then loads the next blit's registers, or draws with the CPU, while the
; previous blit still runs. Each poll now reads DMACONR once first, as WHDLoad's
; BLITWAIT does. The CPU drawing (the star plot at $435d6, the vertical line at $43908,
; the HUD digits at $5c5ac and $5c5f2) waits for the blitter first: with the game in
; Chip RAM and the blitter nasty, a 68000 could not run during a blit, but a CPU running
; from its cache can, and the line drawer returns with its last blit still running.

FixBlitWaitA6	tst.b	2(a6)
.Wait		btst	#6,2(a6)
		bne.b	.Wait
		rts

FixBlitWaitA0	tst.b	2(a0)
.Wait		btst	#6,2(a0)
		bne.b	.Wait
		rts

FixBlitIdle	tst.b	$dff002
.Wait		btst	#6,$dff002
		bne.b	.Wait
		rts

FixPlotStart	bsr.b	FixBlitIdle		; star plot: movea.l $936.w,a1
		movea.l	$936.w,a1		; adda.w (a0,d1.w),a1
		adda.w	(a0,d1.w),a1
		rts

FixVlineStart	bsr.b	FixBlitIdle		; vertical line: movea.l $936.w,a0
		movea.l	$936.w,a0		; adda.w d7,a0
		adda.w	d7,a0
		rts

FixDigitStart	bsr.b	FixBlitIdle		; HUD digits: lea $5c658,a1
		lea	$5c658,a1
		rts

; Self-modified drawing code. The digit colour setter $5c56a copies the four per-plane
; opcodes of a colour (or.b d1 to set a plane, and.b d2 to clear it; the table at
; $43a8c) into the HUD digit plots at $5c5dc, $5c62c and $5c640, and the vertical line
; $43832 copies them into its own loop at $43908 when the colour changes. With an
; instruction cache the CPU can keep running the previous colour's opcodes. Both now
; flush the caches after the copy (resload_FlushCache keeps every register); the code
; that runs is the original's.

FixDigitColour	movem.l	(sp)+,d1/a0-a4		; the setter's end
		bra.b	FixFlush

FixVlineColour	move.w	(a0)+,(a1)+		; the vertical line's copy
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
FixFlush	move.l	a0,-(sp)
		move.l	_resload(pc),a0
		jsr	resload_FlushCache(a0)
		move.l	(sp)+,a0
		rts

; CPU-timed waits. The sound effects player at $53922 switches a channel's DMA off,
; counts 257 passes of a dbf loop, loads the channel and switches DMA on, then counts
; 257 more before writing the repeat pointer; $53800 counts 513 after switching one off.
; On an A500 these took 5.7 to 6.5 and 11.4 raster lines; a fast CPU counts them in a
; fraction of a line, before Paula has taken the new sample. The pause (Esc, $24e2)
; fades the palette down to $666 and back in steps $111 apart, each timed by 2048
; passes of a loop (83 to 88 lines on an A500); a fast CPU fades in no time. All of
; them now wait by the beam, as long as on the A500, and leave the counter as the loop
; did (-1, or 0 for the fade's).

FixLines	movem.l	d0/d2,-(sp)		; d1.w: lines to wait, by the beam's
		bsr.b	.Line			; position (an interrupt cannot
		move.w	d0,d2			; shorten it)
.Wait		bsr.b	.Line
		sub.w	d2,d0
		bpl.b	.Same
		addi.w	#312,d0			; past the end of the frame
.Same		cmp.w	d1,d0
		blo.b	.Wait
		movem.l	(sp)+,d0/d2
		rts

.Line		move.l	d1,-(sp)		; d0.w: the line (V8-V0), read until
.Again		move.l	$dff004,d0		; two reads agree: the two words
		lsr.l	#8,d0			; can straddle a line
		andi.w	#$1ff,d0
		move.l	$dff004,d1
		lsr.l	#8,d1
		andi.w	#$1ff,d1
		cmp.w	d1,d0
		bne.b	.Again
		move.l	(sp)+,d1
		rts

FixAudioD7	move.l	d1,-(sp)		; move.w #$100,d7; dbf d7,*
		moveq	#7,d1			; 5.7 to 6.5 on an A500
		bsr.b	FixLines
		move.l	(sp)+,d1
		move.w	#-1,d7
		rts

FixAudioD0	move.l	d1,-(sp)		; move.w #$200,d0; dbf d0,*
		moveq	#12,d1			; 11.4 lines on an A500
		bsr.b	FixLines
		move.l	(sp)+,d1
		move.w	#-1,d0
		rts

FixFadeStep	move.l	d1,-(sp)		; move.w #$800,d2; subq; bne
		moveq	#87,d1			; 83 to 88 on an A500
		bsr.b	FixLines
		move.l	(sp)+,d1
		clr.w	d2			; the word the loop leaves
		rts
