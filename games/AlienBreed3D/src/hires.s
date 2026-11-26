;----------------------------------------------------------------------
; The 1x1 renderer (resolution plan step 5): the game's own writers draw the small view at
; 192x160. Most of the geometry is in _ds_sites (sites.s: each view's value of an
; immediate or an opcode); what a constant cannot express is here, patched at the game
; offsets given (AlienBreed3D.s): the writers' row and column addressing for any width
; (both views), and in the small view the doubling of every height above or below the
; eye before its divide, the walls' texture step halved, and 2x2 writers of our own for
; the gun, the sky and the water tint, which draw from fixed-size images.

; the area, past DA_INFO: tables for 192 columns and 161 lines, both views
DA_SLOT		= DA_INFO+DI_SIZE	;192 words: a pixel's offset in its line, 4x + 4(x / 32)
DA_YTAB		= DA_SLOT+2*SMALL_W	;161 longs: (y + 1) lines
DA_ACROSS	= DA_YTAB+4*(SMALL_H+1)	;doacrossline for 192: move.w d0,n(a3) each, then rts
DA_EDGES	= (DA_ACROSS+4*SMALL_W+2+3)&-4	;the polygons' edges, top then bottom,
					;8 bytes a column, EDGE_STRIDE apart
EDGE_STRIDE	= 8*200			;(the game's are $28b46 and $29146, 1536 apart: at
					;192 columns its writes of column 192, past the
					;right clip, land on the bottom's column 0 and on
					;the objects' graphics table at $2974a)
DA_END		= DA_EDGES+2*EDGE_STRIDE
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

G_FONT		= $4414			;the pause screen's letters, 8x8 colour words each
G_PAUSETEXT	= $433c			;its text, 12 letters a row
G_PAUSESRC	= $41aa			;pointers: the frame shown, the list drawn into
G_PAUSEDST	= $41ae

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
	PALEA	DA_SLOT,a0
	moveq	#0,d0
.slot	move.w	d0,d1
	lsr.w	#5,d1
	add.w	d0,d1
	add.w	d1,d1
	add.w	d1,d1
	move.w	d1,(a0)+
	addq.w	#1,d0
	cmp.w	#SMALL_W,d0
	blo.s	.slot
	PALEA	DA_YTAB,a0
	move.l	#DS_STRIDE,d0
	move.w	#SMALL_H,d1
.ytab	move.l	d0,(a0)+
	addi.l	#DS_STRIDE,d0
	dbf	d1,.ytab
	PALEA	DA_ACROSS,a0
	PALEA	DA_SLOT,a1
	move.w	#SMALL_W-1,d1
.across	move.w	#$3740,(a0)+		;move.w d0,n(a3)
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
.done	rts				;(_ds_stride flushes the caches)
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
	dc.l	0

; PL_PS at $1a616 and $1a3ac (walls, see-through walls), over movea.l fromPt,a3 and adda.w
; (XTOCOPX,pc,d0.w*2),a3: column d0's slot (d1 is loaded next)
_t_column
	movea.l	_ds_frompt(pc),a3
	movea.l	(a3),a3
	move.w	d0,d1
	lsr.w	#5,d1
	add.w	d0,d1
	add.w	d1,d1
	add.w	d1,d1
	adda.w	d1,a3
	rts

; PL_PS at $1cb8a and $1cf18 (a wall strip), over adda.l (timeslarge,pc,d5.w*4),a3, move.w
; d5,d4 and the two consttab reads: line d5 + 1, and in the small view half the texture
; step (16.16) for twice the lines; the start is the same.
_t_strip
	move.w	d5,d4
	addq.w	#1,d4
	mulu.w	#DS_STRIDE,d4
	adda.l	d4,a3
	move.w	d5,d4
	move.l	4(a1,d2.w*8),d0
	move.l	(a1,d2.w*8),d2
	tst.b	_ds_gview(pc)
	bne.s	.full
	asr.l	#1,d2
.full	rts

; PL_PS at $1d13a, $1b3b0 (sub.l d6,top) and $1d146, $1b3b6 (sub.l d6,bottom): a wall's
; top and bottom less the eye (d6), doubled in the small view
_t_walltop
	move.l	a0,-(sp)
	HUNK	G_WALLTOP,a0
	bra.s	_t_wallh
_t_wallbot
	move.l	a0,-(sp)
	HUNK	G_WALLBOT,a0
_t_wallh
	sub.l	d6,(a0)
	tst.b	_ds_gview(pc)
	bne.s	.full
	move.l	d6,-(sp)
	move.l	(a0),d6
	add.l	d6,(a0)
	move.l	(sp)+,d6
.full	movea.l	(sp)+,a0
	rts

; PL_PS over sub.l eye,d6 (glass and bitmaps' zone clips, $2142e $21452 $21770 $21794) and
; sub.l eye,d2 (their height, $2147a $21864; a polygon's, $21e28): doubled in the small view
_t_eye6
	move.l	a0,-(sp)
	movea.l	_ds_eye(pc),a0
	sub.l	(a0),d6
	movea.l	(sp)+,a0
	tst.b	_ds_gview(pc)
	bne.s	.full
	add.l	d6,d6
.full	rts
_t_eye2
	move.l	a0,-(sp)
	movea.l	_ds_eye(pc),a0
	sub.l	(a0),d2
	movea.l	(sp)+,a0
	tst.b	_ds_gview(pc)
	bne.s	.full
	add.l	d2,d2
.full	rts

; PL_PS at $2149a and $21884 (glass, bitmaps; over asl.w #7,d3, asl.w #7,d4 and their
; divs.w d1 by the distance): the half sizes, doubled in the small view after the divide
; (an 8-bit size shifted 8 would be negative in the word). The game doubles them again
; into the width and height, a word: an object so close that they do not fit (the
; original's at under half our distance) is dropped, a half width of -$1000 putting its
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
	add.w	d3,d3
	add.w	d4,d4
	cmp.w	#$3fff,d3		;(unsigned: a negative one is dropped too)
	bhi.s	.drop
	cmp.w	#$3fff,d4
	bls.s	.full
.drop	move.w	#-$1000,d3
.full	rts

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

; PL_PS at $5826 (DrawInGun, over move.w d7,d6 and muls.w #416,d6; d7 = its top row): full
; screen as the game's. The small view's gun is ours, 2x2: the game's draws 96 columns of
; rows d7-78 from a fixed-size image. From there a0 = the image, a2 and a5 its frame's
; columns (d0 the frame, d5 its offset), a4 the colours, a6 = fromPt.
_t_gun
	tst.b	_ds_gview(pc)
	beq.s	.small
	move.w	d7,d6
	muls.w	#DS_STRIDE,d6
	rts
.small	addq.l	#4,sp			;not back: this draws the gun and returns for it
	asl.w	#2,d0
	add.w	d5,d0
	move.w	(a2,d0.w*4),d1
	lea	(a5,d1.w),a5
	move.w	d7,d6
	mulu.w	#2*DS_STRIDE,d6
	adda.l	d6,a6
	moveq	#0,d0			;the column
.col	move.b	(a5),d2			;how its texels are packed
	move.l	(a5)+,d1		;0: an empty column
	beq.w	.next
	andi.l	#$ffffff,d1
	lea	(a0,d1.l),a1
	movea.l	a6,a3
	moveq	#78,d3
	sub.w	d7,d3
	cmp.b	#1,d2
	bgt.s	.m2
	beq.s	.m1
.m0	move.w	(a1)+,d1		;the low 5 bits
	andi.w	#31,d1
	beq.s	.n0
	move.w	(a4,d1.w*2),d1
	move.w	d1,(a3)
	move.w	d1,4(a3)
	move.w	d1,DS_STRIDE(a3)
	move.w	d1,DS_STRIDE+4(a3)
.n0	lea	2*DS_STRIDE(a3),a3
	dbf	d3,.m0
	bra.s	.next
.m1	move.w	(a1)+,d1		;the middle 5
	lsr.w	#5,d1
	andi.w	#31,d1
	beq.s	.n1
	move.w	(a4,d1.w*2),d1
	move.w	d1,(a3)
	move.w	d1,4(a3)
	move.w	d1,DS_STRIDE(a3)
	move.w	d1,DS_STRIDE+4(a3)
.n1	lea	2*DS_STRIDE(a3),a3
	dbf	d3,.m1
	bra.s	.next
.m2	move.b	(a1),d1			;the high 5
	addq.w	#2,a1
	lsr.b	#2,d1
	andi.w	#31,d1
	beq.s	.n2
	move.w	(a4,d1.w*2),d1
	move.w	d1,(a3)
	move.w	d1,4(a3)
	move.w	d1,DS_STRIDE(a3)
	move.w	d1,DS_STRIDE+4(a3)
.n2	lea	2*DS_STRIDE(a3),a3
	dbf	d3,.m2
.next	addq.w	#8,a6			;two pixels
	addq.w	#1,d0
	moveq	#15,d1
	and.w	d0,d1
	bne.s	.same
	addq.w	#4,a6			;the next bank
.same	cmp.w	#96,d0
	blo.w	.col
	rts

; PL_P at $1933e (the sky, over move.l a0,-(sp) and the angle's read): full screen as the
; game's. The small view's is ours, 2x2: the game's draws 96 columns of 38 words from
; lines 1 on (y + 1, as the walls), one sky column each.
_t_sky
	tst.b	_ds_gview(pc)
	beq.s	.small
	move.l	a0,-(sp)
	HUNK	G_ANGLE,a0
	move.w	(a0),d5
	movea.l	(sp),a0
	JMPG	$19346
.small	movem.l	d0-d7/a0-a6,-(sp)
	HUNK	G_ANGLE,a0
	move.w	(a0),d5
	andi.w	#8191,d5
	muls.w	#432,d5
	divs.w	#8192,d5
	muls.w	#76,d5
	HUNK	G_SKY,a2		;the first column
	HUNK	G_SKYEND,a3
	lea	(a2,d5.l),a1
	movea.l	_ds_frompt(pc),a0
	movea.l	(a0),a0
	lea	DS_STRIDE(a0),a0
	moveq	#0,d0			;the column
.col	movea.l	a0,a4
	movea.l	a1,a5
	moveq	#38-1,d3
.row	move.w	(a5)+,d1
	move.w	d1,(a4)
	move.w	d1,4(a4)
	move.w	d1,DS_STRIDE(a4)
	move.w	d1,DS_STRIDE+4(a4)
	lea	2*DS_STRIDE(a4),a4
	dbf	d3,.row
	lea	76(a1),a1
	cmpa.l	a3,a1
	blt.s	.in
	movea.l	a2,a1
.in	addq.w	#8,a0
	addq.w	#1,d0
	moveq	#15,d1
	and.w	d0,d1
	bne.s	.same
	addq.w	#4,a0
.same	cmp.w	#96,d0
	blo.s	.col
	movem.l	(sp)+,d0-d7/a0-a6
	rts

; PL_P at $6900 (the water tint, over movea.l #brightentab,a2): full screen as the game's.
; The small view's is ours: the game's clears the red of lines 0-79 (d5 = 3) or 40-79
; (d5 = 1) of 96 pixels; here lines 0-159 or 80-159 of 192.
_t_water
	tst.b	_ds_gview(pc)
	beq.s	.small
	HUNK	G_BRIGHTEN,a2
	JMPG	$6906
.small	movea.l	_ds_frompt(pc),a0
	movea.l	(a0),a0
	moveq	#3,d0
	sub.w	d5,d0
	mulu.w	#40*DS_STRIDE,d0
	adda.l	d0,a0
	moveq	#SMALL_W/32-1,d0
.bank	moveq	#32-1,d1
.col	movea.l	a0,a1
	move.w	d5,d2
	addq.w	#1,d2
	mulu.w	#40,d2
	subq.w	#1,d2
.line	andi.w	#$ff,(a1)
	lea	DS_STRIDE(a1),a1
	dbf	d2,.line
	addq.w	#4,a0
	dbf	d1,.col
	addq.w	#4,a0
	dbf	d0,.bank
	HUNK	G_BRIGHTEN,a2
	moveq	#0,d2
	rts

; PL_P at $41b2 (DRAWPAUSESCRN, over movea.l #font,a0): full screen as the game's. The
; small view's is ours, 2x2: the game's draws a grid of 12x10 blocks of 8x8 over 96x80,
; each a letter of the option text (its font's colour words, 0 see-through) or the frame
; shown (G_PAUSESRC) at half brightness, into the other list (G_PAUSEDST).
_t_pause
	tst.b	_ds_gview(pc)
	beq.s	.small
	HUNK	G_FONT,a0
	JMPG	$41b8
.small	movem.l	d0-d7/a0-a6,-(sp)
	HUNK	G_FONT,a0
	HUNK	G_PAUSETEXT,a1
	HUNK	G_PAUSEDST,a2
	movea.l	(a2),a2
	HUNK	G_PAUSESRC,a3
	movea.l	(a3),a3
	moveq	#0,d7			;y
.y	moveq	#0,d6			;x
.x	move.w	d6,d0			;the pixel's offset: its slot and line
	lsr.w	#5,d0
	add.w	d6,d0
	add.w	d0,d0
	add.w	d0,d0
	move.w	d7,d1
	mulu.w	#DS_STRIDE,d1
	add.l	d0,d1
	move.w	d7,d2			;its block's letter
	lsr.w	#4,d2
	mulu.w	#12,d2
	move.w	d6,d3
	lsr.w	#4,d3
	add.w	d3,d2
	move.b	(a1,d2.w),d3
	subi.b	#65,d3			;as the game's: below A, none
	blt.s	.dim
	andi.w	#$ff,d3
	lsl.w	#7,d3			;128 bytes a letter
	move.w	d7,d2
	lsr.w	#1,d2
	andi.w	#7,d2
	lsl.w	#4,d2			;16 a row
	add.w	d2,d3
	move.w	d6,d2
	lsr.w	#1,d2
	andi.w	#7,d2
	add.w	d2,d2
	add.w	d2,d3
	move.w	(a0,d3.w),d2
	bne.s	.put
.dim	move.w	(a3,d1.l),d2
	andi.w	#$0eee,d2
	lsr.w	#1,d2
.put	move.w	d2,(a2,d1.l)
	addq.w	#1,d6
	cmp.w	#SMALL_W,d6
	blo.s	.x
	addq.w	#1,d7
	cmp.w	#SMALL_H,d7
	blo.s	.y
	movem.l	(sp)+,d0-d7/a0-a6
	rts

_ds_frompt	dc.l	0	;game addresses of G_FROMPT and G_EYE
_ds_eye		dc.l	0
