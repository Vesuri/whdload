;*---------------------------------------------------------------------------
; Enhanced framerate, plan step 3: timers and combat (TFH's FR-01..FR-28 on BH).
; Included by timing.s, whose patch list carries the entries; its state lives in
; timing.s's allocated buffer from DTB_STEP3 on (these DTB3_ offsets), cleared at each
; flight's start (dt_flight).
;
; Rates per second divide by the live T with their fractions carried (dt_att_rate).
; What the original counted in steps is kept as it was at the mission's T (dt_tm), the
; frame rate the mission was tuned for on an A500, and then timed in seconds: a gun's
; reload of T/3 steps is floor(tm/3)/tm seconds, +16 a step is 16 tm a second, a minimum
; of one a step is tm a second.  Countdowns set as k x T (an object's life 16816, the
; mission waits) last k seconds whatever T does meanwhile.  Clocks are Q24 seconds
; (2^24 = 1 s), the steps they lose are ceil(2^24/T): a deadline comes at most 2^-24 s
; early per step and is seen at the first step that reaches it.
;---------------------------------------------------------------------------

DT_PLANES	= 12		;aircraft slots (bh:11fac)

DTB3_ROLLF	= 0				;FR-15 commanded roll, per plane
DTB3_PITCHF	= DTB3_ROLLF+DT_PLANES*2	;pitch 14952
DTB3_FALLF	= DTB3_PITCHF+DT_PLANES*2	;pitch 14616 (falling, stalled)
DTB3_FUELF	= DTB3_FALLF+DT_PLANES*2	;FR-28 fuel
DTB3_GUN	= DTB3_FUELF+DT_PLANES*2	;FR-07 Q24 reload clocks, front then rear guns
DTB3_AI		= DTB3_GUN+DT_PLANES*8		;FR-12/14 Q24 decision clocks, 16 objects
DTB3_FX		= DTB3_AI+16*4			;FR-03 effects clock
DTB3_AIRDMG	= DTB3_FX+4			;FR-10 aircraft damage clock
DTB3_SHIP	= DTB3_AIRDMG+4			;FR-11 ship damage clock
DTB3_W40	= DTB3_SHIP+4			;FR-20 mission reminder (10142)
DTB3_W4		= DTB3_W40+4			;FR-20 mission scan (10140)
DTB3_FILMTIME	= DTB3_W4+4			;FR-22 seconds recorded, Q16
DTB3_BOMBCD	= DTB3_FILMTIME+4		;FR-08 player's release wait 10216: Q20, last
DTB3_MSG	= DTB3_BOMBCD+8			;FR-21 the message's time 28522: Q20, last
DTB3_LIFE	= DTB3_MSG+8			;object timers 16816: Q20 seconds left, last count
DTB3_VZF	= DTB3_LIFE+DT_OBJECTS*6	;FR-01 falling objects' vertical speed fraction
DTB3_SIZE	= DTB3_VZF+DT_OBJECTS*2

;---------------------------------------------------------------------------
; FR-15: the aircraft attitude update (bh:11142, once per step for each of the 12
; planes in D4) turns by rates per second / T, each truncated: a second of commanded roll
; moved 4096 units at T 8 and 4050 at T 50.  Here every rate carries its fraction, in
; three channels per plane as TFH: the commanded roll 15240, the pitch 14952 and the
; falling/stalled pitch 14616 (the game copies one into the other; the fractions follow).
; Commands: roll 4096/s (16384/s fast), pitch down 9216/s and up 5120/s (TFH: 4096 and
; 5120); falling 6400/s (bh:11b26) and 728/s (bh:11bfa), spinning roll 20480/s; the
; player's bank pushes the nose down 910 x f(bank)/s (bh:11536, 11590).  Reaching a target
; or a limit clears that fraction.  The pole crossing (bh:113e6, 114ac) reflects pitch and
; changes its rate: the overshoot past the pole is converted by the rates' ratio, so the
; rest of the step runs at the new rate (TFH's 5/4, here 5/9 and 9/5).
; The original also counted two things per step: the nose rises 16 a step while
; underpowered near level (bh:117ec), and climbing loses max(1, floor(r/T)) of speed a
; step (bh:11648, 116fe).  Here they are 16 tm and tm max(1, floor(r/tm)) per second (the
; native decelerator bh:1207c carries the speed's fraction in 15984).
;---------------------------------------------------------------------------

; < D0.w signed rate per second, D1.w channel (DTB3_), D4 plane
; > D0.w this step's part (floor), the fraction carried
dt_att_rate	movem.l	d1-d3/a0,-(a7)
		move.w	d0,d3
		bpl.b	.pos
		neg.w	d0
.pos		swap	d0
		clr.w	d0
		move.w	(BH_T,a4),d2
		bsr	dt_ldiv
		tst.w	d3
		bpl.b	.carry
		neg.l	d0
.carry		cmp.w	#DT_PLANES,d4
		bhs.b	.floor
		move.l	(dt_buf,pc),a0
		add.w	#DTB_STEP3,a0
		add.w	d1,a0
		move.w	d4,d1
		add.w	d1,d1
		add.w	d1,a0
		moveq	#0,d1
		move.w	(a0),d1
		add.l	d1,d0
		move.w	d0,(a0)
.floor		swap	d0
		movem.l	(a7)+,d1-d3/a0
		rts

; > A0: plane D4's slot of channel D0.w
dt_att_slot	move.l	(dt_buf,pc),a0
		add.w	#DTB_STEP3,a0
		add.w	d0,a0
		move.w	d4,d0
		add.w	d0,d0
		add.w	d0,a0
		rts

; bh:11238: the roll step -46(a5) toward the target 15552 (to bh:125a)
dt_att_roll	movem.l	d0-d2/a0-a1,-(a7)
		lea	(15540,a4),a0		;fast roll
		move.w	#4096,d0
		cmp.b	#1,(a0,d4.w)
		bne.b	.rate
		move.w	#16384,d0
.rate		move.w	d4,d1
		add.w	d1,d1
		lea	(15552,a4),a0
		lea	(BH_ROLL,a4),a1
		move.w	(a0,d1.w),d2
		sub.w	(a1,d1.w),d2
		bpl.b	.pos
		neg.w	d0
.pos		move.w	#DTB3_ROLLF,d1
		bsr	dt_att_rate
		tst.w	d2
		bpl.b	.store
		neg.w	d0
.store		move.w	d0,(-46,a5)
		movem.l	(a7)+,d0-d2/a0-a1
		add.l	#$1125a-$1123e,(a7)
		rts

; bh:112ae, 112fa: the roll reached its target
dt_att_roll_done
		move.b	#2,(a0,d0.l)
		movem.l	d0/a0,-(a7)
		move.w	#DTB3_ROLLF,d0
		bra	dt_att_clear

; bh:113a6, 1146c: the pitch reached its target
dt_att_pitch_done
		move.b	#3,(a0,d0.l)
		movem.l	d0/a0,-(a7)
		move.w	#DTB3_PITCHF,d0
dt_att_clear	bsr	dt_att_slot
		clr.w	(a0)
		movem.l	(a7)+,d0/a0
		rts

; bh:11324: the pitch steps -50(a5) (down) and -52(a5) (up) for the command 15576
dt_att_pitch	movem.l	d0-d1/a0,-(a7)
		lea	(15576,a4),a0
		move.b	(a0,d4.w),d1
		cmp.b	#1,d1
		beq.b	.down
		cmp.b	#2,d1
		bne.b	.done
		move.w	#5120,d0
		move.w	#DTB3_PITCHF,d1
		bsr	dt_att_rate
		move.w	d0,(-52,a5)
		bra.b	.done
.down		move.w	#-9216,d0
		move.w	#DTB3_PITCHF,d1
		bsr	dt_att_rate
		neg.w	d0
		move.w	d0,(-50,a5)
.done		movem.l	(a7)+,d0-d1/a0
		moveq	#0,d0			;as the replaced code
		move.w	d4,d0
		lea	(15576,a4),a0
		rts

; bh:113e6, 114ac: the pitch (A0,D0.L) crossed a pole; reflect it with its fraction,
; the overshoot converted to the new direction's rate
dt_att_reflect	movem.l	d1-d3/a1,-(a7)
		bsr	.frac
		move.w	(a0,d0.l),d2
		swap	d2
		move.w	(a1),d2
		neg.l	d2
		move.l	d0,-(a7)
		lea	(15576,a4),a1
		cmp.b	#1,(a1,d4.w)
		bne.b	.upper
		move.l	d2,d0			;lower pole: diving (9216) to climbing (5120)
		move.l	d0,d3
		lsl.l	#2,d0
		add.l	d3,d0
		moveq	#9,d2
		bsr	dt_ldiv			;overshoot x 5/9
		move.l	d0,d2
		bra.b	.store
.upper		move.l	#$80000000,d3		;upper pole: climbing to diving
		sub.l	d2,d3			;overshoot
		move.l	d3,d0
		moveq	#5,d2
		bsr	dt_ldiv
		move.l	d0,d3
		lsl.l	#3,d0
		add.l	d3,d0			;x 9/5
		move.l	#$80000000,d2
		sub.l	d0,d2
.store		move.l	(a7)+,d0
		bsr	.frac
		move.w	d2,(a1)
		swap	d2
		move.w	d2,(a0,d0.l)
		movem.l	(a7)+,d1-d3/a1
		moveq	#0,d0
		rts
.frac		move.l	(dt_buf,pc),a1
		add.w	#DTB_STEP3+DTB3_PITCHF,a1
		move.w	d4,d1
		add.w	d1,d1
		add.w	d1,a1
		rts

; bh:11538, 11592: the player's bank-induced pitch rate D0.w / T
dt_att_bank	move.w	d1,-(a7)
		move.w	#DTB3_PITCHF,d1
		bsr	dt_att_rate
		move.w	(a7)+,d1
		rts

; bh:11b3c, 11c40: falling pitch, rate D0.w, added to (A0)
dt_att_fall	move.w	d1,-(a7)
		move.w	#DTB3_FALLF,d1
		bsr	dt_att_rate
		move.w	(a7)+,d1
		add.w	d0,(a0)
		rts

; bh:117ec: underpowered near level, the pitch 14616 (A0) rises 16 per mission step
dt_att_sink	move.w	d1,-(a7)
		move.w	(dt_tm,pc),d0
		lsl.w	#4,d0
		move.w	#DTB3_FALLF,d1
		bsr	dt_att_rate
		move.w	(a7)+,d1
		add.w	d0,(a0)
		moveq	#0,d0
		rts

; bh:11d38: a spin's roll, rate D0.w, added to (A0)
dt_att_spin	move.w	d1,-(a7)
		move.w	#DTB3_ROLLF,d1
		bsr	dt_att_rate
		move.w	(a7)+,d1
		add.w	d0,(a0)
		rts

; bh:11b5e, 11c62: falling pitch at its limit
dt_att_fall_limit
		move.w	#$8000,(a0,d0.l)
		movem.l	d0/a0,-(a7)
		move.w	#DTB3_FALLF,d0
		bra	dt_att_clear

; bh:11b78, 11c7c, 11804: 14616 copied to 14952, and its fraction
dt_att_syncfall	move.w	(a0,d0.l),(a1,d1.l)
		movem.l	d0-d1/a0,-(a7)
		move.w	#DTB3_FALLF,d0
		bsr	dt_att_slot
		move.w	(a0),(DTB3_PITCHF-DTB3_FALLF,a0)
		movem.l	(a7)+,d0-d1/a0
		rts

; bh:115d6: 14952 copied to 14616, and its fraction
dt_att_syncpitch
		move.w	(a0,d0.l),(a1,d1.l)
		movem.l	d0-d1/a0,-(a7)
		move.w	#DTB3_PITCHF,d0
		bsr	dt_att_slot
		move.w	(a0),(DTB3_FALLF-DTB3_PITCHF,a0)
		movem.l	(a7)+,d0-d1/a0
		rts

; bh:11d80, 11d90: on the ground, level; no fractions
dt_att_ground	move.w	#$4000,(a0,d0.l)
		movem.l	d0/a0,-(a7)
		cmp.w	#DT_PLANES,d4
		bhs.b	.done
		move.w	#DTB3_ROLLF,d0
		bsr	dt_att_slot
		clr.w	(a0)
		clr.w	(DTB3_PITCHF-DTB3_ROLLF,a0)
		clr.w	(DTB3_FALLF-DTB3_ROLLF,a0)
.done		movem.l	(a7)+,d0/a0
		rts

; bh:1164e (to bh:1167e): climbing loses (-12(a5) >> 8) / T of speed, at least 1
dt_att_slow8	move.w	(-12,a5),d0
		lsr.w	#8,d0
		bsr	dt_att_slow
		add.l	#$1167e-$11654,(a7)
		rts

; bh:116fc (to bh:1172a): the same with D2 >> 10
dt_att_slow10	lsr.w	#8,d2
		lsr.w	#2,d2
		move.w	d2,d0
		bsr	dt_att_slow
		add.l	#$1172a-$11702,(a7)
		rts

; < D0.w r; tm max(1, floor(r/tm)) per second off plane D4's speed through the native
; decelerator (bh:1207c, the fraction in 15984)
dt_att_slow	and.l	#$ffff,d0
		divu.w	(dt_tm,pc),d0
		bne.b	.r
		moveq	#1,d0
.r		mulu.w	(dt_tm,pc),d0
		move.w	d0,-(a7)
		move.w	d4,-(a7)
		move.l	(dt_bh,pc),a0
		add.l	#$1207c,a0
		jsr	(a0)
		addq.l	#4,a7
		rts

;---------------------------------------------------------------------------
; FR-28: fuel 19720[plane] (a long) loses power 19628 / T a step (bh:111dc): the
; fraction is carried.  < D1.l power; > D1.w this step's part, D0 = 0; A0 kept.
dt_fuel		movem.l	d2/a0,-(a7)
		moveq	#0,d0
		move.w	d1,d0
		swap	d0
		move.w	(BH_T,a4),d2
		bsr	dt_ldiv
		cmp.w	#DT_PLANES,d4
		bhs.b	.floor
		move.l	d0,d2
		move.w	#DTB3_FUELF,d0
		bsr	dt_att_slot
		move.l	d2,d0
		moveq	#0,d2
		move.w	(a0),d2
		add.l	d2,d0
		move.w	d0,(a0)
.floor		swap	d0
		move.w	d0,d1
		moveq	#0,d0
		movem.l	(a7)+,d2/a0
		rts

;---------------------------------------------------------------------------
; Clocks
;---------------------------------------------------------------------------

; > D0.l this step in Q24 seconds, ceil(2^24/T)
dt_step24	move.l	d2,-(a7)
		moveq	#0,d2
		move.w	(BH_T,a4),d2
		move.l	#$1000000-1,d0
		add.l	d2,d0
		bsr	dt_ldiv
		move.l	(a7)+,d2
		rts

; > D0.l this step in Q20 seconds, ceil(2^20/T)
dt_step20	move.l	d2,-(a7)
		moveq	#0,d2
		move.w	(BH_T,a4),d2
		move.l	#$100000-1,d0
		add.l	d2,d0
		bsr	dt_ldiv
		move.l	(a7)+,d2
		rts

; < D0.w steps at the mission's T; > D1.l their length in Q24 seconds
dt_tmsteps	movem.l	d0/d2,-(a7)
		and.l	#$ffff,d0
		swap	d0			;Q16
		move.w	(dt_tm,pc),d2
		bsr	dt_ldiv
		lsl.l	#8,d0			;Q24
		move.l	d0,d1
		movem.l	(a7)+,d0/d2
		rts

; < A0 Q24 clock, D1.l period; > D0.w the events due this step (the clock loses the
; step; each event adds a period, so the phase carries across changes of T)
dt_periodic	bsr	dt_step24
		sub.l	d0,(a0)
		moveq	#0,d0
.due		tst.l	(a0)
		bgt.b	.done
		add.l	d1,(a0)
		addq.w	#1,d0
		bra.b	.due
.done		rts

; > A0: the step-3 state at offset D0.w
dt_s3		move.l	(dt_buf,pc),a0
		add.w	#DTB_STEP3,a0
		add.w	d0,a0
		rts

;---------------------------------------------------------------------------
; Countdowns set as a count of steps at the time's T and counted down a step at a time
; (the game's timers): kept as Q20 seconds left beside the count, which is rewritten
; each step as the steps left at the current T, ceil(seconds x T), so the game's own
; tests of it see the deadline in time.  A count changed by code not hooked here (its
; value is not the one last written) is counted down as before.
;---------------------------------------------------------------------------

; < A0 the count (word), A1 its record (Q20 seconds, last count), D1.w the count
; stored now; the seconds are D1/T
dt_cd_set	movem.l	d0/d2,-(a7)
		move.w	d1,(a0)
		move.w	d1,(4,a1)
		moveq	#0,d0
		move.w	d1,d0
		swap	d0
		lsr.l	#4,d0			;count << 12
		moveq	#0,d2
		move.w	(BH_T,a4),d2
		bsr	dt_ldiv
		lsl.l	#8,d0			;Q20
		move.l	d0,(a1)
		movem.l	(a7)+,d0/d2
		rts

; < A0 the count, A1 its record: one step down; > the count's flags as tst.w (a0)
dt_cd_dec	movem.l	d0-d2,-(a7)
		move.w	(a0),d0
		cmp.w	(4,a1),d0
		bne.b	.native
		tst.w	d0
		beq.b	.native			;0 goes to -1, as the game's
		bsr	dt_step20
		sub.l	d0,(a1)
		ble.b	.zero
		move.l	(a1),d0			;ceil(seconds x T)
		add.l	#$fff,d0
		lsr.l	#8,d0
		lsr.l	#4,d0			;Q8
		cmp.l	#$ffff,d0
		bhi.b	.long
		mulu.w	(BH_T,a4),d0
		add.l	#$ff,d0
		lsr.l	#8,d0
.store		cmp.l	#$7fff,d0
		bls.b	.w
		move.w	#$7fff,d0
.w		move.w	d0,(a0)
		move.w	d0,(4,a1)
		bra.b	.done
.zero		clr.w	(a0)
		clr.w	(4,a1)
		bra.b	.done
.long		lsr.l	#8,d0			;over 255 s: whole seconds
		mulu.w	(BH_T,a4),d0
		bra.b	.store
.native		subq.w	#1,(a0)
.done		movem.l	(a7)+,d0-d2
		tst.w	(a0)
		rts

; < D0.l object x 2 (the game's index into 16816); > A1 its record (6 bytes)
dt_life_rec	move.l	d0,-(a7)
		move.l	(dt_buf,pc),a1
		add.w	#DTB_STEP3+DTB3_LIFE,a1
		add.w	d0,a1
		add.w	d0,d0
		add.w	d0,a1
		move.l	(a7)+,d0
		rts

; < A0 16816(a4), D0.l object x 2, D1.w the count stored; as dt_cd_set
dt_life_set	movem.l	a0-a1,-(a7)
		cmp.l	#DT_OBJECTS*2,d0
		bhs.b	.store
		bsr	dt_life_rec
		add.l	d0,a0
		bsr	dt_cd_set
		movem.l	(a7)+,a0-a1
		rts
.store		move.w	d1,(a0,d0.l)
		movem.l	(a7)+,a0-a1
		rts

; < A0 16816(a4), D0.l object x 2; as dt_cd_dec, flags as tst.w (a0,d0.l)
dt_life_dec	movem.l	a0-a1,-(a7)
		cmp.l	#DT_OBJECTS*2,d0
		bhs.b	.native
		bsr	dt_life_rec
		add.l	d0,a0
		bsr	dt_cd_dec
		movem.l	(a7)+,a0-a1
		rts
.native		add.l	d0,a0
		subq.w	#1,(a0)
		movem.l	(a7)+,a0-a1
		tst.w	(a0,d0.l)
		rts

;---------------------------------------------------------------------------
; FR-07: guns.  Firing (bh:c672) set the gun's reload byte (19768 front, 19780 rear) to
; floor(T/3), the weapon pass (bh:c366, once a step) counted it down, and a gun fires
; when it is 0 (bh:c4d6): a shot every floor(T/3) steps, 0.25 s at T 4, 0.32 s at T 50.
; Here each gun has a Q24 clock: a shot adds floor(tm/3)/tm seconds, the weapon pass
; takes off the step, and the byte is 1 while the clock is above 0.  A gun that came due
; in the pass keeps the rest of that step (the phase carries); one already due before
; it builds no credit.
;---------------------------------------------------------------------------

; bh:c388 (to bh:c3bc): the reload clocks of plane D4
dt_gun_step	movem.l	d0-d2/a0-a1,-(a7)
		cmp.w	#DT_PLANES,d4
		bhs.b	.done
		bsr	dt_step24
		move.l	d0,d2
		move.w	d4,d0
		lsl.w	#2,d0
		add.w	#DTB3_GUN,d0
		bsr	dt_s3
		lea	(19768,a4),a1
		bsr	.gun
		lea	(DT_PLANES*4,a0),a0
		lea	(19780,a4),a1
		bsr	.gun
.done		movem.l	(a7)+,d0-d2/a0-a1
		add.l	#$c3bc-$c38e,(a7)
		rts
.gun		tst.l	(a0)
		bgt.b	.run
		clr.l	(a0)			;due before this step: no credit
		bra.b	.byte
.run		sub.l	d2,(a0)
.byte		tst.l	(a0)
		sgt	d0
		and.b	#1,d0
		move.b	d0,(a1,d4.w)
		rts

; bh:c70c (to bh:c726), bh:c76a (to bh:c784): plane D4 fires its front or rear gun
dt_gun_fire0	movem.l	d0-d1/a0-a1,-(a7)
		lea	(19768,a4),a1
		moveq	#0,d1
		bra	dt_gun_fire
dt_gun_fire1	movem.l	d0-d1/a0-a1,-(a7)
		lea	(19780,a4),a1
		moveq	#DT_PLANES*4,d1
dt_gun_fire	move.b	#1,(a1,d4.w)
		cmp.w	#DT_PLANES,d4
		bhs.b	.done
		move.w	d4,d0
		lsl.w	#2,d0
		add.w	d1,d0
		add.w	#DTB3_GUN,d0
		bsr	dt_s3
		move.w	(dt_tm,pc),d0
		and.l	#$ffff,d0
		divu.w	#3,d0			;floor(tm/3) steps at the mission's T
		bsr	dt_tmsteps
		tst.l	(a0)			;already reloading: the other barrel of this shot
		bgt.b	.done
		add.l	d1,(a0)
.done		movem.l	(a7)+,d0-d1/a0-a1
		add.l	#$c726-$c712,(a7)
		rts

;---------------------------------------------------------------------------
; FR-12, FR-14: AI decisions.  BH's two schedulers (bh:f074 for the 12 aircraft, bh:12d22
; for the 4 surface objects 12..15) counted each object's 2T countdown 16296 down a step at
; a time and served at most one object a step, the next due one round from 10190/10192:
; with several objects due, the last waited a step each, 0.25 s at T 4.  Here each object
; has a Q24 clock of 2 seconds (set where the game set 2T: bh:f010, a new script
; bh:12d14) and every due, eligible object (10596 set, 20056 clear) is served each step,
; earliest first, through the native routine (bh:f130, bh:12ddc).  An ineligible object's
; clock stops at 0 (no credit).
;---------------------------------------------------------------------------

; bh:f074, replaced
dt_air_ai	movem.l	d2-d7/a2,-(a7)
		moveq	#0,d5
		moveq	#12,d6
		lea	(10190,a4),a2
		move.l	#$f130,d7
		bsr	dt_ai_sched
		movem.l	(a7)+,d2-d7/a2
		rts

; bh:12d22, replaced
dt_surface_ai	movem.l	d2-d7/a2,-(a7)
		moveq	#12,d5
		moveq	#16,d6
		lea	(10192,a4),a2
		move.l	#$12ddc,d7
		bsr	dt_ai_sched
		movem.l	(a7)+,d2-d7/a2
		rts

; < D5 first object, D6 end, A2 the game's pointer, D7 the routine (bh: offset)
dt_ai_sched	bsr	dt_step24
		move.l	d0,d2
		move.w	d5,d4
.age		move.w	d4,d0
		bsr	dt_ai_clock
		tst.l	(a0)
		ble.b	.stop
		sub.l	d2,(a0)
		bra.b	.next
.stop		clr.l	(a0)			;was due: no credit
.next		addq.w	#1,d4
		cmp.w	d6,d4
		blo.b	.age
.serve		moveq	#-1,d3			;the earliest due, eligible object
		moveq	#1,d1
		move.w	d5,d4
.find		lea	(10596,a4),a1
		tst.b	(a1,d4.w)
		beq.b	.skip
		lea	(20056,a4),a1
		tst.b	(a1,d4.w)
		bne.b	.skip
		move.w	d4,d0
		bsr	dt_ai_clock
		move.l	(a0),d0
		bgt.b	.skip
		cmp.l	d1,d0
		bge.b	.skip
		move.l	d0,d1
		move.w	d4,d3
.skip		addq.w	#1,d4
		cmp.w	d6,d4
		blo.b	.find
		tst.w	d3
		bmi.b	.done
		move.w	d3,(a2)
		movem.l	d1-d7/a1-a2,-(a7)
		move.l	(dt_bh,pc),a0
		add.l	d7,a0
		jsr	(a0)			;the native decision for (A2)
		movem.l	(a7)+,d1-d7/a1-a2
		move.w	d3,d0
		bsr	dt_ai_clock
		add.l	#2<<24,(a0)		;the next in two seconds
		addq.w	#1,d3
		cmp.w	d6,d3
		blo.b	.ptr
		move.w	d5,d3
.ptr		move.w	d3,(a2)
		bra.b	.serve
.done		rts

; < D0.w object; > A0 its decision clock
dt_ai_clock	lsl.w	#2,d0
		add.w	#DTB3_AI,d0
		bra	dt_s3

; bh:f010 (plane D4), bh:12d14 (the object 10194): the countdown 2T and the clock 2 s
dt_ai_reset4	move.w	d4,d1
		bra	dt_ai_reset
dt_ai_reset94	move.w	(10194,a4),d1
dt_ai_reset	movem.l	d0/a0,-(a7)
		cmp.w	#16,d1
		bhs.b	.done
		move.w	d1,d0
		bsr	dt_ai_clock
		move.l	#2<<24,(a0)
.done		movem.l	(a7)+,d0/a0
		move.w	(BH_T,a4),d1		;as the replaced code
		add.w	d1,d1
		rts

;---------------------------------------------------------------------------
; FR-03: effects (bh:aec8: explosions, smoke, debris emission and removal) ran every
; T/8+1 steps: 4 times a second at T 4, 7.1 at T 50.  Here tm / (floor(tm/8)+1) times a
; second, each due tick running the native body (bh:aee2) once.
; FR-10: aircraft damage (bh:de16) every floor(T/3)+1 steps, now (floor(tm/3)+1)/tm s.
; FR-11: ships (bh:e28e) every 4T+1 steps, now (4tm+1)/tm s.
;---------------------------------------------------------------------------

; bh:aec8, replaced
dt_effects	movem.l	d0-d1/a0,-(a7)
		move.w	(dt_tm,pc),d0
		lsr.w	#3,d0
		addq.w	#1,d0
		bsr	dt_tmsteps
		move.w	#DTB3_FX,d0
		bsr	dt_s3
		bsr	dt_periodic
		bra.b	.next
.tick		movem.l	d0-d1/a0,-(a7)
		bsr	.body
		movem.l	(a7)+,d0-d1/a0
.next		dbf	d0,.tick
		movem.l	(a7)+,d0-d1/a0
		rts
.body		link	a5,#-22
		movem.l	d4-d5,-(a7)
		move.l	(dt_bh,pc),a0
		add.l	#$aee2,a0
		jmp	(a0)			;to its epilogue bh:b12c: unlk, rts here

; bh:de16, replaced
dt_air_damage	movem.l	d0-d1/a0,-(a7)
		move.w	(dt_tm,pc),d0
		and.l	#$ffff,d0
		divu.w	#3,d0
		addq.w	#1,d0
		bsr	dt_tmsteps
		move.w	#DTB3_AIRDMG,d0
		bsr	dt_s3
		bsr	dt_periodic
		bra.b	.next
.tick		movem.l	d0-d1/a0,-(a7)
		bsr	.body
		movem.l	(a7)+,d0-d1/a0
.next		dbf	d0,.tick
		movem.l	(a7)+,d0-d1/a0
		rts
.body		link	a5,#-8
		movem.l	d4-d5,-(a7)
		move.l	(dt_bh,pc),a0
		add.l	#$de3e,a0
		jmp	(a0)			;to bh:e16c

; bh:e28e, replaced
dt_ship_damage	movem.l	d0-d1/a0,-(a7)
		move.w	(dt_tm,pc),d0
		lsl.w	#2,d0
		addq.w	#1,d0
		bsr	dt_tmsteps
		move.w	#DTB3_SHIP,d0
		bsr	dt_s3
		bsr	dt_periodic
		bra.b	.next
.tick		movem.l	d0-d1/a0,-(a7)
		bsr	.body
		movem.l	(a7)+,d0-d1/a0
.next		dbf	d0,.tick
		movem.l	(a7)+,d0-d1/a0
		rts
.body		link	a5,#-8
		move.l	d4,-(a7)
		move.l	(dt_bh,pc),a0
		add.l	#$e2ac,a0
		jmp	(a0)			;to bh:e550

;---------------------------------------------------------------------------
; FR-20: the mission scan (bh:ecaa, once a step).  Its reminder (mode 10139 = 1) came
; every 40T+1 steps (10142), the condition scan every 4T+1 (10140).  Here (40tm+1)/tm
; and (4tm+1)/tm seconds; both are due at once when armed (the game cleared the count:
; bh:ef12, flight start).
;---------------------------------------------------------------------------

; bh:ecd0: tst.w 10142(a4); beq.s ecdc (the reminder) or on to ed0e
dt_wait40	movem.l	d0-d1/a0,-(a7)
		move.w	(dt_tm,pc),d0
		mulu.w	#40,d0
		addq.w	#1,d0
		bsr	dt_tmsteps
		move.w	#DTB3_W40,d0
		bsr	dt_wait_due
		movem.l	(a7)+,d0-d1/a0
		beq.b	.no
		addq.l	#$ecdc-$ecd6,(a7)
		rts
.no		add.l	#$ed0e-$ecd6,(a7)
		rts

; bh:ed12: tst.w 10140(a4); bne.w ef18 (to ef1c: no scan) or on to ed1a
dt_wait4	movem.l	d0-d1/a0,-(a7)
		move.w	(dt_tm,pc),d0
		lsl.w	#2,d0
		addq.w	#1,d0
		bsr	dt_tmsteps
		move.w	#DTB3_W4,d0
		bsr	dt_wait_due
		movem.l	(a7)+,d0-d1/a0
		beq.b	.no
		addq.l	#$ed1a-$ed18,(a7)
		rts
.no		add.l	#$ef1c-$ed18,(a7)
		rts

; < D0.w clock (DTB3_), D1.l period; > Z clear when due
dt_wait_due	bsr	dt_s3
		bsr	dt_periodic
		tst.w	d0
		rts

; bh:ef12: clr.w 10142(a4); bra.s ef1c (the reminder armed: due at once)
dt_wait40_arm	movem.l	d0/a0,-(a7)
		clr.w	(10142,a4)
		move.w	#DTB3_W40,d0
		bsr	dt_s3
		clr.l	(a0)
		movem.l	(a7)+,d0/a0
		addq.l	#$ef1c-$ef18,(a7)
		rts

;---------------------------------------------------------------------------
; Timers set as k x T: the player's bomb release wait 10216 (5T, bh:ce34, counted down
; at bh:c36c), and each object's timer 16816: a shot's life 2T (bh:c958), a bomb's and
; a fragment's 5T (bh:ce02, cf26), 180T (bh:d542), a falling object's drag interval 5T
; (bh:8408), a flak burst's delay (bh:e7ce, below); counted down by the falling objects
; (bh:83ea), class 6 (bh:8512), shots (bh:8588) and flak (bh:ebd2).  All through
; dt_cd_set/dt_cd_dec: k seconds whatever T does.  (FR-05 life, FR-08 release.)
;---------------------------------------------------------------------------

; bh:ce34: the count 5T into 10216 (bh:ce3c stores D0 again)
dt_bombcd_set	movem.l	d1/a0-a1,-(a7)
		move.w	(BH_T,a4),d1
		mulu.w	#5,d1
		lea	(10216,a4),a0
		move.l	(dt_buf,pc),a1
		add.w	#DTB_STEP3+DTB3_BOMBCD,a1
		bsr	dt_cd_set
		move.w	d1,d0
		movem.l	(a7)+,d1/a0-a1
		rts

; bh:c36c: tst.w 10216(a4); beq.s c376; subq.w #1,10216(a4) (the beq's target, bh:c376,
; is the next instruction, so the patch covers the test rather than the subtraction)
dt_bombcd_dec	tst.w	(10216,a4)
		beq.b	.done
		movem.l	a0-a1,-(a7)
		lea	(10216,a4),a0
		move.l	(dt_buf,pc),a1
		add.w	#DTB_STEP3+DTB3_BOMBCD,a1
		bsr	dt_cd_dec
		movem.l	(a7)+,a0-a1
.done		rts

;---------------------------------------------------------------------------
; FR-21: a message (bh:87f2) stays up 80 steps, counted down by bh:8862 (28522): 11.4 s
; at a mission T of 7, 1.6 s at T 50.  Here it stays 80 steps at the mission's T.
;---------------------------------------------------------------------------

; bh:8858: move.w #80,28522(a4)
dt_msg_set	movem.l	d0-d2/a0-a1,-(a7)
		moveq	#80,d1
		mulu.w	(BH_T,a4),d1
		moveq	#0,d2
		move.w	(dt_tm,pc),d2
		add.l	d2,d1
		subq.l	#1,d1
		divu.w	d2,d1			;ceil(80 T / tm) steps at T
		lea	(28522,a4),a0
		move.l	(dt_buf,pc),a1
		add.w	#DTB_STEP3+DTB3_MSG,a1
		bsr	dt_cd_set
		movem.l	(a7)+,d0-d2/a0-a1
		rts

; bh:886c: subq.w #1,28522(a4); tst.w 28522(a4) (then bne.s); the game tested it for 0
dt_msg_dec	movem.l	a0-a1,-(a7)
		lea	(28522,a4),a0
		move.l	(dt_buf,pc),a1
		add.w	#DTB_STEP3+DTB3_MSG,a1
		bsr	dt_cd_dec
		movem.l	(a7)+,a0-a1
		rts

; bh:c958: 2T; ce02, cf26, 8408: 5T; d542: 180T.  A0 16816(a4), D0.l object x 2;
; > D1.w the count (stored again by the game)
dt_life2	move.w	(BH_T,a4),d1
		add.w	d1,d1
		bra	dt_life_set
dt_life5	move.w	(BH_T,a4),d1
		mulu.w	#5,d1
		bra	dt_life_set
dt_life180	move.w	(BH_T,a4),d1
		mulu.w	#180,d1
		bra	dt_life_set

; bh:83ea: subq.w #1,(a0,d0.l); bra.s 8414
dt_life_drag	bsr	dt_life_dec
		add.l	#$8414-$83f0,(a7)
		rts

; bh:8512, 8588, ebd2: subq.w #1,(a0,d0.l), then the game tests it
dt_life_step	bra	dt_life_dec
dt_life_flak	bsr	dt_life_dec
		moveq	#0,d0
		rts

;---------------------------------------------------------------------------
; FR-01: falling objects (classes 4, 5, 9: bombs, fragments; bh:83c0).  Their vertical
; speed 16008 lost max(1, floor(11/T)) a step: 7 a second at T 7, 50 at T 50; and the
; height changed by round(round(v x 4660/256) / T), the rounding lost.  Here the
; speed loses tm max(1, floor(11/tm)) a second (7 at a mission T of 7, as on the A500)
; and the height moves by the step's mean speed x 4660/256 / T (the speed's carried
; fraction counted, as the integer speed trails the true one by half a unit), both with
; their fractions carried (the height's in the object's z fraction, dt_polar's): a fall
; covers the same height in the same time at every T.  The drag interval is a timer.
;---------------------------------------------------------------------------

; > D0.l the vertical speed's change a step in 16.16 (positive: down), the gravity of
; tm max(1, floor(11/tm)) a second at this T
dt_fall_rate	move.l	d2,-(a7)
		moveq	#11,d0
		divu.w	(dt_tm,pc),d0
		bne.b	.g
		moveq	#1,d0
.g		mulu.w	(dt_tm,pc),d0		;per second
		swap	d0
		clr.w	d0
		moveq	#0,d2
		move.w	(BH_T,a4),d2
		bsr	dt_ldiv			;16.16 per step
		move.l	(a7)+,d2
		rts

; bh:8440 (to bh:845e): -4(a5) = this step's change of the vertical speed, object D4
dt_fall_g	movem.l	d1/a0,-(a7)
		bsr	dt_fall_rate
		cmp.w	#DT_OBJECTS,d4
		bhs.b	.floor
		move.l	d0,d1
		move.w	d4,d0
		add.w	d0,d0
		add.w	#DTB3_VZF,d0
		bsr	dt_s3
		move.l	d1,d0
		moveq	#0,d1
		move.w	(a0),d1
		add.l	d1,d0
		move.w	d0,(a0)			;the change not yet taken off the speed
.floor		swap	d0
		neg.w	d0
		move.w	d0,(-4,a5)
		movem.l	(a7)+,d1/a0
		add.l	#$845e-$8446,(a7)
		rts

; bh:8470 (to bh:84e6): the height 12060 of object D4 moves by its mean vertical speed
; this step: the speed 16008 (just changed) less the change not yet taken off it, plus
; half the step's change, x 4660/256/T, in Q4 (|speed| under 4096; above, whole units)
dt_fall_z	movem.l	d1-d4/a0,-(a7)
		move.w	d4,d3
		add.w	d3,d3
		bsr	dt_fall_rate
		lsr.l	#1,d0
		move.l	d0,d1			;half the step's change
		lea	(16008,a4),a0
		move.w	(a0,d3.w),d0
		swap	d0
		clr.w	d0			;the speed, 16.16
		add.l	d1,d0
		cmp.w	#DT_OBJECTS*2,d3
		bhs.b	.q4
		move.l	d0,d1
		move.w	#DTB3_VZF,d0
		add.w	d3,d0
		bsr	dt_s3
		moveq	#0,d2
		move.w	(a0),d2
		move.l	d1,d0
		sub.l	d2,d0
.q4		add.l	#$800,d0
		asr.l	#8,d0
		asr.l	#4,d0			;the mean speed, Q4, rounded
		move.l	d0,d4			;sign
		bpl.b	.pos
		neg.l	d0
.pos		moveq	#0,d2
		move.w	(BH_T,a4),d2
		cmp.l	#$ffff,d0
		bhi.b	.big
		mulu.w	#4660/4,d0		;x = |v| x 16 x 4660/4; x/(1024 T) in 16.16 = x 64/T
		bsr	dt_ldivr		;q, r
		cmp.l	#$1ffffff,d0
		bhi.b	.whole
		lsl.l	#6,d0
		lsl.w	#6,d1
		and.l	#$ffff,d1
		divu.w	d2,d1
		and.l	#$ffff,d1
		add.l	d1,d0			;16.16
		tst.l	d4
		bpl.b	.carry
		neg.l	d0
.carry		cmp.w	#DT_OBJECTS*2,d3
		bhs.b	.add
		move.l	(dt_buf,pc),a0
		add.w	d3,a0
		add.w	d3,a0
		add.w	d3,a0			;DTB_FRAC: 6 bytes an object
		addq.l	#4,a0			;z
		moveq	#0,d1
		move.w	(a0),d1
		add.l	d1,d0
		move.w	d0,(a0)
.add		swap	d0
		ext.l	d0
.move		lea	(12060,a4),a0
		add.w	d3,d3
		add.l	d0,(a0,d3.w)
		movem.l	(a7)+,d1-d4/a0
		add.l	#$84e6-$8476,(a7)
		rts
.big		lsr.l	#4,d0			;whole units a second (never in flight)
		mulu.w	#4660/4,d0
		bsr	dt_ldivr
		lsr.l	#6,d0			;x 4/256
		bra.b	.sign
.whole		lsr.l	#8,d0
		lsr.l	#2,d0			;q / 1024
.sign		tst.l	d4
		bpl.b	.move
		neg.l	d0
		bra.b	.move

; < D0.l, D2.w divisor; > D0.l quotient, D1.l remainder
dt_ldivr	move.l	d3,-(a7)
		move.l	d0,d1
		clr.w	d1
		swap	d1
		divu.w	d2,d1
		move.l	d1,d3
		move.w	d0,d1
		divu.w	d2,d1
		swap	d3
		move.w	d1,d3
		move.l	d3,d0
		clr.w	d1
		swap	d1
		move.l	(a7)+,d3
		rts

;---------------------------------------------------------------------------
; FR-06: flak (bh:e556 makes a burst in slots 84..107).  Its delay 16816 is
; (distance >> k) x T steps, then a random jitter of -22(a5) steps is added or taken off
; (bh:e9d4, e9e8, ead0, eae4), and a count left at 0 or below becomes random & 7 steps
; (bh:ea16, eb12, eb40): the jitter was steps, so it shrank as T grew.  Here the jitter
; is the same number of steps at the mission's T (x T/tm), and when the burst is made
; (bh:e580) its delay becomes a timer in seconds.  The delay is limited to a word
; (bh:e7b2: at T 50 a far burst overflowed it).
;---------------------------------------------------------------------------

; < D0.w steps at the mission's T; > D0.w as many at T, rounded (at least 0)
dt_tmscale	movem.l	d1-d2,-(a7)
		move.w	d0,d1
		bpl.b	.pos
		neg.w	d0
.pos		mulu.w	(BH_T,a4),d0
		moveq	#0,d2
		move.w	(dt_tm,pc),d2
		lsr.w	#1,d2
		add.l	d2,d0
		divu.w	(dt_tm,pc),d0
		tst.w	d1
		bpl.b	.done
		neg.w	d0
.done		movem.l	(a7)+,d1-d2
		rts

; bh:e7b2: mulu.w 10184(a4),d0; move.w d0,-4(a5)
dt_flak_delay	mulu.w	(BH_T,a4),d0
		cmp.l	#$7fff,d0
		bls.b	.w
		move.w	#$7fff,d0
.w		move.w	d0,(-4,a5)
		rts

; bh:e9d4, ead0: move.w -22(a5),d0; add.w d0,(a0)
dt_flak_jadd	move.w	(-22,a5),d0
		bsr	dt_tmscale
		add.w	d0,(a0)
		rts
; bh:e9e8, eae4: move.w -22(a5),d0; sub.w d0,(a0)
dt_flak_jsub	move.w	(-22,a5),d0
		bsr	dt_tmscale
		sub.w	d0,(a0)
		rts
; bh:ea16, eb12, eb40: and.w #7,d0; move.w d0,(a0,d1.l)
dt_flak_j7	and.w	#7,d0
		bsr	dt_tmscale
		move.w	d0,(a0,d1.l)
		rts

; bh:e580, the burst constructor's exit: movem.l (sp)+,d4-d5; unlk a5; rts.  D5 the
; slot (108: none made)
dt_flak_end	cmp.w	#108,d5
		bhs.b	.ret
		movem.l	d0-d1/a0,-(a7)
		moveq	#0,d0
		move.w	d5,d0
		add.w	d0,d0
		lea	(16816,a4),a0
		move.w	(a0,d0.l),d1
		beq.b	.none
		bsr	dt_life_set
.none		movem.l	(a7)+,d0-d1/a0
.ret		movem.l	(a7)+,d4-d5
		unlk	a5
		rts

;---------------------------------------------------------------------------
; FR-13: a gunner's aim (bh:ca76) leads its target by 1, 2 or 4 of the target's last
; steps (13596/13644/13692) by distance: 4 steps were 0.57 s at T 7 and 0.08 s at T 50.
; Here as long as n steps at the mission's T: the step x n x T / tm.
;---------------------------------------------------------------------------

; bh:cac6, caf2, cb1e: jsr -32244(a4) (D0.l x D1.l: step x n); moveq #0,d1
dt_lead		movem.l	d2-d3,-(a7)
		mulu.w	(BH_T,a4),d1		;n x T
		move.l	d0,d3			;sign
		bpl.b	.pos
		neg.l	d0
.pos		move.l	d0,d2			;|step| x (n T), 32 x 16 bits
		swap	d2
		mulu.w	d1,d2
		swap	d2
		clr.w	d2
		mulu.w	d1,d0
		add.l	d2,d0
		moveq	#0,d2
		move.w	(dt_tm,pc),d2
		move.l	d2,d1
		lsr.w	#1,d1
		add.l	d1,d0
		bsr	dt_ldiv			;/ tm
		tst.l	d3
		bpl.b	.done
		neg.l	d0
.done		movem.l	(a7)+,d2-d3
		moveq	#0,d1
		rts

;---------------------------------------------------------------------------
; The hit test (bh:d942, a shot D4 against plane D5): after a coarse test at the shot's
; position, each axis passed if the shot crossed the plane on it between its last and
; this position (any distance) or stayed near (within 400): with long steps (low T) two
; axes could "cross" at different times, a hit the same shot at T 50 would miss.  Here
; the shot's segment relative to the plane must pass through the box of +-400 on all
; three axes at one time (TFH's dt_hit with BH's tolerance).  Relative positions: last
; -6/-10/-14(a5), this step -18/-22/-26(a5).
;---------------------------------------------------------------------------

DT_HITBOX	= 400

; bh:dae6 (after the attacker's bookkeeping): to the hit (bh:dbca) or the next plane
; (bh:dc5e)
dt_hit		movem.l	d0-d7/a0-a1,-(a7)
		bsr	dt_hit_test
		tst.l	d0
		beq.b	.miss
		movem.l	(a7)+,d0-d7/a0-a1
		add.l	#$dbca-$daec,(a7)
		rts
.miss		movem.l	(a7)+,d0-d7/a0-a1
		add.l	#$dc5e-$daec,(a7)
		rts

; > D0 = 1 for a hit, 0 for a miss; D1-D7/A0-A1 scratch.  (TFH's dt_hit_test.)
dt_hit_test	lea	(-6,a5),a0
		lea	(-18,a5),a1
		moveq	#0,d6			;entry = 0/1
		moveq	#1,d7
		move.l	d7,-(a7)		;exit denominator
		move.l	d7,-(a7)		;exit numerator = 1
		moveq	#2,d5
.axis		move.l	(a0),d4			;last
		move.l	(a1),d2			;this step
		subq.l	#4,a0
		subq.l	#4,a1
		cmp.l	d4,d2
		bge.b	.forward
		neg.l	d4			;reflect decreasing axes
		neg.l	d2
.forward	cmp.l	#DT_HITBOX,d4
		bgt	.miss
		cmp.l	#-DT_HITBOX,d2
		blt	.miss
		move.l	d2,d3
		sub.l	d4,d3			;displacement, >= 0
		cmp.l	#-DT_HITBOX,d4
		bge.b	.exit
		move.l	d2,-(a7)
		move.l	#-DT_HITBOX,d0
		sub.l	d4,d0			;entry numerator
		move.l	d0,-(a7)
		move.l	d3,d1
		move.l	d6,d2
		move.l	d3,-(a7)
		move.l	d7,d3
		bsr	dt_ratio_gt
		move.l	(a7)+,d3
		tst.l	d0
		beq.b	.entry_kept
		move.l	(a7),d6
		move.l	d3,d7
.entry_kept	addq.l	#4,a7
		move.l	(a7)+,d2
.exit		cmp.l	#DT_HITBOX,d2
		ble.b	.overlap
		move.l	#DT_HITBOX,d0
		sub.l	d4,d0			;exit numerator
		move.l	d0,d2
		move.l	(a7),d0
		move.l	(4,a7),d1
		bsr	dt_ratio_gt		;old exit later?
		tst.l	d0
		beq.b	.overlap
		move.l	d2,(a7)
		move.l	d3,(4,a7)
.overlap	move.l	d6,d0
		move.l	d7,d1
		move.l	(a7),d2
		move.l	(4,a7),d3
		bsr	dt_ratio_gt		;entry after exit: no common time
		tst.l	d0
		bne.b	.miss
		dbf	d5,.axis
		moveq	#1,d0
		bra.b	.done
.miss		moveq	#0,d0
.done		addq.l	#8,a7
		rts

; Unsigned D0/D1 > D2/D3?  D0 = 1 or 0, the others kept; 64-bit cross products
dt_ratio_gt	movem.l	d1-d7,-(a7)
		move.l	d2,d6
		move.l	d1,d7
		move.l	d3,d1
		bsr	dt_mul64
		move.l	d0,-(a7)
		move.l	d1,-(a7)
		move.l	d6,d0
		move.l	d7,d1
		bsr	dt_mul64
		move.l	(a7)+,d2
		move.l	(a7)+,d3
		cmp.l	d1,d2
		bhi.b	.yes
		blo.b	.no
		cmp.l	d0,d3
		bhi.b	.yes
.no		moveq	#0,d0
		bra.b	.done
.yes		moveq	#1,d0
.done		movem.l	(a7)+,d1-d7
		rts

; Unsigned D0 x D1 > D1:D0, D2-D7 kept
dt_mul64	movem.l	d2-d5,-(a7)
		move.l	d0,d2
		move.l	d0,d3
		swap	d3
		move.l	d1,d4
		move.l	d1,d5
		swap	d5
		mulu.w	d4,d0
		move.l	d3,d1
		mulu.w	d5,d1
		mulu.w	d5,d2
		mulu.w	d4,d3
		move.l	d2,d4
		swap	d4
		clr.w	d4
		add.l	d4,d0
		moveq	#0,d4
		addx.l	d4,d1
		swap	d2
		and.l	#$ffff,d2
		add.l	d2,d1
		move.l	d3,d4
		swap	d4
		clr.w	d4
		add.l	d4,d0
		moveq	#0,d4
		addx.l	d4,d1
		swap	d3
		and.l	#$ffff,d3
		add.l	d3,d1
		movem.l	(a7)+,d2-d5
		rts

;---------------------------------------------------------------------------
; FR-22: the replay.  BH films a flight's input, 4 words a step (bh:78aa), in a buffer
; of 1023 steps (bh:7902), from a saved state (bh:371a; 112 tables) and replays it a
; step a frame (bh:77fa) from that state.  At 50 steps a second the film held 20 s, and
; each step's T was not kept, so a replay at another frame rate was another flight.
; Here the film is DT_FILM steps in the allocated buffer (24864 points there: bh:77a2,
; bh:8eae) and each step's T beside it (dt_film_t; dt_frame sets T from it while
; 28474 = 1, a replay running); it ends when full or at DT_FILMSEC seconds.  timing.s's
; buffer (the fractions, the clocks above) is saved and restored with the game's two
; states (24868 the film's start, 24872 the flight left for the replay).  A replay runs
; a recorded step a frame: at the frame rate it was filmed at, it takes its time.
;---------------------------------------------------------------------------

; bh:77a2, 8eae: move.l 24852(a4),24864(a4): the film starts in our buffer
dt_film_start	move.l	a0,-(a7)
		move.l	(dt_buf,pc),a0
		add.l	#DTB_FILM,a0
		move.l	a0,(24864,a4)
		move.l	(dt_buf,pc),a0
		clr.l	(DTB_STEP3+DTB3_FILMTIME,a0)
		move.l	(a7)+,a0
		rts

; bh:78aa: movea.l 24864(a4),a0; addq.l #2,24864(a4): a step filmed, and its T
dt_film_rec	move.l	d0,-(a7)
		bsr	dt_film_index
		bhs.b	.full
		move.w	(BH_T,a4),(a0,d0.l)
.full		move.l	(a7)+,d0
		movea.l	(24864,a4),a0
		addq.l	#2,(24864,a4)
		rts

; > D0.l the film step x 2 at 24864, A0 the T beside the film; C clear within the film
dt_film_index	move.l	(24864,a4),d0
		move.l	(dt_buf,pc),a0
		add.l	#DTB_FILM,a0
		sub.l	a0,d0
		lsr.l	#2,d0			;step x 2
		add.l	#DTB_FILMT-DTB_FILM,a0
		cmp.l	#DT_FILM*2,d0
		rts

; bh:7902: addq.w #1,28498(a4); cmpi.w #1023,28498(a4) (then bne.s on): full when
; DT_FILM steps or DT_FILMSEC seconds are filmed
dt_film_count	movem.l	d1-d2/a0,-(a7)
		addq.w	#1,(28498,a4)
		move.l	#$10000-1,d0		;the step, ceil(2^16/T)
		moveq	#0,d2
		move.w	(BH_T,a4),d2
		add.l	d2,d0
		bsr	dt_ldiv
		move.l	(dt_buf,pc),a0
		add.l	(DTB_STEP3+DTB3_FILMTIME,a0),d0
		move.l	d0,(DTB_STEP3+DTB3_FILMTIME,a0)
		moveq	#0,d1			;Z set: full
		cmp.l	#DT_FILMSEC<<16,d0
		bhs.b	.done
		cmp.w	#DT_FILM,(28498,a4)
		bhs.b	.done
		moveq	#1,d1
.done		tst.w	d1
		movem.l	(a7)+,d1-d2/a0
		rts

; From dt_frame while a replay runs: T from the film
dt_film_t	movem.l	d0/a0,-(a7)
		bsr	dt_film_index
		bhs.b	.done
		move.w	(a0,d0.l),d0
		beq.b	.done
		move.w	d0,(BH_T,a4)
		lsr.w	#3,d0
		addq.w	#1,d0
		move.w	d0,(BH_T8,a4)
.done		movem.l	(a7)+,d0/a0
		rts

; bh:371a (save), bh:377a (restore): link.w a5,#-6; movem.l d4-d5,-(sp), with the
; state 4(sp) (after our return) one of 24868, 24872: timing.s's state with it
dt_state_save	moveq	#0,d0
		bra	dt_state
dt_state_load	moveq	#1,d0
dt_state	move.l	(8,a7),d1		;the game's state
		move.l	(dt_buf,pc),a0
		move.l	#DTB_COMPA,a1
		cmp.l	(24868,a4),d1
		beq.b	.which
		move.l	#DTB_COMPB,a1
		cmp.l	(24872,a4),d1
		bne.b	.frame
.which		add.l	a0,a1
		tst.w	d0
		beq.b	.copy
		exg	a0,a1			;restore: from the copy
.copy		move.w	#DTB_STATE/4-1,d1
.c		move.l	(a0)+,(a1)+
		dbf	d1,.c
		tst.w	d0
		beq.b	.frame
		lea	(dt_live,pc),a0		;after a restore: frame timing anew
		clr.w	(a0)
.frame		move.l	(a7)+,a0		;the game's frame, as the replaced code
		link	a5,#-6
		movem.l	d4-d5,-(a7)
		jmp	(a0)
