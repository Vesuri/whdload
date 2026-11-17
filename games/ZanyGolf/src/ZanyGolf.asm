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
_config		dc.b	"C1:L:Start on hole (debug):1. Windmill,2. Hamburger,3. Walls,4. Pinball,5. Fans,"
		dc.b	"6. Carpets,7. Castle,8. Ant Hill,9. Energy,10. Mystery",0
_name		dc.b	"Zany Golf",0
_copy		dc.b	"1988 Electronic Arts",0
_info		dc.b	"installed & fixed by Bored Seal",10
		dc.b	"enhanced by Vesuri",10
		dc.b	"V2.0b (17.11.2026)",0
		dc.b	"$VER: ZanyGolf.slave 2.0b (17.11.2026)",0
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
		move.w	#$4eb9,$5c2(a1)		;the load's delay: jsr LoadDelay
		pea	LoadDelay
		move.l	(sp)+,$5c4(a1)

		move.w	#$4ef9,$658(a1)
		pea	Patch
		move.l	(sp)+,$65a(a1)
		jmp	(a1)

LEW		macro			;\1: the little-endian word at the even address \1
		move.w	\1,\2
		ror.w	#8,\2
		endm
SEW		macro			;store \1 little-endian at the even address \2
		ror.w	#8,\1
		move.w	\1,\2
		ror.w	#8,\1
		endm
LEL		macro			;\1: the little-endian long at the even address \1
		move.l	\1,\2
		ror.w	#8,\2
		swap	\2
		ror.w	#8,\2
		endm
TBIT		macro			;bit \2 of \1 set: set bit \4 of \3
		btst	#\2,\1
		beq.b	.\@
		bset	#\4,\3
.\@
		endm

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

		move.w	#$4eb9,$1d78(a3)	;the input's mouse counts: jsr PtrTake,
		pea	PtrTake			;bra.w $1dc4
		move.l	(sp)+,$1d7a(a3)
		move.l	#$60000044,$1d7e(a3)

		move.w	#$4eb9,$1de2(a3)	;the input's mouse button: jsr ReadButton
		pea	ReadButton
		move.l	(sp)+,$1de4(a3)

		move.w	#$4eb9,$2912(a3)	;the delay $290c: jsr Delay, bra.s $2922
		pea	Delay
		move.l	(sp)+,$2914(a3)
		move.w	#$6008,$2918(a3)
		move.w	#$4eb9,$246a(a3)	;the fades' step delays: jsr FadeIn/Out, nop
		pea	FadeIn
		move.l	(sp)+,$246c(a3)
		move.w	#$4e71,$2470(a3)
		move.w	#$4eb9,$24a2(a3)
		pea	FadeOut
		move.l	(sp)+,$24a4(a3)
		move.w	#$4e71,$24a8(a3)

		lea	(_v,pc),a0
		tst.l	V_EXP(a0)
		beq.b	.norender
		move.w	#$4ef9,$14c4(a3)	;the renderer's tiles: jmp NewDraw
		pea	NewDraw
		move.l	(sp)+,$14c6(a3)
		move.w	#$4eb9,$173c(a3)	;the shape drawer: jsr ShapeHook
		pea	ShapeHook
		move.l	(sp)+,$173e(a3)
		movea.l	V_EXP(a0),a0		;the shape drawer: jmp NewShape
		lea	EX_STAB(a0),a0
		bsr	ShapeTable
		move.w	#$4ef9,$16f2(a3)
		pea	NewShape
		move.l	(sp)+,$16f4(a3)
	ifd VERIFY
		move.w	#$4ef9,$18d4(a3)	;the game's drawer's end: jmp ShapeCheck
		pea	ShapeCheck
		move.l	(sp)+,$18d6(a3)
	endc
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
.hole1		bsr	PtrInit			;the pointer as sprites
		bsr	IpInit			;frames between the steps
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
		move.l	_ptrnext-_lastflip(a0),_ptrview-_lastflip(a0) ;the frame drawn last
		move.l	$1474(a4),_ptrnext-_lastflip(a0)	;shows, this one's view next
		move.b	_ptrwant-_lastflip(a0),_ptron-_lastflip(a0)	;and its pointer
		cmp.w	#PTR_VBL,d1		;from this field: the pointer on it
		bcc.b	.later
		movem.l	d0-d6/a1-a3/a6,-(sp)
		moveq	#1,d6
		bsr	PtrPlace
		movem.l	(sp)+,d0-d6/a1-a3/a6
.later
		move.w	d0,$2312(a4)		;displaced: the fine scroll
		movem.l	(sp)+,d1/a0
		move.w	#$8000,d0		;displaced
		rts

BeamLine	move.l	d0,-(sp)		;d1: the beam's line (VPOSR, VHPOSR)
.read		move.l	$dff004,d0		;two word reads: from line 255 to 256
		move.l	$dff004,d1		;between them they give V8 of 255 and
		eor.l	d1,d0			;the low byte of 256, line 0. So until
		and.l	#$1ff00,d0		;two reads give the same line
		bne.b	.read
		lsr.l	#8,d1
		and.w	#$1ff,d1
		move.l	(sp)+,d0
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
_ptrview	dc.w	0,0			;the view of the frame on screen (PtrVbi)
_ptrnext	dc.w	0,0			;of the frame drawn last
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
; - flag set and fewer: draw only (DrawOnly), between the last two steps (Present), and
;   loop. $4fd0 draws the course pieces that have come into view (it clears their bit 0
;   in $111a); what it reads (the view, the pieces and their bits) changes only in a step
;   or with the view drawn, so while neither changed since its last run it would find
;   nothing, and DrawOnly starts after it.
; A step can change the flag (the pause screen clears it), and the next pass tests it again,
; as the game's own next pass did.
; Steps are due every STEP_FIELDS fields by the field counter; a step more than one step
; late restarts the schedule from now, so a slow machine steps every pass as before and
; never catches up in a burst. With the interrupts off the counter stops, so every pass
; steps. a4 is FILE1's base, d7 and a0 are scratch in the threaded code.
STEP_FIELDS	= 6
Split		bsr	SkipIntro
		bsr	PollButton
		LEW	$5e1c(a4),d7		;between two steps: where the last put
		swap	d7			;the pointer (it may have moved it itself)
		LEW	$5e1e(a4),d7
		lea	(_ptrbase,pc),a0
		move.l	d7,(a0)
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
		bsr	IpSnap			;the state before the step
		bra.b	.step
.late		move.b	$145c(a4),(a0)
		bsr	IpCut			;late: no frames between
.step		lea	(_stepped,pc),a0
		st	(a0)
		lea	$524c(a4),a5		;JSR $1d5a; JSR $62b2; JMP $5232
		jmp	$0122(a4)		;dispatch
.draw		bsr	Present			;d7: the fields since the step was due
		lea	(_stepped,pc),a0
		lea	(DrawOnly,pc),a5
		move.l	$0e9c(a4),d7		;the view $4fd0 would read
		tst.b	(a0)
		bne.b	.full
		cmp.l	_lastview-_stepped(a0),d7
		beq.b	.lite
.full		clr.b	(a0)
		move.l	d7,_lastview-_stepped(a0)
		jmp	$0122(a4)
.lite		addq.w	#4,a5			;no step since $4fd0 last ran: skip it
		jmp	$0122(a4)
.update		move.b	$145c(a4),d7		;the first pass with the flag set steps
		subq.b	#STEP_FIELDS,d7
		move.b	d7,(a0)
.off		lea	(_v+V_RESET,pc),a0	;no frames now (a hole may load): NewDraw
		st	(a0)			;starts again from nothing
		bsr	PtrOff
		bsr	IpCut
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
		dc.w	$0138			;native: the world's state back
		bra.w	Restore
DrawEnd		dc.w	$0438,$5232		;JMP $5232

_lastview	dc.w	0,0			;the view $4fd0 last ran with
_laststep	dc.b	0
_stepped	dc.b	0			;a step ran since $4fd0 last did
		even

