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
; The Multiplayer has no link play. With the ExpMem, frames are drawn between
; the ticks where they pay (below, "Frames between ticks").
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
		clr.l	ENH_BLOCK.w
		tst.l	d0
		beq.b	.done
		move.b	#1,(a2)			; 1: on
		move.w	#3,ENH_PERIOD.w		; 16.7 Hz
		clr.l	ENH_TICKS.w
		clr.l	ENH_FRAMES.w
		clr.l	ENH_DROPPED.w
		clr.b	ENH_COUNT.w
		bsr	enh_Rebase
	IFND	ENH_NOFMODE			; (for A/B checks)
		bsr	enh_FmodeInit
	ENDC
		move.l	_expmem(pc),d0		; frames between ticks: the snapshots
		beq.b	.known			; in the ExpMem, fast or not
		add.l	#ENH_SNAP-ENH_BOTTOM,d0
		lea	_enh_bufs(pc),a0
		move.l	d0,(a0)+
		add.l	#ENH_RSIZE,d0
		move.l	d0,(a0)
	IFND	ENH_NOINTERP			; for A/B measurements: the ticks draw
		lea	_enh_interp(pc),a0
		st	(a0)
		st	_enh_avail-_enh_interp(a0)
	ENDC
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
		bsr	enh_Fmode
		lea	_enh_pl(pc),a0
		sub.l	a1,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
		lea	_enh_moved(pc),a0
		tst.b	(a0)			; once, after every patch is in
		bne.b	.moved
		st	(a0)
		bsr	enh_Move
.moved		bsr	enh_RelocOut
.done		movem.l	(a7)+,d0-d1/a0-a2
		rts

_enh_pl		PL_START
		PL_PS	$B984,enh_Enter		; clr.w $E54E.l: the race loop's entry
		PL_PSS	$B98A,enh_Pass,2	; lea $E566(pc),a5; move.w $E562(pc),d7
		PL_PS	$BE86,enh_Unpause	; tst.w $E53E.l: the end of a pause
		PL_PSS	$DB04,enh_View,2	; cmpi.w #1,$11484.l: a view's drawing
		PL_PSS	$D348,enh_Swap,2	; cmpi.w #$50,$C8.l: the frame's end
		PL_PS	$D010,enh_Marker	; movea.l #$4BD9E,a1: the map markers
		PL_PS	$D084,enh_Lights	; move.w $E53E(pc),d0; blt.s $D0D8
		PL_PSS	$D38C,enh_Next,2	; move.b $E557(pc),d0; cmp.b $E556(pc),d0
		PL_PS	$D3A6,enh_Land		; move.l 2(a3),$A(a5): a view's landscape
		PL_PS	$D3CA,enh_Turn		; tst.w $D4(a5); blt.s $D3F0
		PL_PS	$D3F0,enh_TurnRec	; move.w $1199C.l,d7
		PL_PSS	$10012,enh_Pitch,2	; move.w $1187C(pc),d1; cmpi.w #$5208,d1
		PL_PS	$F3F2,enh_Engine0	; move.w $1254A(pc),d4; beq.s $F406
		PL_PS	$F644,enh_Engine1	; move.w $1254A(pc),d4; beq.s $F658
		PL_PSS	$FB26,enh_Sort,2	; sub.l d7,d1; cmpi.l #$7FFF,d1
		PL_PSS	$E10C,enh_WheelXY,18	; move.l d6,($A,a5,d5.w) ... move.l d6,(a5,d5.w)
		PL_PSS	$808E,enh_R808E,2	; move.w $E564(pc),d0; cmp.w $7FCA(pc),d0
		PL_PSS	$8444,enh_R8444,2	; move.b $E5C1(pc),d6; move.w #-1,d7
		PL_PSS	$845A,enh_R8444,2
		PL_PS	$846A,enh_R846A		; moveq #0,d7; move.b $E601(pc),d7
		PL_PSS	$8538,enh_R8538,2	; move.l $EA5A(pc),$8F00.l
		PL_PS	$DCAA,enh_Hud		; movea.l $E55A(pc),a5; moveq #0,d0
		PL_PS	$13676,enh_Hud0		; movea.l $E55A.l,a5: the tyres' marks
		PL_PS	$12CB0,enh_Wheel	; jsr $11FDE.l: the wheel's lower part
		PL_PS	$D258,enh_Score		; lea $8B98.l,a0: the score's digits
		PL_PS	$D282,enh_Time		; lea $8D26.l,a0: the time's digits
	IFND	ENH_NOGROUND			; (for A/B measurements)
		PL_PS	$DB36,enh_Clear		; jsr $11D2A: the sky and ground clear
		PL_PS	$DB54,enh_Clear
		PL_PS	$DB5C,enh_Clear
		PL_S	$11DDA,$11E1C-$11DDA	; its ground entries (enh_Ground)
	ENDC
	IFND	ENH_NOBLITSITES			; (for A/B checks)
		ENH_BLITSITES			; jsr ENH_BLT0-6 for jsr $10C-$124
	ENDC
		PL_END

;---------------------------------------------------------------------------
; Fast memory (Vroom's step 19 and 20). With the ExpMem in fast memory, the
; race block ($B254-$1CBAF: the race's setup and loop, the race state, the
; landscape, the renderer, the objects and the scalers with their variables)
; runs from a copy there, and the program's stack moves below the copy. The
; copy's bottom is at the ExpMem's start (any offset works). tools/reloc.py
; lists the long addresses into the block, in it and outside it (src/reloc.i).
; The PC-relative references across its edges are rewritten here; the
; slave's own references take the block's offset (ENH_BLOCK) from low memory:
; ([ENH_BLOCK.w],address), and src/fixes.i's go through its pointers. ExpMem
; below $200000 is chip memory, and in $C00000-$DFFFFF slow memory on the
; chip bus: the block stays.
;---------------------------------------------------------------------------

ENH_BLOCK	= $1D6			; long: the race block's offset (0: not moved)

ENH_LO		= $B254			; the race block, moved to fast memory
ENH_HI		= $1CBB0
ENH_MID		= ((ENH_LO+ENH_HI)/2)&-2	; RELOC_IN counts from here
ENH_TAIL	= $1CD14		; the scaler's table ($1CB14, read PC-relative,
					; 128 entries up to the buffers at $1CD14)
					; runs on to here: in the copy too
ENH_STACK	= $B240			; the stack's top, below the block in the copy
ENH_STACKSIZE	= $800			; and its size (the race uses about 400 bytes)
ENH_TRSIZE	= $100			; the trampolines, below the stack (bsr.w range)
ENH_TR		= ENH_STACK-ENH_STACKSIZE-ENH_TRSIZE
ENH_BOTTOM	= ENH_TR		; the lowest address used, in the copy
ENH_SNAP	= ENH_BOTTOM+((ENH_TAIL-ENH_BOTTOM+$F)&-$10)	; after the copy:
					; the two snapshots of the race state
					; (frames between ticks), ENH_RSIZE bytes each
ENH_EXPSIZE	= (ENH_SNAP+2*ENH_RSIZE-ENH_BOTTOM+$FFF)&$FFFFF000	; ws_ExpMem
					; (optional; 80 KB, as Vroom's, for the 1 MB
					; A500): the trampolines, the stack, the block
					; and its tail, then the snapshots

