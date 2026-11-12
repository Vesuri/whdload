;*---------------------------------------------------------------------------
;  :Program.	EncounterHD.s
;  :Contents.	Slave for "Encounter"
;  :Author.	Harry, JOTD, Vesuri
;  :History.	11.01.98/11.05.98 highscore (Harry)
;		1.2 (JOTD): src/original/EncounterHD.s, as upstream has it
;		2.0b (Vesuri): WHDLoad 17 header; option Enhanced framerate
;		(CUSTOM1) runs the game's code and stack from fast memory on a
;		68020 or better, and shows a frame every field when there is
;		time while the world steps at 1.2's 25 Hz: the frame in between
;		has the camera and the objects halfway. Without it the game
;		runs as with 1.2.
;  :Requires.	whdload-package :)
;  :Copyright.	Freeware
;  :Language.	68000 Assembler
;  :Translator.	vasm
;  :To Do.
;---------------------------------------------------------------------------*

;crc_v1	= $57C1
;crc_v2	= $F885	;NTSC

	INCLUDE	whdload.i
	INCLUDE	hardware/custom.i
	INCLUDE	hardware/intbits.i

; The ExpMem (optional): the program copy, the supervisor stack's page, the staged frame's
; save area, the objects before the world step.
EXP_COPY	= 0			;COPY_LO..COPY_HI (src/relocs.i)
EXP_PAGE	= $E000			;the page; offsets in it:
PG_STACKTOP	= $1000			;the stack uses about 128 bytes
EXP_SAVE	= EXP_PAGE+PG_STACKTOP	;_stab's ranges while a staged frame draws
SAVESIZE	= $2000			;ws_ExpMem is whole 4 KB pages
SV_ANIM		= $C00			;in it: _save's animation words, after _stab's ranges
SV_COW		= $1000			;and _tcow's slots
EXP_PREV	= EXP_SAVE+SAVESIZE	;_objsnap's x, y, z, lifetime (128 longs each), then _objstage's list
PREVSIZE	= $1000
EXPMEMSIZE	= EXP_PREV+PREVSIZE
; For tools/route.py and tools/bench.py: the addresses of the main loop's marks (the
; screen swap, the end of the field wait, the logic frame's head) and the logic head itself,
; an rts the loop calls (a breakpoint there sees the state 1.2 has at $DA30).
PG_MSWAP	= $0
PG_MGO		= $4
PG_PREW		= $8			;_pre's wait for the beam: first, last + 2
PG_PREWE	= $C
PG_CAM		= $10			;_camsnap's 18 bytes
PG_PRECLR	= $24			;_kpre: the clear that runs ahead
PG_CLEAR	= $2C			;_clear: the draw's
PG_SORT		= $200			;_sort's copy of the list (128 longs)
PG_STAGE	= $28			;_save: a staged frame starts
PG_HASH		= $108
; VERIFY: the trapped PC and the loop the trap ends in; the space up to the stack's top is
; filled with GUARD, so tools/route.py can tell how deep the stack went.
PG_TRAP		= $100
PG_TRAPLOOP	= $104
PG_GUARD	= $400
GUARD		= $5A5A5A5A

; A staged frame runs only if it is expected to end in its field, by line STAGEEND: its
; estimate (_est) is the last committed draw + this logic frame's transform and sort + the
; last staged frame's save and restore, or the last staged frame's length if longer, + the
; clear unless it ran ahead, + 1/16.
	IFND STAGEEND
STAGEEND	= 300
	ENDC
; The back buffer's clear ($DF94: the view, rows 0-135 of the four planes; the panel below
; is drawn once) runs ahead, in time the loop would wait (_pre, _idle): once the beam has
; shown the view's last row (row 135 at line 44 + 135) of the buffer the next draw goes to,
; until line FIELDLAST; the draw clears the rows left.
CROWS		= 136
VIEWEND		= 44+CROWS
FIELDLAST	= 308
KROWS		= 8			;rows per chunk of the clear
	IFND DDFA
DDFA		= $30			;FMODE 3's fetch window (AGA): the same pixels as
	ENDC
	IFND DDFB
DDFB		= $A8			;the game's $34/$CA at FMODE 0
	ENDC
	IFNE	CROWS-CROWS/KROWS*KROWS
	FAIL	"CROWS is not whole chunks"
	ENDC

; jsr/jmp into the program: assembled with the chip address, moved to the copy by _enhance
; (every $4EB9/$4EF9 with an operand in COPY_LO..COPY_HI between _eloop and _eloopend)
CALL	MACRO
	jsr	(\1).l
	ENDM
GOTO	MACRO
	jmp	(\1).l
	ENDM

;======================================================================

_base		SLAVE_HEADER		;ws_Security + ws_ID
		dc.w	17		;ws_Version
	IFD VERIFY
		dc.w	WHDLF_Disk|WHDLF_NoError|WHDLF_EmulTrap|WHDLF_EmulDivZero|WHDLF_EmulIllegal
	ELSE
		dc.w	WHDLF_Disk|WHDLF_NoError|WHDLF_EmulTrap|WHDLF_EmulDivZero	;ws_flags
	ENDC
		dc.l	$80000		;ws_BaseMemSize
		dc.l	$00		;ws_ExecInstall
		dc.w	SLStart-_base	;ws_GameLoader
		dc.w	0		;ws_CurrentDir
		dc.w	0		;ws_DontCache
 		dc.b	$00		;debugkey
_keyexit	dc.b	$5D		;quitkey
_expmem		dc.l	-EXPMEMSIZE	;ws_ExpMem: optional, WHDLoad writes its address here
		dc.w	_name-_base	;ws_name
		dc.w	_copy-_base	;ws_copy
		dc.w	_info-_base	;ws_info
		dc.w	0		;ws_kickname
		dc.l	0		;ws_kicksize
		dc.w	0		;ws_kickcrc
		dc.w	_config-_base	;ws_config

;============================================================================

_name		dc.b	"Encounter"
		dc.b	0
_copy		dc.b	"1991 Novagen",0
_info		dc.b	"adapted & fixed by Harry & JOTD, Vesuri",10,10
		dc.b	"Version 2.0b (12.11.2026)"
	IFD VERIFY
		dc.b	" (VERIFY)"
	ENDC
		dc.b	0
_config		dc.b	"C1:B:Enhanced framerate",0
		even

;======================================================================
SLStart	;	A0 = resident loader
;======================================================================

	lea	(_resload,pc),a1
	move.l	a0,(a1)			;save for later using

	move.l	_resload(pc),a2

	move.l	#CACRF_EnableI,d0	;enable instruction cache
	move.l	d0,d1			;mask
	jsr	(resload_SetCACR,a2)

	lea	(_tag,pc),a0
	jsr	(resload_Control,a2)

	MOVE.L	#$8C00,D0
	MOVE.L	#$400,D1
	LEA	$400.W,A0
	MOVEQ	#1,D2
	MOVE.L	_resload(PC),A2
	jsr	(resload_DiskLoad,a2)

	MOVEQ.L	#0,D0
	MOVE.L	#$7E00,D1
	LEA	$68000,A0
	MOVEQ.L	#1,D2
	MOVE.L	_resload(PC),A2
	jsr	(resload_DiskLoad,a2)


	JSR	$4BC.W

	bsr	_flushcache
	move.l	_buttonwait(pc),d0
	beq.b	.sk
