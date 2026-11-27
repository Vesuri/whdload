; Enhanced framerate (CUSTOM1, a 68020 or better): 50 frames a second at the game's own
; speed. Addresses are the game's ($500 + image offset).
;
; The game runs one tick per pass of its main loop ($226c: the task list, the state's
; update and draw, ending in the swap $5dc02), and the timing fix holds a tick to three
; fields. Here each tick still runs exactly once, unchanged, but what it draws is recorded
; instead of drawn: every call of the routines the game draws with (the line $435f2, the
; vertical line $43832, the plot $435a0, the horizontal line $43d04, the HUD glyphs $5c5ac
; and $5c5f2 with their colour $5c56a, the clear $3f742, and the pieces of the HUD that
; write the screen themselves, the sites at SmCall). At the swap the presenter draws the recording
; three times, one frame a field: 1/3 and 2/3 of the way from the previous tick's
; recording, then this one exactly. The game's logic, its random numbers and sounds run as
; they did; only the pictures between two ticks are new.
;
; Pairing: each line and plot has a key, unique in its recording: for a model's lines the
; object being drawn ($752) and the line's place in the model's display list, for the
; star field's dots their place in the lattice, else the code address that drew it and how
; many it drew before. It is paired with the op of the same key in the previous recording
; (a hash table). Unpaired ops, and ops that moved more than SM_T pixels (SM_TID for the
; keyed ones), are drawn where they are now.
;
; Screens: the exact frame is drawn into the game's back screen, as the game would have
; drawn it, and becomes its front screen; the in-between frames into one of two more
; (SM_X0, SM_X1: free Chip RAM, the stack moved below them). Each frame is drawn for the
; first field it can make (by the last frame's drawing time) and queued, one at most; the
; VBL server ($1806) shows it from its field. An in-between frame is drawn only if the
; exact frame still makes its field after it: slow frames thin out the in-between frames,
; not the game.
;
; Direct mode: when more than half of the recent ticks are late, the hooks only pass
; through and ticks run as the default runs them, until a direct tick's work and its
; in-between frames would fit again.

SM_OPS		= 1536			; ops per recording
SM_OPSZ		= 16
SM_HASH		= 2048			; hash table entries (a power of two)
SM_T		= 40			; farther than this (pixels) is not interpolated
SM_TID		= 96			; the same for keyed ops (objects, stars)
SM_N		= 3			; fields a tick
SM_MARGIN	= 12			; raster lines added to the last frame's time
SM_LATE		= 128			; more of the recent ticks late than this (of 256, about
					; the last 16 ticks): direct
SM_GO		= 4			; quarters of the tick's fields a smooth tick must fit in
SM_HOLD		= 50			; direct ticks at least, before trying again
SM_KEYS		= 16			; code addresses counted a tick (SmSeq)
SM_X0		= $60000		; the screens for in-between frames: each in one 64 KB
SM_X1		= $67d00		; bank, as the line drawer's address (low word) needs
SM_STACK	= $60000		; the main loop's stack ($70000), below them
SM_VLINE	= $28			; the VBL shows a frame no later than this line
SM_CALLSZ	= 5			; slots of a CALL op
	IFD	VERIFY
SM_TIMING	= 1			; (the costs by op type, sv_tcost)
	ENDC
SM_BANDS	= 25			; the screen's bands of 8 rows (SmRender)
SM_CWORDS	= 4			; words a site's CALL op records (+72)
	IFD	VERIFY
SM_LIVE		= 0			; (recorded too, for SmCheck)
	ELSE
SM_LIVE		= $80000000		; a site's word read as it is
	ENDC
	IFD	SM_ALLSTATES
SM_STATES	= -1			; (to check them all)
	ELSE
SM_STATES	= 1<<$00|1<<$01|1<<$02|1<<$0a ; the game states ($73a) presented smooth
	ENDC

; ExpMem: the two recordings, each its hash table, a next index per op (the hash
; chains), then its ops; a recording's address is its ops'
em_hash		= -SM_HASH*2-SM_OPS*2
em_next		= -SM_OPS*2
em_HDR		= SM_HASH*2+SM_OPS*2
em_RECSIZE	= em_HDR+SM_OPS*SM_OPSZ
em_scr		= 2*em_RECSIZE		; SmRender: 16 bytes an op (SmPrep)
em_cmp		= em_scr+SM_OPS*16	; VERIFY: a screen to compare with (SmPCheck),
em_tick		= em_cmp+32000		; the screen as the tick drew it (SmCheck), and
em_rep		= em_tick+32000		; as replayed, when they differed
	IFD	VERIFY
SM_EXPMEM	= (em_rep+32000+$fff)&-$1000
	ELSE
SM_EXPMEM	= (em_cmp+$fff)&-$1000
	ENDC

; op: +0 type.b (OPF_ flags in bits 5-7), +1 colour.b, +2 key.l (+0..+5 name the op for
; pairing), +6 four words, +14 pair (index into the previous recording, -1 none)
;   LINE   +6 x0 y0 x1 y1 (the line $435f2 draws from the pen to $774, $776)
;   VLINE  +6 x y0 x y1   ($43832: x $774, from $770 to $776)
;   PLOT   +6 x y         ($435a0: d0, d1)
;   HLINE  +6 x0 x1 y     ($43d04: d0, d1, d2)
;   GLYPH  +1 the text colour, +2 the routine (0 $5c5ac, 1 $5c5f2), +4 the character,
;          +6 the screen offset (or the address, OPF_ABS)
;   CLEAR
;   CALL   +2 the registers relative to the screen (bit 0 d0 .. bit 14 a6), +4 d0-d7/a0-a6,
;          +64 the site's entry (SmCall), +68 its trampoline, +72 the words it reads
;          (SM_CWORDS): SM_CALLSZ slots
OPF_ID		= 7			; the key names the thing drawn (SM_TID)
OPF_ABS		= 6			; GLYPH: an address, not a screen offset
OP_TYPE		= $1f
OP_LINE		= 1
OP_VLINE	= 2
OP_PLOT		= 3
OP_HLINE	= 4
OP_GLYPH	= 5
OP_CLEAR	= 6
OP_CALL		= 7

		RSRESET
sv_mem		rs.l	1		; ExpMem (0: no enhanced framerate)
sv_cur		rs.l	1		; the recording being made
sv_prev		rs.l	1		; the previous tick's
sv_ptr		rs.l	1		; next free op
sv_end		rs.l	1		; where SmNew stops (room for a CALL op after it)
sv_b0		rs.l	1		; the game's back screen when the tick began
sv_disp		rs.l	1		; the screen in the copper list
sv_odisp	rs.l	1		; the one before it (on display until sv_shown)
sv_ready	rs.l	1		; the queued frame's screen (0: none; the VBL shows it)
sv_tgt		rs.l	1		; the screen a frame is drawn into
sv_l0		rs.l	1		; the time a direct tick began
sv_jmp		rs.l	1		; SmRender: the trampoline of a CALL op
sv_vret		rs.l	1		; VERIFY: a site's return
sv_regs		rs.l	15		; SmRender: a CALL op's registers
sv_shown	rs.w	1		; the field from which sv_disp is on display
sv_rt		rs.w	1		; the field the queued frame is for
sv_lastt	rs.w	1		; the field of the last frame queued (or skipped)
sv_base		rs.w	1		; B: the field the last tick's exact frame was for
sv_r		rs.w	1		; lines the last frame took to draw, plus SM_MARGIN
sv_ravg		rs.w	1		; frame drawing time, running average (lines x 8)
sv_late		rs.w	1		; share of recent ticks late (256 = all), running average
sv_hold		rs.w	1		; direct ticks before smooth is tried again
sv_state	rs.w	1		; the game state ($73a) of the last recording
sv_tcol		rs.w	1		; the text colour last set ($5c56a)
sv_f		rs.w	1		; SmRender: the step (0..32768)
sv_nkeys	rs.w	1		; SmSeq: code addresses counted this tick
sv_keys		rs.l	2*SM_KEYS	; and they, each with its count
sv_rec		rs.b	1		; recording
sv_ok		rs.b	1		; the previous recording can be paired with
sv_ran		rs.b	1		; the last tick was presented smooth
sv_direct	rs.b	1		; ticks run as the default runs them
sv_slow		rs.b	1		; the late share passed SM_LATE this tick
sv_exact	rs.b	1		; SmRender: the exact frame
sv_ticks	rs.l	1		; statistics (read with the gdb stub):
sv_all		rs.l	1		;  every tick, and the field of the first,
sv_f0		rs.l	1
sv_frames	rs.l	1		;  frames drawn (smooth ticks),
sv_dropped	rs.l	1		;  in-between frames not drawn,
sv_lates	rs.l	1		;  late ticks,
sv_dticks	rs.l	1		;  direct ticks,
sv_maxops	rs.l	1		;  most ops in a tick,
sv_ovf		rs.l	1		;  ticks that ran out of ops,
sv_paired	rs.l	1		;  ops paired, last tick,
sv_unpaired	rs.l	1		;  pairable ops not paired, last tick,
sv_rmax		rs.l	1		;  longest frame (lines),
sv_work		rs.l	1		;  the last direct tick's work (lines),
sv_cmpn		rs.l	1		;  VERIFY: exact replays compared,
sv_cmpbad	rs.l	1		;  of them not the same as the tick drew,
sv_cmpoff	rs.l	1		;  the first differing offset of the last such,
sv_cmpst	rs.l	1		;  and its state and ops
sv_tcost	rs.l	8		;  VERIFY: colour clocks per op type, drawing,
sv_tcnt		rs.l	8		;  and ops drawn per type,
sv_bands	rs.l	1		;  bands drawn,
sv_pcmpn	rs.l	1		;  VERIFY: frames drawn by band compared,
sv_pbad		rs.l	1		;  of them not as drawn whole,
sv_poff		rs.l	1		;  the first differing offset of the last such
sv_bhist	rs.l	SM_BANDS	;  frames each band was drawn in
sv_stn		rs.w	32		;  VERIFY: SmCheck's compared, by state,
sv_stbad	rs.w	32		;  and differing
sv_tsig		rs.l	4*SM_BANDS	; each screen's bands' signatures, as last drawn (the
sv_tclip	rs.l	4		; game's two, SM_X0, SM_X1), and the clip window then
sv_nsig		rs.l	SM_BANDS	; SmRender: this frame's
sv_dirty	rs.l	1		; SmRender: the bands to draw (bit 31: always)
sv_t0		rs.l	1		; SM_TIMING: SmRender's start
sv_tmax		rs.l	1		; and its longest (lines)
sv_cws		rs.w	SM_CWORDS	; SmRender: a site's words, while it is replayed
sv_tok		rs.b	4		; the screen's signatures are valid
sv_full		rs.b	1		; SmRender: the whole screen
sv_part		rs.b	1		; SmRender: by bands (the recording starts clear)
sv_SIZE		rs.b	0

;----------------------------------------------------------------------------
; Install: d0 = ExpMem (or 0). Called before the game starts, when CUSTOM1 is set on a
; 68020 or better.

SmInit		lea	SmV(pc),a0
		move.l	d0,sv_mem(a0)
		beq.b	.out
		add.l	#em_HDR,d0
		move.l	d0,sv_cur(a0)
		move.l	d0,sv_ptr(a0)
		add.l	#em_RECSIZE,d0
		move.l	d0,sv_prev(a0)
		move.w	#SM_MARGIN,sv_r(a0)
		move.w	#$7fff,sv_state(a0)
		move.l	#$70000,sv_disp(a0)
		move.l	#$70000,sv_odisp(a0)
.out		rts

;----------------------------------------------------------------------------
; Tick start, $226c in the main loop: lea $90e.w,a0; move.w (a0)+,d0

SmTick		movem.l	d0-d2/a0-a1,-(sp)
		lea	SmV(pc),a1
		tst.l	sv_mem(a1)
		beq.w	.out
		tst.l	sv_all(a1)		; (statistics)
		bne.b	.c
		move.w	_FixFields(pc),sv_f0+2(a1)
.c		addq.l	#1,sv_all(a1)
		clr.b	sv_rec(a1)
	IFD	SM_DIRECT			; (the baseline: every tick direct)
		st	sv_direct(a1)
		move.w	#SM_HOLD,sv_hold(a1)
	ENDC
		tst.b	sv_direct(a1)
		beq.b	.smooth
.dr		tst.l	sv_ready(a1)		; direct: as the default, once the last
		bne.b	.dr			; frame queued is shown; the time noted
		bsr	SmNow
		move.l	d0,sv_l0(a1)
		bsr	SmInval
		clr.b	sv_ran(a1)
		bra.b	.out
.smooth		move.w	$73a.w,d0		; a state not known to replay right: as
		cmp.w	#32,d0			; the default
		bhs.b	.plain
		move.l	#SM_STATES,d1
		btst	d0,d1
		bne.b	.known
.plain		tst.l	sv_ready(a1)		; (once the last frame queued is shown)
		bne.b	.plain
		clr.b	sv_ran(a1)
		bsr	SmInval
		bra.b	.out
.known		moveq	#0,d2			; the previous recording pairs if it is the
		tst.b	sv_ran(a1)		; same state's, just before
		beq.b	.no
		move.w	$73a.w,d0
		cmp.w	sv_state(a1),d0
		bne.b	.no
		moveq	#1,d2
.no		move.b	d2,sv_ok(a1)
		move.w	$73a.w,sv_state(a1)
		clr.b	sv_ran(a1)
		move.l	sv_cur(a1),a0		; swap the recordings
		move.l	sv_prev(a1),d1
		move.l	a0,sv_prev(a1)
		move.l	d1,sv_cur(a1)
		move.l	d1,sv_ptr(a1)
		add.l	#(SM_OPS-SM_CALLSZ)*SM_OPSZ,d1
		move.l	d1,sv_end(a1)
		move.l	$936.w,sv_b0(a1)
		clr.w	sv_nkeys(a1)
		move.w	#-1,sv_tcol(a1)
		st	sv_rec(a1)
.out		movem.l	(sp)+,d0-d2/a0-a1
		lea	$90e.w,a0		; the original
		move.w	(a0)+,d0
		rts

;----------------------------------------------------------------------------
; Recording

; At a hook: on to \1 (the original) unless this call is recorded: a recording tick,
; drawing into its back screen. All registers kept.
SmRec		MACRO
		move.l	a1,-(sp)
		lea	SmV(pc),a1
		tst.b	sv_rec(a1)
		beq.b	.n\@
		move.l	sv_b0(a1),a1
		cmpa.l	$936.w,a1
		movea.l	(sp)+,a1		; (flags kept)
		beq.b	.y\@
		bsr	SmInval			; drawn elsewhere: perhaps a screen
		bra.w	\1
.n\@		movea.l	(sp)+,a1
		bra.w	\1
.y\@
		ENDM

; The game's screens' contents are no longer what their band signatures say (drawn
; directly). SM_X0 and SM_X1 only the replay draws into.
SmInval		move.l	a1,-(sp)
		lea	SmV+sv_tok(pc),a1
		clr.b	(a1)+
		clr.b	(a1)
		move.l	(sp)+,a1
		rts

; a3: SmV -> d0.w: sv_tgt's screen (0 $70000, 1 $78000, 2 SM_X0, 3 SM_X1)
SmSIdx		move.l	sv_tgt(a3),d0
		cmp.l	#$70000,d0
		beq.b	.0
		cmp.l	#$78000,d0
		beq.b	.1
		cmp.l	#SM_X0,d0
		beq.b	.2
		moveq	#3,d0
		rts
.0		moveq	#0,d0
		rts
.1		moveq	#1,d0
		rts
.2		moveq	#2,d0
		rts

; After recording a call: back to the caller. The VERIFY build also runs the original
; \1, not recording meanwhile, so that the tick draws as the default (SmCheck).
SmDone		MACRO
	IFD	VERIFY
		bsr	SmRecOff
		bsr.w	\1
		bsr	SmRecOn
	ENDC
		rts
		ENDM

	IFD	VERIFY
SmRecOff	move.l	a1,-(sp)
		lea	SmV(pc),a1
		clr.b	sv_rec(a1)
		move.l	(sp)+,a1
		rts
SmRecOn		move.l	a1,-(sp)
		lea	SmV(pc),a1
		st	sv_rec(a1)
		move.l	(sp)+,a1
		rts
	ENDC

; out: a0 = a free op (+0 cleared, no pair), Z clear; Z set when the recording is full.
; d0 trashed.
SmNew		move.l	a1,-(sp)
		lea	SmV(pc),a1
		move.l	sv_ptr(a1),a0
		cmpa.l	sv_end(a1),a0
		bhs.b	.full
		clr.l	(a0)
		move.w	#-1,14(a0)
		lea	SM_OPSZ(a0),a0
		move.l	a0,sv_ptr(a1)
		lea	-SM_OPSZ(a0),a0
		move.l	(sp)+,a1
		moveq	#1,d0			; Z clear
		rts
.full		move.l	(sp)+,a1
		moveq	#0,d0
		rts

; d1.l: a code address -> d1.l: a key, the address and how many ops it recorded before
; this tick (so each is unique). d0/a1 trashed.
SmSeq		lea	SmV+sv_nkeys(pc),a1
		move.w	(a1)+,d0		; a1: sv_keys
		bra.b	.in
.l		cmp.l	(a1),d1
		beq.b	.hit
		addq.l	#8,a1
.in		dbf	d0,.l
		lea	SmV+sv_nkeys(pc),a1	; a new address
		cmp.w	#SM_KEYS,(a1)
		bhs.b	.x			; no room: the address alone
		move.w	(a1),d0
		addq.w	#1,(a1)
		lsl.w	#3,d0
		lea	2(a1,d0.w),a1
		move.l	d1,(a1)+
		clr.l	(a1)
.x		rts
.hit		addq.l	#1,4(a1)
		move.l	4(a1),d0
		ror.l	#8,d0			; the count in the top bits
		ror.l	#4,d0
		eor.l	d0,d1
		rts

; $435f2 the line from the pen ($76e, $770) to $774, $776 in colour $946; the pen moves
; there. The original: move.w $774,$77a
SmLine		SmRec	.run
		movem.l	d0-d1/a0-a1,-(sp)
		bsr	SmNew
		beq.b	.x
		move.b	#OP_LINE,(a0)
		move.b	$947.w,1(a0)
		move.l	16(sp),d1		; the return address
		cmp.l	#$3fab6,d1		; a model's line (the display lists at $3fa7e,
		beq.b	.obj			; $3fae6): the object, and where in its list
		cmp.l	#$3fb34,d1
		beq.b	.obj
		bsr	SmSeq
		bra.b	.key
.obj		bset	#OPF_ID,(a0)
		move.l	8(sp),d1		; a0: the display list
		sub.l	#$3f000,d1
		and.l	#$1ffff,d1
		move.l	$752.w,d0
		and.l	#$3fff,d0
		swap	d0
		add.l	d0,d0
		or.l	d0,d1
.key		move.l	d1,2(a0)
		move.l	$76e.w,6(a0)		; x0 y0
		move.l	$774.w,10(a0)		; x1 y1
.x
	IFND	VERIFY
		move.l	$774.w,d0		; the pen, as the line drawer leaves it
		move.l	d0,$77a.w
		move.l	d0,$76e.w
	ENDC
		movem.l	(sp)+,d0-d1/a0-a1
		SmDone	.run
.run		move.w	$774.w,$77a.w
		jmp	$435f8

; $43832 the vertical line at $774 from $770 to $776 in colour $946, then the pen moves to
; $77a, $77c ($4360a). Reached by jsr (the HUD), from $43826 (which sets $77a, $77c) and
; from the line drawer. The original: move.w $946,d0; cmp.w $940,d0
SmVline		SmRec	.run
		movem.l	d0-d1/a0-a1,-(sp)
		bsr	SmNew
		beq.b	.x
		move.b	#OP_VLINE,(a0)
		move.b	$947.w,1(a0)
		move.l	16(sp),d1
		bsr	SmSeq
		move.l	d1,2(a0)
		move.w	$774.w,6(a0)
		move.w	$770.w,8(a0)
		move.w	$774.w,10(a0)
		move.w	$776.w,12(a0)
.x
	IFND	VERIFY
		move.l	$77a.w,d0		; the pen, as $4360a leaves it
		move.l	d0,$774.w
		move.l	d0,$76e.w
	ENDC
		movem.l	(sp)+,d0-d1/a0-a1
		SmDone	.run
.run		move.w	$946.w,d0
		cmp.w	$940.w,d0
		jmp	$4383a

; $435a0 the plot at d0, d1 in colour $946 (the clipped plot $4358e falls into it). The
; star field's dots ($5c3b4) are keyed by their place in the lattice. The original:
; move.w d0,d4; lea $43b74,a0
SmPlot		SmRec	.run
		movem.l	d0-d2/a0-a1,-(sp)	; the return at 20(sp)
		bsr	SmNew
		beq.b	.x
		move.b	#OP_PLOT,(a0)
		move.b	$947.w,1(a0)
		move.w	2(sp),6(a0)		; d0
		move.w	4+2(sp),8(a0)		; d1
		move.l	20(sp),d1
		cmp.l	#$5c3ba,d1
		beq.b	.star
		bsr	SmSeq
		move.l	d1,2(a0)
		bra.b	.x
.star		bset	#OPF_ID,(a0)		; $5c386 and $5c3a2 pushed the loops' d0-d2/d4
		move.w	$792.w,d0		; (inner, outer). The lattice's cell: the
		bsr.w	.cell			; camera's x and z rounded up to 1024 (as
		sub.w	24+6(sp),d0		; $5c34a builds it), less the loop's count
		and.w	#$3f,d0
		move.w	d0,d2
		move.w	$796.w,d0
		bsr.w	.cell
		sub.w	24+8+6(sp),d0
		and.w	#$3f,d0
		lsl.w	#6,d0
		or.w	d0,d2
		and.l	#$fff,d2
		or.l	#$5c3ba<<12,d2
		move.l	d2,2(a0)