; The stack's one setting is at the program's start ($365A: movea.l
; #$30F36,a7), which runs right after the first call from Patch.
enh_Fast	move.l	_expmem(pc),d0
		beq.b	.out
		cmp.l	#$200000,d0
		blo.b	.out
		cmp.l	#$C00000,d0
		blo.b	.fast
		cmp.l	#$E00000,d0
		blo.b	.out
.fast		cmp.l	#$2E7C0003,$365A	; movea.l #$30F36,a7
		bne.b	.out
		cmp.w	#$0F36,$365A+4
		bne.b	.out
		sub.l	#ENH_BOTTOM,d0		; the copy's offset: its ENH_BOTTOM at the
		move.l	d0,ENH_BLOCK.w		; ExpMem's start (a multiple of $1000)
		add.l	#ENH_STACK,d0
		move.l	d0,$365A+2
	IFD	ENH_NOBLOCK			; for A/B measurements: the stack only
		clr.l	ENH_BLOCK.w
	ENDC
.out		rts

; Copy the block, relocate it and the references to it, rewrite the edges.
enh_Move	movem.l	d0-d2/a0-a3,-(a7)
		move.l	ENH_BLOCK.w,d2
		beq	.out
		lea	ENH_LO,a0		; the copy, with the table's tail
		lea	(a0,d2.l),a1
		move.l	#(ENH_TAIL-ENH_LO)/4-1,d0
.copy		move.l	(a0)+,(a1)+
		subq.l	#1,d0
		bpl.b	.copy
		lea	enh_Tramps(pc),a0	; the trampolines, below the stack
		lea	ENH_TR,a1
		add.l	d2,a1
		move.w	#(enh_TrampsEnd-enh_Tramps)/2-1,d0
.tramp		move.w	(a0)+,(a1)+
		dbf	d0,.tramp
		lea	RELOC_IN(pc),a0		; the addresses in it: (site-ENH_MID)/2
		lea	ENH_MID,a1
		add.l	d2,a1
.in		move.w	(a0)+,d0
		cmp.w	#$8000,d0
		beq.b	.edges
		ext.l	d0
		add.l	d0,d0
		add.l	d2,(a1,d0.l)
		bra.b	.in
.edges		lea	_enh_edges(pc),a0	; bsr.w to the trampolines
.edge		move.w	(a0)+,d0
		bmi.b	.ptrs
		lea	ENH_LO,a1
		add.l	d2,a1
		add.w	d0,a1
		move.w	(a0)+,(a1)+		; the opcode
		move.w	(a0)+,(a1)+		; the displacement
		move.w	(a0)+,d1		; and the words to fill with nop
		bra.b	.fill
.nop		move.w	#$4E71,(a1)+
.fill		dbf	d1,.nop
		bra.b	.edge
.ptrs		lea	_fix_blk(pc),a0		; src/fixes.i's references
		moveq	#(_fix_blk_end-_fix_blk)/4-1,d0
.ptr		add.l	d2,(a0)+
		dbf	d0,.ptr
		move.l	_resload(pc),a2
		jsr	resload_FlushCache(a2)
.out		movem.l	(a7)+,d0-d2/a0-a3
		rts

; The addresses into the block from outside it, where the site still holds
; the address (after each Fix: a reload over the program brings back the
; original code, and data loaded over code must stay as it is).
; IN:	-
; OUT:	-	all registers preserved
enh_RelocOut	movem.l	d0-d2/a0-a1,-(a7)
		move.l	ENH_BLOCK.w,d2
		beq.b	.out
		lea	RELOC_OUT(pc),a0
.next		moveq	#0,d0
		move.w	(a0)+,d0
		beq.b	.flush
		add.l	d0,d0
		move.l	d0,a1			; the site
		move.l	(a0)+,d1		; the address it holds
		cmp.l	(a1),d1
		bne.b	.next
		add.l	d2,(a1)
		bra.b	.next
.flush		move.l	_resload(pc),a1
		jsr	resload_FlushCache(a1)
.out		movem.l	(a7)+,d0-d2/a0-a1
		rts

; The PC-relative reads out of the block: in the copy each becomes a bsr.w to
; a trampoline below the stack. site, opcode, displacement (the trampoline's
; offset from the site, the same for any copy), words of nop after it.
ENH_EDGE	MACRO	; site, opcode, trampoline, nop words
		dc.w	\1-ENH_LO,\2,ENH_TR+(\3-enh_Tramps)-(\1+2),\4
		ENDM
_enh_edges	ENH_EDGE	$B2C0,$6100,enh_T8FBEd0,0	; move.w $8FBE(pc),d0
		ENH_EDGE	$B2E8,$6100,enh_T8FBEd0,0
		ENH_EDGE	$B310,$6100,enh_T8FBEd0,0
		ENH_EDGE	$B3FA,$6100,enh_T9116d0,0	; move.w $9116(pc),d0
		ENH_EDGE	$B466,$6100,enh_T927Ad7,0	; move.w $927A(pc),d7
		ENH_EDGE	$B46C,$6100,enh_T92D2d6,0	; move.w $92D2(pc),d6
		ENH_EDGE	$B516,$6100,enh_T8FBEd2,0	; move.w $8FBE(pc),d2
		ENH_EDGE	$B5B6,$6100,enh_T8FBEd2,0
		ENH_EDGE	$B7E2,$6100,enh_T9116d3,0	; move.w $9116(pc),d3
		ENH_EDGE	$B8AA,$6100,enh_T9116d4,0	; move.w $9116(pc),d4
		ENH_EDGE	$B8BA,$6100,enh_T9116d4,0
		ENH_EDGE	$B9DC,$6100,enh_T8A6Cd1,0	; move.w $8A6C(pc),d1
		ENH_EDGE	$B9E0,$6100,enh_T8A6Ad2,0	; move.w $8A6A(pc),d2
		ENH_EDGE	$B9E4,$6100,enh_T8A69d3,0	; move.b $8A69(pc),d3
		ENH_EDGE	$BAB0,$6100,enh_T8A68a0,0	; lea $8A68(pc),a0
		ENH_EDGE	$D188,$6100,enh_TView,2		; move.l $8F00(pc),$EA5A.l
		ENH_EDGE	$D1AE,$6100,enh_TE550,2		; move.w $9116(pc),$E550.l
		ENH_EDGE	$D374,$6100,enh_TSwap,2		; move.l $8F00(pc),$972E.l
		ENH_EDGE	$D3FA,$6100,enh_T8A7Ca0,0	; lea $8A7C(pc),a0
		ENH_EDGE	$D57C,$6100,enh_T9114d6,0	; move.l $9114(pc),d6
		ENH_EDGE	$D5A6,$6100,enh_T9114d6,0
		ENH_EDGE	$D7D6,$6100,enh_T8FBEd3,0	; move.w $8FBE(pc),d3
		ENH_EDGE	$DAE4,$6100,enh_T9114d0,0	; move.l $9114(pc),d0
		ENH_EDGE	$DB76,$6100,enh_T8A7Ca0,0	; lea $8A7C(pc),a0
		ENH_EDGE	$DC38,$6100,enh_T9116d0,0
		ENH_EDGE	$DC98,$6100,enh_T9116d0,0
		ENH_EDGE	$DDB0,$6100,enh_T7FD8d0,0	; move.w $7FD8(pc),d0
		ENH_EDGE	$DE0E,$6100,enh_T8F00a4,0	; movea.l $8F00(pc),a4
		ENH_EDGE	$DE18,$6100,enh_T7FD6a4,0	; adda.w $7FD6(pc),a4
		dc.w	-1

; Copied below the stack: position-independent, reached by bsr.w from the
; copy. Each sets the condition codes its replaced instruction set.
enh_Tramps
enh_T8FBEd0	move.w	$8FBE,d0
		rts
enh_T8FBEd2	move.w	$8FBE,d2
		rts
enh_T8FBEd3	move.w	$8FBE,d3
		rts
enh_T9116d0	move.w	$9116,d0
		rts
enh_T9116d3	move.w	$9116,d3
		rts
enh_T9116d4	move.w	$9116,d4
		rts
enh_T927Ad7	move.w	$927A,d7
		rts
enh_T92D2d6	move.w	$92D2,d6
		rts
enh_T8A6Cd1	move.w	$8A6C,d1
		rts
enh_T8A6Ad2	move.w	$8A6A,d2
		rts
enh_T8A69d3	move.b	$8A69,d3
		rts
enh_T8A68a0	lea	$8A68,a0
		rts
enh_T8A7Ca0	lea	$8A7C,a0
		rts
enh_T9114d6	move.l	$9114,d6
		rts
enh_T9114d0	move.l	$9114,d0
		rts
enh_T7FD8d0	move.w	$7FD8,d0
		rts
enh_T8F00a4	movea.l	$8F00,a4
		rts
enh_T7FD6a4	adda.w	$7FD6,a4
		rts
enh_TView	move.l	$8F00,([ENH_BLOCK.w],$EA5A)
		rts
enh_TE550	move.w	$9116,([ENH_BLOCK.w],$E550)
		rts
enh_TSwap	move.l	$8F00,$972E
		rts
enh_TrampsEnd
	IFGT	enh_TrampsEnd-enh_Tramps-ENH_TRSIZE
	FAIL	"the trampolines run into the stack"
	ENDC

; The PC-relative reads into the block from outside it, at the race's end
; ($808E-$853F): from the block's copy.
enh_R808E	move.w	([ENH_BLOCK.w],$E564),d0
		cmp.w	$7FCA,d0
		rts
enh_R8444	move.b	([ENH_BLOCK.w],$E5C1),d6
		move.w	#-1,d7
		rts
enh_R846A	moveq	#0,d7
		move.b	([ENH_BLOCK.w],$E601),d7
		rts
enh_R8538	move.l	([ENH_BLOCK.w],$EA5A),$8F00
		rts

	INCLUDE	reloc.i

; The tick clock starts again: the next tick is due now.
enh_Rebase	move.l	ENH_FIELDS,ENH_DUE.w
		sf	ENH_SKIP.w
		sf	ENH_SKIPS.w
		move.l	a0,-(a7)
		lea	_enh_snapped(pc),a0	; no last tick to draw from
		sf	(a0)
		move.l	(a7)+,a0
		rts

enh_Enter	clr.w	([ENH_BLOCK.w],$E54E)
		bra.b	enh_Rebase

; Returns the flags of the replaced tst.w $E53E.
enh_Unpause	bsr.b	enh_Rebase
		tst.w	([ENH_BLOCK.w],$E53E)
		rts

; A pass starts: wait for its tick, decide whether it draws.
enh_Pass	movem.l	d0-d1,-(a7)
		tst.b	_enh_interp(pc)
		bne	enh_PassI
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
.tick		bsr	enh_Start
		moveq	#0,d0
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
		lea	([ENH_BLOCK.w],$E566),a5		; the players
		move.w	([ENH_BLOCK.w],$E562),d7		; their count - 1
		rts

; A view's drawing ($DB04, called from $D6F0 with nothing kept in the
; registers). A pass that does not draw keeps what the sky and ground clear
; $11D2A keeps between frames, as $11D2A-$11DD9 (the queue it writes is not
; started), and goes on at $DBD0, after the scaler. Returns the flags of the
; replaced cmpi.w #1,$11484.
enh_View	tst.b	ENH_SKIP.w
		bne.b	.undrawn
		cmp.w	#1,([ENH_BLOCK.w],$11484)
		rts
