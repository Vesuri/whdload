
;*---------------------------------------------------------------------------
;  :Modul.      kick13.asm
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


; pour choisir le crack de Robinson Requiem ECS
PARADOX_CRACK
;PRESTIGE_CRACK

        INCDIR  Includes:
        INCLUDE whdload.i
       INCLUDE whdmacros.i
       INCLUDE lvo/dos.i
       INCLUDE lvo/exec.i
       INCLUDE exec/memory.i


        IFD BARFLY
        OUTPUT  "RobinsonSRequiemECS.Slave"
        BOPT    O+                              ;enable optimizing
        BOPT    OG+                             ;enable optimizing
        BOPT    ODd-                            ;disable mul optimizing
        BOPT    ODe-                            ;disable mul optimizing
        BOPT    w4-                             ;disable 64k warnings
        BOPT    wo-                             ;disable optimize warnings
        SUPER
        ENDC

;============================================================================

CHIPMEMSIZE     = $80000*2
; 1 MB of fast memory besides the Kickstart (ECS plan step 7): START sizes its fast pool from
; it (AvailMem - 50,000, none under 100,000: none in v1.2's 256 KB) and keeps it, and on the
; 68020 and up the renderer's buffers and the map's copy go there too (_mempatch).
; MemConfig=1 (slv_MemConfig) is CFou!'s v1.2 layout, 256 KB, for machines without the room.
FASTMEMSIZE     = $100000
FASTMEMSIZE_V12 = $40000
NUMDRIVES       = 1
WPDRIVES        = %1111

BLACKSCREEN
;BOOTBLOCK
;BOOTEARLY
BOOTDOS
;CBDOSLOADSEG
;CBDOSREAD
; BaseMem write-through, instruction and data caches on (the 68000 has none). The blitter
; draws only into the screens (hunk 2), which the CPU writes but does not read back
; (docs/internals.md, "ECS improvements", item 3).
CACHECHIPDATA
;DEBUG
;DISKSONBOOT
;DOSASSIGN
;FONTHEIGHT     = 8
HDINIT
;HRTMON
IOCACHE         = 12000
;MEMFREE        = $100
;NEEDFPU
;POINTERTICKS   = 1
SETPATCH
;STACKSIZE      = 60000
;TRDCHANGEDISK

;============================================================================

slv_Version     = 20
slv_Flags       = WHDLF_NoError|WHDLF_Examine|WHDLF_ClearMem ;|WHDLF_EmulPriv
slv_keyexit     = $59   ;F10

;============================================================================

        INCLUDE whdload/kick13.s

;============================================================================

        IFD BARFLY
        IFND    .passchk
        DOSCMD  "WDate  >T:date"
.passchk
        ENDC
        ENDC

slv_CurrentDir  dc.b    "data-ecs",0
slv_name        dc.b    "Robinson Requiem ECS",0
slv_copy        dc.b    "Silmarils",0
slv_info        dc.b    "Coded By CFou!",10
                dc.b    "Version 1.2 "
        IFD BARFLY
                INCBIN  "T:date"
        ENDC
                dc.b    0
        EVEN

slv_config	dc.b 0
	EVEN
slv_MemConfig   dc.l    CHIPMEMSIZE,KICKSIZE+FASTMEMSIZE_V12
                dc.l    0
;============================================================================
; entry before any diskaccess is performed, no dos.library available

        IFD BOOTEARLY

_bootearly
                  blitz
                rts

        ENDC

;============================================================================
; bootblock from "Disk.1" has been loaded, no dos.library available

        IFD BOOTBLOCK

; A1 = ioreq ($2c+a5)
; A4 = buffer (1024 bytes)
; A6 = execbase

_bootblock      blitz
                jmp     (12,a4)

        ENDC

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
       ;    blitz

           MOVE.W  #$4EF9,D0
           MOVE.W  D0,-$72(A6)
           PEA     int_dos(PC)
           MOVE.L  (SP)+,-$70(A6)       ; debug track disk info


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

;       MOVE.B  #4,$BFDD00
;        lea $dff080,a1
;.enc
;        clr.l (a1)+
;        cmp.l #$dff180,a1
;        bne .enc
;        move.w #$f,$dff1fc

        ;call


;******************** PARADOX_CRACKDEB

      IFD PARADOX_CRACK
;crack
                move.l  d7,a1
                add.l   a1,a1
                add.l   a1,a1
                move.l (a1),d1
                lsl.l #2,d1

                add.l #$f9c,d1
                move.l d1,a1
                cmp.l #$548b4e75,(a1)
                bne .pas
                move.l #$4ef80100,(a1)

        LEA     _crackPARADOX(PC),A1
        move.w #$4ef9,$100
        move.l a1,$102

.pas
       ENDC
;******************** PARADOX_CRACKFIN


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

            move.l  d7,a1
            add.l   a1,a1
            add.l   a1,a1
            bsr _hunks
   IFD PROFILE
            pea     slv_base(pc)        ; for tools/rr_prof.py and rr_report.py
            move.l  (a7)+,PROFILE_SLAVE.w
            clr.l   PROFILE_FRAMES.w
   ENDC
            bsr _c2ppatch
            bsr _skypatch
            bsr _mempatch

	move.w	#$7fff,$dff09A
	move.w	#$e028,$dff09A

;crackfin
                move.l  d7,a1
                add.l   a1,a1
                add.l   a1,a1
                moveq   #_args_end-_args,d0
                lea     (_args,pc),a0
                movem.l (_saveregs,pc),d1-d6/a2-a6
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
; callback/hook which gets executed after each successful call to dos.LoadSeg
; can also be used instead of _bootdos, requires the presence of
; "startup-sequence"

; the following example uses a parameter table to patch different executables
; after they get loaded

        IFD CBDOSLOADSEG

; D0 = BSTR name of the loaded program as BCPL string
; D1 = BPTR segment list of the loaded program as BCPL pointer

_cb_dosLoadSeg  lsl.l   #2,d0           ;-> APTR
                move.l  d0,a0
                moveq   #0,d0
                move.b  (a0)+,d0        ;D0 = name length
        ;remove leading path
                move.l  a0,a1
                move.l  d0,d2
.2              move.b  (a1)+,d3
                subq.l  #1,d2
                cmp.b   #":",d3
                beq     .1
                cmp.b   #"/",d3
                beq     .1
                tst.l   d2
                bne     .2
                bra     .3
.1              move.l  a1,a0           ;A0 = name
                move.l  d2,d0           ;D0 = name length
                bra     .2
.3      ;get hunk length sum
                move.l  d1,a1           ;D1 = segment
                moveq   #0,d2
.add            add.l   a1,a1
                add.l   a1,a1
                add.l   (-4,a1),d2      ;D2 = hunks length
                subq.l  #8,d2           ;hunk header
                move.l  (a1),a1
                move.l  a1,d7
                bne     .add
        ;search patch
                lea     (.patch,pc),a1
.next           move.l  (a1)+,d3
                movem.w (a1)+,d4-d5
                beq     .end
                cmp.l   d2,d3           ;length match?
                bne     .next
        ;compare name
                lea     (.patch,pc,d4.w),a2
                move.l  a0,a3
                move.l  d0,d6
.cmp            move.b  (a3)+,d7
                cmp.b   #"a",d7
                blo     .l
                cmp.b   #"z",d7
                bhi     .l
                sub.b   #$20,d7
.l              cmp.b   (a2)+,d7
                bne     .next
                subq.l  #1,d6
                bne     .cmp
                tst.b   (a2)
                bne     .next
        ;patch
                lea     (.patch,pc,d5.w),a0
                move.l  d1,a1
                move.l  (_resload,pc),a2
                jsr     (resload_PatchSeg,a2)
        ;end
.end
        IFD DEBUG
        ;set debug
                clr.l   -(a7)
                move.l  d1,-(a7)
                pea     WHDLTAG_DBGSEG_SET
                move.l  a7,a0
                move.l  (_resload,pc),a2
                jsr     (resload_Control,a2)
                add.w   #12,a7
        ENDC
                rts

PATCH   MACRO
                dc.l    \1              ;cumulated size of hunks (not filesize!)
                dc.w    \2-.patch       ;name
                dc.w    \3-.patch       ;patch list
        ENDM

.patch          PATCH   2516,.n_run,_p_run2568
                dc.l    0

        ;all upper case!
.n_run          dc.b    "RUN",0
        EVEN

_p_run2568      PL_START
        ;       PL_P    0,.1
                PL_END

        ENDC

;============================================================================
; callback/hook which gets executed after each successful call to
; dos.LoadRead

; the following example uses a parameter table to patch different files
; after they get loaded

        IFD CBDOSREAD

; D0 = ULONG bytes read
; D1 = ULONG offset in file
; A0 = CPTR name of file
; A1 = APTR memory buffer

_cb_dosRead
                move.l  a0,a2
.1              tst.b   (a2)+
                bne     .1
                lea     (.name,pc),a3
                move.l  a3,a4
.2              tst.b   (a4)+
                bne     .2
                sub.l   a4,a2
                add.l   a3,a2           ;first char to check
.4              move.b  (a2)+,d2
                cmp.b   #"A",d2
                blo     .3
                cmp.b   #"Z",d2
                bhi     .3
                add.b   #$20,d2
.3              cmp.b   (a3)+,d2
                bne     .no
                tst.b   d2
                bne     .4

        ;check position
                move.l  d0,d2
                add.l   d1,d2
                lea     (.data,pc),a2
                moveq   #0,d3
.next           movem.w (a2)+,d3-d4
                tst.w   d3
                beq     .no
                cmp.l   d1,d3
                blo     .next
                cmp.l   d2,d3
                bhs     .next
                sub.l   d1,d3
                move.b  d4,(a1,d3.l)
                bra     .next

.no             rts

.name           dc.b    "tables01",0    ;lower case!
        EVEN
        ;offset, new data
.data           dc.w    $4278,$c        ;original = 0b
                dc.w    $45b4,$c        ;original = 0b
                dc.w    0

        ENDC

;============================================================================
int_dos
        MOVE.L  A0,-(SP)
        MOVE.L  D2,A0
        move.l #0,0(a0)
        move.l #0,4(a0)
        MOVE.L  #$52,8(A0)
        MOVE.L  #$2710,$c(A0)
;        MOVE.L  #5,$10(A0)
;        MOVE.L  #$1E8,$14(A0)
        MOVE.L  #$444F5300,$18(A0)
        move.l #0,$1c(a0)
        MOVE.L  #0,$20(A0)
        MOVE.L  (SP)+,A0
        move.l #-1,d0
        RTS



**********************************************************************
;        LEA     _crackPARADOX(PC),A1
;        move.w #$4ef9,$100
;        move.l a1,$102

  IFD PARADOX_CRACK
_crackPARADOX
        CMP.B   #$53,$12(A3)
        BNE.S   .skp
        CMP.B   #$62,$18(A3)
        BNE.S   .skp
        CMP.B   #$56,$19(A3)
        BNE.S   .skp
        MOVE.B  #$1E,$12(A3)
        MOVE.B  #$1E,$18(A3)
        MOVE.B  #$1E,$19(A3)
.skp
        ADDQ.L  #2,A3
        RTS
        dc.l    $0
_crackfin
         ENDC
**********************************************************************

**********************************************************************

  IFD PRESTIGE_CRACK
        ; first hunk adr  A1 deuxieme dans (a1)*4
CrackRobinsonRequiemECS
_crackPRESTIGE

;   blitz

;        MOVEM.L D0-D7/A0-A6,-(SP)
;
;        LEA     lbC000000(PC),A0
;        MOVE.L  -4(A0),D0
        move.l (a1),d0

        LSL.L   #2,D0
        ADDQ.L  #4,D0

;        MOVE.L  D0,$A2(A0)
        lea _saveadrhunk1(pc),a0
        move.l d0,(a0)

        MOVE.L  D0,A0
;        MOVE.L  -4(A0),D0
;        LSL.L   #2,D0
;        ADDQ.L  #4,D0
;        MOVE.L  D0,A0
        ADD.L   #$DD6,A0
        cmp.l #$101b4880,(a0)
        bne .pas
        MOVE.W  #$4EB9,(A0)+
        PEA     _crackECS(PC)
        MOVE.L  (SP)+,(A0)
.pas
;        MOVEM.L (SP)+,D0-D7/A0-A6
;        MOVE.L  _saveadrhunk1(PC),-(SP)
        RTS

 ;       BRA   .fin1

_crackECS
        CMP.B   #7,-5(A3)
        BNE   .skip
        MOVEM.L D0/A0-A3,-(SP)
        LEA     lbL00007E(PC),A2
        BSR     _CopyData
        BNE  .skp0
        LEA     lbL00008E(PC),A2
        BSR     _CopyData
        BEQ   .skp1
.skp0
        CMP.B   #$14,(A0)
        BNE   .skp1
        MOVE.B  #10,(A0)
.skp1
        MOVEM.L (SP)+,D0/A0-A3
.skip
        MOVE.B  (A3)+,D0
        EXT.W   D0
        SWAP    D0
        RTS

_CopyData
        MOVE.L  A3,A0
        ADD.W   (A2)+,A0
        LEA     -4(A3),A1
        MOVEQ   #6,D0
.enc
        CMPM.B  (A1)+,(A2)+
        BNE .fin
        DBRA    D0,.enc

        MOVEQ   #-$1,D0
        RTS
.fin
       MOVEQ   #0,D0
        RTS

lbL00007E
        dc.l    $02A30003
        dc.l    $02070000
        dc.l    $849ADED6
        dc.l    $5EA0A68E
lbL00008E
        dc.l    $02AD0000
        dc.l    $E0070002
        dc.w    $8E00

.fin1
        MOVEM.L (SP)+,D0-D7/A0-A6
        MOVE.L  _saveadrhunk1(PC),-(SP)
        RTS

;lbL0000A2
_saveadrhunk1
       dc.l    0
       ENDC


**********************************************
; Development builds: boot straight into the game, as the AGA slave's _directstart does
; (docs/internals.md, "Direct start"). START's open wrapper (hunk 0 +$1af0) is entered with
; a3 on the name inside the MAIN script op that loads the file and a6 on MAIN's variables;
; at the loads of logo and init3d the hook changes MAIN's branches, checked byte for byte:
; - after "logo.AO": a branch over the logo to the load of the pointer (souris, slot 2, which
;   the 3D set-up needs), and one after it over the flags and the intro to the path an Esc's
;   branch takes, with MAIN's language byte ($e68) set to English;
; - after "init3d.AO": the options menu's load, its object and the wait for it are branched
;   over.

  IFD DEVELOPER

_directstart
        lea     4(a1),a0                ; hunk 0
        cmp.l   #$61986100,$1af0(a0)    ; bsr.s $1a8a / bsr.w $fe
        bne     .no
        cmp.w   #$e60a,$1af4(a0)
        bne     .no
        lea     $1a8a(a0),a1
        lea     _open1(pc),a2
        move.l  a1,(a2)
        lea     $fe(a0),a1
        move.l  a1,4(a2)
        move.w  #$4eb9,$1af0(a0)
        pea     _openhook(pc)
        move.l  (a7)+,$1af2(a0)
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
        lea     _souris_at(pc),a1
        bsr     _match
        bne     .done
        lea     _logo_jump(pc),a1
        bsr     _write
        lea     _souris_jump(pc),a1
        bsr     _write
        move.b  #1,$e68(a6)             ; English
        bra     .done
.init3d lea     _init3d(pc),a1
        bsr     _match
        bne     .done
        lea     _prefs_at(pc),a1
        bsr     _match
        bne     .done
        lea     _menu_at(pc),a1
        bsr     _match
        bne     .done
        lea     _wait_at(pc),a1
        bsr     _match
        bne     .done
        lea     _menu_to(pc),a1
        bsr     _match
        bne     .done
        lea     _prefs_jump(pc),a1
        bsr     _write
        lea     _menu_jump(pc),a1
        bsr     _write
        lea     _wait_jump(pc),a1
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

_open1          dc.l    0
_open2          dc.l    0

; offsets from the name in MAIN's load op (a3)
_logo           dc.w    0,8
                dc.b    "logo.AO",0
_logo_at        dc.w    8,6                     ; create the logo object
                dc.b    $40,$00,$01,$08,$39,$20
_logo_to        dc.w    $47b,5                  ; after the intro: where an Esc's branch (+$46d) lands
                dc.b    $a1,$96,$00,$00,$42
_souris_at      dc.w    $6c,16                  ; load the pointer into slot 2, language := none
                dc.b    $45,$00,$02,"souris.AO",0,$1e,$00,$ff
_logo_jump      dc.w    8,4                     ; over the logo to the pointer's load
                dc.b    $0a,$00,$00,$60
_souris_jump    dc.w    $79,4                   ; over the flags and the intro
                dc.b    $0a,$00,$03,$fe
_init3d         dc.w    0,10
                dc.b    "init3d.AO",0
_prefs_at       dc.w    $32,12                  ; load the menu
                dc.b    $45,$00,$54,"prefs.AO",0
_menu_at        dc.w    $55,10                  ; create the menu object, four yields
                dc.b    $40,$00,$54,$08,$39,$20,$42,$42,$42,$42
_wait_at        dc.w    $6d,7                   ; wait for the menu's end
                dc.b    $94,$00,$54,$08,$39,$20,$42
_menu_to        dc.w    $9f,3                   ; free the menu's slots
                dc.b    $3d,$00,$54
_prefs_jump     dc.w    $32,4
                dc.b    $0a,$00,$00,$08
_menu_jump      dc.w    $55,4
                dc.b    $0a,$00,$00,$06
_wait_jump      dc.w    $6d,4
                dc.b    $0a,$00,$00,$2e
        EVEN

  ENDC

**********************************************
; The game's hunks 1 and 2 (a1: the segment list, hunk 0's link).

