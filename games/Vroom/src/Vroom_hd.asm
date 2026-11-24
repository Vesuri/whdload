;*---------------------------------------------------------------------------
;  :Program.	Vroom.asm
;  :Contents.	Slave for "Vroom" from Lankhor
;  :Author.	Mr.Larmer of Wanted Team
;  :History.	02.02.2000
;		03.06.2006 updated by cfou
;		23.11.2026 2.0b by Vesuri: CPU caches, fast CPUs
;  :Requires.	-
;  :Copyright.	Public Domain
;  :Language.	68000 Assembler
;  :Translator.	Devpac 3.14
;  :To Do.
;---------------------------------------------------------------------------*

	OUTPUT	Vroom.slave

;	BOPT	O+		;enable optimizing	; vasm: Barfly only
;	BOPT	OG+		;enable optimizing	; vasm: Barfly only
;	BOPT	ODd-		;disable mul optimizing	; vasm: Barfly only
;	BOPT	ODe-		;disable mul optimizing	; vasm: Barfly only
;	BOPT	w4-		;disable 64k warnings	; vasm: Barfly only
;	BOPT	wo-		;disable optimizer warnings	; vasm: Barfly only
	;BOPT	c-		;loawcase	= uppervase
;	SUPER	; vasm: Barfly only

;	INCDIR	Include:	; vasm: the build passes the include paths
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i

; vasm: whdmacros.i BLITWAIT as of the shipped slave (before its 03.09.07 change), which
; the shipped bytes need.
BLITWAIT_V14	MACRO
		tst.b	(_custom+dmaconr)
.wb\@	tst.b	(_ciaa)
		tst.b	(_ciaa)
		btst	#DMAB_BLTDONE-8,(_custom+dmaconr)
		bne.b	.wb\@
		tst.b	(_custom+dmaconr)
		ENDM


CHIPMEMSIZE	=	$80000
BASEMEM		=	CHIPMEMSIZE

_base
		SLAVE_HEADER		;ws_Security + ws_ID
		dc.w	17		;ws_Version (16: PL_PA, PL_PSS; 17: ws_config)
		dc.w	WHDLF_NoError|WHDLF_EmulTrap	; |WHDLF_NoKbd	;ws_flags
		dc.l	BASEMEM		;ws_BaseMemSize
		dc.l	0		;ws_ExecInstall
		dc.w	_start-_base	;ws_GameLoader
		dc.w	_data-_base	;ws_CurrentDir
		dc.w	0		;ws_DontCache
_keydebug	dc.b	$5f		;ws_keydebug
_keyexit	dc.b	$5d		;ws_keyexit = *
_expmem		dc.l	-ENH_EXPSIZE	;ws_ExpMem (optional: src/enhanced.i)
		dc.w	_name-_base	;ws_name
		dc.w	_copy-_base	;ws_copy
		dc.w	_info-_base	;ws_info
		dc.w	0		;ws_kickname (version 16 fields)
		dc.l	0		;ws_kicksize
		dc.w	0		;ws_kickcrc
		dc.w	_config-_base	;ws_config (version 17)

;===========================================================================

	IFD BARFLY
	DOSCMD	"WDate	>T:date"
	ENDC

_config	dc.b	"C1:B:Enhanced framerate;"
	dc.b	"C2:L:Game speed:16.7 Hz,25 Hz",0
_data	dc.b	0
_name	dc.b	"Vroom",0
_copy	dc.b	"1991 Lankhor ",0
_info	dc.b	"Done by Mr.Larmer updated by CFou!",10
	dc.b	"enhanced by Vesuri",10
	dc.b	"Version 2.0b (23.11.2026)"
	dc.b	10,"Greeting to Harry"
	dc.b	0
	dc.b	"$VER: Vroom.slave 2.0b (23.11.2026)",0
;====================================================================== 
	even
