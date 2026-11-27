;*---------------------------------------------------------------------------
; Program:	EmpireStrikesBack.s
; Contents:	Slave for "Empire Strikes Back" (c) 1989 Vektor Grafix/Domark
; Author:	Codetapper of Action
; History:	27.05.00 - v1.0
;		         - Full load from HD
;		         - Saves high scores to disk
;		         - Fade in and out of the title picture
;		         - ButtonWait tooltype
;		20.03.03 - v1.2
;		         - Supports another version
;		         - Quit key changed to F10
; Requires:	WHDLoad 10+
; Info:		Reconstructed from the v1.2 slave, which shipped without source. It
;		assembles to that slave byte for byte; the labels and comments are new.
;---------------------------------------------------------------------------*

		INCLUDE	whdload.i

;======================================================================

_base		SLAVE_HEADER			;ws_Security + ws_ID
		dc.w	17			;ws_Version
		dc.w	WHDLF_NoError|WHDLF_EmulTrap	;ws_flags
		dc.l	$80000			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	_Start-_base		;ws_GameLoader
		dc.w	0			;ws_CurrentDir
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$59			;ws_keyexit = F10
_expmem		dc.l	0			;ws_ExpMem
		dc.w	_name-_base		;ws_name
		dc.w	_copy-_base		;ws_copy
		dc.w	_info-_base		;ws_info
		dc.w	0			;ws_kickname (none: a direct slave)
		dc.l	0			;ws_kicksize
		dc.w	0			;ws_kickcrc
		dc.w	0			;ws_config

;============================================================================

_name		dc.b	"Empire Strikes Back",0
_copy		dc.b	"1989 Vektor Grafix/Domark",0
_info		dc.b	"Installed by Codetapper/Action!",10
		dc.b	"Version 1.2 (20.03.2003)",-1
		dc.b	"Thanks to Jan Vieten and Christian Sauer",10
		dc.b	"for sending the originals!",0
_HighsName	dc.b	"EmpireStrikesBack.highs",0
_Version	dc.b	1			;1: game at $dc00, 2: at $c800
		EVEN

;======================================================================
_Start						;A0 = resident loader
;======================================================================

		lea	_resload(pc),a1
		move.l	a0,(a1)			;Save for later use

		lea	_Tags(pc),a0
		move.l	_resload(pc),a2
		jsr	resload_Control(a2)

		lea	$73000,a0		;Title picture of the first version
		move.l	#$2c00,d0
		move.l	#$9c80,d1
		movea.l	a0,a5
		bsr.w	_DiskLoad
		cmpi.l	#$f9f0fa07,12(a5)
		beq.s	.ShowTitle

		lea	$73000,a0		;Title picture of the other version
		move.l	#$2800,d0
		move.l	#$9c80,d1
		movea.l	a0,a5
		bsr.w	_DiskLoad
		cmpi.l	#$f9f0fa07,12(a5)
		bne.w	_WrongVersion
		lea	_Version(pc),a0
		move.b	#2,(a0)

.ShowTitle	move.l	#40000,d0		;Palette after 5 planes of 8000
		movea.l	a5,a1
		bsr.w	_ShowPicture
		bsr.w	_FadeIn

		lea	$500.w,a0		;Load the game
		move.l	#$dc00,d0
		move.b	_Version(pc),d2
		cmpi.b	#1,d2
		beq.s	.Offset
		move.l	#$c800,d0
.Offset		move.l	#$5e000,d1
		movea.l	a0,a5
		bsr.w	_DiskLoad

		bsr.w	_TitleWait
		bsr.w	_FadeOut

		lea	$73000,a0		;Clear the picture
		moveq	#0,d0
		move.l	#5632,d1
.Clear		move.l	d0,(a0)+
		move.l	d0,(a0)+
		dbf	d1,.Clear

		bsr.s	_LoadHighs

		lea	_PL_Game(pc),a0
		suba.l	a1,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
		jmp	$500.w

_PL_Game	PL_START
		PL_PS	$175c,_Keybd
		PL_PS	$455d6,_SaveHighs
		PL_PS	$1806,FixVblCount	;Timing fix: count the fields
		PL_PSS	$5dc0c,FixSwapWait,16	;Timing fix: 3 fields a frame at least
		PL_END

;======================================================================

_SaveHighs	movem.l	d0-d1/a0-a3,-(sp)
		lea	_HighsName(pc),a0
		lea	$5b000,a1
		movea.l	a1,a3
		bsr.s	_Crypt			;d0 = 378, the table's size
		move.l	_resload(pc),a2
		jsr	resload_SaveFile(a2)
		movea.l	a3,a1
		bsr.s	_Crypt
		movem.l	(sp)+,d0-d1/a0-a3
		move.w	#$800e,$73a.w		;Original instruction
		rts

_LoadHighs	lea	_HighsName(pc),a0
		move.l	_resload(pc),a2
		jsr	resload_GetFileSize(a2)
		tst.l	d0
		beq.s	.NoFile
		lea	_HighsName(pc),a0
		lea	$5b000,a1
		movea.l	a1,a3
		move.l	_resload(pc),a2
		jsr	resload_LoadFileDecrunch(a2)
		movea.l	a3,a1
		bra.s	_Crypt
.NoFile		rts

_Crypt		move.l	#378,d0			;eor the high-score table
		move.l	d0,-(sp)
.Loop		eor.b	d0,(a1)+
		subq.l	#1,d0
		bne.s	.Loop
		move.l	(sp)+,d0
		suba.l	d0,a1
		rts

