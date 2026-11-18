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

; 18-Nov-2026	- game time no longer follows the frame rate: the renderer's
;		  steps, moves and two effects advance with the fields their frames
;		  take, at most a step every 6 fields (timing.s; Vesuri)
;		- the level 3 handler's self-modifying jsr goes through a
;		  variable, and the instruction cache is on (Vesuri)
;		- the swap's bitplane pointers are written with interrupts off and
;		  never while the copper loads them; on a 68020 or better the
;		  frame no longer waits for a field before the swap (Vesuri)

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
	dc.w	10		; ws_version
	dc.w	FLAGS		; flags
	dc.l	524288		; ws_BaseMemSize
	dc.l	0		; ws_ExecInstall
	dc.w	Patch-HEADER	; ws_GameLoader
	dc.w	.dir-HEADER	; ws_CurrentDir
	dc.w	0		; ws_DontCache
	dc.b	0		; ws_KeyDebug
	dc.b	QUITKEY		; ws_KeyExit
	dc.l	0		; ws_ExpMem
	dc.w	.name-HEADER	; ws_name
	dc.w	.copy-HEADER	; ws_copy
	dc.w	.info-HEADER	; ws_info

; v16
	dc.w	0		; ws_kickname
	dc.l	0		; ws_kicksize
	dc.w	0		; ws_kickcrc

; v17
	dc.w	.config-HEADER	; ws_config


.config	dc.b	0

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
		dc.l	TAG_END

resload	dc.l	0

Patch	lea	resload(pc),a1
	move.l	a0,(a1)
	move.l	a0,a2

	lea	TAGLIST(pc),a0
	jsr	resload_Control(a2)


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
	cmpi.w	#$55bf,d0		; SPS 627 (cmpi: the shipped slave's encoding)
	beq.b	.ok
	lea	PLGAME_US(pc),a3
	lea	GT628(pc),a4
	move.l	#$cec0,d4
	lea	PLFAST_US(pc),a6
	cmpi.w	#$f600,d0		; SPS 628 (cmpi: the shipped slave's encoding)
	beq.b	.ok

.wrongver
	pea	(TDREASON_WRONGVER).w
	bra.b	EXIT

.ok	lea	t_table(pc),a0
	move.l	a4,(a0)

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
	add.l	d3,(a1)
.reloc	moveq	#0,d2
	move.b	(a0)+,d2
	beq.b	.done
	cmpi.b	#1,d2	; immediate form as the shipped slave has it: vasm encodes op #,Dn as the Dn form
	bne.b	.normal
	add.w	#$FE,a1
	bra.b	.reloc

.normal	add.l	d2,a1
	add.l	d3,(a1)
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

; the instruction cache for BaseMem, no data cache (it would make the screens
; data-cacheable where WHDLoad uses the MMU)
	move.l	#WCPUF_Base_WT|WCPUF_IC,d0
	move.l	#WCPUF_Base|WCPUF_IC|WCPUF_DC,d1
	jsr	resload_SetCPU(a2)


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


; SPS 627, 68020 or better
PLFAST	PL_START
	PL_S	$1185c,6		; no field wait before the swap
	PL_END

; SPS 628, 68020 or better
PLFAST_US
	PL_START
	PL_S	$11b14,6		; no field wait before the swap
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
	move.b	d0,$2000+$1c+$e33c
	jmp	$2000+$1c+$e37e
	

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
.intro	move.l	#$2000+$1c+$1264c,d0
	btst	#6,$bfe001
	bne.b	.noquit
	moveq	#0,d2
.noquit	rts
	

.setkbd	lea	.kbdcust(pc),a0
	move.l	a0,KbdCust-.kbdcust(a0)
	rts

.kbdcust
	move.b	RawKey(pc),d0
	move.b	d0,$2000+$1c+$e390
	jmp	$2000+$1c+$e3d2


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


