***************************************************************************
*             /                                                           *
*       _____.__ _                                         .___.          *
*      /    /_____________.  _________.__________.________ |   |________  *
*  ___/____      /    ____|_/         |         /|        \|   ._      /  *
*  \     \/      \    \     \    /    |    :___/¯|    \    \   |/     /   *
*   \_____________\___/_____/___/_____|____|     |____|\_____________/    *
*     -========================/===========|______\================-      *
*                                                                         *
*   .---.----(*( LINKS - THE CHALLENGE OF GOLF WHDLOAD SLAVE )*)---.---.  *
*   `-./                                                            \.-'  *
*                                                                         *
*                         (c)oded by StingRay                             *
*                         --------------------                            *
*                              April 2013                                 *
*                                                                         *
*                                                                         *
***************************************************************************

***********************************
*** History			***
***********************************

; 28-Apr-2013	- course disk bug fixed, game destroyed the FIB while
;		  trying to read the course name so only 1 coourse
;		  would be displayed in the requester, lame!

; 13-Apr-2013	- work started


	INCDIR	SOURCES:Include/
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	;INCLUDE	lvo/dos.i

; absolute skip
PL_SA	MACRO
	PL_S	\1,\2-(\1)
	ENDM

MC68020	MACRO
	ENDM

;============================================================================

CHIPMEMSIZE	= 524288
FASTMEMSIZE	= 524288*2
NUMDRIVES	= 1
WPDRIVES	= %0000

BLACKSCREEN
;BOOTBLOCK
BOOTDOS
;BOOTEARLY
;CBDOSLOADSEG
;CBDOSREAD
CACHE
DEBUG
;DISKSONBOOT
;DOSASSIGN
FONTHEIGHT	= 8
HDINIT
HRTMON
;INITAGA
;INIT_AUDIO
;INIT_GADTOOLS
;INIT_LOWLEVEL
;INIT_MATHFFP
IOCACHE		= 8192
;JOYPADEMU
;MEMFREE	= $200
;NEEDFPU
NO68020
POINTERTICKS	= 1
;PROMOTE_DISPLAY
STACKSIZE	= 6000
;TRDCHANGEDISK

;============================================================================

slv_Version	= 17
slv_Flags	= WHDLF_NoError|WHDLF_Examine
slv_keyexit	= $59	; F10

;============================================================================

	INCLUDE	Sources:whdload/kick13.s

;============================================================================


slv_CurrentDir	IFD	DEBUG
		dc.b	"SOURCES:WHD_Slaves/Links/data",0
		ELSE
		dc.b	"data",0
		ENDIF

slv_name	dc.b	"Links - The Challenge of Golf",0
slv_copy	dc.b	"1992 Access",0
slv_info	dc.b	"installed by StingRay/[S]carab^Scoopex",10
		IFD	DEBUG
		dc.b	"DEBUG!!! "
		ENDC
		dc.b	"Version 1.01 (28.04.2013)",0

slv_config	dc.b	"C1:B:Skip Intro"
		dc.b	0

		CNOP	0,4
	IFD BOOTDOS

_bootdos
	lea	_dosname(pc),a1
	move.l	$4.w,a6
	jsr	_LVOOldOpenLibrary(a6)
	lea	DOSbase(pc),a0
	move.l	d0,(a0)
	move.l	d0,a6

	move.l	_resload(pc),a2
	lea	TAGLIST(pc),a0
	jsr	resload_Control(a2)

; load intro
	move.l	NOINTRO(pc),d0
	bne.b	.skipintro
	moveq	#0,d0
	moveq	#4,d1
	lea	.title(pc),a0
	lea	PT_TITLE(pc),a1
	bsr.b	.LoadAndPatch
	bsr.b	.run
.skipintro

; load game
.dogame	move.w	#$12e,d0
	move.w	#$146-$12e,d1
	lea	.game(pc),a0
	lea	PT_GAME(pc),a1
.go	bsr.b	.LoadAndPatch
	bsr.b	.run
	bra.w	QUIT

.run	move.l	d7,a1
	add.l	a1,a1
	add.l	a1,a1
	movem.l	d7/a6,-(a7)
	lea	.cmd(pc),a0
	moveq	#.cmdlen,d0
	jsr	4(a1)
	movem.l	(a7)+,d7/a6
	move.l	d7,d1
	jmp	_LVOUnLoadSeg(a6)

; d0.w: start offset for version check
; d1.w: length for version check
; a0.l: file name
; a1.l: patch table
; a6.l: dos base
; ---
; d7: segment

.LoadAndPatch
	move.w	d0,d3
	moveq	#0,d4
	move.w	d1,d4

	move.l	a0,d6
	move.l	a1,a5
	move.l	a0,d1
	jsr	_LVOLoadSeg(a6)
	move.l	d0,d7
	beq.b	.error

	move.l	d7,a0
	add.l	a0,a0
	add.l	a0,a0

	lea	4(a0,d3.w),a0
	move.l	d4,d0
	move.l	_resload(pc),a2
	jsr	resload_CRC16(a2)
	move.w	d0,d2

; d0: checksum
	move.l	a5,a0
.find	move.w	(a0)+,d0
	beq.b	.wrongver
	cmp.w	#-1,d0
	beq.b	.out
	cmp.w	#-2,d0			; don't care about CRC
	beq.b	.found
	cmp.w	d0,d2
	beq.b	.found
	addq.w	#2,a0
	bra.b	.find

; unsupported/unknown version
.wrongver
	pea	(TDREASON_WRONGVER).w
	bra.b	EXIT


.found	add.w	(a0),a5
	move.l	a5,a0
.patch	move.l	d7,a1
	move.l	_resload(pc),a2
	jsr	resload_PatchSeg(a2)
.out	rts

.error	jsr	_LVOIoErr(a6)
	move.l	d6,-(a7)
	move.l	d0,-(a7)
	pea	(TDREASON_DOSREAD).w
	bra.b	EXIT


.cmd	dc.b	"",10,0			; fake command line
.cmdlen	= *-.cmd
.title	dc.b	"title",0
.game	dc.b	"golf",0
	CNOP	0,4


QUIT	pea	(TDREASON_OK).w
EXIT	move.l	_resload(pc),a2
	jmp	resload_Abort(a2)

DOSbase	dc.l	0

; format: checksum, offset to patch list
PT_TITLE
	dc.w	-2,PLTITLE-PT_TITLE	; SPS 2010+SPS2481 (1.50/1.53)
	dc.w	0			; end of tab


; format: checksum, offset to patch list
PT_GAME	dc.w	$e70a,PLGAME150-PT_GAME	; SPS 2010 (v1.50)
	dc.w	$371d,PLGAME153-PT_GAME	; SPS 2481 (v1.53)
	dc.w	0			; end of tab


PLTITLE	PL_START
	PL_END

PLGAME150
	PL_START
	PL_SA	$2da,$2e8		; skip cache clear
	PL_PS	$1546c,getFIB		; fix course disk support
	PL_PS	$15476,getFIB2		; as above
	PL_END

PLGAME153
	PL_START
	PL_SA	$2e4,$2f2		; skip cache clear
	PL_PS	$15478,getFIB		; fix course disk support
	PL_PS	$15482,getFIB2		; as above
	PL_END

getFIB	pea	FIB(pc)
	move.l	(a7)+,d2
	rts

getFIB2
	lea	FIB(pc),a0
	rts



	CNOP	0,4
FIB	ds.b	fib_SIZEOF

TAGLIST	dc.l	WHDLTAG_CUSTOM1_GET
NOINTRO	dc.l	0
	dc.l	TAG_END




	ENDC

