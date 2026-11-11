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
;   The frames between ticks need the Enhanced framerate option (CUSTOM2);
;   without it each frame waits for its tick: 12.5 fps.
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
GFX_SIZE	= 240000			;alloc 2
GFX_BUGGY	= $d3a8				;the player's buggy in it: 4 planes, 8000 apart,
BUGGY_BYTES	= 40*40				;of 40 rows of 40 bytes; the logic animates plane 1

W_SAVE		= 0				;the state saved around a frame between ticks
W_PREV		= $600				;the state of the tick before the last
W_SCREEN	= $1000				;fast memory: the road's screen (as a chip one)
W_ROADGFX	= $9000				;fast memory: copy of alloc 4 (the road's source)
W_BLT		= $17000			;the clear's blitter registers, recorded (_QClear)
W_QUEUE		= $17080			;the recorded blits, Q_ENTRY bytes each
W_GFX		= $17800			;fast memory: copy of alloc 2 (the graphics)
W_END		= W_GFX+GFX_SIZE
FINE		= 64				;presentation positions per segment (_FineInit)
OBJ_SET		= 442				;one phase's object table ($76b0)
W_FOBJ		= W_END				;FINE object tables, $76b0's layout
W_FSTRIPE	= W_FOBJ+FINE*OBJ_SET		;FINE stripe tables ($685a's) per parity
W_FMAP		= W_FSTRIPE+2*FINE*192		;FINE row-to-slice maps: count.w, 98 bytes
W_FT		= W_FMAP+FINE*100		;slice boundaries: 5 phases, and one fine
W_FX		= W_FT+6*30			;the rows' x of the second projection
W_TSAVE		= W_FX+106*2			;a tick frame's position variables (_TickPose)
W_FEND		= W_TSAVE+$240
	IFD VERIFY
W_VERIFY	= (W_FEND+$fff)&-$1000		;copy of the program
W_LOG		= W_VERIFY+$b000		;the log (tools/verify.py)
W_VCOURSES	= W_LOG+$400			;copy of COURSES.DAT
W_VCLEAR	= W_VCOURSES+$10000		;the queued clear's rows 0 to 103, against 1.3's
W_SIZE		= (W_VCLEAR+$4800+$fff)&-$1000
	ELSE
W_SIZE		= (W_FEND+$fff)&-$1000
	ENDC
EXPSIZE		= $10000+EXP_WORK+W_SIZE+EXP_STACK	;ws_ExpMem (optional)
	IFNE EXPSIZE&$fff
		FAIL	"ws_ExpMem must be a multiple of $1000 (WHDLoad: slave is illegal)"
	ENDC

TICK		= 4				;fields per logic tick (12.5 Hz, 1.3's default lock)
LMAX		= 24				;the smoothed position's most lag (1/FINE segment)
CATCH		= 16				;its catch-up per field into a crossed segment
LAT_MAX		= 128				;a larger lateral change per tick is a jump (steering
						;moves it up to 60 a tick, $810c, plus the drift)

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
P_GFX		= $982e				;pointer to alloc 2 (the graphics)
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
P_STRIPES	= $685a				;the road's stripes: 96 words per parity + phase
P_OBJTAB	= $76b0				;object rows: OBJ_SET bytes per phase
P_SLICEH	= $7daa				;slice heights - 1: 16 bytes per phase
P_ROWS		= $9b22				;the projection's per-row longs (106)
P_ROWHI		= $9b4a				;the road's row 0 among them
P_SLICES	= $9980				;the slices' rows, 32 bytes each
P_CROP		= $7e4a				;tall objects: 4 longs per size, one per phase
P_STEPS		= $804c				;phase steps / 2: 8 words per speed band
V_SPEED		= $98b2-P_BLOCK			;speed; the band is speed & $70
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
		move.w	#$360/4-1,d0
.clr		clr.l	(a0)+
		dbf	d0,.clr
	ENDC
		lea	_PL_Tick(pc),a0
		move.l	a5,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)
		lea	_PL_Plot(pc),a0
		move.l	a5,a1
		jsr	resload_Patch(a2)
		lea	_PL_Fine(pc),a0
		move.l	a5,a1
		jsr	resload_Patch(a2)
		bsr	_FineInit
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

; At the frame's start (the back buffer is free once the swap's field wait
; is over): the sky's planes 0 and 2, as 1.3's blits, which depend on
; nothing the frame computes. Planes 1 and 3 are _CpuSky's, as 1.3's.
_QSky		movem.l	d0/a0-a2/a5-a6,-(sp)
		bsr.b	.screen
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
		move.w	d0,$74(a2)		;planes 0 and 2: -1
		move.l	a6,a0
		bsr.b	.sky
		lea	16000(a6),a0
		bsr.b	.sky
		bsr	_QStart
		movem.l	(sp)+,d0/a0-a2/a5-a6
		rts
.sky		move.l	a0,$54(a2)
		move.w	#SKY_SIZE,$58(a2)
		bra	_Snap
.screen		move.l	_ProgBase(pc),a5
		move.l	a5,a0
		add.l	#P_SCREENSEL,a0
		adda.w	(a0)+,a0
		move.l	(a0),a6			;the back buffer, as the clear's
		rts

; After the pose: the rest of the clear, its blits added to the queue.
_QClear		movem.l	d0-d7/a0-a6,-(sp)
		bsr.b	_QSky\.screen
	IFD VERIFY
		lea	_VHorizon(pc),a0
		move.l	a5,a1
		add.l	#P_BLOCK+V_HORIZON,a1
		move.w	(a1),(a0)
	ENDC
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
		lea	$dff000,a0
		move.w	#$4000,$9a(a0)		;the queue's end against the additions
		TSTPC	_QBusy
		bne.b	.running
		bsr	_QStart			;it had run dry: from the first added
.running	move.w	#$c000,$9a(a0)
		movem.l	(sp)+,d0-d7/a0-a6
		rts

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

; The sky's planes 1 and 3 (rows 0 to 83) cleared by the CPU, after the road's
; copy: measured on the a1200-030, the blitter filling them as well is slower
; (0.988 fields a frame against 0.967), and the CPU all four too (0.977).
_CpuSky		movem.l	d0-d1/a0-a1,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_SCREENSEL,a0
		adda.w	(a0)+,a0
		move.l	(a0),a1
		lea	8000(a1),a0
		bsr.b	.plane
		lea	24000(a1),a0
		bsr.b	.plane
		movem.l	(sp)+,d0-d1/a0-a1
		rts
.plane		move.w	#84*40/32-1,d0
		moveq	#0,d1
.clr		move.l	d1,(a0)+
		move.l	d1,(a0)+
		move.l	d1,(a0)+
		move.l	d1,(a0)+
		move.l	d1,(a0)+
		move.l	d1,(a0)+
		move.l	d1,(a0)+
		move.l	d1,(a0)+
		dbf	d0,.clr
		rts

_QSync		TSTPC	_QBusy
		bne.b	_QSync
		rts

	IFD VERIFY
; Alloc 2 against its fast copy, but for the buggy's plane 1, every 16th
; frame of the race loop: log + $350 counts the frames, + $354 the longwords
; that differ, + $358 and + $35C the lowest and highest offset.
_CompareGfx	movem.l	d0-d1/a0-a2,-(sp)
		move.l	_Work(pc),a2
		add.l	#W_LOG+$350,a2
		TSTPC	_FastExp
		beq.b	.none
		lea	_VGfxCount(pc),a0
		addq.w	#1,(a0)
		and.w	#15,(a0)
		bne.b	.none
		addq.l	#1,(a2)+
		move.l	_GfxLo(pc),a0
		move.l	_Work(pc),a1
		add.l	#W_GFX,a1
		move.l	#GFX_SIZE/4-1,d0
.cmp		cmpm.l	(a0)+,(a1)+
		beq.b	.same
		move.l	a0,d1
		sub.l	_GfxLo(pc),d1
		sub.l	#GFX_BUGGY+8000+4,d1
		cmp.l	#BUGGY_BYTES,d1
		blo.b	.same			;the animated plane
		addq.l	#1,(a2)
		move.l	a0,d1
		sub.l	_GfxLo(pc),d1
		subq.l	#4,d1
		tst.l	4(a2)
		beq.b	.min
		cmp.l	4(a2),d1
		bhs.b	.max
.min		move.l	d1,4(a2)		;+ $358: the lowest offset that differed
.max		cmp.l	8(a2),d1
		bls.b	.same
		move.l	d1,8(a2)		;+ $35C: the highest
.same		subq.l	#1,d0
		bpl.b	.cmp
.none		movem.l	(sp)+,d0-d1/a0-a2
		rts

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

; The CPU's masked plotters, each screen word or longword read and written
; once per plane instead of an and and an or in place (half the chip
; accesses); every register and flag they leave is the original's. With
; fast ExpMem and between _PreDraw and _PostDraw (_GfxDelta set), the column
; plotter reads its source from the fast copy of alloc 2 that _RaceInit
; makes, unless the source overlaps the player's buggy: the logic ($1434)
; animates that graphic in place, the only part of alloc 2 that changes in a
; race (the VERIFY build compares the rest).
_PL_Plot	PL_START
		PL_P	$3dc4,_PlotColumn	;the column loop to its rts
		PL_P	$41a4,_PlotBuggy	;the buggy's loops to their rts
		PL_PSS	$4a94,_PlotText,62	;the 8 rows of a HUD character
		PL_END

; a1 = source, d4.w = rows - 1, (a3) = the source's stride up per row (2 or
; 42), a0 = the screen (a2 = a0 + 2), d6 = shift, d3/d5 = the colours.
_PlotColumn	movem.l	a4-a5,-(sp)
		move.w	d4,-(sp)
		sub.l	a5,a5
		move.l	_GfxDelta(pc),d0
		beq.b	.go
		move.l	a1,d1			;the rows the source spans
		cmp.l	_GfxLo(pc),d1
		blo.b	.go
		moveq	#0,d2
		move.w	(a3),d2
		subq.w	#2,d2
		moveq	#0,d7
		move.w	d4,d7
		addq.l	#1,d7
		mulu.w	d7,d2
		sub.l	d2,d1
		cmp.l	_GfxLo(pc),d1
		blo.b	.go
		move.l	a1,d2
		add.l	#24002,d2
		cmp.l	_GfxHi(pc),d2
		bhi.b	.go
		sub.l	#24000,d2		;[d1, d2): the span of plane 0
		move.l	_GfxLo(pc),d7
		add.l	#GFX_BUGGY+3*8000+BUGGY_BYTES,d7
		moveq	#7-1,d4			;the buggy's planes, from 3 below to 3 above
