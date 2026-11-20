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
; Everything the CPU alone uses, copied to ExpMem when that is fast memory
; (docs/internals.md, "CPU-only data in fast memory"): the work memory from $1000, the
; image's data, the stack and the code ($57000 on). The DMA data in it stays in chip
; memory: the copper lists and the samples, $3ca1e-$4a545.
CODE_START	= $57000
MOVE_START	= $1000
MOVE_END	= $68800
CHIP_START	= $3ca1e
CHIP_END	= $4a546
; With it, the drawing buffer (docs/internals.md, "Drawing in fast memory"): a screen
; (four planes of 8000 bytes) with room for the renderer's writes past its end.
FB_OFF		= (MOVE_END-MOVE_START+$1fff)&-$1000	;from ExpMem, 4 KB after the block
FB_SIZE		= $10000
ROWS_OFF	= FB_OFF+FB_SIZE			;the chip screens' row flags, 2 * ROWS
EXP_SIZE	= FB_OFF+FB_SIZE+$1000			;WHDLoad: whole 4 KB
SCREEN		= 4*8000				;the four planes
VIEW		= $280					;the 3D view: 16 lines down
VIEW_SIZE	= 184*40				;its 184 lines a plane
ROWS		= SCREEN/40				;a screen's rows: 200 lines of 4 planes

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
_expmem		dc.l	-EXP_SIZE		;ws_ExpMem: optional
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

		bsr.w	_relocate
		bsr.w	_loadhi

		lea	_pl_game(pc),a0
		lea	CODE_START,a1		;patch addresses are offsets from it
		add.l	_delta(pc),a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)

		move.l	_fbuf(pc),d0		;moved: the drawing in fast memory
		beq.b	.nofast
		lea	_pl_fast(pc),a0
		lea	CODE_START,a1
		add.l	_delta(pc),a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
.nofast

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
		lea	CODE_START,a1
		add.l	_delta(pc),a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
.orig
		move.l	#1,d0
		move.l	d0,d1
		move.l	_resload(pc),a2
		jsr	resload_SetCACR(a2)	;instruction cache on

		move.l	#GAME_START,a0
		add.l	_delta(pc),a0
		jmp	(a0)

;----------------------------------------------------------------------
; With fast ExpMem: copies $1000-$687ff there and adds the distance (_delta) to every long
; in the image that holds an address in it (src/reloc.i, from tools/relocmap.py) and to the
; slave's own (_srel). The chip copy, but for the chip data, is then filled with ILLEGAL, so
; that a code reference the table missed stops at once.

_relocate	move.l	_expmem(pc),d0
		beq.w	.none
		cmp.l	#$200000,d0		;chip memory: nothing to gain
		bcs.w	.none
		sub.l	#MOVE_START,d0
		lea	_delta(pc),a0
		move.l	d0,(a0)
		lea	(MOVE_START).w,a0
		move.l	_expmem(pc),a1
		move.l	#(MOVE_END-MOVE_START)/4,d1
.copy		move.l	(a0)+,(a1)+
		subq.l	#1,d1
		bne.b	.copy
		lea	DISK_BASE,a1		;the image there: the first entry's base
		add.l	d0,a1
		lea	_reloc(pc),a0
		move.w	#RELOC_COUNT-1,d1
.reloc		moveq	#0,d2
		move.w	(a0)+,d2		;the distance from the previous one / 2
		add.l	d2,a1
		add.l	d2,a1
		add.l	d0,(a1)
		dbf	d1,.reloc
		move.l	_expmem(pc),d1
		add.l	#FB_OFF,d1
		lea	_fbuf(pc),a0
		move.l	d1,(a0)
		bsr.w	_stale			;the row flags
		add.l	#ROWS_OFF-FB_OFF,d1
		lea	_lastrows(pc),a0
		move.l	d1,(a0)
		lea	_srel(pc),a0		;the slave's own references
		lea	base(pc),a1
.srel		move.w	(a0)+,d2
		beq.b	.fill
		add.l	d0,(a1,d2.w)
		bra.b	.srel
