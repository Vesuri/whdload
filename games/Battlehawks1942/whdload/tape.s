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
RAW_UP		= $80			;or-ed into a code: key release

; Tape: (fields to wait before the event, raw key code); 0 ends it. Fields count from the
; LoadSeg of BH. The boot shows the title and the credits by itself; then each screen waits
; for Return: main menu (Select Training is highlighted), Select Training Mission (the first
; mission), Ready Room (Begin Flight), and the Recognition Test (the manual check, shown
; before the first flight; any answer passes). Measured with the KickEmu slave on the
; A500-equivalent machine: the menu is up by field ~2800, so the first key comes at 3000 and
; one more every 505 fields. Faster machines only reach each screen sooner.
tape:	dc.w	TAPE_FIRST,RAW_RETURN, 5,RAW_RETURN|RAW_UP
	dc.w	TAPE_GAP,RAW_RETURN, 5,RAW_RETURN|RAW_UP
	dc.w	TAPE_GAP,RAW_RETURN, 5,RAW_RETURN|RAW_UP
	dc.w	TAPE_GAP,RAW_RETURN, 5,RAW_RETURN|RAW_UP
	dc.w	0

	IFND	TAPE_FIRST
TAPE_FIRST	= 3000
	ENDC
	IFND	TAPE_GAP
TAPE_GAP	= 500
	ENDC

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
	lea	tape(pc),a3
.next:	move.w	(a3)+,d2
	beq.s	.done
.wait:	exg	a5,a6
	jsr	_LVOWaitTOF(a6)
	exg	a5,a6
	lea	tape_fields(pc),a0
	addq.l	#1,(a0)
	subq.w	#1,d2
	bne.s	.wait
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
; the last event. The marker locates them in memory.
	CNOP	0,4
	dc.b	"BHTAPE!!"
tape_fields:	dc.l	0
tape_end:	dc.l	TAPE_FIRST+5+3*(TAPE_GAP+5)

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