;=============================================================================
; Frames between the steps. A step changes the world every 6 fields; the draw-only
; passes between show it (Split). IpSnap keeps, before each step, what the frames draw
; moving things from: the view ($0e9c/$0e9e) and the 32 objects' x and y ($0f5a/$0f9a)
; and frames ($0f1a), with what tells an object's moves from a cut (active $0fda, shape
; $0eda, shape set $105a, the state $0ea8 and the hole $5c5a). Present, before a
; draw-only pass, puts in their place, for the pass only, (Restore puts the world's back
; after it):
; - the view and each object that moved less than IP_JUMP on each axis, between the
;   step before and the last, (fields since the step was due + 1)/6 of the way, to the
;   nearest pixel, and for the first half the step before's frame of the object, so an
;   animation keeps with its moves: the frame, shown from the next field, is a step
;   behind the world at most; an object that has moved on this screen (IpSnap) and whose
;   frame changed by its frame's box, x its middle and y its bottom, between the two
;   frames' (.anim);
; - the course pieces each step draws over the objects, on every pass (.mask);
; - while the player points or draws a stroke back ($5e1a 0, $9676 0 or 1, in play):
;   the pointer ($5e1c), where the next step will put it by the counts gathered so far
;   (PtrPredict), and what the step makes of it: the view, scrolled as $8afe scrolls it,
;   the pointer's object ($8dd6) or, drawing back, the ball's mark, the three dots
;   and the pointer's object ($8e0c). The sprite and these then move together.
; Without the buffer (IpInit) the frames between show the last step.
IP_JUMP		= 96			;a move longer than this is a cut
IP_PREV		= 0			;x 64, y 64, active 64, shape 64, set 64, view 4,
IP_PSTATE	= 324			;state, hole
IP_SAVE		= 326			;$0f1a-$1019, view 4, pointer 4
IP_MASK		= IP_SAVE+256+8		;the last step's pieces: bit 1 of $111a 64, $119a 64,
IP_MASKP	= IP_MASK+128		;the step before's the same
IP_MSAVE	= IP_MASKP+128		;$111a 64, $119a 64, for Restore
IP_PFRAME	= IP_MSAVE+128		;the step before's frames ($0f1a) 64
IP_MOVED	= IP_PFRAME+64		;each object moved on this screen: 64
IP_SIZE		= IP_MOVED+64

IpInit		movem.l	d0-d1/a0-a1/a6,-(sp)
		move.l	#IP_SIZE,d0
		move.l	#$10001,d1		;MEMF_PUBLIC|MEMF_CLEAR
		movea.l	4.w,a6
		jsr	-198(a6)		;AllocMem
		lea	(_ipbuf,pc),a0
		move.l	d0,(a0)
		movem.l	(sp)+,d0-d1/a0-a1/a6
		rts

; Before a step (Split; d7 and a0 scratch).
IpSnap		movem.l	d0-d1/a1-a2,-(sp)
		move.l	(_ipbuf,pc),d0
		beq	.out
		movea.l	d0,a1
		moveq	#0,d1			;X: marks the objects that moved since
		move.b	$0ea8(a4),d0		;the last snapshot, on the same screen
		cmp.b	IP_PSTATE(a1),d0	;and hole, with the same shape
		bne.b	.mclr
		move.b	$5c5a(a4),d0
		cmp.b	IP_PSTATE+1(a1),d0
		bne.b	.mclr
.mobj		lea	(a4,d1.w),a0
		lea	(a1,d1.w),a2
		tst.b	$0fda(a0)
		beq.b	.mnot
		tst.b	128(a2)
		beq.b	.mnot
		move.b	$0eda(a0),d0
		cmp.b	192(a2),d0
		bne.b	.mnot
		move.w	$0f5a(a0),d0
		cmp.w	(a2),d0
		bne.b	.mset
		move.w	$0f9a(a0),d0
		cmp.w	64(a2),d0
		beq.b	.mnext
.mset		st	IP_MOVED(a2)
		bra.b	.mnext
.mnot		clr.b	IP_MOVED(a2)
.mnext		addq.w	#2,d1
		cmp.w	#64,d1
		bne.b	.mobj
		bra.b	.snap
.mclr		lea	IP_MOVED(a1),a2
		moveq	#64/4-1,d0
.mc		clr.l	(a2)+
		dbf	d0,.mc
.snap		lea	$0f5a(a4),a2		;x, y, active
		moveq	#192/4-1,d0
.xya		move.l	(a2)+,(a1)+
		dbf	d0,.xya
		lea	$0eda(a4),a2
		moveq	#64/4-1,d0
.shape		move.l	(a2)+,(a1)+
		dbf	d0,.shape
		lea	$105a(a4),a2
		moveq	#64/4-1,d0
.set		move.l	(a2)+,(a1)+
		dbf	d0,.set
		move.l	$0e9c(a4),(a1)+
		move.b	$0ea8(a4),(a1)+
		move.b	$5c5a(a4),(a1)+
		lea	IP_PFRAME-IP_SAVE(a1),a1
		lea	$0f1a(a4),a2
		moveq	#64/4-1,d0
.frame		move.l	(a2)+,(a1)+
		dbf	d0,.frame
		lea	(_ipvalid,pc),a2
		st	(a2)
.out		movem.l	(sp)+,d0-d1/a1-a2
		rts

IpCut		lea	(_ipvalid,pc),a0	;no step before to draw from
		clr.b	(a0)
		rts

; Before a draw-only pass (Split): d7 the fields since the step was due (0-5). Keeps
; all registers but d7 and a0.
Present		movem.l	d0-d6/a1-a3,-(sp)
		move.l	(_ipbuf,pc),d0
		beq	.out
		movea.l	d0,a1
		lea	IP_SAVE(a1),a2		;the world's, for Restore
		lea	$0f1a(a4),a0
		moveq	#256/4-1,d0
.save		move.l	(a0)+,(a2)+
		dbf	d0,.save
		move.l	$0e9c(a4),(a2)+
		move.l	$5e1c(a4),(a2)+
		lea	(_ipin,pc),a0
		st	(a0)
		moveq	#0,d6
		move.b	d7,d6
		addq.w	#1,d6			;the way from the step before: d6/6
		moveq	#0,d5			;d5: the step before is drawn from
		tst.b	_ipvalid-_ipin(a0)
		beq.b	.nosame
		move.b	$0ea8(a4),d0		;the same screen and hole
		cmp.b	IP_PSTATE(a1),d0
		bne.b	.nosame
		move.b	$5c5a(a4),d0
		cmp.b	IP_PSTATE+1(a1),d0
		bne.b	.nosame
		moveq	#1,d5
.nosame		bsr	.mask
		tst.b	d5
		beq	.ptr
		moveq	#0,d1			;X: the object
.obj		lea	(a4,d1.w),a0
		lea	(a1,d1.w),a2
		tst.b	$0fda(a0)
		beq.b	.onext
		tst.b	128(a2)
		beq.b	.onext
		move.b	$0eda(a0),d0
		cmp.b	192(a2),d0
		bne.b	.onext
		move.w	$105a(a0),d0
		cmp.w	256(a2),d0
		bne.b	.onext
		LEW	(a2),d2
		LEW	$0f5a(a0),d3
		bsr	.lerp
		bcs.b	.onext
		move.w	d3,d5
		LEW	64(a2),d2
		LEW	$0f9a(a0),d3
		bsr	.lerp
		bcs.b	.onext
		move.b	IP_PFRAME(a2),d0	;a new frame: the frames' boxes
		cmp.b	$0f1a(a0),d0		;between the steps instead
		beq.b	.oput
		tst.b	IP_MOVED(a2)		;not an animation in place
		beq.b	.oput
		bsr	.anim
.oput		SEW	d5,$0f5a(a0)
		SEW	d3,$0f9a(a0)
		cmp.w	#3,d6			;the frame with the position: the step
		bcc.b	.onext			;before's for the first half
		move.b	IP_PFRAME(a2),$0f1a(a0)
.onext		addq.w	#2,d1
		cmp.w	#$40,d1
		bne	.obj
		LEW	320(a1),d2		;the view
		LEW	$0e9c(a4),d3
		bsr	.lerp
		bcs.b	.ptr
		move.w	d3,d5
		LEW	322(a1),d2
		LEW	$0e9e(a4),d3
		bsr	.lerp
		bcs.b	.ptr
		SEW	d5,$0e9c(a4)
		SEW	d3,$0e9e(a4)

.ptr		cmp.b	#4,$0ea8(a4)		;in play, the ball at rest
		bne	.out
		tst.b	$0fda(a4)
		beq	.out
		tst.b	$5e1a(a4)
		bne	.out
		lea	$4000(a4),a0
		move.b	$9676-$4000(a0),d6
		cmp.b	#2,d6
		bcc	.out
		lea	IP_SAVE+8(a1),a0	;objects 4-8 are the next step's: its
		lea	$0f22(a4),a2		;frames
		moveq	#10-1,d0
.pframe		move.b	(a0)+,(a2)+
		dbf	d0,.pframe
		bsr	PtrPredict		;d0, d1: the pointer the step will see
		SEW	d0,$5e1c(a4)
		SEW	d1,$5e1e(a4)
		LEW	IP_SAVE+256(a1),d2	;the view the step scrolls ($8afe)
		move.w	d0,d3
		subq.w	#8,d3
		cmp.w	d2,d3
		bge.b	.vx1
		move.w	d3,d2
.vx1		move.w	d0,d3
		add.w	#8-$130,d3
		cmp.w	d2,d3
		blt.b	.vx2
		move.w	d3,d2
.vx2		SEW	d2,$0e9c(a4)
		LEW	IP_SAVE+258(a1),d2
		move.w	d1,d3
		subq.w	#8,d3
		cmp.w	d2,d3
		bge.b	.vy1
		move.w	d3,d2
