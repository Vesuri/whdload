;*---------------------------------------------------------------------------
;  :Program.	wildwestworld.asm
;  :Contents.	Slave for "Wild West World" from Software 2000
;  :Author.	Wepl
;  :Original	v1 
;  :Version.	$Id: wildwestworld.asm 1.2 2002/02/08 01:18:39 wepl Exp wepl $
;  :History.	07.08.00 started
;		03.08.01 some steps forward ;)
;		30.01.02 final beta
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
	OUTPUT	"Gunship2000AGA.slave"
	BOPT	O+				;enable optimizing
	BOPT	OG+				;enable optimizing
	BOPT	ODd-				;disable mul optimizing
	BOPT	ODe-				;disable mul optimizing
	BOPT	w4-				;disable 64k warnings
	BOPT	wo-			;disable optimizer warnings
	SUPER
	ENDC

;============================================================================

CHIPMEMSIZE	= $100000
FASTMEMSIZE	= $100000
NUMDRIVES	= 1
WPDRIVES	= %1111
;DEBUG
;DISKSONBOOT
DOSASSIGN
HDINIT
INITAGA
IOCACHE		= 10000
;MEMFREE	= $200
;NEEDFPU
;SETPATCH
CBDOSLOADSEG
BOOTDOS
STACKSIZE = 13000
; The instruction cache for all memory. JOTD's CACHE marks BaseMem non-cacheable, and
; without WHDLoad's MMU (its default on a 68030) that switches both caches off.
CACHECHIP

;============================================================================


slv_Version	= 16
slv_Flags	= WHDLF_NoError|WHDLF_Examine|WHDLF_ClearMem
slv_keyexit	= $5D	; num '*'

;============================================================================

	include	whdload/kick31.s

;============================================================================

	IFD BARFLY
	DOSCMD	"WDate  >T:date"
	ENDC

_dsk1
	dc.b	"gs_dsk1",0
_dsk2
	dc.b	"gs_dsk2",0
_dsk3
	dc.b	"gs_dsk3",0
_dsk4
	dc.b	"gs_dsk4",0
_env
	dc.b	"ENV",0


DECL_VERSION:MACRO
	incbin	"slave_version"
	IFD BARFLY
		dc.b	" "
		INCBIN	"T:date"
	ENDC
	ENDM

slv_name		dc.b	"Gunship 2000 AGA",0
slv_copy		dc.b	"1993 Microprose",0
slv_info		dc.b	"adapted by JOTD",10
		dc.b	"enhanced by Vesuri",10,10
		dc.b	"Version "
		DECL_VERSION
		dc.b	0
slv_CurrentDir:
	dc.b	"data",0
	EVEN

_program:
	dc.b	"Gunship 2000",0
_args		dc.b	10
_args_end
	dc.b	0
	cnop	0,4
_rampath:
	dc.b	"RAM:",0

	dc.b	"$","VER: Gunship2000AGA.slave "
	DECL_VERSION
	dc.b	$A,$D,0

	EVEN


;============================================================================

	;initialize kickstart and environment

; < D0: BSTR filename
; < D1: seglist
_cb_dosLoadSeg
	clr.l	0

	; now D1 is start address

	lsl.l	#2,d0
	move.l	d0,a0

	bsr	.strip_colon
	cmp.b	#'g',(A0)
	bne.b	.nomain
	cmp.b	#'s',1(A0)
	bne.b	.nomain
	cmp.b	#'2',2(A0)
	beq.b	.gs2_run
	tst.b	2(a0)
	bne.b	.nomain

	; gs file

	bsr	.patch_gs_segments
	bra.b	.noboot

	; gs2.run file
.gs2_run
	cmp.b	#'.',3(A0)
	bne.b	.nomain
	bsr	.patch_gs2_run_segments
	bra.b	.noboot

.nomain:
	cmp.b	#'G',(A0)
	bne.b	.noboot
	cmp.b	#'u',1(A0)
	bne.b	.noboot
	move.l	d1,d7
	bsr	_patch_exe
.noboot
	rts

.strip_colon
	addq.l	#1,a0
	movem.l	a0,-(a7)
.loop
	move.b	(a0)+,d0
	beq.b	.fail
	cmp.b	#':',d0
	bne.b	.loop
	addq.l	#4,a7
	rts	
.fail
	movem.l	(a7)+,a0
	rts