;======================================================================
_start	;	A0 = resident loader
;======================================================================

		lea	_resload(pc),a1
		move.l	a0,(a1)			;save for later use
		
		lea	$60000,A0
		moveq	#0,D0
		move.l	#$400,D1
		moveq	#1,d2
		bsr.w	_LoadDisk

		move.l	#$00804E40,$30(a0)		; trap #0

		move.w	#$4E71,$7A(a0)			; move.l A1,A2

		pea	Patch(pc)
		move.l	(A7)+,$20E(a0)

		lea	$6EE88,A0
		move.l	#$1600,D0
		move.l	#$16DC,D1
		moveq	#1,d2
		bsr.w	_LoadDisk

		move.w	#$4E75,d0
		move.w	d0,$6C(a0)
		move.l	#$70004E75,$A4(a0)
		move.w	d0,$112(a0)
		move.w	d0,$132(a0)
		move.w	d0,$17A(a0)

		move.w	#$4EB9,$1D6(a0)
		pea	Load(pc)
		move.l	(A7)+,$1D8(a0)

		move.w	#$606A,$1DC(a0)		; skip decode MFM

		lea	$6B6C0+$1B4-$88,A2
	ifne	0
		move.b	$BFEE01,D0
		andi.b	#$C0,D0
		ori.b	#8,D0
		move.b	D0,$BFEE01
		move.b	#$7F,$BFED01
		move.b	#$64,$BFE501
		move.b	#8,$BFE401
		moveq	#0,d0
lbC0000B6:
		addq.l	#1,D0
		btst	#0,$BFED01
		beq.s	lbC0000B6
		mulu.w	#$30,D0
		divu.w	#$C1C,D0
		move.w	D0,$C8.w
		move.b	#$88,$BFED01
	endc
		clr.w	$C8.w

		jmp	$6000C

;--------------------------------

Patch
		move.w	#$6072,$39C2.w		; skip read protection track

		bsr.w	InsertWaitBlit

		move.w	#$4E71,$6534.w		; skip protection move.w d4,(a1)+

		bsr.w	Patch2

		move.w	#$6002,$81A8		; skip read protection track
		move.b	#$60,$81BE		; skip check protection track data

		move.w	#$4E71,$13126		; skip protection move.w d4,(a1)+

		move.w	#$4EF9,$100.w
		pea	SelfModCode(pc)
		move.l	(a7)+,$102.w

		move.w	#$4EF9,$106.w
		pea	SelfModCode2(pc)
		move.l	(a7)+,$108.w

		pea	$4EB80100
		move.l	(a7),$19EBE
		move.l	(a7),$19F8C
		move.l	(a7)+,$1A23E
		pea	$4EB80106
		move.l	(a7),$19F02
		move.l	(a7),$19FC2
		move.l	(a7)+,$1A264

		move.w	#$4EF9,$1D0F8
		pea	Decrunch(pc)
		move.l	(A7)+,$1D0FA

		move.w	#$4E75,$1D16C		; change head position
		move.w	#$4E75,$1D1C6		; skip delay loop
		move.w	#$4E75,$1D1E2		; change head position on 0
		move.w	#$4E75,$1D202		; change head position on nr
		move.w	#$4E75,$1D24A		; skip delay loop

		move.w	#$4EF9,$1D280
		pea	_savehighs(pc)
		move.l	(A7)+,$1D282

		move.w	#$4EB9,$1D3D8
		pea	Load2(pc)
		move.l	(A7)+,$1D3DA

		move.w	#$6052,$1D3DE		; skip decode MFM
		bsr	_InstKey
		bsr	Fix
		jmp	$3658.w

;--------------------------------

SelfModCode
		move.l	(a4,d0.w),(a5)
		rts
SelfModCode2
		move.l	(a4,d0.w),(a6)
		rts

;--------------------------------

InsertWaitBlit
		movem.l	a0-a1,-(a7)
		lea	$3E00.w,a0
		lea	$3F00.w,a1
