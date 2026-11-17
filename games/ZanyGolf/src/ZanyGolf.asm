		incdir	"include:"
		include	whdload.i
		opt	o4-		; the shipped slave keeps move.l #65536,d0, not moveq+swap

_base		SLAVE_HEADER			;ws_Security + ws_ID
		dc.w	17			;ws_Version: 17 for ws_config
		dc.w	WHDLF_NoError|WHDLF_EmulTrap|WHDLF_NoKbd
		dc.l	$80000			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	Start-_base		;ws_GameLoader
		dc.w	_data-_base
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$59			;ws_keyexit = F10
_expmem		dc.l	-EXPSIZE		;optional: the renderer's caches (NewDraw)
		dc.w	_name-_base		;ws_name
		dc.w	_copy-_base		;ws_copy
		dc.w	_info-_base		;ws_info
		dc.w	0			;ws_kickname: no Kickstart
		dc.l	0			;ws_kicksize
		dc.w	0			;ws_kickcrc
		dc.w	_config-_base		;ws_config
_data		dc.b	"data",0
_config		dc.b	"C1:L:Start on hole (debug):1,2,3,4,5,6,7,8,9,10",0
_name		dc.b	"Zany Golf",0
_copy		dc.b	"1988 Electronic Arts",0
_info		dc.b	"installed & fixed by Bored Seal",10
		dc.b	"V1.1 (23-Jul-2006)",0
		even

Start		lea	_resload(pc),a1
		move.l	a0,(a1)
		move.l	a0,a2

		lea	(_tags,pc),a0		;CUSTOM1: the hole a new game starts on
		jsr	(resload_Control,a2)

		lea	(_expmem,pc),a0		;take the ExpMem for the renderer, and hide
		move.l	(a0),d0			;it from OSEmu, which would otherwise give
		clr.l	(a0)			;it to the game as memory
		lea	(_v,pc),a1
		move.l	d0,V_EXP(a1)
		beq.b	.slow
		cmp.l	#$200000,d0		;chip RAM
		bcs.b	.slow
		cmp.l	#$c00000,d0
		bcs.b	.fast
		cmp.l	#$e00000,d0		;slow RAM, on the chip bus too
		bcs.b	.slow
.fast		st	V_FAST(a1)
.slow

		lea	(_OSEmu,pc),a0	;load&init the osemu module
		lea	($400).w,a3
		move.l	a3,a1
		jsr	(resload_LoadFileDecrunch,a2)
		move.l	a2,a0
		lea	(_base,pc),a1
		jsr	(a3)
		move.w	#0,sr

		lea	dosname,a1
		clr.l	d0
		movea.l	4,a6
		jsr	-$228(a6)
		move.l	d0,a6

		lea	file,a0
		move.l	a0,d1
		jsr	-150(a6)

		add.l	d0,d0
		add.l	d0,d0
		addq.l	#4,d0
		move.l	d0,a1

		sub.l	a0,a0
		moveq.l	#0,d0

		move.w	#$6002,$48(a1)		;deprotect
		move.b	#$60,$5a(a1)

		move.w	#$4e75,$62e(a1)		;disk access

		move.w	#$4ef9,$658(a1)
		pea	Patch
		move.l	(sp)+,$65a(a1)
		jmp	(a1)

Patch		movem.l	d0-d7/a0-a6,-(sp)
		move.l	a3,a0
		move.l	#65536,d0
		move.l	(_resload,pc),a2
		jsr     (resload_CRC16,a2)
		cmpi.w	#$9cc8,d0	; cmpi as the shipped slave has it: vasm encodes cmp #,Dn as CMP
		bne	Unsupported

		move.l	#$4e714eb9,$1f38(a3)	;fix keyboard and set cheat
		pea	FixKey
		move.l	(sp)+,$1f3c(a3)

		move.w	#$4eb9,$14a4(a3)	;the renderer's flip: at most one frame
		pea	FrameCap		;each FRAME_FIELDS fields
		move.l	(sp)+,$14a6(a3)
		move.w	#$4e71,$14aa(a3)
		move.l	#$4eb94e71,$14bc(a3)	;after the flip: jsr Hidden, nop
		pea	Hidden
		move.l	(sp)+,$14be(a3)
		move.w	#$4e71,$14c2(a3)

		move.l	#$01384ef9,$5238(a3)	;the main loop: step the world each
		pea	Split			;STEP_FIELDS fields, draw in between
		move.l	(sp)+,$523c(a3)

		move.w	#$4eb9,$1de2(a3)	;the input's mouse button: jsr ReadButton
		pea	ReadButton
		move.l	(sp)+,$1de4(a3)

		lea	(_v,pc),a0
		tst.l	V_EXP(a0)
		beq.b	.norender
		move.w	#$4ef9,$14c4(a3)	;the renderer's tiles: jmp NewDraw
		pea	NewDraw
		move.l	(sp)+,$14c6(a3)
		move.w	#$4eb9,$173c(a3)	;the shape drawer: jsr ShapeHook
		pea	ShapeHook
		move.l	(sp)+,$173e(a3)
.norender
		move.l	#$01384ef9,$48d4(a3)	;the draw list: jmp NewList
		pea	NewList
		move.l	(sp)+,$48d8(a3)
	ifd VERIFY
		lea	(_v,pc),a0
		tst.l	V_EXP(a0)
		beq.b	.nolcheck
		move.l	#$01384ef9,$4d44(a3)	;the original's phases end: jmp ListCheck
		pea	ListCheck
		move.l	(sp)+,$4d48(a3)
.nolcheck
	endc
		move.l	(_hole,pc),d0
		beq.b	.hole1
		cmp.l	#9,d0			;holes 1-10 (0-9)
		bhi.b	.hole1
		move.w	d0,$7a9c(a3)		;a game's start: LDY #0 -> LDY #hole (CUSTOM1)
.hole1
		jsr	(resload_FlushCache,a2)	;the code changed
		move.l	#CACRF_EnableI,d0	;the instruction cache for BaseMem: the
		move.l	d0,d1			;game never changes its code. Not the
		jsr	(resload_SetCACR,a2)	;data cache: chip RAM is not cacheable

		movem.l	(sp)+,d0-d7/a0-a6
		jmp	(a3)

