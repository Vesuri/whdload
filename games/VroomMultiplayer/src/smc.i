;---------------------------------------------------------------------------
; Vroom Multiplayer's self-modifying code, made safe for CPU caches
; (docs/internals.md, "Self-modifying code"): games/Vroom's src/smc.i at the
; Multiplayer's (v1) addresses. The including source defines the init code's
; two writers SMC_VBLW1/SMC_VBLW2.
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
SMC_HI		= $1C632		; (Fix_Decrunched in src/fixes.i)

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
smc_Init	move.l	$B028,_smc_vecA-_smc_state(a2)
		move.l	$B02E,_smc_vecB-_smc_state(a2)
		move.l	$10618,_smc_insA-_smc_state(a2)
		move.l	$10642,_smc_insB-_smc_state(a2)
		lea	smc_1056A_run(pc),a0
		move.l	a0,_smc_p1056A-_smc_state(a2)
		lea	smc_11322_run(pc),a0
		move.l	a0,_smc_p11322-_smc_state(a2)
		lea	smc_1064C_run(pc),a0
		move.l	a0,_smc_p1064C-_smc_state(a2)
		lea	scale_P00(pc),a0	; nop, nop: what the slots hold
		lea	_scale_ptrs(pc),a1
		moveq	#16+6-1,d0
.nop		move.l	a0,(a1)+
		dbf	d0,.nop
		rts

	MACHINE	MC68020

;--- the VBL routine: jsr <vector> at $B026 and $B02C, the vectors written by
;    seven instructions (patched to write _smc_vecA/_smc_vecB instead)
smc_VblA	jmp	([_smc_vecA,pc])
smc_VblB	jmp	([_smc_vecB,pc])

;--- the renderer's line routine: at $10618 and $10642 either
;    "move.w $10788(pc),(a0)+" or "bsr.w $1078A" (whose routine starts with that
;    move), copied from $ED6A-$ED79 by 20 instructions (patched to write
;    _smc_insA/_smc_insB instead); the sites call these through trampolines
smc_DispA	cmpi.w	#$6100,_smc_insA(pc)	; bsr?
		beq.b	smc_Bsr
smc_Move	move.w	([_blk_10788,pc]),(a0)+
		rts
smc_DispB	cmpi.w	#$6100,_smc_insB(pc)
		bne.b	smc_Move
smc_Bsr		jmp	([_blk_1078A,pc])