.undrawn	tst.b	_enh_interp(pc)		; a tick with frames between ticks:
		beq.b	.queue			; the screen on display taken first
.shown		tst.l	$972E			; (enh_Hud)
		bpl.b	.shown
.queue		jsr	FIX_TRAMP.w		; fix_Queue: a6 = the queue, now idle
		move.w	([ENH_BLOCK.w],$1199C),d7		; the horizon's scroll
		jsr	([ENH_BLOCK.w],$14FA4)
		move.l	#8000,d0		; the ground's top line, clamped to
		sub.l	([ENH_BLOCK.w],$12136),d0		; the view
		ble.b	.done
		divu.w	#40,d0
		move.w	#199,d2
		sub.w	([ENH_BLOCK.w],$113C8),d2
		cmp.w	d2,d0
		ble.b	.done
		move.l	([ENH_BLOCK.w],$113C4),([ENH_BLOCK.w],$12136)
.done		move.l	ENH_BLOCK.w,(a7)
		add.l	#$DBD0,(a7)
		tst.b	_enh_interp(pc)
		beq.b	.out
		move.l	ENH_BLOCK.w,(a7)	; (a tick: not the panel's copy)
		add.l	#$DC2E,(a7)
.out		rts

; The sky and ground clear ($11D2A) queues the horizon, the sky and the
; ground, clamps the ground's top line $12136 to the view and starts the
; queue; then the CPU fills the ground (enh_Ground) while the blitter runs the
; horizon and the sky.
enh_Clear	jsr	([ENH_BLOCK.w],$11D2A)
		; (fall through)

; The ground's fill: the two planes the queue's ground entries fill ($11DDA-
; $11E1B: plane 2 with 0, plane 3 with 1, from the ground's top line $12136
; down, as many lines as the view has left, the view's width $113D6 and
; modulo $113D4; the road spans $11A1E draw the other planes). The CPU fills
; them while the blitter runs the rest of the queue $11D2A started, which goes
; without those entries (Vroom's enh_Ground).
; IN:	-
; OUT:	-	all registers preserved
enh_Ground	movem.l	d0-d4/a0-a1,-(a7)
		move.l	#8000,d0
		sub.l	([ENH_BLOCK.w],$12136),d0
		ble.b	.out
		divu.w	#40,d0			; the lines, as $11DC0-$11DD0
		move.w	#199,d2
		sub.w	([ENH_BLOCK.w],$113C8),d2
		cmp.w	d2,d0
		ble.b	.lines
		move.w	d2,d0
.lines		subq.w	#1,d0
		bmi.b	.out
		moveq	#$3F,d3			; the words a line
		and.w	([ENH_BLOCK.w],$113D6),d3
		beq.b	.out
		move.w	([ENH_BLOCK.w],$113D4),d4		; the modulo
		ext.l	d4
		move.l	$8F00,a0		; the view's buffer
		add.l	#16000,a0		; plane 2: 0
		add.l	([ENH_BLOCK.w],$12136),a0
		lea	8000(a0),a1		; plane 3: 1
		moveq	#-1,d2
		lsr.w	#1,d3			; in longs, with a last word
		bcs.b	.odd
		subq.w	#1,d3
.line		move.w	d3,d1
.long		clr.l	(a0)+
		move.l	d2,(a1)+
		dbf	d1,.long
		add.l	d4,a0
		add.l	d4,a1
		dbf	d0,.line
		bra.b	.out
.odd		move.w	d3,d1
		bra.b	.oddl
.long2		clr.l	(a0)+
		move.l	d2,(a1)+
.oddl		dbf	d1,.long2
		clr.w	(a0)+
		move.w	d2,(a1)+
		add.l	d4,a0
		add.l	d4,a1
		dbf	d0,.odd
.out		movem.l	(a7)+,d0-d4/a0-a1
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
.out		move.l	ENH_BLOCK.w,(a7)
		add.l	#$D38C,(a7)
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

;---------------------------------------------------------------------------
; Frames between ticks (with an ExpMem, fast or not; Vroom's design). No tick
; draws: every frame comes from here, drawn while the next tick is early.
; A frame shows the race between the last two ticks: alpha = fields since the
; last tick was due / fields a tick. It loads the snapshot of the tick before
; (its state at the pass's start), moves the cars on by alpha of their way to
; this tick and each player's camera by alpha of the player's step, runs the
; race loop's drawing from the map markers ($D010) to the swap ($D38B): every
; view's landscape ($D3A6, which follows the track by the step it is given)
; and drawing ($DB04), and loads this tick's snapshot back. In a frame the
; start lights' count and the race end's bonus ($D084-$D15F) and a view's
; timers ($D43C-$D6EF) are left out, the horizon's turn and the sky objects
; are mixed (enh_Turn), and so are the landscape's pitch and height
; (enh_Pitch); the engine's sound is the ticks' (enh_Engine0/1). The
; snapshots hold the race state (_enh_r) but not what follows the screens:
; the map markers' positions per screen ($E51C-$E52B), the race clock and its
; gate ($EA54-$EA59), the view's buffer ($EA5A), the swap's field $EB36, the
; screens, the blitter queue, the sound, the VBL's variables. A tick waits for
; the screen on display to be taken before it draws anything (enh_Marker).
; Behind by ENH_SKIPS_MAX ticks in a row, a frame is drawn anyway, of this
; tick. CUSTOM3=n (for the checks): n frames before each tick, at alpha 0,
; 1/n ..., whatever the time.
;---------------------------------------------------------------------------

ENH_R		MACRO
		dc.l	\1
		dc.w	(\2)/2-1
ENH_RS		SET	ENH_RS+(\2)
		ENDM
ENH_RS		SET	0
ENH_OB		= $E52C			; the globals, the 16 cars, the order...
ENH_OP		= $1254C		; the four players' blocks ($106 bytes each)
ENH_OPS		= $E52C-ENH_OB+$EA54-$E52C	; their offset in a snapshot
ENH_SKY		= $8A7C			; the sky objects, three for each view
_enh_r		ENH_R	ENH_OB,$EA54-ENH_OB	; to the race clock
		ENH_R	ENH_OP,4*$106
		ENH_R	$E504,$E51C-$E504	; before the map markers
		ENH_R	$EA5E,$EB36-$EA5E	; after the view's buffer, to the swap's field
		ENH_R	$11866,$119A0-$11866	; the landscape's variables
		ENH_R	$CC14,6			; the opponents' order work
		ENH_R	$1134A,$11362-$1134A	; the landscape's track pointers
		ENH_R	$12B5E,6		; the steering's state
		ENH_R	$12130,8		; the ground's top lines
		ENH_R	$149F4,4
		ENH_R	$15120,$20		; the horizon's scroll per view
		ENH_R	$1CA80,4
		ENH_R	$36032,4
		ENH_R	$8B94,4			; the ARCADE score
ENH_OSKY	= ENH_RS
		ENH_R	ENH_SKY,2*$12		; the sky objects
		dc.l	0
ENH_RSIZE	= ENH_RS

; A snapshot of the race state into (a0), or one from it.
; IN:	a0 = snapshot
; OUT:	-	all registers preserved
enh_Save	movem.l	d0-d2/a0-a2,-(a7)
		moveq	#0,d2
		bra.b	enh_Copy
enh_Load	movem.l	d0-d2/a0-a2,-(a7)
		moveq	#1,d2
enh_Copy	lea	_enh_r(pc),a2
.range		move.l	(a2)+,d0
		beq.b	.done
		move.l	d0,a1
		cmp.l	#ENH_LO,d0		; in the race block: its copy's
		blo.b	.at
		cmp.l	#ENH_HI,d0
		bhs.b	.at
		add.l	ENH_BLOCK.w,a1
.at		move.w	(a2)+,d0
		tst.b	d2
		bne.b	.load
.save		move.w	(a1)+,(a0)+
		dbf	d0,.save
		bra.b	.range
.load		move.w	(a0)+,(a1)+
		dbf	d0,.load
		bra.b	.range
.done		movem.l	(a7)+,d0-d2/a0-a2
		rts

; At a pass's start: the last snapshot becomes the tick before, and the state
; now this tick's (both, at the first pass after the race's start or a pause).
enh_Snap	movem.l	d0/a0-a2,-(a7)
		lea	_enh_bufs(pc),a1
		move.l	(a1),a0
		tst.b	_enh_snapped-_enh_bufs(a1)
		bne.b	.swap
		st	_enh_snapped-_enh_bufs(a1)
		bsr.b	enh_Save
		lea	_enh_lat(pc),a0		; the cameras' lateral positions (for
		lea	([ENH_BLOCK.w],ENH_OP+8),a2	; CUSTOM3's frames before a landscape)
		moveq	#4-1,d0
.lat		move.w	(a2),(a0)+
		lea	$106(a2),a2
		dbf	d0,.lat
		move.l	(a1),a0
		bra.b	.cur
.swap		move.l	4(a1),(a1)		; exchange
		move.l	a0,4(a1)
.cur		move.l	4(a1),a0
		bsr.b	enh_Save
		movem.l	(a7)+,d0/a0-a2
		rts

; enh_Pass with frames between ticks (d0-d1 saved; returns through it).
enh_PassI	move.l	d2,-(a7)
		bsr.b	enh_Snap
		moveq	#0,d2
		move.b	ENH_FORCE.w,d2		; CUSTOM3
		bne.b	.forced
.wait		move.l	ENH_FIELDS,d1
		sub.l	ENH_DUE.w,d1		; fields since this tick was due
		bpl.b	.late
		move.l	d1,d0			; early: the field the next frame
		addq.l	#1,d0			; shows in, if it draws within a
		tst.l	$972E			; field: the next, or the one after
		bmi.b	.shown			; if a frame waits for the VBL
		addq.l	#1,d0
.shown		tst.l	d0
		bpl.b	.tick			; the tick is due by then: run it now
		move.w	ENH_PERIOD.w,d2
		add.w	d2,d0			; fields since the last tick was due
		bpl.b	.alpha			; (an early tick, then the VBL took
		moveq	#0,d0			; the frame: one field less to wait)
.alpha		bsr	enh_Frame
		bra.b	.wait
.late		cmp.l	#ENH_LIMIT,d1
		bls.b	.behind
		add.l	d1,ENH_DROPPED.w	; too far behind: drop the debt
		move.l	ENH_FIELDS,ENH_DUE.w
.behind		cmp.b	#ENH_SKIPS_MAX,ENH_SKIPS.w
		blo.b	.tick
		move.w	ENH_PERIOD.w,d0		; ticks in a row without a frame:
		move.w	d0,d2			; one, of this tick
		bsr	enh_Frame
.tick		moveq	#0,d0
		move.w	ENH_PERIOD.w,d0
		add.l	d0,ENH_DUE.w
		addq.l	#1,ENH_TICKS.w
		st	ENH_SKIP.w		; a tick draws nothing
		bsr	enh_Window
		cmp.b	#ENH_SKIPS_MAX,ENH_SKIPS.w
		bhs.b	.done
		addq.b	#1,ENH_SKIPS.w
.done		move.l	(a7)+,d2
		movem.l	(a7)+,d0-d1
		lea	([ENH_BLOCK.w],$E566),a5		; the players
		move.w	([ENH_BLOCK.w],$E562),d7		; their count - 1
		rts
.forced		moveq	#0,d0			; n frames, alpha i/n
.frame		bsr	enh_Frame
		addq.w	#1,d0
		cmp.w	d2,d0
		blo.b	.frame
		move.l	ENH_FIELDS,ENH_DUE.w	; no catch-up
		bra.b	.tick

; A frame between ticks.
; IN:	d0.w, d2.w = alpha: d0/d2, 0 <= d0 <= d2
; OUT:	-	all registers preserved
enh_Frame	movem.l	d0-a6,-(a7)
		ext.l	d0
		ext.l	d2
		cmp.l	d2,d0			; 0 <= alpha <= 1 (outside it the
		bls.b	.alpha			; camera's step would turn huge)
		moveq	#0,d0
		tst.w	2(a7)			; the caller's d0
		bmi.b	.alpha
		move.l	d2,d0
.alpha		lea	_enh_an(pc),a2		; for enh_Mix
		move.l	d0,(a2)+
		move.l	d2,(a2)
		lea	_enh_bufs(pc),a2
		st	_enh_frame-_enh_bufs(a2)
		move.l	(a2),a0			; the tick before
		bsr	enh_Load
		move.l	4(a2),a1		; this tick
		move.l	([ENH_BLOCK.w],$E518),d7		; the track's length: the ticks wrap
					; the distances at the line
		lea	([ENH_BLOCK.w],$E586),a4		; the cars: alpha of the way, distance
		lea	($E586-ENH_OB,a1),a5	; (+2) and lateral (+8)
		moveq	#16-1,d4
.car		move.l	2(a5),d5
		sub.l	2(a4),d5
		bsr	.part
		add.l	2(a4),d5
		cmp.l	d7,d5			; across the line: as the tick before
		bhs.b	.lateral
		move.l	d5,2(a4)
.lateral	move.w	8(a5),d5
		ext.l	d5
		move.w	8(a4),d6
		ext.l	d6
		sub.l	d6,d5
		bsr.b	.part
		add.w	d5,8(a4)
		lea	64(a4),a4
		lea	64(a5),a5
		dbf	d4,.car
		lea	([ENH_BLOCK.w],$E566),a3		; the players: the camera by alpha of
		move.w	([ENH_BLOCK.w],$E562),d4		; the step, which a frame stops short
.player		lea	([ENH_BLOCK.w],$E586),a4		; of the line
		add.w	(a3),a4			; the player's car
		move.l	2(a3),a5		; and block
		move.l	a5,d1
		sub.l	ENH_BLOCK.w,d1		; (the copy's addresses)
		sub.l	#ENH_OP,d1
		lea	(ENH_OPS,a1,d1.l),a6	; this tick's block
		moveq	#0,d3
		move.w	4(a6),d3
		mulu.l	d0,d3
		divu.l	d2,d3
		move.l	a4,d5			; (a0 = the tick before)
		sub.l	ENH_BLOCK.w,d5
		sub.l	#ENH_OB-2,d5
		move.l	(a0,d5.l),d6		; the tick before's distance
		move.l	d7,d5
		subq.l	#1,d5
		sub.l	d6,d5
		bmi.b	.short
		cmp.l	d5,d3
		bls.b	.step
.short		move.l	d5,d3
		bpl.b	.step
		moveq	#0,d3
.step		move.w	d3,4(a5)
		add.l	d6,d3
		move.l	d3,2(a4)
		move.w	$CA(a6),$CA(a5)		; this tick's speed and controls
		move.w	$9C(a6),$9C(a5)
		move.w	$B2(a6),$B2(a5)
		divu.w	#$106,d1		; the camera's lateral position: the
		lea	_enh_lat(pc),a6		; race loop's steering moves it before
		move.w	(a6,d1.w*2),d1		; the landscape, once a tick
		move.w	d0,-(a7)
		move.w	8(a5),d0
		bsr	enh_Mix
		move.w	d1,8(a5)
		move.w	(a7)+,d0
		addq.l	#8,a3
		dbf	d4,.player
		lea	_enh_winf(pc),a0	; (enh_Window)
		addq.w	#1,(a0)
		sf	ENH_SKIP.w		; the drawing: from the map markers
		pea	.back(pc)		; to the swap (enh_Next returns here)
		lea	_enh_sp(pc),a0
		move.l	a7,(a0)
		jmp	([ENH_BLOCK.w],$D010)
.back		lea	_enh_bufs(pc),a2
		move.l	4(a2),a0		; this tick back
		bsr	enh_Load
		sf	_enh_frame-_enh_bufs(a2)
		sf	ENH_SKIPS.w
		movem.l	(a7)+,d0-a6
		rts
; d5 = d5*alpha; a jump of more than 4096 (a restart, the line) none
.part		move.l	d5,d6
		bpl.b	.pos
		neg.l	d6
.pos		cmp.l	#4096,d6
		bhi.b	.jump
		muls.l	d0,d5
		divs.l	d2,d5
		rts
.jump		moveq	#0,d5
		rts

; d1 = d0 + alpha of the way to d1 (words; d0 and d1 extended).
enh_Mix		ext.l	d0
		ext.l	d1
		sub.l	d0,d1
		muls.l	_enh_an(pc),d1
		divs.l	_enh_ad(pc),d1
		add.l	d0,d1
		rts

; The player block a5's number.
; IN:	a5 = a player's block
; OUT:	d1.l = 0-3
enh_Index	move.l	a5,d1
		sub.l	ENH_BLOCK.w,d1
		sub.l	#ENH_OP,d1
		divu.w	#$106,d1
		ext.l	d1
		rts

; Frames between ticks or the ticks' own: the frames pay only where a frame
; takes less than a tick. Each tick costs as much as without them but for
; the drawing, and a frame as a tick's drawing plus a view's landscape, so
; where a frame takes most of a tick, they draw fewer (two views on the
; a1200 and the a1200-030). Every ENH_WIN ticks with frames between them,
; ENH_WIN frames or fewer go back to the ticks' drawing, for ENH_HOLD ticks
; at least (doubled at each such try in a row, up to ENH_HOLDMAX: 20 s); then
; ENH_WIN drawn ticks in a row of 2 fields or less (from the tick's start to
; its swap) try the frames again.
ENH_WIN		= 8
ENH_HOLD	= 64
ENH_HOLDMAX	= 1024

; A tick that may draw starts (its wait is over).
enh_Start	tst.b	_enh_avail(pc)
		beq.b	.out
		move.l	a0,-(a7)
		lea	_enh_start(pc),a0
		move.l	ENH_FIELDS,(a0)
		lea	_enh_hold(pc),a0
		tst.w	(a0)
		beq.b	.held
		subq.w	#1,(a0)
.held		move.l	(a7)+,a0
.out		rts

; A tick's end without frames between ticks (at $D38C).
enh_Drawn	tst.b	_enh_avail(pc)
		beq.b	.out
		tst.b	_enh_interp(pc)
		bne.b	.out
		tst.b	ENH_SKIP.w
		bne.b	.out
		movem.l	d0/a0,-(a7)
		lea	_enh_fits(pc),a0
		move.l	ENH_FIELDS,d0
		sub.l	_enh_start(pc),d0
		cmp.l	#2,d0
		bls.b	.fits
		sf	(a0)
		bra.b	.done
.fits		addq.b	#1,(a0)
		cmp.b	#ENH_WIN,(a0)
		blo.b	.done
		tst.w	_enh_hold(pc)
		bne.b	.done
		sf	(a0)			; try the frames between ticks
		lea	_enh_wint(pc),a0
		clr.l	(a0)			; (and _enh_winf)
		lea	_enh_snapped(pc),a0
		sf	(a0)
		lea	_enh_interp(pc),a0
		st	(a0)
.done		movem.l	(a7)+,d0/a0
.out		rts

; A tick with frames between ticks: every ENH_WIN of them, back to the
; ticks' drawing unless the frames drew more.
enh_Window	movem.l	d0/a0,-(a7)
		lea	_enh_wint(pc),a0
		addq.w	#1,(a0)
		cmp.w	#ENH_WIN,(a0)
		blo.b	.out
		move.w	2(a0),d0		; the window's frames
		clr.l	(a0)
		cmp.w	#ENH_WIN,d0
		bhi.b	.paid
		lea	_enh_interp(pc),a0
		sf	(a0)
		lea	_enh_holdn(pc),a0	; the hold doubles at every failed
		move.w	(a0),d0			; try, up to ENH_HOLDMAX
		move.w	d0,_enh_hold-_enh_holdn(a0)
		add.w	d0,d0
		cmp.w	#ENH_HOLDMAX,d0
		bls.b	.next
		move.w	#ENH_HOLDMAX,d0
.next		move.w	d0,(a0)
		lea	_enh_fits(pc),a0
		sf	(a0)
		bra.b	.out
.paid		lea	_enh_holdn(pc),a0
		move.w	#ENH_HOLD,(a0)
.out		movem.l	(a7)+,d0/a0
		rts

; The frame's end ($D38C, after the swap): a frame returns to enh_Frame.
; Returns the flags of the replaced cmp.b $E556(pc),d0.
enh_Next	tst.b	_enh_frame(pc)
		bne.b	.frame
		bsr	enh_Drawn
		move.b	([ENH_BLOCK.w],$E557),d0
		cmp.b	([ENH_BLOCK.w],$E556),d0
		rts
.frame		move.l	_enh_sp(pc),a7
		rts

; A tick with frames between ticks leaves out what the frames draw: the map
; markers ($D010-$D083), in each view the panel's copy ($DBD0-$DC2D), the
; tyres' marks ($13676), the wheel's lower part ($12CB0) and the cockpit, the
; mirrors, the gear, the speed, the fuel ($DCAA-$DE65), and the score's or
; the time's digits ($D258-$D2CB). What it still draws (the start lights, the
; crash sequences, the pit stop) waits for the screen on display to be taken
; (enh_View): a tick often runs while the last frame waits for the VBL.
ENH_TICK	MACRO			; to \1 unless this pass is such a tick
		tst.b	_enh_interp(pc)
		beq.b	\1
		tst.b	ENH_SKIP.w
		beq.b	\1
		ENDM
enh_Marker	ENH_TICK .draw
		move.l	ENH_BLOCK.w,(a7)
		add.l	#$D084,(a7)
		rts
.draw		tst.b	_enh_frame(pc)		; a frame's: the CPU draws them into
		beq.b	.go			; the view's buffer, which may still
.shown		tst.l	$972E			; be on display
		bpl.b	.shown
.go		movea.l	#$4BD9E,a1
		rts
enh_Hud		ENH_TICK .draw
		move.l	ENH_BLOCK.w,(a7)
		add.l	#$DE66,(a7)
		rts
.draw		movea.l	([ENH_BLOCK.w],$E55A),a5
		moveq	#0,d0
		rts
enh_Hud0	ENH_TICK .draw
		addq.l	#4,a7			; out of $13676
		rts
.draw		movea.l	([ENH_BLOCK.w],$E55A),a5
		rts
enh_Wheel	ENH_TICK .draw
		addq.l	#4,a7			; out of $12CB0
		rts
.draw		jmp	([ENH_BLOCK.w],$11FDE)
enh_Score	ENH_TICK .draw
		move.l	ENH_BLOCK.w,(a7)
		add.l	#$D2CC,(a7)
		rts
.draw		lea	$8B98,a0
		rts
enh_Time	ENH_TICK .draw
		move.l	ENH_BLOCK.w,(a7)
		add.l	#$D2CC,(a7)
		rts
.draw		lea	$8D26,a0
		rts

; The start lights' count ($D084-$D0D7) and the race end's bonus ($D0D8-
; $D15F): the ticks'. Returns d0 and the flags of the replaced
; move.w $E53E(pc),d0.
enh_Lights	tst.b	_enh_frame(pc)
		bne.b	.frame
		move.w	([ENH_BLOCK.w],$E53E),d0
		blt.b	.out
		tst.b	_enh_interp(pc)		; a tick that changes the lights draws
		beq.b	.go			; them ($D0A4): the screen on display
		cmp.w	#1,([ENH_BLOCK.w],$E540)		; taken first
		bne.b	.go
.shown		tst.l	$972E
		bpl.b	.shown
.go		tst.w	d0
		rts
.out		move.l	ENH_BLOCK.w,(a7)
		add.l	#$D0D8,(a7)
		rts
.frame		move.l	ENH_BLOCK.w,(a7)	; the views
		add.l	#$D160,(a7)
		rts

; A view's landscape ($D3A6; a5 = the player's block, a3 = the car): a tick
; keeps the camera's lateral position as the landscape starts (enh_Frame).
enh_Land	tst.b	_enh_frame(pc)
		bne.b	.go
		movem.l	d1/a0,-(a7)
		bsr.b	enh_Index
		lea	_enh_lat(pc),a0
		move.w	8(a5),(a0,d1.w*2)
		movem.l	(a7)+,d1/a0
.go		move.l	2(a3),$A(a5)
		rts

; The horizon's turn ($1199C, $D3CA-$D3EF: the curve's part and the steering's,
; with the remainder $34(a5)) moves the horizon's scroll ($14FA4, from the sky
; and ground clear) and the view's three sky objects ($D3F0-$D43B). A frame
; moves both by alpha of this tick's turn from the tick before (as Vroom's
; enh_Sky), and leaves out the view's timers after them ($D43C-$D6EF: the
; tyres, the fuel, the lap times).
; IN:	a5 = the player's block
enh_Turn	tst.b	_enh_frame(pc)
		bne.b	.frame
		tst.w	$D4(a5)
		blt.b	.d3f0
		rts