.x		movem.l	(sp)+,d0-d2/a0-a1
		SmDone	.run
.cell		move.w	d0,d1
		neg.w	d1
		and.w	#1023,d1
		add.w	d1,d0
		asr.w	#8,d0
		asr.w	#2,d0
		rts
.run		move.w	d0,d4
		lea	$43b74,a0
		jmp	$435a8

; $43d04 the horizontal line from d0 to d1 at d2 in colour $946. The original:
; cmp.w $136e,d2; bgt.w $43e04
SmHline		SmRec	.run
		movem.l	d0-d2/a0-a1,-(sp)
		bsr	SmNew
		beq.b	.x
		move.b	#OP_HLINE,(a0)
		move.b	$947.w,1(a0)
		move.w	2(sp),6(a0)		; d0
		move.w	4+2(sp),8(a0)		; d1
		move.w	8+2(sp),10(a0)		; d2
		move.l	20(sp),d1
		bsr	SmSeq
		move.l	d1,2(a0)
.x		movem.l	(sp)+,d0-d2/a0-a1
		SmDone	.run
.run		cmp.w	$136e.w,d2		; (the hook covers half of the bgt.w)
		bgt.b	.out
		jmp	$43d0c
.out		jmp	$43e04

; $3f742 the clear of the drawing screen. The original: movea.l #$dff000,a6
SmClear		SmRec	.run
		movem.l	d0/a0,-(sp)
		bsr	SmNew
		beq.b	.x
		move.b	#OP_CLEAR,(a0)