;--- RTS at $1056A (subq.w #1,d4 / ble.w $1062C), set at $105A8 and cleared at
;    $105B4 around the renderer's recursive call
smc_1056A	jmp	([_smc_p1056A,pc])
smc_1056A_run	subq.w	#1,d4
		ble.b	.le
		jmp	([_blk_10570,pc])
.le		jmp	([_blk_1062C,pc])

;--- RTS at $11322 (move.w $1134C(pc),d7 / cmp.w (a3),d7) and $1064C
;    (move.b #-1,9(a0)), set at $10966/$1096E and cleared at $1098E/$10996
smc_11322	jmp	([_smc_p11322,pc])
smc_11322_run	move.w	([_blk_1134C,pc]),d7
		cmp.w	(a3),d7
		jmp	([_blk_11328,pc])
smc_1064C	jmp	([_smc_p1064C,pc])
smc_1064C_run	move.b	#-1,9(a0)
		jmp	([_blk_10652,pc])

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
smc_Set1056A	SMC_SET	_smc_p1056A,smc_Rts
smc_Clr1056A	SMC_SET	_smc_p1056A,smc_1056A_run
smc_Set11322	SMC_SET	_smc_p11322,smc_Rts
smc_Set1064C	SMC_SET	_smc_p1064C,smc_Rts
smc_Clr11322	SMC_SET	_smc_p11322,smc_11322_run
smc_Clr1064C	SMC_SET	_smc_p1064C,smc_1064C_run
smc_Store	move.l	a0,(a1)
		movem.l	(a7)+,a0/a1
		andi.b	#$10,ccr
		rts

;--- shift counts and masks: at the four routines $102F8, $1036A, $1044C and
;    $104BC "andi.w #mask" and three shifts, copied from a table by
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
;--- NOP or "asr.w #n,d4" at $FA2E, copied from $FA32 at $FA12
smc_FA2E	move.w	(a4,d4.w),-4(a4)
smc_Flush	move.w	ccr,-(a7)
		move.l	a2,-(a7)
		move.l	_resload(pc),a2
		jsr	resload_FlushCache(a2)
		move.l	(a7)+,a2
		move.w	(a7)+,ccr
		rts


;--- the bitmap scaler: "jsr $100.w"/"jsr $106.w" (the original slave's
;    move.l (a4,d0.w),(a5)/(a6)) store entry d0/4 of the table at $1B9A4 into
;    one of six 4-byte slots at $1C60C-$1C631 (Vroom has them inside the loop;
;    here the loop calls them, bsr.w, or branches to them, bra.w, and they
;    return with rts or bra.w), and $1B612 branches into a slot again. The
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

; the table's writers: two copies of 16 entries from $1BAA4 or $1BAE4
; (move.l (a3)+,(a4)+ / dbf d0) and one entry from $1B9A0
scale_Copy	move.l	(a3)+,(a4)+
		dbf	d0,scale_Copy
		bra.b	scale_Sync
scale_SetEntry	move.l	([_blk_1B9A0,pc]),(a0,d0.w)
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
		move.l	_blk_1B9A4(pc),a0
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
		dc.w	smc_Set1056A-_smc_tramps		; +12
		dc.w	smc_Clr1056A-_smc_tramps		; +18
		dc.w	smc_Set11322-_smc_tramps	; +24
		dc.w	smc_Set1064C-_smc_tramps		; +30
		dc.w	smc_Clr11322-_smc_tramps	; +36
		dc.w	smc_Clr1064C-_smc_tramps		; +42
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
		PL_PS	$B026,smc_VblA
		PL_PS	$B02C,smc_VblB
		PL_PA	SMC_VBLW1,_smc_vecB	; move.l #x,$B02E
		PL_PA	SMC_VBLW2,_smc_vecA	; move.l #x,$B028
		PL_PA	$9A92,_smc_vecB
		PL_PA	$9A9E,_smc_vecB
		PL_PA	$ADC2,_smc_vecA		; move.l (a0,d0.w),$B028
		PL_PA	$AE1E,_smc_vecA
		PL_PA	$AE88,_smc_vecA
	; the line routine: move.l $ED6A-$ED79(pc),$10618/$10642
		SMC_JSRW $10618,0
		SMC_JSRW $10642,1
		PL_PA	$EB72+4,_smc_insA
		PL_PA	$EB7A+4,_smc_insB
		PL_PA	$EBDC+4,_smc_insA
		PL_PA	$EBE4+4,_smc_insB
		PL_PA	$EC82+4,_smc_insA
		PL_PA	$EC8A+4,_smc_insB
		PL_PA	$ED22+4,_smc_insA
		PL_PA	$ED2A+4,_smc_insB
		PL_PA	$F082+4,_smc_insA
		PL_PA	$F08A+4,_smc_insB
		PL_PA	$F0A4+4,_smc_insA
		PL_PA	$F0AC+4,_smc_insB
		PL_PA	$F136+4,_smc_insA
		PL_PA	$F13E+4,_smc_insB
		PL_PA	$F232+4,_smc_insA
		PL_PA	$F23A+4,_smc_insB
		PL_PA	$F24C+4,_smc_insA
		PL_PA	$F254+4,_smc_insB
		PL_PA	$F85A+4,_smc_insA
		PL_PA	$F862+4,_smc_insB
	; RTS at $1056A
		PL_P	$1056A,smc_1056A
		SMC_JSRW $105A8,2
		SMC_JSRW $105B4,3
	; RTS at $11322 and $1064C
		PL_P	$11322,smc_11322
		PL_P	$1064C,smc_1064C
		SMC_JSRW $10966,4
		SMC_JSRW $1096E,5
		SMC_JSRW $1098E,6
		SMC_JSRW $10996,7
	; shift counts: the four moves after each lea
		PL_PSS	$10174,smc_Sh1_10,8
		PL_PSS	$1085C,smc_Sh1_10,8
		PL_PSS	$10A6E,smc_Sh1_10,8
		PL_PSS	$10D2A,smc_Sh1_10,8
		PL_PSS	$10112,smc_Sh1_12,8
		PL_PSS	$10910,smc_Sh1_12,8
		PL_PSS	$10C00,smc_Sh1_12,8
		PL_PSS	$10CB8,smc_Sh1_12,8
		PL_PSS	$1021E,smc_Sh2_12,8
		PL_PSS	$10E7A,smc_Sh2_12,8
		PL_PSS	$10F70,smc_Sh2_12,8
		PL_PSS	$110A4,smc_Sh2_12,8
		PL_PSS	$102A0,smc_Sh2_14,8
		PL_PSS	$10F10,smc_Sh2_14,8
		PL_PSS	$10FD0,smc_Sh2_14,8
		PL_PSS	$11036,smc_Sh2_14,8
	; NOP/ASR at $FA2E
		PL_PS	$FA12,smc_FA2E
	; the bitmap scaler: selections and slots
		SMC_JSRW $1B526,8
		SMC_JSRW $1C628,9
		SMC_JSRW $1B568,10
		SMC_JSRW $1C62E,11
		SMC_JSRW $1B5F0,12
		SMC_JSRW $1C60C,13
		SMC_JSRW $1B626,14
		SMC_JSRW $1C614,15
		SMC_JSRW $1B8A2,16
		SMC_JSRW $1C61C,17
		SMC_JSRW $1B8C8,18
		SMC_JSRW $1C622,19
		PL_PS	$1B316,scale_Copy
		PL_PS	$1B6D8,scale_Copy
		PL_PS	$1B702,scale_SetEntry
		PL_END

		CNOP	0,4
_smc_vecA	dc.l	0
_smc_vecB	dc.l	0
_smc_insA	dc.l	0
_smc_insB	dc.l	0
_smc_p1056A	dc.l	0
_smc_p11322	dc.l	0
_smc_p1064C	dc.l	0
_scale_ptrs	ds.l	16		; the table's entries as pairs
_scale_slot1	dc.l	0		; each slot's pair
_scale_slot2	dc.l	0
_scale_slot3	dc.l	0
_scale_slot4	dc.l	0
_scale_slot5	dc.l	0
_scale_slot6	dc.l	0
_smc_state	dc.b	0		; 0 unknown, -1 no caches, 1 patched
		even
