; Drawing and sound that hold on fast CPUs (SPS 0403).
;
; The game polls BBUSY right after writing BLTSIZE (or a few instructions later), and a
; fast CPU can read DMACONR before Agnus has set the bit: it then writes the registers
; of the next blit, or draws with the CPU, while the previous blit still runs. Its
; vector font shows it first (strokes missing on a 68060). Every wait here reads
; DMACONR once before polling, as WHDLoad's BLITWAIT does, and the routines that draw
; with the CPU (the plot, the horizontal line in the line routine, the screen clear)
; wait for the blitter first: with the game's code in Chip RAM and the blitter nasty,
; a 68000 could not touch Chip RAM while a blit ran, but a CPU in Fast RAM can.
;
; The colour setter at $1840 also rewrote the four bset/bclr instructions (one per
; bitplane) of the plot at $1b70 and of the horizontal line at $1bb0 for every colour:
; with an instruction cache (8 KB on a 68060) the CPU kept drawing with the stale
; opcodes, so CPU-drawn strokes came out in the wrong colour or not at all. The
; setter's code writes are skipped, and both places call SetPixel, which reads the
; per-plane flags the setter stores anyway (sne -28138..-28135(a4)).

BLIT_WAIT	MACRO
	tst.b	$dff002
	btst	#6,$dff002
	beq.b	.done\@
.wait\@	tst.b	$bfe001			; slows the polling, as BLITWAIT does
	btst	#6,$dff002
	bne.b	.wait\@
.done\@
	ENDM

