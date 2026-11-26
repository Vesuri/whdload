;======================================================================
; Enhanced resolution (CUSTOM5), resolution plan step 4: the display skeleton. The game's
; renderer is unchanged and still draws its 96x80 frame of 12-bit colour words into the
; copper-slot layout, but into two lists in fast memory (the area) that the copper never
; shows. At each of the game's three swaps (main loop, pause, level end and death) the
; finished frame goes through the palette's map to pens, 2x2 (small view) or 3x3 (full
; screen) into a chunky buffer, through the Kalms c2p (c2p.s) into the back one of two
; 8-plane chip screens, and is shown from the next field by switching COP1LC to that
; screen's copper head. Keypad Enter's view byte picks the size; a head is rebuilt when
; the view it was built for is not the current one.
;
; The heads replace the game's template ($9a080, chip hunk 1): the same DMACON and INTREQ
; (the frame wait's flag, COPER for the game's field server), FMODE, window and fetch,
; pens 0-15 and the sprite pointers copied from it, then the 240 pens (PA_PALETTE), the
; damage flash (COLOR00), 8 planes, and in the small view pen 15 on each line pair from
; HealthPal (the bars' colour); then they jump into the game's panel list, whose COP1LC
; points back at the head shown. The copper also sets INTREQ DSKBLK (no interrupt is
; enabled for it) at the top of each field: once it is set after a switch, the other
; screen is no longer shown and the next frame may be converted into it.
;
; The small view's screen rows are its 192 pixels (24 bytes, 160 rows, FMODE 3), so a
; plane is one run (modulo 0). Full screen's 288 pixels are delayed 16 by BPLCON1 to where
; the game's 320-pixel pattern has them, with pen 0 (the border, the flash) on either
; side as in the original. Below a 68040 its rows are 36 bytes (240 rows), so the c2p
; converts the frame in one call: FMODE 1, whose 32-pixel fetches make the same DDF
; $38-$b8 fetch 288 where FMODE 3 fetched 320. A 68040's c2p is bound by its Chip
; writes, and FMODE 1's display takes twice FMODE 3's slots (MEASURED 13.1 ms a frame
; against 17.5), so from the 68040 on the rows are 40 bytes at FMODE 3 and the c2p
; converts a row at a time (_ds_wide). The c2p's plane size is set for the view at each
; switch (_ds_geom).

SMALL_ROW	= 24			;bytes a screen row, SMALL_W / 8
FULL_ROW	= 36			;FULL_W / 8
SMALL_PLANE	= SMALL_ROW*160		;3840
FULL_PLANE	= FULL_ROW*240		;8640
WIDE_ROW	= 40			;from the 68040 on: 320 pixels
WIDE_PLANE	= WIDE_ROW*240		;9600
DS_SCREEN	= WIDE_PLANE*8
DS_HEAD		= $800			;a copper head
DS_SCREENS	= CHIPPOOL		;the two screens, then the two heads, above the chip pool
DS_HEADS	= DS_SCREENS+2*DS_SCREEN
DS_CHIP		= 2*DS_SCREEN+2*DS_HEAD
	IFNE	(DS_HEADS>>16)-((DS_HEADS+2*DS_HEAD-1)>>16)
	FAIL	the heads must share a high word: only COP1LCL is switched
	ENDC
	IFGT	CHIPPOOL+DS_CHIP-CHIPMEM
	FAIL	CHIPMEM is too small for the screens and heads
	ENDC

SMALL_W		= 192			;the views' chunky sizes
SMALL_H		= 160
FULL_W		= 288
FULL_H		= 240

; The game's lists keep the copper-slot layout (a pixel's colour word at fromPt + 4x + 4 more
; at each 32-pixel bank), with lines of DS_STRIDE bytes in place of 416: room for full
; screen's 288 pixels (9 banks of 132 bytes) on 240 lines, and one more: the writers draw
; row y at line y + 1. With LORES (both views 96x80) the small view's 192 and 160: the
; game's own sky runs there, whose unrolled displacements must fit a word.
; With PENS (resolution plan step 7; the release build, AlienBreed3D.s, but for WORDS,
; LORES and ORIGINAL) the writers write pen bytes instead, pixel x at
; fromPt + x, lines of FULL_W bytes in both views; the c2p reads the frame from the list,
; and fromPt is on a long (the list starts 2 bytes in).
	IFD	PENS
	IFND	PSTRIDE
