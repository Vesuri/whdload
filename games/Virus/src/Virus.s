;*---------------------------------------------------------------------------
;  :Program.	Virus.s
;  :Contents.	Slave for "Virus" (c) 1988 D.J. Braben / Firebird
;  :Author.	John Selck (slave V1.0, 15.01.99)
;  :Note.	The install package ships no source. This is a reconstruction
;		from the shipped Virus.slave (420 bytes; vasm rebuilt it byte for
;		byte with -no-opt); labels and comments are ours. 2.0b from here.
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
		dc.w	17			;ws_Version: ws_config
		dc.w	WHDLF_Disk|WHDLF_NoError	;ws_Flags
		dc.l	$88000			;ws_BaseMemSize: 544 KB, see below
		dc.l	0			;ws_ExecInstall
		dc.w	_start-base		;ws_GameLoader
		dc.w	0			;ws_CurrentDir
		dc.w	0			;ws_DontCache
_keydebug	dc.b	$58			;ws_keydebug = F9
_keyexit	dc.b	$59			;ws_keyexit = F10
		dc.l	0			;ws_ExpMem
		dc.w	_name-base		;ws_name
		dc.w	_copy-base		;ws_copy
		dc.w	_info-base		;ws_info
		dc.w	0			;ws_kickname
		dc.l	0			;ws_kicksize
		dc.w	0			;ws_kickcrc
		dc.w	_config-base		;ws_config

_config		dc.b	"C1:B:Enhanced framerate;"
		dc.b	"C2:L:Game speed:25 Hz,16.7 Hz,12.5 Hz",0
_name		dc.b	"Virus",0
_copy		dc.b	"1988 D.J. Braben / Firebird",0
_info		dc.b	"installed by John Selck",10
		dc.b	"enhanced by Vesuri",10
		dc.b	"Version 2.0b (20.11.2026)",0
		dc.b	"$VER: Virus.slave 2.0b (20.11.2026)",0
		even

;======================================================================

_start		lea	_resload(pc),a1
		move.l	a0,(a1)
		lea	_tags(pc),a0
		move.l	_resload(pc),a2
		jsr	resload_Control(a2)

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

		lea	_pl_game(pc),a0
		sub.l	a1,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)

		move.l	_enhanced(pc),d0
		beq.b	.orig
		move.l	_speed(pc),d0		;game speed 0-2: a tick every 2-4 fields
		cmp.l	#2,d0
		bls.b	.speed
		moveq	#0,d0
.speed		addq.l	#2,d0
		lea	_period(pc),a0
		move.l	d0,(a0)
		lea	_pl_enhanced(pc),a0
		sub.l	a1,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
.orig
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
; The landscape setup ($643d8) rewrites five renderer instructions ($6577a-$65785,
; $65850-$65853) when the landscape type changes, then builds the map; nothing flushed
; the instruction cache after it.

_pl_game	PL_START
		PL_PSS	$644b6,_flush,4		;move.w $c9fe,$c9fc: the setup's end
		PL_END

_flush		move.w	$c9fe,$c9fc		;the type now set up
		move.l	a0,-(sp)
		move.l	_resload(pc),a0
		jsr	resload_FlushCache(a0)	;keeps every register
		move.l	(sp)+,a0
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
; Enhanced framerate (CUSTOM1=1): fixed-rate game time (docs/internals.md, "Game time").
; The original runs one simulation step per rendered frame, so the game's speed follows
; the frame rate. Here every main loop pass is one tick, due every _period fields (2-4,
; CUSTOM2), counted by the VBL. A pass waits while it is early; when the next tick is
; already due as well, the pass leaves out the drawing (the renderer, the swap and the
; clear request) and only simulates, at most MAX_SKIP passes in a row. Behind by more
; than LIMIT fields (a machine that cannot keep up), the time past it is dropped.
; The attract screen's approaching ship (768 frames and the departure, at most one a
; field because of the clear) gets the same at a tick a field.

MAX_SKIP	= 3
LIMIT		= 16