.x		movem.l	(sp)+,d0/a0
		movea.l	#$dff000,a6		; as the clear leaves it
		SmDone	.run
.run		movea.l	#$dff000,a6
		jmp	$3f748

; $5c56a the text colour d0: copies its plane opcodes into the glyph plots. Recording,
; only noted for the glyphs (nothing is drawn). The original:
; movem.l d1/a0-a4,-(sp); lea $43a8c,a4
SmTCol		SmRec	.run
		move.l	a1,-(sp)
		lea	SmV+sv_tcol(pc),a1
		move.w	d0,(a1)
		move.l	(sp)+,a1
		SmDone	.run
.run		movem.l	d1/a0-a4,-(sp)
		lea	$43a8c,a4
		jmp	$5c574

; $5c5ac and $5c5f2 a glyph: the character d0 at a0, in the text colour. The originals
; start with lea $5c658,a1 (the fix: jsr FixDigitStart)
SmGlyph0	SmRec	.run
		movem.l	d0-d1/a0-a1,-(sp)
		moveq	#0,d1
		bsr.w	SmGlyph
		movem.l	(sp)+,d0-d1/a0-a1
		SmDone	.run
.run		bsr	FixDigitStart
		jmp	$5c5b2
SmGlyph1	SmRec	.run
		movem.l	d0-d1/a0-a1,-(sp)
		moveq	#1,d1
		bsr.w	SmGlyph
		movem.l	(sp)+,d0-d1/a0-a1
		SmDone	.run
.run		bsr	FixDigitStart
		jmp	$5c5f8
SmGlyph		bsr	SmNew			; (the saved d0 at 4(sp), a0 at 12(sp))
		beq.b	.x
		move.b	#OP_GLYPH,(a0)
		move.b	SmV+sv_tcol+1(pc),1(a0)
		move.w	d1,2(a0)
		move.w	4+2(sp),4(a0)		; the character
		move.l	4+8(sp),d0		; the address
		sub.l	SmV+sv_b0(pc),d0
		cmp.l	#32000,d0
		blo.b	.rel
		bset	#OPF_ABS,(a0)
		add.l	SmV+sv_b0(pc),d0
.rel		move.l	d0,6(a0)
.x		rts

;----------------------------------------------------------------------------
; The pieces of the HUD that write the screen themselves: recorded with their registers
; and run again in each frame. Each site is drawing only, from there to the rts that
; returns from it (the stack holds that return at the site). Its hook: pea its entry;
; bra.w SmCall. The entry: the rows it draws (first, last; -1: unknown; -2: by the
; routine at last, from the entry: a0 the recorded registers -> d4.l, d5.l), the registers it
; reads (bit 0 d0 .. bit 14 a6), its fixup (from the entry; 0 none: what it does besides
; drawing, done when it is recorded instead of run), the addresses of the words it reads
; (0 ends them; at most SM_CWORDS without SM_LIVE: their values are recorded and put back
; while it is replayed; SM_LIVE: read as they are, the VBL's), then its trampoline (the
; instructions the hook replaced, a jump back).

; (sp): the site's entry, then the site's return
SmCall		movem.l	d0-d7/a0-a6,-(sp)
		move.l	60(sp),a0		; the trampoline, after the words
		move.l	a0,d6
		addq.l	#8,a0
.t		tst.l	(a0)+
		bne.b	.t
		move.l	a0,d7
		move.l	a0,60(sp)
		lea	SmV(pc),a1
		tst.b	sv_rec(a1)
		beq.w	.run
		move.l	$936.w,d1
		cmp.l	sv_b0(a1),d1
		bne.w	.run
		move.l	sv_ptr(a1),a2		; (SmNew leaves room for one)
		cmpa.l	sv_end(a1),a2
		bhi.b	.skip
		lea	SM_CALLSZ*SM_OPSZ(a2),a0
		move.l	a0,sv_ptr(a1)
		move.l	d6,64(a2)		; the entry, the trampoline
		move.l	d7,68(a2)
		move.w	#OP_CALL<<8,(a2)
		lea	4(a2),a3		; the registers, those in the screen relative
		moveq	#0,d2
		moveq	#0,d3
		move.l	sp,a4
		moveq	#15-1,d4
.r		move.l	(a4)+,d0
		move.l	d0,d1
		sub.l	sv_b0(a1),d1
		cmp.l	#32000,d1
		bhs.b	.abs
		bset	d3,d2
		move.l	d1,d0
.abs		move.l	d0,(a3)+
		addq.w	#1,d3
		dbf	d4,.r
		move.w	d2,2(a2)
		move.l	d6,a0			; the words it reads
		addq.l	#8,a0
		lea	72(a2),a3
.w		move.l	(a0)+,d0
		beq.b	.wx
		bmi.b	.w
		move.l	d0,a4
		move.w	(a4),(a3)+
		bra.b	.w
.wx
	IFND	VERIFY
		move.l	d6,a0			; its fixup (the VERIFY build runs it)
		move.w	6(a0),d0
		beq.b	.skip
		jsr	(a0,d0.w)
	ENDC
.skip		movem.l	(sp)+,d0-d7/a0-a6
	IFD	VERIFY
		move.l	a1,-(sp)		; run it too, back here after its rts
		lea	SmV+sv_vret(pc),a1
		move.l	8(sp),(a1)
		lea	.vback(pc),a1
		move.l	a1,8(sp)
		move.l	(sp)+,a1
		bsr	SmRecOff
		rts				; into the trampoline
.vback		bsr	SmRecOn
		move.l	SmV+sv_vret(pc),-(sp)
		rts
	ELSE
		addq.l	#4,sp			; back from the site
		rts
	ENDC
.run		bsr	SmInval			; (drawn directly)
		movem.l	(sp)+,d0-d7/a0-a6
		rts				; into the trampoline

; The sites. The cannons (play, $2b08 and $493b2; and $47f0a at $26bc, $337e, $34c2):
; blits at rows 161 to 199, by the crosshair ($47db6 x, $47db8 y: as they are now, so
; that they follow it as the crosshair does) and $1370.
SmC0		pea	SmS0(pc)
		bra.w	SmCall
SmS0		dc.w	150,199,0,0
		dc.l	$47db6|SM_LIVE,$47db8|SM_LIVE,$1370,0
		move.w	$47db8,d0
		jmp	$47dec
SmC1		pea	SmS1(pc)
		bra.w	SmCall
SmS1		dc.w	150,199,0,0
		dc.l	$47db8|SM_LIVE,0
		move.w	$47db8,d0
		jmp	$47f10

; The shield gauge ($4630a in the task $462ca): rows 0 to 55, by d7 (the hit count down,
; $46252), $74a and $5cf68; with $5cf68 set it also sets the star colour $76a to 6.
SmC2		pea	SmS2(pc)
		bra.w	SmCall
SmS2		dc.w	0,55,1<<7,.fix-SmS2
		dc.l	$74a,$5cf68,$40704,0
		movea.l	$936.w,a0
		adda.w	#16010,a0
		jmp	$46312
.fix		tst.b	$5cf68
		beq.b	.x
		move.w	#6,$76a.w
.x		rts

; The scanner's bars ($494aa, the end of $49438): rows 32 to 58, by $759.
SmC3		pea	SmS3(pc)
		bra.w	SmCall
SmS3		dc.w	32,58,0,0
		dc.l	$758,0
		movea.l	$936.w,a0
		adda.w	#8000,a0
		jmp	$494b2

; The scanner's marks ($5bf90 in $5bf76): rows 35 to 56, by d6, d7 and $5bf74.
SmC4		pea	SmS4(pc)
		bra.w	SmCall
SmS4		dc.w	35,56,1<<6|1<<7,0
		dc.l	$5bf74,0
		move.w	$5bf74,d4
		jmp	$5bf96

; The wave number's big digits ($5b428): rows 4 to 19, by $74c (converted at $5b470,
; which only this reads).
SmC6		pea	SmS6(pc)
		bra.w	SmCall
SmS6		dc.w	4,19,0,0
		dc.l	$74c,0
		movea.l	$936.w,a1
		adda.w	#16190,a1
		jmp	$5b430

; The scanner's bars in the other scenes ($2d04): rows 32 to 51.
SmC7		pea	SmS7(pc)
		bra.w	SmCall
SmS7		dc.w	32,51,0,0
		dc.l	0
		movea.l	$936.w,a0
		adda.w	#8000,a0
		jmp	$2d0c