.fill		lea	(MOVE_START).w,a0	;the chip copy, but for the chip data
		move.l	#(CHIP_START-MOVE_START)/2,d1
		bsr.b	.ill
		lea	CHIP_END,a0
		move.l	#(MOVE_END-CHIP_END)/2,d1
.ill		move.w	#$4afc,(a0)+
		subq.l	#1,d1
		bne.b	.ill
.none		rts

;----------------------------------------------------------------------

_loadhi		lea	_hiname(pc),a0
		move.l	_resload(pc),a2
		jsr	resload_GetFileSize(a2)
		cmp.l	#HI_SIZE,d0
		bne.b	.none
		lea	_hiname(pc),a0
		lea	HI_TABLE,a1
		add.l	_delta(pc),a1
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
		add.l	_delta(pc),a1
		move.l	_resload(pc),a2
		jsr	resload_SaveFile(a2)
		movem.l	(a7)+,d0-a6
.nosave		move.w	#3000,d7
		cmp.w	#127,d0
		rts

;----------------------------------------------------------------------
; Toggles the table between the game's form and the file's (its own inverse).

_crypt		lea	HI_TABLE,a1
		add.l	_delta(pc),a1
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
		PL_PS	$607fe-CODE_START,_vbl		;move.b $3ca1b,d0 (the VBL's fade countdown)
		PL_W	$608c0-CODE_START,$4e71		;level 2: bset #6,$bfee01 -> nop, jsr _keyboard
		PL_PS	$608c2-CODE_START,_keyboard
		PL_PSS	$644b6-CODE_START,_flush,4		;move.w $c9fe,$c9fc: the setup's end
		PL_W	$67116-CODE_START,$4e71		;highscore entry -> nop, jsr _savehi
		PL_PS	$67118-CODE_START,_savehi
		PL_END

_flush		move.w	($c9fe).l,($c9fc).l	;the type now set up
_sr_flush	equ	*
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

;----------------------------------------------------------------------
; Calls and jumps from the slave into the game's code, wherever it runs: the address plus
; _delta. Registers and the stack as with jsr / jmp.

GCALL		MACRO
		pea	.r\@(pc)
		pea	\1
		bra.w	_gcall
.r\@
		ENDM
GJMP		MACRO
		pea	\1
		bra.w	_gcall
		ENDM

_gcall		move.l	d0,-(sp)
		move.l	_delta(pc),d0
		add.l	d0,4(sp)
		move.l	(sp)+,d0
		rts

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
		PL_PS	$641fe-CODE_START,_enter		;jsr $58d38: the main loop's entry
		PL_PS	$64212-CODE_START,_pass		;tst.b $3ca07 (pause), bne.s; the calls
		PL_W	$64218-CODE_START,$6032		;bra.s $6424c: the keys after the calls
		PL_PS	$65d30-CODE_START,_attract_enter	;jsr $62236: the fade-in, then the ship
		PL_PS	$65d84-CODE_START,_attract		;lea $1084,a1: the ship's frame, to $65db1
		PL_W	$65d8a-CODE_START,$6026		;bra.s $65db2: the keys
		PL_PS	$66c72-CODE_START,_death		;tst.b $609a2: the death sequence's pass
		PL_PS	$66c7c-CODE_START,_drequest	;jsr $58cfe: its clear request
		PL_PS	$66c94-CODE_START,_drender	;jsr $65174: its renderer
		PL_PS	$66ce4-CODE_START,_dshow		;jsr $58d8c: its swap
		PL_PSS	$66a50-CODE_START,_shipemit,2	;lea $673aa(pc),a2; movem.l a2/a6,(a1)
		PL_END

; In the level 3 handler's VBL part, all registers saved.
_vbl		lea	_fields(pc),a0
		addq.l	#1,(a0)
		move.b	($3ca1b).l,d0
_sr_vbl		equ	*
		rts

; The main loop's entry, after the title, a wave or a pause screen: time starts now.
_enter		GCALL	$58d38			;clear the screen and wait
		bra.b	_rebase

_attract_enter	GCALL	$62236			;fade in
_rebase		move.l	a0,-(sp)
		lea	_due(pc),a0
		move.l	_fields(pc),(a0)
		move.l	(sp)+,a0
		rts

; One main loop pass: the original's calls, from $6421a to $6424b.
_pass		tst.b	($3ca07).l		;paused: no game time passes
_sr_pass	equ	*
		bne.b	_rebase
		move.l	d1,-(sp)
		move.l	_period(pc),d1
		bsr.w	_pace
		move.l	(sp)+,d1
		move.l	a0,-(sp)
		lea	_shipent(pc),a0
		clr.l	(a0)			;not in the lists yet
		movea.l	(sp)+,a0
		GCALL	$672fc			;object rotations from the frame counter
		GCALL	$60a1c			;particles: move, into the depth lists
		GCALL	$66718			;the player, the camera
		GCALL	$6249a			;the other objects, the radar list
		bsr.w	_draw
		beq.b	.nodraw
		GCALL	$65174			;the renderer: landscape, objects, radar
		bra.b	.drawn
.nodraw		move.l	#$9ea6,($1022).l	;the radar list, as the renderer leaves it
_sr_nodraw	equ	*
		bsr.w	_shiptest		;the drawer's test of the ship against the terrain
.drawn		GCALL	$64d74			;the depth lists emptied
		GCALL	$61f32			;the wave's end
		bsr.w	_draw
		beq.b	.noswap
		move.l	a0,-(sp)
		lea	_frames(pc),a0
		addq.l	#1,(a0)
		movea.l	(sp)+,a0
		bsr.w	_show			;show the frame
		bsr.w	_request		;clear the other buffer
.noswap		GCALL	$65a78			;the score, extra lives
		GJMP	$64356			;the ship's trail

; The death sequence ($66c72-$66d05): 51 passes of its own (particles, objects, renderer,
; swap), counted in passes. Each is a tick too; behind, a pass leaves out the clear
; request, the renderer and the swap. The last pass (the count $c9f6 at 50) always draws.
_death		move.l	d1,-(sp)
		move.l	_period(pc),d1
		bsr.w	_pace
		move.l	a0,-(sp)
		cmp.w	#50,($c9f6).l		;the pass count
_sr_dcount	equ	*
		bcs.b	.paced
		lea	_skips(pc),a0
		clr.b	(a0)
		st	1(a0)			;_drawn
.paced		movea.l	(sp)+,a0
		move.l	(sp)+,d1
		tst.b	($609a2).l		;the replaced instruction: its flags returned
_sr_death	equ	*
		rts

_drequest	bsr.w	_draw
		bne.w	_request
		rts

_drender	bsr.w	_draw
		beq.b	.no
		GJMP	$65174			;the renderer
.no		move.l	#$9ea6,($1022).l	;the radar list, as the renderer leaves it
_sr_dnodraw	equ	*
		rts

_dshow		bsr.w	_draw
		beq.b	.no
		move.l	a0,-(sp)
		lea	_frames(pc),a0
		addq.l	#1,(a0)
		movea.l	(sp)+,a0
		bra.w	_show
.no		rts

; The attract screen's frame, d0-d3 pushed by the caller: d0/d1 the angles, 4(sp) the
; distance. Draws the ship, shows it and clears the other buffer, unless behind.
_attract	move.l	d1,-(sp)
		moveq	#1,d1
		bsr.w	_pace
		move.l	(sp)+,d1
		bsr.w	_draw
		beq.b	.skip
		lea	($1084).l,a1
_sr_attract1	equ	*
		GCALL	$604aa			;the rotation
		movem.w	8(sp),d2
		lea	($4b638).l,a6
_sr_attract2	equ	*
		moveq	#0,d0
		moveq	#0,d1
		GCALL	$6776c			;the ship
		GCALL	$58d8c			;show it
		GCALL	$58d48			;clear the other buffer
.skip		rts

; The ship's depth-list entry ($66a50, the main loop's pass): the drawer tests the ship's
; vertices against the terrain height and marks a contact in $3ca0f, on which the player
; routine crashes the ship at the next tick (docs/internals.md, "Game time"). A pass that
; does not draw runs the same test from the same entry, so that no contact is missed.
_shipemit	move.l	#$673aa,a2		;the replaced instructions: the object drawer
		add.l	_delta(pc),a2
		movem.l	a2/a6,(a1)
		move.l	a0,-(sp)
		lea	_shipent(pc),a0
		move.l	a1,(a0)
		movea.l	(sp)+,a0
		rts

