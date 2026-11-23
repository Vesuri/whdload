;---------------------------------------------------------------------------
; Vroom's self-modifying code, made safe for CPU caches (docs/internals.md,
; "Self-modifying code"). Included by both slaves; the program is the same at
; every address here except the init code's two writers SMC_VBLW1/SMC_VBLW2,
; which the including source defines.
;
; The 3D renderer and the VBL routine rewrite instructions while the game runs.
; With the instruction cache on, the CPU keeps executing the old ones: the
; renderer recurses until its buffer runs off the end of BaseMem.
;
; - Changes to branches (the VBL routine's two JSR targets, a BSR/MOVE swap
;   in the renderer, three RTS inserted and removed again) become dispatches
;   through variables here: the game no longer writes those instructions.
; - Changes to other instructions (shift counts and a mask in four renderer
;   routines, one NOP/ASR) keep the game's writes and flush the caches after
;   them.
; - The bitmap scaler (cars, cockpit, panel, roadside objects) stores one of
;   16 instruction pairs from a table into its loop for every 4 pixels.
;   Precompiled pairs run instead, chosen through pointers decoded from the
;   table whenever the game rebuilds it.
;
; Applied on a 68020 or higher only: a 68000 or 68010 has no caches, and the
; game runs there unchanged. The stubs use 68020 instructions and keep the
; condition codes and stack as the replaced instructions left them.
;---------------------------------------------------------------------------

SMC_TRAMP	= $130			; JMP trampolines for the 4-byte sites,
					; after the original slave's ($100-$129)
SMC_LO		= SMC_VBLW1		; lowest and highest+1 patched address
SMC_HI		= $1A26E		; (Fix_Decrunched in src/fixes.i)

; IN:	-
; OUT:	-	all registers preserved
FixSMC		movem.l	d0-d1/a0-a2,-(a7)
		lea	_smc_state(pc),a2
		tst.b	(a2)
		bne.b	.known
		clr.l	-(a7)			; TAG_DONE
		clr.l	-(a7)
		pea	WHDLTAG_ATTNFLAGS_GET
		move.l	a7,a0
		move.l	_resload(pc),a1
		jsr	resload_Control(a1)
		move.l	4(a7),d0
		lea	12(a7),a7
		st	(a2)			; -1: no caches
		btst	#AFB_68020,d0
		beq.b	.done
		move.b	#1,(a2)			; 1: patch
		bsr.b	smc_Init
.known		tst.b	(a2)
		bmi.b	.done
		lea	SMC_TRAMP.w,a0
		lea	_smc_tramps(pc),a1
		moveq	#(_smc_tramps_end-_smc_tramps)/2-1,d1
.tramp		move.w	#$4EF9,(a0)+		; jmp xxx.l
		lea	_smc_tramps(pc),a2
		add.w	(a1)+,a2
		move.l	a2,(a0)+
		dbf	d1,.tramp
		lea	_smc_pl(pc),a0
		sub.l	a1,a1
		move.l	_resload(pc),a2
		jsr	resload_Patch(a2)	; flushes the caches
.done		movem.l	(a7)+,d0-d1/a0-a2
		rts

; The variables start from the program's own state, once: a reload over the
; program reapplies the patches but keeps them.
smc_Init	move.l	$A56C,_smc_vecA-_smc_state(a2)
		move.l	$A572,_smc_vecB-_smc_state(a2)
		move.l	$F98C,_smc_insA-_smc_state(a2)
		move.l	$F9B6,_smc_insB-_smc_state(a2)
		lea	smc_F8DE_run(pc),a0
		move.l	a0,_smc_pF8DE-_smc_state(a2)
		lea	smc_10654_run(pc),a0
		move.l	a0,_smc_p10654-_smc_state(a2)
		lea	smc_F9C0_run(pc),a0
		move.l	a0,_smc_pF9C0-_smc_state(a2)
		lea	scale_P00(pc),a0	; nop, nop: what the slots hold
		lea	_scale_ptrs(pc),a1
		moveq	#16+6-1,d0
.nop		move.l	a0,(a1)+
		dbf	d0,.nop
		rts

; Called after every decrunch: one that lands on patched code (the program
; reloads part of itself from $439C) gets the patches again.
; IN:	-
; OUT:	-	all registers preserved
	MACHINE	MC68020

