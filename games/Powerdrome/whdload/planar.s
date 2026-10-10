; Optional planar staging. Native entry instructions are copied at runtime.
; C1 enables staging; VERIFY C4=1 twins pure clear/polygon blocks.
; The private guest expansion pool is reserved even when C1 is off, keeping PD in chip RAM.
PERF_BITMAP = 32000
PERF_GUARD = $a55aa55a
PERF_POISON = $6d936d93
 IFND COPY_MOVEM
COPY_MOVEM = 1
 ENDC
 IFND FULL_PLANAR
FULL_PLANAR = 0
 ENDC
reserve_arena
 movem.l d0-d2/a0-a2/a6,-(sp)
 move.l (4).w,a6
 move.l #MEMF_FAST|MEMF_LARGEST,d1
 jsr _LVOAvailMem(a6)
 lea perf_status(pc),a2
 move.l d0,perf_arena_size-perf_status(a2)
 cmp.l #$9800,d0
 blo.s .done
 moveq #MEMF_FAST,d1
 jsr _LVOAllocMem(a6)
 move.l d0,perf_arena-perf_status(a2)
 ; WHDLoad can back expansion with slow memory. Never advertise that as fast.
 cmp.l #$200000,d0
 blo.s .done
 cmp.l #$c00000,d0
 blo.s .usable
 cmp.l #$e00000,d0
 blo.s .done
.usable
 add.l #128,d0
 move.l d0,perf_bitmap-perf_status(a2)
 move.l d0,a0
 lea -128(a0),a0
 move.l d0,a1
 lea PERF_BITMAP(a1),a1
 moveq #31,d0
.guard
 move.l #PERF_GUARD,(a0)+
 move.l #PERF_GUARD,(a1)+
 dbf d0,.guard
.done
 movem.l (sp)+,d0-d2/a0-a2/a6
 rts

install_planar
 ; a1 is the game hunk. Preserve caller's loader state.
 movem.l d0-d2/a0-a2,-(sp)
 lea perf_status(pc),a2
 move.l a1,perf_game-perf_status(a2)
 move.l custom1(pc),d0
 beq.w .done
 move.l perf_bitmap(pc),d0
 beq.w .done
 ; MOVE from SR is privileged on 68010+. Use MOVE from CCR there.
 ; Install-time code changes are flushed by resload_Patch below.
 move.l (4).w,a0
 btst #AFB_68010,AttnFlags+1(a0)
 beq.s .flags_done
 lea scene_entry(pc),a0
 move.w #$42e7,(a0)
 lea scene_ccr_return(pc),a0
 move.w #$42e7,(a0)
 IFD VERIFY
 lea twin_clear(pc),a0
 move.w #$42e7,(a0)
 lea twin_poly(pc),a0
 move.w #$42e7,(a0)
 lea poly_reference_ccr(pc),a0
 move.w #$42e7,(a0)
 lea poly_actual_ccr(pc),a0
 move.w #$42e7,(a0)
 ENDC
.flags_done
 move.l a1,a0
 adda.l #$10df2,a0
 cmp.w #$2079,(a0)
 bne.w .done
 lea native_scene(pc),a2
 move.l (a0),(a2)
 move.w 4(a0),4(a2)
 addq.l #6,a0
 move.l a0,8(a2)
 bsr install_raster
 lea pl_planar(pc),a0
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
 IFD VERIFY
 move.l custom4(pc),d0
 beq.w .done
 move.l perf_game(pc),a1
 move.l a1,d0
 add.l #$1578a,d0
 lea native_clear(pc),a0
 move.l d0,2(a0)
 move.l _resload(pc),a2
 lea pl_twin(pc),a0
 jsr resload_Patch(a2)
 ENDC
.done
 movem.l (sp)+,d0-d2/a0-a2
 rts

pl_planar PL_START
 ; PERF_RANGE h0:$10df2 6 bit=C1
 PL_P $10df2,scene_entry
 ; PERF_RANGE h0:$15ee8 6 bit=C1
 PL_P $15ee8,routed_poly
 PL_END
 IFD VERIFY
