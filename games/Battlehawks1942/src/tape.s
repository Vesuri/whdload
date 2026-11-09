; VERIFY-only input tape: types raw keys into input.device so a capture can reach gameplay
; without a person at the keyboard. (This FS-UAE build cannot replay input recordings, and
; the gdb stub cannot write memory; see docs/profiling.md.)
;
; The LoadSeg hook starts a task when BH is loaded. The task counts PAL fields with
; graphics.library WaitTOF and presses Return (IECLASS_RAWKEY events with IND_WRITEEVENT,
; so intuition and the game's own input handler see an ordinary key press) every TAPE_GAP
; fields from field TAPE_FIRST until the first flight frame (tape_key sets tape_flying).
; Every screen on the way takes Return, so every CPU reaches the flight on its own
; schedule. Under DETERMINISTIC=1 the whole run then repeats exactly. Then the task
; Wait()s forever, so it costs nothing during a measurement window. Flight input goes into
; BH's frame loop instead (tape_key below), which also keeps the flight record.
;
; The task, its stack and its I/O blocks live in the slave, not in Amiga memory, so the
; game's own allocations are unchanged.

	INCLUDE	exec/types.i
	INCLUDE	exec/nodes.i
	INCLUDE	exec/lists.i
	INCLUDE	exec/tasks.i
	INCLUDE	exec/ports.i
	INCLUDE	exec/io.i
	INCLUDE	devices/input.i
	INCLUDE	devices/inputevent.i
	INCLUDE	lvo/exec_lib.i
	INCLUDE	lvo/graphics_lib.i

RAW_RETURN	= $44
RAW_UP		= $80			;or-ed into a code: key release
BH_KEY		= $3e98			;BH: the frame's key (one IDCMP character, or 0)
BH_KEYCALL	= $75c4			;BH: return address of the flight loop's call of it
BH_FRAME	= 26292			;(a4).w BH's flight frame counter (bh:6e52)
CHAR_LEFT	= 3			;BH's character for cursor left (its key table)

; Fields count from the LoadSeg of BH. The boot shows the title and the credits by itself;
; then each screen waits for Return: main menu (Select Training is highlighted), Select
; Training Mission (the first mission), Ready Room (Begin Flight), and the Recognition Test
; (the manual check, shown before the first flight; any answer passes). With the KickEmu
; slave on the 68000 the menu is up by field ~2800 and the screens are ~505 fields apart;
; a Return that comes while a screen loads is taken by the next one or lost, and the next
; press follows TAPE_GAP fields later.
	IFND	TAPE_FIRST
TAPE_FIRST	= 3000
	ENDC
	IFND	TAPE_GAP
TAPE_GAP	= 300
	ENDC

; Called from the LoadSeg hook (a task, all registers saved by the caller).
tape_start:
	bsr	rec_alloc
	move.l	(4).w,a6
	lea	tape_task(pc),a1
	move.b	#NT_TASK,LN_TYPE(a1)
	move.b	#1,LN_PRI(a1)		;above the game, so events go out on time
	lea	tape_name(pc),a0
	move.l	a0,LN_NAME(a1)
	lea	TC_MEMENTRY(a1),a0
	NEWLIST	a0
	lea	tape_stack(pc),a0
	move.l	a0,TC_SPLOWER(a1)
	lea	tape_stack_end(pc),a0
	move.l	a0,TC_SPUPPER(a1)
	move.l	a0,TC_SPREG(a1)
	lea	tape_task_code(pc),a2
	sub.l	a3,a3
	jmp	_LVOAddTask(a6)

tape_task_code:
	move.l	(4).w,a6
	lea	tape_gfx_name(pc),a1
	moveq	#0,d0
	jsr	_LVOOpenLibrary(a6)
	move.l	d0,a5
	moveq	#-1,d0
	jsr	_LVOAllocSignal(a6)
	lea	tape_port(pc),a2
	move.b	d0,MP_SIGBIT(a2)
	move.b	#NT_MSGPORT,LN_TYPE(a2)
	move.b	#PA_SIGNAL,MP_FLAGS(a2)
	sub.l	a1,a1
	jsr	_LVOFindTask(a6)
	move.l	d0,MP_SIGTASK(a2)
	lea	MP_MSGLIST(a2),a0
	NEWLIST	a0
	lea	tape_io(pc),a1
	move.l	a2,MN_REPLYPORT(a1)
	lea	tape_input_name(pc),a0
	moveq	#0,d0
	moveq	#0,d1
	jsr	_LVOOpenDevice(a6)
	move.w	#TAPE_FIRST,d2
.next:	bsr.s	.wait
	lea	tape_flying(pc),a0
	tst.b	(a0)
	bne.s	.done
	moveq	#RAW_RETURN,d0
	bsr.s	.key
	moveq	#5,d2
	bsr.s	.wait
	move.w	#RAW_RETURN|RAW_UP,d0
	bsr.s	.key
	move.w	#TAPE_GAP-5,d2
	bra.s	.next
.wait:	exg	a5,a6
	jsr	_LVOWaitTOF(a6)
	exg	a5,a6
	lea	tape_fields(pc),a0
	addq.l	#1,(a0)
	subq.w	#1,d2
	bne.s	.wait
	rts
.key:	lea	tape_event(pc),a0
	move.b	#IECLASS_RAWKEY,ie_Class(a0)
	move.w	d0,ie_Code(a0)
	lea	tape_io(pc),a1
	move.w	#IND_WRITEEVENT,IO_COMMAND(a1)
	move.l	a0,IO_DATA(a1)
	move.l	#ie_SIZEOF,IO_LENGTH(a1)
	jmp	_LVODoIO(a6)
.done:	moveq	#0,d0
	jsr	_LVOWait(a6)
	bra.s	.done

; In flight the keys go straight into BH's frame loop instead (the pl_bh patch at bh:75be,
; VERIFY only): the loop asks BH_KEY for this frame's character; when there is none, the
; flight tape gives one on the frames it lists. The game steps once per frame, so input on
; exact frame numbers gives the same flight on every CPU and in every run, wherever the
; debugger stopped the emulator (its stops are not cycle-transparent, and a key typed
; through input.device at a field could land a frame early or late).
; The benchmark scene: bank left so the plane turns. A cursor character is full aileron for
; one frame (the controller, bh:7f30): 8 of them 3 frames apart from frame 30 give about 10
; degrees, then one every 10 frames keeps it banked (the bank grows into a descending spiral:
; small banks level out by themselves, larger ones tighten).
tape_key:
	lea	tape_flying(pc),a0
	tst.b	(a0)
	bne.s	.flying
	st	(a0)
	lea	tape_t0(pc),a0		;the first flight frame's field
	move.w	dt_fields(pc),(a0)
