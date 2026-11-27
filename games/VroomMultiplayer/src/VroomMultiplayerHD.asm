;*---------------------------------------------------------------------------
;	:Program.	VroomMultiplayerHD.asm
;	:Contents.	Slave for "VroomMultiplayer" from
;	:Author. JOTD
;	:Original	Mr.LARMER
;	:Version.	
;	:History.	01.12.97 started
;	v1.1	19.12.97 finished
;	:Requires.	-
;	:Copyright. Public Domain
;	:Language.	68000 Assembler
;	:Translator.	Devpac 3.14, Barfly 2.9
;	:To Do.
;---------------------------------------------------------------------------*

	INCDIR	Include:
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i

	IFD BARFLY
	OUTPUT	"VroomMultiplayer.slave"
	BOPT	O+	;enable optimizing
	BOPT	OG+	;enable optimizing
	BOPT	ODd-	;disable mul optimizing
	BOPT	ODe-	;disable mul optimizing
	BOPT	w4-	;disable 64k warnings
	BOPT	wo-	;disable optimizer warnings
	SUPER
	ENDC

;============================================================================
	
BASEMEM	= $80000
EXPMEM	= $0

;=============================================================================

_base	SLAVE_HEADER						;ws_Security + ws_ID
		dc.w	16					;ws_Version (16: PL_PA, PL_PSS)
		dc.w	WHDLF_NoError|WHDLF_NoKbd|WHDLF_EmulTrap;ws_flags
		dc.l	BASEMEM					;ws_BaseMemSize
		dc.l	0					;ws_ExecInstall
		dc.w	_start-_base				;ws_GameLoader
		dc.w	_data-_base				;ws_CurrentDir
		dc.w	0					;ws_DontCache
_keydebug	dc.b	0					;ws_keydebug
_keyexit	dc.b	$59					;ws_keyexit = F10
_expmem		dc.l	EXPMEM					;ws_ExpMem
		dc.w	_name-_base				;ws_name
		dc.w	_copy-_base				;ws_copy
		dc.w	_info-_base				;ws_info
		dc.w	0					;ws_kickname (version 16 fields)
		dc.l	0					;ws_kicksize
		dc.w	0					;ws_kickcrc

;============================================================================

	IFD BARFLY
	DOSCMD	"WDate	>T:date"
	ENDC

_data	dc.b	0
_name	dc.b	"Vroom Multiplayer",0
_copy	dc.b	"1993 Lankhor",0
_info	dc.b	"Install by Mr.Larmer Updated by CFou!",10
	dc.b	"Version 1.6 "
	IFD BARFLY
	INCBIN	"T:date"
	ELSE
	dc.b	"(03.06.2006)"	; vasm: the date Barfly's WDate wrote
	ENDC
	dc.b	0

	even

;============================================================================
_start	;	A0 = resident loader
;============================================================================

**********************************************************************
	LEA	_resload(PC),A1
	MOVE.L	A0,(A1)
	LEA	$40000,A0
	MOVEQ	#0,D0
	MOVE.L	#$400,D1
	MOVEQ	#1,D2
	BSR	_LoadTrack

	MOVE.L	#$804E40,$40030
	MOVE.W	#$4E71,$4007A
	cmp.l	#$3658,$401f8
	beq	.v1
	cmp.l	#$3658,$40222+2
	bne	.notsup

.v2	PEA	_PatchV2(PC)
	MOVE.L	(SP)+,$40222+2
	move.l	#2,$100	; v2
	bra	.commun