_hunks
        lea     _hunk0(pc),a2
        lea     4(a1),a0
        move.l  a0,(a2)
        move.l  (a1),d0
        lsl.l   #2,d0
        move.l  d0,a0                   ; hunk 1's link
        addq.l  #4,d0
        lea     _hunk1(pc),a2
        move.l  d0,(a2)
        move.l  (a0),d0
        lsl.l   #2,d0
        addq.l  #4,d0
        move.l  d0,4(a2)                ; _hunk2
        rts

_hunk0          dc.l    0
_hunk1          dc.l    0
_hunk2          dc.l    0

; Profile builds, as the AGA slave's: the frames the game draws in PROFILE_FRAMES (user
; vector 67), counted at each conversion (_c2ppatch, once per frame), and the slave's address
; in PROFILE_SLAVE (vector 68), for tools/rr_prof.py and rr_report.py.
PROFILE_FRAMES  = $10c
PROFILE_SLAVE   = $110

**********************************************
; The chunky-to-planar conversion (src/c2p000.s, and src/c2p020.s on the 68020 and up, ECS
; plan step 8): hunk 2 +$1a5e, START's loop, starts with move.w d6,a4 / move.w a4,d6
; (checked first, with the routine's end at +$1b98 and the chunky modulo's address at
; +$1b8c), which becomes jmp _c2p000 or jmp _c2p020.

