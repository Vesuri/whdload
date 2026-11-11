;*---------------------------------------------------------------------------
; Buggy Boy Enhanced: the path for a 68020 or better, DOS version only.
; Included by BuggyBoyHD.s. A 68000 or 68010, and the disk versions, keep 1.3.
;
; - The CPU caches are enabled (resload_SetCPU).
; - With the ExpMem in fast memory the program, its public allocations
;   (COURSES.DAT) and the stack are there; the DMA buffers stay in chip.
; - With any ExpMem the race runs on a fixed tick: the logic once every
;   TICK fields, and as many frames drawn as the machine manages. A tick
;   frame draws the committed state, as the original did after each logic
;   step; a frame between ticks saves the state, draws, and restores it, so
;   the game state sees exactly the original sequence of logic and drawing.
;
; Offsets P_* are program offsets (docs/internals.md).
;---------------------------------------------------------------------------*

; The ExpMem: from _ExpBase (with fast ExpMem the program's address, the
; first 64 KB boundary at least $20 bytes in, so that the program does not
; cross one, as at $400 in chip; else the ExpMem's start) the heap and the
; work area, and the stack at the ExpMem's top.
EXP_HEAP	= $c000				;public allocations, after the program
EXP_WORK	= $1c000			;the slave's buffers
EXP_STACK	= $2000				;the stack

W_SAVE		= 0				;the state saved around a frame between ticks
W_PREV		= $600				;the state of the tick before the last
W_SCREEN	= $1000				;fast memory: the road's screen (as a chip one)
W_ROADGFX	= $9000				;fast memory: copy of alloc 4 (the road's source)
W_BLT		= $17000			;the clear's blitter registers, recorded (_QClear)
W_QUEUE		= $17080			;the recorded blits, Q_ENTRY bytes each
	IFD VERIFY
W_VERIFY	= $17800			;copy of the program
W_LOG		= $22800			;the log (tools/verify.py)
W_VCOURSES	= $22c00			;copy of COURSES.DAT
W_VCLEAR	= $32800			;the queued clear's rows 0 to 103, against 1.3's
W_SIZE		= $37000
	ELSE
W_SIZE		= $18000
	ENDC
EXPSIZE		= $10000+EXP_WORK+W_SIZE+EXP_STACK	;ws_ExpMem (optional)
	IFNE EXPSIZE&$fff
		FAIL	"ws_ExpMem must be a multiple of $1000 (WHDLoad: slave is illegal)"
	ENDC

TICK		= 5				;fields per logic tick (10 Hz)
LAT_MAX		= 16				;a larger lateral change per tick is a jump

P_SETUP		= $138				;race setup: lea $dff000,a0 (every way in)
P_LOOP		= $158				;the race loop
P_LOGIC		= $153e
P_ROAD		= $6716
P_SWAP		= $2672
P_CLEAR		= $1e2				;sky (rows 0-83), horizon step, backdrop (84-103)
P_BACKDROP	= $27e				;the clear after the sky: a6 = the back buffer
P_HSTEP		= $98d2				;written by the clear's horizon step
P_FIELDS	= $66d8				;the level-3 handler's field counter
P_RACEEND	= $9874				;tested after the swap (bmi: the race ends)
P_SIZE		= $a9b0				;the code hunk
P_COURSES	= $9822				;pointer to COURSES.DAT (alloc 3)
P_COURSE	= $9826				;the course's data in it
REGIONS_SIZE	= ($9d6c-$9860)+$10+$20		;_StateRegions
P_PROJECT	= $2352				;the road projection (part of the logic)
P_SCREENSEL	= $9818				;word: 0 or 4, then the two screens' pointers
P_ROADGFX	= $982a				;pointer to alloc 4
ROADGFX_SIZE	= 57088
SCREEN_SIZE	= 32000				;4 planes of 8000 bytes
ROAD_TOP	= 104*40			;the road: rows 104 to 199 of every plane
ROAD_BYTES	= 96*40
SKY_SIZE	= 84<<6|20			;BLTSIZE of a plane's sky
CLEAR_BYTES	= 104*40			;what the clear writes of a plane
Q_ENTRY		= 36				;_Snap's layout
Q_MAX		= 40				;the clear records at most 20
	IFGT W_QUEUE+Q_MAX*Q_ENTRY-$17800
		FAIL	"the blit queue runs into the VERIFY area"
	ENDC
P_BLOCK		= $9860				;the logic's state block; V_* are offsets in it
V_PARITY	= $987a-P_BLOCK			;segment parity, 0 or 8
V_PHASE		= $987c-P_BLOCK			;phase in the segment, 0 2 4 6 (of 8)
V_PHASE221	= $987e-P_BLOCK			;phase * 221 (the object tables)
V_ROADPH	= $9880-P_BLOCK			;(parity + phase) * 96 (the road)
V_LAT		= $9890-P_BLOCK			;lateral position
V_HSPEED	= $98da-P_BLOCK			;horizon step = V_HSPEED * V_CURVE0
V_CURVE0	= $98dc-P_BLOCK			;the nearest curve value ($2352)
V_HORIZON	= $98de-P_BLOCK			;horizon scroll, 0 to 639 (the clear adds the step)
COURSES_SIZE	= 63072
ALLOC1_SIZE	= 67102				;the screens and the copper list

	IFD VERIFY
	IFGT W_VCOURSES+COURSES_SIZE-W_SIZE
	FAIL	the work area is too small
	ENDC
	ENDC

CPU_68020	= 1				;AttnFlags bits (exec/execbase.i)
CPU_68040	= 3
CPU_68060	= 7
MEM_CHIP	= 1				;MEMB_CHIP (exec/memory.i)
I_BLIT		= 6				;INTB_BLIT (hardware/intbits.i)
I_LEVEL3	= $30				;INTF_VERTB|INTF_COPER, the handler's own
P_L3END		= $4dea				;the level-3 handler's movem and rte

; tst.b label(pc), which the 68000 lacks; a0 and the other registers kept
TSTPC		MACRO
		move.l	a0,-(sp)
		lea	\1(pc),a0
		tst.b	(a0)
		move.l	(sp)+,a0		;movea: flags kept
		ENDM

;======================================================================
; After resload_Control: decide the path.
;======================================================================

_EnhInit	movem.l	d0/a0,-(sp)
		lea	_Enh(pc),a0
		clr.w	(a0)			;_Enh, _FastExp
		move.l	_AttnFlags(pc),d0
		btst	#CPU_68020,d0
		beq.b	.done
		st	(a0)			;_Enh: a 68020 or better
		move.l	_expmem(pc),d0
		beq.b	.done
		move.l	d0,_ExpBase-_Enh(a0)
		cmp.l	#$200000,d0		;chip memory
		blo.b	.done
		cmp.l	#$c00000,d0		;slow memory on the chip bus
		blo.b	.fast
		cmp.l	#$e00000,d0
		blo.b	.done
.fast		st	1(a0)			;_FastExp
		add.l	#$20+$ffff,d0
		clr.w	d0
		move.l	d0,_ExpBase-_Enh(a0)
		add.l	#EXP_HEAP,d0
		move.l	d0,_ExpFree-_Enh(a0)
.done		movem.l	(sp)+,d0/a0
		rts

;======================================================================
; Destination of bug.p (32-byte hunk header, the program after it).
;======================================================================

_EnhDest	lea	DOSGAMEADDRESS-$20,a1
		TSTPC	_FastExp
		beq.b	.chip
		move.l	_ExpBase(pc),a1
		sub.w	#$20,a1
.chip		rts

;======================================================================
; The game's AllocMem: public requests go to the ExpMem when it is fast.
; d0 = size, d1 = requirements; returns d0 = a0 = cleared memory.
;======================================================================

_AllocMem	btst	#MEM_CHIP,d1
		bne.b	.chip
		TSTPC	_FastExp
		beq	_AllocChip
		movem.l	d1-d2/a1,-(sp)
		lea	_ExpFree(pc),a1
		move.l	(a1),d1
		move.l	d1,d2
		add.l	#$10,d0
		and.l	#$fffffff0,d0
		add.l	d0,d1
		move.l	_ExpBase(pc),a0
		add.l	#EXP_WORK,a0
		cmp.l	a0,d1
		bhi.b	.full
		move.l	d1,(a1)
		asr.l	#4,d0
		move.l	d2,a0
.clear		clr.l	(a0)+
		clr.l	(a0)+
		clr.l	(a0)+
		clr.l	(a0)+
		dbf	d0,.clear
		move.l	d2,a0
		move.l	d2,d0
		movem.l	(sp)+,d1-d2/a1
		rts
.full		sub.l	#$10,d0			;undo the rounding's safety
		movem.l	(sp)+,d1-d2/a1
		bra	_AllocChip

; Alloc 1 holds the two screens at + $C1E and + $891E, 2 bytes off a
; longword: 2 bytes later the game's longword accesses to them are aligned,
; one chip access each instead of two. Its DMA needs only word alignment.
.chip		TSTPC	_Enh
		beq	_AllocChip
		cmp.l	#ALLOC1_SIZE,d0
		bne	_AllocChip
		addq.l	#4,d0
		bsr	_AllocChip
		addq.l	#2,d0
		addq.l	#2,a0
		rts

;======================================================================
; Start the DOS version: a5 = program.
;======================================================================

_EnhGo		lea	_ProgBase(pc),a0
		move.l	a5,(a0)
		TSTPC	_Enh
		beq.b	.go
		bsr	_EnhCache
		bsr	_TickPatch
		TSTPC	_FastExp
		beq.b	.go
		move.l	_expmem(pc),a0
		add.l	#EXPSIZE,a0
		move.l	a0,sp
.go		move.w	#$83d0,$dff096		;Enable DMA
		jsr	(a5)
		bra	_exit

; Instruction and data caches; on the 68060 also the branch cache and
; superscalar dispatch. BaseMem (chip) is write-through: without the MMU a
; non-cacheable region turns every cache off. On a 68040 or 68060 (WHDLoad
; uses the MMU) with the program in fast memory BaseMem is non-cacheable:
; those CPUs slow down on cacheable chip accesses.
_EnhCache	movem.l	d0-d1/a0-a2,-(sp)
		move.l	#WCPUF_Base_WT|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC,d0
		move.l	_AttnFlags(pc),d1
		btst	#CPU_68040,d1
		beq.b	.mode
		TSTPC	_FastExp
		beq.b	.mode
		move.l	#WCPUF_Base_NC|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC,d0
.mode		btst	#CPU_68060,d1
		beq.b	.set
		or.l	#WCPUF_BC|WCPUF_SS,d0
.set		move.l	#WCPUF_Base|WCPUF_Exp|WCPUF_Slave|WCPUF_IC|WCPUF_DC|WCPUF_BC|WCPUF_SS,d1
		move.l	_resload(pc),a2
		jsr	resload_SetCPU(a2)
		movem.l	(sp)+,d0-d1/a0-a2
		rts

;======================================================================
; The fixed tick. Needs an ExpMem (any kind) for its buffers.
;======================================================================

_TickPatch	movem.l	d0-d1/a0-a2,-(sp)
		move.l	_ExpBase(pc),d0
		beq	.no
		add.l	#EXP_WORK,d0
		lea	_Work(pc),a0
		move.l	d0,(a0)
		lea	_AddrLogic(pc),a0
		move.l	a5,d0
		add.l	#P_LOGIC,d0
		move.l	d0,(a0)+		;_AddrLogic
		move.l	a5,d0
		add.l	#P_ROAD,d0
		move.l	d0,(a0)+		;_AddrRoad
		move.l	a5,d0
		add.l	#P_SWAP,d0
		move.l	d0,(a0)+		;_AddrSwap
		move.l	a5,d0
		add.l	#P_LOOP,d0
		move.l	d0,(a0)+		;_AddrLoop
	IFD VERIFY
		move.l	_Work(pc),a0
		add.l	#W_LOG,a0
		move.l	a0,$3c0			;for the tools
		move.w	#$350/4-1,d0
.clr		clr.l	(a0)+
		dbf	d0,.clr
	ENDC
		lea	_PL_Tick(pc),a0
		move.l	a5,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
		TSTPC	_FastExp
		beq.b	.no
		move.l	_Work(pc),d0
		add.l	#W_SCREEN,d0
		lea	_FakeSel+2(pc),a0
		move.l	d0,(a0)
		lea	_PL_Road(pc),a0
		move.l	a5,a1
		jsr	resload_Patch(a2)
		lea	_PL_Queue(pc),a0
		move.l	a5,a1
		jsr	resload_Patch(a2)
.no		movem.l	(sp)+,d0-d1/a0-a2
		rts

_PL_Tick	PL_START
		PL_PS	P_SETUP,_RaceInit	;lea $dff000,a0
		PL_PSS	P_LOOP,_PreDraw,6	;bsr logic; bsr road; bsr clear
		PL_PSS	P_LOOP+$14,_PostDraw,4	;bsr swap; tst.w $9874
		PL_PSS	$2682,_SetCop,2		;move.l (a1,d0.w),$dff080
		PL_END

; With fast ExpMem the race loop's road draws into a screen in fast memory
; from a fast copy of its source, and _CopyRoad moves its rows to chip. The
; road writes every word of rows 104 to 199 in every plane, reading only what
; it wrote, so the result is the same. Its other callers draw as before.
_PL_Road	PL_START
		PL_PS	$9d6a,_RoadScreen	;lea $9818,a0
		PL_PS	$9d78,_RoadSource	;movea.l $982a,a3
		PL_END

_RoadScreen	TSTPC	_RoadFast
		bne.b	.fast
		move.l	_ProgBase(pc),a0
		add.l	#P_SCREENSEL,a0
		rts
.fast		lea	_FakeSel(pc),a0		;the road's adda.w (a0)+,a0; movea.l (a0),a2
		rts

_RoadSource	move.l	_ProgBase(pc),a3
		add.l	#P_ROADGFX,a3
		move.l	(a3),a3
		TSTPC	_RoadFast
		beq.b	.chip
		move.l	_Work(pc),a3
		add.l	#W_ROADGFX,a3
.chip		rts

; The road's rows from the fast screen to the back buffer.
_CopyRoad	movem.l	d0-d1/a0-a1,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_SCREENSEL,a0
		adda.w	(a0)+,a0
		move.l	(a0),a1
		add.l	#ROAD_TOP,a1
		move.l	_Work(pc),a0
		add.l	#W_SCREEN+ROAD_TOP,a0
		moveq	#4-1,d1
		move.l	a1,d0
		btst	#1,d0
		bne.b	.odd
.plane		move.w	#ROAD_BYTES/32-1,d0
.copy		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		dbf	d0,.copy
		add.l	#8000-ROAD_BYTES,a0
		add.l	#8000-ROAD_BYTES,a1
		dbf	d1,.plane
		bra.b	.done
; The screens are 2 bytes off a longword (alloc 1 + $C1E and + $891E): a
; word first, so the longword writes are aligned, one chip access each.
.odd		move.w	(a0)+,(a1)+
		move.w	#ROAD_BYTES/32-1,d0
		bra.b	.oddin
.oddcopy	move.l	(a0)+,(a1)+
.oddin		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		dbf	d0,.oddcopy
		move.w	(a0)+,(a1)+
		add.l	#8000-ROAD_BYTES,a0
		add.l	#8000-ROAD_BYTES,a1
		dbf	d1,.odd
.done
		movem.l	(sp)+,d0-d1/a0-a1
		rts

	IFD VERIFY
; The road drawn in fast memory against the original's in the back buffer:
; log + $340 counts the frames, + $344 the longwords that differ.
_CompareRoad	movem.l	d0-d1/a0-a2,-(sp)
		move.l	_Work(pc),a2
		add.l	#W_LOG+$340,a2
		addq.l	#1,(a2)
		move.l	_ProgBase(pc),a0
		add.l	#P_SCREENSEL,a0
		adda.w	(a0)+,a0
		move.l	(a0),a1
		add.l	#ROAD_TOP,a1
		move.l	_Work(pc),a0
		add.l	#W_SCREEN+ROAD_TOP,a0
		moveq	#4-1,d1
.plane		move.w	#ROAD_BYTES/4-1,d0
.cmp		cmpm.l	(a0)+,(a1)+
		beq.b	.same
		addq.l	#1,4(a2)
.same		dbf	d0,.cmp
		add.l	#8000-ROAD_BYTES,a0
		add.l	#8000-ROAD_BYTES,a1
		dbf	d1,.plane
		movem.l	(sp)+,d0-d1/a0-a2
		rts
	ENDC

; The race loop's clear, with fast ExpMem: its blits are recorded and the
; blitter interrupt runs them while the CPU draws the road in fast memory;
; _QSync waits for the last before the objects, the next to use the blitter.
; The sky (rows 0 to 83) is 4 blits, where 1.3 blits planes 0 and 2 and the
; CPU clears 1 and 3; the clear's own code from P_BACKDROP steps the horizon
; (read only by the logic) and records the backdrop's blits. All the later
; blit code sets every register it uses.
_PL_Queue	PL_START
		PL_PS	$2d4,_BltBase		;lea $dff000,a2
		PL_PSS	$318,_BWait,4		;btst #6,2(a2); bne.w *
		PL_PSS	$354,_BWait,4
		PL_PSS	$372,_BWait,4
		PL_PSS	$390,_BWait,4
		PL_PSS	$3c4,_BWait,4
		PL_PSS	$408,_BWait,4
		PL_PSS	$42c,_BWait,4
		PL_PSS	$450,_BWait,4
		PL_PSS	$490,_BWait,4
		PL_PSS	$4c0,_BWait,4
		PL_PSS	$4de,_BWait,4
		PL_PSS	$4fc,_BWait,4
		PL_PSS	$52a,_BWait,4
		PL_PSS	$56e,_BWait,4
		PL_PSS	$592,_BWait,4
		PL_PSS	$5b6,_BWait,4
		PL_PSS	$4db6,_Level3,2		;move.w $1e(a0),d0; and.w $1c(a0),d0
		PL_END

_QClear		movem.l	d0-d7/a0-a6,-(sp)
		move.l	_ProgBase(pc),a5
	IFD VERIFY
		lea	_VHorizon(pc),a0
		move.l	a5,a1
		add.l	#P_BLOCK+V_HORIZON,a1
		move.w	(a1),(a0)
	ENDC
		move.l	a5,a0
		add.l	#P_SCREENSEL,a0
		adda.w	(a0)+,a0
		move.l	(a0),a6			;the back buffer, as the clear's
		move.l	_Work(pc),a2
		move.l	a2,a1
		add.l	#W_QUEUE,a1
		lea	_QHead(pc),a0
		move.l	a1,(a0)+
		move.l	a1,(a0)			;_QTail
		add.l	#W_BLT,a2
		clr.w	$58(a2)
		move.w	#$01f0,$40(a2)		;D = A data
		clr.w	$42(a2)
		moveq	#-1,d0
		move.l	d0,$44(a2)
		clr.w	$66(a2)
		clr.w	$74(a2)			;planes 1 and 3: 0
		lea	8000(a6),a0
		bsr.b	.sky
		lea	24000(a6),a0
		bsr.b	.sky
		move.w	d0,$74(a2)		;planes 0 and 2: -1, as 1.3 leaves it
		move.l	a6,a0
		bsr.b	.sky
		lea	16000(a6),a0
		bsr.b	.sky
		lea	_QRec(pc),a0
		st	(a0)
		move.l	a5,a0
		add.l	#P_BACKDROP,a0
		jsr	(a0)
		move.l	_Work(pc),a2
		add.l	#W_BLT,a2
		bsr.b	_Snap			;the last
		lea	_QRec(pc),a0
		sf	(a0)
		bsr	_QStart
		movem.l	(sp)+,d0-d7/a0-a6
		rts
.sky		move.l	a0,$54(a2)
		move.w	#SKY_SIZE,$58(a2)
		bra.b	_Snap

; The clear's lea $dff000,a2 before the backdrop.
_BltBase	lea	$dff000,a2
		TSTPC	_QRec
		beq.b	.hw
		move.l	_Work(pc),a2
		add.l	#W_BLT,a2
.hw		rts

; The clear's waits for the blitter, before each blit but its first: on the
; recorded registers, the blit they set up so far.
_BWait		cmp.l	#$dff000,a2
		bne.b	_Snap
.wait		btst	#6,2(a2)
		bne.b	.wait
		rts

; a2 = the recorded registers; a blit set up (BLTSIZE written) is queued.
_Snap		tst.w	$58(a2)
		beq.b	.none
		movem.l	a0-a1,-(sp)
		lea	_QTail(pc),a0
		move.l	(a0),a1
		move.l	$40(a2),(a1)+		;BLTCON0, BLTCON1
		move.l	$44(a2),(a1)+		;BLTAFWM, BLTALWM
		move.l	$48(a2),(a1)+		;BLTCPT
		move.l	$4c(a2),(a1)+		;BLTBPT
		move.l	$50(a2),(a1)+		;BLTAPT
		move.l	$54(a2),(a1)+		;BLTDPT
		move.l	$60(a2),(a1)+		;BLTCMOD, BLTBMOD
		move.l	$64(a2),(a1)+		;BLTAMOD, BLTDMOD
		move.w	$74(a2),(a1)+		;BLTADAT
		move.w	$58(a2),(a1)+		;BLTSIZE
		move.l	a1,(a0)
		clr.w	$58(a2)
		movem.l	(sp)+,a0-a1
.none		rts

_QStart		movem.l	a0-a1,-(sp)
		lea	$dff000,a0
		tst.b	2(a0)
.idle		btst	#6,2(a0)
		bne.b	.idle
		move.w	#1<<I_BLIT,$9c(a0)	;an old blit's request
		move.w	#1<<I_BLIT,$9c(a0)
		lea	_QBusy(pc),a1
		st	(a1)
		move.w	#$8000|1<<I_BLIT,$9a(a0)
		bsr.b	_QNext
		movem.l	(sp)+,a0-a1
		rts

; a0 = $dff000: starts the next blit, or ends the queue. Uses a1.
_QNext		move.l	a2,-(sp)
		lea	_QHead(pc),a2
		move.l	(a2)+,a1
		cmp.l	(a2),a1			;_QTail
		beq.b	.done
		move.l	(a1)+,$40(a0)
		move.l	(a1)+,$44(a0)
		move.l	(a1)+,$48(a0)
		move.l	(a1)+,$4c(a0)
		move.l	(a1)+,$50(a0)
		move.l	(a1)+,$54(a0)
		move.l	(a1)+,$60(a0)
		move.l	(a1)+,$64(a0)
		move.w	(a1)+,$74(a0)
		addq.l	#2,a1
		move.l	a1,-(a2)		;_QHead: the next entry
		move.w	-2(a1),$58(a0)		;starts the blit
		move.l	(sp)+,a2
		rts
.done		move.w	#1<<I_BLIT,$9a(a0)
		lea	_QBusy(pc),a1
		sf	(a1)
		move.l	(sp)+,a2
		rts

; In the level-3 handler (d0-d1/a0-a2/a5 saved, a0 = $dff000): returns
; its d0, the requests to handle, without the blitter's, which is handled
; here; a blitter request alone leaves through the handler's end, without
; counting a field.
_Level3		move.w	$1e(a0),d0
		and.w	$1c(a0),d0
		btst	#I_BLIT,d0
		beq.b	.rts
		move.w	#1<<I_BLIT,$9c(a0)
		move.w	#1<<I_BLIT,$9c(a0)
		bsr.b	_QNext
		and.w	#I_LEVEL3,d0
		bne.b	.rts
		addq.l	#4,sp
		move.l	_ProgBase(pc),-(sp)
		add.l	#P_L3END,(sp)
.rts		rts

_QSync		TSTPC	_QBusy
		bne.b	_QSync
		rts

	IFD VERIFY
; The queued clear's rows 0 to 103 against 1.3's clear drawn after it, from
; the same horizon: log + $348 counts the frames (its high word those whose
; horizon differs), + $34C the longwords that differ.
_CompareClear	movem.l	d0-d7/a0-a6,-(sp)
		move.l	_ProgBase(pc),a5
		move.l	a5,a0
		add.l	#P_SCREENSEL,a0
		adda.w	(a0)+,a0
		move.l	(a0),a3			;the back buffer
		move.l	_Work(pc),a4
		move.l	a4,a1
		add.l	#W_VCLEAR,a1
		move.l	a3,a0
		moveq	#4-1,d1
.save		move.w	#CLEAR_BYTES/4-1,d0
.savel		move.l	(a0)+,(a1)+
		dbf	d0,.savel
		add.l	#8000-CLEAR_BYTES,a0
		dbf	d1,.save
		move.l	a5,a2
		add.l	#P_BLOCK+V_HORIZON,a2
		move.w	(a2),d7
		move.w	_VHorizon(pc),(a2)
		move.l	a5,a0
		add.l	#P_CLEAR,a0
		movem.l	d7/a2-a3,-(sp)
		jsr	(a0)
		movem.l	(sp)+,d7/a2-a3
		move.l	_Work(pc),a4
		add.l	#W_LOG+$348,a4
		addq.l	#1,(a4)
		cmp.w	(a2),d7
		beq.b	.hsame
		add.l	#$10000,(a4)		;the horizon differs
.hsame		addq.l	#4,a4
		move.l	_Work(pc),a1
		add.l	#W_VCLEAR,a1
		move.l	a3,a0
		moveq	#4-1,d1
.plane		move.w	#CLEAR_BYTES/4-1,d0
.cmp		cmpm.l	(a0)+,(a1)+
		beq.b	.same
		addq.l	#1,(a4)
.same		dbf	d0,.cmp
		add.l	#8000-CLEAR_BYTES,a0
		dbf	d1,.plane
		movem.l	(sp)+,d0-d7/a0-a6
		rts
	ENDC

; Before the race loop: the first pass runs the logic and draws its result.
_RaceInit	move.l	a0,-(sp)
		lea	_Pending(pc),a0
		st	(a0)
		move.l	_ProgBase(pc),a0
		move.w	P_FIELDS(a0),-(sp)
		lea	_NextTick(pc),a0
		move.w	(sp)+,(a0)
		TSTPC	_FastExp
		beq.b	.nogfx
		movem.l	d0/a1,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_ROADGFX,a0
		move.l	(a0),a0
		move.l	_Work(pc),a1
		add.l	#W_ROADGFX,a1
		move.w	#ROADGFX_SIZE/4-1,d0
.gfx		move.l	(a0)+,(a1)+
		dbf	d0,.gfx
		movem.l	(sp)+,d0/a1
.nogfx		move.l	(sp)+,a0
		lea	$dff000,a0		;stolen
		rts

; Replaces the loop's calls of the logic, the road and the clear.
_PreDraw	movem.l	d0-d7/a0-a6,-(sp)
		TSTPC	_Pending
		beq.b	.due
		lea	_Pending(pc),a0
		sf	(a0)
		move.l	_Work(pc),a1
		lea	W_PREV(a1),a1
		bsr	_ToBuf			;the state shown at the last tick
		move.l	_AddrLogic(pc),a0
		jsr	(a0)
.due		move.l	_ProgBase(pc),a5
		lea	_NextTick(pc),a4
		move.w	P_FIELDS(a5),d0
		move.w	d0,d1
		sub.w	(a4),d0			;fields since the tick was due
		bmi.b	.between
		addq.w	#TICK,(a4)		;a tick frame: draw the committed state
		cmp.w	#TICK,d0
		blt.b	.ontime
		add.w	#TICK,d1		;a tick or more late: start again
		move.w	d1,(a4)
.ontime		lea	_Pending(pc),a0
		st	(a0)			;the next logic step after this frame
		bra.b	.road
.between	lea	_Staged(pc),a0
		st	(a0)
		bsr	_SaveState
		bsr	_Pose
.road		movem.l	(sp)+,d0-d7/a0-a6
		TSTPC	_FastExp
		bne.b	.fast
		move.l	_AddrRoad(pc),a0
		jsr	(a0)
		move.l	_ProgBase(pc),-(sp)
		add.l	#P_CLEAR,(sp)
		rts
.fast		bsr	_QClear			;its blits run while the road draws
		lea	_RoadFast(pc),a0	;the road sets a0 first
		st	(a0)
		move.l	_AddrRoad(pc),a0
		jsr	(a0)
		lea	_RoadFast(pc),a0
		sf	(a0)
	IFD VERIFY
		move.l	_AddrRoad(pc),a0	;and in chip, as the original
		jsr	(a0)
		bsr	_CompareRoad
		bsr	_QSync
		bra	_CompareClear
	ELSE
		bsr	_CopyRoad
		bra	_QSync
	ENDC

; The pose of a frame between ticks, in the live state (S_next, the last
; tick's result; W_PREV holds S_prev, the tick before, in the same layout).
; d0.w = fields now - the next tick's due field (-TICK to -1), so n = TICK + d0
; fields have passed since the frame that showed S_next was due.
; - Forward: the position goes from S_prev's to S_next's, n/TICK of the way.
;   A tick moves it at most one segment (a crossing clears the phase); the
;   phase is rounded to the renderers' 4 steps. Before the crossing the pose
;   is S_prev's state, after it S_next's, with the phase replaced.
; - Lateral: interpolated, unless it jumped (more than LAT_MAX).
; - The projection ($2352) is run again for the pose.
; - Horizon: set so that the clear's step lands n/TICK of the way.
; Anything else (objects in their slices, the HUD, the player's sprite) is
; the chosen tick's.
_Pose		move.w	d0,d7
		add.w	#TICK,d7		;n
		bpl.b	.n
		moveq	#0,d7
.n		move.l	_ProgBase(pc),a5
		move.l	a5,a4
		add.l	#P_BLOCK,a4		;S_next (live)
		move.l	_Work(pc),a3
		lea	W_PREV(a3),a3		;S_prev
		move.w	V_PHASE(a3),d1		;ph0
		move.w	V_PHASE(a4),d2		;ph1
		move.w	V_PARITY(a4),d3
		cmp.w	V_PARITY(a3),d3
		beq.b	.same
		moveq	#8,d3			;crossed: 8 - ph0 + ph1
		sub.w	d1,d3
		add.w	d2,d3
		bra.b	.have
.same		move.w	d2,d3
		sub.w	d1,d3
		bmi	.hold			;backwards: a new race or a reset
.have		cmp.w	#8,d3
		bhi	.hold
		mulu	d7,d3			;d * n
		move.w	d1,d4
		mulu	#TICK,d4
		add.w	d3,d4			;the position * TICK
		add.w	#TICK,d4
		divu	#2*TICK,d4
		add.w	d4,d4			;q: rounded to an even phase, 0 to 8
		moveq	#0,d5			;no lateral
		move.w	V_LAT(a3),d0		;lat0
		move.w	V_LAT(a4),d6
		sub.w	d0,d6			;lat1 - lat0
		move.w	d6,d1
		bpl.b	.abs
		neg.w	d1
.abs		cmp.w	#LAT_MAX,d1
		bhi.b	.block
		muls	d7,d6
		divs	#TICK,d6
		add.w	d0,d6			;lat
		moveq	#-1,d5
.block		cmp.w	#8,d4
		blo.b	.prev
		subq.w	#8,d4			;past the crossing: S_next's segment
		bra.b	.set
.prev		move.l	a3,a1
		bsr	_FromBuf		;S_prev's segment
.set		move.w	d4,V_PHASE(a4)
		move.w	d4,d0
		mulu	#221,d0
		move.w	d0,V_PHASE221(a4)
		moveq	#8,d0
		and.w	V_PARITY(a4),d0
		add.w	d4,d0
		mulu	#96,d0
		move.w	d0,V_ROADPH(a4)
		tst.w	d5
		beq.b	.project
		move.w	d6,V_LAT(a4)
.project	movem.l	d7/a4,-(sp)
		move.l	a5,a0
		add.l	#P_PROJECT,a0
		jsr	(a0)
		movem.l	(sp)+,d7/a4
		move.w	V_CURVE0(a4),d0		;the clear's step
		muls	V_HSPEED(a4),d0
		move.w	d7,d1
		sub.w	#TICK,d1
		muls	d1,d0
		divs	#TICK,d0		;step * (n - TICK) / TICK
		add.w	V_HORIZON(a4),d0
.lo		bpl.b	.hi
		add.w	#640,d0
		bra.b	.lo
.hi		cmp.w	#640,d0
		blt.b	.hok
		sub.w	#640,d0
		bra.b	.hi
.hok		move.w	d0,V_HORIZON(a4)
.hold		rts

; Replaces the loop's swap and the test after it. A frame between ticks
; restores the state and goes straight back to the loop: the checks after
; the swap (race end, right button, left button delay) see only tick frames.
_PostDraw	movem.l	d0-d1/a0-a1,-(sp)
		TSTPC	_Staged
		beq.b	.swap
		bsr	_RestoreState
.swap		movem.l	(sp)+,d0-d1/a0-a1
		lea	_InLoop(pc),a0
		st	(a0)
		move.l	_AddrSwap(pc),a0
		jsr	(a0)			;sets a0 and d0 itself
		move.l	a1,-(sp)
		lea	_InLoop(pc),a1
		sf	(a1)
		lea	_Staged(pc),a1
		tst.b	(a1)
		bne.b	.between
		move.l	_ProgBase(pc),a1
		add.l	#P_RACEEND,a1
		tst.w	(a1)
		move.l	(sp)+,a1		;movea: flags kept
		rts
.between	sf	(a1)
		move.l	(sp)+,a1
		addq.l	#4,sp
		move.l	_AddrLoop(pc),-(sp)
		rts

; The swap's COP1LC write: no wait in the race loop (the swap's own wait
; for the next field follows), 1.3's frame lock everywhere else.
_SetCop		TSTPC	_InLoop
		beq	_LockFrameRate
		move.l	(a1,d0.w),$dff080
		rts

; The state a frame writes: the logic's block and the drawing's own words
; (docs/internals.md, "The fixed tick"). Longwords: offset, count.
_StateRegions	dc.l	$9860,($9d6c-$9860)/4
		dc.l	$8b40,$10/4
		dc.l	$8e70,$20/4
		dc.l	0

_SaveState	movem.l	d0/a0-a3,-(sp)
		move.l	_Work(pc),a1
		bsr.b	_ToBuf
		bsr	_CourseWords
		move.w	(a0),(a1)+
		move.w	$4e0(a0),(a1)
	IFD VERIFY
		move.l	_ProgBase(pc),a3
		move.l	a3,a0
		move.l	_Work(pc),a1
		add.l	#W_VERIFY,a1
		move.w	#P_SIZE/4-1,d0
.vcopy		move.l	(a0)+,(a1)+
		dbf	d0,.vcopy
		move.l	a3,a0
		add.l	#P_COURSES,a0
		move.l	(a0),a0
		move.l	_Work(pc),a1
		add.l	#W_VCOURSES,a1
		move.w	#COURSES_SIZE/4-1,d0
.vcopy2		move.l	(a0)+,(a1)+
		dbf	d0,.vcopy2
	ENDC
		movem.l	(sp)+,d0/a0-a3
		rts

_RestoreState	movem.l	d0/a0-a3,-(sp)
		move.l	_Work(pc),a1
		bsr.b	_FromBuf
		bsr	_CourseWords
		move.w	(a1)+,(a0)
		move.w	(a1),$4e0(a0)
	IFD VERIFY
		move.l	_ProgBase(pc),a3
		bsr	_Verify
	ENDC
		movem.l	(sp)+,d0/a0-a3
		rts

; The state regions to (_ToBuf) or from (_FromBuf) the buffer at a1.
_ToBuf		movem.l	d0/a0-a3,-(sp)
		bsr.b	_Regions
.next		move.l	(a2)+,a0
		add.l	a3,a0
		move.l	(a2)+,d0
		subq.w	#1,d0
.copy		move.l	(a0)+,(a1)+
		dbf	d0,.copy
		tst.l	(a2)
		bne.b	.next
		movem.l	(sp)+,d0/a0-a3
		rts

_FromBuf	movem.l	d0/a0-a3,-(sp)
		bsr.b	_Regions
.next		move.l	(a2)+,a0
		add.l	a3,a0
		move.l	(a2)+,d0
		subq.w	#1,d0
.copy		move.l	(a1)+,(a0)+
		dbf	d0,.copy
		tst.l	(a2)
		bne.b	.next
		movem.l	(sp)+,d0/a0-a3
		rts

; The two COURSES.DAT words the object routine animates each frame ($3418):
; a0 = the first ($9826 + $D70; the second is $4E0 after it), a1 = their
; place in W_SAVE, after the regions.
_CourseWords	move.l	_ProgBase(pc),a0
		add.l	#P_COURSE,a0
		move.l	(a0),a0
		lea	$d70(a0),a0
		move.l	_Work(pc),a1
		lea	W_SAVE+REGIONS_SIZE(a1),a1
		rts

_Regions	lea	_StateRegions(pc),a2
		move.l	_ProgBase(pc),a3
		rts

	IFD VERIFY
; Compare the program and COURSES.DAT with their copies from before the
; frame, but for what the level-3 handler writes (the field counter, the
; sound channels). The log: frames checked, differing longwords seen, then up
; to 200 entries of (offset.w, count.w), one per longword offset; COURSES.DAT
; offsets with $8000 added (it is 63072 bytes, and offsets are longword/2).
_Verify		movem.l	d0-d3/a0-a4,-(sp)
		move.l	_Work(pc),a4
		add.l	#W_LOG,a4
		addq.l	#1,(a4)
		move.l	a3,a0
		move.l	_Work(pc),a1
		add.l	#W_VERIFY,a1
		moveq	#0,d1			;offset
.cmp		cmpm.l	(a0)+,(a1)+
		beq.b	.same
		cmp.w	#P_FIELDS&$fffc,d1
		beq.b	.same
		cmp.w	#$4edc&$fffc,d1
		blo.b	.diff
		cmp.w	#$4f14,d1
		blo.b	.same
.diff		addq.l	#1,4(a4)
		lea	8(a4),a2
		move.w	#200-1,d2
.find		tst.l	(a2)
		beq.b	.new
		cmp.w	(a2),d1
		beq.b	.count
		addq.l	#4,a2
		dbf	d2,.find
		bra.b	.same			;log full
.new		move.w	d1,(a2)
.count		addq.w	#1,2(a2)
.same		addq.w	#4,d1
		cmp.w	#P_SIZE,d1
		blo.b	.cmp
		move.l	a3,a0
		add.l	#P_COURSES,a0
		move.l	(a0),a0
		move.l	_Work(pc),a1
		add.l	#W_VCOURSES,a1
		move.w	#COURSES_SIZE/4-1,d3
		move.w	#$8000,d1
.cmp2		cmpm.l	(a0)+,(a1)+
		beq.b	.same2
		addq.l	#1,4(a4)
		lea	8(a4),a2
		move.w	#200-1,d2
.find2		tst.l	(a2)
		beq.b	.new2
		cmp.w	(a2),d1
		beq.b	.count2
		addq.l	#4,a2
		dbf	d2,.find2
		bra.b	.same2
.new2		move.w	d1,(a2)
.count2		addq.w	#1,2(a2)
.same2		addq.w	#2,d1
		dbf	d3,.cmp2
		movem.l	(sp)+,d0-d3/a0-a4
		rts
	ENDC

;======================================================================

_ProgBase	dc.l	0			;program offset 0
_ExpBase	dc.l	0			;see EXP_HEAP; 0: no ExpMem
_Work		dc.l	0			;_ExpBase + EXP_WORK
_AddrLogic	dc.l	0			;these four in this order
_AddrRoad	dc.l	0
_AddrSwap	dc.l	0
_AddrLoop	dc.l	0
_ExpFree	dc.l	0			;next public allocation
_QHead		dc.l	0			;the next blit to start
_QTail		dc.l	0			;the end of the recorded blits
_NextTick	dc.w	0			;P_FIELDS value the next tick is due at
	IFD VERIFY
_VHorizon	dc.w	0			;V_HORIZON before the queued clear
	ENDC
_Enh		dc.b	0			;-1: the enhanced path (word-aligned)
_FastExp	dc.b	0			;-1: the ExpMem is fast memory
_Pending	dc.b	0			;-1: run the logic before the next frame
_Staged		dc.b	0			;-1: this frame is between ticks
_InLoop		dc.b	0			;-1: the race loop's swap
_RoadFast	dc.b	0			;-1: the race loop's road, to fast memory
_QRec		dc.b	0			;-1: the clear records its blits
_QBusy		dc.b	0			;-1: the queue is running
		EVEN
_FakeSel	dc.w	0			;for _RoadScreen
		dc.l	0			;_Work + W_SCREEN
		EVEN
