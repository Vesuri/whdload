 include "timing-offsets.i"
; Native 0658 weapons/actors with private deadline fire flags and RNG.
; Standalone. Requires timing-world-rng.i; native callbacks remain authoritative.
WW_CODE_SIZE equ GS0_9b9a-GS0_979c          ; +0979c..+09b9a, includes RTS
WW_SIZE equ WW_CODE_SIZE+4     ; native player binding after code

; a0=hunk 0, a1=even clone, a2=deadline RNG, a3=private two-byte fire packet,
; a4=hunk 6. Return 0/-1; preserve non-result registers. Validate before writes.
; Caller validates version, owns nonoverlapping lifetimes and flushes caches.
world_weapons_prepare:
	movem.l d1-d3/a0-a6,-(sp)
	movea.l a0,a6
	adda.l #GS0_979c,a0
	cmpi.w #$4239,(a0)
	bne .bad
	movea.l a6,a5
	adda.l #GS0_b92c,a5
	cmpa.l 2(a0),a5
	bne .bad
	cmpi.w #$4eb9,$1a(a0)
	bne .bad
	movea.l a6,a5
	adda.l #GS0_bed4,a5
	cmpa.l $1c(a0),a5
	bne .bad
	cmpi.w #$4eb9,(GS0_99fa-GS0_979c)(a0)
	bne .bad
	lea GS0_7a5c(a6),a5
	cmpa.l (GS0_99fc-GS0_979c)(a0),a5
	bne .bad
	cmpi.w #$4e75,WW_CODE_SIZE-2(a0)
	bne .bad
	lea .fire(pc),a6
	moveq #7,d3
.validate:
	move.w (a6)+,d1
	move.w (a6)+,d2
	cmp.w -2(a0,d1.w),d2
	bne .bad
	moveq #0,d2
	move.w (a6)+,d2
	lea $4292(a4),a5
	adda.l d2,a5
	cmpa.l 0(a0,d1.w),a5
	bne .bad
	dbf d3,.validate
	movea.l a1,a5
	move.w #WW_CODE_SIZE/2-1,d3
.copy:
	move.w (a0)+,(a5)+
	dbf d3,.copy
	lea $3b88(a4),a5
	move.l a5,WW_CODE_SIZE(a1)
	move.l a2,(GS0_99fc-GS0_979c)(a1)          ; native default bound 256 entry
	lea .fire(pc),a6
	moveq #7,d3
.patch:
	move.w (a6)+,d1
	addq.l #2,a6
	moveq #0,d2
	move.w (a6)+,d2
	movea.l a3,a5
	adda.l d2,a5
	move.l a5,0(a1,d1.w)
	dbf d3,.patch
	moveq #0,d0
	bra .done
.bad:
	moveq #-1,d0
.done:
	movem.l (sp)+,d1-d3/a0-a6
	rts
.fire:
	; operand offset, native opcode, byte offset within the two-byte packet
	dc.w $016,$4239,0,$05e,$4a79,0,(GS0_9832-GS0_979c),$4279,0,(GS0_995a-GS0_979c),$4a39,0
	dc.w (GS0_9a92-GS0_979c),$4239,0,(GS0_9b7a-GS0_979c),$4239,0,(GS0_983c-GS0_979c),$4a39,1,(GS0_9854-GS0_979c),$4239,1

; a0=native authoritative player with trailing object tables, a1=prepared clone.
; Return 0/-1, preserve others. Authoritative effects are real, not a preview.
; Run once per world tick after committed player motion and command dispatch.
world_weapons_step:
	movem.l d1-d7/a0-a6,-(sp)
	cmpa.l WW_CODE_SIZE(a1),a0
	bne .bad
	movea.l a0,a5
	jsr (a1)
	moveq #0,d0
	bra .done
.bad:
	moveq #-1,d0
.done:
	movem.l (sp)+,d1-d7/a0-a6
	rts
