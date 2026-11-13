; Enhanced framerate (CUSTOM2): 50 frames a second at the game's own speed (SPS 0403).
;
; The game updates its world once per tick (three fields in the game and the wave
; select, two to four in the attract loops) and draws each tick once. Here each tick
; still runs exactly once, unchanged, but what it draws is recorded instead of drawn:
; every call to the seven routines the game draws with (colour, line, plot, shape,
; rectangle fill, plane copy, screen clear). After the tick the presenter draws the
; recording n times, one frame per field: at j/n of the way from the previous tick's
; recording to this one, then this one exactly. The game logic, its random numbers and
; its sounds run as they did; only the pictures between two ticks are new.
;
; Pairing: each line, plot and shape is keyed by the code address that drew it (and,
; for TIE fighters, by the fighter), and paired with the next op of the same key in
; the previous recording. Unpaired ops, and ops whose coordinates moved more than
; SM_T pixels (a respawn, a star wrapping round), are drawn where they are now.
;
; Pacing: in smooth mode the counter -26430(a4) runs free (one count per field).
; Frames are queued with the field they belong to: frame j of a tick belongs to field
; B+j, B being the field the previous tick's exact frame was for, and the display
; (the hook at $00a0) shows a queued frame no earlier than its field. One frame at most
; is queued. A frame is drawn for the first field it can still make (by the beam
; position and the last frame's drawing time r). An in-between frame is drawn only if
; the exact frame can still make its field after it (2.25 r, checked again after
; waiting for a screen), and is dropped if it misses its field after all, so slow
; frames thin out the in-between frames instead of making the tick late.
;
; Screens: the exact frame is drawn into the game's own back screen, as the game would
; have drawn it; in-between frames into one of two extra Chip RAM screens (when free),
; with the HUD strip of the game's back screen copied first.
;
; Direct mode: when more than half of the recent ticks are late (a tick's exact frame
; misses its field, or the tick starts late), the machine is too slow for in-between
; frames. Then the drawing hooks are taken out again (SmHooks) and ticks run as the
; default runs them, until a direct tick's work plus its in-between frames' drawing
; (the running average frame time) fits SM_GO quarters of the tick's fields (after
; SM_HOLD ticks at least). A 68000 and a stock A1200 stay in direct mode.
;
; Without the recording buffers (CUSTOM2 off, or AllocMem failed) the hooks are never
; installed and the tick and present patches do what the timing fix does.

SM_OPS		= 4096			; ops per recording
SM_OPSZ		= 16
SM_T		= 40			; farther than this (pixels) is not interpolated
SM_W		= 64			; how far ahead pairing searches the previous recording
SM_BUDGET	= 16384			; pairing probes per tick
SM_MARGIN	= 16			; raster lines added to the last frame's time
SM_SCREEN	= 32000			; a screen: four planes of 8000 bytes
SM_CHIPKEEP	= 65536			; Chip RAM left for the game after the third screen
SM_HUDROWS	= 31			; rows the clear ($1c08) leaves: the HUD strip
SM_LATE		= 128			; more of the recent ticks late than this (of 256): direct
SM_GO		= 3			; quarters of the tick's fields a smooth tick must fit in
SM_HOLD		= 50			; direct ticks at least, before trying

; op layout: +0 type.b, +1 flags.b, +2 key.w, +4..+10 four words, +12 long
;   COLOR  +4 colour
;   LINE   +4 x0 y0 x1 y1, +12 pair (index into the previous recording, -1 none)
;   PLOT   +4 x y, +12 pair
;   SHAPE  +4 x y, +8 shape, +12 pair
;   RECT   +4 x0 y0 x1 y1, +12 colour (-26414(a4))
;   COPY   +4 x0 y0 x1 y1, +12 source; the next op (ARG) +12 destination;
;          flags: bits 0/1 source relative to the back/front buffer, bits 2/3 the same
;          for the destination
;   CLEAR
;   STATE  +4 -26412(a4).l (origin x, y), +8 -26398(a4).l (y max, min),
;          +12 -25800(a4).l (x min, max)
;   BUF    +12 the drawing buffer: 0 back, 1 front, else the address
OP_NOP		= 0
OP_COLOR	= 1
OP_LINE		= 2
OP_PLOT		= 3
OP_SHAPE	= 4
OP_RECT		= 5
OP_COPY		= 6
OP_ARG		= 7
OP_CLEAR	= 8
OP_STATE	= 9
OP_BUF		= 10

	RSRESET
