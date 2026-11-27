;---------------------------------------------------------------------------
; Enhanced framerate (CUSTOM1=1, on a 68020 or higher): the race on a fixed
; tick (docs/internals.md, "Enhanced framerate"). Included by src/fixes.i;
; games/Vroom's src/enhanced.i is the design, here at the Multiplayer's (v1)
; addresses and around its rebuilt race loop.
;
; The race loop ($B98A-$D394) takes one simulation step per pass for every
; player ($B992-$BE18), then for each view ($D190-$D1FC: one, or two split
; screen) runs the landscape and the player's timers ($D3A6) and draws the
; view ($DB04), then swaps once ($D348-$D386). The game's speed follows the
; frame rate. Here every pass is one tick, due every ENH_PERIOD fields (3:
; 16.7 Hz), counted by the game's VBL ($98DE). A pass waits while it is early.
; When the next tick is already due as well, the pass leaves out what only
; draws (at most ENH_SKIPS_MAX passes in a row):
;   in each view's $DB04, the wait for the beam or a new field, the sky and
;   ground clear ($11D2A, its state kept: the horizon's scroll $14FA4 and the
;   ground's top line $12136), the road spans ($11A1E), the sky objects and
;   the scaler ($197AA): $DB04-$DBCF;
;   the frame end's wait and the swap ($D348-$D38B).
; The rest runs in every pass: the landscape follows the track for the
; simulation and decides whether a car is off the road, and the player's
; timers, the start lights, the crash sequences, the pit stop and the panel
; count passes.
; Behind by more than ENH_LIMIT fields, the time past it is dropped. The race's
; start and the end of a pause start the tick clock again, with no catch-up.
; The Multiplayer has no link play.
;
; The scheduler's variables are in low memory, where the tools can read them.
;
; Blitter waits: src/blitwait.i makes every blitter start in the renderer wait
; for its blit ($10C-$124). Where the game waits itself before its next blit,
; with nothing in between that touches memory, the start only reads dmaconr
; once (Agnus sets the busy bit a cycle late) and returns: the CPU runs on
; while the blitter works. src/blitsites.i lists those sites
; (tools/blitsites.py).
;---------------------------------------------------------------------------

	INCLUDE	blitsites.i

ENH_VARS	= $1C0			; low memory, after src/fixes.i's trampolines
ENH_DUE		= ENH_VARS+0		; long: the field the next tick is due
ENH_TICKS	= ENH_VARS+4		; long: passes (ticks) run
ENH_FRAMES	= ENH_VARS+8		; long: passes that drew
ENH_DROPPED	= ENH_VARS+12		; long: fields dropped (behind by more than ENH_LIMIT)
ENH_PERIOD	= ENH_VARS+16		; word: fields a tick
ENH_SKIP	= ENH_VARS+18		; byte: this pass leaves out the drawing
ENH_SKIPS	= ENH_VARS+19		; byte: passes in a row that have left it out
ENH_FORCE	= ENH_VARS+20		; byte: CUSTOM3, for the checks (below)
ENH_COUNT	= ENH_VARS+21		; byte: its pass count

ENH_BLT0	= $1E0			; jmp trampolines for the blitter starts,
ENH_BLT1	= ENH_BLT0+6		; as src/fixes.i's $10C-$124
ENH_BLT4	= ENH_BLT0+12
ENH_BLT5	= ENH_BLT0+18
ENH_BLT6	= ENH_BLT0+24

ENH_FIELDS	= $98DE			; the VBL's field counter (long)

ENH_LIMIT	= 50			; fields of debt kept: 1 s
ENH_SKIPS_MAX	= 3			; passes in a row without drawing

; CUSTOM3=n (for the checks, not in ws_config): n of every n+1 passes leave
; out the drawing, whatever the time. The simulation must not notice.

	MACHINE	MC68020				; all of it runs on a 68020 or higher

; IN:	-
; OUT:	-	all registers preserved
; Called from Fix on a 68020 or higher.
Enhanced	movem.l	d0-d1/a0-a2,-(a7)
		lea	_enh_state(pc),a2
		tst.b	(a2)
		bne.b	.known
		clr.l	-(a7)			; TAG_DONE
		clr.l	-(a7)
		pea	WHDLTAG_CUSTOM3_GET
		clr.l	-(a7)
		pea	WHDLTAG_CUSTOM1_GET
		move.l	a7,a0
		move.l	_resload(pc),a1
		jsr	resload_Control(a1)
		move.l	4(a7),d0		; CUSTOM1
		move.b	12+3(a7),ENH_FORCE.w	; CUSTOM3
		lea	20(a7),a7
		st	(a2)			; -1: off
		tst.l	d0
		beq.b	.done
		move.b	#1,(a2)			; 1: on
		move.w	#3,ENH_PERIOD.w		; 16.7 Hz
		clr.l	ENH_TICKS.w
		clr.l	ENH_FRAMES.w
		clr.l	ENH_DROPPED.w
		clr.b	ENH_COUNT.w
		bsr	enh_Rebase
.known		tst.b	(a2)
		bmi.b	.done
		lea	ENH_BLT0.w,a0		; jmp enh_Blt0 ... enh_Blt6
		lea	_enh_blt(pc),a1
		move.l	a1,a2
		moveq	#5-1,d0
.tramp		move.w	#$4EF9,(a0)+		; jmp xxx.l
		move.w	(a1)+,d1
		pea	(a2,d1.w)
		move.l	(a7)+,(a0)+
		dbf	d0,.tramp
		lea	_enh_pl(pc),a0
		sub.l	a1,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
.done		movem.l	(a7)+,d0-d1/a0-a2
		rts

_enh_pl		PL_START
		PL_PS	$B984,enh_Enter		; clr.w $E54E.l: the race loop's entry
		PL_PSS	$B98A,enh_Pass,2	; lea $E566(pc),a5; move.w $E562(pc),d7
		PL_PS	$BE86,enh_Unpause	; tst.w $E53E.l: the end of a pause
		PL_PSS	$DB04,enh_View,2	; cmpi.w #1,$11484.l: a view's drawing
		PL_PSS	$D348,enh_Swap,2	; cmpi.w #$50,$C8.l: the frame's end
	IFND	ENH_NOBLITSITES			; (for A/B checks)
		ENH_BLITSITES			; jsr ENH_BLT0-6 for jsr $10C-$124
	ENDC
		PL_END

; The tick clock starts again: the next tick is due now.
enh_Rebase	move.l	ENH_FIELDS,ENH_DUE.w
		sf	ENH_SKIP.w
		sf	ENH_SKIPS.w
		rts

enh_Enter	clr.w	$E54E
		bra.b	enh_Rebase

; Returns the flags of the replaced tst.w $E53E.
enh_Unpause	bsr.b	enh_Rebase
		tst.w	$E53E
		rts

; A pass starts: wait for its tick, decide whether it draws.
enh_Pass	movem.l	d0-d1,-(a7)
		move.l	ENH_FIELDS,d1
		sub.l	ENH_DUE.w,d1		; fields since the tick was due
		bpl.b	.late
.early		move.l	ENH_FIELDS,d1
		sub.l	ENH_DUE.w,d1
		bmi.b	.early
		bra.b	.tick
.late		cmp.l	#ENH_LIMIT,d1
		bls.b	.tick
		add.l	d1,ENH_DROPPED.w	; too far behind: drop the debt
		move.l	ENH_FIELDS,ENH_DUE.w
		moveq	#0,d1
.tick		moveq	#0,d0
		move.w	ENH_PERIOD.w,d0
		add.l	d0,ENH_DUE.w
		addq.l	#1,ENH_TICKS.w
		cmp.l	d0,d1			; the next tick due already?
		blo.b	.draw
		cmp.b	#ENH_SKIPS_MAX,ENH_SKIPS.w
		bhs.b	.draw
		st	ENH_SKIP.w
		addq.b	#1,ENH_SKIPS.w
		bra.b	.force
.draw		sf	ENH_SKIP.w
		sf	ENH_SKIPS.w
.force		move.b	ENH_FORCE.w,d0		; CUSTOM3: skip n of n+1 passes
		beq.b	.done
		move.b	ENH_COUNT.w,d1
		sne	ENH_SKIP.w		; the first of each n+1 draws
		addq.b	#1,d1
		cmp.b	d0,d1
		bls.b	.count
		moveq	#0,d1
.count		move.b	d1,ENH_COUNT.w
.done		movem.l	(a7)+,d0-d1
		lea	$E566,a5		; the players
		move.w	$E562,d7		; their count - 1
		rts

; A view's drawing ($DB04, called from $D6F0 with nothing kept in the
; registers). A pass that does not draw keeps what the sky and ground clear
; $11D2A keeps between frames, as $11D2A-$11DD9 (the queue it writes is not
; started), and goes on at $DBD0, after the scaler. Returns the flags of the
; replaced cmpi.w #1,$11484.
enh_View	tst.b	ENH_SKIP.w
		bne.b	.undrawn
		cmp.w	#1,$11484
		rts