PLFIX403
	PL_START
	PL_PSS	$0898,BlitWait,4	; rectangle fill (btst #6,2(a2); beq; bra)
	PL_PSS	$0a9c,BlitWait,4	; plane copy
	PL_PSS	$1a7e,BlitWait,2	; line: btst #6,2(a0); bne
	PL_PSS	$1aae,BlitWait,2	; line, next plane
	PL_PSS	$990e,BlitWait,4	; shape drawer (btst #6,2(a3); beq; bra)
	PL_PSS	$9942,BlitWait,4
	PL_PSS	$9a16,BlitWait,4
	PL_PSS	$9a4a,BlitWait,4
	PL_PSS	$9b3c,BlitWait,4
	PL_PSS	$9b76,BlitWait,4
	PL_PS	$9918,BlitMasks		; shape drawer, the clipped shape's copy:
	PL_PS	$9a20,BlitMasks		; move.w #$8400,150(a3)
	PL_PSS	$1b86,BlitHLine,2	; CPU horizontal line: sub.w d2,d0; bpl; neg; sub
	PL_GA	$1b32,BlitPlotRet
	PL_P	$1b2c,BlitPlot		; CPU plot: move.w d6,-(sp); move.w 6(sp),d6
	PL_S	$1890,$18b4-$1890	; colour setter: no code writes
	PL_PSS	$1b70,SetPixel,8	; plot: bset d6,(a0); bset d6,8000(a0); ...
	PL_PSS	$1bb0,SetPixel,8	; horizontal line, the same
	PL_PSS	$9f7c,AudioWait,10	; music: 50-pass CPU loop after AUD0 DMA on
	PL_GA	$1c10,BlitClearRet
	PL_P	$1c08,BlitClear		; CPU clear: movem.l d0-a3/a5,-(sp); movea.l -26442(a4),a0
	PL_W	$3958,3			; title zoom: cmpi.w #1,-26430(a4) waits for 3
	PL_PSS	$26f6,SelectStart,2	; wave select: jsr -32700(a4); jsr -32670(a4)
	PL_GA	$59e6,SelectCannons
	PL_PSS	$270c,SelectEnd,2	; jsr $59e6(pc); jsr -32694(a4) (the loop enters at
					; $2714, so that stays)
	PL_NEXT	PLSMOOTH403		; StarWarsSmooth.s (CUSTOM2)

; Paces on fast CPUs, waits an A500 never reaches (it is slower): the title zoom waits
; for 3 fields of work (4 or 5 a pass on an A500, 2 on an A1200 with a 68030), and the
; wave select loop, which had no wait (3 fields a pass on an A500, 1 on a 68060), for 2
; after the swap, so a pass takes 3. Its 10 s timeout reads the counter, which keeps
; running: the pass start is noted instead of clearing it.
SelectStart
	jsr	-32700(a4)		; the swap wait $09a8
	lea	SelectT(pc),a0
	move.w	-26430(a4),(a0)
	jmp	-32670(a4)
SelectEnd
	move.l	SelectCannons(pc),a0	; the cannons and the cockpit
	jsr	(a0)
.w	move.w	-26430(a4),d0
	sub.w	SelectT(pc),d0
	cmp.w	#2,d0
	blt.b	.w
	jmp	-32694(a4)		; the swap request $09c0
SelectCannons	dc.l	0
SelectT	dc.w	0

BlitWait
	BLIT_WAIT
	rts

; The game never writes BLTALWM (only the line drawer writes BLTAFWM, $ffff), so its
; blits ran with whatever was there: 0 in FS-UAE, what the OS last left under WHDLoad.
; The shape drawer copies a shape clipped at the left or right edge (mask and planes)
; through a buffer with the A channel, so the mask's last word came out opaque and the
; cannons (wave select, the left ones at some crosshair x) cut a black box, up to 16
; pixels wide, into the WAVE 1 text and Death Star. Both masks are set open there and
; at the screen clear; the rectangle fill ($0810, BLTADAT) gets its last word too.
BlitMasks
	move.w	#$8400,150(a3)
	move.l	#-1,$44(a3)
	rts

BlitHLine
	BLIT_WAIT
	sub.w	d2,d0
	bpl.b	.pos
	neg.w	d0
	sub.w	d0,d2
.pos	rts

BlitPlot
	BLIT_WAIT
	move.w	d6,-(a7)
	move.w	6(a7),d6
	move.l	BlitPlotRet(pc),-(a7)
	rts

BlitClear
	BLIT_WAIT
	move.l	#-1,$dff044		; BLTAFWM, BLTALWM (BlitMasks)
	movem.l	d0-a3/a5,-(a7)
	move.l	-26442(a4),a0		; the drawing buffer
	move.l	BlitClearRet(pc),-(a7)
	rts

; d6: bit number, a0: byte in plane 0 (planes 8000 bytes apart). Flags: preserved
; only as far as the callers need (none read them after the four instructions).
SetPixel
	tst.b	-28138(a4)
	beq.b	.c0
	bset	d6,(a0)
	bra.b	.p1
.c0	bclr	d6,(a0)
.p1	tst.b	-28137(a4)
	beq.b	.c1
	bset	d6,8000(a0)
	bra.b	.p2
.c1	bclr	d6,8000(a0)
.p2	tst.b	-28136(a4)
	beq.b	.c2
	bset	d6,16000(a0)
	bra.b	.p3
.c2	bclr	d6,16000(a0)
.p3	tst.b	-28135(a4)
	beq.b	.c3
	bset	d6,24000(a0)
	rts
.c3	bclr	d6,24000(a0)
	rts

; The music player starts channel 0 (DMA on), counts -10(a5) to 50 in a CPU loop
; (about 5 raster lines on a 68000, microseconds on a 68030) and then writes the
; repeat pointer and length. Paula must have fetched the first ones by then: wait 8
; raster lines, two periods of the longest note period in the player's table (880),
; by the beam. The counter is left at 50 as the loop left it.
AudioWait
	movem.l	d0-d2,-(a7)
	moveq	#8-1,d2
.line	move.b	$dff006,d0
.same	move.b	$dff006,d1
	cmp.b	d0,d1
	beq.b	.same
	dbf	d2,.line
	move.w	#50,-10(a5)
	movem.l	(a7)+,d0-d2
	rts

BlitPlotRet	dc.l	0
BlitClearRet	dc.l	0
