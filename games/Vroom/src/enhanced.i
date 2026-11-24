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
; enh_Move, enh_RelocOut; docs/internals.md, "Fast memory"), and so do the
; loader's unpacker variables and tables (the load's time). Developer builds:
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
ENH_TAIL	= $1B600		; the scaler's pointer table ($1B464) runs on
					; to here: in the copy too, past ENH_HI
ENH_WORK_HI	= ENH_WORK_LO+$64C	; the loader's unpacker variables and
					; tables (ENH_WORK_LO: in the slave's source),
					; moved to the page after the copy (ENH_WORK,
					; in its addresses)
ENH_WORK	= ENH_BOTTOM+((ENH_TAIL-ENH_BOTTOM+$FFF)&$FFFFF000)
ENH_SNAP	= ENH_WORK+((ENH_WORK_HI-ENH_WORK_LO+$F)&-$10)	; after them: the
					; two snapshots of the race state (frames
					; between ticks), ENH_RSIZE bytes each
ENH_RSIZE	= $8C4			; the ranges of _enh_r
ENH_EXPSIZE	= (ENH_SNAP+2*ENH_RSIZE-ENH_BOTTOM+$FFF)&$FFFFF000	; ws_ExpMem (optional; small
					; for the 1 MB A500): the trampolines, the
					; stack and the block, from its start, then
					; the unpacker's page and the snapshots

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
		bsr	enh_FmodeInit
		moveq	#3,d0			; 16.7 Hz
		tst.l	d1
		beq.b	.period
		moveq	#2,d0			; 25 Hz
.period		move.w	d0,ENH_PERIOD.w
		clr.l	ENH_TICKS.w
		clr.l	ENH_FRAMES.w
		clr.l	ENH_DROPPED.w
		clr.b	ENH_COUNT.w
		bsr	enh_Rebase
		move.l	_expmem(pc),d0		; frames between ticks: the snapshots
		beq.b	.fast			; in the ExpMem, fast or not
		add.l	#ENH_SNAP-ENH_BOTTOM,d0
		lea	_enh_bufs(pc),a0
		move.l	d0,(a0)+
		add.l	#ENH_RSIZE,d0
		move.l	d0,(a0)
		lea	_enh_interp(pc),a0
		st	(a0)
	IFD	ENH_NOINTERP			; for A/B measurements: the tick draws
		sf	(a0)
	ENDC
.fast		bsr	enh_Fast
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
		bsr	enh_Fmode		; before the block's copy
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
		PL_S	$1103A,$11078-$1103A	; the ground's queue entries (enh_Ground)
		PL_PSS	$D142,enh_Objects,6	; move.l $E258(pc),d7; cmp.l $A884,d7; beq.s *-6
		PL_PSS	$D510,enh_Swap,4	; move.l $A884,$E258
	PL_PS	$D530,enh_Clock		; clr.w $8504: the start lights
	PL_PS	$D602,enh_Clock		; clr.w $8504: the pit stop
	PL_PS	$E6A0,enh_Engine	; move.w d5,$9FC4: the engine's pitch
	PL_PS	$E6A6,enh_Bump		; move.w d0,$A03C: the bump's sound
	PL_PS	$E936,enh_Engine
	PL_PS	$E93C,enh_Bump
	PL_PSS	$F396,enh_Pitch,2	; move.w $10ACA(pc),d1; cmpi.w #21000,d1
	PL_PSS	$D800,enh_WheelXY,4	; move.l d6,(10,a5,d5.w); move.l (8,a3,d3.w),(0,a5,d5.w)
	PL_PS	$C8F8,enh_Marker	; move.l $86DE,d5: the map marker
	PL_PS	$120A6,enh_Hud0		; move.w $12150(pc),d0; addq.w #1,d0
	PL_PS	$D216,enh_Hud		; blt.s; bsr.w $D5FC: the pit stop, then the cockpit
	PL_PS	$118DE,enh_Wheel	; movea.l #$DFF000,a6: the wheel ($D20A)
	PL_PS	$D414,enh_Score		; lea $8374,a0: the score's digits
	PL_PS	$D43E,enh_Time		; lea $850E,a0: the time's digits
	PL_PSS	$ED76,enh_Sort,2	; sub.l d7,d1; cmpi.l #32767,d1: the cars ahead
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
		lea	ENH_WORK_LO,a0		; the unpacker's variables and tables:
		lea	ENH_WORK,a1		; to ENH_WORK
		add.l	d2,a1
		move.w	#(ENH_WORK_HI-ENH_WORK_LO)/2-1,d0
.wcopy		move.w	(a0)+,(a1)+
		dbf	d0,.wcopy
		lea	_enh_work(pc),a0	; and the loader's references to them
		move.l	#ENH_WORK-ENH_WORK_LO,d1
		add.l	d2,d1
.work		moveq	#0,d0
		move.w	(a0)+,d0
		beq.b	.flush
		add.l	#ENH_LDR,d0
		move.l	d0,a1
		move.l	(a1),d0
		sub.l	#ENH_WORK_LO,d0
		cmp.l	#ENH_WORK_HI-ENH_WORK_LO,d0
		bhs.b	.work
		add.l	d1,(a1)
		bra.b	.work
.flush
		move.l	_resload(pc),a2
		jsr	resload_FlushCache(a2)
.out		movem.l	(a7)+,d0-d2/a0-a3
		rts

; The loader's long addresses of the unpacker's variables and tables
; (ENH_WORK_LO-ENH_WORK_HI; the decrunched length before them, $34F32, which
; the slave and the tools read, stays), as offsets from ENH_LDR. The same in
; both programs.
ENH_LDR		= $1D000
_enh_work	dc.w	$5BA,$5C2,$5E4,$5EC,$5FA,$628,$62E,$634,$680,$6A6,$6AC,$6B8
		dc.w	$6CE,$6D4,$6E2,$6EC,$704,$782,$7B8,$7BE,$7C4,$7D0,$810,$86E,0

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
_blk_D13C	dc.l	$D13C
_blk_D1C2	dc.l	$D1C2
_blk_D5FC	dc.l	$D5FC
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
		move.l	a0,-(a7)
		lea	_enh_snapped(pc),a0	; no last tick to draw from
		sf	(a0)
		move.l	(a7)+,a0
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
		tst.b	_enh_interp(pc)
		bne	enh_PassI
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
.link		bsr	enh_Rebase
		bra.b	.done

;---------------------------------------------------------------------------
; Frames between ticks (with an ExpMem, fast or not). No tick draws: every
; frame comes from here, drawn while the next tick is early, once a field.
; A frame shows the race between the last two ticks: alpha = fields since the
; last tick was due / fields a tick. It loads the snapshot of the tick before
; (its state at the pass's start), moves the cars on by alpha of their way to
; this tick, and the camera by alpha of the player's step, runs the game's own
; landscape (which follows the track by the step it is given, $10C30) and
; $D13C (the drawing and the swap), and loads this tick's snapshot back. The
; snapshots hold the race state (_enh_r) but not what follows the screens:
; the map markers' positions per screen ($DBD8-$DBE7), the swap's field $E258,
; the screens, the blitter queue ($11268-$11527, which a frame's blits may
; still be reading when it returns; the sky's and the ground's lines $11368
; and $1136C lie in it, and the landscape writes them again before $10F90
; reads them), the sound, the VBL's variables. The race
; clock's gate ($8504) and the bump's sound ($A03C) are left to the ticks
; (enh_Clock, enh_Bump). Behind by ENH_SKIPS_MAX ticks in a row, a frame is
; drawn anyway, of this tick. CUSTOM3=n (for the checks): n frames before
; each tick, at alpha 0, 1/n ..., whatever the time.
;---------------------------------------------------------------------------

; The race state, as the program's addresses (in the race block: its copy's)
; and byte counts. The first two first: the offsets below count on them.
ENH_R		MACRO
		dc.l	\1
		dc.w	(\2)/2-1
ENH_RS		SET	ENH_RS+(\2)
		ENDM
ENH_RS		SET	0
ENH_R1		= $DBE8			; globals, the 16 cars, the car order...
ENH_R2		= $10A90		; the landscape's variables
ENH_O2		= $E254-ENH_R1		; ENH_R2's offset in a snapshot
_enh_r		ENH_R	ENH_R1,$E254-ENH_R1	; to the landscape's result $E254
		ENH_R	ENH_R2,$10C54-ENH_R2	; to the bounce $10C50
		ENH_R	$DBC0,$DBD8-$DBC0	; before the map markers
		ENH_R	$C46E,6			; the opponents' order work
		ENH_R	$1067C,$10694-$1067C	; the landscape's track pointers
		ENH_R	$11784,8		; the steering's state
		ENH_R	$11C84,4		; the start lights' flag $11C86
		ENH_R	$12150,4
		ENH_R	$133DC,4
		ENH_R	$1407C,8		; the horizon's scroll
		ENH_R	$1B28C,8		; the collision's state
		ENH_R	$1B3D4,4
		ENH_R	$8370,4			; the ARCADE score
		ENH_R	$9CD0,$20		; the car order's work
		ENH_R	$4988A,$12		; the three sky objects
		dc.l	0
	IFNE	ENH_RS-ENH_RSIZE
	FAIL	"ENH_RSIZE is not the ranges' size"
	ENDC

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
		cmp.l	#ENH_LO,d0
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
enh_Snap	movem.l	a0-a1,-(a7)
		lea	_enh_bufs(pc),a1
		move.l	(a1),a0
		tst.b	_enh_snapped-_enh_bufs(a1)
		bne.b	.swap
		st	_enh_snapped-_enh_bufs(a1)
		bsr.b	enh_Save
		move.l	ENH_BLOCK.w,a0		; (CUSTOM3's frames may come first)
		move.w	($DBEC,a0),_enh_lat-_enh_bufs(a1)
		move.l	(a1),a0
		bra.b	.cur
.swap		move.l	4(a1),(a1)		; exchange
		move.l	a0,4(a1)
.cur		move.l	4(a1),a0
		bsr.b	enh_Save
		movem.l	(a7)+,a0-a1
		rts

; enh_Pass with frames between ticks (d0-d1 saved; returns through it).
enh_PassI	move.l	d2,-(a7)
		bsr.b	enh_Snap
		moveq	#0,d2
		move.b	ENH_FORCE.w,d2		; CUSTOM3
		bne.b	.forced
.wait		move.l	$A884,d1
		sub.l	ENH_DUE.w,d1		; fields since this tick was due
		bpl.b	.late
		move.l	d1,d0			; early: the field the next frame
		addq.l	#1,d0			; shows in, if it draws within a
		cmp.l	#-1,$A71C		; field: the next, or the one after
		beq.b	.shown			; if a frame waits for the VBL
		addq.l	#1,d0
.shown		tst.l	d0
		bpl.b	.tick			; the tick is due by then: run it now
		move.w	ENH_PERIOD.w,d2
		add.w	d2,d0			; fields since the last tick was due
		bpl.b	.alpha			; (an early tick, then the VBL took
		moveq	#0,d0			; the frame: one field less to wait)
.alpha		bsr	enh_Frame		; (its landscape runs before the wait)
		bra.b	.wait
.late		cmp.l	#ENH_LIMIT,d1
		bls.b	.behind
		add.l	d1,ENH_DROPPED.w	; too far behind: drop the debt
		move.l	$A884,ENH_DUE.w
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
		cmp.b	#ENH_SKIPS_MAX,ENH_SKIPS.w
		bhs.b	.done
		addq.b	#1,ENH_SKIPS.w
.done		move.l	(a7)+,d2
		movem.l	(a7)+,d0-d1
		tst.w	([_blk_DC34,pc])
		rts
.forced		moveq	#0,d0			; n frames, alpha i/n
.frame		bsr	enh_Frame
		addq.w	#1,d0
		cmp.w	d2,d0
		blo.b	.frame
		move.l	$A884,ENH_DUE.w		; no catch-up
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
.alpha
		lea	_enh_an(pc),a2		; for enh_Mix
		move.l	d0,(a2)+
		move.l	d2,(a2)
		lea	_enh_bufs(pc),a2
		st	_enh_frame-_enh_bufs(a2)
		move.l	(a2),a0			; the tick before
		bsr.b	enh_Load
		move.l	4(a2),a1		; this tick
		move.l	ENH_BLOCK.w,a3		; the block's offset
		moveq	#0,d3			; the camera: alpha of the step
		move.w	(ENH_O2+$10C30-ENH_R2,a1),d3
		mulu.l	d0,d3
		divu.l	d2,d3
		move.l	($DBD4,a3),d7		; the track's length: the ticks wrap
		subq.l	#1,d7			; the distances at the line, so a
		sub.l	($DC50,a3),d7		; frame stops short of it
		cmp.l	d7,d3
		bls.b	.step
		move.l	d7,d3
.step		move.w	d3,($10C30,a3)
		add.l	d3,($DC50,a3)
		move.l	($DBD4,a3),d7
		move.w	($DC60-ENH_R1,a1),($DC60,a3)	; this tick's speed and controls
		move.w	(ENH_O2+$10C46-ENH_R2,a1),($10C46,a3)
		move.w	($DBF8-ENH_R1,a1),($DBF8,a3)
		lea	($DC4E+64,a3),a4	; the other cars: alpha of the way,
		lea	($DC4E+64-ENH_R1,a1),a5	; distance (+2) and lateral (+8)
		moveq	#15-1,d4
.car		move.l	2(a5),d5
		sub.l	2(a4),d5
		bsr.b	.part
		add.l	2(a4),d5
		cmp.l	d7,d5			; across the line: as the tick before
		bhs.b	.lateral
		move.l	d5,2(a4)
.lateral
		move.w	8(a5),d5
		ext.l	d5
		move.w	8(a4),d6
		ext.l	d6
		sub.l	d6,d5
		bsr.b	.part
		add.w	d5,8(a4)
		lea	64(a4),a4
		lea	64(a5),a5
		dbf	d4,.car
		move.w	($DBEC,a3),d0		; the camera's lateral position:
		move.w	_enh_lat(pc),d1		; the race loop's steering ($BC9E-
		bsr	enh_Mix			; $BDAA) moves it before the
		move.w	d1,($DBEC,a3)		; landscape, once a tick
		move.w	($DC56,a3),d0		; the player's (the race loop's copy
		move.w	($DC56-ENH_R1,a1),d1	; of $DBF0, $C55C): the mirrors, the
		bsr	enh_Mix			; crash
		move.w	d1,($DC56,a3)
		bsr	enh_QueueIdle
		move.l	ENH_BLOCK.w,a3		; the landscape, as $C960-$C984
		move.w	($DBEC,a3),($DBEE,a3)
		jsr	($E4F8,a3)
		move.l	ENH_BLOCK.w,a3
		bsr	enh_Sky
		move.l	a6,($E254,a3)
		move.w	($DBEC,a3),d7
		sub.w	d7,($DBEE,a3)
		neg.w	d7
		sub.w	#66,d7
		move.w	d7,($DBF0,a3)
		bsr	fix_WaitShown		; the map marker, as $C8F2-$C91C,
		move.l	ENH_BLOCK.w,a3		; after it: the CPU draws it into
		movea.l	#$4A90A,a1		; the screen
		move.l	$86DE,d5
		lea	($DBD8,a3),a4
		move.w	(a4,d5.w),d4
		jsr	($1284C,a3)
		move.l	ENH_BLOCK.w,a3
		move.l	($DC50,a3),d4
		lea	($DBD2,a3),a0
		divu.w	(a0),d4
		move.w	d4,(a4,d5.w)
		jsr	($12808,a3)
		move.l	ENH_BLOCK.w,a3
		sf	ENH_SKIP.w		; and the drawing
		jsr	($D13C,a3)
		lea	_enh_bufs(pc),a2
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

; A frame's horizon and sky objects. The horizon's scroll ($13F16, from
; $10F90) and the three sky objects ($4988A, $C9C0-$C9FA) move by $10C42,
; which in a tick the race loop sets after the landscape ($C99A: the
; steering's turn $DC3E with the landscape's remainder) and in a frame only
; the landscape sets (the curve's part). A frame moves both by alpha of this
; tick's $10C42 from the tick before: the objects (the mountain's top) and
; the horizon (its foot) together.
; IN:	a3 = the block's offset
; OUT:	-	d0-d1, d4, a0-a1, a4-a5 used
enh_Sky		move.l	_enh_bufs+4(pc),a1	; this tick
		moveq	#0,d0
		move.w	(ENH_O2+$10C42-ENH_R2,a1),d1
		bsr	enh_Mix
		move.w	d1,($10C42,a3)
		move.l	_enh_bufs(pc),a4	; the tick before's objects
		lea	(ENH_RSIZE-$12,a4),a4	; (the snapshot's last range)
		lea	(ENH_RSIZE-$12,a1),a5
		lea	$4988A,a0
		moveq	#3-1,d4
.obj		tst.w	(a4)
		bmi.b	.out
		move.w	2(a4),d0
		move.w	2(a5),d1
		sub.w	d0,d1			; the shorter way round the 1264
		cmp.w	#632,d1
		ble.b	.lo
		sub.w	#1264,d1
.lo		cmp.w	#-632,d1
		bge.b	.hi
		add.w	#1264,d1
.hi		add.w	d0,d1
		bsr	enh_Mix
		tst.w	d1
		bpl.b	.pos
		add.w	#1264,d1
.pos		cmp.w	#1264,d1
		blt.b	.in
		sub.w	#1264,d1
.in		move.w	d1,2(a0)
		addq.l	#6,a0
		addq.l	#6,a4
		addq.l	#6,a5
		dbf	d4,.obj
.out		rts

; The landscape's pitch and height ($F396, after its simulation part: the
; bounce, the jump, the acceleration's tilt from the step's change, the shake
; off the road), which feed the horizon $10B32 and the projection. Each runs
; once a pass and integrates by the pass, so a frame re-running it from the
; tick before gets a whole pass of it (and a tilt from its own part step):
; a frame takes alpha of the way between the two ticks' values instead. The
; mixed pitch goes back to $10ACA too: the flat road ($10AD8 zero) reads it
; again at $F436.
; IN:	d3.w = the height; OUT: d1.w = the pitch, d3, and the flags of
;	cmpi.w #21000,d1 (the replaced instructions)
enh_Pitch	tst.b	_enh_frame(pc)
		bne.b	.frame
		move.l	a0,-(a7)
		move.l	ENH_BLOCK.w,a0
		move.w	($10ACA,a0),d1
		move.l	(a7)+,a0
		cmp.w	#21000,d1
		rts
.frame		movem.l	d0/a0-a1,-(a7)
		movem.l	_enh_bufs(pc),a0-a1	; the tick before, this tick
		move.w	(ENH_O2+$10C4E-ENH_R2,a0),d0
		move.w	(ENH_O2+$10C4E-ENH_R2,a1),d1
		bsr	enh_Mix
		move.w	d1,d3
		move.w	(ENH_O2+$10ACA-ENH_R2,a0),d0
		move.w	(ENH_O2+$10ACA-ENH_R2,a1),d1
		bsr	enh_Mix
		move.l	ENH_BLOCK.w,a0		; for the flat road's $F436 too
		move.w	d1,($10ACA,a0)
		movem.l	(a7)+,d0/a0-a1
		cmp.w	#21000,d1
		rts

; The crash's flying wheel ($D7BE-$D814): its step $E0DC indexes a table of
; positions ($E134: x at +4, the line's offset at +8), one step a pass. A
; frame draws the tick before's step: it takes alpha of the way from the
; step before it.
; IN:	d3.w = step*16, a3 = the table, d4.w = the side (-1 mirrored), d6 =
;	the x, a5, d5 = the object and the screen's offset
; OUT:	(10,a5,d5.w) = x, (0,a5,d5.w) = the line's offset
enh_WheelXY	tst.b	_enh_frame(pc)
		beq.b	.set
		tst.w	d3
		beq.b	.set			; the first step
		movem.l	d0-d2/d6,-(a7)
		move.l	(4-16,a3,d3.w),d0	; x: from the step before
		sub.l	(4,a3,d3.w),d0
		tst.w	d4
		bpl.b	.side
		neg.l	d0
.side		add.w	d6,d0
		move.w	d6,d1
		bsr	enh_Mix
		ext.l	d1
		move.l	d1,(10,a5,d5.w)
		move.l	(8-16,a3,d3.w),d0	; the line
		divu.w	#40,d0
		move.l	(8,a3,d3.w),d1
		divu.w	#40,d1
		bsr	enh_Mix
		mulu.w	#40,d1
		move.l	d1,(0,a5,d5.w)
		movem.l	(a7)+,d0-d2/d6
		rts
.set		move.l	d6,(10,a5,d5.w)
		move.l	(8,a3,d3.w),(0,a5,d5.w)
		rts

; The landscape writes the sky's line $11368, which lies in the blitter queue
; ($11268-$11527): the queue the last frame left running (its last entries,
; the wheel's, $11C88, reach past $11368) must be done first. The original
; loop waited for the VBL to take the frame before the landscape
; (fix_Landscape); here the landscape comes first.
; IN:	-
; OUT:	-	all registers preserved
enh_QueueIdle	move.l	a6,-(a7)
		jsr	FIX_TRAMP.w		; fix_Queue: waits for it
		move.l	(a7)+,a6
		rts

; The race clock's gate and the bump's sound: the ticks', not the frames'.
enh_Clock	tst.b	_enh_frame(pc)
		bne.b	.out
		clr.w	$8504
.out		rts
enh_Bump	tst.b	_enh_frame(pc)
		bne.b	.out
		move.w	d0,$A03C
.out		rts
; The engine's pitch from the revs: the ticks' too. A frame's comes from the
; tick before's revs, so the target went back and forth every tick, and the
; sound's glide ($999A) and its sample switch at 138 ($9A0C, through the
; audio interrupt) with it: a glitch mid-way up the revs, and at times the
; wrong sample's pitch.
enh_Engine	tst.b	_enh_frame(pc)
		bne.b	.out
		move.w	d5,$9FC4
.out		rts

_enh_an		dc.l	0		; a frame's alpha: _enh_an/_enh_ad
_enh_ad		dc.l	1
_enh_lat	dc.w	0		; $DBEC as the tick's landscape started
_enh_bufs	dc.l	0,0		; the snapshots: the tick before, this tick
_enh_snapped	dc.b	0		; they hold a tick
_enh_frame	dc.b	0		; a frame between ticks is drawing
_enh_interp	dc.b	0		; frames between ticks (an ExpMem)
		even


; The landscape, then the wait for the VBL to take the last frame: the race
; loop's panel updates ($CA10-$CCFA) after it draw into the screens, and with
; frames between ticks a tick often runs while the last frame still waits.
enh_Landscape	movem.l	a0-a1,-(a7)		; the camera's lateral position
		move.l	ENH_BLOCK.w,a0		; as the landscape starts (enh_Frame)
		lea	_enh_lat(pc),a1
		move.w	($DBEC,a0),(a1)
		movem.l	(a7)+,a0-a1
		bsr	enh_QueueIdle
		jsr	([_blk_E4F8,pc])
		bra	fix_WaitShown

; A tick with frames between ticks leaves out what the frames draw: the map
; marker ($C8F8-$C95F), the HUD in $D13C ($120A6; the wheel's lower part
; $118D8, from $D20A; $D21C-$D3BB: the cockpit, the mirrors, the gear, the
; speed, the wheel; the score's or the time's digits). Each goes on where the
; drawing ends. A tick may run while the last frame waits for the VBL, so
; whatever it drew would land in the screen on display.
ENH_TICK	MACRO			; to \1 unless this pass is such a tick
		tst.b	_enh_interp(pc)
		beq.b	\1
		tst.b	ENH_SKIP.w
		beq.b	\1
		ENDM
ENH_GOTO	MACRO			; return to the block's \1
		move.l	ENH_BLOCK.w,(a7)
		add.l	#\1,(a7)
		rts
		ENDM
enh_Marker	ENH_TICK .draw
		ENH_GOTO $C960
.draw		move.l	$86DE,d5
		rts
enh_Hud0	ENH_TICK .draw
		addq.l	#4,a7			; out of $120A6
		rts
.draw		move.l	a0,-(a7)
		move.l	ENH_BLOCK.w,a0
		move.w	($12150,a0),d0
		move.l	(a7)+,a0
		addq.w	#1,d0
		rts
enh_Hud		tst.w	d0			; $DC38
		bmi.b	.nopit
		jsr	([_blk_D5FC,pc])
.nopit		ENH_TICK .draw
		ENH_GOTO $D3BC
.draw		rts
enh_Wheel	ENH_TICK .draw
		addq.l	#4,a7			; out of $118D8
		rts
.draw		movea.l	#$DFF000,a6
		rts
enh_Score	ENH_TICK .draw
		ENH_GOTO $D48A
.draw		lea	$8374,a0
		rts
enh_Time	ENH_TICK .draw
		ENH_GOTO $D48A
.draw		lea	$850E,a0
		rts

; The cars ahead of the camera, sorted by distance into the list at $10B3E
; ($ED5A-$EDD6): the insertion walks down until an entry is no further than
; this car, and the word 0 at $10B3A ends it. A tick takes them in the car
; order from the camera on, all ahead of it. A frame mixes the cars and the
; camera, which moves by alpha of the player's step, but keeps the tick
; before's order: a car the player passes in this tick can be behind the
; camera. Its distance ahead is then negative, the walk runs below the list
; and the insertion moves the landscape's variables up ($10ADA, the road's
; detail, indexes a jump table at $10776: an Illegal Instruction at $10B76 on
; the a1200-030 in a player race). A frame leaves such a car out: it is
; behind the camera.
; IN:	d1 = the car's distance, d7 = the camera's
; OUT:	d1 = the car's distance ahead, the flags as cmpi.l #32767,d1
enh_Sort	sub.l	d7,d1
		bpl.b	.ahead
		tst.b	_enh_frame(pc)
		beq.b	.ahead
		ENH_GOTO $ED5A			; the next car
.ahead		cmpi.l	#32767,d1
		rts

; $D13C's first drawing: $10F90 waits for the blitter queue ($1B0, src/fixes.i's
; fix_Queue), lets $13F16 scroll the horizon (its blits go into the queue),
; queues the sky and ground clear, clamps the ground's top line $1136C and
; starts the queue; then the CPU fills the ground (enh_Ground). A pass that
; does not draw keeps the state: the queue is
; written as $10F90 would, but not started.
enh_Clear	tst.b	ENH_SKIP.w
		bne.b	.undrawn
		jsr	([_blk_10F90,pc])
		bra	enh_Ground
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

