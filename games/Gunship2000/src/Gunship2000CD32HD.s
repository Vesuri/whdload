;*---------------------------------------------------------------------------
;  :Program.	Gunship2000HD.asm
;  :Contents.	Slave for "Gunship2000"
;  :Author.	JOTD, from Wepl sources
;  :Original	v1 
;  :Version.	$Id: Gunship2000HD.asm 1.2 2002/02/08 01:18:39 wepl Exp wepl $
;  :History.	%DATE% started
;  :Requires.	-
;  :Copyright.	Public Domain
;  :Language.	68000 Assembler
;  :Translator.	Devpac 3.14, Barfly 2.9
;  :To Do.
;---------------------------------------------------------------------------*

	INCDIR	Include:
	INCDIR	osemu:
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	INCLUDE	lvo/dos.i

	IFD BARFLY
	OUTPUT	"Gunship2000CD32.slave"
	BOPT	O+				;enable optimizing
	BOPT	OG+				;enable optimizing
	BOPT	ODd-				;disable mul optimizing
	BOPT	ODe-				;disable mul optimizing
	BOPT	w4-				;disable 64k warnings
	BOPT	wo-			;disable optimizer warnings
	SUPER
	ENDC

;============================================================================

CHIPMEMSIZE	= $1FF000
FASTMEMSIZE	= $130000	; JOTD's none: the flight's code, data, stack and models in fast memory
NUMDRIVES	= 1
WPDRIVES	= %0000

;DISKSONBOOT
DOSASSIGN
DEBUG
HDINIT
INITAGA
;HRTMON
IOCACHE		= 10000
;MEMFREE	= $200
;NEEDFPU
;SETPATCH
CBDOSLOADSEG
; The instruction cache for all memory. JOTD's CACHE marks BaseMem, all of this version's
; memory, non-cacheable, which switches the caches off.
CACHECHIP

FORCEPAL
BOOTDOS
QKSTRUCT

;============================================================================


slv_Version	= 17
slv_Flags	= WHDLF_NoError|WHDLF_Examine
slv_keyexit	= $5D	; num '*'

; The CD32 build of gs2.run (flight.s; the AGA slave's offsets are the comments')
G_DT		= $28
G_CLOCK		= $78
G_PHASE		= $2a6
G_WAIT		= $2c4
G_BLINK		= $2fc
G_VBL		= $606
G_COLLECTIVE_UP	= $121c
G_COLLECTIVE_DOWN = $1272
G_SPEED		= $76d0
G_SPEED_STEP	= $7bbe
G_HEADING	= $7d94
G_CLIMB		= $790a
G_FILL		= $fa70
G_COLOURS	= $fcb2
G_LINE		= $fcf6
G_RECT		= $13806
G_STACK		= $13f9c
G_MODELS	= $188fc
G_SEED		= $18b22
G_START		= $18b6a
G_SIZE		= $19750
B_PATTERNS	= $108c
B_RECTS		= $b5b8
B_DRAWN		= $b8dc
B_VBL		= $b8fc
B_DT		= $c6ba
B_TICKS		= $c6bc
B_BLINK		= $c6c6
B_PHASE		= $c6c7
B_PAUSE		= $c774
B_CLIMB_TARGET	= $2ca
B_CLIMB		= $2cc
B_COLLECTIVE	= 6
D_EDGES		= $1e9e
D_HEAP		= $2c3c
D_SAVESP	= $2e24
D_MODELS	= $9508
D_MODELS_NEXT	= $9510
LINES_CPU	= AFB_68030	; the CPU lines on a 68030 or later: no faster on the 68020 here
GS_RAND		= $330e
GS_TIME_HUNK	= 96
GS_MISSION_HUNK	= 21

;============================================================================

	INCLUDE	whdload/kick31.s	; by its path in the WHDLoad tree, as the ECS and AGA sources do
	INCLUDE	fakepad.s

;============================================================================

	IFD BARFLY
	DOSCMD	"WDate  >T:date"
	ENDC

; keys

_qkstruct:
	dc.w	$50,$0,$51,0,$52,$0,$53,0,$54,0,$55,0

_assign1
	dc.b	"CD0",0
_assign2
	dc.b	"Gunship_2000",0
_assign3
	dc.b	"ENV",0


DECL_VERSION:MACRO
	incbin	"slave_version"
	IFD BARFLY
		dc.b	" "
		INCBIN	"T:date"
	ENDC
	ENDM

slv_name		dc.b	"Gunship 2000 CD³²",0
slv_copy		dc.b	"1992 Microprose",0
slv_info		dc.b	"adapted by JOTD",10
		dc.b	"enhanced by Vesuri",10
		dc.b	"Version "
		DECL_VERSION
		dc.b	0