.vy1		moveq	#0,d4
		move.b	$11e6(a4),d4
		move.w	d1,d3
		addq.w	#8,d3
		sub.w	d4,d3
		cmp.w	d2,d3
		blt.b	.vy2
		move.w	d3,d2
.vy2		SEW	d2,$0e9e(a4)
		subq.w	#8,d0			;the pointer's object at it less 8
		subq.w	#8,d1
		tst.b	d6
		bne.b	.back
		SEW	d0,$0f62(a4)		;object 4 ($8dd6)
		SEW	d1,$0fa2(a4)
		bra	.out
.back		SEW	d0,$0f6a(a4)		;$8e0c: object 8 the pointer,
		SEW	d1,$0faa(a4)
		LEW	$5df0(a4),d2		;4 the ball's mark
		subq.w	#8,d2
		SEW	d2,$0f62(a4)
		LEW	$5df2(a4),d3
		subq.w	#8,d3
		SEW	d3,$0fa2(a4)
		sub.w	d2,d0			;dx, dy from the ball
		sub.w	d3,d1
		moveq	#1,d4
		move.b	d4,$0fe2(a4)		;4-7 on, the mark's frame 1
		move.b	d4,$0fe4(a4)
		move.b	d4,$0fe6(a4)
		move.b	d4,$0fe8(a4)
		move.b	d4,$0f22(a4)
		move.w	d0,d4			;|dx| + |dy| under 256: the dots
		bpl.b	.ax
		neg.w	d4
.ax		move.w	d1,d5
		bpl.b	.ay
		neg.w	d5
.ay		cmp.w	#4,d4			;on the ball ($9148): the mark's frame 0
		bcc.b	.off
		cmp.w	#4,d5
		bcc.b	.off
		clr.b	$0f22(a4)
.off		add.w	d5,d4
		cmp.w	#$100,d4		;nearer than 8 from the ball are off
		bcc.b	.dots
		lsr.b	#1,d4
		cmp.b	#8,d4
		bcc.b	.d6
		clr.b	$0fe6(a4)
.d6		move.b	d4,d5
		lsr.b	#1,d5
		add.b	d4,d5
		cmp.b	#8,d5
		bcc.b	.d7
		clr.b	$0fe8(a4)
.d7		lsr.b	#1,d4
		cmp.b	#8,d4
		bcc.b	.dots
		clr.b	$0fe4(a4)
.dots		asr.w	#1,d0			;6 halfway, 5 and 7 a quarter each side
		asr.w	#1,d1
		move.w	d2,d4
		add.w	d0,d4
		SEW	d4,$0f66(a4)
		move.w	d3,d5
		add.w	d1,d5
		SEW	d5,$0fa6(a4)
		asr.w	#1,d0
		asr.w	#1,d1
		add.w	d0,d2
		SEW	d2,$0f64(a4)
		add.w	d1,d3
		SEW	d3,$0fa4(a4)
		add.w	d0,d4
		SEW	d4,$0f68(a4)
		add.w	d1,d5
		SEW	d5,$0fa8(a4)
.out		movem.l	(sp)+,d0-d6/a1-a3
		rts
