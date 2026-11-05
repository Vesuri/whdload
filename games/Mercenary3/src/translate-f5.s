; F5 (Custom1 bit 20): the render scratch (chip $340..$407F) in fast RAM.
; Requires M1, S3 and F2 on a 68020+ with real fast RAM. The copied code is
; translated, not copied: tools/translate.py generates translate-f5.i from
; the game's Disk.1, an edit recipe per block that rewrites the scratch
; operands as 32-bit addresses ((bd.l,An) and abs.l) and re-targets the
; branches the growth moves. Tables use 6-byte entries: 68020+ only.

_f5on	dc.b	0
	even

_f5check
	btst	#4,(_custom1+1,pc)
	beq.b	.done
	btst	#5,(_custom1+3,pc)		;M1
	beq.b	.done
	btst	#1,(_custom1+2,pc)		;S3
	beq.b	.done
	btst	#1,(_custom1+1,pc)		;F2
	beq.b	.done
	move.w	(_attn,pc),d0
	btst	#AFB_68020,d0
	beq.b	.done
	move.l	(_expmem,pc),d0
	cmpi.l	#$200000,d0
	blo.b	.done
	cmpi.l	#$a00000,d0
	blo.b	.on
	cmpi.l	#$1000000,d0
	blo.b	.done
.on	lea	(_f5on,pc),a0
	st	(a0)
.done	rts

; d7 = 0: translate the M1 blocks; 1: the render blocks.
_f5translate
	movem.l	d0-d7/a0-a6,-(sp)
	lea	(_f5_blocks,pc),a4
.block	move.l	(a4),d0
	beq.w	.done
	move.l	(8,a4),d1
	moveq	#0,d2
	cmpi.l	#F5RENDER,d1
	blo.b	.kind
	moveq	#1,d2
.kind	cmp.w	d7,d2
	bne.w	.nextblock
	movea.l	d0,a0				;original
	movea.l	d1,a1
	adda.l	(_expmem,pc),a1			;translation
	lea	(_f5_blocks,pc),a2
	adda.l	(12,a4),a2			;recipe
.op	move.w	(a2)+,d0
	beq.b	.nextblock
	move.w	d0,d1
	andi.w	#$0fff,d1
	lsr.w	#8,d0
	lsr.w	#4,d0
	subq.w	#1,d0
	beq.b	.copy
	subq.w	#1,d0
	beq.b	.skip
	subq.w	#1,d0
	beq.b	.xor
	subq.w	#1,d0
	beq.b	.word
	subq.w	#1,d0
	beq.b	.extd
	subq.w	#1,d0
	beq.b	.setlo
; abs.w -> abs.l of the moved data
	moveq	#0,d0
	move.w	(a2)+,d0
	bsr.w	_f5datamap
	move.l	d0,(a1)+
	addq.l	#2,a0
	bra.b	.op
.copy	subq.w	#1,d1
.c	move.w	(a0)+,(a1)+
	dbra	d1,.c
	bra.b	.op
.skip	add.w	d1,d1
	adda.w	d1,a0
	bra.b	.op
.xor	move.w	(a0)+,d0			;opcode: addressing mode bits
	eor.w	d1,d0
	move.w	d0,(a1)+
	bra.b	.op
.word	move.w	(a2)+,(a1)+			;new displacement
	bra.b	.op
; (d16,An) -> (bd.l,An): full-format extension, no index, long displacement
.extd	move.w	#$0170,(a1)+
	moveq	#0,d0
	move.w	(a2)+,d0
	bsr.w	_f5datamap
	move.l	d0,(a1)+
	addq.l	#2,a0
	bra.b	.op
.setlo	move.w	(a0)+,d0			;byte branch displacement
	move.b	d1,d0
	move.w	d0,(a1)+
	bra.b	.op
.nextblock
	lea	(20,a4),a4
	bra.w	.block
.done	movem.l	(sp)+,d0-d7/a0-a6
	rts

; d0: original code address -> translated address (unchanged outside the
; blocks), after F2's dispatch aliases. Preserves all other registers.
_f5map
	movem.l	d1-d4/a2-a3,-(sp)
	lea	(_render_aliases,pc),a2
.alias	move.l	(a2)+,d1
	beq.b	.blocks
	move.l	(a2)+,d2
	cmp.l	d1,d0
	bne.b	.alias
	move.l	d2,d0
.blocks	lea	(_f5_blocks,pc),a2
.next	move.l	(a2)+,d1
	beq.b	.done
	move.l	(a2)+,d2
	cmp.l	d1,d0
	blo.b	.skip
	cmp.l	d2,d0
	bhs.b	.skip
	move.l	d0,d3
	sub.l	d1,d0
	add.l	(a2)+,d0			;destination
	add.l	(_expmem,pc),d0
	addq.l	#4,a2
	lea	(_f5_blocks,pc),a3
	adda.l	(a2),a3				;growth: offset, bytes so far
	sub.l	d1,d3				;offset in the block (below $FFFF)
	moveq	#0,d4
