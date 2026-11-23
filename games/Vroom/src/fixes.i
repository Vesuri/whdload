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
		bsr	FixSMC			; sets _smc_state from the CPU
		lea	_smc_state(pc),a0
		tst.b	(a0)
		ble.b	.done			; a 68000 or 68010 runs the game's delays
		lea	_fix_pl020(pc),a0
		sub.l	a1,a1
		jsr	resload_Patch(a2)
.done		movem.l	(a7)+,d0-d1/a0-a2
		rts

; A decrunch over the program (it reloads part of itself to $439C) lands on
; patched code: patch it again. src/smc.i's variables keep their state.
; IN:	-
; OUT:	-	all registers preserved
FIX_LO		= SMC_LO		; lowest and highest+1 patched address
FIX_HI		= SMC_HI

Fix_Decrunched	move.l	d0,-(a7)
		move.l	$1D90E,d0		; destination
		cmp.l	#FIX_HI,d0
		bhs.b	.no
		add.l	$34F32,d0		; + decrunched length
		cmp.l	#FIX_LO,d0
		bls.b	.no
		bsr	Fix
.no		move.l	(a7)+,d0
		rts

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
	; the keyboard handshake: $C8 loops of nop/dbf, a count the boot loader
	; would have calibrated and the original slave set to 0
		PL_PSS	$A2AC,fix_KbdDelay,4	; move.w $C8.w,d0; nop; dbf d0,*-2
		PL_END

	; CPU-timed delays (dbf to itself), on a 68020 or higher: beam waits
	; of their length on a 68000 (10 cycles a dbf, 454 cycles a line)
_fix_pl020	PL_START
		PL_PSS	$481A,fix_Wipe,2	; the menu's two wipes, after each
		PL_PSS	$534A,fix_Wipe,2	; line: move.w #3000,d2; dbf d2,*
		PL_PSS	$4986,fix_Delay9,10	; after a menu choice: 9 x 32001 dbf
		PL_PSS	$816C,fix_Delay11,10	; 11 x 32001 dbf
		PL_PSS	$153CA,fix_Delay11,10	; the same, d0 and d1 swapped
	; the race loop's landscape ($C968) draws into the buffer the frame end
	; ($D51A) has just handed to the VBL's $A71C: until the next VBL shows it,
	; that buffer is still on screen. Wait until the VBL has taken it
		PL_PS	$C968,fix_Landscape	; jsr $E4F8
		PL_END

fix_Queue	jsr	$1123A			; uses a6
		lea	$11268,a6
		rts

fix_BlitInt	move.w	#INTF_BLIT,_custom+intreq
		BLITWAIT
		rts

fix_KbdDelay	move.l	d0,-(a7)
		moveq	#3,d0			; at least 2 lines: over the 75 us
		bsr.b	fix_WaitLines		; the keyboard needs
		move.l	(a7)+,d0
		rts

; at most 2 fields, in case no VBL takes the buffer
fix_Landscape	movem.l	d0-d1,-(a7)
		move.l	$A884,d1		; the field counter
.wait		cmp.l	#-1,$A71C		; -1: the VBL has taken it
		beq.b	.go
		move.l	$A884,d0
		sub.l	d1,d0
		subq.l	#2,d0
		bcs.b	.wait
.go		movem.l	(a7)+,d0-d1
		jmp	$E4F8

; dbf leaves the counters at -1 (their low words)
fix_Wipe	move.l	d0,-(a7)
		moveq	#66,d0			; 30022 cycles
		bsr.b	fix_WaitLines
		move.l	(a7)+,d0
		move.w	#-1,d2
		rts

fix_Delay9	move.w	#6344,d0		; 2880296 cycles, 20.3 fields
		bra.b	fix_Delay
fix_Delay11	move.w	#7754,d0		; 3520360 cycles, 24.8 fields
fix_Delay	bsr.b	fix_WaitLines
		move.w	#-1,d0
		move.w	d0,d1
		rts

; IN:	d0.w = raster lines to wait (1 or more): changes of the beam's line
; OUT:	-	all registers preserved
fix_WaitLines	movem.l	d0-d1,-(a7)
.line		move.b	_custom+vhposr,d1
.same		cmp.b	_custom+vhposr,d1
		beq.b	.same
		subq.w	#1,d0
		bne.b	.line
		movem.l	(a7)+,d0-d1
		rts

	INCLUDE	smc.i