PSTRIDE		= FULL_W
	ENDC
DS_STRIDE	= PSTRIDE
LIST_LINES	= FULL_H+1
	ELSE
	IFND	LORES
DS_STRIDE	= 9*132			;(pixel 287's word ends at 1182)
LIST_LINES	= FULL_H+1
	ELSE
DS_STRIDE	= 800
LIST_LINES	= SMALL_H+1
	ENDC
	ENDC
	IFD	PENS
LIST_OFF	= 2
	ELSE
LIST_OFF	= 0
	ENDC

; the area, past the palette's tables
DA_CHUNKY	= PA_END		;FULL_W * FULL_H pens; the c2p reads 4 bytes past a row
DA_C2PBUF	= DA_CHUNKY+FULL_W*FULL_H+16	;the c2p's FULL_W / 2 bytes
DA_INFO		= DA_C2PBUF+FULL_W/2	;for the tools: the frame last shown's
DI_STRIDE	= 0			;word: line stride of the list,
DI_W		= 2			;word: pixels a line,
DI_H		= 4			;word: lines,
DI_PENS		= 6			;long: its pens' first line (line 0),
DI_PROW		= 10			;word: and their line stride
DI_SIZE		= 12
DA_LISTS	= (PA_SQ+2*SQ_C+4+7)&-8	;past the palette build's scratch: the game's lists
LIST_SIZE	= DS_STRIDE*LIST_LINES	;each (InitCopperScrn's are 33296 bytes)
	IFD	PENS
DA_C2PFULL	= (DA_LISTS+LIST_OFF+2*LIST_SIZE+15)&-16	;full screen's c2p scratch
	IFGT	DA_C2PFULL+FULL_W*FULL_H/2-PA_SIZE
	FAIL	the area is too small for full screen's c2p scratch
	ENDC
	ENDC
	IFGT	DA_LISTS+LIST_OFF+2*LIST_SIZE-PA_SIZE
	FAIL	the area is too small for the copper lists
	ENDC
	IFGT	DA_INFO+DI_SIZE-DA_LISTS
	FAIL	the chunky buffer overlaps the copper lists
	ENDC

; game offsets, hunk 0 of the $c4dc version
G_TEMPLATEPTR	= $2ea8			;move.l #template,d0 at $2ea6: the template's address
G_LEVELCOP	= $31a0			;level start: move.l #template,$dff080 (10 bytes)
G_VIEWFLAG	= $40279		;keypad Enter's byte: 0 the small view, else full screen
G_LIST1		= $43c38		;the two copper lists' pointers
G_LIST2		= $43c3c
G_COPLISTS	= $4463e		;InitCopperScrn's first AllocMem
; chip hunk 1, from the template ($9a080)
T_DIW		= $9a08c-$9a080		;DIWSTRT, DIWSTOP, DDFSTRT, DDFSTOP
T_PENS		= $9a09c-$9a080		;pens 0-15 in both nibbles, then SPR0-7PT: 50 moves
T_HITCOL	= $9a1fe-$9a080		;COLOR00's value: the damage flash
T_PANEL		= $9a262-$9a080		;the panel list: COP1LCH, COP1LCL first
T_HEALTHPAL	= $93f5c-$9a080		;80 words: the bars' colour on each view line

; a head, by offset
HD_PAL		= 4*(3+4+50)		;the 240 pens
HD_FLASH	= HD_PAL+4+4*16+7*(4+4*32)+4+2	;COLOR00's value
SMALL_BARS	= $2bdffffe		;WAIT: pen 15 for line pair 0 at the end of line $2b
SMALL_END	= $c9dffffe		;WAIT: the panel right after the last bar, as the game's
FULL_END	= $1801fffe		;WAIT after $ffdf: display off from line $118, as the game's

;----------------------------------------------------------------------
; PL_PS at $4463e (InitCopperScrn, then PL_S past both AllocMems): the game's two copper
; lists go in the area, past the palette build's scratch. Their FreeMem ($43c40) is an rts.
_p_coplists
	move.l	(sp),d0
	subi.l	#G_COPLISTS+6,d0
	movea.l	d0,a0			;hunk 0
	movea.l	_expmem(pc),a1
	adda.l	#PA_OFF+DA_LISTS+LIST_OFF,a1
	move.l	a1,d0
	adda.l	#G_LIST1,a0
	move.l	d0,(a0)+		;G_LIST1, G_LIST2
	addi.l	#LIST_SIZE,d0
	move.l	d0,(a0)
	movea.l	(4).w,a6		;as after AllocMem
	rts

; From _p_loaded, at each level's load (a5 = hunk 0, a4 = the area): the writers' row
; tables, lines of 416 bytes, to lines of DS_STRIDE (a table whose step is no longer 416
; is done; the immediates are stride.s's, in the patch list).
_ds_stride
	lea	_ds_hunk0(pc),a0
	move.l	a5,(a0)
	IFND	LORES
	bsr.w	_ds_tables
	ENDC
	lea	.tables(pc),a1
.table	move.l	(a1)+,d0		;game offset; 0 ends
	beq.s	.done
	lea	(a5,d0.l),a0
	move.w	(a1)+,d1		;longs
	subq.w	#1,d1
	move.l	4(a0),d0
	sub.l	(a0),d0
	cmp.l	#416,d0
	bne.s	.table
.entry	move.l	(a0),d0
	divu.w	#416,d0
	mulu.w	#DS_STRIDE,d0
	move.l	d0,(a0)+
	dbf	d1,.entry
	bra.s	.table
.done	movea.l	_resload(pc),a2
	jmp	resload_FlushCache(a2)
.tables	dc.l	$1cbe2			;timeslarge: walls, (y + 1) lines
	dc.w	80
	dc.l	$1cf6a			;timeslargethru: see-through walls
	dc.w	80
	dc.l	$22214			;dopoly's rows, (y + 1) lines; glass and bitmaps too
	dc.w	90
	dc.l	$224b6			;dopolyg's
	dc.w	90
	dc.l	$2276e			;dopolyh's, y lines
	dc.w	90
	dc.l	0

; PL_PS at $31a0 (level start; PL_S past the rest): the heads instead of the template.
; Both screens cleared, both heads built, head 0 shown.
_p_cop1
	movem.l	d0-d7/a0-a6,-(sp)
	movea.l	60(sp),a5
	suba.l	#G_LEVELCOP+6,a5
	lea	_ds_hunk0(pc),a0
	move.l	a5,(a0)
	GLEA	G_TEMPLATEPTR,a0
	movea.l	(a0),a3
	lea	_ds_template(pc),a0
	move.l	a3,(a0)
	movea.l	_expmem(pc),a4
	adda.l	#PA_OFF,a4
	lea	DS_SCREENS,a0
	move.w	#2*DS_SCREEN/16-1,d0
.clr	clr.l	(a0)+
	clr.l	(a0)+
	clr.l	(a0)+
	clr.l	(a0)+
	dbf	d0,.clr
	lea	_ds_hview(pc),a0
	move.w	#-1,(a0)
	bsr.w	_ds_view
	bsr.w	_ds_geom
	moveq	#0,d6
	bsr.w	_ds_build
	moveq	#1,d6
	bsr.w	_ds_build
	lea	_ds_back(pc),a0
	move.w	#1,(a0)
	move.l	#DS_HEADS,d0
	move.l	d0,$dff080
	move.w	d0,T_PANEL+6(a3)
	swap	d0
	move.w	d0,T_PANEL+2(a3)
	move.w	#$0002,$dff09c		;DSKBLK: the field flag
	movem.l	(sp)+,d0-d7/a0-a6
	rts

; PL_PS at $32d2, $3e42 and $8e5e, the swaps' move.l d0,$dff084: d0 = the finished list
; (the game's new oldDrawPt). Shown on the back screen from the next field on.
_p_show
	movem.l	d0-d7/a0-a6,-(sp)
	movea.l	d0,a6
	movea.l	_ds_hunk0(pc),a5
	movea.l	_ds_template(pc),a3
	movea.l	_expmem(pc),a4
	adda.l	#PA_OFF,a4
	bsr.w	_ds_wait
	moveq	#0,d7
	move.b	_ds_gview(pc),d7	;the view this frame was drawn for
	move.w	_ds_back(pc),d6
	bsr.w	_ds_build
	bsr.w	_ds_info
	IFD	PENS
	lea	10(a6),a0		;line 0 black: no writer draws it (black's pen, not
	movea.l	_expmem(pc),a1		;pen 0, the border, which the damage flash sets)
	adda.l	#PA_OFF,a1
	moveq	#0,d0
	move.b	PA_MAP(a1),d0
	move.l	d0,d1
	lsl.l	#8,d1
	or.l	d1,d0
	move.l	d0,d1
	swap	d1
	or.l	d1,d0
	moveq	#DS_STRIDE/4-1,d1
.black	move.l	d0,(a0)+
	dbf	d1,.black
	ELSE
	IFND	LORES
	bsr.w	_ds_one
	ELSE
	tst.b	d7
	bne.s	.lfull
	bsr.w	_ds_small
	bra.s	.lsmall
.lfull	bsr.w	_ds_full
.lsmall
	ENDC
	ENDC
	tst.b	d7
	bne.s	.full
	move.l	#SMALL_W,d5
	move.w	#SMALL_H-1,d4
	moveq	#SMALL_ROW,d3
	bra.s	.c2p
.full	move.l	#FULL_W,d5
	move.w	#FULL_H-1,d4
	moveq	#FULL_ROW,d3
	bsr.w	_ds_wide
	beq.s	.c2p
	moveq	#WIDE_ROW,d3
.c2p	lea	c2p1x1_8_c5_030_2_pixels(pc),a0
	move.l	d5,(a0)
	lea	c2p1x1_8_c5_030_2_fastbuf(pc),a0
	PALEA	DA_C2PBUF,a1
	move.l	a1,(a0)
	IFD	PENS
	lea	10(a6),a2		;the frame itself
	move.l	#DS_STRIDE,d5
	tst.b	d7			;full screen's lines are its rows (DS_STRIDE =
	beq.s	.rows			;FULL_W): below a 68040 one call for the frame
	bsr.w	_ds_wide
	bne.s	.rows
	move.l	#FULL_W*FULL_H,c2p1x1_8_c5_030_2_pixels-c2p1x1_8_c5_030_2_fastbuf(a0)
	PALEA	DA_C2PFULL,a1
	move.l	a1,(a0)
	moveq	#0,d4
.rows
	ELSE
	PALEA	DA_CHUNKY,a2
	ENDC
	move.w	_ds_back(pc),d6
	bsr.w	_ds_addr
	movea.l	a1,a6
.row	movea.l	a2,a0
	movea.l	a6,a1
	bsr.w	c2p1x1_8_c5_030_2
	adda.l	d5,a2
	adda.w	d3,a6
	dbf	d4,.row
	move.w	_ds_back(pc),d6		;the switch
	bsr.w	_ds_addr
	movea.l	_ds_template(pc),a3
	move.w	T_HITCOL(a3),HD_FLASH(a0)
	move.l	a0,d0
	move.w	d0,$dff082		;COP1LCL
	move.w	d0,T_PANEL+6(a3)
	move.w	#$0002,$dff09c		;DSKBLK, which the head sets
	lea	_ds_back(pc),a0
	eori.w	#1,(a0)
	movea.l	_ds_hunk0(pc),a5	;(the convert uses a5)
	bsr.w	_ds_view		;the next frame is drawn for the view now asked
	cmp.b	_ds_gview(pc),d7
	beq.s	.same
	bsr.w	_ds_geom
.same
	IFD	HOLES			;debug: $f0f in every pixel of the list drawn next
	movea.l	_ds_hunk0(pc),a5	;(with PENS pen 1, which no writer writes: ab3d.py
	GLEA	$5dd40,a0		;shows it as $f0f; HOLES=2: pen PEN0's colour, which
	movea.l	(a0),a0			;is its pen's exactly, for comparing with WORDS: the
	lea	10(a0),a0		;water reads pixels not yet drawn)
	movea.l	_expmem(pc),a4
	adda.l	#PA_OFF,a4
	IFD	PENS
	IFEQ	HOLES-2
	moveq	#PEN0,d0
	ELSE
	moveq	#1,d0
	ENDC
	move.l	#LIST_LINES*DS_STRIDE,d4
.hl	move.b	d0,(a0)+
	subq.l	#1,d4
	bne.s	.hl
	ELSE
	move.w	#$0f0f,d0
	IFEQ	HOLES-2
	move.w	PA_PALETTE(a4),d0
	ENDC
	move.w	#LIST_LINES-1,d4
.hl	moveq	#DS_STRIDE/132-1,d5
.hb	moveq	#32-1,d6
.hp	move.w	d0,(a0)
	addq.l	#4,a0
	dbf	d6,.hp
	addq.l	#4,a0
	dbf	d5,.hb
	lea	DS_STRIDE-DS_STRIDE/132*132(a0),a0
	dbf	d4,.hl
	ENDC
	ENDC
	movem.l	(sp)+,d0-d7/a0-a6
	rts

; d7 = the view: 0 small, 1 full screen (a5 = hunk 0)
_ds_view
	GLEA	G_VIEWFLAG,a0
	moveq	#0,d7
	tst.b	(a0)
	beq.s	.small
	moveq	#1,d7
.small	rts

; d6 = 0, 1: a1 = that screen, a0 = its head
_ds_addr
	lea	DS_SCREENS,a1
	lea	DS_HEADS,a0
	tst.w	d6
	beq.s	.first
	adda.l	#DS_SCREEN,a1
	lea	DS_HEAD(a0),a0
.first	rts

; Until the head switched to last has started (it sets DSKBLK), or about two fields.
_ds_wait
	lea	$dff000,a0
	moveq	#4,d1			;line wraps (at 256 and at the end of the field)
	move.b	6(a0),d0
.w	btst	#1,$1f(a0)
	bne.s	.done
	move.b	6(a0),d2
	cmp.b	d0,d2
	bhs.s	.same
	subq.w	#1,d1
	beq.s	.done
.same	move.b	d2,d0
	bra.s	.w
.done	rts

; ne from the 68040 on: full screen's rows are 40 bytes, a row converted at a time
_ds_wide
	btst	#AFB_68040,_attnflags+3(pc)
	rts

; d6 = head (0, 1), d7 = view: built unless it already is for this view
; (a3 = template, a4 = area)
_ds_build
	lea	_ds_hview(pc),a0
	cmp.b	(a0,d6.w),d7
	beq.w	.done
	move.b	d7,(a0,d6.w)
	bsr.w	_ds_addr
	move.l	#$00968020,(a0)+	;DMACON: sprites on
	move.l	#$009c8013,(a0)+	;INTREQ: the frame wait's flag, COPER, DSKBLK
	move.l	#$01fc000f,d0		;FMODE: sprites 64 wide, planes 64 bits a fetch,
	tst.b	d7
	beq.s	.fmode
	bsr.w	_ds_wide
	bne.s	.fmode
	move.w	#$000d,d0		;full screen below a 68040 32
.fmode	move.l	d0,(a0)+
	lea	T_DIW(a3),a2
	moveq	#4-1,d0
.diw	move.l	(a2)+,(a0)+
	dbf	d0,.diw
	lea	T_PENS(a3),a2
	moveq	#50-1,d0
.pens	move.l	(a2)+,(a0)+
	dbf	d0,.pens
	lea	PA_PALETTE(a4),a2	;HD_PAL: pens 16-31 in bank 0, then banks 1-7
	move.l	#$01060c42,(a0)+
	move.w	#$01a0,d1
	moveq	#16-1,d0
.b0	move.w	d1,(a0)+
	move.w	(a2)+,(a0)+
	addq.w	#2,d1
	dbf	d0,.b0
	move.l	#$01062c42,d2
	moveq	#7-1,d3
.bank	move.l	d2,(a0)+
	move.w	#$0180,d1
	moveq	#32-1,d0
.pen	move.w	d1,(a0)+
	move.w	(a2)+,(a0)+
	addq.w	#2,d1
	dbf	d0,.pen
	addi.w	#$2000,d2
	dbf	d3,.bank
	move.l	#$01060c42,(a0)+
	move.w	#$0180,(a0)+		;HD_FLASH
	move.w	T_HITCOL(a3),(a0)+
	move.l	#$01000211,(a0)+	;BPLCON0: 8 planes
	move.l	#$01020000,d0		;BPLCON1
	moveq	#0,d1			;the modulo
	move.l	#SMALL_PLANE,d3
	tst.b	d7
	beq.s	.con1
	move.w	#$4400,d0		;full screen: 16 pixels later,
	lea	FULL_ROW(a1),a1		;and from the second row: the game's rows of three
	move.l	#FULL_PLANE,d3
	bsr.w	_ds_wide
	beq.s	.con1
	lea	WIDE_ROW-FULL_ROW(a1),a1
	move.l	#WIDE_PLANE,d3
.con1	move.l	d0,(a0)+
	move.l	#$010c0000,(a0)+	;BPLCON4
	move.w	#$0108,(a0)+
	move.w	d1,(a0)+
	move.w	#$010a,(a0)+
	move.w	d1,(a0)+
	move.l	a1,d0
	move.w	#$00e0,d1
	moveq	#8-1,d2
.bpl	swap	d0
	move.w	d1,(a0)+
	move.w	d0,(a0)+
	addq.w	#2,d1
	swap	d0
	move.w	d1,(a0)+
	move.w	d0,(a0)+
	addq.w	#2,d1
	add.l	d3,d0
	dbf	d2,.bpl
	move.l	#$1001ff00,(a0)+	;WAIT line $10
	move.l	#$009c0011,(a0)+	;INTREQ: the flag and COPER off
	tst.b	d7
	bne.s	.full
	lea	T_HEALTHPAL(a3),a2
	move.l	#SMALL_BARS,d0
	moveq	#SMALL_H/2-1,d2
.bar	move.l	d0,(a0)+
	move.w	#$019e,(a0)+		;COLOR15
	move.w	(a2)+,(a0)+
	addi.l	#$02000000,d0
	dbf	d2,.bar
	move.l	#SMALL_END,(a0)+
	bra.s	.panel
.full	move.l	#$ffdffffe,(a0)+
	move.l	#FULL_END,(a0)+
.panel	lea	T_PANEL(a3),a2
	move.l	a2,d0
	swap	d0
	move.w	#$0080,(a0)+
	move.w	d0,(a0)+
	swap	d0
	move.w	#$0082,(a0)+
	move.w	d0,(a0)+
	move.l	#$00880000,(a0)+	;COPJMP1
	move.l	#$fffffffe,(a0)+
.done	rts

; d7 = the view: its frame's geometry into DA_INFO, for the tools
; (a6 = its list)
_ds_info
	PALEA	DA_INFO,a0
	move.w	#DS_STRIDE,(a0)+
	move.l	#96<<16|80,(a0)
	IFND	LORES
	move.l	#SMALL_W<<16|SMALL_H,(a0)
	tst.b	d7
	beq.s	.small
	move.l	#FULL_W<<16|FULL_H,(a0)
.small
	ENDC
	IFD	PENS
	lea	10(a6),a1
	move.l	a1,4(a0)
	move.w	#DS_STRIDE,8(a0)
	ELSE
	PALEA	DA_CHUNKY,a1
	move.l	a1,4(a0)
	move.w	(a0),8(a0)		;DI_W
	ENDC
	rts

; d7 = the view the next frame is drawn for: each geometry site of _ds_sites gets its value
; for it, in the game's code, and the caches are flushed (a5 = hunk 0)
_ds_geom
	movem.l	d0-d1/a0-a2,-(sp)
	lea	_ds_gview(pc),a0
	move.b	d7,(a0)
	IFND	LORES
	lea	_ds_scale(pc),a0
	move.w	#2,(a0)
	add.w	d7,(a0)			;S
	ENDC
	lea	_ds_sites(pc),a0
.site	move.l	(a0)+,d0		;size << 24 | game offset; 0 ends
	beq.s	.done
	move.l	d0,d1
	andi.l	#$ffffff,d1
	lea	(a5,d1.l),a1
	rol.l	#8,d0
	move.l	(a0)+,d1		;the small view's value
	tst.b	d7
	beq.s	.small
	move.l	(a0),d1			;full screen's
.small	addq.l	#4,a0
	subq.b	#2,d0
	bcs.s	.byte
	beq.s	.word
	move.l	d1,(a1)
	bra.s	.site
.word	move.w	d1,(a1)
	bra.s	.site
.byte	move.b	d1,(a1)
	bra.s	.site
.done	move.w	#SMALL_PLANE,d0		;the c2p's plane size (c2p.s: Kalms' smcinit)
	tst.b	d7
	beq.s	.plane
	move.w	#FULL_PLANE,d0
	bsr.w	_ds_wide
	beq.s	.plane
	move.w	#WIDE_PLANE,d0
.plane	lea	c2p1x1_8_c5_030_2_smc1(pc),a0
	move.w	d0,(a0)
	lea	c2p1x1_8_c5_030_2_smc2(pc),a0
	move.w	d0,(a0)
	lea	c2p1x1_8_c5_030_2_smc5(pc),a0
	move.w	d0,(a0)
	lea	c2p1x1_8_c5_030_2_smc8(pc),a0
	move.w	d0,(a0)
	lea	c2p1x1_8_c5_030_2_smc11(pc),a0
	move.w	d0,(a0)
	move.w	d0,d1
	neg.w	d1
	subq.w	#4,d1
	lea	c2p1x1_8_c5_030_2_smc3(pc),a0
	move.w	d1,(a0)
	lea	c2p1x1_8_c5_030_2_smc6(pc),a0
	move.w	d1,(a0)
	lea	c2p1x1_8_c5_030_2_smc9(pc),a0
	move.w	d1,(a0)
	lea	c2p1x1_8_c5_030_2_smc12(pc),a0
	move.w	d1,(a0)
	add.w	d0,d0
	lea	c2p1x1_8_c5_030_2_smc4(pc),a0
	move.w	d0,(a0)
	lea	c2p1x1_8_c5_030_2_smc10(pc),a0
	move.w	d0,(a0)
	andi.l	#$ffff,d0
	add.l	d0,d0
	lea	c2p1x1_8_c5_030_2_smc7(pc),a0
	move.l	d0,(a0)
	movea.l	_resload(pc),a2
	jsr	resload_FlushCache(a2)
	movem.l	(sp)+,d0-d1/a0-a2
	rts

	IFD	LORES
; The frame at a6 + 10 (the first colour word; a line is DS_STRIDE bytes, a pixel 4, and 4
; more at each 32-pixel bank) to pens, each 2x2 or 3x3, into the chunky buffer.
_ds_small
	lea	10(a6),a0
	PALEA	DA_CHUNKY,a1
	lea	PA_MAP(a4),a2
	move.w	#$0fff,d3
	moveq	#80-1,d4
.line	moveq	#3-1,d5
.bank	moveq	#32-1,d6
.px	move.w	(a0),d0
	addq.l	#4,a0
	and.w	d3,d0
	move.b	(a2,d0.w),d1
	move.b	d1,(a1)+
	move.b	d1,(a1)+
	dbf	d6,.px
	addq.l	#4,a0
	dbf	d5,.bank
	lea	DS_STRIDE-3*(4+32*4)(a0),a0
	lea	-SMALL_W(a1),a5
	moveq	#SMALL_W/4-1,d6
.dup	move.l	(a5)+,(a1)+
	dbf	d6,.dup
	dbf	d4,.line
	rts

_ds_full
	lea	10(a6),a0
	PALEA	DA_CHUNKY,a1
	lea	PA_MAP(a4),a2
	move.w	#$0fff,d3
	moveq	#80-1,d4
.line	moveq	#3-1,d5
.bank	moveq	#32-1,d6
.px	move.w	(a0),d0
	addq.l	#4,a0
	and.w	d3,d0
	move.b	(a2,d0.w),d1
	move.b	d1,(a1)+
	move.b	d1,(a1)+
	move.b	d1,(a1)+
	dbf	d6,.px
	addq.l	#4,a0
	dbf	d5,.bank
	lea	DS_STRIDE-3*(4+32*4)(a0),a0
	lea	-FULL_W(a1),a5
	move.w	#2*FULL_W/4-1,d6
.dup	move.l	(a5)+,(a1)+
	dbf	d6,.dup
	dbf	d4,.line
	rts
	ELSE

; d7 = the view: its frame at 1x1, 192x160 or 288x240 words, to pens.
_ds_one
	lea	10(a6),a0
	PALEA	DA_CHUNKY,a1
	lea	PA_MAP(a4),a2
	moveq	#SMALL_W/32-1,d2
	move.w	#SMALL_H-1,d4
	tst.b	d7
	beq.s	.go
	moveq	#FULL_W/32-1,d2
	move.w	#FULL_H-1,d4
.go	moveq	#0,d3			;line 0 black, as the original's: no writer draws
.line	movea.l	a0,a5			;it, and the builders' moves are in it
	move.w	d2,d5
.bank	moveq	#32-1,d6
.px	move.w	(a0),d0
	addq.l	#4,a0
	and.w	d3,d0
	move.b	(a2,d0.w),(a1)+
	dbf	d6,.px
	addq.l	#4,a0
	dbf	d5,.bank
	lea	DS_STRIDE(a5),a0
	move.w	#$0fff,d3
	dbf	d4,.line
	rts
	ENDC

_ds_hunk0	dc.l	0
_ds_template	dc.l	0
_ds_back	dc.w	0		;the screen and head to convert into next
_ds_hview	dc.b	-1,-1		;the view each head was built for
_ds_gview	dc.b	0		;the view the game's geometry is set for
	EVEN

; The geometry sites: where the game's code has the view's size, and each view's value.
; SITE SIZE (1, 2, 4), game offset, the 192x160 value, the 288x240 value, the 96x80 value
; (the original's), which both views take with LORES.
SITE	MACRO
	dc.l	\1<<24|\2
	IFND	LORES
	dc.l	\3,\4
	ELSE
	dc.l	\5,\5
	ENDC
	ENDM
_ds_sites
	INCLUDE	sites.s			;(with LORES both views take the 96x80 values)
	dc.l	0

	IFND	LORES
	INCLUDE	hires.s
	ENDC

BPLSIZE		= SMALL_PLANE		;(_ds_geom sets the view's)
CHUNKYXMAX	= FULL_W
CHUNKYYMAX	= 1
	INCLUDE	c2p.s
