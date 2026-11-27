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
;		v1.1 (Vesa Halttunen)
;		         - Enhanced framerate (CUSTOM3, 68020+): Stunt Track Racer
;		           Unleashed 1.1's 60 FPS from a relocated copy in ExpMem
;		         - CUSTOM1 starts with infinite boost; the trainer key moves
;		           to F6 (the game redefines its keys with F1 in pause)
;		         - Turbo mode removed
; Requires:	WHDLoad 17+
; Info:		Reconstructed from the v1.0 slave, which shipped without source (the
;		import commit assembles to that slave byte for byte); the labels and
;		comments are new. The enhanced framerate uses Stunt Car Racer's
;		relocation table and Unleashed blob (games/StuntCarRacer/src), built
;		for NTSC: the two programs have the same layout.
;---------------------------------------------------------------------------*

		INCLUDE	whdload.i

; Enhanced framerate (CUSTOM3, 68020 or better): the main program runs from a copy in
; ExpMem, relocated with relocTable. ExpMem is optional.
IMG_START	= $e700			;the main program
IMG_END		= $722e0
IMG_COPY	= $1000			;its copy, from the start of ExpMem
EXPMEM		= $70000

;======================================================================

_base		SLAVE_HEADER			;ws_Security + ws_ID
		dc.w	17			;ws_Version
		dc.w	WHDLF_EmulTrap|WHDLF_NoError	;ws_flags
		dc.l	$80000			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	_Start-_base		;ws_GameLoader
		dc.w	0			;ws_CurrentDir
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$5d			;ws_keyexit = '*' on the keypad
_expmem		dc.l	-EXPMEM			;ws_ExpMem: optional
		dc.w	_name-_base		;ws_name
		dc.w	_copy-_base		;ws_copy
		dc.w	_info-_base		;ws_info
		dc.w	0			;ws_kickname
		dc.l	0			;ws_kicksize
		dc.w	0			;ws_kickcrc
		dc.w	.config-_base		;ws_config

.config		dc.b	"C1:B:Infinite Boost;"
		dc.b	"C3:B:Enhanced framerate;"
		dc.b	"BW"
		dc.b	0

;============================================================================

_name		dc.b	"Stunt Track Racer",0
_copy		dc.b	"1989 Microstyle",0
_info		dc.b	"Installed by Codetapper/Action!",10
		dc.b	"Version 1.1"
		dc.b	10,"Enhanced by Vesuri"
		dc.b	-1,"Keys:   F6 - Toggle infinite boost   "
		dc.b	10,"      Help - Win race                "
		dc.b	0
_SaveName	dc.b	"StuntTrackRacer.save",0
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

		movem.l	d0-d2/a0-a2,-(sp)
		lea	_Tags(pc),a0
		movea.l	_resload(pc),a2
		jsr	resload_Control(a2)
		bsr.w	_Enhance		;the copy, when it runs
		move.l	_ImgDelta(pc),d2	;the program's patches go there

		lea	$5c8f0,a0		;Copylock: move.l #$9cedcd02,d0
		adda.l	d2,a0			;and branch past it
		move.l	#$203c9ced,(a0)
		move.l	#$cd026000,4(a0)
		move.w	#$05b2,8(a0)
		lea	$1ba60,a0
		adda.l	d2,a0
		move.l	#$4e714e71,(a0)

		lea	$f036,a0		;Keyboard
		adda.l	d2,a0
		move.w	#$4eb9,(a0)+
		pea	_Keybd(pc)
		move.l	(sp)+,(a0)+
		lea	$62e86,a0		;Rob Northen loader
		adda.l	d2,a0
		move.w	#$4ef9,(a0)+
		pea	_Loader(pc)
		move.l	(sp)+,(a0)+
		lea	$59846,a0		;Don't ask for floppy
		adda.l	d2,a0
		move.w	#$4e75,(a0)
		lea	$e716,a0		;Checksum
		adda.l	d2,a0
		move.w	#$303c,(a0)
		move.b	#$60,4(a0)
		move.l	_UlBase(pc),d0		;Not with the enhanced framerate:
		bne.b	.Enhanced		;the blob fixes the 24 bit faults
		lea	$69fec,a0		;for any memory
		move.w	#$4eb9,(a0)+
		pea	_24Bit_Ror(pc)
		move.l	(sp)+,(a0)+
		lea	$6a06e,a0
		move.w	#$4eb9,(a0)+
		pea	_24Bit_Add_2_A0(pc)
		move.l	(sp)+,(a0)+
.Enhanced
		move.l	_Version(pc),d0
		cmpi.b	#12,d0
		blt.s	.NoKeyTrans
		bsr.w	_KeyTrans
.NoKeyTrans	move.l	_Custom1(pc),d0		;CUSTOM1: start with infinite boost
		beq.s	.NoBoost
		bsr.w	_RefreshBoost
.NoBoost	move.l	_BWait(pc),d0
		beq.s	.NoButtonWait
		bsr.w	_ButtonWait
.NoButtonWait	movea.l	_resload(pc),a2
		jsr	resload_FlushCache(a2)
		movem.l	(sp)+,d0-d2/a0-a2
		move.l	_ImgDelta(pc),-(sp)	;Start the game, at $e700 or in
		addi.l	#IMG_START,(sp)		;its copy (it sets its own stack)
		rts
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
		cmpi.b	#$55,d0			;F6 = infinite boost
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

_WinRace	move.l	a0,-(sp)
		lea	$1bb20,a0
		adda.l	_ImgDelta(pc),a0
		move.b	#4,(a0)
		movea.l	(sp)+,a0
		rts

_RefreshBoost	movem.l	d0/a0,-(sp)
		move.l	_UlBase(pc),d0		;Enhanced framerate: Unleashed's
		beq.s	.Original		;flag, no self-modifying code
		movea.l	d0,a0
		movea.l	4(a0),a0
		jsr	(a0)			;ulRefreshBoost
		bra.s	.Done
.Original	tst.b	$1ca20
		bne.s	.Toggle
		move.b	#$80,$1ca20
.Toggle		eori.l	#$65000008~$4e714e71,$60836
.Done		movem.l	(sp)+,d0/a0
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
		adda.l	_ImgDelta(pc),a1
		moveq	#47,d0
		bsr.s	.Copy
		movea.l	a2,a0
		lea	$10(a0),a0
		lea	$1b960,a1
		adda.l	_ImgDelta(pc),a1
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
; The enhanced framerate: with CUSTOM3 on a 68020 or better and the ExpMem there, the
; program is copied to ExpMem+IMG_COPY and every absolute reference it makes to itself
; moved with it (relocTable), less what stays in chip memory for the hardware (the copper
; list, the samples, the frame buffers). Unleashed's blob follows the copy; ulInstall
; writes its patches over the copy. The program at $e700 stays decrypted: the chip memory
; parts of it are used from there.

_Enhance	move.l	_Custom3(pc),d0
		beq.w	.Off
		move.l	_AttnFlags(pc),d0
		btst	#1,d0			;AFB_68020
		beq.w	.Off
		move.l	_expmem(pc),d0
		beq.w	.Off
		addi.l	#IMG_COPY,d0
		movea.l	d0,a1
		subi.l	#IMG_START,d0
		lea	_ImgDelta(pc),a0
		move.l	d0,(a0)
		lea	IMG_START,a0
		move.l	#(IMG_END-IMG_START)/4,d1
.Copy		move.l	(a0)+,(a1)+
		subq.l	#1,d1
		bne.b	.Copy

		lea	relocTable(pc),a0
		movea.l	_ImgDelta(pc),a1
		adda.l	#IMG_START,a1
		move.l	_ImgDelta(pc),d1
.Next		moveq	#0,d0
		move.w	(a0)+,d0
		bne.b	.Site
		move.l	(a0)+,d0
		beq.b	.Done
.Site		adda.l	d0,a1
		move.l	(a1),d2
		cmpi.l	#IMG_START,d2
		blo.b	.Next
		cmpi.l	#$80000,d2
		bhs.b	.Next
		add.l	d1,(a1)
		bra.b	.Next
.Done
		lea	ulBlob(pc),a0		;Unleashed's routines and patches
		movea.l	_ImgDelta(pc),a1	;behind the copy, relocated with it
		adda.l	#IMG_END,a1
		lea	_UlBase(pc),a2
		move.l	a1,(a2)
		move.w	#UL_CODE/2-1,d1
.CopyUl		move.w	(a0)+,(a1)+
		dbf	d1,.CopyUl
		lea	ulRelocs(pc),a0
		movea.l	_UlBase(pc),a1
		subq.l	#2,a1
		move.l	_ImgDelta(pc),d1
.NextUl		moveq	#0,d0
		move.w	(a0)+,d0
		bne.b	.SiteUl
		move.l	(a0)+,d0
		beq.b	.DoneUl
.SiteUl		adda.l	d0,a1
		add.l	d1,(a1)
		bra.b	.NextUl
.DoneUl		movea.l	_UlBase(pc),a0
		movea.l	(a0),a0
		jsr	(a0)			;ulInstall
		IFD	VERIFY			;The original's copy is read and write
		move.l	a3,-(sp)		;protected: an access through a reference
		lea	_Protect(pc),a3		;relocTable misses faults there
.Range		move.l	(a3)+,d0		;(an MMU is needed)
		beq.b	.Protected
		movea.l	d0,a0
		move.l	(a3)+,d0
		sub.l	a0,d0
		movea.l	_resload(pc),a2
		jsr	resload_ProtectReadWrite(a2)
		bra.b	.Range
.Protected	move.l	(sp)+,a3
		ENDC
.Off		rts

		IFD	VERIFY			;The program, less what stays in chip
_Protect	dc.l	$e700,$e74e,$e836,$f4b4,$1b6ca,$6a594,0
		ENDC

;======================================================================
_resload	dc.l	0			;Resident loader
_Tags		dc.l	WHDLTAG_VERSION_GET
_Version	dc.l	0
		dc.l	WHDLTAG_BUTTONWAIT_GET
_BWait		dc.l	0
		dc.l	WHDLTAG_CUSTOM1_GET
_Custom1	dc.l	0
		dc.l	WHDLTAG_CUSTOM3_GET
_Custom3	dc.l	0
		dc.l	WHDLTAG_ATTNFLAGS_GET
_AttnFlags	dc.l	0
		dc.l	TAG_DONE
_ImgDelta	dc.l	0			;The main program's copy - IMG_START
_UlBase		dc.l	0			;The Unleashed blob, when it runs
;======================================================================

_exit		pea	(TDREASON_OK).w
		bra.s	_end
_debug		pea	(TDREASON_DEBUG).w
_end		move.l	_resload(pc),-(sp)
		addq.l	#resload_Abort,(sp)
		rts

;======================================================================

		INCLUDE	relocs.s

;======================================================================
; Stunt Track Racer Unleashed 1.1's framerate (Stunt Car Racer's src/unleashed.s, built
; for NTSC into tmp/include/ by game.sh): its code, then ulRelocs. It and what it reserves
; follow the copy.

		INCLUDE	unleashed.i
		CNOP	0,2
ulBlob		INCBIN	unleashed.bin

		IFGT	IMG_COPY+IMG_END-IMG_START+UL_SIZE-EXPMEM
		FAIL	"ExpMem is too small for the copy and the Unleashed blob"
		ENDC
