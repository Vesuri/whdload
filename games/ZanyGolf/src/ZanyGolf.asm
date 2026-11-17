		incdir	"include:"
		include	whdload.i

_base		SLAVE_HEADER			;ws_Security + ws_ID
		dc.w	10			;ws_Version
		dc.w	WHDLF_NoError|WHDLF_EmulTrap|WHDLF_NoKbd
		dc.l	$80000			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	Start-_base		;ws_GameLoader
		dc.w	_data-_base
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$59			;ws_keyexit = F10
_expmem		dc.l	0
		dc.w	_name-_base		;ws_name
		dc.w	_copy-_base		;ws_copy
		dc.w	_info-_base		;ws_info
_data		dc.b	"data",0
_name		dc.b	"Zany Golf",0
_copy		dc.b	"1988 Electronic Arts",0
_info		dc.b	"installed & fixed by Bored Seal",10
		dc.b	"V1.1 (23-Jul-2006)",0
		even

Start		lea	_resload(pc),a1
		move.l	a0,(a1)
		move.l	a0,a2

		lea	(_OSEmu,pc),a0	;load&init the osemu module
		lea	($400).w,a3
		move.l	a3,a1
		jsr	(resload_LoadFileDecrunch,a2)
		move.l	a2,a0
		lea	(_base,pc),a1
		jsr	(a3)
		move.w	#0,sr

		lea	dosname,a1
		clr.l	d0
		movea.l	4,a6
		jsr	-$228(a6)
		move.l	d0,a6

		lea	file,a0
		move.l	a0,d1
		jsr	-150(a6)

		add.l	d0,d0
		add.l	d0,d0
		addq.l	#4,d0
		move.l	d0,a1

		sub.l	a0,a0
		moveq.l	#0,d0

		move.w	#$6002,$48(a1)		;deprotect
		move.b	#$60,$5a(a1)

		move.w	#$4e75,$62e(a1)		;disk access

		move.w	#$4ef9,$658(a1)
		pea	Patch
		move.l	(sp)+,$65a(a1)
		jmp	(a1)

Patch		movem.l	d0-d7/a0-a6,-(sp)
		move.l	a3,a0
		move.l	#65536,d0
		move.l	(_resload,pc),a2
		jsr     (resload_CRC16,a2)
		cmp.w	#$9cc8,d0
		bne	Unsupported

		move.l	#$4e714eb9,$1f38(a3)	;fix keyboard and set cheat
		pea	FixKey
		move.l	(sp)+,$1f3c(a3)

		movem.l	(sp)+,d0-d7/a0-a6
		jmp	(a3)

FixKey		move.w	4(sp),d0
		ror.b	#1,d0
		not.b	d0
		cmp.b	#$59,d0
		bne	BeamDelay
		move.b	#9,$15ca2	;set 9 strokes
BeamDelay	moveq	#8,d0
BM_1		move.w  d0,-(sp)
		move.b	$dff006,d0
BM_2		cmp.b	$dff006,d0
		beq	BM_2
		move.w	(sp)+,d0
		dbf	d0,BM_1
		rts

Unsupported	pea	TDREASON_WRONGVER
_end		move.l	(_resload,pc),a2
		jmp	(resload_Abort,a2)

_resload	dc.l	0		;address of resident loader
_OSEmu		dc.b	'osemu.400',0
file		dc.b	"zany",0
dosname		dc.b	"dos.library",0