_c2ppatch
        move.l  _hunk2(pc),a0
        lea     $1a5e(a0),a1
        cmp.l   #$38463c0c,(a1)
        bne     .no
        cmp.l   #$4cdf7fff,$1b98(a0)
        bne     .no
        lea     $46(a0),a2
        cmp.l   $1b8c(a0),a2
        bne     .no
        lea     _c2pmod(pc),a3
        move.l  a2,(a3)
        lea     _c2p000(pc),a2
        move.l  _attnflags(pc),d0
        and.w   #AFF_68020,d0
        beq     .set
        lea     _c2p020(pc),a2
.set    lea     _c2pentry(pc),a3
        move.l  a2,(a3)
        move.w  #$4ef9,(a1)
   IFD PROFILE
        pea     _framehook(pc)
        move.l  (a7)+,2(a1)
   ELSE
        move.l  a2,2(a1)
   ENDC
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

   IFD PROFILE
_framehook
        addq.l  #1,PROFILE_FRAMES.w
        move.l  _c2pentry(pc),-(a7)
        rts
   ENDC

_c2pmod         dc.l    0
_c2pentry       dc.l    0               ; _c2p000 or _c2p020

        INCLUDE c2p000.s
        INCLUDE c2p020.s

**********************************************
; The sky copy (src/sky000.s): hunk 1 +$c8b8-$c8e7, START's row loop, becomes jsr _skyrows
; and bra.w +$c8e8, after a check of its bytes (with the address of <hunk 1 +$d454> at
; +$c8c8).