.loop
		cmp.l	#$082E0006,(a0)
		bne.b	.next
		cmp.l	#$000266F8,4(a0)
		bne.b	.next

		move.l	#$4E714EB9,(a0)
		pea	WaitBlit(pc)
		move.l	(a7)+,4(a0)
.next
		addq.l	#2,a0
		cmp.l	a0,a1
		bne.b	.loop
		movem.l	(a7)+,a0-a1
		rts

;--------------------------------

WaitBlit7
		move.w	D0,$DFF058
		bra.b	WaitBlit1

;--------------------------------

;WaitBlitInt
;;		bsr.b	WaitBlit

;		btst	#6,2(A6)
;		btst	#6,2(A6)
;		bne.b	.skip

;		move.w	(A0)+,$58(A6)
;		rts
;.skip
;		addq.w	#2,A0
;		rts

;--------------------------------

WaitBlit0
		move.w	D0,$58(A6)
		bra.b	WaitBlit
WaitBlit1
		move.w	D1,$58(A6)
		bra.b	WaitBlit
WaitBlit4
		move.w	D4,$58(A6)
		bra.b	WaitBlit
WaitBlit5
		move.w	D5,$58(A6)
		bra.b	WaitBlit
WaitBlit6
		move.w	D6,$58(A6)
WaitBlit
		BLITWAIT_V14	; the shipped slave was built with this older form
		rts

;--------------------------------

Patch2
		move.w	#$4EB9,$11DD6
		pea	WaitBlit7(pc)
		move.l	(A7)+,$11DD8

		movem.l	d0/a0-a2,-(a7)

		lea	$10C.w,a0
		move.w	#$4EF9,d0

		move.w	d0,(a0)+
		pea	WaitBlit0(pc)
		move.l	(a7)+,(a0)+

		move.w	d0,(a0)+
		pea	WaitBlit1(pc)
		move.l	(a7)+,(a0)+

		move.w	d0,(a0)+
		pea	WaitBlit4(pc)
		move.l	(a7)+,(a0)+

		move.w	d0,(a0)+
		pea	WaitBlit5(pc)
		move.l	(a7)+,(a0)+

		move.w	d0,(a0)+
		pea	WaitBlit6(pc)
		move.l	(a7)+,(a0)+

;		move.w	d0,(a0)+
;		pea	WaitBlitInt(pc)
;		move.l	(a7)+,(a0)+

		lea	$11000,a0
		lea	$19C00,a1
.loop
		move.l	(a0),d0
		andi.l	#$FFF0FFFF,d0		; vasm: andi is the shipped encoding
		cmpi.l	#$3D400058,d0		; move.w D?,$58(a6) (vasm: cmpi is the shipped encoding)
		bne.b	.next

		moveq	#0,d0
		move.b	1(a0),d0
		andi.b	#$F,d0		; vasm: andi is the shipped encoding
		cmpi.b	#6,d0		; vasm: cmpi is the shipped encoding
		bhi.b	.next
		lsl.w	#1,d0
		move.w	#$4EB8,(a0)
		lea	Table(pc),a2
		move.w	(a2,d0.w),2(a0)
.next
;		cmp.l	#$3D580058,(a0)		; move.w (a0)+,$58(a6)
;		bne.b	.next2

;		move.l	#$4EB8012A,(a0)
.next2
		addq.l	#2,a0
		cmp.l	a0,a1
		bne.b	.loop
		movem.l	(a7)+,d0/a0-a2

		rts

Table
		dc.w	$10C,$112,-1,-1,$118,$11E,$124
;--------------------------------

Decrunch	movem.l	d0-a6,-(a7)
		jsr	$1D798			; A0=source A1=dest
		movem.l	(A7)+,D0-A6

		cmp.l	#$439C,$1D90E		; destination
		bne.b	.skip
		cmp.w	#$32C4,$6534.w
		bne.b	.skip

		move.w	#$4E71,$6534.w		; skip protection
