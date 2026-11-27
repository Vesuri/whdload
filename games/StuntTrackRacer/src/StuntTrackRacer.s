;*---------------------------------------------------------------------------
; Program:	StuntTrackRacer.s
; Contents:	Slave for "Stunt Track Racer" (c) 1989 Microplay
; Author:	Codetapper of Action
; History:	06.10.00 - v1.0
;		         - Full load from HD
;		         - Loads and saves driver information to a separate file
;		         - Snoop problems fixed, 2 access faults fixed, checksum removed
;		         - Quit option (default key is '*' on keypad)
;		         - Turbo mode (F2), trainer (F1 infinite boost, Help wins the race)
;		         - ButtonWait tooltype, international keyboard (WHDLoad 12+)
; Requires:	WHDLoad 10+
; Info:		Reconstructed from the v1.0 slave, which shipped without source. It
;		assembles to that slave byte for byte; the labels and comments are new.
;---------------------------------------------------------------------------*

		INCLUDE	whdload.i

;======================================================================

_base		SLAVE_HEADER			;ws_Security + ws_ID
		dc.w	10			;ws_Version
		dc.w	WHDLF_EmulTrap|WHDLF_NoError	;ws_flags
		dc.l	$80000			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	_Start-_base		;ws_GameLoader
		dc.w	0			;ws_CurrentDir
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$5d			;ws_keyexit = '*' on the keypad
_expmem		dc.l	0			;ws_ExpMem
		dc.w	_name-_base		;ws_name
		dc.w	_copy-_base		;ws_copy
		dc.w	_info-_base		;ws_info

;============================================================================

_name		dc.b	"Stunt Track Racer",0
_copy		dc.b	"1989 Microstyle",0
_info		dc.b	"Installed by Codetapper/Action!",10
		dc.b	"Version 1.0 (06.10.2000)"
		dc.b	-1,"Keys:   F1 - Toggle infinite boost   "
		dc.b	10,"        F2 - Toggle turbo mode on/off"
		dc.b	10,"      Help - Win race                "
		dc.b	0
_SaveName	dc.b	"StuntTrackRacer.save",0
_TurboFlag	dc.b	0
		EVEN

;======================================================================
_Start						;A0 = resident loader
;======================================================================

		lea	_resload(pc),a1
		move.l	a0,(a1)			;Save for later use

		move.l	#$2c00,d0		;Load the intro
		move.l	#$9800,d1
		moveq	#1,d2
		lea	$9448,a0
		movea.l	a0,a5
		movea.l	_resload(pc),a2
		jsr	resload_DiskLoad(a2)

		movea.l	a5,a3			;Decrypt the intro in place
		movea.l	a3,a0
		move.l	#$22b5,d0
		moveq	#26,d5
		moveq	#16,d6
		move.l	#$4ffa049c,d7
		bsr.w	_Decrypt

		move.l	a0,-(sp)
		lea	_PatchMain(pc),a0	;Intro calls _PatchMain before
		move.l	a0,$126(a3)		;the main program
		lea	$99b8,a0		;Rob Northen loader
		move.w	#$4ef9,(a0)+		;jmp _Loader
		pea	_Loader(pc)
		move.l	(sp)+,(a0)
		movea.l	(sp)+,a0
		jmp	(a3)

;======================================================================

