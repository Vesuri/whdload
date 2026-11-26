;======================================================================
; Enhanced resolution (CUSTOM5), resolution plan step 3: the 1x1 views' palette, and every
; shade table remapped to its pens, built once when the game has loaded its walls, floor
; and objects (before the menu). The renderer will read pen bytes from these tables
; instead of 12-bit colour words from the game's own.
;
; The method (docs/resolution-plan.md, Colour) and the census behind it are in
; tools/colours.py, whose `build`, `remap` and `effects` are this code's model, bit for bit
; (`colours.py check` compares a dump of the area below with them):
; 1. a histogram of 12-bit colours: each shade-table entry weighted by its class's share,
;    its row's brightness ((rows - row)^2, row 0 the brightest) and its texel count;
; 2. pens: the POPULAR heaviest colours, then FARTHEST more, each the weighted colour
;    farthest (CIELAB) from the pens so far;
; 3. every 12-bit colour's nearest pen (CIELAB), and the tables remapped through that.
;
; Only the $c4dc version is hooked (_pl_v3). The area is the top PA_SIZE of ExpMem, above
; the stacks (EXPMEM is that much larger with the option compiled in). From PA_END on it is
; the build's scratch, free once the build is done.

; game offsets, hunk 0 of the $c4dc version
G_LOADOBJECTS	= $436d6	;LoadObjects, the last of the game's loads
G_HOOKRET	= $44aaa	;after its jsr at $44aa4 (PL_PS)
G_WALLTILES	= $42a66	;a pointer to each loaded wall file
G_WALLCHUNK	= $42b06	;(name, unpacked size) pairs, ended by zeros
G_FLOORTILE	= $55cee	;a pointer to the floor texture
G_FLOORPAL	= $536e6	;floorScaleCols: 15 rows of 256 colour words
G_TEXPAL	= $3e066	;TexturePal: textured polygons' 15 rows of 256
G_TEXMAPS	= $2e066	;TextureMaps: their 64 KB of texels
G_OBJECTS	= $2974a	;18 entries of (wad, ptr, frames, pal); a pal is 15 rows of 32
G_SKY		= $55d00	;BackPicture: 16416 colour words
G_BRIGHTEN	= $766d2	;brightentab: 5632 colour words
G_WATER		= $812d2	;waterfile: the water's 64 KB of texels

N_WALLS		= 14		;the area holds this many walls
N_OBJECTS	= 18
GUN		= 9		;DrawInGun draws entry 9 from its pal's first row
SKY_WORDS	= 16416
BRIGHT_WORDS	= 5632
WATER_ROWS	= 13
POPULAR		= 200
FARTHEST	= 40
PEN0		= 16		;pens 0-15: the border and the frame sprites
TOTAL		= $40000000	;the histogram's weight
SHARE_SUM	= 97		;the classes' shares, in _pal_hist
FLIN_T		= 36		;f(t) is a line up to t = 36 (of 4095)
FLIN_A		= 510456
FLIN_B		= 37025580

; the area: what stays
PA_OFF		= $156000	;from _expmem, which _start moves past the exec and dos
	IFND	LORES
PA_SIZE		= $b2000
	ELSE
PA_SIZE		= $66000
	ENDC
	IFND	ORIGINAL
	IFNE	EXPMEM-$158000-PA_SIZE
	FAIL	EXPMEM must be the game's $158000 and the area
	ENDC
	ENDC
PA_NPENS	= 0		;word: pens built, set last
PA_STATE	= 2		;word: 2 done; while building $10 + the step (1-7)
PA_PALETTE	= 4		;words: pen PEN0 + k's 12-bit colour
PA_MAP		= 512		;4096 bytes: each 12-bit colour's pen
PA_LIGHT	= 4608		;256 bytes each, pen to pen: light beams (brightentab),
PA_TINT		= 4864		;the water tint (red removed),
PA_PAUSE	= 5120		;the pause screen (half brightness)
PA_WALLS	= 5376		;N_WALLS * 1024
PA_FLOOR	= 19712		;3840
PA_POLY		= 23552		;3840
PA_OBJS		= 27392		;N_OBJECTS * 480, one per entry
PA_SKY		= 36032		;SKY_WORDS
PA_BRIGHT	= 52448		;BRIGHT_WORDS
PA_END		= 58080
; and what the build uses on the way
PA_HIST		= $e300		;4096 longs; then the cube-root table; then:
PA_FT		= PA_HIST
PA_PLAB		= PA_HIST	;the pens' (L, a, b) words, in pen order
PA_SL		= PA_HIST+2048	;the pens' (a, L, b, pen) words, sorted by a
PA_IDX		= PA_SL+2048	;bytes: for a = -2048..2047, the first PA_SL entry at or above
PA_LAB		= PA_HIST+16384	;4096 * (L, a, b) words
PA_ULIST	= PA_LAB+24576	;the colours with weight (words), later their PA_LAB offsets
PA_MD		= PA_ULIST+8192	;longs, one per colour in PA_ULIST; first the texel counts,
				;then the popular pens' (weight, colour, 0)