; The ground's fill: the two planes the queue's ground entries fill ($1103A-
; $11077: plane 2 with 0, 3 with 1, from the ground's top line $1136C to the
; screen's end; the road spans $10CD2 draw the others). The CPU fills them
; while the blitter runs the rest of the queue $10F90 started (the horizon and
; the sky), which goes without those entries. Measured against other splits
; (docs/open-work.md, step 24), this one is the fastest.
; IN:	-
; OUT:	-	all registers preserved
enh_Ground	movem.l	d0-d2/a0-a1,-(a7)
		move.l	#8000,d0
		move.l	([_blk_1136C,pc]),d1
		sub.l	d1,d0
		ble.b	.out
		move.l	$86EA,a0
		add.l	#16000,a0
		add.l	d1,a0			; plane 2: 0
		lea	8000(a0),a1		; plane 3: 1
		lsr.l	#3,d0
		subq.l	#1,d0
		moveq	#0,d1
		moveq	#-1,d2
.fill		move.l	d1,(a0)+
		move.l	d1,(a0)+
		move.l	d2,(a1)+
		move.l	d2,(a1)+
		dbf	d0,.fill
.out		movem.l	(a7)+,d0-d2/a0-a1
		rts

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

;---------------------------------------------------------------------------
; 64-bit bitplane fetch (AGA; docs/internals.md, "64-bit fetch"). Four lores
; planes fetched 16 bits at a time take one chip bus slot in two on a display
; line; FMODE 3 takes a quarter of that, and the slots go to the blitter, whose
; time is the gap to 50 fps. It needs every plane on an 8-byte boundary: the
; two screens ($1FAC6 and $277C6, 8000-byte planes, 40-byte rows) move down by
; ENH_SCR_D bytes, into the fill below the first one. Every reference to them:
; the startup's (the first picture and its plane pointers into the copper list
; $A720; the data disk's loader has a copy of the first, $1DA6E-$1DAA3), the
; screens' and the draw buffer's pointers $86E2/$86E6/$86EA, the screen the
; VBL shows next $A71C, the copper lists' initial plane pointers ($A720,
; $A78C), and three in the race's map code ($1278C, $12A62, $12BC4); the rest
; takes them from the pointers. Its own fetch window: the mode setting ($A4A6)
; writes DDFSTOP $D0 for FMODE 0; the 64-bit fetch of the same 320 pixels at
; the same place stops at $B0 (DDFSTRT $38 for both). Every lores plane
; pointer setting ($A32C, $A3F4: the VBL's new screen; $A4A6: a new mode) picks
; the fetch by the address it sets, so a screen not moved keeps FMODE 0. The
; hires mode ($A388, $A4C0) keeps FMODE 0.
;---------------------------------------------------------------------------

ENH_SCR_D	= 6			; the screens' move down

ENH_SCR		MACRO			; a long that holds a screen address
		dc.l	\1,\2
		ENDM
_enh_scr0	ENH_SCR	$3676,$1FAC6		; Vroom's startup
		ENH_SCR	$36B0,$277C6
		ENH_SCR	$36C2,$1FAC6
		ENH_SCR	$36C8,$277C6
		ENH_SCR	$3BBA,$277C6
		ENH_SCR	$3BC8,$277C6+8000
		ENH_SCR	$3BD8,$277C6+2*8000
		ENH_SCR	$3BE8,$277C6+3*8000
		dc.l	0
_enh_scr1	ENH_SCR	$3676,$1FAC6		; the data disk's startup
		ENH_SCR	$36EA,$277C6
		ENH_SCR	$36FC,$1FAC6
		ENH_SCR	$3702,$277C6
		ENH_SCR	$3BAA,$277C6
		ENH_SCR	$3BB8,$277C6+8000
		ENH_SCR	$3BC8,$277C6+2*8000
		ENH_SCR	$3BD8,$277C6+3*8000
		ENH_SCR	$1DA7C,$277C6		; and its loader's copy of the
		ENH_SCR	$1DA8E,$1FAC6		; first picture's
		ENH_SCR	$1DA94,$277C6
		dc.l	0
_enh_scrc	ENH_SCR	$86E2,$1FAC6		; both programs'
		ENH_SCR	$86E6,$277C6
		ENH_SCR	$1278E,$1FAC6+$99A	; the race's map code
		ENH_SCR	$12A64,$1FAC6
		ENH_SCR	$12BC6,$1FAC6+$434
		dc.l	0
_enh_scro	ENH_SCR	$86EA,$1FAC6		; the draw buffer and the displayed
		ENH_SCR	$86EA,$277C6		; screen: either (not required)
		ENH_SCR	$A71C,$1FAC6
		ENH_SCR	$A71C,$277C6
		dc.l	0
_enh_scrw	dc.w	$A726,$77C6		; the copper lists' planes' low words
		dc.w	$A72E,$77C6+8000
		dc.w	$A736,$77C6+2*8000
		dc.w	$A73E,$77C6+3*8000
		dc.w	$A792,$77C6
		dc.w	$A79A,$77C6+8000
		dc.w	$A7A2,$77C6+2*8000
		dc.w	$A7AA,$77C6+3*8000
		dc.w	0

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
		lea	_enh_scrc(pc),a0	; at the first Fix all of a program's
		bsr.b	enh_ScrHeld		; references hold the screens
		bne.b	.out
		lea	_enh_scr0(pc),a0	; and which program's startup
		bsr.b	.held
		beq.b	.on
		lea	_enh_scr1(pc),a0
		bsr.b	.held
		bne.b	.out
.on		lea	_enh_fmlist(pc),a1
		move.l	a0,(a1)
		lea	_enh_fm(pc),a0
		st	(a0)
.out		movem.l	(a7)+,d0-d1/a0-a1
		rts
.held		move.l	a0,-(a7)
		bsr.b	enh_ScrHeld
		movem.l	(a7)+,a0		; (the flags stay)
		rts

; At every Fix (a load may bring the original values back): the screens'
; references that still hold the original addresses move, and the plane
; pointer settings pick the fetch.
; IN:	-
; OUT:	-	all registers preserved
enh_Fmode	tst.b	_enh_fm(pc)
		beq.b	.out
		movem.l	d0-d1/a0-a2,-(a7)
		move.l	_enh_fmlist(pc),a0	; the program's startup
		bsr.b	enh_ScrMove
		lea	_enh_scrc(pc),a0
		bsr.b	enh_ScrMove
		lea	_enh_scro(pc),a0
		bsr.b	enh_ScrMove
.words		lea	_enh_scrw(pc),a0
.word		moveq	#0,d0
		move.w	(a0)+,d0
		beq.b	.patch
		move.l	d0,a1
		move.w	(a0)+,d1
		cmp.w	(a1),d1
		bne.b	.word
		subq.w	#ENH_SCR_D,(a1)
		bra.b	.word
.patch		lea	_enh_fmpl(pc),a0
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
		subq.l	#ENH_SCR_D,(a1)
		bra.b	enh_ScrMove
.out		rts

_enh_fmpl	PL_START
		PL_PS	$A32C,enh_Ptr0		; lea $A722(pc),a1; moveq #3,d0
		PL_PS	$A388,enh_Ptr1		; lea $A74E(pc),a1; moveq #1,d0
		PL_PS	$A3F4,enh_Ptr2		; lea $A78E(pc),a1; moveq #3,d0
		PL_P	$A4A6,enh_Lores		; the lores mode
		PL_P	$A4C0,enh_Hires		; the hires mode
		PL_END

; The VBL's new screen (d1) into a copper list's plane pointers.
enh_Ptr0	bsr.b	enh_Fetch
		lea	$A722,a1
		moveq	#3,d0
		rts
enh_Ptr1	move.w	#0,_custom+fmode
		lea	$A74E,a1
		moveq	#1,d0
		rts
enh_Ptr2	bsr.b	enh_Fetch
		lea	$A78E,a1
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

_enh_fmlist	dc.l	0		; the program's startup references
_enh_fm		dc.b	0		; the 64-bit fetch is on
_enh_state	dc.b	0		; 0 unknown, -1 off, 1 on
_enh_moved	dc.b	0		; the block has been copied (or stays)
		even