_PatchMain	movea.l	#$e700,a0		;Decrypt the main program
		move.l	#$19e40,d0
		moveq	#17,d5
		moveq	#7,d6
		move.l	#$207c0000,d7
		bsr.w	_Decrypt

		lea	$5c8f0,a0		;Copylock: move.l #$9cedcd02,d0
		move.l	#$203c9ced,(a0)		;and branch past it
		move.l	#$cd026000,4(a0)
		move.w	#$05b2,8(a0)
		move.l	#$4e714e71,$1ba60

		movem.l	d0-d1/a0-a2,-(sp)
		lea	$f036,a0		;Keyboard
		move.w	#$4eb9,(a0)+
		pea	_Keybd(pc)
		move.l	(sp)+,(a0)+
		lea	$62e86,a0		;Rob Northen loader
		move.w	#$4ef9,(a0)+
		pea	_Loader(pc)
		move.l	(sp)+,(a0)+
		move.w	#$4e75,$59846		;Don't ask for floppy
		move.w	#$303c,$e716		;Checksum
		move.b	#$60,$e71a
		lea	$69fec,a0		;24 bit access faults
		move.w	#$4eb9,(a0)+
		pea	_24Bit_Ror(pc)
		move.l	(sp)+,(a0)+
		lea	$6a06e,a0
		move.w	#$4eb9,(a0)+
		pea	_24Bit_Add_2_A0(pc)
		move.l	(sp)+,(a0)+
		lea	$5dac0,a0		;Turbo mode
		move.w	#$4eb9,(a0)+
		pea	_CheckTurboMode(pc)
		move.l	(sp)+,(a0)+
		move.l	#$4e714e71,(a0)+
		lea	$64516,a0
		move.w	#$4eb9,(a0)+
		pea	_CheckTurboMode(pc)
		move.l	(sp)+,(a0)+
		move.l	#$4e714e71,(a0)+

		clr.l	-(sp)			;TAG_DONE
		clr.l	-(sp)
		pea	WHDLTAG_BUTTONWAIT_GET
		clr.l	-(sp)
		pea	WHDLTAG_VERSION_GET
		movea.l	sp,a0
		movea.l	_resload(pc),a2
		jsr	resload_Control(a2)
		move.l	4(sp),d0		;d0 = WHDLoad version
		move.l	12(sp),d1		;d1 = ButtonWait
		lea	20(sp),sp
		cmpi.b	#12,d0
		blt.s	.NoKeyTrans
		bsr.w	_KeyTrans
.NoKeyTrans	tst.b	d1
		beq.s	.NoButtonWait
		bsr.w	_ButtonWait
.NoButtonWait	movem.l	(sp)+,d0-d1/a0-a2
		jmp	$e700			;Start the game

;======================================================================

_Decrypt	movea.l	a0,a1			;Rob Northen decryption (3 keys)
		lea	$c9c(a0),a0		;from +$c9c down to a0
		move.l	(a0),d4
		sub.l	d4,d7
		bra.s	.Skip2
.DecryptLoop	lsl.l	#1,d7
		btst	d5,d7
		beq.s	.Skip1
		btst	d6,d7
		beq.s	.Skip3
		bra.s	.Skip2
.Skip1		btst	d6,d7
		beq.s	.Skip2
.Skip3		addq.l	#1,d7
.Skip2		add.l	d7,(a0)
		move.l	(a0),(a1)+
		add.l	(a0)+,d7
		subq.l	#1,d0
		bne.s	.DecryptLoop
		rts

;======================================================================

_Keybd		ror.b	#1,d0			;Stolen code
		eori.b	#$ff,d0
		cmp.b	_keyexit(pc),d0
		beq.w	_exit
		cmpi.b	#$51,d0			;F2 = turbo on/off
		beq.s	_ToggleTurbo
		cmpi.b	#$50,d0			;F1 = infinite boost
		beq.w	_RefreshBoost
		cmpi.b	#$5f,d0			;Help = win the race
		beq.s	_WinRace
		rts

;======================================================================

_Loader		movem.l	d1-d7/a0-a6,-(sp)
		movea.l	_resload(pc),a2		;a0 = address
		mulu	#$200,d1		;d1 = offset
		mulu	#$200,d2		;d2 = length
		cmpi.l	#$dc00,d1		;The main program
		beq.s	.DiskLoad
		cmpi.l	#$a00,d1		;The times, loaded at the start
		beq.s	.DiskLoad
		move.l	d2,d0			;d0 = length
		movea.l	a0,a1			;a1 = address
		lea	_SaveName(pc),a0
		cmpi.w	#1,d3			;0 = read, 1 = write
		beq.s	.Save
		jsr	resload_LoadFileOffset(a2)
		bra.s	.Done
