;*---------------------------------------------------------------------------
;  :Program.	MarbleMadness.asm
;  :Contents.	Slave for "MarbleMadness"
;  :Author.	JOTD, from Wepl sources
;  :Original	v1 
;  :Version.	$Id: wildwestworld.asm 1.2 2002/02/08 01:18:39 wepl Exp wepl $
;  :History.	07.08.00 started
;		03.08.01 some steps forward ;)
;		30.01.02 final beta
;  :Requires.	-
;  :Copyright.	Public Domain
;  :Language.	68000 Assembler
;  :Translator.	Devpac 3.14, Barfly 2.9
;  :To Do.
;---------------------------------------------------------------------------*

	INCDIR	Include:
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	INCLUDE	lvo/dos.i
	INCLUDE	lvo/exec.i
	INCLUDE	exec/tasks.i
	INCLUDE	exec/memory.i
	INCLUDE	exec/interrupts.i
	INCLUDE	exec/ports.i
	INCLUDE	hardware/intbits.i

	IFD BARFLY
	OUTPUT	"MarbleMadness.slave"
	BOPT	O+				;enable optimizing
	BOPT	OG+				;enable optimizing
	BOPT	ODd-				;disable mul optimizing
	BOPT	ODe-				;disable mul optimizing
	BOPT	w4-				;disable 64k warnings
	BOPT	wo-			;disable optimizer warnings
	SUPER
	ENDC
;============================================================================

;DEBUG

; wondering why that game needs more than 512k when running on kickemu...
; it requires 512k on a real amiga since 1986. well...

	IFD	DEBUG
FASTMEMSIZE = $0
CHIPMEMSIZE	= $C0000
	ELSE
FASTMEMSIZE	= $40000
CHIPMEMSIZE	= $80000
	ENDC
NUMDRIVES	= 1
WPDRIVES	= %0000

STACKSIZE = 8000
SETPATCH
BLACKSCREEN

; the diskimage version allows to load the diskimage in RAM
; at once, and avoids constant disk access (ex: with CD32load)
; this is the base for the CD32 version with audio tracks
; it uses an image of the cracked version (cracked exe)

	IFD	DISKIMAGE
DISKSONBOOT
CBDOSLOADSEG
	ELSE
;
;DOSASSIGN
;HRTMON
IOCACHE		= 10000
;MEMFREE	= $200
;NEEDFPU
BOOTDOS
HDINIT
	ENDC
	
;============================================================================


slv_Version=17
slv_Flags	= WHDLF_NoError|WHDLF_Examine|WHDLF_EmulTrap
slv_keyexit	= $5D	; num '*'

	; vasm: kick13.s is under whdload/ in the shared WHDLoad Src/sources
	include 	whdload/kick13.s


;============================================================================

	IFD BARFLY
	DOSCMD	"WDate  >T:date"
	ENDC

DECL_VERSION:MACRO
	dc.b	"2.3"
	IFD BARFLY
		dc.b	" "
		INCBIN	"T:date"
	ENDC
	IFD	DATETIME
		dc.b	" "
		incbin	datetime
	ENDC
	ENDM

slv_name		dc.b	"Marble Madness"
	IFD	DEBUG
	dc.b	" (DEBUG MODE)"
	ENDC
	dc.b	0
slv_copy		dc.b	"1984-1986 Atari Games & Electronic Arts",0
slv_info		dc.b	"Installed & fixed by JOTD",10,10
			dc.b	"Version "
			DECL_VERSION
		dc.b	0
slv_CurrentDir:
	dc.b	"data",0
slv_config:
	dc.b	"BW;"
	dc.b    "C1:X:Trainer Infinite Time (ESC=game over):0;"
	dc.b    "C2:X:Sound effects only (no music):0;"
	dc.b    "C3:L:Start level:Practice,Beginner,Intermediate,Aerial,Silly,Ultimate;"			
	dc.b	"C4:X:Enhanced framerate (68020+):0;"
	dc.b	"C5:X:Music and sound at NTSC tempo on PAL:0;"
	dc.b	0

; version xx.slave works

	dc.b	"$","VER: slave "
	DECL_VERSION
	dc.b	0
	even
	
intro:
	dc.b	"c/bootscr",0
introargs:
	dc.b	"c/splash"	; no linefeed or it doesn't work, buggy argument parsing for bootscr
introargs_end:
	dc.b	0
	even
	IFD	BOOTDOS
program:
	dc.b	"MarbleMadness!",0
args
	dc.b	10
args_end
	dc.b	0
	EVEN

	
_bootdos

	move.l	(_resload,pc),a2		;A2 = resload

	;get tags
		lea	(_tag,pc),a0
		jsr	(resload_Control,a2)
		

	;enable cache
		move.l	#WCPUF_Base_NC|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC|WCPUF_BC|WCPUF_SS|WCPUF_SB,d0
		move.l	#WCPUF_All,d1
		jsr	(resload_SetCPU,a2)

	;open doslib
		lea	(_dosname,pc),a1
		move.l	(4),a6
		jsr	(_LVOOldOpenLibrary,a6)
		move.l	d0,a6			;A6 = dosbase
; useful when stubbing dos C wrappers
		lea	_dosbase(pc),a0
		move.l	a6,(a0)
		
; load intro screen

	lea	intro(pc),a0
	lea	(introargs,pc),a1
	sub.l	a5,a5
	move.l	#introargs_end-introargs,d0
	bsr	_load_exe

	move.l	_buttonwait(pc),d0
	beq.b	.skw
.lmbloop
	btst	#6,$bfe001
	bne.b	.lmbloop
.skw

; load main program
	lea	program(pc),a0
	lea	(args,pc),a1
	move.l	#args_end-args,d0
	lea	patch_exe(pc),a5
	bsr	_load_exe

	rts
; < a0: program name
; < a1: arguments
; < d0: argument string length
; < a5: patch routine (0 if no patch routine)

_load_exe:
	movem.l	d0-a6,-(a7)
	move.l	d0,d2
	move.l	a0,a3
	move.l	a1,a4
	move.l	a0,d1
	jsr	(_LVOLoadSeg,a6)
	move.l	d0,d7			;D7 = segment
	beq	.end			;file not found

	;patch here
	cmp.l	#0,A5
	beq.b	.skip
	movem.l	d2/d7/a4,-(a7)
	jsr	(a5)
	bsr	_flushcache
	movem.l	(a7)+,d2/d7/a4
.skip
	;call
	move.l	d7,a1
	add.l	a1,a1
	add.l	a1,a1

	move.l	a4,a0
	move.l	($44,a7),d0		;stacksize
	sub.l	#5*4,d0			;required for MANX stack check
	movem.l	d0/d7/a2/a6,-(a7)
	move.l	d2,d0			; argument string length
	jsr	(4,a1)
	movem.l	(a7)+,d1/d7/a2/a6

	;remove exe
	move.l	d7,d1
	jsr	(_LVOUnLoadSeg,a6)

	movem.l	(a7)+,d0-a6
	rts

