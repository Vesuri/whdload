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
; - the sound effect trigger's CPU-timed DMA-off wait is beam-timed
;   (SfxDmaWait), at least the 68000's length on every CPU
; - the pan step waits for its last blit before the field it shows it in (not
;   and StingRay's wait at $30c are always on: CUSTOM1 no longer drops them
; - the PAL/NTSC test reads only the beam's line: AGA's chip ID in VPOSR made
;   an NTSC A1200 run the game's PAL clock, 20% fast
; - CUSTOM1, Enhanced framerate (a 68020 or better, the optional ExpMem): the
;   render buffer and the edge tables in the ExpMem, a span filler without
;   movep (SpanFill), and the pan's scroll-in from the vertical blank, its
;   blits chained by the blitter's interrupt, beside the next step's render

	INCDIR	SOURCES:Include/
	INCLUDE	whdload.i

FLAGS		= WHDLF_NoError|WHDLF_ClearMem|WHDLF_EmulTrap
QUITKEY		= $59		; F10
;DEBUG

BASE		= $57fe4	; destination address for binary
STRIP		= $70000	; the game's render buffer: 320x200, 4 word-interleaved planes
STRIPSIZE	= $7d00
EDGES		= $8000		; ExpMem: the render buffer, then the edge tables,
SCROLLBUF	= $9000		; then two copies of the strip for the scroll-in
FASTSIZE	= (SCROLLBUF+2*192*160+$fff)&~$fff	; whole 4 KB pages, as WHDLoad needs
SOUND		= $20000	; the sound module, loaded by the game

; one 16-pixel group of the span (a2, 4 plane words, advanced past it):
; the pixels in mask d2 get colour d4/d5, those also in d3 the edge colour
; (d6/d7 hold colour ^ edge colour); d0, d1 scratch
GROUP	MACRO
	move.l	d6,d0
	and.l	d3,d0
	eor.l	d4,d0
	move.l	(a2),d1
	eor.l	d1,d0
	and.l	d2,d0
	eor.l	d1,d0
	move.l	d0,(a2)+
	move.l	d7,d0
	and.l	d3,d0
	eor.l	d5,d0
	move.l	(a2),d1
	eor.l	d1,d0
	and.l	d2,d0
	eor.l	d1,d0
	move.l	d0,(a2)+
	ENDM

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
EXPMEM	dc.l	-FASTSIZE		; ws_ExpMem: optional, WHDLoad writes its address here
	dc.w	.name-HEADER		; ws_name
	dc.w	.copy-HEADER		; ws_copy
	dc.w	.info-HEADER		; ws_info

; v16
	dc.w	0			; ws_kickname
	dc.l	0			; ws_kicksize
	dc.w	0			; ws_kickcrc

; v17
	dc.w	.config-HEADER		; ws_config


.config	dc.b	"C1:B:Enhanced framerate"
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




	bsr.w	FastSetup

	lea	PLGAME(pc),a0
	lea	BASE,a1
	jsr	resload_Patch(a2)

	move.l	fast(pc),d0
	beq.b	.go
	lea	PLFAST(pc),a0
	lea	BASE,a1
	jsr	resload_Patch(a2)
.go


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

	PL_PSS	$30c,.wblit1,2
	
	PL_PSS	$6d4,.ackVBI,2

; Vesuri's patches (2.0b)
	PL_P	$14be,EdgeStep		; the edge scan converter's stepping
	PL_PS	$47ac,.wblit2		; the pan step: wait for the last blit
	PL_L	$3c9a,$1ff		; PAL/NTSC test: the line, not AGA's chip ID
	; and in the sound module: PLSOUND, applied by Loader
	PL_END

.ackVBI	move.w	#1<<4|1<<5|1<<6,$dff09c
	move.w	#1<<4|1<<5|1<<6,$dff09c
	rts

.wblit1	bsr.b	WaitBlit
	move.w	#$09f0,$dff040
	rts

; The pan step starts its plane blits (the wait at $30c covers each start,
; not the last one's end), clears the field flag, waits for it and restarts
; the copper on the buffer they wrote. On a 68000 blitter-nasty holds the
; CPU until the blit ends, so the field it waits for starts after it; a
; 68040 or 68060 running from its caches is not held.
.wblit2	bsr.b	WaitBlit
	clr.w	BASE+$c8c		; clr.w $58c70: the field flag
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
	move.l	a0,a3
	move.l	resload(pc),a2
	jsr	resload_DiskLoad(a2)
	cmpa.l	#SOUND,a3		; the sound module?
	bne.b	.done
	cmpi.l	#$303c0200,SOUND+$f2e	; move.w #512,d0
	bne.b	.done
	cmpi.l	#$51c8fffe,SOUND+$f32	; dbf d0,*
	bne.b	.done
	lea	PLSOUND(pc),a0
	move.l	a3,a1
	jsr	resload_Patch(a2)
.done	movem.l	(a7)+,d0-a6
	rts

; The sound module at $20000 (offsets in it). Its effect trigger turns the
; channel's DMA off, then waited with a CPU loop (move.w #512,d0; dbf d0,*,
; 11.3 raster lines on the 68000, about one on a 68040) before letting the
; next vertical blank turn it on with the effect's sample; Paula needs it
; off for a sample period to restart the channel. The trigger runs with
; interrupts off and the caller saves every register.
PLSOUND	PL_START
	PL_PSS	$f2e,SfxDmaWait,2
	PL_END

; at least 12 raster lines on every CPU, d0.w ends as after the dbf
SfxDmaWait
	move.l	d1,-(a7)
	moveq	#13-1,d1
.line	move.b	$dff006,d0
.same	cmp.b	$dff006,d0
	beq.b	.same
	dbf	d1,.line
	move.l	(a7)+,d1
	moveq	#-1,d0
	rts

resload	dc.l	0

; Enhanced framerate (CUSTOM1, a 68020 or better, the ExpMem allocated):
; the game's render buffer at $70000 moves to the ExpMem, fast memory where
; there is some. The CPU reaches it through the row tables at $56010 and
; $56100 (loaded with the data at $55000, relocated by Tables), the pan
; step's column pointers at $4854 and three absolute addresses; the blitter
; only in the pan step's horizontal column copy, which ColumnH does instead.
FastSetup
	lea	tags(pc),a0
	jsr	resload_Control(a2)
	move.l	custom1(pc),d0
	beq.b	.off
	move.l	attn(pc),d0
	btst	#AFB_68020,d0
	beq.b	.off
	move.l	EXPMEM(pc),d0
	beq.b	.off
	lea	fast(pc),a0
	move.l	d0,(a0)
	lea	BASE,a0
	move.l	d0,$39d4(a0)		; lea $70000,a0: the copy for the view's
	sub.l	#STRIP,d0		; conversion to planes
	add.l	d0,$39f2(a0)		; lea $77d00,a1
	moveq	#5-1,d1
	lea	$4854(a0),a1		; the pan step's column pointers
.col	add.l	d0,(a1)+
	dbf	d1,.col
	add.l	d0,$502e(a0)		; movea.l #$70000: the dissolve
	add.l	d0,$5e8e(a0)		; movea.l #$70000
	move.w	#$0400,$dff096		; no blitter-nasty (E16)
	add.l	#STRIP+EDGES-$7b00,d0	; the edge tables
	lea	edgedelta(pc),a0
	move.l	d0,(a0)
.off	rts

fast	dc.l	0			; the render buffer in ExpMem, or 0
tags	dc.l	WHDLTAG_CUSTOM1_GET
custom1	dc.l	0
	dc.l	WHDLTAG_ATTNFLAGS_GET
attn	dc.l	0
	dc.l	TAG_DONE

PLFAST	PL_START
	PL_P	$66f8,Tables		; the data at $55000 with the row tables
	PL_P	$48e4,ColumnH		; the pan step's horizontal column copy
	PL_P	$18b4,SpanFill		; the span filler
	PL_P	$14be,EdgeStepF		; the edge scan converter's stepping
	PL_PSS	$13d0,EdgePoint,10	; a one-row polygon's edges
; the scroll-in from the vertical blank (E15) and the chip bus (E16)
	PL_P	$4740,StepQueue		; the pan step's set-up and scroll-in
	PL_PS	$574,VblScroll		; the level 3 interrupt
	PL_PS	$46d6,PassExit		; the pass loop asking for a full redraw
	PL_PS	$3708,PassCmd		; a command from the pass loop
	PL_PSS	$369c,PassEvent,2	; an event from the pass loop
	PL_PS	$68c,PointerGate	; the pointer during the passes
	PL_PS	$2ce4,StatusWait	; the status line's copies to the screen
	PL_PS	$2d10,StatusWait
	PL_PS	$39cc,ViewWait		; a full view's copy
	PL_W	$48c,$8068		; INTENA: the blitter's interrupt too
	PL_PSS	$6d4,AckNoBlit,2	; the level 3 interrupt's end
	PL_END

; move.w $18fa,$7b00(a4); move.w $18fc,$7d00(a4) into the ExpMem's tables
EdgePoint
	move.l	a0,-(a7)
	move.l	edgedelta(pc),a0
	adda.l	a4,a0
	move.w	$18fa.w,$7b00(a0)
	move.w	$18fc.w,$7d00(a0)
	move.l	(a7)+,a0
	rts

; the game's copy of the loaded data to $55000..$56fff, then the row pointers
; into the render buffer (the text rows at $56010, the span rows at $56100)
Tables	lea	$10000,a1
	lea	$55000,a0
	move.w	#2047,d7
.copy	move.l	(a1)+,(a0)+
	dbf	d7,.copy
	movem.l	d0-d2/a0,-(a7)
	move.l	fast(pc),d1
	sub.l	#STRIP,d1
	lea	$56010,a0
	move.w	#($56740-$56010)/4-1,d2
.rel	move.l	(a0),d0
	cmp.l	#STRIP,d0
	blo.b	.next
	cmp.l	#STRIP+STRIPSIZE,d0
	bhs.b	.next
	add.l	d1,d0
	move.l	d0,(a0)
.next	addq.l	#4,a0
	dbf	d2,.rel
	movem.l	(a7)+,d0-d2/a0
	bra.w	SpanTables

; Whether the span filler's tables (loaded with the data at $55000) are what
; SpanFill computes instead: for colour c and pixel i of a byte (0 the left),
; with S the colour's four plane bytes at $56e60+c*4 (each byte 0 or $ff per
; plane), the left edge's keep mask $56e00 (pixels < i) and pattern
; $56800+c*32 (S, pixels > i), the right edge's keep mask $56e20 (pixels > i)
; and pattern $56a00+c*32 (S, pixels < i), the edge pixel $56c00+c*32 (S,
; pixel i) and $56e40 (pixels <= i), each byte the same in the four planes.
; spanok is set if every long matches.
	MACHINE	68020
