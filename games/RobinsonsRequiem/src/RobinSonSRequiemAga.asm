
; active crack
PRESTIGE_CRACK
;_FlashHunk

;--------------------------------------------------------------------------
;  :Modul.      kick31.asm
;  :Contents.   kickstart 1.3 booter example
;  :Author.     Wepl
;  :Original.
;  :Version.    $Id: kick13.asm 1.8 2004/01/18 13:29:40 wepl Exp wepl $
;  :History.    19.10.99 started
;               20.09.01 ready for JOTD ;)
;               23.07.02 RUN patch added
;               04.03.03 full caches
;               20.06.03 rework for whdload v16
;  :Requires.   -
;  :Copyright.  Public Domain
;  :Language.   68000 Assembler
;  :Translator. Barfly V2.9
;  :To Do.
;---------------------------------------------------------------------------*

        INCDIR  Includes:
        INCLUDE whdload.i
       INCLUDE whdmacros.i
       INCLUDE lvo/dos.i
       INCLUDE lvo/intuition.i
       INCLUDE intuition/screens.i

        IFD BARFLY
        OUTPUT  "RobinsonSRequiemAga.Slave"
        BOPT    O+                              ;enable optimizing
        BOPT    OG+                             ;enable optimizing
        BOPT    ODd-                            ;disable mul optimizing
        BOPT    ODe-                            ;disable mul optimizing
        BOPT    w4-                             ;disable 64k warnings
        BOPT    wo-                             ;disable optimize warnings
        SUPER
        ENDC

;============================================================================

CHIPMEMSIZE     = $1A0000
; 1 MB of fast memory besides the Kickstart, for START's fast pool (_fastpool). MemConfig=1
; (slv_MemConfig) is CFou!'s v1.2 layout, 256 KB: the pool is then left out and the game
; runs from chip memory as before.
FASTMEMSIZE     = $100000
FASTMEMSIZE_V12 = $40000
NUMDRIVES       = 1
WPDRIVES        = %1111

;BLACKSCREEN
;BOOTBLOCK
;BOOTEARLY
BOOTDOS
;CBDOSLOADSEG
;CBDOSREAD
; BaseMem write-through instead of v1.2's CACHE (non-cacheable): the caches stay on without
; WHDLoad's MMU, the 68030's default. The game's only blitter use copies the shown planes into
; the back planes (hunk 2 +$5b6), which the CPU only writes.
CACHECHIPDATA
;DEBUG
;DISKSONBOOT
;DOSASSIGN
;FONTHEIGHT     = 8
HDINIT
;HRTMON
IOCACHE         = 11000
INITAGA
;MEMFREE        = $100
;NEEDFPU
;POINTERTICKS   = 1
;SETPATCH
STACKSIZE      = 6000
;TRDCHANGEDISK

;============================================================================

slv_Version     = 20
slv_Flags       = WHDLF_NoError|WHDLF_Examine|WHDLF_ReqAGA|WHDLF_ClearMem
slv_keyexit     = $59   ;F10

;============================================================================

        INCLUDE whdload/kick31.s

;============================================================================

        IFD BARFLY
        IFND    .passchk
        DOSCMD  "WDate  >T:date"
.passchk
        ENDC
        ENDC

slv_CurrentDir  dc.b    "data-aga",0
slv_name        dc.b    "Robinson Requiem AGA",0
slv_copy        dc.b    "Silmarils",0
slv_info        dc.b    "Coded By CFou!, improved by Vesuri",10
                dc.b    "Version 2.0b (17.11.2026) "
        IFD BARFLY
                INCBIN  "T:date"
        ENDC
                dc.b    0
                dc.b    "$VER: RobinsonSRequiemAga.Slave 2.0b (17.11.2026)",0
slv_config	dc.b	"C2:B:Enhanced framerate;"
		dc.b	"C1:L:Movement speed:Original,1X (ECS),2X (AGA);"
		dc.b	"C3:B:Smooth landscape;",0
        EVEN
slv_MemConfig   dc.l    CHIPMEMSIZE,KICKSIZE+FASTMEMSIZE_V12
                dc.l    0


;********************************************************
;********************************************************
;********************************************************
;******************* fix GFX bug with fast memory
; as main AGA silmarils game
; code try to take intuituion bitplan adress to preserve memory
; 
; move.l	_intuitionBase,a0
; move.l	$38(a0),a1
; move.l	$c0(a1),a0	=>BPL1ADR of intuition screen
; but it's do'nt work on Kick31 => fast adress is return for BPl1ADR and Game use it for  first BitPlans
;********************************************************
_ChipSCRLg	=$3e80*3		;  but 1 more for security
_ChipSCRAbs	=CHIPMEMSIZE-$10000

_NoEnoughMem	dc.b "No enough chip memory in KickEmul",0
	even
_ADR_RESERVE_chip	dc.l	0
;********************************************************

_TakeChipBPL1AdrFix
	move.l	_ADR_RESERVE_chip(pc),d1
	RTS
;********************************************************

_TakeChipBPL1AdrFixPrep
	movem.l	d0-a6,-(a7)
        LSL.L   #2,D0
        MOVE.L  D0,A0
	IFD _FlashHunk
.t1
	move.w	#$f0,$dff180
	btst	#6,$bfe001
	bne	.t1
	ENDC

	CMP.L	#$222800C0,$456(A0)	; move.l	$c0(a0),d1 ; take Intuition BPL1ADR
	bne .nofound
	move.l	#$4EB80106,$456(a0)
	pea _TakeChipBPL1AdrFix(pc)
	move.w #$4EF9,$106
	move.l	(a7)+,$106+2

;	move.l 4,a6
;	MOVE.L #$3E80*2,D0	; reserve  first BitPLan for game
;	MOVE.L #$10002,D1	; CLEAR & CHIP
;	JSR -198(A6)		; AllocMem		; gfx bug game use it without allocation!!!


	move.l 4,a6
	move.l	#_ChipSCRAbs,a1
	MOVE.L #_ChipSCRLg,D0	; reserve  first 2 BitPLans for game (1 more by security
	JSR -204(A6)		; AllocAbs
	CMP.L	#_ChipSCRAbs+_ChipSCRLg,A0
	beq .ok

; error quit
        move.l  (_resload,pc),a2           ;A2 = resload
	PEA	_NoEnoughMem(pc)
        pea     TDREASON_FAILMSG
        jmp     (resload_Abort,a2)
.ok
	LEA _ADR_RESERVE_chip(PC),A1
	MOVE.L #_ChipSCRAbs,(A1)

.nofound
	movem.l	(a7)+,d0-a6
	rts
;********************************************************
;********************************************************
;********************************************************

; The bitplanes on 8-byte boundaries. START sets FMODE 3 (hunk 0 +$710), which fetches the
; planes 64 bits at a time: each plane's address must be a multiple of 8, or every line is
; fetched from the boundary below it. Its own planes come from AllocMem (CHIP|CLEAR), which
; guarantees only 4: the six at hunk 0 +$5ba (96,000 bytes, the pointers at hunk 1 +$13e
; to +$152) and the eighth at +$4ba (8,000 bytes, hunk 1 +$b6). Each call's 16 bytes,
; +$5c0-+$5cf and +$4c0-+$4cf (movem.l a6 / movea.l 4,a6 / jsr -198(a6) / movem.l), become
; jsr _planealloc and bra.s to the store after them, checked first. START never frees
; them. The first two planes are CFou!'s block at _ChipSCRAbs, already aligned. On every
; CPU, also without Enhanced framerate: a fix of v1.2's display on real AGA machines.
; a1 START's segment list (its first hunk's link).

_planepatch
        movem.l d0-d1/a0-a2,-(a7)
        lea     4(a1),a0                ; hunk 0
        lea     $5ba(a0),a1
        cmp.l   #$203c0001,(a1)         ; move.l #96000,d0
        bne     .x
        cmp.w   #$7700,4(a1)
        bne     .x
        lea     $4ba(a0),a1
        cmp.l   #$203c0000,(a1)         ; move.l #8000,d0
        bne     .x
        cmp.w   #$1f40,4(a1)
        bne     .x
        lea     $5c0(a0),a1
        bsr     .site
        bne     .x
        lea     $4c0(a0),a1
        bsr     .site
        bne     .x
        lea     $5c0(a0),a1
        bsr     .set
        lea     $4c0(a0),a1
        bsr     .set
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.x      movem.l (a7)+,d0-d1/a0-a2
        rts
.site   cmp.l   #$48e70002,(a1)         ; movem.l a6,-(sp)
        bne     .r
        cmp.l   #$2c780004,4(a1)        ; movea.l 4.w,a6
        bne     .r
        cmp.l   #$4eaeff3a,8(a1)        ; jsr _LVOAllocMem(a6)
        bne     .r
        cmp.l   #$4cdf4000,12(a1)       ; movem.l (sp)+,a6
.r      rts
.set    move.w  #$4eb9,(a1)+            ; jsr _planealloc
        pea     _planealloc(pc)
        move.l  (a7)+,(a1)+
        move.w  #$6008,(a1)             ; bra.s past the call's 16 bytes
        rts

; START's AllocMem for its planes (d0 the size, d1 the requirements): 8 bytes more, the
; address rounded up to a multiple of 8; 0 if none.
_planealloc
        move.l  a6,-(a7)
        addq.l  #8,d0
        move.l  4.w,a6
        jsr     _LVOAllocMem(a6)
        move.l  (a7)+,a6
        tst.l   d0
        beq.s   .x
        addq.l  #7,d0
        and.w   #-8,d0
.x      rts


;============================================================================
; like a program from "startup-sequence" executed, full dos process,
; HDINIT is required

; the following example is extensive because it saves all registers and
;   restores them before executing the program, the reason for this that some
;   programs (e.g. MANX Aztec-C) require specific registers properly setup on
;   calling
; in most cases a simpler routine is sufficient :-)

        IFD BOOTDOS

_bootdos        lea     (_saveregs,pc),a0
                movem.l d1-d6/a2-a6,(a0)
                move.l  (a7)+,(44,a0)


;
         bra _patch
_cont

    ;open doslib
                lea     (_dosname,pc),a1
                move.l  (4),a6
                jsr     (_LVOOldOpenLibrary,a6)
                lea     (_dosbase,pc),a0
                move.l  d0,(a0)
                move.l  d0,a6                   ;A6 = dosbase


        ;assigns
            ;    lea     (_disk1,pc),a0
            ;    sub.l   a1,a1
            ;    bsr     _dos_assign

        ;check version
                lea     (_program,pc),a0
                move.l  a0,d1
                move.l  #MODE_OLDFILE,d2
                jsr     (_LVOOpen,a6)
                move.l  d0,d1
                beq     .end
                move.l  #300,d3
                sub.l   d3,a7
                move.l  a7,d2
                jsr     (_LVORead,a6)
                move.l  d3,d0
                move.l  a7,a0
                move.l  (_resload,pc),a2
                jsr     (resload_CRC16,a2)
                add.l   d3,a7
                
                cmp.w   #$dd8e,d0
                beq     .versionok
;                pea     TDREASON_WRONGVER
;                jmp     (resload_Abort,a2)
.versionok
           ;blitz


        ;load exe
                lea     (_program,pc),a0
                move.l  a0,d1
                jsr     (_LVOLoadSeg,a6)
                move.l  d0,d7                   ;D7 = segment
                beq     .end

        ;patch
                lea     (_pl_program,pc),a0
                move.l  d7,a1
                jsr     (resload_PatchSeg,a2)

        IFD DEBUG
        ;set debug
                clr.l   -(a7)
                move.l  d7,-(a7)
                pea     WHDLTAG_DBGSEG_SET
                move.l  a7,a0
                jsr     (resload_Control,a2)
                add.w   #12,a7
        ENDC



                move.l  d7,d0
		bsr _TakeChipBPL1AdrFixPrep
            move.l  d7,a1
            add.l   a1,a1
            add.l   a1,a1
            bsr _planepatch


;******************** PRESTIGE_CRACKDEB
   IFD PRESTIGE_CRACK
            move.l  d7,a1
            add.l   a1,a1
            add.l   a1,a1
            bsr _crackPRESTIGE
   ENDC
;******************** PRESTIGE_CRACKFIN

   IFD DEVELOPER
            move.l  d7,a1
            add.l   a1,a1
            add.l   a1,a1
            bsr _directstart
   ENDC

   IFD PROFILE
            move.l  d7,a1
            add.l   a1,a1
            add.l   a1,a1
            bsr _framecount
   ENDC
            move.l  d7,a1
            add.l   a1,a1
            add.l   a1,a1
            bsr _hunks
            bsr _enhget
            beq .orig
            bsr _fastpool
            bsr _fastblocks
            bsr _c2ppatch
            bsr _skypatch
            bsr _objpatch
            bsr _worldpatch
            bsr _mappatch
            bsr _landpatch
            move.l  #$a888,a1
            move.l  #$ee2e,d1
            move.l  #$d750,d2
            move.l  #$d860,d3
            bsr _projpatch
            move.l  #$bbf4,a1
            bsr _spanpatch
            move.l  #$78e6,a1
            move.l  #$ed97,d1
            move.l  _hunk2(pc),a2
            lea     $4ec(a2),a2
            bsr _ptrpatch
            bsr _speedpatch
            bsr _swappatch
            bsr _prespatch
            bra .go
.orig       bsr _cpu12
            bsr _landpatch
            bsr _speedpatch
.go

        ;call
                move.l  d7,a1
                add.l   a1,a1
                add.l   a1,a1
                moveq   #_args_end-_args,d0
                lea     (_args,pc),a0
                movem.l (_saveregs,pc),d1-d6/a2-a6
                move.w #$f,$dff1fc
                jsr     (4,a1)

        IFD QUIT_AFTER_PROGRAM_EXIT
                pea     TDREASON_OK
                jmp     (resload_Abort,a2)
        ELSE
        ;remove exe
                move.l  d7,d1
                move.l  (_dosbase,pc),a6
                jsr     (_LVOUnLoadSeg,a6)
        ENDC

.end            moveq   #0,d0
                move.l  (_saverts,pc),-(a7)
                rts

_pl_program     PL_START
                PL_END

_disk1          dc.b    "df0",0         ;for Assign
_program        dc.b    "start",0
_args           dc.b    10
_args_end       dc.b    0
        EVEN

_saveregs       ds.l    11
_saverts        dc.l    0
_dosbase        dc.l    0

        ENDC

;============================================================================
Info
        MOVE.L  A0,-(SP)
        MOVE.L  D2,A0
        MOVE.L  #$0,0(A0)
        MOVE.L  #$0,4(A0)
        MOVE.L  #$52,8(A0)
        MOVE.L  #$2710,$C(A0)
        MOVE.L  #5,$10(A0)
        MOVE.L  #$1E8,$14(A0)
        MOVE.L  #$444F5300,$18(A0)
        MOVE.L  #0,$1c(A0)
        MOVE.L  #0,$20(A0)
        MOVE.L  (SP)+,A0
        RTS

