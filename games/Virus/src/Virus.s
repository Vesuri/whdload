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
; Frames between ticks (with Enhanced framerate): the depth-list entries of the last two ticks by key
; (docs/internals.md, "Frames between ticks").
KEYS		= 1024				;particle slot * 2 + 0/1, K_OBJ +, K_LIGHT +, K_SHIP
RECS		= 1024				;entries a tick: at most 375 * 2 + 128 + 128 + 1
BUCKET		= 3276				;a depth list's bucket
STG_OFF		= ROWS_OFF+$1000		;the staging lists: 10 buckets
ENT_OFF		= STG_OFF+$8000			;the entries by key: two tables of KEYS * 32
TAG_OFF		= ENT_OFF+2*KEYS*32		;their tags: tick.w, size.b, bucket.b
USE_OFF		= TAG_OFF+2*KEYS*4		;the tick a last tick's entry was paired in
REC_OFF		= USE_OFF+KEYS*2		;the tick's records: two lists of RECS * 12
GONE_OFF	= REC_OFF+2*RECS*12		;the tick a slot was moved away in: 384 + 128
BTV_OFF		= GONE_OFF+(384+128)*2		;and BTV_SIZE bytes of the slave's own (BV_)
BT_END		= BTV_OFF+$200
EXP_SIZE	= (BT_END+$fff)&-$1000			;WHDLoad: whole 4 KB
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
		dc.b	"C2:L:Game speed:16.7 Hz,25 Hz,12.5 Hz",0
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
		move.l	_speed(pc),d0		;game speed 0-2: 16.7, 25, 12.5 Hz
		cmp.l	#2,d0
		bls.b	.speed
		moveq	#0,d0
.speed		moveq	#0,d1
		move.b	.fields(pc,d0.l),d1	;a tick every 3, 2 or 4 fields
		lea	_period(pc),a0
		move.l	d1,(a0)
		bra.b	.patch
.fields		dc.b	3,2,4,0
.patch
		lea	_pl_enhanced(pc),a0
		lea	CODE_START,a1
		add.l	_delta(pc),a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
		move.l	_fbuf(pc),d0		;frames between ticks: with fast memory
		beq.b	.orig
		bsr.w	_btinit
		lea	_pl_between(pc),a0
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
		PL_PS	$6406c-CODE_START,_title		;jsr $62236: the title's fade-in
		PL_PS	$640fe-CODE_START,_untitle	;jsr $621a6: its fade-out
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

;----------------------------------------------------------------------
; The title shows while the game builds its tables, from the fade-in to the fade-out: 543
; fields on the a500+, 166 on the a1200, 12 on a 50 MHz 68030. It now shows at least the
; a1200's TITLE fields.

TITLE		= 166

_title		GCALL	$62236			;fade in
		move.l	a0,-(sp)
		lea	_shown(pc),a0
		move.l	_fields(pc),(a0)
		movea.l	(sp)+,a0
		rts

_untitle	move.l	d0,-(sp)
.wait		move.l	_fields(pc),d0
		sub.l	_shown(pc),d0
		cmp.l	#TITLE,d0
		bcs.b	.wait
		move.l	(sp)+,d0
		GJMP	$621a6			;fade out

_shown		dc.l	0			;_fields when the title had faded in

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
		move.l	a0,-(sp)
		lea	_okcur(pc),a0
		sf	(a0)			;no last tick to draw from
		movea.l	(sp)+,a0
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
		bsr.w	_btbegin		;frames between ticks: record the entries
		GCALL	$672fc			;object rotations from the frame counter
		GCALL	$60a1c			;particles: move, into the depth lists
		GCALL	$66718			;the player, the camera
		GCALL	$6249a			;the other objects, the radar list
		bsr.w	_btcapture
		bsr.w	_draw
		beq.b	.nodraw
		bsr.w	_btframes		;the frames between the last tick and this one
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
		bsr.w	_btbegin		;frames between ticks: a tick of its own
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

