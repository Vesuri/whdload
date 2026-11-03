;*---------------------------------------------------------------------------
;  :Program.	mercenary3.slave.asm
;  :Contents.	Slave for "Mercenary 3 - The Dion Crisis"
;  :Author.	Harry/Graham/Wepl/Vesuri
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
RENDERMEM	= $1a000
STAGEMEM	= $18000	;32 KB bitmap plus up to 64 KB alignment
OBJECTMEM	= $3000		;256 pose histories (40 bytes each), page rounded
RESTOREMEM	= $5000		;17,912 bytes, rounded to whole pages
DATAMEM		= $5000		;F5: render scratch at its chip offset ($340..$407F)
; F5 destinations, as offsets from ws_ExpMem (whdload/translate-f5.i).
F5HOT		= STACKSIZE
F5RENDER	= STACKSIZE+HOTSIZE+TABLEMEM+RESTOREMEM
F5DATA		= STACKSIZE+HOTSIZE+TABLEMEM+RESTOREMEM+RENDERMEM+STAGEMEM+OBJECTMEM

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
_expmem		dc.l	-(STACKSIZE+HOTSIZE+TABLEMEM+RESTOREMEM+RENDERMEM+STAGEMEM+OBJECTMEM+DATAMEM) ;optional workspace
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
_info		dc.b	"adapted by Harry/Graham/Wepl/Vesuri",10
		dc.b	"Version 2.0 (23.10.2026)",10
		dc.b	"enhanced framerate edition"
	IFD VERIFY
		dc.b	" (VERIFY)"
	ENDC
		dc.b	0
_config		dc.b	"C5:B:Enhanced framerate",0
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

; Boolean player control (enabled by the installed icon). VERIFY retains Custom1 for individual feature
; comparisons when Custom5=0. Off keeps the original game's behaviour, not the shipped
; slave's defects (user decision): the release Off setting keeps bit 0 (the shipped
; _dmaon drops part of the palette copy and waits a field every frame) and bit 15
; (the 68040/060 cache-safe clipping limit) and clears every other feature.
	lea	(_custom1,pc),a0
	IFND VERIFY
	move.l	#1<<15|1<<0,(a0)
	ENDC
	move.l	(_enhanced,pc),d0
	beq.b	.featuresready
	move.l	#$3ffffff,(a0)
.featuresready

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
	bne.b	.indirect
; Copied renderer code uses the existing indirect-call variant on 020/030 too.
	btst	#1,(_custom1+2,pc)
	beq.w	lbC0002AA
	btst	#AFB_68020,d0
	beq.w	lbC0002AA
	move.l	(_expmem,pc),d0
	cmpi.l	#$200000,d0
	blo.w	lbC0002AA
	cmpi.l	#$a00000,d0
	blo.b	.indirect
	cmpi.l	#$1000000,d0
	blo.w	lbC0002AA
.indirect
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
	bsr.w	_f5check
	bsr.w	_trafficinit
	bsr.w	_f3data
	bsr.w	_hotcode
	bsr.w	_hotdata
	bsr.w	_patchspans
	bsr.w	_stageinit
	IFD VERIFY
	bsr.w	_bypass
	ENDC
	bsr.w	_hotrenderer
	bsr.w	_objectinit
	bsr.w	_viewinit
	bsr.w	_doorinit
	bsr.w	_cockpitinit
	bsr.w	_caminit
	bsr.w	_clipinit
; Let WHDLoad handle CPU/MMU differences and NOCACHE. Preserve the shipped
; instruction-only request with bit 13 off; SetCACR also flushes patched code.
	moveq	#CACRF_EnableI,d0
	btst	#5,(_custom1+2,pc)
	beq.b	.icacheonly
	ori.l	#CACRF_EnableD,d0
.icacheonly
	move.l	d0,d1
	movea.l	(_resload,pc),a0
	jsr	(resload_SetCACR,a0)
	move.l	(_render_base,pc),d0
	beq.b	.norenderflush
	movea.l	(_resload,pc),a0
	jsr	(resload_FlushCache,a0)
.norenderflush

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
; F5: translate the blocks instead (block 1 keeps its layout, for F4).
	btst	#0,(_f5on,pc)
	beq.b	.m1copy
	moveq	#0,d7
	bsr.w	_f5translate
	bra.b	.copied
.m1copy	lea	($4b134).l,a0
	move.w	#($4b2e2-$4b134)/2-1,d0
.copy1	move.w	(a0)+,(a1)+
	dbra	d0,.copy1
	lea	($57380).l,a0
	move.w	#($57c68-$57380)/2-1,d0
.copy2	move.w	(a0)+,(a1)+
	dbra	d0,.copy2
.copied
; F4 (Custom1 bit 19): BFFFO finds the log conversion's leading bit in the copy.
	btst	#3,(_custom1+1,pc)
	beq.b	.entries
	lea	(_f4code,pc),a0
	lea	($4ee88-$4ede4,a3),a1
	moveq	#(_f4end-_f4code)/2-1,d0
.copy4	move.w	(a0)+,(a1)+
	dbra	d0,.copy4
	move.b	#_f4word-_f4code+4,($4ee83-$4ede4,a3)	;$4EE76's bra.s
.entries
	lea	(_hotentries,pc),a0
.next	move.l	(a0)+,d0
	beq.b	.done
	movea.l	d0,a1
	moveq	#0,d0
	move.w	(a0)+,d0
	add.l	a3,d0
	btst	#0,(_f5on,pc)
	beq.b	.store
	move.l	a1,d0
	bsr.w	_f5map
.store	move.w	#$4ef9,(a1)+
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

	machine	68020
	INCLUDE	"whdload/log-f4.i"
	machine	68000

; F3: CPU-only projection state, line masks and row offsets. Use the unused tail of
; M2's page-rounded allocation; the native display pointer stays in chip.
; Patch before M1/S3/F2 copy code, so all copies inherit the same operands.
; Layout within the table slot: $6200 state, $62d0 mask/offset tables
; (base $6300, negative indexes included), $6600 row offsets. End $6710.
; The low-word-addressed $42e00 coordinate table remains in chip RAM.
_f3data
	btst	#2,(_custom1+1,pc)
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
.fast	addi.l	#STACKSIZE+HOTSIZE+$6200,d0
	move.l	d0,d6
	movea.l	d0,a1
	lea	($42c04).l,a0
	moveq	#($42c76-$42c04)/2-1,d0
.state	move.w	(a0)+,(a1)+
	dbra	d0,.state
	movea.l	d6,a1
	adda.w	#$d0,a1
	lea	($49880).l,a0
	move.w	#($49b34-$49880)/2-1,d0
.masks	move.w	(a0)+,(a1)+
	dbra	d0,.masks
	movea.l	d6,a1
	adda.w	#$400,a1
	lea	($43080).l,a0
	move.w	#($43190-$43080)/2-1,d0
.lookup	move.w	(a0)+,(a1)+
	dbra	d0,.lookup
	lea	(_f3_operands,pc),a0
.next	move.l	(a0)+,d0
	beq.b	.slave
	movea.l	d0,a1
	bsr.b	.patch
	bra.b	.next
.slave	lea	(_f3_slave,pc),a0
.nextslave
	move.w	(a0)+,d0
	beq.b	.restore
	lea	(_base,pc),a1
	adda.w	d0,a1
	bsr.b	.patch
	bra.b	.nextslave
.restore
	lea	(_restore_projection,pc),a0
	move.l	d6,(a0)
.done	rts
.patch	move.l	(a1),d0
	cmpi.l	#$498b0,d0
	bne.b	.projection
	move.l	d6,d0
	addi.l	#$100,d0
	bra.b	.store
.projection
	cmpi.l	#$43080,d0
	blo.b	.stateptr
	subi.l	#$43080-$400,d0
	add.l	d6,d0
	bra.b	.store
.stateptr
	subi.l	#$42c04,d0
	add.l	d6,d0
.store	move.l	d0,(a1)
	rts
_f3_slave
	dc.w	_f3sky0+2-_base
	dc.w	_f3sky1+2-_base
	dc.w	_f3sky2+2-_base
	dc.w	_f3sky3+2-_base
	dc.w	_f3sky4+2-_base
	dc.w	0
	INCLUDE "whdload/data-f3.i"

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

; S3/F2: renderer blocks, including their PC-relative data. Absolute
; references and external branch islands are described by Disk.1 offsets.
; Copy after M2/R1 and VERIFY bypasses, before the final instruction-cache flush.
; S4: only view writers use _drawbase. The native chip-buffer pointer stays
; live for the panel, IRQ text, full-screen copies and display hardware.
_stageinit
	btst	#2,(_custom1+2,pc)
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
.fast	addi.l	#STACKSIZE+HOTSIZE+TABLEMEM+RESTOREMEM+RENDERMEM+$7fff,d0
	andi.l	#$ffff0000,d0
	ori.l	#$8000,d0
	lea	(_stagebase,pc),a0
	move.l	d0,(a0)
	lea	(_drawbase,pc),a0
	move.l	($42c00).l,(a0)
	move.l	a0,d0
	lea	(_stageoperands,pc),a1
.next	move.l	(a1)+,d1
	beq.b	.hooks
	movea.l	d1,a2
	move.l	d0,(a2)
	bra.b	.next
.hooks
; Disk.1 $5E840: first clear base load becomes a call setting the view target.
	move.w	#$4eb9,($5ab90).l
	lea	(_stageclear,pc),a0
	move.l	a0,($5ab92).l
; Disk.1 $5E458: copy before publication, then resume its original body.
	move.w	#$4ef9,($5a7a8).l
	lea	(_stagepublish,pc),a0
	move.l	a0,($5a7aa).l
	move.w	#$4e71,($5a7ae).l
.done	rts

_stageclear
	move.w	sr,-(sp)
	move.l	a0,-(sp)
	lea	(_drawbase,pc),a0
	move.l	($42c00).l,(a0)
	tst.w	($71cc).w
	bpl.b	.chip
	move.l	(_stagebase,pc),(a0)
	lea	(_stagepending,pc),a0
	move.w	#1,(a0)
.chip	movea.l	(_drawbase,pc),a6
	movea.l	(sp)+,a0
	move.w	(sp)+,ccr
	rts

_stagepublish
	move.w	sr,-(sp)
	movem.l	d0-d7/a0-a6,-(sp)
	move.w	(_stagepending,pc),d0
	beq.b	.native
	tst.w	($71cc).w
	bpl.b	.native
	movea.l	(_stagebase,pc),a0
	movea.l	($42c00).l,a1
	moveq	#3,d0
.plane	move.w	#169,d1
.copy	movem.l	(a0)+,d2-d7/a2-a3
	movem.l	d2-d7/a2-a3,(a1)
	lea	32(a1),a1
	dbra	d1,.copy
	lea	2560(a0),a0
	lea	2560(a1),a1
	dbra	d0,.plane
