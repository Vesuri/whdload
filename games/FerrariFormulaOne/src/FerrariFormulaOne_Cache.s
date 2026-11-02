; Performance-mode CPU caches (CUSTOM2=1), as in Secret Weapons of the Luftwaffe.
; 68040/060: request WHDLoad's CACHE setup: BaseMem (Chip) noncacheable;
; ExpMem, slave and WHDLoad copyback; instruction and data caches, 68060 branch
; cache, store buffer and superscalar dispatch. If WHDLoad cannot separate Chip
; from ExpMem it switches every cache off (CACR 0); then use CACHECHIP's setup.
; 68020/030: CACHECHIP's setup: instruction cache on Chip and ExpMem (68030
; instruction burst), data cache off. The 68030 data cache (WHDLoad's MMU
; option) crashes performance-mode startup, with the unchanged build too.
; DMA buffers stay in Chip, so the data cache never holds blitter/disk data.
; 68000/010: nothing to set. The FPU setting stays as kick13.s left it.
; Called by the performance payloads when their path activates (Fine.s,
; CoarseInstall.s C1Activate) through FF1_HOST_CACHE, so boot, loading and
; menus keep kick13's caches-off setup, as before. SetCPU flushes the caches.
; Exec usable. All registers preserved.
FF1_CACHE_FULL equ WCPUF_Base_NC|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC|WCPUF_BC|WCPUF_SS|WCPUF_SB
FF1_CACHE_CHIP equ WCPUF_Base_WT|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_BC|WCPUF_SS|WCPUF_SB
FF1_CACHE_MASK equ WCPUF_All-WCPUF_FPU
FF1CachePolicy:
 movem.l d0-d1/a0-a2/a5-a6,-(sp)
 move.l FF1ProfileAttn(pc),d0
 btst #1,d0                 ; AFB_68020 from WHDLoad; 68000/010 have no CACR
 beq.b .done
 move.l _resload(pc),a2
 andi.b #$88,d0             ; AFB_68040 or AFB_68060
 beq.b .chip
 move.l #FF1_CACHE_FULL,d0
 move.l #FF1_CACHE_MASK,d1
 jsr resload_SetCPU(a2)
 move.l $4.w,a6
 lea .getcacr(pc),a5
 jsr -30(a6)                ; Supervisor (privilege violation forwarded: WHDLF_EmulPriv)
 andi.w #$8001,d0           ; IC (68040/060) or EI (68020/030)
 bne.b .done
.chip:
 move.l #FF1_CACHE_CHIP,d0
 move.l #FF1_CACHE_MASK,d1
 jsr resload_SetCPU(a2)
.done:
 movem.l (sp)+,d0-d1/a0-a2/a5-a6
 rts
.getcacr:
 dc.w $4e7a,$0002           ; movec cacr,d0 (host assembles for 68000)
 rte
