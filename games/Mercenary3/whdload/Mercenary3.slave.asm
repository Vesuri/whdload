;*---------------------------------------------------------------------------
;  :Program.	mercenary3.slave.asm
;  :Contents.	Slave for "Mercenary 3 - The Dion Crisis"
;  :Author.	Harry/Graham/Wepl
;  :History.	19.03.1998
;		29.07.04 merged Harry and Graham (ReSourced Slave) sources
;		performance version, from whdload/original/ (the shipped 1.2):
;		WHDLoad 17 header with options; with every option off the game
;		runs as with the shipped slave
;  :Requires.	whdload-package :)
;  :Copyright.	Freeware
;  :Language.	68000 Assembler
;  :Translator.	vasm
;  :To Do.
;---------------------------------------------------------------------------*

	INCLUDE	whdload.i
	INCLUDE	whdmacros.i

STACKSIZE	= $1000
HOTSIZE		= $1000
TABLESIZE	= $6104
TABLEMEM	= $7000		;ws_ExpMem requires whole 4 KB pages
RESTOREMEM	= $5000		;17,366 bytes, rounded to whole pages

;======================================================================

_base		SLAVE_HEADER			;ws_Security + ws_ID
		dc.w	17			;ws_Version
		dc.w	WHDLF_NoError|WHDLF_Disk|WHDLF_EmulTrap	;ws_flags
		dc.l	$80000			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	_boot-_base		;ws_GameLoader
		dc.w	0			;ws_CurrentDir
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$41			;ws_keyexit = Backspace
_expmem		dc.l	-(STACKSIZE+HOTSIZE+TABLEMEM+RESTOREMEM) ;optional workspace
		dc.w	_name-_base		;ws_name
		dc.w	_copy-_base		;ws_copy
		dc.w	_info-_base		;ws_info
		dc.w	0			;ws_kickname
		dc.l	0			;ws_kicksize
		dc.w	0			;ws_kickcrc
		dc.w	_config-_base		;ws_config

;============================================================================

_name		dc.b	"Mercenary 3 - The Dion Crisis",0
_copy		dc.b	"1991 Novagen",0
_info		dc.b	"adapted by Harry/Graham/Wepl",10
		dc.b	"Version 1.2 (29.07.2004)",10
		dc.b	"performance version in development"
	IFD VERIFY
		dc.b	" (VERIFY)"
	ENDC
		dc.b	0
_config		dc.b	"C1:X:Enable display DMA once, copy whole palette:0;"
		dc.b	"C1:X:64-bit bitplane fetch on AGA (FMODE 3):1;"
		dc.b	"C1:X:Supervisor stack in expansion memory:2;"
		dc.b	"C1:X:Native walking logic rate:3;"
		dc.b	"C1:X:Walking presentation frames (includes logic gate):4;"
		dc.b	"C1:X:Hot code in fast RAM (68020+):5;"
		dc.b	"C1:X:Read-only lookup tables in fast RAM (68020+):6;"
		dc.b	"C1:X:Longword horizontal span fills:7;"
		dc.b	"C1:X:Bulk presentation restore:8;"
		dc.b	0
Mercenary3sav	dc.b	'Mercenary3.save',0,0
	EVEN

;======================================================================
_boot		;	A0 = resident loader
;======================================================================

	lea	($1800).w,sp
	move.l	sp,usp
	lea	(_resload,pc),a1
	move.l	a0,(a1)
	movea.l	a0,a2
	lea	(_tags,pc),a0
	jsr	(resload_Control,a2)

	lea	($4000).w,a0
	moveq	#0,d0
	move.l	#$7D80,d1
	bsr.w	_diskload

	lea	(_int68,pc),a0
	move.l	a0,($68).w
	move.b	#$7F,(_ciaa+ciaicr).l
	tst.b	(_ciaa+ciaicr).l
	move.w	#(INTF_PORTS|INTF_INTEN|INTF_SETCLR),(_custom+intena).l
	move.b	#(CIAICRF_SP|CIAICRF_SETCLR),(_ciaa+ciaicr).l

	lea	($4080).w,a0
	lea	($48000).l,a1
	move.w	#$F9F,d0
lbC00010C	move.w	(a0)+,(a1)+
	move.w	(a0)+,($1FFE,a1)
	move.w	(a0)+,($3FFE,a1)
	move.w	(a0)+,($5FFE,a1)
	dbra	d0,lbC00010C
	moveq	#15,d0
	lea	($4004).w,a0
	lea	(_custom+color).l,a1
lbC00012A	move.w	(a0)+,d1
	add.w	d1,d1
	move.w	d1,(a1)+
	dbra	d0,lbC00012A
	lea	(_custom).l,a6
	lea	(_clist,pc),a0
	lea	($800).w,a1
	move.l	a1,(cop1lc,a6)
lbC000146	move.l	(a0)+,(a1)+
	bpl.b	lbC000146
	clr.w	(copjmp1,a6)
	bsr.w	_waitvb
	move.w	#(DMAF_COPPER|DMAF_RASTER|DMAF_MASTER|DMAF_SETCLR),(dmacon,a6)

	moveq	#50,d0
	jsr	(resload_Delay,a2)

	bsr.w	_waitvb
	move.w	#$7FFF,(dmacon,a6)

	lea	($100).w,a0
	move.w	#$FFDF,d0
lbC00018C	clr.l	(a0)+
	clr.l	(a0)+
	dbra	d0,lbC00018C

	lea	($5350).w,a0
	move.l	#$9000,d0
	move.l	#$6D7B0,d1
	bsr.w	_diskload

	lea	($56300).l,a1
	lea	(8).w,a0
	move.l	a0,($32,a1)
	addq.l	#1,a0
	move.l	a0,($2A,a1)
	move.l	a0,($3E,a1)
	move.l	a0,($4C,a1)

	move.w	(_attn,pc),d0
	btst	#AFB_68040,d0
	beq.b	lbC0002AA
	lea	($C0).w,a0
	move.l	a0,($458CC).l
	addq.l	#4,a0
	move.l	a0,($458D6).l
	addq.l	#4,a0
	move.l	a0,($4F87C).l
	addq.l	#4,a0
	move.l	a0,($4F882).l
	move.l	#$207800C0,d0
	move.w	#$4E90,d1
	move.l	d0,($459B8).l
	move.w	d1,($459BC).l
	addq.w	#4,d0
	move.l	d0,($459C4).l
	move.w	d1,($459C8).l
	addq.w	#4,d0
	move.l	d0,($4F9C0).l
	move.w	d1,($4F9C4).l
	addq.w	#4,d0
	move.l	d0,($4FA08).l
	move.w	d1,($4FA0C).l
lbC0002AA

	lea	$5a1b0,a0
	cmpi.w	#$4eb9,(a0)		;copy protected version?
	bne.b	.notprotected
	move.w	#$7000,d0
	move.w	d0,(a0)+
	move.w	d0,(a0)+
	move.w	d0,(a0)+
.notprotected

	lea	(_pl,pc),a0
	lea	$50000,a1
	jsr	(resload_Patch,a2)

; Replace the operand of the main-loop head's jsr (Disk.1 $5DF92) only
; when enabled. SetCACR below makes the patched instruction visible.
	btst	#3,(_custom1+3,pc)
	beq.b	.nogate
	lea	(_logicgate,pc),a0
	move.l	a0,($5a2e4).l
.nogate
	btst	#4,(_custom1+3,pc)
	beq.b	.nopresent
; Without a restore buffer, retain native-rate logic but omit redraws.
	lea	(_logicgate,pc),a0
	move.l	a0,($5a2e4).l
	move.l	(_expmem,pc),d0
	beq.b	.nopresent
	addi.l	#STACKSIZE+HOTSIZE+TABLEMEM,d0
	lea	(_restore_buffer,pc),a0
	move.l	d0,(a0)
	lea	(_presentgate,pc),a0
	move.l	a0,($5a2e4).l
; Disk.1 $5E4DE: count publications separately from logic passes. Replace
; addq.w #1,$7180.w and move.w $52952.l,d1 (ten bytes).
	move.w	#$4eb9,($5a82e).l
	lea	(_pubcount,pc),a0
	move.l	a0,($5a830).l
	move.l	#$4e714e71,($5a834).l
.nopresent
	bsr.w	_hotcode
	bsr.w	_hotdata
	bsr.w	_patchspans
	IFD VERIFY
	bsr.w	_bypass
	ENDC
	moveq	#CACRF_EnableI,d0
	move.l	d0,d1
	movea.l	(_resload,pc),a0
	jsr	(resload_SetCACR,a0)