PA_SQ		= PA_MD+16384	;longs: the squares of -4095..4095 (CIELAB is within -2048..2047)
SQ_C		= 4095*4	;0's entry

PALEA	MACRO			;offset in the area, address register
	movea.l	a4,\2
	adda.l	#\1,\2
	ENDM
GLEA	MACRO			;game offset, address register
	movea.l	a5,\2
	adda.l	#\1,\2
	ENDM

; PL_PS at $44aa4: LoadObjects with the game's registers, then the build.
_p_loaded
	pea	.loaded(pc)
	move.l	4(sp),-(sp)
	subi.l	#G_HOOKRET-G_LOADOBJECTS,(sp)
	rts
.loaded
	movem.l	d0-d7/a0-a6,-(sp)
	movea.l	60(sp),a5
	suba.l	#G_HOOKRET,a5
	movea.l	_expmem(pc),a4
	adda.l	#PA_OFF,a4
	bsr.w	_pal_build
	bsr.w	_ds_stride
	movem.l	(sp)+,d0-d7/a0-a6
	rts

; a4 = the area, a5 = hunk 0
_pal_build
	movea.l	a4,a0
	move.w	#PA_END/4-1,d0
.clr	clr.l	(a0)+
	dbf	d0,.clr
	move.w	#$11,PA_STATE(a4)
	bsr.w	_pal_hist
	move.w	#$12,PA_STATE(a4)
	bsr.w	_pal_popular		;d7 = colours with weight, d6 = pens
	move.w	#$13,PA_STATE(a4)
	bsr.w	_pal_lab
	bsr.w	_pal_squares
	move.w	#$14,PA_STATE(a4)
	bsr.w	_pal_farthest
	move.w	d6,PA_NPENS(a4)
	move.w	#$15,PA_STATE(a4)
	bsr.w	_pal_map
	move.w	#$16,PA_STATE(a4)
	bsr.w	_pal_remap
	move.w	#$17,PA_STATE(a4)
	bsr.w	_pal_effects
	move.w	#2,PA_STATE(a4)
	rts

;----------------------------------------------------------------------
; 1. The histogram

_pal_hist
	PALEA	PA_HIST,a2
	move.w	#4096-1,d0
.clr	clr.l	(a2)+
	dbf	d0,.clr
	PALEA	PA_HIST,a2
	; walls: count them, then each with its texel counts
	GLEA	G_WALLCHUNK+4,a0
	moveq	#0,d1
.nw	tst.l	(a0)
	beq.s	.nwd
	addq.l	#8,a0
	addq.w	#1,d1
	cmpi.w	#40,d1
	bne.s	.nw
.nwd	moveq	#45,d0
	bsr.w	_pal_budget
	GLEA	G_WALLCHUNK+4,a6
	GLEA	G_WALLTILES,a3
.wall	move.l	(a6),d0
	beq.s	.walld
	movea.l	(a3)+,a0
	move.l	a0,-(sp)
	lea	2048(a0),a0
	subi.l	#2048,d0
	lsr.l	#1,d0
	bsr.w	_pal_count32
	movea.l	(sp)+,a0
	moveq	#32,d0
	moveq	#32,d1
	PALEA	PA_MD,a1
	bsr.w	_pal_addtable
	addq.l	#8,a6
	bra.s	.wall
.walld
	; the floor, the polygons and the water: 256 colours a row, counts from 64 KB of texels
	movea.l	a5,a0
	adda.l	#G_FLOORTILE,a0
	movea.l	(a0),a0
	moveq	#30,d0
	GLEA	G_FLOORPAL,a3
	moveq	#15,d4
	bsr.w	.t256
	GLEA	G_TEXMAPS,a0
	moveq	#4,d0
	GLEA	G_TEXPAL,a3
	moveq	#15,d4
	bsr.w	.t256
	GLEA	G_WATER,a0
	moveq	#3,d0
	GLEA	G_BRIGHTEN,a3
	moveq	#WATER_ROWS,d4
	bsr.w	.t256
	; the sky: one row
	moveq	#2,d0
	moveq	#1,d1
	bsr.w	_pal_budget
	GLEA	G_SKY,a0
	moveq	#1,d0
	move.w	#SKY_WORDS,d1
	suba.l	a1,a1
	bsr.w	_pal_addtable
	; the objects: each pal once; the gun's first row only
	moveq	#0,d1
	moveq	#0,d5
