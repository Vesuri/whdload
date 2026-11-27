;---------------------------------------------------------------------------
; Vroom Multiplayer's fixes for CPU caches and fast CPUs (docs/internals.md,
; "Fixes"): games/Vroom's src/fixes.i at the Multiplayer's (v1) addresses.
; v2 (NTSC) is not among the inputs, so only v1 gets them.
;---------------------------------------------------------------------------

	INCLUDE	blitwait.i

; IN:	-
; OUT:	-	all registers preserved
FIX_TRAMP	= $1B0			; JMP trampolines, after src/smc.i's
FIX_TRAMP2	= $1B6

BLIT_TRAMP	= $10C			; WaitBlit0-6, after the original slave's
					; $100-$10B (as in Vroom's original slave)

Fix		movem.l	d0-d1/a0-a2,-(a7)
		lea	BLIT_TRAMP.w,a0
		lea	_blit_tramps(pc),a1
		moveq	#5-1,d1
.blit		move.w	#$4EF9,(a0)+		; jmp xxx.l
		lea	_blit_tramps(pc),a2
		add.w	(a1)+,a2
		move.l	a2,(a0)+
		dbf	d1,.blit
		lea	FIX_TRAMP.w,a0
		move.w	#$4EF9,(a0)+		; jmp xxx.l
		pea	fix_Queue(pc)
		move.l	(a7)+,(a0)+
		move.w	#$4EF9,(a0)+
		pea	fix_Tyres(pc)
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

; A decrunch over the program lands on patched code: patch it again.
; src/smc.i's variables keep their state.
; IN:	-
; OUT:	-	all registers preserved
FIX_LO		= SMC_LO		; lowest and highest+1 patched address
FIX_HI		= SMC_HI

Fix_Decrunched	move.l	d0,-(a7)
		move.l	$1F25A,d0		; destination
		cmp.l	#FIX_HI,d0
		bhs.b	.no
		add.l	$3623A,d0		; + decrunched length
		cmp.l	#FIX_LO,d0
		bls.b	.no
		bsr	Fix
.no		move.l	(a7)+,d0
		rts

; the program's decrunch call ($1EA00: movem, bsr.w $1F0E4, movem,
; move.w #-1,$3A.l, rts), and Fix_Decrunched after it
fix_Decrunch	movem.l	d0-a6,-(a7)
		jsr	$1F0E4			; A0=source A1=dest
		movem.l	(a7)+,d0-a6
		bsr	Fix_Decrunched
		move.w	#-1,$3A.w
		rts

_fix_pl		PL_START
		PL_P	$1EA00,fix_Decrunch
	; Vroom's original slave's blitter waits, which this slave lacked: each
	; blitter start in the renderer waits for its blit (src/blitwait.i), the
	; init code's waits read dmaconr once first (CHKBLTWAIT stopped at $1767E)
		BLITWAIT_STARTS
		PL_PS	$13344,WaitBlit7	; move.w d0,$DFF058
		BLITWAIT_LOOPS
	; the VBL routine's drive motor off ($AFFE: or/and/or on ciab.prb):
	; WHDLoad owns the drives
		PL_W	$B004,$600A		; bra.s $B010
	; the blitter queue: the blitter-done interrupt ($AB8A) starts the next
	; queued blit while the last one is still finishing
		PL_PSS	$AB8C,fix_BlitInt,2	; move.w #INTF_BLIT,intreq
	; the blitter queue: the CPU starts writing a new queue ($11D2A) or
	; programming the blitter ($13070 and $13122, the cars' tyres; $13206)
	; after waiting only for the current blit ($11FA6), so a fast CPU
	; overwrites a queue the interrupt is still running (and it jumps to a
	; field as its next handler: a crash at $4). They wait as the game's other
	; blitter users do: $11FDE waits for the queue to finish and the blitter
		PL_L	$11D2A,$4EB80000+FIX_TRAMP	; lea $12032(pc),a6
		PL_L	$13072,$11FDE		; jsr $11FA6
		PL_L	$13124,$11FDE		; jsr $11FA6
	; the tyres then write the blitter through a6, which $11FA6 kept at
	; $DFF000 and $11FDE leaves at $1202A
		PL_L	$13076,$4EB80000+FIX_TRAMP2	; move.l a4,84(a6)
		PL_L	$13128,$4EB80000+FIX_TRAMP2	; move.l a4,84(a6)
		PL_L	$13208,$11FDE		; jsr $11FA6
	; the keyboard handshake: $C8 loops of nop/dbf, a count the boot loader
	; would have calibrated and the original slave set to $F0
		PL_PSS	$AD6A,fix_KbdDelay,6	; move.w $C8.l,d0; nop; dbf d0,*-2
		PL_END

	; CPU-timed delays (dbf to itself), on a 68020 or higher: beam waits
	; of their length on a 68000 (10 cycles a dbf, 454 cycles a line)
_fix_pl020	PL_START
		PL_PSS	$46E0,fix_Wipe,2	; the menu's two wipes, after each
		PL_PSS	$5334,fix_Wipe,2	; line: move.w #3000,d2; dbf d2,*
		PL_PSS	$4822,fix_Delay9,10	; after a menu choice: 9 x 32001 dbf
		PL_PSS	$8978,fix_Delay11,10	; 11 x 32001 dbf
		PL_PSS	$1682A,fix_Delay11,10	; the same, d0 and d1 swapped
		PL_END

_blit_tramps	dc.w	WaitBlit0-_blit_tramps	; $10C: d0
		dc.w	WaitBlit1-_blit_tramps	; $112: d1
		dc.w	WaitBlit4-_blit_tramps	; $118: d4
		dc.w	WaitBlit5-_blit_tramps	; $11E: d5
		dc.w	WaitBlit6-_blit_tramps	; $124: d6

WaitBlit7	move.w	d0,_custom+bltsize
		bra.b	WaitBlit
WaitBlit0	move.w	d0,bltsize(a6)
		bra.b	WaitBlit
WaitBlit1	move.w	d1,bltsize(a6)
		bra.b	WaitBlit
WaitBlit4	move.w	d4,bltsize(a6)
		bra.b	WaitBlit
WaitBlit5	move.w	d5,bltsize(a6)
		bra.b	WaitBlit
WaitBlit6	move.w	d6,bltsize(a6)
WaitBlit	BLITWAIT
		rts

fix_Queue	move.l	_blk_11FDE(pc),a6	; it uses a6
		jsr	(a6)
		move.l	_blk_12032(pc),a6
		rts

fix_Tyres	lea	_custom,a6
		move.l	a4,bltdpt(a6)
		rts

fix_BlitInt	move.w	#INTF_BLIT,_custom+intreq
		BLITWAIT
		rts

fix_KbdDelay	move.l	d0,-(a7)
		moveq	#3,d0			; at least 2 lines: over the 75 us
		bsr.b	fix_WaitLines		; the keyboard needs
		move.l	(a7)+,d0
		rts

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

; The program's addresses the slave's code jumps to or reads (named by their
; address; one place to move them from)
_blk_10570	dc.l	$10570
_blk_1062C	dc.l	$1062C
_blk_10652	dc.l	$10652
_blk_10788	dc.l	$10788
_blk_1078A	dc.l	$1078A
_blk_11328	dc.l	$11328
_blk_1134C	dc.l	$1134C
_blk_11FDE	dc.l	$11FDE
_blk_12032	dc.l	$12032
_blk_1B9A0	dc.l	$1B9A0
_blk_1B9A4	dc.l	$1B9A4

	INCLUDE	smc.i