.native
	movem.l	(sp)+,d0-d7/a0-a6
	move.w	(sp)+,ccr
	movea.l	($72b4).w,a0
	tst.w	($6ee4).w
	jsr	($5a7b0).l
	move.w	sr,-(sp)
	move.l	a0,-(sp)
	lea	(_stagepending,pc),a0
	clr.w	(a0)
	lea	(_drawbase,pc),a0
	move.l	($42c00).l,(a0)
	movea.l	(sp)+,a0
	move.w	(sp)+,ccr
	rts
_stagebase	dc.l	0
_drawbase	dc.l	0
_stagepending	dc.w	0
; Absolute base-load operands, expressed as Disk.1 offsets. IRQ text and
; full-screen/menu/blitter users deliberately retain the native chip pointer.
_stageoperands
	dc.l	$49524-$3cb0
	dc.l	$4a2de-$3cb0
	dc.l	$4a3b0-$3cb0
	dc.l	$4a482-$3cb0
	dc.l	$4a554-$3cb0
	dc.l	$4a626-$3cb0
	dc.l	$4a6f8-$3cb0
	dc.l	$4a7ca-$3cb0
	dc.l	$4a89c-$3cb0
	dc.l	$4a96e-$3cb0
	dc.l	$4aa40-$3cb0
	dc.l	$4ab12-$3cb0
	dc.l	$4abe4-$3cb0
	dc.l	$4acb6-$3cb0
	dc.l	$4ad88-$3cb0
	dc.l	$4ae5a-$3cb0
	dc.l	$4af2c-$3cb0
	dc.l	$4b060-$3cb0
	dc.l	$4b272-$3cb0
	dc.l	$4b484-$3cb0
	dc.l	$4b696-$3cb0
	dc.l	$4b8a8-$3cb0
	dc.l	$4baba-$3cb0
	dc.l	$4bccc-$3cb0
	dc.l	$4bede-$3cb0
	dc.l	$4c0f0-$3cb0
	dc.l	$4c302-$3cb0
	dc.l	$4c514-$3cb0
	dc.l	$4c726-$3cb0
	dc.l	$4c938-$3cb0
	dc.l	$4cb4a-$3cb0
	dc.l	$4cd5c-$3cb0
	dc.l	$4cf6e-$3cb0
	dc.l	$53540-$3cb0
	dc.l	$53b32-$3cb0
	dc.l	$53b60-$3cb0
	dc.l	$53b8e-$3cb0
	dc.l	$53bbc-$3cb0
	dc.l	$53bea-$3cb0
	dc.l	$53c18-$3cb0
	dc.l	$53c46-$3cb0
	dc.l	$53c74-$3cb0
	dc.l	$53ca2-$3cb0
	dc.l	$53cd0-$3cb0
	dc.l	$53cfe-$3cb0
	dc.l	$53d2c-$3cb0
	dc.l	$53d5a-$3cb0
	dc.l	$53d88-$3cb0
	dc.l	$53db6-$3cb0
	dc.l	$53de4-$3cb0
	dc.l	$55e00-$3cb0
	dc.l	$5c84e-$3cb0
	dc.l	$5c886-$3cb0
	dc.l	$5c8cc-$3cb0
	dc.l	$5e51a-$3cb0
	dc.l	$5e84e-$3cb0
	dc.l	$5e85c-$3cb0
	dc.l	$5e86a-$3cb0
	dc.l	0

_hotrenderer
	btst	#1,(_custom1+2,pc)
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
.fast
	btst	#0,(_f5on,pc)
	bne.w	_f5renderer
	lea	(_render_ranges,pc),a0
	lea	(_render_operands,pc),a1
	lea	(_render_branches,pc),a2
	lea	(_render_entries,pc),a3
; Custom1 bit 17 extends S3 and bypasses M1 chip entry jumps.
	btst	#1,(_custom1+1,pc)
	beq.b	.tables
	lea	(_f2_ranges,pc),a0
	lea	(_f2_operands,pc),a1
	lea	(_f2_branches,pc),a2
	lea	(_f2_entries,pc),a3
.tables
	lea	(_render_tables,pc),a4
	movem.l	a0-a3,(a4)
	addi.l	#STACKSIZE+HOTSIZE+TABLEMEM+RESTOREMEM,d0
	lea	(_render_base,pc),a0
	move.l	d0,(a0)
	move.l	d0,d6
	movea.l	(_render_tables,pc),a2
.copyrange
	move.l	(a2)+,d0
	beq.b	.operands
	movea.l	d0,a0
	move.l	(a2)+,d1
	sub.l	d0,d1
	move.l	(a2)+,d0
	add.l	d6,d0
	movea.l	d0,a1
	lsr.l	#1,d1
	subq.w	#1,d1
.copy	move.w	(a0)+,(a1)+
	dbra	d1,.copy
	bra.b	.copyrange
.operands
	movea.l	(_render_tables+4,pc),a0
.nextop	move.l	(a0)+,d0
	beq.b	.branches
	movea.l	d0,a1
	move.l	(a1),d0
	bsr.w	_rendermap
	move.l	d0,d3
	move.l	a1,d0
	bsr.w	_rendermap
	movea.l	d0,a1
	move.l	d3,(a1)
	bra.b	.nextop
.branches
	movea.l	(_render_tables+8,pc),a0
.nextbr	move.l	(a0)+,d0
	beq.b	.entries
	bsr.w	_rendermap
	movea.l	d0,a1
	move.l	(a0)+,d0
	bsr.w	_rendermap
	move.l	d0,d3
	move.l	(a0)+,d0
	add.l	d6,d0
	movea.l	d0,a3
	move.w	#$4ef9,(a3)+
	move.l	d3,(a3)
	sub.l	a1,d0
	move.w	d0,(a1)
	bra.b	.nextbr
.entries
	movea.l	(_render_tables+12,pc),a0
.nextentry
	move.l	(a0)+,d0
	beq.b	.restore
	movea.l	d0,a1
	bsr.w	_rendermap
	move.w	#$4ef9,(a1)+
	move.l	d0,(a1)
	bra.b	.nextentry
.restore
; P1 must restore the moved mutable words, not their unused chip copies.
	lea	(_restore_ranges,pc),a0
.nextrange
	move.l	(a0),d0
	beq.b	.done
	bsr.w	_rendermap
	move.l	d0,(a0)
	addq.l	#6,a0
	bra.b	.nextrange
.done	rts

; Bit 15: the ground renderer temporarily changes the lower clipping limit.
; Its native immediate comparison (Disk.1 $5366A) can remain stale in the
; instruction cache. Keep the limit as data, in chip or relocated rendering.
_clipinit
	lea	(_cliplimit,pc),a0
	lea	(_restore_clip,pc),a1
	move.l	a0,(a1)
	btst	#7,(_custom1+2,pc)
	beq.w	.done
	move.w	(_attn,pc),d0
	btst	#AFB_68040,d0
	beq.w	.done
	move.l	(_render_base,pc),d6
	move.l	#$5366c-$3cb0,d0
	bsr.w	_clipmap
	movea.l	d0,a0
	lea	(_cliplimit,pc),a1
	move.w	(a0),(a1)
	move.l	#$5380a-$3cb0,d0
	bsr.w	_clipmap
	movea.l	d0,a0
	move.l	a1,(a0)
	move.l	#$53822-$3cb0,d0
	bsr.w	_clipmap
	movea.l	d0,a0
	move.l	a1,(a0)
	move.l	#$53668-$3cb0,d0
	bsr.w	_clipmap
	movea.l	d0,a0
	move.w	#$4eb9,(a0)+
	lea	(_cliprow,pc),a1
	move.l	a1,(a0)
	move.l	#$5368e-$3cb0,d0
	bsr.w	_clipmap
	movea.l	d0,a0
	move.w	#$4eb9,(a0)+
	lea	(_cliplast,pc),a1
	move.l	a1,(a0)
	move.l	#$536be-$3cb0,d0
	bsr.w	_clipmap
	lea	(_clipend+2,pc),a0
	move.l	d0,(a0)
.done	rts
_clipmap
	tst.l	d6
	beq.b	.done
	bra.w	_rendermap
.done	rts
_cliprow
	move.w	a3,d7
	cmp.w	(_cliplimit,pc),d7
	rts
_cliplast
	cmp.w	(_cliplimit,pc),d0
	bcs.b	_clipreturn
	lea	(4,sp),sp
_clipend
	jmp	0.l
_clipreturn	rts
_cliplimit	dc.w	$9540

; d0: original address -> copied address, unchanged outside the blocks.
; Clobbers a2/d1/d2 only. d6 holds the renderer allocation base during boot.
_rendermap
	btst	#0,(_f5on,pc)
	bne.w	_f5map
	btst	#1,(_custom1+1,pc)
	beq.b	.ranges
; Native drawing dispatch entries are four-byte branches; leave them intact
; for register/computed users, but send copied direct callers to the callee.
	lea	(_render_aliases,pc),a2
.alias	move.l	(a2)+,d1
	beq.b	.m1
	move.l	(a2)+,d2
	cmp.l	d1,d0
	bne.b	.alias
	move.l	d2,d0
	bra.b	.ranges
.m1	btst	#5,(_custom1+3,pc)
	beq.b	.ranges
	cmpi.l	#$4ede4-$3cb0,d0
	blo.b	.ranges
	cmpi.l	#$4ef92-$3cb0,d0
	bhs.b	.projection
	subi.l	#$4ede4-$3cb0,d0
	bra.b	.hot
.projection
	cmpi.l	#$5b030-$3cb0,d0
	blo.b	.ranges
	cmpi.l	#$5b918-$3cb0,d0
	bhs.b	.ranges
	subi.l	#$5b030-$3cb0-($4ef92-$4ede4),d0
.hot	add.l	(_expmem,pc),d0
	addi.l	#STACKSIZE,d0
	rts
.ranges
	movea.l	(_render_tables,pc),a2
.next	move.l	(a2)+,d1
	beq.b	.done
	move.l	(a2)+,d2
	cmp.l	d1,d0
	blo.b	.skip
	cmp.l	d2,d0
	bhs.b	.skip
	sub.l	d1,d0
	add.l	(a2),d0
	add.l	d6,d0
	rts
.skip	addq.l	#4,a2
	bra.b	.next
.done	rts
_render_aliases
	dc.l	$469b0-$3cb0,$494b6-$3cb0
	dc.l	$469b4-$3cb0,$4a26c-$3cb0
	dc.l	$469b8-$3cb0,$4afd4-$3cb0
	dc.l	$469c4-$3cb0,$492b0-$3cb0
	dc.l	$469c8-$3cb0,$48e3c-$3cb0
	dc.l	0
