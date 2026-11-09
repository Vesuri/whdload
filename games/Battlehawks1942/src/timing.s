;*---------------------------------------------------------------------------
; Enhanced framerate (CUSTOM2=1 only): real-time simulation, ported from Their Finest
; Hour's timing.s (2.0b), whose flight code BH shares (docs/open-work.md; tools/xmatch.py
; maps TFH's sites and globals to BH's).
;
; Each pass of BH's flight loop (bh:6e4c) is one simulation step of 1/T seconds, with
; T = 10184(a4) from the mission record (7 x a mission byte / 16, at least 3, bh:1341c).
; Game speed was therefore fps/T: right only at the frame rate the mission was tuned for on
; an A500.  Here T is set every frame from the frame's average length in fields (counted by
; a VERTB server, dt_vbint; it moves 1/8 of the way to each frame's length): T = fields per
; second / average, as an integer.  The time owed (frames' lengths less the steps taken) is
; carried, and a quarter of it is added to the next step aimed at, so game time follows
; real time.  The flight's first frame steps by the mission's T; the average starts at the
; first frame measured (TFH moved it there from the boot T 1/8 at a time: at one frame per
; field that ran the game 0.9 s ahead in its first half second, and at T 50, a step per
; field, the game cannot give time back).  The game counts many intervals in frames, set as multiples of T (a gun's
; reload T/3): T from one frame's length would alternate between frames of 1 and 2 fields,
; and those intervals would take half or twice their time.
; T stays within DT_TMIN and the field rate; a frame of more than DT_STALL fields (a disk
; load) advances no extra time.  TFH let the game run at most one field ahead of real time;
; at BH's 3-6 fields per frame on the 68000 the integer T makes the time owed swing by
; about a field, and that limit cut the swings off: the game ran 1% fast.  DT_AHEAD
; fields leave room for the swings (0.15% in a replay of that flight's frame lengths).  Above one frame per field the game would run faster than
; real time: dt_pace holds the c2p to one frame per field.  10186(a4) = T/8+1 follows T.
; The mission's T is restored when the flight ends (BH uses T in its menus too, bh:246,
; bh:30a) and at the next flight's start.
;
; Stick input arrives per event, not per frame: the mouse's counts summed over the frame,
; a key's deflection on the frames it repeats (bh:110, bh:7f30).  The game divides it by T
; into a per-step rate, so its response per second was counts per second / T.  It divides
; by the mission's T here, which keeps the original's response at every frame rate; the
; per-frame mouse limit (bh:3eb0) is scaled by mission T / T for the same reason.
;
; At large T the per-step increments are small and the game truncated each one.  Each
; object's step (dt_steplen, dt_polar), the player's stick rates and turn (dt_stick,
; dt_turn) and the AI planes' turn (dt_aiadd, dt_aisub) are computed in 16.16 here, with
; their fractions carried to the next step.
;
; BH's two busy waits (bh:30a, the menus' pauses, 1000 x T x n loops; bh:12ac, a wait for
; a key of 7n x 1000 loops) become waits of their length on a 7.09 MHz 68000.
;
; The fraction arrays are allocated at install; without the memory none of this is applied.
;---------------------------------------------------------------------------

DT_HZ		= 50		;PAL fields per second
DT_HZ_NTSC	= 60
DT_LINES	= 288		;highest line of a field: PAL 312, NTSC 262
DT_ONE		= 256		;fixed point: units per field
DT_TMIN		= 4		;as TFH: T at most dt_hz (one frame per field)
DT_STALL	= 25		;fields
DT_AVG		= 3		;the average frame moves 1/8 of the way per frame
DT_AHEAD	= 4		;fields the game may run ahead (TFH: 1)
DT_OBJECTS	= 144		;BH's object slots (bh:86b2)

BH_T		= 10184		;(a4) the step divisor T
BH_T8		= 10186		;(a4) T/8+1
BH_STICK	= 10308		;(a4) roll, pitch stick (10310), mouse counts << 7 or keys
BH_RATE		= 28506		;(a4) roll, pitch rate (28508), heading (28510), pitch (28512)
BH_ROLL		= 15240		;(a4) roll angle per plane, player first
BH_SIN		= 670		;(a4) sin magnitudes, 2048 words, sign from angle bit 15