; file "gs"

.patch_gs_segments:
	move.l	d1,a1
	add.l	a1,a1
	add.l	a1,a1
	addq.l	#4,a1

	patch	$D0,crack

	IFD VERIFY
	move.l	d1,-(a7)
	ENDC
	lea	pl_gs(pc),a0
	move.l	_resload(pc),a2
	jsr	resload_Patch(a2)

	IFD VERIFY
	; The same mission on every machine and slave. random() (hunk 97) seeds from time() on
	; its first call: a constant instead. The office animations then call it a
	; timing-dependent number of times, so the mission setup in hunk 22 (time of day, ...)
	; also reseeds.
	move.l	(a7),d1
	moveq	#0,d0
	bsr	.gs_hunk
	move.l	$35c6(a1),d0		; rand's move.w seed,d0: the seed's address
	lea	verify_seed(pc),a0
	move.l	d0,(a0)
	moveq	#97,d0
	bsr	.gs_hunk
	lea	pl_gs_97(pc),a0
	jsr	resload_Patch(a2)
	move.l	(a7)+,d1		; resload_Patch may change D1
	moveq	#22,d0
	bsr	.gs_hunk
	lea	pl_gs_22(pc),a0
	jsr	resload_Patch(a2)
	ENDC

	rts

	IFD VERIFY
; < D0: hunk number, D1: seglist   > A1: the hunk's start
.gs_hunk
	move.l	d1,a1
	bra.b	.gs_hunk_next
.gs_hunk_loop
	move.l	(a1),a1
.gs_hunk_next
	add.l	a1,a1
	add.l	a1,a1
	dbf	d0,.gs_hunk_loop
	addq.l	#4,a1
	rts
	ENDC

; file "gs2.run"

.patch_gs2_run_segments:
	move.l	d1,a1
	add.l	a1,a1
	add.l	a1,a1
	addq.l	#4,a1
	lea	pl_gs2_run(pc),a0
	move.l	_resload(pc),a2
	jsr	resload_Patch(a2)

	rts

pl_gs
	PL_START
	PL_L	$4970,$4EB800D0	; crack
	PL_END

	IFD VERIFY
pl_gs_97
	PL_START
	PL_L	$aa,$70014E71		; move.l -4(a5),d0 (the time) -> moveq #1,d0
	PL_END

pl_gs_22
	PL_START
	PL_PS	$2a40,reseed_mission	; moveq #0,d0; move.l d0,d5; move.w d5,-18(a5)
	PL_NOP	$2a46,2
	PL_END
	ENDC

pl_gs2_run
	PL_START
	PL_L	$12780,$4E714E71	; remove WaitTOF before LoadView
	PL_PS	$12834,set_copperlist
	PL_PS	$13d52,fast_stack	; keep the stack in fast memory
	PL_S	$13d58,$13d62-$13d58
	IFD VERIFY
	PL_PS	$183e8,seed_flight	; move.w VHPOSR,bss+$b8fe: the flight's random seed
	ENDC
;;	PL_P	$13E6A,quit
	PL_END

; The flight moved its stack onto the first 2000 bytes of its chip work area (heap pointer
; data+$2c3e). Stay on the process stack (ExpMem) and still take the 2000 bytes, so the
; heap is laid out as before. A5 = data+$2dfc, where the process stack pointer was saved.
fast_stack
	add.l	#2000,-($2dfc-$2c3e)(a5)
	rts

	IFD VERIFY
verify_seed
	dc.l	0

reseed_mission
	move.l	a0,-(a7)
	move.l	verify_seed(pc),a0
	move.w	#1,(a0)
	move.l	(a7)+,a0
	moveq	#0,d0
	move.l	d0,d5
	move.w	d5,-18(a5)
	rts

; A constant flight seed; the seed's address is the instruction's operand after the jsr.
seed_flight
	move.l	a0,-(a7)
	move.l	4(a7),a0
	move.l	(a0),a0
	move.w	#1,(a0)
	move.l	(a7)+,a0
	addq.l	#4,(a7)
	rts
	ENDC

quit
	pea	TDREASON_OK
	move.l	_resload(pc),-(a7)
	addq.l	#resload_Abort,(a7)
	rts