.d3f0		move.l	ENH_BLOCK.w,(a7)
		add.l	#$D3F0,(a7)
		rts
.frame		movem.l	d0-d1/d4-d6/a0-a1/a4,-(a7)
		bsr	enh_Index
		lea	_enh_turn(pc),a0
		move.w	(a0,d1.w*2),d1
		moveq	#0,d0
		bsr	enh_Mix
		move.w	d1,([ENH_BLOCK.w],$1199C)
		move.l	_enh_bufs(pc),a4	; the tick before's objects
		move.l	_enh_bufs+4(pc),a1	; and this tick's
		lea	(ENH_OSKY,a4),a4
		lea	(ENH_OSKY,a1),a1
		lea	ENH_SKY,a0
		tst.w	([ENH_BLOCK.w],$1254A)			; the view
		beq.b	.view
		moveq	#$12,d0
		add.l	d0,a0
		add.l	d0,a4
		add.l	d0,a1
.view		move.w	([ENH_BLOCK.w],$1511A),d5		; the width the objects wrap at
		move.w	d5,d6
		lsr.w	#1,d6
		moveq	#3-1,d4
.obj		tst.w	(a4)
		bmi.b	.out
		move.w	2(a4),d0
		move.w	2(a1),d1
		sub.w	d0,d1			; the shorter way round
		cmp.w	d6,d1
		ble.b	.lo
		sub.w	d5,d1
