; VERIFY only, CUSTOM5 bit 1. Original C2P runs on the identical source into
; scratch planes seeded from the screen; compare 40 bytes per row, including
; the padded area and guards outside it. Abort at the first differing byte.
_c2p_twin_before
		movem.l	d0-a6,-(sp)
		bsr	_c2p_flip_low
		lea	(_c2p_bitmap+bm_Planes,pc),a2
		lea	(_c2p_bitmap,pc),a3
		adda.l	#_c2p_scratch-_c2p_bitmap,a3
		moveq	#4-1,d7
.plane		move.l	(a2)+,a0
		move.l	a3,a1
		move.w	(_c2p_height,pc),d6
		subq.w	#1,d6
.row		moveq	#10-1,d5
.copy		move.l	(a0)+,(a1)+
		dbf	d5,.copy
		dbf	d6,.row
		lea	40*92(a3),a3
		dbf	d7,.plane
	; Save and redirect the game's original view-origin plane pointers.
		lea	(h12_00042,a5),a0
		lea	(_c2p_saved_planes,pc),a1
		lea	(_c2p_bitmap,pc),a2
		adda.l	#_c2p_scratch-_c2p_bitmap,a2
		moveq	#0,d0
		move.w	(_c2p_left,pc),d0
		lsr.w	#3,d0
		add.l	d0,a2
		moveq	#4-1,d7
.redirect	move.l	(a0),(a1)+
		move.l	a2,(a0)+
		lea	40*92(a2),a2
		dbf	d7,.redirect
		bsr	_c2p_original
		lea	(h12_00042,a5),a0
		lea	(_c2p_saved_planes,pc),a1
		moveq	#4-1,d7
.restore	move.l	(a1)+,(a0)+
		dbf	d7,.restore
		movem.l	(sp)+,d0-a6
		rts

_c2p_twin_after
		movem.l	d0-a6,-(sp)
		lea	(_c2p_bitmap+bm_Planes,pc),a2
		lea	(_c2p_bitmap,pc),a3
		adda.l	#_c2p_scratch-_c2p_bitmap,a3
		moveq	#0,d0			;plane-major byte index, stride 3680
		moveq	#4-1,d7
.plane		move.l	(a2)+,a0
		move.l	a3,a1
		move.w	(_c2p_height,pc),d6
		subq.w	#1,d6
.row		moveq	#40-1,d5
.byte		cmpm.b	(a0)+,(a1)+
		bne	_c2p_difference
		addq.l	#1,d0
		dbf	d5,.byte
		dbf	d6,.row
		lea	40*92(a3),a3
		dbf	d7,.plane
		bsr	_c2p_flip_low		;restore the input bytes exactly
	; Record actual geometry and successful counts for each observed view size.
		lea	(_c2p_geometries,pc),a0
		lea	(_c2p_counts,pc),a1
		move.w	(h12_0002e,a5),d0
		moveq	#3-1,d7
.find		tst.w	(a0)
		beq	.record
		cmp.w	(a0),d0
		beq	.record
		addq.l	#8,a0
		addq.l	#4,a1
		dbf	d7,.find
		bra	_c2p_geometry_bad
.record		move.w	d0,(a0)
		move.w	(h12_00030,a5),(2,a0)
		move.w	(h12_0003e,a5),(4,a0)
		move.w	(h12_00040,a5),(6,a0)
		addq.l	#1,(a1)
		lea	(_c2p_tests,pc),a0
		addq.l	#1,(a0)
_c2p_test_done	nop
		movem.l	(sp)+,d0-a6
		rts

; Both routines see the same deliberately perturbed low nibble. Colour bits
; remain unchanged; the input bytes are restored after the successful comparison.
_c2p_flip_low	movem.l	d0-d2/a0-a1,-(sp)
		move.l	(_h11,pc),a0
		move.l	(h11_05fc2,a0),a0
		move.w	(h12_00030,a5),d2
		subq.w	#1,d2
.row		move.l	a0,a1
		move.w	(h12_0002e,a5),d1
		subq.w	#1,d1
.byte		eor.b	#$0f,(a1)+
		dbf	d1,.byte
		lea	192(a0),a0
		dbf	d2,.row
		movem.l	(sp)+,d0-d2/a0-a1
		rts

_c2p_difference
		lea	(_c2p_failure,pc),a2
		move.l	a0,(a2)+
		move.l	a1,(a2)+
		move.b	(-1,a0),(a2)+
		move.b	(-1,a1),(a2)+
		move.l	a1,d0
		lea	(_c2p_bitmap,pc),a0
		adda.l	#_c2p_scratch-_c2p_bitmap,a0
		sub.l	a0,d0
		subq.l	#1,d0
	; D0 identifies the first differing byte in the scratch plane layout.
		lea	(_c2p_diffhex,pc),a0
		moveq	#8-1,d1
.hex		rol.l	#4,d0
		move.l	d0,d2
		and.w	#15,d2
		add.b	#'0',d2
		cmp.b	#'9',d2
		bls	.digit
		add.b	#7,d2
.digit		move.b	d2,(a0)+
		dbf	d1,.hex
		lea	(_c2p_diffmsg,pc),a0
		bra	_c2p_abort

_c2p_diffmsg	dc.b	"C2P pixel twin: first differing plane byte $"
_c2p_diffhex	dc.b	"00000000",0
		EVEN
		CNOP 0,4
_c2p_original	ds.b	16
_c2p_saved_planes ds.l	4
_c2p_tests	dc.l	0
_c2p_geometries	ds.w	3*4
_c2p_counts	ds.l	3
_c2p_failure	ds.b	10
