; Verification only. Keep all native game/DMA memory non-cacheable.
; In particular do NOT use KickEmu CACHE: it enables the 68060 branch cache,
; which ignores page cache inhibition and would see native branch rewriting.
verify_cache_setup
 movem.l d0-d2/a0-a2/a5-a6,-(sp)
 lea cache_status(pc),a0
 move.l #1,8(a0)
 move.l custom3(pc),d0
 beq.s .sample
 move.l #WCPUF_Base_NC|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC,d0
 move.l d0,12(a0)
 move.l #WCPUF_All,d1
 move.l _resload(pc),a2
 jsr resload_SetCPU(a2)
.sample
 moveq #0,d0
 moveq #0,d1
 move.l _resload(pc),a2
 jsr resload_SetCPU(a2)
 lea cache_status(pc),a0
 move.l d0,16(a0)
 move.l (4).w,a6
 moveq #0,d0
 move.w AttnFlags(a6),d0
 move.l d0,20(a0)
 btst #AFB_68020,d0
 beq.s .done
 lea .read_control(pc),a5
 jsr _LVOSupervisor(a6)
.done
 movem.l (sp)+,d0-d2/a0-a2/a5-a6
 rts
.read_control
 MACHINE 68020
 movec cacr,d0
 lea cache_status(pc),a0
 move.l d0,24(a0)
 ; The 68030 TC is read with PMOVE; 040/060 use MOVEC.
 move.l 20(a0),d0
 btst #AFB_68040,d0
 bne.s .tc40
 btst #AFB_68030,d0
 beq.s .return
 MACHINE 68030
 pmove tc,28(a0)
 bra.s .return
.tc40
 MACHINE 68040
 movec tc,d0
 move.l d0,28(a0)
.return
 rte
 MACHINE 68000
cache_status
 dc.b "PDCACHE1"
 dc.l 0,0,0,0,0,0 ; initialized, request, SetCPU state, AttnFlags, CACR, TC