; The course pieces drawn over the objects. Each step flags the piece under each moving
; object ($9faa: bit 1 of $111a,X, with the depth $119a,X from the object's y) and the
; draw list draws the flagged ones that are visible over the shapes, clearing the flag
; ($4d20): only the first frame after a step would have them. The first pass after a
; step keeps the flags and depths; each pass flags the last step's pieces and, drawn
; from the step before (d5), that step's too, with the nearer depth. Restore puts the
; world's back, less the flags the list cleared of them. a1 the buffer; keeps d5-d6.
.mask		lea	$111a(a4),a0
		lea	IP_MSAVE(a1),a2
		moveq	#64/4-1,d0
.msave		move.l	(a0)+,(a2)+
		dbf	d0,.msave
		lea	$119a(a4),a0
		moveq	#64/4-1,d0
.msave2		move.l	(a0)+,(a2)+
		dbf	d0,.msave2
		lea	(_stepped,pc),a0	;the first pass after a step
		tst.b	(a0)
		beq.b	.mput
		lea	IP_MASK(a1),a2
		moveq	#128/4-1,d0
.mshift		move.l	(a2),d1			;the last step's become the step before's
		tst.b	d5
		bne.b	.mkeep
		moveq	#0,d1
.mkeep		move.l	d1,IP_MASKP-IP_MASK(a2)
		addq.w	#4,a2
		dbf	d0,.mshift
		lea	IP_MASK(a1),a2
		lea	$111a(a4),a0
		moveq	#64-1,d0
.mflag		move.b	(a0)+,d1
		and.b	#2,d1
		move.b	d1,(a2)+
		dbf	d0,.mflag
		lea	$119a(a4),a0
		moveq	#64/4-1,d0
.mdepth		move.l	(a0)+,(a2)+
		dbf	d0,.mdepth
.mput		lea	IP_MASK(a1),a2
		lea	IP_MASKP(a1),a3
		lea	$115a(a4),a0		;between $111a and $119a
		moveq	#0,d1			;X: the piece
.mpiece		move.b	(a2,d1.w),d0
		LEW	64(a2,d1.w),d2
		tst.b	d5
		beq.b	.mone
		or.b	(a3,d1.w),d0
		LEW	64(a3,d1.w),d3
		cmp.w	d2,d3
		bcc.b	.mone
		move.w	d3,d2
.mone		tst.b	d0
		beq.b	.mnext
		bset	#1,$111a-$115a(a0,d1.w)
		SEW	d2,$119a-$115a(a0,d1.w)
.mnext		addq.w	#2,d1
		cmp.w	#64,d1
		bne.b	.mpiece
		rts

; An object whose frame changed (a0 it in the table, a2 in the buffer, d0 the step
; before's frame): d5 and d3 its x and y, the shown frame placed for the middle of its
; box (x) and its bottom (y) to be d6/6 of the way between the two frames'. The burger
; of hole 2 grows down from its top, 2 to 5 lines a frame, while the game moves it up by
; about as much: its bottom bun then stays put and its top takes the frame's change,
; where with its top interpolated its bottom jumped at each frame.
.anim		movem.l	d1/d7,-(sp)
		bsr.b	.fmid			;the step before's frame's box
		move.w	d4,d1
		move.w	d5,d7
		move.b	$0f1a(a0),d0
		bsr.b	.fmid			;the last's
		move.w	d5,-(sp)
		move.w	d4,d5
		move.w	d1,d4
		LEW	(a2),d0
		LEW	$0f5a(a0),d3
		bsr.b	.half
		move.w	d3,d1
		move.w	d7,d4
		move.w	(sp)+,d5
		LEW	64(a2),d0
		LEW	$0f9a(a0),d3
		bsr.b	.half
		move.w	d1,d5
		movem.l	(sp)+,d1/d7
		rts

; d0 the frame of the object a0: d4 the middle of its frame's box and d5 its bottom,
; from the position in half pixels (as Frame and NewShape find the record: x from byte 0
; and the width, y from the first line, byte 2, and the rows). d0, a3.
.fmid		LEW	$109a(a0),d4		;the shape set
		swap	d4
		LEW	$105a(a0),d4
		lea	(a4,d4.l),a3
		moveq	#0,d4
		move.b	$0eda(a0),d4
		lsl.w	#3,d4
		move.w	(a3,d4.w),d4		;the shape's frames
		ror.w	#8,d4
		and.w	#$ff,d0
		add.w	d0,d0
		add.w	d0,d4
		move.w	(a3,d4.w),d4		;the frame's record
		ror.w	#8,d4
		adda.w	d4,a3
		moveq	#0,d0
		moveq	#0,d4
		move.b	(a3),d4
		add.w	d4,d4
		move.b	4(a3),d0
		add.w	d0,d4
		move.b	2(a3),d5		;y: the bottom, below its last line
		ext.w	d5
		move.b	6(a3),d0
		add.w	d0,d5
		add.w	d5,d5
		rts

; d0 the step before's position, d3 the last's, d4 and d5 their frames' points (half
; pixels): d3 where the shown frame goes (the step before's for d6 below 3).
.half		add.w	d0,d0
		add.w	d4,d0
		move.w	d0,d2
		add.w	d3,d3
		add.w	d5,d3
		cmp.w	#3,d6
		bcc.b	.hcur
		move.w	d4,d5
.hcur		bsr.b	.lerpn
		sub.w	d5,d3
		asr.w	#1,d3
		rts

; d2 the step before's, d3 the last's: d3 d6/6 of the way, to the nearest pixel (a
; half away from 0, so a pixel's move comes at d6 3, with the frame). Carry set: a cut.
.lerp		sub.w	d2,d3
		beq.b	.same
		move.w	d3,d4
		bpl.b	.lpos
		neg.w	d4
.lpos		cmp.w	#IP_JUMP,d4
		bhi.b	.cut
.lmul		muls	d6,d3
		add.w	d3,d3
		bmi.b	.lneg
		addq.w	#6,d3
		bra.b	.ldiv
.lneg		subq.w	#6,d3
.ldiv		divs	#12,d3
.same		add.w	d2,d3
		moveq	#0,d4			;carry clear
		rts
.cut		ori	#1,ccr
		rts

.lerpn		sub.w	d2,d3			;the same without the cut
		bra.b	.lmul

; After a draw-only pass (DrawOnly, native from primitive $0138): the world's state
; back, then on to the thread's JMP $5232.
Restore		movem.l	d0-d1/a1-a2,-(sp)
		lea	(_ipin,pc),a0
		tst.b	(a0)
		beq.b	.go
		clr.b	(a0)
		movea.l	(_ipbuf,pc),a1
		lea	IP_SAVE(a1),a1
		lea	$0f1a(a4),a2
		moveq	#256/4-1,d0
.back		move.l	(a1)+,(a2)+
		dbf	d0,.back
		move.l	(a1)+,$0e9c(a4)
		move.l	(a1)+,$5e1c(a4)
		lea	IP_MSAVE-IP_SAVE-264(a1),a1	;the pieces' flags: the world's, less
		lea	$111a(a4),a2		;those the list cleared
		moveq	#64/4-1,d0
.flags		move.l	(a2),d1
		or.l	#$fdfdfdfd,d1
		and.l	(a1)+,d1
		move.l	d1,(a2)+
		dbf	d0,.flags
		lea	$119a(a4),a2
		moveq	#64/4-1,d0
.depths		move.l	(a1)+,(a2)+
		dbf	d0,.depths
.go		movem.l	(sp)+,d0-d1/a1-a2
		lea	(DrawEnd,pc),a5
		jmp	$0122(a4)

_ipbuf		dc.l	0			;IP_SIZE, public; 0 none
_ipvalid	dc.b	0			;IpSnap kept the step before
_ipin		dc.b	0			;Present put its state in
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
; The pointer. The game draws it as an object, a shape in the frame, at the pointer's
; position on the course map ($5e1c x, $5e1e y, little-endian) less 8: object 4 (X=8)
; while the player points ($9676 0), object 8 (X=$10) while a stroke is drawn back ($9676
; 1). Each step moves the position by the input routine's ($1d5c) quarter of the mouse's
; counts, clamped to +-31 ($0e80/$0e88; the counts beyond are lost, each axis on its own),
; and keeps it 8 pixels inside the hole ($5e20/$5e22) and the view, which it scrolls. With
; a chip block (PtrInit), sprites 0 and 1, attached (15 colours, COLOR17-31 copied from the
; playfield's), show it instead, moved by the interrupt every field:
; - PtrTake takes the counts in the input routine's place, with the clamp PTR_MAX
;   (always, sprites or not: shown every field, the clamped axis stopped while the other
;   went on, and a fast straight stroke wobbled), and keeps where the step puts the
;   pointer (_ptrbase);
; - PtrVbi, at each vertical blank, places the sprites at PtrPredict (_ptrbase plus the
;   quarter of the counts gathered since, clamped as the next step will clamp them) in
;   the view of the frame on screen (which FrameCap keeps at the flip); the frames
;   between the steps scroll the view and draw the aiming line for that point too
;   (Present);
; - PtrList, after the draw list, takes the pointer's entry out of the list and draws its
;   frame into the sprites when the frame changed; the sprites show from the flip that
;   shows the frame (FrameCap). A frame wider than 16 pixels or taller
;   than PTR_H lines stays a shape.
; The copper list ($2274) turned the sprite DMA off at line $90 and cleared the sprites'
; data registers: its tail now loads the eight sprite pointers below the playfield (line
; $f8; 2-7 an empty sprite), and its top turns the sprite DMA on and puts sprites 0 and 1
; in front of the playfield (BPLCON2). Without the block the game draws the pointer.
PTR_H		= 32			;lines a sprite holds
PTR_SPR		= 4+4*PTR_H+4		;a sprite: position, control, PTR_H lines, the end
PTR_SIZE	= 2*PTR_SPR+8		;sprites 0 and 1, the empty sprite
PTR_HPOS	= $7f			;HSTART at the view's left edge
PTR_VPOS	= $52			;VSTART at its top: the playfield's first line
PTR_VBL		= $48			;the interrupt's runs before this line are the VERTB's
PTR_MAX		= 100			;a step's move from the mouse, at most (the game's 31;
					;the cursor keys add up to 14 to the signed byte)

PtrInit		movem.l	d0-d2/a0-a2/a6,-(sp)	;a3 = FILE1
		move.l	#PTR_SIZE,d0
		move.l	#$10002,d1		;MEMF_CHIP|MEMF_CLEAR
		movea.l	4.w,a6
		jsr	-198(a6)		;AllocMem
		tst.l	d0
		beq	.no
		lea	(_ptrspr,pc),a0
		move.l	d0,(a0)
		movea.l	d0,a1
		lea	2*PTR_SPR(a1),a2	;the empty sprite
		lea	$dff120,a0		;until the copper list loads them
		moveq	#8-1,d1
.null		move.l	a2,(a0)+
		dbf	d1,.null
		move.l	#$01040024,$22b0(a3)	;the copper list's top: BPLCON2, sprites
		move.l	#$00968020,$22b4(a3)	;in front; DMACON, sprites on
		move.l	#$f801ff00,$2338(a3)	;its tail: wait for line $f8, then the
		lea	$233c(a3),a0		;pointers
		move.w	#$0120,d1
		move.l	a1,d0			;sprite 0
		bsr.b	.ptr
		lea	PTR_SPR(a1),a6
		move.l	a6,d0			;sprite 1
		bsr.b	.ptr
		moveq	#6-1,d2
.rest		move.l	a2,d0
		bsr.b	.ptr
		dbf	d2,.rest
		move.w	#$4eb9,$2246(a3)	;the interrupt: jsr PtrVbi; nop over
		pea	PtrVbi			;bsr.w $1f0c; tst.b $126e(a4)
		move.l	(sp)+,$2248(a3)
		move.w	#$4e71,$224c(a3)
.no		movem.l	(sp)+,d0-d2/a0-a2/a6
		rts
.ptr		swap	d0			;the moves for SPRxPTH and SPRxPTL
		move.w	d1,(a0)+
		move.w	d0,(a0)+
		addq.w	#2,d1
		swap	d0
		move.w	d1,(a0)+
		move.w	d0,(a0)+
		addq.w	#2,d1
		rts

; The input routine's counts ($1d78-$1dc3; a4 = FILE1, d0-d2 and a0 free): for each
; axis a quarter of the counts the interrupt gathered ($1d54/$1d56), the remainder of 4
; left, clamped to +-PTR_MAX into $0e80/$0e88, with the interrupts off, so PtrVbi never
; sees the counts taken and the pointer not yet moved. Keeps where the step will put the
; pointer (_ptrbase: the position plus the counts, clamped as $92de and $8afe clamp it).
PtrTake		movem.l	d3-d4,-(sp)
		move.w	$dff01c,d4		;INTENAR
		move.w	#$4000,$dff09a		;the interrupts off
		lea	$1d54(a4),a0
		bsr.b	.take
		move.b	d0,$0e80(a4)
		move.w	d0,d3
		lea	$1d56(a4),a0
		bsr.b	.take
		move.b	d0,$0e88(a4)
		move.w	d0,d1
		LEW	$5e1e(a4),d0
		add.w	d0,d1
		LEW	$5e1c(a4),d0
		add.w	d3,d0
		bsr	PtrClamp
		swap	d0
		move.w	d1,d0
		lea	(_ptrbase,pc),a0
		move.l	d0,(a0)
		btst	#14,d4
		beq.b	.off
		move.w	#$c000,$dff09a		;back on
.off		movem.l	(sp)+,d3-d4
		rts
.take		move.w	(a0),d0
		asr.w	#2,d0
		move.w	d0,d1
		asl.w	#2,d1
		sub.w	d1,(a0)
		bra.b	PtrQ

; d0: a quarter of the counts, clamped as the input routine clamps it.
PtrQ		cmp.w	#PTR_MAX,d0
		ble.b	.lo
		moveq	#PTR_MAX,d0
.lo		cmp.w	#-PTR_MAX,d0
		bge.b	.ok
		moveq	#-PTR_MAX,d0
.ok		rts

; Where the next step puts the pointer: _ptrbase plus the counts gathered since,
; clamped. Out: d0 x, d1 y. Keeps the other registers.
PtrPredict	move.l	d2,-(sp)
		move.w	$1d54(a4),d0
		asr.w	#2,d0
		bsr.b	PtrQ
		add.w	(_ptrbase,pc),d0
		move.w	d0,d2
		move.w	$1d56(a4),d0
		asr.w	#2,d0
		bsr.b	PtrQ
		add.w	(_ptrbase+2,pc),d0
		move.w	d0,d1
		move.w	d2,d0
		move.l	(sp)+,d2		;and on into PtrClamp

; Clamp the pointer d0 (x), d1 (y) as the step does: while a stroke is drawn back ($9676
; 1) into the box around the ball ($92de: $34 left of $5df0 to $33 right, $24 above
; $5df2 to $23 below), then 8 pixels inside the hole ($8afe). Keeps the other registers.
PtrClamp	movem.l	d2-d3/a0,-(sp)
		lea	$4000(a4),a0
		cmp.b	#1,$9676-$4000(a0)
		bne.b	.hole
		LEW	$5df0(a4),d2
		sub.w	#$34,d2
		move.w	d0,d3
		sub.w	d2,d3
		bpl.b	.bx
		move.w	d2,d0
		bra.b	.by
.bx		cmp.w	#$68,d3
		bcs.b	.by
		add.w	#$67,d2
		move.w	d2,d0
.by		LEW	$5df2(a4),d2
		sub.w	#$24,d2
		move.w	d1,d3
		sub.w	d2,d3
		bpl.b	.by1
		move.w	d2,d1
		bra.b	.hole
.by1		cmp.w	#$48,d3
		bcs.b	.hole
		add.w	#$47,d2
		move.w	d2,d1
.hole		cmp.w	#8,d0
		bge.b	.h1
		moveq	#8,d0
.h1		LEW	$5e20(a4),d2
		subq.w	#8,d2
		cmp.w	d2,d0
		blt.b	.h2
		move.w	d2,d0
.h2		cmp.w	#8,d1
		bge.b	.h3
		moveq	#8,d1
.h3		LEW	$5e22(a4),d2
		subq.w	#8,d2
		cmp.w	d2,d1
		blt.b	.h4
		move.w	d2,d1
.h4		movem.l	(sp)+,d2-d3/a0
		rts

; From the interrupt ($2246), after it has added the mouse's counts; a4 = FILE1. Keeps
; every register.
PtrVbi		movem.l	d0-d6/a1-a3/a6,-(sp)
		bsr	BeamLine
		cmp.w	#PTR_VBL,d1
		bcc.b	.done
		moveq	#0,d6			;the sprites' control words
		bsr.b	PtrPlace
.done		movem.l	(sp)+,d0-d6/a1-a3/a6
		jsr	$1f0c(a4)		;displaced
		tst.b	$126e(a4)
		rts

; Place the sprites (or hide them): their control words, which the sprite DMA loads
; after the vertical blank, and with d6 set their registers too, for a frame that shows
; from this field after that (FrameCap). d0-d5, a1-a3, a6.
PtrPlace	move.l	(_ptrspr,pc),d0
		beq	.out
		movea.l	d0,a1
		lea	(_ptron,pc),a2
		moveq	#0,d0
		moveq	#0,d2
		tst.b	(a2)
		beq	.put
		lea	$22ba+4(a4),a3		;the copper list's COLOR01-15
		moveq	#15-1,d1
		lea	$dff1a2,a6		;COLOR17-31
.col		move.w	(a3),(a6)+
		addq.w	#4,a3
		dbf	d1,.col
		bsr	PtrPredict		;on the course
		sub.w	_ptrview-_ptron(a2),d0	;in the view of the frame on screen
		move.w	#$128,d4
		bsr	.screen
		move.w	d0,d5
		add.w	_ptroff-_ptron(a2),d5
		add.w	#PTR_HPOS,d5		;HSTART
		move.w	d1,d0
		sub.w	_ptrview+2-_ptron(a2),d0
		moveq	#0,d4
		move.b	$11e6(a4),d4
		subq.w	#8,d4
		bsr	.screen
		add.w	_ptroff+2-_ptron(a2),d0
		add.w	#PTR_VPOS,d0		;VSTART
		move.w	d0,d1
		add.w	_ptrh-_ptron(a2),d1	;VSTOP
		moveq	#0,d2			;the control word: VSTOP, the high bits
		move.w	d1,d2
		lsl.w	#8,d2
		btst	#8,d0
		beq.b	.v8
		addq.w	#4,d2
.v8		btst	#8,d1
		beq.b	.e8
		addq.w	#2,d2
.e8		lsr.w	#1,d5
		bcc.b	.h0
		addq.w	#1,d2
.h0		lsl.w	#8,d0			;the position word: VSTART, HSTART/2
		move.b	d5,d0
.put		move.w	d0,(a1)
		move.w	d2,2(a1)
		move.w	d0,PTR_SPR(a1)
		tst.w	d2
		beq.b	.att
		or.w	#$80,d2			;attached
.att		move.w	d2,PTR_SPR+2(a1)
		tst.b	d6
		beq.b	.out
		lea	$dff140,a3		;SPR0POS
		move.w	d0,8(a3)		;SPR1POS, CTL, then sprite 0's
		move.w	d2,10(a3)
		and.w	#$ff7f,d2
		move.w	d0,(a3)
		move.w	d2,2(a3)
.out		rts

; d0 into 8 to d4, the pointer's places in the view.
.screen		cmp.w	#8,d0
		bge.b	.s1
		moveq	#8,d0
.s1		cmp.w	d4,d0
		ble.b	.s2
		move.w	d4,d0
.s2		rts

; No pointer until a frame is drawn again (Split, the drawing flag clear or the
; interrupts off: a hole may load, with new shapes). Only d7 and a0.
PtrOff		lea	(_ptron,pc),a0
		clr.b	(a0)
		clr.b	_ptrwant-_ptron(a0)
		clr.l	_ptrrec-_ptron(a0)
		move.l	_ptrspr-_ptron(a0),d7
		beq.b	.no
		movea.l	d7,a0
		clr.l	(a0)
		clr.l	PTR_SPR(a0)
.no		rts

; After the draw list (NewList, or ListCheck in the verify build): d2 holds Y, the
; entries times 2. If the pointer's object is in the list, take its entry out (the last
; entry takes its place: the list is sorted after) and show the sprites. Keeps every
; register but d2's low byte.
PtrList		movem.l	d0-d1/d3-d7/a0-a3,-(sp)
		moveq	#0,d6			;the sprites off
		move.l	(_ptrspr,pc),d0
		beq	.out
		moveq	#8,d1			;the pointer's object
		lea	$4000(a4),a0		;$9676: beyond a 16-bit displacement
		move.b	$9676-$4000(a0),d0
		beq.b	.obj
		moveq	#$10,d1
		subq.b	#1,d0
		bne	.done
.obj		lea	(a4,d1.w),a0
		tst.b	$0fda(a0)
		beq	.done
		LEW	$5e1c(a4),d3		;at the pointer, less 8
		subq.w	#8,d3
		LEW	$0f5a(a0),d0
		cmp.w	d0,d3
		bne	.done
		LEW	$5e1e(a4),d3
		subq.w	#8,d3
		LEW	$0f9a(a0),d0
		cmp.w	d0,d3
		bne	.done
		moveq	#0,d7
		move.b	d2,d7
		moveq	#0,d5			;its entry
.find		cmp.w	d7,d5
		bcc	.done			;not in the view
		lea	(a4,d5.w),a1
		tst.b	$4782(a1)
		bne.b	.fnext
		move.w	$4702(a1),d0
		cmp.w	$0f5a(a0),d0
		bne.b	.fnext
		move.w	$4722(a1),d0
		cmp.w	$0f9a(a0),d0
		bne.b	.fnext
		move.b	$46a2(a1),d0
		cmp.b	$0eda(a0),d0
		bne.b	.fnext
		move.b	$46c2(a1),d0
		cmp.b	$0f1a(a0),d0
		beq.b	.found
.fnext		addq.w	#2,d5
		bra.b	.find
.found		move.w	$109a(a0),d0		;the frame's record, as NewShape finds
		ror.w	#8,d0			;it: the bank ($2a, little-endian)
		swap	d0
		move.w	$105a(a0),d0
		ror.w	#8,d0
		movea.l	d0,a3
		adda.l	a4,a3
		movea.l	a3,a2
		moveq	#0,d0
		move.b	$0eda(a0),d0		;the shape's frames
		asl.w	#3,d0
		adda.w	d0,a2
		LEW	(a2),d0
		movea.l	a3,a2
		adda.w	d0,a2
		moveq	#0,d0
		move.b	$0f1a(a0),d0		;the frame
		add.w	d0,d0
		adda.w	d0,a2
		LEW	(a2),d0
		adda.w	d0,a3
		lea	(_ptron,pc),a2
		cmpa.l	_ptrrec-_ptron(a2),a3
		beq.b	.drawn
		bsr	PtrDraw
.drawn		tst.b	_ptrfit-_ptron(a2)
		beq.b	.done			;too big: a shape
		subq.w	#2,d7			;the last entry into its place
		lea	(a4,d7.w),a2
		move.w	$46a2(a2),$46a2(a1)
		move.w	$46c2(a2),$46c2(a1)
		move.w	$46e2(a2),$46e2(a1)
		move.w	$4702(a2),$4702(a1)
		move.w	$4722(a2),$4722(a1)
		move.w	$4742(a2),$4742(a1)
		move.w	$4762(a2),$4762(a1)
		move.w	$4782(a2),$4782(a1)
		move.b	d7,d2
		moveq	#1,d6
.done		lea	(_ptrwant,pc),a0	;from the flip that shows the frame
		move.b	d6,(a0)
.out		movem.l	(sp)+,d0-d1/d3-d7/a0-a3
		rts

; Draw the frame whose record is at a3 into the sprites: its rows as NewShape walks
; them, a line each. A nibble is the pixel's colour (its bit 3 goes to the buffer's first
; plane, which the copper list loads as BPL4PT): bits 0 and 1 into sprite 0's two words,
; 2 and 3 into sprite 1's. Sets _ptrrec, _ptrfit, _ptroff (the
; frame's left column and first line from the pointer) and _ptrh.
PtrDraw		movem.l	d0-d7/a0-a3,-(sp)
		lea	(_ptron,pc),a2
		move.l	a3,_ptrrec-_ptron(a2)
		clr.b	_ptrfit-_ptron(a2)
		moveq	#0,d6
		move.b	6(a3),d6		;rows
		beq	.out
		cmp.w	#PTR_H,d6
		bhi	.out
		lea	8(a3),a1
		move.w	#$7fff,d4		;the leftmost pixel
		move.w	#-$8000,d5		;the rightmost
		moveq	#0,d0			;x
		moveq	#0,d1			;the previous row's pairs
		move.w	d6,d3
		subq.w	#1,d3
.span		bsr	.x
		tst.w	d1
		beq.b	.snext
		bmi	.out
		cmp.w	d0,d4
		ble.b	.s1
		move.w	d0,d4
.s1		move.w	d1,d2
		add.w	d2,d2
		add.w	d0,d2
		subq.w	#1,d2
		cmp.w	d2,d5
		bge.b	.s2
		move.w	d2,d5
.s2		adda.w	d1,a1
.snext		dbf	d3,.span
		move.w	d5,d2
		sub.w	d4,d2
		cmp.w	#15,d2			;16 pixels at most
		bhi	.out
		movea.l	(_ptrspr,pc),a0
		addq.w	#4,a0
		moveq	#PTR_H-1,d2
.clr		clr.l	(a0)
		clr.l	PTR_SPR(a0)
		addq.w	#4,a0
		dbf	d2,.clr
		movea.l	(_ptrspr,pc),a0
		addq.w	#4,a0			;line 0
		lea	8(a3),a1
		moveq	#0,d0
		moveq	#0,d1
		move.w	d6,d3
		subq.w	#1,d3
.row		bsr	.x
		move.w	d1,d7
		beq.b	.rnext
		move.w	d0,d2			;the first pixel's bit
		sub.w	d4,d2
		move.w	#$8000,d6
		lsr.w	d2,d6
		subq.w	#1,d7
.pair		move.b	(a1)+,d2
		move.b	d2,d5
		lsr.b	#4,d5
		bsr	.pix
		move.b	d2,d5
		bsr	.pix
		dbf	d7,.pair
.rnext		addq.w	#4,a0
		dbf	d3,.row
		subq.w	#8,d4			;from the pointer: the object is 8 up
		move.w	d4,_ptroff-_ptron(a2)	;and left
		move.b	2(a3),d0
		ext.w	d0
		subq.w	#8,d0
		move.w	d0,_ptroff+2-_ptron(a2)
		moveq	#0,d0
		move.b	6(a3),d0
		move.w	d0,_ptrh-_ptron(a2)
		st	_ptrfit-_ptron(a2)
.out		movem.l	(sp)+,d0-d7/a0-a3
		rts
.x		move.b	(a1),d2			;the row's x, as the game steps it
		ext.w	d2
		add.w	d1,d2
		add.w	d2,d2
		add.w	d2,d0
		moveq	#0,d1
		move.b	2(a1),d1		;its pairs
		ext.w	d1
		addq.w	#4,a1
		rts
.pix		btst	#0,d5			;the nibble is the colour
		beq.b	.p1
		or.w	d6,(a0)
.p1		btst	#1,d5
		beq.b	.p2
		or.w	d6,2(a0)
.p2		btst	#2,d5
		beq.b	.p3
		or.w	d6,PTR_SPR(a0)
.p3		btst	#3,d5
		beq.b	.p4
		or.w	d6,PTR_SPR+2(a0)
.p4		lsr.w	#1,d6
		rts

_ptrspr		dc.l	0			;the sprites, chip; 0 none
_ptrrec		dc.l	0			;the frame drawn into them, 0 none
_ptrbase	dc.w	0,0			;x, y where the last step put the pointer, or this one will
_ptroff		dc.w	0,0			;the frame's left column, first line
_ptrh		dc.w	0			;its lines
_ptron		dc.b	0			;show the sprites
_ptrwant	dc.b	0			;the frame drawn last shows them
_ptrfit		dc.b	0			;the frame drawn fits them

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
	ifd VERIFY				;WHDLoad wants whole $1000s
EXPSIZE		= (EX_VLIST+2*VL_SIZE+$fff)&$fffff000
	else
EXPSIZE		= (EX_STAB+STABSIZE+$fff)&$fffff000
	endc

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
ShapeMark	movem.l	d0-d7/a0-a3/a5,-(sp)	;NewShape's entry: a0 = $32 as read
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
; The shape drawer. $16ec (entered from threaded code, which saved d0-d2 at $16ee) draws
; a frame of a shape: $2a the shape bank (a little-endian pointer), $22 the shape, $24 the
; frame, $26/$28 its x and y on the map, $32 where to draw ($30000: the status line, at
; fixed lines). A frame's record holds its rows (byte 6), the offset of its first line
; (byte 2), then the rows: an x step (signed, plus the previous row's count, in pixel
; pairs), a count of pixel pairs and two more bytes, then the pairs, a byte each: the left
; pixel in the high nibble, bit 3 of a nibble plane 0 to bit 0 plane 3, 0 transparent. Rows
; are clipped to the buffer's 160 lines and pixels to 0-319. The game plots each pixel
; with four bclr and up to four bset. NewShape replaces $16f2-$18de with every write the
; game makes ($26/$28 made screen-relative, $16d2-$16dd), and d3, d4 and d6 left as the
; game leaves them: a row is built 16 pixels at a time, a word per plane from the table
; at EX_STAB (2 bits a plane for each byte, at its position), the pixels outside 0-319 masked off, and
; written with one masked long read-modify-write a plane at the row's word (a long may
; reach a word past the row's either end, which it writes back unchanged). The status
; line's path stays the game's ($18e2). Installed with ExpMem, which holds the table. Replaces $16f2-$16f7 (clr.w $16da(a4); movea.l $2a(a4),a0).
EX_STAB		= EX_TILES+TILESIZE	;ExpMem: 256 bytes by 8 positions, planes 0/1 and 2/3
STABSIZE	= 256*64


; A pair byte b at position j of 16 pixels (0 the leftmost pair), at b*64+j*8: planes 0
; and 1 at bits 31-30 and 15-14 shifted right by 2*j (left pixel the higher bit), then
; planes 2 and 3 the same. a0: the table.
ShapeTable	moveq	#0,d0
.e		move.w	d0,d1
		lsr.w	#4,d1			;left pixel
		move.w	d0,d2
		and.w	#15,d2			;right pixel
		moveq	#0,d3
		moveq	#0,d4
		TBIT	d1,3,d3,31
		TBIT	d2,3,d3,30
		TBIT	d1,2,d3,15
		TBIT	d2,2,d3,14
		TBIT	d1,1,d4,31
		TBIT	d2,1,d4,30
		TBIT	d1,0,d4,15
		TBIT	d2,0,d4,14
		moveq	#8-1,d5
.j		move.l	d3,(a0)+
		move.l	d4,(a0)+
		lsr.l	#2,d3
		lsr.l	#2,d4
		dbf	d5,.j
		addq.w	#1,d0
		cmp.w	#256,d0
		bcs.b	.e
		rts

NewShape	movem.l	d3-d4/a2,-(sp)		;the game keeps d3 (the carry) and a2
	ifd VERIFY
		bsr	ShapeSave
	endc
		clr.w	$16da(a4)		;the previous row's count
		LEL	$2a(a4),d0		;the bank
		movea.l	d0,a0
		adda.l	a4,a0
		movea.l	a0,a3
		movea.l	a0,a5
		moveq	#0,d0
		move.b	$22(a4),d0
		asl.w	#3,d0
		adda.w	d0,a0
		LEW	(a0),d0			;the shape's frames
		movea.l	a5,a0
		adda.w	d0,a0
		moveq	#0,d0
		move.b	$24(a4),d0
		add.w	d0,d0
		adda.w	d0,a0
		LEW	(a0),d0			;the frame's record
		adda.w	d0,a3
		moveq	#0,d6
		move.b	6(a3),d6		;rows
		beq	.end
		moveq	#0,d7
		move.b	2(a3),d7
		ext.w	d7
		move.w	d7,$16d2(a4)		;the first line's offset
		addq.w	#8,a3
		movea.l	$32(a4),a0
		bsr	ShapeMark		;the cells it covers
		LEL	$32(a4),d0
		cmp.l	#$30000,d0
		bne.b	.buf
		movea.l	d0,a0			;the status line: the game's path, with
	ifd VERIFY				;its registers as at $174e
		addq.l	#1,$1b4.w
	endc
		movem.l	(sp)+,d3-d4/a2
		jmp	$18e2(a4)
.buf		LEW	$28(a4),d0		;y and x on the screen
		sub.w	$1476(a4),d0
		SEW	d0,$28(a4)
		LEW	$26(a4),d0
		move.w	$1474(a4),d1
		and.w	#$fff0,d1
		sub.w	d1,d0
		SEW	d0,$26(a4)
		move.l	$1462(a4),d0		;the back buffer
		move.w	$2326(a4),d0
		eori.w	#$8000,d0
		movea.l	d0,a0
		move.l	a0,$16dc(a4)
		LEW	$28(a4),d0
		add.w	$16d2(a4),d0
		muls	#40,d0
		adda.l	d0,a0			;the first row's line
		LEW	$26(a4),d0
		move.w	d0,$16d6(a4)		;x
		lea	(_v,pc),a2
		movea.l	V_EXP(a2),a2
		lea	EX_STAB(a2),a2

.row		move.b	(a3),d0			;the row's x
		ext.w	d0
		add.w	$16da(a4),d0
		add.w	d0,d0
		add.w	$16d6(a4),d0
		move.w	d0,$16d6(a4)
		move.w	d0,d4
		moveq	#0,d5
		move.b	2(a3),d5		;pairs
		move.b	d5,$16db(a4)
		addq.w	#4,a3
		cmpa.l	$16dc(a4),a0		;lines 0-159
		blt.b	.skip
		move.l	a0,d1
		subi.l	#6400,d1
		cmp.l	$16dc(a4),d1
		blt.b	.draw
.skip		ext.w	d5			;as the game: a signed count
		adda.w	d5,a3
		bra	.next
.draw		tst.w	d5
		beq	.next
		move.w	d5,d1
		add.w	d1,d1
		add.w	d4,d1			;the x the game ends the row at
		move.w	d1,-(sp)
	ifd VERIFY
		tst.w	d4
		bmi.b	.vedge
		cmp.w	#320,d1
		bhi.b	.vedge
		addq.l	#1,$1b8.w
		bra.b	.vin
.vedge		addq.l	#1,$1bc.w
.vin
	endc
		move.w	d6,a5			;rows
		movea.w	d4,a6			;the chunk's first pixel
		move.w	d4,d1
		asr.w	#4,d1
		add.w	d1,d1
		lea	(a0,d1.w),a1		;the row's first word
		and.w	#15,d4			;its shift
		move.w	d5,d2			;pairs left
.chunk		moveq	#8,d3
		cmp.w	d3,d2
		bcc.b	.c8
		move.w	d2,d3
.c8		sub.w	d3,d2
		moveq	#0,d0
		moveq	#0,d1
		moveq	#8,d6			;k pairs: the last k positions, from
		sub.w	d3,d6			;step 8-k (14 bytes a step)
		move.w	d6,d3
		lsl.w	#4,d6
		sub.w	d3,d6
		sub.w	d3,d6
		jmp	.pairs(pc,d6.w)
.pairs
J		set	0
		rept	8
		moveq	#0,d7
		move.b	(a3)+,d7
		lsl.w	#6,d7
		or.l	J*8(a2,d7.w),d0
		or.l	J*8+4(a2,d7.w),d1
J		set	J+1
		endr
		tst.w	d3			;fewer than 8: left-align them
		beq.b	.full
		add.w	d3,d3
		lsl.l	d3,d0
		lsl.l	d3,d1
.full		move.w	a6,d6			;the 16 pixels inside 0-319?
		bmi.b	.clip
		cmp.w	#320-16,d6
		bgt.b	.clip
.mask		move.l	d0,d5			;the mask: any plane set
		or.l	d1,d5
		move.l	d5,d6
		swap	d6
		or.w	d6,d5
		beq	.empty
		swap	d5
		clr.w	d5
		lsr.l	d4,d5
		not.l	d5
		move.l	d0,d6			;plane 0
		clr.w	d6
		lsr.l	d4,d6
		move.l	(a1),d7
		and.l	d5,d7
		or.l	d6,d7
		move.l	d7,(a1)
		move.w	d0,d6			;plane 1
		swap	d6
		clr.w	d6
		lsr.l	d4,d6
		move.l	$2000(a1),d7
		and.l	d5,d7
		or.l	d6,d7
		move.l	d7,$2000(a1)
		move.l	d1,d6			;plane 2
		clr.w	d6
		lsr.l	d4,d6
		move.l	$4000(a1),d7
		and.l	d5,d7
		or.l	d6,d7
		move.l	d7,$4000(a1)
		move.w	d1,d6			;plane 3
		swap	d6
		clr.w	d6
		lsr.l	d4,d6
		move.l	$6000(a1),d7
		and.l	d5,d7
		or.l	d6,d7
		move.l	d7,$6000(a1)
.empty		addq.w	#2,a1
		lea	16(a6),a6
		tst.w	d2
		bne	.chunk
		move.w	a5,d6
		move.w	(sp)+,d4
		bra.b	.next
.clip		moveq	#-1,d7			;the pixels inside 0-319 (a chunk is
		tst.w	d6			;narrower than the screen: one edge)
		bpl.b	.cr
		neg.w	d6			;left of 0
		cmp.w	#16,d6
		bcc.b	.empty
		lsr.w	d6,d7
		bra.b	.cm