_drender	bsr.w	_btcapture
		bsr.w	_draw
		beq.b	.no
		move.l	a0,-(sp)
		lea	_dpass(pc),a0
		st	(a0)
		bsr.w	_btframes		;its frames between ticks
		sf	(a0)
		movea.l	(sp)+,a0
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
		bsr.w	_recording		;frames between ticks: its record
		beq.b	.r
		movem.l	d0-d3/a0,-(sp)
		move.w	#K_SHIP,d0
		move.w	d0,d1
		move.w	d5,d2
		moveq	#32,d3
		movea.l	a1,a0
		bsr.w	_record
		movem.l	(sp)+,d0-d3/a0
.r		rts

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

;======================================================================
; Frames between ticks (with Enhanced framerate and fast memory): on the fields
; between the last tick's frame and this one's, frames interpolated between the two ticks
; (docs/internals.md, "Frames between ticks"). Hooks at the simulation's depth-list stores
; record each entry: its key (from its slot now), the key it had on the last tick (the same
; slot or, right after a removal's move, the last slot's), its bucket, size and place.
; After the simulation the entries are copied by key into this tick's table; the other
; table holds the last tick's. A frame between builds staging lists from the two, points
; the renderer at them with the camera blended, and restores or holds back everything the
; renderer would change in the game state.

K_OBJ		= 768
K_LIGHT		= 896
K_SHIP		= 1023
BV_STS		= 0				;the staging buckets' starts and ends (10 * 8)
BV_STP		= 80				;their write pointers and ends
BV_TMP		= 160				;a blended entry (32)
BV_TAB		= 192				;the game's list tables, saved (160)
BV_GV		= 352				;the game's variables, saved (26)

_pl_between	PL_START
		PL_PSS	$60aa4-CODE_START,_hdot,2	;move.l d4,(a4); movem.w d0-d1,4(a4)
		PL_PS	$60b12-CODE_START,_hdot2	;move.l #$5788a,(a4)
		PL_PSS	$60b48-CODE_START,_hground,2	;move.l d4,(a4); movem.w d0/d5,4(a4)
		PL_PSS	$60bbc-CODE_START,_hshard,2	;lea $673aa(pc),a2; movem.l a2/a5,(a1)
		PL_PSS	$60c1e-CODE_START,_hpmove,4	;movem.w (a3),d0-d6/a4-a5; ...,-14(a6)
		PL_PSS	$625ac-CODE_START,_hobject,2	;lea $673aa(pc),a2; movem.l a2/a5,(a1)
		PL_PSS	$62626-CODE_START,_homove,2	;movem.w (a3),d0-d7/a4-a5; ...,(a6)
		PL_PS	$634dc-CODE_START,_hlight	;move.l #$63982,(a1)
		PL_PS	$64b7e-CODE_START,_rsound	;the renderer's sounds: jsr $58258
		PL_PS	$64ba8-CODE_START,_rsound
		PL_PS	$64cbc-CODE_START,_rsound
		PL_PS	$64cce-CODE_START,_rsound
		PL_PS	$64fca-CODE_START,_rsound
		PL_PS	$6501c-CODE_START,_rsmoke	;its smoke: jsr $6147e
		PL_END

; At install: the tables' places, the tags and marks cleared, the staging buckets.
_btinit		movem.l	d0-d2/a0-a1,-(sp)
		move.l	_fbuf(pc),d1
		sub.l	#FB_OFF,d1		;ExpMem
		lea	_ecur(pc),a1
		move.l	d1,d0
		add.l	#ENT_OFF,d0
		move.l	d0,(a1)+		;_ecur
		add.l	#KEYS*32,d0
		move.l	d0,(a1)+		;_eprv
		move.l	d1,d0
		add.l	#TAG_OFF,d0
		move.l	d0,(a1)+		;_tcur
		add.l	#KEYS*4,d0
		move.l	d0,(a1)+		;_tprv
		move.l	d1,d0
		add.l	#REC_OFF,d0
		move.l	d0,(a1)+		;_rcur
		add.l	#RECS*12,d0
		move.l	d0,(a1)+		;_rprv
		move.l	d0,(a1)+		;_recp
		move.l	d0,(a1)+		;_recend
		move.l	d0,(a1)+		;_rpend: the last tick's list empty
		move.l	d1,d0
		add.l	#USE_OFF,d0
		move.l	d0,(a1)+		;_use
		move.l	d1,d0
		add.l	#GONE_OFF,d0
		move.l	d0,(a1)+		;_gone
		move.l	d1,d0
		add.l	#BTV_OFF,d0
		move.l	d0,(a1)+		;_btv
		move.l	d1,a0
		add.l	#TAG_OFF,a0
		move.w	#(BT_END-TAG_OFF)/4-1,d2