.no	bsr.w	.newpal
	beq.s	.no1
	cmpi.w	#GUN,d5
	beq.s	.no1
	addq.w	#1,d1
.no1	addq.w	#1,d5
	cmpi.w	#N_OBJECTS,d5
	bne.s	.no
	moveq	#8,d0
	bsr.w	_pal_budget
	move.l	d2,d7			;the objects' budget
	moveq	#5,d0
	moveq	#1,d1
	bsr.w	_pal_budget		;d2 = the gun's
	moveq	#0,d5
.ob	bsr.s	.newpal
	beq.s	.ob1
	movea.l	d3,a0
	moveq	#32,d1
	suba.l	a1,a1
	moveq	#1,d0
	cmpi.w	#GUN,d5
	beq.s	.gun
	moveq	#15,d0
	exg	d2,d7
	bsr.w	_pal_addtable
	exg	d2,d7
	bra.s	.ob1
.gun	bsr.w	_pal_addtable
.ob1	addq.w	#1,d5
	cmpi.w	#N_OBJECTS,d5
	bne.s	.ob
	rts

; d5 = entry: d3 = its pal; Z clear when no earlier entry has that pal
.newpal
	GLEA	G_OBJECTS+12,a0
	move.w	d5,d0
	lsl.w	#4,d0
	move.l	(a0,d0.w),d3
	move.w	d5,d0
	bra.s	.np2
.np1	cmp.l	(a0),d3
	beq.s	.npx			;seen: Z set
	lea	16(a0),a0
.np2	dbf	d0,.np1
	moveq	#1,d0			;Z clear
	rts
.npx	moveq	#0,d0
	rts

; a0 = 64 KB of texels, d0 = share, a3 = the colour rows, d4 = rows
.t256	PALEA	PA_MD,a1
	bsr.w	_pal_count256
	moveq	#1,d1
	bsr.s	_pal_budget
	movea.l	a3,a0
	move.w	d4,d0
	move.w	#256,d1
	PALEA	PA_MD,a1
	bra.s	_pal_addtable

; d0 = share, d1 = tables in the class: d2 = TOTAL * share // (SHARE_SUM * tables)
_pal_budget
	movem.l	d0/d1/d3,-(sp)
	move.l	#TOTAL,d3
	mulu.l	d0,d2:d3
	mulu.w	#SHARE_SUM,d1
	divu.l	d1,d2:d3
	move.l	d3,d2
	movem.l	(sp)+,d0/d1/d3
	rts

; a0 = R rows of n colour words, d0 = R, d1 = n, a1 = n texel counts (longs) or 0 for 1
; each, d2 = budget, a2 = histogram. Entry (r, i) adds
; budget * (R - r)^2 * count_i // (sum of (R - r)^2 * sum of counts).
_pal_addtable
	movem.l	d0-d7/a0/a3,-(sp)
	move.l	a1,d3
	beq.s	.uni
	moveq	#0,d3
	movea.l	a1,a3
	move.w	d1,d5
	subq.w	#1,d5
.sc	add.l	(a3)+,d3
	dbf	d5,.sc
	bra.s	.sr
.uni	moveq	#0,d3
	move.w	d1,d3
.sr	moveq	#0,d4
	move.w	d0,d5
.sq	move.w	d5,d6
	mulu.w	d6,d6
	add.l	d6,d4
	subq.w	#1,d5
	bne.s	.sq
	mulu.l	d3,d4			;the divisor
	beq.s	.done
	move.w	d0,d5			;R - r, from R down to 1
.row	move.w	d5,d6
	mulu.w	d6,d6
	move.w	d1,d7
	subq.w	#1,d7
	move.l	a1,d3
	bne.s	.counted
	move.l	d6,d3			;one weight for the whole row
	mulu.l	d2,d0:d3
	divu.l	d4,d0:d3
.ue	move.w	(a0)+,d0
	andi.w	#$fff,d0
	add.l	d3,(a2,d0.w*4)
	dbf	d7,.ue
	bra.s	.next
.counted
	movea.l	a1,a3
.ce	move.l	(a3)+,d3
	mulu.l	d6,d3
	mulu.l	d2,d0:d3
	divu.l	d4,d0:d3
	move.w	(a0)+,d0
	andi.w	#$fff,d0
	add.l	d3,(a2,d0.w*4)
	dbf	d7,.ce
.next	subq.w	#1,d5
	bne.s	.row