; One row of the drawer's rotation ($67454): \1 = row (a1)+ . (d0,d1,d2), d6 used.
SROW		MACRO
		move.w	(a1)+,\1
		muls.w	d0,\1
		swap	\1
		add.w	\1,\1
		move.w	(a1)+,d6
		muls.w	d1,d6
		swap	d6
		add.w	d6,d6
		add.w	d6,\1
		move.w	(a1)+,d6
		muls.w	d2,d6
		swap	d6
		add.w	d6,d6
		add.w	d6,\1
		ENDM

; The drawer's test ($6741e-$6763e) for the ship's entry: entry +4 the model, +8 the
; matrix, +26 the position; the model's flags (bit 0 drawn this way, bit 1 tested), its
; vertex count - 1 at +2 and the vertices from +8. Keeps every register.
_shiptest	movem.l	d0-d7/a0-a6,-(sp)
		lea	_shipent(pc),a0
		move.l	(a0),d0
		beq.w	.done
		clr.l	(a0)
		movea.l	d0,a0
		movea.l	4(a0),a4
		btst	#0,(a4)
		beq.w	.done
		btst	#1,(a4)
		beq.w	.done
		move.w	2(a4),d7
		lea	8(a4),a6
.vertex		movem.w	(a6)+,d0-d2
		lea	8(a0),a1
		SROW	d3
		SROW	d4
		SROW	d5
		add.w	26(a0),d3		;x, y, z against the camera
		add.w	28(a0),d4
		add.w	30(a0),d5
		move.l	_gv(pc),a3
		move.w	d3,d6
		add.w	$107e-$1000(a3),d6
		move.w	d7,-(sp)
		move.w	d5,d7
		add.w	$1082-$1000(a3),d7
		sub.w	#3584,d7
		movem.l	d4/a0/a4/a6,-(sp)
		GCALL	$656b2			;the terrain height there: d1
		movem.l	(sp)+,d4/a0/a4/a6
		move.w	(sp)+,d7
		move.l	_gv(pc),a3
		sub.w	$1080-$1000(a3),d1
		cmp.w	d1,d4
		ble.b	.next
		move.l	_p3ca0f(pc),a1		;below it: the contact
		st	(a1)
		bra.b	.done
.next		dbf	d7,.vertex
.done		movem.l	(sp)+,d0-d7/a0-a6
		rts

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

;======================================================================
; With the game moved to fast memory, the main loop draws into a buffer there instead of
; the chip back buffer (docs/internals.md, "Drawing in fast memory"). Its swap copies the
; buffer to the chip back buffer (once that has left the display) and shows it; its clear
; request is a CPU clear of the buffer's 3D view, done where the game would wait for the
; blitter clear. Everything else that swaps, clears or waits for the clear first leaves
; the mode (_leave): the buffer goes to the chip back buffer and the game's pointers back
; to it, so the other screens run as in the original. In the game's terms: $1006/$100a
; the drawing buffer and its view, $100e/$1012 the two chip buffers, $3ca08 which is the
; back one, $606ac the clear flag.

_pl_fast	PL_START
		PL_PS	$64238-CODE_START,_fswap	;the main loop: jsr $58d8c (show the frame)
		PL_PS	$6423e-CODE_START,_fclear	;jsr $58cfe (clear the other buffer)
		PL_PSS	$58d8c-CODE_START,_leave_swap,2	;the swap: eori.b #$ff,$3ca08
		PL_PSS	$58dda-CODE_START,_pswap,2	;the pointers' swap alone (the score)
		PL_PS	$58cfe-CODE_START,_leave_wait	;the clear request: tst.w $606ac
		PL_PS	$58d48-CODE_START,_leave_wait	;the attract screen's clear: the same
		PL_PS	$58d3e-CODE_START,_fwait	;waits for the clear: tst.w $606ac
		PL_PS	$6547e-CODE_START,_fwait	;the renderer
		PL_PS	$65de8-CODE_START,_fwait
		PL_PS	$65f22-CODE_START,_fwait
		PL_PS	$67822-CODE_START,_fwait
		PL_END