; The shape blits $470fa (the wave select's, the walkers' scanner marks) and $5c1bc
; (the wave): the shape a0, d4 rows high, at x d0, y d1, into the planes d5.
SmC8		pea	SmS8(pc)
		bra.w	SmCall
SmS8		dc.w	-2,SmBlitRows-SmS8,1<<0|1<<1|1<<4|1<<5|1<<8,0
		dc.l	0
		lea	$43b74,a2
		jmp	$47100
SmC9		pea	SmS9(pc)
		bra.w	SmCall
SmS9		dc.w	-2,SmBlitRows-SmS9,1<<0|1<<1|1<<4|1<<5|1<<8,0
		dc.l	0
		lea	$43b74,a2
		jmp	$5c1c2
SmBlitRows	move.l	#199,d4			; a0: d0-a6 -> d4, d5: rows 199-y to 199-y+h
		move.w	4+2(a0),d5
		ext.l	d5
		sub.l	d5,d4
		move.w	16+2(a0),d5
		ext.l	d5
		add.l	d4,d5
		rts

; The four icons ($5c008): rows 29 to 53, by their states at $5c004. The drawing is
; followed by their animation (at $5c046), so the site is a copy of the drawing only.
SmC5		bsr.b	.s
		jmp	$5c046
.s		pea	SmS5(pc)
		bra.w	SmCall
SmS5		dc.w	29,53,0,0
		dc.l	$5c004,$5c006,0
		lea	$5c004,a4		; $5c008-$5c044
		moveq	#3,d4
		movea.l	$936.w,a2
		adda.w	#9170,a2
		move.w	#40,d5
.l		move.b	(a4)+,d0
		bmi.b	.n
		lea	$5c088,a0
		ext.w	d0
		add.w	d0,d0
		add.w	d0,d0
		movea.l	(a0,d0.w),a0
		movea.l	a2,a1
		moveq	#23,d3
.r		move.w	(a0)+,d0
		or.w	d0,(a1)
		adda.w	d5,a1
		dbf	d3,.r
.n		adda.w	#6,a2
		dbf	d4,.l
		rts

;----------------------------------------------------------------------------
; The swap $5dc02, the end of every tick: jsr $40ac4 (the hit flash, once a tick), the
; frame count, the wait and the bitplane pointers. A recording tick is presented here.

