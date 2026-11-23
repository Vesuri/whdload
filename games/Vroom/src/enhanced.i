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
; With fast ExpMem the program's stack and the race block ($A924-$1B4FF: the
; race's setup and loop, its state, the renderer, the objects and the
; scalers) move there (enh_Fast,
; enh_Move, enh_RelocOut; docs/internals.md, "Fast memory"). Developer builds:
; -DENH_PROTECT protects the block left in chip memory (a 68030 with MMU),
; -DENH_NOBLOCK moves only the stack (for A/B measurements).
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

ENH_BLOCK	= $1D6			; long: the race block's offset in fast memory (0: not moved)

ENH_LO		= $A924			; the race block, moved to fast memory
ENH_HI		= $1B500
ENH_MID		= ((ENH_LO+ENH_HI)/2)&-2	; RELOC_IN counts from here
ENH_STACK	= $A900			; the stack's top, below the block in the copy
ENH_STACKSIZE	= $1000			; and its size
ENH_TRSIZE	= $100			; the trampolines, below the stack (bsr.w range)
ENH_TR		= ENH_STACK-ENH_STACKSIZE-ENH_TRSIZE
ENH_BOTTOM	= ENH_TR		; the lowest address used, in the copy
ENH_EXPSIZE	= (ENH_HI-ENH_BOTTOM+$FFF)&$FFFFF000	; ws_ExpMem (optional; small
					; for the 1 MB A500): the trampolines, the
					; stack and the block, from its start

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
		clr.l	ENH_BLOCK.w
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
		lea	_enh_moved(pc),a0
		tst.b	(a0)			; once, after every patch is in
		bne.b	.moved
		st	(a0)
		bsr	enh_Move
.moved		bsr	enh_RelocOut
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

;---------------------------------------------------------------------------
; Fast memory. With fast ExpMem, the race block ($A924-$1B4FF: the race's
; setup and loop, the race state, the renderer, the objects, the scalers and
; their variables) runs from a copy there, and the program's stack moves below
; the copy. The copy starts at the ExpMem's start (any offset works: nothing
; in the block depends on its addresses' low words). tools/reloc.py lists the long addresses into the block, in it and outside it
; (src/reloc_<variant>.i). The PC-relative references across its edges are
; rewritten here, and the slave's own references go through _blk_ptrs.
; ExpMem below $200000 is chip memory, and in $C00000-$DFFFFF slow memory on
; the chip bus: the block stays.
;---------------------------------------------------------------------------