.flying:
	bsr	rec_frame
	IFD	TAPE_MOUSE
	bsr	tape_mouse
	ENDC
	move.l	(sp),a0			;bh+BH_KEYCALL
	jsr	(BH_KEY-BH_KEYCALL,a0)	;d0.w = this frame's character or 0
	tst.w	d0
	bne.s	.store			;a real key wins
	IFD	TAPE_MOUSE
	bra.s	.store			;the mouse only, no keys
	ENDC
	lea	tape_flight(pc),a1
	adda.w	tape_flight_pos(pc),a1
	move.w	(a1),d1
	beq.s	.store			;tape done
	IFD	TAPE_TIME
	add.w	tape_t0(pc),d1
	cmp.w	dt_fields(pc),d1
	ELSE
	cmp.w	(BH_FRAME,a4),d1
	ENDC
	bhi.s	.store			;not yet
	move.w	(2,a1),d0
	lea	tape_flight_pos(pc),a0
	addq.w	#4,(a0)
.store:	move.w	d0,(10280,a4)		;as the replaced move.w d0,10280(a4)
	rts

	IFD	TAPE_MOUSE
; TAPE_MOUSE (the mouse build): the stick from the mouse alone. Before the frame's input
; read, MOUSE_DY counts per field since the last frame are added to BH's vertical mouse
; accumulator 25190(a4) (as its input handler bh:19a86 adds RAWMOUSE counts): down
; (positive) from field 100 to 300 after the first flight frame, still until 500, up until
; 700. A rate per field: the same movement in real time on every machine.
	IFND	MOUSE_DY
MOUSE_DY	= 2
	ENDC
tape_mouse:
	movem.l	d0-d2/a0,-(sp)
	move.w	dt_fields(pc),d0
	lea	tape_mlast(pc),a0
	move.w	(a0),d1
	move.w	d0,(a0)
	tst.w	(2,a0)
	bne.s	.go
	st	(2,a0)			;first frame: nothing owed
	bra.s	.done
.go	sub.w	d1,d0			;fields since the last frame
	move.w	dt_fields(pc),d1
	sub.w	tape_t0(pc),d1		;fields into the flight
	moveq	#MOUSE_DY,d2
	cmp.w	#100,d1
	blo.s	.done
	cmp.w	#300,d1
	blo.s	.add
	cmp.w	#500,d1
	blo.s	.done
	cmp.w	#700,d1
	bhs.s	.done
	neg.w	d2
.add	muls	d2,d0
	add.w	d0,(25190,a4)
.done	movem.l	(sp)+,d0-d2/a0
	rts
tape_mlast:	dc.w	0,0
	ENDC

; (flight frame, character); 0 ends it.
; With TSCALE (the T experiment, t_scale below) a step is 1/TSCALE as long: each press at
; frame F becomes TSCALE presses ending at frame F*TSCALE, the same game time and the same
; total stick (the controller divides it by T). With STICKREF the stick divides by the
; mission's reference T instead (as a fix would), so one press per original press.
	IFND	TSCALE
TSCALE	= 1
	ENDC