.done	movem.l	(sp)+,d0-d7/a0/a3
	rts

; a0 = d0 texel words, three 5-bit texels each: their counts, 32 longs at PA_MD. The low
; two texels are counted together (1024 longs after those), then added in.
_pal_count32
	movem.l	d0-d3/a0-a2,-(sp)
	PALEA	PA_MD,a2
	movea.l	a2,a1
	move.w	#32+1024-1,d1
.clr	clr.l	(a1)+
	dbf	d1,.clr
	lea	128(a2),a1
	subq.l	#1,d0
	bcs.s	.fold
.w	move.w	(a0)+,d1
	move.w	d1,d2
	andi.w	#$3ff,d2
	addq.l	#1,(a1,d2.w*4)
	rol.w	#6,d1
	andi.w	#31,d1
	addq.l	#1,(a2,d1.w*4)
	dbf	d0,.w
	subi.l	#$10000,d0
	bcc.s	.w
.fold	moveq	#0,d1
.f	move.l	(a1)+,d2
	beq.s	.f1
	move.w	d1,d3
	andi.w	#31,d3
	add.l	d2,(a2,d3.w*4)
	move.w	d1,d3
	lsr.w	#5,d3
	add.l	d2,(a2,d3.w*4)
.f1	addq.w	#1,d1
	cmpi.w	#1024,d1
	bne.s	.f
	movem.l	(sp)+,d0-d3/a0-a2
	rts

; a0 = 65536 texel bytes: their counts, 256 longs at a1
_pal_count256
	movem.l	d0-d1/a0-a1,-(sp)
	move.w	#256-1,d0
.clr	clr.l	(a1)+
	dbf	d0,.clr
	lea	-1024(a1),a1
	move.w	#65536/4-1,d0
	moveq	#0,d1
.b	move.b	(a0)+,d1
	addq.l	#1,(a1,d1.w*4)
	move.b	(a0)+,d1
	addq.l	#1,(a1,d1.w*4)
	move.b	(a0)+,d1
	addq.l	#1,(a1,d1.w*4)
	move.b	(a0)+,d1
	addq.l	#1,(a1,d1.w*4)
	dbf	d0,.b
	movem.l	(sp)+,d0-d1/a0-a1
	rts

;----------------------------------------------------------------------
; 2. The POPULAR heaviest colours, heaviest first and the lowest colour of equals first:
; d7 = colours with weight (listed at PA_ULIST), d6 = pens taken (at PA_PALETTE). T, the
; POPULAR-th weight, by bisection; the pens are the weights over T, then the first at T,
; sorted.

_pal_popular
	PALEA	PA_HIST,a2
	PALEA	PA_ULIST,a1
	moveq	#0,d0
	moveq	#0,d7
	moveq	#0,d3			;the largest weight
.u	move.l	(a2,d0.w*4),d1
	beq.s	.u0
	move.w	d0,(a1)+
	addq.w	#1,d7
	cmp.l	d3,d1
	bls.s	.u0
	move.l	d1,d3
.u0	addq.w	#1,d0
	cmpi.w	#4096,d0
	bne.s	.u
	move.w	#POPULAR,d6
	cmp.w	d7,d6
	bls.s	.t
	move.w	d7,d6
.t	moveq	#1,d4			;lo: d6 colours weigh at least this
	addq.l	#1,d3			;hi: fewer do
.bis	move.l	d3,d0
	sub.l	d4,d0
	cmpi.l	#1,d0
	beq.s	.got
	lsr.l	#1,d0
	add.l	d4,d0			;mid
	PALEA	PA_ULIST,a1
	moveq	#0,d2
	move.w	d7,d5
	bra.s	.n2
.n1	move.w	(a1)+,d1
	cmp.l	(a2,d1.w*4),d0
	bhi.s	.n2
	addq.w	#1,d2
.n2	dbf	d5,.n1
	cmp.w	d6,d2
	bcs.s	.hi
	move.l	d0,d4
	bra.s	.bis
.hi	move.l	d0,d3
	bra.s	.bis
.got	PALEA	PA_MD,a3		;d4 = T: (weight, colour, 0) of each pen
	moveq	#0,d2
	PALEA	PA_ULIST,a1
	move.w	d7,d5
	bra.s	.a2
.a1	move.w	(a1)+,d1
	move.l	(a2,d1.w*4),d0
	cmp.l	d4,d0
	bls.s	.a2
	move.l	d0,(a3)+
	move.w	d1,(a3)+
	clr.w	(a3)+
	addq.w	#1,d2
.a2	dbf	d5,.a1
	PALEA	PA_ULIST,a1
	move.w	d7,d5
	bra.s	.b2