;======================================================================

_TitleWait	movem.l	d0/a0,-(sp)
		lea	_ButtonWait(pc),a0
		move.l	(a0),d0
		tst.l	d0
		beq.s	.Delay
		bsr.s	_WaitButton
		bra.s	.Done
.Delay		moveq	#75,d0			;76 frames
.Frame		btst	#0,$dff005
		beq.s	.Frame
.Line		btst	#0,$dff005
		bne.s	.Line
		dbf	d0,.Frame
.Done		movem.l	(sp)+,d0/a0
		rts

_WaitButton	move.l	a0,-(sp)
		lea	$bfe001,a0
.Loop		btst	#6,(a0)
		beq.s	.Pressed
		btst	#7,(a0)
		bne.s	.Loop
.Pressed	movea.l	(sp)+,a0
		rts

;======================================================================

_ShowPicture	movem.l	d2-d7/a2-a6,-(sp)	;a1 = planes, d0 = palette offset
		lea	$dff000,a6
		movea.l	_resload(pc),a5
		movea.l	a1,a4
		moveq	#5,d4			;Planes
		lea	(a4,d0.l),a1
		moveq	#2,d0
		lsl.w	d4,d0
		lea	_Palette(pc),a2
		move.l	a1,(a2)
		adda.l	d0,a1			;Copper list after the palette
		move.w	#$e0,d1
		move.l	a1,$80(a6)
		move.l	a4,d2
		move.l	d4,d3
.Planes		move.w	d1,(a1)+
		addq.w	#2,d1
		swap	d2
		move.w	d2,(a1)+
		move.w	d1,(a1)+
		addq.w	#2,d1
		swap	d2
		move.w	d2,(a1)+
		addi.l	#8000,d2
		subq.w	#1,d3
		bne.s	.Planes
		moveq	#-2,d0
		move.l	d0,(a1)+
.Wait1		btst	#0,5(a6)
		beq.s	.Wait1
.Wait2		btst	#0,5(a6)
		bne.s	.Wait2
		move.w	#$8280,$96(a6)
		lea	$180(a6),a1
		moveq	#1,d0
		lsl.w	d4,d0
.Black		clr.w	(a1)+
		subq.w	#1,d0
		bne.s	.Black
		move.l	#$2981f1c1,$8e(a6)
		move.l	#$3800d0,$92(a6)
		move.w	d4,d0
		ror.w	#4,d0
		ori.w	#$200,d0
		move.w	d0,$100(a6)
		clr.w	$102(a6)
		move.w	d4,d0
		subq.w	#1,d0
		moveq	#0,d0
		move.w	d0,$108(a6)
		move.w	d0,$10a(a6)
.Wait3		btst	#0,5(a6)
		beq.s	.Wait3
.Wait4		btst	#0,5(a6)
		bne.s	.Wait4
		move.w	#$8300,$96(a6)
		movem.l	(sp)+,d2-d7/a2-a6
		rts

_FadeOut	moveq	#0,d7
.Loop		move.w	d7,-(sp)
		bsr.s	_WaitVBL
		bsr.s	_SetFade
		move.w	(sp)+,d7
		addq.w	#1,d7
		cmpi.w	#32,d7
		bne.s	.Loop
		rts

_FadeIn		moveq	#15,d7
.Loop		move.w	d7,-(sp)
		bsr.s	_WaitVBL
		bsr.s	_SetFade
		move.w	(sp)+,d7
		dbf	d7,.Loop
		rts

_SetFade	move.w	d7,d6			;The palette less d7 per component
		lsl.w	#4,d6
		move.w	d6,d5
		lsl.w	#4,d5
		movea.l	_Palette(pc),a0
		lea	$dff180,a1
		moveq	#31,d4
.Colour		move.w	(a0)+,d2
		moveq	#15,d0
		and.w	d2,d0
		sub.w	d7,d0
		bpl.s	.Blue
		moveq	#0,d0
.Blue		move.w	#$f0,d1
		and.w	d2,d1
		sub.w	d6,d1
		bmi.s	.Green
		or.w	d1,d0
.Green		andi.w	#$f00,d2
		sub.w	d5,d2
		bmi.s	.Red
		or.w	d2,d0
.Red		move.w	d0,(a1)+
		dbf	d4,.Colour
		rts

_WaitVBL	btst	#0,$dff005
		beq.s	_WaitVBL
.Line		btst	#0,$dff005
		bne.s	.Line
		rts

;======================================================================

_Keybd		cmp.b	_keyexit(pc),d0
		beq.s	_Quit
		lea	$1ac4.w,a0		;Original instruction
		rts

_DiskLoad	movem.l	d0-d2/a0-a2,-(sp)
		moveq	#1,d2
		move.l	_resload(pc),a2
		jsr	resload_DiskLoad(a2)
		movem.l	(sp)+,d0-d2/a0-a2
		rts

;======================================================================

_resload	dc.l	0
_Palette	dc.l	0
_Tags		dc.l	WHDLTAG_BUTTONWAIT_GET
_ButtonWait	dc.l	0
		dc.l	TAG_DONE

;======================================================================

_Quit		pea	TDREASON_OK.w
		bra.s	_End
_WrongVersion	pea	TDREASON_WRONGVER.w
_End		move.l	_resload(pc),-(sp)
		addq.l	#resload_Abort,(sp)
		rts

;======================================================================

		INCLUDE	EmpireStrikesBackFixes.s