.undrawn	jsr	FIX_TRAMP.w		; fix_Queue: a6 = the queue, now idle
		move.w	$1199C,d7		; the horizon's scroll
		jsr	$14FA4
		move.l	#8000,d0		; the ground's top line, clamped to
		sub.l	$12136,d0		; the view
		ble.b	.done
		divu.w	#40,d0
		move.w	#199,d2
		sub.w	$113C8,d2
		cmp.w	d2,d0
		ble.b	.done
		move.l	$113C4,$12136
.done		move.l	#$DBD0,(a7)
		rts

; The frame's end: a pass that does not draw goes on at $D38C, leaving out the
; wait and the swap ($D374: the screen for the VBL $972E, the swap's field
; $EB36, the buffers' toggle $145F8). Returns the flags of the replaced
; cmpi.w #$50,$C8.
enh_Swap	tst.b	ENH_SKIP.w
		bne.b	.out
		addq.l	#1,ENH_FRAMES.w
		cmp.w	#$50,$C8.w
		rts
.out		move.l	#$D38C,(a7)
		rts

; A blitter start the game waits after itself: start, let Agnus set the busy
; bit (a dummy read, as WHDLoad's BLITWAIT), return.
_enh_blt	dc.w	enh_Blt0-_enh_blt,enh_Blt1-_enh_blt,enh_Blt4-_enh_blt
		dc.w	enh_Blt5-_enh_blt,enh_Blt6-_enh_blt
enh_Blt0	move.w	d0,bltsize(a6)
		bra.b	enh_Blt
enh_Blt1	move.w	d1,bltsize(a6)
		bra.b	enh_Blt
enh_Blt4	move.w	d4,bltsize(a6)
		bra.b	enh_Blt
enh_Blt5	move.w	d5,bltsize(a6)
		bra.b	enh_Blt
enh_Blt6	move.w	d6,bltsize(a6)
enh_Blt		tst.b	_custom+dmaconr
		rts

_enh_state	dc.b	0		; 0 unknown, -1 off, 1 on
		even

	MACHINE	MC68000