; dt_buf: fractions carried per step (16 bits each)
DTB_FRAC	= 0				;x, y, z per object (dt_polar)
DTB_AIFRAC	= DTB_FRAC+DT_OBJECTS*6		;AI turn per object
DTB_RFRAC	= DTB_AIFRAC+DT_OBJECTS*2	;roll, pitch, heading, pitch-change rates
DTB_SIZE	= DTB_RFRAC+8

; < A2: resload, D1: seglist (BPTR); all registers saved by the caller
timing_patch	move.l	d1,d7
		move.l	(4).w,a6
	IFD VERIFY
		bsr	dt_vbinstall		;the flight record counts fields in both modes
	ENDC
		move.l	(_improve,pc),d0
		beq.b	.done
		move.l	(dt_buf,pc),d0		;BH loaded again: as before
		bne.b	.buf
		move.l	#DTB_SIZE,d0
		move.l	#MEMF_PUBLIC|MEMF_CLEAR,d1
		jsr	(_LVOAllocMem,a6)
		tst.l	d0
		beq.b	.done			;no memory: the original game
		lea	(dt_buf,pc),a0
		move.l	d0,(a0)
.buf
		move.l	d7,d1
		lsl.l	#2,d1
		addq.l	#4,d1
		lea	(dt_bh,pc),a0
		move.l	d1,(a0)			;hunk 0
		bsr	dt_rate
		lea	(dt_hz,pc),a0
		move.w	d0,(a0)
	IFND VERIFY
		bsr	dt_vbinstall
	ENDC
		lea	(_pl_timing,pc),a0
		move.l	d7,a1
		jsr	(resload_PatchSeg,a2)
.done		rts

; < A6: exec; the VERTB server counting dt_fields (once)
dt_vbinstall	lea	(dt_vbint,pc),a1
		tst.b	(LN_TYPE,a1)
		bne.b	.done
		move.b	#NT_INTERRUPT,(LN_TYPE,a1)
		lea	(dt_fields,pc),a0
		move.l	a0,(IS_DATA,a1)
		lea	(dt_vbcode,pc),a0
		move.l	a0,(IS_CODE,a1)
		moveq	#INTB_VERTB,d0
		jmp	(_LVOAddIntServer,a6)
.done		rts

_pl_timing	PL_START
		PL_PS	$1344e,dt_mission	;move.w 10184(a4),d0; lsr.w #3,d0
		PL_PS	$6b1c,dt_flight		;jsr -32724(a4)
		PL_NOP	$6b22,2
		PL_PS	$6e52,dt_loop		;addq.w #1,26292(a4); clr.w 26720(a4)
		PL_NOP	$6e58,2
		PL_PS	$6e8e,dt_pace		;tst.w 26720(a4); beq.s 6e9c
		PL_PS	$6eb6,dt_flight_end	;move.w #64,-(sp); clr.w -(sp)
		PL_PS	$3eb0,dt_mouse_limit	;cmpi.w #-192,10298(a4), to bh:3ee8
		PL_PS	$7920,dt_stick		;cmpi.w #-32768,10308(a4), to bh:7982
		PL_PS	$79fe,dt_turn		;move.w 15240(a4),-(sp), to bh:7a24
		PL_PS	$800c,dt_viewdiv	;swap d0; divu.w 10184(a4),d0
		PL_PS	$8022,dt_viewdiv
		PL_PS	$803e,dt_viewdiv
		PL_PS	$8054,dt_viewdiv
		PL_PS	$8290,dt_steplen	;jsr -32472(a4); addq.w #4,sp
		PL_PS	$831c,dt_polar		;jsr -32418(a4); addq.w #6,sp
		PL_PS	$839e,dt_polar
		PL_PS	$842a,dt_polar
		PL_PS	$855c,dt_polar
		PL_PS	$8622,dt_polar
		PL_PS	$11e50,dt_aiadd		;move.w -42(a5),d0; swap d0
		PL_PS	$11ee2,dt_aisub		;same bytes
		PL_P	$30e,dt_delay		;bh:30a after its link
		PL_P	$12b8,dt_keywait	;bh:12ac after its link and movem
		PL_END

; VERTB server: fields since install
dt_vbcode	addq.w	#1,(a1)
		moveq	#0,d0
		rts

; > D0.w: fields per second, from the highest beam line of a field (as TFH)
dt_rate		movem.l	d1-d3,-(a7)
		bsr.b	.line