.clr		clr.l	(a0)+
		dbf	d2,.clr
		move.l	d1,d0
		add.l	#STG_OFF,d0
		move.l	_btv(pc),a0
		moveq	#10-1,d2
.bucket		move.l	d0,(a0)+		;BV_STS
		add.l	#BUCKET,d0
		move.l	d0,(a0)+
		dbf	d2,.bucket
		lea	_tick(pc),a0
		move.w	#2,(a0)			;the tags are 0: never the last tick's
		lea	_bt(pc),a0
		st	(a0)
		movem.l	(sp)+,d0-d2/a0-a1
		rts

; Z clear while the pass records. Keeps every register.
_recording	move.l	a0,-(sp)
		lea	_rec(pc),a0
		tst.b	(a0)
		movea.l	(sp)+,a0
		rts

; Records an entry: d0 its key, d1 its key on the last tick (-1: none), d2 its bucket,
; d3 its size, a0 the entry. Keeps every register.
_record		movem.l	a1-a2,-(sp)
		lea	_recp(pc),a1
		movea.l	(a1),a2
		cmpa.l	_recend(pc),a2
		bcc.b	.full
		move.w	d0,(a2)+
		move.w	d1,(a2)+
		move.w	d2,(a2)+
		move.w	d3,(a2)+
		move.l	a0,(a2)+
		move.l	a2,(a1)
.full		movem.l	(sp)+,a1-a2
		rts

; The keys of particle slot d7, part d1 (0 the dot or shard, 1 the ground dot): d0 now,
; d1 on the last tick (-1: none).
_pkey		movem.l	d2/a0,-(sp)
		move.w	d7,d0
		add.w	d0,d0
		add.w	d1,d0
		move.w	d7,d2
		cmp.w	_pmd(pc),d2
		bne.b	.own
		move.w	_pmo(pc),d2		;moved here this tick from the last slot
		bra.b	.key
.own		move.l	_gone(pc),a0
		add.w	d2,d2
		move.w	(a0,d2.w),d2
		cmp.w	_tick(pc),d2
		beq.b	.none			;its record was moved away this tick
		move.w	d7,d2
.key		add.w	d2,d2
		add.w	d2,d1
		bra.b	.done
.none		moveq	#-1,d1
.done		movem.l	(sp)+,d2/a0
		rts

; The keys of the object in hand ($c9f2) from d1 (K_OBJ, K_LIGHT): d0 now, d1 on the last
; tick (-1: none).
_okey		movem.l	d2/a0,-(sp)
		move.l	_pc9ec(pc),a0
		move.w	$c9f2-$c9ec(a0),d2
		move.w	d2,d0
		add.w	d1,d0
		cmp.w	_omd(pc),d2
		bne.b	.own
		move.w	_omo(pc),d2
		bra.b	.key
.own		move.l	_gone(pc),a0
		lea	384*2(a0),a0
		add.w	d2,d2
		move.w	(a0,d2.w),d2
		cmp.w	_tick(pc),d2
		beq.b	.none
		move.l	_pc9ec(pc),a0
		move.w	$c9f2-$c9ec(a0),d2
.key		add.w	d2,d1
		bra.b	.done
.none		moveq	#-1,d1
.done		movem.l	(sp)+,d2/a0
		rts

; A particle's dot ($60aa4, $60b12): d7 its slot, d6 the bucket, a4 the entry.
_hdot		move.l	d4,(a4)
		movem.w	d0-d1,4(a4)
_pdot		bsr.w	_recording
		beq.b	.r
		movem.l	d0-d3/a0,-(sp)
		moveq	#0,d1
		bsr.w	_pkey
		move.w	d6,d2
		moveq	#8,d3
		movea.l	a4,a0
		bsr.w	_record
		movem.l	(sp)+,d0-d3/a0