_skypatch
        move.l  _hunk1(pc),a0
        move.l  a0,a1
        add.l   #$c8b8,a1               ; offsets above $7fff: no lea
        lea     _skyold(pc),a2
        moveq   #0,d1
.cmp    cmp.w   #$10,d1                 ; +$c8c8: the address
        beq     .addr
        move.w  (a2),d2
        cmp.w   (a1,d1.w),d2
        bne     .no
        bra     .next
.addr   move.l  a0,d2
        add.l   #$d454,d2
        cmp.l   (a1,d1.w),d2
        bne     .no
        addq.w  #2,d1
        addq.l  #2,a2
.next   addq.w  #2,d1
        addq.l  #2,a2
        cmp.w   #48,d1
        blo     .cmp
        move.w  #$4eb9,(a1)
        pea     _skyrows(pc)
        move.l  (a7)+,2(a1)
        move.l  #$60000028,6(a1)        ; bra.w +$c8e8
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

_skyold dc.w    $4a40,$6d00,$000a,$3600,$32d8,$51cb,$fffc,$3639
        dc.w    $0000,$d454,$e24b,$9640,$5543,$6d00,$000a,$90c1
        dc.w    $32d8,$51cb,$fffc,$d2c5,$d8c1,$204c,$51cf,$ffd2

        INCLUDE sky000.s