.b1	cmp.w	d6,d2
	beq.s	.sort
	move.w	(a1)+,d1
	cmp.l	(a2,d1.w*4),d4
	bne.s	.b2
	move.l	d4,(a3)+
	move.w	d1,(a3)+
	clr.w	(a3)+
	addq.w	#1,d2
.b2	dbf	d5,.b1
.sort	PALEA	PA_MD,a3		;insertion sort, heaviest first, stable
	moveq	#1,d5
	bra.s	.s3
.s1	move.w	d5,d0
	lsl.w	#3,d0
	lea	(a3,d0.w),a1
	move.l	(a1),d0
	move.l	4(a1),d1
.s2	cmpa.l	a3,a1
	beq.s	.s4
	cmp.l	-8(a1),d0
	bls.s	.s4
	move.l	-8(a1),(a1)
	move.l	-4(a1),4(a1)
	subq.l	#8,a1
	bra.s	.s2
.s4	move.l	d0,(a1)
	move.l	d1,4(a1)
	addq.w	#1,d5
.s3	cmp.w	d6,d5
	bcs.s	.s1
	lea	PA_PALETTE(a4),a1
	move.w	d6,d5
	bra.s	.w2
.w1	move.w	4(a3),(a1)+
	addq.l	#8,a3
.w2	dbf	d5,.w1
	rts

;----------------------------------------------------------------------
; CIELAB of every 12-bit colour, in 1/16 units: f() as a table of 4096 (t in 1/4095,
; f in 1/4096), then L = (116 fY - 65536) >> 8, a = 500 (fX - fY) >> 8,
; b = 200 (fY - fZ) >> 8.

_pal_lab
	movem.l	d6-d7,-(sp)
	PALEA	PA_FT,a0
	moveq	#0,d0			;t
	moveq	#0,d7			;floor(cbrt): it only grows with t
.ft	cmpi.w	#FLIN_T,d0
	bhi.s	.cbrt
	move.l	d0,d1
	mulu.l	#FLIN_A,d1
	addi.l	#FLIN_B,d1
	swap	d1
	move.w	d1,(a0)+
	bra.s	.ftn
.cbrt	move.l	d0,d2			;N = (t << 36) // 4095, as d2:d3
	lsl.l	#4,d2
	divul.l	#4095,d4:d2
	moveq	#0,d3
	divu.l	#4095,d4:d3
.inc	move.l	d7,d5			;while (x + 1)^3 <= N: x++
	addq.l	#1,d5
	move.l	d5,d6
	mulu.l	d5,d6
	mulu.l	d5,d4:d6
	cmp.l	d2,d4
	bhi.s	.got
	bcs.s	.take
	cmp.l	d3,d6
	bhi.s	.got
.take	addq.l	#1,d7
	bra.s	.inc
.got	move.w	d7,(a0)+
.ftn	addq.w	#1,d0
	cmpi.w	#4096,d0
	bne.s	.ft
	PALEA	PA_FT,a0
	PALEA	PA_LAB,a1
	lea	_pal_lin(pc),a2
	moveq	#0,d0			;the colour
.c	move.w	d0,d1
	lsr.w	#8,d1
	andi.w	#15,d1
	move.w	(a2,d1.w*2),d1
	move.w	d0,d2
	lsr.w	#4,d2
	andi.w	#15,d2
	move.w	(a2,d2.w*2),d2
	move.w	d0,d3
	andi.w	#15,d3
	move.w	(a2,d3.w*2),d3
	lea	_pal_xyz(pc),a3
	move.w	(a3)+,d7		;X
	mulu.w	d1,d7
	move.w	(a3)+,d5
	mulu.w	d2,d5
	add.l	d5,d7
	move.w	(a3)+,d5
	mulu.w	d3,d5
	add.l	d5,d7
	bsr.s	.f
	move.w	d7,d4
	move.w	(a3)+,d7		;Y
	mulu.w	d1,d7
	move.w	(a3)+,d6
	mulu.w	d2,d6
	add.l	d6,d7
	move.w	(a3)+,d6
	mulu.w	d3,d6
	add.l	d6,d7
	bsr.s	.f
	move.w	d7,d5
	move.w	(a3)+,d7		;Z
	mulu.w	d1,d7
	move.w	(a3)+,d1
	mulu.w	d2,d1
	add.l	d1,d7
	move.w	(a3)+,d1
	mulu.w	d3,d1
	add.l	d1,d7
	bsr.s	.f
	move.w	d7,d6
	moveq	#0,d7			;L
	move.w	d5,d7
	mulu.w	#116,d7
	subi.l	#65536,d7
	asr.l	#8,d7
	move.w	d7,(a1)+
	move.w	d4,d7			;a
	sub.w	d5,d7
	muls.w	#500,d7
	asr.l	#8,d7
	move.w	d7,(a1)+
	move.w	d5,d7			;b
	sub.w	d6,d7
	muls.w	#200,d7
	asr.l	#8,d7
	move.w	d7,(a1)+
	addq.w	#1,d0
	cmpi.w	#4096,d0
	bne.w	.c
	movem.l	(sp)+,d6-d7
	rts
; d7 = sum of products: f((d7 + 2048) >> 12, at most 4095)
.f	addi.l	#2048,d7
	lsr.l	#8,d7
	lsr.l	#4,d7
	cmpi.l	#4095,d7
	bls.s	.f1
	move.l	#4095,d7
.f1	move.w	(a0,d7.w*2),d7
	rts

; sRGB to linear (4095 = 1) of each 4-bit level, and linear RGB to XYZ over the D65
; white, times 4096 (tools/colours.py LIN and XYZ)
_pal_lin
	dc.w	0,23,66,136,237,372,544,755,1008,1304,1646,2035,2473,2961,3501,4095
_pal_xyz
	dc.w	1777,1541,778
	dc.w	871,2929,296
	dc.w	73,448,3576

;----------------------------------------------------------------------
; 3. FARTHEST more pens, each the colour farthest from the pens so far. d7 = colours in
; PA_ULIST, d6 = pens (in and out).

_pal_farthest
	; the list's colours become PA_LAB offsets (colour * 6); the pens' CIELAB to PA_PLAB
	PALEA	PA_ULIST,a0
	move.w	d7,d0
	bra.s	.o2
.o1	move.w	(a0),d1
	add.w	d1,d1
	move.w	d1,d2
	add.w	d1,d1
	add.w	d2,d1
	move.w	d1,(a0)+
.o2	dbf	d0,.o1
	PALEA	PA_LAB,a2
	PALEA	PA_PLAB,a1
	lea	PA_PALETTE(a4),a0
	move.w	d6,d0
	bra.s	.pl2
.pl1	move.w	(a0)+,d1
	bsr.w	.lab
.pl2	dbf	d0,.pl1
	; each colour's distance to its nearest pen
	move.w	d6,PA_NPENS(a4)
	bsr.w	_pal_sort
	movem.l	d6-d7/a5,-(sp)
	move.w	d7,-(sp)
	PALEA	PA_ULIST,a0
	PALEA	PA_MD,a5
	PALEA	PA_SL,a3
	PALEA	PA_SQ+SQ_C,a6
	bra.s	.i2
.i1	move.w	(a0)+,d4
	movem.w	PA_LAB(a4,d4.w),d1-d3
	bsr.w	_pal_near
	move.l	d0,(a5)+
.i2	subq.w	#1,(sp)
	bcc.s	.i1
	addq.l	#2,sp
	movem.l	(sp)+,d6-d7/a5
	PALEA	PA_LAB,a2
	; then FARTHEST times the farthest colour becomes a pen
	moveq	#FARTHEST-1,d5
.far	PALEA	PA_MD,a6
	PALEA	PA_ULIST,a3
	moveq	#0,d2			;the farthest distance
	moveq	#0,d3			;its PA_LAB offset
	move.w	d7,d4
	bra.s	.f2
.f1	move.w	(a3)+,d0
	move.l	(a6)+,d1
	cmp.l	d2,d1
	bls.s	.f2
	move.l	d1,d2
	move.w	d0,d3
.f2	dbf	d4,.f1
	tst.l	d2
	beq.s	.done
	moveq	#0,d1			;its colour: offset / 6
	move.w	d3,d1
	divu.w	#6,d1
	move.w	d6,d0
	add.w	d0,d0
	move.w	d1,PA_PALETTE(a4,d0.w)
	move.w	d6,d0			;its CIELAB after the pens'
	mulu.w	#6,d0
	PALEA	PA_PLAB,a1
	adda.l	d0,a1
	move.l	a1,-(sp)
	bsr.s	.lab
	movea.l	(sp)+,a1
	addq.w	#1,d6
	bsr.s	.update
	dbf	d5,.far
.done	rts

; d1 = colour: its CIELAB to (a1)+ (a2 = PA_LAB)
.lab	move.w	d1,d2
	add.w	d2,d2
	move.w	d2,d3
	add.w	d2,d2
	add.w	d3,d2
	move.l	(a2,d2.w),(a1)+
	move.w	4(a2,d2.w),(a1)+
	rts

