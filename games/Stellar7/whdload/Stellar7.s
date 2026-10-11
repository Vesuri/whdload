; Stellar 7 loader, reconstructed from Psygore's v1.0 game-specific startup.
; Shared WHDLoad 20.0 KickEmu replaces the embedded 2008 implementation.
; Opt-in fixed-step timing. Original CRC checks and SetCPU values retained.
        INCLUDE whdload.i
        INCLUDE whdmacros.i
        INCLUDE lvo/dos.i
        INCLUDE exec/execbase.i
CHIPMEMSIZE = $80000
FASTMEMSIZE = $80000
NUMDRIVES = 1
WPDRIVES = 0
HDINIT
BOOTDOS
FONTHEIGHT = 8
slv_Version = 17
slv_Flags = WHDLF_NoError|WHDLF_ClearMem|WHDLF_Examine
slv_keyexit = $5d
        INCLUDE whdload/kick13.s
slv_name: dc.b "Stellar 7",0
slv_copy: dc.b "1991 Dynamix",0
slv_info: dc.b "Installed by Psygore",10,"Development baseline (KickEmu 20.0)",0
slv_CurrentDir: dc.b "data",0
slv_config:
        IFD SIM60
        dc.b "C1:B:Experimental ",48+S60_RATE/10,48+S60_RATE-(S60_RATE/10)*10," Hz simulation;"
        ELSE
        dc.b "C1:B:Experimental fixed simulation;"
        dc.b "C2:L:Simulation Hz:Default (5),1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25;"
        ENDC
        IFD VERIFY
        dc.b "C3:B:Movement and firing fixture;C4:L:Draw every N steps:Default (1),1,2,3,4,5,6,7,8;C5:B:Deterministic menu fixture;"
        ENDC
        dc.b 0
_game: dc.b "s7",0
_args: dc.b 10,0
        EVEN
_s7tags: dc.l WHDLTAG_CUSTOM1_GET
_custom1: dc.l 0
        dc.l WHDLTAG_CUSTOM2_GET
_custom2: dc.l 0
        IFD VERIFY
        dc.l WHDLTAG_CUSTOM3_GET
_custom3: dc.l 0
        dc.l WHDLTAG_CUSTOM4_GET
_custom4: dc.l 0
        dc.l WHDLTAG_CUSTOM5_GET
_custom5: dc.l 0
        ENDC
        dc.l 0
_bootdos:
        move.l #$393d,d0
        move.l #$7f3f,d1
        move.l (_resload,pc),a2
        jsr (resload_SetCPU,a2)
        pea (_game,pc)
        move.l (sp),a0
        jsr (resload_GetFileSize,a2)
        move.l d0,d6
        beq .nofile
        move.l (sp)+,a3
        move.l ($4).w,a6
        move.l d6,d0
        moveq #0,d1
        jsr (_LVOAllocMem,a6)
        move.l d0,d5
        move.l a3,a0
        move.l d5,a1
        jsr (resload_LoadFileDecrunch,a2)
        move.l d5,a0
        jsr (resload_CRC16,a2)
        cmp.w #$b9ea,d0
        beq .supported
        cmp.w #$fcc4,d0
        bne .wrongver
.supported:
        move.l d6,d0
        move.l d5,a1
        jsr (_LVOFreeMem,a6)
        lea (_dosname,pc),a1
        move.l ($4).w,a6
        jsr (_LVOOldOpenLibrary,a6)
        move.l d0,a6
        move.l a3,d1
        jsr (_LVOLoadSeg,a6)
        move.l d0,d7
        beq .loaderror
        movem.l d0-d7/a0-a6,-(sp)
        lea (_s7tags,pc),a0
        jsr (resload_Control,a2)
        move.l (_custom1,pc),d0
        beq .notiming
        bsr timing_install
.notiming:
        IFD VERIFY
        move.l (_custom5,pc),d0
        beq .notape
        bsr fixture_install
.notape:
        ENDC
        movem.l (sp)+,d0-d7/a0-a6
        move.l d7,a1
        add.l a1,a1
        add.l a1,a1
        lea (_args,pc),a0
        move.l (4,sp),d2
        sub.l #20,d2
        movem.l d0/d7/a2/a6,-(sp)
        moveq #1,d0
        jsr (4,a1)
        movem.l (sp)+,d1/d7/a2/a6
        bra .success
.loaderror:
        pea (121).w
        bra .doserror
.nofile:
        pea (205).w
.doserror:
        pea (TDREASON_DOSREAD).w
        bra .abort
.wrongver:
        pea (TDREASON_WRONGVER).w
        bra .abort
.success:
        pea (TDREASON_OK).w
.abort:
        move.l (_resload,pc),-(sp)
        addq.l #resload_Abort,(sp)
        rts

        IFD VERIFY
        INCLUDE fixture.s
        ENDC

        IFD SIM60
        INCLUDE sim60.s
        ELSE
        INCLUDE timing.s
        ENDC