.WAIT	BTST	#7,$BFE001
	BEQ.S	.sk
	BTST	#6,$BFE001
	BNE.S	.WAIT

.sk
	MOVE.L	#$9000,D0
	MOVE.L	#$6B000-$1AD0,D1
	LEA	$1AD0,A0
	MOVEQ.L	#1,D2
	MOVE.L	_resload(PC),A2
	jsr	(resload_DiskLoad,a2)


	MOVE.W	#$3491,D0
	LEA	$00006000,A0
	LEA	$00013000,A1
.DEC	MOVE.W	D0,D1
	ASL.W	#3,D1
	EOR.W	D0,D1
	ROXL.W	#1,D1
	ROXL.W	#1,D0
	EORI.W	#$AAAA,D0
	EOR.W	D0,(A0)+
	CMPA.L	A0,A1
	BNE.B	.DEC

	bsr	_gate

	lea	(HIGHNAME,PC),a0	;filename
	move.l	(_resload,PC),a3
	jsr	(resload_GetFileSize,a3)
	tst.l	d0
	beq.s	.SK1
	MOVE.L	#$91E2,A1	;ADDY
	MOVE.L	#$90,D0		;LEN
	lea	(HIGHNAME,PC),a0	;filename
	jsr	(resload_LoadFile,a3)

.SK1
	PEA	INT3(PC)
	MOVE.L	(A7)+,$6C.W

	MOVE.W	#$4EB9,$94C6
	PEA	SAVEHIGH(PC)
	MOVE.L	(A7)+,$94C8

	MOVE.W	#$4eb9,$c4d2
	pea	keyhp(PC)
	MOVE.L	(A7)+,$c4d4

; The game-over pause: a CPU-speed countdown of d0 from $8A354 ($DC54-$DC67), about 108
; fields on a 68000 and a blink on a 68030. Now jsr _gowait; bra.b $DC68.
	MOVE.W	#$4EB9,$DC54
	pea	(_gowait,PC)
	MOVE.L	(A7)+,$DC56
	MOVE.W	#$600C,$DC5A

	move.l	(_enhanced,pc),d0
	beq.b	.native
	bsr	_enhance
.native
	MOVE.W	#$8390,$DFF096
	MOVE.W	#$8000+$3500,$DFF09E

	bsr	_flushcache

	JMP	$D7E2			;with Enhanced framerate a jmp to the copy

INT3	MOVE.W	#$380,$DFF09C
	RTE

_flushcache:
	move.l	a2,-(a7)
	move.l	_resload(pc),a2
	jsr	resload_FlushCache(a2)
	move.l	(a7)+,a2
	rts

SAVEHIGH
	CLR.B	$939B
	MOVEM.L	D0-A2,-(A7)
	LEA.L	$91E2,A1		;ADDY
	move.l	#$90,D0			;len
	lea	HIGHNAME(PC),a0		;filename
	move.l	(_resload,pc),a2
	jsr	(resload_SaveFile,a2)
	MOVEM.L	(A7)+,D0-A2
	RTS


; Waits GOFIELDS field changes of the game's field counter (the level-3 interrupt counts it;
; $E28C, called next, waits on it too).
GOFIELDS = 108
_gowait	movem.l	d0/d1,-(a7)
	move.w	#GOFIELDS-1,d1
.f	move.w	$11DEC,d0
.w	cmp.w	$11DEC,d0
	beq.b	.w
	dbf	d1,.f
	movem.l	(a7)+,d0/d1
	rts

DBFD1
	AND.L	#$FFFF,D1
	DIVU	#$28,D1
.4	MOVE.L	D1,-(A7)
	MOVE.B	$DFF006,D1
.3	CMP.B	$DFF006,D1
	BEQ.S	.3
	MOVE.L	(A7)+,D1
	DBF	D1,.4
	RTS

;version	dc.w	0	;version of disks
_resload	dc.l	0	;address of resident loader
HIGHNAME	DC.B	'ENHIGH',0
	EVEN

; RAW-Key-Codes:
;	ESC	$45
;	DEL	$46
;	F1..F10	$50..$59
;	HELP	$5f
;	NUM *	$5D

keyhp
	MOVEQ.L	#$50,D1
	BSR.W	DBFD1

	CMP.B	_keyexit(pc),D0
	BEQ.S	QUIT


	CMP.B	#$5B,D0
	BNE.S	.C

;	MOVE.W	#$8280,$dff096
	MOVE.B	#0,$DFF101
	MOVE.B	#0,$DFF104
	MOVE.W	#0,$DFF106
	MOVE.W	#$11,$DFF10C

.C	RTS

QUIT	pea	TDREASON_OK
_end	move.l	(_resload,pc),-(a7)
	add.l	#resload_Abort,(a7)
	rts

;======================================================================
; Enhanced framerate
;======================================================================

; _enhanced = 1 when CUSTOM1 is set, the CPU is a 68020 or better, the ExpMem was allocated
; in fast memory ($200000-$9FFFFF or from $1000000 up; never chip or the $C00000 slow
; memory), and the decrypted program is the one src/relocs.i was made from. Otherwise 0 and
; the game runs as with 1.2. VERIFY: CUSTOM2 bits fake a failing check (0: no ExpMem,
; 1: ExpMem in chip, 2: a 68000, 3: another program).
_gate	movem.l	d0-d2/a0-a2,-(a7)
	moveq	#0,d2
	move.l	(_custom1,pc),d0
	beq.b	.off
	move.w	(_attn,pc),d0
	IFD VERIFY
	btst	#2,(_custom2+3,pc)
	beq.b	.v2
	moveq	#0,d0
.v2
	ENDC
	btst	#AFB_68020,d0
	beq.b	.off
	move.l	(_expmem,pc),d0
	IFD VERIFY
	btst	#0,(_custom2+3,pc)
	beq.b	.v0
	moveq	#0,d0
.v0	btst	#1,(_custom2+3,pc)
	beq.b	.v1
	move.l	#$40000,d0
.v1
	ENDC
	cmp.l	#$200000,d0
	blo.b	.off
	cmp.l	#$a00000,d0
	blo.b	.fast
	cmp.l	#$1000000,d0
	blo.b	.off
.fast	lea	COPY_LO,a0
	move.l	#COPY_HI-COPY_LO,d0
	move.l	(_resload,pc),a2
	jsr	(resload_CRC16,a2)
	IFD VERIFY
	btst	#3,(_custom2+3,pc)
	beq.b	.v3
	not.w	d0
.v3
	ENDC
	cmp.w	#COPY_CRC,d0
	bne.b	.off
	moveq	#1,d2
.off	lea	(_enhanced,pc),a0
	move.l	d2,(a0)
	movem.l	(a7)+,d0-d2/a0-a2
	rts