_render_base	dc.l	0
_render_tables	dc.l	0,0,0,0
	INCLUDE	"whdload/renderer-relocs.i"
	INCLUDE	"whdload/renderer-f2.i"
	INCLUDE	"whdload/translate-f5.s"

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
	bsr.w	_replaygate
	bne.b	.done
	lea	(_logicstamp,pc),a0
	cmpi.w	#1,($7122).w
	beq.b	.modeok
	btst	#4,(_custom1+2,pc)
	beq.b	.othermode
	move.w	($7142).w,d0
	cmp.w	($7122).w,d0
	bne.b	.othermode
	cmpi.w	#2,d0
	bhi.b	.othermode
.modeok
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

; Bit 24: a passenger flight replays recorded input per logic pass ($70A2, see
; _presentgate), so its real-time length follows the pass rate. On the A500 the trip
; takes about ten fields a pass and the pilot's talk ends before landing. Pace the
; replay at REPLAYFIELDS fields a pass; the game's 4..8 tick clamp keeps the world
; in real time up to 8. Returns Z clear when it paced the pass. Uses d0/a0.
; Its own stamp, invalid outside replays: a later trip starts with native timing.
REPLAYFIELDS	=	8
_replaygate
	lea	(_replaystamp,pc),a0
	tst.w	($70a2).w
	beq.b	.no
	btst	#0,(_custom1,pc)
	beq.b	.no
	tst.w	(2,a0)
	beq.b	.first
.check	move.w	($529f4).l,d0
	sub.w	(a0),d0			;word subtraction handles VERTB wrap
	cmpi.w	#REPLAYFIELDS,d0
	bhs.b	.ready
	move.w	($529f4).l,d0
.wait	cmp.w	($529f4).l,d0
	beq.b	.wait
	bra.b	.check
.ready	move.w	d0,($52954).l
	add.w	d0,(a0)
	bra.b	.yes
.first	move.w	($529f4).l,(a0)
	move.w	#1,(2,a0)
.yes	moveq	#1,d0
	rts
.no	clr.w	(2,a0)
	moveq	#0,d0
	rts
_replaystamp	dc.w	0,0			;last accepted VERTB, valid replay pass

; Bit 25: traffic moves at the A500's speed. The traffic routine (Disk.1 $54F0E,
; called once per logic pass at $5E084 and $5E22A) steps every vehicle a fixed
; distance a few times a pass: the mover loops at $553F0 and $55502 add the slot's
; velocity ($6CB0/$6CB2) to X/Z and its speed ($6C7C) to the 16-bit cell progress
; ($6C7E), whose carry ends the cell; $5553A then snaps the vehicle onto the cell
; and reads the next turn. Real-time traffic speed so follows the pass rate: the
; taxi rides are timed for the A500's ten fields a pass, the release runs four.
; Scale each step by elapsed fields / TRAFFICFIELDS, never above the native step,
; so velocity and progress stay in proportion and the cell snap stays exact.
; Patch before F2 copies the loops ($553AE..$5553A); no F2 operand, branch or
; entry lies in the replaced instructions. Replays keep native steps (bit 24).
TRAFFICFIELDS	=	10
_trafficinit
	btst	#1,(_custom1,pc)
	beq.b	.done
	lea	($553fc-$3cb0).l,a0
	bsr.b	.match
	bne.b	.done
	lea	($55510-$3cb0).l,a0
	bsr.b	.match
	bne.b	.done
	cmpi.l	#$4eb9<<16|($54f0e-$3cb0)>>16,($5e084-$3cb0).l
	bne.b	.done
	cmpi.w	#($54f0e-$3cb0)&$ffff,($5e088-$3cb0).l
	bne.b	.done
	cmpi.l	#$4eb9<<16|($54f0e-$3cb0)>>16,($5e22a-$3cb0).l
	bne.b	.done
	cmpi.w	#($54f0e-$3cb0)&$ffff,($5e22e-$3cb0).l
	bne.b	.done
	lea	($553fc-$3cb0).l,a0
	bsr.b	.patch
	lea	($55510-$3cb0).l,a0
	bsr.b	.patch
	lea	(_trafficpass,pc),a0
	move.l	a0,($5e086-$3cb0).l
	move.l	a0,($5e22c-$3cb0).l
.done	rts
; move.w $6cb0(a0),d0 / move.w $6cb2(a0),d1 / ext.l d0 / ext.l d1
.match	cmpi.l	#$30286cb0,(a0)
	bne.b	.no
	cmpi.l	#$32286cb2,(4,a0)
	bne.b	.no
	cmpi.l	#$48c048c1,(8,a0)
.no	rts
.patch	move.w	#$4eb9,(a0)+
	lea	(_trafficstep,pc),a1
	move.l	a1,(a0)+
	move.l	#$4e714e71,(a0)+
	move.w	#$4e71,(a0)
	rts

; Once per pass: the step scale in 1/4096 from the pass's elapsed fields ($52954,
; stored by the gates before the world ticks). Zero keeps the native step.
_trafficpass
	movem.l	d0/a0,-(sp)
	moveq	#0,d0
	tst.w	($70a2).w
	bne.b	.set
	move.w	($52954).l,d0
	bne.b	.some
	moveq	#1,d0
.some	cmpi.w	#TRAFFICFIELDS,d0
	blo.b	.scale
	moveq	#0,d0
	bra.b	.set
.scale	lsl.w	#8,d0
	lsl.w	#4,d0
	divu.w	#TRAFFICFIELDS,d0
.set	lea	(_trafficf,pc),a0
	move.w	d0,(a0)
	movem.l	(sp)+,d0/a0
	jmp	($54f0e-$3cb0).l

