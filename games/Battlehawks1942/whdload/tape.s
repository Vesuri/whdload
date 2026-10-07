; VERIFY-only input tape: types raw keys into input.device so a capture can reach gameplay
; without a person at the keyboard. (This FS-UAE build cannot replay input recordings, and
; the gdb stub cannot write memory; see docs/profiling.md.)
;
; The LoadSeg hook starts a task when BH is loaded. The task counts PAL fields with
; graphics.library WaitTOF and sends each tape entry as an IECLASS_RAWKEY event with
; IND_WRITEEVENT, so intuition and the game's own input handler see an ordinary key press.
; Under DETERMINISTIC=1 the whole run then repeats exactly. When the tape ends the task
; Wait()s forever, so it costs nothing during a measurement window.
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
RAW_LEFT	= $4F			;cursor left: the controller, bank left
RAW_UP		= $80			;or-ed into a code: key release
TAPE_FRAME	= $8000			;or-ed into a wait: until BH's flight frame counter >= n
BH_FRAMES	= $7ffe+26292		;BH's frame counter: data hunk + $7FFE (a4) + 26292

; Tape: (wait, raw key code); 0 ends it. A wait is a number of fields (counted from the
; LoadSeg of BH, through the menus), or TAPE_FRAME|n: until BH's flight frame counter
; (incremented once per pass of the flight loop, bh:6e52) is at least n. The boot shows the title and the credits by itself; then each screen waits
; for Return: main menu (Select Training is highlighted), Select Training Mission (the first
; mission), Ready Room (Begin Flight), and the Recognition Test (the manual check, shown
; before the first flight; any answer passes). Measured with the KickEmu slave on the
; A500-equivalent machine: the menu is up by field ~2800, so the first key comes at 3000 and
; one more every 505 fields. Faster machines only reach each screen sooner.
	IFND	TAPE_FIRST
TAPE_FIRST	= 3000
	ENDC
	IFND	TAPE_GAP
TAPE_GAP	= 500
	ENDC

tape:	dc.w	TAPE_FIRST,RAW_RETURN, 5,RAW_RETURN|RAW_UP
	dc.w	TAPE_GAP,RAW_RETURN, 5,RAW_RETURN|RAW_UP
	dc.w	TAPE_GAP,RAW_RETURN, 5,RAW_RETURN|RAW_UP
	dc.w	TAPE_GAP,RAW_RETURN, 5,RAW_RETURN|RAW_UP
; Then, timed by BH's own flight frame counter (an entry with TAPE_FRAME set waits until the
; counter reaches the frame), bank left so the plane flies in circles: the benchmark scene.
; The game steps once per frame, so frame-timed input gives the same flight on every CPU and
; the window (a frame number too) shows the same scene everywhere. A key press is one
; character to the game, and its controller (bh:7f30) turns one character into full aileron
; for one frame: 8 presses 3 frames apart from frame 30 give about 10 degrees of bank. The
; plane levels its wings by itself, so one more press every 10 frames holds the circle.
F	SET	30
	REPT	8
	dc.w	TAPE_FRAME|F,RAW_LEFT, TAPE_FRAME|(F+1),RAW_LEFT|RAW_UP
F	SET	F+3
	ENDR
F	SET	60
	REPT	400
	dc.w	TAPE_FRAME|F,RAW_LEFT, TAPE_FRAME|(F+1),RAW_LEFT|RAW_UP
F	SET	F+10
	ENDR
	dc.w	0

; Called from the LoadSeg hook (a task, all registers saved by the caller).
tape_start:
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
	move.l	tape_seglist(pc),d0	;BH's first segment: BPTR to the next one,
	lsl.l	#2,d0			;the data hunk
	move.l	d0,a0
	move.l	(a0),d0
	lsl.l	#2,d0
	add.l	#4+BH_FRAMES,d0
	move.l	d0,a4			;BH's frame counter (word)
	lea	tape(pc),a3
.next:	move.w	(a3)+,d2
	beq.s	.done
	bmi.s	.frame
.wait:	bsr.s	.field
	subq.w	#1,d2
	bne.s	.wait
	bra.s	.send
.frame:	and.w	#$7fff,d2
.fwait:	cmp.w	(a4),d2
	bls.s	.send
	bsr.s	.field
	bra.s	.fwait
.field:	exg	a5,a6
	jsr	_LVOWaitTOF(a6)
	exg	a5,a6
	lea	tape_fields(pc),a0
	addq.l	#1,(a0)
	rts
.send:
	lea	tape_event(pc),a0
	move.b	#IECLASS_RAWKEY,ie_Class(a0)
	move.w	(a3)+,ie_Code(a0)
	lea	tape_io(pc),a1
	move.w	#IND_WRITEEVENT,IO_COMMAND(a1)
	move.l	a0,IO_DATA(a1)
	move.l	#ie_SIZEOF,IO_LENGTH(a1)
	jsr	_LVODoIO(a6)
	bra.s	.next
.done:	moveq	#0,d0
	jsr	_LVOWait(a6)
	bra.s	.done

; Read by tools/fixed_window.sh (gdb, read-only): fields counted so far, and the field of
; the last Return (the window anchors on the first flight frame after it). The marker locates them in memory.
	CNOP	0,4
	dc.b	"BHTAPE!!"
tape_fields:	dc.l	0
tape_end:	dc.l	TAPE_FIRST+5+3*(TAPE_GAP+5)

tape_seglist:	dc.l	0			;BH's seglist (BPTR), set by the LoadSeg hook
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
