;*---------------------------------------------------------------------------
; flight.s: the flight's patches (gs2.run, 4.0b), shared by the three slaves. Each version's
; gs2.run is a build of one source; the slave defines where its build has each place
; (found by aligning the code hunks, docs/internals.md "Flight"), and comments give the AGA
; offsets. Before including this file:
;
;   G_* code offsets: G_DT G_CLOCK G_PHASE G_WAIT G_BLINK G_VBL G_COLLECTIVE_UP
;	G_COLLECTIVE_DOWN G_SPEED G_SPEED_STEP G_HEADING G_CLIMB G_FILL G_COLOURS G_LINE
;	G_STACK G_MODELS G_SEED G_START G_SIZE, and G_RECT where the rectangles are drawn at
;	once (not the ECS build, which queues them), and G_LOADVIEW where the game clears
;	LoadView's View with suba.w a1,a1 (AGA, CD32)
;   B_* BSS offsets: B_TICKS B_DT B_VBL B_PAUSE B_PHASE B_BLINK B_CLIMB_TARGET B_CLIMB
;	B_COLLECTIVE B_PATTERNS B_DRAWN, B_RECTS with G_RECT
;   D_* data offsets: D_EDGES D_HEAP D_MODELS D_MODELS_NEXT, and D_SAVESP for a flight on its
;	process stack, or SUPERVISOR_STACK for one that takes the machine over (ECS)
;   GS_RAND, GS_TIME_HUNK, GS_MISSION_HUNK: the front end gs, for VERIFY
;   LINES_CPU: the lowest CPU (AFB_*) the CPU lines are used on, or undefined for all
;
; The slave calls flight_gs2 (D1 gs2.run's seglist) and, in VERIFY builds, flight_gs (D1 gs's
; seglist) from its _cb_dosLoadSeg. The hunk pointers are kept $8000 on (gs2_*8), so that
; d16 displacements reach every offset on a 68000.
;---------------------------------------------------------------------------*

MODELS_SIZE	= $21000	; the largest model data block moved to fast memory
SSTACK_SIZE	= 2000		; SUPERVISOR_STACK: the flight's own 2000 bytes

; < D1: gs2.run's seglist
flight_gs2
	movem.l	d0-d2/a0-a2/a6,-(a7)
	move.l	_resload(pc),a2
	lea	fl_tags(pc),a0
	jsr	resload_Control(a2)
	lea	gs2_code(pc),a2		; the hunks
	moveq	#0,d2
.hunks	move.l	4(a7),d1
	move.l	d2,d0
	bsr	flight_hunk
	move.l	a1,d0
	tst.w	d2
	bne.b	.biased
	move.l	d0,(a2)+		; gs2_code