.end
	jsr	(_LVOIoErr,a6)
	move.l	a3,-(a7)
	move.l	d0,-(a7)
	pea	TDREASON_DOSREAD
	move.l	(_resload,pc),-(a7)
	add.l	#resload_Abort,(a7)
	rts
	ENDC
	
	IFD	CBDOSLOADSEG

get_tags:
	movem.l	d0-d1/a0-a2,-(a7)
	move.l	(_resload,pc),a2		;A2 = resload

	;get tags
	lea	(_tag,pc),a0
	jsr	(resload_Control,a2)
	movem.l	(a7)+,d0-d1/a0-a2
	rts
; < D0: BSTR filename
; < D1: seglist
_cb_dosLoadSeg
	movem.l	d7,-(a7)

	lsl.l	#2,d0
	move.l	d0,a0
	addq.l	#1,a0
	bsr	get_long

	cmp.l	#'c/bo',d0
	bne.b	.skip_intro
	
	move.l	d1,d7
	bsr	patch_intro
	bra.b	.noboot
	
.skip_intro
	cmp.l	#'Marb',D0
	bne.b	.skip
	bsr	get_tags
	
	move.l	_buttonwait(pc),d0
	beq.b	.skw
.lmbloop
	btst	#6,$bfe001
	bne.b	.lmbloop
.skw
	move.l	d1,d7	; so we can reuse the patch_exe routine
	bsr	patch_exe
.skip
.noboot
	movem.l	(a7)+,d7
	rts

_quit
	PEA	TDREASON_OK
	MOVE.L	_resload(PC),-(A7)
	add.l	#resload_Abort,(a7)
	rts

; < A0: address
; > D0: longword
get_long
	move.l	a0,-(a7)
	move.b	(a0)+,d0
	lsl.l	#8,d0
	move.b	(a0)+,d0
	lsl.l	#8,d0
	move.b	(a0)+,d0
	lsl.l	#8,d0
	move.b	(a0)+,d0
	move.l	(a7)+,a0
	rts
	

patch_intro:
	move.l	_resload(pc),a2
	move.l	d7,a1
	lea	pl_intro(pc),a0
	jsr	(resload_PatchSeg,a2)
	rts
	
open_get_args
	MOVEM.L	16(A7),D1-D2
	move.l	D1,A0
.loop
	move.b	(a0),d1
	beq.b	.out
	cmp.b	#$A,d1
	bne.b	.cont
	MOVEM.L	16(A7),D1-D2
	;lea	introargs(pc),a0
	;move.l	a0,d1
	RTS
.cont
	addq.l	#1,a0
	bra.b	.loop
.out
	MOVEM.L	16(A7),D1-D2
	rts

pl_intro
	PL_START
	PL_PS	$1dac,open_get_args
	PL_END
	

	ENDC
	
