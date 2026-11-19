***************************************************************************
*             /                                                           *
*       _____.__ _                                         .___.          *
*      /    /_____________.  _________.__________.________ |   |________  *
*  ___/____      /    ____|_/         |         /|        \|   ._      /  *
*  \     \/      \    \     \    /    |    :___/¯|    \    \   |/     /   *
*   \_____________\___/_____/___/_____|____|     |____|\_____________/    *
*     -========================/===========|______\================-      *
*                                                                         *
*   .---.----(*(       ARCHIPELAGOS WHDLOAD SLAVE           )*)---.---.   *
*   `-./                                                           \.-'   *
*                                                                         *
*                         (c)oded by StingRay                             *
*                         --------------------                            *
*                             December 2015                               *
*                                                                         *
*                                                                         *
***************************************************************************

***********************************
*** History			***
***********************************

; 19-Nov-2026	- on a 68020 or better the far objects no longer flicker: the
;		  cells between the far rows, which no row crosses, are searched
;		  for objects too, up to the game's object limit (Vesuri)

; 18-Nov-2026	- game time no longer follows the frame rate: the renderer's
;		  steps, moves and two effects advance with the fields their frames
;		  take, at most a step every 6 fields (timing.s; Vesuri)
;		- the level 3 handler's self-modifying jsr goes through a
;		  variable, and the instruction cache is on (Vesuri)
;		- the swap's bitplane pointers are written with interrupts off and
;		  never while the copper loads them; on a 68020 or better the
;		  frame no longer waits for a field before the swap (Vesuri)
;		- on a 68020 or better with fast memory (optional ExpMem) the
;		  program and its stack run there; what DMA reads stays in
;		  chip memory (Vesuri)
;		- on a 68020 or better the ground's two plane fills and the sky
;		  fill run from a blit queue while the CPU draws the ground, the
;		  CPU clears the border, and the CPU's polls leave the objects'
;		  blits every cycle (BLITHOG) (Vesuri)
;		- with the body in fast memory the title's pre-scaler reads and
;		  writes fast copies, then copies each object to chip (Vesuri)
;		- on a 68020 or better the ground's rows are built in registers
;		  and written a long at a time, and the far rows' spans go from
;		  carry to carry instead of a pixel at a time (Vesuri)
;		- the instruction cache, fast memory and the 68020 patches only
;		  with CUSTOM1 (Enhanced framerate; ws_version 17) (Vesuri)

; 31-Aug-2023	- WaitRaster waits for the start of a frame (VPOSR V8 set, then
;		  clear) instead of line 303, which NTSC never reaches
;		  (reconstructed from the shipped v1.2 slave, which has no source)

; 20-Dec-2015	- changed the patch to use real files

; 19-Dec-2015	- DMA wait in replayer fixed

; 18-Dec-2015	- load/save support for both versions implemented

; 17-Dec-2015	- load/save support added
;		- CPU dependent delay in text writer fixed

; 16-Dec-2015	- work started


	INCDIR	SOURCES:INCLUDE/
	INCLUDE	WHDLoad.i
	

FLAGS		= WHDLF_NoError|WHDLF_ClearMem|WHDLF_EmulTrap
QUITKEY		= $59		; F10
EXPSIZE		= $16000	; the program body (up to $146a0) and a stack below the top
;DEBUG

; absolute skip
PL_SA	MACRO
	PL_S	\1,\2-(\1)
	ENDM

; jsr+absolute skip
PL_PSA	MACRO
	PL_PS	\1,\2		; could use PSS here but it fills memory
	PL_S	\1+6,\3-(\1+6)	; with NOPS so we use standard skip
	ENDM


HEADER	SLAVE_HEADER		; ws_security + ws_ID
	dc.w	17		; ws_version
	dc.w	FLAGS		; flags
	dc.l	524288		; ws_BaseMemSize
	dc.l	0		; ws_ExecInstall
	dc.w	Patch-HEADER	; ws_GameLoader
	dc.w	.dir-HEADER	; ws_CurrentDir
	dc.w	0		; ws_DontCache
	dc.b	0		; ws_KeyDebug
	dc.b	QUITKEY		; ws_KeyExit
	dc.l	-EXPSIZE	; ws_ExpMem: optional, the program and its stack
	dc.w	.name-HEADER	; ws_name
	dc.w	.copy-HEADER	; ws_copy
	dc.w	.info-HEADER	; ws_info

; v16
	dc.w	0		; ws_kickname
	dc.l	0		; ws_kicksize
	dc.w	0		; ws_kickcrc

; v17
	dc.w	.config-HEADER	; ws_config


.config	dc.b	"C1:B:Enhanced framerate",0

.dir	IFD	DEBUG
	dc.b	"SOURCES:WHD_Slaves/Archipelagos/"
	ENDC
	dc.b	"data",0

.name	dc.b	"Archipelagos",0
.copy	dc.b	"1989 Astral Software",0
.info	dc.b	"installed by StingRay/[S]carab^Scoopex",10
	IFD	DEBUG
	dc.b	"DEBUG!!! "
	ENDC
	dc.b	"enhanced by Vesuri",10
	dc.b	"Version 2.0b (18.11.2026)",0
	dc.b	"$VER: Archipelagos.slave 2.0b (18.11.2026)",0
Name	dc.b	"Archipelagos_"
Num	dc.b	"03FC00",0
	CNOP	0,2


TAGLIST		dc.l	WHDLTAG_ATTNFLAGS_GET
CPUFLAGS	dc.l	0
		dc.l	WHDLTAG_CUSTOM1_GET
Enhanced	dc.l	0		; Enhanced framerate: the 68020 patches and caches
		dc.l	TAG_END

resload	dc.l	0

Patch	lea	resload(pc),a1
	move.l	a0,(a1)
	move.l	a0,a2

	lea	TAGLIST(pc),a0
	jsr	resload_Control(a2)
	move.l	Enhanced(pc),d0		; Enhanced framerate off: as on a 68000
	bne.b	.enh
	lea	CPUFLAGS(pc),a0
	clr.l	(a0)
.enh


; install keyboard irq
	bsr	SetLev2IRQ

	lea	$800.w,a7

; load game
	lea	Name(pc),a0
	lea	$2000.w,a1
	move.l	a1,a5
	jsr	resload_LoadFileDecrunch(a2)
	move.l	a5,a0
	jsr	resload_CRC16(a2)
	lea	PLGAME(pc),a3
	lea	GT627(pc),a4
	move.l	#$ce94,d4		; the level 3 handler's jsr target
	lea	PLFAST(pc),a6
	lea	CHIP627(pc),a0
	cmpi.w	#$55bf,d0		; SPS 627 (cmpi: the shipped slave's encoding)
	beq.b	.ok
	lea	PLGAME_US(pc),a3
	lea	GT628(pc),a4
	move.l	#$cec0,d4
	lea	PLFAST_US(pc),a6
	lea	CHIP628(pc),a0
	cmpi.w	#$f600,d0		; SPS 628 (cmpi: the shipped slave's encoding)
	beq.b	.ok

.wrongver
	pea	(TDREASON_WRONGVER).w
	bra.w	EXIT

.ok	lea	Chip(pc),a1
	move.l	a0,(a1)
	lea	BackOff(pc),a1		; SPS 627: the back buffer's pointer, the
	move.l	#$1286a,(a1)+		; level 3 handler past its first two
	move.l	#$ce24,(a1)		; instructions
	cmpi.l	#$ce94,d4
	beq.b	.v627
	move.l	#$ce50,(a1)
	move.l	#$12c0e,-(a1)
.v627
	lea	PS627(pc),a0		; the pre-scaler's offsets
	cmpi.l	#$ce94,d4
	beq.b	.p627
	lea	PS628(pc),a0
.p627	lea	PSVer(pc),a1
	move.l	a0,(a1)
	lea	SD627(pc),a0		; the span drawer's
	cmpi.l	#$ce94,d4
	beq.b	.s627
	lea	SD628(pc),a0
.s627	lea	SDVer(pc),a1
	move.l	a0,(a1)
	lea	t_table(pc),a0
	move.l	a4,(a0)

; a 68020 or better with ExpMem in fast memory: the body goes there
	moveq	#0,d0
	move.l	CPUFLAGS(pc),d1
	btst	#AFB_68020,d1
	beq.b	.chip
	move.l	HEADER+ws_ExpMem(pc),d1
	cmpi.l	#$200000,d1		; none, or chip memory
	bcs.b	.chip
	cmpi.l	#$c00000,d1		; slow memory, on the chip bus
	bcs.b	.exp
	cmpi.l	#$e00000,d1
	bcs.b	.chip
.exp	move.l	d1,d0
	subi.l	#$2000+$1c,d0
.chip	lea	FastDelta(pc),a1
	move.l	d0,(a1)

; relocate Atari-ST binary
	move.l	a5,a0
	move.l	a0,a1
	move.l	a0,d3
	add.l	2(a1),a0
	add.w	#$1C,a1
	add.w	#$1C,a0
	addi.l	#$1C,d3	; immediate form as the shipped slave has it: vasm encodes op #,Dn as the Dn form
	move.l	(a0)+,d0
	add.l	d0,a1
	bsr	Reloc
.reloc	moveq	#0,d2
	move.b	(a0)+,d2
	beq.b	.done
	cmpi.b	#1,d2	; immediate form as the shipped slave has it: vasm encodes op #,Dn as the Dn form
	bne.b	.normal
	add.w	#$FE,a1
	bra.b	.reloc

.normal	add.l	d2,a1
	bsr	Reloc
	bra.b	.reloc

.done
	lea	L3Vec(pc),a0		; the jsr's first target, relocated
	move.l	$1c(a5,d4.l),(a0)

; patch
	add.w	#$1c,a5			; skip ST header
	move.l	a3,a0
	move.l	a5,a1
	jsr	resload_Patch(a2)

; a 68020 or better: no field wait before the swap
	move.l	CPUFLAGS(pc),d0
	btst	#AFB_68020,d0
	beq.b	.slow
	move.l	a6,a0
	move.l	a5,a1
	jsr	resload_Patch(a2)
.slow

; the fast copy: the relocated and patched body (the chip copy has the fast
; memory patches too, so the two are the same); the slave's absolute
; addresses into it follow
	move.l	FastDelta(pc),d0
	beq.b	.nocopy
	lea	PLFASTMEM(pc),a0
	cmpi.l	#$ce94,d4
	beq.b	.fm
	lea	PLFASTMEM_US(pc),a0
.fm	move.l	a5,a1
	jsr	resload_Patch(a2)
	move.l	FastDelta(pc),d0
	move.l	a5,a0
	lea	(a5,d0.l),a1
	move.l	-$1c+2(a5),d1		; the text size
	lsr.l	#2,d1
.copy	move.l	(a0)+,(a1)+
	subq.l	#1,d1
	bpl.b	.copy
	add.l	d0,a5
	move.l	t_table(pc),a0
	moveq	#13-1,d1		; GT627/GT628 entries
.gt	add.l	d0,(a0)+
	dbf	d1,.gt
	lea	GameBody(pc),a0
	add.l	d0,(a0)
	jsr	resload_FlushCache(a2)
.nocopy

; the instruction cache for BaseMem and ExpMem, no data cache (it would make
; the screens data-cacheable where WHDLoad uses the MMU). BaseMem stays
; cacheable: without the MMU one noncacheable area turns both caches off.
	move.l	Enhanced(pc),d0		; off: WHDLoad's caches, as before
	beq.b	.nocpu
	move.l	#WCPUF_Base_WT|WCPUF_Exp_CB|WCPUF_IC,d0
	move.l	#WCPUF_Base|WCPUF_Exp|WCPUF_IC|WCPUF_DC,d1
	jsr	resload_SetCPU(a2)
.nocpu

; for the tools: the running body's address in the ST header's reserved long,
; which nothing reads after the relocation
	move.l	GameBody(pc),$2000+$12.w

; the stack at ExpMem's top
	move.l	FastDelta(pc),d0
	beq.b	.go
	move.l	HEADER+ws_ExpMem(pc),a7
	add.l	#EXPSIZE,a7
.go


; and start
	lea	$dff000,a6
	jmp	(a5)



QUIT	pea	(TDREASON_OK).w
EXIT	move.l	resload(pc),a2
	bsr.b	KillSys
	jmp	resload_Abort(a2)


KillSys	move.w	#$7fff,$dff09a
	bsr	WaitRaster
	move.w	#$7ff,$dff096
	move.w	#$7fff,$dff09c
	rts

AckVBI	move.w	#1<<4+1<<5+1<<6,$dff09c
	move.w	#1<<4+1<<5+1<<6,$dff09c
	rts

; The level 3 handler called the pointer or the pan routine with a jsr whose
; target the game rewrote, which an instruction cache would miss. The writes
; now go to L3Vec, and the jsr comes here.
L3Jump	move.l	L3Vec(pc),-(a7)
	rts

L3Vec	dc.l	0

; A relocation: the long at (a1) is an offset into the body. The chip
; copy's address for one in a CHIP block (Chip, ending with -1), the fast
; copy's otherwise (FastDelta, 0 without fast memory). d3 is the chip body.
Reloc	movem.l	d0-d1/a0,-(a7)
	move.l	(a1),d0
	move.l	Chip(pc),a0
.next	move.l	(a0)+,d1
	bmi.b	.fast
	cmp.l	d1,d0
	bcs.b	.skip
	cmp.l	(a0),d0
	bcs.b	.chip
.skip	addq.l	#4,a0
	bra.b	.next
.fast	add.l	FastDelta(pc),d0
.chip	add.l	d3,d0
	move.l	d0,(a1)
	movem.l	(a7)+,d0-d1/a0
	rts

Chip		dc.l	0		; CHIP627 or CHIP628
FastDelta	dc.l	0		; the fast body minus the chip body
GameBody	dc.l	$2000+$1c	; the body the game runs

; What stays in chip memory, as body offsets: from offset 0 the replayer,
; which addresses its data and samples pc-relative, with the samples and
; data up to the boot code; the sprites; the copper lists (the sky's five
; at $906a-$9976, which the level 3 handler takes in turn every 4096 fields,
; and the screen's); the blitter's
; shape tables; a buffer the blitter reads. Every DMA read of the body on
; every screen is in one of them. Nothing outside a block refers into it
; pc-relative but the five lea of PLFASTMEM, nor the other way round.
CHIP627	dc.l	$0,$8d2a,$8f50,$8f9c,$8ffa,$99ac
	dc.l	$b004,$b0a4,$b2cc,$b7ec,$14076,$140f8,-1
CHIP628	dc.l	$0,$8d2a,$8f50,$8f9c,$8ffa,$99ac
	dc.l	$b010,$b0b0,$b2da,$b7fa,$1441a,$1449c,-1

; The blitter's sources, which the game takes pc-relative: the chip copy.
BlitA627
	lea	$2000+$1c+$b004,a3
	lea	$2000+$1c+$b7cc,a2
	rts
BlitB627
	lea	$2000+$1c+$b2cc,a3
	lea	$2000+$1c+$b7cc,a2
	rts
BlitC627
	lea	$2000+$1c+$14076,a2
	movea.l	GameBody(pc),a0
	adda.l	#$1286a,a0
	movea.l	(a0),a0			; the back buffer
	rts
BlitA628
	lea	$2000+$1c+$b010,a3
	lea	$2000+$1c+$b7da,a2
	rts
BlitB628
	lea	$2000+$1c+$b2da,a3
	lea	$2000+$1c+$b7da,a2
	rts
BlitC628
	lea	$2000+$1c+$1441a,a2
	movea.l	GameBody(pc),a0
	adda.l	#$12c0e,a0
	movea.l	(a0),a0			; the back buffer
	rts

; The swap writes the five bitplane pointers into the copper list's first
; moves, which the copper reads at the start of each frame. A write while it
; reads them would show one frame with planes from both buffers. The game
; turned off only VERTB; all interrupts are off now, from before the beam
; check to after the writes. The writes wait out the copper's lines (0-2)
; and a frame's last three (310-312 PAL, 260-262 NTSC; 260-262 wait on PAL
; too). The beam position is read twice so that a line change between
; VPOSR and VHPOSR is not taken for a line.
SwapOff	lea	IntEna(pc),a2
	move.w	$dff01c,(a2)
	move.w	#$4000,$dff09a
.beam	move.l	$dff004,d0
	move.l	$dff004,d1
	eor.l	d0,d1
	andi.l	#$1ff00,d1
	bne.b	.beam
	lsr.l	#8,d0
	andi.w	#$1ff,d0
	cmpi.w	#3,d0
	bcs.b	.beam
	cmpi.w	#260,d0
	bcs.b	.ok
	cmpi.w	#263,d0
	bcs.b	.beam
	cmpi.w	#310,d0
	bcc.b	.beam
.ok	move.w	#$0020,$dff09a		; the game's own write
	rts

SwapOn	move.w	#$8020,$dff09a		; the game's own write
	move.w	IntEna(pc),d0
	andi.w	#$4000,d0
	beq.b	.off
	move.w	#$c000,$dff09a
.off	rts

IntEna	dc.w	0

AckLev6	move.w	#1<<13,$dff09c
	move.w	#1<<13,$dff09c
	rte


; The blit queue (68020 or better). Draw view starts with two plane fills
; of the ground and the sky fill after it has five, all with the CPU
; waiting for the blitter: 120 lines a frame on the a1200-030. They go into
; a queue now, at the start of draw view, and run from the blitter
; interrupt while the CPU draws the ground (lines 113-179, planes 0-2; the
; fills are the ground's planes 3-4 and the sky, lines 20-112). The game's
; blitter wait, which every blit of the game calls first, waits for the
; queue as well, so every other blit runs after it, as before. An entry:
; BLTSIZE (0 ends the list), BLTDMOD, BLTADAT, and BLTDPT as an offset into
; the back buffer; BLTCON0 $01f0 (D = A), BLTCON1 0, both masks $ffff, as
; the game sets them.
QTab	dc.w	$10d0,8,$ffff
	dc.l	3*8000+113*40+4		; the ground, planes 3 and 4
	dc.w	$10d0,8,0
	dc.l	4*8000+113*40+4
	dc.w	$1750,8,$ffff
	dc.l	20*40+4			; the sky, planes 0-4
	dc.w	$1750,8,0
	dc.l	1*8000+20*40+4
	dc.w	$1750,8,0
	dc.l	2*8000+20*40+4
	dc.w	$1750,8,0
	dc.l	3*8000+20*40+4
	dc.w	$1750,8,0
	dc.l	4*8000+20*40+4
	dc.w	0

QPtr	dc.l	0			; the entry running, 0 when idle
Hog	dc.b	0			; the objects: BLITHOG in the wait
	even
QBase	dc.l	0			; the back buffer
BackOff	dc.l	0			; the back buffer's pointer (body offset)
L3Rest	dc.l	0			; the level 3 handler's third instruction

; a0: the back buffer
Back	movea.l	GameBody(pc),a0
	adda.l	BackOff(pc),a0
	movea.l	(a0),a0
	rts

; draw view's start: the queue's fills, then the registers as the game's
; two blits left a0 and a1
QView	bsr	Back
	lea	QBase(pc),a1
	move.l	a0,(a1)
	bsr	BWait			; the blitter idle
	lea	QTab(pc),a0
	lea	QPtr(pc),a1
	move.l	a0,(a1)
	move.w	#$0040,$dff09c		; an earlier blit's BLIT request
	move.w	#$0040,$dff09c
	bsr	QStart
	move.w	#$8040,$dff09a		; BLIT on
	movea.l	QBase(pc),a0
	adda.l	#4*8000+113*40+4,a0
	lea	$dff000,a1
	rts

; the sky fill: queued already. The objects follow, and the CPU only polls
; while their blits run: BLITHOG then (BWait) keeps the CPU's DMACONR reads
; from taking every fourth cycle of a four-channel blit.
QSky	move.l	a0,-(a7)
	lea	Hog(pc),a0
	st	(a0)
	move.l	(a7)+,a0
	bsr	Back
	adda.l	#4*8000+20*40+4,a0
	lea	$dff000,a1
	rts

; a0: the entry to start, the blitter idle
QStart	movem.l	d0/a1,-(a7)
	lea	$dff000,a1
	move.w	#$01f0,$40(a1)
	clr.w	$42(a1)
	moveq	#-1,d0
	move.l	d0,$44(a1)
	move.w	2(a0),$66(a1)
	move.w	4(a0),$74(a1)
	move.l	6(a0),d0
	add.l	QBase(pc),d0
	move.l	d0,$54(a1)
	move.w	(a0),$58(a1)
	movem.l	(a7)+,d0/a1
	rts

; the running entry is done: the next, or BLIT off
QNext	movem.l	d0/a0-a1,-(a7)
	move.w	#$0040,$dff09c
	move.w	#$0040,$dff09c
	lea	QPtr(pc),a1
	move.l	(a1),d0
	beq.b	.done
	movea.l	d0,a0
	lea	10(a0),a0
	tst.w	(a0)
	beq.b	.idle
	move.l	a0,(a1)
	bsr	QStart
	bra.b	.done
.idle	clr.l	(a1)
	move.w	#$0040,$dff09a		; BLIT off
.done	movem.l	(a7)+,d0/a0-a1
	rts

; The game's blitter wait: the queue empty, then the blitter idle. It
; runs the queue itself when the interrupt cannot (a wait with the level 3
; interrupt masked, a BLIT request taken by another handler). Flags and d0
; as the game's wait leaves them.
BWait	move.l	a0,-(a7)
	lea	QPtr(pc),a0
	tst.l	(a0)
	beq.b	.blit
.q	btst	#6,$dff01f		; INTREQR: BLIT, not yet taken
	beq.b	.more
	move.w	#$0040,$dff09a		; the interrupt off, then look again
	btst	#6,$dff01f
	beq.b	.on
	bsr	QNext
.on	tst.l	(a0)
	beq.b	.blit
	move.w	#$8040,$dff09a
.more	tst.l	(a0)
	bne.b	.q
.blit	tst.b	$dff002
	tst.b	Hog-QPtr(a0)
	movea.l	(a7)+,a0		; flags kept
	beq.b	.wait
	btst	#6,$dff002
	beq.b	.idle
	move.w	#$8400,$dff096		; BLITHOG while the CPU only polls
.hog	btst	#6,$dff002
	bne.b	.hog
	move.w	#$0400,$dff096
	bra.b	.idle
.wait	btst	#6,$dff002
	bne.b	.wait
.idle	tst.w	d0
	rts

; The level 3 handler's start: a queued blit done, the next one. The rest
; is the game's, which now leaves BLIT alone (AckVB).
L3Blit	movem.l	d0-a6,-(a7)
	lea	$dff000,a0
	move.w	$1c(a0),d0
	and.w	$1e(a0),d0
	btst	#6,d0
	beq.b	.game
	bsr	QNext
.game	movea.l	GameBody(pc),a1
	adda.l	L3Rest(pc),a1
	jmp	(a1)

AckVB	move.w	#1<<4+1<<5,$dff09c
	move.w	#1<<4+1<<5,$dff09c
	rts

; The border clear (68020 or better): five planes of bytes 36-43 of lines
; 20-179 (the right border and the next line's left), which the objects'
; blits overrun. The game blitted them after the objects with the CPU
; waiting; the CPU writes them now, after the objects' last blit, and
; leaves the blitter's registers, a0 and a1 as the game's last blit did.
CBorder	movem.l	d0-d2,-(a7)
	bsr	Back
	lea	20*40+36(a0),a0
	bsr	BWait
	lea	Hog(pc),a1
	sf	(a1)
	moveq	#0,d0
	moveq	#5-1,d2
.plane	move.w	#160-1,d1
.line	move.l	d0,(a0)
	move.l	d0,4(a0)
	lea	40(a0),a0
	dbf	d1,.line
	lea	8000-160*40(a0),a0
	dbf	d2,.plane
	lea	$dff000,a1
	move.w	#$01f0,$40(a1)
	clr.w	$42(a1)
	moveq	#-1,d1
	move.l	d1,$44(a1)
	move.w	#32,$66(a1)
	clr.w	$74(a1)
	lea	-8000(a0),a0		; plane 4's start
	lea	160*40(a0),a1
	move.l	a1,$dff054		; where the game's blit ended
	lea	$dff000,a1
	movem.l	(a7)+,d0-d2
	rts


; The span drawer (68020 or better), called for each row of the ground,
; 67 a frame, bottom to top: the row's span list ($13c26; an entry is a
; span's end x, 0 ending the list, and its map cell), and the row's start in
; the back buffer (a6, long-aligned; 256 pixels, planes 0-2). The game
; called a routine for each word, with the colour (the cell's terrain type,
; plane k bit k), and read-modify-wrote each span's first word in chip
; memory. A span runs from the last one's end (0 for the first) to its own,
; and the last one to the row's end; a span from s writes its colour from s
; to its last word's end, and later spans write over what follows. So a row
; depends on its list alone: here each 32 pixels of the three planes are
; built in registers and written once, 24 long writes a row. A cell with an
; object is noted as the game does (the list at $12f26, its length at
; $1288e, where the row at $12890 is no further than the one at $12892) and
; its map bit cleared. a0, a2 and a6 as the game left them.
; body offsets: the span list, the row, the object limit, the object list's
; length, the object list; the cell's x step (a byte) and y step (a word
; after it), the far rows' list end; the row records (GapFill)
SD627	dc.l	$13c26,$12890,$12892,$1288e,$12f26,$129ba,$11e2c,$12fa6
SD628	dc.l	$13fca,$12c34,$12c36,$12c32,$132ca,$12d5e,$120e4,$1334a
SDVer	dc.l	0

; A span from d3 to d4 (d3 <= d4 <= 256) in a terrain type's colour, planes
; 0, 1 and 2 (\1, \2, \3): the long being built (d0-d2) from d3 on, then
; whole longs, then the next long started. What lies beyond d4 in a long, a
; later span writes. a4: the next long to write.
SDPAINT	MACRO
	cmp.w	d4,d3
	bcc.b	.r\@
	moveq	#-1,d5
	move.w	d3,d6
	andi.w	#31,d6
	lsr.l	d6,d5			; d5: from d3 to the long's end
	IFEQ	(\1)*(\2)*(\3)
	move.l	d5,d6
	not.l	d6
	ENDC
	IFNE	\1
	or.l	d5,d0
	ELSE
	and.l	d6,d0
	ENDC
	IFNE	\2
	or.l	d5,d1
	ELSE
	and.l	d6,d1
	ENDC
	IFNE	\3
	or.l	d5,d2
	ELSE
	and.l	d6,d2
	ENDC
	move.w	d3,d7
	ori.w	#31,d7
	addq.w	#1,d7			; d7: the next long's start
	cmp.w	d7,d4
	bcs.b	.r\@			; d4 inside this long
	move.l	d1,8000(a4)
	move.l	d2,16000(a4)
	move.l	d0,(a4)+
	moveq	#-(\1),d0		; whole longs, and the one d4 is in
	moveq	#-(\2),d1
	moveq	#-(\3),d2
.w\@	addi.w	#32,d7
	cmp.w	d4,d7
	bhi.b	.r\@
	move.l	d1,8000(a4)
	move.l	d2,16000(a4)
	move.l	d0,(a4)+
	bra.b	.w\@
.r\@	rts
	ENDM

SpanD	clr.w	(a5)+			; the list's end, as the game's
	movem.l	a0/a2/a6,-(a7)
	movea.l	SDVer(pc),a1
	movea.l	GameBody(pc),a5
	adda.l	(a1),a5
.skip	tst.w	(a5)			; spans ending at 0
	bne.b	.go
	addq.l	#4,a5
	bra.b	.skip
.go	movea.l	a6,a4			; a4: the next long to write
	moveq	#0,d3			; d3: the span's start
	movea.w	#-1,a1			; a1: its type times 2, none yet
.ent	move.w	(a5)+,d4		; d4: its end
	beq.b	.last
	move.w	(a5)+,d6		; d6: its cell
	move.b	(a3,d6.w),d7
	bpl.b	.col
	movem.l	d0-d1/a2,-(a7)		; an object
	movea.l	SDVer(pc),a1
	movea.l	GameBody(pc),a2
	move.l	4(a1),d1
	move.w	(a2,d1.l),d0
	move.l	8(a1),d1
	cmp.w	(a2,d1.l),d0
	bgt.b	.noob
	bclr	#7,(a3,d6.w)
	move.l	12(a1),d1
	move.w	(a2,d1.l),d0
	addq.w	#2,(a2,d1.l)
	adda.l	16(a1),a2
	move.w	d6,(a2,d0.w)
.noob	movem.l	(a7)+,d0-d1/a2
.col	andi.w	#7,d7
	add.w	d7,d7
	movea.w	d7,a1
	move.w	.pt(pc,d7.w),d7
	jsr	.pt(pc,d7.w)
	move.w	d4,d3
	bra.b	.ent
.last	move.w	a1,d7
	bmi.b	.done			; an empty list: nothing, as the game's
	move.w	#256,d4
	move.w	.pt(pc,d7.w),d7
	jsr	.pt(pc,d7.w)
.done	movem.l	(a7)+,a0/a2/a6
	rts

.pt	dc.w	.p0-.pt,.p1-.pt,.p2-.pt,.p3-.pt,.p4-.pt,.p5-.pt,.p6-.pt,.p7-.pt
.p0	SDPAINT	0,0,0
.p1	SDPAINT	1,0,0
.p2	SDPAINT	0,1,0
.p3	SDPAINT	1,1,0
.p4	SDPAINT	0,0,1
.p5	SDPAINT	1,0,1
.p6	SDPAINT	0,1,1
.p7	SDPAINT	1,1,1

; A far row's spans (68020 or better; the rows beyond the 45th from the
; bottom, where the cells are small; the nearer rows go by division). The game steps
; x a pixel at a time to the row's end (x a byte, d2's low byte), adding d0
; to d6 and d1 to d5: each carry ends a span at x with the cell in d4
; (d6's first, then d5's), and steps the cell in x (a byte) or y. 256 steps
; a row, most of them without a carry. Here each accumulator's carries are
; worked out: the first (65535 - acc) / step + 1 steps on; after a carry
; the accumulator is below the step, so the next comes q = 65536 / step
; steps on, or q + 1 if the accumulator is below r = 65536 - q * step, and
; leaves it r less (plus the step). The spans in the game's order, then the
; game's list end. An x is kept with d2's high byte, as the list has it.
FarRow	movem.l	a0-a4/a6,-(a7)
	movea.l	SDVer(pc),a1
	move.l	24(a1),-(a7)		; the game's list end
	movea.l	GameBody(pc),a6
	move.l	a6,d3
	add.l	d3,(a7)
	adda.l	20(a1),a6		; a6: the x step (a byte), the y step
	moveq	#0,d3
	move.w	d2,d3
	movea.l	d3,a1			; a1: d6's next carry, an x
	movea.l	d3,a2			; a2: d5's
	move.b	#255,d3
	movea.l	d3,a0			; a0: the row's last x
; the first carries
	moveq	#0,d3
	not.w	d3
	sub.w	d6,d3
	divu.w	d0,d3
	swap	d3
	clr.w	d3
	swap	d3
	addq.l	#1,d3
	adda.l	d3,a1
	mulu.w	d0,d3
	add.w	d3,d6
	moveq	#0,d3
	not.w	d3
	sub.w	d5,d3
	divu.w	d1,d3
	swap	d3
	clr.w	d3
	swap	d3
	addq.l	#1,d3
	adda.l	d3,a2
	mulu.w	d1,d3
	add.w	d3,d5
; q and r: a3 and d3 for d6, a4 and d7 for d5
	move.w	d1,d2
	bsr.b	.qr
	movea.l	d2,a4
	move.w	d3,d7
	move.w	d0,d2
	bsr.b	.qr
	movea.l	d2,a3
.next	cmpa.l	a2,a1
	bhi.b	.e5
	cmpa.l	a0,a1
	bhi.b	.done
	move.w	a1,(a5)+
	move.w	d4,(a5)+
	add.b	(a6),d4
	adda.l	a3,a1
	cmp.w	d3,d6
	bcc.b	.q6
	addq.l	#1,a1
	add.w	d0,d6
.q6	sub.w	d3,d6
	bra.b	.next
.e5	cmpa.l	a0,a2
	bhi.b	.done
	move.w	a2,(a5)+
	move.w	d4,(a5)+
	add.w	2(a6),d4
	adda.l	a4,a2
	cmp.w	d7,d5
	bcc.b	.q5
	addq.l	#1,a2
	add.w	d1,d5
.q5	sub.w	d7,d5
	bra.b	.next
.done	move.l	(a7)+,d3
	movem.l	(a7)+,a0-a4/a6
	move.l	d3,-(a7)
	rts

; d2.w: a step; out d2.l = 65536 / step, d3.w = the remainder
.qr	cmpi.w	#1,d2
	bne.b	.div
	move.l	#$10000,d2
	moveq	#0,d3
	rts
.div	move.l	#$10000,d3
	divu.w	d2,d3
	moveq	#0,d2
	move.w	d3,d2
	swap	d3
	rts

; The objects between the rows (68020 or better). The game notes an object
; only in a cell a row's spans cross, and the far rows, a screen line each,
; lie more than a cell apart: at 8 frames a second the objects there came
; and went with the view now and then, at 50 they flicker. Before each row
; up to the object limit, lines parallel to the row and the last one, at
; most a cell apart, cross the gap between them, and each object cell they
; meet is noted as the row would (the list's order is near to far: these go
; before the row's own, the last line the farthest). The row records (8
; bytes a row, 2 a row index): the right end's x and y and the vector to
; the left end, 8.8 (a cell is a byte of each, y's the cell's high byte).
; At most GFMAX bytes of the list (64 cells long) are filled this way.
GFMAX	= 96

; The rows lie farther apart the farther they are, so a row within a cell
; of the last means every nearer one is too: GFFirst is the nearest row
; that may have a gap, raised past each row found without one, and
; lowered by two rows a frame (at row 0) in case the spacing changes.
GFRowA	dc.l	0			; the row's address
GFFirst	dc.w	0

SpanG	move.l	GFRowA(pc),d0
	beq.b	.init
.go	movea.l	d0,a1
	move.w	(a1),d7			; d7: the row
	beq.b	.frame
	cmp.w	GFFirst(pc),d7
	bcs.w	SpanD			; nearer: no gap
	bsr.b	GapFill
	bra.w	SpanD
.frame	lea	GFFirst(pc),a1
	subq.w	#4,(a1)
	bcc.w	SpanD
	clr.w	(a1)
	bra.w	SpanD
.init	movea.l	SDVer(pc),a1
	move.l	4(a1),d0
	add.l	GameBody(pc),d0
	lea	GFRowA(pc),a1
	move.l	d0,(a1)
	bra.b	.go

; d7: the row (2 or more); a3: the map's middle, as the span drawer has
; it. a0, a2, a5 and a6 kept; the span drawer, which follows, takes no
; others.
GapFill	movea.l	SDVer(pc),a1
	movea.l	GameBody(pc),a4
	move.l	8(a1),d0
	cmp.w	(a4,d0.l),d7
	bgt.w	.out			; beyond the limit, as the game's
	move.l	28(a1),d0
	adda.l	d0,a4
	move.w	d7,d0
	ext.l	d0
	lsl.l	#2,d0
	adda.l	d0,a4
	subq.l	#8,a4			; a4: the last row's record, this one's 8 on
; the gap: the right end moves along its ray, 32 degrees off the view, so
; the rows lie |move| cos 32 apart; lines at most a cell apart need k gaps,
; the least k with |move|^2 / 8 <= k^2 * 11125 (65536 / 8 / cos^2 32 is
; 11391). |x| + |y| <= 256 is within a cell.
	move.w	8(a4),d0
	sub.w	(a4),d0			; the right end's move
	move.w	10(a4),d1
	sub.w	2(a4),d1
	move.w	d0,d2
	bpl.b	.ax
	neg.w	d2
.ax	move.w	d1,d3
	bpl.b	.ay
	neg.w	d3
.ay	add.w	d3,d2
	cmpi.w	#256,d2
	bls.b	.none
	muls.w	d0,d0
	muls.w	d1,d1
	add.l	d1,d0
	lsr.l	#3,d0
	cmpi.l	#11125,d0
	bhi.b	.gap
.none	addq.w	#2,d7			; within a cell: the rows meet every cell
	lea	GFFirst(pc),a1
	cmp.w	(a1),d7
	bls.b	.nr
	move.w	d7,(a1)
.nr	rts
.gap	moveq	#2,d1
.kl	move.w	d1,d2
	mulu.w	d2,d2
	mulu.w	#11125,d2
	cmp.l	d2,d0
	bls.b	.kd
	addq.w	#1,d1
	cmpi.w	#16,d1
	bcs.b	.kl
.kd	movem.l	a0/a2/a5/a6,-(a7)
	movea.l	GameBody(pc),a2
	move.l	12(a1),d0
	lea	(a2,d0.l),a6		; a6: the list's length
	move.l	16(a1),d0
	lea	(a2,d0.l),a5		; a5: the list
	move.w	d1,d0
.k	movea.w	d0,a1			; a1: the gaps
	movea.w	#1,a0			; a0: the line, near to far
; each of x, y, dx, dy: the last row's plus (this row's minus the last's)
; times the line over the gaps, or half of it for one line
GFLERP	MACRO
	move.w	8+\1(a4),\2
	sub.w	\1(a4),\2
	IFEQ	\3
	muls.w	d6,\2
	divs.w	d5,\2
	ELSE
	asr.w	#1,\2
	ENDC
	add.w	\1(a4),\2
	ENDM
.line	move.w	a0,d6
	move.w	a1,d5
	cmpi.w	#2,d5
	beq.b	.half
	GFLERP	0,d0,0
	GFLERP	2,d1,0
	GFLERP	4,d2,0
	GFLERP	6,d3,0
	bra.b	.walk
.half	GFLERP	0,d0,1
	GFLERP	2,d1,1
	GFLERP	4,d2,1
	GFLERP	6,d3,1
.walk	bsr.w	GFLine
	addq.w	#1,a0
	cmpa.w	a1,a0
	bcs.w	.line
	movem.l	(a7)+,a0/a2/a5/a6
.out	rts

; A line from x, y (d0, d1) by dx, dy (d2, d3): every cell it crosses, in
; order, its object noted. Each step is to the next cell in x or in y,
; whichever boundary the line meets first: e = bx * ay - by * ax (b the way
; to the next boundary, a the line's length, each axis) is below 0 when it
; is x's. d0-d7 and a2 used.
GFLine	move.w	d1,d4
	move.w	d0,d5
	lsr.w	#8,d5
	move.b	d5,d4
	move.w	d4,-(a7)		; the first cell
	move.w	#$100,d7		; d7: the y step
	moveq	#0,d5
	move.b	d1,d5
	tst.w	d3
	bmi.b	.yn
	neg.w	d5
	addi.w	#256,d5			; d5: by
	move.w	d3,d1
	sub.w	d5,d1
	addi.w	#256,d1
	bra.b	.yd
.yn	neg.w	d3			; d3: ay
	neg.w	d7
	move.w	d3,d1
	sub.w	d5,d1
	addi.w	#255,d1
.yd	lsr.w	#8,d1			; d1: the steps in y
	moveq	#1,d6			; d6: the x step
	moveq	#0,d4
	move.b	d0,d4
	tst.w	d2
	bmi.b	.xn
	neg.w	d4
	addi.w	#256,d4			; d4: bx
	move.w	d2,d0
	sub.w	d4,d0
	addi.w	#256,d0
	bra.b	.xd
.xn	neg.w	d2			; d2: ax
	moveq	#-1,d6
	move.w	d2,d0
	sub.w	d4,d0
	addi.w	#255,d0
.xd	lsr.w	#8,d0			; d0: the steps in x
	mulu.w	d3,d4
	mulu.w	d2,d5
	sub.l	d5,d4			; d4: e
	andi.l	#$ffff,d3
	lsl.l	#8,d3			; an x step adds 256 ay
	andi.l	#$ffff,d2
	lsl.l	#8,d2			; a y step takes 256 ax
	move.w	(a7)+,d5		; d5: the cell
.cell	tst.b	(a3,d5.w)
	bpl.b	.next
	movea.w	(a6),a2
	cmpa.w	#GFMAX,a2
	bcc.b	.next
	bclr	#7,(a3,d5.w)
	move.w	d5,(a5,a2.w)
	addq.w	#2,(a6)
.next	tst.w	d0
	beq.b	.y
	tst.w	d1
	beq.b	.x
	tst.l	d4
	bpl.b	.y
.x	add.b	d6,d5
	add.l	d3,d4
	subq.w	#1,d0
	bra.b	.cell
.y	tst.w	d1
	beq.b	.end
	add.w	d7,d5
	sub.l	d2,d4
	subq.w	#1,d1
	bra.b	.cell
.end	rts

; The pre-scaler (the title's PLEASE WAIT, the body in fast memory). Once
; at boot the game scales each of 36 objects (48x48, in the ST picture at
; $70000) to 15 sizes, a pixel at a time, into the blitter's object buffer
; ($193b8-$5c780, chip): per pixel four word reads of the source and a
; read-modify-write of five destination planes, all in chip memory. The
; game's own scaler still draws every pixel, but from a fast copy of the
; object's source rows into a fast scratch buffer, which is then copied to
; the object's place in chip memory. The scratch is the fast copy's
; replayer area, which only the chip copy runs (body offsets $1000 and
; $3000). Everything the routine leaves (the size table's pointers, the
; stride, the object counter, the objects' offset table) as the game's.
PSD	= $1000			; the scratch: an object's 15 sizes (stride bytes)
PSS	= $3000			; the scratch: an object's 48 source rows, 160 apart

; body offsets: the size table (15 entries of 20 bytes), the stride, the
; object counter, the objects' offset table, the scaler, the source's size,
; the source offset table
PS627	dc.l	$d1b2,$cf0a,$12e62,$d122,$c724,$cf0e,$d3f6
PS628	dc.l	$d1de,$cf36,$13206,$d14e,$c750,$cf3a,$d422
PSVer	dc.l	0

FScale	movem.l	d0-a6,-(a7)
	movea.l	PSVer(pc),a3
	movea.l	GameBody(pc),a4
	movea.l	(a3),a0			; the size table's chip pointers,
	adda.l	a4,a0			; as the game sets them
	movea.l	#$193b8,a1
	moveq	#15-1,d1
.ptr	move.l	a1,6(a0)
	move.w	(a0),d0
	move.w	4(a0),d2
	move.w	d2,d3
	mulu.w	d0,d2
	adda.l	d2,a1
	move.l	a1,10(a0)
	asr.w	#2,d3
	mulu.w	d0,d3
	adda.l	d3,a1
	lea	20(a0),a0
	dbf	d1,.ptr
	move.l	a1,d5
	subi.l	#$193b8,d5		; d5: the stride
	move.l	4(a3),d0
	move.l	d5,(a4,d0.l)
	moveq	#36-1,d7
.obj	move.l	8(a3),d0
	moveq	#0,d6
	move.w	(a4,d0.l),d6		; d6: the object
; its source rows to the fast scratch
	move.l	24(a3),d0
	add.l	a4,d0
	movea.l	d0,a0
	move.l	d6,d0
	lsl.l	#2,d0
	move.l	(a0,d0.l),d0
	addi.l	#$70000,d0
	movea.l	d0,a0
	lea	PSS(a4),a1
	move.l	20(a3),d0
	move.w	(a4,d0.l),d1		; the source's size (48)
	subq.w	#1,d1
.row	movem.l	(a0),d0/d2-d4/a5-a6	; 48 pixels, four planes
	movem.l	d0/d2-d4/a5-a6,(a1)
	lea	160(a0),a0
	lea	160(a1),a1
	dbf	d1,.row
; the size table's pointers moved by d4 = the scratch minus the object's
; place, which the scaler adds back (stride times the object)
	move.l	d5,d4
	mulu.w	d6,d4
	neg.l	d4
	addi.l	#-$193b8+PSD,d4
	add.l	a4,d4
	bsr	.move
; the scratch cleared, the object's 15 sizes scaled into it
	lea	PSD(a4),a0
	move.l	d5,d0
	lsr.l	#1,d0
	subq.l	#1,d0
.clr	clr.w	(a0)+
	subq.l	#1,d0
	bpl.b	.clr
	movea.l	(a3),a0
	adda.l	a4,a0
	moveq	#15-1,d1
.size	movem.l	d1/d4-d7/a0/a3-a4,-(a7)
	movea.l	16(a3),a1
	jsr	(a4,a1.l)
	movem.l	(a7)+,d1/d4-d7/a0/a3-a4
	lea	20(a0),a0
	dbf	d1,.size
	neg.l	d4
	bsr	.move
; the scratch to the object's place in chip memory
	lea	PSD(a4),a0
	move.l	d5,d0
	mulu.w	d6,d0
	addi.l	#$193b8,d0
	movea.l	d0,a1
	move.l	d5,d0
	move.l	a1,d1
	btst	#1,d1			; long writes, long-aligned
	beq.b	.al
	move.w	(a0)+,(a1)+
	subq.l	#2,d0
.al	move.l	d0,d1
	lsr.l	#2,d1
	bra.b	.cpe
.cp	move.l	(a0)+,(a1)+
.cpe	subq.l	#1,d1
	bpl.b	.cp
	btst	#1,d0
	beq.b	.next
	move.w	(a0)+,(a1)+
.next	move.l	8(a3),d0
	addq.w	#1,(a4,d0.l)
	dbf	d7,.obj
; the objects' offset table
	move.l	12(a3),d0
	lea	(a4,d0.l),a0
	moveq	#0,d0
	moveq	#36-1,d1
.off	move.l	d0,(a0)+
	add.l	d5,d0
	dbf	d1,.off
	movem.l	(a7)+,d0-a6
	rts

; the size table's pointers plus d4
.move	movea.l	(a3),a0
	adda.l	a4,a0
	moveq	#15-1,d1
.mv	add.l	d4,6(a0)
	add.l	d4,10(a0)
	lea	20(a0),a0
	dbf	d1,.mv
	rts

; the scaler's source: the fast copy of the object's rows
FSrc	move.l	GameBody(pc),d6
	addi.l	#PSS,d6
	rts


; SPS 627, 68020 or better
PLFAST	PL_START
	PL_S	$1185c,6		; no field wait before the swap
	PL_P	$11efa,BWait		; the blitter wait waits for the queue too
	PL_PS	$11b72,QView		; the ground's and the sky's fills queued
	PL_SA	$11b78,$11bce
	PL_P	$ae32,QSky
	PL_P	$b7f0,CBorder		; the border cleared by the CPU
	PL_P	$ce1a,L3Blit		; the level 3 handler runs the queue
	PL_PS	$cea2,AckVB
	PL_P	$11e52,SpanG		; the objects between the rows, the span drawer
	PL_P	$11e0e,FarRow		; the far rows' spans, carry to carry
	PL_END

; SPS 628, 68020 or better
PLFAST_US
	PL_START
	PL_S	$11b14,6		; no field wait before the swap
	PL_P	$121b2,BWait
	PL_PS	$11e2a,QView
	PL_SA	$11e30,$11e86
	PL_P	$ae3e,QSky
	PL_P	$b7fe,CBorder
	PL_P	$ce46,L3Blit
	PL_PS	$cece,AckVB
	PL_P	$1210a,SpanG
	PL_P	$120c6,FarRow
	PL_END

; SPS 627, the body in fast memory
PLFASTMEM	PL_START
	PL_PSS	$aefa,BlitA627,2
	PL_PSS	$b10e,BlitB627,2
	PL_PSS	$c8d8,BlitC627,2
	PL_P	$c636,FScale		; the pre-scaler, from fast copies
	PL_PS	$c77a,FSrc
	PL_END

; SPS 628, the body in fast memory
PLFASTMEM_US
	PL_START
	PL_PSS	$af06,BlitA628,2
	PL_PSS	$b11c,BlitB628,2
	PL_PSS	$c904,BlitC628,2
	PL_P	$c662,FScale
	PL_PS	$c7a6,FSrc
	PL_END

; SPS 627
PLGAME	PL_START
	PL_P	$8e68,AckLev1
	PL_PSS	$8d44,.setkbd,4
	PL_PS	$cea2,AckVBI
	PL_P	$8e72,AckLev5
	PL_P	$8e7c,AckLev6
	PL_SA	$8d6c,$8d76		; don't modify level 7 interrupt vector
	PL_R	$a2c8			; disable loader init
	PL_R	$a4da			; disable "drive on"
	PL_PSA	$9fd2,load,$a03e
	PL_R	$a47a			; disable "drive off"
	PL_R	$12240			; disable protection track check
	PL_SA	$11512,$117cc		; skip complete manual protection
	PL_R	$e4b8			; end level 2 interrupt code
	PL_PSS	$c4aa,delay10000,2	; fix CPU dependent delay in writer
	PL_P	$1118,FixDMAWait	; fix DMA wait in replayer
	PL_PSS	$1098c,SaveGame,2

	PL_PSA	$11ac6,t_steps,$11ae6	; game time: the renderer's steps,
	PL_P	$11fa8,t_move		; moves,
	PL_PSS	$cd4e,t_pace,2		; the six-frame effect,
	PL_PSS	$c5f2,t_pacedraw,6	; the two ramps
	PL_PSS	$c60e,t_pacedraw,6
	PL_P	$12220,t_swapend	; the swap measures each frame

	PL_PS	$ce92,L3Jump		; the level 3 handler's jsr, through L3Vec
	PL_PA	$e494,L3Vec		; and its four writes
	PL_PA	$10bba,L3Vec
	PL_PA	$11884,L3Vec
	PL_PA	$118b4,L3Vec
	PL_PSS	$12334,SwapOff,2	; the swap's copper list writes
	PL_PSS	$1238c,SwapOn,2
	PL_END



.setkbd	lea	.kbdcust(pc),a0
	move.l	a0,KbdCust-.kbdcust(a0)
	rts

.kbdcust
	move.b	RawKey(pc),d0
	movea.l	GameBody(pc),a0
	adda.l	#$e33c,a0
	move.b	d0,(a0)
	jmp	$e37e-$e33c(a0)
	

load	move.l	(a0)+,d0		; offset
	move.l	(a0)+,a1		; destination
;	move.l	(a0)+,d1		; length

; build file name
	bsr.b	CreateFileName

	lea	Name(pc),a0
	move.l	resload(pc),a2
	jmp	resload_LoadFileDecrunch(a2)


CreateFileName
	move.l	d0,d2
	lea	Num+6(pc),a0
	moveq	#6/2-1,d4
.cloop	move.b	d2,d3
	bsr.b	.conv2
	move.b	d2,d3
	lsr.b	#4,d3
	bsr.b	.conv2
	lsr.l	#8,d2
	dbf	d4,.cloop
	rts

.conv2	andi.b	#$f,d3	; immediate form as the shipped slave has it: vasm encodes op #,Dn as the Dn form
	cmpi.b	#9,d3
	ble.b	.ok
	addq.b	#7,d3
.ok	addi.b	#"0",d3
	move.b	d3,-(a0)
	rts



; US version (SPS 628)
PLGAME_US
	PL_START
	PL_P	$8e68,AckLev1
	PL_PSS	$8d44,.setkbd,4
	PL_PS	$cece,AckVBI
	PL_P	$8e72,AckLev5
	PL_P	$8e7c,AckLev6
	PL_SA	$8d6c,$8d76		; don't modify level 7 interrupt vector
	PL_R	$a2d4			; disable loader init
	PL_R	$a4e6			; disable "drive on"
	PL_PSA	$9fde,load,$a04a
	PL_R	$a486			; disable "drive off"
	PL_R	$124f8			; disable protection track check
	PL_SA	$1175a,$11a82		; skip complete manual protection
	PL_R	$e50c			; end level 2 interrupt code
	PL_PSS	$c4bc,delay10000,2	; fix CPU dependent delay in writer
	PL_P	$1118,FixDMAWait	; fix DMA wait in replayer
	PL_PS	$125ce,.intro		; exit "Fanfare intro" with LMB

	PL_P	$9e60,SaveGame

	PL_PSA	$11d7e,t_steps,$11d9e	; game time: the renderer's steps,
	PL_P	$12260,t_move		; moves,
	PL_PSS	$cd7a,t_pace,2		; the six-frame effect,
	PL_PSS	$c61e,t_pacedraw,6	; the two ramps
	PL_PSS	$c63a,t_pacedraw,6
	PL_P	$124d8,t_swapend	; the swap measures each frame

	PL_PS	$cebe,L3Jump		; the level 3 handler's jsr, through L3Vec
	PL_PA	$e4e8,L3Vec		; and its four writes
	PL_PA	$10c9e,L3Vec
	PL_PA	$11b3c,L3Vec
	PL_PA	$11b6c,L3Vec
	PL_PSS	$126d8,SwapOff,2	; the swap's copper list writes
	PL_PSS	$12730,SwapOn,2
	PL_END

; add LMB check to "Fanfare intro"
.intro	move.l	GameBody(pc),d0
	addi.l	#$1264c,d0
	btst	#6,$bfe001
	bne.b	.noquit
	moveq	#0,d2
.noquit	rts
	

.setkbd	lea	.kbdcust(pc),a0
	move.l	a0,KbdCust-.kbdcust(a0)
	rts

.kbdcust
	move.b	RawKey(pc),d0
	movea.l	GameBody(pc),a0
	adda.l	#$e390,a0
	move.b	d0,(a0)
	jmp	$e3d2-$e390(a0)


SaveGame
	move.l	a0,-(a7)

	move.l	#76*512*10,d0
	bsr	CreateFileName
	
	move.l	(a7)+,a1
	lea	Name(pc),a0
	move.l	#512,d0
	move.l	resload(pc),a2
	jmp	resload_SaveFile(a2)




AckLev1	move.w	#7,$dff09c
	move.w	#7,$dff09c
	rte

AckLev5	move.w	#$1800,$dff09c
	move.w	#$1800,$dff09c
	rte

WaitRaster
.wait	btst	#0,$dff005
	beq.b	.wait
.wait2	btst	#0,$dff005
	bne.b	.wait2
	rts


delay10000
	move.w	#10000/(34*5),d5
.loop	bsr.b	FixDMAWait
	dbf	d5,.loop
	rts

FixDMAWait
	movem.l	d0/d1,-(a7)
	moveq	#5-1,d1	
.loop	move.b	$dff006,d0
.wait	cmp.b	$dff006,d0
	beq.b	.wait
	dbf	d1,.loop
	movem.l	(a7)+,d0/d1
	rts

	INCLUDE	timing.s

***********************************
*** Level 2 IRQ			***
***********************************

SetLev2IRQ
	pea	.int(pc)
	move.l	(a7)+,$68.w

	move.b	#1<<7|1<<3,$bfed01		; enable keyboard interrupts
	tst.b	$bfed01				; clear all CIA A interrupts
	and.b	#~(1<<6),$bfee01		; set input mode

	move.w	#1<<3,$dff09c			; clear ports interrupt
	move.w	#1<<15|1<<14|1<<3,$dff09a	; and enable it
	rts

.int	movem.l	d0-d1/a0-a2,-(a7)
	lea	$dff000,a0
	lea	$bfe001,a1


	btst	#3,$1e+1(a0)			; PORTS irq?
	beq.w	.end

	btst	#3,$d00(a1)			; KBD irq?
	beq.b	.end

	moveq	#0,d0
	move.b	$c00(a1),d0
	lea	Key(pc),a2
	move.b	d0,(a2)+
	not.b	d0
	ror.b	d0
	move.b	d0,(a2)

	move.l	KbdCust(pc),d1
	beq.b	.nocustom
	movem.l	d0-a6,-(a7)
	move.l	d1,a0
	jsr	(a0)
	movem.l	(a7)+,d0-a6
.nocustom	
	


	or.b	#1<<6,$e00(a1)			; set output mode



	cmp.b	HEADER+ws_keydebug(pc),d0	
	bne.b	.nodebug
	movem.l	(a7)+,d0-d1/a0-a2
	move.w	(a7),6(a7)			; sr
	move.l	2(a7),(a7)			; pc
	clr.w	4(a7)				; ext.l sr
	bra.b	.debug


.nodebug
	cmp.b	HEADER+ws_keyexit(pc),d0
	beq.b	.exit
	

.nokeys	moveq	#3-1,d1
.loop	move.b	$6(a0),d0
.wait	cmp.b	$6(a0),d0
	beq.b	.wait
	dbf	d1,.loop


	and.b	#~(1<<6),$e00(a1)	; set input mode
.end	move.w	#1<<3,$9c(a0)
	move.w	#1<<3,$9c(a0)		; twice to avoid a4k hw bug
	movem.l	(a7)+,d0-d1/a0-a2
	rte

.debug	pea	(TDREASON_DEBUG).w
	bra.w	EXIT

.exit	bra.w	QUIT


Key	dc.b	0
RawKey	dc.b	0
KbdCust	dc.l	0			; ptr to custom routine


