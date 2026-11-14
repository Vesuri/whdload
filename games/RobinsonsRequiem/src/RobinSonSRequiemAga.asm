
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
FASTMEMSIZE     = $40000
NUMDRIVES       = 1
WPDRIVES        = %1111

;BLACKSCREEN
;BOOTBLOCK
;BOOTEARLY
BOOTDOS
;CBDOSLOADSEG
;CBDOSREAD
CACHE
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

slv_Version     = 17
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
slv_info        dc.b    "Coded By CFou!",10
                dc.b    "Version 1.2  "
        IFD BARFLY
                INCBIN  "T:date"
        ENDC
                dc.b    0
slv_config	dc.b	0
        EVEN


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

