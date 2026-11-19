; Title, all modes: once the MicroProse logo has faded into the background
; (colour 30 = colour 0), the title clears its rows with RectFill on the
; displayed bitmap. The blitter clears one plane after another, so a field
; can show the logo half cleared, in another pen (colour 24, grey). Clear
; instead with the CPU, one row of every plane at a time, never while the
; beam is on or just before that row: each displayed row is then the faded
; logo or blank, both the background colour. Chip memory is non-cacheable.
; Replaces "moveq #74,d3; add.l d3,d3; jsr _LVORectFill(a6)" with a1=RastPort,
; a6=GfxBase, d0-d2 = 0,50,319. Same scratch as RectFill (d0-d1/a0-a1).
; Anything else (a layer, another width, an unexpected view) uses RectFill.
LOGO_CLEAR_LEAD = 6 ; lines: a 68000 row of 5 planes takes about 2-3

logo_clear:
	move.l #148,d3
	movem.l d2-d7/a2-a3,-(sp)
	tst.l (a1) ; rp_Layer
	bne .native
	tst.w d0
	bne .native
	cmpi.w #319,d2
	bne .native
	movea.l 4(a1),a2 ; rp_BitMap
	cmpi.w #40,(a2) ; bm_BytesPerRow
	bne .native
	moveq #0,d5
	move.b 5(a2),d5 ; bm_Depth
	beq .native
	cmpi.w #8,d5
	bhi .native
	cmp.w 2(a2),d3 ; bm_Rows
	bhs .native
	cmp.w d3,d1
	bhi .native
	movea.l 34(a6),a0 ; gb_ActiView
	move.l a0,d7
	beq .native
	move.w 12(a0),d7 ; v_DyOffset
	movea.l (a0),a0 ; v_ViewPort
	move.l a0,d4
	beq .native
	add.w 30(a0),d7 ; vp_DyOffset
	; Finish any blit still drawing into this bitmap.
	movem.l d1/a1,-(sp)
	jsr -228(a6) ; _LVOWaitBlit
	movem.l (sp)+,d1/a1
	moveq #0,d6
	move.w d1,d6
	mulu.w #40,d6 ; row offset
	add.w d1,d7 ; beam line of the first row
	subq.w #1,d5
.row:
	; Wait while the beam is within LOGO_CLEAR_LEAD lines before the row,
	; or on it: the whole row must be written between two scans of it.
.beam:
	move.l $dff004,d0
	lsr.l #8,d0
	andi.w #$1ff,d0
	sub.w d7,d0
	addi.w #LOGO_CLEAR_LEAD,d0
	cmpi.w #LOGO_CLEAR_LEAD,d0
	bls .beam
	lea 8(a2),a3 ; bm_Planes
	move.w d5,d4
.plane:
	movea.l (a3)+,a0
	adda.l d6,a0
	moveq #0,d0
	moveq #9,d2
.long:
	move.l d0,(a0)+
	dbf d2,.long
	dbf d4,.plane
	addi.l #40,d6
	addq.w #1,d7
	addq.w #1,d1
	cmp.w d3,d1
	bls .row
	movem.l (sp)+,d2-d7/a2-a3
	rts
.native:
	movem.l (sp)+,d2-d7/a2-a3
	jmp -306(a6) ; _LVORectFill