pl_twin PL_START
 ; PERF_RANGE h0:$112b6 6 bit=C1 (VERIFY+C4 only)
 PL_PS $112b6,twin_clear
 PL_P $15ee8,twin_poly
 PL_END
 ENDC
native_scene
 ds.b 6
 dc.w $4ef9
 dc.l 0

scene_entry
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 lea perf_status(pc),a2
 IFD VERIFY
 addq.l #1,perf_seen-perf_status(a2)
 ENDC
 move.l perf_game(pc),d0
 add.l #$ceec,d0
 cmp.l 62(sp),d0
 bne.w scene_native
 ; Initial supported mode: normal cockpit with a complete background clear.
 tst.w $2f2(a6)
 bne.w scene_native
 tst.w $2ea(a6)
 bne.w scene_native
 tst.w $4ce(a6)
 bne.w scene_native
 tst.w $4d0(a6)
 bne.w scene_native
 tst.w $106(a6)
 beq.w scene_native
 tst.w $e6(a6)
 bne.w scene_native
 tst.w $aa(a6)
 bne.w scene_native
 ; Exact normal-cockpit clip/clear layout. No other viewport is staged.
 cmp.w #19,$386(a6)
 bne.w scene_native
 cmp.w #149,$388(a6)
 bne.w scene_native
 cmp.w #320,$38a(a6)
 bne.w scene_native
 tst.w $38c(a6)
 bne.w scene_native
 cmp.l #6000,$48c(a6)
 bne.w scene_native
 cmp.l #130,$490(a6)
 bne.w scene_native
 move.l $3ba(a6),a0
 cmpa.l $3b2(a6),a0
 beq.w scene_native
 move.l a0,d0
 btst #0,d0
 bne.w scene_native
 cmp.l #$80000-PERF_BITMAP,d0
 bhi.w scene_native
 move.l a0,perf_chip-perf_status(a2)
 move.l perf_game(pc),a1
 move.l $4666(a1),a6
 jsr -228(a6) ; WaitBlit: finish users of the native destination before seeding
 IFD VERIFY
 move.l custom4(pc),d0
 beq.s scene_seed
 ; Poison all staging pixels. Partial seeding must suffice on its own;
 ; untouched regions must remain poison, rather than inherit a full seed.
 move.l perf_bitmap(pc),a0
 move.w #PERF_BITMAP/4-1,d0
scene_poison
 move.l #PERF_POISON,(a0)+
 dbf d0,scene_poison
scene_seed
 ENDC
scene_seed_begin
 move.l perf_chip(pc),a0
 move.l perf_bitmap(pc),a1
 IFNE FULL_PLANAR
 bsr copy_bitmap
 ELSE
 ; Only rows 150..153 survive the native clear and can be read/modified.
 lea 6000(a0),a0
 lea 6000(a1),a1
 moveq #3,d1
scene_seed_plane
 moveq #39,d0
scene_seed_row
 move.l (a0)+,(a1)+
 dbf d0,scene_seed_row
 lea 7840(a0),a0
 lea 7840(a1),a1
 dbf d1,scene_seed_plane
 ENDC
scene_seed_end
 bsr seed_edge
 lea perf_status(pc),a2
 move.l perf_game(pc),a6
 lea $a6e(a6),a6
 move.l perf_bitmap(pc),$3ba(a6)
 move.w #1,perf_active-perf_status(a2)
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 bsr native_scene
scene_ccr_return
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 lea perf_status(pc),a2
 IFD VERIFY
 move.l custom4(pc),d0
 beq.s scene_copy
 move.l perf_chip(pc),a0
 move.l perf_bitmap(pc),a1
 IFNE FULL_PLANAR
 move.w #PERF_BITMAP/4-1,d0
scene_check
 cmpm.l (a0)+,(a1)+
 dbne d0,scene_check
 bne.s scene_bad_pixel
 ELSE
 moveq #3,d1
scene_check_plane
 move.w #189,d0 ; rows 0..18: untouched
scene_head
 cmp.l #PERF_POISON,(a1)+
 dbne d0,scene_head
 bne.s scene_bad_pixel
 lea 760(a0),a0
 move.w #1349,d0 ; rows 19..153: exact native image