; In both mover loops, for the replaced loads: d0/d1 = X/Z velocity, d2 = the
; progress step (speed, negated in $55502's loop), all scaled by _trafficf.
	IFD VERIFY
	dc.b	'M3TRF001'
_trafficcount	dc.l	0			;mover steps, VERIFY only
	ENDC
_trafficstep
	IFD VERIFY
	move.l	a1,-(sp)
	lea	(_trafficcount,pc),a1
	addq.l	#1,(a1)
	move.l	(sp)+,a1
	ENDC
	move.w	($6cb0,a0),d0
	move.w	($6cb2,a0),d1
	ext.l	d0
	ext.l	d1
	move.l	d3,-(sp)
	move.w	(_trafficf,pc),d3
	beq.b	.native
	muls.w	d3,d0
	asr.l	#8,d0
	asr.l	#4,d0
	muls.w	d3,d1
	asr.l	#8,d1
	asr.l	#4,d1
	muls.w	d3,d2
	asr.l	#8,d2
	asr.l	#4,d2
.native	move.l	(sp)+,d3
	rts
_trafficf	dc.w	0

; P2: snapshot in the object renderer (Disk.1 $577BE), after collision.
; Logic frames use the previous pose too, so intermediate frames never rewind.
; History: previous XYZ, current XYZ, location, model flags, generation,
; previous/current heading bytes, changed flag, padding (40 bytes per object).
_objectinit
	IFD VERIFY
; Preserve the main-3D bypass; the object entry hook would replace its RTS.
	btst	#0,(_custom2+3,pc)
	bne.w	.done
	ENDC
	btst	#3,(_custom1+2,pc)
	beq.w	.done
	move.l	(_restore_buffer,pc),d0
	beq.w	.done
	move.l	(_expmem,pc),d0
	cmpi.l	#$200000,d0
	blo.w	.done
	move.w	(_attn,pc),d1
	btst	#AFB_68020,d1
	beq.w	.done
	addi.l	#STACKSIZE+HOTSIZE+TABLEMEM+RESTOREMEM+RENDERMEM+STAGEMEM,d0
	lea	(_object_buffer,pc),a0
	move.l	d0,(a0)
	movea.l	d0,a0
	move.w	#OBJECTMEM/4-1,d1
.clear	clr.l	(a0)+
	dbra	d1,.clear
; Enter the unmodified continuation in chip or its S3 copy.
	move.l	#$577c8-$3cb0,d0
	move.l	(_render_base,pc),d6
	beq.b	.chip
	bsr.w	_rendermap
.chip	lea	(_object_continue+2,pc),a0
	move.l	d0,(a0)
	move.w	#$4ef9,($577be-$3cb0).l
	lea	(_objectdraw,pc),a0
	move.l	a0,($577c0-$3cb0).l
; Stage the model only after its committed distance/selection test.
	move.l	#$57c36-$3cb0,d0
	tst.l	d6
	beq.b	.modelchip
	bsr.w	_rendermap
.modelchip
	movea.l	d0,a1
	move.w	#$4ef9,(a1)+
	lea	(_objectmodel,pc),a0
	move.l	a0,(a1)
	addq.l	#6,d0
	lea	(_model_continue+2,pc),a0
	move.l	d0,(a0)
.done	rts
_object_buffer	dc.l	0
_object_generation	dc.w	0
_object_scene	dc.l	-1
_object_active	dc.w	0
_object_alpha	dc.w	0

_objectdraw
	move.w	sr,-(sp)
	movem.l	d0-d7/a0-a6,-(sp)
	lea	(_inpresent,pc),a6
	lea	(_object_active,pc),a0
	clr.w	(a0)
	tst.w	($70a2).w		;recorded-input replay: native (see _presentgate)
	bne.w	.reset
	move.w	($7142).w,d0
	cmp.w	($7122).w,d0
	bne.w	.reset
	cmpi.w	#1,d0
	beq.b	.modeok
	btst	#4,(_custom1+2,pc)
	beq.w	.reset
	cmpi.w	#2,d0
	bhi.w	.reset
.modeok
	tst.w	($71cc).w
	bpl.w	.reset
	move.w	(_object_generation,pc),d5
	tst.w	(a6)
	bne.b	.time
	addq.w	#1,d5
	bne.b	.generation
; Reset scene validity on wrap so every visible object snaps.
	lea	(_object_scene,pc),a0
	move.l	#-1,(a0)
	movea.l	(_object_buffer,pc),a0
	move.w	#255,d0
.wrap	clr.w	(32,a0)
	lea	(40,a0),a0
	dbra	d0,.wrap
	moveq	#1,d5
.generation
	lea	(_object_generation,pc),a0
	move.w	d5,(a0)
.time	btst	#6,(_custom1+2,pc)
	beq.b	.livetime
	move.w	(_viewalpha,pc),d6
	bra.b	.timeok
.livetime
	move.w	($529f4).l,d6
	sub.w	(_pstate,pc),d6
.timeok
	move.w	(_pstate+4,pc),d7
	cmp.w	d7,d6
	bls.b	.ratio
	move.w	d7,d6
.ratio	lea	(_object_alpha,pc),a0
	move.w	d6,(a0)
	lea	(_object_active,pc),a0
	move.w	#1,(a0)
	lea	($7423).w,a3
	move.w	($71e6).w,d4
	beq.w	.draw
	subq.w	#1,d4
.next	moveq	#0,d0
	move.b	(a3)+,d0
	beq.w	.skip		; player/world marker
	cmpi.w	#10,d0		; player proxy follows P1, not object delay
	beq.w	.skip
	move.w	d0,d1
	mulu.w	#40,d1
	movea.l	(_object_buffer,pc),a1
	adda.l	d1,a1
	add.w	d0,d0
	add.w	d0,d0
	movea.w	d0,a0		; object index * 4
	tst.w	(a6)
	bne.w	.skip
	move.l	(12,a1),(a1)
	move.l	(16,a1),(4,a1)
	move.l	(20,a1),(8,a1)
	move.b	(35,a1),(34,a1)
	move.l	($581c,a0),(12,a1)
	move.l	($5c1c,a0),(16,a1)
	move.l	($601c,a0),(20,a1)
	moveq	#0,d1
; The native heading byte is used by the vehicle slots 1..27.
	cmpi.w	#28*4,d0
	bhs.b	.heading
	move.b	($6c1c,a0),d1
.heading	move.b	d1,(35,a1)
	move.l	($681c,a0),d1
	clr.b	d1		; last byte is the changing spatial cell
	cmp.l	(24,a1),d1
	bne.b	.snap
	move.l	($641c,a0),d2
	cmp.l	(28,a1),d2
	bne.b	.snap
	move.w	d5,d2
	subq.w	#1,d2
	cmp.w	(32,a1),d2
	bne.b	.snap
	move.l	($7158).w,d2
	cmp.l	(_object_scene,pc),d2
	bne.b	.snap
; Large discontinuities snap, including wrapped world coordinates.
	moveq	#0,d2
.validate
	move.l	(12,a1,d2.w),d3
	sub.l	(a1,d2.w),d3
	cmpi.l	#32767,d3
	bgt.b	.snap
	cmpi.l	#-32767,d3
	blt.b	.snap
	addq.w	#4,d2
	cmpi.w	#12,d2
	bne.b	.validate
	bra.b	.record
.snap	movem.l	(12,a1),d1-d3
	movem.l	d1-d3,(a1)
	move.b	(35,a1),(34,a1)
; Projectiles (slots 50..63, Disk.1 $546A2) first appear one pass after spawning,
; already moved by one velocity step. In the same scene, start them one step back
; so the presentations before their second pass move too. Life $7FFF is static.
	cmpi.w	#50*4,d0
	blo.b	.record
	cmpi.w	#63*4,d0
	bhi.b	.record
	move.w	($5492,a0),d1
	beq.b	.record
	cmpi.w	#$7fff,d1
	beq.b	.record
	move.l	($7158).w,d1
	cmp.l	(_object_scene,pc),d1
	bne.b	.record
; X, Y and Z velocities are tables $38 bytes apart; same limit as .validate.
	lea	($54ca,a0),a2
	moveq	#2,d2
.check	move.l	(a2),d1
	addi.l	#32767,d1
	cmpi.l	#2*32767,d1
	bhi.b	.record
	lea	($38,a2),a2
	dbra	d2,.check
	lea	($54ca,a0),a2
	movea.l	a1,a4
	moveq	#2,d2
.step	move.l	(a2),d1
	sub.l	d1,(a4)+
	lea	($38,a2),a2
	dbra	d2,.step
.record	move.l	($681c,a0),d1
	clr.b	d1
	move.l	d1,(24,a1)
	move.l	($641c,a0),(28,a1)
	move.w	d5,(32,a1)
	clr.w	(36,a1)
; Static objects need no staging.
	move.l	(a1),d1
	cmp.l	(12,a1),d1
	bne.b	.changed
	move.l	(4,a1),d1
	cmp.l	(16,a1),d1
	bne.b	.changed
	move.l	(8,a1),d1
	cmp.l	(20,a1),d1
	bne.b	.changed
	move.b	(34,a1),d1
	cmp.b	(35,a1),d1
	beq.b	.skip
.changed	move.w	#1,(36,a1)
.skip	dbra	d4,.next
	tst.w	(a6)
	bne.b	.draw
	lea	(_object_scene,pc),a0
	move.l	($7158).w,(a0)
	bra.b	.draw
.reset	lea	(_object_scene,pc),a0
	move.l	#-1,(a0)
.draw	movem.l	(sp)+,d0-d7/a0-a6
	move.w	(sp)+,ccr
	bsr.w	_objectnative
	move.w	sr,-(sp)
	move.l	a0,-(sp)
	lea	(_object_active,pc),a0
	clr.w	(a0)
	movea.l	(sp)+,a0
	move.w	(sp)+,ccr
	rts
_objectnative
	clr.w	($6f32).w
	move.w	#$7fff,($71da).w
_object_continue
	jmp	($577c8-$3cb0).l

; Distance ordering and the nearest-object result remain committed. Only
; geometry sees staged coordinates, restored before this model returns.
_objectmodel
; Most visible objects are static. Avoid the full staging frame for them.
	movem.l	d0/a1,-(sp)
	move.w	(_object_active,pc),d0
	beq.w	.native
	move.w	a0,d0
	beq.w	.native
	cmpi.w	#10*4,d0
	beq.b	.native
	cmpi.w	#255*4,d0
	bhi.b	.native
	mulu.w	#10,d0
	movea.l	(_object_buffer,pc),a1
	adda.l	d0,a1
	move.w	(_object_generation,pc),d0
	cmp.w	(32,a1),d0
	bne.b	.unrecorded
	tst.w	(36,a1)
	bne.b	.moving
; Ships move after the renderer (Disk.1 $546A2). A pose recorded as static may
; already be a pass ahead; draw the recorded pose, not the live one.
	move.l	($581c,a0),d0
	cmp.l	(12,a1),d0
	bne.b	.moving
	move.l	($5c1c,a0),d0
	cmp.l	(16,a1),d0
	bne.b	.moving
	move.l	($601c,a0),d0
	cmp.l	(20,a1),d0
	bne.b	.moving
	cmpa.w	#28*4,a0
	bhs.b	.native
	move.b	($6c1c,a0),d0
	cmp.b	(35,a1),d0
	beq.b	.native
.moving	movem.l	(sp)+,d0/a1
	bra.b	.stage
; A projectile spawned after the last logic pass's recording is not yet on the
; presented timeline; its live pose is a pass ahead. Presentations draw it as an
; empty model (opcode 0 returns, Disk.1 $57C54), after the committed selection test.
.unrecorded
	move.w	(_inpresent,pc),d0
	beq.b	.native
	move.w	a0,d0
	cmpi.w	#50*4,d0
	blo.b	.native
	cmpi.w	#63*4,d0
	bhi.b	.native
	move.w	($5492,a0),d0
	beq.b	.native
	cmpi.w	#$7fff,d0
	beq.b	.native
	movem.l	(sp)+,d0/a1
	rts
.native	movem.l	(sp)+,d0/a1
	bra.w	_modelnative
.stage	suba.w	#20,sp		; object pointer, XYZ, heading word, active word
	move.w	sr,-(sp)
	movem.l	d0-d7/a0-a6,-(sp)
	lea	(62,sp),a5
	clr.w	(18,a5)
	move.w	a0,d0
	mulu.w	#10,d0
	movea.l	(_object_buffer,pc),a1
	adda.l	d0,a1
	move.w	(_object_alpha,pc),d6
	move.w	(_pstate+4,pc),d7
	tst.w	d7
	beq.w	.draw
; Caught up: the recorded pose. The live one may be a pass ahead.
	cmp.w	d7,d6
	bls.b	.alpha
	move.w	d7,d6
.alpha	move.l	a0,(a5)
	move.l	($581c,a0),(4,a5)
	move.l	($5c1c,a0),(8,a5)
	move.l	($601c,a0),(12,a5)
	move.w	#1,(18,a5)
	moveq	#0,d2
	lea	($581c,a0),a2
.position
	move.l	(12,a1,d2.w),d1
	sub.l	(a1,d2.w),d1
	muls.w	d6,d1
	divs.w	d7,d1
	ext.l	d1
	add.l	(a1,d2.w),d1
	move.l	d1,(a2)
	lea	($400,a2),a2
	addq.w	#4,d2
	cmpi.w	#12,d2
	bne.b	.position
	cmpa.w	#28*4,a0
	bhs.b	.draw
	move.b	($6c1c,a0),(16,a5)
	moveq	#0,d1
	move.b	(35,a1),d1
	sub.b	(34,a1),d1
	ext.w	d1
	muls.w	d6,d1
	divs.w	d7,d1
	add.b	(34,a1),d1
	move.b	d1,($6c1c,a0)
.draw	movem.l	(sp)+,d0-d7/a0-a6
	move.w	(sp)+,ccr
	bsr.w	_modelnative
	move.w	sr,-(sp)
	movem.l	d0/a0-a1,-(sp)
	lea	(14,sp),a1
	tst.w	(18,a1)
	beq.b	.done
	movea.l	(a1),a0
	move.l	(4,a1),($581c,a0)
	move.l	(8,a1),($5c1c,a0)
	move.l	(12,a1),($601c,a0)
	cmpa.w	#28*4,a0
	bhs.b	.done
	move.b	(16,a1),($6c1c,a0)
.done	movem.l	(sp)+,d0/a0-a1
	move.w	(sp)+,ccr
	adda.w	#20,sp
	rts
_modelnative
	move.w	(a4,d7.w),d7
	adda.l	d7,a4
_model_continue
	jmp	($57c3c-$3cb0).l

; Bit 14: a single delayed camera timeline for logic and extra frames.
; Collision still sees committed coordinates; its drawing tail runs with the
; presented camera. Hooks below name Disk.1 offsets.
_viewinit
	btst	#6,(_custom1+2,pc)
	beq.w	.done
	btst	#4,(_custom1+3,pc)
	beq.w	.done
	move.l	(_restore_buffer,pc),d0
	beq.w	.done
	moveq	#0,d7
	btst	#4,(_custom1+2,pc)
	beq.b	.walkhooks
	moveq	#1,d7
; Vehicle view setup is already done with the staged pose at publication.
	move.l	#$4e714e71,($5e2d8-$3cb0).l
.walkhooks
	lea	(_viewhooks,pc),a1
.next	move.l	(a1)+,d0
	beq.b	.tableend
	movea.l	d0,a0
	move.w	#$4eb9,(a0)+
	move.w	(a1)+,d0
	lea	(_viewhooks,pc),a2
	adda.w	d0,a2
	move.l	a2,(a0)+
	move.w	(a1)+,d0
	beq.b	.next
	move.w	d0,(a0)
	bra.b	.next
.tableend
	tst.w	d7
	beq.b	.geometry
	moveq	#0,d7
	lea	(_viewtransporthooks,pc),a1
	bra.b	.next
.geometry
	lea	($577be-$3cb0).l,a0
	lea	(_viewobjects_call+2,pc),a1
	lea	(_viewobjects,pc),a2
	lea	(_objectnative,pc),a3
	bsr.w	_viewhook
	lea	($5765e-$3cb0).l,a0
	lea	(_viewscene_call+2,pc),a1
	lea	(_viewscene,pc),a2
	lea	(_viewscenechip,pc),a3
	bsr.w	_viewhook
.done	rts
_viewhook
	cmpi.w	#$4e75,(a0)
	beq.b	.done
	cmpi.w	#$4ef9,(a0)
	bne.b	.chip
	movea.l	(2,a0),a3
.chip	move.l	a3,(a1)
	move.w	#$4ef9,(a0)+
	move.l	a2,(a0)
.done	rts
_viewscenechip
	tst.w	($713e).w
	beq.b	.zero
	jmp	($57664-$3cb0).l
.zero	jmp	($57674-$3cb0).l
_viewhooks
	dc.l	$5e0ba-$3cb0
	dc.w	_nativewalk-_viewhooks,$6000+($5e0dc-($5e0ba+8))
	dc.l	$5e186-$3cb0
	dc.w	_nativecollision-_viewhooks,$4e71
	dc.l	$5e1be-$3cb0
	dc.w	_rollbackcamera-_viewhooks,$4e71
	dc.l	$5e1e6-$3cb0
	dc.w	_endwalk-_viewhooks,0
	dc.l	$5aee0-$3cb0
	dc.w	_collisiontail-_viewhooks,0
	dc.l	0
_viewtransporthooks
	dc.l	$5e280-$3cb0
	dc.w	_nativevehicle-_viewhooks,$6000+($5e2c0-($5e280+8))
	dc.l	$5e3ce-$3cb0
	dc.w	_nativespace-_viewhooks,$6000+($5e3dc-($5e3ce+8))
	dc.l	$5e37a-$3cb0
	dc.w	_nativecollision-_viewhooks,$4e71
	dc.l	$5e39e-$3cb0
	dc.w	_endvehicle-_viewhooks,0
	dc.l	$5e43a-$3cb0
	dc.w	_endvehicle-_viewhooks,0
	dc.l	0

_viewalpha	dc.w	0
_viewready	dc.w	0
_viewpose	ds.b	32
_viewnav	ds.b	12
_viewlocal	ds.b	12
_viewspaceactive dc.w 0
_committednav	ds.b	12
_collisiononly	dc.w	0
_drawcollision	dc.w	0

_viewtime
	move.w	($529f4).l,d6
	sub.w	(_pstate,pc),d6
	move.w	(_pstate+4,pc),d7
	cmp.w	d7,d6
	bls.b	.clamped
	move.w	d7,d6
.clamped
	lea	(_viewalpha,pc),a0
	move.w	d6,(a0)
	rts

; Temporarily stage the player, derive all camera inputs, then restore the
; committed pose before returning to native code. d6/d7 is the frozen alpha.
_viewcamera
	movem.l	($7142).w,d0-d7
	movem.l	d0-d7,-(sp)
	movem.l	($702a).w,d0-d2
	movem.l	d0-d2,-(sp)
	movem.l	($7038).w,d0-d2
	movem.l	d0-d2,-(sp)
	move.w	(_viewalpha,pc),d6
	move.w	(_pstate+4,pc),d7
	bsr.w	_interpolateplayer
	bsr.w	_rememberview
	bsr.w	_deriveview
	movem.l	(sp)+,d0-d2
	movem.l	d0-d2,($7038).w
	movem.l	(sp)+,d0-d2
	movem.l	d0-d2,($702a).w
	movem.l	(sp)+,d0-d7
	movem.l	d0-d7,($7142).w
	rts
_deriveview
	cmpi.w	#2,($7142).w
	beq.b	.space
	tst.w	($7142).w
	bne.b	.camera
	move.w	($714e).w,d1
	asr.w	#2,d1
	addi.w	#256,d1
	andi.w	#$3ff,d1
	move.w	d1,($70b8).w
_f3sky0	equ	*
	move.w	d1,($42c70).l
	move.w	($7146).w,d0
	asr.w	#2,d0
	andi.w	#$3ff,d0
	move.w	d0,($70b4).w
.camera
	jsr	($59b94).l
	jsr	($59da0).l
	jsr	($56c6e).l
	move.w	($70b4).w,d0
	movea.l	($713a).w,a1
	add.w	($575a,a1),d0
	andi.w	#$3ff,d0
_f3sky1	equ	*
	move.w	d0,($42c6c).l
	rts
.space	jsr	($59ba0).l
	jmp	($56c6e).l

_nativewalk
	lea	(_drawcollision,pc),a0
	clr.w	(a0)
	bra.b	_prepareview
_nativevehicle
	jsr	($59b94).l
	jsr	($58e42).l
	bra.b	_prepareview
_nativespace
	lea	(_drawcollision,pc),a0
	clr.w	(a0)
	bsr.b	_prepareview
	jmp	($42d14).l
_prepareview
	lea	(_viewready,pc),a0
	move.w	#1,(a0)
	bra.w	_deriveview

; Publication has completed its field wait. Sample once here, so crossing a
; field during camera preparation cannot alternate the interpolation interval.
_publishedview
	move.w	sr,-(sp)
	movem.l	d0-d7/a0-a6,-(sp)
	btst	#6,(_custom1+2,pc)
	beq.b	.done
	move.w	(_viewready,pc),d0
	beq.b	.done
	bsr.w	_viewtime
	move.w	(_inpresent,pc),d0
	beq.b	.native
	bsr.w	_interpolateplayer
	bsr.w	_rememberview
	bsr.w	_deriveview
	bra.b	.done
.native
	cmpi.w	#2,($7142).w
	beq.b	.space
	bsr.w	_viewcamera
	bra.b	.done
.space
	lea	(_committednav,pc),a0
	movem.l	($702a).w,d0-d2
	movem.l	d0-d2,(a0)
	lea	(_viewspaceactive,pc),a0
	move.w	#1,(a0)
	bsr.w	_viewcamera
	lea	(_viewnav,pc),a0
	movem.l	(a0),d0-d2
	movem.l	d0-d2,($702a).w
.done
	movem.l	(sp)+,d0-d7/a0-a6
	move.w	(sp)+,ccr
	rts
_rollbackcamera
	bra.w	_viewcamera
_endwalk
	lea	(_viewready,pc),a0
	clr.w	(a0)
	bsr.w	_deriveview
	jmp	($509f2).l
_endvehicle
	lea	(_viewspaceactive,pc),a0
	tst.w	(a0)
	beq.b	.camera
	clr.w	(a0)
	lea	(_committednav,pc),a0
	movem.l	(a0),d0-d2
	movem.l	d0-d2,($702a).w
.camera
	lea	(_viewready,pc),a0
	clr.w	(a0)
	bsr.w	_deriveview
	jmp	($50b62).l

_nativecollision
	lea	(_drawcollision,pc),a0
	clr.w	(a0)
	bsr.w	_deriveview
	lea	(_collisiononly,pc),a0
	move.w	#1,(a0)
	jsr	($56e00).l
	lea	(_collisiononly,pc),a0
	clr.w	(a0)
	bsr.w	_viewcamera
	bsr.w	_drawbuildings
	move.b	($6fda).w,d0
	rts
_collisiontail
; Hook the comparison, leaving the loop's move.w entry intact. Its back edge
; enters two bytes before this hook. Discard this JSR's return on either path.
	addq.l	#4,sp
	move.w	(_collisiononly,pc),d0
	bne.b	.done
	cmpi.w	#-32768,d3
	beq.b	.return
	jmp	($57236).l
.done	lea	(_drawcollision,pc),a0
	move.w	#1,(a0)
.return	rts

_drawbuildings
	move.w	(_drawcollision,pc),d0
	beq.b	.done
	jmp	($5722a).l
.done	rts

; Some model and secondary-view code reads the live pose directly. Give it
; the same world, navigation and room-local pose as the camera, restoring all
; three before returning to game logic.
_rememberview
	lea	(_viewpose,pc),a0
	movem.l	($7142).w,d0-d7
	movem.l	d0-d7,(a0)
	movem.l	($702a).w,d0-d2
	movem.l	d0-d2,(32,a0)
	movem.l	($7038).w,d0-d2
	movem.l	d0-d2,(44,a0)
	lea	(_viewready,pc),a0
	move.w	#1,(a0)
	rts

_VIEWDRAW MACRO
	suba.w	#56,sp
	move.w	sr,-(sp)
	movem.l	d0-d7/a0-a1,-(sp)
	lea	(42,sp),a1
	movem.l	($7142).w,d0-d7
	movem.l	d0-d7,(a1)
	movem.l	($702a).w,d0-d2
	movem.l	d0-d2,(32,a1)
	movem.l	($7038).w,d0-d2
	movem.l	d0-d2,(44,a1)
	move.w	(_viewready,pc),d0
	beq.b	.native
	lea	(_viewpose,pc),a0
	movem.l	(a0),d0-d7
	movem.l	d0-d7,($7142).w
	movem.l	(32,a0),d0-d2
	movem.l	d0-d2,($702a).w
	movem.l	(44,a0),d0-d2
	movem.l	d0-d2,($7038).w
.native	movem.l	(sp)+,d0-d7/a0-a1
	move.w	(sp)+,ccr
\1
	jsr	0.l
	move.w	sr,-(sp)
	movem.l	d0-d7/a0,-(sp)
	lea	(38,sp),a0
	movem.l	(a0),d0-d7
	movem.l	d0-d7,($7142).w
	movem.l	(32,a0),d0-d2
	movem.l	d0-d2,($702a).w
	movem.l	(44,a0),d0-d2
	movem.l	d0-d2,($7038).w
	movem.l	(sp)+,d0-d7/a0
	move.w	(sp)+,ccr
	adda.w	#56,sp
	rts
	ENDM
_viewobjects
	_VIEWDRAW _viewobjects_call
_viewscene
	_VIEWDRAW _viewscene_call

; P6 (bit 21): door motion on the presentation timeline. The door tick (Disk.1
; $5F724) moves door vertices in the room vertex arrays ($1640..$1AEF, F5's
; fast-RAM copy when moved) by one unit per tick. Draw them at the camera's
; delayed alpha between the previous pass and this one; logic keeps them live.
DOORBYTES	= $1af0-$1640
DOORMAX		= 48			;staged words per draw; more snaps
DOORSTEP	= 8			;the 8-tick cap at one unit per tick
_doorinit
	btst	#5,(_custom1+1,pc)
	beq.b	.done
	btst	#6,(_custom1+2,pc)
	beq.b	.done
	btst	#4,(_custom1+3,pc)
	beq.b	.done
	move.w	(_attn,pc),d0
	btst	#AFB_68020,d0
	beq.b	.done
	move.l	(_restore_buffer,pc),d0
	beq.b	.done
; Chain after _viewinit's pose wrapper; leave a bypassed (RTS) entry alone.
	lea	($577be-$3cb0).l,a0
	cmpi.w	#$4ef9,(a0)
	bne.b	.done
	move.l	#$1640,d0
	btst	#0,(_f5on,pc)
	beq.b	.chip
	bsr.w	_f5datamap
.chip	lea	(_doorbase,pc),a1
	move.l	d0,(a1)
	lea	(_doordraw_call+2,pc),a1
	lea	(_doordraw,pc),a2
	lea	(_objectnative,pc),a3
	bsr.w	_viewhook
.done	rts

; At each accepted pass (from _presentgate, registers saved there).
_doorrecord
	move.l	(_doorbase,pc),d0
	beq.b	.done
	movea.l	d0,a0
	lea	(_doorprev,pc),a1
	move.w	#DOORBYTES/4-1,d0
.copy	move.l	(a0)+,(a1)+
	dbra	d0,.copy
	lea	(_doorscene,pc),a0
	move.l	($7158).w,(a0)
	lea	(_doorvalid,pc),a0
	move.w	#1,(a0)
.done	rts

_doordraw
	bsr.b	_doorstage
_doordraw_call
	jsr	0.l
	move.w	sr,-(sp)
	movem.l	d0/a0-a1,-(sp)
	bsr.w	_doorrestore
	movem.l	(sp)+,d0/a0-a1
	move.w	(sp)+,ccr
	rts

_doorstage
	move.w	sr,-(sp)
	movem.l	d0-d7/a0-a3,-(sp)
	move.w	(_doorcount,pc),d0
	bne.w	.done			;nested draw: already staged
	move.w	(_doorvalid,pc),d0
	beq.w	.done
	move.w	(_collisiononly,pc),d0
	bne.w	.done
	tst.w	($70a2).w
	bne.w	.done
	cmpi.w	#1,($7142).w
	bne.w	.done
	cmpi.w	#1,($7122).w
	bne.w	.done
	tst.w	($71cc).w		;enclosed rooms keep native drawing
	bpl.w	.done
	move.l	($7158).w,d0
	cmp.l	(_doorscene,pc),d0
	bne.w	.done
	move.w	(_viewalpha,pc),d6
	move.w	(_pstate+4,pc),d7
	cmp.w	d7,d6
	bhs.b	.done			;caught up: the live pose
	movea.l	(_doorbase,pc),a0
	lea	(_doorprev,pc),a1
	lea	(_doorsaved,pc),a2
	moveq	#DOORMAX,d4
	move.w	#DOORBYTES/4-1,d5
.scan	cmpm.l	(a1)+,(a0)+
	dbne	d5,.scan
	beq.b	.count
	subq.l	#4,a0
	subq.l	#4,a1
	bsr.b	.word
	bsr.b	.word
	dbra	d5,.scan
.count	moveq	#DOORMAX,d0
	sub.w	d4,d0
	lea	(_doorcount,pc),a0
	move.w	d0,(a0)
.done	movem.l	(sp)+,d0-d7/a0-a3
	move.w	(sp)+,ccr
	rts
; a0 live, a1 previous. A change over DOORSTEP is not door motion: snap all.
.word	move.w	(a0),d0
	move.w	(a1)+,d1
	sub.w	d1,d0
	beq.b	.same
	move.w	d0,d2
	bpl.b	.abs
	neg.w	d2
.abs	cmpi.w	#DOORSTEP,d2
	bhi.b	.snap
	subq.w	#1,d4
	bmi.b	.snap
	move.l	a0,(a2)+
	move.w	(a0),(a2)+
	muls.w	d6,d0
	divs.w	d7,d0
	add.w	d1,d0
	move.w	d0,(a0)
.same	addq.l	#2,a0
	rts
.snap	addq.l	#4,sp			;leave .word and the scan
	tst.w	d4
	bpl.b	.undo
	moveq	#0,d4
.undo	moveq	#DOORMAX,d0
	sub.w	d4,d0
	lea	(_doorcount,pc),a0
	move.w	d0,(a0)
	bsr.w	_doorrestore
	bra.b	.done

_doorrestore
	lea	(_doorcount,pc),a0
	move.w	(a0),d0
	beq.b	.done
	clr.w	(a0)
	lea	(_doorsaved,pc),a0
	subq.w	#1,d0
.next	movea.l	(a0)+,a1
	move.w	(a0)+,(a1)
	dbra	d0,.next
.done	rts

; P7 (bit 22): camera-attached models (the passenger-ship cockpit) turn with
; the camera angles. Disk.1 $57D9E, $57DD2 and $57E0C look up $7152,
; $7154+$200 and $7156+$200 as angle>>2 in the 256-entry sine table at $7E68,
; while the view matrices use 1024 steps (Disk.1 $5A91E), so the cockpit
; swung by (angle & 3) and snapped back. Interpolate the table instead.
; Per site: replaced code, its first long, the wrapper, the rotation after
; the replaced code and the original beq's target (no rotation).
_cockpitsites
	dc.l	$57d9e-$3cb0,$7e003e38
	dc.w	_angle7152-_cockpitsites,$57db4-$57d9e,$57dd2-$57d9e
	dc.l	$57dd2-$3cb0,$30387154
	dc.w	_angle7154-_cockpitsites,$57dee-$57dd2,$57e0c-$57dd2
	dc.l	$57e0c-$3cb0,$30387156
	dc.w	_angle7156-_cockpitsites,$57e28-$57e0c,$57e46-$57e0c
	dc.l	0
_cockpitinit
	btst	#6,(_custom1+1,pc)
	beq.b	.done
	lea	(_cockpitsites,pc),a3
.site	move.l	(a3),d0
	beq.b	.done
	bsr.b	.patch
	move.l	(_render_base,pc),d6
	beq.b	.next
	move.l	(a3),d0
	moveq	#0,d3
	move.w	(12,a3),d3
	add.l	d3,d0
	bsr.w	_rendermap		;clobbers d1/d2/a2
	move.l	d0,d4
	move.l	(a3),d0
	bsr.w	_rendermap
	cmp.l	(a3),d0
	beq.b	.next			;not copied
	sub.l	d0,d4
	cmp.l	d3,d4
	bne.b	.next			;copy changed the layout: keep native
	bsr.b	.patch
.next	lea	(14,a3),a3
	bra.b	.site
.done	rts
.patch	movea.l	d0,a0
	move.l	(4,a3),d1
	cmp.l	(a0),d1
	bne.b	.skip
	move.w	#$4eb9,(a0)+
	lea	(_cockpitsites,pc),a1
	adda.w	(8,a3),a1
	move.l	a1,(a0)+
	move.w	(10,a3),d1		;bra.b from the call's return to the rotation
	subq.w	#8,d1
	ori.w	#$6000,d1
	move.w	d1,(a0)
.skip	rts

; Each returns d7/a4 as the replaced code (a4 at sin, ($80,a4) cos) and the
; same d0; at angle 0 it returns past the rotation, as natively.
_angle7152
	move.l	d0,-(sp)
	bsr.w	_camcheck
	bne.b	.exact
	move.w	($7152).w,d0
	bsr.b	_fineangle
	movem.l	(sp)+,d0
	bne.b	.done
	addi.l	#$57dd2-($57d9e+6),(sp)
.done	rts
.exact	bsr.w	_camvertexexact		;P8: instead of the rotation and $5B038
	move.l	(sp)+,d0
	addi.l	#$57f90-($57d9e+6),(sp)
	rts
_angle7154
	move.w	($7154).w,d0
	addi.w	#$200,d0
	bsr.b	_fineangle
	bne.b	.done
	addi.l	#$57e0c-($57dd2+6),(sp)
.done	rts
_angle7156
	move.w	($7156).w,d0
	addi.w	#$200,d0
	bsr.b	_fineangle
	bne.b	.done
	addi.l	#$57e46-($57e0c+6),(sp)
.done	rts
; d0: angle in 1024 units. Z set (d7 = 0) at angle 0.
_fineangle
	move.w	d0,d7
	andi.w	#$3ff,d7
	beq.b	.done
	movem.l	d1-d2,-(sp)
	bsr.w	_finesc
	lea	(_cockpitrot,pc),a4
	move.w	d1,(a4)
	move.w	d2,($80,a4)
	movem.l	(sp)+,d1-d2
	move.l	a4,d7
.done	rts
; d0: angle in 1024 units -> d1 sine, d2 cosine ($7E68 interpolated).
_finesc
	movem.l	d3/a0/a4,-(sp)
	move.w	d0,d3
	andi.w	#3,d3
	move.w	d0,d1
	lsr.w	#1,d1
	andi.w	#$1fe,d1
	lea	($7e68).w,a0
	lea	(a0,d1.w),a4
	addq.w	#2,d1
	andi.w	#$1fe,d1
	adda.w	d1,a0
	move.w	(a0),d1
	sub.w	(a4),d1
	muls.w	d3,d1
	asr.l	#2,d1
	add.w	(a4),d1
	move.w	($80,a0),d2
	sub.w	($80,a4),d2
	muls.w	d3,d2
	asr.l	#2,d2
	add.w	($80,a4),d2
	movem.l	(sp)+,d3/a0/a4
	rts
_cockpitrot	ds.w	65

; P8 (bit 23): camera-attached vertices without the logarithmic transform.
; The view transform (Disk.1 $5B038) multiplies through log tables, about
; 0.1-0.2% per term, so the cockpit (turned by the camera angles, then back
; by the view) moved a pixel and back as the angles changed. The view is the
; inverse model rotation with camera axes (depth, -x, -y), so the vertex is
; exact in camera space: (z, -x, -y) plus the offset a1-a3 turned back by
; heading, pitch and roll. _angle7152 (reached only by these models) writes
; what the rotation and $5B038 would, then returns to Disk.1 $57F90: depth, x and y
; ($840/$340/$5C0), the screen position (floats $AC0/$D40, words $FC0/$FC2)
; and the clip code ($1240, via $77DA), or $80 behind the camera. Floats are
; a normalised mantissa (|m| $1000..$1FFE, even) times 2^(exponent-12).
_caminit
	btst	#7,(_custom1+1,pc)
	beq.b	.done
	btst	#6,(_custom1+1,pc)
	beq.b	.done
	move.w	(_attn,pc),d0
	btst	#AFB_68020,d0
	beq.b	.done
	btst	#0,(_f5on,pc)
	beq.b	.chip
	lea	(_camout,pc),a3
	moveq	#8-1,d3
.map	move.l	(a3),d0
	bsr.w	_f5datamap
	move.l	d0,(a3)+
	dbra	d3,.map
.chip	lea	($57d9e-$3cb0).l,a0
	bsr.b	.patched
	bne.b	.done
	move.l	(_render_base,pc),d6
	beq.b	.on
	move.l	#$57d9e-$3cb0,d0
	bsr.w	_rendermap
	cmpi.l	#$57d9e-$3cb0,d0
	beq.b	.on			;not copied
	move.l	d0,d3
	movea.l	d0,a0
	bsr.b	.patched
	bne.b	.on			;the copy keeps the native rotation
	move.l	#$57f90-$3cb0,d0
	bsr.w	_rendermap
	sub.l	d3,d0
	cmpi.l	#$57f90-$57d9e,d0
	bne.b	.done			;copy layout changed
.on	lea	(_camexact,pc),a0
	st	(a0)
.done	rts
; a0: a $57D9E instance. Z set when P7 replaced it with _angle7152.
.patched
	cmpi.w	#$4eb9,(a0)
	bne.b	.native
	lea	(_angle7152,pc),a1
	cmpa.l	(2,a0),a1
	bne.b	.native
	moveq	#0,d0
	rts
.native	moveq	#1,d0
	rts

; From _angle7152 (d0 saved there). Z clear: transform this vertex exactly.
_camcheck
	move.b	(_camexact,pc),d0
	beq.b	.no
	cmpi.w	#1,($7122).w		;$5B038's other transforms
	beq.b	.no
	tst.w	($7124).w
	bmi.b	.no
	tst.w	($6ff6).w		;projection scale: a power of two
	bne.b	.no
	cmpi.w	#20,($6ff4).w
	bhi.b	.no
	move.l	a1,d0			;offset within 1024: Q4 words below
	bsr.b	.range
	bhs.b	.no
	move.l	a2,d0
	bsr.b	.range
	bhs.b	.no
	move.l	a3,d0
	bsr.b	.range
	bhs.b	.no
	moveq	#1,d0
	rts
.no	moveq	#0,d0
	rts
.range	addi.l	#1024,d0
	cmpi.l	#2048,d0
	rts

	machine	68020
; d3-d5: model vertex, a1-a3: offset, a0: vertex index.
_camvertexexact
	movem.l	d0-d7/a1-a4,-(sp)
	lea	(_camkey,pc),a4
	cmpa.l	(a4),a1
	bne.w	.offset
	cmpa.l	(4,a4),a2
	bne.w	.offset
	cmpa.l	(8,a4),a3
	bne.w	.offset
	move.l	($7152).w,d0
	cmp.l	(12,a4),d0
	bne.w	.offset
	move.w	($7156).w,d0
	cmp.w	(16,a4),d0
	beq.w	.vertex
.offset	movem.l	d3-d5,-(sp)
	move.l	a1,(a4)
	move.l	a2,(4,a4)
	move.l	a3,(8,a4)
	move.l	($7152).w,(12,a4)
	move.w	($7156).w,(16,a4)
	move.l	a1,d3
	asl.l	#4,d3
	move.l	a3,d4
	asl.l	#4,d4
	move.w	($7156).w,d0
	addi.w	#$200,d0
	bsr.w	.turn			;d3 X, d4 Z
	move.l	d3,d7
	move.l	d4,d3
	move.l	a2,d4
	asl.l	#4,d4
	move.w	($7154).w,d0
	addi.w	#$200,d0
	bsr.w	.turn			;d3 Z, d4 Y
	move.l	d3,(18,a4)
	move.l	d7,d3
	move.w	($7152).w,d0
	bsr.w	.turn			;d3 X, d4 Y
	neg.l	d3
	neg.l	d4
	move.l	d3,(22,a4)
	move.l	d4,(26,a4)
	movem.l	(sp)+,d3-d5
.vertex	movem.l	(18,a4),d0-d2		;offset in camera space, Q4
	ext.l	d5
	asl.l	#4,d5
	add.l	d5,d0			;depth
	ext.l	d3
	asl.l	#4,d3
	sub.l	d3,d1			;x
	ext.l	d4
	asl.l	#4,d4
	sub.l	d4,d2			;y
	lea	(_camout,pc),a3
	movea.l	d0,a1
	bsr.w	.float
	movea.l	(a3),a2
	move.l	d0,(a2,a0.l)		;$840
	move.l	d1,d0
	bsr.w	.float
	movea.l	(4,a3),a2
	move.l	d0,(a2,a0.l)		;$340
	move.l	d2,d0
	bsr.w	.float
	movea.l	(8,a3),a2
	move.l	d0,(a2,a0.l)		;$5C0
	move.l	a1,d7			;depth
	ble.w	.behind
	moveq	#4,d0
	add.w	($6ff4).w,d0
	moveq	#1,d6
	lsl.l	d0,d6			;screen scale, Q4
	move.l	d1,d0
	muls.l	d6,d3:d0
	divs.l	d7,d3:d0
	bvs.w	.behind
	move.l	#160*16,d1
	sub.l	d0,d1
	bvs.w	.behind
	move.l	d2,d0
	muls.l	d6,d3:d0
	divs.l	d7,d3:d0
	bvs.w	.behind
	move.l	#68*16,d2
	add.l	d0,d2
	bvs.w	.behind
	move.l	d1,d0
	bsr.w	.float
	movea.l	(12,a3),a2
	move.l	d0,(a2,a0.l)		;$AC0
	move.l	d2,d0
	bsr.w	.float
	movea.l	(16,a3),a2
	move.l	d0,(a2,a0.l)		;$D40
	move.l	d1,d0
	bsr.w	.screen
	movea.l	(20,a3),a2
	move.w	d0,(a2,a0.l)		;$FC0
	move.w	d0,d1
	move.l	d2,d0
	bsr.w	.screen
	movea.l	(24,a3),a2
	move.w	d0,(a2,a0.l)		;$FC2
	moveq	#0,d2
	cmpi.w	#$140,d1
	blo.w	.x
	addq.w	#1,d2
	tst.w	d1
	bpl.w	.x
	addq.w	#4,d2
.x	cmpi.w	#$88,d0
	blo.w	.y
	addq.w	#2,d2
	tst.w	d0
	bpl.w	.y
	addq.w	#8,d2
.y	lea	($77da).l,a4
	movea.l	(28,a3),a2
	move.b	(a4,d2.w),(a2,a0.l)	;$1240
	movem.l	(sp)+,d0-d7/a1-a4
	rts
.behind	movea.l	(28,a3),a2
	move.b	#$80,(a2,a0.l)
	movem.l	(sp)+,d0-d7/a1-a4
	rts
; d0: Q4 -> nearest word, saturated.
.screen	addq.l	#8,d0
	asr.l	#4,d0
	cmpi.l	#$7fff,d0
	ble.w	.lo
	move.w	#$7fff,d0
	rts
.lo	cmpi.l	#-$8000,d0
	bge.w	.in
	move.w	#$8000,d0
.in	rts
; d0: Q4 long -> game float.
.float	movem.l	d1-d2,-(sp)
	tst.l	d0
	beq.w	.zero
	smi	d2
	bpl.w	.pos
	neg.l	d0
.pos	bfffo	d0{0:32},d1
	neg.l	d1
	addi.l	#31-12,d1		;shift that puts the top bit at bit 12
	bmi.w	.left
	lsr.l	d1,d0
	bra.w	.norm
.left	neg.l	d1
	lsl.l	d1,d0
	neg.l	d1
.norm	andi.w	#$fffe,d0
	tst.b	d2
	beq.w	.sign
	neg.w	d0
.sign	addi.w	#12-4,d1
	swap	d1
	move.w	d0,d1
	move.l	d1,d0
	movem.l	(sp)+,d1-d2
	rts
.zero	move.l	#$fff01000,d0
	movem.l	(sp)+,d1-d2
	rts
; d3 a, d4 b, d0 angle -> d3 a*cos - b*sin, d4 b*cos + a*sin (Q15, rounded).
.turn	movem.l	d1-d2/d5-d6,-(sp)
	bsr.w	_finesc
	move.w	d3,d5
	muls.w	d2,d5
	move.w	d4,d6
	muls.w	d1,d6
	sub.l	d6,d5
	muls.w	d2,d4
	muls.w	d1,d3
	add.l	d3,d4
	move.l	d5,d3
	moveq	#15,d6
	addi.l	#$4000,d3
	asr.l	d6,d3
	addi.l	#$4000,d4
	asr.l	d6,d4
	movem.l	(sp)+,d1-d2/d5-d6
	rts
	machine	68000
; Offset, $7152/$7154 and $7156 of the cached turn, then the result.
_camkey		dc.l	$80000000,0,0,0
		dc.w	0
_camoffset	dc.l	0,0,0
; The vertex outputs; F5 moves them with the scratch.
_camout		dc.l	$840,$340,$5c0,$ac0,$d40,$fc0,$fc2,$1240
_camexact	dc.b	0
	even

_doorbase	dc.l	0
_doorscene	dc.l	0
_doorvalid	dc.w	0
_doorcount	dc.w	0
_doorsaved	ds.b	DOORMAX*6
_doorprev	ds.l	DOORBYTES/4


_interpolateplayer
	move.w	(_pstate+2,pc),d0
	beq.w	.done
	tst.w	($71cc).w
	bpl.w	.done
	lea	(_previous,pc),a0
	lea	($7142).w,a1
	move.l	(a1),d0
	cmp.l	(a0),d0
	bne.w	.done
; Floor, scene and model changes snap instead of blending coordinate systems.
	move.l	(22,a1),d0
	cmp.l	(22,a0),d0
	bne.w	.done
	move.l	(24,a1),d0
	cmp.l	(24,a0),d0
	bne.w	.done
	sub.w	d7,d6
	cmpi.w	#1,(a1)
	bne.b	.vehicle
; Walking: height changes over 1024 (lift arrivals) snap. A taxi carries the
; player up to 8,200 units per pass horizontally (Disk.1 $5562A).
	move.l	(8,a1),d0
	sub.l	(8,a0),d0
	bpl.b	.height
	neg.l	d0
.height	cmpi.l	#1024,d0
	bgt.w	.done
	move.l	#16383,d3
	bra.b	.limit
.vehicle
	btst	#4,(_custom1+2,pc)
	beq.w	.done
	move.l	#32767,d3
.limit	moveq	#2,d5
	moveq	#4,d4
.validate
	move.l	(a1,d4.w),d0
	sub.l	(a0,d4.w),d0
	asl.l	#4,d0
	asr.l	#4,d0
	cmp.l	d3,d0
	bgt.w	.done
	neg.l	d0
	cmp.l	d3,d0
	bgt.w	.done
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
; Bit 16: room walls use separate local XYZ words. Apply the same delta,
; retaining the native room origin and the existing discontinuity guards.
	cmpi.w	#1,(a1)
	bne.b	.spaceposition
	btst	#0,(_custom1+1,pc)
	beq.b	.next
	lea	($7034).w,a2
	add.w	d0,(a2,d4.w)
	bra.b	.next
.spaceposition
	cmpi.w	#2,(a1)
	bne.b	.next
	lea	($7026).w,a2
	add.l	d0,(a2,d4.w)
.next	addq.w	#4,d4
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
.done	rts

; P1 uses its own gate so disabled options retain L1's measured path.
_presentgate
	move.w	sr,-(sp)
	movem.l	d0-d7/a0-a6,-(sp)
	lea	(_viewready,pc),a0
	clr.w	(a0)
	lea	(_pstate,pc),a5
; $70A2: the game replays recorded input from $709A (a passenger flight). With
; presentations or interpolated objects the flight leaves the recording's course,
; so replay keeps native drawing, paced by bit 24 (_replaygate).
	tst.w	($70a2).w
	beq.b	.live
	bsr.w	_replaygate
	bra.w	.other
.live
	move.w	($7142).w,d0
	cmp.w	($7122).w,d0
	bne.w	.other
	cmpi.w	#1,d0
	beq.b	.modeok
	btst	#4,(_custom1+2,pc)
	beq.w	.other
	cmpi.w	#2,d0
	bhi.w	.other
.modeok
; Reset velocity history on boarding, leaving, or changing coordinate systems.
	cmp.w	(_previous,pc),d0
	bne.b	.first
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
.screen	tst.w	($71cc).w		; enclosed rooms keep their native drawing path
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
	bsr.w	_doorrecord
	bra.b	.done
.other	clr.w	(2,a5)
	lea	(_doorvalid,pc),a0
	clr.w	(a0)
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
	bsr.w	_publishedview
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
	btst	#6,(_custom1+2,pc)
	beq.b	.predict
	lea	(_viewready,pc),a0
	move.w	#1,(a0)
	bra.w	.draw
.predict
; Never extrapolate a transport, floor, scene or coordinate-system change.
	btst	#4,(_custom1+2,pc)
	beq.b	.walkcollision
	lea	(_previous,pc),a0
	move.l	($7142).w,d0
	cmp.l	(a0),d0
	bne.w	.draw
	move.l	($7158).w,d0
	cmp.l	(22,a0),d0
	bne.w	.draw
	move.l	($715a).w,d0
	cmp.l	(24,a0),d0
	bne.w	.draw
	cmpi.w	#2,($7142).w
	beq.b	.velocity
	tst.w	($6f56).w
	bmi.w	.draw
	tst.w	($7142).w
	beq.b	.velocity
; Walking collision rollback suppresses extrapolation.
.walkcollision
	tst.w	($70e2).w
	bne.w	.draw
	tst.w	($6f56).w
	bmi.w	.draw
	tst.w	($71cc).w
	bpl.w	.draw
.velocity
	lea	(_previous,pc),a0
	lea	($7142).w,a1
	move.w	(_pstate+4,pc),d7
; Reject discontinuities before staging any position. 28-bit X/Z wrap.
; Walking: height over 1024 (lift arrivals) snaps; taxis move up to 8,200.
	move.l	#32767,d3
	cmpi.w	#1,($7142).w
	bne.b	.limit
	move.l	(8,a1),d0
	sub.l	(8,a0),d0
	bpl.b	.height
	neg.l	d0
.height	cmpi.l	#1024,d0
	bgt.w	.draw
	move.l	#16383,d3
.limit
	moveq	#2,d5
	moveq	#4,d4
.validate
	move.l	(a1,d4.w),d0
	sub.l	(a0,d4.w),d0
	asl.l	#4,d0
	asr.l	#4,d0
	cmp.l	d3,d0
	bgt.w	.draw
	neg.l	d0
	cmp.l	d3,d0
	bgt.w	.draw
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
	cmpi.w	#2,($7142).w
	bne.b	.nextposition
; Space bodies use the navigation pose, in the same coordinates as the player.
	lea	($7026).w,a2
	add.l	d0,(a2,d4.w)
.nextposition
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
	cmpi.w	#1,($7142).w
	bne.w	.transport
	jsr	($59b94).l		; camera, Disk.1 $5D844
; Disk.1 $5E0BA is inline, not a callable routine: derive sky heading.
	move.w	($70b4).w,d0
	movea.l	($713a).w,a1
	add.w	($575a,a1),d0
	andi.w	#$3ff,d0
_f3sky2	equ	*
	move.w	d0,($42c6c).l
	jsr	($59da0).l		; Disk.1 $5DA50
	jsr	($56c6e).l		; Disk.1 $5A91E
; Every native path draws the sights into the finished frame before publishing it.
	jsr	($5213e).l		; sights, Disk.1 $55DEE
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
	btst	#6,(_custom1+2,pc)
	beq.b	.nobuildings
	bsr.w	_drawbuildings		; drawing tail only, Disk.1 $5AEDA
.nobuildings
	jsr	($556f6).l		; Disk.1 $593A6
	jsr	($572fa).l		; Disk.1 $5AFAA
	jsr	($53b0e).l		; Disk.1 $577BE
	bra.w	.restore
.transport
	bsr.w	_presenttransport
.restore
	lea	(_viewready,pc),a0
	clr.w	(a0)
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

; P3: redraw the native vehicle/flight view without its simulation or collision.
; Disk.1 $5E280..$5E3BA (surface) and $5E3CE..$5E440 (space).
_presenttransport
	cmpi.w	#2,($7142).w
	beq.w	.space
	move.w	($714e).w,d1
	asr.w	#2,d1
	addi.w	#256,d1
	andi.w	#$3ff,d1
	move.w	d1,($70b8).w
_f3sky3	equ	*
	move.w	d1,($42c70).l
	move.w	($7146).w,d0
	asr.w	#2,d0
	andi.w	#$3ff,d0
	move.w	d0,($70b4).w
	movea.l	($713a).w,a1
	add.w	($575a,a1),d0
	andi.w	#$3ff,d0
_f3sky4	equ	*
	move.w	d0,($42c6c).l
	jsr	($59b94).l
	jsr	($59da0).l
	jsr	($5213e).l		; sights, Disk.1 $55DEE
	jsr	($5a7a8).l
	jsr	($5ab90).l
	jsr	($56c6e).l
	jsr	($42d14).l
	jsr	($42d18).l
	lea	($2ea40).l,a0
	move.w	#$556,($10,a0)
	move.w	#$445,($12,a0)
	move.w	#$334,($14,a0)
	move.w	#$640,($16,a0)
	movea.l	($72b4).w,a0
	move.w	($7324).w,($10,a0)
	move.w	($7186).w,($1c,a0)
	move.w	#$88a,($1a,a0)
	tst.w	($6f56).w
	bne.b	.interior
	tst.w	($713e).w
	beq.b	.interior
	move.w	($70b0).w,($20,a0)
	move.w	#$caa,($1e,a0)
	jsr	($5045e).l
	jsr	($539ae).l
	bra.b	.objects
.interior
	move.w	($70b0).w,d0
	tst.w	($6f56).w
	bne.b	.colour
	tst.w	($70c6).w
	beq.b	.setcolour
.colour	move.w	($7326).w,d0
.setcolour
	move.w	d0,($1e,a0)
	jsr	($502a2).l
	jsr	($539ae).l
	jsr	($5a864).l
.objects
	btst	#6,(_custom1+2,pc)
	beq.b	.nobuildings
	bsr.w	_drawbuildings
.nobuildings
	jsr	($556f6).l
	tst.w	($70c6).w
	bne.b	.models
	jsr	($572fa).l
.models	jmp	($53b0e).l
.space
	jsr	($59ba0).l
	jsr	($56c6e).l
	jsr	($42d14).l
	jsr	($5213e).l		; sights, Disk.1 $55DEE
	jsr	($5a7a8).l
	lea	($2ea40).l,a0
	move.w	#$444,($10,a0)
	move.w	#$333,($12,a0)
	move.w	#$222,($14,a0)
	move.w	#$740,($16,a0)
	movea.l	($72b4).w,a0
	move.w	#2,($10,a0)
	move.w	#$eee,($1e,a0)
	move.w	#$822,($1c,a0)
	move.w	#$666,($1a,a0)
	jsr	($5ab90).l
	jsr	($50524).l
; Disk.1 $57374 has no chip entry jump under F5 (bit 20): its chip original reads the
; vacated scratch and drew a full-view frame of one colour. Call through the native
; operand (Disk.1 $5E42C), which F2/F5 retarget to the copy.
	movea.l	($5e42c-$3cb0).l,a0
	jsr	(a0)
	jmp	($53b0e).l

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
	dc.w	$ff
	dc.l	$5330
	dc.w	$0
	dc.l	$6f48
	dc.w	0
	dc.l	$6f32
	dc.w	$0
	dc.l	$6fae
	dc.w	$5
	dc.l	$700e
	dc.w	$5
	dc.l	$702a
	dc.w	$5
; Room-local camera words changed only during presentation (bit 16).
	dc.l	$7038
	dc.w	0
	dc.l	$703c
	dc.w	0
	dc.l	$7040
	dc.w	0
	dc.l	$704a
	dc.w	$3
	dc.l	$7084
	dc.w	$3
	dc.l	$70b4
	dc.w	$2
	dc.l	$70be
	dc.w	$0
	dc.l	$70c2
	dc.w	$7
	dc.l	$7122
	dc.w	$2f
	dc.l	$7182
	dc.w	$0
	dc.l	$719e
	dc.w	$0
	dc.l	$71a2
	dc.w	$0
	dc.l	$71ae
	dc.w	$1d
	dc.l	$7220
	dc.w	$5
	dc.l	$727c
	dc.w	$0
	dc.l	$72ae
	dc.w	$0
	dc.l	$aa6e
	dc.w	$457
	dc.l	$b31e
	dc.w	$0
	dc.l	$b364
	dc.w	$0
	dc.l	$505e2
	dc.w	$1f
	dc.l	$354e2
	dc.w	$8
_restore_projection
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
_restore_clip	dc.l	0
	dc.w	0
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
	dc.l	WHDLTAG_CUSTOM5_GET
_enhanced	dc.l	0
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