.Save		jsr	resload_SaveFileOffset(a2)
		bra.s	.Done
.DiskLoad	move.l	d1,d0			;d0 = offset
		move.l	d2,d1			;d1 = length
		moveq	#1,d2			;d2 = disk
		jsr	resload_DiskLoad(a2)
.Done		movem.l	(sp)+,d1-d7/a0-a6
		moveq	#0,d0
		rts

;======================================================================

_CheckTurboMode	move.l	d0,-(sp)
		move.b	_TurboFlag(pc),d0
		tst.b	d0
		beq.s	.NormalMode
		move.l	(sp)+,d0
		rts
.NormalMode	move.l	(sp)+,d0
.Wait		tst.b	$616d8			;The game's frame delay
		bne.s	.Wait
		rts

_ToggleTurbo	move.l	a0,-(sp)
		lea	_TurboFlag(pc),a0
		not.b	(a0)
		movea.l	(sp)+,a0
		rts

_WinRace	move.b	#4,$1bb20
		rts

_RefreshBoost	tst.b	$1ca20
		bne.s	.Toggle
		move.b	#$80,$1ca20
.Toggle		eori.l	#$65000008~$4e714e71,$60836
		rts

;======================================================================

_24Bit_Add_2_A0	move.l	d0,-(sp)		;Fix 24 bit A0 bug
		move.l	a0,d0
		andi.l	#$ffffff,d0
		movea.l	d0,a0
		move.l	(sp)+,d0
		addq.l	#2,a0			;Stolen code
		rts

_24Bit_Ror	move.w	#$ffff,d0		;Stolen code
		move.l	d0,-(sp)		;Fix 24 bit A0 bug
		move.l	a0,d0
		andi.l	#$ffffff,d0
		movea.l	d0,a0
		move.l	(sp)+,d0
		ror.l	d3,d0			;Stolen code
		rts

;======================================================================

_KeyTrans	movem.l	d0-d2/a0-a2,-(sp)	;International keyboard: the
		clr.l	-(sp)			;game's two key tables from
		clr.l	-(sp)			;WHDLoad's rawkey table
		pea	WHDLTAG_KEYTRANS_GET
		movea.l	sp,a0
		movea.l	_resload(pc),a2
		jsr	resload_Control(a2)
		movea.l	4(sp),a0
		lea	12(sp),sp
		movea.l	a0,a2
		lea	$90(a0),a0
		lea	$1b8a8,a1
		moveq	#47,d0
		bsr.s	.Copy
		movea.l	a2,a0
		lea	$10(a0),a0
		lea	$1b960,a1
		moveq	#47,d0
		bsr.s	.Copy
		movem.l	(sp)+,d0-d2/a0-a2
		rts

.Copy		move.b	(a0)+,d2		;Replace each mapped key that
		move.b	(a1),d1			;the game has with a printable
		beq.s	.Next			;character from WHDLoad's table
		cmpi.b	#$7c,d2
		bgt.s	.Next
		move.b	d2,(a1)
.Next		addq.w	#1,a1
		dbf	d0,.Copy
		rts

;======================================================================

_ButtonWait	move.l	a0,-(sp)		;Wait for the mouse or fire button
		lea	$bfe001,a0
.Wait		btst	#6,(a0)
		beq.s	.Done
		btst	#7,(a0)
		bne.s	.Wait
.Done		movea.l	(sp)+,a0
		rts

;======================================================================
_resload	dc.l	0			;Resident loader
;======================================================================

_exit		pea	(TDREASON_OK).w
		bra.s	_end
_debug		pea	(TDREASON_DEBUG).w
_end		move.l	_resload(pc),-(sp)
		addq.l	#resload_Abort,(sp)
		rts
		dc.w	0			;The original pads the hunk with zero, vasm with nop