.th	cmp.w	(a3)+,d3
	blo.b	.add
	move.w	(a3)+,d4
	bra.b	.th
.add	add.l	d4,d0
	bra.b	.done
.skip	lea	(12,a2),a2
	bra.b	.next
.done	movem.l	(sp)+,d1-d4/a2-a3
	rts

; d0: chip data address -> its fast-RAM address (unchanged if not moved).
_f5datamap
	movem.l	d1-d2/a2,-(sp)
	lea	(_f5_data,pc),a2
.next	move.l	(a2)+,d1
	beq.b	.done
	move.l	(a2)+,d2
	cmp.l	d1,d0
	blo.b	.skip
	cmp.l	d2,d0
	bhs.b	.skip
	add.l	(a2),d0
	add.l	(_expmem,pc),d0
	addi.l	#F5DATA,d0
	bra.b	.done
.skip	addq.l	#4,a2
	bra.b	.next
.done	movem.l	(sp)+,d1-d2/a2
	rts

; _hotrenderer with F5: d0 = ws_ExpMem.
_f5renderer
	addi.l	#STACKSIZE+HOTSIZE+TABLEMEM+RESTOREMEM,d0
	lea	(_render_base,pc),a0
	move.l	d0,(a0)
; The scratch keeps its current contents.
	move.l	#$340,d0
	bsr.w	_f5datamap
	movea.l	d0,a1
	lea	($340).w,a0
	move.w	#($4080-$340)/4-1,d0
.scratch
	move.l	(a0)+,(a1)+
	dbra	d0,.scratch
	IFD VERIFY
; Custom2 bit 7: fill the vacated chip scratch, so a missed user draws garbage.
; The boot stack below $1800 is in use.
	btst	#7,(_custom2+3,pc)
	beq.b	.notrip
	lea	($340).w,a0
	move.w	#($1400-$340)/4-1,d0
.trip1	move.l	#$a55aa55a,(a0)+
	dbra	d0,.trip1
	lea	($1800).w,a0
	move.w	#($4080-$1800)/4-1,d0
.trip2	move.l	#$a55aa55a,(a0)+
	dbra	d0,.trip2
.notrip
	ENDC
	moveq	#1,d7
	bsr.w	_f5translate
	lea	(_f2_operands,pc),a0
	bsr.b	.operands
	lea	(_f5_operands,pc),a0
	bsr.b	.operands
	bra.b	.branches
.operands
	move.l	(a0)+,d0
	beq.b	.opsdone
	movea.l	d0,a1
	move.l	(a1),d0
	bsr.w	_f5map
	move.l	d0,d3
	move.l	a1,d0
	bsr.w	_f5map
	movea.l	d0,a1
	move.l	d3,(a1)
	bra.b	.operands
.opsdone
	rts
.branches
	lea	(_f5_branches,pc),a0
.nextbr	move.l	(a0)+,d0
	beq.b	.entries
	bsr.w	_f5map
	movea.l	d0,a1				;displacement word in the translation
	move.l	(a0)+,d0
	bsr.w	_f5map
	move.l	d0,d3				;target
	move.l	(a0)+,d0
	add.l	(_expmem,pc),d0
	movea.l	d0,a3				;island
	move.w	#$4ef9,(a3)+
	move.l	d3,(a3)
	sub.l	a1,d0
	move.w	d0,(a1)
	bra.b	.nextbr
.entries
	lea	(_f2_entries,pc),a0
	bsr.b	.install
	lea	(_f5_entries,pc),a0
	bsr.b	.install
; P1 restores the moved data and translated code words, not their chip originals.
	lea	(_restore_ranges,pc),a0
.nextrange
	move.l	(a0),d0
	beq.b	.restored
	move.l	d0,d1
	bsr.w	_f5datamap
	cmp.l	d0,d1
	bne.b	.store
	bsr.w	_f5map
.store	move.l	d0,(a0)
	addq.l	#6,a0
	bra.b	.nextrange
.restored
	IFD VERIFY
	lea	(_poison_start,pc),a0
	move.l	(a0),d0
	bne.b	.pstart
	move.l	#$340,d0
.pstart	bsr.w	_f5datamap
	move.l	d0,(a0)+
	move.l	(a0),d0
	bne.b	.pend
	move.l	#$4000,d0
.pend	subq.l	#1,d0
	bsr.w	_f5datamap
	addq.l	#1,d0
	move.l	d0,(a0)
	ENDC
	rts
.install
	move.l	(a0)+,d0
	beq.b	.installed
	movea.l	d0,a1
	bsr.w	_f5map
	move.w	#$4ef9,(a1)+
	move.l	d0,(a1)
	bra.b	.install
.installed
	rts

	INCLUDE	"translate-f5.i"