.cr		sub.w	#320-16,d6		;right of 319
		cmp.w	#16,d6
		bcc.b	.empty
		lsr.w	d6,d7
		lsl.w	d6,d7
.cm		move.w	d7,d6
		swap	d7
		move.w	d6,d7
		and.l	d7,d0
		and.l	d7,d1
		bra	.mask
.next		lea	40(a0),a0
		subq.w	#1,d6
		bne	.row
.end
	ifd VERIFY
		bra	ShapeDone
	endc
		move.l	(sp)+,d3		;d4 as the game leaves it
		addq.w	#4,sp
		movea.l	(sp)+,a2
		movem.l	(sp)+,d0-d2		;displaced: $18d4-$18de
		lea	$18e0(a4),a5
		jmp	$0106(a4)

	ifd VERIFY
; Debug builds: NewShape saves the back buffer's 160 lines of each plane (and a word
; more, which a long write may read and write back) and $26-$29 and $16d2-$16dd
; (ShapeSave), draws, keeps what it drew with its d4 and a3, puts the saved state back
; (ShapeDone) and runs the game's drawer from $16f2 (put back for the run) with d3, d4 and
; a2 as they came; at its end ($18d4, ShapeCheck) the planes, the variables, d4 and a3
; are compared with NewShape's and the hook goes back. Low memory (fill $cc): $1c0 counts
; the shapes that differed, $1c4 the shapes checked, $1c8 the first difference (the low
; word of $1c4 then, and the byte's offset: plane p at p*VS_PLANE, then the variables,
; d4 and a3). $1b8 counts the rows NewShape drew inside 0-319, $1bc those across an
; edge, $1b4 the status line's shapes (not checked).
VS_PLANE	= 6400+4
VS_VARS		= 4+12
VS_SIZE		= 4*VS_PLANE+VS_VARS+6
EX_VSHAPE	= EX_STAB+STABSIZE	;the saved state, then NewShape's
EX_VLIST	= EX_VSHAPE+2*VS_SIZE