_pl_enhanced	PL_START
		PL_PS	$607fe,_vbl		;move.b $3ca1b,d0 (the VBL's fade countdown)
		PL_PS	$641fe,_enter		;jsr $58d38: the main loop's entry
		PL_PS	$64212,_pass		;tst.b $3ca07 (pause), bne.s; the calls
		PL_W	$64218,$6032		;bra.s $6424c: the keys after the calls
		PL_PS	$65d30,_attract_enter	;jsr $62236: the fade-in, then the ship
		PL_PS	$65d84,_attract		;lea $1084,a1: the ship's frame, to $65db1
		PL_W	$65d8a,$6026		;bra.s $65db2: the keys
		PL_END

; In the level 3 handler's VBL part, all registers saved.
_vbl		lea	_fields(pc),a0
		addq.l	#1,(a0)
		move.b	$3ca1b,d0
		rts

; The main loop's entry, after the title, a wave or a pause screen: time starts now.
_enter		jsr	$58d38			;clear the screen and wait
		bra.b	_rebase

_attract_enter	jsr	$62236			;fade in
_rebase		move.l	a0,-(sp)
		lea	_due(pc),a0
		move.l	_fields(pc),(a0)
		move.l	(sp)+,a0
		rts

; One main loop pass: the original's calls, from $6421a to $6424b.
_pass		tst.b	$3ca07			;paused: no game time passes
		bne.b	_rebase
		move.l	d1,-(sp)
		move.l	_period(pc),d1
		bsr.w	_pace
		move.l	(sp)+,d1
		jsr	$672fc			;object rotations from the frame counter
		jsr	$60a1c			;particles: move, into the depth lists
		jsr	$66718			;the player, the camera
		jsr	$6249a			;the other objects, the radar list
		bsr.w	_draw
		beq.b	.nodraw
		jsr	$65174			;the renderer: landscape, objects, radar
		bra.b	.drawn
.nodraw		move.l	#$9ea6,$1022		;the radar list, as the renderer leaves it
.drawn		jsr	$64d74			;the depth lists emptied
		jsr	$61f32			;the wave's end
		bsr.w	_draw
		beq.b	.noswap
		move.l	a0,-(sp)
		lea	_frames(pc),a0
		addq.l	#1,(a0)
		movea.l	(sp)+,a0
		jsr	$58d8c			;show the frame
		jsr	$58cfe			;clear the other buffer from the next VBL
.noswap		jsr	$65a78			;the score, extra lives
		jmp	$64356			;the ship's trail

; The attract screen's frame, d0-d3 pushed by the caller: d0/d1 the angles, 4(sp) the
; distance. Draws the ship, shows it and clears the other buffer, unless behind.
_attract	move.l	d1,-(sp)
		moveq	#1,d1
		bsr.w	_pace
		move.l	(sp)+,d1
		bsr.w	_draw
		beq.b	.skip
		lea	$1084,a1
		jsr	$604aa			;the rotation
		movem.w	8(sp),d2
		lea	$4b638,a6
		moveq	#0,d0
		moveq	#0,d1
		jsr	$6776c			;the ship
		jsr	$58d8c			;show it
		jsr	$58d48			;clear the other buffer
.skip		rts

; Z set when this pass does not draw. Keeps every register.
_draw		move.l	a0,-(sp)
		lea	_drawn(pc),a0
		tst.b	(a0)
		movea.l	(sp)+,a0
		rts

; Wait for the tick's field, then decide whether the pass draws; d1 fields a tick.
_pace		movem.l	d0-d1/a0,-(sp)
		lea	_due(pc),a0
.wait		move.l	_fields(pc),d0
		sub.l	(a0),d0			;fields since the tick was due
		bmi.b	.wait
		cmp.l	#LIMIT,d0
		bls.b	.ok
		move.l	_fields(pc),(a0)	;too far behind: drop the time
		moveq	#0,d0
.ok		add.l	d1,(a0)			;the next tick
		lea	_skips(pc),a0
		cmp.l	d1,d0
		bcs.b	.draw			;the next tick is not due yet
		cmp.b	#MAX_SKIP,(a0)
		bcc.b	.draw
		addq.b	#1,(a0)
		sf	1(a0)			;_drawn
		bra.b	.done
.draw		clr.b	(a0)
		st	1(a0)
.done		movem.l	(sp)+,d0-d1/a0
		rts

_tags		dc.l	WHDLTAG_CUSTOM1_GET
_enhanced	dc.l	0
		dc.l	WHDLTAG_CUSTOM2_GET
_speed		dc.l	0
		dc.l	TAG_END
_fields		dc.l	0			;VBLs since the start (tools/pace.py reads
_frames		dc.l	0			;these two and _period from _pass's address)
_due		dc.l	0			;the field the next tick is due
_period		dc.l	3			;fields a tick
_skips		dc.b	0			;passes in a row without drawing
_drawn		dc.b	0			;this pass draws

;======================================================================

_resload	dc.l	0
_hiname		dc.b	"Virus.hi",0
		even