.lo		neg.w	d6
		cmp.w	d6,d1
		bge.b	.hi
		add.w	d5,d1
.hi		neg.w	d6
		add.w	d0,d1
		bsr	enh_Mix
		tst.w	d1
		bpl.b	.pos
		add.w	d5,d1
.pos		cmp.w	d5,d1
		blt.b	.in
		sub.w	d5,d1
.in		move.w	d1,2(a0)
		addq.l	#6,a0
		addq.l	#6,a4
		addq.l	#6,a1
		dbf	d4,.obj
.out		movem.l	(a7)+,d0-d1/d4-d6/a0-a1/a4
		move.l	ENH_BLOCK.w,(a7)	; bsr $DB04: the drawing
		add.l	#$D6F0,(a7)
		rts

; A tick keeps the view's turn ($D3F0, after it is set; d7 = it).
enh_TurnRec	movem.l	d1/a0,-(a7)
		bsr	enh_Index
		lea	_enh_turn(pc),a0
		move.w	([ENH_BLOCK.w],$1199C),(a0,d1.w*2)
		movem.l	(a7)+,d1/a0
		move.w	([ENH_BLOCK.w],$1199C),d7
		rts

; The landscape's pitch ($1187C, from the player's $1C(a5) with the bounce,
; the jump, the acceleration's tilt and the shake off the road) and height
; (d3, kept in $D2(a5)): each integrates by the pass, so a frame re-running
; the landscape from the tick before would get a whole pass of it. A frame
; takes alpha of the way between the two ticks' values (as Vroom's enh_Pitch);
; the ticks keep the pitch per player, the last two.
; IN:	d3.w = the height, a5 = the player's block
; OUT:	d1.w = the pitch, d3, and the flags of cmpi.w #$5208,d1
enh_Pitch	movem.l	d0/d4/a0-a1,-(a7)
		exg	d1,d4
		bsr	enh_Index
		exg	d1,d4			; d4 = the player
		lea	_enh_pitch(pc),a0
		tst.b	_enh_frame(pc)
		bne.b	.frame
		move.w	(a0,d4.w*2),(8,a0,d4.w*2)	; the tick before's
		move.w	([ENH_BLOCK.w],$1187C),d1
		move.w	d1,(a0,d4.w*2)		; and this tick's
		bra.b	.out
