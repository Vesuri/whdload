;*---------------------------------------------------------------------------
;  :Program.	Virus.s
;  :Contents.	Slave for "Virus" (c) 1988 D.J. Braben / Firebird
;  :Author.	John Selck (slave V1.0, 15.01.99)
;  :Note.	The install package ships no source. This is a reconstruction
;		from the shipped Virus.slave (420 bytes) that vasm rebuilds byte
;		for byte with -no-opt; labels and comments are ours.
;---------------------------------------------------------------------------*

	INCLUDE	whdload.i

; The game: the whole disk image (Disk.1, 184320 bytes) loads at $3b800 and starts
; at $63ec8. Highscores: 280 bytes at $66e2e, stored nibble-swapped and inverted.
DISK_BASE	= $3b800
DISK_SIZE	= 184320
GAME_START	= $63ec8
HI_TABLE	= $66e2e
HI_SIZE		= 280

;======================================================================

base		moveq	#-1,d0
		rts
		dc.b	"WHDLOADS"		;ws_ID
		dc.w	4			;ws_Version
		dc.w	WHDLF_Disk|WHDLF_NoError	;ws_Flags
		dc.l	$88000			;ws_BaseMemSize: 544 KB, see below
		dc.l	0			;ws_ExecInstall
		dc.w	_start-base		;ws_GameLoader
		dc.w	0			;ws_CurrentDir
		dc.w	0			;ws_DontCache
_keydebug	dc.b	$58			;ws_keydebug = F9
_keyexit	dc.b	$59			;ws_keyexit = F10

		dc.b	"$VER:Virus slave V1.0 by John Selck 15.01.99 ",0

;======================================================================

_start		lea	_resload(pc),a1
		move.l	a0,(a1)

	; clear $1000-$3b7ff
		lea	($1000).w,a0
		move.w	#($3b800-$1000)/4-1,d0
.clr		clr.l	(a0)+
		dbf	d0,.clr

	; load the whole disk
		lea	DISK_BASE,a0
		moveq	#0,d0
		move.l	#DISK_SIZE,d1
		moveq	#1,d2
		move.l	_resload(pc),a2
		jsr	resload_DiskLoad(a2)

		bsr.b	_loadhi

	; keyboard interrupt: nop + jsr _keyboard
		move.l	#$4e714eb9,d0
		move.l	d0,$608c0
		lea	_keyboard(pc),a0
		move.l	a0,$608c4
	; highscore entry: nop + jsr _savehi
		move.l	d0,$67116
		lea	_savehi(pc),a0
		move.l	a0,$6711a

		move.l	#1,d0
		move.l	d0,d1
		move.l	_resload(pc),a2
		jsr	resload_SetCACR(a2)	;instruction cache on

		jmp	GAME_START

;----------------------------------------------------------------------

_loadhi		lea	_hiname(pc),a0
		move.l	_resload(pc),a2
		jsr	resload_GetFileSize(a2)
		cmp.l	#HI_SIZE,d0
		bne.b	.none
		lea	_hiname(pc),a0
		lea	HI_TABLE,a1
		move.l	_resload(pc),a2
		jsr	resload_LoadFile(a2)
		bsr.b	_crypt
.none		rts

;----------------------------------------------------------------------
; Called from $6711a in place of "move.w #3000,d7; cmp.w #127,d0".

_savehi		cmp.w	#13,d0
		bne.b	.nosave
		movem.l	d0-a6,-(a7)
		bsr.b	_crypt
		move.l	#HI_SIZE,d0
		lea	_hiname(pc),a0
		lea	HI_TABLE,a1
		move.l	_resload(pc),a2
		jsr	resload_SaveFile(a2)
		movem.l	(a7)+,d0-a6
.nosave		move.w	#3000,d7
		cmp.w	#127,d0
		rts

;----------------------------------------------------------------------
; Toggles the table between the game's form and the file's (its own inverse).

_crypt		lea	HI_TABLE,a1
		move.w	#HI_SIZE-1,d0
.loop		move.b	(a1,d0.w),d1
		ror.b	#4,d1
		not.b	d1
		move.b	d1,(a1,d0.w)
		dbf	d0,.loop
		rts

;----------------------------------------------------------------------
; Not referenced: clamps a3 below $78b40 before an offset add. Apparently meant for
; the renderer writes past 512 KB that the 544 KB ws_BaseMemSize covers instead.

_clamp		cmp.l	#$78b40,a3
		blt.b	.ok
		move.l	#$78b40,a3
.ok		lsr.w	#4,d6
		add.w	d6,d6
		add.w	d6,a3
		rts

;----------------------------------------------------------------------
; Called from $608c4 with the raw CIA-A SDR byte in d0.

_keyboard	bset	#6,$bfee01		;CIA-A CRA SPMODE: handshake
		move.l	d0,-(a7)
		ror.b	#1,d0
		not.b	d0
		cmp.b	#$78,d0			;reset warning
		beq.b	.quit
		cmp.b	_keyexit(pc),d0
		beq.b	.quit
		move.l	(a7)+,d0
		rts

.quit		move.l	#TDREASON_OK,-(a7)
		move.l	_resload(pc),a2
		jmp	resload_Abort(a2)

;======================================================================

_resload	dc.l	0
_hiname		dc.b	"Virus.hi",0
		even