.v1	MOVE.B	#$60,$401EE
	move.l	#$4E714E71,$401EA	; bsr.w $401FC: the boot block's AGA check
					; again (move.w #0,$DFF07C: SNOOP), its d0 unused
	PEA	_PatchV1(PC)
	MOVE.L	(SP)+,$401F8
	move.l	#1,$100	; v1
.commun
	LEA	$6EE88,A0
	MOVE.L	#$1600,D0
	MOVE.L	#$16DC,D1
	MOVEQ	#1,D2
	BSR	_LoadTrack
	MOVE.W	#$4E75,$6EEF4
	MOVE.L	#$70004E75,$6EF2C
	MOVE.W	#$4E75,$6EF9A
	MOVE.W	#$4E75,$6EFBA
	MOVE.W	#$4E75,$6F002
	MOVE.W	#$4EB9,$6F05E
	PEA	_LoadTrack0(PC)
	MOVE.L	(SP)+,$6F060
	MOVE.W	#$606A,$6F064
	bsr	patch_decrunch

	MOVE.W	#$F0,$C8

	cmp.l	#2,$100
	beq	.v2b
	LEA	$6B7B4,A2
	JMP	$4000C
.v2b	LEA	$6B7ec,A2
	JMP	$4000C

.notsup	bra	_bad_version

dec=$8c
_PatchV2
;	move.l	#dec,d0
	moveq	#$73,d0	; ~dec; vasm: Barfly's encoding of move.l #dec,d0
	not.b	d0
	lea	_TrackNumAdr(pc),a0
	sub.l	#dec,(a0)
	lea	_TrackDestAdr(pc),a0
	sub.l	#dec,(a0)
	bra	_cont
_PatchV1
	clr.l	d0
_cont
	MOVE.W	#$6072,$394E
	MOVE.W	#$C018,$3BCE

	lea	$1ea84,a0
	sub.l	d0,a0
	MOVE.W	#$4E75,$1EA84-$1ea84(a0)
	MOVE.W	#$4E75,$1EAFE-$1ea84(a0)
	MOVE.W	#$4E75,$1EB1E-$1ea84(a0)

	MOVE.W	#$4EF9,$1EBA0-$1ea84(a0)
	PEA	_SaveTrackVx(PC)
	MOVE.L	(SP)+,$1EBA0-$1ea84+2(a0)

	MOVE.W	#$4EB9,$1ED06-$1ea84(a0)
	PEA	_LoadTrackVx(PC)
	MOVE.L	(SP)+,$1ED06-$1ea84+2(a0)
	MOVE.W	#$6052,$1ED06-$1ea84+6(a0)

	bsr	_InstKey	
	tst.l	d0			; v1: the fixes (src/fixes.i)
	bne.b	.v2
	bsr	Fix
.v2	JMP	$3658

_InstKey
	movem.l	a0-a1,-(a7)
	lea	_Key(pc),a0
	lea	$accc,a1	; v1 & 2
	bsr	.PatchK
	movem.l	(a7)+,a0/a1
	rts
.PatchK
	cmp.w	#$1039,(a1)
	bne	.no
	move.w	#$4eb9,(a1)+
	move.l	a0,(a1)
.no	rts

_Key	move.b	$bfec01,d0
	move.l	d0,-(a7)
	NOT.B	D0
	ROR.B	#1,D0

	cmp.b	_keyexit(pc),D0
	beq	_Exit

	cmpi.b	#$58,d0	; vasm: cmpi is the shipped encoding
	bne	.f9
	move.w	#$f0,$dff180
	move.w	#$f0,$dff180
	move.w	#$f0,$dff180
	move.w	#$0,$dff180
.f9:	move.l	(a7)+,d0
	rts

_LoadTrack0
	MOVEM.L	D0-D7/A0-A6,-(SP)
	MOVEQ	#0,D0
	MOVE.W	$6EEDE,D0
	SUBQ.L	#1,D0
	MULU	#$16DC,D0
	ADDI.L	#$1600,D0	; vasm: addi is the shipped encoding
	MOVE.L	#$16DC,D1
	MOVEQ	#1,D2
	MOVE.L	$6EEC4,A0
	BSR	_LoadTrack
	MOVEM.L	(SP)+,D0-D7/A0-A6
	MOVEQ	#0,D0
	RTS

_TrackNumAdr	dc.l	$1f278	; v1=$1f278 v2=$1f278-dec
_TrackDestAdr	dc.l	$1f252	; v1=$1f258 v2=$1f258-dec

_LoadTrackVx
	MOVEM.L	D0-D7/A0-A6,-(SP)
	MOVEQ	#0,D0
	move.l	_TrackNumAdr(pc),a0
	move.w	(a0),d0	; MOVE.W	$1F278,D0

	SUBQ.L	#1,D0
	MULU	#$16DC,D0
	ADDI.L	#$1600,D0	; vasm: addi is the shipped encoding
	MOVE.L	#$16DC,D1
	MOVEQ	#1,D2

	move.l	_TrackDestAdr(pc),a0
	move.l	(a0),a0	; MOVE.L	$1F252,A0

	BSR	_LoadTrack
	MOVEM.L	(SP)+,D0-D7/A0-A6
	MOVEQ	#0,D0
	RTS

_SaveTrackVx
	MOVEM.L	D0-D7/A0-A6,-(SP)
	MOVE.L	#$16DC,D0
	MOVEQ	#0,D1
	MOVE.W	$1F278,D1
	SUBQ.L	#1,D1
	MULU	#$16DC,D1
	ADDI.L	#$1600,D1	; vasm: addi is the shipped encoding
	MOVE.L	$1F252,A1
	LEA	_SaveDiskName(PC),A0
	MOVE.L	_resload(PC),A2
	JSR	resload_SaveFileOffset(A2)
	MOVEM.L	(SP)+,D0-D7/A0-A6
	MOVEQ	#0,D0
	RTS

_SaveDiskName	dc.b	'Disk.1',0
		even
; where the init code writes the VBL routine's vectors (src/smc.i), and the fixes
SMC_VBLW1	= $3ABA		; the address in move.l #x,$B02E
SMC_VBLW2	= $3AC4		; the address in move.l #x,$B028
	INCLUDE	fixes.i
_resload	dc.l	0

_LoadTrack	MOVEM.L	D0/D1/A0-A2,-(SP)
		MOVE.L	_resload(PC),A2
		JSR	resload_DiskLoad(A2)
		bsr	patch_automodif
		bsr	patch_decrunch
		MOVEM.L	(SP)+,D0/D1/A0-A2
		RTS

patch_automodif:
	cmp.w	#$2ab4,$1b526	; v1
	bne	.pas
	bsr	prep_automodif
	PEA	$4EB80100
	MOVE.L	(SP)+,$1b526
	PEA	$4EB80100
	MOVE.L	(SP)+,$1b5f0
	PEA	$4EB80100
	MOVE.L	(SP)+,$1b8a2

	PEA	$4EB80106
	MOVE.L	(SP)+,$1b568
	PEA	$4EB80106
	MOVE.L	(SP)+,$1b626
	PEA	$4EB80106
	MOVE.L	(SP)+,$1b8c8
.pas

	cmp.w	#$2ab4,$1b526-$5a	; v1
	bne	.pas2
	bsr	prep_automodif
	PEA	$4EB80100
	MOVE.L	(SP)+,$1b526-$5a
	PEA	$4EB80100
	MOVE.L	(SP)+,$1b5f0-$56
	PEA	$4EB80100
	MOVE.L	(SP)+,$1b8a2-$56

	PEA	$4EB80106
	MOVE.L	(SP)+,$1b568-$58
	PEA	$4EB80106
	MOVE.L	(SP)+,$1b626-$56
	PEA	$4EB80106
	MOVE.L	(SP)+,$1b8c8-$56
.pas2	rts

prep_automodif
;	MOVE.W	#$4EF9,$100
;	PEA	debug_automodif1(PC)
;	MOVE.L	(SP)+,$102
;	MOVE.W	#$4EF9,$106
;	PEA	debug_automodif2(PC)
;	MOVE.L	(SP)+,$108
	lea	debug_automodif1(pc),a0
	move.l	(a0)+,$100
	move.w	(a0)+,$100+4
	lea debug_automodif2(pc),a0
	move.l	(a0)+,$106
	move.w	(a0)+,$106+4
	rts

debug_automodif1
	MOVE.L	0(A4,D0.W),(A5)
	;	move.w #$f0,$dff180
	RTS

debug_automodif2
	MOVE.L	0(A4,D0.W),(A6)
	;	move.w #$f,$dff180
	RTS	

patch_decrunch

	cmp.l	#$20dc0ca8,$6f23c ; V1& V2
	bne	.pas0
	MOVE.W	#$4EF9,$6f23c
	PEA	.decrunch1(PC)
	MOVE.L	(SP)+,$6f23c+2

	MOVE.W	#$4EF9,$6f428
	PEA	_decrunch1b(PC)
	MOVE.L	(SP)+,$6f428+2
.pas0

	cmp.l	#$20dc0ca8,$1ef0a ; V1
	bne	.pas
	MOVE.W	#$4EF9,$1ef0a
	PEA	.decrunch2_V1(PC)
	MOVE.L	(SP)+,$1ef0a+2

	MOVE.W	#$4EF9,$1f118
	PEA	_decrunch2b(PC)
	MOVE.L	(SP)+,$1f118+2

;	MOVE.W	#$4EF9,$1b4ac
;	PEA	_DecrunchGFX_V1(PC)
;	MOVE.L	(SP)+,$1b4ac+2
.pas


	cmp.l	#$20dc0ca8,$1ee7e ; v2
	bne	.pas2

	MOVE.W	#$4EF9,$1ee7e
	PEA	.decrunch2_V2(PC)
	MOVE.L	(SP)+,$1ee7e+2

	MOVE.W	#$4EF9,$1f08c
	PEA	_decrunch2b(PC)
	MOVE.L	(SP)+,$1f08c+2

;	MOVE.W	#$4EF9,$1b452
;	PEA	_DecrunchGFX_V2(PC)
;	MOVE.L	(SP)+,$1b452+2

;	MOVE.W	#$4EF9,$1b826
;	PEA	_DecrunchGFX_V2b(PC)
;	MOVE.L	(SP)+,$1b826+2
.pas2

	cmp.l	#$33fc009e,$61ee	; v2 track disk protection
	bne	.pas3
	cmp.w	#$662e,$89b2
	bne	.pas3
	move.b	#$60,$89b2	; crack
.pas3	rts

_BaseDec1=$3623e

.decrunch2_V2
;	move.w	#$f,$dff180
	movem.l	a5-a6,-(a7)
	lea	_BaseDec1,a6
	lea	$1F1ca,a5
	bra	.lbc00000

.decrunch1
;	move.w	#$f,$dff180
	movem.l	a5-a6,-(a7)
	lea	$6f670,a6	; lea _BaseDec1,a6
	lea	$6eecc,a5
	bra	.lbc00000
.decrunch2_V1
;	move.w	#$f,$dff180
	movem.l	a5-a6,-(a7)
	lea	_BaseDec1,a6
	lea	$1F256,a5
.lbc00000
	MOVE.L	(A4)+,(A0)+
	CMP.L	#$FFFFFFFF,-4(A0)
	BNE.b	.lbc00000
	CLR.B	(A4)+
	MOVE.B	(A4)+,D2
	MOVE.B	D2,D1
	ANDI.B	#7,D1	; vasm: andi is the shipped encoding
	MOVE.B	D1,$36243-_BaseDec1(a6)
	SUBQ.B	#1,D1
	MOVE.B	D1,$36245-_BaseDec1(a6)
	LSR.B	#3,D2
	MOVE.B	D2,D3
	LSL.L	#5,D2
	MOVEQ	#0,D0
	LEA	$36746-_BaseDec1(a6),A1
	MOVEQ	#$20,D7
	MOVE.L	(A4)+,D6
.lbc00036
	MOVEQ	#0,D4
	MOVE.B	D3,D2
.lbc0003A
	ROXL.L	#1,D6
	ROXL.L	#1,D4
	SUBQ.B	#1,D7
	BNE.b	.lbc00048
	MOVEQ	#$20,D7
	MOVE.L	(A4)+,D6
.lbc00048
	SUBQ.B	#1,D2
	BNE.b	.lbc0003A
	TST.B	D4
	BEQ.b	.lbc00056
	ADD.B	D1,D4
.lbc00056
	MOVE.B	D4,(A1)+
	ADDQ.B	#1,D0
	BNE.b	.lbc00036
	LEA	$36646-_BaseDec1(a6),A0
	LEA	$36446-_BaseDec1(a6),A2
	LEA	$36746-_BaseDec1(a6),A3
	MOVEQ	#0,D5
	MOVEQ	#0,D2
.lbc00074
	MOVE.L	A3,A1
	MOVEQ	#0,D0
.lbc00078
	MOVE.B	(A1)+,D1
	BNE.b	.lbc00088
	ADDQ.B	#1,D0
	BEQ.b	.lbc000B4
	BRA.b	.lbc00078

.lbc00088
	MOVE.B	D0,D2
	ADDQ.B	#1,D0
	BEQ.b	.lbc000A6
.lbc00090
	MOVE.B	(A1)+,D3
	BEQ.b	.lbc000A0
	CMP.B	D3,D1
	BLT.b	.lbc000A0
	MOVE.B	D3,D1
	MOVE.B	D0,D2
.lbc000A0
	ADDQ.B	#1,D0
	BNE.b	.lbc00090
.lbc000A6
	MOVE.B	D1,(A0)+
	MOVE.W	D2,(A2)+
	CLR.B	0(A3,D2.W)
	ADDQ.W	#1,D5
	BRA.b	.lbc00074

.lbc000B4
	st	(A0)		; vasm: Barfly's encoding of MOVE.B #$FF,(A0)
	MOVE.B	-(A0),D2
	MOVE.W	D2,D7
	LEA	$36246-_BaseDec1(a6),A1
	MOVE.W	D5,D0
	LSL.W	#1,D0
	ADD.L	D0,A1
	MOVEQ	#0,D4
.lbc000CA
	MOVE.W	D4,-(A1)
	ADDQ.W	#1,D4
	SUBQ.B	#1,D5
	BEQ.b	.lbc000E4
	MOVE.B	-(A0),D3
.lbc000D6
	CMP.B	D3,D2
	BEQ.b	.lbc000CA
	SUBQ.B	#1,D2
	LSR.W	#1,D4
	BRA.b	.lbc000D6

.lbc000E4
	SUBQ.W	#4,A4
	MOVE.B	(A4)+,$3623E-_BaseDec1(a6)
	MOVE.B	(A4)+,$3623F-_BaseDec1(a6)
	MOVE.L	A4,(a5)	; V1 $1F256	V2 $1f1ca
	LEA	$36846-_BaseDec1(a6),A3
	MOVE.L	#$FFFFFFFF,D2
	MOVE.W	#$10,D0
.lbc00108
	MOVE.L	D2,(A3)+
	DBRA	D0,.lbc00108	; vasm: Barfly's DBRA.b

	LEA	$36846-_BaseDec1(a6),A3
	SUB.W	$36244-_BaseDec1(a6),D7
	LSL.W	#1,D7
	MOVE.W	#$FFFE,0(A3,D7.W)
	LEA	$36646-_BaseDec1(a6),A0
	MOVE.W	#$FF,D0
	MOVE.W	$36242-_BaseDec1(a6),D1
	MOVEQ	#0,D2
.lbc00134
	MOVE.B	(A0)+,D2
	BLT.b	.lbc00144
	SUB.B	D1,D2
	LSL.B	#1,D2
	ADDQ.W	#1,0(A3,D2.W)
	DBRA	D0,.lbc00134	; vasm: Barfly's DBRA.b

.lbc00144
	LEA	$36246-_BaseDec1(a6),A1
.lbc0014A
	MOVE.W	(A3)+,D2
	BLT.b	.lbc00182
	BNE.b	.lbc00156
	LEA	2(A1),A1
	BRA.b	.lbc0014A

.lbc00156
	MOVE.W	D2,D3
	LSL.W	#1,D3
	MOVE.W	D3,-2(A3)
	ADD.W	D3,A1
	MOVE.L	A1,A2
	MOVE.W	$200(A1),D6
	MOVE.W	(A1)+,D4
	SUBQ.W	#1,D2
.lbc0016A
	MOVE.W	-(A2),D5
	MOVE.W	D5,2(A2)
	MOVE.W	$200(A2),$202(A2)
	DBRA	D2,.lbc0016A	; vasm: Barfly's DBRA.b

	MOVE.W	D4,(A2)
	MOVE.W	D6,$200(A2)
	BRA.b	.lbc0014A

.lbc00182
	CMPI.W	#$FFFF,D2	; vasm: cmpi is the shipped encoding
	BEQ.b	.lbc0014A
 ;	move.w #$0,$dff180
	movem.l (a7)+,a5-a6
	RTS
	
;--------------------------------------
_decrunch1b
	lea	$6f670,a4	;	lea _BaseDec1,a4
	bra	_contb

_decrunch2b
	lea	_BaseDec1,a4
_contb
;	move.w #$ff0,$dff180
	CLR.L	D4
	MOVE.W	$36244-_BaseDec1(a4),D6
	MOVE.W	D6,D3
	MOVE.L	$3623A-_BaseDec1(a4),D2
	SUBQ.W	#1,D2
	MOVE.W	(A0)+,D4
	MOVEQ	#15,D5
	SWAP	D4
.lbc00018
	ROL.L	#1,D4
	DBRA	D5,.lbc00026	; vasm: Barfly's DBRA.b

	MOVEQ	#15,D5
	SWAP	D4
	MOVE.W	(A0)+,D4
	SWAP	D4
.lbc00026
	DBRA	D3,.lbc00018	; vasm: Barfly's DBRA.b

	MOVE.L	A6,A2
	MOVE.L	A5,A3
	MOVE.W	(A3)+,D3
.lbc00030
	CMP.W	(A2)+,D4
	BLT.b	.lbc00054
	BEQ.b	.lbc0003C
	SUB.W	(A2)+,D4
	ASL.W	#1,D4
	SUB.W	D4,A2
.lbc0003C
	MOVE.W	D6,D3
	MOVE.W	$1FE(A2),D4
	CMP.B	$36240-_BaseDec1(a4),D4
	BEQ.b	.lbc0006E
	MOVE.B	D4,(A1)+
	CLR.B	D4
	DBRA	D2,.lbc00018	; vasm: Barfly's DBRA.b
	RTS

.lbc00054
	ADD.W	D3,A2
.lbc00056
	ROL.L	#1,D4
	DBRA	D5,.lbc00064	; vasm: Barfly's DBRA.b

	MOVEQ	#15,D5
	SWAP	D4
	MOVE.W	(A0)+,D4
	SWAP	D4
.lbc00064
	MOVE.W	(A3)+,D3
	BGE.b	.lbc00030
	CMPI.W	#$FFFF,D3	; vasm: cmpi is the shipped encoding
	BEQ.b	.lbc00056
.lbc0006E
	CLR.B	D4
.lbc00070
	ROL.L	#1,D4
	DBRA	D5,.lbc0007E	; vasm: Barfly's DBRA.b

	MOVEQ	#15,D5
	SWAP	D4
	MOVE.W	(A0)+,D4
	SWAP	D4
.lbc0007E
	DBRA	D3,.lbc00070	; vasm: Barfly's DBRA.b

	MOVE.L	A6,A2
	MOVE.L	A5,A3
	MOVE.W	(A3)+,D3
.lbc00088
	CMP.W	(A2)+,D4
	BLT.b	.lbc000B6
	BEQ.b	.lbc00094
	SUB.W	(A2)+,D4
	ASL.W	#1,D4
	SUB.W	D4,A2
.lbc00094
	MOVE.W	D6,D3
	MOVE.W	$1FE(A2),D4
	CMPI.W	#2,D4	; vasm: cmpi is the shipped encoding
	BGE.b	.lbc000D0
.lbc000A0
	MOVE.B	$36240-_BaseDec1(a4),(A1)+
	SUBQ.L	#1,D2
	DBRA	D4,.lbc000A0	; vasm: Barfly's DBRA.b

	CLR.W	D4
	TST.L	D2
	BGE.b	.lbc00018
	RTS

.lbc000B6
	ADD.W	D3,A2
.lbc000B8
	ROL.L	#1,D4
	DBRA	D5,.lbc000C6	; vasm: Barfly's DBRA.b

	MOVEQ	#15,D5
	SWAP	D4
	MOVE.W	(A0)+,D4
	SWAP	D4
.lbc000C6
	MOVE.W	(A3)+,D3
	BGE.b	.lbc00088
	CMPI.W	#$FFFF,D3	; vasm: cmpi is the shipped encoding
	BEQ.b	.lbc000B8
.lbc000D0
	MOVE.W	D4,D1
	CLR.B	D4
.lbc000D4
	ROL.L	#1,D4
	DBRA	D5,.lbc000E2	; vasm: Barfly's DBRA.b

	MOVEQ	#15,D5
	SWAP	D4
	MOVE.W	(A0)+,D4
	SWAP	D4
.lbc000E2
	DBRA	D3,.lbc000D4	; vasm: Barfly's DBRA.b

	MOVE.L	A6,A2
	MOVE.L	A5,A3
	MOVE.W	(A3)+,D3
.lbc000EC
	CMP.W	(A2)+,D4
	BLT.b	.lbc00110
	BEQ.b	.lbc000F8
	SUB.W	(A2)+,D4
	ASL.W	#1,D4
	SUB.W	D4,A2
.lbc000F8
	MOVE.W	D6,D3
	MOVE.W	$1FE(A2),D4
.lbc000FE
	MOVE.B	D4,(A1)+
	SUBQ.L	#1,D2
	DBRA	D1,.lbc000FE	; vasm: Barfly's DBRA.b

	CLR.B	D4
	TST.L	D2
	BGE.b	.lbc00018
	RTS

.lbc00110
	ADD.W	D3,A2
.lbc00112
	ROL.L	#1,D4
	DBRA	D5,.lbc00120	; vasm: Barfly's DBRA.b

	MOVEQ	#15,D5
	SWAP	D4
	MOVE.W	(A0)+,D4
	SWAP	D4
.lbc00120
	MOVE.W	(A3)+,D3
	BGE.b	.lbc000EC
	CMPI.W	#$FFFF,D3	; vasm: cmpi is the shipped encoding
	BEQ.b	.lbc00112

_quit
_Exit
	PEA	TDREASON_OK
	move.l	(_resload,pc),a2
	jmp	(resload_Abort,a2)
_bad_version
	moveq	#0,d0	; vasm: Barfly's encoding of clr.l d0
	pea	TDREASON_WRONGVER
	move.l	(_resload,pc),a2
	jmp	(resload_Abort,a2)
		
	end
; Attention avec Self-modifying code
_DecGfxCont
	dc.l $1c590

_DecrunchGFX_V2
_1b4b8
	move.l	a4,-(a7)
	lea	_DecGfxCont(pc),a4
	move.l	#$1c590,(a4)
	lea	$1c590,a4
	MOVEQ	#0,D3
	MOVE.L	D3,D4
	MOVE.W	(A2),D6
	MOVEQ	#0,D2
	MOVE.W	D6,D2
	MOVEQ	#0,D0
	MOVE.B	(4,A2),D0
	MULU.W	D0,D2
	LSR.L	#6,D2
	MOVE.W	D2,($10,A3)
	MOVEQ	#0,D1
	MOVE.W	(2,A2),D1
	MOVE.B	(5,A2),D0
	MULU.W	D0,D1
	LSR.L	#6,D1
	MOVE.W	D1,(14,A3)
	CLR.W	D0
	TST.W	(2,A2)
	BEQ.W	.dec0130

	lea	.dec0080(pc),a5	;LEA	($1B4D2).L,A5
	lea	.dec00C4(pc),a6	;LEA	($1B516).L,A6
	MOVE.W	(2,A2),D1
.dec0044
	ADDI.W	#$80,(14,A3)
	CMP.W	(14,A3),D1
	BGT.B	.dec0062
	SUB.W	D1,(14,A3)
	ADDA.L	(10,A3),A0
	subq.w	#1,(a4)	; SUBQ.W	#1,($1C590).L
	BGE.B	.dec0044
	move.l	(a7)+,a4
	RTS

.dec0062
	MOVE.W	(6,A3),D1
.dec0066
	ADDI.W	#$80,D2
	CMP.W	D6,D2
	BLT.B	.dec0072
	SUB.W	D6,D2
	BRA.B	.dec009C

.dec0072
	MOVE.B	(A0),D0
	ANDI.W	#$F0,D0
	LSR.W	#2,D0
	move.l	(a7),a4
	JSR	($100).W
	move.l	_DecGfxCont(pc),a4
	NOP
.dec0080	; self modif
	OR.L	D5,D3
	OR.W	D7,D4
	ROR.L	#1,D5
	ROR.L	#1,D7
	BCC.B	.dec009C
	SWAP	D5
	MOVE.L	D3,(A1)+
	MOVE.L	D4,(A1)+
	MOVEQ	#0,D3
	MOVE.L	D3,D4
	DBRA	D1,.dec00A4
	ADDQ.L	#1,A0
	BRA.B	.dec00EE

.dec009C
	DBRA	D1,.dec00A4
	ADDQ.L	#1,A0
	BRA.B	.dec00E2

.dec00A4
	ADDI.W	#$80,D2
	CMP.W	D6,D2
	BLT.B	.dec00B6
	SUB.W	D6,D2
	ADDQ.L	#1,A0
	DBRA	D1,.dec0066
	BRA.B	.dec00E2

.dec00B6
	MOVE.B	(A0)+,D0
	ANDI.W	#15,D0
	LSL.W	#2,D0
	move.l	(a7),a4
	JSR	($106).W
	move.l	_DecGfxCont(pc),a4
	NOP
.dec00C4	; self modif
	OR.L	D5,D3
	OR.W	D7,D4
	ROR.L	#1,D5
	ROR.L	#1,D7
	BCC.B	.dec00DE
	SWAP	D5
	MOVE.L	D3,(A1)+
	MOVE.L	D4,(A1)+
	MOVEQ	#0,D3
	MOVE.L	D3,D4
	DBRA	D1,.dec0066
	BRA.B	.dec00EE

.dec00DE
	DBRA	D1,.dec0066
.dec00E2
	TST.W	D7
	BLT.B	.dec00EE
	MOVE.L	D3,(A1)+
	MOVE.L	D4,(A1)+
	MOVEQ	#0,D3
	MOVE.L	D3,D4
.dec00EE
	MOVE.L	#$80008000,D7
	MOVE.L	#$80000000,D5
	MOVE.W	($10,A3),D2
	MOVE.W	(2,A2),D1
.dec0102
	ADDI.W	#$80,(14,A3)
	CMP.W	(14,A3),D1
	BGT.B	.dec0120
	SUB.W	D1,(14,A3)
	ADDA.L	(10,A3),A0
	subq.w	#1,(a4)	;SUBQ.W	#1,($1C590).L
	BGE.B	.dec0102
	move.l	(a7)+,a4
	RTS

.dec0120
	MOVE.W	(6,A3),D1
	subq.w	#1,(a4)	;SUBQ.W	#1,($1C590).L
	BGE.W	.dec0066
	move.l	(a7)+,a4
	RTS

.dec0130
	MOVE.W	(6,A3),D1
	LEA	.dec014E(pc),a5	;lea ($1B5A0).L,A5
	LEA	.dec0184(pc),a6	;lea ($1B5D6).L,A6
.dec0140
	MOVE.B	(A0),D0
	ANDI.B	#$F0,D0
	LSR.B	#2,D0
	move.l	(a7),a4
	JSR	($100).W
	move.l	_DecGfxCont(pc),a4
	NOP
.dec014E	; self modif
	NOP
	NOP
	ROR.L	#1,D5
	ROR.L	#1,D7
	BCC.B	.dec0162
	SWAP	D5
	MOVE.L	D3,(A1)+
	MOVE.L	D4,(A1)+
	MOVEQ	#0,D3
	MOVE.L	D3,D4
.dec0162
	ADDI.W	#$80,D2
	CMP.W	D6,D2
	BLT.B	.dec016E
	SUB.W	D6,D2
	BRA.B	.dec014E

.dec016E
	DBRA	D1,.dec0176
	ADDQ.L	#1,A0
	BRA.B	.dec01A8

.dec0176
	MOVE.B	(A0)+,D0
	ANDI.B	#15,D0
	LSL.B	#2,D0
	move.l	(a7),a4
	JSR	($106).W
	move.l	_DecGfxCont(pc),a4
	NOP
.dec0184	; self modif
	NOP
	NOP
	ROR.L	#1,D5
	ROR.L	#1,D7
	BCC.B	.dec0198
	SWAP	D5
	MOVE.L	D3,(A1)+
	MOVE.L	D4,(A1)+
	MOVEQ	#0,D3
	MOVE.L	D3,D4
.dec0198
	ADDI.W	#$80,D2
	CMP.W	D6,D2
	BLT.B	.dec01A4
	SUB.W	D6,D2
	BRA.B	.dec0184

.dec01A4
	DBRA	D1,.dec0140
.dec01A8
	TST.W	D7
	BLT.B	.dec01B4
	MOVE.L	D3,(A1)+
	MOVE.L	D4,(A1)+
	MOVEQ	#0,D3
	MOVE.L	D3,D4
.dec01B4
	MOVE.L	#$80008000,D7
	MOVE.L	#$80000000,D5
	MOVE.W	($10,A3),D2
	MOVE.W	(6,A3),D1
	subq.w #1,(a4)	;SUBQ.W	#1,($1C590).L
	BGE.W	.dec0140
	move.l (a7)+,a4
	RTS

_DecrunchGFX_V2b

_1b826
	lea .dec2002e(pc),a5
	lea .dec20054(pc),a6
	MOVEQ	#0,D3
	MOVEQ	#0,D4
	CLR.W	D0
	MOVE.B	(A0),D0
	BRA.B	.dec20020

.dec2000A
	ROR.L	#1,D5
	ROR.L	#1,D7
	BCC.B	.dec20020
	SWAP	D5
	AND.L	D2,(A1)
	OR.L	D3,(A1)+
	AND.L	D2,(A1)
	OR.L	D4,(A1)+
	MOVEQ	#0,D2
	MOVE.L	D2,D3
	MOVE.L	D2,D4
.dec20020
	ANDI.B	#$F0,D0
	LSR.B	#2,D0
	JSR	($100).W
	MOVE.B	(A0)+,D0
.dec2002e
	OR.W	D7,D3
	OR.W	D7,D4
	ROR.L	#1,D5
	ROR.L	#1,D7
	BCC.B	.dec20046
	SWAP	D5
	AND.L	D2,(A1)
	OR.L	D3,(A1)+
	AND.L	D2,(A1)
	OR.L	D4,(A1)+
	MOVEQ	#0,D2
	MOVE.L	D2,D3
	MOVE.L	D2,D4
.dec20046
	ANDI.B	#15,D0
	LSL.B	#2,D0
	JSR	($106).W
	MOVE.B	(A0),D0
.dec20054
	NOP
	NOP
	DBRA	D1,.dec2000A
	BTST	#0,(7,A3)
	BNE.B	.dec2006E
	MOVE.L	D7,D1
	EORI.L	#$FFFFFFFF,D1
	AND.L	D1,D3
	AND.L	D1,D4
.dec2006E
	TST.W	($1C58E).L
	BNE.B	.dec200A2
	MOVE.W	#1,($1C58E).L
	MOVE.W	D7,D1
	EORI.W	#$FFFF,D1
	MOVE.W	#$FFFF,($1C594).L
	BTST	#0,(7,A3)
	BNE.B	.dec20098
	ROL.W	#1,D1
	BCC.B	.dec200A2
.dec20098
	AND.W	D1,($1C594).L
	ROL.W	#1,D1
	BCS.B	.dec20098
.dec200A2
	OR.W	$1c594,D2
	SWAP	D2
	OR.W	$1c594,D2
	AND.L	D2,(A1)
	OR.L	D3,(A1)+
	AND.L	D2,(A1)
	OR.L	D4,(A1)+
	MOVEQ	#0,D3
	MOVEQ	#0,D4
	MOVE.W	$1c592,D2
	SWAP	D2
	MOVE.W	$1c592,D2
	ADDI.L	#$A0,(A3)
	MOVEA.L	(A3),A1
	MOVE.W	(4,A3),D7
	SWAP	D7
	MOVE.L	D7,D5
	CLR.W	D5
	MOVE.W	(4,A3),D7
	MOVE.W	(6,A3),D1
	LSR.W	#1,D1
	MOVE.B	(A0),D0
	SUBQ.W	#1,($1C590).L
	BGE.W	.dec20020
	jmp	$1b910
	end
