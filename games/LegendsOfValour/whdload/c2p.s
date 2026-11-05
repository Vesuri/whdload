; W1: CPU-selected Kalms C2P. Only CUSTOM2 bit 0 writes game instructions.
; Ten-byte hook covers whole instructions. VERIFY copies the relocated original
; prologue at runtime, so no original game bytes or translated routine are shipped.
_c2p_install
		movem.l	d0-a6,-(sp)
		move.l	(_custom2,pc),d0
		btst	#0,d0
		beq	.done
		move.l	(_custom1,pc),d0
		bne	.done			;CHARACT is not AMIGA2
		move.l	(_h12,pc),a0
		cmp.l	#$48e7fffe,($54ce,a0)
		bne	.bad
		cmp.w	#$2079,($54d2,a0)
		bne	.bad
		move.l	(_h11,pc),d0
		add.l	#$5fc2,d0
		cmp.l	($54d4,a0),d0
		bne	.bad
		lea	(c2p1x1_4_c5_bm_word,pc),a1
		move.l	(_lov_attnflags,pc),d0
		btst	#1,d0			;AFB_68020, includes later CPUs
		beq	.cpu
		lea	(c2p1x1_4_c5_bm,pc),a1
.cpu		lea	(_c2p_function,pc),a2
		move.l	a1,(a2)
	IFD VERIFY
		lea	(_c2p_original,pc),a1
		move.l	($54ce,a0),(a1)+
		move.l	($54d2,a0),(a1)+
		move.w	($54d6,a0),(a1)+
		move.w	#$4ef9,(a1)+
		lea	($54d8,a0),a2
		move.l	a2,(a1)
	ENDC
	; PERF_RANGE is declared beside the call in LegendsOfValourHD.s.
		move.w	#$4ef9,($54ce,a0)
		lea	(_c2p_entry,pc),a1
		move.l	a1,($54d0,a0)
		move.l	#$4e714e71,($54d4,a0)
		move.l	(_resload,pc),a2
		jsr	(resload_FlushCache,a2)
.done		movem.l	(sp)+,d0-a6
		rts
.bad		lea	(_c2p_badcode,pc),a0
		bra	_c2p_abort

_c2p_entry	movem.l	d0-a6,-(sp)
		move.l	(_h12,pc),a5
		move.w	($2e,a5),d0
		move.w	($30,a5),d1
		cmp.w	#192,d0
		bhi	_c2p_geometry_bad
		tst.w	d0
		beq	_c2p_geometry_bad
		cmp.w	#92,d1
		bhi	_c2p_geometry_bad
		tst.w	d1
		beq	_c2p_geometry_bad
	; Enclose to a word-aligned left edge and a 32-pixel-multiple width.
		moveq	#0,d2
		move.w	($3e,a5),d2
		and.w	#15,d2
		move.w	d0,d3
		add.w	d2,d3
		add.w	#31,d3
		and.w	#$ffe0,d3
		cmp.w	#192,d3
		bhi	_c2p_geometry_bad
		lea	(_c2p_width,pc),a0
		move.w	d3,(a0)
		move.w	d2,(_c2p_left-_c2p_width,a0)
		move.w	d1,(_c2p_height-_c2p_width,a0)
		lsr.w	#3,d2
		lea	(_c2p_bitmap+bm_Planes,pc),a1
		lea	($42,a5),a2
		moveq	#4-1,d4
.planes		move.l	(a2)+,d5
		sub.l	d2,d5
		move.l	d5,(a1)+
		dbf	d4,.planes
	IFD VERIFY
		move.l	(_custom5,pc),d4
		btst	#1,d4
		beq	.notwin
		bsr	_c2p_twin_before
.notwin
	ENDC
		bsr	_c2p_edges_save
	; Large view reads the game's source directly. Smaller views use a private
	; 192-byte-stride staging area: preserve source column 0 and never write left of it.
		move.l	(_h11,pc),a0
		move.l	($5fc2,a0),a0
		move.w	(_c2p_width,pc),d0
		cmp.w	($2e,a5),d0
		beq	.convert
	IFD VERIFY
		lea	(_c2p_function,pc),a1
		adda.l	#_c2p_chunky-_c2p_function,a1
	ELSE
		lea	(_c2p_chunky,pc),a1
	ENDC
		move.w	(_c2p_height,pc),d6
		subq.w	#1,d6