VSREGS		macro			;\1: copy the regions between (a0) and a1
		move.l	$1462(a4),d0
		move.w	$2326(a4),d0
		eori.w	#$8000,d0
		movea.l	d0,a0
		moveq	#4-1,d6
.p\@		move.w	#VS_PLANE-1,d7
		bsr	\1
		lea	$2000-VS_PLANE(a0),a0
		dbf	d6,.p\@
		lea	$26(a4),a0
		moveq	#4-1,d7
		bsr	\1
		lea	$16d2(a4),a0
		moveq	#12-1,d7
		bsr	\1
		endm

ShapeSave	movem.l	d0/d6-d7/a0-a1,-(sp)
		movea.l	(_v,pc),a1
		lea	EX_VSHAPE(a1),a1
		VSREGS	VLOut
		movem.l	(sp)+,d0/d6-d7/a0-a1
		rts

; The end of NewShape: on the stack d3, d4, a2 as they came, then the thread's d0-d2.
ShapeDone	movem.l	d0/d6-d7/a0-a1,-(sp)
		movea.l	(_v,pc),a1
		lea	EX_VSHAPE+VS_SIZE(a1),a1	;keep NewShape's
		VSREGS	VLOut
		move.w	d4,(a1)+
		move.l	a3,(a1)+
		movea.l	(_v,pc),a1
		lea	EX_VSHAPE(a1),a1		;and put the input back
		VSREGS	VLIn
		move.l	#$426c16da,$16f2(a4)	;the game's drawer for the run
		move.w	#$206c,$16f6(a4)
		bsr	ListFlush
		movem.l	(sp)+,d0/d6-d7/a0-a1
		movem.l	(sp)+,d3-d4/a2
		jmp	$16f2(a4)