slv_config	dc.b	"C2:B:Enhanced framerate;"
		dc.b	0
slv_CurrentDir:
	dc.b	"data",0
_rampath:
	dc.b	"RAM:",0
_program:
	dc.b	"Gunship 2000",0
_args		dc.b	10
_args_end
	dc.b	0


	dc.b	"$","VER: Gunship2000CD32.slave "
	DECL_VERSION
	dc.b	$A,$D,0

	EVEN

;DUMMY_CD_DEVICE = 1
USE_DISK_LOWLEVEL_LIB
USE_DISK_NONVOLATILE_LIB

;============================================================================

; < D0: BSTR filename, D1: seglist. gs (VERIFY) and gs2.run get the flight's patches
; (flight.s), by the name after any device, assign or drawer.
_cb_dosLoadSeg
	lsl.l	#2,d0
	move.l	d0,a0
	moveq	#0,d0
	move.b	(a0)+,d0
	lea	(a0,d0.w),a1		; the name's end
	move.l	a0,a2
.part	cmp.l	a1,a2
	beq.b	.name
	move.b	(a2)+,d0
	cmp.b	#':',d0
	beq.b	.after
	cmp.b	#'/',d0
	bne.b	.part
.after	move.l	a2,a0
	bra.b	.part
.name	sub.l	a0,a1			; the file name's length
	cmp.b	#'g',(a0)
	bne.b	.out
	cmp.b	#'s',1(a0)
	bne.b	.out
	cmp.w	#2,a1
	beq.b	.gs
	cmp.w	#7,a1
	bne.b	.out
	cmp.b	#'2',2(a0)
	bne.b	.out
	cmp.b	#'.',3(a0)
	bne.b	.out
	bra	flight_gs2
.gs
	IFD VERIFY
	bra	flight_gs		; the mission pinned
	ENDC
.out	rts

	;initialize kickstart and environment

_bootdos
	clr.l	$0.W

	move.l	(_resload),a2		;A2 = resload

	;open doslib
		lea	(_dosname,pc),a1
		move.l	(4),a6
		jsr	(_LVOOldOpenLibrary,a6)
		move.l	d0,a6			;A6 = dosbase

	;assigns
		lea	_assign1(pc),a0
		sub.l	a1,a1
		bsr	_dos_assign

		lea	_assign2(pc),a0
		sub.l	a1,a1
		bsr	_dos_assign

		lea	_assign3(pc),a0
		lea	_rampath(pc),a1
		bsr	_dos_assign

		bsr	_patch_joypad

	;load exe
		lea	_program(pc),a0
		lea	_args(pc),a1
		moveq	#_args_end-_args,d0
		lea	_patch_gs2000(pc),a5
		bsr	_load_exe
	;quit
_quit		pea	TDREASON_OK
		move.l	(_resload,pc),a2
		jmp	(resload_Abort,a2)

; < d7: seglist

_patch_gs2000
	RTS

	move.l	d7,a1
	add.l	A1,A1
	add.l	A1,A1
	addq	#4,A1
	illegal
	lea	_pl_gs2000(pc),a0
	jsr	resload_Patch(a2)
	illegal
	rts

_pl_gs2000:
	PL_START
	PL_L	$154,$4E714E71
	PL_B	$168,$60
	PL_END

; < a0: program name
; < a1: arguments
; < d0: argument string length
; < a5: patch routine (0 if no patch routine)

_load_exe:
	movem.l	d0-a6,-(a7)
	move.l	d0,d2
	move.l	a0,a3
	move.l	a1,a4
	move.l	a0,d1
	jsr	(_LVOLoadSeg,a6)
	move.l	d0,d7			;D7 = segment
	beq	.end			;file not found

	;patch here
	cmp.l	#0,A5
	beq.b	.skip
	jsr	(a5)
.skip
	;call
	move.l	d7,a1
	add.l	a1,a1
	add.l	a1,a1

	move.l	a4,a0
	move.l	($44,a7),d0		;stacksize
	sub.l	#5*4,d0			;required for MANX stack check
	movem.l	d0/d7/a2/a6,-(a7)
	move.l	d2,d0			; argument string length
	jsr	(4,a1)
	movem.l	(a7)+,d1/d7/a2/a6

	;remove exe
	move.l	d7,d1
	jsr	(_LVOUnLoadSeg,a6)

	movem.l	(a7)+,d0-a6
	rts

.end
	move.l	a3,-(a7)
	pea	205			; file not found
	pea	TDREASON_DOSREAD
	move.l	(_resload,pc),-(a7)
	add.l	#resload_Abort,(a7)
	rts

	include	flight.s

	END