.frame		movem.l	_enh_bufs(pc),a0-a1	; the tick before, this tick
		move.l	a5,d1
		sub.l	ENH_BLOCK.w,d1
		sub.l	#ENH_OP-ENH_OPS-$D2,d1
		move.w	(a0,d1.l),d0
		move.w	(a1,d1.l),d1
		bsr	enh_Mix
		move.w	d1,d3
		lea	_enh_pitch(pc),a0
		move.w	(8,a0,d4.w*2),d0
		move.w	(a0,d4.w*2),d1
		bsr	enh_Mix
		move.w	d1,([ENH_BLOCK.w],$1187C)
.out		movem.l	(a7)+,d0/d4/a0-a1
		cmp.w	#$5208,d1
		rts

; The engine's pitch and the bump's sound per view ($F3F2-$F411, $F644-
; $F663): the ticks'. A frame's come from the tick before's revs.
enh_Engine0	move.w	([ENH_BLOCK.w],$1254A),d4
		tst.b	_enh_frame(pc)
		bne.b	.frame
		tst.w	d4
		beq.b	.v0
		rts
.v0		move.l	ENH_BLOCK.w,(a7)
		add.l	#$F406,(a7)
		rts
.frame		move.l	ENH_BLOCK.w,(a7)
		add.l	#$F412,(a7)
		rts