**********************************************
; Memory on the 68020 and up (docs/performance.md, ECS plan step 7; docs/internals.md, "ECS
; improvements", item 3): the AGA slave's _fastblocks, _mappatch and shade table copy (its
; plan steps 3, 10.2 and 10.3) at the ECS sites (docs/internals.md, "The AGA's sites in the
; ECS game", items 3, 9 and 10), when WHDLoad's AttnFlags have the 68020 bit. Each needs
; START's fast pool (the 1 MB ExpMem) at run time and takes chip as before without it. The
; 68000 keeps START's own allocations: there the chip bus costs it nothing in this game's
; 4 low-resolution planes, and the copies would. The code below runs only on the 68020 and
; up but is assembled for the 68000: hunk 1 offsets above $7fff go through an index register.

H1_FASTLOW      = $f4                   ; START's fast pool: the lowest block (its end, not used)
H1_CHIPLOW      = $fc                   ; the chip pool's lowest block
H1_FRAMEEND     = $d3d8                 ; the objects' frames' end in the fast pool
H1_HANDLES      = $d598                 ; the block allocator's 16 handles
H1_ROWTAB       = $8848                 ; the landscape's row table
H1_SHADE        = $d592                 ; the shade table

_mempatch
        move.l  _attnflags(pc),d0
        and.w   #AFF_68020,d0
        beq     .no
        bsr     _fastblocks
        bsr     _mappatch
        bsr     _skycopy
.no     rts

**********************************************
; The sky in fast memory (ECS plan step 8; the AGA's plan step 12, its sites in the ECS game
; item 13): a room from the fast memory list for _skyrows's copy of the image (src/sky000.s,
; _skyget), and the sky's set-up, hunk 1 +$1876 move.l d2,164(a0) and bsr.w +$6238,
; becoming jsr _skyset and a nop, after a check of their bytes. No room: _skyrows reads the
; image itself.

