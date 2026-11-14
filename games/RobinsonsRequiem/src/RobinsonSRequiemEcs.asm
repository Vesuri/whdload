
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
FASTMEMSIZE     = $40000*1
NUMDRIVES       = 1
WPDRIVES        = %1111

BLACKSCREEN
;BOOTBLOCK
;BOOTEARLY
BOOTDOS
;CBDOSLOADSEG
;CBDOSREAD
;CACHE
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

slv_Version     = 17
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
            bsr _c2ppatch

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

_hunk1          dc.l    0
_hunk2          dc.l    0

**********************************************
; The chunky-to-planar conversion (src/c2p000.s): hunk 2 +$1a5e, START's loop, starts with
; move.w d6,a4 / move.w a4,d6 (checked first, with the routine's end at +$1b98 and the
; chunky modulo's address at +$1b8c), which becomes jmp _c2p000.

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
        move.w  #$4ef9,(a1)
        pea     _c2p000(pc)
        move.l  (a7)+,2(a1)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     rts

_c2pmod         dc.l    0

        INCLUDE c2p000.s