ShapeCheck	movem.l	d0-d7/a0-a6,-(sp)
		movea.l	(_v,pc),a1
		lea	EX_VSHAPE+VS_SIZE(a1),a1
		move.l	$1462(a4),d0
		move.w	$2326(a4),d0
		eori.w	#$8000,d0
		movea.l	d0,a0
		moveq	#0,d5			;bytes that differ
		moveq	#0,d6			;offset
		moveq	#4-1,d4
.pl		move.w	#VS_PLANE,d7
		bsr.b	.cmp
		lea	$2000-VS_PLANE(a0),a0
		dbf	d4,.pl
		lea	$26(a4),a0
		moveq	#4,d7
		bsr.b	.cmp
		lea	$16d2(a4),a0
		moveq	#12,d7
		bsr.b	.cmp
		lea	4*4(sp),a0		;d4 and a3 as the game left them
		moveq	#2,d7
		addq.w	#2,a0
		bsr.b	.cmp
		lea	11*4(sp),a0
		moveq	#4,d7
		bsr.b	.cmp
		tst.w	d5
		beq.b	.same
		addq.l	#1,$1c0.w
.same		addq.l	#1,$1c4.w
		move.w	#$4ef9,$16f2(a4)	;the hook back
		pea	NewShape
		move.l	(sp)+,$16f4(a4)
		bsr	ListFlush
		movem.l	(sp)+,d0-d7/a0-a6
		movem.l	(sp)+,d0-d2		;displaced: $18d4-$18de
		lea	$18e0(a4),a5
		jmp	$0106(a4)