; The main loop's swap. Keeps every register.
_fswap		movem.l	d0-d1/a0-a2,-(sp)
		lea	_away(pc),a0
		sf	(a0)
		move.l	_fbuf(pc),d0
		move.l	_gv(pc),a2
		cmp.l	$1006-$1000(a2),d0
		beq.b	.copy
		bsr.w	_swapbody		;the frame was drawn in chip: show it,
		move.l	$1006-$1000(a2),a0	;and the buffer starts as the new back one
		move.l	d0,a1
		bsr.w	_scopy
		bsr.w	_stale			;the chip screens were drawn by the game
		bra.b	.set
.copy		bsr.w	_backchip
		bsr.w	_hidden
		move.l	d0,a0
		bsr.w	_dcopy
		bsr.w	_swapbody
.set		move.l	d0,$1006-$1000(a2)
		add.l	#VIEW,d0
		move.l	d0,$100a-$1000(a2)
		lea	_swapped(pc),a0
		move.l	_fields(pc),(a0)
		movem.l	(sp)+,d0-d1/a0-a2
		rts

; The main loop's clear request: the clear happens at the next wait for it.
_fclear		move.l	a0,-(sp)
		lea	_pending(pc),a0
		st	(a0)
		movea.l	(sp)+,a0
		rts

; The game's swaps and clear requests, entered: out of the mode first, then the original.
_leave_swap	bsr.w	_leave
		move.l	a0,-(sp)
		move.l	_p3ca08(pc),a0
		eori.b	#$ff,(a0)		;the replaced instruction: its flags returned
		movea.l	(sp)+,a0
		rts

; The pointers' swap alone ($58dda). The score draws into both screens through a pair of
; them (Disk.1 $2a2f0, $2a302). In the mode the first points the game at the shown chip
; screen, the second back at the buffer, so the buffer gets the score and the mode is not
; left; $3ca08 changes as in the original. Otherwise the original's.
_pswap		movem.l	d0/a0/a2,-(sp)
		move.l	_gv(pc),a2
		move.l	_p3ca08(pc),a0
		move.b	_away(pc),d0
		bne.b	.back
		move.l	_fbuf(pc),d0
		cmp.l	$1006-$1000(a2),d0
		bne.b	.orig
		eori.b	#$ff,(a0)		;as the game: the shown screen is now the back
		bne.b	.b			;one in its terms
		move.l	$1012-$1000(a2),d0
		bra.b	.away
.b		move.l	$100e-$1000(a2),d0
.away		lea	_away(pc),a0
		st	(a0)
		bsr.w	_stale			;the game draws in a chip screen
		bra.b	.set
.back		eori.b	#$ff,(a0)
		lea	_away(pc),a0
		sf	(a0)
		move.l	_fbuf(pc),d0
.set		move.l	d0,$1006-$1000(a2)
		add.l	#VIEW,d0
		move.l	d0,$100a-$1000(a2)
		movem.l	(sp)+,d0/a0/a2
		addq.l	#4,sp			;not the game's code: back to its caller
		rts
.orig		movem.l	(sp)+,d0/a0/a2
		bra.b	_leave_swap

_leave_wait	bsr.w	_leave
		bra.b	_tstclear

; A wait for the clear: the pending clear of the buffer first.
_fwait		bsr.w	_fpending
_tstclear	move.l	a0,-(sp)
		move.l	_p606ac(pc),a0
		tst.w	(a0)			;the replaced instruction: its flags returned
		movea.l	(sp)+,a0
		rts

; Out of the mode: the buffer (cleared if due) to the chip back buffer, the pointers there.
_leave		movem.l	d0-d1/a0-a2,-(sp)
		lea	_away(pc),a0
		sf	(a0)
		move.l	_fbuf(pc),d0
		move.l	_gv(pc),a2
		cmp.l	$1006-$1000(a2),d0
		bne.b	.out
		bsr.w	_fpending
		bsr.w	_backchip
		bsr.w	_hidden
		move.l	d0,a0
		bsr.w	_scopy
		bsr.w	_stale			;the game draws in chip from here
		move.l	a1,$1006-$1000(a2)
		lea	VIEW(a1),a1
		move.l	a1,$100a-$1000(a2)
