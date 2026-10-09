; Powerdrome development slave. Original install by Galahad/Fairlight.
; WHDLoad 20 KickEmu supplies the OS; interface 17 requires no v20-only feature.
 INCLUDE whdload.i
 INCLUDE whdmacros.i
 INCLUDE lvo/dos.i
CHIPMEMSIZE = $80000
FASTMEMSIZE = 0
NUMDRIVES = 1
WPDRIVES = 0
DISKSONBOOT
SETPATCH
CBDOSLOADSEG
slv_Version = 17
slv_Flags = WHDLF_NoError
slv_keyexit = $59
 INCLUDE whdload/kick13.s
slv_name dc.b "Powerdrome",0
slv_copy dc.b "1989 Electronic Arts",0
slv_info dc.b "Installed by Galahad/Fairlight",10,"Development by Vesuri",10,"Version 1.1-dev",0
slv_CurrentDir dc.b 0
slv_config
 IFD VERIFY
 dc.b "C5:L:Verification route:Off,Title demo,Practice;"
 ENDC
 dc.b 0
 EVEN

_cb_dosLoadSeg
 lsl.l #2,d0
 move.l d0,a0
 lea endcliname(pc),a1
 moveq #0,d2
 move.b (a0),d2
.cmp cmpm.b (a0)+,(a1)+
 dbne d2,.cmp
 bne.s .done
 lea pl_endcli(pc),a0
 move.l d1,a1
 move.l _resload(pc),a2
 jsr resload_PatchSeg(a2)
.done rts
endcliname dc.b 6,"endcli"
 EVEN
pl_endcli PL_START
 PL_P $4,launch_pd
 PL_END

launch_pd
 move.l (4).w,a6
 moveq #0,d0
 lea dosname(pc),a1
 jsr -552(a6)
 move.l d0,a6
 lea gamename(pc),a0
 move.l a0,d1
 jsr _LVOLoadSeg(a6)
 tst.l d0
 beq.s .error
 lsl.l #2,d0
 move.l d0,a3
 lea 4(a3),a1
 ; Require the exact original Copylock signature before installing its replacement.
 move.l a1,a0
 adda.l #$843c,a0
 cmp.l #$2f0e4dfa,(a0)
 bne.s .error
 lea pl_game(pc),a0
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
 IFD VERIFY
 lea tags(pc),a0
 jsr resload_Control(a2)
 move.l custom5(pc),d0
 beq.s .run
 lea pl_verify(pc),a0
 lea 4(a3),a1
 jsr resload_Patch(a2)
 move.l custom5(pc),d0
 cmp.l #2,d0
 bne.s .run
 lea pl_practice(pc),a0
 lea 4(a3),a1
 jsr resload_Patch(a2)
.run
 ENDC
 jmp (a3)
.error
 pea TDREASON_WRONGVER
 move.l _resload(pc),a2
 jmp resload_Abort(a2)
pl_game PL_START
 PL_P $843c,copylock
 PL_END
copylock move.l #$766cc95c,d0
 rts
dosname dc.b "dos.library",0
gamename dc.b "Powerdrome:PD",0
 EVEN
 IFD VERIFY
; Fixture submits an empty pilot name through the native text-entry path.
; Only the two six-byte JSRs are replaced; normal builds have neither patch.
pl_verify PL_START
 PL_PS $13772,key_ready
 PL_PS $1377c,key_return
 PL_END
key_ready moveq #-1,d0
 rts
key_return moveq #13,d0
 rts
; Whole six-byte input JSRs. Only installed for CUSTOM5=2.
; Key 3 selects the same menu item as the top-middle Practice button.
pl_practice PL_START
 PL_PS $12f6a,practice_ready
 PL_PS $130a4,practice_key
 PL_PS $13c50,pit_ready
 PL_PS $13cde,pit_key
 PL_END
practice_ready
 moveq #0,d0
 move.w practice_sent(pc),d0
 subq.w #1,d0
 rts
practice_key
 move.l a0,-(sp)
 lea practice_sent(pc),a0
 move.w #1,(a0)
 move.l (sp)+,a0
 moveq #$33,d0
 rts
pit_ready
 moveq #0,d0
 move.w pit_sent(pc),d0
 subq.w #1,d0
 rts
pit_key
 move.l a0,-(sp)
 lea pit_sent(pc),a0
 move.w #1,(a0)
 move.l (sp)+,a0
 moveq #32,d0
 rts
practice_sent dc.w 0
pit_sent dc.w 0
tags dc.l WHDLTAG_CUSTOM5_GET
custom5 dc.l 0
 dc.l TAG_DONE
 ENDC