SmSwap		movem.l	d0-d7/a0-a6,-(sp)
		lea	SmV(pc),a3
		btst	#0,sv_rec(a3)
		bne.w	.present
		tst.l	sv_mem(a3)
		beq.b	.orig
		bsr	SmInval			; a frame the game drew (the attract's too)
		tst.b	sv_direct(a3)
		beq.b	.orig
		addq.l	#1,sv_dticks(a3)	; a direct tick: its work decides whether to
		bsr	SmNow			; try smooth again
		sub.l	sv_l0(a3),d0
		bpl.b	.w
		moveq	#0,d0
.w		move.l	d0,sv_work(a3)
		tst.w	sv_hold(a3)
		beq.b	.try
		subq.w	#1,sv_hold(a3)
		bra.b	.orig
.try		moveq	#0,d1			; when the work and an in-between frame fit
		move.w	sv_ravg(a3),d1		; SM_GO/4 of the tick's fields (the frame's
		lsr.w	#3,d1			; time no more than the work, which drew
		cmp.l	d0,d1			; one: the average is the last smooth
		bls.b	.tw			; ticks', perhaps long ago)
		move.l	d0,d1
.tw		add.l	d1,d0
		cmp.l	#SM_N*313*SM_GO/4,d0
		bhs.b	.orig
		clr.b	sv_direct(a3)
.orig		movem.l	(sp)+,d0-d7/a0-a6
		jsr	$40ac4			; the original, back here after its rts
		pea	.swapped(pc)
		jmp	$5dc08
.swapped	movem.l	d0/a3,-(sp)		; its front screen is in the copper list,
		lea	SmV(pc),a3		; shown from the next field
		tst.l	sv_mem(a3)
		beq.b	.sx
		move.l	sv_disp(a3),sv_odisp(a3)
		move.l	$93a.w,sv_disp(a3)
		bsr	SmField
		addq.w	#1,d0
		move.w	d0,sv_shown(a3)
.sx		movem.l	(sp)+,d0/a3
		rts

.present	clr.b	sv_rec(a3)
		addq.l	#1,sv_ticks(a3)
		jsr	$40ac4			; the hit flash, as the swap does (it can
		lea	SmV(pc),a3		; change a3)
		addq.w	#1,$1884.w		; the frames counted
		move.l	sv_ptr(a3),d0		; statistics
		sub.l	sv_cur(a3),d0
		lsr.l	#4,d0
		cmp.l	sv_maxops(a3),d0
		bls.b	.m
		move.l	d0,sv_maxops(a3)
.m		cmp.w	#SM_OPS-2*SM_CALLSZ,d0
		blo.b	.o
		addq.l	#1,sv_ovf(a3)
.o		bsr	SmPair
		bsr	SmHash
	IFD	VERIFY
		bsr	SmCheck
	ENDC
		move.w	sv_late(a3),d1		; late ticks: the share decays by 1/16 a tick
		lsr.w	#4,d1
		sub.w	d1,sv_late(a3)
		bsr	SmField			; B: back in step if late by more than a
		sub.w	sv_base(a3),d0		; frame, or implausibly early
		cmp.w	#SM_N-1,d0
		bgt.b	.lt
		cmp.w	#-6,d0
		bge.b	.ins
		bra.b	.rs
.lt		tst.b	sv_ok(a3)		; (late, unless the state just began)
		beq.b	.rs
		bsr	SmLate
.rs		bsr	SmField
		move.w	d0,sv_lastt(a3)
		subq.w	#1,d0
		move.w	d0,sv_base(a3)
.ins		moveq	#OP_TYPE,d0		; in-between frames only for a recording
		move.l	sv_cur(a3),a0		; that starts with the clear (the others
		and.b	(a0),d0			; draw over what the game's screen holds)
		cmp.b	#OP_CLEAR,d0
		sne	d5
	IFND	SM_ALLSTATES			; (checking them all: the exact frame only,
		tst.b	sv_ok(a3)		; at the game's speed)
		bne.b	.frame
	ENDC
		st	d5
.frame		move.w	sv_r(a3),d0		; j: the first field the frame can make, after
		bsr	SmEta			; its drawing (by the last frame's time) and
		move.w	sv_lastt(a3),d1		; after the frame queued last
		addq.w	#1,d1
		cmp.w	d1,d0
		bpl.b	.e
		move.w	d1,d0
.e		sub.w	sv_base(a3),d0
		cmp.w	#1,d0
		bge.b	.a
		moveq	#1,d0
.a		cmp.w	#SM_N,d0
		ble.b	.b
		moveq	#SM_N,d0
.b		move.w	d0,d6
		cmp.w	#SM_N,d6
		bhs.b	.ex
		tst.b	d5
		bne.b	.xx
		move.w	sv_r(a3),d0		; an in-between frame if the exact frame
		move.w	d0,d1			; still makes its field after it (two frames'
		lsr.w	#2,d1			; time from now and a quarter more: the
		add.w	d1,d0			; recording may have grown since)
		add.w	sv_r(a3),d0
		bsr	SmEta
		sub.w	sv_base(a3),d0
		cmp.w	#SM_N,d0
		bgt.b	.xx
		bsr	SmFreeX			; into one of the extra screens
		tst.l	d0
		bne.b	.in
		move.w	sv_base(a3),d0		; none free: skip this frame
		add.w	d6,d0
		move.w	d0,sv_lastt(a3)
		addq.l	#1,sv_dropped(a3)
		bra.b	.frame
.xx		moveq	#SM_N,d6		; no: the exact frame now
.ex		bsr	SmWaitB0
		move.l	sv_b0(a3),d0
.in		move.l	d0,sv_tgt(a3)
		bsr	SmNow
		move.l	d0,d7
		bsr	SmRender
		bsr	SmNow			; the drawing time in lines
		sub.l	d7,d0
		bpl.b	.r0
		moveq	#0,d0
.r0		cmp.l	#SM_N*313,d0
		bls.b	.rt
		move.l	#SM_N*313,d0
.rt		cmp.l	sv_rmax(a3),d0
		bls.b	.rm
		move.l	d0,sv_rmax(a3)
.rm		move.w	sv_ravg(a3),d1		; average += (this - average) / 8
		lsr.w	#3,d1
		sub.w	d1,sv_ravg(a3)
		add.w	d0,sv_ravg(a3)
		add.w	#SM_MARGIN,d0
		move.w	d0,sv_r(a3)
		addq.l	#1,sv_frames(a3)
	IFD	VERIFY
		bsr	SmPCheck		; (not timed)
	ENDC
.q		tst.l	sv_ready(a3)		; queue it: one frame at most waits
		bne.b	.q
		move.w	sv_base(a3),d4		; its field
		add.w	d6,d4
		cmp.w	#SM_N,d6
		bhs.b	.qe
		bsr	SmField			; an in-between frame that missed its field
		cmp.w	d0,d4			; (it, or the frame before it, took longer
		bgt.b	.qe			; than planned) is dropped: queued, it would
		move.w	d4,sv_lastt(a3)		; hold up the exact frame
		addq.l	#1,sv_dropped(a3)
		bra.w	.frame
.qe		move.w	d4,sv_rt(a3)
		move.w	d4,sv_lastt(a3)
		cmp.w	#SM_N,d6
		blo.b	.qq
		bsr	SmField			; the exact frame misses its field: late
		cmp.w	d0,d4
		bgt.b	.qq
		tst.b	sv_ok(a3)
		beq.b	.qq
		bsr	SmLate
.qq		move.l	sv_tgt(a3),sv_ready(a3)
		cmp.w	#SM_N,d6
		blo.w	.frame
		add.w	#SM_N,sv_base(a3)	; the tick is presented
		move.w	sv_tcol(a3),d0		; the game's glyph opcodes as its tick would
		bmi.b	.tc			; have left them (the replay's glyphs do not
		jsr	$5c56a			; set them)
		lea	SmV(pc),a3
.tc
		st	sv_ran(a3)
		move.l	sv_tgt(a3),d0		; the game's screens as its swap leaves them:
		move.l	d0,$936.w		; the exact frame shown, the other drawn next
		move.w	d0,$93c.w
		eor.w	#$8000,d0
		move.w	d0,$938.w
		lea	_FixLast(pc),a1		; the timing fix counts from the field before
		move.w	sv_base(a3),d0		; the exact frame's
		subq.w	#1,d0
		move.w	d0,(a1)
		tst.b	sv_slow(a3)		; too slow for in-between frames: direct ticks
		beq.b	.out
		clr.b	sv_slow(a3)
		clr.w	sv_late(a3)
	IFND	SM_ALLSTATES			; (checking them all: never)
		st	sv_direct(a3)
	ENDC
		move.w	#SM_HOLD,sv_hold(a3)
.out		movem.l	(sp)+,d0-d7/a0-a6
		rts

; a3: SmV. A late tick.
SmLate		addq.l	#1,sv_lates(a3)
		add.w	#256/16,sv_late(a3)
		cmp.w	#SM_LATE,sv_late(a3)
		bls.b	.x
		st	sv_slow(a3)
.x		rts

; a3: SmV, d0.w: a drawing time (lines) -> d0.w: the first field a frame drawn from now
; for that long can be shown from (the VBL shows it at the field's start)
SmEta		movem.l	d1-d2,-(sp)
		move.w	d0,d2
.a		bsr.w	SmField
		move.w	d0,d1
		bsr.w	SmLine0
		exg	d0,d1			; d0 the field, d1 the line
		move.w	d0,-(sp)
		bsr.w	SmField
		cmp.w	(sp)+,d0
		bne.b	.a
		add.w	d2,d1
		and.l	#$ffff,d1
		divu	#313,d1
		add.w	d1,d0
		addq.w	#1,d0
		movem.l	(sp)+,d1-d2
		rts

; a3: SmV, d0.l: a screen -> Z clear if it is on display, about to be, or queued
SmBusy		movem.l	d1,-(sp)
		cmp.l	sv_ready(a3),d0
		beq.b	.y
		cmp.l	sv_disp(a3),d0
		beq.b	.y
		cmp.l	sv_odisp(a3),d0
		bne.b	.n
		move.l	d0,-(sp)
		bsr.w	SmField
		sub.w	sv_shown(a3),d0
		movem.l	(sp)+,d0		; (flags kept)
		bmi.b	.y
.n		moveq	#0,d1			; Z set: free
		movem.l	(sp)+,d1
		rts
.y		moveq	#1,d1
		movem.l	(sp)+,d1
		rts

; d0.w <- INTENAR; the interrupts off
SmDi		move.w	$dff01c,d0
		move.w	#$4000,$dff09a
		rts
; d0.w: SmDi's INTENAR: the interrupts on again if they were
SmEi		btst	#14,d0
		beq.b	.x
		move.w	#$c000,$dff09a
.x		rts

; a3: SmV -> d0.l: SM_X0 or SM_X1, whichever is neither on display nor queued, waiting
; for the queued frame to be shown if both are; 0 if there is none (one is shown and the
; other queued: a frame skipped, not waited for).
SmFreeX		movem.l	d1-d2,-(sp)
.again		bsr	SmDi			; (no VBL between the tests)
		move.w	d0,d2
		move.l	#SM_X0,d0
		bsr	SmBusy
		beq.b	.ok
		move.l	#SM_X1,d0
		bsr	SmBusy
		beq.b	.ok
		move.w	d2,d0
		bsr	SmEi
		moveq	#0,d0
		bra.b	.x
.ok		move.l	d0,d1
		move.w	d2,d0
		bsr	SmEi
		move.l	d1,d0
.x		movem.l	(sp)+,d1-d2
		rts

; a3: SmV. Waits until the game's back screen (sv_b0) is neither on display nor queued.
SmWaitB0	move.l	d0,-(sp)
.w		move.l	sv_b0(a3),d0
		bsr	SmBusy
		bne.b	.w
		move.l	(sp)+,d0
		rts

; a3: SmV. Waits until no frame is queued (the display is the game's front screen
; then): before the game draws into its back screen itself.
SmDrain		tst.l	sv_ready(a3)
		bne.b	SmDrain
		rts

; $1806 in the VBL server (every register saved): the timing fix's field count, then the
; queued frame shown from its field (or late: at once). Its bitplane pointers go into
; the copper list, which loaded the old ones at line 0, and into BPL1PT-BPL4PT, before
; the display starts; after SM_VLINE only into the copper list, shown from the next field.
SmVbl		lea	_FixFields(pc),a0
		addq.w	#1,(a0)
		lea	SmV(pc),a3
		move.l	sv_ready(a3),d1
		beq.b	.x
		move.w	(a0),d0
		sub.w	sv_rt(a3),d0
		bpl.b	.show
		cmp.w	#-6,d0			; (implausibly far ahead)
		bge.b	.x
.show		clr.l	sv_ready(a3)
		move.l	sv_disp(a3),sv_odisp(a3)
		move.l	d1,sv_disp(a3)
		move.w	(a0),d2			; on display from this field, or the next
		bsr.w	SmLine0
		cmp.w	#SM_VLINE,d0
		bhi.b	.late
		lea	$dff0e0,a1
		move.l	d1,d0
		move.l	d0,(a1)+
		add.l	#8000,d0
		move.l	d0,(a1)+
		add.l	#8000,d0
		move.l	d0,(a1)+
		add.l	#8000,d0
		move.l	d0,(a1)
		bra.b	.cop
.late		addq.w	#1,d2
.cop		move.w	d2,sv_shown(a3)
		move.w	#8000,d0		; as the swap writes them
		move.w	d1,$1bca.w
		add.w	d0,d1
		move.w	d1,$1bd2.w
		add.w	d0,d1
		move.w	d1,$1bda.w
		add.w	d0,d1
		move.w	d1,$1be2.w
		swap	d1
		move.w	d1,$1bc6.w
		move.w	d1,$1bce.w
		move.w	d1,$1bd6.w
		move.w	d1,$1bde.w
.x		jmp	$52690			; the original call, returns to the VBL server

; d0.w: this field: the timing fix's count, plus one while the VBL server has not
; counted it yet (VERTB pending)
SmField		move.l	d1,-(sp)
.a		move.w	_FixFields(pc),d0
		move.w	$dff01e,d1
		cmp.w	_FixFields(pc),d0
		bne.b	.a
		btst	#5,d1
		beq.b	.x
		addq.w	#1,d0
.x		move.l	(sp)+,d1
		rts

; d0.w: the beam's line, read until two reads agree
SmLine0		move.l	d1,-(sp)
.a		move.l	$dff004,d0
		lsr.l	#8,d0
		and.w	#$1ff,d0
		move.l	$dff004,d1
		lsr.l	#8,d1
		and.w	#$1ff,d1
		cmp.w	d1,d0
		bne.b	.a
		move.l	(sp)+,d1
		rts

; d0.l: the time in lines (field * 313 + line; for differences)
SmNow		move.l	d1,-(sp)
.a		bsr.w	SmField
		move.w	d0,d1
		bsr.w	SmLine0
		exg	d0,d1
		move.w	d0,-(sp)
		bsr.w	SmField
		cmp.w	(sp)+,d0
		bne.b	.a
		and.l	#$ffff,d0
		mulu	#313,d0
		and.l	#$ffff,d1
		add.l	d1,d0
		move.l	(sp)+,d1
		rts

;----------------------------------------------------------------------------
; Pairing

; d0.l: a key -> d0.w: its hash's offset in the table; \1 trashed
SmH		MACRO
		move.l	d0,\1
		swap	\1
		eor.w	\1,d0
		move.w	d0,\1
		lsr.w	#7,\1
		eor.w	\1,d0
		and.w	#SM_HASH-1,d0
		add.w	d0,d0
		ENDM

; a3: SmV. Pairs each line and plot of the current recording with the op of the same
; name in the previous one (its hash table), unless it moved too far.
SmPair		move.l	sv_cur(a3),a0
		move.l	sv_ptr(a3),a2
		moveq	#0,d5			; paired
		moveq	#0,d6			; not
		tst.b	sv_ok(a3)
		beq.w	.done
		move.l	sv_prev(a3),a4
		lea	em_hash(a4),a5
		lea	em_next(a4),a6
.loop		cmp.l	a2,a0
		bhs.w	.done
		moveq	#OP_TYPE,d0
		and.b	(a0),d0
		cmp.b	#OP_CALL,d0
		beq.w	.call
		cmp.b	#OP_HLINE,d0
		bhi.w	.next
		move.l	2(a0),d0
		SmH	d1
		moveq	#0,d1
		move.w	(a5,d0.w),d1		; index + 1
.chain		beq.b	.none
		subq.w	#1,d1
		move.l	d1,d2
		lsl.l	#4,d2
		lea	(a4,d2.l),a1
		move.l	2(a1),d0
		cmp.l	2(a0),d0
		bne.b	.n
		move.w	(a1),d0
		cmp.w	(a0),d0
		beq.b	.hit
.n		add.w	d1,d1
		move.w	(a6,d1.w),d1
		bra.b	.chain
.hit		moveq	#SM_T,d3		; how far it may have moved
		btst	#OPF_ID,(a0)
		beq.b	.t
		moveq	#SM_TID,d3
.t		moveq	#4-1,d4
		addq.l	#6,a1
		move.l	a0,d2
		addq.l	#6,a0
.c		move.w	(a0)+,d0
		sub.w	(a1)+,d0
		bvs.b	.far
		bpl.b	.p
		neg.w	d0
.p		cmp.w	d3,d0
		bgt.b	.far
		dbf	d4,.c
		move.l	d2,a0
		move.w	d1,14(a0)
		addq.l	#1,d5
		bra.b	.next
.far		move.l	d2,a0
.none		addq.l	#1,d6
.next		lea	SM_OPSZ(a0),a0
		bra.w	.loop
.call		lea	SM_CALLSZ*SM_OPSZ(a0),a0
		bra.w	.loop
.done		move.l	d5,sv_paired(a3)
		move.l	d6,sv_unpaired(a3)
		rts

; a3: SmV. The current recording's hash table, for the next tick's pairing.
SmHash		move.l	sv_cur(a3),a4
		lea	em_hash(a4),a5
		lea	em_next(a4),a6
		move.l	a5,a0			; cleared
		move.w	#SM_HASH/2-1,d0
		moveq	#0,d1
.clr		move.l	d1,(a0)+
		dbf	d0,.clr
		move.l	a4,a0
		move.l	sv_ptr(a3),a2
		moveq	#0,d2			; the op's index
.loop		cmp.l	a2,a0
		bhs.b	.done
		moveq	#OP_TYPE,d0
		and.b	(a0),d0
		cmp.b	#OP_CALL,d0
		beq.b	.call
		cmp.b	#OP_HLINE,d0
		bhi.b	.next
		move.l	2(a0),d0
		SmH	d1
		move.w	(a5,d0.w),d1		; the chain: this op first
		move.w	d2,d3
		add.w	d3,d3
		move.w	d1,(a6,d3.w)
		move.w	d2,d1
		addq.w	#1,d1
		move.w	d1,(a5,d0.w)
.next		lea	SM_OPSZ(a0),a0
		addq.w	#1,d2
		bra.b	.loop
.call		lea	SM_CALLSZ*SM_OPSZ(a0),a0
		addq.w	#SM_CALLSZ,d2
		bra.b	.loop
.done		rts

;----------------------------------------------------------------------------
; Drawing

; a3: SmV, d6.w: the frame (1..SM_N). Draws the current recording into sv_tgt, d6/SM_N of
; the way from the previous recording's (SM_N: exactly). Not recording: the hooks run the
; game's routines.
;
; By bands: a recording that starts with the clear is drawn only where the frame differs
; from what sv_tgt shows. Each band of 8 rows has a signature, of the ops drawn in it
; (their coordinates as drawn, in order); the bands whose signature is not the one sv_tgt
; was last drawn with are cleared and their ops drawn again. An op drawn draws all its
; bands, so all of them are drawn (SmPrep).
SmRender	movem.l	d0-d7/a0-a6,-(sp)
		move.l	$936.w,-(sp)		; what the replay changes, restored after
		move.l	$76e.w,-(sp)
		move.l	$774.w,-(sp)
		move.l	$77a.w,-(sp)
		move.w	$946.w,-(sp)
	IFD	SM_TIMING
		bsr	SmNow			; (slot 4: all of it, in lines)
		move.l	d0,sv_t0(a3)
	ENDC
		move.l	sv_tgt(a3),$936.w
		cmp.w	#SM_N,d6
		seq	sv_exact(a3)
		move.l	#32768,d0
		mulu	d6,d0
		divu	#SM_N,d0
		move.w	d0,sv_f(a3)
	IFD	SM_TIMING
		bsr	SmCC
		move.l	d0,-(sp)
	ENDC
		bsr	SmPrep
	IFD	SM_TIMING
		moveq	#0,d1			; (slot 0: SmPrep)
		bsr	SmCost
	ENDC
		move.l	d7,sv_dirty(a3)
		tst.b	sv_part(a3)
		beq.b	.d
	IFD	SM_TIMING
		bsr	SmCC
		move.l	d0,-(sp)
	ENDC
		bsr	SmBClr
	IFD	SM_TIMING
		moveq	#OP_CLEAR,d1		; (the clear's slot: SmBClr)
		bsr	SmCost
	ENDC
.d		move.l	sv_cur(a3),a5
		move.l	sv_mem(a3),a1
		add.l	#em_scr,a1
.loop		cmpa.l	sv_ptr(a3),a5
		bhs.w	.done
		moveq	#OP_TYPE,d0
		and.b	(a5),d0
		lea	SM_OPSZ(a5),a4		; the next op
		cmp.b	#OP_CALL,d0
		bne.b	.o
		lea	SM_CALLSZ*SM_OPSZ(a5),a4
.o		tst.b	sv_part(a3)
		beq.b	.go
		move.l	12(a1),d1		; by bands: any of its to draw?
		and.l	sv_dirty(a3),d1
		beq.b	.skip
.go
	IFD	SM_TIMING
		move.w	d0,-(sp)
		bsr	SmCC
		move.l	d0,-(sp)
		move.w	4(sp),d0
	ENDC
		add.w	d0,d0
		move.w	.tab(pc,d0.w),d0
		movem.l	a1/a3-a5,-(sp)
		jsr	.tab(pc,d0.w)
		movem.l	(sp)+,a1/a3-a5
	IFD	SM_TIMING
		bsr	SmCC
		sub.l	(sp)+,d0
		bpl.b	.cp
		add.l	#313*227,d0
.cp		move.w	(sp)+,d1
		lsl.w	#2,d1
		lea	sv_tcost(a3),a0
		add.l	d0,(a0,d1.w)
		lea	sv_tcnt(a3),a0
		addq.l	#1,(a0,d1.w)
	ENDC
.skip		move.l	a4,a5
		lea	16(a1),a1
		bra.b	.loop
.tab		dc.w	.nop-.tab,.line-.tab,.vline-.tab,.plot-.tab,.hline-.tab
		dc.w	.glyph-.tab,.clear-.tab,.call-.tab
.nop		rts
.done		bsr	SmSIdx			; what sv_tgt now shows
		lea	sv_tok(a3),a0
		move.b	sv_part(a3),(a0,d0.w)
		beq.b	.r
		bsr	SmClip
		lsl.w	#2,d0
		lea	sv_tclip(a3),a0
		move.l	d1,(a0,d0.w)
		mulu	#SM_BANDS,d0
		lea	sv_tsig(a3),a1
		add.l	d0,a1
		lea	sv_nsig(a3),a0
		moveq	#SM_BANDS-1,d0
.ts		move.l	(a0)+,(a1)+
		dbf	d0,.ts
.r
	IFD	SM_TIMING
		bsr	SmNow
		sub.l	sv_t0(a3),d0
		add.l	d0,sv_tcost+4*OP_HLINE(a3)
		addq.l	#1,sv_tcnt+4*OP_HLINE(a3)
		cmp.l	sv_t0+4(a3),d0		; and the longest
		bls.b	.tm
		move.l	d0,sv_t0+4(a3)
.tm
	ENDC
		move.w	(sp)+,$946.w
		move.l	(sp)+,$77a.w
		move.l	(sp)+,$774.w
		move.l	(sp)+,$76e.w
		move.l	(sp)+,$936.w
		movem.l	(sp)+,d0-d7/a0-a6
		rts

; a1: the op's coordinates (SmPrep)
.line		movem.w	(a1),d0-d3
		move.b	1(a5),$947.w
		move.w	d0,$76e.w
		move.w	d1,$770.w
		move.w	d2,$774.w
		move.w	d3,$776.w
		jmp	$435f2
.vline		movem.w	(a1),d0-d3
		move.b	1(a5),$947.w
		move.w	d0,$774.w
		move.w	d1,$770.w
		move.w	d3,$776.w
		jmp	$43832
.plot		movem.w	(a1),d0-d1
		move.b	1(a5),$947.w
		jmp	$435a0
.hline		movem.w	(a1),d0-d2
		move.b	1(a5),$947.w
		jmp	$43d04
.clear		jmp	$3f742
.glyph		move.l	6(a5),a0
		btst	#OPF_ABS,(a5)
		bne.b	.ga
		add.l	sv_tgt(a3),a0
.ga		move.w	4(a5),d0
		move.b	1(a5),d3
		move.w	2(a5),d1
		bra.w	SmGlyphD
.call		move.l	68(a5),sv_jmp(a3)
		move.w	2(a5),d2		; the registers, those in the screen relative
		lea	4(a5),a0
		lea	sv_regs(a3),a1
		moveq	#0,d3
		moveq	#15-1,d4
.cr		move.l	(a0)+,d0
		btst	d3,d2
		beq.b	.ra
		add.l	sv_tgt(a3),d0
.ra		move.l	d0,(a1)+
		addq.w	#1,d3
		dbf	d4,.cr
		move.l	64(a5),a0		; the words it reads, as recorded (the
		addq.l	#8,a0			; values now kept)
		lea	72(a5),a1
		lea	sv_cws(a3),a4
.cw		move.l	(a0)+,d0
		beq.b	.cg
		bmi.b	.cw
		move.l	d0,a2
		move.w	(a2),(a4)+
		move.w	(a1)+,(a2)
		bra.b	.cw
.cg		move.l	a5,-(sp)
		bsr.b	.cs
		move.l	(sp)+,a5
		lea	SmV(pc),a3
		move.l	64(a5),a0		; and back
		addq.l	#8,a0
		lea	sv_cws(a3),a4
.cb		move.l	(a0)+,d0
		beq.b	.cx
		bmi.b	.cb
		move.l	d0,a2
		move.w	(a4)+,(a2)
		bra.b	.cb
.cx		rts
.cs		move.l	sv_jmp(a3),-(sp)	; the site, back after its rts
		movem.l	sv_regs(a3),d0-d7/a0-a6
		rts				; into its trampoline

; The replay's glyph ($5c5ac, $5c5f2, without their self-modified opcodes): a0 the
; address, d0.w the character, d1.w 0 (at a byte) or 1 (half a byte on), d3.b the text
; colour. A plane whose colour bit is set gets the glyph's pixels set, the others clear
; (the opcodes $5c56a copies from $43a8c). d0-d7/a0-a1 trashed.
SmGlyphD	bsr	FixBlitIdle		; (as FixDigitStart)
		lea	$5c658,a1
		cmp.b	#32,d0
		bne.b	.c
		moveq	#58,d0
.c		sub.b	#48,d0
		ext.w	d0
		lsl.w	#3,d0
		adda.w	d0,a1
		move.l	(a1)+,d4		; the 8 rows
		move.l	(a1),d5
		moveq	#4-1,d7
		tst.w	d1
		bne.w	.h
.p0		lsr.b	#1,d3
		bcc.w	.c0
		move.l	d4,d6
		rol.l	#8,d6
		or.b	d6,(a0)
		rol.l	#8,d6
		or.b	d6,40(a0)
		rol.l	#8,d6
		or.b	d6,80(a0)
		rol.l	#8,d6
		or.b	d6,120(a0)
		move.l	d5,d6
		rol.l	#8,d6
		or.b	d6,160(a0)
		rol.l	#8,d6
		or.b	d6,200(a0)
		rol.l	#8,d6
		or.b	d6,240(a0)
		rol.l	#8,d6
		or.b	d6,280(a0)
		bra.w	.n0
.c0
		move.l	d4,d6
		not.l	d6
		rol.l	#8,d6
		and.b	d6,(a0)
		rol.l	#8,d6
		and.b	d6,40(a0)
		rol.l	#8,d6
		and.b	d6,80(a0)
		rol.l	#8,d6
		and.b	d6,120(a0)
		move.l	d5,d6
		not.l	d6
		rol.l	#8,d6
		and.b	d6,160(a0)
		rol.l	#8,d6
		and.b	d6,200(a0)
		rol.l	#8,d6
		and.b	d6,240(a0)
		rol.l	#8,d6
		and.b	d6,280(a0)
.n0		lea	8000(a0),a0
		dbf	d7,.p0
		rts
.h		move.l	d4,d1			; firsts: the high halves; seconds: the
		lsl.l	#4,d1			; low halves, shifted up
		and.l	#$f0f0f0f0,d1
		move.l	d5,d2
		lsl.l	#4,d2
		and.l	#$f0f0f0f0,d2
		lsr.l	#4,d4
		and.l	#$0f0f0f0f,d4
		lsr.l	#4,d5
		and.l	#$0f0f0f0f,d5
.p1		lsr.b	#1,d3
		bcc.w	.c1
		move.l	d4,d6
		rol.l	#8,d6
		or.b	d6,(a0)
		rol.l	#8,d6
		or.b	d6,40(a0)
		rol.l	#8,d6
		or.b	d6,80(a0)
		rol.l	#8,d6
		or.b	d6,120(a0)
		move.l	d5,d6
		rol.l	#8,d6
		or.b	d6,160(a0)
		rol.l	#8,d6
		or.b	d6,200(a0)
		rol.l	#8,d6
		or.b	d6,240(a0)
		rol.l	#8,d6
		or.b	d6,280(a0)
		move.l	d1,d6
		rol.l	#8,d6
		or.b	d6,1(a0)
		rol.l	#8,d6
		or.b	d6,41(a0)
		rol.l	#8,d6
		or.b	d6,81(a0)
		rol.l	#8,d6
		or.b	d6,121(a0)
		move.l	d2,d6
		rol.l	#8,d6
		or.b	d6,161(a0)
		rol.l	#8,d6
		or.b	d6,201(a0)
		rol.l	#8,d6
		or.b	d6,241(a0)
		rol.l	#8,d6
		or.b	d6,281(a0)
		bra.w	.n1
.c1
		move.l	d4,d6
		not.l	d6
		rol.l	#8,d6
		and.b	d6,(a0)
		rol.l	#8,d6
		and.b	d6,40(a0)
		rol.l	#8,d6
		and.b	d6,80(a0)
		rol.l	#8,d6
		and.b	d6,120(a0)
		move.l	d5,d6
		not.l	d6
		rol.l	#8,d6
		and.b	d6,160(a0)
		rol.l	#8,d6
		and.b	d6,200(a0)
		rol.l	#8,d6
		and.b	d6,240(a0)
		rol.l	#8,d6
		and.b	d6,280(a0)
		move.l	d1,d6
		not.l	d6
		rol.l	#8,d6
		and.b	d6,1(a0)
		rol.l	#8,d6
		and.b	d6,41(a0)
		rol.l	#8,d6
		and.b	d6,81(a0)
		rol.l	#8,d6
		and.b	d6,121(a0)
		move.l	d2,d6
		not.l	d6
		rol.l	#8,d6
		and.b	d6,161(a0)
		rol.l	#8,d6
		and.b	d6,201(a0)
		rol.l	#8,d6
		and.b	d6,241(a0)
		rol.l	#8,d6
		and.b	d6,281(a0)
.n1		lea	8000(a0),a0
		dbf	d7,.p1
		rts

; a3: SmV, d6.w: the frame. SmRender's first pass: each op's coordinates as drawn, 16
; bytes an op at em_scr (+0 four words, +12 the mask of its bands: 0 none, bit 31 always),
; and the bands' signatures (sv_nsig). Out: d7.l the bands to draw (-1: all), sv_part.
SmPrep		lea	sv_nsig(a3),a2
		move.l	a2,a0
		moveq	#SM_BANDS-1,d0
.c		clr.l	(a0)+
		dbf	d0,.c
		move.l	sv_mem(a3),a1
		add.l	#em_scr,a1
		move.l	sv_cur(a3),a5
		sf	sv_part(a3)		; by bands if the clear comes first
		cmpa.l	sv_ptr(a3),a5
		bhs.b	.l
		moveq	#OP_TYPE,d0
		and.b	(a5),d0
		cmp.b	#OP_CLEAR,d0
		seq	sv_part(a3)
.l		cmpa.l	sv_ptr(a3),a5
		bhs.w	.dirty
		moveq	#OP_TYPE,d0
		and.b	(a5),d0
		lea	SM_OPSZ(a5),a4
		cmp.b	#OP_CALL,d0
		bne.b	.o
		lea	SM_CALLSZ*SM_OPSZ(a5),a4
.o		add.w	d0,d0
		move.w	.tab(pc,d0.w),d0
		moveq	#0,d7
		jsr	.tab(pc,d0.w)		; d4.l, d5.l: its first and last row (d7 1:
		bsr.w	.sig			; always drawn, 2: never), d1.l: its hash
		move.l	a4,a5
		lea	16(a1),a1
		bra.b	.l
.tab		dc.w	.nop-.tab,.line-.tab,.vline-.tab,.plot-.tab,.hline-.tab
		dc.w	.glyph-.tab,.clear-.tab,.call-.tab
.clear		cmpa.l	sv_cur(a3),a5		; not first: not by bands
		beq.b	.nop
		sf	sv_part(a3)
.nop		moveq	#2,d7
		rts
.line
.vline		bsr.w	.coords
		movem.w	d0-d3,(a1)
		bra.b	.rows
.plot		bsr.w	.coords
		moveq	#0,d2
		moveq	#0,d3
		movem.w	d0-d3,(a1)
		move.w	d1,d3
		bra.b	.rows
.hline		bsr.w	.coords
		moveq	#0,d3
		movem.w	d0-d3,(a1)
		move.w	d2,d1
		move.w	d2,d3
.rows		ext.l	d1			; the rows: 199 - y
		ext.l	d3
		move.l	#199,d4
		sub.l	d1,d4
		move.l	#199,d5
		sub.l	d3,d5
		cmp.l	d4,d5
		bge.b	.h
		exg	d4,d5
.h		moveq	#0,d1			; the hash: type, colour, coordinates
		move.w	(a5),d1
		ror.l	#7,d1
		move.l	(a1),d2
		eor.l	d2,d1
		ror.l	#7,d1
		move.l	4(a1),d2
		eor.l	d2,d1
		rts
.glyph		move.l	2(a5),(a1)		; the routine, the character, the offset
		move.l	6(a5),4(a1)
		moveq	#1,d7
		btst	#OPF_ABS,(a5)		; (not in the screen: always drawn)
		bne.b	.h
		moveq	#0,d7
		move.l	6(a5),d4		; its 8 rows from the offset's
		divu	#40,d4
		and.l	#$ffff,d4
		divu	#200,d4
		clr.w	d4
		swap	d4
		moveq	#7,d5
		add.l	d4,d5
		bra.b	.h
.call		move.l	64(a5),a0		; the hash: the site, the registers and the
		move.l	a0,d1			; words it reads
		lea	4(a5),a6
		move.w	4(a0),d3
		moveq	#0,d0
.cr		btst	d0,d3
		beq.b	.cq
		rol.l	#5,d1
		move.l	(a6),d2
		eor.l	d2,d1
.cq		addq.l	#4,a6
		addq.w	#1,d0
		cmp.w	#15,d0
		blo.b	.cr
		movem.w	(a0)+,d4-d5		; its rows
		addq.l	#4,a0
		cmp.w	#-2,d4
		bne.b	.cm
		movem.l	a0/a6,-(sp)		; by its registers
		move.l	64(a5),a6
		add.w	d5,a6
		lea	4(a5),a0
		jsr	(a6)
		movem.l	(sp)+,a0/a6
.cm		lea	72(a5),a6
.cwl		move.l	(a0)+,d0
		beq.b	.ce
		rol.l	#5,d1
		tst.l	d0
		bmi.b	.cv
		move.w	(a6)+,d0		; as recorded
		eor.w	d0,d1
		bra.b	.cwl
.cv		and.l	#~SM_LIVE,d0		; as it is
		move.l	a6,-(sp)
		move.l	d0,a6
		move.w	(a6),d0
		eor.w	d0,d1
		move.l	(sp)+,a6
		bra.b	.cwl
.ce		tst.l	d4
		bpl.b	.cx
		moveq	#0,d4			; not known: all
		move.l	#199,d5
.cx		rts

; a1: the op's scratch, a2: sv_nsig, d4/d5/d7, d1: as .tab leaves them
.sig		moveq	#0,d0
		tst.w	d7
		beq.b	.s0
		cmp.w	#1,d7
		bne.b	.sm
		bset	#31,d0
.sm		move.l	d0,12(a1)
		rts
.s0		cmp.l	#199,d4			; on the screen?
		bgt.b	.sm
		tst.l	d5
		bmi.b	.sm
		tst.l	d4
		bpl.b	.s1
		moveq	#0,d4
.s1		cmp.l	#199,d5
		ble.b	.s2
		move.l	#199,d5
.s2		lsr.w	#3,d4			; its bands
		lsr.w	#3,d5
		moveq	#2,d0
		lsl.l	d5,d0
		moveq	#1,d2
		lsl.l	d4,d2
		sub.l	d2,d0
		move.l	d0,12(a1)
		sub.w	d4,d5
		lsl.w	#2,d4
.s3		move.l	(a2,d4.w),d0		; each band's signature: rotated, the op's
		rol.l	#5,d0			; hash added
		eor.l	d1,d0
		move.l	d0,(a2,d4.w)
		addq.w	#4,d4
		dbf	d5,.s3
		rts

.dirty		move.l	a1,a6			; the scratch's end
		moveq	#-1,d7			; all, unless by bands into a screen whose
		tst.b	sv_part(a3)		; bands are known
		beq.w	.x
		tst.b	sv_full(a3)
		bne.w	.x
		bsr	SmClip
		bsr	SmSIdx
		lea	sv_tok(a3),a0
		tst.b	(a0,d0.w)
		beq.w	.x
		lsl.w	#2,d0
		lea	sv_tclip(a3),a1
		add.w	d0,a1
		mulu	#SM_BANDS,d0
		lea	sv_tsig(a3),a0
		add.l	d0,a0
.ts		cmp.l	(a1),d1
		bne.b	.x
		moveq	#0,d7			; the bands whose signature changed
		moveq	#0,d0
.b		cmpm.l	(a0)+,(a2)+
		beq.b	.be
		bset	d0,d7
.be		addq.w	#1,d0
		cmp.w	#SM_BANDS,d0
		blo.b	.b
.cl		moveq	#0,d3			; and all the bands of the ops drawn in them
		move.l	sv_mem(a3),a1
		add.l	#em_scr,a1
.cw		cmpa.l	a6,a1
		bhs.b	.cn
		move.l	12(a1),d0
		move.l	d0,d1
		and.l	d7,d1
		beq.b	.cy
		cmp.l	d0,d1
		beq.b	.cy
		or.l	d0,d7
		moveq	#1,d3
.cy		lea	16(a1),a1
		bra.b	.cw
.cn		tst.w	d3
		bne.b	.cl
		bset	#31,d7			; the ops always drawn
.x		rts

; a3: SmV, a5: an op -> d0-d3: its four words, d6/SM_N of the way from its pair
.coords		movem.w	6(a5),d0-d3
		tst.b	sv_exact(a3)
		bne.b	.cz
		moveq	#0,d4
		move.w	14(a5),d4
		bmi.b	.cz
		lsl.l	#4,d4
		move.l	sv_prev(a3),a0
		lea	6(a0,d4.l),a0
		move.w	sv_f(a3),d5
		bsr.w	.lerp
		exg	d0,d1
		bsr.w	.lerp
		exg	d0,d1
		exg	d0,d2
		bsr.w	.lerp
		exg	d0,d2
		exg	d0,d3
		bsr.w	.lerp
		exg	d0,d3
.cz		rts
.lerp		move.w	(a0)+,d4		; d0 = p + (d0 - p) * f
		sub.w	d4,d0
		muls	d5,d0
		add.l	d0,d0
		swap	d0
		add.w	d4,d0
		rts

; d1.l: the clip window's hash ($1368-$136e: x, y min, x, y max)
SmClip		move.l	d0,-(sp)
		move.l	$1368.w,d1
		rol.l	#7,d1
		move.l	$136c.w,d0
		eor.l	d0,d1
		move.l	(sp)+,d0
		rts

; a3: SmV, d7: the bands to clear in sv_tgt, each run of them by four blits (a plane
; each), as the clear $3f742 blits.
SmBClr		movem.l	d0-d4/a0/a6,-(sp)
		lea	$dff000,a6
		bsr	FixBlitWaitA6
		move.l	#$01000000,$40(a6)
		move.w	#0,$66(a6)
		moveq	#0,d0
.n		cmp.w	#SM_BANDS,d0
		bhs.w	.x
		btst	d0,d7
		bne.b	.run
		addq.w	#1,d0
		bra.w	.n
.run		move.w	d0,d1			; bands d0 to d1 - 1
.e		addq.w	#1,d1
		cmp.w	#SM_BANDS,d1
		bhs.b	.r
		btst	d1,d7
		bne.b	.e
.r		move.w	d1,d2
		sub.w	d0,d2
		ext.l	d2
		add.l	d2,sv_bands(a3)
		movem.l	d0/d2/a0,-(sp)		; (statistics)
		lsl.w	#2,d0
		lea	sv_bhist(a3),a0
		add.w	d0,a0
		subq.w	#1,d2
.hb		addq.l	#1,(a0)+
		dbf	d2,.hb
		movem.l	(sp)+,d0/d2/a0
		lsl.w	#8,d2			; 8 rows a band, 20 words a row
		add.w	d2,d2
		or.w	#20,d2
		move.w	d0,d3			; 320 bytes a band
		lsl.w	#6,d3
		move.w	d3,d4
		lsl.w	#2,d3
		add.w	d4,d3
		move.l	sv_tgt(a3),a0
		add.w	d3,a0
	IFD	SM_BLITCLR
		moveq	#4-1,d4
.p		bsr	FixBlitWaitA6
		move.l	a0,$54(a6)
		move.w	d2,$58(a6)
		lea	8000(a0),a0
		dbf	d4,.p
	ELSE
		bsr	FixBlitIdle		; by the CPU, 32 bits at a time (the AGA
		movem.l	d0-d1/d5-d7/a1,-(sp)	; blitter writes 16)
		move.w	d1,d4			; bands * 10 blocks of 32 bytes
		sub.w	d0,d4
		mulu	#10,d4
		subq.w	#1,d4
		moveq	#0,d0
		moveq	#0,d1
		moveq	#0,d5
		moveq	#0,d6
		moveq	#4-1,d7
.p		move.l	a0,a1
		move.w	d4,d2
.b		move.l	d0,(a1)+
		move.l	d1,(a1)+
		move.l	d5,(a1)+
		move.l	d6,(a1)+
		move.l	d0,(a1)+
		move.l	d1,(a1)+
		move.l	d5,(a1)+
		move.l	d6,(a1)+
		dbf	d2,.b
		lea	8000(a0),a0
		dbf	d7,.p
		movem.l	(sp)+,d0-d1/d5-d7/a1
	ENDC
		move.w	d1,d0
		bra.w	.n
.x		movem.l	(sp)+,d0-d4/a0/a6
		rts

	IFD	SM_TIMING
; 4(sp): SmCC's time before, d1.w: the slot. Adds the time since to it, pops the time.
SmCost		move.l	d0,-(sp)
		bsr	SmCC
		sub.l	8(sp),d0
		bpl.b	.p
		add.l	#313*227,d0
.p		lsl.w	#2,d1
		movem.l	a0,-(sp)
		lea	SmV+sv_tcost(pc),a0
		add.l	d0,(a0,d1.w)
		lea	SmV+sv_tcnt(pc),a0
		addq.l	#1,(a0,d1.w)
		movem.l	(sp)+,a0
		move.l	(sp)+,d0
		move.l	(sp)+,(sp)		; the return over the time
		rts

; d0.l: the beam in colour clocks (line * 227 + h)
SmCC		move.l	d1,-(sp)
.a		move.l	$dff004,d0
		move.l	$dff004,d1
		eor.l	d0,d1
		and.l	#$1ff00,d1
		bne.b	.a
		move.l	d0,d1
		and.l	#$ff,d1
		lsr.l	#8,d0
		and.l	#$1ff,d0
		mulu	#227,d0
		add.l	d1,d0
		move.l	(sp)+,d1
		rts

	ENDC

	IFD	VERIFY
; a3: SmV. The exact frame replayed into the tick's back screen, which the hooks also
; drew into (SmDone), compared with what they drew.
SmCheck		movem.l	d0-d7/a0-a6,-(sp)
		move.l	sv_b0(a3),a0
		move.l	sv_mem(a3),a1
		add.l	#em_cmp,a1
		move.w	#32000/4-1,d0
.c		move.l	(a0)+,(a1)+
		dbf	d0,.c
		move.l	sv_b0(a3),sv_tgt(a3)
		moveq	#SM_N,d6
		st	sv_full(a3)
		bsr	SmRender
		sf	sv_full(a3)
		bsr	FixBlitIdle
		addq.l	#1,sv_cmpn(a3)
		moveq	#31,d2			; d2: the state's counter's offset
		and.w	$73a.w,d2
		add.w	d2,d2
		lea	sv_stn(a3),a0
		addq.w	#1,(a0,d2.w)
		move.l	sv_b0(a3),a0
		move.l	sv_mem(a3),a1
		add.l	#em_cmp,a1
		move.w	#32000/4-1,d0
.d		cmpm.l	(a0)+,(a1)+
		bne.b	.bad
		dbf	d0,.d
		bra.b	.x
.bad		addq.l	#1,sv_cmpbad(a3)
		lea	sv_stbad(a3),a1
		addq.w	#1,(a1,d2.w)
		subq.l	#4,a0
		sub.l	sv_b0(a3),a0
		move.l	a0,sv_cmpoff(a3)
		move.b	sv_ok(a3),d0		; (pairable, the state, the ops)
		lsl.w	#8,d0
		move.b	$73b.w,d0
		swap	d0
		move.l	sv_ptr(a3),d1
		sub.l	sv_cur(a3),d1
		lsr.l	#4,d1
		move.w	d1,d0
		move.l	d0,sv_cmpst(a3)
		move.l	sv_b0(a3),a0		; the replay kept beside the tick's
		move.l	sv_mem(a3),a1
		add.l	#em_rep,a1
		move.l	sv_mem(a3),a2
		add.l	#em_cmp,a2
		lea	em_tick-em_rep(a1),a4
		move.w	#32000/4-1,d0
.k		move.l	(a0)+,(a1)+
		move.l	(a2)+,(a4)+
		dbf	d0,.k
.x		movem.l	(sp)+,d0-d7/a0-a6
		rts

; a3: SmV, d6: the frame just drawn into sv_tgt. If it was drawn by bands: drawn again
; whole, and compared.
SmPCheck	tst.b	sv_part(a3)
		beq.b	.out
		movem.l	d0/a0-a1,-(sp)
		bsr	FixBlitIdle
		move.l	sv_tgt(a3),a0
		move.l	sv_mem(a3),a1
		add.l	#em_cmp,a1
		move.w	#32000/4-1,d0
.c		move.l	(a0)+,(a1)+
		dbf	d0,.c
		st	sv_full(a3)
		bsr	SmRender
		sf	sv_full(a3)
		bsr	FixBlitIdle
		addq.l	#1,sv_pcmpn(a3)
		move.l	sv_tgt(a3),a0
		move.l	sv_mem(a3),a1
		add.l	#em_cmp,a1
		move.w	#32000/4-1,d0
.d		cmpm.l	(a0)+,(a1)+
		bne.b	.bad
		dbf	d0,.d
		bra.b	.x
.bad		addq.l	#1,sv_pbad(a3)
		subq.l	#4,a0
		sub.l	sv_tgt(a3),a0
		move.l	a0,sv_poff(a3)
.x		movem.l	(sp)+,d0/a0-a1
.out		rts
	ENDC

;----------------------------------------------------------------------------

_PL_Smooth	PL_START
		PL_PS	$226c,SmTick		; lea $90e.w,a0; move.w (a0)+,d0
		PL_P	$5dc02,SmSwap		; jsr $40ac4
		PL_PS	$1806,SmVbl		; jsr $52690 (FixVblCount)
		PL_L	$2258,SM_STACK		; lea $70000,sp
		PL_P	$435f2,SmLine		; move.w $774,$77a
		PL_P	$43832,SmVline		; move.w $946,d0; cmp.w $940,d0
		PL_P	$435a0,SmPlot		; move.w d0,d4; lea $43b74,a0
		PL_P	$43d04,SmHline		; cmp.w $136e,d2; bgt.w $43e04
		PL_P	$3f742,SmClear		; movea.l #$dff000,a6
		PL_P	$5c56a,SmTCol		; movem.l d1/a0-a4,-(sp); lea $43a8c,a4
		PL_P	$5c5ac,SmGlyph0		; (the fix's jsr FixDigitStart)
		PL_P	$5c5f2,SmGlyph1
		PL_P	$47de6,SmC0		; move.w $47db8,d0
		PL_P	$47f0a,SmC1		; move.w $47db8,d0
		PL_P	$4630a,SmC2		; movea.l $936,a0; adda.w #16010,a0
		PL_P	$494aa,SmC3		; movea.l $936,a0; adda.w #8000,a0
		PL_P	$5bf90,SmC4		; move.w $5bf74,d4
		PL_P	$5c008,SmC5		; lea $5c004,a4
		PL_P	$5b428,SmC6		; movea.l $936,a1; adda.w #16190,a1
		PL_P	$2d04,SmC7		; movea.l $936,a0; adda.w #8000,a0
		PL_P	$470fa,SmC8		; lea $43b74,a2
		PL_P	$5c1bc,SmC9		; lea $43b74,a2
		PL_END

SmV		ds.b	sv_SIZE
		EVEN