SpanTables
	movem.l	d0-d7/a0-a2,-(a7)
	lea	spanok(pc),a1
	sf	(a1)
	lea	$56800,a0
	lea	$56e60,a2
	moveq	#0,d7			; c
.c	move.l	(a2)+,d6		; S
	moveq	#0,d5			; i
.i	move.w	#$ff00,d0		; pixels < i
	lsr.w	d5,d0
	move.b	d0,d1			; ~
	not.b	d1			; d1: pixels >= i; d0.b: pixels < i
	move.b	#$80,d2
	lsr.b	d5,d2			; pixel i
	move.b	d1,d3
	eor.b	d2,d3			; pixels > i
	lea	cmp4(pc),a1
	move.b	d3,(a1)			; A0: S & pixels > i
	bsr.w	.rep4
	and.l	d6,d4
	cmp.l	(a0,d5.w*4),d4
	bne.w	.bad
	move.b	d0,(a1)			; A: S & pixels < i
	bsr.w	.rep4
	and.l	d6,d4
	cmp.l	$200(a0,d5.w*4),d4
	bne.w	.bad
	move.b	d2,(a1)			; B: S & pixel i
	bsr.w	.rep4
	and.l	d6,d4
	cmp.l	$400(a0,d5.w*4),d4
	bne.w	.bad
	tst.w	d7
	bne.b	.inext
	move.b	d0,(a1)			; the masks, once
	bsr.w	.rep4
	cmp.l	$56e00-$56800(a0,d5.w*4),d4
	bne.w	.bad
	move.b	d3,(a1)
	bsr.w	.rep4
	cmp.l	$56e20-$56800(a0,d5.w*4),d4
	bne.w	.bad
	move.b	d2,d3
	or.b	d0,d3			; pixels <= i
	move.b	d3,(a1)
	bsr.w	.rep4
	cmp.l	$56e40-$56800(a0,d5.w*4),d4
	bne.w	.bad