; Copy the program (after the decryption and the patches above) to the ExpMem and relocate
; the copy (src/relocs.i, tools/relocs.py): code addresses to the copy, the two variables
; the code also reads PC-relative into the copy, the stack into the ExpMem. Replace the
; horizon plotter's self-modifying loops in the copy. Point the chip entries reached through
; data at the copy. The chip program stays as it was otherwise: code the relocation does not
; reach runs from chip, unrelocated, and is only slower.
_enhance
	movem.l	d0-d7/a0-a6,-(a7)
	move.l	(_expmem,pc),a1
	move.l	a1,d7
	sub.l	#COPY_LO,d7		;d7 = copy - chip
	lea	COPY_LO,a0
	move.w	#(COPY_HI-COPY_LO)/4-1,d0
.copy	move.l	(a0)+,(a1)+
	dbf	d0,.copy
	lea	(_rel_code,pc),a0
	bsr.w	.rel
	lea	(_rel_moved,pc),a0
	bsr.w	.rel
	lea	(_rel_smc,pc),a0
	bsr.w	.rel
	lea	(_rel_tab,pc),a0
	bsr.w	.rel
; movea.l #$7FFFE,a7 at the entry: the stack's top in the ExpMem
	bsr	_page
	move.l	a0,d0
	add.l	#PG_STACKTOP,d0
	lea	STACK_OPERAND,a0
	move.l	d0,(a0,d7.l)
	bsr	_fmode
	bsr	_hzinstall
	lea	$E50E,a0		;the transform's first store to a slot's arrays
	add.l	d7,a0
	move.w	#$4EB9,(a0)+		;jsr _tcow; nop; nop
	pea	(_tcow,pc)
	move.l	(a7)+,(a0)+
	move.l	#$4E714E71,(a0)
; The level-3 handler ends with move.w #$20,$DFF09C / rte ($81A8). From fast memory the rte
; completes before Paula drops the request and the handler runs again at once (twice a
; field). The copy jumps to _ack3 instead, which acknowledges twice.
	lea	$81A8,a0
	add.l	d7,a0
	move.w	#$4EF9,(a0)+
	pea	(_ack3,pc)
	move.l	(a7)+,(a0)
	lea	(_tramp,pc),a0
.tr	move.l	(a0)+,d0
	beq.b	.trd
	move.l	d0,a1
	move.w	#$4EF9,(a1)+		;jmp copy
	add.l	d7,d0
	move.l	d0,(a1)
	bra.b	.tr
.trd	bsr	_loopinstall
	IFD VERIFY
	bsr	_verifyinit
	ENDC
; Caches: as 1.2 the instruction cache, now also the data cache and the ExpMem and slave
; copyback. Chip memory is not data-cached: the hardware inhibits it on the 68030, and
; on the 68040/060 (WHDLoad uses the MMU) BaseMem is made noncacheable. A 68030 without
; WHDLoad's MMU would turn all caches off for a noncacheable BaseMem, so there it is
; write-through. resload_SetCPU flushes, and does nothing under NoCache.
	move.l	#WCPUF_Base_WT|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC,d0
	move.w	(_attn,pc),d1
	btst	#AFB_68040,d1
	beq.b	.wt
	move.l	#WCPUF_Base_NC|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC,d0
.wt	move.l	#WCPUF_Base|WCPUF_Exp|WCPUF_Slave|WCPUF_IC|WCPUF_DC,d1
	move.l	(_resload,pc),a2
	jsr	(resload_SetCPU,a2)
	movem.l	(a7)+,d0-d7/a0-a6
	rts

; add d7 to the copy's long at each listed chip address
.rel	move.l	(a0)+,d0
	beq.b	.reld
	move.l	d0,a1
	add.l	d7,(a1,d7.l)
	bra.b	.rel
.reld	rts

_ack3	move.w	#INTF_VERTB,$DFF000+intreq
	move.w	#INTF_VERTB,$DFF000+intreq
	rte

; a0 = the ExpMem's page
_page	move.l	(_expmem,pc),a0
	add.l	#EXP_PAGE,a0
	rts