.buggy		cmp.l	d7,d1
		bhs.b	.clear
		move.l	d7,a4
		suba.w	#BUGGY_BYTES,a4
		cmp.l	a4,d2
		bls.b	.clear
		move.w	(sp),d4			;overlaps: from chip
		bra.b	.go
.clear		sub.l	#8000,d7
		dbf	d4,.buggy
		move.w	(sp),d4
		move.l	d0,a5
		add.l	a5,a1
.go		addq.l	#2,sp
.row		move.w	d4,-(sp)
		moveq	#-1,d0
		moveq	#0,d1
		moveq	#0,d2
		moveq	#0,d7
		moveq	#0,d4
		move.w	(a1)+,d1
		move.w	7998(a1),d2
		move.w	15998(a1),d7
		move.w	23998(a1),d4
		move.w	d4,d0
		not.w	d0
		or.w	d1,d0
		or.w	d2,d0
		or.w	d7,d0
		not.w	d0
		rol.l	d6,d0			;the mask: 1 keeps the screen
		lsl.l	d6,d1
		lsl.l	d6,d2
		lsl.l	d6,d7
		lsl.l	d6,d4
		not.l	d0
		and.l	d0,d4
		swap	d3
		swap	d1
		and.w	d3,d1
		swap	d1
		and.w	d3,d1
		swap	d3
		swap	d2
		and.w	d3,d2
		swap	d2
		and.w	d3,d2
		swap	d5
		swap	d7
		and.w	d5,d7
		swap	d7
		and.w	d5,d7
		swap	d5
		swap	d4
		and.w	d5,d4
		swap	d4
		and.w	d5,d4
		not.l	d0
		move.l	d6,a4
		move.l	(a0),d6
		and.l	d0,d6
		or.l	d1,d6
		move.l	d6,(a0)
		move.l	8000(a0),d6
		and.l	d0,d6
		or.l	d2,d6
		move.l	d6,8000(a0)
		move.l	16000(a0),d6
		and.l	d0,d6
		or.l	d7,d6
		move.l	d6,16000(a0)
		move.l	24000(a0),d6
		and.l	d0,d6
		or.l	d4,d6
		move.l	d6,24000(a0)
		move.l	a4,d6
		not.l	d0
		addq.l	#2,a0
		addq.l	#2,a2
		move.w	(sp)+,d4
		suba.w	#42,a0
		suba.w	#42,a2
		suba.w	(a3),a1
		dbf	d4,.row
		suba.l	a5,a1
		movem.l	(sp)+,a4-a5		;flags: the move.w (sp)+,d4's
		rts

; a0 = the screen, a1 = alloc 2 + $D3A8: 40 rows of 4 longwords; source
; plane 0 is the mask, 1 goes to screen plane 0, 2 to 1 and 2, 3 to 3.
_PlotBuggy	movem.l	d0/d5-d6,-(sp)
		moveq	#24,d2
		moveq	#39,d4
.row		moveq	#3,d3
.long		move.l	(a1)+,d1		;the mask
		move.l	24000(a0),d0
		and.l	d1,d0
		or.l	23996(a1),d0
		move.l	d0,24000(a0)
		move.l	15996(a1),d6
		move.l	16000(a0),d0
		and.l	d1,d0
		or.l	d6,d0
		move.l	d0,16000(a0)
		move.l	8000(a0),d0
		and.l	d1,d0
		or.l	d6,d0
		move.l	d0,8000(a0)
		move.l	7996(a1),d5
		move.l	(a0),d0
		and.l	d1,d0
		move.l	d5,d1
		or.l	d5,d0
		move.l	d0,(a0)+		;flags as the original's last or.l
		dbf	d3,.long
		adda.w	d2,a0
		adda.w	d2,a1
		dbf	d4,.row
		movem.l	(sp)+,d0/d5-d6
		rts

; a1/a2 = the two glyphs' rows, a0 = the screen, d2/d3 = the colours.
_PlotText	move.l	d6,-(sp)
		moveq	#7,d4
.row		move.w	(a1)+,d7
		move.w	(a2)+,d0
		move.w	d0,d1
		move.b	d7,d1
		rol.w	#8,d1
		move.b	d1,d7
		move.b	d0,d1
		move.w	d1,d0
		swap	d0
		move.w	d1,d0
		move.l	d0,d1
		and.l	d2,d0
		and.l	d3,d1
		move.w	24000(a0),d6
		and.w	d7,d6
		or.w	d1,d6
		move.w	d6,24000(a0)
		swap	d1
		move.w	16000(a0),d6
		and.w	d7,d6
		or.w	d1,d6
		move.w	d6,16000(a0)
		move.w	8000(a0),d6
		and.w	d7,d6
		or.w	d0,d6
		move.w	d6,8000(a0)
		swap	d0
		move.w	(a0),d6
		and.w	d7,d6
		or.w	d0,d6
		move.w	d6,(a0)
		lea	40(a0),a0
		dbf	d4,.row
		movem.l	(sp)+,d6		;flags: the last write's, as the original's or.w
		rts

; The drawing's readers of the phase that take a fine position between
; ticks (_Pose; docs/internals.md, "Fine positions"). The others read the
; phase, which the pose sets to the even phase below the position.
_PL_Fine	PL_START
		PL_PS	$3536,_ObjRows		;adda.w $987e,a5
		PL_PSS	$35d4,_Grow,2		;mulu.w $987c,d7; lsr.w #4,d7
		PL_PS	$39f4,_Phase0		;move.w $987e,d7
		PL_PS	$3a22,_Phase0		;move.w $987e,d7
		PL_PS	$9d8a,_Stripes		;adda.w $9880,a6
		PL_PSS	$3d3c,_PoleLen,6	;move.w $987c,d7; lsr.w #1,d7; move.b 4(a2,d7.w),d4
		PL_P	$3d0c,_Crop		;the tall objects' place and crop (type 54)
		PL_END

; a5 = $76b0 + a row's offset: its table for the phase.
_ObjRows	TSTPC	_Fine
		beq.b	.orig
		suba.l	_ProgBase(pc),a5
		suba.l	#P_OBJTAB,a5
		adda.l	_FineObj(pc),a5
		rts
.orig		move.l	a0,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_BLOCK,a0
		adda.w	V_PHASE221(a0),a5
		move.l	(sp)+,a0
		rts

; d7 = a size step's height difference: the sprite's lift, difference *
; phase / 16 (fine: * position / 128, the same at the even phases). It
; keeps the sprite centred on its slice's true size, also through the
; size change at the crossing (the lift reaches half the step there).
_Grow		TSTPC	_Fine
		beq.b	.orig
		mulu	_FineF(pc),d7
		lsr.w	#7,d7
		rts
.orig		move.l	a0,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_BLOCK,a0
		mulu	V_PHASE(a0),d7
		lsr.w	#4,d7
		move.l	(sp)+,a0
		rts

; d7.w = the distance from the row's table to phase 0's.
_Phase0		TSTPC	_Fine
		beq.b	.orig
		move.w	_FineF(pc),d7
		mulu	#OBJ_SET,d7
		rts
.orig		move.l	a0,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_BLOCK,a0
		move.w	V_PHASE221(a0),d7
		move.l	(sp)+,a0
		rts

; a6 = $685a: the stripes for the parity and phase.
_Stripes	TSTPC	_Fine
		beq.b	.orig
		move.l	_FineStripe(pc),a6
		rts
.orig		move.l	a0,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_BLOCK,a0
		adda.w	V_ROADPH(a0),a6
		move.l	(sp)+,a0
		rts

; d4.b = a pole's length (the sprite entry's 4 bytes per phase, a2 = the
; entry + 8; d6 = the row's entry offset, 0 for the nearest). Fine: between
; the phase's byte and the next, after the last the next size's first (the
; nearest size continues its last step). d7 = the phase / 2, as the original.
_PoleLen	TSTPC	_Fine
		beq.b	.orig
		move.w	_FineF(pc),d7
		lsr.w	#4,d7
		movem.l	d0-d1,-(sp)
		moveq	#0,d0
		move.b	4(a2,d7.w),d0
		moveq	#0,d1
		cmp.w	#3,d7
		beq.b	.last
		move.b	5(a2,d7.w),d1
		bra.b	.lerp
.last		tst.w	d6
		beq.b	.nearest
		move.b	-12(a2),d1		;the next size's (16 bytes before)
		bra.b	.lerp
.nearest	move.b	6(a2),d1
		neg.w	d1
		add.w	d0,d1
		add.w	d0,d1
.lerp		sub.w	d0,d1
		move.w	_FineF(pc),d4
		and.w	#15,d4
		muls	d4,d1
		asr.l	#4,d1
		add.w	d0,d1
		move.b	d1,d4
		movem.l	(sp)+,d0-d1
		rts
.orig		move.l	a0,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_BLOCK,a0
		move.w	V_PHASE(a0),d7
		move.l	(sp)+,a0
		lsr.w	#1,d7
		move.b	4(a2,d7.w),d4
		rts

; $3d0c: a tall object drawn from row y up, its top held at phase 6's place
; through the segment: P_CROP + the entry's offset (16 per row) + phase * 4
; gives the graphics' offset down (a1, c rows), y * 40, and c (taken off
; d4). c = y(phase 6) - y. Fine: y the row's fine y, up to phase 6, then
; phase 6's (moving on down would need rows below the graphics' bottom).
_Crop		movea.l	a6,a0
		move.l	_ProgBase(pc),a3
		add.l	#P_CROP,a3
		adda.w	-(a2),a3
		TSTPC	_Fine
		beq.b	.orig
		move.w	(a2),d3
		cmp.w	#11*16,d3
		bhi.b	.orig
		and.w	#15,d3
		bne.b	.orig
		move.w	_FineF(pc),d3
		cmp.w	#48,d3
		bhi.b	.p6
		movem.l	d0-d1/a4,-(sp)
		move.w	(a2),d0
		lsr.w	#4,d0			;the row
		mulu	#34,d0
		move.l	_FineObj(pc),a4
		move.w	(a4,d0.w),d0		;y * 40
		moveq	#-32,d1
		and.w	12+2(a3),d1
		asr.w	#2,d1			;y(phase 6) * 40
		sub.w	d0,d1			;c * 40
		adda.w	d0,a0
		suba.w	d1,a1
		ext.l	d1
		divu	#40,d1
		sub.w	d1,d4
		move.w	d1,d3
		move.w	_FineF(pc),d0		;a3 as the original leaves it
		lsr.w	#4,d0
		lsl.w	#2,d0			;phase * 2 (4 per even phase)
		lea	2(a3,d0.w),a3
		movem.l	(sp)+,d0-d1/a4
		rts
.p6		moveq	#6,d3
		bra.b	.ph
.orig		move.l	a0,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_BLOCK,a0
		move.w	V_PHASE(a0),d3
		move.l	(sp)+,a0
.ph		add.w	d3,d3
		adda.w	d3,a3
		suba.w	(a3)+,a1
		moveq	#-32,d3
		and.w	(a3),d3
		asr.w	#2,d3
		adda.w	d3,a0
		moveq	#31,d3
		and.w	(a3),d3
		sub.w	d3,d4
		rts

; The FINE positions' tables, from the program's 4 phases. Position F is
; 16a + g: phase 2a and g/16 of the way to phase 2a + 2, where phase 8 is
; phase 0 one slice nearer. The slices' boundaries (cumulative rows) are
; interpolated; the row-to-slice maps and the stripes follow from them. The
; object rows' screen rows and lanes' x are interpolated (the nearest row at
; phase 8 is at the screen's bottom, row 200, its x extrapolated along the
; lane). Rounding down keeps every row above 200. At F = 16a every table
; equals the program's.
_FineInit	movem.l	d0-d7/a0-a6,-(sp)
		move.l	_ProgBase(pc),a5
		move.l	_Work(pc),a6
		move.l	a6,a0
		add.l	#W_FT,a0
		move.l	a5,a1
		add.l	#P_SLICEH,a1
		moveq	#4-1,d7
.tp		moveq	#0,d0
		move.w	d0,(a0)+
		moveq	#14-1,d6
.ti		moveq	#0,d1
		move.b	(a1)+,d1
		addq.w	#1,d1
		add.w	d1,d0
		move.w	d0,(a0)+
		dbf	d6,.ti
		addq.l	#2,a1
		dbf	d7,.tp
		lea	-4*30+2(a0),a1		;phase 8: phase 0's from the second
		moveq	#14-1,d6
.t8		move.w	(a1)+,(a0)+
		dbf	d6,.t8
		move.w	-2(a0),d0
		addq.w	#1,d0
		move.w	d0,(a0)+
		moveq	#0,d7			;F
.f		move.w	d7,d6
		lsr.w	#4,d6			;a
		moveq	#15,d5
		and.w	d7,d5			;g
		move.l	a6,a0			;the boundaries
		add.l	#W_FT,a0
		move.w	d6,d0
		mulu	#30,d0
		add.w	d0,a0
		lea	30(a0),a1
		move.l	a6,a2
		add.l	#W_FT+5*30,a2
		moveq	#15-1,d4
.tf		move.w	(a1)+,d0
		move.w	(a0)+,d1
		sub.w	d1,d0
		muls	d5,d0
		asr.l	#4,d0
		add.w	d1,d0
		move.w	d0,(a2)+
		dbf	d4,.tf
		lea	-30(a2),a2
		move.l	a6,a3			;the map
		add.l	#W_FMAP,a3
		move.w	d7,d0
		mulu	#100,d0
		add.l	d0,a3
		move.l	a3,a4
		move.w	28(a2),d0
		cmp.w	#98,d0
		bls.b	.cnt
		moveq	#98,d0
.cnt		move.w	d0,(a3)+
		moveq	#0,d1			;row
		moveq	#0,d2			;slice
.mr		cmp.w	d0,d1
		bhs.b	.mdone
.ms		move.w	d2,d3
		add.w	d3,d3
		cmp.w	2(a2,d3.w),d1
		blo.b	.mput
		addq.w	#1,d2
		bra.b	.ms
.mput		move.b	d2,(a3)+
		addq.w	#1,d1
		bra.b	.mr
.mdone		lea	2(a4),a3		;the stripes: even slices coloured at parity 0
		move.l	a6,a4
		add.l	#W_FSTRIPE,a4
		move.w	d7,d0
		mulu	#192,d0
		add.l	d0,a4
		moveq	#96-1,d4
.st		moveq	#1,d0
		and.b	(a3)+,d0
		beq.b	.even
		clr.w	(a4)
		move.w	#10240,FINE*192(a4)
		bra.b	.snext
.even		move.w	#10240,(a4)
		clr.w	FINE*192(a4)
.snext		addq.l	#2,a4
		dbf	d4,.st
		move.l	a6,a4			;the object rows
		add.l	#W_FOBJ,a4
		move.w	d7,d0
		mulu	#OBJ_SET,d0
		add.l	d0,a4
		move.l	a5,a0
		add.l	#P_OBJTAB,a0
		move.w	d6,d0
		mulu	#OBJ_SET,d0
		add.w	d0,a0			;phase 2a
		lea	OBJ_SET(a0),a1		;phase 2a + 2
		cmp.w	#3,d6
		bne.b	.b
		move.l	a5,a1
		add.l	#P_OBJTAB+34,a1		;phase 8: phase 0 one row on
.b		moveq	#0,d4			;row
.row		moveq	#0,d0
		move.w	(a0),d0
		divu	#40,d0			;yA
		cmp.w	#3,d6
		bne.b	.yb
		cmp.w	#11,d4
		bne.b	.yb
		move.w	#200,d2
		bra.b	.yl
.yb		moveq	#0,d2
		move.w	(a1),d2
		divu	#40,d2			;yB
.yl		move.w	d2,d3
		sub.w	d0,d3
		muls	d5,d3
		asr.l	#4,d3
		add.w	d0,d3			;y
		move.w	d3,d1
		mulu	#40,d1
		move.w	d1,(a4)+
		move.w	d3,d1
		sub.w	#104,d1
		add.w	d1,d1
		add.w	d1,d1
		move.w	d1,(a4)+		;the row's place in the projection's rows
		lea	4(a0),a2
		lea	4(a1),a3
		moveq	#15-1,d1
.lane		move.w	(a2)+,d2		;xA
		cmp.w	#3,d6
		bne.b	.lb
		cmp.w	#11,d4
		bne.b	.lb
		move.l	d1,-(sp)		;xB = xA + (xA - x0) * (200 - yA) / (yA - y0)
		move.w	d2,d3
		sub.w	-34(a3),d3
		move.w	#200,d1
		sub.w	d0,d1
		muls	d1,d3
		moveq	#0,d1
		move.w	-34(a1),d1
		divu	#40,d1
		neg.w	d1
		add.w	d0,d1
		divs	d1,d3
		add.w	d2,d3
		move.l	(sp)+,d1
		bra.b	.lx
.lb		move.w	(a3),d3			;xB
.lx		addq.l	#2,a3
		sub.w	d2,d3
		muls	d5,d3
		asr.l	#4,d3
		add.w	d2,d3
		move.w	d3,(a4)+
		dbf	d1,.lane
		lea	34(a0),a0
		lea	34(a1),a1
		addq.w	#1,d4
		cmp.w	#12,d4
		blo	.row
		moveq	#17-1,d1		;row 12 as the phase's
.r12		move.w	(a0)+,(a4)+
		dbf	d1,.r12
		addq.w	#1,d7
		cmp.w	#FINE,d7
		blo	.f
		movem.l	(sp)+,d0-d7/a0-a6
		rts

; Before the race loop: the first pass runs the logic and draws its result.
_RaceInit	move.l	a0,-(sp)
		lea	_Pending(pc),a0
		st	(a0)
		move.l	_ProgBase(pc),a0
		move.w	P_FIELDS(a0),-(sp)
		lea	_NextTick(pc),a0
		move.w	(sp)+,(a0)
		movem.l	d0/a1,-(sp)
		move.l	_ProgBase(pc),a0
		move.w	P_FIELDS(a0),d0
		lea	_LastF(pc),a1
		move.w	d0,(a1)
		add.l	#P_BLOCK,a0
		moveq	#0,d0
		move.w	V_PHASE(a0),d0		;the positions from the race's start
		lsl.w	#3,d0
		lea	_XLive(pc),a1
		move.l	d0,(a1)+		;_XLive
		move.l	d0,(a1)+		;_XPrev
		lsl.l	#4,d0
		move.l	d0,(a1)			;_XS
		movem.l	(sp)+,d0/a1
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
		move.l	_ProgBase(pc),a0
		add.l	#P_GFX,a0
		move.l	(a0),a0
		lea	_GfxLo(pc),a1
		move.l	a0,(a1)+		;_GfxLo
		move.l	a0,d0
		add.l	#GFX_SIZE,d0
		move.l	d0,(a1)+		;_GfxHi
		move.l	_Work(pc),d0
		add.l	#W_GFX,d0
		sub.l	a0,d0
		move.l	d0,(a1)			;_GfxRace
		move.l	_Work(pc),a1
		add.l	#W_GFX,a1
		move.l	#GFX_SIZE/16-1,d0
.gfx2		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		move.l	(a0)+,(a1)+
		subq.l	#1,d0
		bpl.b	.gfx2
		movem.l	(sp)+,d0/a1
.nogfx		move.l	(sp)+,a0
		lea	$dff000,a0		;stolen
		rts

; Replaces the loop's calls of the logic, the road and the clear.
_PreDraw	movem.l	d0-d7/a0-a6,-(sp)
		move.l	_Custom2(pc),d0		;Enhanced framerate
		bne.b	.free
		move.l	_ProgBase(pc),a0	;off: every frame a tick frame (12.5 fps)
.cap		move.w	P_FIELDS(a0),d0
		sub.w	_NextTick(pc),d0
		bmi.b	.cap
.free
		TSTPC	_FastExp
		beq.b	.nosky
		bsr	_QSky
.nosky
		TSTPC	_Pending
		beq.b	.due
		lea	_Pending(pc),a0
		sf	(a0)
		move.l	_Work(pc),a1
		lea	W_PREV(a1),a1
		bsr	_ToBuf			;the state shown at the last tick
		move.l	_AddrLogic(pc),a0
		jsr	(a0)
		bsr	_Advance
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
	IFND NOSMOOTH
		move.l	_Custom2(pc),d1
		beq.b	.road
		moveq	#0,d0
		bsr	_Smooth
		bsr	_TickPose
	ENDC
		bra.b	.road
.between	lea	_Staged(pc),a0
		st	(a0)
		bsr	_SaveState
		bsr	_Smooth
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
		bsr	_CpuSky
		bsr	_QSync
		bsr	_CompareClear
	ELSE
		bsr	_CopyRoad
		bsr	_CpuSky
		bsr	_QSync
	ENDC
		lea	_GfxDelta(pc),a0	;the objects' and the buggy's source
		move.l	_GfxRace(pc),(a0)
		rts

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
		lea	_PoseNext(pc),a0
		sf	(a0)
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
		lsl.w	#3,d3
		divu	#TICK,d3
		lsl.w	#3,d1
		add.w	d1,d3			;u: S_prev's segment start + 0 to 128, in 1/FINE
		move.w	d3,d4
	IFND NOSMOOTH
		move.l	_XS(pc),d0		;smoothed: u = X - S_prev's segment start
		lsr.l	#4,d0
		sub.l	_XPrev(pc),d0
		add.w	d1,d0
		bpl.b	.u
		moveq	#0,d0
.u		move.w	d0,d4
	ENDC
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
.block		lea	_PoseLat(pc),a0
		move.w	d6,(a0)+		;_PoseLat
		move.w	d5,(a0)			;_PoseLatOn
		move.w	d4,d3
		cmp.w	#FINE,d3
		blo.b	.prev
		sub.w	#FINE,d3		;past the crossing: S_next's segment
		lea	_PoseNext(pc),a0
		st	(a0)
.prev
	IFD COARSE
		and.w	#-16,d3			;A/B: only the program's 4 phases
	ENDC
		lea	_FineF(pc),a0
		move.w	d3,(a0)
		moveq	#15,d4
		and.w	d3,d4			;g: sixteenths from P0 to P0 + 2
		lsr.w	#4,d3
		add.w	d3,d3			;P0
		tst.w	d4
		beq.b	.final
		cmp.w	#6,d3
		bne.b	.sameb
		TSTPC	_PoseNext
		bne.b	.sameb
		moveq	#0,d0			;P0 + 2 = 8: S_next (live) at 0
		bsr	_ProjAt
		bsr	_SaveRows
		bra.b	.final
.sameb		bsr	_PoseState
		move.w	d3,d0
		addq.w	#2,d0
		bsr	_ProjAt
		bsr	_SaveRows
.final		bsr	_PoseState
		move.w	d3,d0
		bsr	_ProjAt
		tst.w	d4
		beq.b	.tables
		bsr	_LerpRows
		bsr	_FineMap
.tables		bsr	_FineTables
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

; The fine tables' pointers for _FineF and the live state's parity; the
; drawing's readers use them from now (_Fine).
_FineTables	movem.l	d0-d1/a0-a1,-(sp)
		move.w	_FineF(pc),d0
		move.l	_Work(pc),a0
		add.l	#W_FOBJ,a0
		move.w	d0,d1
		mulu	#OBJ_SET,d1
		add.l	d1,a0
		lea	_FineObj(pc),a1
		move.l	a0,(a1)+		;_FineObj
		move.l	_Work(pc),a0
		add.l	#W_FSTRIPE,a0
		moveq	#8,d1
		and.w	V_PARITY(a4),d1
		lsl.w	#3,d1			;parity * FINE
		add.w	d0,d1
		mulu	#192,d1
		add.l	d1,a0
		move.l	a0,(a1)			;_FineStripe
		lea	_Fine(pc),a0
		st	(a0)

		movem.l	(sp)+,d0-d1/a0-a1
		rts

; At a logic step: the committed position, counted on in 1/FINE segment
; (_XLive, and _XPrev before the step). A step backwards or of more than
; a segment (a new race, a reset) starts the count again.
_Advance	movem.l	d0-d3/a0-a2,-(sp)
		move.l	_ProgBase(pc),a0
		add.l	#P_BLOCK,a0
		move.l	_Work(pc),a1
		lea	W_PREV(a1),a1
		move.w	V_PHASE(a1),d1		;ph0
		move.w	V_PHASE(a0),d2		;ph1
		move.w	V_PARITY(a0),d3
		cmp.w	V_PARITY(a1),d3
		beq.b	.same
		moveq	#8,d0
		sub.w	d1,d0
		add.w	d2,d0
		bra.b	.have
.same		move.w	d2,d0
		sub.w	d1,d0
		bmi.b	.reset
.have		cmp.w	#8,d0
		bhi.b	.reset
		lsl.w	#3,d0
		ext.l	d0
		lea	_XLive(pc),a2
		move.l	(a2),d1
		move.l	d1,4(a2)		;_XPrev
		add.l	d0,d1
		move.l	d1,(a2)
		bra.b	.done
.reset		lea	_XLive(pc),a2
		moveq	#0,d0
		move.w	d2,d0
		lsl.w	#3,d0
		move.l	d0,(a2)+		;_XLive: ph1 in segment 0
		lsl.w	#3,d1
		move.l	d1,(a2)+		;_XPrev: ph0 in segment 0
		lsl.l	#4,d0
		move.l	d0,(a2)			;_XS