_skycopy
        IFND SKYCOPY_OFF
        movem.l d0-d1/a0-a1/a6,-(a7)
        move.l  _hunk1(pc),a0
        cmp.l   #$214200a4,$1876(a0)
        bne     .x
        cmp.l   #$610049bc,$187a(a0)
        bne     .x
        move.l  #SKYMAX+40,d0
        moveq   #MEMF_FAST|MEMF_PUBLIC,d1
        move.l  4.w,a6
        jsr     _LVOAllocMem(a6)
        move.l  _hunk1(pc),a0
        tst.l   d0
        beq     .x
        add.l   #15,d0
        and.w   #-16,d0
        lea     _kvars(pc),a1
        move.l  d0,K_BUF(a1)
        move.w  #$4eb9,$1876(a0)
        pea     _skyset(pc)
        move.l  (a7)+,$1878(a0)
        move.w  #$4e71,$187c(a0)        ; nop
        move.l  _resload(pc),a1
        jsr     resload_FlushCache(a1)
.x      movem.l (a7)+,d0-d1/a0-a1/a6
        ENDC
        rts

; +$1876: the view's image set as before, the copy to be made again, on to +$6238 (its rts
; returning to the nop after the jsr, as the bsr.w did)
_skyset move.l  d2,164(a0)
        move.l  a1,-(a7)
        lea     _kvars(pc),a1
        clr.l   K_ORIG(a1)
        move.l  (a7)+,a1
        move.l  _hunk1(pc),-(a7)
        add.l   #$6238,(a7)
        rts

**********************************************
; The renderer's buffers in fast memory (the AGA's plan step 3). START's block allocator
; (hunk 0 +$2be8: d0 size -> d0 handle, an entry of the table at hunk 1 +$d598 whose first
; longword is the block) takes from the top of the chip pool; the calls for the 3D view's
; chunky buffer (hunk 1 +$891c), the renderer's tables (+$8938) and the row table (+$8978)
; go to _fastalloc instead, which takes the same blocks from the top of the fast pool (hunk 1
; +$f4, its end, which START sets and does not use) down to the end of the objects' frames
; (+$d3d8), or from chip as before when there is no fast pool or no room. _fastfree replaces
; START's free (hunk 0 +$2c42, which first passes over a null handle) for both: like it, it
; gives a block back only when it is the lowest one of its pool.

_fastblocks
        move.l  _hunk0(pc),a1
        lea     $2be8(a1),a0
        cmp.l   #$48e74080,(a0)         ; movem.l d1/a0,-(a7)
        bne     .no
        lea     _chipalloc(pc),a2
        move.l  a0,(a2)
        cmp.l   #$48e78080,$2c42(a1)    ; movem.l d0/a0,-(a7) / tst.l d0
        bne     .no
        cmp.w   #$4a80,$2c46(a1)
        bne     .no
        move.l  _hunk1(pc),a2
        lea     _fastsites(pc),a3
.check  move.l  (a3)+,d0                ; all call sites first
        beq     .patch
        cmp.w   #$4eb9,(a2,d0.l)
        bne     .no
        cmp.l   2(a2,d0.l),a0
        bne     .no
        bra     .check
.patch  lea     _fastsites(pc),a3
        lea     _fastalloc(pc),a0
.p      move.l  (a3)+,d0
        beq     .free
        move.l  a0,2(a2,d0.l)
        bra     .p