.r		rts

_hdot2		move.l	d0,-(sp)
		move.l	#$5788a,d0		;the dot of a dot and its ground dot
		add.l	_delta(pc),d0
		move.l	d0,(a4)
		move.l	(sp)+,d0
		bra.b	_pdot

; Its ground dot ($60b48).
_hground	move.l	d4,(a4)
		movem.w	d0/d5,4(a4)
		bsr.w	_recording
		beq.b	.r
		movem.l	d0-d3/a0,-(sp)
		moveq	#1,d1
		bsr.w	_pkey
		move.w	d6,d2
		moveq	#8,d3
		movea.l	a4,a0
		bsr.w	_record
		movem.l	(sp)+,d0-d3/a0
.r		rts

; A shard ($60bbc): d7 its slot, d5 the bucket, a1 the entry.
_hshard		move.l	#$673aa,a2		;the object drawer
		add.l	_delta(pc),a2
		movem.l	a2/a5,(a1)
		bsr.w	_recording
		beq.b	.r
		movem.l	d0-d3/a0,-(sp)
		moveq	#0,d1
		bsr.w	_pkey
		move.w	d5,d2
		moveq	#32,d3
		movea.l	a1,a0
		bsr.w	_record
		movem.l	(sp)+,d0-d3/a0
.r		rts

; An object ($625ac): $c9f2 its slot, d5 the bucket, a1 the entry.
_hobject	move.l	#$673aa,a2
		add.l	_delta(pc),a2
		movem.l	a2/a5,(a1)
		bsr.w	_recording
		beq.b	.r
		movem.l	d0-d3/a0,-(sp)
		move.w	#K_OBJ,d1
		bsr.w	_okey
		move.w	d5,d2
		moveq	#32,d3
		movea.l	a1,a0
		bsr.w	_record
		movem.l	(sp)+,d0-d3/a0
.r		rts

; The attractor's lightning ($634dc): its object's slot, d6 the bucket, a1 the entry.
_hlight		move.l	d0,-(sp)
		move.l	#$63982,d0		;its plotter
		add.l	_delta(pc),d0
		move.l	d0,(a1)
		move.l	(sp)+,d0
		bsr.w	_recording
		beq.b	.r
		movem.l	d0-d3/a0,-(sp)
		move.w	#K_LIGHT,d1
		bsr.w	_okey
		move.w	d6,d2
		moveq	#16,d3
		movea.l	a1,a0
		bsr.w	_record
		movem.l	(sp)+,d0-d3/a0
.r		rts

; A particle's removal ($60c1e): the last record (a3) into the freed slot d7, handled next.
_hpmove		movem.w	(a3),d0-d6/a4-a5
		movem.w	d0-d6/a4-a5,-14(a6)
		movem.l	d0/a0-a1,-(sp)
		move.l	_pc9ec(pc),a1
		lea	_pmd(pc),a0
		move.w	d7,(a0)+		;this slot's entries are now the last slot's
		move.w	(a1),d0			;the last slot: the count now
		move.w	d0,(a0)			;_pmo
		move.l	_gone(pc),a0
		add.w	d0,d0
		move.w	_tick(pc),(a0,d0.w)	;nothing left there
		movem.l	(sp)+,d0/a0-a1
		rts

; An object's removal ($62626): the last record into the slot in hand ($c9f2).
_homove		movem.w	(a3),d0-d7/a4-a5
		movem.w	d0-d7/a4-a5,(a6)
		movem.l	d0/a0-a1,-(sp)
		move.l	_pc9ec(pc),a1
		lea	_omd(pc),a0
		move.w	$c9f2-$c9ec(a1),(a0)+
		move.w	$c9ee-$c9ec(a1),d0
		move.w	d0,(a0)			;_omo
		move.l	_gone(pc),a0
		lea	384*2(a0),a0
		add.w	d0,d0
		move.w	_tick(pc),(a0,d0.w)
		movem.l	(sp)+,d0/a0-a1
		rts