; The horizon plotter ($CA52-$CB90) writes the four plane operations of the current colour
; into its two loops ($CB0A-$CB1C, $CB80-$CB86) when the colour changes, with six move.l at
; $CA86-$CAA4 (a5, a4 = the operations, from the table at $12A40 indexed by the colour).
; The copy keeps that, but the stores go through _hzset, which then makes the new
; instructions visible: copyback fast memory on the 68040/060 holds them in the data cache,
; and no 68020-060 instruction cache sees data writes. The replacement at $CA86:
; jsr _hzset; bra.b $CAAA (the original's next instruction). Registers and memory end as
; after the original's stores.
_hzinstall
	lea	$CB0A,a0
	add.l	d7,a0
	lea	(_hzslots,pc),a1
	move.l	a0,(a1)
	lea	(_hzflush30,pc),a1
	move.w	(_attn,pc),d0
	and.w	#(1<<AFB_68040)|(1<<7),d0	;68040, 68060 (AFB_68060)
	beq.b	.flush
	lea	(_hzflush40,pc),a1
.flush	lea	(_hzflush,pc),a0
	move.l	a1,(a0)
	lea	$CA86,a0
	add.l	d7,a0
	move.w	#$4EB9,(a0)+		;jsr _hzset
	pea	(_hzset,pc)
	move.l	(a7)+,(a0)+
	move.w	#$601C,(a0)		;bra.b $CAAA
	rts

; The transform ($E32A) stores a slot's results only past its view checks, the first at
; $E50E, in the arrays $400, $600, $800, $A00, $C00, $E00 (a0 = the slot's offset). In a
; staged transform (_cowpt set) the slot's six longs are saved first, for _restore. Then
; the copy's $E50E-$E517: move.w d3,$E02(a0); sub.w $11EB4,d3 (the next instruction sets
; the flags again).
_tcow	move.l	a1,-(a7)
	lea	(_cowpt,pc),a1
	tst.l	(a1)
	beq.b	.o
	movea.l	(a1),a1
	move.l	a0,(a1)+
	move.l	($400,a0),(a1)+
	move.l	($600,a0),(a1)+
	move.l	($800,a0),(a1)+
	move.l	($A00,a0),(a1)+
	move.l	($C00,a0),(a1)+
	move.l	($E00,a0),(a1)+
	move.l	a1,-(a7)
	lea	(_cowpt,pc),a1
	move.l	(a7)+,(a1)
.o	movea.l	(a7)+,a1
	move.w	d3,($E02,a0)
	sub.w	$11EB4,d3
	rts

_hzset	move.l	a0,-(a7)
	move.l	(_hzslots,pc),a0
	move.l	a5,(a0)			;$CB0A
	move.l	a5,($CB16-$CB0A,a0)
	move.l	a5,($CB80-$CB0A,a0)
	move.l	a4,($CB0E-$CB0A,a0)
	move.l	a4,($CB1A-$CB0A,a0)
	move.l	a4,($CB84-$CB0A,a0)
	move.l	(a7)+,a0
	move.l	(_hzflush,pc),-(a7)
	rts

; 68020/030: clear the instruction cache (CACR bit 3). The 68030's data cache writes through.
_hzflush30
	move.l	d0,-(a7)
	dc.w	$4E7A,$0002		;movec cacr,d0
	bset	#3,d0
	dc.w	$4E7B,$0002		;movec d0,cacr
	move.l	(a7)+,d0
	rts

; 68040/060: push the slots' data cache lines to memory and invalidate them in both caches
_hzflush40
	move.l	a0,-(a7)
	move.l	(_hzslots,pc),a0
	dc.w	$F4E8			;cpushl bc,(a0): $CB00-$CB0F
	lea	($10,a0),a0
	dc.w	$F4E8			;$CB10-$CB1F
	lea	($CB80-$CB1A,a0),a0
	dc.w	$F4E8			;$CB80-$CB8F
	move.l	(a7)+,a0
	rts

_hzslots	dc.l	0		;the copy's $CB0A
_hzflush	dc.l	0		;_hzflush30 or _hzflush40

; Move the loop's calls into the copy, point the copy's main loop head ($DA30) at _eloop,
; and set up the page: the logic head, the marks, the save area.
_loopinstall
	lea	(_eloop,pc),a0
	lea	(_eloopend,pc),a1
.sc	move.w	(a0),d0
	cmp.w	#$4EB9,d0		;jsr abs.l
	beq.b	.op
	cmp.w	#$4EF9,d0		;jmp abs.l
	bne.b	.nx
.op	move.l	(2,a0),d0
	cmp.l	#COPY_LO,d0
	blo.b	.nx
	cmp.l	#COPY_HI,d0
	bhs.b	.nx
	add.l	d7,d0
	move.l	d0,(2,a0)
	addq.l	#4,a0
.nx	addq.l	#2,a0
	cmp.l	a1,a0
	blo.b	.sc
	lea	$DA30,a0
	add.l	d7,a0
	move.w	#$4EF9,(a0)+		;jmp _eloop
	pea	(_eloop,pc)
	move.l	(a7)+,(a0)
	bsr	_page
	move.w	#$4E75,(PG_HASH,a0)	;rts
	lea	(PG_HASH,a0),a1
	lea	(_hashpt,pc),a2
	move.l	a1,(a2)
	pea	(_mswap,pc)
	move.l	(a7)+,(PG_MSWAP,a0)
	pea	(_mgo,pc)
	move.l	(a7)+,(PG_MGO,a0)
	pea	(_prew,pc)
	move.l	(a7)+,(PG_PREW,a0)
	pea	(_prewe,pc)
	move.l	(a7)+,(PG_PREWE,a0)
	pea	(_kpre,pc)
	move.l	(a7)+,(PG_PRECLR,a0)
	pea	(_clear,pc)
	move.l	(a7)+,(PG_CLEAR,a0)
	pea	(_save,pc)
	move.l	(a7)+,(PG_STAGE,a0)
	lea	(PG_CAM,a0),a1
	lea	(_campt,pc),a2
	move.l	a1,(a2)
	lea	(PG_SORT,a0),a1
	lea	(_sortpt,pc),a2
	move.l	a1,(a2)
	add.l	#EXP_SAVE-EXP_PAGE,a0
	lea	(_savept,pc),a2
	move.l	a0,(a2)
	add.l	#EXP_PREV-EXP_SAVE,a0
	lea	(_prevpt,pc),a2
	move.l	a0,(a2)
	rts

;----------------------------------------------------------------------
; The Enhanced main loop, in place of 1.2's ($DA30-$DB0E). 1.2 runs, every frame (two fields
; at its cap): the draw, the frame end (screen swap, pacing to two fields since the last
; frame), the world (with the player stepped once per elapsed field), the transform and
; depth sort, the keys. Here the world (a logic frame) runs every second field as 1.2 runs
; it, and every field shows a frame:
; - the field after a logic frame shows a staged frame: the camera as it was after the
;   first of the logic frame's two player steps, the objects halfway between their
;   positions before and after the world step (_objstage). Everything the
;   transform, the sort and the draw write is saved before and restored after (_stab), so
;   the staged frame leaves no trace in the game's state;
; - the next field shows the committed frame: 1.2's draw of the same state.
; So the state at each logic head (PG_HASH) is 1.2's at $DA30, the screen shown there is
; 1.2's, and the world steps 25 times a second. The committed frame is part of the logic
; frame's work as far as the state goes (1.2's draw also steps animations), so it always
; runs; the staged frame is dropped when it would not end in its field (STAGEEND). Logic
; frames that fall more than a frame behind restart the schedule from now (the game slows,
; as 1.2 does).
; The first frame after (re)entry is 1.2's, with its own frame end ($DE3E): it paces from
; the last exit and sets the elapsed count the player steps use.
_eloop	lea	(_first,pc),a0
	st	(a0)
	lea	(_pclr,pc),a0
	clr.l	(a0)
.head	lea	(_first,pc),a0
	tst.b	(a0)
	beq.b	.run
	sf	(a0)
	moveq	#1,d0			;the dots in the buffers as 1.2 left them
	and.b	$11E67,d0
	add.w	d0,d0
	add.w	d0,d0
	lea	(_dots,pc),a0
	move.l	$A000,(a0,d0.w)		;the back buffer's: two draws ago
	eori.w	#4,d0
	move.l	$9FFC,(a0,d0.w)		;the front buffer's: the last draw
	bsr	_draw
	CALL	$DE3E
	lea	(_lpar,pc),a0
	move.b	$11E67,(a0)
	lea	(_lnom,pc),a0
	move.w	$11ECC,(a0)
	bra.w	.world
.run	lea	(_lline,pc),a0
	move.w	#STAGEEND,(a0)
	bsr	_since
	tst.w	d0
	bne.w	.late			;the logic frame ran into the next field
	bsr	_line			;will the staged frame end in this field?
	lea	(_lline,pc),a0
	move.w	d0,(a0)
	bsr	_est
	add.w	d1,d0
	cmp.w	#STAGEEND,d0
	bls.b	.stage
	lea	(_sdur,pc),a0		;no: and let an old long measurement fade
	move.w	(a0),d0
	lsr.w	#3,d0
	sub.w	d0,(a0)
	bra.w	.late
.stage	bsr	_clock
	lea	(_t0,pc),a0
	move.l	d0,(a0)
	bsr	_save
	bsr	_camstage
	bsr	_objstage
	bsr	_clock
	sub.l	(_t0,pc),d0
	lea	(_spd,pc),a0
	move.w	d0,(a0)			;the save and staging
	movea.l	#4,a1
	CALL	$E32A
	bsr	_cowend
	bsr	_sort
	bsr	_draw
	bsr	_clock
	lea	(_t1,pc),a0
	move.l	d0,(a0)
	bsr	_restore
	bsr	_objrestore
	bsr	_clock
	move.l	d0,d2
	sub.l	(_t1,pc),d2
	lea	(_spd,pc),a0
	add.w	d2,(a0)			;and the restore
	sub.l	(_t0,pc),d0
	sub.w	(_kin,pc),d0
	lea	(_sdur,pc),a0
	move.w	d0,(a0)
	bsr	_fend
