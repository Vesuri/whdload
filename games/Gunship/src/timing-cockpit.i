 include "timing-offsets.i"
; E3: retain unchanged needles independently in the two chip bitmaps.
; Native screen swaps invalidate both entries; modal/native rendering always
; executes the original erase and draw. No simulation state is cached.
cockpit_install:
 movem.l a0-a3,-(sp)
 move.l cpu_render_buffer(pc),d0
 beq .done
 movea.l RT_HUNKS(a0),a3
 movea.l a3,a0
 adda.l #GS0_ac14,a0
 cmpi.w #$45f9,(a0)
 bne .bad
 lea cockpit_native_erase(pc),a1
 move.l (a0)+,(a1)+
 move.w (a0)+,(a1)+
 move.w #$4ef9,(a1)+
 move.l a0,(a1)
 movea.l a3,a0
 adda.l #GS0_acf0,a0
 cmpi.w #$1039,(a0)
 bne .bad
 cmpi.w #$3039,$1c(a0)
 bne .bad
 cmpi.w #$1039,$32(a0)
 bne .bad
 move.l a0,-(sp)
 movea.l a3,a0
 adda.l #GS0_aaa4,a0
 lea cockpit_restore_counters(pc),a1
 move.l (a0),(a1)
 movea.l (sp)+,a0
 lea cockpit_inputs(pc),a1
 move.l 2(a0),(a1)+
 move.l $1e(a0),(a1)+
 move.l $34(a0),(a1)
 lea cockpit_native_draw(pc),a1
 move.l (a0)+,(a1)+
 move.w (a0)+,(a1)+
 move.w #$4ef9,(a1)+
 move.l a0,(a1)
 bsr cockpit_invalidate
 movea.l a3,a1
 lea .patches(pc),a0
 jsr resload_Patch(a2)
 moveq #0,d0
 bra .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,a0-a3
 rts
.patches:
 PL_START
 PL_P GS0_ac14,cockpit_erase
 PL_P GS0_acf0,cockpit_draw
 PL_END

cockpit_invalidate:
 move.l a0,-(sp)
 lea cockpit_keys(pc),a0
 clr.l (a0)+
 clr.l (a0)+
 clr.w (a0)
 movea.l (sp)+,a0
 rts

 ; Called before AA80 consumes the eight two-buffer restore counters.
 ; The rotor warning artwork overlaps its needle: repaint even when the
 ; angle is unchanged whenever any cockpit panel is being restored.
cockpit_check_restores:
 movem.l d0/a0,-(sp)
 move.l cockpit_restore_counters(pc),d0
 beq .done
 movea.l d0,a0
 moveq #7,d0
.loop:
 tst.w (a0)+
 bne .invalidate
 dbf d0,.loop
 bra .done
.invalidate:
 bsr cockpit_invalidate
.done:
 movem.l (sp)+,d0/a0
 rts

cockpit_erase:
 movem.l d0-d1/a0-a2,-(sp)
 lea cockpit_skip(pc),a2
 clr.w (a2)
 movea.l timing_runtime_arena(pc),a0
 cmpi.w #1,RT_CAPTURE_OWNER(a0)
 bne .native
 tst.w RT_BOUNDARY_PHASE(a0)
 bne .native
 movea.l RT_HUNKS+24(a0),a0
 move.w $4bb0(a0),d1
 cmpi.w #1,d1
 bhi .native
 lea cockpit_inputs(pc),a0
 movea.l (a0)+,a1
 moveq #1,d0 ; valid tag followed by three native needle inputs
 lsl.l #8,d0
 move.b (a1),d0
 movea.l (a0)+,a1
 lsl.l #8,d0
 move.b 1(a1),d0 ; native word load, then low-byte mask
 movea.l (a0),a1
 lsl.l #8,d0
 move.b (a1),d0
 lsl.w #2,d1
 lea cockpit_keys(pc),a0
 cmp.l (a0,d1.w),d0
 bne .changed
 move.w #1,(a2)
 movem.l (sp)+,d0-d1/a0-a2
 rts
.changed:
 move.l d0,(a0,d1.w)
.native:
 movem.l (sp)+,d0-d1/a0-a2
 bra cockpit_native_erase

cockpit_draw:
 move.l a0,-(sp)
 lea cockpit_skip(pc),a0
 tst.w (a0)
 movem.l (sp)+,a0
 beq cockpit_native_draw
 rts

 even
cockpit_restore_counters: dc.l 0
cockpit_inputs: dc.l 0,0,0
cockpit_keys: dc.l 0,0
cockpit_skip: dc.w 0
cockpit_native_erase: ds.b 12
cockpit_native_draw: ds.b 12