sv_buf		rs.l	1		; both recordings (0: smooth mode off)
sv_cur		rs.l	1		; the recording being made
sv_prev		rs.l	1		; the previous tick's
sv_ptr		rs.l	1		; next free op in the current recording
sv_end		rs.l	1		; its end
sv_pend		rs.l	1		; end of the previous recording's ops
sv_b0		rs.l	1		; back and front buffer when the tick began
sv_f0		rs.l	1
sv_vp		rs.l	3		; the viewport last recorded
sv_vbuf		rs.l	1		; the drawing buffer last recorded
sv_tmp		rs.w	4		; interpolated coordinates
sv_obj		rs.w	1		; object key (the TIE fighter being drawn)
sv_r		rs.w	1		; raster lines the last frame took to draw, plus SM_MARGIN
sv_rec		rs.b	1		; recording
sv_ok		rs.b	1		; the previous recording can be paired with
sv_ran		rs.b	1		; the last tick was presented
sv_phase	rs.b	1		; 1 space, 2 surface, 3 trench
sv_maxops	rs.l	1		; VERIFY statistics: most ops in a tick,
sv_ovf		rs.l	1		; ticks that ran out of ops,
sv_ticks	rs.l	1		; ticks presented,
sv_frames	rs.l	1		; frames drawn,
sv_paired	rs.l	1		; ops paired, last tick
sv_unpaired	rs.l	1		; pairable ops not paired, last tick
sv_fields	rs.l	1		; fields between tick starts, summed
sv_first	rs.l	4		; ticks whose first frame was for field 0..3
sv_rl0		rs.l	1		; VERIFY: beam line at the render start
sv_rhist	rs.l	16		; render time histogram, 32-line buckets
sv_rmax		rs.l	1		; longest render (lines)
sv_x		rs.l	2		; the screens for in-between frames (Chip RAM), 0: none
sv_shown	rs.l	1		; the screen on display (0: the game's front, -26446)
sv_ready	rs.l	1		; the queued frame's screen (the VBL hook shows it)
sv_t		rs.w	1		; the field it is for
sv_base		rs.w	1		; B: the field the last tick's exact frame is for
sv_lastt	rs.w	1		; the field of the last frame queued
sv_lastc	rs.w	1		; the counter when the last tick was presented
sv_hudcopies	rs.l	1		; VERIFY: HUD strip copies
sv_direct	rs.b	1		; this machine draws ticks directly (too slow for more)
sv_slow		rs.b	1		; the late share passed SM_LATE this tick
sv_hold		rs.w	1		; direct ticks before smooth is tried again
sv_l0		rs.l	1		; beam line when a direct tick began
sv_work		rs.l	1		; VERIFY: the last direct tick's work (lines)
sv_dticks	rs.l	1		; VERIFY: direct ticks
sv_hooked	rs.b	1		; the drawing hooks are in (SmHooks)
sv_saved	rs.b	1		; the bytes they replace are saved
sv_ravg		rs.w	1		; frame drawing time, running average (lines x 8)
sv_worksum	rs.l	1		; VERIFY: direct ticks' work, summed (lines)
sv_late		rs.w	1		; share of recent ticks late (256 = all), running average
sv_lates	rs.w	1		; VERIFY: late ticks
sv_chipfree	rs.l	1		; largest Chip RAM block when the screens were due (0: not yet)
sv_n		rs.w	1		; fields per tick of the loop being presented (2 or 3)
sv_mul		rs.w	1		; 32768/sv_n: the in-between step
sv_thr		rs.w	1		; its wait threshold (direct ticks)
sv_call		rs.w	1		; and the swap routine it calls then (code-hunk offset)
sv_exact	rs.b	1		; the queued frame is a tick's exact frame
sv_prec		rs.b	1		; sv_rec while the game is paused
sv_cstart	rs.w	1		; the counter at the tick start (relative loops)
sv_rel		rs.b	1		; the loop keeps the counter running (phase 8 on)
sv_pad		rs.b	1
sv_pad2		rs.w	1
sv_dropped	rs.l	1		; VERIFY: in-between frames that missed their field
sv_SIZE		rs.b	0

; the game routine at code-hunk offset \1, called
CALLG	MACRO
	move.l	SmCode(pc),a0
	add.l	#\1,a0
	jsr	(a0)
	ENDM

; continue in the game at code-hunk offset \1 (no register changes)
GOTOG	MACRO
	move.l	SmCode(pc),-(a7)
	add.l	#\1,(a7)
	rts
	ENDM

PLSMOOTH403
	PL_START
	PL_IFC2
	PL_GA	0,SmCode
	PL_PSS	$0066,SmVbl,12		; the VBL server's buffer swap and its clr.w -26448(a4)
	PL_PSS	$00a0,SmBpl,2		; its bitplane pointers: movea.l -26446(a4),a2; move.l a2,224(a3)
	PL_PS	$514a,SmPauseOn	; the pause key: move.l -26442(a4),-4(a5)
	PL_PS	$516c,SmPauseOff	; move.l -4(a5),-26442(a4)
	PL_PSS	$8962,SmTickSpace,2	; clr.w -26430(a4); jsr $8720(pc)
	PL_PSS	$b55e,SmTickSurface,2	; clr.w -26430(a4); jsr $b2f8(pc)
	PL_PSS	$b63a,SmTickSurface,2	; the same
	PL_PSS	$d584,SmTickTrench,2	; clr.w -26430(a4); jsr -32454(a4)
	PL_PSS	$897e,SmPresent3a,8	; the wait (cmpi.w; bge.s; bra.s) and the swap jsr
	PL_PSS	$b612,SmPresent3b,8
	PL_PSS	$b65e,SmPresent3a,8
	PL_PSS	$d5a8,SmPresent3b,8
	; the attract loops: each pass waits for the swap, clears the counter, draws, waits
	; for the counter (1 or 2) and requests a swap, so a pass takes 2 or 3 fields
	PL_PSS	$771e,SmTickText,2	; jsr $09a8; clr.w -26430(a4): the text pages
	PL_PSS	$7734,SmPresent2,8	; cmpi.w #1; bge.s; bra.s; jsr $09c0
	PL_PSS	$393c,SmTickZoom,2	; the title zooming in
	PL_PSS	$3956,SmPresent2,8	; cmpi.w #1
	PL_PSS	$398c,SmTickObiWan,2	; the Obi-Wan text scrolling up
	PL_PSS	$39dc,SmPresent2,8
	PL_PSS	$42ce,SmTickCrawl,2	; the flight instructions
	PL_PSS	$432c,SmPresent3c,8	; cmpi.w #2
	; the loops that keep the counter running: the counter noted at the start, the
	; wait for 1 more (move.w; sub.w; cmp.w #1,d0; bge.s; bra.s) and jsr $09c0
	PL_PSS	$389a,SmTickCredits,4	; the credits (jsr $09a8; move.w -26430(a4),-4(a5))
	PL_PSS	$38c0,SmPresent2,14
	PL_PSS	$43b4,SmTickScoring,4	; the scoring page (... -10(a5))
	PL_PSS	$441c,SmPresent2,14
	PL_PSS	$26f6,SmTickSelect,2	; the wave select loop (jsr $09a8; jsr -32670(a4)),
	PL_PSS	$270c,SmPresentSelect,2	; paced as the fix paces it (jsr $59e6(pc);
					; jsr $09c0)
	PL_ENDIF
	PL_END

; In _bootdos: allocate the recordings when CUSTOM2 is set. a6 is not preserved.
SmAlloc
	lea	SmTags(pc),a0
	move.l	_resload(pc),a2
	jsr	resload_Control(a2)
	move.l	SmTags+4(pc),d0
	beq.b	.out
	move.l	#2*SM_OPS*SM_OPSZ,d0
	moveq	#MEMF_PUBLIC,d1
	move.l	$4.w,a6
	jsr	_LVOAllocMem(a6)
	lea	SmV(pc),a0
	move.l	d0,sv_buf(a0)
	beq.b	.out
	move.l	d0,sv_cur(a0)
	move.l	d0,sv_ptr(a0)
	add.l	#SM_OPS*SM_OPSZ,d0
	move.l	d0,sv_prev(a0)
	move.l	d0,sv_pend(a0)
	move.w	#SM_MARGIN,sv_r(a0)
.out	rts

;----------------------------------------------------------------------------
; Tick start: the loops' clr.w -26430(a4) and the call after it

SmTickSpace
	moveq	#1,d0
	bsr.w	SmBegin
	GOTOG	$8720

SmTickSurface
	moveq	#2,d0
	bsr.w	SmBegin
	GOTOG	$b2f8

SmTickTrench
	moveq	#3,d0
	bsr.w	SmBegin
	jmp	-32454(a4)

; the attract loops' jsr $09a8; clr.w -26430(a4)
SmTickText
	moveq	#4,d0
	bra.b	SmTickA
SmTickZoom
	moveq	#5,d0
	bra.b	SmTickA
SmTickObiWan
	moveq	#6,d0
	bra.b	SmTickA
SmTickCrawl
	moveq	#7,d0
	bra.b	SmTickA
; the loops that keep the counter running: jsr $09a8; move.w -26430(a4),-n(a5)
; (the store only fed the replaced wait)
SmTickCredits
	moveq	#8,d0
	bra.b	SmTickA
SmTickScoring
	moveq	#9,d0
SmTickA	move.l	SmV+sv_buf(pc),d1	; (d0-d1/a0-a1 are free: the jsr took them)
	bne.w	SmBegin			; (a direct tick waits for the swap there)
	move.l	d0,-(a7)
	CALLG	$09a8
	move.l	(a7)+,d0
	bra.w	SmClr
; the wave select loop: jsr $09a8; jsr -32670(a4)
SmTickSelect
	moveq	#10,d0
	bsr.b	SmTickA
	jmp	-32670(a4)

; A direct tick's start, d0.b its phase: the loop's clr.w -26430(a4), or for the loops
; that keep the counter running (phase 8 on) the counter noted in sv_cstart
SmClr	move.l	a0,-(a7)
	lea	SmV(pc),a0
	clr.w	sv_cstart(a0)
	cmp.b	#8,d0
	shs	sv_rel(a0)
	bhs.b	.r
	clr.w	-26430(a4)
	bra.b	.x
.r	move.w	-26430(a4),sv_cstart(a0)
.x	move.l	(a7)+,a0
	rts

; d0.b: phase (1 space, 2 surface, 3 trench, 4-7 the attract loops, 8 on the loops that
; keep the counter running)
SmBegin
	movem.l	d1-d2/a0-a1,-(a7)
	lea	SmV(pc),a1
	tst.l	sv_buf(a1)
	bne.b	.sm
	bsr	SmClr			; (the original; smooth mode lets it run)
	bra.w	.out
.sm	bsr	SmScreens
	tst.l	sv_x(a1)		; no screen for in-between frames: always direct
	beq.b	.dir
	tst.b	sv_direct(a1)
	beq.b	.smooth
.dir
	tst.b	sv_hooked(a1)		; direct: the default's code
	beq.b	.dh
	move.l	d0,-(a7)
	moveq	#0,d0
	bsr	SmHooks
	move.l	(a7)+,d0
.dh	bsr	SmDirectScreen		; a direct tick: as the game, on a screen not shown
	bsr	SmClr
	clr.b	sv_ran(a1)
	move.l	d0,-(a7)
	bsr	SmLineNow
	move.l	d0,sv_l0(a1)
	move.l	(a7)+,d0
	bra.w	.out
.smooth	tst.b	sv_hooked(a1)
	bne.b	.sh
	move.l	d0,-(a7)
	moveq	#1,d0
	bsr	SmHooks
	move.l	(a7)+,d0
.sh	move.w	-26430(a4),d1		; fields since the last tick was presented
	sub.w	sv_lastc(a1),d1
	moveq	#0,d2			; the previous recording pairs if it is the
	tst.b	sv_ran(a1)		; same phase's, just before
	beq.b	.no
	cmp.b	sv_phase(a1),d0
	bne.b	.no
	cmp.w	#6,d1
	bhi.b	.no
	moveq	#1,d2
.no	move.b	d2,sv_ok(a1)
	move.b	d0,sv_phase(a1)
	clr.b	sv_ran(a1)
	move.l	sv_cur(a1),a0		; swap the recordings
	move.l	sv_prev(a1),d1
	move.l	a0,sv_prev(a1)
	move.l	sv_ptr(a1),sv_pend(a1)
	move.l	d1,sv_cur(a1)
	move.l	d1,sv_ptr(a1)
	add.l	#SM_OPS*SM_OPSZ,d1
	move.l	d1,sv_end(a1)
	move.l	-26442(a4),sv_b0(a1)
	move.l	-26446(a4),sv_f0(a1)
	moveq	#-1,d1
	move.l	d1,sv_vbuf(a1)		; record the state with the first op
	st	sv_rec(a1)
.out	movem.l	(a7)+,d1-d2/a0-a1
	rts

; a1: SmV. Before a direct tick: the queued frame shown, then the display follows the
; game's front again.
SmDirectScreen
.r	tst.l	sv_ready(a1)
	bne.b	.r
	clr.l	sv_shown(a1)
.w	tst.w	-26448(a4)
	bne.b	.w
	rts

; a1: SmV. The two screens for in-between frames, allocated the first time if the
; largest Chip RAM block leaves SM_CHIPKEEP after them (one if it leaves that after one).
SmScreens
	tst.l	sv_chipfree(a1)
	bne.b	.x
	movem.l	d0-d1/a0-a1/a6,-(a7)
	move.l	$4.w,a6
	move.l	#MEMF_CHIP|MEMF_LARGEST,d1
	jsr	_LVOAvailMem(a6)
	move.l	12(a7),a1
	move.l	d0,sv_chipfree(a1)
	moveq	#2,d1
	cmp.l	#2*SM_SCREEN+SM_CHIPKEEP,d0
	bhs.b	.al
	moveq	#1,d1
	cmp.l	#SM_SCREEN+SM_CHIPKEEP,d0
	blo.b	.out
.al	lea	sv_x(a1),a0
.l	movem.l	d1/a0,-(a7)
	move.l	#SM_SCREEN,d0
	move.l	#MEMF_CHIP|MEMF_CLEAR,d1
	jsr	_LVOAllocMem(a6)
	movem.l	(a7)+,d1/a0
	move.l	d0,(a0)+
	subq.w	#1,d1
	bne.b	.l
.out	movem.l	(a7)+,d0-d1/a0-a1/a6
.x	rts

; $0066 in the VBL server, reached when the game requested a swap (-26448(a4) set;
; smooth ticks never do): the original swap, and the display follows the game's front
; again. a2 and d0/d1 are free.
SmVbl
	move.l	-26446(a4),a2		; the original: swap shown and drawing screens
	move.l	-26442(a4),-26446(a4)
	move.l	a2,-26442(a4)
	clr.w	-26448(a4)
	lea	SmV(pc),a2
	clr.l	sv_shown(a2)
	clr.l	sv_ready(a2)
	rts

; $00a0 in the VBL server, every field (a3: the custom chips; a0, a2, d0, d1 are free):
; shows the queued frame from its field on, then points the bitplanes at the screen on
; display. Showing a tick's exact frame does what the game's swap path does besides the
; swap ($0078-$009e): a step of the palette fade.
SmBpl
	lea	SmV(pc),a2
	move.l	sv_ready(a2),d0
	beq.b	.s
	move.w	-26430(a4),d1		; this field (the counter counts it after this)
	addq.w	#1,d1
	sub.w	sv_t(a2),d1
	bpl.b	.show
	cmp.w	#-6,d1			; implausibly far ahead (the counter was reset)
	bge.b	.s
.show	move.l	d0,sv_shown(a2)
	clr.l	sv_ready(a2)
	tst.b	sv_exact(a2)
	beq.b	.s
	move.w	-26438(a4),d0		; the fade
	beq.b	.s
	subq.w	#1,-26438(a4)
	muls	-26436(a4),d0
	move.l	-26434(a4),a0
	move.w	d0,(a0)
	move.w	d0,16(a0)
.s	move.l	sv_shown(a2),d0
	bne.b	.p
	move.l	-26446(a4),d0
.p	move.l	d0,a2
	move.l	a2,224(a3)
	rts

; $514a and $516c in the key handler $5124: the pause draws "Game Paused" into the
; front screen and waits for a key. It may come in a tick's logic: drawn, not recorded.
SmPauseOn
	lea	SmV+sv_prec(pc),a0
	move.b	SmV+sv_rec(pc),(a0)
	lea	SmV+sv_rec(pc),a0
	clr.b	(a0)
	move.l	-26442(a4),-4(a5)
	rts
SmPauseOff
	move.l	-4(a5),-26442(a4)
	lea	SmV+sv_rec(pc),a0
	move.b	SmV+sv_prec(pc),(a0)
	rts

; The drawing hooks, installed at run time so that a direct tick runs exactly the
; default build's code: code-hunk offset, the hook (relative to SmHookTab). Each site
; starts with six bytes of whole instructions, which the hook replays.
SmHookTab
	dc.w	$1840,SmColor-SmHookTab		; movem.l d0-d4/a0,-(sp); move.w 28(sp),d4
	dc.w	$19ae,SmLine-SmHookTab		; move.w -25534(a4),d7; bsr.w $18ca
	dc.w	$1b2c,SmPlot-SmHookTab		; (the fix's jmp BlitPlot)
	dc.w	$9806,SmShape-SmHookTab		; link a5,#-32; movem.l d4-d7/a2-a3,-(sp)
	dc.w	$0810,SmRect-SmHookTab		; link a5,#-4; movem.l d4-d7/a2-a3,-(sp)
	dc.w	$0a1c,SmCopy-SmHookTab		; link a5,#-8; movem.l d4-d7/a2,-(sp)
	dc.w	$1c08,SmClear-SmHookTab		; (the fix's jmp BlitClear)
	dc.w	$09a8,SmWaitSwap-SmHookTab	; link a5,#0; jsr $0c3a(pc)
	dc.w	$839c,SmTie-SmHookTab		; link a5,#0; movem.l d4/a2-a3,-(sp)
	dc.w	$09fa,SmReq-SmHookTab		; move.w #-1,-26448(a4) in $09c0
	dc.w	0
SM_HOOKS	= 10
SmHookSave	ds.b	SM_HOOKS*6

; d0: 1 install the hooks (jmp, saving the bytes the first time), 0 restore the bytes
SmHooks
	movem.l	d0-d2/a0-a3,-(a7)
	lea	SmV(pc),a3
	lea	SmHookTab(pc),a0
	lea	SmHookSave(pc),a2
.l	moveq	#0,d1
	move.w	(a0)+,d1
	beq.b	.done
	move.l	SmCode(pc),a1
	add.l	d1,a1
	move.w	(a0)+,d1		; the hook, relative to SmHookTab
	tst.w	d0
	beq.b	.off
	tst.b	sv_saved(a3)
	bne.b	.on
	move.l	(a1),(a2)
	move.w	4(a1),4(a2)
.on	move.w	#$4ef9,(a1)+		; jmp abs.l
	lea	SmHookTab(pc),a3
	add.w	d1,a3
	move.l	a3,(a1)
	lea	SmV(pc),a3
	bra.b	.n
.off	move.l	(a2),(a1)
	move.w	4(a2),4(a1)
.n	addq.l	#6,a2
	bra.b	.l
.done	st	sv_saved(a3)
	move.b	d0,sv_hooked(a3)
	move.l	_resload(pc),a2
	jsr	resload_FlushCache(a2)
	movem.l	(a7)+,d0-d2/a0-a3
	rts

;----------------------------------------------------------------------------
; Recording

; out: a0 = a free op (+0 cleared), Z clear; Z set when the recording is full.
; Records the viewport and the drawing buffer first when they changed.
SmNew
	movem.l	d0/a1,-(a7)
	lea	SmV(pc),a1
	move.l	-26412(a4),d0
	cmp.l	sv_vp(a1),d0
	bne.b	.state
	move.l	-26398(a4),d0
	cmp.l	sv_vp+4(a1),d0
	bne.b	.state
	move.l	-25800(a4),d0
	cmp.l	sv_vp+8(a1),d0
	bne.b	.state
	move.l	-26442(a4),d0
	cmp.l	sv_vbuf(a1),d0
	bne.b	.state
.slot	move.l	sv_ptr(a1),a0
	cmp.l	sv_end(a1),a0
	bhs.b	.full
	clr.l	(a0)
	lea	SM_OPSZ(a0),a0
	move.l	a0,sv_ptr(a1)
	lea	-SM_OPSZ(a0),a0
	moveq	#1,d0			; Z clear
	movem.l	(a7)+,d0/a1
	rts
.full	moveq	#0,d0			; Z set
	movem.l	(a7)+,d0/a1
	rts
.state	move.l	sv_ptr(a1),a0
	lea	3*SM_OPSZ(a0),a0	; room for STATE, BUF and the op
	cmp.l	sv_end(a1),a0
	bhi.b	.full
	lea	-3*SM_OPSZ(a0),a0
	move.l	#OP_STATE<<24,(a0)
	move.l	-26412(a4),d0
	move.l	d0,4(a0)
	move.l	d0,sv_vp(a1)
	move.l	-26398(a4),d0
	move.l	d0,8(a0)
	move.l	d0,sv_vp+4(a1)
	move.l	-25800(a4),d0
	move.l	d0,12(a0)
	move.l	d0,sv_vp+8(a1)
	move.l	#OP_BUF<<24,16(a0)
	move.l	-26442(a4),d0
	move.l	d0,sv_vbuf(a1)
	cmp.l	sv_b0(a1),d0
	bne.b	.nb
	moveq	#0,d0
	bra.b	.sb
.nb	cmp.l	sv_f0(a1),d0
	bne.b	.sb
	moveq	#1,d0
.sb	move.l	d0,28(a0)
	lea	2*SM_OPSZ(a0),a0
	move.l	a0,sv_ptr(a1)
	bra.w	.slot

; d1.l: a return address into the game -> d1.w: its key (code-hunk offset, mixed with
; the object being drawn)
SmKey
	sub.l	SmCode(pc),d1
	move.l	d0,-(a7)
	move.w	SmV+sv_obj(pc),d0
	eor.w	d0,d1
	move.l	(a7)+,d0
	rts

; d0.l: an address -> d0.l: the offset into the back (d1.b = 1) or front (2) buffer
; of the tick, or the address (d1.b = 0)
SmXlate
	moveq	#1,d1
	sub.l	SmV+sv_b0(pc),d0
	cmp.l	#32000,d0
	blo.b	.ok
	add.l	SmV+sv_b0(pc),d0
	moveq	#2,d1
	sub.l	SmV+sv_f0(pc),d0
	cmp.l	#32000,d0
	blo.b	.ok
	add.l	SmV+sv_f0(pc),d0
	moveq	#0,d1
.ok	rts

; $1840 colour (word on the stack)
SmColor
	btst	#0,SmV+sv_rec(pc)
	beq.b	.run
	movem.l	d0-d1/a0-a1,-(a7)
	bsr	SmNew
	beq.b	.x
	move.b	#OP_COLOR,(a0)
	move.w	16+4(a7),4(a0)
.x	movem.l	(a7)+,d0-d1/a0-a1
.run	movem.l	d0-d4/a0,-(a7)
	move.w	28(a7),d4
	GOTOG	$1848

; $19ae the line from (d0,d1) to (d2,d5), the outcode of the start in -25534(a4).
; Reached from $199e (the game's jsr) and $1b06 (bsr, its caller's return 40 bytes
; further up).
SmLine
	btst	#0,SmV+sv_rec(pc)
	bne.b	.rec
	move.w	-25534(a4),d7
	move.l	SmCode(pc),-(a7)	; $18ca returns to $19b6
	add.l	#$19b6,(a7)
	GOTOG	$18ca
.rec	movem.l	d0-d1/a0-a1,-(a7)
	move.l	16(a7),d1
	move.l	d1,a1
	sub.l	SmCode(pc),a1
	cmp.w	#$1b26,a1
	bne.b	.k
	move.l	16+4+36(a7),d1
.k	bsr	SmKey
	bsr	SmNew
	beq.b	.x
	move.b	#OP_LINE,(a0)
	move.w	d1,2(a0)
	move.w	d0,4(a0)
	move.w	6(a7),6(a0)		; d1 as saved
	move.w	d2,8(a0)
	move.w	d5,10(a0)
.x	movem.l	(a7)+,d0-d1/a0-a1
	rts

; $1b2c plot (x, y on the stack); the release fix's blitter wait when drawing
SmPlot
	btst	#0,SmV+sv_rec(pc)
	bne.b	.rec
	BLIT_WAIT
	move.w	d6,-(a7)
	move.w	6(a7),d6
	GOTOG	$1b32
.rec	movem.l	d0-d1/a0-a1,-(a7)
	move.l	16(a7),d1
	bsr	SmKey
	bsr	SmNew
	beq.b	.x
	move.b	#OP_PLOT,(a0)
	move.w	d1,2(a0)
	move.l	16+4(a7),4(a0)
.x	movem.l	(a7)+,d0-d1/a0-a1
	rts

; $9806 shape (x, y, shape on the stack)
SmShape
	btst	#0,SmV+sv_rec(pc)
	bne.b	.rec
	link	a5,#-32
	movem.l	d4-d7/a2-a3,-(a7)
	GOTOG	$980e
.rec	movem.l	d0-d1/a0-a1,-(a7)
	move.l	16(a7),d1
	bsr	SmKey
	bsr	SmNew
	beq.b	.x
	move.b	#OP_SHAPE,(a0)
	move.w	d1,2(a0)
	move.l	16+4(a7),4(a0)
	move.l	16+8(a7),8(a0)
.x	movem.l	(a7)+,d0-d1/a0-a1
	rts

; $0810 rectangle fill (x0, y0, x1, y1 on the stack) in colour -26414(a4)
SmRect
	btst	#0,SmV+sv_rec(pc)
	bne.b	.rec
	link	a5,#-4
	movem.l	d4-d7/a2-a3,-(a7)
	GOTOG	$0818
.rec	movem.l	d0-d1/a0-a1,-(a7)
	bsr	SmNew
	beq.b	.x
	move.b	#OP_RECT,(a0)
	move.l	16+4(a7),4(a0)
	move.l	16+8(a7),8(a0)
	move.w	-26414(a4),12(a0)
.x	movem.l	(a7)+,d0-d1/a0-a1
	rts

; $0a1c plane copy (source, destination, x0, y0, x1, y1 on the stack)
SmCopy
	btst	#0,SmV+sv_rec(pc)
	bne.b	.rec
	link	a5,#-8
	movem.l	d4-d7/a2,-(a7)
	GOTOG	$0a24
.rec	movem.l	d0-d2/a0-a1,-(a7)
	bsr	SmNew
	beq.b	.x
	move.l	a0,a1
	bsr	SmNew
	bne.b	.two
	clr.b	(a1)			; no room for the second: drop it
	bra.b	.x
.two	move.b	#OP_ARG,(a0)
	move.l	20+12(a7),4(a1)		; x0 y0
	move.l	20+16(a7),8(a1)		; x1 y1
	move.l	20+4(a7),d0
	bsr	SmXlate
	move.l	d0,12(a1)
	move.b	d1,d2
	move.l	20+8(a7),d0
	bsr	SmXlate
	move.l	d0,12(a0)
	lsl.b	#2,d1
	or.b	d1,d2
	move.b	d2,1(a1)
	move.b	#OP_COPY,(a1)
.x	movem.l	(a7)+,d0-d2/a0-a1
	rts

; $1c08 screen clear; the release fix's blitter wait when drawing
SmClear
	btst	#0,SmV+sv_rec(pc)
	bne.b	.rec
	BLIT_WAIT
	movem.l	d0-a3/a5,-(a7)
	move.l	-26442(a4),a0
	GOTOG	$1c10
.rec	movem.l	d0/a0,-(a7)
	bsr	SmNew
	beq.b	.x
	move.b	#OP_CLEAR,(a0)
.x	movem.l	(a7)+,d0/a0
	rts

; $09a8 wait for the buffer swap: not while recording (nothing is drawn)
SmWaitSwap
	btst	#0,SmV+sv_rec(pc)
	bne.b	.x
	link	a5,#0
	move.l	SmCode(pc),-(a7)	; $0c3a returns to $09b0
	add.l	#$09b0,(a7)
	GOTOG	$0c3a
.x	rts

; $09fa in $09c0 (jumped to): the swap request, not while recording (the presenter
; queues frames); then on at $0a00 (unlk a5; rts)
SmReq
	btst	#0,SmV+sv_rec(pc)
	bne.b	.x
	move.w	#-1,-26448(a4)
.x	GOTOG	$0a00

; $839c draws the TIE fighter whose record is on the stack: its lines get the
; fighter's key (the low word of its point buffer, 52(record))
SmTie
	move.w	SmV+sv_obj(pc),-(a7)
	move.l	6(a7),a0
	move.w	52+2(a0),d0
	lea	SmV+sv_obj(pc),a0
	move.w	d0,(a0)
	move.l	6(a7),-(a7)
	bsr.b	.draw
	addq.l	#4,a7
	lea	SmV+sv_obj(pc),a0
	move.w	(a7)+,(a0)
	rts
.draw	link	a5,#0
	movem.l	d4/a2-a3,-(a7)
	GOTOG	$83a4

;----------------------------------------------------------------------------
; Presenting: replaces each loop's wait for three fields and its swap

; d0: fields per tick, d1: the loop's threshold, a1: its swap call (d0-d1/a0-a1 are
; free: the jsr they replace may change them)
SmPresent3a
	moveq	#3,d0			; space, surface: jsr $09c0
	moveq	#3,d1
	move.w	#$09c0,a1
	bra.b	SmPresent
SmPresent3b
	moveq	#3,d0			; surface run-in, trench: jsr $0a10
	moveq	#3,d1
	move.w	#$0a10,a1
	bra.b	SmPresent
SmPresent3c
	moveq	#3,d0			; an attract loop waiting for 2: jsr $09c0
	moveq	#2,d1
	move.w	#$09c0,a1
	bra.b	SmPresent
SmPresentSelect
	CALLG	$59e6			; the wave select loop: its cannons and cockpit
	bra.b	SmPresent3c		; (recorded), then paced as the fix paces it
SmPresent2
	moveq	#2,d0			; the attract loops waiting for 1: jsr $09c0
	moveq	#1,d1
	move.w	#$09c0,a1
SmPresent
	movem.l	d0-d7/a0-a6,-(a7)
	lea	SmV(pc),a3
	move.w	d0,sv_n(a3)
	move.w	d1,sv_thr(a3)
	move.w	a1,sv_call(a3)
	move.l	#32768,d1
	divu	d0,d1
	move.w	d1,sv_mul(a3)
	tst.l	sv_buf(a3)
	bne.b	.go0
.wait	move.w	sv_thr(a3),d0		; no recordings: as the loop waits (the timing
.w	move.w	-26430(a4),d1		; fix's thresholds), from the tick start
	sub.w	sv_cstart(a3),d1
	cmp.w	d1,d0
	bgt.b	.w
	moveq	#0,d0
	move.w	sv_call(a3),d0
	add.l	SmCode(pc),d0
	move.l	d0,a0
	jsr	(a0)
	bra.w	.out
; $09c0, the swap request, also does per-tick work (the shield display's countdown
; -26408(a4), which decides when a hit counts; the countdowns -26406 and -26404 and
; what they draw): once per tick as before, recorded, without its request (SmReq).
.go0	tst.b	sv_direct(a3)
	beq.b	.go2
	addq.l	#1,sv_dticks(a3)	; a direct tick: its work in lines decides
	bsr	SmLineNow		; whether to try smooth again
	moveq	#0,d1
	move.w	-26430(a4),d1
	sub.w	sv_cstart(a3),d1
	mulu	#313,d1
	add.l	d0,d1
	sub.l	sv_l0(a3),d1
	move.l	d1,sv_work(a3)
	add.l	d1,sv_worksum(a3)
	tst.w	sv_hold(a3)
	beq.b	.try
	subq.w	#1,sv_hold(a3)
	bra.w	.wait
.try	moveq	#0,d0			; try smooth again when the work and the
	move.w	sv_ravg(a3),d0		; in-between frames' drawing fit SM_GO/4 of
	lsr.w	#3,d0			; the tick's fields: work + (n-1) * frame time
	move.w	sv_n(a3),d2
	subq.w	#1,d2
	mulu	d2,d0
	add.l	d1,d0
	move.w	sv_n(a3),d2
	mulu	#313*SM_GO/4,d2
	cmp.l	d2,d0
	bhs.w	.wait
	clr.b	sv_direct(a3)
	bra.w	.wait
.go2	btst	#0,sv_rec(a3)
	beq.b	.go1
	CALLG	$09c0
.go1	clr.b	sv_rec(a3)
	move.l	sv_ptr(a3),d0		; VERIFY statistics
	sub.l	sv_cur(a3),d0
	lsr.l	#4,d0
	cmp.l	sv_maxops(a3),d0
	bls.b	.m
	move.l	d0,sv_maxops(a3)
.m	cmp.w	#SM_OPS-2,d0
	blo.b	.o
	addq.l	#1,sv_ovf(a3)
.o	addq.l	#1,sv_ticks(a3)
	bsr	SmPair
	move.w	sv_late(a3),d1		; late ticks: the share decays by 1/4 a tick
	lsr.w	#2,d1
	sub.w	d1,sv_late(a3)
	move.w	-26430(a4),d0		; B: back in step if late by more than a frame
	sub.w	sv_base(a3),d0		; or implausibly early (the counter was reset)
	move.w	sv_n(a3),d1
	subq.w	#1,d1
	cmp.w	d1,d0
	bgt.b	.lt
	cmp.w	#-6,d0
	bge.b	.ins
	bra.b	.rs
.lt	tst.b	sv_ok(a3)		; (late, unless the loop just began)
	beq.b	.rs
	add.w	#256/4,sv_late(a3)
	addq.w	#1,sv_lates(a3)
	cmp.w	#SM_LATE,sv_late(a3)
	bls.b	.rs
	st	sv_slow(a3)		; slower than the game: direct ticks from the next
.rs	move.w	-26430(a4),d0
	move.w	d0,sv_lastt(a3)
	subq.w	#1,d0
	move.w	d0,sv_base(a3)
.ins	moveq	#1,d4			; (VERIFY: first frame)
.frame	bsr	SmLineNow		; the first field the frame can make: after the
	move.l	d0,sv_rl0(a3)		; drawing ends (by the last frame's time) and
	add.w	sv_r(a3),d0		; after the frame queued last
	divu	#313,d0
	add.w	-26430(a4),d0
	addq.w	#1,d0
	move.w	sv_lastt(a3),d1
	addq.w	#1,d1
	move.w	d0,d2
	sub.w	d1,d2
	bpl.b	.e
	move.w	d1,d0
.e	sub.w	sv_base(a3),d0		; j
	cmp.w	#1,d0
	bge.b	.a
	moveq	#1,d0
.a	cmp.w	sv_n(a3),d0
	ble.b	.b
	move.w	sv_n(a3),d0
.b	move.w	d0,d6
	cmp.w	sv_n(a3),d6		; the exact frame: into the game's own back
	bhs.b	.ex			; screen, as the game would have drawn it
	move.l	sv_rl0(a3),d0		; an in-between frame only if the exact frame
	add.w	sv_r(a3),d0		; still makes its field after it (two frames'
	add.w	sv_r(a3),d0		; time from now, and a quarter more: the
	move.w	sv_r(a3),d1		; recording may have grown since)
	lsr.w	#2,d1
	add.w	d1,d0
	divu	#313,d0
	add.w	-26430(a4),d0
	addq.w	#1,d0
	sub.w	sv_base(a3),d0
	cmp.w	sv_n(a3),d0
	ble.b	.fx
	move.w	sv_n(a3),d6		; no: the exact frame now
	bra.b	.ex
.fx	bsr	SmFreeX			; in between: one of ours, with the HUD strip
	tst.l	d0			; of the game's back screen
	bne.b	.in
	move.w	sv_base(a3),d0		; none free: skip this frame
	add.w	d6,d0
	move.w	d0,sv_lastt(a3)
	bra.w	.frame
.in	move.l	d0,-26442(a4)
	bsr	SmHudCopy
	bsr	SmLineNow		; again after any wait for the screen and the
	add.w	sv_r(a3),d0		; HUD copy: still time for both?
	add.w	sv_r(a3),d0
	move.w	sv_r(a3),d1
	lsr.w	#2,d1
	add.w	d1,d0
	divu	#313,d0
	add.w	-26430(a4),d0
	addq.w	#1,d0
	sub.w	sv_base(a3),d0
	cmp.w	sv_n(a3),d0
	ble.b	.dr
	move.w	sv_n(a3),d6		; no: the exact frame now (SmWaitB0 sets the
	bra.w	.ex			; game's back screen again)
.ex	bsr	SmWaitB0
.dr	tst.w	d4			; VERIFY: the field of each first frame
	beq.b	.jj
	moveq	#0,d4
	move.w	d6,d0
	cmp.w	#3,d0			; (four counts: 0-3)
	bhi.b	.jj
	add.w	d0,d0
	add.w	d0,d0
	addq.l	#1,sv_first(a3,d0.w)
.jj	bsr	SmLineNow		; the drawing time from here (not the waits)
	move.l	d0,sv_rl0(a3)
	move.w	-26430(a4),d7
	bsr	SmRender
	bsr	SmLineNow		; the drawing time in lines
	move.w	-26430(a4),d1
	sub.w	d7,d1
	mulu	#313,d1
	add.l	d0,d1
	sub.l	sv_rl0(a3),d1
	cmp.l	#3*313,d1
	bls.b	.rt
	move.l	#3*313,d1
.rt	move.w	d1,d0
	add.w	#SM_MARGIN,d0
	move.w	d0,sv_r(a3)
	move.w	sv_ravg(a3),d0		; average += (this - average) / 8
	lsr.w	#3,d0
	sub.w	d0,sv_ravg(a3)
	add.w	d1,sv_ravg(a3)

	cmp.l	sv_rmax(a3),d1		; VERIFY statistics
	bls.b	.rm
	move.l	d1,sv_rmax(a3)
.rm	lsr.l	#5,d1
	cmp.l	#15,d1
	bls.b	.rh
	moveq	#15,d1
.rh	lsl.w	#2,d1
	addq.l	#1,sv_rhist(a3,d1.w)
	addq.l	#1,sv_frames(a3)
.q	tst.l	sv_ready(a3)		; queue it: one frame at most waits
	bne.b	.q
	cmp.w	sv_n(a3),d6		; an in-between frame that missed its field
	bhs.b	.qe			; (it, or the frame queued before it, took
	move.w	sv_base(a3),d0		; longer than planned) is dropped: queued,
	add.w	d6,d0			; it would hold up the exact frame
	cmp.w	-26430(a4),d0
	bgt.b	.qe
	move.w	d0,sv_lastt(a3)
	move.l	sv_b0(a3),-26442(a4)
	addq.l	#1,sv_dropped(a3)
	bra.w	.frame
.qe
	move.w	sv_base(a3),d0
	add.w	d6,d0
	move.w	d0,sv_t(a3)
	move.w	d0,sv_lastt(a3)
	cmp.w	sv_n(a3),d6
	shs	sv_exact(a3)
	blo.b	.qq
	sub.w	-26430(a4),d0		; the exact frame misses its field: late (the
	bgt.b	.qq			; tick shows a field late, the next one early)
	tst.b	sv_ok(a3)
	beq.b	.qq
	add.w	#256/4,sv_late(a3)
	addq.w	#1,sv_lates(a3)
	cmp.w	#SM_LATE,sv_late(a3)
	bls.b	.qq
	st	sv_slow(a3)
.qq	move.l	-26442(a4),sv_ready(a3)
	move.l	sv_b0(a3),-26442(a4)	; the game's back screen again
	cmp.w	sv_n(a3),d6
	blo.w	.frame
	move.l	sv_f0(a3),-26442(a4)	; the exact frame: the game's swap (the display
	move.l	sv_b0(a3),-26446(a4)	; follows at its field)
	move.w	sv_n(a3),d0		; the tick is presented
	add.w	d0,sv_base(a3)
	move.w	-26430(a4),d0
	move.w	d0,d1
	sub.w	sv_lastc(a3),d1		; VERIFY: fields per tick
	cmp.w	#12,d1
	bhi.b	.l
	ext.l	d1
	add.l	d1,sv_fields(a3)
.l	move.w	d0,sv_lastc(a3)
	st	sv_ran(a3)
	tst.b	sv_slow(a3)		; too slow for in-between frames: direct ticks
	beq.b	.out
	clr.b	sv_slow(a3)
	clr.w	sv_late(a3)
	st	sv_direct(a3)
	move.w	#SM_HOLD,sv_hold(a3)
.out	movem.l	(a7)+,d0-d7/a0-a6
	rts

; a3: SmV -> d0: the screen on display
SmOnShow
	move.l	sv_shown(a3),d0
	bne.b	.x
	move.l	-26446(a4),d0
.x	rts

; a3: SmV -> d0.l: one of our screens that is neither on display nor queued, waiting
; for the queued frame to be shown if both are; 0 if there is none.
SmFreeX
	movem.l	d1-d2/a0,-(a7)
.again	lea	sv_x(a3),a0
	moveq	#2-1,d1
	move.w	#$4000,$dff09a		; (no VBL between the tests)
.l	move.l	(a0)+,d2
	beq.b	.n
	cmp.l	sv_ready(a3),d2
	beq.b	.n
	bsr.b	SmOnShow
	cmp.l	d0,d2
	bne.b	.ok
.n	dbf	d1,.l
	move.w	#$c000,$dff09a
	tst.l	sv_ready(a3)
	beq.b	.none
.w	tst.l	sv_ready(a3)
	bne.b	.w
	bra.b	.again
.none	moveq	#0,d0
	bra.b	.x
.ok	move.w	#$c000,$dff09a
	move.l	d2,d0
.x	movem.l	(a7)+,d1-d2/a0
	rts

; a3: SmV. Waits until the game's back screen (sv_b0) is neither on display nor
; queued (while a frame is queued), and makes it the drawing screen.
SmWaitB0
	move.l	d0,-(a7)
.w	move.l	sv_ready(a3),d0
	beq.b	.go
	cmp.l	sv_b0(a3),d0
	beq.b	.w
	bsr.b	SmOnShow
	cmp.l	sv_b0(a3),d0
	beq.b	.w
.go	move.l	sv_b0(a3),-26442(a4)
	move.l	(a7)+,d0
	rts

; a3: SmV. The HUD strip (the top SM_HUDROWS rows, which the clear $1c08 leaves) of
; the game's back screen into the drawing screen: what the game would draw there over.
SmHudCopy
	movem.l	d0-d1/a1-a2,-(a7)
	addq.l	#1,sv_hudcopies(a3)
	move.l	sv_b0(a3),a1
	move.l	-26442(a4),a2
	moveq	#4-1,d1			; planes
.p	move.w	#SM_HUDROWS*40/4-1,d0
	move.l	a1,-(a7)
	move.l	a2,-(a7)
.c	move.l	(a1)+,(a2)+
	dbf	d0,.c
	move.l	(a7)+,a2
	move.l	(a7)+,a1
	lea	8000(a1),a1
	lea	8000(a2),a2
	dbf	d1,.p
	movem.l	(a7)+,d0-d1/a1-a2
	rts

; d0.l: the beam line now
SmLineNow
	move.l	$dff004,d0
	lsr.l	#8,d0
	and.l	#$1ff,d0
	rts

; a3: SmV. Pairs each line, plot and shape of the current recording with the first op
; of the same type and key (and shape) at most SM_W ops after the last pair in the
; previous recording.
SmPair
	move.l	sv_cur(a3),a0
	move.l	sv_ptr(a3),a2
	move.l	sv_prev(a3),a1
	move.l	sv_pend(a3),d4
	tst.b	sv_ok(a3)
	bne.b	.go
	move.l	a1,d4			; nothing to pair with
.go	move.l	#SM_BUDGET,d7
	moveq	#0,d5			; paired
	moveq	#0,d6			; not paired
.loop	cmp.l	a2,a0
	bhs.b	.done
	move.b	(a0),d0
	cmp.b	#OP_LINE,d0
	beq.b	.p
	cmp.b	#OP_PLOT,d0
	beq.b	.p
	cmp.b	#OP_SHAPE,d0
	bne.b	.next
.p	move.w	#-1,12(a0)
	move.l	(a0),d1			; type, flags, key
	move.l	a1,a5
	move.w	#SM_W-1,d3
.s	cmp.l	d4,a5
	bhs.b	.none
	subq.l	#1,d7
	bmi.b	.none
	cmp.l	(a5),d1
	beq.b	.hit
.s2	lea	SM_OPSZ(a5),a5
	dbf	d3,.s
	bra.b	.none
.hit	cmp.b	#OP_SHAPE,d0
	bne.b	.ok
	move.l	8(a5),d2
	cmp.l	8(a0),d2
	bne.b	.s2
.ok	move.l	a5,d2
	sub.l	sv_prev(a3),d2
	lsr.l	#4,d2
	move.w	d2,12(a0)
	lea	SM_OPSZ(a5),a1
	addq.l	#1,d5
	bra.b	.next
.none	addq.l	#1,d6
.next	lea	SM_OPSZ(a0),a0
	bra.b	.loop
.done	move.l	d5,sv_paired(a3)
	move.l	d6,sv_unpaired(a3)
	rts

; a3: SmV, d6.w: the field (1..sv_n) the frame is for. Draws the current recording
; into the back buffer, coordinates d6/sv_n of the way from the previous recording's.
SmRender
	movem.l	d0-d7/a0-a6,-(a7)
	move.l	-26412(a4),-(a7)	; what the replay changes, restored after
	move.l	-26398(a4),-(a7)
	move.l	-25800(a4),-(a7)
	move.l	-26442(a4),-(a7)
	move.l	-25542(a4),-(a7)	; pen x, y
	move.w	-25534(a4),-(a7)	; its outcode
	move.w	-26414(a4),-(a7)	; fill colour
	move.w	-28142(a4),-(a7)	; line colour
	move.l	-28138(a4),-(a7)	; its plane flags
	move.l	-26442(a4),d4		; back buffer
	move.l	-26446(a4),d5		; front buffer
	move.l	sv_cur(a3),a2
	move.l	sv_prev(a3),a6
.loop	cmp.l	sv_ptr(a3),a2
	bhs.b	.done
	moveq	#0,d0
	move.b	(a2),d0
	add.w	d0,d0
	move.w	.tab(pc,d0.w),d0
	jsr	.tab(pc,d0.w)
	lea	SM_OPSZ(a2),a2
	bra.b	.loop
.done	move.l	(a7)+,-28138(a4)
	move.w	(a7)+,-28142(a4)
	move.w	(a7)+,-26414(a4)
	move.w	(a7)+,-25534(a4)
	move.l	(a7)+,-25542(a4)
	move.l	(a7)+,-26442(a4)
	move.l	(a7)+,-25800(a4)
	move.l	(a7)+,-26398(a4)
	move.l	(a7)+,-26412(a4)
	movem.l	(a7)+,d0-d7/a0-a6
	rts

.tab	dc.w	.nop-.tab,.color-.tab,.line-.tab,.plot-.tab,.shape-.tab
	dc.w	.rect-.tab,.copy-.tab,.nop-.tab,.clear-.tab,.state-.tab,.buf-.tab

.nop	rts

.color	move.w	4(a2),-(a7)
	CALLG	$1840
	addq.l	#2,a7
	rts

.line	moveq	#4-1,d7
	bsr	.coords
	move.w	2(a0),-(a7)
	move.w	(a0),-(a7)
	CALLG	$1ae4			; move to
	addq.l	#4,a7
	lea	SmV+sv_tmp(pc),a0
	move.w	6(a0),-(a7)
	move.w	4(a0),-(a7)
	CALLG	$1b06			; line to
	addq.l	#4,a7
	rts

.plot	moveq	#2-1,d7
	bsr	.coords
	move.l	(a0),-(a7)
	CALLG	$1b2c
	addq.l	#4,a7
	rts

.shape	moveq	#2-1,d7
	bsr	.coords
	move.l	8(a2),-(a7)
	move.l	(a0),-(a7)
	CALLG	$9806
	addq.l	#8,a7
	rts

.rect	move.w	12(a2),-26414(a4)
	move.l	8(a2),-(a7)
	move.l	4(a2),-(a7)
	CALLG	$0810
	addq.l	#8,a7
	rts

.copy	move.l	8(a2),-(a7)		; x1 y1
	move.l	4(a2),-(a7)		; x0 y0
	move.b	1(a2),d2
	move.l	SM_OPSZ+12(a2),d0	; destination
	move.b	d2,d1
	lsr.b	#2,d1
	bsr.b	.unx
	move.l	d0,-(a7)
	move.l	12(a2),d0		; source
	move.b	d2,d1
	bsr.b	.unx
	move.l	d0,-(a7)
	CALLG	$0a1c
	lea	16(a7),a7
	lea	SM_OPSZ(a2),a2		; and the ARG op
	rts
.unx	and.b	#3,d1
	beq.b	.abs
	subq.b	#1,d1
	bne.b	.front
	add.l	d4,d0
.abs	rts
.front	add.l	d5,d0
	rts

.clear	CALLG	$1c08
	rts

.state	move.l	4(a2),-26412(a4)
	move.l	8(a2),-26398(a4)
	move.l	12(a2),-25800(a4)
	rts

.buf	move.l	12(a2),d0
	bne.b	.b1
	move.l	d4,d0
	bra.b	.bs
.b1	cmp.l	#1,d0
	bne.b	.bs
	move.l	d5,d0
.bs	move.l	d0,-26442(a4)
	rts

; d7.w: coordinates - 1. Copies them from the op (+4) to sv_tmp and moves them d6/sv_n
; of the way from the paired op's, unless one moved farther than SM_T.
; Out: a0 = sv_tmp
.coords	lea	SmV+sv_tmp(pc),a0
	move.l	4(a2),(a0)
	move.l	8(a2),4(a0)
	cmp.w	SmV+sv_n(pc),d6
	bhs.b	.cx
	move.w	12(a2),d0
	bmi.b	.cx
	movem.l	d1-d3/d7/a0-a1,-(a7)
	ext.l	d0
	lsl.l	#4,d0
	lea	4(a6,d0.l),a1		; the paired op's coordinates
	move.w	d7,d3
.chk	move.w	(a0)+,d0
	ext.l	d0
	move.w	(a1)+,d1
	ext.l	d1
	sub.l	d1,d0
	bpl.b	.pos
	neg.l	d0
.pos	cmp.l	#SM_T,d0
	bgt.b	.snap
	dbf	d3,.chk
	movem.l	(a7),d1-d3/d7/a0-a1
	move.w	12(a2),d0
	ext.l	d0
	lsl.l	#4,d0
	lea	4(a6,d0.l),a1
.lerp	move.w	(a1)+,d1
	move.w	(a0),d0
	sub.w	d1,d0
	muls	d6,d0
	muls	SmV+sv_mul(pc),d0
	add.l	d0,d0
	add.l	#$8000,d0
	swap	d0
	add.w	d1,d0
	move.w	d0,(a0)+
	dbf	d7,.lerp
.snap	movem.l	(a7)+,d1-d3/d7/a0-a1
.cx	rts

;----------------------------------------------------------------------------

SmCode	dc.l	0			; the code hunk (PL_GA)
SmTags	dc.l	WHDLTAG_CUSTOM2_GET,0
	dc.l	0			; TAG_DONE
	dc.l	"SWSM"			; the harness finds SmV behind this
SmV	ds.b	sv_SIZE
	CNOP	0,4