scene_check
 cmpm.l (a0)+,(a1)+
 dbne d0,scene_check
 bne.s scene_bad_pixel
 move.w #459,d0 ; rows 154..199: untouched
scene_tail
 cmp.l #PERF_POISON,(a1)+
 dbne d0,scene_tail
 bne.s scene_bad_pixel
 lea 1840(a0),a0
 dbf d1,scene_check_plane
 ENDC
 bra.s scene_copy
scene_bad_pixel
 addq.l #1,perf_failures-perf_status(a2)
 move.l a1,d1
 sub.l perf_bitmap(pc),d1
 move.l d1,perf_bad_offset-perf_status(a2)
 bra.s scene_restore
scene_copy
 ENDC
scene_copy_begin
 move.l perf_bitmap(pc),a0
 move.l perf_chip(pc),a1
 IFNE FULL_PLANAR
 bsr copy_bitmap
 ELSE
 lea 760(a0),a0
 lea 760(a1),a1
 moveq #3,d1
scene_copy_plane
 IFNE COPY_MOVEM
 move.w #134,d0
scene_copy_block
 movem.l (a0)+,d2-d7/a2-a5
 movem.l d2-d7/a2-a5,(a1)
 lea 40(a1),a1
 dbf d0,scene_copy_block
 ELSE
 move.w #674,d0
scene_copy_row
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 dbf d0,scene_copy_row
 ENDC
 lea 2600(a0),a0
 lea 2600(a1),a1
 dbf d1,scene_copy_plane
 ENDC
scene_copy_end
scene_restore
 bsr restore_edge
 lea perf_status(pc),a2
 move.l perf_game(pc),a6
 lea $a6e(a6),a6
 move.l perf_chip(pc),$3ba(a6)
 ; The clear caches an end pointer; retain its native address semantics.
 move.l $392(a6),d0
 sub.l perf_bitmap(pc),d0
 add.l perf_chip(pc),d0
 move.l d0,$392(a6)
 IFD VERIFY
 ; Check both 128-byte arena guards, including full-copy builds.
 move.l perf_bitmap(pc),a0
 lea -128(a0),a0
 move.l perf_bitmap(pc),a1
 lea PERF_BITMAP(a1),a1
 moveq #31,d0
scene_guard
 cmp.l #PERF_GUARD,(a0)+
 bne.s scene_bad_guard
 cmp.l #PERF_GUARD,(a1)+
 bne.s scene_bad_guard
 dbf d0,scene_guard
 bra.s scene_guards_ok
scene_bad_guard
 addq.l #1,perf_guards-perf_status(a2)
scene_guards_ok
 ENDC
 ; Return the same pointer values as the native renderer.
 move.l sp,a0
 bsr normalize_registers
 clr.w perf_active-perf_status(a2)
 IFD VERIFY
 addq.l #1,perf_frames-perf_status(a2)
 ENDC
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 rts
scene_native
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 bra native_scene

normalize_registers
 ; a0 points at saved d0-d7/a0-a6. Only known pointer outputs are translated.
 move.l a0,a1
 lea 12(a1),a0
 bsr normalize_pointer
 lea 32(a1),a0
 bsr normalize_pointer
 lea 40(a1),a0
 bsr normalize_pointer
 lea 44(a1),a0
 bsr normalize_pointer
 lea 48(a1),a0
 bsr normalize_pointer
 lea 36(a1),a0
 bsr normalize_code_pointer
 ; Empty scanlines can leave a4 pointing at the rasterizer's colour table.
 lea 48(a1),a0
 bsr normalize_code_pointer
.edge
 move.w perf_edge_active(pc),d0
 beq.s .done
 lea 40(a1),a0
 bsr normalize_edge_pointer
 lea 52(a1),a0
 bsr normalize_edge_pointer
.done
 rts

normalize_code_pointer
 move.l perf_code(pc),d0
 beq.s .done
 move.l (a0),d0
 sub.l perf_code(pc),d0
 cmp.l #RASTER_SIZE,d0
 bhs.s .done
 add.l perf_game(pc),d0
 add.l #RASTER_START,d0
 move.l d0,(a0)