FLIGHT_KEY	MACRO
	IFD	STICKREF
	dc.w	\1*TSCALE,CHAR_LEFT	;one press: the stick no longer divides by T
	MEXIT
	ENDC
R	SET	TSCALE-1
	REPT	TSCALE
	dc.w	\1*TSCALE-R,CHAR_LEFT
R	SET	R-1
	ENDR
	ENDM
tape_flight:
	IFD	TAPE_TIME
; TAPE_TIME: the same left turn by fields since the first flight frame instead of frame
; numbers (the 68000's ~5.4 fields per frame): the same input in real time on every
; machine, for comparing machines when game time follows real time (CUSTOM2=1).
F	SET	160
	REPT	8
	dc.w	F,CHAR_LEFT
F	SET	F+16
	ENDR
F	SET	330
	REPT	400
	dc.w	F,CHAR_LEFT
F	SET	F+54
	ENDR
	ELSE
F	SET	30
	REPT	8
	FLIGHT_KEY	F
F	SET	F+3
	ENDR
F	SET	60
	REPT	400
	FLIGHT_KEY	F
F	SET	F+10
	ENDR
	ENDC
	dc.w	0
tape_flight_pos:	dc.w	0		;offset of the next entry

; The T experiment (make build BUILD=tscale TSCALE=n, docs/profiling.md §9): BH divides per-step
; quantities by T = 10184(a4), set per mission at bh:1341c. Multiply it, in place of
; move.w 10184(a4),d0; lsr.w #3,d0 at bh:1344e (10186(a4) = T/8 + 1 follows).
t_scale:
	move.w	(10184,a4),d0
	mulu	#TSCALE,d0
	move.w	d0,(10184,a4)
	lsr.w	#3,d0
	rts

; Read by tools/fixed_window.sh (gdb, read-only): fields counted so far, and the field to
; arm the window's anchor from, ARM_EARLY (1000) fields before it: no flight starts before
; the first Return. The marker locates them in memory.
	CNOP	0,4
	dc.b	"BHTAPE!!"
tape_fields:	dc.l	0
tape_end:	dc.l	TAPE_FIRST+1000
tape_flying:	dc.b	0
	EVEN
tape_t0:	dc.w	0

; Flight record (tools/record.sh, tools/speed.py): one REC_SIZE entry per flight frame,
; taken at the frame's key read (after timing.s has set the frame's T): the VERTB count
; (timing.s's dt_fields, counted in VERIFY builds whatever CUSTOM2), T, the player's
; (object 0) x, y, z, heading, roll, pitch and speed, and BH's frame counter. REC_FRAMES
; entries in a buffer allocated at LoadSeg (none if that fails); then it stops.
	IFND	REC_FRAMES
REC_FRAMES	= 2048
	ENDC
REC_SIZE	= 28

rec_alloc:
	move.l	(4).w,a6
	move.l	#REC_FRAMES*REC_SIZE,d0
	move.l	#MEMF_PUBLIC|MEMF_CLEAR,d1
	jsr	_LVOAllocMem(a6)
	lea	rec_buf(pc),a0
	move.l	d0,(a0)
	rts

rec_frame:
	movem.l	d0/a0-a1,-(sp)
	move.l	rec_buf(pc),d0
	beq.s	.done
	move.l	rec_count(pc),d0
	cmp.l	#REC_FRAMES,d0
	bhs.s	.done
	mulu	#REC_SIZE,d0
	move.l	rec_buf(pc),a0
	add.l	d0,a0
	move.w	dt_fields(pc),(a0)+
	move.w	(BH_T,a4),(a0)+
	move.l	(10908,a4),(a0)+	;x[0]
	move.l	(11484,a4),(a0)+	;y[0]
	move.l	(12060,a4),(a0)+	;z[0]
	move.w	(14328,a4),(a0)+	;heading[0]
	move.w	(15240,a4),(a0)+	;roll[0]
	move.w	(14952,a4),(a0)+	;pitch[0]
	move.w	(15696,a4),(a0)+	;speed[0]
	move.w	(BH_FRAME,a4),(a0)+
	lea	rec_count(pc),a0
	addq.l	#1,(a0)
.done:	movem.l	(sp)+,d0/a0-a1
	rts

	CNOP	0,4
	dc.b	"BHREC!!!"
rec_count:	dc.l	0
rec_buf:	dc.l	0
rec_frames:	dc.l	REC_FRAMES
rec_spans:	dc.l	0,0,0			;SPANCHECK: spans checked, ran past, of
						;those, spans that ended before they began

tape_name:	dc.b	"bh tape",0
tape_gfx_name:	dc.b	"graphics.library",0
tape_input_name:	dc.b	"input.device",0
	EVEN
tape_task:	dcb.b	TC_SIZE,0
tape_port:	dcb.b	MP_SIZE,0
tape_io:	dcb.b	IOSTD_SIZE,0
tape_event:	dcb.b	ie_SIZEOF,0
	EVEN
tape_stack:	dcb.b	1024,0
tape_stack_end:
