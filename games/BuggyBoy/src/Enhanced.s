;*---------------------------------------------------------------------------
; Buggy Boy Enhanced: the path for a 68020 or better, DOS version only.
; Included by BuggyBoyHD.s. A 68000 or 68010, and the disk versions, keep 1.3.
;
; - The CPU caches are enabled (resload_SetCPU).
; - With the ExpMem in fast memory the program, its public allocations
;   (COURSES.DAT) and the stack are there; the DMA buffers stay in chip.
;---------------------------------------------------------------------------*

EXPSIZE		= $30000			;ws_ExpMem (optional)
EXP_HEAP	= $c000				;public allocations, after the program
EXP_STACK	= $2000				;the stack, at the top

CPU_68020	= 1				;AttnFlags bits (exec/execbase.i)
CPU_68040	= 3
CPU_68060	= 7
MEM_CHIP	= 1				;MEMB_CHIP (exec/memory.i)

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
		cmp.l	#$200000,d0		;chip memory
		blo.b	.done
		cmp.l	#$c00000,d0		;slow memory on the chip bus
		blo.b	.fast
		cmp.l	#$e00000,d0
		blo.b	.done
.fast		st	1(a0)			;_FastExp
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
		move.l	_expmem(pc),a1
.chip		rts

;======================================================================
; The game's AllocMem: public requests go to the ExpMem when it is fast.
; d0 = size, d1 = requirements; returns d0 = a0 = cleared memory.
;======================================================================

_AllocMem	btst	#MEM_CHIP,d1
		bne	_AllocChip
		TSTPC	_FastExp
		beq	_AllocChip
		movem.l	d1-d2/a1,-(sp)
		lea	_ExpFree(pc),a1
		move.l	(a1),d1
		move.l	d1,d2
		add.l	#$10,d0
		and.l	#$fffffff0,d0
		add.l	d0,d1
		move.l	_expmem(pc),a0
		add.l	#EXPSIZE-EXP_STACK,a0
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

;======================================================================
; Start the DOS version: a5 = program.
;======================================================================

_EnhGo		lea	_ProgBase(pc),a0
		move.l	a5,(a0)
		TSTPC	_Enh
		beq.b	.go
		bsr.b	_EnhCache
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

_ProgBase	dc.l	0			;program offset 0
_ExpFree	dc.l	0			;next public allocation
_Enh		dc.b	0			;-1: the enhanced path
_FastExp	dc.b	0			;-1: the ExpMem is fast memory
		EVEN