_patch
 
   
        MOVE.L  $4.W,A6                 ;OPEN DOSLIB FOR USE (THE EMU
   
****


        ;        move.b  #%100,$BFDD00           ; disable TOD timer int

; alloc mem for screen (if necessary ?)

                move.l  #2*80*256,D0
                moveq   #0,D1
                move.l  4.w,A6
                jsr     _LVOAllocMem(a6)
                move.l  D0,-(A7)

; alloc mem for screen struct

                move.l  #$15A*4,D0
                moveq   #0,D1
                move.l  4.w,A6
                jsr     _LVOAllocMem(a6)
                move.l  D0,-(A7)

                moveq   #0,D0
                lea     IntName(pc),A1
                move.l  4.w,A6
                jsr     _LVOOpenLibrary(a6)
                move.l  D0,A6

; patch some functions
                move.w  #$4EF9,D0
                pea     return(pc)
                move.w  D0,_LVOSetPointer(a6)
                move.l  (A7),_LVOSetPointer+2(a6)
                move.w  D0,_LVOMoveScreen(a6)
                move.l  (A7),_LVOMoveScreen+2(a6)
                move.w  D0,_LVOOpenWindow(a6)
                move.l  (A7)+,_LVOOpenWindow+2(a6)
                move.w  D0,_LVOOpenScreen(a6)
                pea     OpenScreen(pc)
                move.l  (A7)+,_LVOOpenScreen+2(a6)


                move.l  (a7)+,A0
                move.l  A0,$38(a6)              ; screen struct

                move.w  #200,$E(A0)             ; screen height NTSC

                move.l  (A7)+,$C0(A0)           ; bitmap ptr

                move.l  _monitor(pc),D0
                cmp.l   #PAL_MONITOR_ID,D0
                bne.b   .skip
               move.w  #256,$E(A0)             ; screen height PAL
.skip
     
                moveq   #0,D0
                lea     GfxName(pc),A1
                move.l  4.w,A6
                jsr     _LVOOpenLibrary(a6)
                move.l  D0,A6

; patch some functions
                move.w  #$4EF9,D0
                pea     return(pc)
                move.w  D0,_LVOSetRast(a6)
                move.l  (A7),_LVOSetRast+2(a6)
  ;              move.w  D0,_LVORectFill(a6)
  ;             move.l  (A7)+,_LVORectFill+2(a6)

                moveq   #0,D0
                lea     DosName(pc),A1
                move.l  4.w,A6
                jsr     _LVOOpenLibrary(a6)
                move.l  D0,A6

; patch some functions
                move.w  #$4EF9,D0
                move.w  D0,_LVOInfo(a6)
                pea     Info(pc)
                move.l  (A7)+,_LVOInfo+2(a6)
                move.w  D0,_LVODeleteFile(a6)
                pea     Delete(pc)
                move.l  (A7)+,_LVODeleteFile+2(a6)
            ;
    bra _cont

DosName
                dc.b    'dos.library',0
GfxName
                dc.b    'graphics.library',0
IntName
                dc.b    'intuition.library',0
 even
OpenScreen
                movem.l d1-a6,-(a7)

                moveq   #0,d0
                move.w  ns_Width(a0),d0
                lsr.w   #3,d0
                mulu    ns_Height(a0),d0
                move.l  d0,-(a7)
                move.w  ns_Depth(a0),-(a7)
                mulu    (a7),d0
                moveq   #0,d1
                move.l  4.w,a6
                jsr     _LVOAllocMem(a6)
                move.l  d0,-(a7)

                move.l  #sc_SIZEOF,d0
                moveq   #0,d1
                move.l  4.w,a6
                jsr     _LVOAllocMem(a6)
                move.l  d0,a0

                move.l  (a7)+,d1
                moveq   #0,d3
                move.w  (a7)+,d3
                subq.w  #1,d3
                moveq   #0,d2
                lea     $C0(a0),a0
.loop
                move.l  d1,(a0)
                add.l   d2,(a0)+
                add.l   (a7),d2
                dbf     d3,.loop
                addq.l  #4,a7

                movem.l (a7)+,d1-a6
                rts

return
                moveq   #0,d0
                rts
Delete
                movem.l d1/a0-a2,-(a7)
                move.l  d1,a0
                move.l  _resload(pc),a2
                jsr     resload_DeleteFile(a2)
                movem.l (a7)+,d1/a0-a2
                rts
*************************************
     
   
       bra _cont

   
lbC0002AE       MOVEQ   #0,D0
        RTS


patchint
        rts
        MOVEM.L D1-D7/A0-A6,-(SP)
        MOVEQ   #0,D0
        MOVE.W  4(A0),D0
        LSR.W   #3,D0
        MULU    6(A0),D0
        MOVE.L  D0,-(SP)
        MOVE.W  8(A0),-(SP)
        MULU    (SP),D0
        MOVEQ   #2,D1
        MOVE.L  4,A6
        JSR     -$C6(A6)
        MOVE.L  D0,-(SP)
        MOVE.L  #$15A,D0
        MOVEQ   #2,D1
        MOVE.L  4,A6
        JSR     -$C6(A6)
        MOVE.L  D0,A0
        MOVE.L  (SP)+,D1
        MOVEQ   #0,D3
        MOVE.W  (SP)+,D3
        SUBQ.W  #1,D3
        MOVEQ   #0,D2
        LEA     $C0(A0),A0
lbC000342       MOVE.L  D1,(A0)
        ADD.L   D2,(A0)+
        ADD.L   (SP),D2
        DBRA    D3,lbC000342

        ADDQ.L  #4,SP
        MOVEM.L (SP)+,D1-D7/A0-A6
        RTS

doslibrary.MSG  dc.b    'dos.library',0
graphicslibra.MSG       dc.b    'graphics.library',0
intuitionlibr.MSG       dc.b    'intuition.library',0
TX.MSG  dc.b    'start',0
OSEmu400.MSG    dc.b    'OSEmu.400',0,0
lbL000392       dc.l    $88000002
lbL000396       dc.l    0
        dc.l    $88000005
lbL00039E       dc.l    $FFFFFFFF
        dc.l    0
path:
        dc.b 'data',0
        

        even

lbC000306       RTS

lbL000308       dc.l    0
        dc.l    0
        dc.l    0
        dc.l    0
        dc.l    0
        dc.w    0

lbC00031E
        MOVEQ   #0,D0
        RTS

**********************************************

  IFD PRESTIGE_CRACK

_crackPRESTIGE

;        blitz
        move.l (a1),d0
        LSL.L   #2,D0
        ADDQ.L  #4,D0

        MOVE.L  D0,A0
        ADD.L   #$2632,A0
        cmp.l #$101b4880,(a0)
        bne .pas
        MOVE.W  #$4EB9,(A0)+
        PEA     _prepcrack(PC)
        MOVE.L  (SP)+,(A0)
.pas
        RTS

_prepcrack
        CMP.B   #7,-5(A3)
        BNE .skip
        MOVEM.L D0/A0-A3,-(SP)
        LEA     lbL00007E(PC),A2
        BSR  _test_data
        BNE .sk1
        LEA     lbL00008E(PC),A2
        BSR  _test_data
        BEQ .sk2
.sk1
       CMP.B   #$14,(A0)
        BNE .sk2
        MOVE.B  #10,(A0)
.sk2
       MOVEM.L (SP)+,D0/A0-A3
.skip
       MOVE.B  (A3)+,D0
        EXT.W   D0
        SWAP    D0
        RTS

_test_data
        MOVE.L  A3,A0
        ADD.W   (A2)+,A0
        LEA     -4(A3),A1
        MOVEQ   #6,D0
.enc
        CMPM.B  (A1)+,(A2)+
        BNE .fin2
        DBRA    D0,.enc

        MOVEQ   #-$1,D0
        RTS
.fin2
        MOVEQ   #0,D0
        RTS

lbL00007E
        dc.l    $2A30003
        dc.l    $2070000
        dc.l    $849ADED6
        dc.l    $5EA0A68E
lbL00008E
        dc.l    $2AD0000
        dc.l    $E0070002
        dc.w    $8E00

.fin
        MOVEM.L (SP)+,D0-D7/A0-A6

  

       ENDC


**********************************************
; Development builds: boot straight into the game. START's open wrapper (hunk 0 +$2540) is
; entered with a3 on the name inside the MAIN script op that loads the file; at the loads of
; logo and init3d the hook changes two branches of MAIN, checked byte for byte first:
; - after "logo.AO": a branch to MAIN's path for an Esc during the logo, which skips the
;   intro, with MAIN's language byte ($e68) set to English (the flags screen is skipped);
; - in the block that loads init3d: the options menu's load and its object are branched
;   over. Level of detail ($383e) and 3D window ($383d) keep their boot value 0, HIGH.
; A click during the jungle's set-up then reaches the pointer's 3D pick (hunk 1 +$afd8,
; from yoda's script) before the view's projection is first set (+$e92e-+$e940, MAIN's
; -940..-934 from the view's +$70..+$7a), and the point's projection (+$af4c) divides by
; MAIN's -938, still 0 (an Integer Divide by Zero at +$af6c). Through the menu the set-up
; comes first. +$af4c movem.l d3-d7,-(sp) / move.w d2,d4 (48e7 1f00 3802, checked first)
; becomes jsr _pickproj, which gives the point (0,0,0) while that divisor is 0.

  IFD DEVELOPER

_directstart
        move.l  (a1),d0                 ; hunk 1
        lsl.l   #2,d0
        addq.l  #4,d0
        add.l   #$eda8,d0               ; -> pointer to MAIN's variables
        lea     _mainvars(pc),a0
        move.l  d0,(a0)
        lea     4(a1),a0                ; hunk 0
        cmp.l   #$61986100,$2540(a0)    ; bsr.s $24da / bsr.w $294a
        bne     .no
        cmp.w   #$0406,$2544(a0)
        bne     .no
        lea     $24da(a0),a1
        lea     _open1(pc),a2
        move.l  a1,(a2)
        lea     $294a(a0),a1
        move.l  a1,4(a2)
        move.w  #$4eb9,$2540(a0)
        pea     _openhook(pc)
        move.l  (a7)+,$2542(a0)
        move.l  d0,a1                   ; hunk 1: the point's projection
        sub.l   #$eda8,a1
        cmp.l   #$48e71f00,$af4c(a1)
        bne     .flush
        cmp.w   #$3802,$af50(a1)
        bne     .flush
        move.w  #$4eb9,$af4c(a1)
        pea     _pickproj(pc)
        move.l  (a7)+,$af4e(a1)
.flush  move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

; replaces +$af4c movem.l d3-d7,-(sp) / move.w d2,d4; a1 MAIN's variables plus the view's
; offset (-938(a1) the divisor)
_pickproj
        tst.w   -938(a1)
        bne     .on
        addq.l  #4,a7                   ; to +$af4c's caller: the point (0,0,0)
        moveq   #0,d0
        moveq   #0,d1
        moveq   #0,d2
        rts
.on     sub.w   #20,a7                  ; as movem.l d3-d7,-(sp) under the return
        move.l  20(a7),(a7)
        movem.l d3-d7,4(a7)
        move.w  d2,d4
        rts

_openhook
        movem.l d0/a0-a2,-(a7)
        lea     _logo(pc),a1
        bsr     _match
        bne     .init3d
        lea     _logo_at(pc),a1
        bsr     _match
        bne     .done
        lea     _logo_to(pc),a1
        bsr     _match
        bne     .done
        lea     _logo_jump(pc),a1
        bsr     _write
        move.l  _mainvars(pc),a0
        move.l  (a0),a0
        move.b  #1,$e68(a0)             ; English
        bra     .done
.init3d lea     _init3d(pc),a1
        bsr     _match
        bne     .done
        lea     _prefs_at(pc),a1
        bsr     _match
        bne     .done
        lea     _prefs_to(pc),a1
        bsr     _match
        bne     .done
        lea     _menu_at(pc),a1
        bsr     _match
        bne     .done
        lea     _menu_to(pc),a1
        bsr     _match
        bne     .done
        lea     _prefs_jump(pc),a1
        bsr     _write
        lea     _menu_jump(pc),a1
        bsr     _write
.done   movem.l (a7)+,d0/a0-a2
        pea     .r1(pc)                 ; the two calls the hook replaced
        move.l  _open1(pc),-(a7)
        rts
.r1     pea     .r2(pc)
        move.l  _open2(pc),-(a7)
        rts
.r2     rts

; a1: dc.w offset from a3, length; bytes. Z set when they are at a3+offset.
_match  move.l  a3,a0
        add.w   (a1)+,a0
        move.w  (a1)+,d0
        subq.w  #1,d0
.m      cmpm.b  (a0)+,(a1)+
        dbne    d0,.m
        rts

; a1: dc.w offset from a3, length; bytes: written at a3+offset.
_write  move.l  a3,a0
        add.w   (a1)+,a0
        move.w  (a1)+,d0
        subq.w  #1,d0
.w      move.b  (a1)+,(a0)+
        dbf     d0,.w
        rts

_mainvars       dc.l    0
_open1          dc.l    0
_open2          dc.l    0

; offsets from the name in MAIN's load op (a3)
_logo           dc.w    0,8
                dc.b    "logo.AO",0
_logo_at        dc.w    8,6                     ; create the logo object
                dc.b    $40,$00,$01,$08,$39,$38
_logo_to        dc.w    $603,4                  ; MAIN's path after an Esc in the logo
                dc.b    $96,$00,$00,$42
_logo_jump      dc.w    8,4
                dc.b    $0a,$00,$05,$f7
_init3d         dc.w    0,10
                dc.b    "init3d.AO",0
_prefs_at       dc.w    $20,5                   ; switch on the language: load the menu
                dc.b    $2f,$06,$0e,$68,$02
_prefs_to       dc.w    $5f,4
                dc.b    $07,$00,$05,$1d
_menu_at        dc.w    $97,6                   ; create the menu object, wait for its end
                dc.b    $40,$00,$54,$08,$39,$38
_menu_to        dc.w    $cc,3                   ; free the menu's slots
                dc.b    $3d,$00,$54
_prefs_jump     dc.w    $20,4
                dc.b    $0a,$00,$00,$3b
_menu_jump      dc.w    $97,4
                dc.b    $0a,$00,$00,$31
        EVEN

  ENDC

**********************************************
; Profile builds: count the frames the game draws in PROFILE_FRAMES (a longword in user
; vector 67, after the $106 jump) and keep the slave's address in PROFILE_SLAVE (vector 68),
; for tools/rr_prof.py. The chunky-to-planar entry, hunk 2
; +$2db8, calls the conversion loop once per frame through jsr <hunk 2 +$2e84> at +$2e78;
; that call goes through _framehook instead.

  IFD PROFILE

PROFILE_FRAMES  = $10c
PROFILE_SLAVE   = $110

_framecount
        move.l  (a1),d0                 ; hunk 1
        lsl.l   #2,d0
        move.l  d0,a0
        move.l  (a0),d0                 ; hunk 2
        lsl.l   #2,d0
        move.l  d0,a0
        addq.l  #4,a0
        cmp.w   #$4eb9,$2e78(a0)
        bne     .no
        lea     $2e84(a0),a1
        cmp.l   $2e7a(a0),a1
        bne     .no
        lea     _c2p(pc),a2
        move.l  a1,(a2)
        pea     _framehook(pc)
        move.l  (a7)+,$2e7a(a0)
        clr.l   PROFILE_FRAMES.w
        pea     slv_base(pc)
        move.l  (a7)+,PROFILE_SLAVE.w
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

_framehook
        addq.l  #1,PROFILE_FRAMES.w
        move.l  _c2p(pc),-(a7)
        rts

_c2p    dc.l    0

  ENDC

**********************************************
; START sizes a fast-memory pool (hunk 0 +$162, AvailMem(MEMF_FAST|MEMF_LARGEST) - 50000,
; none under 100000) and then discards it with move.l #0,<hunk 1 +$f4> at hunk 0 +$196, so
; everything comes from the chip pool. With the 1 MB ExpMem, branch over that store: MAIN's
; object table and the objects' variables then live in fast memory (hunk 1 +$8c7c,
; docs/internals.md). Not with MemConfig=1's 256 KB.

_fastpool
        move.l  _expmemsize(pc),d0
        sub.l   _kicksize(pc),d0
        cmp.l   #FASTMEMSIZE,d0
        blo     .no
        lea     4(a1),a0                ; hunk 0
        cmp.l   #$23fc0000,$196(a0)
        bne     .no
        cmp.w   #$0000,$19a(a0)
        bne     .no
        move.w  #$6008,$196(a0)         ; bra.s to +$1a0
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

**********************************************
; The renderer's buffers in fast memory. START's block allocator (hunk 0 +$36ee: d0 size ->
; d0 handle, an entry of the table at hunk 1 +$ef42 whose first longword is the block)
; takes from the top of the chip pool; the calls for the 3D view's chunky buffer and the
; renderer's tables go to _fastalloc instead, which takes the same blocks from the top of the fast pool
; (hunk 1 +$100, its end, which START sets and does not use) down to the end of the objects'
; frames (hunk 1 +$ed82), or from chip as before when there is no fast pool or no room.
; _fastfree replaces START's free (hunk 0 +$3748) for both: like it, it gives a block back
; only when it is the lowest one of its pool.

_fastblocks
        lea     4(a1),a1                ; hunk 0
        lea     $36ee(a1),a0
        cmp.l   #$48e74080,(a0)         ; movem.l d1/a0,-(a7)
        bne     .no
        lea     _chipalloc(pc),a2
        move.l  a0,(a2)
        cmp.l   #$48e78080,$3748(a1)    ; movem.l d0/a0,-(a7) / movea.l d0,a0
        bne     .no
        cmp.w   #$2040,$374c(a1)
        bne     .no
        lea     _fastsites(pc),a2
.check  move.w  (a2)+,d0                ; all call sites first
        bmi     .patch
        move.w  (a2)+,d1
        bsr     .site
        cmp.w   #$4eb9,(a0)
        bne     .no
        lea     $36ee(a1),a3
        cmp.l   2(a0),a3
        bne     .no
        bra     .check
.patch  lea     _fastsites(pc),a2
.p      move.w  (a2)+,d0
        bmi     .free
        move.w  (a2)+,d1
        bsr     .site
        pea     _fastalloc(pc)
        move.l  (a7)+,2(a0)
        bra     .p
.free   move.w  #$4ef9,$3748(a1)
        pea     _fastfree(pc)
        move.l  (a7)+,$374a(a1)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts
; d0 hunk, d1 offset -> a0
.site   move.l  a1,a0
        tst.w   d0
        beq     .s
        move.l  _hunk1(pc),a0
        subq.w  #1,d0
        beq     .s
        move.l  _hunk2(pc),a0
.s      swap    d1
        clr.w   d1
        swap    d1
        add.l   d1,a0                   ; offsets above $7fff: no sign extension
        rts

; jsr <hunk 0 +$36ee> sites: hunk, offset
_fastsites
        dc.w    1,$a2b2                 ; the 3D view's chunky buffer
        dc.w    1,$a2ce                 ; the renderer's tables, 34,592 bytes
        dc.w    1,$a30e                 ; a table of longwords
        dc.w    -1

_fastalloc
        movem.l d1/a0-a1,-(a7)
        move.l  _hunk1(pc),a1
        move.l  $100(a1),d1             ; the lowest fast block, 0 without a pool
        beq     .chip
        sub.l   d0,d1
        subq.l  #8,d1                   ; header
        and.w   #-16,d1
        cmp.l   $ed82(a1),d1
        blo     .chip
        move.l  d1,a0
        move.l  $100(a1),d0
        sub.l   d1,d0
        move.l  d0,(a0)                 ; header: the distance to the block above
        move.l  a0,$100(a1)
        addq.l  #8,a0
        move.l  a0,d0
        lea     $ef42(a1),a0
        moveq   #15,d1
.find   tst.l   (a0)
        beq     .got
        addq.l  #8,a0
        dbf     d1,.find
        moveq   #0,d0                   ; no handle: as START, the block stays taken
        bra     .out
.got    move.l  d0,(a0)
        move.l  d0,4(a0)
        move.l  a0,d0
.out    movem.l (a7)+,d1/a0-a1
        rts
.chip   movem.l (a7)+,d1/a0-a1
        move.l  _chipalloc(pc),-(a7)
        rts

_fastfree
        movem.l d0/a0-a1,-(a7)
        move.l  d0,a0
        move.l  4(a0),d0
        clr.l   (a0)
        clr.l   4(a0)
        subq.l  #8,d0                   ; header
        move.l  _hunk1(pc),a1
        lea     $100(a1),a0             ; the fast pool's lowest block
        cmp.l   (a0),d0
        beq     .back
        lea     $108(a1),a0             ; the chip pool's
        cmp.l   (a0),d0
        bne     .out
.back   move.l  d0,a1
        add.l   (a1),d0
        move.l  d0,(a0)
.out    movem.l (a7)+,d0/a0-a1
        rts

_hunk1          dc.l    0
_hunk2          dc.l    0

; _hunks: a1 START's segment list (its first hunk's link); _hunk1 and _hunk2 set, a1 kept
_hunks
        move.l  (a1),d0
        lsl.l   #2,d0
        move.l  d0,a2                   ; hunk 1 - 4
        move.l  (a2),d0
        lsl.l   #2,d0
        addq.l  #4,d0
        lea     _hunk2(pc),a0
        move.l  d0,(a0)
        addq.l  #4,a2
        lea     _hunk1(pc),a0
        move.l  a2,(a0)
        rts

; Enhanced framerate (CUSTOM2): Z clear, all of "AGA improvements" (docs/internals.md); Z
; set, the game as version 1.2 had it: none of them but the options' own patches, and
; _cpu12 for v1.2's caches. All registers kept.
_enhget
        movem.l d0-d1/a0-a2,-(a7)
        lea     _enhtags(pc),a0
        move.l  _resload(pc),a2
        jsr     resload_Control(a2)
        movem.l (a7)+,d0-d1/a0-a2
        tst.l   _enh(pc)
        rts
_enhtags        dc.l    WHDLTAG_CUSTOM2_GET
_enh            dc.l    0
                dc.l    0

; v1.2's caches: its CACHE option's, the KickEmu's CACHECHIPDATA undone. All registers kept.
_cpu12
        movem.l d0-d1/a0-a2,-(a7)
        move.l  #WCPUF_Base_NC|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC|WCPUF_BC|WCPUF_SS|WCPUF_SB,d0
        move.l  #WCPUF_All,d1
        move.l  _resload(pc),a2
        jsr     resload_SetCPU(a2)
        movem.l (a7)+,d0-d1/a0-a2
        rts
_chipalloc      dc.l    0

**********************************************
; The chunky-to-planar conversion (src/c2p030.s, src/c2p040.s): START's loop at hunk 2
; +$2e84 starts with move.w d6,<hunk 2 +$2db6>, which becomes jmp _c2p030, or jmp _c2p040
; when WHDLoad's AttnFlags have the 68040 or 68060 bit. C2P040_OFF (a test define): the
; 68030's on every CPU. After _fastblocks (_hunk2).

_c2ppatch
        move.l  _hunk2(pc),a0
        lea     $2e84(a0),a1
        cmp.w   #$33c6,(a1)
        bne     .no
        lea     $2db6(a0),a0
        cmp.l   2(a1),a0
        bne     .no
        move.l  a3,-(a7)
        move.l  _resload(pc),a2
        lea     _c2p030(pc),a3
    IFND C2P040_OFF
        move.l  a1,-(a7)
        lea     _c2ptags(pc),a0
        jsr     resload_Control(a2)
        move.l  (a7)+,a1
        move.l  _c2pattn(pc),d0
        and.w   #AFF_68040|1<<7,d0      ; 1<<7: AFF_68060
        beq     .set
        lea     _c2p040(pc),a3
    ENDC
.set    move.w  #$4ef9,(a1)
        move.l  a3,2(a1)
        move.l  (a7)+,a3
        jsr     resload_FlushCache(a2)
.no     rts

_c2ptags        dc.l    WHDLTAG_ATTNFLAGS_GET
_c2pattn        dc.l    0
                dc.l    0

        INCLUDE c2p030.s
        INCLUDE c2p040.s

**********************************************
; The sky copy (src/sky030.s): hunk 1 +$e262-$e291, START's row loop, becomes jsr _skyrows
; and bra.w +$e292, after a check of its bytes (with the address of <hunk 1 +$edfe> at
; +$e272). After _fastblocks (_hunk1).

_skypatch
        move.l  _hunk1(pc),a0
        move.l  a0,a1
        add.l   #$e262,a1
        lea     .old(pc),a2
        moveq   #(.oldend-.old)/2-1,d0
        moveq   #0,d1
.cmp    cmp.w   #$10,d1                 ; +$e272: the address
        beq     .addr
        move.w  (a2),d2
        cmp.w   (a1,d1.w),d2
        bne     .no
        addq.w  #2,d1
        addq.l  #2,a2
        dbf     d0,.cmp
        move.w  #$4eb9,(a1)
        pea     _skyrows(pc)
        move.l  (a7)+,2(a1)
        move.l  #$60000028,6(a1)        ; bra.w +$e292
        bsr     _skycopy
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts
.addr   move.l  a0,d2
        add.l   #$edfe,d2
        cmp.l   (a1,d1.w),d2
        bne     .no
        addq.w  #4,d1
        addq.l  #4,a2
        subq.w  #1,d0
        dbf     d0,.cmp
        bra     .no
.old    dc.w    $4a40,$6d00,$000a,$3600,$32d8,$51cb,$fffc,$3639,0,0,$e24b,$9640
        dc.w    $5543,$6d00,$000a,$90c1,$32d8,$51cb,$fffc,$d2c5,$d8c1,$204c,$51cf,$ffd2
.oldend

; The sky in fast memory (docs/performance.md, plan step 12): a room from the fast memory
; list for _skyrows's copy of the image, and the sky's set-up (the script op +$30bc, the
; view's image at +164) +$30e0 move.l d2,164(a0) and bsr.w +$7b58 becoming jsr _skyset and
; a nop, after a check of their bytes. No room: _skyrows reads the image itself. a0 hunk 1.

_skycopy
        IFND SKYCOPY_OFF
        movem.l d0-d1/a0-a1/a6,-(a7)
        cmp.l   #$214200a4,$30e0(a0)
        bne     .x
        cmp.l   #$61004a72,$30e4(a0)
        bne     .x
        move.l  #SKYMAX+40,d0
        moveq   #MEMF_FAST|MEMF_PUBLIC,d1
        move.l  4.w,a6
        jsr     _LVOAllocMem(a6)
        move.l  8(a7),a0
        tst.l   d0
        beq     .x
        add.l   #15,d0
        and.w   #-16,d0
        lea     _kvars(pc),a1
        move.l  d0,K_BUF(a1)
        move.w  #$4eb9,$30e0(a0)
        pea     _skyset(pc)
        move.l  (a7)+,$30e2(a0)
        move.w  #$4e71,$30e6(a0)        ; nop
.x      movem.l (a7)+,d0-d1/a0-a1/a6
        ENDC
        rts

; +$30e0: the view's image set as before, the copy to be made again, on to +$7b58 (its rts
; returning to the nop after the jsr, as the bsr.w did)
_skyset move.l  d2,164(a0)
        move.l  a1,-(a7)
        lea     _kvars(pc),a1
        clr.l   K_ORIG(a1)
        move.l  (a7)+,a1
        move.l  _hunk1(pc),-(a7)
        add.l   #$7b58,(a7)
        rts

        INCLUDE sky030.s

**********************************************
; The landscape's inner loop in the 68030's instruction cache (docs/performance.md, plan
; step 15; src/land030.s), its copy in a 16-byte aligned block from the fast memory list
; (none: no patch; the block is not freed if the loop's words differ). The test define
; LAND_OFF leaves it out.

_landpatch
        IFND LAND_OFF
        movem.l d0-d1/a0-a2/a6,-(a7)
        lea     _landtags(pc),a0
        move.l  _resload(pc),a2
        jsr     resload_Control(a2)
        move.l  _landopt(pc),d0         ; without Enhanced framerate only for Smooth landscape
        or.l    _enh(pc),d0
        beq     .x
        move.l  #LCOPYMAX+16,d0
        moveq   #MEMF_FAST|MEMF_PUBLIC,d1
        move.l  4.w,a6
        jsr     _LVOAllocMem(a6)
        tst.l   d0
        beq     .x
        add.l   #15,d0
        and.w   #-16,d0
        move.l  d0,a1
        move.l  _hunk1(pc),a0
        move.l  _landopt(pc),d0         ; Smooth landscape: _bloop
        bsr     _landinst
        tst.l   d0
        beq     .x
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.x      movem.l (a7)+,d0-d1/a0-a2/a6
        ENDC
        rts
_landtags       dc.l    WHDLTAG_CUSTOM3_GET
_landopt        dc.l    0
                dc.l    0

        INCLUDE land030.s
        INCLUDE proj020.s
        INCLUDE span020.s
        INCLUDE ptr020.s
; src/speed.s: the load op's bsr to the loader, the loader's lookup (hunk 1)
SPD_AGA         = 1
SPD_LOAD        = $2e22
SPD_LOOKUP      = $94b2
        INCLUDE speed.s

**********************************************
; The objects' images in fast memory (docs/performance.md, plan step 13). The 3D view's
; sprite routine (hunk 1 +$ea3a) finds an object's image at +$ea4a, adda.l (a2),a2 (an
; image of the resource heap in chip: type 28 or 30 at +0, width - 1 at +2, height - 1 at
; +4, the pixels from +8, as the sky's), and reads it only through a2: its header, the
; scaled pixels (+$eb5c, +$ec88) and the pick test's pixel (+$ebf4). +$ea4a adda.l (a2),a2
; and cmpi.b #28,(a2) become jsr _objimg, which gives the routine a copy in fast memory:
; a cache of OSLOTS images in an OBJMAX room from the fast memory list, each at its
; image's address modulo 16, found by the image's address. The heap changes only through
; its top <+$ed60>: an allocation (+$9540 add.l d1,<+$ed60>), the compaction that moves
; the blocks above a freed one down (+$92ee sub.l d1,<+$ed60>) and its reset (+$8d42
; move.l d0,<+$ed60>); each becomes a jsr that does the same and empties the cache. A full
; cache is emptied too. Each copy holds OMARGIN bytes after the image as well. MAPCHECK
; compares each image given with the original, counting
; differing longwords in O_BAD. All sites are checked first; no room: no patch.

OBJMAX  equ     65536                   ; the cache's bytes
OSLOTS  equ     128                     ; its images
OMARGIN equ     64                      ; bytes copied after an image: the scaled reads'
                                        ; rounding past its last pixel reads the same

_objpatch
        IFND OBJCOPY_OFF
        movem.l d0-d2/a0-a2/a6,-(a7)
        move.l  _hunk1(pc),a0
        lea     .sites(pc),a2
.chk    move.l  (a2)+,d0
        bmi     .ok
        move.w  (a2)+,d1
        cmp.w   (a0,d0.l),d1
        bne     .x
        move.l  a0,d2
        add.l   (a2)+,d2
        tst.l   -4(a2)
        bmi     .chk                    ; no address operand
        cmp.l   2(a0,d0.l),d2
        bne     .x
        bra     .chk
.ok     move.l  #OBJMAX+OSLOTS*8+16,d0
        moveq   #MEMF_FAST|MEMF_PUBLIC,d1
        move.l  4.w,a6
        jsr     _LVOAllocMem(a6)
        tst.l   d0
        beq     .x
        add.l   #15,d0
        and.w   #-16,d0
        lea     _ovars(pc),a1
        move.l  d0,O_TAB(a1)
        add.l   #OSLOTS*8,d0
        move.l  d0,O_BUF(a1)
        move.l  d0,O_FREE(a1)
        add.l   #OBJMAX,d0
        move.l  d0,O_END(a1)
        move.l  _hunk1(pc),a0
        lea     .jsrs(pc),a2
.put    move.l  (a2)+,d0
        beq     .done
        move.l  (a2)+,d1
        move.w  #$4eb9,(a0,d0.l)
        lea     .jsrs(pc,d1.l),a1
        move.l  a1,2(a0,d0.l)
        bra     .put
.done   move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.x      movem.l (a7)+,d0-d2/a0-a2/a6
        ENDC
        rts
; offset, opcode, the address operand's hunk 1 offset (-1: the next word instead)
.sites  dc.l    $ea4a
        dc.w    $d5d2
        dc.l    -1
        dc.l    $ea4c
        dc.w    $0c12
        dc.l    -1
        dc.l    $ea4e
        dc.w    $001c
        dc.l    -1
        dc.l    $9540
        dc.w    $d3b9
        dc.l    $ed60
        dc.l    $92ee
        dc.w    $93b9
        dc.l    $ed60
        dc.l    $8d42
        dc.w    $23c0
        dc.l    $ed60
        dc.l    -1
.jsrs   dc.l    $ea4a,_objimg-.jsrs
        dc.l    $9540,_heapadd-.jsrs
        dc.l    $92ee,_heapsub-.jsrs
        dc.l    $8d42,_heapset-.jsrs
        dc.l    0

_heapadd
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        add.l   d1,($ed60,a0)
        bra     _heapch
_heapsub
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        sub.l   d1,($ed60,a0)
        bra     _heapch
_heapset
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        move.l  d0,($ed60,a0)
_heapch lea     _ovars(pc),a0
        st      O_FLUSH(a0)
        move.l  (a7)+,a0
        rts

; +$ea4a: a2 the object's image (its offset at (a2) added); flags as cmpi.b #28,(a2)
_objimg adda.l  (a2),a2
        cmp.b   #28,(a2)
        beq     .t
        cmp.b   #30,(a2)
        bne     .cmp
.t      movem.l d0-d3/a0-a1/a3,-(a7)
        lea     _ovars(pc),a3
        tst.b   O_FLUSH(a3)
        beq     .look
.empty  sf      O_FLUSH(a3)
        clr.l   O_N(a3)
        move.l  O_BUF(a3),O_FREE(a3)
.look   move.l  O_TAB(a3),a0
        move.l  O_N(a3),d0
        bra     .lt
.l      cmp.l   (a0),a2
        beq     .hit
        addq.l  #8,a0
.lt     dbf     d0,.l
        moveq   #0,d0                   ; not there: its bytes
        move.w  2(a2),d0
        addq.l  #1,d0
        moveq   #0,d1
        move.w  4(a2),d1
        addq.l  #1,d1
        mulu.l  d1,d0
        addq.l  #8,d0
        cmp.l   #OBJMAX/2,d0
        bhi     .out
        cmp.l   #OSLOTS,O_N(a3)
        bhs     .empty
        move.l  a2,d2
        moveq   #15,d3
        and.l   d3,d2                   ; the image's address modulo 16
        move.l  O_FREE(a3),d1
        add.l   d3,d1
        and.w   #-16,d1
        add.l   d2,d1                   ; the copy
        add.l   #OMARGIN,d0             ; and the bytes after it
        move.l  d1,d3
        add.l   d0,d3
        addq.l  #3,d3
        cmp.l   O_END(a3),d3
        bhi     .empty
        move.l  d3,O_FREE(a3)
        move.l  a2,(a0)+                ; the new entry
        move.l  d1,(a0)
        subq.l  #4,a0
        addq.l  #1,O_N(a3)
        moveq   #3,d3
        and.l   d2,d3                   ; the offset in the first longword
        add.l   d3,d0
        addq.l  #3,d0
        lsr.l   #2,d0                   ; the longwords
        move.l  a2,a1
        suba.l  d3,a1
        move.l  d1,a3
        suba.l  d3,a3
        bra     .ct
.c      move.l  (a1)+,(a3)+
.ct     dbf     d0,.c
.hit
        IFD MAPCHECK
        lea     _ovars(pc),a3
        moveq   #0,d0
        move.w  2(a2),d0
        addq.l  #1,d0
        moveq   #0,d1
        move.w  4(a2),d1
        addq.l  #1,d1
        mulu.l  d1,d0
        addq.l  #8,d0
        lsr.l   #2,d0
        move.l  a2,a1
        move.l  4(a0),d1
        move.l  d1,d2
        move.l  d1,a3
        bra     .kt
.k      cmpm.l  (a1)+,(a3)+
        beq     .kt
        lea     _ovars(pc),a1           ; one count a call is enough
        addq.l  #1,O_BAD(a1)
        bra     .kd
.kt     dbf     d0,.k
.kd     lea     _ovars(pc),a3
        addq.l  #1,O_CALLS(a3)
        ENDC
        move.l  4(a0),a2
.out    movem.l (a7)+,d0-d3/a0-a1/a3
.cmp    cmp.b   #28,(a2)
        rts

_ovars
_otab   dc.l    0                       ; the cache's entries: image, copy
_obuf   dc.l    0                       ; its room
_oend   dc.l    0                       ; and the room's end
_ofree  dc.l    0                       ; the next copy's room
_on     dc.l    0                       ; the entries
_obad   dc.l    0                       ; MAPCHECK: calls with a copy that differed
_ocalls dc.l    0                       ; MAPCHECK: calls with a copy
_oflush dc.b    0                       ; the heap changed: the cache to be emptied
        even
O_TAB   equ     _otab-_ovars
O_BUF   equ     _obuf-_ovars
O_END   equ     _oend-_ovars
O_FREE  equ     _ofree-_ovars
O_N     equ     _on-_ovars
O_BAD   equ     _obad-_ovars
O_CALLS equ     _ocalls-_ovars
O_FLUSH equ     _oflush-_ovars

**********************************************
; The world on the cap's grid (docs/performance.md, plan step 7). MAIN runs the due script
; objects, then the frame routine (hunk 1 +$49b2: the cap wait, the drawing, the swap), and
; again; an object is due once the VBL count (+$ee6c) passes its next run (-62(a6)), its
; last run's count plus its period (-58(a6)). Keeping up, the passes start a cap (+$ee6a, 3
; fields in game) apart and every object runs on that grid; a long drawing pass breaks it.
; In 3D mode (+$ee03) a world count W takes the VBL count's place: W goes up by the cap per
; pass, each pass waits at its end for the VBL count to reach W (the cap wait's job), and while W is a
; pass or more behind at the list's end MAIN goes round the list again without the frame
; routine, at most twice in a row; three passes or more behind (a load, a pause) W is set
; to the count.
; - hunk 1 +$257e movea.l <+$ee6c>,a3 (the scheduler's due test) becomes jsr _wa3
; - +$6480 movea.l <+$ee6c>,a0 (op $36, the period) becomes jsr _wa0
; - +$250e bsr.w +$49b2, bra.s +$251a (the list's end) becomes jsr _listend
; - +$49e8 move.b <+$ee6a>,d0 (the cap, for the wait at +$49ee) becomes jsr _capwait
; - +$4b54 movem.l (sp)+,d0-a6 and rts (the frame routine's end) become jmp _passend, which
;   waits for W (plan step 10: the wait at the pass's end, not before its drawing)
; and, for plan step 8 (below), when it checks:
; - +$4b8e jsr +$a3a6 (the 3D view's drawing) becomes jsr _view
; - +$4880 movea.l <+$ed86>,a1 (an object's elements moved) becomes jsr _emove (step 9)

_worldpatch
        move.l  _hunk1(pc),a0
        lea     .sites(pc),a2
.chk    move.l  (a2)+,d0
        beq     .ok
        move.w  (a2)+,d2
        move.l  (a2)+,d3
        add.l   a0,d3                   ; the absolute operand
        cmp.w   (a0,d0.l),d2
        bne     .no
        cmp.l   2(a0,d0.l),d3
        bne     .no
        bra     .chk
.ok     move.l  a0,a1
        add.l   #$250e,a1
        cmp.l   #$610024a2,(a1)         ; bsr.w +$49b2
        bne     .no
        cmp.w   #$6006,4(a1)            ; bra.s +$251a
        bne     .no
        cmp.l   #$4cdf7fff,$4b54(a0)    ; movem.l (sp)+,d0-a6, rts: the frame routine's end
        bne     .no
        cmp.w   #$4e75,$4b58(a0)
        bne     .no
        lea     _wvars(pc),a2
        move.l  a0,d0
        add.l   #$ee6c,d0
        move.l  d0,W_VBL(a2)
        move.l  d0,W_PTR(a2)
        move.l  a0,d0
        add.l   #$ee6a,d0
        move.l  d0,W_CAP(a2)
        move.l  a0,d0
        add.l   #$ee03,d0
        move.l  d0,W_3D(a2)
        move.l  a0,d0
        add.l   #$49b2,d0
        move.l  d0,W_FRAME(a2)
        move.l  a0,d0
        add.l   #$ed6c,d0
        move.l  d0,W_OBJTAB(a2)
        move.l  a0,d0
        add.l   #$eef5,d0
        move.l  d0,W_FLAGS(a2)
        move.l  a0,a3
        add.l   #$4b8e,a3
        cmp.w   #$4eb9,(a3)
        bne     .noview
        move.l  a0,d0
        add.l   #$a3a6,d0
        cmp.l   2(a3),d0
        bne     .noview
        move.l  d0,W_DRAW(a2)
        move.w  #$4eb9,(a3)
        pea     _view(pc)
        move.l  (a7)+,2(a3)
.noview
        move.w  #$4eb9,d1
        move.w  d1,(a1)
        pea     _listend(pc)
        move.l  (a7)+,2(a1)
        lea     $257e(a0),a1
        move.w  d1,(a1)
        pea     _wa3(pc)
        move.l  (a7)+,2(a1)
        lea     $6480(a0),a1
        move.w  d1,(a1)
        pea     _wa0(pc)
        move.l  (a7)+,2(a1)
        lea     $49e8(a0),a1
        move.w  d1,(a1)
        pea     _capwait(pc)
        move.l  (a7)+,2(a1)
        lea     $4b54(a0),a1
        move.w  #$4ef9,(a1)
        pea     _passend(pc)
        move.l  (a7)+,2(a1)
        move.l  a0,a3                   ; plan step 9, when it checks and its table
        add.l   #$4880,a3               ; is allocated
        cmp.w   #$2279,(a3)
        bne     .noelem
        move.l  a0,d0
        add.l   #$ed86,d0
        cmp.l   2(a3),d0
        bne     .noelem
        move.l  d0,W_ELEM(a2)
        move.l  a0,d0
        add.l   #$edb8,d0
        move.l  d0,W_PREVH(a2)
        movem.l d1/a0-a1/a6,-(a7)
        move.l  #ESLOTS*ESIZE,d0
        move.l  #$10001,d1              ; MEMF_PUBLIC|MEMF_CLEAR
        move.l  4.w,a6
        jsr     _LVOAllocMem(a6)
        movem.l (a7)+,d1/a0-a1/a6
        move.l  d0,W_ETAB(a2)
        beq     .noelem
        move.w  #$4eb9,(a3)
        pea     _emove(pc)
        move.l  (a7)+,2(a3)
.noelem
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts
.sites  dc.l    $257e
        dc.w    $2679
        dc.l    $ee6c
        dc.l    $6480
        dc.w    $2079
        dc.l    $ee6c
        dc.l    $49e8
        dc.w    $1039
        dc.l    $ee6a
        dc.l    0

; the count the objects run by: W in 3D mode, the VBL count otherwise
_wa3    move.l  _wvars+W_PTR(pc),a3
        move.l  (a3),a3
        rts
_wa0    move.l  _wvars+W_PTR(pc),a0
        move.l  (a0),a0
        rts

; the list's end: a catch-up pass (back to +$251a without the frame routine) while W is a
; pass or more behind, at most twice in a row; the frame routine otherwise
_listend
        addq.l  #6,(a7)                 ; +$2514 -> +$251a
        bsr     _isample
        movem.l d0-d2/a0-a1,-(a7)
        lea     _wvars(pc),a1
        tst.b   W_ON(a1)
        beq     .frame
        move.l  W_3D(a1),a0
        tst.b   (a0)
        beq     .frame
        move.l  W_CAP(a1),a0
        moveq   #0,d1
        move.b  (a0),d1
        beq     .frame
        move.l  W_VBL(a1),a0
        move.l  (a0),d0
        sub.l   W_W(a1),d0              ; fields behind
        cmp.l   d1,d0
        blt     .frame                  ; less than a pass
        move.l  d1,d2
        add.l   d2,d2
        add.l   d1,d2
        cmp.l   d2,d0
        bge     .rebase
        cmp.b   #2,W_CATCH(a1)
        bhs     .frame
        addq.b  #1,W_CATCH(a1)
        add.l   d1,W_W(a1)
        movem.l (a7)+,d0-d2/a0-a1
        rts
.rebase move.l  (a0),d0                 ; W = the count less the cap, which the frame
        sub.l   d1,d0                   ; routine's wait adds back
        move.l  d0,W_W(a1)
.frame  clr.b   W_CATCH(a1)
        movem.l (a7)+,d0-d2/a0-a1
        move.l  _wvars+W_FRAME(pc),-(a7)
        rts

; d0.b the cap for the wait at +$49ee, as START's move.b (the rest of d0 kept); in 3D mode
; 0 (no wait: the wait for W is at the pass's end, _passend) and the drawing's time, the
; next pass's count
_capwait
        movem.l d1/a0-a1,-(a7)
        lea     _wvars(pc),a1
        move.l  W_CAP(a1),a0
        move.b  (a0),d0
        beq     .off
        move.l  W_3D(a1),a0
        tst.b   (a0)
        beq     .off
        move.l  W_VBL(a1),a0
        tst.b   W_ON(a1)
        bne     .on
.start  cmp.b   -1(a0),d0               ; 3D starts: START's cap wait (+$ee6b), then W
        bhi     .start                  ; from the count
        move.l  (a0),W_W(a1)
        st      W_ON(a1)
        lea     W_W(a1),a0
        move.l  a0,W_PTR(a1)
.on     moveq   #0,d1
        move.b  d0,d1
        add.l   W_W(a1),d1
        IFND PRESENT_OFF
        tst.b   _pvars+P_ON(pc)         ; plan step 11: the field the frame shows in, at
        beq     .t                      ; most W plus the cap (W, the next pass's count,
        movem.l d0/d2/a0,-(a7)          ; in a presentation frame)
        lea     _pvars(pc),a0
        move.l  d1,d2
        tst.b   P_IN(a0)
        beq     .t1
        move.l  W_W(a1),d2
.t1     bsr     _now
        move.l  d0,P_T0(a0)
        st      P_TIMED(a0)
        sf      P_ACC(a0)
        bsr     _pwhen
        move.l  d2,d1
        movem.l (a7)+,d0/d2/a0
.t
        ENDC
        move.l  d1,W_DRAWT(a1)
        clr.b   d0
        movem.l (a7)+,d1/a0-a1
        rts
.off    sf      W_ON(a1)
        move.l  W_VBL(a1),W_PTR(a1)
        movem.l (a7)+,d1/a0-a1
        rts

; the frame routine's end (+$4b54): in 3D mode W goes up by the cap and the pass waits for
; the count to reach it, so the next list runs at its time and the next drawing starts as
; soon as that list has run
_passend
        movem.l (a7)+,d0-a6
        tst.b   _pvars+P_IN(pc)
        bne     _passpres               ; a presentation frame's end: back to _present
        movem.l d1/a0-a1,-(a7)
        lea     _wvars(pc),a1
        tst.b   W_ON(a1)
        beq     _passout
        move.l  W_3D(a1),a0
        tst.b   (a0)
        beq     _passout
        move.l  W_CAP(a1),a0
        moveq   #0,d1
        move.b  (a0),d1
        beq     _passout
        add.l   W_W(a1),d1
        move.l  d1,W_W(a1)
        bsr     _present                ; plan step 11: frames while there is time
        move.l  W_VBL(a1),a0
_wwait  cmp.l   (a0),d1                 ; until the count reaches W
        bhi     _wwait
_wwaitend
_passout
        movem.l (a7)+,d1/a0-a1
_passpres
        rts

**********************************************
; Frames between world passes (docs/performance.md, plan step 11). After a world pass's
; frame, while the next pass is not due, _passend draws again: START's frame routine from
; +$49c2 (past +$49b2's operand reads from the list's script stream, +$294a), as on a pass
; on which no object was due, with the camera and the staged elements at the field the
; frame will show in. Per-pass work stays on world passes: the scripts' countdown (+$4bd6
; subq.b #1,<+$ef2a>, checked first, becomes jsr _cdown, which skips it in a presentation
; frame; _view skips it too), the view's velocity (+$4980, on the game's own changes only)
; and the objects' sampling (_listend). A presentation frame is drawn only when the last
; frame drawn was staged (the camera, or an element), when its field is later than the
; last frame's, and when it is expected to swap before the next pass is due; one that did
; not swap ends them for that pass.
;
; Times are in lines: the VBL count x 313 + the beam's line. The frame's field is
; estimated from the last frame drawn (its start to its first access to the back screen,
; and from after that access's wait to its swap): the access waits for the last swap to
; show. PRESENT_OFF (a test define): no presentation frames and the drawing's time W plus
; the cap, the frames those of plan step 10.2.

P_LINES equ     313
P_MARGIN equ    P_LINES/8               ; lines to spare before the next pass is due

; d0 the time in lines. START's VBL routine counts the field first thing (hunk 1 +$99ea);
; in the field's first half with VERTB still requested it has not run yet for this field
_now    movem.l d1-d2/a0,-(a7)
        move.l  _wvars+W_VBL(pc),a0
.r      move.l  (a0),d1
        move.l  $dff004,d0
        move.w  $dff01e,d2
        cmp.l   (a0),d1
        bne     .r
        lsr.l   #8,d0
        and.l   #$1ff,d0
        btst    #5,d2
        beq     .t
        cmp.w   #P_LINES/2,d0
        bhs     .t
        addq.l  #1,d1
.t      mulu.l  #P_LINES,d1
        add.l   d1,d0
        movem.l (a7)+,d1-d2/a0
        rts

; d0 the time now, d2 the latest field: d1 the frame's expected swap (lines), d2 the field
; it shows in, at most the given one
_pwhen  movem.l d0/d3,-(a7)
        add.l   _pvars+P_PRE(pc),d0     ; to its first access to the back screen
        move.l  _bvars+B_SVBL(pc),d3
        addq.l  #1,d3                   ; the field the last swap shows in, which the
        mulu.l  #P_LINES,d3             ; access waits for
        cmp.l   d3,d0
        bhs     .w
        move.l  d3,d0
.w      add.l   _pvars+P_TAIL(pc),d0
        move.l  d0,d1
        divu.l  #P_LINES,d0
        addq.l  #1,d0                   ; shown from the next field
        cmp.l   d2,d0
        bhs     .x
        move.l  d0,d2
.x      movem.l (a7)+,d0/d3
        rts

; from _passend, a1 _wvars, W the next pass's count
_present
        IFND PRESENT_OFF
        movem.l d0-a6,-(a7)
        lea     _pvars(pc),a4
        tst.b   P_ON(a4)
        beq     .out
.loop   bsr     _pneed
        beq     .out
        bsr     _now
        move.l  _wvars+W_W(pc),d2
        bsr     _pwhen
        cmp.l   P_LASTT(a4),d2
        bls     .out                    ; no later field than the last frame's
        add.l   #P_MARGIN,d1
        move.l  _wvars+W_W(pc),d0
        mulu.l  #P_LINES,d0
        cmp.l   d0,d1
        bhs     .out                    ; it would end after the next pass is due
        st      P_IN(a4)
        sf      P_SWAP(a4)
        move.l  _hunk1(pc),a0
        jsr     $49c2(a0)
        lea     _pvars(pc),a4
        sf      P_IN(a4)
        tst.b   P_SWAP(a4)
        beq     .out
        addq.l  #1,P_FRAMES(a4)
        bra     .loop
.out    movem.l (a7)+,d0-a6
        ENDC
        rts

; Z clear when the last frame drawn was staged: the camera, or an element (step 9's slots)
_pneed  movem.l d0/d7/a3,-(a7)
        tst.b   _ivars+I_STAGED(pc)
        bne     .yes
        move.l  _wvars+W_ETAB(pc),d0
        beq     .no
        move.l  d0,a3
        moveq   #ESLOTS-1,d7
.s      tst.l   (a3)
        beq     .n
        tst.b   22(a3)
        bne     .yes
.n      lea     ESIZE(a3),a3
        dbf     d7,.s
.no     moveq   #0,d0
        bra     .x
.yes    moveq   #1,d0
.x      movem.l (a7)+,d0/d7/a3
        rts

; +$4bd6, the countdown of a view with bit 5 set: not in a presentation frame (Z clear: the
; bne.w after it taken, as for a count not yet out)
_cdown  tst.b   _pvars+P_IN(pc)
        bne     .x
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        subq.b  #1,($ef2a,a0)
        movea.l (a7)+,a0
.x      rts

; the frame's timing: at its first access to the back screen (_bflush, before and after the
; wait for the last swap) and at its swap
_ptacc  movem.l d0/a0,-(a7)
        lea     _pvars(pc),a0
        tst.b   P_TIMED(a0)
        beq     .x
        tst.b   P_ACC(a0)
        bne     .x
        bsr     _now
        move.l  d0,P_TA(a0)
.x      movem.l (a7)+,d0/a0
        rts
_ptwait movem.l d0/a0,-(a7)
        lea     _pvars(pc),a0
        tst.b   P_TIMED(a0)
        beq     .x
        tst.b   P_ACC(a0)
        bne     .x
        st      P_ACC(a0)
        bsr     _now
        move.l  d0,P_TB(a0)
.x      movem.l (a7)+,d0/a0
        rts
_ptswap movem.l d0-d1/a0,-(a7)
        lea     _pvars(pc),a0
        st      P_SWAP(a0)
        tst.b   P_TIMED(a0)
        beq     .x
        sf      P_TIMED(a0)
        move.l  _wvars+W_DRAWT(pc),P_LASTT(a0)
        bsr     _now
        tst.b   P_ACC(a0)
        bne     .acc
        sub.l   P_T0(a0),d0             ; no access noted: all of it before
        move.l  d0,P_PRE(a0)
        clr.l   P_TAIL(a0)
        bra     .x
.acc    sub.l   P_TB(a0),d0
        move.l  d0,P_TAIL(a0)
        move.l  P_TA(a0),d0
        sub.l   P_T0(a0),d0
        move.l  d0,P_PRE(a0)
.x      movem.l (a7)+,d0-d1/a0
        rts

_pvars
_pt0            dc.l    0               ; the frame's start
_pta            dc.l    0               ; its first access to the back screen
_ptb            dc.l    0               ; after that access's wait
_ppre           dc.l    0               ; the last frame drawn: its start to its access
_ptail          dc.l    0               ; and after the wait to its swap
_plastt         dc.l    0               ; its field (W_DRAWT)
_pframes        dc.l    0               ; presentation frames drawn
_pon            dc.b    0               ; patched
_pin            dc.b    0               ; in a presentation frame
_ptimed         dc.b    0               ; the frame timed (3D, W in use)
_pacc           dc.b    0               ; its access noted
_pswap          dc.b    0               ; a swap in the presentation frame
        even
P_T0    equ     _pt0-_pvars
P_TA    equ     _pta-_pvars
P_TB    equ     _ptb-_pvars
P_PRE   equ     _ppre-_pvars
P_TAIL  equ     _ptail-_pvars
P_LASTT equ     _plastt-_pvars
P_FRAMES equ    _pframes-_pvars
P_ON    equ     _pon-_pvars
P_IN    equ     _pin-_pvars
P_TIMED equ     _ptimed-_pvars
P_ACC   equ     _pacc-_pvars
P_SWAP  equ     _pswap-_pvars

**********************************************
; The camera between the followed object's runs (docs/performance.md, plan step 8). The
; 3D view (in MAIN's frame, +$eda8; its camera at +22/24/26, its angles at +52/54/56)
; follows an object (+96; flags +132, bit 0 the position, bit 1 the angles): hunk 1 +$48b8
; sets the camera from the object's pose and marks the view changed (bit 7 of +0), so it
; changes only when that object has run, every 9 fields for the player. At each list's end
; (_listend) _isample reads the object's pose as +$48b8 does (the position words +0/+8/+16,
; the angles +24/+32/+40 plus +64/+68/+72); a new pose keeps the one before it and the
; world count W of the change. Before the drawing (+$4b8e jsr +$a3a6 becomes jsr _view)
; the camera is moved back by (cur - prev) x (1 - alpha), alpha = (W - W of cur) / the
; change's interval (at most the object's period on the cap's grid), angles the short way
; round; when that camera differs from the last one drawn the view is marked changed, it is
; drawn, and the camera is put back. A frame drawn only for the staging takes the changed
; path after the drawing (+$4b94: the other views and the swap), so the unchanged path's
; per-frame flags and countdown (+$4ba8-+$4be6: +$eef5, +$ef2b, +$ef2a) are done here for
; it. A change more than the interval after the one before (the object was standing) is
; staged with (1 + alpha) / 2: half of it in the first frame, so a key's first step shows at
; once, and the rest by the next run, where the next change takes over without a hold. No
; interpolation across a jump (a position step over I_JUMP or an angle over 45 degrees), for a new view or followed object, or outside 3D mode (W not in use).
; INTERP_OFF (a test define): alpha always 1, the frames those of plan step 7.

I_JUMP  equ     128

; a2 the view, a1 START's element table (+$ed86)
_view   movem.l d0-d7/a0-a1/a3-a4,-(a7)
        lea     _ivars(pc),a3
        lea     .cam(pc),a1
        lea     I_OFF(a3),a4
        clr.l   (a4)+
        clr.l   (a4)+
        clr.l   (a4)
        bsr     _pcclr
        cmp.l   I_VIEW(a3),a2
        beq     .same
        move.l  a2,I_VIEW(a3)
        sf      I_VALID(a3)
        sf      I_DRAWN(a3)
        sf      I_STAGED(a3)
        bra     .staged
.same   lea     _wvars(pc),a0
        tst.b   W_ON(a0)
        beq     .staged
        tst.b   I_VALID(a3)
        beq     .staged
        IFND INTERP_OFF
        move.w  96(a2),d0
        bmi     .staged
        move.l  _wvars+W_OBJTAB(pc),a0
        move.l  (a0),a0
        move.l  (a0,d0.w),d0
        cmp.l   I_OBJ(a3),d0
        bne     .staged
        move.l  _wvars+W_DRAWT(pc),d6
        sub.l   I_WR(a3),d6             ; alpha's numerator
        move.l  I_DEN(a3),d7
        cmp.l   d7,d6
        bhs     .staged                 ; alpha 1 (or before the change: none)
        tst.b   I_START(a3)
        beq     .lin
        add.l   d7,d6                   ; from standing: (1 + alpha) / 2
        add.l   d7,d7
.lin
        moveq   #0,d5
.off    move.w  I_CUR(a3,d5.w),d0
        sub.w   I_PREV(a3,d5.w),d0      ; the step
        cmp.w   #6,d5
        blo     .pos
        cmp.w   #180,d0
        ble     .a1
        sub.w   #360,d0
.a1     cmp.w   #-180,d0
        bge     .a2
        add.w   #360,d0
.a2     btst    #1,132(a2)
        bra     .part
.pos    btst    #0,132(a2)
.part   beq     .next
        cmp.w   #6,d5
        bhs     .ang
        move.w  d0,d1                   ; a position: in 1/64 units
        ext.l   d1
        muls.l  d6,d1
        asl.l   #6,d1
        divs.l  d7,d1
        ext.l   d0
        asl.l   #6,d0
        sub.l   d0,d1                   ; step x alpha - step
        move.l  d1,d0
        asr.l   #6,d0
        move.w  d0,I_OFF(a3,d5.w)       ; whole units, down
        and.w   #63,d1
        bsr     _pcam                   ; the fraction, for the projection (src/proj020.s)
        bra     .next
.ang    move.w  d0,d1
        muls.w  d6,d1
        divs.w  d7,d1
        sub.w   d0,d1                   ; step x alpha - step
        move.w  d1,I_OFF(a3,d5.w)
.next   addq.w  #2,d5
        cmp.w   #12,d5
        blo     .off
        ENDC
.staged moveq   #0,d4                   ; the staged camera: d4 differs from the last drawn
        moveq   #0,d3                   ; d3 offsets
        moveq   #0,d5
.stage  move.w  (a1,d5.w),d0
        move.w  (a2,d0.w),d1
        move.w  d1,I_SAVE(a3,d5.w)
        move.w  I_OFF(a3,d5.w),d2
        or.w    d2,d3
        add.w   d1,d2
        cmp.w   #6,d5
        blo     .spos
        cmp.w   #360,d2
        ble     .s1
        sub.w   #360,d2
.s1     cmp.w   #-360,d2
        bge     .spos
        add.w   #360,d2
.spos   move.w  d2,I_NEW(a3,d5.w)
        cmp.w   I_DRAWV(a3,d5.w),d2
        sne     d0
        or.b    d0,d4
        addq.w  #2,d5
        cmp.w   #12,d5
        blo     .stage
        bsr     _pcst                   ; the fractions: staged, changed
        or.w    d0,d3
        or.b    d1,d4
        tst.b   I_DRAWN(a3)
        bne     .known
        st      d4
.known  tst.w   d3                      ; staged now, or the last drawn was
        bne     .need
        tst.b   I_STAGED(a3)
        bne     .need
        moveq   #0,d4
.need   bsr     _eplan                  ; the other moving objects (step 9)
        beq     .eno
        st      d4
.eno    moveq   #0,d6                   ; d6 a frame only for the staging
        tst.b   (a2)
        bmi     .set
        tst.b   d4
        beq     .draw                   ; unchanged: as START
        bset    #7,(a2)
        moveq   #1,d6
        move.w  14(a7),d0               ; d3 at entry: the view's element chain
        move.l  36(a7),a0               ; a1 at entry: START's element table
        bsr     _emark
.set    moveq   #0,d5                   ; the staged camera in, and drawn
.put    move.w  (a1,d5.w),d0
        move.w  I_NEW(a3,d5.w),d1
        move.w  d1,(a2,d0.w)
        move.w  d1,I_DRAWV(a3,d5.w)
        addq.w  #2,d5
        cmp.w   #12,d5
        blo     .put
        st      I_DRAWN(a3)
        tst.w   d3
        sne     I_STAGED(a3)
        bsr     _pcon
        bsr     _eapply
        move.l  _wvars+W_DRAW(pc),a0
        jsr     (a0)
        bsr     _eundo
        bsr     _pcoff
        moveq   #0,d5                   ; the camera back
.back   move.w  (a1,d5.w),d0
        move.w  I_SAVE(a3,d5.w),(a2,d0.w)
        addq.w  #2,d5
        cmp.w   #12,d5
        blo     .back
        tst.b   d6
        beq     .out
        move.l  _wvars+W_FLAGS(pc),a0   ; +$eef5, +$ef2b, +$ef2a as +$4ba8-+$4be6
        sf      (a0)
        btst    #2,1(a2)
        beq     .f1
        move.b  #1,(a0)
.f1     sf      $ef2b-$eef5(a0)
        btst    #5,(a2)
        beq     .out
        move.b  #1,$ef2b-$eef5(a0)
        tst.b   _pvars+P_IN(pc)         ; plan step 11: per world pass
        bne     .out
        subq.b  #1,$ef2a-$eef5(a0)
        bne     .out
        st      $ef2b-$eef5(a0)
.out    bsr     _bflush                 ; plan step 10.2: the screen brought up to date
        movem.l (a7)+,d0-d7/a0-a1/a3-a4
        rts
.draw   move.l  _wvars+W_DRAW(pc),a0
        jsr     (a0)
        bra     .out
.cam    dc.w    22,24,26,52,54,56

; the view's elements to be projected again, as +$4992-+$49ae on the game's own changes
; (an element is projected only in state 2, so one left in state 0 keeps its screen
; position from the last change): each in state 0 with byte +33 not negative set to 2.
; d0 the view's chain (its offset in the table), a0 START's element table
_emark  move.w  6(a0,d0.w),d0
        beq     .out
        tst.b   33(a0,d0.w)
        bmi     _emark
        tst.b   (a0,d0.w)
        bne     _emark
        move.b  #2,(a0,d0.w)
        bra     _emark
.out    rts

; at each list's end, W the list's count: the followed object's pose, kept with the one
; before it when it changes
_isample
        movem.l d0-d7/a0-a3,-(a7)
        lea     _ivars(pc),a3
        lea     _wvars(pc),a1
        move.l  I_VIEW(a3),d0
        beq     .out
        move.l  d0,a2
        tst.b   W_ON(a1)
        beq     .none
        tst.b   132(a2)
        beq     .none
        move.w  96(a2),d0
        bmi     .none
        move.l  W_OBJTAB(a1),a0
        move.l  (a0),a0
        move.l  (a0,d0.w),d0
        beq     .none
        move.l  d0,a0
        lea     I_POSE(a3),a2           ; the pose as +$48b8 reads it
        move.w  (a0),(a2)+
        move.w  8(a0),(a2)+
        move.w  16(a0),(a2)+
        move.w  24(a0),d0
        add.w   64(a0),d0
        move.w  d0,(a2)+
        move.w  32(a0),d0
        add.w   68(a0),d0
        move.w  d0,(a2)+
        move.w  40(a0),d0
        add.w   72(a0),d0
        move.w  d0,(a2)
        move.l  W_W(a1),d7
        tst.b   I_VALID(a3)
        beq     .snap
        cmp.l   I_OBJ(a3),a0
        bne     .snap
        moveq   #0,d4                   ; moved
        moveq   #0,d5
.cmp    move.w  I_POSE(a3,d5.w),d0
        sub.w   I_CUR(a3,d5.w),d0
        beq     .cnext
        moveq   #1,d4
        cmp.w   #6,d5
        blo     .cpos
        cmp.w   #180,d0                 ; an angle the short way round
        ble     .c1
        sub.w   #360,d0
.c1     cmp.w   #-180,d0
        bge     .c2
        add.w   #360,d0
.c2     bsr     .abs
        cmp.w   #45,d0
        bhi     .snap
        bra     .cnext
.cpos   bsr     .abs
        cmp.w   #I_JUMP,d0
        bhi     .snap
.cnext  addq.w  #2,d5
        cmp.w   #12,d5
        blo     .cmp
        tst.b   d4
        beq     .out
        move.l  I_CUR(a3),I_PREV(a3)
        move.l  I_CUR+4(a3),I_PREV+4(a3)
        move.l  I_CUR+8(a3),I_PREV+8(a3)
        move.l  d7,d0                   ; the interval: since the last change, at most
        sub.l   I_WR(a3),d0             ; the period on the cap's grid
        move.l  W_CAP(a1),a2
        moveq   #0,d1
        move.b  (a2),d1
        beq     .none
        moveq   #0,d2
        move.w  -58(a0),d2              ; period + 1 rounded up to the cap
        addq.l  #1,d2
        add.l   d1,d2
        subq.l  #1,d2
        divu.w  d1,d2
        mulu.w  d1,d2
        tst.l   d0
        ble     .grid
        cmp.l   d2,d0
        bls     .den
        st      I_START(a3)             ; longer: from standing, half shown at once
        move.l  d2,d0
        bra     .den1
.grid   move.l  d2,d0
.den    sf      I_START(a3)
.den1   move.l  d0,I_DEN(a3)
        bra     .keep
.snap   move.l  a0,I_OBJ(a3)            ; a jump, or a new object: no interpolation
        st      I_VALID(a3)
        sf      I_START(a3)
        move.l  I_POSE(a3),I_PREV(a3)
        move.l  I_POSE+4(a3),I_PREV+4(a3)
        move.l  I_POSE+8(a3),I_PREV+8(a3)
.keep   move.l  I_POSE(a3),I_CUR(a3)
        move.l  I_POSE+4(a3),I_CUR+4(a3)
        move.l  I_POSE+8(a3),I_CUR+8(a3)
        move.l  d7,I_WR(a3)
.out    movem.l (a7)+,d0-d7/a0-a3
        rts
.none   sf      I_VALID(a3)
        bra     .out
.abs    tst.w   d0
        bpl     .abs1
        neg.w   d0
.abs1   rts

**********************************************
; The other moving objects between their runs (docs/performance.md, plan step 9). After an
; object's run +$4792 moves its 3D elements (+$ed86's table, chained from -24(a6) through
; +4) by the pose's difference and sets their heading (+36) to the object's (+40): hunk 1
; +$4880 movea.l <+$ed86>,a1, reached only when the object moved or turned (d4-d6 the
; position's step, d7 the heading, +$edb8 the heading before the run), becomes jsr _emove,
; which keeps the step, the world count and the interval (as _isample's) for up to ESLOTS
; objects. _view stages them for the drawing (_eplan, _eapply, _eundo): each element moved
; back by step x (1 - alpha), its heading too where it is the object's, and put back after
; it. While the camera stays, a frame is drawn for the staging only when a staged element's
; screen box (+12/+14, size +40/+42, +16 negative when not projected) meets the view's
; (+14/+16, size +18/+20); the game's own redraw of a moved element's region (+$4be8,
; +$5094) stays for the rest. A slot's object is looked up in MAIN's object table at each
; drawing, so a freed object is dropped. No interpolation across a jump (as _isample's).

ESLOTS  equ     8
ESIZE   equ     40
; a slot: +0 the object (0 free), +4 W of the move, +8 the interval, +12/14/16 the position's
; step, +18 the heading's, +20 the heading after it, +22 staged in the last frame drawn,
; +24/26/28/30 the offsets (position, heading; whole units, down), +32 the staged heading,
; +34/36/38 the position offsets' fractions (1/64 units)

; at +$4880: a6 the object, d4-d6 the step, d7 the heading; a1 START's element table out
_emove  move.l  _wvars+W_ELEM(pc),a1
        move.l  (a1),a1
        movem.l d0-d3/a0/a2-a3,-(a7)
        lea     _wvars(pc),a0
        tst.b   W_ON(a0)
        beq     .out
        move.l  W_ETAB(a0),d0
        beq     .out
        tst.w   -24(a6)
        beq     .out
        move.l  d0,a3
        move.l  W_PREVH(a0),a2
        move.w  d7,d3
        sub.w   (a2),d3                 ; the heading's step, the short way round
        cmp.w   #180,d3
        ble     .h1
        sub.w   #360,d3
.h1     cmp.w   #-180,d3
        bge     .h2
        add.w   #360,d3
.h2     moveq   #0,d2                   ; d2 a jump
        move.w  d4,d0
        bsr     .big
        move.w  d5,d0
        bsr     .big
        move.w  d6,d0
        bsr     .big
        move.w  d3,d0
        bpl     .h3
        neg.w   d0
.h3     cmp.w   #45,d0
        shi     d0
        or.b    d0,d2
        sub.l   a2,a2                   ; a2 the object's slot, a1 kept: a free one
        moveq   #ESLOTS-1,d1
.find   cmp.l   (a3),a6
        beq     .found
        tst.l   (a3)
        bne     .nf
        move.l  a2,d0
        bne     .nf
        move.l  a3,a2
.nf     lea     ESIZE(a3),a3
        dbf     d1,.find
        tst.b   d2
        bne     .out
        move.l  a2,d0
        beq     .out                    ; no room: drawn as moved
        move.l  d0,a3
        clr.w   22(a3)
        move.l  W_W(a0),d0
        bsr     .grid
        move.l  d1,d0
        bra     .set
.found  tst.b   d2
        beq     .again
        clr.l   (a3)                    ; a jump: as moved, and put back if it was staged
        bra     .out
.again  move.l  W_W(a0),d0
        sub.l   4(a3),d0                ; since the last move, at most the grid
        bsr     .grid
        tst.l   d0
        ble     .g
        cmp.l   d1,d0
        bls     .set
.g      move.l  d1,d0
.set    move.l  a6,(a3)
        move.l  W_W(a0),4(a3)
        move.l  d0,8(a3)
        movem.w d4-d6,12(a3)
        move.w  d3,18(a3)
        move.w  d7,20(a3)
.out    movem.l (a7)+,d0-d3/a0/a2-a3
        rts
; d0 a step: d2 set when it is a jump
.big    tst.w   d0
        bpl     .b1
        neg.w   d0
.b1     cmp.w   #I_JUMP,d0
        shi     d0
        or.b    d0,d2
        rts
; d1 the object's period on the cap's grid (a0 _wvars, a6 the object)
.grid   movem.l d0/a1,-(a7)
        move.l  W_CAP(a0),a1
        moveq   #0,d0
        move.b  (a1),d0
        bne     .g1
        moveq   #1,d0
.g1     moveq   #0,d1
        move.w  -58(a6),d1
        addq.l  #1,d1
        add.l   d0,d1
        subq.l  #1,d1
        divu.w  d0,d1
        mulu.w  d0,d1
        movem.l (a7)+,d0/a1
        rts

; a2 the view: the slots' offsets for this drawing; d0.b set when a frame is needed for
; them (a staged element in view, or the last frame drawn staged and the move now done)
_eplan  movem.l d1-d7/a0-a1/a3-a4,-(a7)
        moveq   #0,d0
        lea     _wvars(pc),a0
        move.l  W_ETAB(a0),d1
        beq     .out
        move.l  d1,a3
        move.l  W_ELEM(a0),a1
        move.l  (a1),a1
        moveq   #ESLOTS-1,d7
.slot   move.l  (a3),d1
        beq     .next
        bsr     _elive
        bne     .free
        clr.l   24(a3)
        clr.l   28(a3)
        clr.w   32(a3)
        clr.l   34(a3)
        clr.w   38(a3)
        tst.b   W_ON(a0)
        beq     .done
        move.l  W_DRAWT(a0),d5
        sub.l   4(a3),d5                ; alpha's numerator
        move.l  8(a3),d6
        cmp.l   d6,d5
        bhs     .done
        moveq   #0,d3                   ; any offset
        moveq   #0,d2
.off    move.w  12(a3,d2.w),d1
        cmp.w   #6,d2
        bhs     .offh
        move.w  d1,d4                   ; a position: in 1/64 units
        ext.l   d4
        muls.l  d5,d4
        asl.l   #6,d4
        divs.l  d6,d4
        ext.l   d1
        asl.l   #6,d1
        sub.l   d1,d4                   ; step x alpha - step
        move.l  d4,a4
        asr.l   #6,d4
        move.w  d4,24(a3,d2.w)          ; whole units, down
        or.w    d4,d3
        move.l  a4,d4
        and.w   #63,d4
        move.w  d4,34(a3,d2.w)          ; the fraction
        or.w    d4,d3
        bra     .onext
.offh   move.w  d1,d4
        muls.w  d5,d4
        divs.w  d6,d4
        sub.w   d1,d4                   ; step x alpha - step
        move.w  d4,24(a3,d2.w)
        or.w    d4,d3
.onext  addq.w  #2,d2
        cmp.w   #8,d2
        blo     .off
        tst.w   d3
        beq     .done
        bsr     _evis
        beq     .next
        st      d0
        bra     .next
.done   tst.b   22(a3)                  ; the move done: a last frame if it was staged
        beq     .free
        bsr     _evis
        beq     .free
        st      d0
        bra     .next
.free   clr.l   (a3)
.next   lea     ESIZE(a3),a3
        dbf     d7,.slot
.out    movem.l (a7)+,d1-d7/a0-a1/a3-a4
        tst.b   d0
        rts

; a3 a slot (its object live): Z clear when one of its elements' screen box meets the view's
; (a2), a1 START's element table
_evis   movem.l d0-d5/a4,-(a7)
        move.l  (a3),a4
        move.w  -24(a4),d1
.el     beq     .no
        tst.w   16(a1,d1.w)
        bmi     .nx
        move.w  12(a1,d1.w),d2          ; x
        move.w  d2,d3
        add.w   40(a1,d1.w),d3
        move.w  14(a2),d4
        cmp.w   d4,d3
        blt     .nx
        add.w   18(a2),d4
        cmp.w   d4,d2
        bgt     .nx
        move.w  14(a1,d1.w),d2          ; y
        move.w  d2,d3
        add.w   42(a1,d1.w),d3
        move.w  16(a2),d4
        cmp.w   d4,d3
        blt     .nx
        add.w   20(a2),d4
        cmp.w   d4,d2
        bgt     .nx
        moveq   #1,d0
        bra     .ret
.nx     move.w  4(a1,d1.w),d1
        bra     .el
.no     moveq   #0,d0
.ret    movem.l (a7)+,d0-d5/a4
        rts

; d1 an object frame: Z set when it is in MAIN's object table
_elive  movem.l d0/a0,-(a7)
        move.l  _wvars+W_OBJTAB(pc),a0
        move.l  (a0),a0
        moveq   #0,d0
.e      cmp.l   (a0,d0.w),d1
        beq     .ret
        move.w  4(a0,d0.w),d0
        bne     .e
        moveq   #1,d0                   ; Z clear
.ret    movem.l (a7)+,d0/a0
        rts

; the offsets in (d0 0) or out (d0 1) for the slots _eplan gave offsets
_eapply bsr     _pfclr                  ; the fractions' table (src/proj020.s)
        moveq   #0,d0
        bra     _estage
_eundo  moveq   #1,d0
_estage movem.l d0-d7/a0-a1/a3-a4,-(a7)
        lea     _wvars(pc),a0
        move.l  W_ETAB(a0),d1
        beq     .out
        move.l  d1,a3
        move.l  W_ELEM(a0),a1
        move.l  (a1),a1
        moveq   #ESLOTS-1,d7
.slot   tst.l   (a3)
        beq     .next
        tst.b   d0                      ; in: the elements' fractions to the table
        bne     .nof
        movem.w 34(a3),d2-d4
        move.w  d2,d6
        or.w    d3,d6
        or.w    d4,d6
        beq     .nof
        move.l  (a3),a4
        move.w  -24(a4),d1
.fe     beq     .nof
        lea     (a1,d1.w),a4
        bsr     _pfadd
        move.w  4(a4),d1
        bra     .fe
.nof    movem.w 24(a3),d2-d5            ; the offsets
        move.w  d2,d6
        or.w    d3,d6
        or.w    d4,d6
        or.w    d5,d6
        bne     .some
        tst.b   d0                      ; none: after the drawing, a done move's slot freed
        beq     .clr
        move.l  W_DRAWT(a0),d6
        sub.l   4(a3),d6
        cmp.l   8(a3),d6
        blo     .next
        clr.l   (a3)
        bra     .next
.clr    sf      22(a3)
        bra     .next
.some   tst.b   d0
        bne     .neg
        st      22(a3)
        move.w  20(a3),d6               ; the staged heading
        add.w   d5,d6
        cmp.w   #360,d6
        ble     .n1
        sub.w   #360,d6
.n1     cmp.w   #-360,d6
        bge     .n2
        add.w   #360,d6
.n2     move.w  d6,32(a3)
        bra     .walk
.neg    neg.w   d2
        neg.w   d3
        neg.w   d4
.walk   move.l  (a3),a4
        move.w  -24(a4),d1
.el     beq     .next
        add.w   d2,22(a1,d1.w)
        add.w   d3,24(a1,d1.w)
        add.w   d4,26(a1,d1.w)
        tst.w   d5
        beq     .nx
        move.w  36(a1,d1.w),d6
        tst.b   d0
        bne     .hb
        cmp.w   20(a3),d6
        bne     .nx
        move.w  32(a3),36(a1,d1.w)
        bra     .nx
.hb     cmp.w   32(a3),d6
        bne     .nx
        move.w  20(a3),36(a1,d1.w)
.nx     move.w  4(a1,d1.w),d1
        bra     .el
.next   lea     ESIZE(a3),a3
        dbf     d7,.slot
.out    movem.l (a7)+,d0-d7/a0-a1/a3-a4
        rts

**********************************************
; The map in fast memory (docs/performance.md, plan step 10.2). The landscape (hunk 1
; +$d88c) reads the map, a script object's grid of word cells (512 rows of 256 in the
; jungle, 256 KB in the resource heap in chip), through the row table at <+$a1de>, which it
; loads once at +$d908; the spans and the far samples read it through the landscape's cell
; pointers. The row table's allocation (+$a30e, jsr _fastalloc since plan step 3) becomes
; jsr _rowalloc, which asks the fast pool for a fast row table and a copy of the map behind
; START's table in the same block, freed with it (when they do not fit, START's table alone
; as before); +$d908 movea.l <+$a1de>,a2 becomes jsr _maprows, which gives the landscape
; the fast table while START's table is that block, the copy at the map's address modulo
; 16 (+$b986 uses bit 1 of a cell's address). The copy is made again in full when the map's
; address, size or stride changes, after the fill op (+$3b74) wrote it and after a map
; object's set-up (+$3540); the rectangle op's writes (+$3b22) are copied at the next call;
; and the row after the map (the shading reads the next row, +$ba8e) is copied at every
; call. The two reads at a tile's offset from a cell (+$de74, +$df78: types with a negative
; flag stand on another cell, 89,192 bytes on in the jungle) go back to the original, so
; no offset leaves the copy. A map that has grown past the block, or an irregular row
; table: START's own table. MAPCHECK (a test define): every call compares the whole copy
; with the map after the update, counting differing longwords in M_BAD.

_mappatch
        move.l  _hunk1(pc),a0
        lea     .sites(pc),a2
.chk    move.l  (a2)+,d0
        beq     .ok
        move.l  (a2)+,d2
        move.l  (a2)+,d3
        cmp.l   (a0,d0.l),d2
        bne     .no
        cmp.l   4(a0,d0.l),d3
        bne     .no
        bra     .chk
.ok     cmp.w   #$2479,$d908(a0)        ; movea.l <+$a1de>,a2
        bne     .no
        move.l  a0,d0
        add.l   #$a1de,d0
        cmp.l   $d90a(a0),d0
        bne     .no
        lea     _mvars(pc),a2
        move.l  d0,M_TABA(a2)
        cmp.w   #$4eb9,$a30e(a0)        ; the row table's allocation: _fastalloc (plan step
        bne     .no                     ; 3), with a fast pool
        lea     _fastalloc(pc),a1
        cmp.l   $a310(a0),a1
        bne     .no
        lea     _rowalloc(pc),a1
        move.l  a1,$a310(a0)
        lea     .jsrs(pc),a2
.put    move.l  (a2)+,d0
        beq     .done
        move.l  (a2)+,d1
        move.w  #$4eb9,(a0,d0.l)
        lea     .jsrs(pc,d1.l),a1
        move.l  a1,2(a0,d0.l)
        tst.l   (a2)+
        beq     .put
        move.w  #$4e71,6(a0,d0.l)       ; nop
        bra     .put
.done   move.l  a0,d0                   ; the shade table: its set-up and its two reads
        add.l   #$ef3c,d0
        cmp.w   #$23c9,$30b4(a0)        ; move.l a1,<+$ef3c>
        bne     .fl
        cmp.l   $30b6(a0),d0
        bne     .fl
        cmp.w   #$2079,$baac(a0)        ; movea.l <+$ef3c>,a0
        bne     .fl
        cmp.l   $baae(a0),d0
        bne     .fl
        cmp.w   #$2079,$be7e(a0)
        bne     .fl
        cmp.l   $be80(a0),d0
        bne     .fl
        lea     _mvars(pc),a2
        move.l  d0,S_TABA(a2)
        move.w  #$4eb9,$30b4(a0)
        lea     _shadeset(pc),a1
        move.l  a1,$30b6(a0)
        lea     _sshade(pc),a1
        move.l  a1,$baae(a0)
        move.l  a1,$be80(a0)
.fl     move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts
.sites  dc.l    $de74,$34311016,$d1f11010       ; move.w (22,a1,d1.w),d2; adda.l (16,a1,d1.w),a0
        dc.l    $df78,$d1f11010,$34311016
        dc.l    $3b22,$43f10800,$3228fc3c       ; lea (0,a1,d0.l),a1; move.w -964(a0),d1
        dc.l    $3b74,$22484a29,$ffff6a00       ; movea.l a0,a1; tst.b -1(a1); bpl.w
        dc.l    $3540,$217c0000,$0004fc24       ; move.l #4,-988(a0)
        dc.l    0
; site, routine (from .jsrs), a nop after the jsr
.jsrs   dc.l    $d908,_maprows-.jsrs,0
        dc.l    $de74,_mapoff-.jsrs,1
        dc.l    $df78,_mapoff-.jsrs,1
        dc.l    $3b22,_maprect-.jsrs,1
        dc.l    $3b74,_mapfill-.jsrs,0
        dc.l    $3540,_mapinit-.jsrs,1
        dc.l    0

; a1 (and a3) the map's object: a2 the row table for the landscape
_maprows
        movem.l d0-d7/a0-a1/a3-a6,-(a7)
        lea     _mvars(pc),a4
        move.l  M_TABA(a4),a5
        move.l  (a5),a5                 ; START's row table
        move.l  a5,a2
        bsr     _shadeupd
        cmp.l   M_ROWBLK(a4),a5         ; the block _rowalloc extended
        bne     .orig
        moveq   #0,d6
        move.w  -972(a1),d6             ; the rows
        cmp.l   #2,d6
        blo     .orig
        cmp.l   M_ROWS(a4),d6
        bhi     .orig
        move.l  (a5),d0                 ; the map
        move.l  4(a5),d7
        sub.l   d0,d7                   ; the stride
        ble     .orig
        cmp.l   #1020,d7
        bhi     .orig
        move.l  d6,d1
        subq.l  #1,d1
        move.l  d1,d2
        mulu.w  d7,d2
        add.l   d0,d2
        lsl.l   #2,d1
        cmp.l   (a5,d1.l),d2            ; a regular table
        bne     .orig
        move.l  d6,d5
        mulu.w  d7,d5                   ; the size
        move.l  d0,d1
        and.l   #15,d1                  ; the copy's offset in its room
        add.l   d5,d1
        add.l   d7,d1
        addq.l  #4,d1
        cmp.l   M_BUFSIZE(a4),d1
        bhi     .orig
        tst.b   M_FULL(a4)
        bne     .full
        cmp.l   M_ORIG(a4),d0
        bne     .full
        cmp.l   M_SIZE(a4),d5
        bne     .full
        move.l  d5,d1
        add.l   d7,d1
        addq.l  #4,d1
        cmp.l   M_SPAN(a4),d1           ; the stride
        bne     .full
        move.l  M_HI(a4),d2             ; the rectangle op's writes
        beq     .margin
        move.l  M_LO(a4),d1
        cmp.l   d5,d2
        bls     .h
        move.l  d5,d2
.h      cmp.l   d2,d1
        bhs     .clean
        bsr     .copy
.clean  clr.l   M_HI(a4)
        bra     .margin
.full   sf      M_FULL(a4)
        clr.l   M_HI(a4)
        move.l  d0,M_ORIG(a4)
        move.l  d5,M_SIZE(a4)
        move.l  d5,d1
        add.l   d7,d1
        addq.l  #4,d1
        move.l  d1,M_SPAN(a4)
        move.l  d0,d1
        moveq   #15,d2
        and.l   d2,d1
        add.l   M_BUF(a4),d1
        move.l  d1,M_COPY(a4)
        moveq   #0,d1
        move.l  d5,d2
        bsr     .copy
        move.l  M_COPY(a4),d3           ; the fast table: START's entries moved to the copy
        sub.l   d0,d3
        move.l  M_TAB(a4),a0
        move.l  a5,a6
        move.l  d6,d1
        subq.w  #1,d1
.t      move.l  (a6)+,d4
        add.l   d3,d4
        move.l  d4,(a0)+
        dbf     d1,.t
.margin move.l  d5,d1                   ; the row after the map
        move.l  M_SPAN(a4),d2
        bsr     .copy
        IFD MAPCHECK
        addq.l  #1,M_CALLS(a4)
        move.l  M_ORIG(a4),a0
        move.l  M_COPY(a4),a1
        move.l  d5,d1
        lsr.l   #2,d1
.k      cmpm.l  (a0)+,(a1)+
        beq     .k1
        addq.l  #1,M_BAD(a4)
.k1     subq.l  #1,d1
        bne     .k
        ENDC
        move.l  M_TAB(a4),a2
        movem.l (a7)+,d0-d7/a0-a1/a3-a6
        rts
.orig   clr.l   M_ORIG(a4)
        clr.l   M_SIZE(a4)
        clr.l   M_SPAN(a4)
        movem.l (a7)+,d0-d7/a0-a1/a3-a6
        rts
; the map's bytes d1 to d2 into the copy (the two equal modulo 16)
.copy   movem.l d1-d2/a0-a1,-(a7)
        move.l  M_ORIG(a4),a0
        move.l  M_COPY(a4),a1
        add.l   d1,a0
        add.l   d1,a1
        sub.l   d1,d2
        beq     .cend
.cb     move.l  a0,d1
        and.w   #3,d1
        beq     .cl
        move.b  (a0)+,(a1)+
        subq.l  #1,d2
        bne     .cb
        bra     .cend
.cl     move.l  d2,d1
        lsr.l   #2,d1
        beq     .ct
.cll    move.l  (a0)+,(a1)+
        subq.l  #1,d1
        bne     .cll
.ct     and.w   #3,d2
        beq     .cend
.ctb    move.b  (a0)+,(a1)+
        subq.w  #1,d2
        bne     .ctb
.cend   movem.l (a7)+,d1-d2/a0-a1
        rts

; +$a30e: d0 the row table's size (4 x the rows), a3 the map's object: START's table, then
; the fast table and the copy (the map, the row after it, the alignment) in one block from
; the fast pool when they fit; START's table alone otherwise
_rowalloc
        movem.l d1-d4/a0-a2,-(a7)
        lea     _mvars(pc),a2
        clr.l   M_ROWBLK(a2)
        clr.l   S_BUF(a2)               ; no shade copy: the spans read the table itself
        clr.l   S_ORIG(a2)
        move.l  S_TABA(a2),d1
        beq     .ns
        move.l  d1,a0
        move.l  (a0),S_SHADE(a2)
.ns
        move.l  d0,d3                   ; START's size
        moveq   #0,d1
        move.w  -970(a3),d1
        add.l   d1,d1                   ; the stride
        moveq   #0,d2
        move.w  -972(a3),d2             ; the rows
        move.l  d2,d4
        mulu.w  d1,d2
        add.l   d1,d2
        add.l   #4+15+15,d2             ; the copy's room: its alignment and offset
        move.l  d2,d1
        add.l   d3,d2
        add.l   d3,d2
        add.l   #SHADEMAX+15,d2         ; the block, with the shade table's copy
        move.l  _hunk1(pc),a1           ; room in the fast pool (as _fastalloc)
        move.l  $100(a1),d0
        beq     .start
        sub.l   d2,d0
        subq.l  #8,d0
        and.w   #-16,d0
        cmp.l   $ed82(a1),d0
        blo     .start
        move.l  d2,d0
        bsr     _fastalloc
        tst.l   d0
        beq     .out
        move.l  d0,a0
        move.l  (a0),a0                 ; the block
        move.l  a0,M_ROWBLK(a2)
        move.l  d4,M_ROWS(a2)
        add.l   d3,a0
        move.l  a0,M_TAB(a2)
        add.l   d3,a0
        move.l  a0,d2
        add.l   #15,d2
        and.w   #-16,d2
        move.l  d2,S_BUF(a2)
        move.l  d2,a0
        lea     SHADEMAX(a0),a0
        move.l  a0,d2
        add.l   #15,d2
        and.w   #-16,d2
        move.l  d2,M_BUF(a2)
        sub.l   a0,d2
        sub.l   d2,d1
        move.l  d1,M_BUFSIZE(a2)
        clr.l   M_ORIG(a2)
        clr.l   M_SIZE(a2)
        clr.l   M_SPAN(a2)
        bra     .out
.start  move.l  d3,d0
        bsr     _fastalloc
.out    movem.l (a7)+,d1-d4/a0-a2
        rts

; +$de74, +$df78: a0 a cell, a1 the tile table, d1 the tile's entry; a0 back in the map
_mapoff move.l  d0,-(a7)
        move.l  a0,d0
        sub.l   _mvars+M_COPY(pc),d0
        cmp.l   _mvars+M_SPAN(pc),d0
        bhs     .o
        add.l   _mvars+M_ORIG(pc),d0
        move.l  d0,a0
.o      move.l  (a7)+,d0
        move.w  22(a1,d1.w),d2
        adda.l  16(a1,d1.w),a0
        rts

; +$3b22, the rectangle op: a1 its first word, d1 the grid's stride, d7+1 columns of up to
; d6+2 rows: the bytes it writes kept to be copied when the grid is the map
_maprect
        lea     0(a1,d0.l),a1
        move.w  -964(a0),d1
        movem.l d0/d2-d3/a2,-(a7)
        lea     _mvars(pc),a2
        move.l  a1,d0
        sub.l   M_ORIG(a2),d0
        cmp.l   M_SIZE(a2),d0
        bhs     .out
        move.w  d6,d2
        ext.l   d2
        bpl     .r
        moveq   #0,d2
.r      addq.l  #2,d2
        mulu.w  d1,d2
        add.l   d0,d2
        moveq   #0,d3
        move.w  d7,d3
        addq.l  #1,d3
        add.l   d3,d3
        add.l   d3,d2
        tst.l   M_HI(a2)
        beq     .set
        cmp.l   M_LO(a2),d0
        bhs     .l1
        move.l  d0,M_LO(a2)
.l1     cmp.l   M_HI(a2),d2
        bls     .out
        move.l  d2,M_HI(a2)
        bra     .out
.set    move.l  d0,M_LO(a2)
        move.l  d2,M_HI(a2)
.out    movem.l (a7)+,d0/d2-d3/a2
        rts

; +$3b74, the fill op: a0 the grid's object; the copy made again when it is the map
_mapfill
        movea.l a0,a1
        movem.l d0/a2,-(a7)
        move.l  a1,d0
        tst.b   -1(a1)
        bpl     .d
        move.l  (a1),a2
        move.l  (a2),d0
.d      lea     _mvars(pc),a2
        cmp.l   M_ORIG(a2),d0
        bne     .x
        st      M_FULL(a2)
.x      movem.l (a7)+,d0/a2
        tst.b   -1(a1)
        rts

; +$3540, a grid object's set-up: the copy made again
_mapinit
        move.l  #4,-988(a0)
        move.l  a2,-(a7)
        lea     _mvars(pc),a2
        st      M_FULL(a2)
        move.l  (a7)+,a2
        rts

; +$30b4 move.l a1,<+$ef3c>, the end of the view's shade set-up: a0 the view, a1 the table
; (16 levels of 256 colours in the jungle), 160(a0) its levels, 158(a0) the far level.
; Each drawing's shading steps from a start level (levels - 1, 6, 0 or the far level) to
; the far level over the rows and three steps on (+$dcc2, +$de18), each step a fraction of
; a level, so it reads the table's first max(levels, far + 1, 7) levels: copied when that
; is the table, with a level to spare above the far level of every set-up so far
_shadeset
        movem.l d0-d1/a2-a3,-(a7)
        lea     _mvars(pc),a2
        move.l  a1,S_SHADE(a2)
        clr.l   S_ORIG(a2)
        clr.l   S_N(a2)
        move.w  158(a0),d1
        bmi     .no
        cmp.w   S_FAR(a2),d1
        bls     .f
        move.w  d1,S_FAR(a2)
.f      moveq   #0,d0
        move.w  160(a0),d0
        move.w  S_FAR(a2),d1
        addq.w  #1,d1
        cmp.w   d1,d0
        bls     .no
        cmp.w   #7,d0
        blo     .no
        cmp.w   #SHADEMAX/256,d0
        bhi     .no
        lsl.l   #8,d0
        move.l  d0,S_N(a2)
.no     move.l  S_TABA(a2),a3
        move.l  a1,(a3)                 ; the original's store and flags
        movem.l (a7)+,d0-d1/a2-a3
        rts

; from _maprows, a4 _mvars, a5 START's row table: the spans' table, the copy when the row
; table is _rowalloc's block and the set-up allowed it, the table itself otherwise
_shadeupd
        move.l  S_TABA(a4),d0
        beq     .x
        movem.l d0-d1/a0-a1,-(a7)
        move.l  d0,a0
        move.l  (a0),d0                 ; the table
        cmp.l   M_ROWBLK(a4),a5
        bne     .t
        move.l  S_N(a4),d1
        beq     .t
        move.l  S_BUF(a4),a1
        move.l  a1,d1
        beq     .t
        cmp.l   S_ORIG(a4),d0
        beq     .c
        move.l  d0,a0
        move.l  S_N(a4),d1
        lsr.l   #2,d1
        subq.w  #1,d1
.l      move.l  (a0)+,(a1)+
        dbf     d1,.l
        move.l  d0,S_ORIG(a4)
.c
        IFD MAPCHECK
        move.l  d0,a0
        move.l  S_BUF(a4),a1
        move.l  S_N(a4),d1
        lsr.l   #2,d1
        subq.w  #1,d1
.k      cmpm.l  (a0)+,(a1)+
        beq     .k1
        addq.l  #1,S_BAD(a4)
.k1     dbf     d1,.k
        addq.l  #1,S_CALLS(a4)
        ENDC
        move.l  S_BUF(a4),d0
.t      move.l  d0,S_SHADE(a4)
        movem.l (a7)+,d0-d1/a0-a1
.x      rts

**********************************************
; The swap without the beam wait (docs/performance.md, plan step 10.2). START's 3D swap
; (hunk 1 +$4b30 jsr <hunk 0 +$13e0>) waits for line 256 (+$13ce), writes the plane pointers
; at the copper list's start (+$13f6) and clears INTENA's COPER bit, which the list's next
; move after the pointers sets again: a pass's start (+$49cc jsr <hunk 0 +$13c0>) waits for
; that bit, the new screen shown, and then (+$4a0a-+$4a7c) for the VBL's pointer redraw on it
; (+$4a14, <+$ed99>), copies last pass's rectangles from the shown screen into the back one
; (+$525a), puts back the background under the pointer there (hunk 2 +$4ec) and empties the
; rectangle list (+$4a76). The copper takes the pointers at the field's start, so the line
; does not change the field the frame shows in; the passes' waits only kept the next
; drawing from starting. Here:
; - +$4b30 becomes jsr _swap: the pointers written at once, the bit cleared, except within
;   the lines where the copper takes them (310 to 1)
; - +$49cc becomes jsr _pstart: the wait and the block put off (<+$edd0> set: both as before)
; - +$4a0a tst.b <+$ed97> becomes jmp _pblock: the block, unless put off, then +$4a80
; - the block put off (_bflush) runs before the pass's first access to the back screen: the
;   conversion's (hunk 2 +$2e02 movea.l <+$10>,a1 becomes jsr _c2pld), a 2D view's (+$4b5e
;   movea.l <+$ed86>,a1 becomes jsr _viewent), the 3D view's drawing's end (_view), the
;   views' end (+$4ada clr.b <+$edcf> becomes jsr _vend)
; - the other loads of the back screen (<+$10>) in hunks 0 and 2 that draw into it (text,
;   rectangles, blits: _gsites) wait for the swap to show first (_bshow), so nothing the
;   scripts draw between the swap and the field's start shows on the old screen; not
;   +$4fc, the VBL's pointer, which runs at the field's start.
; All checked first; with _worldpatch's _view.

_swappatch
        move.l  _hunk1(pc),a0
        move.l  _hunk2(pc),a3
        lea     _bvars(pc),a2
        tst.l   _wvars+W_DRAW(pc)
        beq     .no
        cmp.w   #$4eb9,$49cc(a0)
        bne     .no
        move.l  $49ce(a0),d0            ; hunk 0 +$13c0
        move.l  d0,B_13C0(a2)
        move.l  d0,a1
        sub.w   #$13c0,a1               ; hunk 0
        cmp.l   #$08390004,$13c0(a1)    ; btst #4,$dff01d
        bne     .no
        cmp.l   #$00dff01d,$13c4(a1)
        bne     .no
        lea     $13e0(a1),a4            ; the swap: jsr +$13ce, jsr +$13f6, move.w #$10,$dff09a
        cmp.w   #$4eb9,(a4)
        bne     .no
        lea     $13ce(a1),a5
        cmp.l   2(a4),a5
        bne     .no
        cmp.w   #$4eb9,6(a4)
        bne     .no
        lea     $13f6(a1),a5
        cmp.l   8(a4),a5
        bne     .no
        move.l  a5,B_13F6(a2)
        cmp.l   #$33fc0010,12(a4)
        bne     .no
        cmp.l   #$00dff09a,16(a4)
        bne     .no
        lea     $c(a0),a5               ; the screens exchanged before it
        cmp.w   #$23c9,$4b24(a0)        ; move.l a1,<+$c>
        bne     .no
        cmp.l   $4b26(a0),a5
        bne     .no
        lea     $10(a0),a5
        cmp.w   #$23c8,$4b2a(a0)        ; move.l a0,<+$10>
        bne     .no
        cmp.l   $4b2c(a0),a5
        bne     .no
        cmp.w   #$4eb9,$4b30(a0)        ; the 3D swap
        bne     .no
        cmp.l   $4b32(a0),a4
        bne     .no
        lea     .h1(pc),a4              ; hunk 1's sites: offset, opcode, operand in hunk 1
.c1     move.l  (a4)+,d0
        beq     .c1end
        move.w  (a4)+,d1
        move.l  (a4)+,d2
        add.l   a0,d2
        cmp.w   (a0,d0.l),d1
        bne     .no
        cmp.l   2(a0,d0.l),d2
        bne     .no
        bra     .c1
.c1end  cmp.w   #$4eb9,$4a2c(a0)        ; jsr +$525a
        bne     .no
        lea     $525a(a0),a5
        cmp.l   $4a2e(a0),a5
        bne     .no
        move.l  a5,B_525A(a2)
        cmp.w   #$4eb9,$4a46(a0)        ; jsr <hunk 2 +$4ec>
        bne     .no
        lea     $4ec(a3),a5
        cmp.l   $4a48(a0),a5
        bne     .no
        move.l  a5,B_4EC(a2)
        cmp.w   #$23fc,$4a76(a0)        ; move.l #<the rectangle list>,<+$ee08>
        bne     .no
        lea     $ee08(a0),a5
        cmp.l   $4a7c(a0),a5
        bne     .no
        move.l  $4a78(a0),B_LIST(a2)
        cmp.l   #$66f85239,$4a1a(a0)    ; bne.s +$4a14, addq.b #1,<+$ed98>
        bne     .no
        cmp.w   #$2279,$2e02(a3)        ; movea.l <+$10>,a1: the conversion
        bne     .no
        lea     $10(a0),a5
        cmp.l   $2e04(a3),a5
        bne     .no
        lea     _gsites(pc),a4          ; the back screen's other loads
.cg     move.w  (a4)+,d0
        bmi     .cgend
        move.w  (a4)+,d1
        move.w  (a4)+,d2
        bsr     .site
        cmp.w   (a1),d2
        bne     .no
        cmp.l   2(a1),a5
        bne     .no
        bra     .cg
.cgend  move.w  #$4eb9,d1               ; all checked: the patches
        lea     $49cc(a0),a1
        lea     _pstart(pc),a4
        bsr     .jsr
        lea     $4ada(a0),a1
        lea     _vend(pc),a4
        bsr     .jsr
        lea     $4b30(a0),a1
        lea     _swap(pc),a4
        bsr     .jsr
        lea     $4b5e(a0),a1
        lea     _viewent(pc),a4
        bsr     .jsr
        lea     $2e02(a3),a1
        lea     _c2pld(pc),a4
        bsr     .jsr
        lea     $4a0a(a0),a1
        lea     _pblock(pc),a4
        move.w  #$4ef9,(a1)
        move.l  a4,2(a1)
        lea     _gsites(pc),a4
.pg     move.w  (a4)+,d0
        bmi     .pgend
        move.w  (a4)+,d1
        move.w  (a4)+,d2
        bsr     .site
        rol.w   #7,d2
        and.w   #7,d2                   ; the register
        mulu.w  #_g10a1-_g10a0,d2
        move.w  #$4eb9,(a1)
        lea     _g10a0(pc,d2.w),a6
        move.l  a6,2(a1)
        bra     .pg
.pgend  st      B_ON(a2)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts
; d0 the hunk, d1 the offset: a1 the site (a1 above hunk 0 kept in a6)
.site   move.l  a6,-(a7)
        move.l  a0,a6
        cmp.w   #1,d0
        beq     .s
        move.l  a3,a6
        cmp.w   #2,d0
        beq     .s
        move.l  B_13C0(a2),a6
        sub.w   #$13c0,a6
.s      lea     (a6,d1.w),a1
        cmp.w   #$8000,d1
        blo     .s1
        add.l   #$10000,a1
.s1     move.l  (a7)+,a6
        rts
.jsr    move.w  d1,(a1)
        move.l  a4,2(a1)
        rts
.h1     dc.l    $4a0a
        dc.w    $4a39
        dc.l    $ed97
        dc.l    $4a14
        dc.w    $4a39
        dc.l    $ed99
        dc.l    $4a80
        dc.w    $4239
        dc.l    $ee05
        dc.l    $4ada
        dc.w    $4239
        dc.l    $edcf
        dc.l    $4b5e
        dc.w    $2279
        dc.l    $ed86
        dc.l    0

; plan step 11, with _view, step 9's slots and the swap patched: +$4bd6 subq.b #1,<+$ef2a>
; becomes jsr _cdown, and frames between world passes are drawn
_prespatch
        IFND PRESENT_OFF
        tst.b   _bvars+B_ON(pc)
        beq     .no
        tst.l   _wvars+W_DRAW(pc)
        beq     .no
        tst.l   _wvars+W_ETAB(pc)
        beq     .no
        move.l  _hunk1(pc),a0
        lea     $4bd6(a0),a1
        cmp.w   #$5339,(a1)
        bne     .no
        lea     $ef2a(a0),a2
        cmp.l   2(a1),a2
        bne     .no
        cmp.l   #$6600000a,6(a1)        ; bne.w +$4be8
        bne     .no
        move.w  #$4eb9,(a1)
        pea     _cdown(pc)
        move.l  (a7)+,2(a1)
        lea     _pvars(pc),a2
        st      P_ON(a2)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no
        ENDC
        rts

; hunk, offset, movea.l <+$10>,An
_gsites dc.w    0,$1394,$2479,0,$184e,$2c79,0,$1896,$2c79,0,$1994,$2879,0,$1ad8,$2879
        dc.w    0,$1b50,$2479,0,$1b98,$2479,0,$1bd4,$2479,0,$1c26,$2879,0,$1c66,$2879
        dc.w    0,$1c9e,$2879,0,$1e20,$2879,0,$1e7e,$2879
        dc.w    2,$3e,$2679,2,$618,$2079,2,$67e,$2079,2,$884,$2c79,2,$9a4,$2c79
        dc.w    2,$a62,$2c79,2,$3c1e,$2279,2,$3d5e,$2a79,2,$4364,$2a79
        dc.w    -1

; +$4b30: the 3D swap without the beam wait. START has exchanged the screens (+$4b18-
; +$4b2f, <+$c> and <+$10>) and holds the pointer's lock (<+$ed98>); it marks the pointer
; as left on the old screen (<+$ed99>) after this. A wait can take in a VBL, whose pointer
; hiding runs without the lock and would restore the background on the new screen, leaving
; the pointer on the old one: so while waiting the screens are exchanged back.
_swap   movem.l d0-d1/a0,-(a7)
_swait  bsr     _sline                  ; not while the copper takes the pointers
        cmp.w   #2,d0
        blo     .wait
        cmp.w   #310,d0
        blo     _swaitend
.wait   bsr     _sxchg
.w      bsr     _sline
        cmp.w   #2,d0
        blo     .w
        cmp.w   #310,d0
        bhs     .w
        bsr     _sxchg
_swaitend
        move.l  _bvars+B_13F6(pc),a0
        jsr     (a0)
        move.w  #$10,$dff09a
        lea     _bvars(pc),a0
        st      B_UNSHOWN(a0)
        move.l  _wvars+W_VBL(pc),d0
        move.l  d0,a0
        move.l  (a0),d0
        lea     _bvars(pc),a0
        move.l  d0,B_SVBL(a0)
        bsr     _ptswap
        movem.l (a7)+,d0-d1/a0
        rts

; d0 the beam's line, read twice until both agree: a long is two word reads, and at the
; field's end V8 can come from line 311 and the rest from line 0; d1 used
_sline  move.l  $dff004,d0
        move.l  $dff004,d1
        lsr.l   #8,d0
        lsr.l   #8,d1
        and.w   #$1ff,d0
        and.w   #$1ff,d1
        cmp.w   d0,d1
        bne     _sline
        rts

; <+$c> and <+$10> exchanged, by one instruction each way (the VBL reads them); d0, d1
; and a0 used
_sxchg  move.l  _hunk1(pc),a0
        movem.l $c(a0),d0-d1
        exg     d0,d1
        movem.l d0-d1,$c(a0)
        rts

; +$49cc in 3D mode: the wait for the swap and the block put off, both now with <+$edd0>
_pstart movem.l a0-a1,-(a7)
        lea     _bvars(pc),a1
        move.l  _hunk1(pc),a0
        tst.b   ($edd0,a0)
        bne     .now
        st      B_PEND(a1)
        movem.l (a7)+,a0-a1
        rts
.now    sf      B_PEND(a1)
        move.l  B_13C0(a1),a0
        jsr     (a0)
        sf      B_UNSHOWN(a1)
        movem.l (a7)+,a0-a1
        rts

; +$4a0a: the block now when not put off; on at +$4a80
_pblock tst.b   _bvars+B_PEND(pc)
        bne     .on
        bsr     _bblock
.on     move.l  _hunk1(pc),-(a7)
        add.l   #$4a80,(a7)
        rts

; +$4ada: the views' end
_vend   bsr     _bflush
        move.l  a0,-(a7)
        move.l  _hunk1(pc),a0
        clr.b   ($edcf,a0)
        move.l  (a7)+,a0
        rts

; +$4b5e, a view's drawing: a2 the view; a 2D view (bit 1 of +1 clear) draws into the screen
_viewent
        btst    #1,1(a2)
        bne     .v
        bsr     _bflush
.v      move.l  _hunk1(pc),a1
        move.l  ($ed86,a1),a1
        rts

; hunk 2 +$2e02, the conversion
_c2pld  bsr     _bflush
        move.l  _hunk1(pc),a1
        move.l  $10(a1),a1
        rts

; the block put off, if it is: the wait for the swap (+$13c0) and the block, the drawing's
; rectangle (+$edda-+$ede3, which +$525a leaves at the last one it copies) kept
_bflush tst.b   _bvars+B_PEND(pc)
        beq     .x
        movem.l d0-d2/a0-a1,-(a7)
        lea     _bvars(pc),a1
        sf      B_PEND(a1)
        bsr     _ptacc
        move.l  B_13C0(a1),a0
        jsr     (a0)
        bsr     _ptwait
        sf      B_UNSHOWN(a1)
        move.l  _hunk1(pc),a0
        move.l  ($edda,a0),d0
        move.l  ($edde,a0),d1
        move.w  ($ede2,a0),d2
        bsr     _bblock
        move.l  _hunk1(pc),a0
        move.l  d0,($edda,a0)
        move.l  d1,($edde,a0)
        move.w  d2,($ede2,a0)
        movem.l (a7)+,d0-d2/a0-a1
.x      rts

; START's +$4a0a-+$4a7c
_bblock movem.l d0-d7/a0-a6,-(a7)
        move.l  _hunk1(pc),a5
        tst.b   ($ed97,a5)
        bmi     _bbneg
_bpwait tst.b   ($ed99,a5)              ; the VBL's pointer redraw
        bne     _bpwait
_bpwaitend
        addq.b  #1,($ed98,a5)
        beq     .l
        subq.b  #1,($ed98,a5)
.l      move.l  _bvars+B_525A(pc),a0
        jsr     (a0)
        move.b  #1,($ed99,a5)
        cmpi.b  #2,($ed97,a5)
        beq     .s
        move.l  _bvars+B_4EC(pc),a0
        jsr     (a0)                    ; it keeps no registers
        move.l  _hunk1(pc),a5
.s      clr.b   ($ed99,a5)
        st      ($ed98,a5)
        tst.b   ($ed97,a5)
        bne     _bbend
        st      ($ed97,a5)
        bra     _bbend
_bbneg  move.l  _bvars+B_525A(pc),a0
        jsr     (a0)
_bbend  move.l  _bvars+B_LIST(pc),($ee08,a5)
        movem.l (a7)+,d0-d7/a0-a6
        rts

; the back screen loaded, after the swap shows (INTENA's COPER bit set again, or two
; fields since the swap); no wait when none is pending
_bshow  move.w  ccr,-(a7)
        tst.b   _bvars+B_UNSHOWN(pc)
        beq     _bshx
        movem.l d0-d1/a0-a1,-(a7)
        lea     _bvars(pc),a1
        move.l  _wvars+W_VBL(pc),a0
        move.l  #200000,d1
_gwait  btst    #4,$dff01d
        bne     _gwaitend
        move.l  (a0),d0
        sub.l   B_SVBL(a1),d0
        cmp.l   #2,d0
        bge     _gwaitend
        subq.l  #1,d1
        bne     _gwait
_gwaitend
        sf      B_UNSHOWN(a1)
        movem.l (a7)+,d0-d1/a0-a1
_bshx   move.w  (a7)+,ccr
        rts
_g10a0  bsr.w   _bshow
        move.l  _hunk1(pc),a0
        move.l  $10(a0),a0
        rts
_g10a1  bsr.w   _bshow
        move.l  _hunk1(pc),a1
        move.l  $10(a1),a1
        rts
_g10a2  bsr.w   _bshow
        move.l  _hunk1(pc),a2
        move.l  $10(a2),a2
        rts
_g10a3  bsr.w   _bshow
        move.l  _hunk1(pc),a3
        move.l  $10(a3),a3
        rts
_g10a4  bsr.w   _bshow
        move.l  _hunk1(pc),a4
        move.l  $10(a4),a4
        rts
_g10a5  bsr.w   _bshow
        move.l  _hunk1(pc),a5
        move.l  $10(a5),a5
        rts
_g10a6  bsr.w   _bshow
        move.l  _hunk1(pc),a6
        move.l  $10(a6),a6
        rts

_bvars
_b13c0          dc.l    0               ; hunk 0 +$13c0, the wait for the swap
_b13f6          dc.l    0               ; hunk 0 +$13f6, the plane pointers
_b525a          dc.l    0               ; hunk 1 +$525a, the rectangles' copy
_b4ec           dc.l    0               ; hunk 2 +$4ec, the pointer's background
_blist          dc.l    0               ; the rectangle list's start
_bsvbl          dc.l    0               ; the VBL count at the swap
_bpend          dc.b    0               ; the wait and the block put off
_bunshown       dc.b    0               ; a swap not yet shown
_bon            dc.b    0               ; patched
        even
B_13C0  equ     _b13c0-_bvars
B_13F6  equ     _b13f6-_bvars
B_525A  equ     _b525a-_bvars
B_4EC   equ     _b4ec-_bvars
B_LIST  equ     _blist-_bvars
B_SVBL  equ     _bsvbl-_bvars
B_PEND  equ     _bpend-_bvars
B_UNSHOWN equ   _bunshown-_bvars
B_ON    equ     _bon-_bvars

_mvars
_mtaba          dc.l    0               ; hunk 1 +$a1de
_mrowblk        dc.l    0               ; START's row table that _rowalloc extended
_mrows          dc.l    0               ; its rows
_mtab           dc.l    0               ; the fast row table, after START's
_mbuf           dc.l    0               ; the copy's room, after it
_mbufsize       dc.l    0               ; its size
_morig          dc.l    0               ; the map copied
_mcopy          dc.l    0               ; the copy
_msize          dc.l    0               ; the map's size
_mspan          dc.l    0               ; and the row after it
_mlo            dc.l    0               ; the rectangle op's writes, from
_mhi            dc.l    0               ; to (0 none)
_mbad           dc.l    0               ; MAPCHECK: longwords that differed
_mcalls         dc.l    0               ; MAPCHECK: calls
_mfull          dc.b    0               ; the copy to be made again
        even
_staba          dc.l    0               ; hunk 1 +$ef3c (0: the shade table not patched)
_sshade         dc.l    0               ; the table the spans read (+$baac, +$be7e)
_sbuf           dc.l    0               ; the copy's room in _rowalloc's block (0 none)
_sorig          dc.l    0               ; the table copied (0 none)
_sn             dc.l    0               ; the bytes the shading reads (0: no copy)
_sbad           dc.l    0               ; MAPCHECK: longwords that differed
_scalls         dc.l    0               ; MAPCHECK: calls with the copy
_sfar           dc.w    0               ; the highest far level set up
SHADEMAX equ    32*256
M_TABA  equ     _mtaba-_mvars
M_ROWBLK equ    _mrowblk-_mvars
M_ROWS  equ     _mrows-_mvars
M_TAB   equ     _mtab-_mvars
M_BUF   equ     _mbuf-_mvars
M_BUFSIZE equ   _mbufsize-_mvars
M_ORIG  equ     _morig-_mvars
M_COPY  equ     _mcopy-_mvars
M_SIZE  equ     _msize-_mvars
M_SPAN  equ     _mspan-_mvars
M_LO    equ     _mlo-_mvars
M_HI    equ     _mhi-_mvars
M_BAD   equ     _mbad-_mvars
M_CALLS equ     _mcalls-_mvars
M_FULL  equ     _mfull-_mvars
S_TABA  equ     _staba-_mvars
S_SHADE equ     _sshade-_mvars
S_BUF   equ     _sbuf-_mvars
S_ORIG  equ     _sorig-_mvars
S_N     equ     _sn-_mvars
S_BAD   equ     _sbad-_mvars
S_CALLS equ     _scalls-_mvars
S_FAR   equ     _sfar-_mvars

_ivars
_iview          dc.l    0               ; the view
_iobj           dc.l    0               ; the object it follows
_iwr            dc.l    0               ; W of the pose's change
_iden           dc.l    0               ; the change's interval
_ipose          dc.w    0,0,0,0,0,0     ; the pose sampled
_icur           dc.w    0,0,0,0,0,0     ; the pose (camera order: x, y, z, three angles)
_iprev          dc.w    0,0,0,0,0,0     ; the pose before it
_ioff           dc.w    0,0,0,0,0,0     ; the staging's offsets
_isave          dc.w    0,0,0,0,0,0     ; the camera
_inew           dc.w    0,0,0,0,0,0     ; the staged camera
_idrawv         dc.w    0,0,0,0,0,0     ; the last camera drawn
_ivalid         dc.b    0               ; a pose sampled
_idrawn         dc.b    0               ; a camera drawn
_istaged        dc.b    0               ; the last camera drawn was staged
_istart         dc.b    0               ; the change started from standing
        even
I_VIEW  equ     _iview-_ivars
I_OBJ   equ     _iobj-_ivars
I_WR    equ     _iwr-_ivars
I_DEN   equ     _iden-_ivars
I_POSE  equ     _ipose-_ivars
I_CUR   equ     _icur-_ivars
I_PREV  equ     _iprev-_ivars
I_OFF   equ     _ioff-_ivars
I_SAVE  equ     _isave-_ivars
I_NEW   equ     _inew-_ivars
I_DRAWV equ     _idrawv-_ivars
I_VALID equ     _ivalid-_ivars
I_DRAWN equ     _idrawn-_ivars
I_STAGED equ    _istaged-_ivars
I_START equ     _istart-_ivars


_wvars
_ww             dc.l    0               ; W
_wdrawt         dc.l    0               ; the drawing's time: W plus the cap
_wptr           dc.l    0               ; the count the objects run by: +$ee6c or W
_wvbl           dc.l    0               ; +$ee6c
_wcap           dc.l    0               ; +$ee6a
_w3d            dc.l    0               ; +$ee03
_wframe         dc.l    0               ; +$49b2
_wobjtab        dc.l    0               ; +$ed6c
_wdraw          dc.l    0               ; +$a3a6
_wflags         dc.l    0               ; +$eef5
_welem          dc.l    0               ; +$ed86
_wprevh         dc.l    0               ; +$edb8
_wetab          dc.l    0               ; step 9's slots (allocated)
_wcatch         dc.b    0               ; catch-up passes in a row
_won            dc.b    0               ; W in use
        even
W_W     equ     _ww-_wvars
W_DRAWT equ     _wdrawt-_wvars
W_PTR   equ     _wptr-_wvars
W_VBL   equ     _wvbl-_wvars
W_CAP   equ     _wcap-_wvars
W_3D    equ     _w3d-_wvars
W_FRAME equ     _wframe-_wvars
W_OBJTAB equ    _wobjtab-_wvars
W_DRAW  equ     _wdraw-_wvars
W_FLAGS equ     _wflags-_wvars
W_ELEM  equ     _welem-_wvars
W_PREVH equ     _wprevh-_wvars
W_ETAB  equ     _wetab-_wvars
W_CATCH equ     _wcatch-_wvars
W_ON    equ     _won-_wvars