.late	bsr	_clock			;the committed frame: the transform and sort
	lea	(_t1,pc),a0
	move.l	d0,(a0)
	movea.l	#4,a1
	CALL	$E32A
	bsr	_sort
	bsr	_clock
	sub.l	(_t1,pc),d0
	lea	(_tdur,pc),a0
	move.w	d0,(a0)
	bsr	_clock			;and 1.2's draw
	lea	(_t0,pc),a0
	move.l	d0,(a0)
	bsr	_draw
	bsr	_clock
	sub.l	(_t0,pc),d0
	sub.w	(_kin,pc),d0
	lea	(_cdur,pc),a0
	move.w	d0,(a0)
	bsr	_fend
.due	bsr	_since			;without a staged frame: wait for the logic frame
	cmp.w	#2,d0
	bhs.b	.logic
	bsr	_idle
	CALL	$E28C
	bra.b	.due
.logic	bsr	_lcount
; 1.2's $DA56-$DB0A
.world	move.l	(_hashpt,pc),a0
	jsr	(a0)			;the logic head: the state is 1.2's at $DA56
	lea	(_pvalid,pc),a0		;the objects before the world step, if this
	sf	(a0)			;logic frame's staged frame may run: as the
	bsr	_est			;last one, if it ended by the same line
	add.w	(_lline,pc),d1
	cmp.w	#STAGEEND,d1
	bhi.b	.ed
	bsr	_objsnap
.ed	CALL	$ED76
	CALL	$A1F6
	moveq	#2,d0
	tst.w	$11E06			;the attract demo: two steps
	bne.b	.n
	move.b	$11ECF,d0
	cmp.b	#3,d0
	blo.b	.n
	moveq	#3,d0
.n	move.b	d0,$DD9A
	lea	(_snap,pc),a0
	st	(a0)
.step	CALL	$A836
	CALL	$E7AA
	CALL	$FD26
	bne.b	.alive
	bsr	_sync
	GOTO	$DB12
.alive	lea	(_snap,pc),a0
	tst.b	(a0)
	beq.b	.ns
	sf	(a0)
	bsr	_camsnap
.ns	subq.b	#1,$DD9A
	bne.b	.step
	CALL	$A570
	CALL	$E29E
	CALL	$F0A6
	CALL	$CC2C
	movea.l	#$20,a0
	movea.l	#$40,a2
	CALL	$F2CA
	movea.l	#$1C0,a1
	movea.l	#$200,a2
	move.w	#$100,d0
	CALL	$EE86
	bcc.b	.c1
	bsr	_noclr
	CALL	$A006
.c1	movea.l	#4,a1
	movea.l	#8,a2
	move.w	#$180,d0
	CALL	$EE86
	bcc.b	.c2
	bsr	_noclr
	CALL	$A006
.c2	tst.w	$11ED2
	beq.b	.go
	bsr	_sync
	GOTO	$DBC2
.go	CALL	$C536			;(before the transform, which 1.2 runs first:
	bra.w	.head			;they share no data)

; 1.2's draw ($DA30-$DA4E). The radar dot ($9D10) is erased at the position it was drawn
; at two draws before ($A000), which is right while draws alternate between the buffers,
; as in 1.2. Here the committed frames all go to one buffer, the staged ones to the other:
; so the erase position is kept per buffer (_dots). $9D10 then moves $9FFC (the dot it
; drew last) to $A000 before anything reads it, so the state stays 1.2's.
_draw	moveq	#1,d0
	and.b	$11E67,d0		;the back buffer
	add.w	d0,d0
	add.w	d0,d0
	lea	(_dots,pc),a0
	move.l	(a0,d0.w),$A000
	move.l	d0,-(a7)
	bsr.b	.draw
	move.l	(a7)+,d0
	lea	(_dots,pc),a0
	move.l	$9FFC,(a0,d0.w)
	rts
.draw	bsr	_clear
	CALL	$D636
	CALL	$D374
	CALL	$10B48
	CALL	$CD14
	CALL	$DDC0
	CALL	$9D10
	CALL	$D362
	rts

; A presented frame's end: 1.2's frame end ($DE3E) without the frame counters, waiting for
; the next field only. The swap parity $11E67 picks the copper list and the next back buffer.
_fend	move.b	$11E67,d0
	eori.b	#1,d0
	move.b	d0,$11E67
	btst	#0,d0
	beq.b	.ev
	move.l	#$12370,$DFF080
	bra.b	_mswap
.ev	move.l	#$12324,$DFF080
_mswap	tst.w	$11E0C
	beq.b	.cp
	move.l	#$1256A,$124B6
	move.l	#$1255E,$124BE
	bra.b	.w
.cp	move.l	$124AE,$124B6
	move.l	$124B2,$124BE
.w	move.w	$11DEC,-(a7)
	bsr	_pre
	move.w	(a7)+,d0
	cmp.w	$11DEC,d0
	bne.b	_mgo			;the field ended in _pre: no more to wait for
	CALL	$E28C
_mgo	move.w	$11DEC,$11ECC
	rts

; The draw's clear: the rows the clear ahead left for this buffer, or all of them, timed
; (_kin). The registers are then $DF94's at its end.
_clear	move.l	$11E66,d0
	cmp.l	(_pclr,pc),d0
	beq.b	.part
	lea	(_prow,pc),a0
	clr.w	(a0)
.part	lea	(_pclr,pc),a0
	clr.l	(a0)
	bsr	_clock
	move.l	d0,-(a7)
	moveq	#0,d5			;to the end
	move.w	(_prow,pc),d0
	bne.b	.k
	bsr	_kall
	bra.b	.t
.k	bsr	_kclr
.t	bsr	_clock
	sub.l	(a7)+,d0
	lea	(_kin,pc),a0
	move.w	d0,(a0)
	movea.l	$11E66,a6
	lea	(3*$1F40+CROWS*40,a6),a6
	moveq	#-1,d0
	move.l	d0,d1
	move.l	d0,d2
	move.l	d0,d3
	move.l	d0,d4
	move.l	d0,d5
	move.l	d0,d6
	move.l	d0,d7
	movea.l	d0,a0
	movea.l	d0,a1
	movea.l	d0,a2
	movea.l	d0,a3
	movea.l	d0,a4
	movea.l	d0,a5
	rts

; At a presented frame's end, after the swap: the next back buffer ($11E66) is the one
; this field shows. Once the beam is past its view, clear it until the field's end.
_pre	bsr.b	_kset
	beq.b	_prex
	move.w	$11DEC,d4
_prew	move.l	$DFF004,d0		;the line, as _line
	lsr.l	#8,d0
	and.w	#$1FF,d0
	cmp.w	$11DEC,d4
	bne.b	_prex			;a new field: the wait is over
	cmp.w	#VIEWEND,d0
	blo.b	_prew
_prewe	move.w	#FIELDLAST,d5
	bra.b	_kpre
