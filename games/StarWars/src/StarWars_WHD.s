***************************************************************************
*             /                                                           *
*       _____.__ _                                         .___.          *
*      /    /_____________.  _________.__________.________ |   |________  *
*  ___/____      /    ____|_/         |         /|        \|   ._      /  *
*  \     \/      \    \     \    /    |    :___/¯|    \    \   |/     /   *
*   \_____________\___/_____/___/_____|____|     |____|\_____________/    *
*     -========================/===========|______\================-      *
*                                                                         *
*   .---.----(*(        STAR WARS WHDLOAD SLAVE             )*)---.---.   *
*   `-./                                                           \.-'   *
*                                                                         *
*                         (c)oded by StingRay                             *
*                         --------------------                            *
*                             August 2016                                 *
*                                                                         *
*                                                                         *
***************************************************************************

***********************************
*** History			***
***********************************

; 10-Aug-2016	- support for SPS 2926 added, took many many hours due
;		  to the protection, interrupt problems, trashed code
;		  and the high-score saving
;		- taglist removed as all CUSTOM1/2 handling is done
;		  using PLIFCx commands in the patch lists
;		- black screen disabled as the game writes some info text
;		  before starting

; 09-Aug-2016	- work started
;		- timing fixed, unlimited shields trainer added,
;		  high-score saving problem fixed



	INCDIR	SOURCES:Include/
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	;INCLUDE	lvo/dos.i

; absolute skip
PL_SA	MACRO
	PL_S	\1,\2-(\1)
	ENDM

; jsr+absolute skip
PL_PSA	MACRO
	PL_PS	\1,\2		; could use PSS here but it fills memory
	PL_S	\1+6,\3-(\1+6)	; with NOPS so we use standard skip
	ENDM

MC68020	MACRO
	ENDM

;============================================================================

CHIPMEMSIZE	= 524288
FASTMEMSIZE	= 524288
NUMDRIVES	= 1
WPDRIVES	= %0000

;BLACKSCREEN
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
;HRTMON
;INITAGA
;INIT_AUDIO
;INIT_GADTOOLS
;INIT_LOWLEVEL
;INIT_MATHFFP
IOCACHE		= 4096
;JOYPADEMU
;MEMFREE	= $200
;NEEDFPU
;NO68020
POINTERTICKS	= 1
;PROMOTE_DISPLAY
STACKSIZE	= 6000
;TRDCHANGEDISK

;============================================================================

slv_Version	= 17
slv_Flags	= WHDLF_NoError|WHDLF_Examine
slv_keyexit	= $46	; Del


;============================================================================

	INCLUDE	Sources:whdload/kick13.s

;============================================================================


slv_CurrentDir	IFD	DEBUG
		dc.b	"SOURCES:WHD_Slaves/StarWars/"
		ENDC
		dc.b	"data",0

slv_name	dc.b	"Star Wars",0
slv_copy	dc.b	"1988 Domark",0
slv_info	dc.b	"installed by StingRay/[S]carab^Scoopex",10
		IFD	DEBUG
		dc.b	"DEBUG!!! "
		ENDC
		dc.b	"Version 2.00 (10.08.2016)",0
slv_config	dc.b	"C1:B:Unlimited Shields;"
		dc.b	"C2:B:Disable Timing Fix"
		dc.b	0
		CNOP	0,4

		CNOP	0,4

DOSbase	dc.l	0

	IFD BOOTDOS

_bootdos
	lea	.saveregs(pc),a0
	movem.l	d1-d3/d5-d7/a1-a2/a4-a6,(a0)

	lea	_dosname(pc),a1
	move.l	$4.w,a6
	jsr	_LVOOldOpenLibrary(a6)
	move.l	d0,a6
	lea	DOSbase(pc),a0
	move.l	d0,(a0)
	move.l	d0,a6


.ok	

; load game
.dogame	lea	.game(pc),a0
	bsr.b	.run
	bra.w	QUIT


.run	lea	PT_GAME(pc),a1
	bsr.b	.LoadAndPatch
	move.l	d7,d1
	moveq	#.arglen,d0
	lea	.args(pc),a0
	movem.l	d7/a6,-(a7)		; save segment/dosbase
	bsr.b	.call
	movem.l	(a7)+,d1/a6
	jmp	_LVOUnLoadSeg(a6)



; d0.l: argument length
; d1.l: segment
; a0.l: argument (command line)
; a6.l: dosbase
.call	lea	.callregs(pc),a1
	movem.l	d2-d7/a2-a6,(a1)
	move.l	(a7)+,11*4(a1)
	move.l	d0,d4
	lsl.l	#2,d1
	move.l	d1,a3
	move.l	a0,a4		; save command line
; create longword aligned copy of args
	lea	.callargs(pc),a1
	move.l	a1,d2
.copy	move.b	(a0)+,(a1)+
	subq.w	#1,d0
	bne.b	.copy

; set args
	jsr	_LVOInput(a6)
	lsl.l	#2,d0		; BPTR -> APTR
	move.l	d0,a0
	lsr.l	#2,d2		; APTR -> BPTR
	move.l	d2,fh_Buf(a0)
	clr.l	fh_Pos(a0)
	move.l	d4,fh_End(a0)
; call
	move.l	d4,d0
	move.l	a4,a0
	movem.l	.saveregs(pc),d1-d3/d5-d7/a1-a2/a4-a6

	
	jsr	4(a3)

; return
	movem.l	.callregs(pc),d2-d7/a2-a6
	move.l	.callrts(pc),a0
	jmp	(a0)





; a0.l: file name
; a1.l: patch table
; a6.l: dos base
; ---
; d7: segment

.LoadAndPatch
	move.l	a1,a5
	movem.w	(a1),d0/d1	; start/end offset for CRC16
	and.l	#$ffff,d0	; because movem sign extends
	and.l	#$ffff,d1
	sub.w	d0,d1		; length to check
	move.l	d0,d3
	move.l	d1,d4

	move.l	a0,d6
	move.l	a0,d1
	jsr	_LVOLoadSeg(a6)
	move.l	d0,d7
	beq.b	.error

	bsr.b	.CRC16

; d2.w: checksum
	move.l	a5,a0		; a0: current entry in tab
.find	move.w	2*2(a0),d0	; (points to CRC16 value)
	cmp.w	#-1,d0
	beq.b	.out
	tst.w	d0
	beq.b	.wrongver
	cmp.w	d0,d2
	beq.b	.found

	addq.w	#4*2,a0		; next entry in tab
	tst.w	(a0)		; end of tab?
	beq.b	.wrongver	; yes!
	movem.w	(a0),d3/d4	; new start/end offset for CRC16
	and.l	#$ffff,d3	; because movem sign extends
	and.l	#$ffff,d4
	sub.w	d3,d4		; length
	bsr.b	.CRC16		; get new checksum
	bra.b	.find

; unsupported/unknown version
.wrongver
	pea	(TDREASON_WRONGVER).w
	bra.w	EXIT


.found	add.w	3*2(a0),a5	; a5: patch list



	move.l	a5,a0
.patch	move.l	d7,a1
	move.l	_resload(pc),a2
	jsr	resload_PatchSeg(a2)
.out	rts

.error	jsr	_LVOIoErr(a6)
	move.l	d6,-(a7)
	move.l	d0,-(a7)
	pea	(TDREASON_DOSREAD).w
	bra.w	EXIT

; d3.l: offset
; d4.l: length to check
; d7.l: segment
; ----
; d0.w: CRC16 value
; d2.w: CRC16 value

.CRC16	move.l	a0,-(a7)
	move.l	d7,a0
	add.l	a0,a0
	add.l	a0,a0
	lea	4(a0,d3.l),a0
	move.l	d4,d0
	move.l	_resload(pc),a2
	jsr	resload_CRC16(a2)
	move.w	d0,d2
	move.l	(a7)+,a0
	rts

.game	dc.b	"starwars",0
.args	dc.b	"  ",10		; must be LF terminated
.arglen	= *-.args
	CNOP	0,4

.saveregs	ds.l	11
.saverts	dc.l	0
.dosbase	dc.l	0
.callregs	ds.l	11
.callrts	dc.l	0
.callargs	ds.b	208


QUIT	pea	(TDREASON_OK).w
EXIT	move.l	_resload(pc),a2
	jmp	resload_Abort(a2)


	CNOP 0,4


; format: start, end, checksum, offset to patch list
PT_GAME	dc.w	$0512,$058a,$48a3,PLGAME403-PT_GAME	; SPS 403
	dc.w	$3b5e,$3c08,$6f40,PLGAME2926-PT_GAME	; SPS 2926
	dc.w	0					; end of tab


; SPS 2926
PLGAME2926
	PL_START
	PL_SA	$e314,$e432		; skip protection check
	PL_PS	$d084,SetStack
	PL_R	$7184			; disable 2nd protection check
	PL_PS	$874e,delay		; fix CPU dependent delay (info text)
	

	PL_PSS	$23a,.fixDMAWait,10
	PL_PSS	$28c,.fixDMAWait,10
	PL_PSS	$2de,.fixDMAWait,10
	PL_PSS	$330,.fixDMAWait,10

; add high-score saving
	PL_IFC1
; only if no trainer is used! :)

	PL_ELSE

	PL_GA	$8d9e,.savehigh		; address of high-score saving routine
	PL_R	$8db2			; so we can call it easily
	PL_GA	$6f50,.end		; name entry finished -> save high-scores
	PL_GA	$6eda,.cont		; continue name entry 
	PL_P	$6ed4,.savehighscores	; handle high-score saving, MUST be called with jmp!

	PL_ENDIF

	PL_IFC1
	PL_B	$4ac4,$4a		; unlimited shield
	PL_PSS	$4b56,.CheckKey,2	; S - toggle unlimited shields
	PL_GA	$4ac4,DecShields
	PL_ENDIF




; fix timing
	PL_IFC2
	PL_ELSE
	PL_W	$8390+2,3
	PL_W	$b0fe+2,3
	PL_W	$b14a+2,3
	PL_W	$ceca+2,3

	PL_ENDIF
	PL_END

.end		dc.l	0
.cont		dc.l	0
.savehigh	dc.l	0

.savehighscores
	addq.w	#4,a7
	tst.w	d0
	beq.b	.saveit
	move.l	.cont(pc),-(a7)
	rts

.saveit	move.l	.end(pc),-(a7)
	move.l	.savehigh(pc),-(a7)
	rts


.CheckKey
	cmp.l	#$21,8(a5)		; S - toggle unlimited shields
	bne.b	.noS
	bsr	ToggleShields
.noS

	cmp.l	#$52,8(a5)		; original code, check F3
	rts



.fixDMAWait
	moveq	#3-1,d0
.loop	move.b	$dff006,d1
.waitR	cmp.b	$dff006,d1
	beq.b	.waitR
	dbf	d0,.loop
	rts


delay	moveq	#3*10,d0
	move.l	_resload(pc),a0
	jmp	resload_Delay(a0)


; SPS 403, V1.0
PLGAME403
	PL_START
	PL_PS	$d750,SetStack
	PL_PS	$8d36,delay		; fix CPU dependent delay (info text)

; fix high-score saving problem
	PL_IFC1
; only if no trainer is used! :)

	PL_ELSE
	PL_B	$6ca,$60		; beq -> bra, disable IO_SIZE check
	PL_B	$6fa,$60		; as above
	PL_W	$752,$4e71		; disable delay afer saving
	PL_ENDIF

	PL_IFC1
	PL_B	$511a,$4a		; unlimited shield
	PL_PSS	$51c2,.CheckKey,2	; E - toggle unlimited energy
	PL_GA	$511a,DecShields
	PL_ENDIF


; fix timing
	PL_IFC2
	PL_ELSE
	PL_W	$897e+2,3
	PL_W	$b612+2,3
	PL_W	$b65e+2,3
	PL_W	$d5a8+2,3

	PL_ENDIF
	PL_END

.CheckKey
	cmp.l	#$21,8(a5)		; S - toggle unlimited shields
	bne.b	.noS
	bsr.b	ToggleShields
.noS


	cmp.l	#$59,8(a5)		; original code, check F10
	rts

ToggleShields
	move.l	a0,-(a7)

	move.l	DecShields(pc),a0
	eor.b	#$9b,(a0)		; add.w d0,Shields(a4) <-> tst.w Shields(a4)
	move.l	(a7)+,a0
	rts

DecShields	dc.l	0

SetStack
	sub.l	#STACKSIZE,d0
	addq.l	#8,d0
	rts