.done		movem.l	(sp)+,d0-d3/a0-a2
		rts

; The smoothed position _XS (1/16 of 1/FINE segment): on by the speed band's
; mean phase step (the 8 steps of P_STEPS) per field since the last frame,
; then held between the committed position less LMAX and the committed
; position, and in a state the frame can draw: a tick frame (d0.w >= 0) in
; the committed segment, a frame between ticks (n = TICK + d0) in S_prev's
; or S_next's, and reaching S_next's by the tick frame (CATCH per field).
_Smooth		movem.l	d0-d6/a0-a2,-(sp)
		move.l	_ProgBase(pc),a0
		move.w	P_FIELDS(a0),d1
		lea	_LastF(pc),a1
		move.w	d1,d2
		sub.w	(a1),d2			;fields since the last frame
		move.w	d1,(a1)
		cmp.w	#8,d2
		bls.b	.dt
		moveq	#8,d2
.dt		add.l	#P_BLOCK,a0
		moveq	#$70,d3
		and.w	V_SPEED(a0),d3
		move.l	_ProgBase(pc),a2
		add.l	#P_STEPS,a2
		adda.w	d3,a2
		moveq	#0,d4
		moveq	#8-1,d5
.sum		add.w	(a2)+,d4
		dbf	d5,.sum
		lsl.w	#3,d4			;sum * 2 phase units * 8 / 8 ticks / TICK * 16
		mulu	d2,d4
		move.l	_XS(pc),d5
		add.l	d4,d5
		move.l	_XLive(pc),d3		;hi
		move.w	V_PHASE(a0),d4
		lsl.w	#3,d4
		ext.l	d4
		move.l	d3,d6
		sub.l	d4,d6			;S_next's segment start
		move.l	d3,d1
		sub.l	#LMAX,d1		;lo
		tst.w	d0
		bmi.b	.between
		cmp.l	d6,d1
		bge.b	.clamp
		move.l	d6,d1
		bra.b	.clamp
.between	move.l	_Work(pc),a2
		lea	W_PREV(a2),a2
		move.w	V_PHASE(a2),d4
		lsl.w	#3,d4
		ext.l	d4
		move.l	_XPrev(pc),d2
		sub.l	d4,d2			;S_prev's segment start
		cmp.l	d2,d1
		bge.b	.ramp
		move.l	d2,d1
.ramp		move.w	d0,d4			;n - TICK
		muls	#CATCH,d4
		add.l	d6,d4
		cmp.l	d4,d1
		bge.b	.clamp
		move.l	d4,d1
.clamp		lsl.l	#4,d1
		lsl.l	#4,d3
		cmp.l	d1,d5
		bge.b	.lo
		move.l	d1,d5
.lo		cmp.l	d3,d5
		ble.b	.hi
		move.l	d3,d5
.hi		lea	_XS(pc),a1
		move.l	d5,(a1)
		movem.l	(sp)+,d0-d6/a0-a2
		rts

; A tick frame at the smoothed position: in the committed state, only the
; position's variables changed (the phase's three, the projection's
; output), and _PostDraw puts them back, so the drawing's own writes stay.
_TickPose	movem.l	d0-d7/a0-a6,-(sp)
		move.l	_ProgBase(pc),a5
		move.l	a5,a4
		add.l	#P_BLOCK,a4
		move.l	_XS(pc),d3
		lsr.l	#4,d3
		move.w	V_PHASE(a4),d1
		lsl.w	#3,d1
		ext.l	d1
		move.l	_XLive(pc),d2
		sub.l	d1,d2
		sub.l	d2,d3			;F in the committed segment
		bmi	.no
	IFD COARSE
		and.w	#-16,d3
	ENDC
		cmp.w	d1,d3
		bhs	.no			;at the committed position
		bsr	_TSave
		lea	_PoseNext(pc),a0
		st	(a0)
		lea	_PoseLatOn(pc),a0
		clr.w	(a0)
		lea	_FineF(pc),a0
		move.w	d3,(a0)
		moveq	#15,d4
		and.w	d3,d4
		lsr.w	#4,d3
		add.w	d3,d3			;P0
		tst.w	d4
		beq.b	.final
		move.w	d3,d0
		addq.w	#2,d0
		bsr	_ProjAt
		bsr	_SaveRows
.final		move.w	d3,d0
		bsr	_ProjAt
		tst.w	d4
		beq.b	.tables
		bsr	_LerpRows
		bsr	_FineMap
.tables		bsr	_FineTables
		lea	_TickPosed(pc),a0
		st	(a0)
.no		movem.l	(sp)+,d0-d7/a0-a6
		rts

; The position's variables of a tick frame, to W_TSAVE (_TSave) and back.
_TRegions	dc.l	$987c,6/2		;words: the phase, * 221, the road's
		dc.l	$9892,4/2		;the projection's
		dc.l	$98dc,2/2
		dc.l	$9b22,($9d3c-$9b22)/2	;rows and curves
		dc.l	0

_TSave		movem.l	d0/a0-a2,-(sp)
		move.l	_Work(pc),a1
		add.l	#W_TSAVE,a1
		lea	_TRegions(pc),a2
.next		move.l	(a2)+,a0
		add.l	_ProgBase(pc),a0
		move.l	(a2)+,d0
		subq.w	#1,d0
.copy		move.w	(a0)+,(a1)+
		dbf	d0,.copy
		tst.l	(a2)
		bne.b	.next
		movem.l	(sp)+,d0/a0-a2
		rts

_TRestore	movem.l	d0/a0-a2,-(sp)
		move.l	_Work(pc),a1
		add.l	#W_TSAVE,a1
		lea	_TRegions(pc),a2
.next		move.l	(a2)+,a0
		add.l	_ProgBase(pc),a0
		move.l	(a2)+,d0
		subq.w	#1,d0
.copy		move.w	(a1)+,(a0)+
		dbf	d0,.copy
		tst.l	(a2)
		bne.b	.next
		movem.l	(sp)+,d0/a0-a2
		rts

