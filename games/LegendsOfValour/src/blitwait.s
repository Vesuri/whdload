; Blitter waits after the game's own graphics.library calls (all builds, every CUSTOM2).
;
; The game's glue for graphics.library (h15, GfxBase h11:05ea8) returns from SetRast, Draw
; and RectFill while their blit is still running. The game then draws text with the CPU
; (h12:05408 and h12:053fe and/or every plane byte): h1:0117c clears the message box with
; RectFill and h1:02446 prints "Legends of Valour!" into it at once; h1:014ec does the
; same for the guild titles. On a fast CPU the first glyphs are written before the blitter
; has cleared the later planes and rows, so it wipes some of their planes (red/green first
; words, the cut row moving with timing). CFou!'s v1.0 shows it on a 68040 with CUSTOM2=0.
;
; _blit_install replaces each glue's jsr with a jmp to a copy that adds WaitBlit before
; the glue's own return. Each site is skipped unless its bytes match; CHARACT does not
; call any of them.

_blit_install
		movem.l	d0-d1/a0-a2,-(sp)
		move.l	(_custom1,pc),d0
		bne	.done
		move.l	(_hunks+15*4,pc),d0
		beq	.done
		move.l	d0,a2
		cmp.l	#$4eaeff16,(h15_00054,a2)	;jsr _LVOSetRast(a6)
		bne	.draw
		cmp.l	#$2c5f4e75,(h15_00058,a2)	;move.l (sp)+,a6 / rts
		bne	.draw
		lea	(_blit_setrast,pc),a0
		move.w	#$4ef9,(h15_00054,a2)
		move.l	a0,(h15_00056,a2)
.draw		cmp.l	#$4eaeff0a,(h15_0008a,a2)	;jsr _LVODraw(a6)
		bne	.rectfill
		cmp.l	#$2c5f4e75,(h15_0008e,a2)
		bne	.rectfill
		lea	(_blit_draw,pc),a0
		move.w	#$4ef9,(h15_0008a,a2)
		move.l	a0,(h15_0008c,a2)
.rectfill	cmp.l	#$4eaefece,(h15_000a8,a2)	;jsr _LVORectFill(a6)
		bne	.flush
		cmp.l	#$4cdf400c,(h15_000ac,a2)	;movem.l (sp)+,d2-d3/a6
		bne	.flush
		cmp.w	#$4e75,(h15_000b0,a2)
		bne	.flush
		lea	(_blit_rectfill,pc),a0
		move.w	#$4ef9,(h15_000a8,a2)
		move.l	a0,(h15_000aa,a2)
.flush		move.l	(_resload,pc),a2
		jsr	(resload_FlushCache,a2)
.done		movem.l	(sp)+,d0-d1/a0-a2
		rts

_blit_setrast	jsr	(-$ea,a6)		;SetRast
		jsr	(-$e4,a6)		;WaitBlit
		move.l	(sp)+,a6
		rts

_blit_draw	jsr	(-$f6,a6)		;Draw
		jsr	(-$e4,a6)
		move.l	(sp)+,a6
		rts

_blit_rectfill	jsr	(-$132,a6)		;RectFill
		jsr	(-$e4,a6)
		movem.l	(sp)+,d2-d3/a6
		rts