.free   move.w  #$4ef9,$2c42(a1)
        pea     _fastfree(pc)
        move.l  (a7)+,$2c44(a1)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

; jsr <hunk 0 +$2be8> sites in hunk 1
_fastsites
        dc.l    $891c                   ; the 3D view's chunky buffer
        dc.l    $8938                   ; the renderer's tables
        dc.l    $8978                   ; the row table (_rowalloc)
        dc.l    0

_fastalloc
        movem.l d1-d2/a0-a1,-(a7)
        move.l  _hunk1(pc),a1
        move.l  H1_FASTLOW(a1),d1       ; the lowest fast block, 0 without a pool
        beq     .chip
        sub.l   d0,d1
        subq.l  #8,d1                   ; header
        and.w   #-16,d1
        move.l  #H1_FRAMEEND,d2
        cmp.l   (a1,d2.l),d1
        blo     .chip
        move.l  d1,a0
        move.l  H1_FASTLOW(a1),d0
        sub.l   d1,d0
        move.l  d0,(a0)                 ; header: the distance to the block above
        move.l  a0,H1_FASTLOW(a1)
        addq.l  #8,a0
        move.l  a0,d0
        move.l  a1,a0
        add.l   #H1_HANDLES,a0
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
.out    movem.l (a7)+,d1-d2/a0-a1
        rts
.chip   movem.l (a7)+,d1-d2/a0-a1
        move.l  _chipalloc(pc),-(a7)
        rts

_fastfree
        movem.l d0/a0-a1,-(a7)
        tst.l   d0
        beq     .out
        move.l  d0,a0
        move.l  4(a0),d0
        clr.l   (a0)
        clr.l   4(a0)
        subq.l  #8,d0                   ; header
        move.l  _hunk1(pc),a1
        lea     H1_FASTLOW(a1),a0       ; the fast pool's lowest block
        cmp.l   (a0),d0
        beq     .back
        lea     H1_CHIPLOW(a1),a0       ; the chip pool's
        cmp.l   (a0),d0
        bne     .out
.back   move.l  d0,a1
        add.l   (a1),d0
        move.l  d0,(a0)
.out    movem.l (a7)+,d0/a0-a1
        rts

_chipalloc      dc.l    0