; a1 = a pen's CIELAB: each listed colour's distance to its nearest pen, updated
.update
	movem.l	d0-d7/a0/a3/a6,-(sp)
	movem.w	(a1),d1-d3
	PALEA	PA_ULIST,a3
	PALEA	PA_MD,a6
	PALEA	PA_SQ+SQ_C,a0
	move.w	d7,d0
	bra.s	.u2
.u1	move.w	(a3)+,d4
	movem.w	(a2,d4.w),d4-d6
	sub.w	d1,d4
	move.l	(a0,d4.w*4),d4
	cmp.l	(a6),d4
	bcc.s	.u0
	sub.w	d2,d5
	add.l	(a0,d5.w*4),d4
	cmp.l	(a6),d4
	bcc.s	.u0
	sub.w	d3,d6
	add.l	(a0,d6.w*4),d4
	cmp.l	(a6),d4
	bcc.s	.u0
	move.l	d4,(a6)
.u0	addq.l	#4,a6
.u2	dbf	d0,.u1
	movem.l	(sp)+,d0-d7/a0/a3/a6
	rts

;----------------------------------------------------------------------
; The squares, for the distances

_pal_squares
	PALEA	PA_SQ+SQ_C,a6
	moveq	#0,d0			;v
	moveq	#0,d1			;v^2
.s	move.l	d1,(a6,d0.w*4)
	neg.w	d0
	move.l	d1,(a6,d0.w*4)
	neg.w	d0
	add.l	d0,d1
	add.l	d0,d1
	addq.l	#1,d1
	addq.w	#1,d0
	cmpi.w	#4096,d0
	bne.s	.s
	rts

; The PA_NPENS pens of PA_PLAB into PA_SL, sorted by a (insertion, stable), and PA_IDX
_pal_sort
	movem.l	d0-d7/a0-a3,-(sp)
	PALEA	PA_PLAB,a0
	PALEA	PA_SL,a3
	movea.l	a3,a1
	moveq	#PEN0,d6
	move.w	PA_NPENS(a4),d7
	bra.s	.c2
.c1	movem.w	(a0)+,d0-d2		;L, a, b
	movea.l	a1,a2
.ins	cmpa.l	a3,a2
	beq.s	.put
	cmp.w	-8(a2),d1
	bge.s	.put
	move.l	-8(a2),(a2)
	move.l	-4(a2),4(a2)
	subq.l	#8,a2
	bra.s	.ins
.put	move.w	d1,(a2)
	move.w	d0,2(a2)
	move.w	d2,4(a2)
	move.w	d6,6(a2)
	addq.w	#1,d6
	addq.l	#8,a1
.c2	dbf	d7,.c1
	PALEA	PA_IDX,a0
	movea.l	a3,a2
	moveq	#0,d0			;the entry
	move.w	#-2048,d1		;a
	move.w	PA_NPENS(a4),d7
.ix	cmp.w	d7,d0
	beq.s	.ixs
	cmp.w	(a2),d1
	ble.s	.ixs
	addq.w	#1,d0
	addq.l	#8,a2
	bra.s	.ix
.ixs	move.b	d0,(a0)+
	addq.w	#1,d1
	cmpi.w	#2048,d1
	bne.s	.ix
	movem.l	(sp)+,d0-d7/a0-a3
	rts

; d1-d3 = a colour's L, a, b: d0 = the distance to its nearest pen, d6 = that pen (the
; lowest of equals). From the first pen at or above its a, upward and then downward, until
; a alone is farther than the best. a3 = PA_SL, a6 = the squares' 0. Uses d4, d5, d7,
; a1, a2.
_pal_near
	moveq	#0,d4
	move.b	PA_IDX-PA_SL+2048(a3,d2.w),d4
	move.w	d4,d7
	swap	d7			;pens below
	move.w	PA_NPENS(a4),d7
	sub.w	d4,d7			;pens at and above
	lsl.w	#3,d4
	lea	(a3,d4.w),a1
	movea.l	a1,a2
	move.l	#$7fffffff,d0
	move.w	#$7fff,d6
	bra.s	.u2
.up	move.w	(a1),d5
	sub.w	d2,d5
	move.l	(a6,d5.w*4),d5
	cmp.l	d0,d5
	bhi.s	.down
	move.w	2(a1),d4
	sub.w	d1,d4
	add.l	(a6,d4.w*4),d5
	cmp.l	d0,d5
	bhi.s	.un
	move.w	4(a1),d4
	sub.w	d3,d4
	add.l	(a6,d4.w*4),d5
	cmp.l	d0,d5
	bhi.s	.un
	bcs.s	.ut
	cmp.w	6(a1),d6
	bls.s	.un
