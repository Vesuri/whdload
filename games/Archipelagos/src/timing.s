;*---------------------------------------------------------------------------
; Game time decoupled from the frame rate (docs/internals.md, "Game time").
;
; The game counts some of its time in frames drawn:
; - at the start of every render, one step of the spread across connected land, the
;   terrain animation phase and two object animation timers;
; - a move between cells: eight frames, each an eighth of the way, then one on the cell;
; - two effects: six frames, and two ramps of 32 frames.
; All of them ran as fast as the CPU drew.  Here each advances with the fields its frames
; take, one step for every STEP_FIELDS fields (6, the game's own world tick) and never
; more than one step a frame.  A frame of STEP_FIELDS fields or more (every frame in play
; on an A500) takes one step, as in the original, so slow machines run as before and a
; faster one never runs faster than one step every STEP_FIELDS fields.  The world tick is
; the game's own (at most once a frame, every 6 fields).
;
; Time is the level 3 handler's field counter, read where it matters and clamped to
; STEP_FIELDS (the game clears the counter when an archipelago starts, which reads as a
; long interval and is clamped too).
;
; - t_steps, in place of the renderer's steps: each render adds the fields since the
;   previous render to t_stepacc and takes the steps when that reaches STEP_FIELDS,
;   carrying the rest.  Its own interval, not the frame's: the game also renders without
;   a swap.  A render with no swap since the previous one (only an archipelago's opening
;   has them: its last render and the first frame's, in one field) takes the steps
;   anyway, as the original did, which keeps an A500's game state the original's.
; - The swap measures a frame's length, the fields since the previous swap (t_frame).
; - t_move, in place of the move: the position is the start plus the original's eighth
;   of the way times the fields into the move / STEP_FIELDS (the last frame's length
;   added each frame, at most 8 x STEP_FIELDS), so a move takes 8 x STEP_FIELDS fields in
;   as many frames as fit.  At STEP_FIELDS fields a frame the positions are the original's.
;   The frame on the cell is the original's.
; - t_pace and t_pacedraw, in place of an effect's frame: frames until the effect's step
;   has had STEP_FIELDS fields (t_paceacc, carrying the rest).
;
; State is kept here, not in registers: the game's render and swap keep none.

STEP_FIELDS	= 6		; fields a frame-counted step takes at least: the world tick's
MOVE_STEPS	= 8		; a move's frames before the one on the cell

BODY		= $2000+$1c	; the program body (patch list offsets are from here)

; The game's addresses the routines use, a table per version.
		RSRESET
gt_fields	rs.l	1	; the field counter (long, the level 3 handler's)
gt_back		rs.l	1	; the back buffer's address (long)
gt_spread	rs.l	1	; one step of the spread
gt_phase	rs.l	1	; the terrain animation phase (word, 9 down to 0)
gt_timer1	rs.l	1	; the two object animation timers (words, 2 a step)
gt_timer2	rs.l	1
gt_world	rs.l	1	; the world update (a tick when one is due)
gt_render	rs.l	1	; the renderer: its steps, a wait for a field, the drawing
gt_draw		rs.l	1	; the renderer's drawing, after the wait
gt_wait		rs.l	1	; wait for the next field
gt_swap		rs.l	1	; show the back buffer from the next field
gt_pos		rs.l	1	; the position (words, 8.8): x, then y
gt_heading	rs.l	1	; the heading (word), then the half the renderer uses

; SPS 627
GT627	dc.l	BODY+$12862,BODY+$1286a,BODY+$c99e,BODY+$12dac,BODY+$12db8
	dc.l	BODY+$12dc8,BODY+$f6f6,BODY+$11ac6,BODY+$11af6,BODY+$123b4
	dc.l	BODY+$12210,BODY+$129be,BODY+$12880

; SPS 628
GT628	dc.l	BODY+$12c06,BODY+$12c0e,BODY+$c9ca,BODY+$13150,BODY+$1315c
	dc.l	BODY+$1316c,BODY+$f74a,BODY+$11d7e,BODY+$11dae,BODY+$12758
	dc.l	BODY+$124c8,BODY+$12d62,BODY+$12c24

t_table		dc.l	0		; GT627 or GT628
t_last		dc.l	$80000000	; the field counter at the last swap (the first
t_lastdraw	dc.l	$80000000	; ... at the last render  interval reads as long)
t_frame		dc.w	0		; the last frame's fields
t_swapped	dc.w	0		; set (byte) by a swap, cleared by a render
t_stepacc	dc.w	0		; fields towards the renderer's next steps
t_paceacc	dc.w	0		; fields towards an effect's next step
t_from		dc.w	0,0		; a move's start (x, y)
t_eighth	dc.w	0,0		; the original's eighth of the way (x, y)
t_into		dc.w	0		; fields into the move

; The swap's last instructions (PL_P on its move.l d0,(back buffer)), then the frame's
; length.
t_swapend
	movem.l	d1/a0-a1,-(a7)
	move.l	t_table(pc),a1
	move.l	gt_back(a1),a0
	move.l	d0,(a0)
	lea	t_last(pc),a0
	bsr.b	t_since
	lea	t_frame(pc),a0
	move.w	d0,(a0)
	st	t_swapped-t_frame(a0)
	movem.l	(a7)+,d1/a0-a1
	move.l	(a7)+,d0		; the swap's own epilogue
	rts

; d0.l = fields since the counter value at (a0), at most STEP_FIELDS; (a0) = the counter.
; Uses d1, a1.
t_since	move.l	t_table(pc),a1
	move.l	gt_fields(a1),a1
	move.l	(a1),d0
	move.l	d0,d1
	sub.l	(a0),d0
	move.l	d1,(a0)
	moveq	#STEP_FIELDS,d1
	cmp.l	d1,d0
	bls.b	.ok			; unsigned: a cleared counter reads as long
	move.l	d1,d0
.ok	rts

; The renderer's frame-counted steps (PL_PSA over them).
t_steps	movem.l	d0-d1/a0-a1,-(a7)
	lea	t_lastdraw(pc),a0
	bsr.b	t_since
	lea	t_swapped(pc),a0
	tst.b	(a0)
	sf	(a0)
	beq.b	.steps			; no swap since the last render
	lea	t_stepacc(pc),a0
	add.w	(a0),d0
	subq.w	#STEP_FIELDS,d0
	bcc.b	.step
	addq.w	#STEP_FIELDS,d0
	move.w	d0,(a0)
	movem.l	(a7)+,d0-d1/a0-a1
	rts

.step	move.w	d0,(a0)
.steps	move.l	t_table(pc),a0
	move.l	gt_spread(a0),a0
	jsr	(a0)			; uses d0-d3/a1-a2, as in the original
	move.l	t_table(pc),a1
	move.l	gt_phase(a1),a0
	subq.w	#1,(a0)
	bpl.b	.phase
	move.w	#9,(a0)
.phase	move.l	gt_timer1(a1),a0
	subq.w	#2,(a0)
	move.l	gt_timer2(a1),a0
	subq.w	#2,(a0)
	movem.l	(a7)+,d0-d1/a0-a1
	rts

; A move between cells (PL_P on the original): d0.w/d1.w the target, as there.
t_move	movem.w	d0-d1,-(a7)		; the target, for the frame on the cell
	move.l	t_table(pc),a0
	move.l	gt_pos(a0),a0
	lea	t_from(pc),a1
	move.w	(a0),(a1)+		; t_from
	move.w	2(a0),(a1)+
	sub.w	(a0),d0
	sub.w	2(a0),d1
	asr.w	#3,d0			; the original's eighth, rounded down
	asr.w	#3,d1
	move.w	d0,(a1)+		; t_eighth
	move.w	d1,(a1)+
	clr.w	(a1)			; t_into

.frame	lea	t_into(pc),a1
	move.w	t_frame(pc),d0
	add.w	(a1),d0
	cmp.w	#MOVE_STEPS*STEP_FIELDS,d0
	bls.b	.into
	move.w	#MOVE_STEPS*STEP_FIELDS,d0
.into	move.w	d0,(a1)
	lea	t_from(pc),a1
	move.l	t_table(pc),a0
	move.l	gt_pos(a0),a0
	move.w	4(a1),d1		; start + eighth x fields / STEP_FIELDS
	muls.w	d0,d1
	divs.w	#STEP_FIELDS,d1
	add.w	(a1),d1
	move.w	d1,(a0)
	move.w	6(a1),d1
	muls.w	d0,d1
	divs.w	#STEP_FIELDS,d1
	add.w	2(a1),d1
	move.w	d1,2(a0)

	move.l	t_table(pc),a0		; then a frame, as the original's
	move.l	gt_world(a0),a0
	jsr	(a0)
	move.l	t_table(pc),a0
	move.l	gt_heading(a0),a0
	move.w	(a0),d0
	asr.w	#1,d0
	move.w	d0,2(a0)
	bsr.b	t_render
	bsr.b	t_show
	move.w	t_into(pc),d0
	cmp.w	#MOVE_STEPS*STEP_FIELDS,d0
	bcs.b	.frame

	movem.w	(a7)+,d0-d1		; the frame on the cell
	move.l	t_table(pc),a0
	move.l	gt_pos(a0),a0
	move.w	d0,(a0)
	move.w	d1,2(a0)
	bsr.b	t_render
	bra.b	t_show

t_render
	move.l	t_table(pc),a0
	move.l	gt_render(a0),a0
	jmp	(a0)

t_show	move.l	t_table(pc),a0
	move.l	gt_swap(a0),a0
	jmp	(a0)

; The six-frame effect's frame (PL_PSS on its render and swap).
t_pace	bsr.b	t_render
	bsr.b	t_show
	bsr.b	t_paced
	bcs.b	t_pace
	rts

; The ramps' frame (PL_PSS on their wait, drawing and swap).
t_pacedraw
	move.l	t_table(pc),a0
	move.l	gt_wait(a0),a0
	jsr	(a0)
	move.l	t_table(pc),a0
	move.l	gt_draw(a0),a0
	jsr	(a0)
	bsr.b	t_show
	bsr.b	t_paced
	bcs.b	t_pacedraw
	rts

; Carry set while the effect's step has had fewer than STEP_FIELDS fields.
t_paced	movem.l	d0/a0,-(a7)
	lea	t_paceacc(pc),a0
	move.w	t_frame(pc),d0
	add.w	(a0),d0
	subq.w	#STEP_FIELDS,d0
	bcs.b	.short
	move.w	d0,(a0)			; carry clear
	movem.l	(a7)+,d0/a0
	rts

.short	addq.w	#STEP_FIELDS,d0
	move.w	d0,(a0)
	movem.l	(a7)+,d0/a0
	ori.b	#1,ccr
	rts