; Custom1 bit 1: on AGA (Lisa's ID in LISAID), fetch the bitplanes 64 bits wide. The
; game's two known in-game copper lists (Disk.1 $56780, $567CC) set the fetch window;
; their 320-pixel window ends at $b8 with 64-bit fetches. The buffers and
; planes are 8-byte aligned and the rows 40 bytes, without modulos.
	btst	#1,(_custom1+3,pc)
	beq.b	.nofmode
	move.w	(_custom+$7c).l,d0	;LISAID
	cmp.b	#$f8,d0
	bne.b	.nofmode
	move.w	#$b8,($52aee).l		;DDFSTOP
	move.w	#$b8,($52b32).l
	move.w	#3,(_custom+$1fc).l	;FMODE
.nofmode
; Custom1 bit 2: the game sets its supervisor stack at the top of chip RAM with
; lea $7fffa,a0 / unlk a0 in three places (Disk.1 $5DE66, $5DE88, $5DEEA) and uses less
; than a page of it. Move it into the expansion memory, which is fast RAM when fitted.
	btst	#2,(_custom1+3,pc)
	beq.b	.nostack
	move.l	(_expmem,pc),d0
	beq.b	.nostack			;no expansion block: keep the chip stack
	add.l	#STACKSIZE-6,d0
	move.l	d0,($5a1b8).l
	move.l	d0,($5a1da).l
	move.l	d0,($5a23c).l
.nostack
	move.w	#$2700,sr
	jmp	($4B100).l

; M1: copy the numeric helpers (Disk.1 $4EDE4..$4EF92) and the
; projection kernels ($5B030..$5B918). All relative branches stay inside
; their copied block; data references are absolute/register based. The
; self-modifying drawing sites stay in chip RAM, under their existing patches.
; Copy before installing entry jumps so internal branches retain original code.
_hotcode
	btst	#5,(_custom1+3,pc)
	beq.w	.done
	move.w	(_attn,pc),d0
	btst	#AFB_68020,d0
	beq.w	.done
	move.l	(_expmem,pc),d0
; ExpMem may be chip or slow RAM. Accept allocated Zorro-II fast RAM or
; 32-bit expansion RAM; reject chip and the $C00000 slow-memory window.
	cmpi.l	#$200000,d0
	blo.w	.done
	cmpi.l	#$a00000,d0
	blo.b	.fast
	cmpi.l	#$1000000,d0
	blo.w	.done
.fast	addi.l	#STACKSIZE,d0
	movea.l	d0,a1
	movea.l	d0,a3
	lea	($4b134).l,a0
	move.w	#($4b2e2-$4b134)/2-1,d0
.copy1	move.w	(a0)+,(a1)+
	dbra	d0,.copy1
	lea	($57380).l,a0
	move.w	#($57c68-$57380)/2-1,d0
.copy2	move.w	(a0)+,(a1)+
	dbra	d0,.copy2
	lea	(_hotentries,pc),a0
.next	move.l	(a0)+,d0
	beq.b	.done
	movea.l	d0,a1
	moveq	#0,d0
	move.w	(a0)+,d0
	add.l	a3,d0
	move.w	#$4ef9,(a1)+
	move.l	d0,(a1)
	bra.b	.next
.done	rts

; Disk.1 entries $4EDE4, $4EE76, $4EE88, $5B030, $5B038,
; $5B050, $5B5C4. The long-input helper at $4EE84 keeps its first
; two instructions in chip and falls through the $4EE88 entry jump.
_hotentries
	dc.l	$4b134
	dc.w	0
	dc.l	$4b1c6
	dc.w	$4b1c6-$4b134
	dc.l	$4b1d8
	dc.w	$4b1d8-$4b134
	dc.l	$57380
	dc.w	$4b2e2-$4b134
	dc.l	$57388
	dc.w	$4b2e2-$4b134+$57388-$57380
	dc.l	$573a0
	dc.w	$4b2e2-$4b134+$573a0-$57380
	dc.l	$57914
	dc.w	$4b2e2-$4b134+$57914-$57380
	dc.l	0

; M2: the read-only lookup region at chip $60000..$66103 supplies
; the renderer's numeric and trigonometric tables. Keep the original copy
; for unpatched users; redirect the explicit table-base loads only.
_hotdata
	btst	#6,(_custom1+3,pc)
	beq.w	.done
	move.w	(_attn,pc),d0
	btst	#AFB_68020,d0
	beq.w	.done
	move.l	(_expmem,pc),d0
	cmpi.l	#$200000,d0
	blo.w	.done
	cmpi.l	#$a00000,d0
	blo.b	.fast
	cmpi.l	#$1000000,d0
	blo.w	.done
.fast	addi.l	#STACKSIZE+HOTSIZE,d0
	movea.l	d0,a1
	move.l	d0,d1
	lea	($60000).l,a0
	move.w	#TABLESIZE/4-1,d0
.copy	move.l	(a0)+,(a1)+
	dbra	d0,.copy
	lea	(_table60000,pc),a0
	bsr.b	.patch
	addi.l	#$4000,d1
	lea	(_table64000,pc),a0
.patch	move.l	(a0)+,d0
	beq.b	.done
	movea.l	d0,a1
	move.l	d1,(a1)
	bra.b	.patch
.done	rts

; Operands of table-base movea.l/lea instructions. To map an operand
; to Disk.1, add $3CB0. None lies in M1's copied code blocks.
_table60000
	dc.l	$45194,$45608,$45814,$458ae,$4c200
	dc.l	$4c6b2,$4c990,$4e4ca,$4e59e,$4f7c6
	dc.l	$4fb7e,$4fbf0,$506ba,$50bd4,$51a5a
	dc.l	$536f8,$539f8,$53ae0,$53b20,$54020
	dc.l	$54096,$54358,$54716,$54b76,$55714
	dc.l	$56654,$5668e,$56c76,$5709a,$57122
	dc.l	$571b0,$5727a,$57318,$583ee,$58c50
	dc.l	$5a8ec,$5b796,$5c140
	dc.l	0
_table64000
	dc.l	$4518e,$4519a,$45602,$4580e,$458a8
	dc.l	$4c1fa,$4c6ac,$4c6b8,$4c98a,$4e4c4
	dc.l	$4e598,$4f7c0,$4fb78,$4fbea,$506b4
	dc.l	$50bce,$51a54,$536f2,$539f2,$53ada
	dc.l	$53b1a,$5401a,$54090,$54352,$54710
	dc.l	$54b70,$5570e,$56688,$56c7c,$57094
	dc.l	$5711c,$571aa,$57274,$57312,$583e8
	dc.l	$58c4a,$5a8e6,$5b790,$5c13a
	dc.l	0

; R1: full-word interiors of the sixteen horizontal colour spans.
; Disk.1 $4978C + colour*$B6: replace the count setup with a call,
; then branch over the old word loop to its unchanged right-edge mask.
_patchspans
	btst	#7,(_custom1+3,pc)
	beq.b	.done
	lea	(_span000,pc),a0
	move.w	(_attn,pc),d0
	btst	#AFB_68020,d0
	beq.b	.install
; The 020 chip-only cell loses to call/alignment overhead: keep it native.
	move.l	(_expmem,pc),d0
	cmpi.l	#$200000,d0
	blo.b	.done
	cmpi.l	#$a00000,d0
	blo.b	.fast
	cmpi.l	#$1000000,d0
	blo.b	.done
.fast	lea	(_span020,pc),a0
.install
	lea	(_spans,pc),a2
	lea	($45adc).l,a1
	moveq	#15,d1
.next	move.w	(a0)+,d0
	ext.l	d0
	add.l	a2,d0
	move.w	#$4eb9,(a1)
	move.l	d0,(2,a1)
	move.w	#$6010,(6,a1)
	adda.w	#$b6,a1
	dbra	d1,.next
.done	rts

	IFD VERIFY
; Custom2 (VERIFY only): skip drawing routines to find each one's share of the frame
; time on CPUs without an instruction trace. Bits 0..4: the 3D drawing (Disk.1 $577BE),
; the back-buffer clear ($5E840), $5410E, $5AFAA and $593A6 return at once.
_bypass	lea	(_bypassed,pc),a0
	moveq	#0,d1
.next	move.l	(a0)+,d0
	beq.b	.done
	btst	d1,(_custom2+3,pc)
	beq.b	.skip
	movea.l	d0,a1
	move.w	#$4e75,(a1)
.skip	addq.w	#1,d1
	bra.b	.next
.done	rts
_bypassed	dc.l	$53b0e,$5ab90,$5045e,$572fa,$556f6,0
	ENDC

; d5=0, d6=-1 from native setup; d2 is the remaining pixel width.
; Retain native masks at both ends and write exactly its complete words.
; 000: pairs at either even alignment. 020+: align to a longword first;
; the small paired loop fits the instruction cache without unrolling.
_SPAN MACRO
	move.w	d2,d7
	lsr.w	#4,d7
	beq.b	.done
	IFNE \5
	move.w	a0,d5
	andi.w	#2,d5
	beq.b	.aligned
	moveq	#0,d5
	move.w	\1,(a0)+
	move.w	\2,(7998,a0)
	move.w	\3,(15998,a0)
	move.w	\4,(23998,a0)
	subq.w	#1,d7
.aligned
	moveq	#0,d5
	subq.w	#2,d7
	bmi.b	.tail
.loop	move.l	\1,(a0)+
	move.l	\2,(7996,a0)
	move.l	\3,(15996,a0)
	move.l	\4,(23996,a0)
	subq.w	#2,d7
	bpl.b	.loop
.tail	addq.w	#1,d7
	bmi.b	.done
	move.w	\1,(a0)+
	move.w	\2,(7998,a0)
	move.w	\3,(15998,a0)
	move.w	\4,(23998,a0)
	ELSE
	lsr.w	#1,d7
	bcc.b	.pairs
	move.w	\1,(a0)+
	move.w	\2,(7998,a0)
	move.w	\3,(15998,a0)
	move.w	\4,(23998,a0)
.pairs	subq.w	#1,d7
	bmi.b	.done
.loop	move.l	\1,(a0)+
	move.l	\2,(7996,a0)
	move.l	\3,(15996,a0)
	move.l	\4,(23996,a0)
	dbra	d7,.loop
	ENDC
.done	move.w	#-1,d7
	rts
	ENDM

_span000
	dc.w	_span0_000-_spans,_span1_000-_spans,_span2_000-_spans,_span3_000-_spans,_span4_000-_spans,_span5_000-_spans,_span6_000-_spans,_span7_000-_spans,_span8_000-_spans,_span9_000-_spans,_span10_000-_spans,_span11_000-_spans,_span12_000-_spans,_span13_000-_spans,_span14_000-_spans,_span15_000-_spans
_span020
	dc.w	_span0_020-_spans,_span1_020-_spans,_span2_020-_spans,_span3_020-_spans,_span4_020-_spans,_span5_020-_spans,_span6_020-_spans,_span7_020-_spans,_span8_020-_spans,_span9_020-_spans,_span10_020-_spans,_span11_020-_spans,_span12_020-_spans,_span13_020-_spans,_span14_020-_spans,_span15_020-_spans
_spans
_span0_000
	_SPAN	d5,d5,d5,d5,0
_span1_000
	_SPAN	d6,d5,d5,d5,0
_span2_000
	_SPAN	d5,d6,d5,d5,0
_span3_000
	_SPAN	d6,d6,d5,d5,0
_span4_000
	_SPAN	d5,d5,d6,d5,0
_span5_000
	_SPAN	d6,d5,d6,d5,0
_span6_000
	_SPAN	d5,d6,d6,d5,0
_span7_000
	_SPAN	d6,d6,d6,d5,0
_span8_000
	_SPAN	d5,d5,d5,d6,0
_span9_000
	_SPAN	d6,d5,d5,d6,0
_span10_000
	_SPAN	d5,d6,d5,d6,0
_span11_000
	_SPAN	d6,d6,d5,d6,0
_span12_000
	_SPAN	d5,d5,d6,d6,0
_span13_000
	_SPAN	d6,d5,d6,d6,0
_span14_000
	_SPAN	d5,d6,d6,d6,0
_span15_000
	_SPAN	d6,d6,d6,d6,0
_span0_020
	_SPAN	d5,d5,d5,d5,1
_span1_020
	_SPAN	d6,d5,d5,d5,1
_span2_020
	_SPAN	d5,d6,d5,d5,1
_span3_020
	_SPAN	d6,d6,d5,d5,1
_span4_020
	_SPAN	d5,d5,d6,d5,1
_span5_020
	_SPAN	d6,d5,d6,d5,1
_span6_020
	_SPAN	d5,d6,d6,d5,1
_span7_020
	_SPAN	d6,d6,d6,d5,1
_span8_020
	_SPAN	d5,d5,d5,d6,1
_span9_020
	_SPAN	d6,d5,d5,d6,1
_span10_020
	_SPAN	d5,d6,d5,d6,1
_span11_020
	_SPAN	d6,d6,d5,d6,1
_span12_020
	_SPAN	d5,d5,d6,d6,1
_span13_020
	_SPAN	d6,d5,d6,d6,1
_span14_020
	_SPAN	d5,d6,d6,d6,1
_span15_020
	_SPAN	d6,d6,d6,d6,1

_pl	PL_START
	PL_W	$716,DMAF_SETCLR|DMAF_MASTER	;game enables master DMA only
	PL_S	$1e30,8			;rom access
	PL_P	$205a,_subd0		;empty dbf loop
	PL_P	$29a6,_patch_aud1
	PL_P	$29bc,_patch_aud1
	PL_P	$29c6,_patch_aud1
	PL_P	$2ac0,_patch_vertb
	PL_P	$2c9e,_patch_vertb
	PL_P	$5e8a,_loadgame
	PL_P	$5f26,_savegame
	PL_P	$a858,_dmaon		;enable copper and bitplanes
	PL_END

; Walking passes start at least four VERTBs apart. Publication owns its own
; timestamp; do not use it as the pass timestamp or count the wait twice.
; The first pass (also after another mode) keeps the native elapsed count.
_logicgate
	move.w	sr,-(sp)
	movem.l	d0/a0,-(sp)
	lea	(_logicstamp,pc),a0
	cmpi.w	#1,($7122).w
	bne.b	.othermode
	tst.w	(2,a0)
	beq.b	.first
.check	move.w	($529f4).l,d0
	sub.w	(a0),d0			;word subtraction handles VERTB wrap
	cmpi.w	#4,d0
	bhs.b	.ready
	move.w	($529f4).l,d0
.wait	cmp.w	($529f4).l,d0
	beq.b	.wait
	bra.b	.check
.ready	move.w	d0,($52954).l		;original code still clamps to 4..8
	add.w	d0,(a0)			;stamp of the accepted pass
	bra.b	.done
.first	move.w	($529f4).l,(a0)
	move.w	#1,(2,a0)
	bra.b	.done
.othermode
	clr.w	(2,a0)
.done	movem.l	(sp)+,d0/a0
	move.w	(sp)+,ccr
	jmp	($5a298).l		;original callee, Disk.1 $5DF48

_logicstamp	dc.w	0,0			;last accepted VERTB, valid walking pass

; P1 uses its own gate so disabled options retain L1's measured path.
_presentgate
	move.w	sr,-(sp)
	movem.l	d0-d7/a0-a6,-(sp)
	lea	(_pstate,pc),a5
	cmpi.w	#1,($7122).w
	bne.w	.other
	cmpi.w	#1,($7142).w
	bne.w	.other
	tst.w	(2,a5)
	beq.b	.first
.check	move.w	($529f4).l,d0
	sub.w	(a5),d0
	cmpi.w	#4,d0
	bhs.b	.ready
; With one field left, only redraw if the last presentation fit in one field.
; Two spare fields can amortise a redraw even when it finishes a field late.
	cmpi.w	#3,d0
	bne.b	.screen
	cmpi.w	#1,(6,a5)
	bhi.b	.waitfield
.screen	tst.w	($71cc).w		; special screens keep their native path
	bmi.b	.render
.waitfield
	move.w	($529f4).l,d0
.wait	cmp.w	($529f4).l,d0
	beq.b	.wait
	bra.b	.check
.render	move.w	($529f4).l,-(sp)
	bsr.w	_present
	lea	(_pstate,pc),a5
	move.w	($529f4).l,d0
	sub.w	(sp)+,d0
	move.w	d0,(6,a5)
	bra.b	.check
.first	move.w	($52954).l,d0
	bra.b	.accept
.ready	move.w	d0,($52954).l
.accept
	move.w	($529f4).l,(a5)
	move.w	#1,(2,a5)
	cmpi.w	#4,d0
	bge.b	.minok
	moveq	#4,d0
.minok	cmpi.w	#8,d0
	ble.b	.maxok
	moveq	#8,d0
.maxok	move.w	d0,(4,a5)
	lea	($7142).w,a0
	lea	(_previous,pc),a1
	movem.l	(a0),d0-d7
	movem.l	d0-d7,(a1)
	bra.b	.done
.other	clr.w	(2,a5)
.done	movem.l	(sp)+,d0-d7/a0-a6
	move.w	(sp)+,ccr
	jmp	($5a298).l

; The game counter remains logic-only. Publication measurement is VERIFY-only.
	IFD VERIFY
	dc.b	'M3PUB001'
_presentcount	dc.w	0
	ENDC
_inpresent	dc.w	0
_pubcount
	move.l	a0,-(sp)
	lea	(_inpresent,pc),a0
	IFD VERIFY
	addq.w	#1,(-2,a0)
	ENDC
	tst.w	(a0)
	bne.b	.presentation
	addq.w	#1,($7180).w
.presentation
	move.l	(sp)+,a0
	move.w	($52952).l,d1
	rts

_pstate	dc.w	0,0,4,2
_previous	ds.b	32

_present
	move.w	d0,-(sp)
	IFD VERIFY
; Host-side SHA-256 and address differences, at these VERIFY-only markers.
	bsr.w	_verify_before
	ENDC
	bsr.w	_savepresent
	move.w	(sp)+,d6
	lea	(_inpresent,pc),a0
	move.w	#1,(a0)
; No extrapolation on a collision rollback or a special screen.
	tst.w	($70e2).w
	bne.w	.draw
	tst.w	($6f56).w
	bmi.w	.draw
	tst.w	($71cc).w
	bpl.w	.draw
	lea	(_previous,pc),a0
	lea	($7142).w,a1
	move.w	(_pstate+4,pc),d7
; Reject discontinuities before staging any position. 28-bit X/Z wrap.
	moveq	#2,d5
	moveq	#4,d4
.validate
	move.l	(a1,d4.w),d0
	sub.l	(a0,d4.w),d0
	asl.l	#4,d0
	asr.l	#4,d0
	cmpi.l	#1024,d0
	bgt.w	.draw
	cmpi.l	#-1024,d0
	blt.w	.draw
	addq.w	#4,d4
	dbra	d5,.validate
	moveq	#2,d5
	moveq	#4,d4
.position
	move.l	(a1,d4.w),d0
	sub.l	(a0,d4.w),d0
	muls.w	d6,d0
	divs.w	d7,d0
	ext.l	d0
	add.l	d0,(a1,d4.w)
	addq.w	#4,d4
	dbra	d5,.position
	moveq	#2,d5
.angle	move.w	(a1,d4.w),d0
	sub.w	(a0,d4.w),d0
	addi.w	#$200,d0
	andi.w	#$3ff,d0
	subi.w	#$200,d0
	muls.w	d6,d0
	divs.w	d7,d0
	add.w	d0,(a1,d4.w)
	andi.w	#$3ff,(a1,d4.w)
	addq.w	#2,d4
	dbra	d5,.angle
.draw
	jsr	($59b94).l		; camera, Disk.1 $5D844
; Disk.1 $5E0BA is inline, not a callable routine: derive sky heading.
	move.w	($70b4).w,d0
	movea.l	($713a).w,a1
	add.w	($575a,a1),d0
	andi.w	#$3ff,d0
	move.w	d0,($42c6c).l
	jsr	($59da0).l		; Disk.1 $5DA50
	jsr	($56c6e).l		; Disk.1 $5A91E
	jsr	($5a7a8).l		; publish, Disk.1 $5E458
	jsr	($5ab90).l		; clear, Disk.1 $5E840
	jsr	($42d14).l		; Disk.1 $469C4
	jsr	($42d18).l		; Disk.1 $469C8
; Palette setup from Disk.1 $5E132, using committed logic's colours.
	movea.l	($72b4).w,a0
	move.w	($7324).w,($10,a0)
	move.w	($70b0).w,d0
	tst.w	($6f56).w
	beq.b	.palette
	move.w	($7326).w,d0
.palette
	move.w	d0,($20,a0)
	move.w	($7186).w,($1c,a0)
	move.w	#$caa,($1e,a0)
	move.w	#$88a,($1a,a0)
	jsr	($5045e).l		; Disk.1 $5410E
	jsr	($539ae).l		; Disk.1 $5765E, scene setup
	jsr	($556f6).l		; Disk.1 $593A6
	jsr	($572fa).l		; Disk.1 $5AFAA
	jsr	($53b0e).l		; Disk.1 $577BE
	bsr.w	_restorepresent
	IFD VERIFY
	bsr.w	_poisonpresent
	ENDC
	lea	(_inpresent,pc),a0
	clr.w	(a0)
	IFD VERIFY
	bsr.w	_verify_after
	ENDC
	rts

_savepresent
	lea	(_restore_ranges,pc),a2
	movea.l	(_restore_buffer,pc),a1
.next	move.l	(a2)+,d0
	beq.b	.done
	movea.l	d0,a0
	move.w	(a2)+,d0
	btst	#0,(_custom1+2,pc)
	beq.b	.words
	bsr.w	_copylongs
	bra.b	.next
.words	move.w	(a0)+,(a1)+
	dbra	d0,.words
	bra.b	.next
.done	rts
_restorepresent
	lea	(_restore_ranges,pc),a2
	movea.l	(_restore_buffer,pc),a0
.next	move.l	(a2)+,d0
	beq.b	.done
	movea.l	d0,a1
	move.w	(a2)+,d0
	btst	#0,(_custom1+2,pc)
	beq.b	.words
	bsr.w	_copylongs
	bra.b	.next
.words	move.w	(a0)+,(a1)+
	dbra	d0,.words
	bra.b	.next
.done	rts

; Range lengths are words minus one. Move 32 bytes per loop, then pairs
; and an odd final word. All registers used here are saved by the gate.
_copylongs
	addq.w	#1,d0
	move.w	d0,d1
	lsr.w	#4,d0
	beq.b	.pairs
	subq.w	#1,d0
.bulk	movem.l	(a0)+,d2-d7/a3-a4
	movem.l	d2-d7/a3-a4,(a1)
	lea	(32,a1),a1
	dbra	d0,.bulk
.pairs	move.w	d1,d0
	andi.w	#15,d0
	lsr.w	#1,d0
	beq.b	.tail
	subq.w	#1,d0
.loop	move.l	(a0)+,(a1)+
	dbra	d0,.loop
.tail	btst	#0,d1
	beq.b	.done
	move.w	(a0)+,(a1)+
.done	rts

	IFD VERIFY
; Custom2 bit 6 enables a matched-cost scratch test; bit 5 complements every
; scratch word. With bit 5 clear, read/write the same words at the same cost.
_poisonpresent
	btst	#6,(_custom2+3,pc)
	beq.b	.done
	btst	#5,(_custom2+3,pc)
	sne	d1
	ext.w	d1
	move.l	(_poison_start,pc),d0
	bne.b	.start
	move.l	#$340,d0
.start	movea.l	d0,a0
	move.l	(_poison_end,pc),d0
	bne.b	.end
	move.l	#$4000,d0
.end
	sub.l	a0,d0
	lsr.l	#1,d0
	subq.w	#1,d0
.loop	move.w	(a0),d2
	eor.w	d1,d2
	move.w	d2,(a0)+
	dbra	d0,.loop
.done	rts
	ENDC

	IFD VERIFY
_verify_before
	nop
	rts
	dc.b	'M3BEFORE'
_verify_after
	nop
	rts
	dc.b	'M3AFTER!'
	ENDC

; Chip data ranges from the existing write audit. No live interrupt state,
; copper lists, display-buffer pointers or bitmaps are rolled back.
_restore_ranges
	dc.l	$c0
	dc.w	$7
	dc.l	$340
	dc.w	$1e5f
	dc.l	$4af0
	dc.w	$21
	dc.l	$5330
	dc.w	$0
	dc.l	$6f32
	dc.w	$0
	dc.l	$700e
	dc.w	$5
	dc.l	$704a
	dc.w	$3
	dc.l	$7084
	dc.w	$3
	dc.l	$70c2
	dc.w	$7
	dc.l	$7122
	dc.w	$2f
	dc.l	$719e
	dc.w	$0
	dc.l	$71ae
	dc.w	$1d
	dc.l	$7220
	dc.w	$5
	dc.l	$727c
	dc.w	$0
	dc.l	$aa6e
	dc.w	$27b
	dc.l	$b31e
	dc.w	$0
	dc.l	$b364
	dc.w	$0
	dc.l	$354e2
	dc.w	$8
	dc.l	$42c04
	dc.w	$38
	dc.l	$459ba
	dc.w	$1
	dc.l	$459c6
	dc.w	$1
	dc.l	$4f700
	dc.w	$a
	dc.l	$4f9bc
	dc.w	$0
	dc.l	$4f9c2
	dc.w	$1
	dc.l	$4fa0a
	dc.w	$1
	dc.l	$52952
	dc.w	$1
	dc.l	$53ad4
	dc.w	$1
	dc.l	$53d36
	dc.w	$8
	dc.l	$5447e
	dc.w	0
	dc.l	$5492c
	dc.w	$4
	dc.l	$54b9c
	dc.w	$1
	dc.l	$5c0ea
	dc.w	$0
	dc.l	$5c0f2
	dc.w	$7
	dc.l	$67ffe
	dc.w	$0
	dc.l	0

; Reached from the frame publication routine's 34-byte copy (Disk.1 $5E4F6), which
; continues past the patch to $5A862. The original body copies six bytes and returns,
; dropping the copy's last 12 bytes, and waits for a vertical blank on every frame.
_dmaon	btst	#0,(_custom1+3,pc)
	beq.b	.orig
	move.l	a2,-(sp)
	lea	(_dmadone,pc),a2
	tst.b	(a2)
	bne.b	.copy
	st	(a2)
	move.w	#DMAF_SETCLR|DMAF_COPPER|DMAF_RASTER,(_custom+dmacon).l
	bsr.w	_waitvb
.copy	move.l	(sp)+,a2
	move.l	(a1)+,(a0)+	;the three replaced moves
	move.l	(a1)+,(a0)+
	move.l	(a1)+,(a0)+
	jmp	($5a85e).l	;the rest of the copy
.orig	move.w	#DMAF_SETCLR|DMAF_COPPER|DMAF_RASTER,(_custom+dmacon).l
	bsr.w	_waitvb
	move.l	(a1)+,(a0)+	;original
	move.w	(a1)+,(a0)+
	rts

_dmadone	dc.b	0
	EVEN

_diskload	moveq	#1,d2
	movea.l	(_resload,pc),a2
	jmp	(resload_DiskLoad,a2)

_patch_vertb	bsr.b	_checkkeyboard
	move.w	#INTF_VERTB,(_custom+intreq).l
	tst.w	_custom+intreqr
	rte

_patch_aud1	bsr.b	_checkkeyboard
	move.w	#INTF_AUD1,(_custom+intreq).l
	tst.w	_custom+intreqr
	rte

_int68	bsr.b	_checkkeyboard
	move.w	#INTF_PORTS,(_custom+intreq).l
	tst.w	_custom+intreqr
	rte

_checkkeyboard	movem.l	d0/d1/a0,-(sp)
	move.w	#(INTF_PORTS|INTF_SETCLR),(_custom+intena).l
	lea	(_ciaa).l,a0
	btst	#CIAICRB_SP,(ciaicr,a0)
	beq.b	.end
	move.w	#INTF_PORTS,(_custom+intreq).l
	move.b	(ciasdr,a0),d0
	ori.b	#CIACRAF_SPMODE,(ciacra,a0)
	move.w	d0,-(sp)
	ror.b	#1,d0
	not.b	d0
	cmp.b	(_keyexit,pc),d0
	beq.b	_quit
	cmpi.b	#$78,d0
	beq.b	_quit
	moveq	#2,d0
.wait1	move.b	(_custom+vhposr).l,d1
.wait2	cmp.b	(_custom+vhposr).l,d1
	beq.b	.wait2
	dbra	d0,.wait1
	andi.b	#$BF,(ciacra,a0)
	move.w	(sp)+,d0
	move.b	d0,(8).w
	moveq	#-1,d1
	move.b	d1,(9).w
.end	movem.l	(sp)+,d0/d1/a0
	rts

_quit	move.l	#$FFFFFFFF,-(sp)
	movea.l	(_resload,pc),a0
	jmp	(resload_Abort,a0)

_loadgame	movem.l	d0-d7/a0-a6,-(sp)
	movea.l	a0,a1
	clr.l	(a1)
	bsr.b	_setsavename
	move.l	a1,-(sp)
	jsr	(resload_GetFileSize,a2)
	movea.l	(sp)+,a1
	cmpi.l	#$2056,d0
	bne.b	lbC0003B0
	bsr.b	_setsavename
	jsr	(resload_LoadFile,a2)
lbC0003B0	move.w	#DMAF_AUD2,(_custom+dmacon).l
	moveq	#0,d0
	move.l	d0,(_custom+aud0+ac_vol).l
	move.l	d0,(_custom+aud1+ac_vol).l
	move.l	d0,(_custom+aud2+ac_vol).l
	move.l	d0,(_custom+aud3+ac_vol).l
	movem.l	(sp)+,d0-d7/a0-a6
	moveq	#0,d0
	rts

_savegame	movem.l	d0-d7/a0-a6,-(sp)
	bsr.b	_setsavename
	lea	($5550).w,a1
	move.l	#$2056,d0
	jsr	(resload_SaveFile,a2)
	movem.l	(sp)+,d0-d7/a0-a6
	jmp	($55EB4).l

_setsavename	move.b	($55F87).l,d0
	lsr.b	#1,d0
	subq.b	#1,d0
	ori.b	#$30,d0
	lea	(Mercenary3sav,pc),a0
	move.b	d0,(15,a0)
	movea.l	(_resload,pc),a2
	rts

_subd0	lsr.l	#3,d0
	move.l	d1,-(a7)
.1	move.b	($dff006),d1
.2	cmp.b	($dff006),d1
	beq.b	.2
	subq.l	#1,d0
	bne.b	.1
	move.l	(a7)+,d1
	move.l	d1,($72b0).w	;original
	rts			;original

_waitvb	btst	#0,(_custom+vposr+1).l
	beq.b	_waitvb
.1	btst	#0,(_custom+vposr+1).l
	bne.b	.1
	rts

_clist	dc.l	$8E2C81
	dc.l	$90F4C1
	dc.l	$920038
	dc.l	$9400D0
	dc.l	$1004200
	dc.l	$1020000
	dc.l	$1040000
	dc.l	$1080000
	dc.l	$10A0000
	dc.l	$E00004
	dc.l	$E28000
	dc.l	$E40004
	dc.l	$E6A000
	dc.l	$E80004
	dc.l	$EAC000
	dc.l	$EC0004
	dc.l	$EEE000
	dc.l	$FFFFFFFE

_tags	dc.l	WHDLTAG_ATTNFLAGS_GET
	dc.w	0
_attn	dc.w	0
	dc.l	WHDLTAG_CUSTOM1_GET
_custom1	dc.l	0
	IFD VERIFY
	dc.l	WHDLTAG_CUSTOM2_GET
_custom2	dc.l	0
	dc.l	WHDLTAG_CUSTOM3_GET
_poison_start	dc.l	$340
	dc.l	WHDLTAG_CUSTOM4_GET
_poison_end	dc.l	$4000
	ENDC
	dc.l	0

_resload	dc.l	0
	CNOP	0,4

_restore_buffer	dc.l	0