_prex	rts

; In a field the loop only waits through: the back buffer is not shown in it.
_idle	bsr.b	_kset
	beq.b	.x
	move.w	$11DEC,d4
	move.w	#FIELDLAST,d5
	bra.b	_kpre
.x	rts

; The clear ahead's buffer is the back buffer ($11E66); a new one starts at row 0. Z: it is
; clear already.
_kset	move.l	$11E66,d0
	lea	(_pclr,pc),a0
	cmp.l	(a0),d0
	beq.b	.s
	move.l	d0,(a0)
	lea	(_prow,pc),a0
	clr.w	(a0)
.s	move.w	(_prow,pc),d0
	sub.w	#CROWS,d0
	rts

_kpre	move.w	(_prow,pc),d0		;the clear ahead (tools/bench.py's mark): when
	sub.w	#CROWS,d0			;the rows left fit before line d5, no beam checks
	neg.w	d0
	mulu	(_kdur,pc),d0
	divu	#CROWS,d0
	move.w	d0,d1
	bsr	_line
	add.w	d1,d0
	cmp.w	d5,d0
	bhs.b	_kclr
	moveq	#0,d5
	move.w	(_prow,pc),d0
	beq.w	_kall

; Clear the back buffer's view ($11E66) as $DF94 does (planes 0-2 to 0, plane 3 to $FF,
; rows 0-135), from row _prow on, KROWS rows of the four planes at a time. d5 = 0: to the
; end; else stop before a chunk once the beam is at line d5 or the field ($11DEC) is no
; longer d4. Sets _prow to the rows done and, from a run of 40 rows or more, _kdur.
_kclr	bsr	_clock
	move.l	d0,-(a7)
	move.w	(_prow,pc),d6
	move.w	d6,-(a7)
	movea.l	$11E66,a5
.chunk	cmp.w	#CROWS,d6
	bhs.w	.end
	tst.w	d5
	beq.b	.go
	cmp.w	$11DEC,d4
	bne.w	.end
	move.l	$DFF004,d0
	lsr.l	#8,d0
	and.w	#$1FF,d0
	cmp.w	d5,d0
	bhs.w	.end
.go	move.w	d6,d0
	mulu	#40,d0
	lea	(a5,d0.l),a6		;the chunk in plane 0
	moveq	#2,d7
	moveq	#0,d0
.pl	bsr.b	.rows
	lea	($1F40,a6),a6
	dbf	d7,.pl
	moveq	#-1,d0
	bsr.b	.rows
	addq.w	#KROWS,d6
	bra.b	.chunk
.rows	move.l	d0,d1
	move.l	d0,d2
	move.l	d0,d3
	movea.l	d0,a0
	movea.l	d0,a1
	movea.l	d0,a2
	movea.l	d0,a3
N	SET	0
	REPT	KROWS*40/32
	movem.l	d0-d3/a0-a3,(N,a6)
N	SET	N+32
	ENDR
	rts
.end	lea	(_prow,pc),a0
	move.w	d6,(a0)
	sub.w	(a7)+,d6		;rows in this run
	bsr	_clock
	sub.l	(a7)+,d0		;lines
	cmp.w	#40,d6
	blo.b	.x
	mulu	#CROWS,d0
	divu	d6,d0
	lea	(_kdur,pc),a0
	move.w	d0,(a0)			;lines for all CROWS rows
.x	rts

; All of the back buffer's view at once: $DF94, timed into _kdur. It is faster than
; _kclr's chunks, which are for the clears that may stop.
_kall	bsr	_clock
	move.l	d0,-(a7)
	CALL	$DF94
	bsr	_clock
	sub.l	(a7)+,d0
	lea	(_kdur,pc),a0
	move.w	d0,(a0)
	lea	(_prow,pc),a0
	move.w	#CROWS,(a0)
	rts

; Something may write the screens outside the draw: no clear ahead counts
_noclr	lea	(_pclr,pc),a0
	clr.l	(a0)
	rts

; The depth sort $E724 on a copy in fast memory: the same selection sort (descending,
; unsigned) on the $11EA0 + 1 longs at $3A5C, which are then copied back; $E724 itself
; reads the chip list about n^2/2 times.
_sort	move.w	$11EA0,d7
	subq.w	#1,d7
	bmi.b	.x			;one entry or none
	lea	$3A5C,a2
	move.l	(_sortpt,pc),a1
	movea.l	a1,a3
	move.w	d7,d6
	addq.w	#1,d6
	move.w	d6,d5
.c	move.l	(a2)+,(a1)+
	dbf	d6,.c
	movea.l	a3,a1
.o	movea.l	a1,a0			;$E734-$E74A
	move.w	d7,d6
	move.l	(a0)+,d0
.i	cmp.l	(a0)+,d0
	bhs.b	.n
	move.l	-(a0),d1
	move.l	d0,(a0)+
	move.l	d1,d0
.n	dbf	d6,.i
	move.l	d0,(a1)+
	dbf	d7,.o
	lea	$3A5C,a2
.b	move.l	(a3)+,(a2)+
	dbf	d5,.b
.x	rts

; d0.w = the beam's line (0-312, PAL)
_line	move.l	$DFF004,d0		;VPOSR, VHPOSR
	lsr.l	#8,d0
	and.w	#$1FF,d0
	rts

; d0.l = lines since the field counter started (for durations)
_clock	bsr.b	_line
	moveq	#0,d1
	move.w	$11DEC,d1
	mulu	#313,d1
	add.l	d1,d0
	rts

; d1.w = the staged frame's expected length in lines (STAGEEND)
_est	move.w	(_cdur,pc),d1
	add.w	(_tdur,pc),d1
	add.w	(_spd,pc),d1
	move.w	(_sdur,pc),d2
	cmp.w	d1,d2
	bls.b	.e
	move.w	d2,d1
.e	move.l	$11E66,d2		;and the clear, less what ran ahead
	cmp.l	(_pclr,pc),d2
	bne.b	.k
	move.w	#CROWS,d2
	sub.w	(_prow,pc),d2
	mulu	(_kdur,pc),d2
	divu	#CROWS,d2
	add.w	d2,d1
	bra.b	.p
.k	add.w	(_kdur,pc),d1
.p	IFND MSHIFT
MSHIFT	= 4
	ENDC
	move.w	d1,d2
	lsr.w	#MSHIFT,d2
	add.w	d2,d1
	rts

; d0 = fields since the current logic frame's nominal start
_since	move.w	$11DEC,d0
	sub.w	(_lnom,pc),d0
	rts

; A logic frame starts: the next nominal start, and the counters 1.2's frame end keeps per
; frame: $11E36 on every second (the logical swap parity), the countdown $11E0C, the
; elapsed count (two fields).
_lcount	lea	(_lnom,pc),a0
	addq.w	#2,(a0)
	bsr.b	_since
	cmp.w	#2,d0
	blo.b	.t
	lea	(_lnom,pc),a0
	move.w	$11DEC,(a0)		;more than a frame behind: restart the schedule