**********************************************
; The map in fast memory (the AGA's plan step 10.2, docs/internals.md, "AGA improvements",
; item 9, at the ECS sites). The landscape (hunk 1 +$bee2) reads the map through the row
; table at <+$8848>, which it loads once at +$bf5e. The row table's allocation (+$8978, jsr
; _fastalloc after _fastblocks) becomes jsr _rowalloc, which asks the fast pool for a fast
; row table and a copy of the map behind START's table in the same block, freed with it
; (when they do not fit, START's table alone as before); +$bf5e movea.l <+$8848>,a2 becomes
; jsr _maprows, which gives the landscape the fast table while START's table is that block,
; the copy at the map's address modulo 16. The copy is made again in full when the map's
; address, size or stride changes, after the fill op (+$2238) wrote it and after a map
; object's set-up (+$1cd6); the rectangle op's writes (+$21e6) are copied at the next call;
; and the row after the map is copied at every call. The two reads at a tile's offset from a
; cell (+$c4ca, +$c5ce) go back to the original, so no offset leaves the copy. The shade
; table (the AGA's plan step 10.3): the view's shade set-up (+$184a move.l a1,<+$d592>)
; becomes jsr _shadeset and the spans' two reads (+$a116, +$a4de movea.l <+$d592>,a0) read
; _sshade, the copy in _rowalloc's block when there is one (hunk 2 +$18dc reads the table
; itself, as in the AGA game). MAPCHECK (a test define): every call compares the whole
; copies with the originals after the update, counting differing longwords.

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
.ok     move.l  #$bf5e,d1
        cmp.w   #$2479,(a0,d1.l)        ; movea.l <+$8848>,a2
        bne     .no
        move.l  a0,d0
        add.l   #H1_ROWTAB,d0
        cmp.l   2(a0,d1.l),d0
        bne     .no
        lea     _mvars(pc),a2
        move.l  d0,M_TABA(a2)
        move.l  #$8978,d1
        cmp.w   #$4eb9,(a0,d1.l)        ; the row table's allocation: _fastalloc
        bne     .no
        lea     _fastalloc(pc),a1
        cmp.l   2(a0,d1.l),a1
        bne     .no
        lea     _rowalloc(pc),a1
        move.l  a1,2(a0,d1.l)
        lea     .jsrs(pc),a2
.put    move.l  (a2)+,d0
        beq     .done
        move.l  (a2)+,d1
        move.w  #$4eb9,(a0,d0.l)
        lea     .jsrs(pc),a1
        add.l   d1,a1
        move.l  a1,2(a0,d0.l)
        tst.l   (a2)+
        beq     .put
        move.w  #$4e71,6(a0,d0.l)       ; nop
        bra     .put
.done   move.l  a0,d0                   ; the shade table: its set-up and its two reads
        add.l   #H1_SHADE,d0
        cmp.w   #$23c9,$184a(a0)        ; move.l a1,<+$d592>
        bne     .fl
        cmp.l   $184c(a0),d0
        bne     .fl
        move.l  #$a116,d1
        cmp.w   #$2079,(a0,d1.l)        ; movea.l <+$d592>,a0
        bne     .fl
        cmp.l   2(a0,d1.l),d0
        bne     .fl
        move.l  #$a4de,d2
        cmp.w   #$2079,(a0,d2.l)
        bne     .fl
        cmp.l   2(a0,d2.l),d0
        bne     .fl
        lea     _mvars(pc),a2
        move.l  d0,S_TABA(a2)
        move.w  #$4eb9,$184a(a0)
        lea     _shadeset(pc),a1
        move.l  a1,$184c(a0)
        lea     _sshade(pc),a1
        move.l  a1,2(a0,d1.l)
        move.l  a1,2(a0,d2.l)
.fl     move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts
.sites  dc.l    $c4ca,$34311016,$d1f11010       ; move.w (22,a1,d1.w),d2; adda.l (16,a1,d1.w),a0
        dc.l    $c5ce,$d1f11010,$34311016
        dc.l    $21e6,$43f10800,$3228fc3c       ; lea (0,a1,d0.l),a1; move.w -964(a0),d1
        dc.l    $2238,$22484a29,$ffff6a00       ; movea.l a0,a1; tst.b -1(a1); bpl.w
        dc.l    $1cd6,$217c0000,$0004fc24       ; move.l #4,-988(a0)
        dc.l    0
; site, routine (from .jsrs), a nop after the jsr
.jsrs   dc.l    $bf5e,_maprows-.jsrs,0
        dc.l    $c4ca,_mapoff-.jsrs,1
        dc.l    $c5ce,_mapoff-.jsrs,1
        dc.l    $21e6,_maprect-.jsrs,1
        dc.l    $2238,_mapfill-.jsrs,0
        dc.l    $1cd6,_mapinit-.jsrs,1
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

; +$8978: d0 the row table's size (4 x the rows), a3 the map's object: START's table, then
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
        move.l  H1_FASTLOW(a1),d0
        beq     .start
        sub.l   d2,d0
        subq.l  #8,d0
        and.w   #-16,d0
        move.l  a0,-(a7)
        move.l  #H1_FRAMEEND,a0
        cmp.l   (a1,a0.l),d0
        move.l  (a7)+,a0
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

; +$c4ca, +$c5ce: a0 a cell, a1 the tile table, d1 the tile's entry; a0 back in the map
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

; +$21e6, the rectangle op: a1 its first word, d1 the grid's stride, d7+1 columns of up to
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

; +$2238, the fill op: a0 the grid's object; the copy made again when it is the map
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

; +$1cd6, a grid object's set-up: the copy made again
_mapinit
        move.l  #4,-988(a0)
        move.l  a2,-(a7)
        lea     _mvars(pc),a2
        st      M_FULL(a2)
        move.l  (a7)+,a2
        rts

; +$184a move.l a1,<+$d592>, the end of the view's shade set-up: a0 the view, a1 the table
; (word entries, 256 bytes a level), 160(a0) its levels, 158(a0) the far level. Each
; drawing's shading steps from a start level to the far level, so it reads the table's first
; max(levels, far + 1, 7) levels: copied when that is the table, with a level to spare above
; the far level of every set-up so far (as the AGA's _shadeset)
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

_mvars
_mtaba          dc.l    0               ; hunk 1 +$8848
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
_staba          dc.l    0               ; hunk 1 +$d592 (0: the shade table not patched)
_sshade         dc.l    0               ; the table the spans read (+$a116, +$a4de)
_sbuf           dc.l    0               ; the copy's room in _rowalloc's block (0 none)
_sorig          dc.l    0               ; the table copied (0 none)
_sn             dc.l    0               ; the bytes the shading reads (0: no copy)
_sbad           dc.l    0               ; MAPCHECK: longwords that differed
_scalls         dc.l    0               ; MAPCHECK: calls with the copy
_sfar           dc.w    0               ; the highest far level set up
        even
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