; The pass's start: this tick's table becomes the last tick's, recording starts.
_btbegin	move.l	a0,-(sp)
		lea	_bt(pc),a0
		tst.b	(a0)
		movea.l	(sp)+,a0
		beq.b	.r
		movem.l	d0/a0-a1,-(sp)
		lea	_ecur(pc),a0
		move.l	(a0),d0			;the entries
		move.l	4(a0),(a0)
		move.l	d0,4(a0)
		move.l	8(a0),d0		;their tags
		move.l	12(a0),8(a0)
		move.l	d0,12(a0)
		move.l	24(a0),32(a0)		;_rpend: the last tick's list's end
		move.l	16(a0),d0		;the records
		move.l	20(a0),16(a0)
		move.l	d0,20(a0)
		move.l	16(a0),d0
		move.l	d0,24(a0)		;_recp
		add.l	#RECS*12,d0
		move.l	d0,28(a0)		;_recend
		lea	_camc(pc),a0
		lea	_camp(pc),a1
		move.l	(a0)+,(a1)+
		move.w	(a0),(a1)
		lea	_okcur(pc),a0
		move.b	(a0),1(a0)		;_okprv
		sf	(a0)
		st	2(a0)			;_rec
		lea	_tick(pc),a0
		addq.w	#1,(a0)+
		move.w	#-1,(a0)+		;_pmd: no move yet
		addq.l	#2,a0
		move.w	#-1,(a0)		;_omd
		movem.l	(sp)+,d0/a0-a1
.r		rts

; After the simulation: the entries copied by key into this tick's table, with the camera.
_btcapture	movem.l	d0-d4/a0-a3,-(sp)
		lea	_rec(pc),a0
		tst.b	(a0)
		beq.w	.done			;not a whole tick (the death sequence ran)
		sf	(a0)
		movea.l	_rcur(pc),a2
		movea.l	_recp(pc),a3
		move.w	_tick(pc),d4
.rec		cmpa.l	a3,a2
		bcc.b	.cam
		movem.w	(a2)+,d0-d3		;key, last key, bucket, size
		movea.l	(a2)+,a0
		move.w	d0,d1
		lsl.w	#5,d1
		movea.l	_ecur(pc),a1
		adda.w	d1,a1
		move.w	d3,d1
		lsr.w	#2,d1
		subq.w	#1,d1
.copy		move.l	(a0)+,(a1)+
		dbf	d1,.copy
		movea.l	_tcur(pc),a1
		add.w	d0,d0
		add.w	d0,d0
		adda.w	d0,a1
		move.w	d4,(a1)+		;the tick
		move.b	d3,(a1)+		;the size
		move.b	d2,(a1)			;the bucket
		bra.b	.rec
.cam		move.l	_gv(pc),a0
		lea	$107e-$1000(a0),a0
		lea	_camc(pc),a1
		move.l	(a0)+,(a1)+
		move.w	(a0),(a1)
		lea	_okcur(pc),a0
		st	(a0)
.done		movem.l	(sp)+,d0-d4/a0-a3
		rts