.done
 rts

normalize_edge_pointer
 move.l (a0),d0
 sub.l perf_edge(pc),d0
 cmp.l #EDGE_SIZE,d0
 bhi.s .done
 add.l perf_native_edge(pc),d0
 move.l d0,(a0)
.done
 rts

normalize_pointer
 move.l (a0),d0
 sub.l perf_bitmap(pc),d0
 cmp.l #PERF_BITMAP,d0
 bhi.s .done
 add.l perf_chip(pc),d0
 move.l d0,(a0)
.done
 rts

copy_bitmap
 move.w #PERF_BITMAP/32-1,d0
.loop
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 dbf d0,.loop
 rts

 IFD VERIFY
; Twin only pure drawing blocks; never invoke the full renderer twice.
twin_clear
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 move.w perf_active(pc),d0
 beq.s .restore
 move.l perf_chip(pc),$3ba(a6)
 movem.l (sp),d0-d7/a0-a6
 move.w 60(sp),ccr
 bsr native_clear
 move.l perf_bitmap(pc),$3ba(a6)
.restore
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
native_clear
 dc.w $4ef9
 dc.l 0

twin_poly
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 move.w perf_active(pc),d0
 beq.w twin_poly_native
 bsr edge_to_native
 move.l perf_chip(pc),$3ba(a6)
 movem.l (sp),d0-d7/a0-a6
 move.w 60(sp),ccr
 bsr native_poly
poly_reference_ccr
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 move.l perf_bitmap(pc),$3ba(a6)
 bsr edge_to_fast
 movem.l 62(sp),d0-d7/a0-a6
 move.w 122(sp),ccr
 bsr routed_poly
poly_actual_ccr
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 ; Normalize a comparison copy. Return the untouched fast outputs so VERIFY
 ; exercises the same intra-renderer register behavior as the normal path.
 move.l sp,a0
 lea -62(sp),sp
 move.l sp,a1
 moveq #30,d0
.snapshot
 move.w (a0)+,(a1)+
 dbf d0,.snapshot
 move.l sp,a0
 bsr normalize_registers
 ; A word-sized result can retain pointer-like high bits from its input.
 ; Never relocate a value that already matches the native output exactly.
 move.l sp,a0
 lea 62(sp),a1
 lea 124(sp),a2
 moveq #14,d0
.exact
 move.l (a1)+,d1
 cmp.l (a2)+,d1
 bne.s .translated
 move.l d1,(a0)
.translated
 addq.l #4,a0
 dbf d0,.exact
 move.l sp,a0
 lea 124(sp),a1
 moveq #14,d0
.compare
 cmpm.l (a0)+,(a1)+
 dbne d0,.compare
 bne.s .bad
 move.w (a0),d0
 move.w (a1),d1
 eor.w d1,d0
 and.w #$1f,d0
 beq.s .checked
.bad
 lea perf_register_failures(pc),a0
 tst.l (a0)
 bne.s .count_bad
 ; Preserve the first mismatch: normalized, raw, reference and input snapshots.
 move.l sp,a1
 lea poly_mismatch+8(pc),a2
 moveq #123,d0
.save_bad
 move.w (a1)+,(a2)+
 dbf d0,.save_bad
.count_bad
 addq.l #1,(a0)
.checked
 lea 62(sp),sp
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 lea 124(sp),sp
 rts
twin_poly_native
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 bra routed_poly

poly_mismatch dc.b "PDMISM01"
 ds.b 248
 ENDC

perf_status dc.b 'PDPERF03'
perf_arena dc.l 0
perf_arena_size dc.l 0
perf_bitmap dc.l 0
perf_game dc.l 0
perf_chip dc.l 0
perf_seen dc.l 0
perf_frames dc.l 0
perf_failures dc.l 0
perf_bad_offset dc.l 0
perf_active dc.w 0
perf_guards dc.l 0
; Signed offsets from the installed scene entry for trace component accounting.
 dc.w scene_seed_begin-scene_entry,scene_seed_end-scene_entry
 dc.w scene_copy_begin-scene_entry,scene_copy_end-scene_entry
 EVEN