enh_Engine1	move.w	([ENH_BLOCK.w],$1254A),d4
		tst.b	_enh_frame(pc)
		bne.b	.frame
		tst.w	d4
		beq.b	.v0
		rts
.v0		move.l	ENH_BLOCK.w,(a7)
		add.l	#$F658,(a7)
		rts
.frame		move.l	ENH_BLOCK.w,(a7)
		add.l	#$F664,(a7)
		rts

; The cars ahead of the camera, sorted by distance ($FB04-$FB7F): a tick
; takes them in the car order from the camera on, all ahead of it. A frame
; mixes the cars and the camera but keeps the tick before's order: a car the
; player passes in this tick can be behind the camera, and its negative
; distance would run the sort below its list. A frame leaves such a car out
; (Vroom's enh_Sort).
; IN:	d1 = the car's distance, d7 = the camera's
; OUT:	d1 = the car's distance ahead, the flags as cmpi.l #$7FFF,d1
enh_Sort	sub.l	d7,d1
		bpl.b	.ahead
		tst.b	_enh_frame(pc)
		beq.b	.ahead
		move.l	ENH_BLOCK.w,(a7)	; the next car
		add.l	#$FB04,(a7)
		rts
.ahead		cmp.l	#$7FFF,d1
		rts

; The crash's flying wheel ($E0C4-$E131, Vroom's $D7BE-$D814): the step $3E
; of the player's block indexes a table of positions ($EAA6: x at +2, the
; line at +4, halved with two views), one step a pass. A frame draws the tick
; before's step: it takes alpha of the way from the step before it.
; IN:	d0.w = the shift (1: two views), d3.w = step*8, a3 = the table,
;	d4.w = the side (-1 mirrored), d6.l = the x, a5, d5 = the object and
;	the screen's offset
; OUT:	($A,a5,d5.w) = x, (a5,d5.w) = d6.l = the line's offset
enh_WheelXY	tst.b	_enh_frame(pc)
		beq.b	.set
		tst.w	d3
		beq.b	.set			; the first step
		movem.l	d0-d2/d7,-(a7)
		move.w	d0,d7
		move.w	(2-8,a3,d3.w),d0	; x: from the step before
		tst.w	d4
		bpl.b	.side
		add.w	#$10,d0
		neg.w	d0
.side		asr.w	d7,d0
		add.w	([ENH_BLOCK.w],$113D0),d0
		move.w	d6,d1
		bsr	enh_Mix
		move.l	d1,($A,a5,d5.w)
		move.w	(4-8,a3,d3.w),d0	; the line
		asr.w	d7,d0
		move.w	(4,a3,d3.w),d1
		asr.w	d7,d1
		bsr	enh_Mix
		muls.w	#40,d1
		add.l	#$1F40,d1
		move.l	d1,(a5,d5.w)
		move.l	d1,d6
		movem.l	(a7)+,d0-d2/d7
		rts
.set		move.l	d6,($A,a5,d5.w)
		move.w	(4,a3,d3.w),d6
		asr.w	d0,d6
		muls.w	#40,d6
		add.l	#$1F40,d6
		move.l	d6,(a5,d5.w)
		rts

_enh_an		dc.l	0		; a frame's alpha: _enh_an/_enh_ad
_enh_ad		dc.l	1
_enh_bufs	dc.l	0,0		; the snapshots: the tick before, this tick
_enh_sp		dc.l	0		; enh_Frame's stack in the drawing
_enh_lat	dc.w	0,0,0,0		; each player's $8(a5) as its landscape started
_enh_turn	dc.w	0,0,0,0		; each player's turn $1199C, this tick
_enh_pitch	dc.w	0,0,0,0		; each player's pitch $1187C, this tick
		dc.w	0,0,0,0		; and the tick before
_enh_start	dc.l	0		; the field a tick that draws started in
_enh_wint	dc.w	0		; ticks in the window (enh_Window)
_enh_winf	dc.w	0		; and frames
_enh_hold	dc.w	0		; ticks before frames between ticks are tried again
_enh_holdn	dc.w	ENH_HOLD	; and after the next failed try
_enh_fits	dc.b	0		; drawn ticks in a row that took 2 fields or less
_enh_avail	dc.b	0		; frames between ticks can be drawn (an ExpMem)
_enh_snapped	dc.b	0		; the snapshots hold a tick
_enh_frame	dc.b	0		; a frame between ticks is drawing
_enh_interp	dc.b	0		; frames between ticks now
		even

_enh_state	dc.b	0		; 0 unknown, -1 off, 1 on
_enh_moved	dc.b	0		; the block has been copied (or stays)
		even