.inext	addq.w	#1,d5
	cmp.w	#8,d5
	bne.w	.i
	moveq	#4-1,d1			; S: each byte 0 or $ff
	move.l	d6,d4
.s	tst.b	d4
	beq.b	.snext
	cmp.b	#$ff,d4
	bne.w	.bad
.snext	lsr.l	#8,d4
	dbf	d1,.s
	lea	32(a0),a0
	addq.w	#1,d7
	cmp.w	#16,d7
	bne.w	.c
	lea	spanok(pc),a1
	st	(a1)
.bad	movem.l	(a7)+,d0-d7/a0-a2
	rts
; d4: the byte at cmp4 in all four bytes
.rep4	moveq	#0,d4
	move.b	(a1),d4
	move.w	d4,-(a7)
	lsl.w	#8,d4
	or.w	(a7)+,d4
	move.w	d4,-(a7)
	swap	d4
	move.w	(a7)+,d4
	rts
	MACHINE	68000

; The span filler ($18b4..$1b17) on the fast drawing path, without movep:
; for each row from $1680 down to $167e (the row at $56100+($ef-row)*4+
; [$18ba], plus [$195a]; 160 bytes a row, 16 pixels in 4 plane words), the
; span from the left edge ($7b00+row*2, in the ExpMem's copy of the tables
; that EdgeStepF and EdgePoint write) to the right one ($7d00), clipped to
; the window $18f0 (left) and $18f2 (width): the edge pixels in colour
; [$1693]>>4, the others in [$1693]&15. It stops at a row whose right edge is
; left of its left edge, and returns at once if the middle row's is. Memory
; and d1, d2, a1, a2 and the flags end as the game's code leaves them, but for
; $191a, the game's scratch for one row; the other registers are left as
; they fall. The game's code runs instead when its tables are not the plain
; ones (SpanTables), with bit 7 of $17f0 (its edge pattern pointer would leave
; base memory), and with a window not in whole bytes.
	MACHINE	68020