.sync		move.w	d0,d1			;wait for the beam to wrap to line 0
		bsr.b	.line
		cmp.w	d1,d0
		bhs.b	.sync
		moveq	#0,d2
.field		cmp.w	d2,d0
		bls.b	.next
		move.w	d0,d2
.next		move.w	d0,d1
		bsr.b	.line
		cmp.w	d1,d0
		bhs.b	.field			;until it wraps again
		moveq	#DT_HZ,d0
		cmp.w	#DT_LINES,d2
		bhs.b	.done
		moveq	#DT_HZ_NTSC,d0
.done		movem.l	(a7)+,d1-d3
		rts
; > D0.w: the beam's line, read until two reads agree (VPOSR bit 0 is line bit 8)
.line		move.l	($dff004),d0
		lsr.l	#8,d0
		and.w	#$1ff,d0
		move.l	($dff004),d3
		lsr.l	#8,d3
		and.w	#$1ff,d3
		cmp.w	d0,d3
		bne.b	.line
		rts

; bh:1344e, end of the mission record: T is the mission's
dt_mission	move.w	(BH_T,a4),d0
		move.l	a0,-(a7)
		lea	(dt_tm,pc),a0
		move.w	d0,(a0)
		move.l	(a7)+,a0
		lsr.w	#3,d0
		rts

; bh:6b1c, flight initialisation: the mission's T, new frame timing
dt_flight	move.l	a0,-(a7)
		lea	(dt_tm,pc),a0
		tst.w	(a0)
		bne.b	.tm
		move.w	(BH_T,a4),(a0)		;no mission record seen: this T
.tm		lea	(dt_live,pc),a0
		clr.w	(a0)
		st	(dt_flying-dt_live,a0)
		move.l	(a7)+,a0
		bsr	dt_restore
		jmp	(-32724,a4)		;as the replaced jsr

; bh:6eb6, the flight loop's exit: the mission's T for the menus
dt_flight_end	bsr	dt_restore
		lea	(dt_flying,pc),a0
		clr.w	(a0)
		move.l	(a7)+,a0		;bh:6ebc
		move.w	#64,-(a7)
		clr.w	-(a7)
		jmp	(a0)

dt_restore	move.l	d0,-(a7)
		move.w	(dt_tm,pc),d0
		beq.b	.none			;no mission seen yet
		move.w	d0,(BH_T,a4)
		lsr.w	#3,d0
		addq.w	#1,d0
		move.w	d0,(BH_T8,a4)
.none		move.l	(a7)+,d0
		rts

; bh:6e52, top of the flight loop, once per frame
dt_loop		addq.w	#1,(26292,a4)
		clr.w	(26720,a4)
		movem.l	d0-d3/a0,-(a7)
		bsr	dt_frame
		movem.l	(a7)+,d0-d3/a0
		rts

dt_frame	move.w	(dt_fields,pc),d0
		lea	(dt_last,pc),a0
		move.w	(a0),d1
		move.w	d0,(a0)
		lea	(dt_live,pc),a0
		tst.w	(a0)
		bne.b	.live
		move.w	#1,(a0)			;first frame of a flight: keep T
		lea	(dt_err,pc),a0
		clr.w	(a0)
		moveq	#0,d0			;the average frame from it
		move.w	(dt_hz,pc),d0
		lsl.w	#8,d0
		divu.w	(BH_T,a4),d0
		lea	(dt_avg,pc),a0
		move.w	d0,(a0)
		rts
.live		neg.w	d1
		add.w	d0,d1			;fields since the last frame
		cmp.w	#DT_STALL,d1
		bls.b	.time
		lea	(dt_err,pc),a0		;stall: no time owed, T unchanged
		clr.w	(a0)
		rts
.time		lsl.w	#8,d1			;*DT_ONE: this frame
		lea	(dt_live,pc),a0
		tst.w	(a0)
		bmi.b	.average
		move.w	#-1,(a0)		;the first frame measured: the average is it
		lea	(dt_avg,pc),a0
		move.w	d1,(a0)
		lea	(dt_err,pc),a0
		clr.w	(a0)
		bra.b	.owe
.average	lea	(dt_avg,pc),a0
		move.w	d1,d0
		sub.w	(a0),d0
		addq.w	#(1<<DT_AVG)/2,d0
		asr.w	#DT_AVG,d0
		add.w	d0,(a0)			;the average frame
