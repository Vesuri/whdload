;*---------------------------------------------------------------------------
;  :Program.	Battlehawks1942.s
;  :Contents.	Slave for "Battlehawks 1942" from Lucasfilm Games
;  :Original	PAL v1.0
;  :History.	12.05.03 v1.0 Galahad of Fairlight (no source distributed; reconstructed
;		in original/Battlehawks1942.s, which rebuilds it byte-identically)
;		06.10.26 rebased on WHDLoad 20.0 KickEmu (kick13.s) for the performance
;		study; behaviour as v1.0
;		09.11.26 caches on (KickEmu CACHE); CUSTOM2=1 Enhanced framerate
;		(timing.s, from Their Finest Hour 2.0b)
;  :Copyright.	Public Domain
;  :Language.	68000 Assembler
;  :Translator.	vasm
;---------------------------------------------------------------------------*
;
; Kickstart 1.3, 512 KB chip RAM plus 512 KB fast memory, the game boots from its own Disk.1
; (startup-sequence runs BH), and the manual check accepts any answer (Return still has to be
; pressed). Galahad's v1.0 gave the game chip RAM only ("SLOW": with fast RAM the game runs
; too fast, its game time follows the frame rate). Here only what DMA needs is in chip RAM:
; BH's hunks are "any" memory, and BH allocates sample data MEMF_CHIP and everything else
; MEMF_ANY (bitplanes come from the OS), so the code, data and chunky buffers go to fast
; memory with no patch to BH. WHDLoad takes the fast memory from chip RAM when a machine has
; no other.
; v1.0 patched the Kickstart image itself and hooked LoadSeg; here KickEmu does the OS part
; and _cb_dosLoadSeg patches BH. All addresses in patch lists are BH hunk-0 offsets.
; pl_bh is v1.0's patch (the manual check) and the VERIFY instruments; everything for
; CUSTOM2=1 is in timing.s's own patch list, so without it BH runs as in v1.0. v1.0 ran
; with the caches off (KickEmu without CACHE turns them all off); they are on here
; (WHDLoad's default, chip memory not cached), with or without CUSTOM2.

	INCDIR	Include:
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	INCLUDE	lvo/dos.i
	INCLUDE	exec/interrupts.i
	INCLUDE	hardware/intbits.i

;============================================================================

CHIPMEMSIZE	= $80000
	IFND	FASTMEMSIZE
	IFD	VERIFY
FASTMEMSIZE	= $90000		;and 56 KB for the flight record (tape.s)
	ELSE
FASTMEMSIZE	= $81000		;-DFASTMEMSIZE=0: chip only, like v1.0; 4 KB for timing.s
	ENDC
	ENDC
NUMDRIVES	= 3		;Disk.1-3 in DF0-DF2: the game never asks for a swap
WPDRIVES	= %1111		;v1.0 let the game write every disk (pilot records)

DISKSONBOOT
SETPATCH
CBDOSLOADSEG
CACHE				;WHDLoad's default cache setup (chip memory not cached)

;============================================================================

slv_Version	= 20
slv_MemConfig	= slv_base	;no alternate memory configurations
slv_Flags	= WHDLF_NoError
slv_keyexit	= $59		;F10

;============================================================================

	INCLUDE	whdload/kick13.s

;============================================================================

slv_name	dc.b	"Battlehawks 1942",0
slv_copy	dc.b	"1990 Lucasfilm Games",0
slv_info	dc.b	"installed by Galahad of Fairlight",10
		dc.b	"KickEmu (WHDLoad 20) rebase by Vesuri",10,10
		dc.b	"Version 1.1-dev",0
slv_CurrentDir	dc.b	0
slv_config	dc.b	"C2:B:Enhanced framerate;"
		dc.b	0
	EVEN

_improve	dc.l	0			;1: enhanced framerate (CUSTOM2=1)
_ctltags	dc.l	WHDLTAG_CUSTOM2_GET
_custom2	dc.l	0
		dc.l	TAG_DONE

;============================================================================
; < D0: BSTR filename
; < D1: seglist (BPTR)

_cb_dosLoadSeg
		lsl.l	#2,d0
		move.l	d0,a0
		lea	_bh_name(pc),a1
		moveq	#0,d2
		move.b	(a0),d2			;BSTR length
.cmp		cmpm.b	(a0)+,(a1)+
		dbne	d2,.cmp
		bne.b	.done
		move.l	_resload(pc),a2
		move.l	d1,-(a7)
		lea	_ctltags(pc),a0
		jsr	resload_Control(a2)
		lea	_improve(pc),a0
		moveq	#0,d0
		tst.l	_custom2-_improve(a0)
		beq.b	.orig
		moveq	#1,d0
.orig		move.l	d0,(a0)
		move.l	(a7),d1
		lea	pl_bh(pc),a0
		move.l	d1,a1			;seglist
		jsr	resload_PatchSeg(a2)
		move.l	(a7)+,d1
		bsr	timing_patch
	IFD VERIFY
		bsr	tape_start
	ENDC
.done		rts

_bh_name	dc.b	2,"BH"
	EVEN

pl_bh		PL_START
	; Manual check: `move.b (0,a0,d1.l),d2; cmp.w d2,d0; beq.s ok` compares a typed
	; character with the expected one. As in v1.0, store the typed one as expected and
	; always take the ok branch.
		PL_PS	$025be,manual_check
		PL_W	$025c4,$6078		;bra.s ok
	IFD	VERIFY
		PL_PS	$075be,tape_key		;flight input on exact frames (tape.s)
		PL_NOP	$075c4,2		;the rest of move.w d0,10280(a4)
	IFD	TSCALE
		PL_PS	$1344e,t_scale		;experiment: T x TSCALE (tape.s)
	ENDC
	IFD	STICKREF
		PL_L	$7934,$80fc0007		;experiment: stick / reference T (7, mission 0)
		PL_L	$794a,$80fc0007		;in place of divu.w 10184(a4),d0
		PL_L	$7966,$80fc0007
		PL_L	$797a,$80fc0007
	ENDC
	ENDC
	IFD	C2P_FULL
		PL_P	$1a2c2,c2p_full		;experiment: full-frame merge c2p
	ENDC
		PL_END

manual_check	move.b	d0,(0,a0,d1.l)
		move.l	d0,d2
		rts

;============================================================================

	INCLUDE	timing.s
	IFD	VERIFY
	INCLUDE	tape.s
	ENDC
	IFD	C2P_FULL
	INCLUDE	c2p_full.s
	ENDC
