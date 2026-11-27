; Enhanced resolution on both versions it runs on: the game offsets its code reads, as the
; $c4dc version (the Aminet 8-channel one, the AGA drawer) has them, and the CD32 one's.
;
; Each G_ name is an entry of _gofs (its index), read with GLEA or HUNK (hires.s) or as
; _gofs+G_NAME(pc). With the CD32 version ($fd78, _pl_v2) _port translates them, and the
; tables of game offsets in display.s and hires.s, once, before the game starts (and sets
; _gwall, the one table whose layout differs: the wall files'): through
; _port_segs (cd32segs.s), where each segment's $c4dc start has its distance to the CD32
; offset. tools/port.py writes cd32segs.s and the CD32 patch list (cd32.s) from the $c4dc
; sources; its check maps every offset and compares the bytes each patch replaces.

GOFS	MACRO			;name, the $c4dc offset (hunk 0)
G_\1	= *-_gofs
	dc.l	\2
	ENDM

_gofs
	GOFS	TEMPLATEPTR,$2ea8	;move.l #template,d0 at $2ea6: the template's address
	GOFS	LEVELCOP,$31a0		;level start: move.l #template,$dff080 (10 bytes)
	GOFS	VIEWFLAG,$40279		;keypad Enter's byte: 0 the small view, else full screen
	GOFS	LIST1,$43c38		;the two copper lists' pointers (the second at +4)
	GOFS	COPLISTS,$4463e		;InitCopperScrn's first AllocMem
	GOFS	FROMPT,$5dd48		;fromPt: the list being drawn
	GOFS	DRAWPT,$5dd40		;drawPt: the list drawn next (the end of the sky)
	GOFS	EYE,$61d54		;the eye's height (long, as the objects' heights)
	GOFS	WALLTOP,$1ca28		;a wall's top and bottom (longs)
	GOFS	WALLBOT,$1ca2c
	GOFS	TOPCLIP,$1d270		;the zone's clip lines (words): a wall strip draws the
	GOFS	BOTCLIP,$1d272		;lines below the top one down to the bottom one
	GOFS	RIGHT,$1f9f4		;FloorLine: the span's right edge (word)
	GOFS	FILLS,$1fcb0		;FloorLine's fills, after its split at the banks
	GOFS	ANGLE,$18ff2		;the view's angle (word; the sky's column)
	GOFS	XSHIFT,$5d8c		;the eye's x shift, added to x * 128 (long)
	GOFS	FONT,$4414		;the pause screen's letters, 8x8 colour words each
	GOFS	PAUSETEXT,$433c		;its text, 12 letters a row
	GOFS	PAUSESRC,$41aa		;pointers: the frame shown, the list drawn into
	GOFS	PAUSEDST,$41ae
	GOFS	WALLPAL,$55ce6		;the wall's shade table, 32 rows of 32 colour words
	GOFS	SIMPLECOLS,$1f46c	;SimpleFloorLine's colours: 16 rows of 32 words
	GOFS	SIMPLEBLACK,$1f3d5	;its moveq #0,d0's byte (detail above 2: black)
	GOFS	LOADOBJECTS,$436d6	;LoadObjects, the last of the game's loads
	GOFS	HOOKRET,$44aaa		;after its jsr at $44aa4 (PL_PS)
	GOFS	WALLTILES,$42a66	;a pointer to each loaded wall file
	GOFS	WALLCHUNK,$42b06	;(name, unpacked size) pairs, ended by zeros
	GOFS	FLOORTILE,$55cee	;a pointer to the floor texture
	GOFS	FLOORPAL,$536e6		;floorScaleCols: 15 rows of 256 colour words
	GOFS	TEXPAL,$3e066		;TexturePal: textured polygons' 15 rows of 256
	GOFS	TEXMAPS,$2e066		;TextureMaps: their 64 KB of texels
	GOFS	OBJECTS,$2974a		;18 entries of (wad, ptr, frames, pal); a pal is 15 rows of 32
	GOFS	SKY,$55d00		;BackPicture: 16416 colour words
	GOFS	BRIGHTEN,$766d2		;brightentab: 5632 colour words
	GOFS	WATER,$812d2		;waterfile: the water's 64 KB of texels
_gofs_end
_gwall	dc.w	8		;G_WALLCHUNK's entries: (name, unpacked size); the CD32
				;version's (name, unpacked size, packed size), 12

GLEA	MACRO			;G_ name, address register: a5 (hunk 0) + its offset
	movea.l	a5,\2
	adda.l	_gofs+\1(pc),\2
	ENDM

; At the version's choice (a4 = its patch list): with the CD32 version, every game offset
; the code reads is the CD32 one's. Each table: its address (from _port_tabs), the bytes
; from one entry to the next; an entry starts with its offset, 0 ends the table.
_port
	movem.l	d0-d2/a0-a2,-(sp)
	lea	_pl_v2(pc),a0
	cmpa.l	a0,a4
	bne.s	.done
	lea	_gwall(pc),a0
	move.w	#12,(a0)
	lea	_gofs(pc),a0
	moveq	#(_gofs_end-_gofs)/4-1,d1
.g	move.l	(a0),d0
	bsr.s	_port_off
	move.l	d0,(a0)+
	dbf	d1,.g
	lea	_ds_sites(pc),a0	;SITE: size << 24 | offset, then the two views' values
.s	move.l	(a0),d0
	beq.s	.tabs
	move.l	d0,d2
	andi.l	#$ffffff,d0
	bsr.s	_port_off
	andi.l	#$ff000000,d2
	or.l	d2,d0
	move.l	d0,(a0)
	lea	12(a0),a0
	bra.s	.s
.tabs	lea	_port_tabs(pc),a1
.t	move.w	(a1)+,d1		;the table, from _port_tabs; 0 ends
	beq.s	.done
	lea	-2(a1,d1.w),a0
	move.w	(a1)+,d1		;the entries' size
.e	move.l	(a0),d0
	beq.s	.t
	bsr.s	_port_off
	move.l	d0,(a0)
	adda.w	d1,a0
	bra.s	.e
.done	movem.l	(sp)+,d0-d2/a0-a2
	rts

; d0 = a $c4dc game offset: the CD32 version's (the distance of the last segment that
; starts at or below it)
_port_off
	movem.l	d1/a2,-(sp)
	lea	_port_segs(pc),a2
	moveq	#0,d1
.s	cmp.l	(a2),d0
	blo.s	.in
	move.l	4(a2),d1
	addq.l	#8,a2
	bra.s	.s
.in	add.l	d1,d0
	movem.l	(sp)+,d1/a2
	rts

PTAB	MACRO			;a table of game offsets, the bytes an entry
	dc.w	\1-*,\2
	ENDM
_port_tabs
	PTAB	_ds_stridetabs,6
	IFND	LORES
	PTAB	_t_ptrs,8
	IFD	PENS
	PTAB	_t_penptrs,8
	PTAB	_t_halve,6
	ENDC
	ENDC
	dc.w	0

_port_segs
	INCLUDE	cd32segs.s		;(start, distance) pairs, then $ffffffff