.t	lea	(_lpar,pc),a0
	bchg	#0,(a0)
	bne.b	.e			;the parity is now even
	cmp.w	#$3C00,$11E36
	beq.b	.e
	addq.w	#1,$11E36
.e	tst.w	$11E0C
	beq.b	.d
	subq.w	#1,$11E0C
	bne.b	.d
	move.l	$124AE,$124B6
	move.l	$124B2,$124BE
.d	move.w	#2,$11ECE
	rts

; Leaving the loop: 1.2's code goes on from the logical parity (it counts $11E36 by it)
; and the next draw (into the back buffer) erases the dot that buffer shows.
_sync	bsr	_noclr
	move.b	(_lpar,pc),d0
	cmp.b	$11E67,d0
	beq.b	.s
	move.b	d0,$11E67
	btst	#0,d0
	beq.b	.e
	move.l	#$12370,$DFF080
	bra.b	.s
.e	move.l	#$12324,$DFF080
.s	moveq	#1,d0
	and.b	$11E67,d0
	add.w	d0,d0
	add.w	d0,d0
	lea	(_dots,pc),a0
	move.l	(a0,d0.w),$A000
	rts

_save	lea	(_stab,pc),a0
	move.l	(_savept,pc),a1
.r	move.l	(a0)+,d0
	beq.b	.d
	move.l	d0,a2
	move.w	(a0)+,d0
.c	move.l	(a2)+,(a1)+
	dbf	d0,.c
	bra.b	.r
; The background objects' animation: $10B48 walks the level's list ($10BAA; entries of a
; word n, 0 ends) and in an animated one (n < 0, 16 bytes) counts +2 down and steps the
; frame +14; a still one (n > 0) is 8 bytes. Those two words, with the entry's address.
.d	move.l	(_savept,pc),a1
	lea	(SV_ANIM,a1),a1
	movea.l	$10BAA,a0
.a	move.w	(a0),d0
	beq.b	.ae
	bpl.b	.st
	move.l	a0,(a1)+
	move.w	(2,a0),(a1)+
	move.w	(14,a0),(a1)+
	lea	(16,a0),a0
	bra.b	.a
.st	addq.l	#8,a0
	bra.b	.a
.ae	moveq	#-1,d0
	move.l	d0,(a1)
; and the transform's per-object arrays: _tcow saves the slots the staged transform writes
	move.l	(_savept,pc),a1
	lea	(SV_COW,a1),a1
	lea	(_cowpt,pc),a0
	move.l	a1,(a0)
	rts

; After the staged transform: close _tcow's list
_cowend	lea	(_cowpt,pc),a0
	move.l	(a0),a1
	clr.l	(a0)
	moveq	#-1,d0
	move.l	d0,(a1)
	rts

_restore
	lea	(_stab,pc),a0
	move.l	(_savept,pc),a1
.r	move.l	(a0)+,d0
	beq.b	.d
	move.l	d0,a2
	move.w	(a0)+,d0
.c	move.l	(a1)+,(a2)+
	dbf	d0,.c
	bra.b	.r
.d	move.l	(_savept,pc),a1
	lea	(SV_ANIM,a1),a1
.a	move.l	(a1)+,d0
	bmi.b	.ae
	movea.l	d0,a0
	move.w	(a1)+,(2,a0)
	move.w	(a1)+,(14,a0)
	bra.b	.a
.ae	move.l	(_savept,pc),a1
	lea	(SV_COW,a1),a1
.o	move.l	(a1)+,d0
	bmi.b	.oe
	movea.l	d0,a0
	move.l	(a1)+,($400,a0)
	move.l	(a1)+,($600,a0)
	move.l	(a1)+,($800,a0)
	move.l	(a1)+,($A00,a0)
	move.l	(a1)+,($C00,a0)
	move.l	(a1)+,($E00,a0)
	bra.b	.o
.oe	rts