.skip		bsr	Fix_Decrunched
		move.w	#-1,$3A.w
		rts

;--------------------------------

Load		movem.l	d0-a6,-(a7)
		moveq	#0,D0
		move.w	$6EE88+$56,D0
		mulu	#$16DC,D0
		subi.l	#$DC,D0		; vasm: subi is the shipped encoding

		move.l	#$16DC,D1
		moveq	#1,D2
		move.l	$6EE88+$3C,A0

		bsr.w	_LoadDisk

		movem.l	(A7)+,d0-a6
		moveq	#0,D0
		rts

;--------------------------------

Load2
		movem.l	d0-a6,-(a7)

		moveq	#0,D0
		move.w	$1D92C,D0
		mulu	#$16DC,D0
		subi.l	#$DC,D0		; vasm: subi is the shipped encoding

		move.l	#$16DC,D1
		move.l	$1D906,A0
		moveq	#1,D2

		bsr.b	_LoadDisk

		movem.l	(A7)+,d0-a6
		moveq	#0,D0
		rts

;--------------------------------

_savehighs
		movem.l	d0-a6,-(a7)

		move.l	#$16DC,d0			;len
		moveq	#0,D1
		move.w	$1D92C,D1
		mulu	#$16DC,D1
		subi.l	#$DC,D1				;offset (vasm: subi is the shipped encoding)
		move.l	$1D906,a1			;address
		lea	_savename(pc),a0		;filename
		move.l	_resload(pc),a2
		jsr	resload_SaveFileOffset(a2)

		movem.l	(a7)+,d0-a6
		moveq	#0,D0
		rts

_savename	dc.b	'Disk.1',0
		even
;--------------------------------
_InstKey
	movem.l	a0-a1,-(a7)
	lea	_Key(pc),a0
	lea	$a1d4,a1	; v2 &v1
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

	cmpi.b	#$58,d0		; vasm: cmpi is the shipped encoding
	bne	.f9
	move.w	#$f0,$dff180
	move.w	#$f0,$dff180
	move.w	#$f0,$dff180
	move.w	#$0,$dff180
.f9:	move.l	(a7)+,d0
	rts
;--------------------------------
; where the init code writes the VBL routine's vectors (src/smc.i), and the fixes
SMC_VBLW1	= $3B54		; the address in move.l #x,$A572
SMC_VBLW2	= $3B5E		; the address in move.l #x,$A56C
ENH_WORK_LO	= $34F36		; the loader's unpacker variables and tables (src/enhanced.i)
	INCLUDE	fixes.i
	INCLUDE	reloc_Vroom.i
;--------------------------------
_resload	dc.l	0			;address of resident loader 
;--------------------------------
; IN:	d0=offset d1=size d2=disk a0=dest
; OUT:	d0=success

_LoadDisk	movem.l	d0-d1/a0-a2,-(a7)
		move.l	_resload(pc),a2
		jsr	resload_DiskLoad(a2)
		movem.l	(a7)+,d0-d1/a0-a2
		rts
;--------------------------------
_ReadFile	movem.l	d1/a0-a2,-(a7)
		move.l	_resload(pc),a2
		jsr	resload_LoadFile(a2)
		movem.l	(a7)+,d1/a0-a2
		rts
;--------------------------------
_GetFileSize
	movem.l	d1-a6,-(a7)
;	lea	save_game_name(pc),a0
	move.l	(_resload,pc),a2
	jsr	(resload_GetFileSize,a2)
	movem.l	(a7)+,d1-a6
	rts
;--------------------------------
_Exit		pea	TDREASON_OK.w
		bra.b	_end
_NoSupported	pea	TDREASON_WRONGVER
		bra	_end
_debug		pea	TDREASON_DEBUG.w
_end		move.l	_resload(pc),-(a7)
		addq.l	#resload_Abort,(a7)
		rts
;====================================================================== 
;======================================================================

	END
