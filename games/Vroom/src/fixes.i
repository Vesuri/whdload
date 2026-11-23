;---------------------------------------------------------------------------
; Fixes shared by both slaves (docs/internals.md, "Fixes"). The program is the
; same at every address here.
;---------------------------------------------------------------------------

; IN:	-
; OUT:	-	all registers preserved
FIX_TRAMP	= $1B0			; a JMP trampoline, after src/smc.i's

Fix		movem.l	d0-d1/a0-a2,-(a7)
		lea	FIX_TRAMP.w,a0
		move.w	#$4EF9,(a0)+		; jmp xxx.l
		pea	fix_Queue(pc)
		move.l	(a7)+,(a0)
		lea	_fix_pl(pc),a0
		sub.l	a1,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
		movem.l	(a7)+,d0-d1/a0-a2
		bra	FixSMC

_fix_pl		PL_START
	; the VBL routine's drive motor off ($A50E: or/and/or on ciab.prb):
	; WHDLoad owns the drives
		PL_W	$A514,$600A		; bra.s $A520
	; the blitter queue: the blitter-done interrupt ($A092) starts the next
	; queued blit while the last one is still finishing
		PL_PSS	$A094,fix_BlitInt,2	; move.w #INTF_BLIT,intreq
	; the blitter queue: the CPU starts writing a new queue ($10F90) or
	; programming the blitter ($11BE4, $11CA6) after waiting only for the
	; current blit, so a fast CPU overwrites a queue the interrupt is still
	; running (and it jumps to a field as its next handler: a crash at $4).
	; They wait as the game's other blitter users do: $1123A waits for the
	; queue to finish and the blitter
		PL_L	$10F90,$4EB80000+FIX_TRAMP	; lea $11268(pc),a6
		PL_L	$11BE6,$1123A		; jsr $11202
		PL_L	$11CA8,$1123A		; jsr $11202
		PL_END

fix_Queue	jsr	$1123A			; uses a6
		lea	$11268,a6
		rts

fix_BlitInt	move.w	#INTF_BLIT,_custom+intreq
		BLITWAIT
		rts

	INCLUDE	smc.i