; The camera: what the player steps ($E7AA) move and the transform and draw read
_camsnap
	move.l	(_campt,pc),a0
	move.l	$2790,(a0)+		;position
	move.l	$2B98,(a0)+
	move.l	$11EAE,(a0)+		;ground scroll
	move.w	$11EB2,(a0)+		;turn since the last draw (the horizon's)
	move.w	$11EB4,(a0)+		;heading
	move.w	$CCF8,(a0)
	rts

_camstage
	move.l	(_campt,pc),a0
	move.l	(a0)+,$2790
	move.l	(a0)+,$2B98
	move.l	(a0)+,$11EAE
	move.w	(a0)+,$11EB2
	move.w	(a0)+,$11EB4
	move.w	(a0),$CCF8
	rts

; The objects before the world step: x $2794, y $2998, z $2B9C (longs, slot n at + 4n, n =
; 0-127; slot -1 is the camera) and the lifetime $1CD2 (word; 0 is a free slot, $FFFF and
; $8000 do not count down). Free slots keep only their lifetime.
_objsnap
	move.l	(_prevpt,pc),a1
	lea	($200,a1),a2
	lea	($200,a2),a3
	lea	($200,a3),a4
	movea.w	#127*4,a0
.o	move.w	($1CD2,a0),d0
	move.w	d0,(0,a4,a0.w)
	beq.b	.n
	move.l	($2794,a0),(0,a1,a0.w)
	move.l	($2998,a0),(0,a2,a0.w)
	move.l	($2B9C,a0),(0,a3,a0.w)
.n	subq.w	#4,a0
	move.w	a0,d0
	bpl.b	.o
	lea	(_pvalid,pc),a0
	st	(a0)
	rts

; Every object halfway between its position before the world step and after it, except
; one that was free before, has a higher lifetime now (a slot used again: a new shot takes
; the oldest shot's slot) or moved OBJSNAP or more on an axis: it is drawn where it is now.
; Positions wrap at 2^28 (the transform uses the high word's low 12 bits). The slots it
; moves are listed with their positions (offset, x, y, z; -1 ends) for _objrestore.
; Without a snapshot (_pvalid) the objects stay where they are.
OBJSNAP	= $10000			;moves on the benchmark and in the demo: under $4000
HALF	MACRO				;array, prev base, half, list offset
	move.l	(\1,a0),\3
	move.l	\3,(\4,a5)
	sub.l	(0,\2,a0.w),\3
	asl.l	#4,\3
	asr.l	#4,\3
	move.l	\3,d0
	bpl.b	.p\@
	neg.l	d0
.p\@	cmp.l	d6,d0
	bhs.w	.n
	asr.l	#1,\3
	ENDM
_objstage
	move.l	(_prevpt,pc),a1
	lea	($200,a1),a2
	lea	($200,a2),a3
	lea	($200,a3),a4
	lea	($200,a4),a5
	move.b	(_pvalid,pc),d0
	beq.w	.e
	move.l	#OBJSNAP,d6
	movea.l	$11EA2,a0		;the last slot's offset
.o	move.w	($1CD2,a0),d0
	beq.w	.n			;free
	move.w	(0,a4,a0.w),d1
	beq.w	.n			;new
	cmp.w	d1,d0
	bhi.w	.n			;used again
	HALF	$2794,a1,d3,4
	HALF	$2998,a2,d4,8
	HALF	$2B9C,a3,d5,12
	move.l	d3,d0
	or.l	d4,d0
	or.l	d5,d0
	beq.b	.n			;not moving
	move.l	a0,(a5)
	move.l	(4,a5),d0
	sub.l	d3,d0
	move.l	d0,($2794,a0)
	move.l	(8,a5),d0
	sub.l	d4,d0
	move.l	d0,($2998,a0)
	move.l	(12,a5),d0
	sub.l	d5,d0
	move.l	d0,($2B9C,a0)
	lea	(16,a5),a5
.n	subq.w	#4,a0
	move.w	a0,d0
	bpl.w	.o
.e	moveq	#-1,d0
	move.l	d0,(a5)
	rts

_objrestore
	move.l	(_prevpt,pc),a1
	lea	($800,a1),a1
.r	move.l	(a1)+,d0
	bmi.b	.d
	movea.l	d0,a0
	move.l	(a1)+,($2794,a0)
	move.l	(a1)+,($2998,a0)
	move.l	(a1)+,($2B9C,a0)
	bra.b	.r
.d	rts
_eloopend

; AGA: the bitplanes fetched 64 bits wide (FMODE 3), a quarter of the chip slots. The
; screens ($68000, $78000, planes $1F40 apart, 40-byte rows) are 8-byte aligned. The two
; copper lists are the only ones the game loads and nothing rewrites their fetch window.
; AGA is told by Lisa's id in DENISEID ($F8), not by the ChipRevBits, which come from the
; Kickstart's graphics.library and lack the AGA bits under a Kickstart for an ECS machine.
_fmode	moveq	#0,d0
	IFND NOFMODE
	move.w	$DFF07C,d1
	cmp.b	#$F8,d1
	bne.b	.w
	move.w	#DDFA,$1233E
	move.w	#DDFB,$12342
	move.w	#DDFA,$12382
	move.w	#DDFB,$12386
	moveq	#3,d0
	ENDC
.w	move.w	d0,$DFF1FC
	rts

; What the transform ($E32A), the sort ($E724) and the draw write, and the camera: chip
; address, longs - 1. The interrupt writes none of it (tools/dataflow.py).
_stab	dc.l	$1000			;the horizon's tables
	dc.w	($1200-$1000)/4-1
	dc.l	$2790
	dc.w	0
	dc.l	$2B98
	dc.w	0
	dc.l	$3A5C			;the visible list, the sort's lists
	dc.w	($3C60-$3A5C)/4-1
	dc.l	$9FFC			;$9D10's
	dc.w	1
	dc.l	$CCF6
	dc.w	0
	dc.l	$11E18
	dc.w	0
	dc.l	$11EA0			;the transform's and the horizon's variables, the camera
	dc.w	($11ECC-$11EA0)/4-1
	dc.l	0
STABLONGS	= ($1200-$1000)/4+1+1+($3C60-$3A5C)/4+2+1+1+($11ECC-$11EA0)/4
	IFGT	STABLONGS*4-SV_ANIM
	FAIL	"SV_ANIM too low"
	ENDC
	IFGT	SV_ANIM+($11228-$10D08)/16*8+4-SV_COW
	FAIL	"SV_COW too low"
	ENDC
	IFGT	SV_COW+128*28+4-SAVESIZE
	FAIL	"SAVESIZE too small"
	ENDC

_hashpt		dc.l	0		;the page's PG_HASH
_savept		dc.l	0		;EXP_SAVE
_campt		dc.l	0		;the page's PG_CAM
_sortpt		dc.l	0		;the page's PG_SORT
_cowpt		dc.l	0		;_tcow's next slot in EXP_SAVE while a staged transform runs
_prevpt		dc.l	0		;EXP_PREV
_lnom		dc.w	0		;the current logic frame's nominal start ($11DEC)
_dots		dc.l	0,0		;the radar dot drawn last into $68000, $78000
_t0		dc.l	0		;_clock at the committed draw's start
_t1		dc.l	0
_tdur		dc.w	0		;the logic frame's transform and sort, in lines
_spd		dc.w	64		;the last staged frame's save, staging and restore
_cdur		dc.w	312		;the last committed draw's length in lines
_sdur		dc.w	0		;the last staged frame's (fading while none runs)
_first		dc.b	0		;the next frame is the first after (re)entry
_lpar		dc.b	0		;the logical swap parity (one toggle per logic frame)
_snap		dc.b	0		;snapshot the camera after this player step
_pvalid		dc.b	0		;_objsnap ran for this logic frame
_lline		dc.w	0		;the line the last logic frame ended at (STAGEEND: late)
_pclr		dc.l	0		;the back buffer the clear ran ahead for, or 0
_kdur		dc.w	60		;a whole clear's length in lines
_prow		dc.w	0		;the rows of _pclr's buffer cleared
_kin		dc.w	0		;the clear's lines inside the current draw
	even

	IFD VERIFY
; Trap any execution of the chip program's reached instructions (an `illegal` over each,
; from the build's codebits.i): the trap stores the PC at PG_TRAP and loops at
; PG_TRAPLOOP, where tools/route.py's hash step has a breakpoint. Fill the rest of the
; page up to the stack's top with GUARD.
_verifyinit
	bsr	_page
	clr.l	(PG_TRAP,a0)
	move.w	#$60FE,(PG_TRAPLOOP,a0)	;bra.s *
	lea	(PG_GUARD,a0),a0
	move.w	#(PG_STACKTOP-PG_GUARD)/4-1,d0
.g	move.l	#GUARD,(a0)+
	dbf	d0,.g
	lea	(_codebits,pc),a0
	lea	COPY_LO,a1
	move.w	#(COPY_HI-COPY_LO)/16-1,d0
.byte	move.b	(a0)+,d1
	moveq	#7,d2
.bit	add.b	d1,d1
	bcc.b	.nb
	move.w	#$4AFC,(a1)		;illegal
.nb	addq.l	#2,a1
	dbf	d2,.bit
	dbf	d0,.byte
	pea	(_vtrap,pc)
	move.l	(a7)+,$10.w
	rts

_vtrap	move.l	a0,-(a7)
	bsr	_page
	move.l	(6,a7),(PG_TRAP,a0)
	lea	(PG_TRAPLOOP,a0),a0
	move.l	a0,(6,a7)
	move.l	(a7)+,a0
	rte

	INCLUDE	codebits.i
	ENDC

	INCLUDE	relocs.i

_tag		dc.l	WHDLTAG_CUSTOM1_GET
_custom1	dc.l	0
		dc.l	WHDLTAG_BUTTONWAIT_GET
_buttonwait	dc.l	0
		dc.l	WHDLTAG_ATTNFLAGS_GET
		dc.w	0
_attn		dc.w	0
	IFD VERIFY
		dc.l	WHDLTAG_CUSTOM2_GET
_custom2	dc.l	0
	ENDC
		dc.l	0
_enhanced	dc.l	0

	dc.b	"$VER: Encounter.slave 2.0b (12.11.2026)",0
	even
