;---------------------------------------------------------------------------
; Enhanced framerate (CUSTOM1=1, on a 68020 or higher): the race on a fixed
; tick (docs/internals.md, "Enhanced framerate"). Included by src/fixes.i.
;
; The original race loop ($AF56-$CD20) takes one simulation step per pass and
; draws a frame in every pass, so the game's speed follows the frame rate.
; Here every pass is one tick, due every ENH_PERIOD fields (3: 16.7 Hz, or 2:
; 25 Hz with CUSTOM2=1), counted by the game's VBL ($A884). A pass waits while
; it is early. When the next tick is already due as well, the pass leaves out
; what only draws (at most ENH_SKIPS_MAX passes in a row):
;   in $D13C, the wait for a new field, the road spans, the objects and the
;   scaler ($D142-$D1C1), and the swap ($D510-$D527).
; The landscape ($E4F8) runs in every pass: it follows the track for the
; simulation, and its projection decides whether the car is off the road
; ($10AAA, from the nearest line's road edges at $FA62). It draws nothing, so
; the wait for the VBL to take the last frame (src/fixes.i's fix_Landscape)
; moves after it, before the race loop's panel updates ($CA10-$CCFA) and the
; drawing in $D13C: the landscape's work overlaps the wait. A pass that does
; not draw leaves out the sky and ground clear that $D13C queues ($10F90) but
; keeps its state (the horizon's scroll, $13F16; the ground's top line
; $1136C). The rest of $D13C runs in every pass: it keeps time (the ARCADE
; score, the start lights, the pit stop, the crash sequences, all counted in
; passes).
; Behind by more than ENH_LIMIT fields, the time past it is dropped. The race's
; start and the end of a pause start the tick clock again, with no catch-up.
; Link play (COMM, $87BC not 0) keeps the original loop: the two machines
; keep step through the serial link.
;
; With fast ExpMem the program's stack moves there (enh_Fast).
;
; The scheduler's variables are in low memory, where the tools can read them.
;
; Blitter waits: the original slave made every blitter start in $11000-$19C00
; wait for its blit ($10C-$124). Where the game waits itself before its next
; blit, with nothing in between that touches memory, the start only reads
; dmaconr once (Agnus sets the busy bit a cycle late) and returns: the CPU
; runs on while the blitter works. src/blitwait.i lists those sites
; (tools/blitsites.py).
;---------------------------------------------------------------------------

ENH_VARS	= $1C0			; low memory, after src/fixes.i's trampoline
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
ENH_BLT1	= ENH_BLT0+6		; as the original slave's $10C-$124
ENH_BLT4	= ENH_BLT0+12
ENH_BLT5	= ENH_BLT0+18
ENH_BLT6	= ENH_BLT0+24

ENH_STACK	= $1000			; the ExpMem: the program's stack, to here
ENH_EXPSIZE	= $1000			; ws_ExpMem (optional): a multiple of $1000

ENH_LIMIT	= 50			; fields of debt kept: 1 s
ENH_SKIPS_MAX	= 3			; passes in a row without drawing

; CUSTOM3=n (for the checks, not in ws_config): n of every n+1 passes leave
; out the drawing, whatever the time. The simulation must not notice.

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
		pea	WHDLTAG_CUSTOM2_GET
		clr.l	-(a7)
		pea	WHDLTAG_CUSTOM1_GET
		move.l	a7,a0
		move.l	_resload(pc),a1
		jsr	resload_Control(a1)
		move.l	4(a7),d0		; CUSTOM1
		move.l	12(a7),d1		; CUSTOM2
		move.b	20+3(a7),ENH_FORCE.w	; CUSTOM3
		lea	28(a7),a7
		st	(a2)			; -1: off
		tst.l	d0
		beq.b	.done
		move.b	#1,(a2)			; 1: on
		moveq	#3,d0			; 16.7 Hz
		tst.l	d1
		beq.b	.period
		moveq	#2,d0			; 25 Hz
.period		move.w	d0,ENH_PERIOD.w
		clr.l	ENH_TICKS.w
		clr.l	ENH_FRAMES.w
		clr.l	ENH_DROPPED.w
		clr.b	ENH_COUNT.w
		bsr.b	enh_Rebase
		bsr	enh_Fast
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
		PL_PS	$AF50,enh_Enter		; clr.w $DC30: the race loop's entry
		PL_PS	$AF56,enh_Pass		; tst.w $DC34: a pass starts
		PL_PS	$B724,enh_Unpause	; clr.w $8504: the end of a pause
		PL_PS	$C968,enh_Landscape	; jsr $E4F8 (src/fixes.i's fix_Landscape)
		PL_PS	$D13C,enh_Clear		; jsr $10F90: the sky and ground clear
		PL_PSS	$D142,enh_Objects,6	; move.l $E258(pc),d7; cmp.l $A884,d7; beq.s *-6
		PL_PSS	$D510,enh_Swap,4	; move.l $A884,$E258
	INCLUDE	blitwait.i
		PL_END

; With fast ExpMem the program's stack moves there. Its one setting is at the
; program's start ($366E: movea.l #$2FC96,a7), which runs right after this
; first call from Patch. ExpMem below $200000 is chip memory, and in
; $C00000-$DFFFFF slow memory on the chip bus.
enh_Fast	move.l	_expmem(pc),d0
		beq.b	.out
		cmp.l	#$200000,d0
		blo.b	.out
		cmp.l	#$C00000,d0
		blo.b	.fast
		cmp.l	#$E00000,d0
		blo.b	.out
.fast		cmp.l	#$2E7C0002,$366E	; movea.l #$2FC96,a7
		bne.b	.out
		cmp.w	#$FC96,$366E+4
		bne.b	.out
		lea	_enh_fast(pc),a0
		move.l	d0,(a0)
		add.l	#ENH_STACK,d0
		move.l	d0,$366E+2
.out		rts

; The tick clock starts again: the next tick is due now.
enh_Rebase	move.l	$A884,ENH_DUE.w
		sf	ENH_SKIP.w
		sf	ENH_SKIPS.w
		rts

enh_Enter	clr.w	$DC30
		bra.b	enh_Rebase

enh_Unpause	clr.w	$8504
		bra.b	enh_Rebase

; A pass starts: wait for its tick, decide whether it draws. Returns with the
; condition codes of the replaced tst.w $DC34.
enh_Pass	movem.l	d0-d1,-(a7)
		tst.w	$87BC			; link play: the original loop
		bne.b	.link
		move.l	$A884,d1
		sub.l	ENH_DUE.w,d1		; fields since the tick was due
		bpl.b	.late
.early		move.l	$A884,d1
		sub.l	ENH_DUE.w,d1
		bmi.b	.early
		bra.b	.tick
.late		cmp.l	#ENH_LIMIT,d1
		bls.b	.tick
		add.l	d1,ENH_DROPPED.w	; too far behind: drop the debt
		move.l	$A884,ENH_DUE.w
		moveq	#0,d1
.tick		moveq	#0,d0
		move.w	ENH_PERIOD.w,d0
		add.l	d0,ENH_DUE.w
		addq.l	#1,ENH_TICKS.w
		cmp.l	d0,d1			; the next tick due already?
		blo.b	.draw
		cmp.b	#ENH_SKIPS_MAX,ENH_SKIPS.w
		bhs.b	.draw
.skip		st	ENH_SKIP.w
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
		tst.w	$DC34
		rts
.link		bsr.b	enh_Rebase
		bra.b	.done


; The landscape, then the wait for the VBL to take the last frame
enh_Landscape	jsr	$E4F8
		bra	fix_WaitShown

; $D13C's first drawing: $10F90 waits for the blitter queue ($1B0, src/fixes.i's
; fix_Queue), lets $13F16 scroll the horizon (its blits go into the queue),
; queues the sky and ground clear, clamps the ground's top line $1136C and
; starts the queue. A pass that does not draw keeps the state: the queue is
; written as $10F90 would, but not started.
enh_Clear	tst.b	ENH_SKIP.w
		bne.b	.undrawn
		jmp	$10F90
.undrawn	jsr	FIX_TRAMP.w		; fix_Queue: a6 = the queue, now idle
		move.w	$10C42,d7		; as $10F94
		jsr	$13F16
		move.l	#8000,d0		; as $11016-$11036
		sub.l	$1136C,d0
		ble.b	.done
		divu.w	#40,d0
		cmp.w	#132,d0
		ble.b	.done
		move.l	#2720,$1136C
.done		rts

; $D13C's wait for a new field and its road spans, objects and scaler. A pass
; that does not draw goes on at $D1C2 (the start lights).
enh_Objects	tst.b	ENH_SKIP.w
		bne.b	.out
		move.l	$E258,d7		; the field of the last swap
.wait		cmp.l	$A884,d7
		beq.b	.wait
		rts
.out		move.l	#$D1C2,(a7)
		rts

; $D13C's swap: a pass that does not draw returns from $D13C instead
; (nothing on the stack at $D510).
enh_Swap	tst.b	ENH_SKIP.w
		bne.b	.out
		addq.l	#1,ENH_FRAMES.w
		move.l	$A884,$E258
		rts
.out		addq.l	#4,a7
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

_enh_fast	dc.l	0		; the ExpMem when it is fast memory, else 0
_enh_state	dc.b	0		; 0 unknown, -1 off, 1 on
		even