.out		movem.l	(sp)+,d0-d1/a0-a2
		rts

; As the game's swap ($58d8c), a2 = $1000 where it is: shows the back buffer, the other
; one becomes the back one.
_swapbody	move.l	_p3ca08(pc),a0
		eori.b	#$ff,(a0)
		bne.b	.b
		move.l	$1012-$1000(a2),a0	;0: $1012 the back one, $100e shown
		move.l	#$3ca1e,d1
		bra.b	.set
.b		move.l	$100e-$1000(a2),a0
		move.l	#$3ca42,d1
.set		move.l	a0,$1006-$1000(a2)
		lea	VIEW(a0),a0
		move.l	a0,$100a-$1000(a2)
		move.l	d1,$dff080
		rts

; a1 = the chip back buffer: $1012 while $3ca08 is 0, else $100e.
_backchip	move.l	_p3ca08(pc),a1
		tst.b	(a1)
		bne.b	.a
		move.l	$1012-$1000(a2),a1
		rts
.a		move.l	$100e-$1000(a2),a1
		rts

; Waits until the chip back buffer has left the display: a VBL since the last swap.
_hidden		move.l	d0,-(sp)
		move.l	_swapped(pc),d0
.wait		cmp.l	_fields(pc),d0
		beq.b	.wait
		move.l	(sp)+,d0
		rts

; Copies a screen from a0 to a1 (a1 kept).
_scopy		movem.l	d0-d7/a0-a1/a3-a6,-(sp)
		move.w	#SCREEN/40-1,d0
.loop		movem.l	(a0)+,d1-d7/a3-a5
		movem.l	d1-d7/a3-a5,(a1)
		lea	40(a1),a1
		dbf	d0,.loop
		movem.l	(sp)+,d0-d7/a0-a1/a3-a6
		rts

; Copies the buffer a0 to the chip back screen a1 (a1 kept), row by row (40 bytes, a
; line of a plane), leaving out the rows that are zero in the buffer and already zero
; there: the sky, the black below the landscape, empty planes. A flag per row and chip
; screen (ROWS_OFF, the second screen's after the first's) says whether the row there may
; be nonzero; _stale sets them all when the game itself has drawn in the chip screens.
_dcopy		movem.l	d0-d7/a0-a6,-(sp)
		move.l	_fbuf(pc),a2
		add.l	#ROWS_OFF-FB_OFF,a2
		move.l	a1,d0
		and.w	#$8000,d0		;$78000: the second screen
		beq.b	.first
		lea	ROWS(a2),a2
.first		lea	_lastrows(pc),a6
		move.l	a2,(a6)
		lea	SCREEN(a0),a6
.row		move.l	(a0),d0
		bne.b	.copy
		move.l	4(a0),d0
		bne.b	.copy
		move.l	8(a0),d0
		bne.b	.copy
		move.l	12(a0),d0
		bne.b	.copy
		move.l	16(a0),d0
		bne.b	.copy
		move.l	20(a0),d0
		bne.b	.copy
		move.l	24(a0),d0
		bne.b	.copy
		move.l	28(a0),d0
		bne.b	.copy
		move.l	32(a0),d0
		bne.b	.copy
		move.l	36(a0),d0
		bne.b	.copy
		tst.b	(a2)+			;zero here: and there?
		beq.b	.skip
		sf	-1(a2)			;not yet: zeros once more
		bra.b	.write
.copy		st	(a2)+
.write		movem.l	(a0)+,d1-d7/a3-a5
		movem.l	d1-d7/a3-a5,(a1)
		lea	40(a1),a1
		cmpa.l	a6,a0
		bne.b	.row
		bra.b	.done
.skip		lea	40(a0),a0
		lea	40(a1),a1
		cmpa.l	a6,a0
		bne.b	.row
.done		movem.l	(sp)+,d0-d7/a0-a6
		rts