.owe		lea	(dt_err,pc),a0
		move.w	(a0),d2
		add.w	d2,d1			;time owed, fields*DT_ONE
		asr.w	#2,d2
		add.w	(dt_avg,pc),d2		;the step aimed at: average + debt/4
		moveq	#0,d0
		move.w	(dt_hz,pc),d0
		lsl.w	#8,d0			;a second: dt_hz*DT_ONE
		move.w	d0,d3
		lsr.w	#2,d3			;/DT_TMIN
		cmp.w	d3,d1
		ble.b	.owed
		move.w	d3,d1
.owed		cmp.w	d3,d2
		ble.b	.aim
		move.w	d3,d2			;at most a step of T = DT_TMIN
.aim		move.w	d2,d3
		move.w	(dt_hz,pc),d2		;T at most dt_hz: a field's time
		cmp.w	#DT_ONE,d3
		blt.b	.step
		move.w	d3,d2			;T = round(dt_hz*DT_ONE / aim)
		lsr.w	#1,d2
		ext.l	d2
		add.l	d0,d2
		divu.w	d3,d2
.step		move.w	d2,d3			;the step's length, rounded
		lsr.w	#1,d3
		ext.l	d3
		add.l	d0,d3
		divu.w	d2,d3
		sub.w	d3,d1
		cmp.w	#-DT_AHEAD*DT_ONE,d1	;at most DT_AHEAD fields ahead
		bge.b	.err
		move.w	#-DT_AHEAD*DT_ONE,d1
.err		move.w	d1,(a0)
		move.w	d2,(BH_T,a4)
		lsr.w	#3,d2			;as bh:1344e
		addq.w	#1,d2
		move.w	d2,(BH_T8,a4)
		rts

; bh:6e8e, before the c2p: at most one frame per field.  Then as the replaced
; tst.w 26720(a4); beq.s 6e9c (the c2p of a full redraw, or the delta c2p).
dt_pace		move.l	a0,-(a7)
		lea	(dt_shown,pc),a0
.wait		move.w	(dt_fields,pc),d0
		cmp.w	(a0),d0
		beq.b	.wait
		move.w	d0,(a0)
		move.l	(a7)+,a0
		tst.w	(26720,a4)
		bne.b	.full
		addq.l	#$6e9c-$6e94,(a7)
.full		rts

