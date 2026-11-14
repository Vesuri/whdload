
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
                dc.b    "Version 2.0b (14.11.2026) "
        IFD BARFLY
                INCBIN  "T:date"
        ENDC
                dc.b    0
slv_config	dc.b	0
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
            bsr _fastpool
            move.l  d7,a1
            add.l   a1,a1
            add.l   a1,a1
            bsr _fastblocks
            bsr _c2ppatch
            bsr _skypatch
            bsr _worldpatch

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
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

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
_chipalloc      dc.l    0

**********************************************
; The chunky-to-planar conversion (src/c2p030.s): START's loop at hunk 2 +$2e84 starts
; with move.w d6,<hunk 2 +$2db6>, which becomes jmp _c2p030. After _fastblocks (_hunk2).

_c2ppatch
        move.l  _hunk2(pc),a0
        lea     $2e84(a0),a1
        cmp.w   #$33c6,(a1)
        bne     .no
        lea     $2db6(a0),a0
        cmp.l   2(a1),a0
        bne     .no
        move.w  #$4ef9,(a1)
        pea     _c2p030(pc)
        move.l  (a7)+,2(a1)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

        INCLUDE c2p030.s

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

        INCLUDE sky030.s

**********************************************
; The world on the cap's grid (docs/performance.md, plan step 7). MAIN runs the due script
; objects, then the frame routine (hunk 1 +$49b2: the cap wait, the drawing, the swap), and
; again; an object is due once the VBL count (+$ee6c) passes its next run (-62(a6)), its
; last run's count plus its period (-58(a6)). Keeping up, the passes start a cap (+$ee6a, 3
; fields in game) apart and every object runs on that grid; a long drawing pass breaks it.
; In 3D mode (+$ee03) a world count W takes the VBL count's place: W goes up by the cap per
; pass, each pass waits for the VBL count to reach W (the cap wait's job), and while W is a
; pass or more behind at the list's end MAIN goes round the list again without the frame
; routine, at most twice in a row; three passes or more behind (a load, a pause) W is set
; to the count.
; - hunk 1 +$257e movea.l <+$ee6c>,a3 (the scheduler's due test) becomes jsr _wa3
; - +$6480 movea.l <+$ee6c>,a0 (op $36, the period) becomes jsr _wa0
; - +$250e bsr.w +$49b2, bra.s +$251a (the list's end) becomes jsr _listend
; - +$49e8 move.b <+$ee6a>,d0 (the cap, for the wait at +$49ee) becomes jsr _capwait
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
; the wait for the count to reach W, and 0 (no wait) for START's
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
        bra     .none
.none   clr.b   d0
        movem.l (a7)+,d1/a0-a1
        rts
.off    sf      W_ON(a1)
        move.l  W_VBL(a1),W_PTR(a1)
        movem.l (a7)+,d1/a0-a1
        rts
.on     moveq   #0,d1
        move.b  d0,d1
        add.l   W_W(a1),d1
        move.l  d1,W_W(a1)
_wwait  cmp.l   (a0),d1                 ; until the count reaches W
        bhi     _wwait
        clr.b   d0
        movem.l (a7)+,d1/a0-a1
        rts
_wwaitend

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
; it. No interpolation across a jump (a position step over I_JUMP or an angle over 45
; degrees), for a new view or followed object, or outside 3D mode (W not in use).
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
        move.l  _wvars+W_W(pc),d6
        sub.l   I_WR(a3),d6             ; alpha's numerator
        move.l  I_DEN(a3),d7
        cmp.l   d7,d6
        bhs     .staged                 ; alpha 1 (or before the change: none)
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
        move.w  d0,d1
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
        bsr     _eapply
        move.l  _wvars+W_DRAW(pc),a0
        jsr     (a0)
        bsr     _eundo
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
        subq.b  #1,$ef2a-$eef5(a0)
        bne     .out
        st      $ef2b-$eef5(a0)
.out    movem.l (a7)+,d0-d7/a0-a1/a3-a4
        rts
.draw   move.l  _wvars+W_DRAW(pc),a0
        jsr     (a0)
        bra     .out
.cam    dc.w    22,24,26,52,54,56

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
.grid   move.l  d2,d0
.den    move.l  d0,I_DEN(a3)
        bra     .keep
.snap   move.l  a0,I_OBJ(a3)            ; a jump, or a new object: no interpolation
        st      I_VALID(a3)
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
ESIZE   equ     36
; a slot: +0 the object (0 free), +4 W of the move, +8 the interval, +12/14/16 the position's
; step, +18 the heading's, +20 the heading after it, +22 staged in the last frame drawn,
; +24/26/28/30 the offsets (position, heading), +32 the staged heading

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
        tst.b   W_ON(a0)
        beq     .done
        move.l  W_W(a0),d5
        sub.l   4(a3),d5                ; alpha's numerator
        move.l  8(a3),d6
        cmp.l   d6,d5
        bhs     .done
        moveq   #0,d3                   ; any offset
        moveq   #0,d2
.off    move.w  12(a3,d2.w),d1
        move.w  d1,d4
        muls.w  d5,d4
        divs.w  d6,d4
        sub.w   d1,d4                   ; step x alpha - step
        move.w  d4,24(a3,d2.w)
        or.w    d4,d3
        addq.w  #2,d2
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
_eapply moveq   #0,d0
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
        movem.w 24(a3),d2-d5            ; the offsets
        move.w  d2,d6
        or.w    d3,d6
        or.w    d4,d6
        or.w    d5,d6
        bne     .some
        tst.b   d0                      ; none: after the drawing, a done move's slot freed
        beq     .clr
        move.l  W_W(a0),d6
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


_wvars
_ww             dc.l    0               ; W
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
