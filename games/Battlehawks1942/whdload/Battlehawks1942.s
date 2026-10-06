;*---------------------------------------------------------------------------
;  :Program.	Battlehawks1942.s
;  :Contents.	Slave for "Battlehawks 1942" from Lucasfilm Games
;  :Original	PAL v1.0
;  :History.	12.05.03 v1.0 Galahad of Fairlight (no source distributed; reconstructed
;		in original/Battlehawks1942.s, which rebuilds it byte-identically)
;		06.10.26 rebased on WHDLoad 20.0 KickEmu (kick13.s) for the performance
;		study; behaviour as v1.0
;  :Copyright.	Public Domain
;  :Language.	68000 Assembler
;  :Translator.	vasm
;---------------------------------------------------------------------------*
;
; Like Galahad's v1.0 "SLOW" slave: Kickstart 1.3, 512 KB chip RAM and no other memory (the
; game is meant to run at A500 speed), the game boots from its own Disk.1 (startup-sequence
; runs BH), and the manual check accepts any answer (Return still has to be pressed).
; v1.0 patched the Kickstart image itself and hooked LoadSeg; here KickEmu does the OS part
; and _cb_dosLoadSeg patches BH. All addresses in patch lists are BH hunk-0 offsets.

	INCDIR	Include:
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	INCLUDE	lvo/dos.i

;============================================================================

CHIPMEMSIZE	= $80000
FASTMEMSIZE	= 0
NUMDRIVES	= 3		;Disk.1-3 in DF0-DF2: the game never asks for a swap
WPDRIVES	= %1111		;v1.0 let the game write every disk (pilot records)

DISKSONBOOT
SETPATCH
CBDOSLOADSEG

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
slv_config	dc.b	0
	EVEN

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
		lea	pl_bh(pc),a0
		move.l	_resload(pc),a2
		move.l	d1,a1			;seglist
		jsr	resload_PatchSeg(a2)
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
		PL_END

manual_check	move.b	d0,(0,a0,d1.l)
		move.l	d0,d2
		rts

;============================================================================

	IFD	VERIFY
	INCLUDE	tape.s
	ENDC