.row		move.l	a0,a2
		move.l	a1,a3
		move.w	(_c2p_left,pc),d2
		move.w	d2,d3
		beq	.copy
		subq.w	#1,d2
.left		clr.b	(a3)+
		dbf	d2,.left
.copy		move.w	($2e,a5),d2
		add.w	d2,d3
		subq.w	#1,d2
.pixels		move.b	(a2)+,(a3)+
		dbf	d2,.pixels
		move.w	(_c2p_width,pc),d2
		sub.w	d3,d2
		beq	.next
		subq.w	#1,d2
.right		clr.b	(a3)+
		dbf	d2,.right
.next		lea	192(a0),a0
		lea	192(a1),a1
		dbf	d6,.row
	IFD VERIFY
		lea	(_c2p_function,pc),a0
		adda.l	#_c2p_chunky-_c2p_function,a0
	ELSE
		lea	(_c2p_chunky,pc),a0
	ENDC
.convert	move.w	(_c2p_width,pc),d0
		move.w	(_c2p_height,pc),d1
		moveq	#0,d2
		moveq	#0,d3
		lea	(_c2p_bitmap,pc),a1
		move.l	(_c2p_function,pc),a2
		jsr	(a2)
		bsr	_c2p_edges_restore
	IFD VERIFY
		move.l	(_custom5,pc),d0
		btst	#1,d0
		beq	.notest
		bsr	_c2p_twin_after
.notest
	ENDC
		movem.l	(sp)+,d0-a6
_c2p_return	rts

; An enclosing row can still contain pixels from a previous larger view at startup
; or during a view change. Preserve every extra screen byte, even when not black.
_c2p_edges_save	movem.l	d0-a6,-(sp)
		moveq	#0,d7
		bra	_c2p_edges_io
_c2p_edges_restore movem.l d0-a6,-(sp)
		moveq	#1,d7
_c2p_edges_io
		move.w	(_c2p_width,pc),d0
		cmp.w	($2e,a5),d0
		beq	.done
		lsr.w	#3,d0
		moveq	#0,d5
		move.w	(_c2p_left,pc),d5
		lsr.w	#3,d5
		move.w	($2e,a5),d6
		lsr.w	#3,d6
		sub.w	d0,d6
		neg.w	d6
		sub.w	d5,d6
		sub.w	d6,d0			;right padding begins at this byte
		lea	(_c2p_bitmap,pc),a2
		adda.l	#_c2p_edges-_c2p_bitmap,a2
		lea	(_c2p_bitmap+bm_Planes,pc),a3
		moveq	#4-1,d4
.plane		move.l	(a3)+,a0
		move.w	(_c2p_height,pc),d3
		subq.w	#1,d3
.row		move.l	a0,a1
		move.w	d5,d1
		beq	.right
		subq.w	#1,d1
.left		tst.w	d7
		bne	.leftput
		move.b	(a1)+,(a2)+
		bra	.leftnext
.leftput	move.b	(a2)+,(a1)+
.leftnext	dbf	d1,.left
.right		move.l	a0,a1
		add.w	d0,a1
		move.w	d6,d1
		beq	.next
		subq.w	#1,d1
.rightbyte	tst.w	d7
		bne	.rightput
		move.b	(a1)+,(a2)+
		bra	.rightnext
.rightput	move.b	(a2)+,(a1)+
.rightnext	dbf	d1,.rightbyte
.next		lea	40(a0),a0
		dbf	d3,.row
		dbf	d4,.plane
.done		movem.l	(sp)+,d0-a6
		rts

_c2p_geometry_bad	lea	(_c2p_badgeometry,pc),a0
_c2p_abort	pea	(a0)
		pea	TDREASON_FAILMSG
		move.l	(_resload,pc),a2
		jmp	(resload_Abort,a2)

_c2p_badcode	dc.b	"C2P: unexpected AMIGA2 conversion entry",0
_c2p_badgeometry dc.b	"C2P: unsupported view geometry",0
		EVEN
		CNOP 0,4
_c2p_function	dc.l	0
_c2p_width	dc.w	0
_c2p_left	dc.w	0
_c2p_height	dc.w	0
		EVEN
_c2p_bitmap	dc.w	40,200
		dc.b	0,4
		dc.w	0
		ds.l	8

	IFD VERIFY
		INCLUDE	c2p_verify.s
	ENDC
		INCLUDE	kalms/c2p1x1_4_c5_bm_word.s
		INCLUDE	kalms/c2p1x1_4_c5_bm.s