.biased	add.l	#$8000,d0
	move.l	d0,(a2)+		; gs2_code8, gs2_data8, gs2_bss8
	addq.w	#1,d2
	cmp.w	#3,d2
	bne.b	.hunks
	; fast memory for the model data (and the ECS flight's supervisor stack), allocated on the
	; first flight and kept: while the flight runs, the ECS version has the OS switched off
	move.l	4.w,a6
	lea	fm_block(pc),a0
	tst.l	(a0)
	bne.b	.havem
	move.l	#MODELS_SIZE,d0
	move.l	#MEMF_FAST,d1
	jsr	(_LVOAllocMem,a6)
	lea	fm_block(pc),a0
	move.l	d0,(a0)
.havem
	IFD SUPERVISOR_STACK
	lea	fs_block(pc),a0
	tst.l	(a0)
	bne.b	.haves
	move.l	#SSTACK_SIZE,d0
	move.l	#MEMF_FAST,d1
	jsr	(_LVOAllocMem,a6)
	lea	fs_block(pc),a0
	move.l	d0,(a0)
.haves
	ENDC
	move.l	_resload(pc),a2
	move.l	gs2_code(pc),a1
	lea	pl_gs2_flight(pc),a0
	jsr	resload_Patch(a2)
	; the renderer's one-colour rectangles and lines by the CPU, and on a 68030 or later also
	; the polygon spans (cf_*, cl_* below; on the 68020 the blitter's spans are faster)
	move.l	_attnflags(pc),d2	; KickEmu's (WHDLTAG_ATTNFLAGS_GET)
	IFD G_RECT
	move.l	gs2_code(pc),a1
	lea	pl_gs2_rect(pc),a0
	jsr	resload_Patch(a2)
	ENDC
	btst	#AFB_68030,d2
	beq.b	.nospans
	move.l	gs2_code(pc),a1
	lea	pl_gs2_spans(pc),a0
	jsr	resload_Patch(a2)
.nospans
	IFD LINES_CPU
	btst	#LINES_CPU,d2
	beq.b	.nolines
	ENDC
	move.l	gs2_code(pc),a1
	lea	pl_gs2_lines(pc),a0
	jsr	resload_Patch(a2)
.nolines
	; CUSTOM2=1: the frame rate is no longer capped (fps_* below)
	move.l	fl_custom2(pc),d0
	beq.b	.nofps
	move.l	gs2_code(pc),a1
	lea	pl_gs2_fps(pc),a0
	jsr	resload_Patch(a2)
	move.l	gs2_code(pc),a1
	bsr	fps_dither_sites
.nofps
	jsr	resload_FlushCache(a2)
	movem.l	(a7)+,d0-d2/a0-a2/a6
	rts

; < D0: hunk number, D1: seglist   > A1: the hunk's start
flight_hunk
	move.l	d1,a1
	bra.b	.next
.loop	move.l	(a1),a1
.next	add.l	a1,a1
	add.l	a1,a1
	dbf	d0,.loop
	addq.l	#4,a1
	rts

fl_tags		dc.l	WHDLTAG_CUSTOM2_GET
fl_custom2	dc.l	0
	IFD VERIFY
		dc.l	WHDLTAG_CUSTOM3_GET
fl_custom3	dc.l	0	; VERIFY: frames of at least this many fields (CUSTOM2=1)
	ENDC
		dc.l	TAG_DONE

gs2_code	dc.l	0
gs2_code8	dc.l	0	; the hunks + $8000
gs2_data8	dc.l	0
gs2_bss8	dc.l	0
fm_block	dc.l	0	; fast memory for the model data, or 0
	IFD SUPERVISOR_STACK
fs_block	dc.l	0	; fast memory for the supervisor stack, or 0
	ENDC

pl_gs2_flight
	PL_START
	IFD SUPERVISOR_STACK
	PL_PS	G_STACK,fast_super_stack	; the flight's supervisor stack in fast memory
	ELSE
	PL_PS	G_STACK,fast_stack	; keep the stack in fast memory
	ENDC
	PL_S	G_STACK+6,$a
	PL_PS	G_MODELS,fast_models	; the model data in fast memory
	IFD G_LOADVIEW
	PL_W	G_LOADVIEW,$93c9	; suba.l a1,a1: LoadView(NULL). The game's suba.w
					; leaves a1 nonzero from $8000 up, which
					; gives LoadView a View (with MMU: a fault)
	ENDC
	IFD VERIFY
	PL_PS	G_SEED,seed_flight	; move.w VHPOSR,bss+$b8fe: the flight's random seed
	ENDC
	PL_END

; CUSTOM2=1. The frame loop (AGA code $28-$304) waited for 6 ticks of the 64 Hz CIA-B timer a
; frame (at most 10.67 fps) and stepped the simulation by the ticks since the last frame.
; Now a frame takes at least one field, and the step is the fields since the last frame
; (frames are presented on the VBL anyway, COP1LC), with the remainders carried:
pl_gs2_fps
	PL_START
	PL_PS	G_DT,fps_dt		; dt from the fields, not the ticks
	PL_S	G_DT+6,$1c
	PL_PS	G_CLOCK,fps_clock	; the mission clock's add, remainder carried
	PL_S	G_CLOCK+6,8
	PL_PS	G_PHASE,fps_phase	; the per-frame phases every 6 ticks of game time
	PL_S	G_PHASE+6,$e
	PL_PS	G_WAIT,fps_wait		; the cap: one field instead of 6 ticks
	PL_S	G_WAIT+6,6
	PL_PS	G_BLINK,fps_blink	; likewise the blink
	PL_PS	G_VBL,fps_vbl		; count the fields (not while paused)
	PL_PS	G_START,fps_start	; the flight's first frame
	PL_NOP	G_START+6,2
	PL_PS	G_SPEED,fps_speed	; the speed's approach once per 6 ticks
	PL_NOP	G_SPEED+6,2
	PL_PS	G_CLIMB,fps_climb	; the climb rate's approach once per 6 ticks
	PL_NOP	G_CLIMB+6,2
	PL_PS	G_COLLECTIVE_UP,fps_collective	; the collective keys once per 6 ticks
	PL_PS	G_COLLECTIVE_DOWN,fps_collective
	PL_END

	IFD G_RECT
pl_gs2_rect
	PL_START
	PL_P	G_RECT,cf_rect		; one-colour rectangles by the CPU, not a blit a plane
	PL_END
	ENDC

pl_gs2_spans
	PL_START
	PL_P	G_FILL,cf_fill		; the polygon spans by the CPU, not one blit each
	PL_END

pl_gs2_lines
	PL_START
	PL_P	G_LINE,cl_line		; the lines by the CPU, not a line blit a plane
	PL_END

	IFD SUPERVISOR_STACK
; The ECS flight takes the machine over (a trap, then SR $2700) and moves its supervisor stack
; onto the first 2000 bytes of its chip work area (heap pointer data+$2c3c in the ECS build).
; Here onto fast memory instead, still taking the 2000 bytes, so the heap is laid out as
; before. No fast memory: the work area, as before.
fast_super_stack
	move.l	(a7)+,a0		; the return (A0 and A1 are set again after)
	move.l	gs2_data8(pc),a1
	add.l	#SSTACK_SIZE,D_HEAP-$8000(a1)
	move.l	fs_block(pc),d0
	beq.b	.chip
	add.l	#SSTACK_SIZE,d0
	move.l	d0,a7
	jmp	(a0)
.chip	move.l	D_HEAP-$8000(a1),a7
	jmp	(a0)
	ELSE
; The flight moved its stack onto the first 2000 bytes of its chip work area (heap pointer
; data+$2c3e). Stay on the process stack (ExpMem) and still take the 2000 bytes, so the
; heap is laid out as before. A5 = data+$2dfc, where the process stack pointer was saved.
fast_stack
	add.l	#2000,-(D_SAVESP-D_HEAP)(a5)
	rts
	ENDC

; The flight's model data (the front end's chip block data+$922a, read by the transform and
; the object code, not the blitter), before $18b8c turns its offsets into addresses: copied
; up to the next block (data+$9232) into fm_block. A larger block or no memory: the chip
; block, as before. > A0 = the block, as replaced.
fast_models
	movem.l	d0-d2/a1-a2,-(a7)
	move.l	gs2_data8(pc),a2
	move.l	D_MODELS_NEXT-$8000(a2),d2
	sub.l	D_MODELS-$8000(a2),d2	; to the next block
	bls.b	.keep
	cmp.l	#MODELS_SIZE,d2
	bhi.b	.keep
	move.l	fm_block(pc),d0
	beq.b	.keep
	move.l	d0,a1
	move.l	D_MODELS-$8000(a2),a0
	move.l	d0,D_MODELS-$8000(a2)
	addq.l	#3,d2
	lsr.l	#2,d2
.copy	move.l	(a0)+,(a1)+
	subq.l	#1,d2
	bne.b	.copy
.keep	move.l	D_MODELS-$8000(a2),a0
	movem.l	(a7)+,d0-d2/a1-a2
	rts

	IFD VERIFY
; < D1: gs's seglist. The same mission on every machine and slave. random() (AGA hunk 97)
; seeds from time() on its first call: a constant instead. The office animations then call it
; a timing-dependent number of times, so the mission setup (AGA hunk 22: time of day, ...)
; also reseeds.
flight_gs
	movem.l	d0-d1/a0-a2,-(a7)
	move.l	_resload(pc),a2
	moveq	#0,d0
	bsr	flight_hunk
	move.l	GS_RAND(a1),d0		; rand's move.w seed,d0: the seed's address
	lea	verify_seed(pc),a0
	move.l	d0,(a0)
	move.l	4(a7),d1
	moveq	#GS_TIME_HUNK,d0
	bsr	flight_hunk
	lea	pl_gs_time(pc),a0
	jsr	resload_Patch(a2)
	move.l	4(a7),d1
	moveq	#GS_MISSION_HUNK,d0
	bsr	flight_hunk
	lea	pl_gs_mission(pc),a0
	jsr	resload_Patch(a2)
	movem.l	(a7)+,d0-d1/a0-a2
	rts

pl_gs_time
	PL_START
	PL_L	$aa,$70014E71		; move.l -4(a5),d0 (the time) -> moveq #1,d0
	PL_END

pl_gs_mission
	PL_START
	PL_PS	$2a40,reseed_mission	; moveq #0,d0; move.l d0,d5; move.w d5,-18(a5)
	PL_NOP	$2a46,2
	PL_END

verify_seed
	dc.l	0

reseed_mission
	move.l	a0,-(a7)
	move.l	verify_seed(pc),a0
	move.w	#1,(a0)
	move.l	(a7)+,a0
	moveq	#0,d0
	move.l	d0,d5
	move.w	d5,-18(a5)
	rts

; A constant flight seed; the seed's address is the instruction's operand after the jsr.
seed_flight
	move.l	a0,-(a7)
	move.l	4(a7),a0
	move.l	(a0),a0
	move.w	#1,(a0)
	move.l	(a7)+,a0
	addq.l	#4,(a7)
	rts
	ENDC

; Enhanced framerate (CUSTOM2=1). dt (bss+$c67e) is 32768 per 15 ticks of 64 Hz; per
; field that is 2097152/750 on PAL (50 Hz), 2097152/900 on NTSC (60 Hz).
fps_k		dc.w	0	; 6-tick periods this simulation step completes
fps_fields	dc.w	0	; fields since the last frame, counted while not paused
fps_shift	dc.w	20	; dt = (fields << shift + fps_rem) / fps_den
fps_den		dc.w	375
fps_max		dc.w	11	; more fields: dt 32767, the game's own clamp (15 ticks)
fps_rem		dc.w	0
fps_crem	dc.l	0	; the clock's remainder, 32nds
fps_pacc	dc.l	0	; game time toward the next phase step, dt * 5 (65536 = 6 ticks)
fps_bacc	dc.l	0	; the same for the blink

; code $18430, the flight's setup: move.w #15,bss+$c680 (the ticks)
fps_start
	movem.l	d0-d3/a0,-(a7)
	move.l	gs2_bss8(pc),a0
	move.w	#15,B_TICKS-$8000(a0)
	lea	fps_fields(pc),a0
	move.w	#99,(a0)		; the first frame: dt 32767, as the game's 15 ticks
	clr.w	fps_rem-fps_fields(a0)
	clr.l	fps_crem-fps_fields(a0)
	clr.l	fps_pacc-fps_fields(a0)
	clr.l	fps_bacc-fps_fields(a0)
	; PAL or NTSC from the highest line of a field (WHDLoad's PAL/NTSC options included)
	bsr	.line
.wrap	move.w	d0,d1
	bsr	.line
	cmp.w	d1,d0
	bhs.b	.wrap
	moveq	#0,d2
.field	cmp.w	d2,d0
	bls.b	.next
	move.w	d0,d2
.next	move.w	d0,d1
	bsr	.line
	cmp.w	d1,d0
	bhs.b	.field
	move.l	#(20<<16)|375,d0	; PAL
	moveq	#11,d1
	cmp.w	#288,d2
	bhs.b	.pal
	move.l	#(19<<16)|225,d0	; NTSC: 2097152/900 = 524288/225
	moveq	#14,d1
.pal	move.l	d0,fps_shift-fps_fields(a0)
	move.w	d1,fps_max-fps_fields(a0)
	movem.l	(a7)+,d0-d3/a0
	rts
; > D0.w: the beam's line, read until two reads agree
.line	move.l	$dff004,d0
	lsr.l	#8,d0
	and.w	#$1ff,d0
	move.l	$dff004,d3
	lsr.l	#8,d3
	and.w	#$1ff,d3
	cmp.w	d0,d3
	bne.b	.line
	rts

; code $608, the VBL client: addq.w #1,bss+$b8fc
fps_vbl
	move.l	a0,-(a7)
	move.l	gs2_bss8(pc),a0
	addq.w	#1,B_VBL-$8000(a0)
	tst.b	B_PAUSE-$8000(a0)		; paused: the CIA-B server stops the ticks too
	bne.b	.paused
	lea	fps_fields(pc),a0
	addq.w	#1,(a0)
.paused	move.l	(a7)+,a0
	rts

; code $28: > D0.w = bss+$c67e = dt for the fields since the last frame
fps_dt
	movem.l	d1/a0-a1,-(a7)
	move.l	gs2_bss8(pc),a0
	clr.w	B_TICKS-$8000(a0)
	lea	fps_fields(pc),a1
	moveq	#0,d0
	move.w	(a1),d0
	sub.w	d0,(a1)			; one instruction: no field lost to the VBL
	cmp.w	fps_max-fps_fields(a1),d0
	bls.b	.step
	clr.w	fps_rem-fps_fields(a1)
	move.w	#32767,d0
	bra.b	.set
.step	move.w	fps_shift-fps_fields(a1),d1
	lsl.l	d1,d0
	moveq	#0,d1
	move.w	fps_rem-fps_fields(a1),d1
	add.l	d1,d0
	divu.w	fps_den-fps_fields(a1),d0
	swap	d0
	move.w	d0,fps_rem-fps_fields(a1)
	swap	d0
.set	move.w	d0,B_DT-$8000(a0)
	movem.l	(a7)+,d1/a0-a1
	rts

; code $78: > D0.w = dt * 15360 / 32768 (= dt * 15 / 32), the remainder carried
fps_clock
	movem.l	d1/a0-a1,-(a7)
	move.l	gs2_bss8(pc),a0
	lea	fps_pacc(pc),a1
	bsr	fps_steps
	lea	fps_k(pc),a1
	move.w	d0,(a1)			; this step's 6-tick periods
	moveq	#0,d0
	move.w	B_DT-$8000(a0),d0
	mulu.w	#15,d0
	lea	fps_crem(pc),a0
	add.l	(a0),d0
	moveq	#31,d1
	and.l	d0,d1
	move.l	d1,(a0)
	lsr.l	#5,d0
	movem.l	(a7)+,d1/a0-a1
	rts

; code $2a8, once per simulation step: not.b bss+$c68b; bss+$c68c = (bss+$c68c + 1) & 3,
; now once per 6 ticks of game time
fps_phase
	movem.l	d0/a0,-(a7)
	move.l	gs2_bss8(pc),a0
	move.w	fps_k(pc),d0
	bra.b	.test
.step	not.b	B_PHASE-$8000(a0)
	addq.b	#1,B_PHASE+1-$8000(a0)
	and.b	#3,B_PHASE+1-$8000(a0)
.test	dbf	d0,.step
	movem.l	(a7)+,d0/a0
	rts

; What the flight model does per step without dt, at the cap once per 6 ticks, now once per
; 6 ticks of game time (fps_k times a step), so it keeps its rate.

; code $7716: bsr $7c04 (the speed approaches its target by 1/8 or 1/16 of the gap, or 1);
; bsr $7dda (the heading)
fps_speed
	movem.l	d0/a0,-(a7)
	move.w	fps_k(pc),d0
	bra.b	.test
.step	movem.l	d0-a6,-(a7)
	move.l	gs2_code8(pc),a0
	jsr	G_SPEED_STEP-$8000(a0)
	movem.l	(a7)+,d0-a6
.test	dbf	d0,.step
	movem.l	(a7)+,d0/a0
	move.l	gs2_code8(pc),-(a7)	; then $7dda, returning to $771c
	add.l	#G_HEADING-$8000,(a7)
	rts

; code $7950: asr.w #2,d1; add.w d1,bss+$2cc (the climb rate moves a quarter of the way to
; bss+$2ca, or the rest when within 16); D1 = bss+$2ca - bss+$2cc, more than 16 apart
fps_climb
	movem.l	d0/d2/a0,-(a7)
	move.l	gs2_bss8(pc),a0
	move.w	fps_k(pc),d0
	bra.b	.test
.step	move.w	B_CLIMB_TARGET-$8000(a0),d1
	sub.w	B_CLIMB-$8000(a0),d1
	move.w	d1,d2
	bpl.b	.pos
	neg.w	d2
.pos	cmp.w	#16,d2
	bgt.b	.quarter
	move.w	B_CLIMB_TARGET-$8000(a0),B_CLIMB-$8000(a0)
	bra.b	.done
.quarter
	asr.w	#2,d1
	add.w	d1,B_CLIMB-$8000(a0)
.test	dbf	d0,.step
.done	movem.l	(a7)+,d0/d2/a0
	rts

; codes $1212 and $1268, the keys = and - (collective up and down): clr.w bss+6, then a step
; of the collective each time they are called (each simulation step the key is held)
fps_collective
	move.l	a0,-(a7)
	lea	fps_k(pc),a0
	tst.w	(a0)
	beq.b	.skip
	move.l	gs2_bss8(pc),a0
	clr.w	B_COLLECTIVE-$8000(a0)
	move.l	(a7)+,a0
	rts
.skip	move.l	(a7)+,a0
	addq.l	#4,a7			; not this step: return from the key's routine
	rts

; code $2fe, once per frame: not.b bss+$c68a (a blink), now once per 6 ticks
fps_blink
	movem.l	d0/a0-a1,-(a7)
	move.l	gs2_bss8(pc),a0
	lea	fps_bacc(pc),a1
	bsr.b	fps_steps
	btst	#0,d0
	beq.b	.even
	not.b	B_BLINK-$8000(a0)
.even	movem.l	(a7)+,d0/a0-a1
	rts

; < A0: bss, A1: an accumulator   > D0.w: how many 6-tick periods dt completes
fps_steps
	move.l	d1,-(a7)
	moveq	#0,d0
	move.w	B_DT-$8000(a0),d0
	mulu.w	#5,d0
	add.l	(a1),d0
	moveq	#0,d1
	move.w	d0,d1
	move.l	d1,(a1)
	clr.w	d0
	swap	d0
	move.l	(a7)+,d1
	rts

; The simulation's x * dt products, muls.w bss+$c67e,Dn; add.l Dn,Dn; swap Dn (84 of them),
; truncate: a frame loses up to one unit of each, so at small dt slow processes (the bank
; levelling out, ...) lose a larger share. Each becomes jsr fps_dtm<n>; nop; swap Dn, which adds
; a uniform fraction before the swap: the result is right on average, and 0 stays 0.
; < A1: gs2.run's code
fps_dither_sites
	movem.l	d0-d4/a0-a2,-(a7)
	move.l	gs2_bss8(pc),d1
	add.l	#B_DT-$8000,d1
	lea	fps_dtp(pc),a0
	move.l	d1,(a0)
	move.l	a1,a2
	add.l	#G_SIZE-10,a2		; the code hunk's size
	lea	fps_dtm0(pc),a0
	moveq	#0,d4
.scan	move.w	(a1),d0
	move.w	d0,d2
	and.w	#$f1ff,d2
	cmp.w	#$c1f9,d2		; muls.w abs.l,Dn
	bne.b	.next
	cmp.l	2(a1),d1
	bne.b	.next
	move.w	d0,d2
	and.w	#$0e00,d2		; Dn << 9
	move.w	d2,d3
	or.w	#$d080,d3		; add.l Dn,Dn
	lsr.w	#8,d2
	lsr.w	#1,d2
	or.w	d2,d3
	cmp.w	6(a1),d3
	bne.b	.next
	move.w	d2,d3
	or.w	#$4840,d3		; swap Dn
	cmp.w	8(a1),d3
	bne.b	.next
	mulu.w	#fps_dtm1-fps_dtm0,d2
	add.l	a0,d2
	move.w	#$4eb9,(a1)		; jsr fps_dtm<n>
	move.l	d2,2(a1)
	move.w	#$4e71,6(a1)		; nop
	addq.w	#1,d4
	lea	10(a1),a1
	bra.b	.more
.next	addq.l	#2,a1
.more	cmp.l	a2,a1
	bls.b	.scan
	lea	fps_sites(pc),a0
	move.w	d4,(a0)
	movem.l	(a7)+,d0-d4/a0-a2
	rts

fps_sites	dc.w	0	; how many were patched (84)
fps_dtp		dc.l	0	; bss+$c67e
	cnop	0,4
fps_dither	dc.l	0	; the high word stays 0

DTM	MACRO
fps_dtm\1
	move.l	a0,-(a7)
	move.l	fps_dtp(pc),a0
	muls.w	(a0),d\1
	add.l	d\1,d\1
	lea	fps_dither(pc),a0
	add.w	#40503,2(a0)		; 65536 / the golden ratio: evenly spread
	add.l	(a0),d\1
	move.l	(a7)+,a0
	rts
	ENDM

	DTM	0
	DTM	1
	DTM	2
	DTM	3
	DTM	4
	DTM	5
	DTM	6
	DTM	7

; code $2c6: wait for a field since the last frame (then COP1LC shows this one)
fps_wait
	move.l	a0,-(a7)
	lea	fps_fields(pc),a0
	IFD VERIFY
	move.l	d0,-(a7)
	move.l	fl_custom3(pc),d0
	bne.b	.min
	moveq	#1,d0
.min	cmp.w	(a0),d0
	bhi.b	.min
	move.l	(a7)+,d0
	ELSE
.wait	tst.w	(a0)
	beq.b	.wait
	ENDC
	move.l	(a7)+,a0
	rts

; code $fd3c: a line by the CPU (the game: a line blit a plane, BLTCON0 $xbca: where the line's
; pixel is, the plane's bit of the colour, elsewhere the screen). The same pixels as the
; blitter's line mode: the game's octant and error terms, the pixel, then (error not
; negative) a step on the minor axis and error + BLTAMOD (else + BLTBMOD), a step on the major
; axis, the sign of the new error. Pixels in one word of a row are written together.
; < D0.w/D1.w the start x, y, D2.w/D3.w the end, D4.b the colour (through the table at code
;   $fcf8), the screen bss+$b8dc, rows of 160 bytes, 4 planes of 40
; > as the game's: D0.w BLTCON0, D1 the last plane's B, D2.w -1, D3.w BLTSIZE, D4.w the
;   colour >> 4, D5.w BLTCON1, D6 the start + 160, A5 $dff000, and the blitter registers it set
cl_line
	movem.l	d7/a0-a2,-(a7)
	move.l	gs2_code8(pc),a5
	move.l	G_COLOURS-$8000(a5),a5
	ext.w	d4
	move.b	(a5,d4.w),d4		; D4: the colour
	move.w	#160,d6			; the game's setup from here
	mulu.w	d1,d6
	move.w	d0,d5
	lsr.w	#4,d5
	add.w	d5,d5
	add.w	d5,d6
	move.l	gs2_bss8(pc),a5
	add.l	B_DRAWN-$8000(a5),d6		; D6: the start's word
	moveq	#0,d5
	sub.w	d1,d3
	roxl.b	#1,d5
	tst.w	d3
	bge.b	.ady
	neg.w	d3
.ady	sub.w	d0,d2
	roxl.b	#1,d5
	tst.w	d2
	bge.b	.adx
	neg.w	d2
.adx	move.w	d3,d1
	sub.w	d2,d1
	bge.b	.ymaj
	exg	d2,d3
.ymaj	roxl.b	#1,d5			; D5: dy < 0, dx < 0, x major
	move.w	d5,d7			; D7: the same
	lea	cl_octants(pc),a5
	move.b	(a5,d5.w),d5		; D5: BLTCON1
	addq.w	#1,d3			; D3: the pixels
	add.w	d2,d2			; D2: BLTBMOD
	move.w	d2,d1
	sub.w	d3,d1			; D1: the error (BLTAPTL)
	bge.b	.pos
	or.b	#$40,d5			; SIGN
.pos	move.w	d1,a1
	sub.w	d3,a1			; A1: BLTAMOD
	and.w	#15,d0
	move.w	d0,a2
	ror.w	#4,d0
	or.w	#$bca,d0		; D0: BLTCON0
	lea	$dff002,a5
	tst.b	(a5)
.bwait	btst	#6,(a5)			; the game's own blits first
	bne.b	.bwait
	lea	-2(a5),a5
	move.w	d0,$40(a5)		; BLTCON0
	move.w	d5,$42(a5)		; BLTCON1
	move.w	#-1,$44(a5)		; BLTAFWM
	move.w	d1,$52(a5)		; BLTAPTL
	move.w	#160,$60(a5)		; BLTCMOD
	move.w	d2,$62(a5)		; BLTBMOD
	move.w	a1,$64(a5)		; BLTAMOD
	move.w	#160,$66(a5)		; BLTDMOD
	move.w	#$8000,$74(a5)		; BLTADAT
	movem.l	d0/d3/d5-d6,-(a7)
	move.w	a2,d0
	move.w	#$8000,d5
	lsr.w	d0,d5
	move.w	d5,d0			; D0: the pixel's bit in its word
	move.l	d6,a0			; A0: its word
	and.w	#1023,d3		; BLTSIZE's height
	bne.b	.h
	move.w	#1024,d3
.h	subq.w	#1,d3
	move.w	#160,a2
	btst	#2,d7
	beq.b	.down
	move.w	#-160,a2		; A2: the step in y
.down	moveq	#0,d6			; D6: the pixels of this word
	lsr.b	#1,d7
	bcc.b	.yloop
	lsr.b	#1,d7
	bcs.b	.xdec
; x major, x up
.xinc	or.w	d0,d6
	tst.w	d1
	bmi.b	.xib
	add.w	a1,d1
	bsr.w	.plot
	add.l	a2,a0
	bra.b	.xis
.xib	add.w	d2,d1
.xis	ror.w	#1,d0
	bcc.b	.xin
	bsr.w	.plot
	addq.l	#2,a0
.xin	dbf	d3,.xinc
	bra.b	.end
; x major, x down
.xdec	or.w	d0,d6
	tst.w	d1
	bmi.b	.xdb
	add.w	a1,d1
	bsr.w	.plot
	add.l	a2,a0
	bra.b	.xds
.xdb	add.w	d2,d1
.xds	rol.w	#1,d0
	bcc.b	.xdn
	bsr.w	.plot
	subq.l	#2,a0
.xdn	dbf	d3,.xdec
	bra.b	.end
; y major: a pixel a row
.yloop	move.w	d0,d6
	bsr.w	.plot
	tst.w	d1
	bmi.b	.yb
	add.w	a1,d1
	btst	#0,d7
	bne.b	.yl
	ror.w	#1,d0
	bcc.b	.ys
	addq.l	#2,a0
	bra.b	.ys
.yl	rol.w	#1,d0
	bcc.b	.ys
	subq.l	#2,a0
	bra.b	.ys
.yb	add.w	d2,d1
.ys	add.l	a2,a0
	dbf	d3,.yloop
.end	bsr.w	.plot
	movem.l	(a7)+,d0/d3/d5-d6
	; the registers as the game's last plane blit leaves them
	move.l	d6,d2
	add.l	#120,d2
	move.l	d2,$48(a5)		; BLTCPT
	move.l	d2,$54(a5)		; BLTDPT
	moveq	#0,d1
	btst	#3,d4
	beq.b	.b
	moveq	#-1,d1
.b	move.w	d1,$72(a5)		; BLTBDAT
	lsr.w	#4,d4
	lsl.w	#6,d3
	addq.w	#2,d3
	add.l	#160,d6
	moveq	#0,d2
	subq.w	#1,d2
	movem.l	(a7)+,d7/a0-a2
	rts
; the pixels D6.w of the word at A0 in the colour D4, D6 cleared (D5 scratch)
.plot	tst.w	d6
	beq.b	.p4
	move.w	d6,d5
	not.w	d5
	btst	#0,d4
	beq.b	.c0
	or.w	d6,(a0)
	bra.b	.p1
.c0	and.w	d5,(a0)
.p1	btst	#1,d4
	beq.b	.c1
	or.w	d6,40(a0)
	bra.b	.p2
.c1	and.w	d5,40(a0)
.p2	btst	#2,d4
	beq.b	.c2
	or.w	d6,80(a0)
	bra.b	.p3
.c2	and.w	d5,80(a0)
.p3	btst	#3,d4
	beq.b	.c3
	or.w	d6,120(a0)
	moveq	#0,d6
	rts
.c3	and.w	d5,120(a0)
	moveq	#0,d6
.p4	rts

; BLTCON1 by D5 (dy < 0, dx < 0, x major): the octant and LINE (code $fd34)
cl_octants	dc.b	$01,$11,$09,$15,$05,$19,$0d,$1d

	machine	mc68020	; the spans run on a 68030 or later, the rectangles on a 68020

; The polygon span filler (code $fab6) by the CPU. The game blits each scanline span:
; BLTCON0 $07ca (B, C to D: D = A ? B : C), A the constant BLTADAT under the first and last
; word masks, B the colour pattern, 4 rows of 40 bytes (the planes), and waits for the
; blitter before each. Here the same pixels by CPU writes:
; < D0.w the pattern index (bss+$108c: below its count a pattern address, A = $ffff; from it
;   the address of two A words, then the pattern), D7.w lines - 1, A0/A1 the left and right
;   x lists, A3 the first line; with code $fab2 not negative, a single span from $fab2/$fab4
; > as the blitter version's: A0/A1/A3 advanced, D7.w -1, D4 the pattern, D5.w 256, D6 the A
;   words (with A words; else kept), A2/A6 the edge tables, A4 $dff044, A5 $dff000
; B: on even lines the pattern's first 160 bytes; on odd ones where the last blit left the
; blitter's B pointer, 160 bytes on (the pattern's second row, or further when the even
; line before had no span). Each plane's 40 bytes of a row are one word repeated.
CF_ADAT		= 0	; A, the even and the odd lines'
CF_B		= 4	; B, a word per plane: the two rows, then a row further on
CF_PAT		= 28	; the pattern
CF_BOFS		= 32	; the B pointer, from the pattern
CF_PHASE	= 34	; 0 an even line, 2 an odd one
CF_EDGES	= 36	; data+$1ea0 (left edges; right ones at +$500)

cf_fill
	move.l	gs2_code8(pc),a5
	tst.w	G_FILL-4-$8000(a5)
	bmi.b	.list
	moveq	#0,d7
	lea	G_FILL-4-$8000(a5),a0
	lea	2(a0),a1
.list	lea	cf_vars(pc),a2
	move.l	gs2_bss8(pc),a6
	move.l	B_PATTERNS-$8000(a6),a5
	cmp.w	(a5)+,d0
	bge.b	.awords
	move.l	(a5,d0.w),d4
	move.l	#-1,CF_ADAT(a2)
	bra.b	.go
.awords	move.l	(a5,d0.w),a5
	move.l	(a5)+,d6
	move.l	a5,d4
	move.l	d6,CF_ADAT(a2)
.go	movem.l	d5-d6,-(a7)
	lea	$dff002,a5
	tst.b	(a5)
.bwait	btst	#6,(a5)			; the game's own blits first
	bne.b	.bwait
	move.l	d4,a5
	move.l	d4,CF_PAT(a2)
	move.w	(a5),CF_B(a2)
	move.w	40(a5),CF_B+2(a2)
	move.w	80(a5),CF_B+4(a2)
	move.w	120(a5),CF_B+6(a2)
	move.w	160(a5),CF_B+8(a2)
	move.w	200(a5),CF_B+10(a2)
	move.w	240(a5),CF_B+12(a2)
	move.w	280(a5),CF_B+14(a2)
	move.l	gs2_data8(pc),a5
	lea	D_EDGES-$8000(a5),a5
	move.l	a5,CF_EDGES(a2)
	move.l	a3,d0			; even or odd: as the game, from the shown screen
	sub.l	B_DRAWN-$8000(a6),d0
	clr.l	CF_BOFS(a2)
	btst	#5,d0
	beq.b	.line
	move.w	#160,CF_BOFS(a2)
	move.w	#2,CF_PHASE(a2)

.line	move.l	CF_EDGES(a2),a6
	move.w	(a0)+,d0
	move.w	(a1)+,d1
	add.w	d0,d0
	add.w	d0,d0
	move.l	(a6,d0.w),d0		; the first word's mask, the byte offset
	moveq	#0,d2
	move.w	d0,d2
	add.w	d1,d1
	add.w	d1,d1
	move.l	($500,a6,d1.w),d3	; the end byte, the last word's mask
	move.w	d3,d0
	swap	d3
	sub.w	d2,d3
	bls.w	.next
	not.l	d0			; D0 = ~first:~last, the words kept
	move.w	CF_PHASE(a2),d1
	move.w	CF_ADAT(a2,d1.w),d4	; A
	tst.w	d1
	bne.b	.odd
	clr.w	CF_BOFS(a2)		; even lines set the B pointer
.odd	lea	CF_B(a2),a4
	move.w	CF_BOFS(a2),d1
	beq.b	.bgot
	addq.l	#8,a4
	cmp.w	#160,d1
	beq.b	.bgot
	addq.l	#8,a4			; further on: read it
	move.l	CF_PAT(a2),a5
	add.w	d1,a5
	move.w	(a5),(a4)
	move.w	40(a5),2(a4)
	move.w	80(a5),4(a4)
	move.w	120(a5),6(a4)
.bgot	add.w	#160,CF_BOFS(a2)
	lea	(a3,d2.l),a5
	lsr.w	#1,d3			; words (BLTSIZE's 6 bits)
	and.w	#63,d3
	bne.b	.words
	moveq	#64,d3
.words	cmp.w	#1,d3
	beq.w	.one
	cmp.w	#-1,d4
	bne.w	.amask

	; A $ffff, 2 words or more: the edges kept where masked, longs between
	subq.w	#2,d3
	moveq	#0,d6
	move.l	a5,d1
	btst	#1,d1
	bne.b	.lalign			; the middle starts on a long
	tst.w	d3
	beq.b	.lalign
	bset	#16,d6			; a word first
	subq.w	#1,d3
.lalign	lsr.w	#1,d3
	bcc.b	.even2
	bset	#17,d6			; a word last
.even2	move.w	d3,d6
	moveq	#3,d4
.plane	move.w	(a4)+,d2
	move.w	d2,d1
	swap	d2
	move.w	d1,d2
	move.l	a5,a6
	swap	d0
	tst.w	d0
	beq.b	.first
	move.w	(a6),d1
	eor.w	d2,d1
	and.w	d0,d1
	eor.w	d2,d1
	move.w	d1,(a6)+
	bra.b	.mid
.first	move.w	d2,(a6)+
.mid	swap	d0
	btst	#16,d6
	beq.b	.mlong
	move.w	d2,(a6)+
.mlong	move.w	d6,d3
	bra.b	.mnext
.mloop	move.l	d2,(a6)+
.mnext	dbf	d3,.mloop
	btst	#17,d6
	beq.b	.last
	move.w	d2,(a6)+
.last	tst.w	d0
	beq.b	.lastw
	move.w	(a6),d1
	eor.w	d2,d1
	and.w	d0,d1
	eor.w	d2,d1
	move.w	d1,(a6)
	bra.b	.pnext
.lastw	move.w	d2,(a6)
.pnext	lea	40(a5),a5
	dbf	d4,.plane
	bra.b	.next

	; one word: both masks and A
.one	move.l	d0,d5
	swap	d5
	or.w	d0,d5
	not.w	d4
	or.w	d4,d5			; the bits kept
	moveq	#3,d4
.oplane	move.w	(a4)+,d2
	move.w	(a5),d1
	eor.w	d2,d1
	and.w	d5,d1
	eor.w	d2,d1
	move.w	d1,(a5)
	lea	40(a5),a5
	dbf	d4,.oplane
	bra.b	.next

	; A words (stipples), 2 words or more: every word read
.amask	not.w	d4
	move.l	d0,d5
	or.w	d4,d5
	swap	d5
	or.w	d4,d5			; ~(first & A), then ~(last & A)
	subq.w	#2,d3
	moveq	#3,d6
.aplane	move.w	(a4)+,d2
	move.l	a5,a6
	move.w	(a6),d1
	eor.w	d2,d1
	and.w	d5,d1
	eor.w	d2,d1
	move.w	d1,(a6)+
	move.w	d3,d0
	bra.b	.anext
.aloop	move.w	(a6),d1
	eor.w	d2,d1
	and.w	d4,d1
	eor.w	d2,d1
	move.w	d1,(a6)+
.anext	dbf	d0,.aloop
	swap	d5
	move.w	(a6),d1
	eor.w	d2,d1
	and.w	d5,d1
	eor.w	d2,d1
	move.w	d1,(a6)
	swap	d5
	lea	40(a5),a5
	dbf	d6,.aplane

.next	eor.w	#2,CF_PHASE(a2)
	lea	160(a3),a3
	dbf	d7,.line
	movem.l	(a7)+,d5-d6
	move.l	CF_PAT(a2),d4
	move.w	#256,d5
	move.l	CF_EDGES(a2),a6
	lea	$500(a6),a2
	lea	$dff000,a5
	lea	$44(a5),a4
	rts

cf_vars		dcb.b	40,0	; CF_* above


	IFD G_RECT
; code $13832: a rectangle of the screen in one colour, by the CPU (the game: a D-only blit a
; plane through code $dda0, BLTCON0 $0100 or $01ff, rows of 160 bytes)
; < D0.w x extent (D0 / 16 + 1 words), D1.w rows, D4 the top left, D7.b the colour
; > as the game's: D0.w the words, D1.w BLTSIZE, D2 $ffff, D4 4 planes on, D6.w the last
;   BLTCON0, D7.b shifted by 4, A6 the end of its blit list (bss+$b5c6), and the blitter
;   registers it set (BLTCON0, BLTCON1, BLTDMOD, BLTDPT)
cf_rect
	movem.l	d3/d5/a0/a5,-(a7)
	lsr.w	#4,d0
	addq.w	#1,d0
	lea	$dff002,a5
	tst.b	(a5)
.bwait	btst	#6,(a5)			; the game's own blits first
	bne.b	.bwait
	lea	cr_planes(pc),a0	; the planes' longs, 0 or -1
	moveq	#3,d2
.pl	lsr.b	#1,d7
	scs	d6
	extb.l	d6
	move.l	d6,(a0)+
	dbf	d2,.pl
	move.w	#$100,d6		; the last BLTCON0
	move.b	cr_planes+15(pc),d6
	movem.l	d1/d6-d7,-(a7)
	move.w	d1,d5			; BLTSIZE's height and width
	and.w	#1023,d5
	bne.b	.h
	move.w	#1024,d5
.h	move.w	d0,d3
	and.w	#63,d3
	bne.b	.w
	moveq	#64,d3
.w	moveq	#0,d6			; a word first, a word last, longs between
	btst	#1,d4
	beq.b	.al
	bset	#16,d6
	subq.w	#1,d3
.al	lsr.w	#1,d3
	bcc.b	.al2
	bset	#17,d6
.al2	move.w	d3,d6
	move.l	d4,a5
	move.w	d5,d3
	subq.w	#1,d3
.row	lea	cr_planes(pc),a0
	moveq	#3,d2
.plane	move.l	(a0)+,d5
	move.l	a5,a6
	btst	#16,d6
	beq.b	.l0
	move.w	d5,(a6)+
.l0	move.w	d6,d7
	bra.b	.l2
.l1	move.l	d5,(a6)+
.l2	dbf	d7,.l1
	btst	#17,d6
	beq.b	.l3
	move.w	d5,(a6)+
.l3	lea	40(a5),a5
	dbf	d2,.plane
	dbf	d3,.row
	lea	$dff000,a6		; the blitter as the last blit left it
	lea	-40(a5),a5
	move.l	a5,$54(a6)		; BLTDPT
	move.w	#160,d2
	sub.w	d0,d2
	sub.w	d0,d2
	move.w	d2,$66(a6)		; BLTDMOD
	clr.w	$42(a6)			; BLTCON1
	movem.l	(a7)+,d1/d6-d7
	move.w	d6,$40(a6)		; BLTCON0
	lsl.w	#6,d1
	add.w	d0,d1
	move.l	#$ffff,d2
	add.l	#160,d4
	; the blit list as the game leaves it, the last plane's blit: the CD32 build runs it again
	; after some rectangles (code $dd4a)
	move.l	gs2_bss8(pc),a6
	lea	B_RECTS-$8000(a6),a6
	move.w	#$40,(a6)+		; BLTCON0
	move.w	d6,(a6)+
	move.w	#-$54,(a6)+		; BLTDPT, the last plane
	move.l	d4,(a6)
	sub.l	#40,(a6)+
	clr.w	(a6)+			; BLTSIZE: the blit
	move.w	d1,(a6)+
	movem.l	(a7)+,d3/d5/a0/a5
	rts

cr_planes	dc.l	0,0,0,0
	ENDC

	machine	mc68000