; The stack's one setting is at the program's start ($366E: movea.l #$2FC96,a7),
; which runs right after this first call from Patch.
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
		sub.l	#ENH_BOTTOM,d0		; the copy's offset: its ENH_BOTTOM at the
					; ExpMem's start (a multiple of $1000)
		move.l	d0,ENH_BLOCK.w
		add.l	#ENH_STACK,d0
		move.l	d0,$366E+2
	IFD	ENH_NOBLOCK			; for A/B measurements: the stack only
		clr.l	ENH_BLOCK.w
	ENDC
.out		rts

; Copy the block, relocate it and the references to it, rewrite the edges.
enh_Move	movem.l	d0-d2/a0-a3,-(a7)
		move.l	ENH_BLOCK.w,d2
		beq	.out
		lea	ENH_LO,a0		; the copy
		lea	(a0,d2.l),a1
		move.w	#(ENH_HI-ENH_LO)/2-1,d0
.copy		move.w	(a0)+,(a1)+
		dbf	d0,.copy
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
.ptrs		lea	_blk_ptrs(pc),a0	; the slave's references
		moveq	#(_blk_end-_blk_ptrs)/4-1,d0
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
	IFD	ENH_PROTECT
		bsr.b	enh_Protect
	ENDC
.out		movem.l	(a7)+,d0-d2/a0-a1
		rts

	IFD	ENH_PROTECT
; A check (-DENH_PROTECT, a 68030 with MMU): between Fixes any access to the
; block left in chip memory faults (the patch lists, applied again by every
; Fix, write there). From its first whole page: the VBL handler at $A076
; can't run in a protected page.
ENH_PROT_LO	= $B000
enh_Protect	lea	_enh_prot(pc),a0
		st	(a0)
		move.l	#ENH_HI-ENH_PROT_LO,d0
		lea	ENH_PROT_LO,a0
		move.l	_resload(pc),a1
		jmp	resload_ProtectReadWrite(a1)
enh_Unprotect	movem.l	d0-d1/a0-a1,-(a7)
		lea	_enh_prot(pc),a0
		tst.b	(a0)
		beq.b	.out
		clr.b	(a0)
		move.l	#ENH_HI-ENH_PROT_LO,d0
		lea	ENH_PROT_LO,a0
		move.l	_resload(pc),a1
		jsr	resload_ProtectRemove(a1)
.out		movem.l	(a7)+,d0-d1/a0-a1
		rts
_enh_prot	dc.b	0
		even
	ENDC

; The PC-relative reads out of the block, and its one branch out: in the copy
; each becomes a bsr.w (the branch a ble.w) to a trampoline after it. site, opcode,
; displacement (the trampoline's offset from the site, the same for any
; copy), words of nop after it.
ENH_EDGE	MACRO	; site, opcode, trampoline, nop words
		dc.w	\1-ENH_LO,\2,ENH_TR+(\3-enh_Tramps)-(\1+2),\4
		ENDM
_enh_edges	ENH_EDGE	$ADAE,$6100,enh_T8764d4,0	; move.w $8764(pc),d4
		ENH_EDGE	$ADBE,$6100,enh_T8764d4,0
		ENH_EDGE	$AF9A,$6100,enh_T8260,0		; move.w $8260(pc),d1
		ENH_EDGE	$AF9E,$6100,enh_T825E,0		; move.w $825E(pc),d2
		ENH_EDGE	$AFA2,$6100,enh_T825D,0		; move.b $825D(pc),d3
		ENH_EDGE	$B0F4,$6100,enh_T8764d1,0	; move.w $8764(pc),d1
		ENH_EDGE	$BF86,$6100,enh_T87BC,0		; move.w $87BC(pc),d3
		ENH_EDGE	$CC4A,$6100,enh_T8500,0		; move.l $8500(pc),d0
		ENH_EDGE	$CC60,$6100,enh_T8500,0
		ENH_EDGE	$CF52,$6F00,enh_T7D30,0		; ble.w $7D30
		ENH_EDGE	$D1AC,$6100,enh_T86EA,0		; movea.l $86EA(pc),a5
		ENH_EDGE	$D436,$6100,enh_T8500,0
		ENH_EDGE	$D51A,$6100,enh_TSwap,2		; move.l $86EA(pc),$A71C
		dc.w	-1

; Copied after the block: position-independent, reached by bsr.w and ble.w
; from the copy. Each returns the condition codes its replaced read set.
enh_Tramps
enh_T8764d4	move.w	$8764,d4
		rts
enh_T8764d1	move.w	$8764,d1
		rts
enh_T8260	move.w	$8260,d1
		rts
enh_T825E	move.w	$825E,d2
		rts
enh_T825D	move.b	$825D,d3
		rts
enh_T87BC	move.w	$87BC,d3
		rts
enh_T8500	move.l	$8500,d0
		rts
enh_T86EA	move.l	$86EA,a5
		rts
enh_TSwap	move.l	$86EA,$A71C
		rts
enh_T7D30	jmp	$7D30
enh_TrampsEnd
	IFGT	enh_TrampsEnd-enh_Tramps-ENH_TRSIZE
	FAIL	"the trampolines run into the stack"
	ENDC

; The slave's references into the block (here, in src/fixes.i and src/smc.i):
; enh_Move adds the copy's offset.
_blk_ptrs
_blk_DC30	dc.l	$DC30
_blk_DC34	dc.l	$DC34
_blk_D1C2	dc.l	$D1C2
_blk_E258	dc.l	$E258
_blk_E4F8	dc.l	$E4F8
_blk_F8E4	dc.l	$F8E4
_blk_F9A0	dc.l	$F9A0
_blk_F9C6	dc.l	$F9C6
_blk_FAD4	dc.l	$FAD4
_blk_FAD6	dc.l	$FAD6
_blk_1065A	dc.l	$1065A
_blk_1067E	dc.l	$1067E
_blk_10C42	dc.l	$10C42
_blk_10F90	dc.l	$10F90
_blk_1123A	dc.l	$1123A
_blk_11268	dc.l	$11268
_blk_1136C	dc.l	$1136C
_blk_13F16	dc.l	$13F16
_blk_1A33C	dc.l	$1A33C
_blk_1A340	dc.l	$1A340
_blk_end

; The tick clock starts again: the next tick is due now.
enh_Rebase	move.l	$A884,ENH_DUE.w
		sf	ENH_SKIP.w
		sf	ENH_SKIPS.w
		rts

enh_Enter	move.l	a0,-(a7)
		move.l	_blk_DC30(pc),a0
		clr.w	(a0)
		move.l	(a7)+,a0
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
		tst.w	([_blk_DC34,pc])
		rts
.link		bsr.b	enh_Rebase
		bra.b	.done


; The landscape, then the wait for the VBL to take the last frame
enh_Landscape	jsr	([_blk_E4F8,pc])
		bra	fix_WaitShown

; $D13C's first drawing: $10F90 waits for the blitter queue ($1B0, src/fixes.i's
; fix_Queue), lets $13F16 scroll the horizon (its blits go into the queue),
; queues the sky and ground clear, clamps the ground's top line $1136C and
; starts the queue. A pass that does not draw keeps the state: the queue is
; written as $10F90 would, but not started.
enh_Clear	tst.b	ENH_SKIP.w
		bne.b	.undrawn
		jmp	([_blk_10F90,pc])
.undrawn	jsr	FIX_TRAMP.w		; fix_Queue: a6 = the queue, now idle
		move.w	([_blk_10C42,pc]),d7	; as $10F94
		jsr	([_blk_13F16,pc])
		move.l	#8000,d0		; as $11016-$11036
		sub.l	([_blk_1136C,pc]),d0
		ble.b	.done
		divu.w	#40,d0
		cmp.w	#132,d0
		ble.b	.done
		move.l	a0,-(a7)
		move.l	_blk_1136C(pc),a0
		move.l	#2720,(a0)
		move.l	(a7)+,a0
.done		rts

; $D13C's wait for a new field and its road spans, objects and scaler. A pass
; that does not draw goes on at $D1C2 (the start lights).
enh_Objects	tst.b	ENH_SKIP.w
		bne.b	.out
		move.l	([_blk_E258,pc]),d7	; the field of the last swap
.wait		cmp.l	$A884,d7
		beq.b	.wait
		rts
.out		move.l	_blk_D1C2(pc),(a7)
		rts

; $D13C's swap: a pass that does not draw returns from $D13C instead
; (nothing on the stack at $D510).
enh_Swap	tst.b	ENH_SKIP.w
		bne.b	.out
		addq.l	#1,ENH_FRAMES.w
		move.l	a0,-(a7)
		move.l	_blk_E258(pc),a0
		move.l	$A884,(a0)
		move.l	(a7)+,a0
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

_enh_state	dc.b	0		; 0 unknown, -1 off, 1 on
_enh_moved	dc.b	0		; the block has been copied (or stays)
		even
