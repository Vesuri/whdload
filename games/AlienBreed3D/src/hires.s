;----------------------------------------------------------------------
; The 1x1 renderer (resolution plan steps 5 and 6): the game's own writers draw the small
; view at 192x160 and full screen at 288x240, S = 2 and 3 times the original's 96x80 in
; both directions. Most of the geometry is in _ds_sites (sites.s: each view's value of an
; immediate); what a constant cannot express is here, patched at the game offsets given
; (AlienBreed3D.s): the writers' row and column addressing for any width, every height
; above or below the eye and every x times S before its divide, the texture steps divided
; by S, and S x S writers of our own for the gun, the sky and the pause screen's letters,
; which draw from fixed-size images, and the water tint.

; the area, past DA_INFO: tables for 288 columns and 241 lines, both views
DA_SLOT		= DA_INFO+DI_SIZE	;288 words: a pixel's offset in its line, 4x + 4(x / 32)
DA_YTAB		= DA_SLOT+2*FULL_W	;241 longs: (y + 1) lines
DA_ACROSS	= DA_YTAB+4*(FULL_H+1)	;doacrossline for 288: move.w d0,n(a3) each, then rts
DA_EDGES	= (DA_ACROSS+4*FULL_W+2+3)&-4	;the polygons' edges, top then bottom,
					;8 bytes a column, EDGE_STRIDE apart
EDGE_STRIDE	= 8*300			;(the game's are $28b46 and $29146, 1536 apart: at
					;192 columns its writes of column 192, past the
					;right clip, land on the bottom's column 0 and on
					;the objects' graphics table at $2974a)
DA_SIDES	= DA_EDGES+2*EDGE_STRIDE	;the floors' leftsidetab, rightsidetab,
SIDE_STRIDE	= 2*256			;leftbrighttab, rightbrighttab: a word a line, each
					;(the game's at $1db5a, 180 lines, 360 bytes apart)
DA_END		= DA_SIDES+4*SIDE_STRIDE
	IFGT	DA_END-DA_LISTS
	FAIL	the 1x1 tables overlap the copper lists
	ENDC

; game offsets (hunk 0) of the variables read here (G_SKY, G_BRIGHTEN: palette.s)
G_FROMPT	= $5dd48		;fromPt: the list being drawn
G_EYE		= $61d54		;the eye's height (long, as the objects' heights)
G_WALLTOP	= $1ca28		;a wall's top and bottom (longs)
G_WALLBOT	= $1ca2c
G_RIGHT		= $1f9f4		;FloorLine: the span's right edge (word)
G_ANGLE		= $18ff2		;the view's angle (word; the sky's column)
G_SKYEND	= $5dd40		;the sky's end (G_SKY, palette.s)
G_XSHIFT	= $5d8c			;the eye's x shift, added to x * 128 (long)

G_FONT		= $4414			;the pause screen's letters, 8x8 colour words each
G_PAUSETEXT	= $433c			;its text, 12 letters a row
G_PAUSESRC	= $41aa			;pointers: the frame shown, the list drawn into
G_PAUSEDST	= $41ae

; \1 (a data register, long) times S: 2 in the small view, 3 in full screen. Flags not kept.
TIMESS	MACRO
	tst.b	_ds_gview(pc)
	bne.s	.\@f
	add.l	\1,\1
	bra.s	.\@e
.\@f	move.l	\1,-(sp)
	add.l	\1,\1
	add.l	(sp)+,\1
.\@e
	ENDM

; \1 (a data register, long, signed) divided by S. Flags not kept.
BYS	MACRO
	tst.b	_ds_gview(pc)
	bne.s	.\@f
	asr.l	#1,\1
	bra.s	.\@e
.\@f	divs.l	#3,\1
.\@e
	ENDM

; Jump to a game offset, every register and the flags kept.
JMPG	MACRO
	subq.l	#4,sp
	move.l	a0,-(sp)
	movea.l	_ds_hunk0(pc),a0
	adda.l	#\1,a0
	move.l	a0,4(sp)
	movea.l	(sp)+,a0
	rts
	ENDM

; Game address of a game offset into an address register.
HUNK	MACRO
	movea.l	_ds_hunk0(pc),\2
	adda.l	#\1,\2
	ENDM

; a pixel: a colour word, or with PENS a pen byte (display.s); PX1 the next pixel's offset in
; a bank
	IFD	PENS
PX	MACRO
	move.b	\1,\2
	ENDM
PX1		= 1
	ELSE
PX	MACRO
	move.w	\1,\2
	ENDM
PX1		= 4
	ENDC

; From _ds_stride (a5 = hunk 0, a4 = the area), at each level's load: the tables (the
; palette build's scratch has overwritten them), and the game's absolute pointers to its
; own 96-wide ones pointed at them.
_ds_tables
	lea	_ds_frompt(pc),a0
	movea.l	a5,a1
	adda.l	#G_FROMPT,a1
	move.l	a1,(a0)
	lea	_ds_eye(pc),a0
	movea.l	a5,a1
	adda.l	#G_EYE,a1
	move.l	a1,(a0)
	lea	_ds_slot(pc),a0
	PALEA	DA_SLOT,a1
	move.l	a1,(a0)
	PALEA	DA_SLOT,a0
	moveq	#0,d0