SpanFill
	move.b	spanok(pc),d0
	beq.w	.orig
	btst	#7,$17f0.w
	bne.w	.orig
	move.w	$18f0.w,d0
	moveq	#7,d1
	and.w	d0,d1
	bne.w	.orig
	move.w	$18f2.w,d1
	moveq	#7,d2
	and.w	d1,d2
	bne.w	.orig
	add.w	d1,d0
	cmp.w	$18f4.w,d0
	bne.w	.orig
	lea	clipl(pc),a0
	move.w	$18f0.w,(a0)+
	move.w	d1,(a0)
	moveq	#0,d0			; the middle row
	move.b	$1680.w,d0
	moveq	#0,d1
	move.b	$167e.w,d1
	add.w	d1,d0
	lsr.w	#1,d0
	add.w	d0,d0
	movea.l	edgedelta(pc),a0	; the ExpMem's edge tables
	adda.w	d0,a0
	move.w	$7d00(a0),d0
	sub.w	$7b00(a0),d0
	bmi.w	.exit
	moveq	#0,d0			; the colours
	move.b	$1693.w,d0
	moveq	#15,d1
	and.w	d0,d1
	lsr.w	#4,d0
	lea	$56e60,a0
	move.l	(a0,d0.w*4),d2
	bsr.w	.double
	move.l	d4,d6
	move.l	d5,d7
	move.l	(a0,d1.w*4),d2
	move.l	d2,$1946.w
	bsr.w	.double
	move.l	d4,$194e.w
	move.l	d5,$1952.w
	eor.l	d4,d6			; colour ^ edge colour, planes 0 and 1
	eor.l	d5,d7			; planes 2 and 3
	move.b	$1680.w,d0		; the top row
	move.b	d0,$18eb.w
	cmp.b	$167e.w,d0
	bcs.w	.exit
	moveq	#-17,d1			; $ef
	sub.b	d0,d1
	andi.w	#$ff,d1
	lsl.w	#2,d1
	add.w	$18ba.w,d1
	lea	$56100,a6
	movea.l	(a6,d1.w),a6
	adda.l	$195a.w,a6
	moveq	#0,d1
	move.b	d0,d1
	sub.b	$167e.w,d0
	andi.w	#$ff,d0
	lea	rows(pc),a0
	move.w	d0,(a0)			; the rows after this one
	add.w	d1,d1
	movea.l	edgedelta(pc),a5
	lea	$7b00(a5),a5
	adda.w	d1,a5

.row	move.w	$200(a5),d1		; R
	move.w	(a5),d0			; L
	cmp.w	d0,d1
	bmi.w	.stop
	sub.w	clipl(pc),d1
	bmi.w	.next
	sub.w	clipl(pc),d0
	cmp.w	clipw(pc),d1
	bpl.b	.rclamp
	moveq	#15,d2
	and.w	d1,d2
	movea.l	(bits,pc,d2.w*4),a4	; the right edge pixel
	bra.b	.left
.rclamp	move.w	clipw(pc),d1		; to the window's right end, no edge
	subq.w	#1,d1
	suba.l	a4,a4
.left	cmp.w	clipw(pc),d0
	bpl.w	.next
	tst.w	d0
	bmi.b	.lclamp
	moveq	#15,d2
	and.w	d0,d2
	movea.l	(bits,pc,d2.w*4),a3	; the left edge pixel
	bra.b	.span
.lclamp	moveq	#0,d0			; from the window's left end, no edge
	suba.l	a3,a3