.cmp		subq.w	#1,d7			;d7 bytes at a0 against a1; d5 counts
.c		cmpm.b	(a0)+,(a1)+		;differing bytes, d6 the offset
		beq.b	.ok
		addq.w	#1,d5
		cmp.l	#$cccccccc,$1c8.w	;the fill: none recorded yet
		bne.b	.ok
		move.w	$1c6.w,$1c8.w
		move.w	d6,$1ca.w
.ok		addq.w	#1,d6
		dbf	d7,.c
		rts
	endc

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
		bsr	PtrList
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
		bsr	PtrList
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
		cmp.b	#$45,d0		;Esc down: for SkipIntro
		bne.b	.noesc
		move.l	a0,-(sp)
		lea	(_esc,pc),a0
		st	(a0)
		move.l	(sp)+,a0
.noesc		cmpi.b	#$59,d0		; cmpi as the shipped slave has it: vasm encodes cmp #,Dn as CMP
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

; The credits (the title state 3, phases $752a 1-3: "Electronic Arts presents", "A
; Sandcastle production", "written by", 200 clock units each from the stamp $752c, table
; $7610) end at Esc (FixKey) or the left mouse button: the phase becomes 4, the blank
; before the title, with its 50 units already passed, so the game's next update sets up
; "Press 1-4 to start" as after the credits. From Split, each pass. Only d7 and a0.
SkipIntro	lea	(_esc,pc),a0
		move.b	(a0),d7
		clr.b	(a0)
		btst	#6,$bfe001
		bne.b	.button
		st	d7
.button		tst.b	d7
		beq.b	.no
		cmp.b	#3,$0ea8(a4)
		bne.b	.no
		move.b	$752a(a4),d7
		subq.b	#1,d7
		cmp.b	#3,d7
		bcc.b	.no
		move.b	#4,$752a(a4)
		LEW	$5de6(a4),d7		;the clock less 100: the blank's 50 passed
		sub.w	#100,d7
		SEW	d7,$752c(a4)
.no		rts

_esc		dc.b	0,0			;Esc pressed since SkipIntro looked

; The game's delay $290c (native, from the threaded code with A the count): A times
; 16001 dbf passes, a CPU loop. The calls: 254 for the timer bonus screen ($7ba0), 240
; for "4 STROKE AWARD!" ($996c), 120 for "GAME OVER, Player N" ($9798) and 100 after the
; last hole ($9f06). On an NTSC A500 254 took 391 fields, interrupts and all (25.68 ms
; a count); a 68030 ran it in a fraction of that. This waits for the A500's time by the
; beam (field ends, as fields of 16.68 ms or, from line 290 on, 20 ms), interrupts or
; not. Replaces tst.b d0 to bra.s at $2912-$2921 (d0 and d1 are saved around it).
DELAY_UNIT	= 2568				;the A500's time for a count, in 10 us
Delay		movem.l	d0/d2-d3,-(sp)
		and.l	#$ff,d0
		mulu	#DELAY_UNIT,d0
		moveq	#0,d2			;the time passed, in 10 us
		bsr	BeamLine
.field		move.w	d1,d3
		bsr	BeamLine
		cmp.w	d3,d1
		bcc.b	.field			;the same field
		add.l	#1668,d2
		cmp.w	#290,d3
		bcs.b	.ntsc
		add.l	#2000-1668,d2
.ntsc		cmp.l	d0,d2
		bcs.b	.field
		movem.l	(sp)+,d0/d2-d3
		rts

; The palette fades $2454 (in, d2 0 to 248) and $248a (out, d2 248 to 0) set 32 steps,
; each followed by 3001 dbf passes ($246a, $24a2), a CPU loop. On an NTSC A500 a step took
; 104 lines fading in and 100 out (12.6 and 12.2 fields), the step's work and the
; interrupts included. These wait until as many lines have passed since the step before
; ended (the first step: since now), by the beam, so the A500 keeps its time and a faster
; CPU takes it too. The frame's length is the highest line seen plus one (NTSC 263, PAL
; 313). Replace move.w #3000,d3; dbf d3,* (d3 ends as $ffff, as there).
FADEIN_LINES	= 103
FADEOUT_LINES	= 99
FadeIn		movem.l	d0-d1/d3/a0,-(sp)
		moveq	#FADEIN_LINES,d0
		tst.w	d2
		bra.b	Fade
FadeOut		movem.l	d0-d1/d3/a0,-(sp)
		moveq	#FADEOUT_LINES,d0
		cmp.w	#248,d2
Fade		lea	(_fade,pc),a0
		bne.b	.wait
		bsr	BeamLine		;the first step
		move.w	d1,(a0)
.wait		bsr	BeamLine
		cmp.w	2(a0),d1
		bls.b	.since
		move.w	d1,2(a0)		;the highest line seen
.since		move.w	d1,d3
		sub.w	(a0),d3
		bcc.b	.lines
		add.w	2(a0),d3		;across the frame's end
		addq.w	#1,d3
.lines		cmp.w	d0,d3
		bcs.b	.wait
		move.w	d1,(a0)			;this step's end
		movem.l	(sp)+,d0-d1/d3/a0
		move.w	#$ffff,d3
		rts

_fade		dc.w	0,262			;the last step's end, the highest line

; The loader's file load (loader offset $5aa) waits 1000000 passes of subi.l/bne before
; it opens the file, a CPU loop (3.6 s on an A500, about 15 fields on a 68030). Pressing
; 1-4 on the title loads the hole's sign first, with the title frozen on screen for
; that time; the loads after it show the sign while they wait. So the sign's load (the
; name Zany:FILES/SIGNn.UNV at loader offset $25c) gets a single pass, the others the
; game's. Replaces move.l #1000000,d0 at $5c2; d0 only.
LoadDelay	move.l	a0,-(sp)
		move.l	4(sp),a0		;the return: loader offset $5c8
		lea	$25c+11-$5c8(a0),a0	;the name after Zany:FILES/
		move.l	#1000000,d0
		cmp.b	#'S',(a0)+
		bne.b	.wait
		cmp.b	#'I',(a0)+
		bne.b	.wait
		cmp.b	#'G',(a0)+
		bne.b	.wait
		cmp.b	#'N',(a0)
		bne.b	.wait
		moveq	#1,d0
.wait		move.l	(sp)+,a0
		rts

Unsupported	pea	TDREASON_WRONGVER
_end		move.l	(_resload,pc),a2
		jmp	(resload_Abort,a2)

_resload	dc.l	0		;address of resident loader
_OSEmu		dc.b	'osemu.400',0
file		dc.b	"zany",0
dosname		dc.b	"dos.library",0