; The pose's state in the live block: S_prev unless the pose is past the
; crossing (S_next, live already). Loaded once.
_PoseState	TSTPC	_PoseNext
		bne.b	.done
		move.l	a1,-(sp)
		lea	_PoseNext(pc),a1
		st	(a1)			;loaded: S_prev is now live
		move.l	a3,a1
		bsr	_FromBuf
		move.l	(sp)+,a1
.done		rts

; The projection for phase d0.w (even, 0 to 6) in the live state, with the
; pose's lateral position.
_ProjAt		movem.l	d0-d7/a0-a6,-(sp)
		move.w	d0,V_PHASE(a4)
		move.w	d0,d1
		mulu	#221,d1
		move.w	d1,V_PHASE221(a4)
		moveq	#8,d1
		and.w	V_PARITY(a4),d1
		add.w	d0,d1
		mulu	#96,d1
		move.w	d1,V_ROADPH(a4)
		TSTPC	_PoseLatOn
		beq.b	.go
		move.w	_PoseLat(pc),V_LAT(a4)
.go		move.l	a5,a0
		add.l	#P_PROJECT,a0
		jsr	(a0)
		movem.l	(sp)+,d0-d7/a0-a6
		rts

; The rows' x (the low words of the projection's per-row longs) to W_FX.
_SaveRows	movem.l	d0/a0-a1,-(sp)
		move.l	a5,a0
		add.l	#P_ROWS+2,a0
		move.l	_Work(pc),a1
		add.l	#W_FX,a1
		moveq	#106-1,d0
.copy		move.w	(a0),(a1)+
		addq.l	#4,a0
		dbf	d0,.copy
		movem.l	(sp)+,d0/a0-a1
		rts

; Rows' x: this projection's, d4/16 of the way to W_FX's.
_LerpRows	movem.l	d0-d2/a0-a1,-(sp)
		move.l	a5,a0
		add.l	#P_ROWS+2,a0
		move.l	_Work(pc),a1
		add.l	#W_FX,a1
		moveq	#106-1,d2
.row		move.w	(a1)+,d0
		move.w	(a0),d1
		sub.w	d1,d0
		muls	d4,d0
		asr.l	#4,d0
		add.w	d1,d0
		move.w	d0,(a0)
		addq.l	#4,a0
		dbf	d2,.row
		movem.l	(sp)+,d0-d2/a0-a1
		rts

; The rows' slices (the projection's last part, $2446) from the fine map.
_FineMap	movem.l	d0-d2/a0-a2,-(sp)
		move.l	a5,a0
		add.l	#P_ROWHI,a0
		move.l	a5,a1
		add.l	#P_SLICES,a1
		move.l	_Work(pc),a2
		add.l	#W_FMAP,a2
		move.w	_FineF(pc),d0
		mulu	#100,d0
		add.l	d0,a2
		move.w	(a2)+,d2
		subq.w	#1,d2
.row		moveq	#0,d0
		move.b	(a2)+,d0
		lsl.w	#5,d0
		move.w	(a1,d0.w),(a0)
		addq.l	#4,a0
		dbf	d2,.row
		movem.l	(sp)+,d0-d2/a0-a2
		rts

; Replaces the loop's swap and the test after it. A frame between ticks
; restores the state and goes straight back to the loop: the checks after
; the swap (race end, right button, left button delay) see only tick frames.
_PostDraw	movem.l	d0-d1/a0-a1,-(sp)
		lea	_GfxDelta(pc),a0
		clr.l	(a0)
		lea	_Fine(pc),a0
		sf	(a0)
		TSTPC	_TickPosed
		beq.b	.posed
		lea	_TickPosed(pc),a0
		sf	(a0)
		bsr	_TRestore
.posed
	IFD VERIFY
		bsr	_CompareGfx
	ENDC
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
_QHead		dc.l	0			;the next blit to start; these two in this order
_QTail		dc.l	0			;the end of the recorded blits
_GfxLo		dc.l	0			;alloc 2, and its end; these three in this order
_GfxHi		dc.l	0
_GfxRace	dc.l	0			;W_GFX - alloc 2, from the race's start
_GfxDelta	dc.l	0			;_GfxRace while the loop draws, else 0
_NextTick	dc.w	0			;P_FIELDS value the next tick is due at
_FineF		dc.w	0			;the pose's position in its segment, 0 to FINE-1
_PoseLat	dc.w	0			;the pose's lateral position; these two in this order
_PoseLatOn	dc.w	0			;-1: set it
_XLive		dc.l	0			;the committed position (1/FINE segment); these three in this order
_XPrev		dc.l	0			;before the last logic step
_XS		dc.l	0			;the smoothed position, * 16
_LastF		dc.w	0			;P_FIELDS at the last frame
_FineObj	dc.l	0			;W_FOBJ's table for _FineF; these two in this order
_FineStripe	dc.l	0			;W_FSTRIPE's table for _FineF and the parity
	IFD VERIFY
_VHorizon	dc.w	0			;V_HORIZON before the queued clear
_VGfxCount	dc.w	0			;_CompareGfx runs every 16th frame
	ENDC
_Enh		dc.b	0			;-1: the enhanced path (word-aligned)
_FastExp	dc.b	0			;-1: the ExpMem is fast memory
_Pending	dc.b	0			;-1: run the logic before the next frame
_Staged		dc.b	0			;-1: this frame is between ticks
_InLoop		dc.b	0			;-1: the race loop's swap
_RoadFast	dc.b	0			;-1: the race loop's road, to fast memory
_QRec		dc.b	0			;-1: the clear records its blits
_QBusy		dc.b	0			;-1: the queue is running
_Fine		dc.b	0			;-1: the drawing uses the fine tables (_Pose)
		EVEN
_PoseNext	dc.b	0			;-1: the live state is the pose's (S_next, or S_prev loaded)
_TickPosed	dc.b	0			;-1: this tick frame is drawn at a smoothed position
		EVEN
_FakeSel	dc.w	0			;for _RoadScreen
		dc.l	0			;_Work + W_SCREEN
		EVEN