; Before the renderer of a pass that draws: frame k = 1 to P-1 at alpha k/P, each while
; its field (the tick's field plus k-1) has not gone, when the last pass recorded a tick.
_btframes	movem.l	d0-d7/a0-a6,-(sp)
		move.b	_bt(pc),d0
		beq.w	.done
		move.b	_okprv(pc),d0
		beq.w	.done
		move.l	_period(pc),d6
		moveq	#1,d7
.frame		cmp.l	d6,d7
		bcc.w	.done
		move.l	_fields(pc),d0
		sub.l	_due(pc),d0
		add.l	d6,d0			;fields since this tick was due
		cmp.l	d7,d0
		bcc.b	.next
		move.l	d7,d0
		swap	d0
		lsr.l	#1,d0
		divu.w	d6,d0
		move.w	d0,d5			;alpha in 1/32768
		move.w	d7,d0
		add.w	d0,d0
		cmp.w	d6,d0
		scc	d4			;nearer this tick (alpha >= 1/2)
	IFD	BTCHECK
		moveq	#0,d5			;the check build: alpha 0, the last tick's frame
		sf	d4
	ENDC
		bsr.w	_btbuild
		bsr.w	_btrender
		bsr.w	_bttext
		lea	_frames(pc),a0
		addq.l	#1,(a0)+
		addq.l	#1,(a0)			;_bframes
		bsr.w	_show
		bsr.w	_request
.next		addq.l	#1,d7
		bra.b	.frame
.done		movem.l	(sp)+,d0-d7/a0-a6
		rts

; In the death sequence's passes from 16 on, on the last life, the game draws its text
; after the renderer ($2b4be-$2b4e3): a frame between draws it too.
_bttext		move.b	_dpass(pc),d0
		beq.b	.no
		move.l	_pc9ec(pc),a0
		cmp.w	#1,$ca02-$c9ec(a0)	;the lives
		bne.b	.no
		cmp.w	#16,$c9f6-$c9ec(a0)	;the pass count
		blt.b	.no
		move.l	#$66d7a,a0		;the text
		add.l	_delta(pc),a0
		GCALL	$58cc6
.no		rts

; a + (b - a) * alpha: (a1)+ the last tick's word, (a2)+ this tick's, to (a3)+; d5 alpha.
BLENDW		MACRO
		move.w	(a1)+,d0
		move.w	(a2)+,d1
		sub.w	d0,d1
		muls.w	d5,d1
		add.l	d1,d1
		swap	d1
		add.w	d1,d0
		move.w	d0,(a3)+
		ENDM

; The staging lists at alpha d5, nearer this tick if d4: the pairs blended, the unpaired
; as on the nearer tick.
_btbuild	movem.l	d0-d7/a0-a6,-(sp)
		move.l	_btv(pc),a0
		lea	BV_STP(a0),a1
		moveq	#20-1,d0
.init		move.l	(a0)+,(a1)+
		dbf	d0,.init
		move.w	_tick(pc),d7
		subq.w	#1,d7			;the last tick
		movea.l	_rcur(pc),a4
.cur		cmpa.l	_recp(pc),a4
		bcc.w	.last
		movem.w	(a4)+,d0-d3		;key, last key, bucket, size
		addq.l	#4,a4
		movea.l	_ecur(pc),a2
		move.w	d0,d6
		lsl.w	#5,d6
		adda.w	d6,a2			;its entry now
		tst.w	d1
		bmi.b	.alone
		movea.l	_tprv(pc),a1
		move.w	d1,d6
		add.w	d6,d6
		add.w	d6,d6
		adda.w	d6,a1
		cmp.w	(a1)+,d7		;made on the last tick,
		bne.b	.alone
		cmp.b	(a1)+,d3		;the same size
		bne.b	.alone
		moveq	#0,d6
		move.b	(a1),d6			;its bucket then
		movea.l	_use(pc),a1
		move.w	d1,d0
		add.w	d0,d0
		move.w	_tick(pc),(a1,d0.w)	;paired
		movea.l	_eprv(pc),a1
		lsl.w	#5,d1
		adda.w	d1,a1			;its entry on the last tick
		tst.b	d4
		bne.b	.blend
		move.w	d6,d2
.blend		bsr.w	_blend
		bra.b	.cur
.alone		tst.b	d4
		beq.b	.cur			;new: from the frames nearer this tick
		movea.l	a2,a0
		bsr.w	_append
		bra.b	.cur
.last		tst.b	d4
		bne.b	.done
		movea.l	_rprv(pc),a4		;nearer the last tick: its unpaired ones
		move.w	_tick(pc),d7
.prv		cmpa.l	_rpend(pc),a4
		bcc.b	.done
		movem.w	(a4)+,d0-d3
		addq.l	#4,a4
		movea.l	_use(pc),a1
		move.w	d0,d6
		add.w	d6,d6
		cmp.w	(a1,d6.w),d7
		beq.b	.prv
		movea.l	_eprv(pc),a0
		lsl.w	#5,d0
		adda.w	d0,a0
		bsr.w	_append
		bra.b	.prv
.done		movem.l	(sp)+,d0-d7/a0-a6
		rts

; Appends the entry a0 of d3 bytes to staging bucket d2 (its offset, 8 a bucket), if it
; fits. Keeps every register.
_append		movem.l	d0/a0-a3,-(sp)
		move.l	_btv(pc),a1
		lea	BV_STP(a1,d2.w),a1
		movea.l	(a1),a2
		lea	(a2,d3.w),a3
		cmpa.l	4(a1),a3
		bhi.b	.full
		move.l	a3,(a1)
		move.w	d3,d0
		lsr.w	#2,d0
		subq.w	#1,d0
.copy		move.l	(a0)+,(a2)+
		dbf	d0,.copy
.full		movem.l	(sp)+,d0/a0-a3
		rts

; Blends the last tick's entry a1 with this tick's a2 (d3 bytes) at alpha d5 and appends
; it; d2 the bucket of a dot or the lightning, d4 nearer this tick. A 3D entry's matrix
; is blended unless a word moves more than 16384 (another matrix, not a turn): then the
; nearer one's; its bucket comes from the blended depth, as the writers compute it.
_blend		movem.l	d0-d3/d6/a0-a4,-(sp)
		move.l	_btv(pc),a3
		lea	BV_TMP(a3),a3
		movea.l	a1,a4
		tst.b	d4
		beq.b	.near
		movea.l	a2,a4			;the nearer tick's entry
.near		move.l	(a4),(a3)+		;the plotter
		addq.l	#4,a1
		addq.l	#4,a2
		cmp.w	#16,d3
		beq.w	.light
		bcs.w	.dot
		move.l	4(a4),(a3)+		;the model
		addq.l	#4,a1
		addq.l	#4,a2
		movem.l	a1-a2,-(sp)
		moveq	#9-1,d6
.test		move.w	(a2)+,d0
		sub.w	(a1)+,d0
		bpl.b	.abs
		neg.w	d0
.abs		cmp.w	#16384,d0
		bhi.b	.other
		dbf	d6,.test
		movem.l	(sp)+,a1-a2
		moveq	#9-1,d6
.mat		BLENDW
		dbf	d6,.mat
		bra.b	.xyz
.other		movem.l	(sp)+,a1-a2
		lea	8(a4),a4
		moveq	#9-1,d6
.copy		move.w	(a4)+,(a3)+
		dbf	d6,.copy
		lea	18(a1),a1
		lea	18(a2),a2
.xyz		BLENDW
		BLENDW
		BLENDW
		move.w	-2(a3),d2		;the depth
		sub.w	#2304,d2
		asr.w	#5,d2
		and.w	#-8,d2
		cmp.w	#80,d2
		bcs.b	.add
		tst.w	d2
		bmi.b	.near0
		moveq	#72,d2
		bra.b	.add
.near0		moveq	#0,d2
		bra.b	.add
.light		moveq	#6-1,d6
.lw		BLENDW
		dbf	d6,.lw
		bra.b	.add
.dot		BLENDW
		BLENDW
.add		move.l	_btv(pc),a0
		lea	BV_TMP(a0),a0
		bsr.w	_append
		movem.l	(sp)+,d0-d3/d6/a0-a4
		rts

; A frame between at alpha d5: the renderer on the staging lists at the blended camera and
; the nearer tick's counter (d4: this tick's); the game's list tables, camera, counter, RNG,
; radar list ends, the ship's terrain contact and the fuel warning's latch restored after
; it; its sounds and smoke held back (_inb).
_btrender	movem.l	d0-d7/a0-a6,-(sp)
		move.l	#$64d94,a0		;the write pointers and ends, then the starts
		add.l	_delta(pc),a0
		move.l	_btv(pc),a4
		lea	BV_TAB(a4),a1
		moveq	#40-1,d0