;---------------------------------------------------------------------------
; 64-bit bitplane fetch (AGA; docs/internals.md, "64-bit fetch"), as in
; Vroom. Four lores planes fetched 16 bits at a time take one chip bus slot in
; two on a display line; FMODE 3 takes a quarter of that, and the slots go to
; the blitter. It needs every plane on an 8-byte boundary: the two screens
; ($21342 and $29042, 8000-byte planes, 40-byte rows) move up by ENH_SCR_D
; bytes, into the fill above the second one (the track's data runs up to the
; first). Every reference to them: the startup's (the first picture and its
; plane pointers into the copper list $9732), the screens' and the draw
; buffer's pointers $8EF8/$8EFC/$8F00, the screen the VBL shows next $972E,
; the panel's copy between the screens ($DBEA), and the race's map code
; ($13BF4, $13C08, $14114, $14138, $142A0) and the gauge's table of line
; addresses ($1448A-$144ED); the rest takes them from the pointers. The mode setting ($AF94) writes DDFSTOP $D0 for FMODE 0; the
; 64-bit fetch of the same 320 pixels stops at $B0. Every lores plane pointer
; setting ($ADEC, $AEB4: the VBL's new screen; $AF94: a new mode) picks the
; fetch by the address it sets. The hires mode ($AE48, $AFAE) keeps FMODE 0.
;---------------------------------------------------------------------------

ENH_SCR_D	= 6			; the screens' move up

ENH_SCR		MACRO			; a long that holds a screen address
		dc.l	\1,\2
		ENDM
_enh_scr0	ENH_SCR	$3698,$21342		; the startup
		ENH_SCR	$36B4,$29042
		ENH_SCR	$36C6,$21342
		ENH_SCR	$36CC,$29042
		ENH_SCR	$3B12,$29042
		ENH_SCR	$3B20,$29042+8000
		ENH_SCR	$3B30,$29042+2*8000
		ENH_SCR	$3B40,$29042+3*8000
		dc.l	0
_enh_scrc	ENH_SCR	$8EF8,$21342		; the screens
		ENH_SCR	$8EFC,$29042
		ENH_SCR	$DBEC,$29042		; the panel's copy
		ENH_SCR	$13BF6,$21342+$99A	; the race's map code
		ENH_SCR	$13C0A,$21342+$99A
		ENH_SCR	$14116,$21342
		ENH_SCR	$1413A,$21342
		ENH_SCR	$142A2,$21342+$434
ENH_GAUGE	SET	0			; the gauge's 25 line addresses
		REPT	25			; ($1448A, read at $143DA)
		ENH_SCR	$1448A+4*ENH_GAUGE,$21C28-40*ENH_GAUGE
ENH_GAUGE	SET	ENH_GAUGE+1
		ENDR
		dc.l	0
_enh_scro	ENH_SCR	$8F00,$21342		; the draw buffer and the displayed
		ENH_SCR	$8F00,$29042		; screen: either (not required)
		ENH_SCR	$972E,$21342
		ENH_SCR	$972E,$29042
		dc.l	0

; At the first Fix with CUSTOM1: on AGA (Lisa, $F8 in LISAID: the chip
; revision bits WHDLoad passes on from Kickstart 3.1 can lack the AA ones),
; with the program's screen references as above, the 64-bit fetch is on.
; FMODE 0 until a mode sets it.
; IN:	-
; OUT:	-	all registers preserved
enh_FmodeInit	movem.l	d0-d1/a0-a1,-(a7)
		move.w	_custom+deniseid,d0
		cmp.b	#$F8,d0
		bne.b	.out
		move.w	#0,_custom+fmode
		lea	_enh_scrc(pc),a0	; at the first Fix all of the
		bsr.b	enh_ScrHeld		; references hold the screens
		bne.b	.out
		lea	_enh_scr0(pc),a0
		bsr.b	enh_ScrHeld
		bne.b	.out
		lea	_enh_fm(pc),a0
		st	(a0)
.out		movem.l	(a7)+,d0-d1/a0-a1
		rts

; At every Fix (a load may bring the original values back): the screens'
; references that still hold the original addresses move, and the plane
; pointer settings pick the fetch.
; IN:	-
; OUT:	-	all registers preserved
enh_Fmode	tst.b	_enh_fm(pc)
		beq.b	.out
		movem.l	d0-d1/a0-a2,-(a7)
		lea	_enh_scr0(pc),a0
		bsr.b	enh_ScrMove
		lea	_enh_scrc(pc),a0
		bsr.b	enh_ScrMove
		lea	_enh_scro(pc),a0
		bsr.b	enh_ScrMove
		lea	_enh_fmpl(pc),a0
		sub.l	a1,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
		movem.l	(a7)+,d0-d1/a0-a2
.out		rts

; IN:	a0 = a list of screen references
; OUT:	Z set if every one holds its screen address; d0-d1/a1 changed
enh_ScrHeld	move.l	(a0)+,d0
		beq.b	.out			; (Z set)
		move.l	d0,a1
		move.l	(a0)+,d1
		cmp.l	(a1),d1
		beq.b	enh_ScrHeld
.out		rts
; IN:	a0 = a list of screen references
; OUT:	those that hold their screen address moved; d0-d1/a0-a1 changed
enh_ScrMove	move.l	(a0)+,d0
		beq.b	.out
		move.l	d0,a1
		move.l	(a0)+,d1
		cmp.l	(a1),d1
		bne.b	enh_ScrMove
		addq.l	#ENH_SCR_D,(a1)
		bra.b	enh_ScrMove
.out		rts

_enh_fmpl	PL_START
		PL_PS	$ADEC,enh_Ptr0		; lea $9734(pc),a1; moveq #3,d0
		PL_PS	$AE48,enh_Ptr1		; lea $9760(pc),a1; moveq #1,d0
		PL_PS	$AEB4,enh_Ptr2		; lea $97A0(pc),a1; moveq #3,d0
		PL_P	$AF94,enh_Lores		; the lores mode
		PL_P	$AFAE,enh_Hires		; the hires mode
		PL_END

; The VBL's new screen (d1) into a copper list's plane pointers.
enh_Ptr0	bsr.b	enh_Fetch
		lea	$9734,a1
		moveq	#3,d0
		rts
enh_Ptr1	move.w	#0,_custom+fmode
		lea	$9760,a1
		moveq	#1,d0
		rts
enh_Ptr2	bsr.b	enh_Fetch
		lea	$97A0,a1
		moveq	#3,d0
		rts
; A new mode (d1: its last plane's end, the screen's alignment).
enh_Lores	lea	_custom,a0
		move.w	#$4200,bplcon0(a0)
		move.w	#$38,ddfstrt(a0)
		bra.b	enh_Fetch
enh_Hires	lea	_custom,a0
		move.w	#$A200,bplcon0(a0)
		move.w	#$3C,ddfstrt(a0)
		move.w	#$D4,ddfstop(a0)
		move.w	#0,fmode(a0)
		rts
; The lores fetch for the screen at d1: 64 bits if it is 8-byte aligned.
; IN:	d1 = a plane's address
; OUT:	-	all registers preserved
enh_Fetch	move.l	d0,-(a7)
		moveq	#7,d0
		and.l	d1,d0
		bne.b	.narrow
		move.w	#$B0,_custom+ddfstop
		move.w	#3,_custom+fmode
		move.l	(a7)+,d0
		rts
.narrow		move.w	#$D0,_custom+ddfstop
		move.w	#0,_custom+fmode
		move.l	(a7)+,d0
		rts

_enh_fm		dc.b	0		; the 64-bit fetch is on
		even

	MACHINE	MC68000
