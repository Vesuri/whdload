; V1.01, stingray, 14.09.2017
; - blitter wait added (Mantis issue #1942)
; - interrupt fixed
; - SMC in slave code fixed
; - default quitkey changed to F10
; - code optimised

; 15.09.2017
; - RawDIC imager coded
; - some more code optimising
; - CUSTOM1 can be used the disable the blitter wait
; - uses WHDLoad v17+ now
; - Harry's patches converted for patch list usage
; - Protection track check disabled "my way"
; - loader patch recoded
; - version check added

; 2.0b, Vesuri, 23.11.2026
; - version and info text
; - the edge scan converter no longer modifies its own code (EdgeStep): with
;   the instruction cache on, 68040 and 68060 drew faces wrongly

	INCDIR	SOURCES:Include/
	INCLUDE	whdload.i

FLAGS		= WHDLF_NoError|WHDLF_ClearMem|WHDLF_EmulTrap
QUITKEY		= $59		; F10
;DEBUG

BASE		= $57fe4	; destination address for binary

; absolute skip
PL_SA	MACRO
	PL_S	\1,\2-(\1)
	ENDM

; jsr+absolute skip
PL_PSA	MACRO
	PL_PS	\1,\2		; could use PSS here but it fills memory
	PL_S	\1+6,\3-(\1+6)	; with NOPS so we use standard skip
	ENDM

HEADER	SLAVE_HEADER
	dc.w	17			; ws_Version
	dc.w	FLAGS			; ws_Flags
	dc.l	$80000			; ws_BaseMemSize
	dc.l	0			; ws_ExecInstall
	dc.w	slv_GameLoader-HEADER	; ws_GameLoader
	IFD	DEBUG
	dc.w	.dir-HEADER		; ws_CurrentDir
	ELSE
	dc.w	0			; ws_CurrentDir
	ENDC
	dc.w	0			; ws_DontCache
	dc.b	0			; ws_keydebug
	dc.b	QUITKEY			; ws_keyexit
	dc.l	0			; ws_ExpMem
	dc.w	.name-HEADER		; ws_name
	dc.w	.copy-HEADER		; ws_copy
	dc.w	.info-HEADER		; ws_info

; v16
	dc.w	0			; ws_kickname
	dc.l	0			; ws_kicksize
	dc.w	0			; ws_kickcrc

; v17
	dc.w	.config-HEADER		; ws_config


.config	dc.b	"C1:B:Disable Blitter Waits"
	dc.b	0

	IFD	DEBUG
.dir	dc.b	"SOURCES:WHD_Slaves/Sentinel",0
	ENDC


.name	dc.b	"The Sentinel",0
.copy	dc.b	"1988 Firebird",0
.info	dc.b	"installed and fixed by Harry & StingRay",10
	dc.b	"enhanced by Vesuri",10
	dc.b	"Version 2.0b (23.11.2026)",0


	DC.B	"$VER: Sentinel.slave 2.0b (23.11.2026)",0
	CNOP	0,2

slv_GameLoader
	lea	resload(pc),a1
	move.l	a0,(a1)
	move.l	a0,a2

	move.l	#1,d0
	move.l	d0,d1
	jsr	resload_SetCACR(a0)

	moveq	#0,d0
	move.l	#$B400,d1
	lea	BASE,a0
	move.l	a0,a5
	move.l	d1,d5
	moveq	#1,d2
	jsr	resload_DiskLoad(a2)

	move.l	a5,a0
	move.l	d5,d0
	jsr	resload_CRC16(a2)
	cmpi.w	#$67e7,d0		; SPS 3025 (cmpi: the shipped encoding)
	beq.b	.ok
	pea	(TDREASON_WRONGVER).w
	bra.w	QUIT

.ok


; only 9 sectors in each track are used
; fix the data as the imager saved 10 sectors/track
	move.l	a5,a0
	move.l	a0,a1
	moveq	#9-1,d1
.loop	move.w	#9*512/4-1,d0
.copy	move.l	(a0)+,(a1)+
	dbf	d0,.copy
	lea	512(a0),a0		; skip unused sector 10
	dbf	d1,.loop


	bset	#1,$BFE001

	move.w	#$C000,$DFF09A




	lea	PLGAME(pc),a0
	lea	BASE,a1
	jsr	resload_Patch(a2)


	jmp	$10d4(a5)


PLGAME	PL_START

; Harry's patches
	PL_R	$a3e			; disable drive access (motor off)
	PL_R	$a78			; disable drive access (motor on)
	PL_R	$adc			; step to track 0
	PL_R	$b9c			; read protection track

	PL_P	$669c,Loader
	PL_PS	$4b2,CheckKeys
	PL_R	$51c			; disable CPU dependent kbd delay


; StingRay's patches (V1.01)
	PL_SA	$c0a,$c6c		; check protection track

	PL_IFC1
; if CUSTOM 1 is used => do nothing

	PL_ELSE
	PL_PSS	$30c,.wblit1,2
	PL_ENDIF
	
	PL_PSS	$6d4,.ackVBI,2

; Vesuri's patches (2.0b)
	PL_P	$14be,EdgeStep		; the edge scan converter's stepping
	PL_END

.ackVBI	move.w	#1<<4|1<<5|1<<6,$dff09c
	move.w	#1<<4|1<<5|1<<6,$dff09c
	rts

.wblit1	bsr.b	WaitBlit
	move.w	#$09f0,$dff040
	rts

WaitBlit
	tst.b	$dff002
.wb	btst	#6,$dff002
	bne.b	.wb
	rts

Loader	movem.l	d0-a6,-(a7)
	lea	BASE+$c98,a1
	movem.w	(a1)+,d0/d1		; track/length
	subq.w	#2,d0
	move.l	(a1),a0			; destination
	mulu.w	#512*10,d0
	mulu.w	#512*10,d1
	moveq	#1,d2
	move.l	resload(pc),a2
	jsr	resload_DiskLoad(a2)
	movem.l	(a7)+,d0-a6
	rts

resload	dc.l	0

; The edge scan converter's stepping, program offsets $14be..$165b, without
; self-modification. The game's code wrote the x step's opcode (addq.w or
; subq.w #1,d1) into its loops at $1546, $15be, $15f6 and $1630, and the
; x-major loop's bcc.s displacement at $15c3 (store x at every step, or only
; at the first step of each row); the 68040/060 instruction cache kept the old
; instructions. Here d3 holds the step (+1 or -1, the same cycles as addq), the
; two x-major modes are two loops, and the mode is bit 16 of d2 (the loops
; count in its low word). Registers, flags and memory end as the game's:
; d3 is restored, or gets the low word the clipped paths left in it.
; Variables (absolute short): $16f9 the count left, $18dc the table ($7b00
; left edges, $7d00 right), $18de dy, $18e0 |dx|, $18e8/$18ec the x ends,
; $18ea clipped, $18eb the rows.

EdgeStep
	move.l	d3,-(a7)
	move.w	$18ec.w,d0
	sub.w	$18e8.w,d0
	bpl.b	.left
	neg.w	d0
	move.w	d0,$18e0.w
	move.b	#$52,d1			; the game's addq.w opcode byte
	moveq	#1,d3
	bra.b	.dir
.left	move.w	d0,$18e0.w
	move.b	#$53,d1			; subq.w
	moveq	#-1,d3
.dir	move.w	$18e0.w,d4
	move.w	$18de.w,d5
	move.b	$18eb.w,d6
	andi.l	#$ff,d6
	asl.w	#1,d6
	add.w	$18dc.w,d6
	movea.l	d6,a6
	move.b	$18eb.w,d6
	cmp.w	d5,d4
	bcc.w	.xmajor

; y-major ($1516)
	move.b	d5,d2
	addq.b	#1,d2
	move.b	d5,d0
	lsr.b	#1,d0
	eori.b	#$ff,d0
	addq.w	#2,a6
	move.b	$18ea.w,d1
	bne.b	.yclip
	move.w	$18ec.w,d1
	bra.b	.ystore
.yloop	add.b	d4,d0
	bcc.b	.ystore
	sub.b	d5,d0
	add.w	d3,d1
.ystore	move.w	d1,-(a6)
	subq.b	#1,d6
	beq.b	.done0
.ynext	subq.b	#1,d2
	bne.b	.yloop
.store	move.b	d2,$16f9.w
.exit	move.l	(a7)+,d3
	clr.l	d1
	clr.l	d2
	rts
.done0	move.b	#0,d2
	bra.b	.store

; y-major, clipped ($15d8): step without storing to the first row
.yclip	addq.b	#1,d6
	move.w	$18ec.w,d1
	bra.b	.ycnext
.ycloop	add.b	d4,d0
	bcc.b	.ycnext
	sub.b	d5,d0
	add.w	d3,d1
.ycnext	subq.b	#1,d6
	beq.b	.ycin
	subq.b	#1,d2
	bne.b	.ycloop
	bra.b	.exit
.ycin	move.w	$18dc.w,2(a7)		; the game's d3.w
	addi.w	#$200,2(a7)
	movea.w	2(a7),a6
	subq.b	#1,d6
	bra.b	.ynext

; x-major ($156a): mode "every" (the game's displacement 8) for left edges
; stepping left and right edges stepping right, else "first" (10)
.xmajor	bclr	#16,d2
	cmpi.w	#$7b00,$18dc.w
	beq.b	.xl
	cmpi.b	#$53,d1
	beq.b	.xfirst
	bra.b	.xmode
.xl	cmpi.b	#$53,d1
	beq.b	.xmode
.xfirst	bset	#16,d2
.xmode	move.w	d4,d2
	addq.w	#1,d2
	move.w	d4,d0
	lsr.w	#1,d0
	eori.w	#$ffff,d0
	move.b	$18ea.w,d1
	bne.b	.xclip
	move.w	$18ec.w,d1
	btst	#16,d2
	bne.b	.xfstore
	bra.b	.xestore

.xeloop	add.w	d3,d1
	add.w	d5,d0
	bcc.b	.xestore
	sub.w	d4,d0
	subq.w	#2,a6
	subq.b	#1,d6
	beq.b	.done0
.xestore
	move.w	d1,(a6)
.xenext	subq.w	#1,d2
	bne.b	.xeloop
	bra.w	.store

.xfloop	add.w	d3,d1
	add.w	d5,d0
	bcc.b	.xfnext
	sub.w	d4,d0
	subq.w	#2,a6
	subq.b	#1,d6
	beq.w	.done0
.xfstore
	move.w	d1,(a6)
.xfnext	subq.w	#1,d2
	bne.b	.xfloop
	bra.w	.store

; x-major, clipped ($161a)
.xclip	addq.b	#1,d6
	move.w	$18ec.w,d1
	bra.b	.xcnext
.xcloop	add.w	d3,d1
	add.w	d5,d0
	bcc.b	.xcnext
	sub.w	d4,d0
	subq.b	#1,d6
	beq.b	.xcin
.xcnext	subq.w	#1,d2
	bne.b	.xcloop
	bra.w	.exit
.xcin	move.w	$18dc.w,2(a7)		; the game's d3.w
	addi.w	#$1fe,2(a7)
	movea.w	2(a7),a6
	subq.b	#1,d6
	btst	#16,d2
	bne.b	.xfnext
	bra.b	.xenext

CheckKeys
	move.b	d0,$58C6B
	tst.b	$BFED01
	move.l	d0,-(sp)
	bset	#6,$BFEE01

	moveq	#3-1,d0
.loop	move.l	d0,-(sp)
	move.b	$DFF006,d0
.wait	cmp.b	$DFF006,d0
	beq.b	.wait
	move.l	(sp)+,d0
	dbf	d0,.loop

	bclr	#6,$BFEE01
	move.l	(sp)+,d0
	cmp.b	HEADER+ws_keyexit(pc),d0
	beq.b	.exit
	rts

.exit	pea	(TDREASON_OK).w
QUIT	move.l	resload(pc),-(a7)
	addq.l	#resload_Abort,(a7)
	rts

	END