.span	moveq	#15,d2
	and.w	d0,d2
	move.l	(fmask,pc,d2.w*4),d2
	moveq	#15,d3
	and.w	d1,d3
	movea.l	(lmask,pc,d3.w*4),a0
	lsr.w	#4,d0
	lsr.w	#4,d1
	lea	(a6,d0.w*8),a2
	sub.w	d0,d1			; the groups after the first
	bne.b	.multi
	move.l	a0,d3			; one group: both ends, both edges
	and.l	d3,d2
	move.l	a3,d3
	move.l	a4,d0
	or.l	d0,d3
	GROUP
	bra.b	.next
.multi	movea.w	d1,a1
	move.l	a3,d3
	GROUP
	move.w	a1,d3
	subq.w	#1,d3
	bra.b	.midt
.mid	move.l	d4,(a2)+
	move.l	d5,(a2)+
.midt	dbf	d3,.mid
	move.l	a0,d2
	move.l	a4,d3
	GROUP
.next	lea	160(a6),a6
	subq.l	#2,a5
	lea	rows(pc),a0
	subq.w	#1,(a0)
	bcc.w	.row
	move.b	$167e.w,$18eb.w
	bra.b	.exit
.stop	move.w	rows(pc),d0		; stopped at row $167e+rows
	add.b	$167e.w,d0
	move.b	d0,$18eb.w
.exit	moveq	#0,d1
	movea.l	d1,a1
	move.l	d1,d2
	movea.l	d2,a2
	rts
.orig	movea.l	edgedelta(pc),a0	; the game's code: the edge tables back
	lea	$7b00(a0),a0
	lea	($7b00).w,a1
	move.w	#$400/4-1,d0
.copy	move.l	(a0)+,(a1)+
	dbf	d0,.copy
	move.b	$1680.w,d0
	jmp	BASE+$18ba

; d2 (bytes b3 b2 b1 b0): d4 = b3 b3 b2 b2, d5 = b1 b1 b0 b0; d2 kept
.double	rol.l	#8,d2
	move.b	d2,d4
	lsl.w	#8,d4
	move.b	d2,d4
	swap	d4
	rol.l	#8,d2
	move.b	d2,d4
	lsl.w	#8,d4
	move.b	d2,d4
	rol.l	#8,d2
	move.b	d2,d5
	lsl.w	#8,d5
	move.b	d2,d5
	swap	d5
	rol.l	#8,d2
	move.b	d2,d5
	lsl.w	#8,d5
	move.b	d2,d5
	rts
	MACHINE	68000

fmask
	dc.l	$ffffffff,$7fff7fff,$3fff3fff,$1fff1fff
	dc.l	$0fff0fff,$07ff07ff,$03ff03ff,$01ff01ff
	dc.l	$00ff00ff,$007f007f,$003f003f,$001f001f
	dc.l	$000f000f,$00070007,$00030003,$00010001
lmask
	dc.l	$80008000,$c000c000,$e000e000,$f000f000
	dc.l	$f800f800,$fc00fc00,$fe00fe00,$ff00ff00
	dc.l	$ff80ff80,$ffc0ffc0,$ffe0ffe0,$fff0fff0
	dc.l	$fff8fff8,$fffcfffc,$fffefffe,$ffffffff
bits
	dc.l	$80008000,$40004000,$20002000,$10001000
	dc.l	$08000800,$04000400,$02000200,$01000100
	dc.l	$00800080,$00400040,$00200020,$00100010
	dc.l	$00080008,$00040004,$00020002,$00010001

spanok	dc.b	0			; SpanTables: the tables are the plain ones
cmp4	dc.b	0
clipl	dc.w	0			; $18f0
clipw	dc.w	0			; $18f2
rows	dc.w	0

; The pan step's column for a horizontal step: one word of each plane from
; 192 rows of the render buffer (a1, 160 bytes a row) into the back buffer's
; planes (a0, a2, a3, a4, 40 bytes a row), as the game's four blits did.
; The plane blits still running write other words.

ColumnH	move.w	#192-1,d7
.row	move.w	(a1),(a0)
	move.w	2(a1),(a2)
	move.w	4(a1),(a3)
	move.w	6(a1),(a4)
	lea	160(a1),a1
	moveq	#40,d0
	add.l	d0,a0
	add.l	d0,a2
	add.l	d0,a3
	add.l	d0,a4
	dbf	d7,.row
	jmp	BASE+$4970		; movem.l (sp)+,d0-a6; rts

	MACHINE	68020