;--- the VBL routine: jsr <vector> at $A56A and $A570, the vectors written by
;    seven instructions (patched to write _smc_vecA/_smc_vecB instead)
smc_VblA	jmp	([_smc_vecA,pc])
smc_VblB	jmp	([_smc_vecB,pc])

;--- the renderer's line routine: at $F98C and $F9B6 either
;    "move.w $FAD4(pc),(a0)+" or "bsr.w $FAD6" (whose routine starts with that
;    move), copied from $E48A-$E499 by 16 instructions (patched to write
;    _smc_insA/_smc_insB instead); the sites call these through trampolines
smc_DispA	cmpi.w	#$6100,_smc_insA(pc)	; bsr?
		beq.b	smc_Bsr
smc_Move	move.w	$FAD4,(a0)+
		rts
smc_DispB	cmpi.w	#$6100,_smc_insB(pc)
		bne.b	smc_Move
smc_Bsr		jmp	$FAD6

;--- RTS at $F8DE (subq.w #1,d4 / ble.w $F9A0), set at $F91C and cleared at
;    $F928 around the renderer's recursive call
smc_F8DE	jmp	([_smc_pF8DE,pc])
smc_F8DE_run	subq.w	#1,d4
		ble.b	.le
		jmp	$F8E4
.le		jmp	$F9A0

;--- RTS at $10654 (move.w $1067E(pc),d7 / cmp.w (a3),d7) and $F9C0
;    (move.b #-1,9(a0)), set at $FCB2/$FCBA and cleared at $FCDA/$FCE2
smc_10654	jmp	([_smc_p10654,pc])
smc_10654_run	move.w	$1067E,d7
		cmp.w	(a3),d7
		jmp	$1065A
smc_F9C0	jmp	([_smc_pF9C0,pc])
smc_F9C0_run	move.b	#-1,9(a0)
		jmp	$F9C6

smc_Rts		rts

; The set and clear sites replace "move.w #<instruction>,(an)": every
; instruction word written is positive and not zero, so that move left N, Z,
; V and C clear.
SMC_SET		MACRO	; pointer, target
		movem.l	a0/a1,-(a7)
		lea	\2(pc),a0
		lea	\1(pc),a1
		bra.b	smc_Store
		ENDM
smc_SetF8DE	SMC_SET	_smc_pF8DE,smc_Rts
smc_ClrF8DE	SMC_SET	_smc_pF8DE,smc_F8DE_run
smc_Set10654	SMC_SET	_smc_p10654,smc_Rts
smc_SetF9C0	SMC_SET	_smc_pF9C0,smc_Rts
smc_Clr10654	SMC_SET	_smc_p10654,smc_10654_run
smc_ClrF9C0	SMC_SET	_smc_pF9C0,smc_F9C0_run
smc_Store	move.l	a0,(a1)
		movem.l	(a7)+,a0/a1
		andi.b	#$10,ccr
		rts

;--- shift counts and masks: at the four routines $F66C, $F6DE, $F7C0 and
;    $F830 "andi.w #mask" and three shifts, copied from a table by
;    lea <routine>(pc),a1/a2 and four moves, 16 times; the moves are kept
smc_Sh1_10	move.w	(a0)+,(a1)
		move.w	(a0)+,4(a1)
		move.w	(a0)+,10(a1)
		move.w	(a0),$10(a1)
		bra.b	smc_Flush
smc_Sh1_12	move.w	(a0)+,(a1)
		move.w	(a0)+,4(a1)
		move.w	(a0)+,10(a1)
		move.w	(a0),$12(a1)
		bra.b	smc_Flush
smc_Sh2_12	move.w	(a0)+,(a2)
		move.w	(a0)+,4(a2)
		move.w	(a0)+,10(a2)
		move.w	(a0),$12(a2)
		bra.b	smc_Flush
smc_Sh2_14	move.w	(a0)+,(a2)
		move.w	(a0)+,4(a2)
		move.w	(a0)+,10(a2)
		move.w	(a0),$14(a2)
		bra.b	smc_Flush
;--- NOP or "asr.w #n,d4" at $ECA0, copied from $ECA4 at $EC84
smc_ECA0	move.w	(a4,d4.w),-4(a4)
smc_Flush	move.w	ccr,-(a7)
		move.l	a2,-(a7)
		move.l	_resload(pc),a2
		jsr	resload_FlushCache(a2)
		move.l	(a7)+,a2
		move.w	(a7)+,ccr
		rts


;--- the bitmap scaler: "jsr $100.w"/"jsr $106.w" (the original slave's
;    move.l (a4,d0.w),(a5)/(a6)) store entry d0/4 of the table at $1A340 into
;    a 4-byte slot that runs next, and $19FB0 branches back into a slot. The
;    stores become selections (sel_n: slot n's pair := entry d0/4) and each
;    slot a call of its selected pair (exe_n), so a branch into a slot still
;    reruns the last stored pair.
SMC_SEL		MACRO	; slot variable
		move.l	a0,-(a7)
		lea	\1(pc),a0
		move.l	(_scale_ptrs,pc,d0.w),(a0)
		move.l	(a7)+,a0
		rts
		ENDM
scale_Sel1	SMC_SEL	_scale_slot1
scale_Sel2	SMC_SEL	_scale_slot2
scale_Sel3	SMC_SEL	_scale_slot3
scale_Sel4	SMC_SEL	_scale_slot4
scale_Sel5	SMC_SEL	_scale_slot5
scale_Sel6	SMC_SEL	_scale_slot6
scale_Exe1	jmp	([_scale_slot1,pc])
scale_Exe2	jmp	([_scale_slot2,pc])
scale_Exe3	jmp	([_scale_slot3,pc])
scale_Exe4	jmp	([_scale_slot4,pc])
scale_Exe5	jmp	([_scale_slot5,pc])
scale_Exe6	jmp	([_scale_slot6,pc])

; the table's writers: two copies of 16 entries from $1A440 or $1A480
; (move.l (a3)+,(a4)+ / dbf d0) and one entry from $1A33C
scale_Copy	move.l	(a3)+,(a4)+
		dbf	d0,scale_Copy
		bra.b	scale_Sync
scale_SetEntry	move.l	$1A33C,(a0,d0.w)
		move.w	ccr,-(a7)
		bsr.b	scale_Sync
		move.w	(a7)+,ccr
		rts

; Decode the table into _scale_ptrs. Its entries are a first instruction
; (nop, or.w d7,d3, or.l d5,d3, or.l d7,d3 or or.l d7,d2) and a second one
; (nop, or.w d7,d4, or.l d5,d4 or or.l d7,d4); no other values occur. An
; unknown word counts as nop.
; IN:	-
; OUT:	-	all registers preserved, CCR changed
scale_Sync	movem.l	d0-d3/a0-a2,-(a7)
		lea	$1A340,a0
		lea	_scale_ptrs(pc),a1
		moveq	#16-1,d3
.entry		moveq	#0,d0
		move.w	(a0)+,d1
		lea	.first(pc),a2
.f		cmp.w	(a2)+,d1
		beq.b	.fok
		addq.w	#1,d0
		cmp.w	#5,d0
		blo.b	.f
		moveq	#0,d0
.fok		lsl.w	#2,d0			; first * 4
		moveq	#0,d2
		move.w	(a0)+,d1
		lea	.second(pc),a2
.s		cmp.w	(a2)+,d1
		beq.b	.sok
		addq.w	#1,d2
		cmp.w	#4,d2
		blo.b	.s
		moveq	#0,d2
.sok		add.w	d2,d0			; first * 4 + second
		lea	scale_Pairs(pc),a2
		add.w	d0,d0
		add.w	(a2,d0.w),a2
		move.l	a2,(a1)+
		dbf	d3,.entry
		movem.l	(a7)+,d0-d3/a0-a2
		rts
.first		dc.w	$4E71,$8647,$8685,$8687,$8487
.second		dc.w	$4E71,$8847,$8885,$8887

SMC_PAIR	MACRO	; first index, second index
		IFEQ	\1-1
		or.w	d7,d3
		ENDC
		IFEQ	\1-2
		or.l	d5,d3
		ENDC
		IFEQ	\1-3
		or.l	d7,d3
		ENDC
		IFEQ	\1-4
		or.l	d7,d2
		ENDC
		IFEQ	\2-1
		or.w	d7,d4
		ENDC
		IFEQ	\2-2
		or.l	d5,d4
		ENDC
		IFEQ	\2-3
		or.l	d7,d4
		ENDC
		rts
		ENDM
scale_Pairs
		dc.w	scale_P00-scale_Pairs
		dc.w	scale_P01-scale_Pairs
		dc.w	scale_P02-scale_Pairs
		dc.w	scale_P03-scale_Pairs
		dc.w	scale_P10-scale_Pairs
		dc.w	scale_P11-scale_Pairs
		dc.w	scale_P12-scale_Pairs
		dc.w	scale_P13-scale_Pairs
		dc.w	scale_P20-scale_Pairs
		dc.w	scale_P21-scale_Pairs
		dc.w	scale_P22-scale_Pairs
		dc.w	scale_P23-scale_Pairs
		dc.w	scale_P30-scale_Pairs
		dc.w	scale_P31-scale_Pairs
		dc.w	scale_P32-scale_Pairs
		dc.w	scale_P33-scale_Pairs
		dc.w	scale_P40-scale_Pairs
		dc.w	scale_P41-scale_Pairs
		dc.w	scale_P42-scale_Pairs
		dc.w	scale_P43-scale_Pairs

scale_P00		SMC_PAIR	0,0
scale_P01		SMC_PAIR	0,1
scale_P02		SMC_PAIR	0,2
scale_P03		SMC_PAIR	0,3
scale_P10		SMC_PAIR	1,0
scale_P11		SMC_PAIR	1,1
scale_P12		SMC_PAIR	1,2
scale_P13		SMC_PAIR	1,3
scale_P20		SMC_PAIR	2,0
scale_P21		SMC_PAIR	2,1
scale_P22		SMC_PAIR	2,2
scale_P23		SMC_PAIR	2,3
scale_P30		SMC_PAIR	3,0
scale_P31		SMC_PAIR	3,1
scale_P32		SMC_PAIR	3,2
scale_P33		SMC_PAIR	3,3
scale_P40		SMC_PAIR	4,0
scale_P41		SMC_PAIR	4,1
scale_P42		SMC_PAIR	4,2
scale_P43		SMC_PAIR	4,3

	MACHINE	MC68000

_smc_tramps	dc.w	smc_DispA-_smc_tramps		; SMC_TRAMP+0
		dc.w	smc_DispB-_smc_tramps		; +6
		dc.w	smc_SetF8DE-_smc_tramps		; +12
		dc.w	smc_ClrF8DE-_smc_tramps		; +18
		dc.w	smc_Set10654-_smc_tramps	; +24
		dc.w	smc_SetF9C0-_smc_tramps		; +30
		dc.w	smc_Clr10654-_smc_tramps	; +36
		dc.w	smc_ClrF9C0-_smc_tramps		; +42
		dc.w	scale_Sel1-_smc_tramps		; 8
		dc.w	scale_Exe1-_smc_tramps
		dc.w	scale_Sel2-_smc_tramps		; 10
		dc.w	scale_Exe2-_smc_tramps
		dc.w	scale_Sel3-_smc_tramps		; 12
		dc.w	scale_Exe3-_smc_tramps
		dc.w	scale_Sel4-_smc_tramps		; 14
		dc.w	scale_Exe4-_smc_tramps
		dc.w	scale_Sel5-_smc_tramps		; 16
		dc.w	scale_Exe5-_smc_tramps
		dc.w	scale_Sel6-_smc_tramps		; 18
		dc.w	scale_Exe6-_smc_tramps
_smc_tramps_end

SMC_JSRW	MACRO	; site, trampoline index: jsr SMC_TRAMP+6*index.w
		PL_L	\1,$4EB80000+SMC_TRAMP+6*\2
		ENDM

_smc_pl		PL_START
	; VBL vectors
		PL_PS	$A56A,smc_VblA
		PL_PS	$A570,smc_VblB
		PL_PA	SMC_VBLW1,_smc_vecB	; move.l #x,$A572
		PL_PA	SMC_VBLW2,_smc_vecA	; move.l #x,$A56C
		PL_PA	$9408,_smc_vecB
		PL_PA	$9414,_smc_vecB
		PL_PA	$A302,_smc_vecA		; move.l (a0,d0.w),$A56C
		PL_PA	$A35E,_smc_vecA
		PL_PA	$A3C8,_smc_vecA
	; the line routine: move.l $E48A-$E499(pc),$F98C/$F9B6
		SMC_JSRW $F98C,0
		SMC_JSRW $F9B6,1
		PL_PA	$E292+4,_smc_insA
		PL_PA	$E29A+4,_smc_insB
		PL_PA	$E2FC+4,_smc_insA
		PL_PA	$E304+4,_smc_insB
		PL_PA	$E3A2+4,_smc_insA
		PL_PA	$E3AA+4,_smc_insB
		PL_PA	$E442+4,_smc_insA
		PL_PA	$E44A+4,_smc_insB
		PL_PA	$E58A+4,_smc_insA
		PL_PA	$E592+4,_smc_insB
		PL_PA	$E5A4+4,_smc_insA
		PL_PA	$E5AC+4,_smc_insB
		PL_PA	$E788+4,_smc_insA
		PL_PA	$E790+4,_smc_insB
		PL_PA	$EAA4+4,_smc_insA
		PL_PA	$EAAC+4,_smc_insB
	; RTS at $F8DE
		PL_P	$F8DE,smc_F8DE
		SMC_JSRW $F91C,2
		SMC_JSRW $F928,3
	; RTS at $10654 and $F9C0
		PL_P	$10654,smc_10654
		PL_P	$F9C0,smc_F9C0
		SMC_JSRW $FCB2,4
		SMC_JSRW $FCBA,5
		SMC_JSRW $FCDA,6
		SMC_JSRW $FCE2,7
	; shift counts: the four moves after each lea
		PL_PSS	$F4FE,smc_Sh1_10,8
		PL_PSS	$FBA8,smc_Sh1_10,8
		PL_PSS	$FDBA,smc_Sh1_10,8
		PL_PSS	$10076,smc_Sh1_10,8
		PL_PSS	$F49C,smc_Sh1_12,8
		PL_PSS	$FC5C,smc_Sh1_12,8
		PL_PSS	$FF4C,smc_Sh1_12,8
		PL_PSS	$10004,smc_Sh1_12,8
		PL_PSS	$F5A2,smc_Sh2_12,8
		PL_PSS	$101C6,smc_Sh2_12,8
		PL_PSS	$102BA,smc_Sh2_12,8
		PL_PSS	$103EE,smc_Sh2_12,8
		PL_PSS	$F61C,smc_Sh2_14,8
		PL_PSS	$1025A,smc_Sh2_14,8
		PL_PSS	$1031A,smc_Sh2_14,8
		PL_PSS	$10380,smc_Sh2_14,8
	; NOP/ASR at $ECA0
		PL_PS	$EC84,smc_ECA0
	; the bitmap scaler: selections and slots
		SMC_JSRW $19EBE,8
		SMC_JSRW $19EC4,9
		SMC_JSRW $19F02,10
		SMC_JSRW $19F08,11
		SMC_JSRW $19F8C,12
		SMC_JSRW $19F92,13
		SMC_JSRW $19FC2,14
		SMC_JSRW $19FC8,15
		SMC_JSRW $1A23E,16
		SMC_JSRW $1A244,17
		SMC_JSRW $1A264,18
		SMC_JSRW $1A26A,19
		PL_PS	$19CAE,scale_Copy
		PL_PS	$1A074,scale_Copy
		PL_PS	$1A09E,scale_SetEntry
		PL_END

		CNOP	0,4
_smc_vecA	dc.l	0
_smc_vecB	dc.l	0
_smc_insA	dc.l	0
_smc_insB	dc.l	0
_smc_pF8DE	dc.l	0
_smc_p10654	dc.l	0
_smc_pF9C0	dc.l	0
_scale_ptrs	ds.l	16		; the table's entries as pairs
_scale_slot1	dc.l	0		; each slot's pair
_scale_slot2	dc.l	0
_scale_slot3	dc.l	0
_scale_slot4	dc.l	0
_scale_slot5	dc.l	0
_scale_slot6	dc.l	0
_smc_state	dc.b	0		; 0 unknown, -1 no caches, 1 patched
		even