.ut	move.l	d5,d0
	move.w	6(a1),d6
.un	addq.l	#8,a1
.u2	dbf	d7,.up
.down	swap	d7
	bra.s	.d2
.dn	subq.l	#8,a2
	move.w	(a2),d5
	sub.w	d2,d5
	move.l	(a6,d5.w*4),d5
	cmp.l	d0,d5
	bhi.s	.done
	move.w	2(a2),d4
	sub.w	d1,d4
	add.l	(a6,d4.w*4),d5
	cmp.l	d0,d5
	bhi.s	.d2
	move.w	4(a2),d4
	sub.w	d3,d4
	add.l	(a6,d4.w*4),d5
	cmp.l	d0,d5
	bhi.s	.d2
	bcs.s	.dt
	cmp.w	6(a2),d6
	bls.s	.d2
.dt	move.l	d5,d0
	move.w	6(a2),d6
.d2	dbf	d7,.dn
.done	rts

;----------------------------------------------------------------------
;Every 12-bit colour's nearest pen (CIELAB; the first of equals), into PA_MAP

_pal_map
	movem.l	d6-d7/a5,-(sp)
	bsr.w	_pal_sort
	PALEA	PA_LAB,a0
	PALEA	PA_MAP,a5
	PALEA	PA_SL,a3
	PALEA	PA_SQ+SQ_C,a6
	move.w	#4096,-(sp)
.c	movem.w	(a0)+,d1-d3
	bsr.w	_pal_near
	move.b	d6,(a5)+
	subq.w	#1,(sp)
	bne.s	.c
	addq.l	#2,sp
	movem.l	(sp)+,d6-d7/a5
	rts

;----------------------------------------------------------------------
; The tables through PA_MAP: the walls, floor, polygons, every Objects entry's pal, the
; sky and brightentab, in the area's order

_pal_remap
	PALEA	PA_MAP,a2
	GLEA	G_WALLCHUNK+4,a6
	GLEA	G_WALLTILES,a3
	PALEA	PA_WALLS,a1
	moveq	#N_WALLS-1,d7
.w	tst.l	(a6)
	beq.s	.wd
	movea.l	(a3)+,a0
	move.l	#1024,d0
	bsr.s	.r
	addq.l	#8,a6
	dbf	d7,.w
.wd	PALEA	PA_FLOOR,a1
	GLEA	G_FLOORPAL,a0
	move.l	#3840,d0
	bsr.s	.r
	GLEA	G_TEXPAL,a0		;PA_POLY
	move.l	#3840,d0
	bsr.s	.r
	GLEA	G_OBJECTS+12,a3		;PA_OBJS
	moveq	#N_OBJECTS-1,d7
.o	movea.l	(a3),a0
	lea	16(a3),a3
	move.l	#480,d0
	bsr.s	.r
	dbf	d7,.o
	GLEA	G_SKY,a0		;PA_SKY
	move.l	#SKY_WORDS,d0
	bsr.s	.r
	GLEA	G_BRIGHTEN,a0		;PA_BRIGHT
	move.l	#BRIGHT_WORDS,d0
.r	move.w	(a0)+,d1
	andi.w	#$fff,d1
	move.b	(a2,d1.w),(a1)+
	subq.l	#1,d0
	bne.s	.r
	rts

; Pen to pen: light beams (brightentab by colour), the water tint (red removed), the pause
; screen ((colour & $eee) >> 1); pens without a colour map to themselves

_pal_effects
	PALEA	PA_LIGHT,a0		;three identities
	moveq	#0,d0
	move.w	#3*256-1,d1
.id	move.b	d0,(a0)+
	addq.b	#1,d0
	dbf	d1,.id
	GLEA	G_BRIGHTEN,a1
	PALEA	PA_MAP,a2
	lea	PA_PALETTE(a4),a0
	moveq	#PEN0,d2		;the pen
	move.w	PA_NPENS(a4),d7
	bra.s	.k2
.k	move.w	(a0)+,d0
	move.w	d0,d1
	add.w	d1,d1
	move.w	(a1,d1.w),d1
	andi.w	#$fff,d1
	move.b	(a2,d1.w),PA_LIGHT(a4,d2.w)
	move.w	d0,d1
	andi.w	#$0ff,d1
	move.b	(a2,d1.w),PA_TINT(a4,d2.w)
	move.w	d0,d1
	andi.w	#$eee,d1
	lsr.w	#1,d1
	move.b	(a2,d1.w),PA_PAUSE(a4,d2.w)
	addq.w	#1,d2
.k2	dbf	d7,.k
	rts