; The game advanced its world one step a drawn frame and counts the step as 6 fields
; (10 steps a second at NTSC). Split (below) now steps the world on its own clock, so
; this only keeps the flips to at most one a field. Replaces the flip's first two
; instructions (FILE1 $14a4: the fine scroll into the copper list, and d0 = $8000) and
; first waits until FRAME_FIELDS fields have passed since the previous flip, by the game's
; field counter (FILE1 $145c, low byte), which advances at the copper interrupt (line $90).
; No wait while the interrupts are off (the counter would not move). a4 is FILE1's base.
; The copper list loads the playfield's plane pointers and fine scroll ($2312-$2326) at
; line $4a and shows the playfield from line $52 to $f4. The flip (the four eor.w after
; this) is kept off lines $48-$4b, so the copper never loads some planes before it and
; some after, and the fine scroll is written with it, not before the wait. _flipline
; keeps the flip's line for Hidden.
FLIP_LOAD	= $4a		;the copper loads the plane pointers
SHOW_END	= $f4		;DIWSTOP: the playfield's last line
FRAME_FIELDS	= 1
FrameCap	movem.l	d1/a0,-(sp)
		lea	(_lastflip,pc),a0
		move.w	$dff01c,d1		;INTENAR: master, COPER and VERTB on?
		and.w	#$4030,d1
		cmp.w	#$4030,d1
		bne.b	.go
.wait		move.b	$145c(a4),d1
		sub.b	(a0),d1
		cmp.b	#FRAME_FIELDS,d1
		bcs.b	.wait
.go		move.b	$145c(a4),(a0)
.load		bsr.b	BeamLine		;not while the copper loads them
		cmp.w	#FLIP_LOAD-2,d1
		bcs.b	.flip
		cmp.w	#FLIP_LOAD+2,d1
		bcs.b	.load
.flip		move.w	d1,_flipline-_lastflip(a0)
		move.w	d0,$2312(a4)		;displaced: the fine scroll
		movem.l	(sp)+,d1/a0
		move.w	#$8000,d0		;displaced
		rts

BeamLine	move.l	$dff004,d1		;d1: the beam's line (VPOSR, VHPOSR)
		lsr.l	#8,d1
		and.w	#$1ff,d1
		rts

; After the flip ($14bc, both renderers). A flip on lines FLIP_LOAD to SHOW_END shows
; from the next field's line FLIP_LOAD; until SHOW_END of this field the display still
; shows the buffer the renderer is about to draw into (and the blitter to copy into, a
; plane at a time). Wait until the beam has passed SHOW_END (or the next field began).
; Replaces move.l $1462(a4),d0; move.w $2326(a4),d0 (the back buffer) at $14bc.
Hidden		movem.l	d1-d2,-(sp)
		move.w	(_flipline,pc),d2
		cmp.w	#FLIP_LOAD,d2
		bcs.b	.done
		cmp.w	#SHOW_END,d2
		bhi.b	.done
.wait		bsr.b	BeamLine
		cmp.w	#SHOW_END,d1
		bhi.b	.done
		cmp.w	d2,d1
		bcc.b	.wait
.done		movem.l	(sp)+,d1-d2
		move.l	$1462(a4),d0		;displaced
		move.w	$2326(a4),d0
		rts

_flipline	dc.w	0
_lastflip	dc.b	0
		even

; The main loop (FILE1 $5232, threaded code) draws a frame when the drawing flag ($0ea0)
; is set (JSR $4fd0, $1478, $48d4), then reads the input (JSR $1d5a) and steps the world
; (JSR $62b2, which also adds 6 fields to the game clock). Replaces the flag test at $5238
; (LDA $0ea0; BEQ $524c) with native code (primitive $0138) that jumps here and picks the
; rest of the pass by setting the thread pointer a5:
; - flag clear: input and step ($524c), and loop; the game clock then counts real fields.
; - flag set and STEP_FIELDS fields since the last step: the same, input and step only, so
;   the step is not held up behind a frame; the next pass draws it.
; - flag set and fewer: draw only (DrawOnly), and loop. $4fd0 draws the course pieces
;   that have come into view (it clears their bit 0 in $111a); what it reads (the view,
;   the pieces and their bits) changes only in a step, so after its first run following a
;   step it would find nothing, and DrawOnly starts after it until the next step.
; A step can change the flag (the pause screen clears it), and the next pass tests it again,
; as the game's own next pass did.
; Steps are due every STEP_FIELDS fields by the field counter; a step more than one step
; late restarts the schedule from now, so a slow machine steps every pass as before and
; never catches up in a burst. With the interrupts off the counter stops, so every pass
; steps. a4 is FILE1's base, d7 and a0 are scratch in the threaded code.
STEP_FIELDS	= 6
Split		bsr	PollButton
		move.b	$0ea0(a4),d0		;displaced: LDA $0ea0
		move.b	d0,d4
		lea	(_laststep,pc),a0
		beq.b	.update
		move.w	$dff01c,d7		;INTENAR: master, COPER and VERTB on?
		and.w	#$4030,d7
		cmp.w	#$4030,d7
		bne.b	.off
		move.b	$145c(a4),d7
		sub.b	(a0),d7
		cmp.b	#STEP_FIELDS,d7
		bcs.b	.draw
		cmp.b	#2*STEP_FIELDS,d7
		bcc.b	.late
		addq.b	#STEP_FIELDS,(a0)
		bra.b	.step
.late		move.b	$145c(a4),(a0)
.step		lea	(_stepped,pc),a0
		st	(a0)
		lea	$524c(a4),a5		;JSR $1d5a; JSR $62b2; JMP $5232
		jmp	$0122(a4)		;dispatch
.draw		lea	(_stepped,pc),a0
		lea	(DrawOnly,pc),a5
		tst.b	(a0)
		beq.b	.lite
		clr.b	(a0)
		jmp	$0122(a4)
.lite		addq.w	#4,a5			;no step since $4fd0 last ran: skip it
		jmp	$0122(a4)
.update		move.b	$145c(a4),d7		;the first pass with the flag set steps
		subq.b	#STEP_FIELDS,d7
		move.b	d7,(a0)
.off		lea	(_v+V_RESET,pc),a0	;no frames now (a hole may load): NewDraw
		st	(a0)			;starts again from nothing
		bra.b	.step