; Enhanced framerate: the pan's scroll-in from the vertical blank (E15).
; The game renders a strip (the step's 128 pixels at the top left of the
; render buffer), scrolls it in over 8 fields, a swap a field, then runs its
; passes until the next pan request. Here the main loop queues the step, a
; copy of its strip, and goes on at once: the vertical blank does each swap
; and scroll step, and starts the queued step after a step's last swap, while
; the main loop runs the passes and renders the next strip. The main loop
; waits for the scroll-in before anything else that draws on the screen.

; $4740, after the step's render: the set-up ($4740..$4794: $17d4, the
; pointer hidden, $17d3, the status lines, the buffers, the column pointer),
; the step queued, then what the game does after the scroll-in ($47fe: $17d9
; as it was, the pointer)
	dc.l	VblEnd-StepQueue	; where a step ends, from here (tools/sentinel.py reads it)
StepQueue
	move.b	$1682.w,$17d4.w
	jsr	BASE+$2fd2
	movem.l	d0-d1/a0-a2,-(a7)
	lea	queued(pc),a2
.wait	tst.b	(a2)			; a step already queued: wait for it
	bne.b	.wait			; to start
	move.l	fast(pc),a0		; the render buffer
	move.l	#SCROLLBUF,d1		; the copy not in use
	not.b	nextbuf-queued(a2)
	beq.b	.buf
	add.l	#192*160,d1
.buf	moveq	#0,d0
	move.b	BASE+$49c0,d0		; the step's direction: 0, 1 horizontal
	move.b	d0,qdir-queued(a2)
	lea	BASE+$4854,a1		; the column pointer, into the copy
	move.l	(a1,d0.w*4),a1		; (the render buffer's)
	adda.l	d1,a1
	move.l	a1,qcol-queued(a2)
	lea	(a0,d1.l),a1
	move.b	$184b.w,d1
	subq.b	#1,d1
	move.b	d1,qsteps-queued(a2)
	cmp.b	#2,d0
	bcc.b	.rows
	move.w	#192-1,d0		; 192 rows of 8 groups (64 bytes)
.h	REPT	16
	move.l	(a0)+,(a1)+
	ENDR
	lea	160-64(a0),a0
	lea	160-64(a1),a1
	dbf	d0,.h
	bra.b	.go
.rows	move.w	#64*160/16-1,d0		; 64 rows
.v	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	move.l	(a0)+,(a1)+
	dbf	d0,.v
.go	move.w	sr,-(a7)
	or.w	#$0700,sr
	tst.b	scrolling-queued(a2)
	beq.b	.now
	st	(a2)			; the vertical blank starts it
	move.w	(a7)+,sr
	bra.b	.after
.now	move.w	(a7)+,sr
	bsr.b	StepStart
.after	movem.l	(a7)+,d0-d1/a0-a2
	move.b	$17d9.w,BASE+$5eb8
	bpl.b	.loop
	jsr	BASE+$2fd8
.loop	jmp	BASE+$46c4

; the queued step's set-up and first scroll step; the front buffer is $78000
StepStart
	movem.l	d0-d1/a0-a1,-(a7)
	jsr	BASE+$4822		; the status lines to the back buffer
	move.l	#$60000,BASE+$c92	; the back buffer and its copper list
	move.l	#BASE+$23e,BASE+$c8e
	move.l	qcol(pc),BASE+$4864
	move.b	qsteps(pc),$17d3.w
	lea	scrolldir(pc),a0
	move.b	qdir(pc),(a0)
	bsr.w	ScrollStep
	lea	scrolling(pc),a0
	st	(a0)
	movem.l	(a7)+,d0-d1/a0-a1
	rts

; one scroll step ($4868, $4976) in the scrolling step's direction: the four
; plane blits, the front buffer into the back one shifted a word or 8 lines,
; each started by the last one's blitter interrupt (BlitNext), so the CPU runs
; on beside them; then the strip's column by the CPU, as the game does it
ScrollStep
	movem.l	d0-d7/a0-a2,-(a7)
	lea	$78140,a1
	lea	$60140,a0
	cmp.l	#$60000,BASE+$c92	; from the front buffer into the back one
	beq.b	.dir
	exg	a0,a1
.dir	addq.l	#2,a1
	moveq	#2,d2			; the modulos
	moveq	#2,d3
	moveq	#19,d0			; words and lines
	move.w	#192,d1
	move.b	scrolldir(pc),d7
	beq.b	.go
	subq.l	#2,a1
	addq.l	#2,a0
	subq.b	#1,d7
	beq.b	.go
	subq.l	#2,a0
	moveq	#20,d0
	move.w	#184,d1
	moveq	#0,d2
	moveq	#0,d3
	lea	320(a0),a0
	subq.b	#1,d7
	beq.b	.go
	lea	-320(a0),a0
	lea	320(a1),a1
.go	lsl.w	#6,d1
	add.w	d0,d1
	bsr.w	WaitBlit
	lea	blitsrc(pc),a2
	move.l	a1,(a2)
	add.l	#8000,(a2)
	move.l	a0,blitdst-blitsrc(a2)
	add.l	#8000,blitdst-blitsrc(a2)
	move.w	d1,blitsize-blitsrc(a2)
	move.b	#3,blitsleft-blitsrc(a2)
	lea	$dff000,a2
	move.w	#$09f0,$40(a2)		; A to D
	move.w	#0,$42(a2)
	move.l	#-1,$44(a2)
	move.w	d2,$64(a2)
	move.w	d3,$66(a2)
	move.l	a1,$50(a2)
	move.l	a0,$54(a2)
	move.w	#$8040,$96(a2)		; blitter DMA, no blitter-nasty (E16)
	move.w	d1,$58(a2)
	move.b	BASE+$49c0,d1		; the column, in the scrolling step's
	move.b	scrolldir(pc),BASE+$49c0	; direction: the main loop may
	bsr.b	.column			; have set the next step's
	move.b	d1,BASE+$49c0
	movem.l	(a7)+,d0-d7/a0-a2
	rts
.column	movem.l	d0-a6,-(a7)		; $4868 after its blits
	jmp	BASE+$488a

; the next plane blit; a blitter interrupt, or the vertical blank waiting
BlitNext
	move.l	a0,-(a7)
	lea	blitsrc(pc),a0
	tst.b	blitsleft-blitsrc(a0)
	beq.b	.none
	subq.b	#1,blitsleft-blitsrc(a0)
	move.l	(a0),$dff050
	move.l	blitdst-blitsrc(a0),$dff054
	add.l	#8000,(a0)
	add.l	#8000,blitdst-blitsrc(a0)
	move.w	blitsize-blitsrc(a0),$dff058
.none	move.l	(a7)+,a0
	rts

; the step's blits finished, in the vertical blank (no blitter interrupt
; comes while it runs)
BlitsDone
	bsr.w	WaitBlit
	move.w	#1<<6,$dff09c
	move.w	#1<<6,$dff09c
	tst.b	blitsleft(pc)
	beq.b	.done
	bsr.b	BlitNext
	bra.b	BlitsDone