.slot	move.w	d0,d1
	IFND	PENS
	lsr.w	#5,d1
	add.w	d0,d1
	add.w	d1,d1
	add.w	d1,d1
	ENDC
	move.w	d1,(a0)+
	addq.w	#1,d0
	cmp.w	#FULL_W,d0
	blo.s	.slot
	PALEA	DA_YTAB,a0
	move.l	#DS_STRIDE,d0
	move.w	#FULL_H,d1
.ytab	move.l	d0,(a0)+
	addi.l	#DS_STRIDE,d0
	dbf	d1,.ytab
	PALEA	DA_ACROSS,a0
	PALEA	DA_SLOT,a1
	move.w	#FULL_W-1,d1
	IFND	PENS
.across	move.w	#$3740,(a0)+		;move.w d0,n(a3)
	ELSE
.across	move.w	#$1740,(a0)+		;move.b d0,n(a3)
	ENDC
	move.w	(a1)+,(a0)+
	dbf	d1,.across
	move.w	#$4e75,(a0)		;rts
	lea	.ptrs(pc),a1
.ptr	move.l	(a1)+,d0		;the operand's game offset; 0 ends
	beq.s	.done
	move.l	(a1)+,d1		;the table's area offset
	add.l	a4,d1
	move.l	d1,(a5,d0.l)
	bra.s	.ptr
.done
	IFD	PENS
	bra.w	_t_pens
	ENDC
	rts				;(_ds_stride flushes the caches)