.save		move.l	(a0)+,(a1)+
		dbf	d0,.save
		lea	-160(a0),a0
		lea	BV_STP(a4),a1
		moveq	#20-1,d0
.stp		move.l	(a1)+,(a0)+		;the staging lists'
		dbf	d0,.stp
		lea	BV_STS(a4),a1
		moveq	#20-1,d0
.sts		move.l	(a1)+,(a0)+
		dbf	d0,.sts
		move.l	_gv(pc),a5
		lea	$101a-$1000(a5),a0	;the RNG, the radar list's ends
		lea	BV_GV(a4),a1
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		lea	$107e-$1000(a5),a0	;the camera
		move.l	(a0)+,(a1)+
		move.w	(a0),(a1)+
		move.l	_p3ca0f(pc),a0
		move.b	(a0),(a1)+		;the ship's terrain contact
		move.b	$3ca17-$3ca0f(a0),(a1)+	;the fuel warning's latch
		move.l	_pc9ec(pc),a0
		move.w	$c9f4-$c9ec(a0),(a1)+	;the counter
		lea	_camp(pc),a1
		lea	_camc(pc),a2
		lea	$107e-$1000(a5),a3
		BLENDW
		BLENDW
		BLENDW
		move.l	_pc9ec(pc),a0
		tst.b	d4
		bne.b	.count
		subq.w	#1,$c9f4-$c9ec(a0)	;the counter: the nearer tick's (its blinks)