; bh:3eb0: this frame's mouse counts 10298/10300(a4), limited to 191/127 per frame in
; the original; in flight the limit per second is kept: 191 or 127 x mission T / T (at
; most 255, which the game's << 7 keeps in a word).  bh:3e98 reads the menus' input too.
dt_mouse_limit	movem.l	d0-d1,-(a7)
		move.w	#191,d1
		bsr	.limit
		move.w	(10298,a4),d0
		bsr	.clamp
		move.w	d0,(10298,a4)
		moveq	#127,d1
		bsr	.limit
		move.w	(10300,a4),d0
		bsr	.clamp
		move.w	d0,(10300,a4)
		movem.l	(a7)+,d0-d1
		add.l	#$3ee8-$3eb6,(a7)
		rts
; < D1.w original limit; > D1.w scaled
.limit		move.w	(dt_flying,pc),d0
		beq.b	.ok
		mulu.w	(dt_tm,pc),d1
		move.w	(BH_T,a4),d0
		lsr.w	#1,d0
		ext.l	d0
		add.l	d0,d1
		divu.w	(BH_T,a4),d1
		cmp.w	#255,d1
		bls.b	.ok
		move.w	#255,d1
.ok		rts
; < D0.w counts, D1.w limit; > D0.w within +-limit
.clamp		cmp.w	d1,d0
		ble.b	.lo
		move.w	d1,d0
.lo		neg.w	d1
		cmp.w	d1,d0
		bge.b	.in
		move.w	d1,d0
.in		neg.w	d1
		rts

; bh:7920: the stick 10308/10310(a4) / mission T into the roll and pitch rates
; 28506/28508(a4), exact with the fractions carried; 28508 in 16.16 kept for dt_turn
dt_stick	movem.l	d0-d2/a0,-(a7)
		move.w	(BH_STICK,a4),d0
		moveq	#0,d1			;roll slot
		bsr	.rate
		move.w	d0,(BH_RATE,a4)
		move.w	(BH_STICK+2,a4),d0
		moveq	#2,d1			;pitch slot
		bsr	.rate
		move.w	d0,(BH_RATE+2,a4)
		movem.l	(a7)+,d0-d2/a0
		add.l	#$7982-$7926,(a7)
		rts
.rate		move.w	d0,-(a7)
		bpl.b	.pos
		neg.w	d0
.pos		and.l	#$ffff,d0
		swap	d0			;|stick| << 16
		move.w	(dt_tm,pc),d2
		bsr	dt_ldiv			;16.16
		tst.w	(a7)+
		bpl.b	.sign
		neg.l	d0
.sign		tst.w	d1
		beq.b	dt_rcarry
		lea	(dt_v,pc),a0
		move.l	d0,(a0)
; < D0.l rate in 16.16, D1.w slot*2; > D0.w with the player's fraction of that slot
dt_rcarry	move.l	(dt_buf,pc),a0
		add.w	#DTB_RFRAC,a0
		add.w	d1,a0
		moveq	#0,d2
		move.w	(a0),d2
		add.l	d2,d0
		move.w	d0,(a0)
		swap	d0			;floor
		rts

; bh:79fe: 28510 = round(v sin(roll)) / 4 and 28512 = round(v cos(roll)) (bh:16574,
; bh:165ac), v = 28508; here v exact (dt_v) and both with their fractions carried
dt_turn		movem.l	d0-d4/a0,-(a7)
		move.l	(dt_v,pc),d4
		move.w	(BH_ROLL,a4),d3
		move.w	d3,d2
		bsr	.mul
		asr.l	#2,d0
		moveq	#4,d1			;heading slot
		bsr	dt_rcarry
		move.w	d0,(BH_RATE+4,a4)
		move.w	d3,d2
		add.w	#16384,d2
		bsr	.mul
		moveq	#6,d1			;pitch-change slot
		bsr	dt_rcarry
		move.w	d0,(BH_RATE+6,a4)
		movem.l	(a7)+,d0-d4/a0
		add.l	#$7a24-$7a04,(a7)
		rts
; < D4.l v (16.16, signed), D2.w angle; > D0.l v sin(angle)
.mul		move.l	d4,d0
		bpl.b	.vpos
		neg.l	d0
.vpos		bsr	dt_sin
		tst.l	d4
		bpl.b	.done
		neg.l	d0
.done		rts

; bh:800c, 8022, 803e, 8054 (the view controller, bh:7f30): the look rate / mission T
dt_viewdiv	swap	d0
		divu.w	(dt_tm,pc),d0
		rts

; bh:8290, object D4's step length in the object loop (bh:826e): as the helper
; bh:15c24, round(round(speed*4660/256) / divisor), and also the exact length in 16.16
; for dt_polar.  Like the helper, only D0-D2 change.  (TFH's dt_steplen.)
dt_steplen	move.l	a0,-(a7)
		lea	(dt_len,pc),a0
		clr.w	(a0)			;no exact length unless it fits
		moveq	#0,d0
		move.w	(8,a7),d0		;speed
		move.w	(10,a7),d2		;divisor (10184)
		mulu.w	#4660,d0
		add.l	#128,d0
		lsr.l	#8,d0
		move.l	d0,d1
		swap	d1
		cmp.w	d2,d1
		bhs.b	.round			;quotient over 16 bits: as the helper
		move.l	d0,-(a7)
		divu.w	d2,d0			;remainder : integer part
		cmp.w	#$7fff,d0
		bhs.b	.big
		move.w	d0,(2,a0)		;integer part
		clr.w	d0
		divu.w	d2,d0			;remainder << 16 / divisor
		move.w	d0,(4,a0)		;fraction
		move.w	d4,(8,a0)		;object
		st	(a0)
.big		move.l	(a7)+,d0
.round		move.w	d0,d1
		lsr.w	#1,d1			;half the dividend, for rounding
		divu.w	d2,d0			;as bh:15c24
		move.l	d0,d2
		swap	d2
		cmp.w	d1,d2
		blo.b	.q
		addq.l	#1,d0
.q		move.w	d0,(6,a0)		;the length the game uses
		move.l	(a7)+,a0
		move.l	(a7),(4,a7)		;return over the two arguments
		addq.l	#4,a7
		rts

; bh:831c, 839e, 842a, 855c, 8622: the object loop's velocity from the step length,
; heading and pitch (bh:16772 sets 512/516/520(a4) to x, y, z per step, each
; truncated).  With the exact length of this object's step the components come in 16.16
; from bh:165e8, and each object's fractions carry to its next step.  Like bh:16772, only
; D0 changes.  (TFH's dt_polar.)
dt_polar	movem.l	d1-d3/a0-a1/a6,-(a7)
		lea	(dt_len,pc),a0
		tst.w	(a0)
		beq.b	.orig
		move.w	(28,a7),d0		;length pushed
		cmp.w	(6,a0),d0
		bne.b	.orig
		cmp.w	(8,a0),d4
		bne.b	.orig
		cmp.w	#DT_OBJECTS,d4
		bhs.b	.orig
		move.w	(2,a0),(400,a4)		;length 16.16
		move.w	(4,a0),(402,a4)
		move.w	(30,a7),d0		;heading, as bh:16786
		sub.w	#16384,d0
		neg.w	d0
		move.w	d0,(404,a4)
		move.w	(32,a7),(406,a4)	;pitch
		move.l	(-32416,a4),a0		;bh:16772, from the jump table
		lea	(-$16772+$165e8,a0),a0
		jsr	(a0)
		move.l	(dt_buf,pc),a0
		move.w	d4,d0
		mulu.w	#6,d0
		add.w	d0,a0			;DTB_FRAC
		lea	(408,a4),a1
		lea	(512,a4),a6
		moveq	#3-1,d3
.axis		move.l	(a1)+,d0		;16.16, signed
		moveq	#0,d1
		move.w	(a0),d1
		add.l	d1,d0
		move.w	d0,(a0)+		;fraction carried
		swap	d0
		ext.l	d0			;floor
		move.l	d0,(a6)+
		dbf	d3,.axis
		movem.l	(a7)+,d1-d3/a0-a1/a6
		bra.b	.ret
.orig		movem.l	(a7)+,d1-d3/a0-a1/a6
		move.w	(8,a7),-(a7)		;pitch, heading, length again
		move.w	(8,a7),-(a7)
		move.w	(8,a7),-(a7)
		jsr	(-32418,a4)
		addq.l	#6,a7
.ret		move.l	(a7),(6,a7)		;return over the three arguments
		addq.l	#6,a7
		rts

; The AI planes turn (bh:11e18) by v = a / 3 / T * 19584[plane] >> 16, a the bank angle
; folded to 0..16384 in -42(a5), added to the heading 14328 for a left bank and
; subtracted for a right one.  D4 is the object.  Here v is exact in 16.16, signed, with
; its fraction carried per object.  (TFH's dt_aiadd, dt_aisub.)

; bh:11e50: v for a left bank, on to bh:11e88
dt_aiadd	movem.l	d1-d3/a0,-(a7)
		bsr	dt_airate
		bsr	dt_aicarry
		move.w	d0,(-42,a5)
		movem.l	(a7)+,d1-d3/a0
		add.l	#$11e88-$11e56,(a7)
		rts

; bh:11ee2: v for a right bank, on to bh:11f1a
dt_aisub	movem.l	d1-d3/a0,-(a7)
		bsr	dt_airate
		neg.l	d0
		bsr	dt_aicarry
		neg.w	d0
		move.w	d0,(-42,a5)
		movem.l	(a7)+,d1-d3/a0
		add.l	#$11f1a-$11ee8,(a7)
		rts

; > D0.l a * 19584[D4] / (3 * T) in 16.16
dt_airate	moveq	#0,d0
		move.w	(-42,a5),d0
		move.w	d4,d1
		add.w	d1,d1
		lea	(19584,a4),a0
		mulu.w	(a0,d1.w),d0
		move.w	(BH_T,a4),d2
		mulu.w	#3,d2
		bra	dt_ldiv

; < D0.l v in 16.16; > D0.w with object D4's fraction carried
dt_aicarry	move.w	d4,d1
		cmp.w	#DT_OBJECTS,d1
		bhs.b	.floor
		add.w	d1,d1
		move.l	(dt_buf,pc),a0
		add.w	#DTB_AIFRAC,a0
		add.w	d1,a0
		moveq	#0,d1
		move.w	(a0),d1
		add.l	d1,d0
		move.w	d0,(a0)
.floor		swap	d0
		rts

; < D0.l, D2.w divisor; > D0.l D0 / D2 (the quotient's upper 16 bits from the high
; word, so no overflow)
dt_ldiv		movem.l	d1-d3,-(a7)
		move.l	d0,d1
		clr.w	d1
		swap	d1
		divu.w	d2,d1			;remainder : quotient of the high word
		move.l	d1,d3
		move.w	d0,d1
		divu.w	d2,d1			;quotient of (remainder << 16) | low word
		swap	d3
		move.w	d1,d3
		move.l	d3,d0
		movem.l	(a7)+,d1-d3
		rts

; < D0.l v (16.16, >= 0), D2.w angle; > D0.l v * sin(angle) in 16.16, from the game's
; table (magnitudes, sign from angle bit 15) as bh:16574
dt_sin		movem.l	d1-d3/a0,-(a7)
		move.w	d2,d3
		lea	(BH_SIN,a4),a0
		lsr.w	#5,d2
		and.w	#-2,d2
		move.w	(a0,d2.w),d2
		move.l	d0,d1
		swap	d1
		mulu.w	d2,d1			;high word * sin
		mulu.w	d2,d0			;low word * sin
		clr.w	d0
		swap	d0
		add.l	d1,d0
		tst.w	d3
		bpl.b	.pos
		neg.l	d0
.pos		movem.l	(a7)+,d1-d3/a0
		rts

; < D0.w fields to wait
dt_wait		movem.l	d0-d1,-(a7)
		bra.b	.next
.field		move.w	(dt_fields,pc),d1
.same		cmp.w	(dt_fields,pc),d1
		beq.b	.same
.next		dbf	d0,.field
		movem.l	(a7)+,d0-d1
		rts

; bh:30e (bh:30a after link.w a5,#-12): a pause of n = 8(a5): (k*T*n) mod 65536 loops
; of 64 cycles (k = 100 at T 3, else 1000), now their fields on a 7.09 MHz 68000
; (141 876 cycles per field: 2217 loops)
dt_delay	move.w	#1000,d1
		move.w	(BH_T,a4),d0
		cmp.w	#3,d0
		bne.b	.k
		moveq	#100,d1
.k		mulu.w	d1,d0
		mulu.w	(8,a5),d0
		and.l	#$ffff,d0
		add.l	#2217/2,d0
		divu.w	#2217,d0
		bsr	dt_wait
		unlk	a5
		rts

; bh:12b8 (bh:12ac after link.w a5,#-2; movem.l d4-d5,-(sp)): wait n = 8(a5) units or
; until a key (bh:3e98) or a button (10296(a4)).  A unit was 7 x 1000 loops of 22
; cycles: 1.0855 fields.  Here the input is read once a field.
dt_keywait	moveq	#0,d4
		move.w	(8,a5),d4
		cmp.w	#60000,d4
		bls.b	.n
		move.w	#60000,d4
.n		mulu.w	#1086,d4
		add.l	#500,d4
		divu.w	#1000,d4		;fields
		bra.b	.next
.field		moveq	#1,d0
		bsr	dt_wait
		move.l	(dt_bh,pc),a0
		jsr	($3e98,a0)
		tst.w	d0
		bne.b	.done
		tst.w	(10296,a4)
		bne.b	.done
.next		dbf	d4,.field
.done		movem.l	(a7)+,d4-d5
		unlk	a5
		rts

dt_buf		dc.l	0			;DTB_SIZE bytes, allocated
dt_bh		dc.l	0			;BH's hunk 0
dt_v		dc.l	0			;28508(a4) in 16.16
dt_hz		dc.w	DT_HZ			;fields per second, measured at install
dt_fields	dc.w	0			;VERTB count
dt_tm		dc.w	0			;the mission's T
dt_last		dc.w	0
dt_shown	dc.w	0
dt_live		dc.w	0			;0 flight start, 1 first frame, -1 measuring
dt_flying	dc.w	0			;between dt_flight and dt_flight_end
dt_err		dc.w	0
dt_avg		dc.w	0			;average frame, fields*DT_ONE
dt_len		dc.w	0,0,0,0,0		;valid, integer, fraction, rounded, object
dt_vbint	dcb.b	IS_SIZE,0
	EVEN