.done	rts

; $574 in the level 3 interrupt (move.w $dff01e,d0): at a vertical blank
; during a scroll-in, what the game's loop does after each field wait
; ($47ac..$47f6): show the buffer the last step drew, swap, the next step;
; after the last, the queued step
VblScroll
	move.w	$dff01e,d0
	btst	#6,d0			; the blitter's interrupt: the next blit
	beq.b	VblVbl
	move.w	#1<<6,$dff09c
	move.w	#1<<6,$dff09c
	bsr.b	BlitNext
VblVbl	move.w	$dff01e,d0
	btst	#5,d0
	beq.b	VblOut
	move.b	scrolling(pc),d0
	beq.b	VblDone
	bsr.b	BlitsDone
	movea.l	BASE+$c8e,a1		; the drawn buffer's copper list
	jsr	BASE+$7c0
	lea	$78000,a1
	lea	BASE+$1da,a2
	move.l	BASE+$c92,d0
	cmp.l	a1,d0
	bne.b	VblSwap
	lea	$60000,a1
	lea	BASE+$23e,a2
VblSwap	move.l	a1,BASE+$c92
	move.l	a2,BASE+$c8e
	subq.b	#1,$17d3.w
	bmi.b	VblEnd
	bsr.w	ScrollStep
	bra.b	VblDone
VblEnd	lea	queued(pc),a0		; a step's last swap
	tst.b	(a0)
	beq.b	VblIdle
	sf	(a0)
	bsr.w	StepStart
	bra.b	VblDone
VblIdle	lea	scrolling(pc),a0
	sf	(a0)
VblDone	move.w	$dff01e,d0
VblOut	rts

; the main loop waits for the scroll-in; from an interrupt it does not
WaitScroll
	move.l	d0,-(a7)
	move.w	sr,d0
	and.w	#$0700,d0
	bne.b	.ret
.wait	tst.b	scrolling(pc)
	bne.b	.wait
.ret	move.l	(a7)+,d0
	rts

; $46d6: st $5a2e4, the pass loop asking for a full redraw
PassExit
	bsr.w	WaitScroll
	st	BASE+$2300
	rts