set_copperlist
	move.l	#$FFFFFFFE,0.W	; fixes hazard on copjmp2 to 0

	; code below actually not needed, but could be useful to fix
	; some copperlist entries

	movem.l	a0,-(a7)
	move.l	4(a7),a0	; return address
	move.l	2(a0),a0	; copperlist variable
	lea	$dff000,a5
	move.l	(a0),$80(a5)
	tst.w	$88(a5)
	movem.l	(a7)+,a0
	addq.l	#4,a7
	rts

crack
	; d7 contains the code to enter
	; a1 contains the string of the code entered by the user

	cmp.b	#':',(a1)
	beq.b	.notyet

	; wait till the user entered 5 digits (or else it does not work)

	movem.l	a0/d1/d2,-(a7)
	MOVE.L	D7,D1			;00: 2207
	LSR	#1,D1			;02: E249
	MOVEQ	#0,D2			;04: 7400
	MOVE	D1,D2			;06: 3401
	MOVEQ	#0,D1			;08: 7200
	MOVE	D7,D1			;0A: 3207
	ADD.L	D2,D1			; code

	MOVE.L	D1,-4(a5)		; replace code entered by the user

	move.l	a1,a0
	bsr	codetostring

	movem.l	(a7)+,a0/d1/d2

.notyet
	MOVE.L	-4(A5),D0	; code entered by the user
	RTS

codetostring:
	DIVU	#$2710,D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)+
	SWAP	D1
	EXT.L	D1
	DIVU	#$03E8,D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)+
	SWAP	D1
	EXT.L	D1
	DIVU	#$0064,D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)+
	SWAP	D1
	EXT.L	D1
	DIVU	#$000A,D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)+
	SWAP	D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)
	RTS				;124: 4E75

_bootdos	move.l	(_resload),a2		;A2 = resload

	;open doslib
		lea	(_dosname,pc),a1
		move.l	(4),a6
		jsr	(_LVOOldOpenLibrary,a6)
		move.l	d0,a6			;A6 = dosbase

		lea	_env(pc),a0
		lea	_rampath(pc),a1
		bsr	_dos_assign
	;load exe
		lea	_program(pc),a0
		move.l	a0,d1
		jsr	(_LVOLoadSeg,a6)
		move.l	d0,d7			;D7 = segment
		beq	.end
	;call
		move.l	d7,a1
		add.l	a1,a1
		add.l	a1,a1

		move.l	(4,a7),d0		;stacksize
		sub.l	#5*4,d0			;required for MANX stack check

		movem.l	d0/d7/a2/a6,-(a7)

		moveq	#_args_end-_args,d0
		lea	(_args,pc),a0
		addq.l	#4,a1
		jsr	(a1)
		movem.l	(a7)+,d1/d7/a2/a6

	;remove exe
		move.l	d7,d1
		jsr	(_LVOUnLoadSeg,a6)

		pea	TDREASON_OK
		jmp	(resload_Abort,a2)

.end		moveq	#0,d0
		rts


_patch_exe:
	move.l	_resload(pc),a2
	move.l	d7,A1
	add.l	A1,A1
	add.l	A1,A1
	addq.l	#4,A1
	cmp.w	#$2C79,$66C(A1)
	beq.b	.ecs
	cmp.w	#$2C79,$512(A1)
	beq.b	.aga

	; wrong version

	pea	TDREASON_WRONGVER
	move.l	_resload(pc),-(a7)
	addq.l	#resload_Abort,(a7)
	rts

.ecs
	lea	_pl_gs2000_ecs(pc),a0
	bra.b	.patch
.aga
	lea	_pl_gs2000_aga(pc),a0
;	bra.b	.patch		; vasm: a bra.b to the next instruction is illegal; Barfly dropped it

.patch
	jsr	resload_Patch(a2)
	rts

_pl_gs2000_ecs:
	PL_START
	PL_P	$66C,move1d0rts
	PL_P	$78E,move1d0rts
	PL_END
_pl_gs2000_aga:
	PL_START
	PL_S	$122,$3E-$22		; skip test for "Install Gunship 2000"
	PL_S	$16C,$F4-$6C
;	PL_P	$512,assign_it
;	PL_P	$512,move1d0rts
;	PL_P	$634,move1d0rts
	PL_END

assign_it:
	move.l	a5,a0
	sub.l	a1,a1
move1d0rts
	moveq.l	#1,D0
	rts

;============================================================================

	END