.count		lea	_inb(pc),a0
		st	(a0)
		GCALL	$65174			;the renderer
		lea	_inb(pc),a0
		sf	(a0)
		move.l	#$64d94,a0
		add.l	_delta(pc),a0
		move.l	_btv(pc),a4
		lea	BV_TAB(a4),a1
		moveq	#40-1,d0
.rtab		move.l	(a1)+,(a0)+
		dbf	d0,.rtab
		move.l	_gv(pc),a5
		lea	$101a-$1000(a5),a0
		lea	BV_GV(a4),a1
		move.l	(a1)+,(a0)+
		move.l	(a1)+,(a0)+
		move.l	(a1)+,(a0)+
		move.l	(a1)+,(a0)+
		lea	$107e-$1000(a5),a0
		move.l	(a1)+,(a0)+
		move.w	(a1)+,(a0)
		move.l	_p3ca0f(pc),a0
		move.b	(a1)+,(a0)
		move.b	(a1)+,$3ca17-$3ca0f(a0)
		move.l	_pc9ec(pc),a0
		move.w	(a1)+,$c9f4-$c9ec(a0)
		movem.l	(sp)+,d0-d7/a0-a6
		rts

; The renderer's sound starts and smoke, held back in a frame between.
_rsound		bsr.b	_inbetween
		bne.b	.no
		GJMP	$58258
.no		rts

_rsmoke		bsr.b	_inbetween
		bne.b	.no
		GJMP	$6147e
.no		rts

; Z clear in a frame between. Keeps every register.
_inbetween	move.l	a0,-(sp)
		lea	_inb(pc),a0
		tst.b	(a0)
		movea.l	(sp)+,a0
		rts

_ecur		dc.l	0			;the entries by key: this tick's,
_eprv		dc.l	0			;the last tick's
_tcur		dc.l	0			;their tags
_tprv		dc.l	0
_rcur		dc.l	0			;the records: this tick's,
_rprv		dc.l	0			;the last tick's
_recp		dc.l	0			;this tick's next
_recend		dc.l	0			;and its end
_rpend		dc.l	0			;the last tick's end
_use		dc.l	0			;the tick a last tick's entry was paired in
_gone		dc.l	0			;the tick a slot's record was moved away in
_btv		dc.l	0			;BV_
_camp		dc.w	0,0,0			;the camera on the last tick,
_camc		dc.w	0,0,0			;this tick
_tick		dc.w	0			;the ticks recorded
_pmd		dc.w	-1			;the slot a particle moved into this tick,
_pmo		dc.w	0			;the slot it came from
_omd		dc.w	-1			;the same for the objects
_omo		dc.w	0
_okcur		dc.b	0			;this tick's table is a whole tick
_okprv		dc.b	0			;the last tick's
_rec		dc.b	0			;recording
_bt		dc.b	0			;frames between ticks on
_inb		dc.b	0			;in a frame between
_dpass		dc.b	0			;in the death sequence's pass
		even

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
_pc9ec		dc.l	$c9ec			;the particle and object counts, the object in hand
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
_frames		dc.l	0			;these, _bframes and _period from _pass's address)
_bframes	dc.l	0			;of them frames between ticks
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
		dc.w	_p3ca0f-base,_pc9ec-base,0

_resload	dc.l	0
_hiname		dc.b	"Virus.hi",0
		even

		INCLUDE	reloc.i