; $3708: move.b d0,$17db, a command from the pass loop
PassCmd
	bsr.w	WaitScroll
	move.b	d0,$17db.w
	rts

; $369c: move.b #30,d0; bsr $515e
PassEvent
	bsr.w	WaitScroll
	move.b	#30,d0
	jmp	BASE+$515e

; $6d4: the level 3 interrupt acknowledged but for the blitter's, which
; VblScroll serves: a blit ending late in the interrupt is not lost
AckNoBlit
	move.w	#1<<4|1<<5,$dff09c
	move.w	#1<<4|1<<5,$dff09c
	rts

; $68c in the level 3 interrupt: tst.b $58c6c, the pointer shown during the
; passes; not while a scroll-in runs (the game hides it during a pan)
PointerGate
	tst.b	scrolling(pc)
	bne.b	.no
	tst.b	BASE+$c88
	rts
.no	cmp.b	d0,d0
	rts

; $2ce4, $2d10: movea.l #$50300,a0, the status line's copies to the screen
StatusWait
	bsr.w	WaitScroll
	movea.l	#$50300,a0
	rts

; $39cc: lea $78000,a1, a full view's copy
ViewWait
	bsr.w	WaitScroll
	lea	$78000,a1
	rts

blitsrc	dc.l	0			; the next plane blit: source,
blitdst	dc.l	0			; destination,
blitsize	dc.w	0			; size
blitsleft	dc.b	0			; the plane blits still to start
	even
qcol	dc.l	0			; the queued step: its column pointer,
queued	dc.b	0			; set while it waits
qdir	dc.b	0			; its direction
qsteps	dc.b	0			; its swaps less one
nextbuf	dc.b	0			; the strip copy for the next step
scrolling	dc.b	0			; set while a scroll-in runs
scrolldir	dc.b	0			; its direction
	even
	MACHINE	68000

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

; \1: 0 the tables at $7b00 and $7d00, 1 those in the ExpMem (edgedelta from
; them), for the fast drawing path
EDGESTEP	MACRO
	move.l	d3,-(a7)
	IFNE	\1
	bsr.w	EdgeUnder
	ENDC
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
	IFNE	\1
	adda.l	edgedelta(pc),a6
	ENDC
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
	IFNE	\1
	suba.l	edgedelta(pc),a6	; a6 as the game's code leaves it
	bsr.w	EdgeOver
	ENDC
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
	IFNE	\1
	adda.l	edgedelta(pc),a6
	ENDC
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
	IFNE	\1
	beq.w	.done0
	ELSE
	beq.b	.done0
	ENDC
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
	IFNE	\1
	adda.l	edgedelta(pc),a6
	ENDC
	subq.b	#1,d6
	btst	#16,d2
	bne.b	.xfnext
	bra.b	.xenext
	ENDM

EdgeStep
	EDGESTEP	0
EdgeStepF
	EDGESTEP	1
edgedelta	dc.l	0		; the ExpMem's edge tables - $7b00
under	dc.w	0

; An unclipped edge ($18ea 0) of 0 rows ($18eb) steps 256 rows down from its
; table: from the left table ($18dc $7b00) the game's code writes below it,
; into $7900..$7aff (a right edge's lower rows are the left table). In that
; case EdgeUnder copies those bytes to the ExpMem below its tables for
; EdgeStepF, and EdgeOver back. The flags are kept.
	MACHINE	68020
EdgeUnder
	move.w	ccr,-(a7)
	tst.b	$18ea.w
	bne.b	.no
	tst.b	$18eb.w
	bne.b	.no
	cmpi.w	#$7d00,$18dc.w	; 256 rows down from the table base
	bhs.b	.no			; stay in the tables
	movem.l	d0/a0-a1,-(a7)
	lea	($7900).w,a0
	move.l	edgedelta(pc),a1
	adda.l	a0,a1
	lea	under(pc),a0
	st	(a0)
	lea	($7900).w,a0
	bra.b	EdgeCopy
.no	move.w	(a7)+,ccr
	rts
EdgeOver
	move.w	ccr,-(a7)
	tst.b	under(pc)
	bne.b	.yes
	move.w	(a7)+,ccr
	rts
.yes	movem.l	d0/a0-a1,-(a7)
	lea	under(pc),a0
	sf	(a0)
	lea	($7900).w,a1
	move.l	edgedelta(pc),a0
	adda.l	a1,a0
EdgeCopy
	move.w	#$200/4-1,d0
.copy	move.l	(a0)+,(a1)+
	dbf	d0,.copy
	movem.l	(a7)+,d0/a0-a1
	move.w	(a7)+,ccr
	rts
	MACHINE	68000

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