; Every row of both chip screens may be nonzero. Keeps every register.
_stale		movem.l	d0/a0,-(sp)
		move.l	_fbuf(pc),a0
		add.l	#ROWS_OFF-FB_OFF,a0
		move.w	#2*ROWS/4-1,d0
.set		move.l	#-1,(a0)+
		dbf	d0,.set
		movem.l	(sp)+,d0/a0
		rts

; The pending clear of the buffer's 3D view, four planes: the rows that may be nonzero.
; The flags of the screen copied last (_lastrows) are, from the copy on, the buffer's own
; (nonzero rows set); nothing draws into the view between the swap and the clear, and the
; score's drawing in chip memory sets them all.
_fpending	movem.l	d0-d7/a0-a1/a3-a6,-(sp)
		lea	_pending(pc),a0
		tst.b	(a0)
		beq.b	.done
		sf	(a0)
		move.l	_fbuf(pc),a0
		lea	VIEW(a0),a0		;the first plane's view
		move.l	_lastrows(pc),a1
		lea	VIEW/40(a1),a1		;its first row's flag
		moveq	#0,d1
		moveq	#0,d2
		moveq	#0,d3
		moveq	#0,d4
		moveq	#0,d5
		moveq	#4-1,d7
.plane		move.w	#VIEW_SIZE/40-1,d0
.row		tst.b	(a1)+
		beq.b	.next
		movem.l	d1-d5,(a0)
		movem.l	d1-d5,20(a0)
.next		lea	40(a0),a0
		dbf	d0,.row
		lea	VIEW/40(a1),a1		;the next plane's
		lea	VIEW(a0),a0
		dbf	d7,.plane
.done		movem.l	(sp)+,d0-d7/a0-a1/a3-a6
		rts

; The enhanced pass's show and clear request.
_show		move.l	d0,-(sp)
		move.l	_fbuf(pc),d0
		movem.l	(sp)+,d0		;keeps the flags
		bne.w	_fswap
		GJMP	$58d8c

_request	move.l	d0,-(sp)
		move.l	_fbuf(pc),d0
		movem.l	(sp)+,d0
		bne.w	_fclear
		GJMP	$58cfe

_fbuf		dc.l	0			;the drawing buffer (0: not moved)
_gv		dc.l	$1000			;the game's variables, $3ca08 and $606ac,
_p3ca08		dc.l	$3ca08			;where they are (relocated with _srel)
_p606ac		dc.l	$606ac
_p3ca0f		dc.l	$3ca0f
_shipent	dc.l	0			;the ship's entry this pass (0: none)
_swapped	dc.l	0			;_fields at the main loop's last swap
_lastrows	dc.l	0			;the row flags of the screen copied last
_pending	dc.b	0			;the buffer's clear is due
_away		dc.b	0			;between the score's two pointer swaps
		even

_tags		dc.l	WHDLTAG_CUSTOM1_GET
_enhanced	dc.l	0
		dc.l	WHDLTAG_CUSTOM2_GET
_speed		dc.l	0
		dc.l	TAG_END
_fields		dc.l	0			;VBLs since the start (tools/pace.py reads
_frames		dc.l	0			;these two and _period from _pass's address)
_due		dc.l	0			;the field the next tick is due
_period		dc.l	3			;fields a tick
_delta		dc.l	0			;the distance moved (0: not moved)
_skips		dc.b	0			;passes in a row without drawing
_drawn		dc.b	0			;this pass draws

;======================================================================

; The slave's references to moved addresses (absolute longs ending at each label).
_srel		dc.w	_sr_flush-8-base,_sr_flush-4-base,_sr_vbl-4-base,_sr_pass-4-base
		dc.w	_sr_nodraw-8-base,_sr_nodraw-4-base,_sr_attract1-4-base
		dc.w	_sr_attract2-4-base,_sr_death-4-base,_sr_dcount-4-base,_sr_dnodraw-8-base
		dc.w	_sr_dnodraw-4-base,_gv-base,_p3ca08-base,_p606ac-base
		dc.w	_p3ca0f-base,0

_resload	dc.l	0
_hiname		dc.b	"Virus.hi",0
		even

		INCLUDE	reloc.i