; Debug: CUSTOM1=N (0-9, the splash window's "Start on hole") starts every game on hole
; N+1 instead of hole 1, the windmill. The game plays the holes in the order of the table
; at $bb02 (3,8,0,9,4,5,1,7,6,2: the hole files HOLEn, 3 the windmill), with the position
; at $bb23 and the hole at $5c5a. A game's start ($7a86, threaded code) sets the position
; with LDY #0 at $7a9a; the patch sets that immediate ($7a9c) to N. The holes before it
; are not played, so their scores stay 0, and the game ends after hole 10 as before.
_tags		dc.l	WHDLTAG_CUSTOM1_GET
_hole		dc.l	0
		dc.l	TAG_DONE

DrawOnly	dc.w	$05e8,$4fd0		;JSR $4fd0
		dc.w	$05e8,$1478		;JSR $1478: the renderer
		dc.w	$05e8,$48d4		;JSR $48d4
		dc.w	$0438,$5232		;JMP $5232

_laststep	dc.b	0
_stepped	dc.b	0			;a step ran since $4fd0 last did
		even

; The input routine (FILE1 $1d5c, part of the step) reads the left mouse button from CIA-A
; ($bfe001 bit 6), the game's only read of it. Steps are 6 fields apart, so a press or a
; release shorter than that between two steps would be lost. Every pass polls the button
; (PollButton, from Split), and the step reports the other state from the one it reported
; last whenever any poll since saw it change: a click between two steps reaches the game
; as a press at one step and a release at the next. ReadButton replaces the read
; (move.b $bfe001,d1) and returns d1 as the port would read with bit 6 for that state.
PollButton	btst	#6,$bfe001		;d7 and a0 are scratch here
		seq	d7
		and.b	#1,d7			;1 pressed
		lea	(_button,pc),a0
		cmp.b	(a0),d7
		beq.b	.same
		st	1(a0)
.same		rts

ReadButton	movem.l	d7/a0,-(sp)
		bsr.b	PollButton
		move.b	(a0),d7
		tst.b	1(a0)
		beq.b	.report
		eori.b	#1,d7
.report		move.b	d7,(a0)
		clr.b	1(a0)
		move.b	$bfe001,d1
		bset	#6,d1
		tst.b	d7
		beq.b	.up
		bclr	#6,d1
.up		movem.l	(sp)+,d7/a0
		rts

_button		dc.b	0,0			;the state the step reported last, changed since

;=============================================================================
; The renderer's tiles. The game's renderer ($147a) flips the buffers, then redraws all
; 20 rows of 40 tiles (8x8, 4 planes, 32 bytes each, copied with move.b) and a partial
; 21st row into the back buffer, every frame. NewDraw replaces the redraw ($14bc-$15dd):
; - a cache per buffer holds the map word each of its 21x40 cells was last drawn from,
;   and a cell is drawn only when the map word differs (ShapeHook marks the cells the
;   shape drawer drew over INVALID, and the course pieces that change are map words);
; - the cache is good for the view origin it was drawn at (x in 16-pixel steps, y in
;   pixels). When the origin moved, the blitter copies the other buffer, drawn last
;   frame, shifted by the difference (whole words: x moves in 16-pixel steps), and its
;   cache comes along shifted; the cells uncovered are INVALID.
; The tiles come from a copy in ExpMem when that is fast memory. Everything is in ExpMem:
; without it the game's renderer stays. a4 is FILE1's base; all registers but a4 and sp
; are free here, as in the game's own code.

INVALID		= $0001		;map words are tile offsets, all even
CROWS		= 21
CSIZE		= CROWS*40*2
EX_TILES	= $1000		;ExpMem: the caches at 0 and CSIZE, the tiles here
TILESIZE	= $10020	;map words are 16-bit offsets of 32-byte tiles
EXPSIZE		= (EX_TILES+TILESIZE+$fff)&$fffff000	;WHDLoad wants whole $1000s

V_EXP		= 0		;l ExpMem, 0 without
V_TILEM		= 4		;l the hole block copied to ExpMem, 0 none
V_A4		= 8		;l
V_P		= 12		;l the back buffer's first plane, at the display's top line
V_M		= 16		;l the hole block: map words, and tiles at the words' offsets
V_T		= 20		;l where the tiles are read from
V_ORG0		= 24		;w,w the origin buffer 0's cache holds: x/16, y
V_ORG1		= 28		;w,w buffer 1
V_NEW		= 32		;w,w this frame's origin
V_K		= 36		;w the back buffer, 0 or 1
V_DROW		= 38		;w,w Scroll's row and 16-pixel column shifts
V_VALID		= 42		;b,b the buffers' caches hold anything
V_RESET		= 44		;b drop both caches and the tile copy
V_FAST		= 45		;b ExpMem is fast memory
V_SIZE		= 46

TILE		macro			;draw the tile at a2 at the cell at a3
		move.b	(a2)+,$6000(a3)
		move.b	(a2)+,$4000(a3)
		move.b	(a2)+,$2000(a3)
		move.b	(a2)+,(a3)
		rept	7
		move.b	(a2)+,$6000+40*(REPTN+1)(a3)
		move.b	(a2)+,$4000+40*(REPTN+1)(a3)
		move.b	(a2)+,$2000+40*(REPTN+1)(a3)
		move.b	(a2)+,40*(REPTN+1)(a3)
		endr
		endm

NewDraw		lea	(_v,pc),a5
		move.l	a4,V_A4(a5)
		move.l	$1462(a4),d0		;the back buffer, as the game finds it
		move.w	$2326(a4),d0
		eori.w	#$8000,d0
		move.l	d0,V_P(a5)
		moveq	#0,d7
		tst.w	d0
		bpl.b	.k0
		moveq	#1,d7
.k0		move.w	d7,V_K(a5)
		move.w	$0e9c(a4),d1		;the view: x/16 and y
		ror.w	#8,d1
		lsr.w	#4,d1
		move.w	$0e9e(a4),d2
		ror.w	#8,d2
		movem.w	d1-d2,V_NEW(a5)
		move.l	$0eb4(a4),d0		;the hole block, a little-endian offset
		ror.w	#8,d0
		swap	d0
		ror.w	#8,d0
		add.l	a4,d0
		move.l	d0,V_M(a5)
		tst.b	V_RESET(a5)
		beq.b	.noreset
		clr.b	V_RESET(a5)
		clr.w	V_VALID(a5)
		clr.l	V_TILEM(a5)
.noreset	move.l	d0,V_T(a5)
		tst.b	V_FAST(a5)
		beq.b	.tchip
		movea.l	V_EXP(a5),a1
		lea	EX_TILES(a1),a1
		move.l	a1,V_T(a5)
		cmp.l	V_TILEM(a5),d0
		beq.b	.tchip
		move.l	d0,V_TILEM(a5)
		movea.l	d0,a0
		move.w	#TILESIZE/4-1,d3
.copy		move.l	(a0)+,(a1)+
		dbf	d3,.copy
.tchip
		lea	V_VALID(a5),a0		;this buffer's cache at this origin?
		tst.b	(a0,d7.w)
		beq.b	.notsame
		move.w	d7,d0
		add.w	d0,d0
		add.w	d0,d0
		lea	V_ORG0(a5),a0
		cmp.w	(a0,d0.w),d1
		bne.b	.notsame
		cmp.w	2(a0,d0.w),d2
	ifd VERIFY
		bne.b	.notsame
		addq.l	#1,$1e0.w		;same origin
		bra	.cells
	else
		beq	.cells
	endc
.notsame	move.w	d7,d6			;the other buffer's, close enough?
		eori.w	#1,d6
		lea	V_VALID(a5),a0
		tst.b	(a0,d6.w)
		beq	.full
		add.w	d6,d6
		add.w	d6,d6
		lea	V_ORG0(a5),a0
		move.w	(a0,d6.w),d3		;x/16 there
		move.w	2(a0,d6.w),d4		;y there
		move.w	d1,d5
		sub.w	d3,d5			;columns of 16 pixels moved
		move.w	d5,d0
		bpl.b	.p1
		neg.w	d0
.p1		cmp.w	#20,d0
		bcc	.full
		move.w	d2,d0
		lsr.w	#3,d0
		move.w	d4,d6
		lsr.w	#3,d6
		sub.w	d6,d0			;tile rows moved
		move.w	d0,d6
		bpl.b	.p2
		neg.w	d6
.p2		cmp.w	#20,d6
		bcc	.full
	ifd VERIFY
		addq.l	#1,$1e4.w		;scrolled
	endc
		bsr	Scroll
		bra.b	.cells
.full
	ifd VERIFY
		addq.l	#1,$1e8.w		;all cells
	endc
		bsr	CacheK
		move.w	#CROWS*40/2-1,d0
		move.l	#INVALID<<16|INVALID,d3
.inv		move.l	d3,(a1)+
		dbf	d0,.inv

.cells		bsr	CacheK
		movem.w	V_NEW(a5),d1-d2
		movea.l	V_M(a5),a0		;the map at the origin
		move.w	$0ed2(a4),d3		;bytes a map row (as the game works it out)
		ror.w	#8,d3
		lsr.w	#2,d3
		add.w	d3,d3
		move.w	d2,d0
		lsr.w	#3,d0
		mulu	d3,d0
		adda.l	d0,a0
		move.w	d1,d0
		lsl.w	#2,d0
		adda.w	d0,a0
		move.w	d3,d4
		sub.w	#80,d4			;to the next map row
		movea.l	V_P(a5),a3		;row 0 starts y&7 lines above the top
		move.w	d2,d0
		and.w	#7,d0
		mulu	#40,d0
		suba.w	d0,a3
		movea.l	V_T(a5),a6
		moveq	#0,d6
		moveq	#19,d7
.row		moveq	#19,d5
.pair		cmpm.l	(a0)+,(a1)+		;two cells at once
		bne.b	.diff
		addq.w	#2,a3
		dbf	d5,.pair
		bra	.rowend
.diff		move.w	-4(a0),d6
		cmp.w	-4(a1),d6
		beq	.second
		move.w	d6,-4(a1)
		lea	(a6,d6.l),a2
		TILE
.second		addq.w	#1,a3
		move.w	-2(a0),d6
		cmp.w	-2(a1),d6
		beq	.next
		move.w	d6,-2(a1)
		lea	(a6,d6.l),a2
		TILE
.next		addq.w	#1,a3
		dbf	d5,.pair
.rowend		adda.w	d4,a0
		lea	320-40(a3),a3
		dbf	d7,.row
		move.w	d2,d0			;the partial 21st row: y&7 lines
		and.w	#7,d0
		beq.b	.nopart
		subq.w	#1,d0
		moveq	#39,d5
.pcell		move.w	(a0)+,d6
		cmp.w	(a1)+,d6
		beq.b	.pnext
		move.w	d6,-2(a1)
		lea	(a6,d6.l),a2
		movea.l	a3,a4
		move.w	d0,d3
.pline		move.b	(a2)+,$6000(a4)
		move.b	(a2)+,$4000(a4)
		move.b	(a2)+,$2000(a4)
		move.b	(a2)+,(a4)
		lea	40(a4),a4
		dbf	d3,.pline
.pnext		addq.w	#1,a3
		dbf	d5,.pcell
.nopart
		movea.l	V_A4(a5),a4
		move.w	V_K(a5),d0
		lea	V_VALID(a5),a0
		st	(a0,d0.w)
		add.w	d0,d0
		add.w	d0,d0
		lea	V_ORG0(a5),a0
		move.l	V_NEW(a5),(a0,d0.w)
	ifd VERIFY
		bsr	CheckCells
	endc
		jmp	$15de(a4)		;the game's renderer, after the redraw

CacheK		movea.l	V_EXP(a5),a1		;a1 = the back buffer's cache
		tst.w	V_K(a5)
		beq.b	.0
		lea	CSIZE(a1),a1
.0		rts

; The view moved since the other buffer was drawn (by d5 columns of 16 pixels and d0 tile
; rows; d2 is the y now, d4 the y there): copy that buffer shifted with the blitter, and
; its cache with it. Dest line l (0 the display's top) shows map y l+y; the source line is
; l+dy. Only lines both buffers drew are copied: from the higher of the two first lines
; (row 0 starts y&7 lines above the top) to the display's last, 159.
Scroll		movem.w	d0/d5,V_DROW(a5)
		move.w	d2,d1
		sub.w	d4,d1			;dy
		move.w	d2,d3
		and.w	#7,d3
		neg.w	d3			;dest's first line
		move.w	d4,d6
		and.w	#7,d6
		neg.w	d6
		sub.w	d1,d6			;the source's first line, in dest lines
		cmp.w	d6,d3
		bge.b	.lo
		move.w	d6,d3			;lo
.lo		move.w	#159,d6
		sub.w	d1,d6
		cmp.w	#159,d6
		ble.b	.hi
		move.w	#159,d6			;hi
.hi		sub.w	d3,d6
		bmi	.noblit
		addq.w	#1,d6
		lsl.w	#6,d6			;height
		moveq	#20,d7
		tst.w	d5
		bmi.b	.left
		sub.w	d5,d7			;width in words
		moveq	#0,d0			;dest's first byte column
		move.w	d5,d4
		add.w	d4,d4			;the source's
		bra.b	.cols
.left		add.w	d5,d7
		move.w	d5,d0
		neg.w	d0
		add.w	d0,d0
		moveq	#0,d4
.cols		or.w	d7,d6			;BLTSIZE
		move.w	d7,d2
		add.w	d2,d2
		neg.w	d2
		add.w	#40,d2			;modulo
		movea.l	V_P(a5),a0
		move.w	d3,d7
		muls	#40,d7
		adda.l	d7,a0
		adda.w	d0,a0			;dest
		move.l	V_P(a5),d7
		eori.w	#$8000,d7		;the other buffer
		movea.l	d7,a1
		move.w	d3,d7
		add.w	d1,d7
		muls	#40,d7
		adda.l	d7,a1
		adda.w	d4,a1			;source
		lea	$dff000,a2
		tst.b	2(a2)
.bw0		btst	#6,2(a2)
		bne.b	.bw0
		move.l	#$09f00000,$40(a2)	;A to D
		move.l	#-1,$44(a2)
		move.w	d2,$64(a2)
		move.w	d2,$66(a2)
		moveq	#3,d7
.plane		tst.b	2(a2)
.bw1		btst	#6,2(a2)
		bne.b	.bw1
		move.l	a1,$50(a2)
		move.l	a0,$54(a2)
		move.w	d6,$58(a2)
		lea	$2000(a0),a0
		lea	$2000(a1),a1
		dbf	d7,.plane
.noblit
		bsr	CacheK			;the other cache, shifted, meanwhile
		movea.l	V_EXP(a5),a0
		tst.w	V_K(a5)
		bne.b	.f0
		lea	CSIZE(a0),a0
.f0		movem.w	V_DROW(a5),d0/d5
		move.l	#INVALID<<16|INVALID,d3
		moveq	#0,d7
.srow		move.w	d7,d1
		add.w	d0,d1			;the row there
		bmi.b	.sinv
		cmp.w	#19,d1			;its full rows only
		bgt.b	.sinv
		mulu	#80,d1
		lea	(a0,d1.l),a2
		move.w	d5,d1
		add.w	d1,d1			;cells moved
		tst.w	d5
		bmi.b	.sleft
		move.w	d1,d4
		add.w	d1,d1
		adda.w	d1,a2
		moveq	#39,d6
		sub.w	d4,d6
.sc1		move.w	(a2)+,(a1)+
		dbf	d6,.sc1
		subq.w	#1,d4
		bmi.b	.snext
.si1		move.w	d3,(a1)+
		dbf	d4,.si1
		bra.b	.snext
.sleft		neg.w	d1
		move.w	d1,d4
		subq.w	#1,d4
.si2		move.w	d3,(a1)+
		dbf	d4,.si2
		moveq	#39,d6
		sub.w	d1,d6
.sc2		move.w	(a2)+,(a1)+
		dbf	d6,.sc2
		bra.b	.snext
.sinv		moveq	#39,d6
.si3		move.w	d3,(a1)+
		dbf	d6,.si3
.snext		addq.w	#1,d7
		cmp.w	#CROWS,d7
		bcs.b	.srow
		lea	$dff000,a2
		tst.b	2(a2)
.bw2		btst	#6,2(a2)
		bne.b	.bw2
		move.l	(_resload,pc),a0	;the blitter wrote behind the data cache
		jsr	(resload_FlushCache,a0)
		rts

; The shape drawer ($16f2) is about to draw a shape: a3 its first row, d6 rows, d7 the
; offset of its first line, $26/$28 (little-endian) its x and y on the map. Mark the
; cells it covers in the back buffer's cache, by the same arithmetic the drawer uses: the
; drawer clips each row to the display's 160 lines and each pixel to 0-319. A row is an x
; step (signed, plus the previous row's count, in pixel pairs), a count of pixel pairs and
; two more bytes, then the pairs. With $32 = $30000 the drawer draws at fixed lines from
; $40000 (the status line) instead: if that reaches the playfield, drop both caches.
ShapeHook	addq.w	#8,a3			;displaced
		movea.l	$32(a4),a0		;displaced
		movem.l	d0-d7/a0-a3/a5,-(sp)
		lea	(_v,pc),a5
		move.l	a0,d0
		ror.w	#8,d0
		swap	d0
		ror.w	#8,d0
		cmp.l	#$30000,d0
		bne.b	.buf
		move.w	$28(a4),d0
		ror.w	#8,d0
		add.w	d7,d0
		add.w	d6,d0
		cmp.w	#33,d0			;buffer 0's tiles start 33 lines down
		ble	.out
		clr.w	V_VALID(a5)
		bra	.out
.buf		movea.l	V_EXP(a5),a1
		move.w	$2326(a4),d0
		eori.w	#$8000,d0
		bpl.b	.b0
		lea	CSIZE(a1),a1
.b0		move.w	$1476(a4),d4		;the frame's view y
		move.w	$28(a4),d0
		ror.w	#8,d0
		sub.w	d4,d0
		add.w	d7,d0			;first line
		move.w	d0,d1
		add.w	d6,d1
		subq.w	#1,d1			;last line
		tst.w	d0
		bpl.b	.c0
		moveq	#0,d0
.c0		cmp.w	#159,d1
		ble.b	.c1
		move.w	#159,d1
.c1		cmp.w	d0,d1
		blt	.out
		and.w	#7,d4
		add.w	d4,d0
		add.w	d4,d1
		lsr.w	#3,d0			;first cell row
		lsr.w	#3,d1			;last
		move.w	$26(a4),d2
		ror.w	#8,d2
		move.w	$1474(a4),d3
		and.w	#$fff0,d3
		sub.w	d3,d2			;x
		move.w	#$7fff,d4		;least x
		move.w	#$8000,d5		;greatest
		moveq	#0,d3
		movea.l	a3,a2
		move.w	d6,d7
		subq.w	#1,d7
.walk		move.b	(a2),d6
		ext.w	d6
		add.w	d3,d6
		add.w	d6,d6
		add.w	d6,d2
		cmp.w	d4,d2
		bge.b	.w1
		move.w	d2,d4
.w1		moveq	#0,d3
		move.b	2(a2),d3
		move.w	d3,d6
		add.w	d6,d6
		add.w	d2,d6
		subq.w	#1,d6
		cmp.w	d5,d6
		ble.b	.w2
		move.w	d6,d5
.w2		lea	4(a2,d3.w),a2
		dbf	d7,.walk
		asr.w	#3,d4
		bpl.b	.x0
		moveq	#0,d4
.x0		asr.w	#3,d5
		cmp.w	#39,d5
		ble.b	.x1
		moveq	#39,d5
.x1		cmp.w	d4,d5
		blt.b	.out
		sub.w	d4,d5			;columns - 1
		move.w	d0,d6
		mulu	#80,d6
		lea	(a1,d6.l),a2
		adda.w	d4,a2
		adda.w	d4,a2
		sub.w	d0,d1			;rows - 1
		moveq	#INVALID,d3
.mr		movea.l	a2,a0
		move.w	d5,d7
.mc		move.w	d3,(a0)+
		dbf	d7,.mc
		lea	80(a2),a2
		dbf	d1,.mr
.out		movem.l	(sp)+,d0-d7/a0-a3/a5
		rts

;=============================================================================
; The draw list. $48d4 (threaded code, once a frame) builds the list of what the frame
; draws (eight tables of 16 entries at $46a2-$4791, an entry per 2 bytes: shape or piece
; and frame $46a2/$46c2, depth $46e2, x $4702, y $4722, width $4742, height $4762, kind
; $4782: 0 shape, 1 course piece), then sorts it ($1ff4) and draws it ($4d44-$4eb8):
; - phase A ($48d4-$4b4a): each of the 32 objects ($0fda,X active) gets its frame from
;   $1656 (Frame here) and is culled against the hole ($0ed4) and the view ($0e9c/$0e9e,
;   304 wide, $11e6 high); a visible one is an entry, and a full list ends both phases;
; - phase B ($4b4a-$4d44): each course piece flagged in $111a bit 1 is an entry from its
;   record in the hole block ($4ec8,X + $0eb0); a visible one has the flag cleared.
; NewList does both natively, with every write the threaded code makes (the scratch at
; $4eba-$4ec7, $000a-$000d and $0022-$0029 included), and continues the threaded code at
; $4d44 with X and Y as it has them there. Replaces $48d4-$48db (LDX #0; TXY; STX $4ec0's
; opcode), entered by $0138 from the routine's JSR, so the caller's return is on the stack.
; a4 is FILE1's base; the threaded code's registers are d0-d4 (A, X, Y, carry, NZ) and
; $0106 sets them up again from the low bytes of d0-d2.

LEW		macro			;\1: the little-endian word at the even address \1
		move.w	\1,\2
		ror.w	#8,\2
		endm
SEW		macro			;store \1 little-endian at the even address \2
		ror.w	#8,\1
		move.w	\1,\2
		ror.w	#8,\1
		endm

NewList		movem.l	d3-d7/a1-a3,-(sp)
	ifd VERIFY
		bsr	ListSave
	endc
		moveq	#0,d0
		moveq	#0,d1			;X: the object
		moveq	#0,d2			;Y: the entry
.obj		move.b	d1,$4ec0(a4)
		move.b	d2,$4ec2(a4)
		lea	(a4,d1.w),a0
		tst.b	$0fda(a0)
		beq	.next
		move.b	$0eda(a0),$22(a4)	;the shape and frame
		move.b	$0f1a(a0),$23(a4)
		move.w	$105a(a0),$24(a4)	;the shape set
		move.w	$109a(a0),$26(a4)
		bsr	Frame
		lea	(a4,d1.w),a0
		LEW	$0f5a(a0),d3		;x less the frame's x origin
		moveq	#0,d0
		move.b	$26(a4),d0
		sub.w	d0,d3
		SEW	d3,$4ec4(a4)
		LEW	$0f9a(a0),d4		;y less the y origin
		move.b	$27(a4),d0
		sub.w	d0,d4
		SEW	d4,$4ec6(a4)
		move.b	$22(a4),d0		;x: in the hole
		move.w	d3,d5
		add.w	d0,d5
		SEW	d5,$4eba(a4)
		bmi	.next
		move.b	$24(a4),d0		;the width
		bsr	InHole
		bne	.next
		LEW	$0e9c(a4),d6		;in the view
		sub.w	d6,d5
		SEW	d5,$4eba(a4)
		bmi.b	.xneg
		cmp.w	#$130,d5
		bcc	.next
		bra.b	.y
.xneg		add.w	d0,d5
		SEW	d5,$4eba(a4)
		bmi	.next
.y		move.b	$23(a4),d0		;y: in the hole
		move.w	d4,d5
		add.w	d0,d5
		SEW	d5,$4eba(a4)
		bmi	.next
		move.b	$25(a4),d0		;the height
		bsr	InHole
		bne	.next
		LEW	$0e9e(a4),d6		;in the view
		sub.w	d6,d5
		SEW	d5,$4eba(a4)
		bmi.b	.yneg
		moveq	#0,d6
		move.b	$11e6(a4),d6
		sub.w	d6,d5
		SEW	d5,$4eba(a4)
		bcc	.next
		bra.b	.vis
.yneg		add.w	d0,d5
		SEW	d5,$4eba(a4)
		bmi	.next
.vis		lea	(a4,d2.w),a1		;the entry
		move.b	$0eda(a0),$46a2(a1)
		move.b	$0f1a(a0),$46c2(a1)
		move.w	$105a(a0),$4742(a1)
		move.w	$109a(a0),$4762(a1)
		move.w	$101a(a0),$46e2(a1)
		move.w	$0f5a(a0),$4702(a1)
		move.w	$0f9a(a0),$4722(a1)
		clr.b	$4782(a1)
		moveq	#0,d0			;A: the LDA #0 for the kind
		addq.b	#2,d2
		cmp.b	#$20,d2
	ifd VERIFY
		bne.b	.notfull
		addq.l	#1,$1cc.w		;lists that filled up
		bra	.end
.notfull
	else
		beq	.end			;the list is full
	endc
.next		addq.b	#2,d1
		cmp.b	#$40,d1
		bne	.obj

		move.b	$0ed8(a4),d0		;phase B: the course pieces
		beq	.end
		moveq	#0,d1			;X: the piece
.piece		lea	(a4,d1.w),a0
		btst	#1,$111a(a0)
		beq	.pnext
		lea	(a4,d2.w),a1		;the entry
		move.b	$119a(a0),$46e2(a1)
		move.b	$119b(a0),$46e3(a1)
		move.b	d2,$4eba(a4)
		move.b	d1,$4ebb(a4)
		moveq	#0,d3			;the piece's record: $4ec8,X + $0eb0
		LEW	$4ec8(a0),d3
		move.l	$0eb0(a4),d4
		ror.w	#8,d4
		swap	d4
		ror.w	#8,d4
		add.l	d3,d4
		move.l	d4,d3
		ror.w	#8,d3
		swap	d3
		ror.w	#8,d3
		move.l	d3,$0a(a4)
		and.l	#$ffffff,d4		;[$0a],Y: 24 bits
		lea	(a4,d4.l),a2
		move.b	4(a2),$4702(a1)
		move.b	5(a2),$4703(a1)
		move.b	6(a2),$4722(a1)
		move.b	7(a2),$4723(a1)
		move.b	8(a2),$4742(a1)
		move.b	9(a2),$4743(a1)
		move.b	10(a2),$4762(a1)
		move.b	11(a2),$4763(a1)
		moveq	#0,d3			;Y = $115a,X * 4 + 12, 8 bits
		move.b	$115a(a0),d3
		add.b	d3,d3
		add.b	d3,d3
		add.b	#12,d3
		move.b	(a2,d3.w),$46a2(a1)
		addq.b	#1,d3
		move.b	(a2,d3.w),$46a3(a1)
		addq.b	#1,d3
		move.b	(a2,d3.w),$46c2(a1)
		addq.b	#1,d3
		move.b	(a2,d3.w),$46c3(a1)
		move.b	#1,$4782(a1)
		LEW	$4702(a1),d5		;x in the view
		LEW	$0e9c(a4),d6
		sub.w	d6,d5
		SEW	d5,$4eba(a4)
		bmi.b	.pxneg
		cmp.w	#$130,d5
		bcc	.pnext
		bra.b	.py
.pxneg		LEW	$4742(a1),d6
		add.w	d6,d5
		SEW	d5,$4eba(a4)
		bmi	.pnext
.py		LEW	$4722(a1),d5		;y in the view
		LEW	$0e9e(a4),d6
		sub.w	d6,d5
		SEW	d5,$4eba(a4)
		bmi.b	.pyneg
		moveq	#0,d6
		move.b	$11e6(a4),d6
		sub.w	d6,d5
		SEW	d5,$4eba(a4)
		bcc	.pnext
		bra.b	.pvis
.pyneg		LEW	$4762(a1),d6
		add.w	d6,d5
		SEW	d5,$4eba(a4)
		bmi	.pnext
.pvis
	ifd VERIFY
		addq.l	#1,$1dc.w		;course-piece entries
	endc
		move.b	$111a(a0),d0		;drawn: clear the flag
		and.b	#$fd,d0
		move.b	d0,$111a(a0)
		addq.b	#2,d2
		beq.b	.end
.pnext		addq.b	#2,d1
		move.b	d1,d0
		lsr.b	#1,d0
		cmp.b	$0ed8(a4),d0
		bne	.piece

.end
	ifd VERIFY
		bsr	ListDone
	endc
		movem.l	(sp)+,d3-d7/a1-a3
	ifd VERIFY
		lea	(_v,pc),a0
		tst.l	V_EXP(a0)
		beq.b	.go
		move.l	#$0864<<16,$48d4(a4)	;run the original on the same input:
		move.l	#$074e077a,$48d8(a4)	;LDX #0; TXY; STX ...
		bsr	ListFlush
		lea	$48d4(a4),a5
		jmp	$0106(a4)
.go
	endc
		lea	$4d44(a4),a5		;STY $4ebe; STY $47a2; ...
		jmp	$0106(a4)

; e = d5 + d0 against the hole's size ($0ed4), as the threaded code tests it: Z clear
; (out) unless e - size borrows or its high byte is 0. Writes e - size at $4ebc.
InHole		move.w	d5,d6
		add.w	d0,d6
		SEW	d6,$4ebc(a4)
		LEW	$0ed4(a4),d7
		sub.w	d7,d6
		SEW	d6,$4ebc(a4)
		bcs.b	.in
		and.w	#$ff00,d6
		rts
.in		cmp.w	d6,d6			;Z
		rts

; $1656: the frame. $0024-$0027 is the shape set (a little-endian offset from a4), $0022
; the shape, $0023 the frame. Out: $0028 (and $0029 = 0), $0026, $0027 the frame's width
; and origin, $0022-$0025 the first bytes of its four words. d0, a0, a2, a3.
Frame		move.l	$24(a4),d0
		ror.w	#8,d0
		swap	d0
		ror.w	#8,d0
		movea.l	d0,a0
		adda.l	a4,a0
		movea.l	a0,a3
		movea.l	a0,a2
		moveq	#0,d0
		move.b	$22(a4),d0
		asl.w	#3,d0
		adda.w	d0,a0
		move.b	2(a0),$28(a4)
		clr.b	$29(a4)
		move.b	4(a0),$26(a4)
		move.b	6(a0),$27(a4)
		move.w	(a0),d0
		ror.w	#8,d0
		movea.l	a2,a0
		adda.w	d0,a0
		moveq	#0,d0
		move.b	$23(a4),d0
		add.w	d0,d0
		adda.w	d0,a0
		move.w	(a0),d0
		ror.w	#8,d0
		adda.w	d0,a3
		move.b	(a3),$22(a4)
		move.b	2(a3),$23(a4)
		move.b	4(a3),$24(a4)
		move.b	6(a3),$25(a4)
		rts

	ifd VERIFY
; Debug builds, with ExpMem: NewList saves what the two phases read or write (ListSave),
; builds the list, keeps what it wrote and puts the saved state back (ListDone), then runs
; the original phases on it from $48d4 (put back for the run); at their end ($4d44,
; ListCheck) everything they wrote is compared with NewList's, and the hook goes back.
; Low memory is filled with $cc: $1d0 counts the lists that differed and $1d4 the lists
; checked (from $cccccccc), $1d8 the first difference (the low word of $1d4 then, and the
; byte's offset in the regions: $000a 0, $0022 4, $111a 12, $46a2 268, $4eba 748, X 762,
; Y 763). $1dc counts NewList's course-piece entries and $1cc its lists that filled up.
EX_VLIST	= EX_TILES+TILESIZE	;ExpMem: the saved state, then NewList's
VL_SIZE		= 4+8+$100+$1e0+14+2	;$000a, $0022, $111a, $46a2, $4eba, X and Y

VLREGS		macro			;\1: copy the regions between (a4) and a1
		lea	$000a(a4),a0
		moveq	#4-1,d7
		bsr.b	\1
		lea	$0022(a4),a0
		moveq	#8-1,d7
		bsr.b	\1
		lea	$111a(a4),a0
		move.w	#$100-1,d7
		bsr.b	\1
		lea	$46a2(a4),a0
		move.w	#$1e0-1,d7
		bsr.b	\1
		lea	$4eba(a4),a0
		moveq	#14-1,d7
		bsr.b	\1
		endm

ListSave	movem.l	d7/a0-a1,-(sp)
		lea	(_v,pc),a0
		move.l	V_EXP(a0),d7
		beq.b	.no
		movea.l	d7,a1
		lea	EX_VLIST(a1),a1
		VLREGS	VLOut
.no		movem.l	(sp)+,d7/a0-a1
		rts
VLOut		move.b	(a0)+,(a1)+
		dbf	d7,VLOut
		rts
VLIn		move.b	(a1)+,(a0)+
		dbf	d7,VLIn
		rts

ListDone	movem.l	d6-d7/a0-a1,-(sp)
		lea	(_v,pc),a0
		move.l	V_EXP(a0),d6		;d7 counts in VLREGS
		beq.b	.no
		movea.l	d6,a1
		lea	EX_VLIST+VL_SIZE(a1),a1	;keep NewList's
		VLREGS	VLOut
		move.b	d1,(a1)+
		move.b	d2,(a1)+
		movea.l	d6,a1
		lea	EX_VLIST(a1),a1		;and put the input back
		VLREGS	VLIn
.no		movem.l	(sp)+,d6-d7/a0-a1
		rts

ListFlush	movem.l	d0-d1/a0-a2,-(sp)
		move.l	(_resload,pc),a2
		jsr	(resload_FlushCache,a2)
		movem.l	(sp)+,d0-d1/a0-a2
		rts

ListCheck	movem.l	d0-d7/a0-a6,-(sp)
		lea	(_v,pc),a0
		movea.l	V_EXP(a0),a1
		lea	EX_VLIST+VL_SIZE(a1),a1
		lea	$000a(a4),a0
		moveq	#0,d5			;bytes that differ
		moveq	#0,d6			;offset
		moveq	#4,d7
		bsr.b	.cmp
		lea	$0022(a4),a0
		moveq	#8,d7
		bsr.b	.cmp
		lea	$111a(a4),a0
		move.w	#$100,d7
		bsr.b	.cmp
		lea	$46a2(a4),a0
		move.w	#$1e0,d7
		bsr.b	.cmp
		lea	$4eba(a4),a0
		moveq	#14,d7
		bsr.b	.cmp
		move.b	d1,-(sp)		;X and Y
		movea.l	sp,a0
		moveq	#1,d7
		bsr.b	.cmp
		move.b	d2,(sp)
		movea.l	sp,a0
		moveq	#1,d7
		bsr.b	.cmp
		addq.w	#2,sp
		tst.w	d5
		beq.b	.same
		addq.l	#1,$1d0.w
.same		addq.l	#1,$1d4.w
		move.l	#$01384ef9,$48d4(a4)	;the hook back
		pea	NewList
		move.l	(sp)+,$48d8(a4)
		bsr	ListFlush
		movem.l	(sp)+,d0-d7/a0-a6
		move.b	d2,$4ebe(a4)		;displaced: STY $4ebe; STY $47a2
		move.b	d2,$47a2(a4)
		move.w	d2,d4
		lea	$4d4c(a4),a5
		jmp	$0122(a4)
.cmp		subq.w	#1,d7			;d7 bytes at a0 against a1; d5 counts
.c		cmpm.b	(a0)+,(a1)+		;differing bytes, d6 the offset
		beq.b	.ok
		addq.w	#1,d5
		cmp.l	#$cccccccc,$1d8.w	;the fill: none recorded yet
		bne.b	.ok
		move.w	$1d6.w,$1d8.w
		move.w	d6,$1da.w
.ok		addq.w	#1,d6
		dbf	d7,.c
		rts
	endc

	ifd VERIFY
; Debug builds: after each redraw, compare every cell of the back buffer with its tile in
; the hole block (chip, not the copy). $1f0 counts the cells that differ, $1f4 the
; frames checked, $1f8 holds the first difference's frame, row and column. $1e0, $1e4
; and $1e8 count the frames drawn at the same origin, scrolled and from nothing.
CheckCells	movem.l	d0-d7/a0-a6,-(sp)
		movem.w	V_NEW(a5),d1-d2
		movea.l	V_M(a5),a0
		move.w	$0ed2(a4),d3
		ror.w	#8,d3
		lsr.w	#2,d3
		add.w	d3,d3
		move.w	d2,d0
		lsr.w	#3,d0
		mulu	d3,d0
		adda.l	d0,a0
		move.w	d1,d0
		lsl.w	#2,d0
		adda.w	d0,a0
		move.w	d3,d4
		sub.w	#80,d4
		movea.l	V_P(a5),a3
		move.w	d2,d0
		and.w	#7,d0
		move.w	d0,-(sp)		;lines of the partial row
		mulu	#40,d0
		suba.w	d0,a3
		movea.l	V_M(a5),a6
		moveq	#0,d6
		moveq	#0,d7			;row
.vrow		moveq	#0,d5			;column
.vcell		move.w	(a0)+,d6
		lea	(a6,d6.l),a2
		movea.l	a3,a1
		moveq	#7,d3
		cmp.w	#20,d7
		bne.b	.vl
		move.w	(sp),d3
		subq.w	#1,d3
.vl		move.b	(a2)+,d0
		cmp.b	$6000(a1),d0
		bne.b	.bad
		move.b	(a2)+,d0
		cmp.b	$4000(a1),d0
		bne.b	.bad
		move.b	(a2)+,d0
		cmp.b	$2000(a1),d0
		bne.b	.bad
		move.b	(a2)+,d0
		cmp.b	(a1),d0
		bne.b	.bad
		lea	40(a1),a1
		dbf	d3,.vl
		bra.b	.vok
.bad		tst.l	$1f8.w
		bne.b	.counted
		move.w	$1f6.w,$1f8.w
		move.b	d7,$1fa.w
		move.b	d5,$1fb.w
.counted	addq.l	#1,$1f0.w
.vok		addq.w	#1,a3
		addq.w	#1,d5
		cmp.w	#40,d5
		bcs.b	.vcell
		adda.w	d4,a0
		lea	320-40(a3),a3
		addq.w	#1,d7
		cmp.w	#20,d7
		bcs.b	.vrow
		bhi.b	.vdone
		tst.w	(sp)
		bne.b	.vrow
.vdone		addq.w	#2,sp
		addq.l	#1,$1f4.w
		movem.l	(sp)+,d0-d7/a0-a6
		rts
	endc

_v		dcb.b	V_SIZE,0
		even

FixKey		move.w	4(sp),d0
		ror.b	#1,d0
		not.b	d0
		cmpi.b	#$59,d0		; cmpi as the shipped slave has it: vasm encodes cmp #,Dn as CMP
		bne	BeamDelay
		move.b	#9,$15ca2	;set 9 strokes
BeamDelay	moveq	#8,d0
BM_1		move.w  d0,-(sp)
		move.b	$dff006,d0
BM_2		cmp.b	$dff006,d0
		beq	BM_2
		move.w	(sp)+,d0
		dbf	d0,BM_1
		rts

Unsupported	pea	TDREASON_WRONGVER
_end		move.l	(_resload,pc),a2
		jmp	(resload_Abort,a2)

_resload	dc.l	0		;address of resident loader
_OSEmu		dc.b	'osemu.400',0
file		dc.b	"zany",0
dosname		dc.b	"dos.library",0