.ptrs	dc.l	$1f3e8,DA_ACROSS	;SimpleFloorLine: movea.l #doacrossline,a1
	dc.l	$8af2,DA_SLOT		;light beams: movea.l #the slot table ($21b74),a1
	dc.l	$2159e,DA_SLOT		;glass
	dc.l	$219aa,DA_SLOT		;bitmaps
	dc.l	$2207e,DA_SLOT		;textured polygons (a2)
	dc.l	$21536,DA_YTAB		;glass: movea.l #the rows ($22214),a6
	dc.l	$21954,DA_YTAB		;bitmaps
	dc.l	$228fc,DA_EDGES		;polygons' edges: movea.l #the top ($28b46),a4
	dc.l	$22b7c,DA_EDGES
	dc.l	$2203e,DA_EDGES+EDGE_STRIDE	;and #the bottom ($29146), the drawers'
	dc.l	$22a24,DA_EDGES+EDGE_STRIDE	;(which read the top at -EDGE_STRIDE: the
	dc.l	$22cc6,DA_EDGES+EDGE_STRIDE	;displacements are AlienBreed3D.s's)
	dc.l	$1d676,DA_SIDES		;floors' edges: movea.l #leftsidetab ($1db5a),a3
	dc.l	$1d8da,DA_SIDES
	dc.l	$1f0b2,DA_SIDES		;(a4)
	dc.l	$1d660,DA_SIDES+SIDE_STRIDE	;#rightsidetab ($1dcc2); the displacements
	dc.l	$1d8c0,DA_SIDES+SIDE_STRIDE	;to the others are AlienBreed3D.s's
	dc.l	0

; PL_PS at $1a616 and $1a3ac (walls, see-through walls), over movea.l fromPt,a3 and adda.w
; (XTOCOPX,pc,d0.w*2),a3: column d0's slot (d1 is loaded next)
_t_column
	movea.l	_ds_frompt(pc),a3
	movea.l	(a3),a3
	IFD	PENS
	adda.w	d0,a3
	ELSE
	move.w	d0,d1
	lsr.w	#5,d1
	add.w	d0,d1
	add.w	d1,d1
	add.w	d1,d1
	adda.w	d1,a3
	ENDC
	rts

; PL_PS at $1cb8a and $1cf18 (a wall strip), over adda.l (timeslarge,pc,d5.w*4),a3, move.w
; d5,d4 and the two consttab reads: line d5 + 1, and the texture step (16.16) divided by S
; for S times the lines; the start is the same.
_t_strip
	move.w	d5,d4
	addq.w	#1,d4
	mulu.w	#DS_STRIDE,d4
	adda.l	d4,a3
	move.w	d5,d4
	move.l	4(a1,d2.w*8),d0
	move.l	(a1,d2.w*8),d2
	BYS	d2
	rts

; PL_PS at $1d13a, $1b3b0 (sub.l d6,top) and $1d146, $1b3b6 (sub.l d6,bottom): a wall's
; top and bottom less the eye (d6), times S
_t_walltop
	move.l	a0,-(sp)
	HUNK	G_WALLTOP,a0
	bra.s	_t_wallh
_t_wallbot
	move.l	a0,-(sp)
	HUNK	G_WALLBOT,a0
_t_wallh
	sub.l	d6,(a0)
	move.l	d6,-(sp)
	move.l	(a0),d6
	TIMESS	d6
	move.l	d6,(a0)
	move.l	(sp)+,d6
	movea.l	(sp)+,a0
	rts

; PL_PS over sub.l eye,d6 (glass and bitmaps' zone clips, $2142e $21452 $21770 $21794) and
; sub.l eye,d2 (their height, $2147a $21864; a polygon's, $21e28): times S
_t_eye6
	move.l	a0,-(sp)
	movea.l	_ds_eye(pc),a0
	sub.l	(a0),d6
	movea.l	(sp)+,a0
	TIMESS	d6
	rts
_t_eye2
	move.l	a0,-(sp)
	movea.l	_ds_eye(pc),a0
	sub.l	(a0),d2
	movea.l	(sp)+,a0
	TIMESS	d2
	rts

; PL_PS at $2149a and $21884 (glass, bitmaps; over asl.w #7,d3, asl.w #7,d4 and their
; divs.w d1 by the distance): the half sizes, times S after the divide (an 8-bit size
; shifted 8 would be negative in the word). The game doubles them into the width and
; height, a word: an object so close that they do not fit (the original's at under 1/S
; of our distance) is dropped, a half width of -$1000 putting its
; left edge past the right clip, which the game's next check skips. Else the width wraps,
; the column loop runs on for thousands of columns and its writes land anywhere in memory
; (a corpse walked over overwrote its own graphics).
_t_size
	asl.w	#7,d3
	asl.w	#7,d4
	divs.w	d1,d3
	divs.w	d1,d4
	tst.b	_ds_gview(pc)
	bne.s	.full
	cmp.w	#$3fff/2,d3		;(unsigned: a negative one is dropped too)
	bhi.s	.drop
	cmp.w	#$3fff/2,d4
	bhi.s	.drop
	add.w	d3,d3
	add.w	d4,d4
	rts
.full	cmp.w	#$3fff/3,d3
	bhi.s	.drop
	cmp.w	#$3fff/3,d4
	bhi.s	.drop
	move.w	d3,-(sp)
	add.w	d3,d3
	add.w	(sp)+,d3
	move.w	d4,-(sp)
	add.w	d4,d4
	add.w	(sp)+,d4
	rts
.drop	move.w	#-$1000,d3
	rts

; PL_PS at $84aa and $8a76 (the level's and the objects' points, over asl.l #7,d2 and
; add.l $5d8c,d2): x * 128 * S, then the eye's x shift as the game's.
_t_x128
	asl.l	#7,d2
	TIMESS	d2
	move.l	a0,-(sp)
	HUNK	G_XSHIFT,a0
	add.l	(a0),d2
	movea.l	(sp)+,a0
	rts

; PL_PS at $1fb96 (FloorLine, over muls.l d6,d3:d1, asr.l #6,d1, add.l d1,d4 and the same
; for d2 and d5; PL_S past them): the span's start at its left edge d6, the steps (the
; change over 96 pixels / 64) divided by S for S times the pixels.
_t_fstep
	muls.l	d6,d3:d1
	asr.l	#6,d1
	BYS	d1
	add.l	d1,d4
	muls.l	d6,d3:d2
	asr.l	#6,d2
	BYS	d2
	add.l	d2,d5
	rts

; PL_PS at $1fbc4 (over asr.l #6,d1, asr.l #6,d2 and movea.w d1,a4): the steps a pixel
_t_fstep2
	asr.l	#6,d1
	asr.l	#6,d2
	BYS	d1
	BYS	d2
	movea.w	d1,a4
	rts

; PL_PS at $214dc $214f6 (glass) and $218f8 $21914 (bitmaps), over swap d7, clr.w d7, swap
; d7 after the divide: the index into the step table (consttab, linear: step ~ (index + 1)
; / 256) divided by S, for S times the size.
_t_index
	andi.l	#$ffff,d7
	divu.w	_ds_scale(pc),d7
	andi.l	#$ffff,d7
	rts

; PL_PS at $21dd6 (a polygon object's vertices, over asr.l #8,d2, move.l d2,(a4)+ and ext.l
; d3; PL_S past asl.l #7,d3 and move.l d3,(a4)+): x / 256 and y * 128, each times S.
_t_pvert
	asr.l	#7,d2			;(x / 256) * 2
	tst.b	_ds_gview(pc)
	beq.s	.x
	move.l	d2,-(sp)		;* 3/2
	asr.l	#1,d2
	add.l	(sp)+,d2
.x	move.l	d2,(a4)+
	ext.l	d3
	asl.l	#7,d3
	TIMESS	d3
	move.l	d3,(a4)+
	rts

; PL_PS at $221c6 and $2271c (dopoly, dopolyh; over adda.l (rows,pc,d1.w*4),a3 and move.w
; #$3f3f,d1) and $22466 (dopolyg; and move.w -1530(a4),d1, the top edge's): line d1 (+ 1)
_t_poly
	addq.w	#1,d1
_t_polyh
	mulu.w	#DS_STRIDE,d1
	adda.l	d1,a3
	move.w	#$3f3f,d1
	rts
_t_polyg
	addq.w	#1,d1
	mulu.w	#DS_STRIDE,d1
	adda.l	d1,a3
	move.w	-EDGE_STRIDE+6(a4),d1
	rts

; PL_P at $1fbf6 (FloorLine, where its split of the span at the bank boundaries begins,
; unrolled for 3 banks): the same for any number. In: a2 = the span's left edge, the right
; at G_RIGHT. Out, as the game's: a3 at the left edge's slot, a2 = the left edge within
; its bank, d7 = the pixels to the end of that bank or of the span, d4 = those after it;
; on at $1fcb0, whose fills take the rest a bank at a time.
_t_split
	move.l	a2,-(sp)
	HUNK	G_RIGHT,a2
	move.w	(a2),d3
	movea.l	(sp)+,a2
	move.w	a2,d7
	IFD	PENS
	movea.w	d7,a2
	lea	(a3,d7.w),a3		;one bank: the whole span
	moveq	#0,d4
	sub.w	d7,d3
	move.w	d3,d7
	JMPG	$1fcb0
	ENDC
.bank	cmp.w	#31,d7
	ble.s	.in
	subi.w	#32,d7
	subi.w	#32,d3
	lea	132(a3),a3
	bra.s	.bank
.in	movea.w	d7,a2
	lea	(a3,d7.w*4),a3
	moveq	#0,d4
	cmp.w	#32,d3
	ble.s	.last
	move.w	d3,d4
	subi.w	#32,d4
	moveq	#32,d3
.last	sub.w	d7,d3
	move.w	d3,d7
	JMPG	$1fcb0

; _t_gun's rows of a column, PENS: \1 the packing (0 the low 5 bits, 1 the middle, 2 the
; high), \2 = S
GUNROWS	MACRO
.r\@
	IFEQ	\1
	move.w	(a1)+,d1
	ENDC
	IFEQ	\1-1
	move.w	(a1)+,d1
	lsr.w	#5,d1
	ENDC
	IFEQ	\1-2
	move.b	(a1),d1
	addq.w	#2,a1
	lsr.b	#2,d1
	ENDC
	andi.w	#31,d1
	beq.s	.s\@
	move.b	(a4,d1.w),d1		;(the objects' pens, _t_pens)
	move.w	(a2,d1.w*2),d5
	move.w	d5,(a3)
	move.w	d5,DS_STRIDE(a3)
	IFEQ	\2-3
	move.b	d5,2(a3)
	move.b	d5,DS_STRIDE+2(a3)
	move.w	d5,2*DS_STRIDE(a3)
	move.b	d5,2*DS_STRIDE+2(a3)
	ENDC
.s\@	lea	\2*DS_STRIDE(a3),a3
	dbf	d3,.r\@
	bra.w	.next
	ENDM

; Our gun and sky draw from images of a fixed size, 96 texels across, stored a column at a
; time: each texel goes S x S into the list, at the slots of its S pixels (DA_SLOT; at S = 3
; a texel may span a bank boundary).

; PL_PS at $5826 (DrawInGun, over move.w d7,d6 and muls.w #416,d6; d7 = its top row). The
; game's draws 96 columns of rows d7-78 from a fixed-size image, ours S x S from line
; S * d7. From there a0 = the image, a2 and a5 its frame's columns (d0 the frame, d5 its
; offset), a4 the colours, a6 = fromPt.
_t_gun
	addq.l	#4,sp			;not back: this draws the gun and returns for it
	move.l	d4,-(sp)		;(the game's keeps d4)
	asl.w	#2,d0
	add.w	d5,d0
	move.w	(a2,d0.w*4),d1
	lea	(a5,d1.w),a5
	move.w	d7,d6
	mulu.w	_ds_scale(pc),d6
	mulu.w	#DS_STRIDE,d6
	adda.l	d6,a6			;line S * top
	IFD	PENS
	; a texel's S pens at once: a word from DA_SKYTAB (and a byte at S = 3; not a long,
	; whose 4th byte might be a transparent texel's), in one of 6 loops: packing x view
	movea.l	_expmem(pc),a2
	adda.l	#PA_OFF+DA_SKYTAB,a2
	move.w	_ds_scale(pc),d6
	moveq	#0,d4			;the column's x
	moveq	#96-1,d0		;the columns left
.col	move.b	(a5),d2			;how its texels are packed
	move.l	(a5)+,d1		;0: an empty column
	beq.w	.next
	andi.l	#$ffffff,d1
	lea	(a0,d1.l),a1
	lea	(a6,d4.w),a3
	moveq	#78,d3
	sub.w	d7,d3
	tst.b	_ds_gview(pc)
	bne.w	.three
	cmp.b	#1,d2
	bgt.w	.a2
	beq.s	.a1
	GUNROWS	0,2
.a1	GUNROWS	1,2
.a2	GUNROWS	2,2
.three	cmp.b	#1,d2
	bgt.w	.b2
	beq.s	.b1
	GUNROWS	0,3
.b1	GUNROWS	1,3
.b2	GUNROWS	2,3
.next	add.w	d6,d4
	dbf	d0,.col
	move.l	(sp)+,d4
	rts
	ELSE
	movea.l	_ds_slot(pc),a2
	moveq	#96-1,d0		;the columns left
.col	move.w	(a2)+,d4		;its pixels' slots
	move.w	(a2)+,d5
	moveq	#0,d6
	tst.b	_ds_gview(pc)
	beq.s	.two
	move.w	(a2)+,d6
.two	move.b	(a5),d2			;how its texels are packed
	move.l	(a5)+,d1		;0: an empty column
	beq.w	.next
	andi.l	#$ffffff,d1
	lea	(a0,d1.l),a1
	movea.l	a6,a3
	moveq	#78,d3
	sub.w	d7,d3
.row	cmp.b	#1,d2
	bgt.s	.m2
	beq.s	.m1
	move.w	(a1)+,d1		;the low 5 bits
	bra.s	.got
.m1	move.w	(a1)+,d1		;the middle 5
	lsr.w	#5,d1
	bra.s	.got
.m2	move.b	(a1),d1			;the high 5
	addq.w	#2,a1
	lsr.b	#2,d1
.got	andi.w	#31,d1
	beq.s	.skip
	IFD	PENS
	move.b	(a4,d1.w),d1		;(the objects' pens, _t_pens)
	ELSE
	move.w	(a4,d1.w*2),d1
	ENDC
	PX	d1,(a3,d4.w)
	PX	d1,(a3,d5.w)
	PX	d1,DS_STRIDE(a3,d4.w)
	PX	d1,DS_STRIDE(a3,d5.w)
	tst.b	_ds_gview(pc)
	beq.s	.skip2
	PX	d1,(a3,d6.w)
	PX	d1,DS_STRIDE(a3,d6.w)
	PX	d1,2*DS_STRIDE(a3,d4.w)
	PX	d1,2*DS_STRIDE(a3,d5.w)
	PX	d1,2*DS_STRIDE(a3,d6.w)
.skip	tst.b	_ds_gview(pc)
	beq.s	.skip2
	lea	DS_STRIDE(a3),a3
.skip2	lea	2*DS_STRIDE(a3),a3
	dbf	d3,.row
.next	dbf	d0,.col
	move.l	(sp)+,d4
	rts
	ENDC

; PL_P at $1933e (the sky, over move.l a0,-(sp) and the angle's read). The game's draws 96
; columns of 38 words from lines 1 on (y + 1, as the walls), one sky column each; ours
; S x S from line 1.
_t_sky
	movem.l	d0-d7/a0-a6,-(sp)
	HUNK	G_ANGLE,a0
	move.w	(a0),d5
	andi.w	#8191,d5
	muls.w	#432,d5
	divs.w	#8192,d5
	IFD	PENS
	; a line a texel row: each texel its S pens at once from DA_SKYTAB (a word of 2, or a
	; long of 3 whose 4th byte the next texel or the line's copy overwrites), the 96
	; columns in two runs split where the 432 wrap; then the line copied S - 1 times
	move.w	#432,d6
	sub.w	d5,d6			;columns before the wrap
	cmp.w	#96,d6
	ble.s	.run
	moveq	#96,d6
.run	moveq	#96,d7
	sub.w	d6,d7			;columns after it
	subq.w	#1,d6
	subq.w	#1,d7
	movea.l	_expmem(pc),a2
	adda.l	#PA_OFF,a2
	lea	DA_SKYTAB(a2),a4
	lea	PA_SKY(a2),a2		;the sky's pens (palette.s), 38 a column
	muls.w	#38,d5
	lea	(a2,d5.l),a1		;row 0 of the first column
	movea.l	a2,a3			;row 0 of column 0
	movea.l	_ds_frompt(pc),a0
	movea.l	(a0),a0
	lea	DS_STRIDE(a0),a0	;line 1
	moveq	#0,d1
	moveq	#38-1,d3
	tst.b	_ds_gview(pc)
	bne.s	.row3
.row2	movea.l	a0,a6
	movea.l	a1,a5
	move.w	d6,d4
.a2	move.b	(a5),d1
	move.w	(a4,d1.w*2),(a6)+
	lea	38(a5),a5
	dbf	d4,.a2
	movea.l	a3,a5
	move.w	d7,d4
	bmi.s	.c2
.b2	move.b	(a5),d1
	move.w	(a4,d1.w*2),(a6)+
	lea	38(a5),a5
	dbf	d4,.b2
.c2	movea.l	a0,a5
	lea	DS_STRIDE(a0),a6
	moveq	#SMALL_W/16-1,d4
.k2	move.l	(a5)+,(a6)+
	move.l	(a5)+,(a6)+
	move.l	(a5)+,(a6)+
	move.l	(a5)+,(a6)+
	dbf	d4,.k2
	lea	2*DS_STRIDE(a0),a0
	addq.l	#1,a1
	addq.l	#1,a3
	dbf	d3,.row2
	bra.s	.done
.row3	movea.l	a0,a6
	movea.l	a1,a5
	move.w	d6,d4
.a3	move.b	(a5),d1
	move.l	512(a4,d1.w*4),(a6)
	addq.l	#3,a6
	lea	38(a5),a5
	dbf	d4,.a3
	movea.l	a3,a5
	move.w	d7,d4
	bmi.s	.c3
.b3	move.b	(a5),d1
	move.l	512(a4,d1.w*4),(a6)
	addq.l	#3,a6
	lea	38(a5),a5
	dbf	d4,.b3
.c3	movea.l	a0,a5
	lea	DS_STRIDE(a0),a6
	lea	2*DS_STRIDE(a0),a2
	moveq	#FULL_W/16-1,d4
.k3	REPT	4
	move.l	(a5)+,d0
	move.l	d0,(a6)+
	move.l	d0,(a2)+
	ENDR
	dbf	d4,.k3
	lea	3*DS_STRIDE(a0),a0
	addq.l	#1,a1
	addq.l	#1,a3
	dbf	d3,.row3
.done	movem.l	(sp)+,d0-d7/a0-a6
	rts
	ELSE
	muls.w	#76,d5
	HUNK	G_SKY,a2		;the first column
	HUNK	G_SKYEND,a3
	lea	(a2,d5.l),a1
	movea.l	_ds_frompt(pc),a0
	movea.l	(a0),a0
	lea	DS_STRIDE(a0),a0	;line 1
	movea.l	_ds_slot(pc),a4
	moveq	#96-1,d0		;the columns left
	tst.b	_ds_gview(pc)
	bne.s	.col3
.col2	move.w	(a4)+,d4		;S = 2: the two pixels are in one bank
	addq.w	#2,a4
	lea	(a0,d4.w),a6
	movea.l	a1,a5
	moveq	#38-1,d3
.row2	PX	(a5)+,d1
	PX	d1,(a6)
	PX	d1,PX1(a6)
	PX	d1,DS_STRIDE(a6)
	PX	d1,DS_STRIDE+PX1(a6)
	lea	2*DS_STRIDE(a6),a6
	dbf	d3,.row2
	bsr.s	.step
	dbf	d0,.col2
	bra.s	.done
.col3	move.w	(a4)+,d4		;S = 3
	move.w	(a4)+,d5
	move.w	(a4)+,d6
	movea.l	a0,a6
	movea.l	a1,a5
	moveq	#38-1,d3
.row3	PX	(a5)+,d1
	PX	d1,(a6,d4.w)
	PX	d1,(a6,d5.w)
	PX	d1,(a6,d6.w)
	PX	d1,DS_STRIDE(a6,d4.w)
	PX	d1,DS_STRIDE(a6,d5.w)
	PX	d1,DS_STRIDE(a6,d6.w)
	PX	d1,2*DS_STRIDE(a6,d4.w)
	PX	d1,2*DS_STRIDE(a6,d5.w)
	PX	d1,2*DS_STRIDE(a6,d6.w)
	lea	3*DS_STRIDE(a6),a6
	dbf	d3,.row3
	bsr.s	.step
	dbf	d0,.col3
.done	movem.l	(sp)+,d0-d7/a0-a6
	rts
.step	lea	76(a1),a1		;the next sky column, wrapping
	cmpa.l	a3,a1
	blt.s	.in
	movea.l	a2,a1
.in	rts
	ENDC

; PL_P at $6900 (the water tint, over movea.l #brightentab,a2): the game's clears the red of
; lines 0-79 (d5 = 3) or 40-79 (d5 = 1) of 96 pixels; ours of S times the lines, of the
; view's width.
_t_water
	movem.l	d0-d4/d6/a0-a1,-(sp)
	movea.l	_ds_frompt(pc),a0
	movea.l	(a0),a0
	move.w	_ds_scale(pc),d6
	moveq	#3,d0
	sub.w	d5,d0
	mulu.w	#20,d0
	mulu.w	d6,d0			;the first line
	mulu.w	#DS_STRIDE,d0
	adda.l	d0,a0
	move.w	d5,d2
	addq.w	#1,d2
	mulu.w	#20,d2
	mulu.w	d6,d2
	subq.w	#1,d2			;the lines - 1
	IFD	PENS
	movea.l	_expmem(pc),a1		;pen to pen, red removed (palette.s)
	adda.l	#PA_OFF+PA_TINT,a1
	move.w	#SMALL_W-1,d1
	tst.b	_ds_gview(pc)
	beq.s	.tline
	move.w	#FULL_W-1,d1
.tline	move.w	d1,d3
	moveq	#0,d0
.tpx	move.b	(a0,d3.w),d0
	move.b	(a1,d0.w),(a0,d3.w)
	dbf	d3,.tpx
	lea	DS_STRIDE(a0),a0
	dbf	d2,.tline
	bra.s	.tdone
	ENDC
	moveq	#SMALL_W/32-1,d0
	tst.b	_ds_gview(pc)
	beq.s	.bank
	moveq	#FULL_W/32-1,d0
.bank	moveq	#32-1,d1
.col	movea.l	a0,a1
	move.w	d2,d3
.line	andi.w	#$ff,(a1)
	lea	DS_STRIDE(a1),a1
	dbf	d3,.line
	addq.w	#4,a0
	dbf	d1,.col
	addq.w	#4,a0
	dbf	d0,.bank
.tdone	movem.l	(sp)+,d0-d4/d6/a0-a1
	HUNK	G_BRIGHTEN,a2
	moveq	#0,d2
	rts

; PL_P at $41b2 (DRAWPAUSESCRN, over movea.l #font,a0). The game's draws a grid of 12x10
; blocks of 8x8 over 96x80, each a letter of the option text (its font's colour words, 0
; see-through) or the frame shown (G_PAUSESRC) at half brightness, into the other list
; (G_PAUSEDST); ours the letters S x S, the frame at 1x1.
_t_pause
	movem.l	d0-d7/a0-a6,-(sp)
	HUNK	G_FONT,a0
	HUNK	G_PAUSETEXT,a1
	HUNK	G_PAUSEDST,a2
	movea.l	(a2),a2
	HUNK	G_PAUSESRC,a3
	movea.l	(a3),a3
	movea.l	_ds_slot(pc),a4
	move.w	#SMALL_W,a5		;the view's width and height
	move.w	#SMALL_H,d7
	tst.b	_ds_gview(pc)
	beq.s	.go
	move.w	#FULL_W,a5
	move.w	#FULL_H,d7
.go	subq.w	#1,d7			;the lines left
	moveq	#0,d5			;the texel row
	move.w	_ds_scale(pc),a6
	subq.w	#1,a6			;its lines left
	moveq	#0,d4			;the line's offset
.y	moveq	#0,d6			;x
	moveq	#0,d3			;the texel column
	move.w	_ds_scale(pc),d2
	subq.w	#1,d2
	swap	d2			;(high: the pixels left in it)
.x	move.w	d5,d0			;its block's letter
	lsr.w	#3,d0
	mulu.w	#12,d0
	move.w	d3,d1
	lsr.w	#3,d1
	add.w	d1,d0
	move.b	(a1,d0.w),d1
	move.w	(a4,d6.w*2),d0		;the pixel's offset
	ext.l	d0
	add.l	d4,d0
	subi.b	#65,d1			;as the game's: below A, none
	blt.s	.dim
	andi.w	#$ff,d1
	lsl.w	#7,d1			;128 bytes a letter
	move.w	d5,d2
	andi.w	#7,d2
	lsl.w	#4,d2			;16 a row
	add.w	d2,d1
	move.w	d3,d2
	andi.w	#7,d2
	add.w	d2,d2
	add.w	d2,d1
	move.w	(a0,d1.w),d1
	IFD	PENS
	beq.s	.dim
	andi.w	#$fff,d1		;the letter's pen
	move.l	a0,-(sp)
	movea.l	_expmem(pc),a0
	move.b	PA_OFF+PA_MAP(a0,d1.w),d1
	movea.l	(sp)+,a0
	bra.s	.put
.dim	moveq	#0,d1			;the frame's pen at half brightness
	move.b	(a3,d0.l),d1
	move.l	a0,-(sp)
	movea.l	_expmem(pc),a0
	adda.l	#PA_OFF+PA_PAUSE,a0
	move.b	(a0,d1.w),d1
	movea.l	(sp)+,a0
.put	move.b	d1,(a2,d0.l)
	ELSE
	bne.s	.put
.dim	move.w	(a3,d0.l),d1
	andi.w	#$0eee,d1
	lsr.w	#1,d1
.put	move.w	d1,(a2,d0.l)
	ENDC
	swap	d2
	subq.w	#1,d2
	bpl.s	.same
	move.w	_ds_scale(pc),d2
	subq.w	#1,d2
	addq.w	#1,d3
.same	swap	d2
	addq.w	#1,d6
	cmp.w	a5,d6
	blo.w	.x
	addi.l	#DS_STRIDE,d4
	subq.w	#1,a6
	move.w	a6,d0
	bpl.s	.ysame
	move.w	_ds_scale(pc),a6
	subq.w	#1,a6
	addq.w	#1,d5
.ysame	dbf	d7,.y
	movem.l	(sp)+,d0-d7/a0-a6
	rts


_ds_frompt	dc.l	0	;game addresses of G_FROMPT and G_EYE
_ds_eye		dc.l	0
_ds_slot	dc.l	0	;DA_SLOT's address
_ds_scale	dc.w	2	;S: 2 in the small view, 3 in full screen (_ds_geom)

	IFD	PENS
;----------------------------------------------------------------------
; Pens (resolution plan step 7): the writers write pen bytes from the palette build's pen
; tables (palette.s) instead of colour words.

G_WALLPAL	= $55ce6		;the wall's shade table, 32 rows of 32 colour words
G_SIMPLECOLS	= $1f46c		;SimpleFloorLine's colours: 16 rows of 32 words
G_SIMPLEBLACK	= $1f3d5		;its moveq #0,d0's byte (detail above 2: black)
G_PEN_OBJECTS	= $2974a		;18 entries of (wad, ptr, frames, pal)
DA_WATER	= DA_CHUNKY		;the water's pens (the chunky buffer is unused):
					;22 rows of 256, by the pen reflected
DA_FLOOR	= DA_WATER+22*256	;the floors' and textured polygons' pens: their 15
DA_POLY		= DA_FLOOR+XROWS*256	;rows, then what follows the game's table, as a
XROWS		= 24			;Gouraud row past 14 reads it (zeros: black)
DA_SKYTAB	= DA_POLY+XROWS*256	;256 words: pen p twice, then 256 longs: 3 times (_t_sky)

; From _ds_tables (a5 = hunk 0, a4 = the area), once: the game's tables for pens. Its
; colour tables' pointers to the pen tables; the row offsets into them halved (a row of
; pens is half a row of words); each object's palette pointer to its pens (DrawInGun's
; too); SimpleFloorLine's colours as pens (the word's low byte, which doacrossline
; writes); the water's table.
_t_pens
	lea	_t_pensdone(pc),a0
	bset	#0,(a0)
	bne.w	.done
	lea	.ptrs(pc),a1
.ptr	move.l	(a1)+,d0		;the operand's game offset; 0 ends
	beq.s	.half
	move.l	(a1)+,d1		;the table's area offset
	add.l	a4,d1
	move.l	d1,(a5,d0.l)
	bra.s	.ptr
.half	lea	.halve(pc),a1
.hn	move.l	(a1)+,d0		;game offset; 0 ends
	beq.s	.objs
	lea	(a5,d0.l),a0
	move.w	(a1)+,d1		;words
	subq.w	#1,d1
.hw	lsr.w	(a0)+
	dbf	d1,.hw
	bra.s	.hn
.objs	lea	G_PEN_OBJECTS+12(a5),a0
	lea	PA_OBJS(a4),a1
	moveq	#N_OBJECTS-1,d0
.obj	move.l	a1,(a0)
	lea	16(a0),a0
	lea	480(a1),a1
	dbf	d0,.obj
	lea	G_SIMPLECOLS(a5),a0
	move.w	#16*32-1,d0
	moveq	#0,d1
.simple	move.w	(a0),d1
	andi.w	#$fff,d1
	move.b	PA_MAP(a4,d1.w),d1
	move.w	d1,(a0)+
	dbf	d0,.simple
	move.b	PA_MAP(a4),G_SIMPLEBLACK(a5)
	lea	G_FLOORPAL(a5),a0
	lea	DA_FLOOR(a4),a1
	bsr.w	.rows
	lea	G_TEXPAL(a5),a0
	lea	DA_POLY(a4),a1
	bsr.w	.rows
	; the water: row k, pen p: the pen of brightentab's colour k * 256 + p's colour's low
	; byte, which texturedwater's reflection read takes from the colour word
	lea	DA_SKYTAB(a4),a0	;the sky's pens, 2 and 3 at once
	lea	512(a0),a1
	moveq	#0,d1
.sky	move.l	d1,d0
	lsl.w	#8,d0
	move.b	d1,d0
	move.w	d0,(a0)+
	swap	d0
	move.w	d1,d0
	lsl.w	#8,d0
	move.b	d1,d0
	move.l	d0,(a1)+
	addq.b	#1,d1
	bne.s	.sky
	lea	G_BRIGHTEN(a5),a0
	lea	DA_WATER(a4),a1
	moveq	#22-1,d2
.wrow	moveq	#0,d3			;p
.wpen	moveq	#0,d1
	cmp.w	#PEN0,d3
	blo.s	.wcol
	move.w	d3,d1
	add.w	d1,d1
	move.w	PA_PALETTE-2*PEN0(a4,d1.w),d1
	andi.w	#$ff,d1
.wcol	move.w	(a0,d1.w*2),d1
	andi.w	#$fff,d1
	move.b	PA_MAP(a4,d1.w),(a1)+
	addq.w	#1,d3
	cmp.w	#256,d3
	blo.s	.wpen
	lea	512(a0),a0
	dbf	d2,.wrow
.done	rts
.rows	move.w	#XROWS*256-1,d0		;a0 = the game's table, a1 = ours
	moveq	#0,d1
.rw	move.w	(a0)+,d1
	andi.w	#$fff,d1
	move.b	PA_MAP(a4,d1.w),(a1)+
	dbf	d0,.rw
	rts
.ptrs	dc.l	$1fa2e,DA_FLOOR		;FloorLine: lea floorScaleCols,a1
	dc.l	$1f154,DA_FLOOR		;dofloor (FloorLine's overwrites it)
	dc.l	$1f2ea,DA_FLOOR		;dofloorGOUR
	dc.l	$1f39a,DA_FLOOR
	dc.l	$220cc,DA_POLY		;dopoly: movea.l #TexturePal,a1
	dc.l	$2238c,DA_POLY		;dopolyg
	dc.l	$22672,DA_POLY		;dopolyh
	dc.l	$21086,DA_WATER		;texturedwater: movea.l #brightentab,a1
	dc.l	0
.halve	dc.l	$1a4f0			;see-through walls' brightness rows (words)
	dc.w	33
	dc.l	$1a772			;walls'
	dc.w	65
	dc.l	$1faae			;FloorLine's rows (29 longs)
	dc.w	58
	dc.l	$217ca			;bitmaps' rows, dopoly's too (x 8)
	dc.w	74
	dc.l	0
_t_pensdone	dc.b	0
	EVEN

; PL_PS at $8aea (LightDraw, over movea.l #brightentab,a4): pen to pen, brighter; d7 is
; read a byte at a time
_t_light
	movea.l	_expmem(pc),a4
	adda.l	#PA_OFF+PA_LIGHT,a4
	moveq	#0,d7
	rts

; PL_PS at $1d0e8 (itsawalldraw, over move.l a3,G_WALLPAL; d1 = the wall's number): the
; wall's pen table instead, 32 rows of 32 pens
_t_wallpal
	move.l	a0,-(sp)
	move.l	d1,-(sp)
	movea.l	_expmem(pc),a0
	adda.l	#PA_OFF+PA_WALLS,a0
	andi.l	#$ffff,d1
	lsl.l	#8,d1
	lsl.l	#2,d1
	adda.l	d1,a0
	move.l	a0,d1
	HUNK	G_WALLPAL,a0
	move.l	d1,(a0)
	move.l	(sp)+,d1
	movea.l	(sp)+,a0
	rts
	ENDC
