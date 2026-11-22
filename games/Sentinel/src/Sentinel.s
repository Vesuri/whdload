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
	dc.b	"Version 1.01 (15.09.2017)",0


	DC.B	'$VER:Sentinel_Slave_1.01',0
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