patch_exe:
	move.l	d7,d1
	add.l	d1,d1
	add.l	d1,d1
	moveq.l	#3,d2
	bsr		get_section
	lea	$005D2-$224(a0),a2
	lea	game_state_address(pc),a4
	move.l	a2,(a4)
	
	move.l	_resload(pc),a2
	move.l	d7,a1
	lea	pl_main(pc),a0
	jsr	(resload_PatchSeg,a2)

	;disable cache
	move.l	#WCPUF_Exp_NCS,d0
	move.l	#WCPUF_Exp,d1
	jsr	(resload_SetCPU,a2)

	; the display rate decides the PAL changes (WHDLoad's NTSC option makes it 60 Hz)
	bsr	is_pal
	lea	pal_display(pc),a0
	move.b	d0,(a0)

	move.l	_pal_sound(pc),d0
	beq.b	.nosound
	tst.b	(a0)
	beq.b	.nosound
	; the effects step $21740 is hunk 254 + $38
	move.l	d7,d1
	add.l	d1,d1
	add.l	d1,d1
	move.l	#254,d2
	bsr	get_section
	lea	($21740-$21708,a0),a0
	lea	sfx_step(pc),a1
	move.l	a0,(a1)
	lea	pl_pal_sound(pc),a0
	move.l	d7,a1
	jsr	(resload_PatchSeg,a2)
.nosound

	move.l	_enhanced(pc),d0
	beq.w	.noenhanced
	move.l	_attnflags(pc),d0
	btst	#AFB_68020,d0
	beq.w	.noenhanced
	lea	field_rate(pc),a0
	move.w	#60,(a0)
	tst.b	pal_display-field_rate(a0)
	beq.b	.ntsc
	move.w	#50,(a0)
.ntsc
	; the game addresses the enhanced path uses
	lea	en_table(pc),a3
	lea	en_addr(pc),a4
.addr
	move.w	(a3)+,d2
	bmi.b	.addrdone
	move.l	d7,d1
	add.l	d1,d1
	add.l	d1,d1
	bsr	get_section
	add.w	(a3)+,a0
	move.l	a0,(a4)+
	bra.b	.addr
.addrdone
	; the two position tables for interpolation, and the field counter's interrupt
	move.l	a6,-(a7)
	move.l	#2*BL_TABLE+LS_TABLE+IS_SIZE,d0
	move.l	#MEMF_PUBLIC|MEMF_CLEAR,d1
	move.l	(4).w,a6
	jsr	(_LVOAllocMem,a6)
	tst.l	d0
	beq.b	.nomem
	lea	bl_cur(pc),a0
	move.l	d0,(a0)+
	add.l	#BL_TABLE,d0
	move.l	d0,(a0)
	add.l	#BL_TABLE,d0
	lea	lists(pc),a0
	move.l	d0,(a0)
	add.l	#LS_TABLE,d0
	move.l	d0,a1
	move.b	#NT_INTERRUPT,(LN_TYPE,a1)
	move.b	#FIELD_PRI,(LN_PRI,a1)
	lea	field_count(pc),a0
	move.l	a0,(IS_DATA,a1)
	lea	field_irq(pc),a0
	move.l	a0,(IS_CODE,a1)
	moveq	#INTB_VERTB,d0
	jsr	(_LVOAddIntServer,a6)
	move.l	(a7)+,a6
	lea	pl_enhanced(pc),a0
	move.l	d7,a1
	jsr	(resload_PatchSeg,a2)
.noenhanced
	rts
.nomem
	move.l	(a7)+,a6
	rts

; VERTB server: counts fields. Its priority is above graphics.library's, so a task woken
; by WaitTOF already sees the new field. (CIA-A's TOD, the obvious counter, ticks a little
; after the vblank in FS-UAE, and some machines clock it from the mains.)
FIELD_PRI = 20
field_irq
	addq.b	#1,(a1)
	moveq	#0,d0
	rts

; Enhanced framerate (CUSTOM4, 68020+): a fixed 30 Hz world, drawn every field.
; The Framer (hunk 33) gives the Scroller a frame (one logic step and its drawing), waits
; for it and then pads to minvbl (2) vsyncs. Here the padding instead waits until the world
; clock owes a step: the clock gains 30 per vsync and a step costs the field rate (3 steps
; per 5 PAL fields, 1 per 2 NTSC fields). Each padding field also asks the Scroller for a
; draw-only job, so every field shows a new picture; the frame counter $230, which the
; logic reads, counts only the frames that a step drew.
;
; A frame is presented as soon as its draw ends: the sprite sets swap ($38F0), their
; pointers go into the copper templates ($85EC, $8630) and the copper list is rebuilt
; ($86B4, which ends with LoadView), so the display takes it at the next vsync. The game
; does that at the vsync, and the list it builds there is shown only a field later, while
; the next draw already fills the set still on screen: fine at 2 fields a frame, not at 1.
; At most one list is built per field (fields counted by a VERTB server, field_irq),
; since a second one would be written into the list on screen; a draw that ends
; after one has been built is presented by the game's own vsync path, and no draw starts
; while the display still shows the set it would fill.
;
; Every picture is interpolated, one step behind: with alpha the time since the latest step
; due, in steps (the clock's remainder over the field rate), each object's screen position
; and the displayed playfield row are prev + alpha * (cur - prev), prev being the step
; before. The draw routines read their object's screen position from the record; a wrapper
; around each call writes the blended position there and restores it afterwards. Each
; step's draw records the positions it is given; new objects, jumps and mode changes are
; drawn unblended.
DRAW_JOB = 6			; message +$14: the game's own codes are 4 (frame) and 5 (quit)

pl_enhanced
	PL_START
	PL_PS	$6E48,vsync_hook	; both per-vsync calls of the Framer
	PL_PS	$6ED0,vsync_hook
	PL_PS	$6EB4,step_due		; "count < minvbl": ge leaves the padding loop
	PL_NOP	$6EBA,4
	PL_PS	$6EC0,pad_field		; the padding loop's WaitTOF
	PL_PS	$AA32,scroller_job	; the Scroller's jsr to its frame job $B23A
	PL_PS	$B292,step_ready	; move.b #1,$5DB after a step's draw
	PL_NOP	$B298,2
	PL_PS	$7600,count_frame	; addq.l #1,$230 on a new frame
	PL_PS	$7606,show_row		; move.w $224,$226 on a new frame
	PL_NOP	$760C,4
	PL_PS	$7610,show_split	; move.w $D30C,$7692 on a new frame
	PL_NOP	$7616,4
	PL_NOP	$7664,10		; no half step ($74D4): the row is blended
	PL_PS	$767C,vsync_rebuild	; tst.b d7, beq, jsr $86B4
	PL_NOP	$7682,4
	PL_PS	$B28C,step_draw		; a step's jsr to the draw pass $11704
	; the draw pass's calls of the draw routines (hunk 26), by object type
	PL_PS	$11850,draw_2a
	PL_PS	$1187E,draw_1
	PL_PS	$118AC,draw_2
	PL_PS	$118D6,draw_2c
	PL_PS	$118FC,draw_4
	PL_PS	$11922,draw_e
	PL_PS	$11946,draw_5
	PL_PS	$11972,draw_7
	PL_PS	$11996,draw_f
	PL_PS	$8DF4,wait_fields	; the vsync wait $8DF0(n): move.w $5D2,d0
	; the lists a step leaves for its draw: the scenery covering a sprite ($11270, per
	; record), the marble's dots ($6864); and the view offset the scenery masks read
	PL_PS	$606C,dots_call		; type 1
	PL_PS	$60C4,occl_call		; type 1
	PL_PS	$61A6,occl_call		; type 2
	PL_PS	$62B4,occl_call		; type 4
	PL_PS	$644C,occl_call		; type $F
	PL_PS	$5EE2,shard_call	; type 1, broken: the lists' images ($10FDC)
	PL_PS	$5EFE,shard_call
	PL_PS	$6402,shard_call	; type $F
	PL_PS	$116BC,mask_view	; move.l $9BA,d3
	PL_END

; screen position field, routine (offset in hunk 26 at $5BE0), largest blended move, the
; field pointing at the image's pointer (0: none; the image is the record's first long)
DRAWCALL	MACRO
	move.l	#(\3<<16)|\1,d0
	move.l	#(\4<<16)|(\2-$5BE0),d1
	bra	blend_call
	ENDM
draw_1	bsr	marble_flag
	DRAWCALL	$1E,$5DFC,48,0
draw_2	DRAWCALL	$1E,$60F6,48,$64
draw_4	DRAWCALL	$28,$621C,48,$62
draw_5	DRAWCALL	$4E,$64B6,48,$42
draw_7	DRAWCALL	$20,$650A,48,$1C	; types 7 to 9
draw_e	DRAWCALL	$28,$645E,48,$3A
draw_f	bsr	dots_f
	DRAWCALL	$20,$6350,48,$1C
draw_2a	DRAWCALL	$06,$62C6,48,0
draw_2c	DRAWCALL	$00,$6562,48*16,0	; in 1/16 pixels

; type $F's draw adds $40 to five dot offsets (+$2C, 8 apart) while $6860 is set; take it
; back first on a draw-only job, so that they move once a step
dots_f
	lea	draw_job(pc),a0
	tst.b	(a0)
	beq.b	.done
	move.l	a_h27(pc),a0
	tst.w	($6860-$6750,a0)
	beq.b	.done
	move.l	(8,a7),a0		; the record (our caller's argument)
	lea	($2C,a0),a0
	moveq	#4,d0
.dot
	sub.w	#$40,(a0)
	addq.l	#8,a0
	dbf	d0,.dot
.done
	rts

; A broken marble: the step sets +$EB and fills its lists (+$38, +$AE) with the shards'
; images, and the draw places them ($10FDC) and clears +$EB. A step's draw saves the flag,
; a draw job puts it back (the lists are list_call's).
MF_MAX = 4
marble_flag
	move.l	(8,a7),a0		; the record (our caller's argument)
	movem.l	d0/a1,-(a7)
	lea	mf_table(pc),a1
	tst.b	bl_record-mf_table(a1)
	beq.b	.restore
	move.w	(a1),d0
	cmp.w	#MF_MAX,d0
	bhs.b	.done
	addq.w	#1,(a1)+
	mulu.w	#6,d0
	add.w	d0,a1
	move.l	a0,(a1)+
	move.b	($EB,a0),(a1)
	bra.b	.done
.restore
	tst.b	draw_job-mf_table(a1)
	beq.b	.done
	move.w	(a1)+,d0
	bra.b	.next
.look
	cmp.l	(a1),a0
	bne.b	.skip
	move.b	(4,a1),($EB,a0)
	bra.b	.done
.skip
	addq.l	#6,a1
.next
	dbf	d0,.look
.done
	movem.l	(a7)+,d0/a1
	rts

BL_MAX = 48				; positions per table
BL_ENTRY = 14				; record.l, field.w, x.w, y.w, image.l
BL_TABLE = 2+BL_MAX*BL_ENTRY		; count.w, entries

; > d0 = largest move << 16 | field offset, d1 = image field << 16 | routine's offset in
; hunk 26; the record is the routine's first argument. Calls the routine with the record's
; position blended; an object whose image changed since the step before is not blended
; (the game moves it with the new frame).
blend_call
	movem.l	d2-d6/a2-a4,-(a7)
	move.l	(36,a7),a2		; the record
	move.l	d1,d4
	swap	d4
	sub.l	a1,a1			; its image
	tst.w	d4
	beq.b	.img
	move.l	(a2,d4.w),a1
	move.l	(a1),a1
.img
	lea	(a2,d0.w),a3		; its position
	move.w	(a3),d2			; cur x
	move.w	(2,a3),d3		; cur y
	lea	bl_slot(pc),a0
	move.l	a3,(a0)+		; restored after the routine
	move.l	(a3),(a0)+
	move.l	(32,a7),(a0)		; the caller
	lea	blend_return(pc),a0
	move.l	a0,(32,a7)
	; the step's draw records the position
	lea	bl_record(pc),a0
	tst.b	(a0)
	beq.b	.find
	move.l	bl_cur(pc),a4
	move.w	(a4),d4
	cmp.w	#BL_MAX,d4
	bhs.b	.find
	addq.w	#1,(a4)
	mulu.w	#BL_ENTRY,d4
	lea	(2,a4,d4.l),a4
	move.l	a2,(a4)+
	move.w	d0,(a4)+
	move.w	d2,(a4)+
	move.w	d3,(a4)+
	move.l	a1,(a4)
.find
	lea	bl_valid(pc),a0
	tst.b	(a0)
	beq.b	.call
	move.w	bl_record-bl_valid(a0),d4	; bl_record, draw_job: one of ours
	beq.b	.call
	move.l	bl_prev(pc),a4
	move.w	(a4)+,d4
	bra.b	.next
.look
	cmp.l	(a4),a2
	bne.b	.skip
	cmp.w	(4,a4),d0
	beq.b	.found
.skip
	lea	(BL_ENTRY,a4),a4
.next
	dbf	d4,.look
	bra.b	.call
.found
	cmp.l	(10,a4),a1
	bne.b	.call			; a new frame
	swap	d0			; the largest move
	move.w	(6,a4),d4		; prev x
	move.w	d2,d5
	sub.w	d4,d5
	bsr	blend
	bcs.b	.call
	add.w	d5,d4
	move.w	d4,(a3)
	move.w	(8,a4),d4		; prev y
	move.w	d3,d5
	sub.w	d4,d5
	bsr	blend
	bcs.b	.restore_x
	add.w	d5,d4
	move.w	d4,(2,a3)
	bra.b	.call
.restore_x
	move.w	d2,(a3)
.call
	move.l	a_h26(pc),a0
	add.w	d1,a0
	movem.l	(a7)+,d2-d6/a2-a4
	jmp	(a0)

blend_return
	subq.l	#4,a7
	movem.l	a0/a1,-(a7)
	lea	bl_slot(pc),a0
	move.l	(a0)+,a1
	move.l	(a0)+,(a1)
	move.l	(a0),(8,a7)
	movem.l	(a7)+,a0/a1
	rts

; > d5.w = cur - prev, d0.w = largest move; < d5.w = its share at alpha, rounded half away
; from zero (so that a sprite and the playfield moved by -d and +d stay together); cs when
; the move is too large to blend
blend
	IFD	NOBLEND			; check build: every draw unblended
	ori.b	#1,ccr
	rts
	ENDC
	move.w	d5,d6
	bpl.b	.pos
	neg.w	d6
.pos
	cmp.w	d0,d6
	bhi.b	.big
	move.l	d7,-(a7)
	muls.w	bl_alpha(pc),d6
	move.w	field_rate(pc),d7
	lsr.w	#1,d7
	ext.l	d7
	add.l	d7,d6
	divu.w	field_rate(pc),d6
	tst.w	d5
	bpl.b	.done
	neg.w	d6
.done
	move.w	d6,d5
	move.l	(a7)+,d7
	andi.b	#$FE,ccr		; cc
	rts
.big
	ori.b	#1,ccr
	rts

; a step's draw: rotate the tables and the rows, then draw at the step's alpha
step_draw
	lea	bl_alpha(pc),a0
	move.w	step_alpha(pc),(a0)
	lea	bl_cur(pc),a0
	move.l	(a0)+,d0
	move.l	(a0),-(a0)
	move.l	d0,(4,a0)		; prev = the old cur
	move.l	(a0),a1
	clr.w	(a1)			; the new cur is empty
	move.l	a_h3(pc),a1
	lea	bl_valid(pc),a0
	st	(a0)
	move.w	($5D2-$224,a1),d0	; the mode
	cmp.w	#MODE_MENU,d0
	beq.b	.noblend		; menu_pointer moves the pointer every field
	cmp.w	bl_mode(pc),d0
	beq.b	.same
.noblend
	sf	(a0)			; no blending into a new mode
	lea	bl_mode(pc),a0
	move.w	d0,(a0)
.same
	lea	row_prev(pc),a0
	move.w	(2,a0),(a0)		; row_prev = row_cur
	move.w	(a1),(2,a0)		; row_cur = $224
	move.l	a_split_logic(pc),a1
	move.w	(6,a0),(4,a0)		; split_prev = split_cur
	move.w	(a1),(6,a0)		; split_cur = $D30C
	move.l	a_h3(pc),a1
	move.w	(10,a0),(8,a0)		; view_prev = view_cur
	move.w	($9BA+2-$224,a1),(10,a0)	; view_cur = $9BA
	tst.b	(bl_valid-row_prev,a0)
	bne.b	.rows
	move.w	(2,a0),(a0)
	move.w	(6,a0),(4,a0)
	move.w	(10,a0),(8,a0)
.rows
	move.l	lists(pc),a0
	clr.w	(a0)			; this step's lists are saved afresh
	lea	mf_table(pc),a0
	clr.w	(a0)
	bsr	set_view
	lea	bl_record(pc),a0
	st	(a0)
	bsr	draw_wait
	move.l	a_draw(pc),a0
	jsr	(a0)
	lea	bl_record(pc),a0
	sf	(a0)
	lea	bl_view(pc),a0
	clr.w	(a0)
	rts

; bl_view = the blended view offset $9BA minus the step's: what a draw at bl_alpha adds to
; the screen y of the scenery (sprites' blended positions include it already)
set_view
	movem.l	d0/d5-d6,-(a7)
	moveq	#0,d5
	lea	bl_valid(pc),a0
	tst.b	(a0)
	beq.b	.set
	move.w	view_cur(pc),d6
	move.w	d6,d5
	sub.w	view_prev(pc),d5
	moveq	#64,d0
	bsr	blend
	bcs.b	.none
	add.w	view_prev(pc),d5
	sub.w	d6,d5
	bra.b	.set
.none
	moveq	#0,d5
.set
	lea	bl_view(pc),a0
	move.w	d5,(a0)
	movem.l	(a7)+,d0/d5-d6
	rts

; $116BC in the scenery mask $11678: the view offset, moved with the blended view
mask_view
	move.l	a0,-(a7)
	move.l	a_h3(pc),a0
	move.l	($9BA-$224,a0),d3
	move.w	bl_view(pc),a0
	add.l	a0,d3
	move.l	(a7)+,a0
	rts

; The step leaves lists in the records for its draw, and the draw marks each entry it uses
; (-1): the pieces of scenery that cover a sprite (image.l, x.w, y.w, in screen positions;
; $11270(list, n, x, y, sprite)) and the marble's dots ($6864(list, sprite), 4 entries).
; A step's draw saves each list before its use, a draw job puts it back first; the screen y
; of the scenery moves by bl_view for the call and is restored after it.
LS_MAX = 32				; lists per step
LS_ENTRY = 4+2+2+5*8			; list.l, n.w, pad, the entries
LS_TABLE = 2+LS_MAX*LS_ENTRY

occl_call
	move.l	a_occl(pc),a0
	move.l	(8,a7),d0		; n
	moveq	#5,d1			; arguments
	bra.b	list_call
shard_call				; $10FDC(list, image, n)
	move.l	a_shards(pc),a0
	move.l	(12,a7),d0
	moveq	#3,d1
	bra.b	list_call
dots_call
	move.l	a_dots(pc),a0
	moveq	#4,d0
	moveq	#2,d1			; arguments
	bset	#31,d1			; and no y to move
list_call
	movem.l	d2-d4/a2-a4,-(a7)
	move.l	a0,a4			; the routine
	move.l	(28,a7),a2		; the list
	tst.w	d0
	beq.w	.plain
	cmp.w	#5,d0
	bhi.w	.plain
	lea	bl_record(pc),a1
	tst.w	(a1)			; bl_record, draw_job
	beq.w	.plain
	move.l	lists(pc),a3
	move.w	d0,d3
	add.w	d3,d3			; longs in the list
	subq.w	#1,d3
	tst.b	(a1)
	beq.b	.restore
	move.w	(a3),d2			; a step's draw: save it
	cmp.w	#LS_MAX,d2
	bhs.b	.move
	addq.w	#1,(a3)
	move.w	d2,d4
	lsl.w	#5,d2
	lsl.w	#4,d4
	add.w	d4,d2			; * 48
	lea	(2,a3,d2.w),a3
	move.l	a2,(a3)+
	move.w	d0,(a3)+
	addq.l	#2,a3
	move.l	a2,a0
.save
	move.l	(a0)+,(a3)+
	dbf	d3,.save
	bra.b	.move
.restore
	move.w	(a3)+,d2		; a draw job: find it
	bra.b	.next
.look
	cmp.l	(a3),a2
	bne.b	.skip
	cmp.w	(4,a3),d0
	beq.b	.found
.skip
	lea	(LS_ENTRY,a3),a3
.next
	dbf	d2,.look
	bra.b	.plain
.found
	lea	(8,a3),a3
	move.l	a2,a0
.put
	move.l	(a3)+,(a0)+
	dbf	d3,.put
.move
	move.w	bl_view(pc),d2
	beq.b	.plain
	tst.l	d1
	bmi.b	.plain
	move.w	d0,a3			; n (the routine keeps d2-d4/a2-a4)
	bsr.b	.shift
	move.w	d1,d3			; the arguments, again
	move.w	d1,d4
	lsl.w	#2,d4
	add.w	#24,d4			; the last one's offset, also after each push
.arg
	move.l	(a7,d4.w),-(a7)
	subq.w	#1,d3
	bne.b	.arg
	jsr	(a4)
	lea	(-24,a7,d4.w),a7
	neg.w	d2
	bsr.b	.shift
	movem.l	(a7)+,d2-d4/a2-a4
	rts
.plain
	move.l	a4,a0
	movem.l	(a7)+,d2-d4/a2-a4
	jmp	(a0)
; add d2 to the y of the list's a3 entries
.shift
	move.l	a2,a0
	move.w	a3,d3
	bra.b	.snext
.sadd
	add.w	d2,(6,a0)
	addq.l	#8,a0
.snext
	dbf	d3,.sadd
	rts

; the displayed row of the frame about to be shown, from the frame's alpha
frame_row
	movem.l	d0/d5-d6/a0,-(a7)
	move.w	row_cur(pc),d5
	sub.w	row_prev(pc),d5
	and.w	#511,d5			; the 512-row circular playfield
	cmp.w	#256,d5
	blo.b	.fwd
	sub.w	#512,d5
.fwd
	moveq	#64,d0
	bsr	blend
	bcc.b	.blend
	move.w	row_cur(pc),d5
	bra.b	.set
.blend
	add.w	row_prev(pc),d5
	and.w	#511,d5
.set
	lea	pending_row(pc),a0
	move.w	d5,(a0)
	move.w	split_cur(pc),d5
	sub.w	split_prev(pc),d5
	moveq	#64,d0
	bsr	blend
	bcc.b	.sblend
	move.w	split_cur(pc),d5
	bra.b	.sset
.sblend
	add.w	split_prev(pc),d5
.sset
	lea	pending_split(pc),a0
	move.w	d5,(a0)
	movem.l	(a7)+,d0/d5-d6/a0
	rts

show_row
	move.l	a_h3(pc),a0
	move.w	pending_row(pc),(2,a0)	; $226
	rts

; one vsync: credit the world clock, then the game's per-vsync routine (its argument stays
; on the stack); at most two steps are owed, so a long frame does not run a burst
vsync_hook
	lea	world_clock(pc),a0
	move.w	(a0),d0
	add.w	#30,d0
	move.w	field_rate(pc),d1
	add.w	d1,d1
	cmp.w	d1,d0
	ble.b	.keep
	move.w	d1,d0
.keep
	move.w	d0,(a0)
	move.l	a_vsync(pc),-(a7)
	rts

; a field without a step: send a draw job if the Scroller is idle and its last frame has
; been shown, then wait for the vsync. A draw that starts before the vsync has taken the
; last sprite set spins in $1179C until it does, so sending one regardless would leave
; every later draw a field late (and the CPU spinning).
pad_field
	lea	draw_busy(pc),a0
	tst.b	(a0)
	bne.b	.wait
	move.l	a_ready(pc),a1
	tst.b	(a1)
	bne.b	.wait
	move.l	a_port(pc),a1
	move.l	(a1),d0			; the Scroller's port
	beq.b	.wait
	move.l	d0,a1
	moveq	#0,d1
	move.b	(MP_SIGBIT,a1),d1
	move.l	a_scroller(pc),a1
	cmp.b	#TS_WAIT,(TC_STATE,a1)
	bne.b	.wait
	move.l	(TC_SIGWAIT,a1),a1
	exg	d0,a1			; d0 = the signals waited for, a1 = the port
	btst	d1,d0
	exg	d0,a1
	beq.b	.wait
	st	(a0)
	move.l	d0,a0
	lea	draw_msg(pc),a1
	move.l	#DRAW_JOB,($14,a1)
	move.w	world_clock(pc),($18,a1)	; the job's alpha
	move.l	a6,-(a7)
	move.l	(4).w,a6
	jsr	(_LVOPutMsg,a6)
	move.l	(a7)+,a6
.wait
	move.l	a_waittof(pc),-(a7)
	rts

; the game's waits of n vsyncs ($8DF0: the end of a race, the bonus count, menu clicks)
; last n/60 s, as on NTSC: n * field_rate / 60 fields, the remainder carried over
wait_fields
	move.w	($A,a6),d0		; n
	ble.b	.keep
	mulu.w	field_rate(pc),d0
	add.w	wait_rem(pc),d0
	divu.w	#60,d0
	move.w	d0,($A,a6)
	swap	d0
	lea	wait_rem(pc),a0
	move.w	d0,(a0)
.keep
	move.l	a_h3(pc),a0
	move.w	($5D2-$224,a0),d0
	rts

; the Scroller's job: the game's frame, or a draw of the current state (the message stays
; ours; it needs no reply)
scroller_job
	move.l	(4,a7),a0
	cmp.l	#DRAW_JOB,($14,a0)
	beq.b	.draw
	move.l	a_frame_job(pc),-(a7)
	rts
.draw
	lea	bl_alpha(pc),a1
	move.w	($18,a0),(a1)
	bsr	set_view
	bsr	draw_wait
	bsr	menu_pointer
	lea	draw_job(pc),a0
	st	(a0)
	move.l	a_draw(pc),a0
	jsr	(a0)
	lea	draw_job(pc),a0
	sf	(a0)
	lea	bl_view(pc),a0
	clr.w	(a0)
	lea	draw_frame(pc),a0
	st	(a0)
	bsr	present
	lea	draw_busy(pc),a0
	sf	(a0)
	rts

; the options menu reads the mouse once a step; a draw job reads it again and moves the
; pointer ($CCA, type $2C, in 1/16 pixel) the way the menu's step does ($CBB4)
MODE_MENU = 5
menu_pointer
	move.l	a_h3(pc),a1
	cmp.w	#MODE_MENU,($5D2-$224,a1)
	bne.b	.done
	move.l	a_menu(pc),a0
	cmp.b	#2,(a0)			; the menu is up
	bne.b	.done
	clr.l	-(a7)			; port 0
	pea	($CDB8-$CDAC,a0)
	pea	($CDB6-$CDAC,a0)
	move.l	a_mouse(pc),a0
	jsr	(a0)
	lea	(12,a7),a7
	move.l	a_menu(pc),a0
	move.l	a_h3(pc),a1
	lea	($CCA-$224,a1),a1
	move.w	($CDB6-$CDAC,a0),d0
	lsl.w	#4,d0
	move.w	d0,(a1)
	move.w	#$100-8,d0
	sub.w	($CDB8-$CDAC,a0),d0
	lsl.w	#4,d0
	move.w	d0,(2,a1)
.done
	rts

step_ready
	lea	draw_frame(pc),a0
	sf	(a0)
	bra	present

; don't start a draw in the field in which the display still shows its target set
draw_wait
.again
	move.b	field_count(pc),d0
	cmp.b	block_field(pc),d0
	bne.b	.go
	move.l	a_waittof(pc),a0
	jsr	(a0)
	bra.b	.again
.go
	rts

; a draw has ended: present it now if no copper list has been built in this field, else
; leave it to the game's vsync path ($5BCA stays set); then flag the frame ready ($5DB)
present
	bsr	frame_row
	move.l	a6,-(a7)
	move.l	(4).w,a6
	jsr	(_LVOForbid,a6)
	move.b	field_count(pc),d0
	cmp.b	last_build_field(pc),d0
	beq.b	.ready
	move.l	a_swap(pc),a0
	jsr	(a0)
	move.l	a_display(pc),a0
	move.l	(a0),-(a7)
	move.l	a_cop_sprites(pc),a0
	jsr	(a0)
	move.l	a_cop_sprites2(pc),a0
	jsr	(a0)
	addq.l	#4,a7
	move.l	a_h3(pc),a0
	move.w	pending_row(pc),(2,a0)	; $226
	move.l	a_split(pc),a0
	move.w	pending_split(pc),(a0)	; $7692
	bsr	build
	lea	block_field(pc),a0
	move.b	d0,(a0)
.ready
	move.l	a_ready(pc),a0
	move.b	#1,(a0)
	jsr	(_LVOPermit,a6)
	move.l	(a7)+,a6
	rts

; rebuild the copper list; < d0.b = the field it ended in
build
	move.l	a_rebuild(pc),a0
	jsr	(a0)
	lea	owed(pc),a0
	sf	(a0)
	move.l	a_display(pc),a0
	lea	built_display(pc),a1
	move.l	(a0),(a1)
	move.b	field_count(pc),d0
	lea	last_build_field(pc),a0
	move.b	d0,(a0)
	rts

; the end of the per-vsync routine (d7: something changed): build now if the sets were
; swapped here, or if a change has waited a whole field for a draw; else leave it to this
; field's draw, which builds anyway
vsync_rebuild
	move.l	a_display(pc),a0
	move.l	(a0),d0
	cmp.l	built_display(pc),d0
	bne.b	.swapped
	move.b	field_count(pc),d0
	cmp.b	last_build_field(pc),d0
	beq.b	.done			; built in this field already
	lea	owed(pc),a0
	tst.b	(a0)
	beq.b	.new
	cmp.b	owed_field(pc),d0
	bne.b	.build			; owed since an earlier field
	rts
.new
	tst.b	d7
	beq.b	.done
	st	(a0)
	lea	owed_field(pc),a0
	move.b	d0,(a0)
.done
	rts
.swapped
	bsr	build
	lea	block_field(pc),a0
	move.b	d0,(a0)
	rts
.build
	bra	build

show_split
	move.l	a_split(pc),a0
	move.w	pending_split(pc),(a0)
	rts

; the vsync that shows a new frame: count it only if a step drew it
count_frame
	move.b	draw_frame(pc),d0
	bne.b	.draw
	move.l	a_frames(pc),a0
	addq.l	#1,(a0)
.draw
	rts

; > ccr: ge when a step is owed (and charges it), lt otherwise
step_due
	move.w	world_clock(pc),d0
	sub.w	field_rate(pc),d0
	blt.b	.not
	lea	world_clock(pc),a0
	move.w	d0,(a0)
	lea	step_alpha(pc),a0
	move.w	d0,(a0)
	moveq	#0,d0
	rts
.not
	moveq	#-1,d0
	rts

; PAL sound at the NTSC tempo (CUSTOM5): both sound clocks tick once a field.
pl_pal_sound
	PL_START
	; music: each vblank step adds (tempo << 16) / 150; on PAL / 125 (6/5 of it)
	PL_L	$1F3D8,125
	; effects: SfxTask runs the envelope step once per vblank; run it 6 times per 5
	PL_PS	$20B1A,sfx_tick
	PL_END

sfx_tick
	move.l	d2,-(a7)
	lea	sfx_phase(pc),a0
	move.w	(a0),d2
	addq.w	#6,d2
.step
	cmp.w	#5,d2
	blt.b	.done
	subq.w	#5,d2
	move.w	d2,(a0)
	move.l	sfx_step(pc),a0
	jsr	(a0)			; the game's step: keeps d2-d7/a2-a6
	lea	sfx_phase(pc),a0
	move.w	(a0),d2
	bra.b	.step
.done
	move.w	d2,(a0)
	move.l	(a7)+,d2
	rts

; > d0.b: -1 when the display has more than 300 lines (PAL), else 0. Watches the beam
;   for two frame wraps and keeps the highest line seen.
is_pal
	movem.l	d1-d3,-(a7)
	moveq	#0,d1			; highest line
	moveq	#2,d2			; wraps to go
	move.l	$dff004,d3
	lsr.l	#8,d3
	and.w	#$1ff,d3
.loop
	move.l	$dff004,d0
	lsr.l	#8,d0
	and.w	#$1ff,d0
	cmp.w	d3,d0
	bhs.b	.same
	subq.w	#1,d2
	beq.b	.done
.same
	move.w	d0,d3
	cmp.w	d1,d0
	bls.b	.loop
	move.w	d0,d1
	bra.b	.loop
.done
	cmp.w	#300,d1
	shi	d0
	movem.l	(a7)+,d1-d3
	rts

pl_main
	PL_START
	; section 14
	PL_PS	$02CF0,key_control
	; section 61
	PL_W	$09910+$E6,$4E71
	PL_PS	$09910+$E8,fix_accessfault_level1
	; section 77, decrease seconds for both players	
	PL_PS	$0B566,seconds_count
	
	; section 90
	PL_L	$CF46,'Mous'
	PL_B	$CF4A,'e'

	PL_W	$CF56,"Jo"
	PL_B	$CF58,"y"
	PL_B	$CF59,$20
	; section 245
	PL_PS	$1E684,fix_accessfault_level5
	
	PL_PS	$033FA,set_start_level
		

	; section 336

	PL_IFC2
	PL_NOP	$1F384,4
	PL_ENDIF
	
	;;PL_PS	$2099A,ingame_loop
	
	PL_END
	; I had a hard time figuring out both A5 pointer origins, so let's bruteforce it
seconds_count
	movem.l	d1/a0/a1,-(a7)
	move.b	pause_flag(pc),d1
	beq.b	.unpause
	lea	pause_flag(pc),a0
	clr.b	(a0)
.wait
	btst.b	#6,$BFE001
	beq.b	.unpause
	btst.b	#7,$BFE001
	beq.b	.unpause
	bra.b	.wait
.unpause
	
	lea	player_seconds_table(pc),a0
	tst.l	(a0)
	bne.b	.first_slot_full
	; first slot zero: store this A5 value for later
	move.l	A5,(a0)
	bra.b	.all_slots_full
.first_slot_full
	addq.l	#4,a0
	tst.l	(a0)
	bne.b	.all_slots_full
	; second slot zero: store this A5 value for later
	move.l	A5,(a0)	
.all_slots_full
	MOVE	(A5),D0			;0B566: 3015	; red/blue player seconds count
	move.l	_infinte_time(pc),d1
	beq.b	.normal
	; not active if not enough seconds
	; leaves power to ESC button which sets seconds to 0
	; and that cannot happen any other way
	cmp.w	#5,d0
	bcs.b	.normal
	move.w	#100,d0
.normal
	SUBQ	#1,D0			;0B568: 5340	; sub seconds
.set
	MOVE	D0,(A5)			;0B56A: 3A80
	
	; on level select, add seconds bonus for both players, only once
	move.l	player_seconds_table+4(pc),d1
	beq.b	.noadd	; no second player/first time in the routine: do nothing

	moveq	#0,d1
	lea	seconds_bonus(pc),a0
	move.b	(a0),d1
	beq.b	.noadd
	clr.b	(a0)
	move.l	player_seconds_table(pc),a0
	add.w	d1,(a0)
	move.l	player_seconds_table+4(pc),a1
	cmp.l	a1,a0
	beq.b	.noadd	; no second player
	add.w	d1,(a1)
.noadd

	movem.l	(a7)+,d1/a0/a1
	RTS
	
	
set_start_level
	move.l	_start_level(pc),d0
	movem.l	a0/a1,-(a7)
	; reset table (in case we switch from 2 players to 1 player)
	
	bsr	set_seconds_to_zero
	
	lea	player_seconds_table(pc),a0
	clr.l	(a0)+
	clr.l	(a0)
	
	lea	seconds_bonus_table(pc),a1
	lea	seconds_bonus(pc),a0
	move.b	(a1,d0.w),(a0)
	movem.l	(a7)+,a0/a1
	rts

set_seconds_to_zero
	move.l	player_seconds_table(pc),a0
	cmp.l	#0,a0
	beq.b	.skip
	clr.w	(a0)
	move.l	player_seconds_table+4(pc),a0
	cmp.l	#0,a0
	beq	.skip
	clr.w	(a0)
.skip
	rts
	; preserving more than D0 & A0 breaks the game
	; that's what I call shaving the stack too close...
	; even like that it crashes, so relocating the stack somewhere else
	; just for that routine (I feel that there are some issues with the code,
	; like returning references to local variables, calling this function, then trying to useful
	; those references. Works until the stack is used... classic error.
key_control:
	move.l	A7,$104.W
	lea	.local_stack(pc),a7
	movem.l	D0/A0,-(A7)
	move.b	$BFEC01,D0
	not.b	D0
	ror.b	#1,D0
	move.b	#0,$BFEC01	; we're the only ones reading this
	lea		old_sdr_value(pc),a0
	cmp.b	(a0),d0
	beq	.skip		; same key as previously: skip
	move.b	d0,(a0)
	cmp.b	#$45,D0	
	bne.b	.noesc
	; set seconds to 0 for both players
	bsr	set_seconds_to_zero

	
	bra	.skip
.noesc
	cmp.b	#$50,D0		; F1
	bne.b	.noadd
	; add 10 seconds for each player
	lea	seconds_bonus(pc),a0
	move.b	#10,(a0)
	bra	.skip

.noadd
	;;IFD	DEBUG
	cmp.b	#$5F,D0		; HELP
	bne.b	.nohelp
	; that doesn't work, because none of the players gets the
	; "player ended race" flag, so skips to next level without any
	; active player...
	move.l	game_state_address(pc),a0
	move.w	#3,(a0)		; level completed
.nohelp
	;;ENDC
	cmp.b	#$19,D0		; HELP
	bne.b	.nopause
	lea	pause_flag(pc),a0
	st.b	(a0)
.nopause
.skip
	movem.l	(A7)+,D0/A0
	move.l	$104.W,A7
	lea	$100.W,A0	; original game
	rts

	ds.l	$100
.local_stack:

fix_accessfault_level1:
	move.l	D0,-(a7)
	move.l	A4,D0
	bmi.b	.avoid
.move
	move.b	(A4),-(A3)
	move.b	(2,A4),($24,A3)
	move.l	(A7)+,D0
	rts
.avoid
	lea	.zeros(pc),A4
	bra.b	.move
.zeros:
	dc.l	0,0,0,0

; < d1 seglist
; < d2 section #
; > a0 segment
get_section
	move.l	d1,a0
	subq	#1,d2
	bmi.b	.out
.loop
	move.l	(a0),a0
	add.l	a0,a0
	add.l	a0,a0
	dbf	d2,.loop
.out
	addq.l	#4,a0
	rts
; access fault at mad level (5), when a bird hits the marble

fix_accessfault_level5:
	cmp.l	#-1,A0
	beq.b	.bypass

	move.b	(A0),D1
	ext.w	D1
	ext.l	D1
.bypass:
	addq.l	#4,A7
	movem.l	(A7)+,D2-D7/A2-A5
	unlk	A6
	rts

;---------------

_tag		dc.l	WHDLTAG_CUSTOM1_GET
_infinte_time	dc.l	0
	dc.l	WHDLTAG_BUTTONWAIT_GET
_buttonwait
	dc.l	0
	dc.l	WHDLTAG_CUSTOM3_GET
_start_level	dc.l	0
	dc.l	WHDLTAG_CUSTOM4_GET
_enhanced	dc.l	0
	dc.l	WHDLTAG_CUSTOM5_GET
_pal_sound	dc.l	0
	dc.l	0
_dosbase
	dc.l	0
game_state_address:
	dc.l	0
player_seconds_table
	dc.l	0,0
seconds_bonus:
	dc.b	0
pause_flag
	dc.b	0
seconds_bonus_table:
	dc.b	0,0,40,50,55,60,65
old_sdr_value:
	dc.b	0
pal_display:
	dc.b	0		; -1: the display has PAL's 312 lines
	even
sfx_step:
	dc.l	0		; the game's effects step ($21740)
sfx_phase:
	dc.w	0		; fifths of a step owed
en_table			; hunk, offset in it: the addresses below, in order
	dc.w	36,$7596-$74D4		; the Framer's per-vsync routine
	dc.w	342,$24B54-$24A64	; the WaitTOF stub
	dc.w	72,$AF60-$AB1C		; the Scroller's port pointer
	dc.w	72,0			; the Scroller's Task ($AB1C)
	dc.w	74,$B23A-$AF74		; the Scroller's frame job
	dc.w	150,0			; the draw pass $11704
	dc.w	3,$5DB-$224		; frame ready
	dc.w	3,$230-$224		; frame counter
	dc.w	3,0			; $224: hunk 3
	dc.w	26,0			; the draw routines
	dc.w	23,$38F0-$3558		; swap the sprite sets
	dc.w	49,$85EC-$8400		; sprite pointers into the copper templates
	dc.w	49,$8630-$8400
	dc.w	49,$86B4-$8400		; rebuild the copper list
	dc.w	24,$5B2C-$3FCC		; the displayed sprite set
	dc.w	37,$7692-$7690		; the view's distance from the top, shown
	dc.w	93,$D30C-$D308		; the same, from the logic
	dc.w	27,0			; $6860: type $F's dots move
	dc.w	90,0			; $CDAC: the options menu's state
	dc.w	200,$19008-$18F64	; the menu's mouse reader
	dc.w	147,$11270-$10FDC	; mask a sprite by a list of scenery
	dc.w	29,0			; $6864: plot the marble's dots
	dc.w	147,0			; $10FDC: place a list's images
	dc.w	-1
en_addr
a_vsync:	dc.l	0
a_waittof:	dc.l	0
a_port:		dc.l	0
a_scroller:	dc.l	0
a_frame_job:	dc.l	0
a_draw:		dc.l	0
a_ready:	dc.l	0
a_frames:	dc.l	0
a_h3:		dc.l	0
a_h26:		dc.l	0
a_swap:		dc.l	0
a_cop_sprites:	dc.l	0
a_cop_sprites2:	dc.l	0
a_rebuild:	dc.l	0
a_display:	dc.l	0
a_split:	dc.l	0
a_split_logic:	dc.l	0
a_h27:		dc.l	0
a_menu:		dc.l	0
a_mouse:	dc.l	0
a_occl:		dc.l	0
a_dots:		dc.l	0
a_shards:	dc.l	0
lists:		dc.l	0		; the lists saved at a step's draw
built_display:	dc.l	0		; the set the last copper list shows
bl_cur:		dc.l	0		; this step's positions
bl_prev:	dc.l	0		; the step before's
bl_slot:	dc.l	0,0,0		; field, its value, the caller's return
bl_alpha:	dc.w	0		; this draw's alpha, in 1/field_rate steps
step_alpha:	dc.w	0
bl_mode:	dc.w	-1
wait_rem:	dc.w	0		; wait_fields' remainder, in 1/60 field
row_prev:	dc.w	0
row_cur:	dc.w	0
split_prev:	dc.w	0		; row_prev + 4
split_cur:	dc.w	0
view_prev:	dc.w	0		; $9BA at the step before (row_prev + 8)
view_cur:	dc.w	0
bl_view:	dc.w	0		; this draw's view offset over the step's
pending_row:	dc.w	0
pending_split:	dc.w	0
last_build_field:	dc.b	-1
block_field:	dc.b	-1
owed:		dc.b	0		; the vsync found a change not yet built
owed_field:	dc.b	0
mf_table:	dcb.b	2+MF_MAX*6,0	; marble_flag: count.w, (record.l, +$EB.b, pad)
bl_record:	dc.b	0		; a step's draw: record the positions
draw_job:	dc.b	0		; a draw job's draw (follows bl_record)
bl_valid:	dc.b	0		; prev is from the same mode
field_count:	dc.b	0		; fields, from field_irq
draw_msg:
	dcb.b	MN_SIZE+6,0	; a Message, the job code (long) and its alpha (word)
draw_busy:
	dc.b	0		; a draw job is queued or running
draw_frame:
	dc.b	0		; the pending new frame is a draw job's
	even
field_rate:
	dc.w	0		; 50 or 60
world_clock:
	dc.w	0		; 30 per vsync, the field rate per step

	even


;============================================================================

	END
