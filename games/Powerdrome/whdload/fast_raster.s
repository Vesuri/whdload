; Fast copy of the existing planar rasterizer. No chunky conversion.
; The original sixteen span writers are retained byte-for-byte.
; Sixteen static scanline loops replace the per-polygon branch rewriting.
RASTER_START = $15b68
RASTER_END = $1609c
RASTER_SIZE = RASTER_END-RASTER_START
RASTER_LOOP = $16020
RASTER_LOOP_SIZE = RASTER_END-RASTER_LOOP
RASTER_ARENA = $8000
RASTER_CLONES = RASTER_ARENA+RASTER_SIZE
RASTER_TABLE = RASTER_CLONES+16*RASTER_LOOP_SIZE
EDGE_ARENA = $9200
EDGE_SIZE = 816
; Compact plane-address construction; keep clone stride and return offset stable.
RASTER_TRIM = 6

install_raster
 movem.l d0-d7/a0-a6,-(sp)
 lea routed_poly(pc),a0
 lea perf_active(pc),a1
 move.l a1,2(a0)
 ; Every mode retains an original polygon trampoline for native fallback/twins.
 move.l perf_game(pc),a0
 adda.l #$15ee8,a0
 lea native_poly(pc),a1
 move.l (a0),(a1)
 move.w 4(a0),4(a1)
 addq.l #6,a0
 move.l a0,8(a1)
 lea fast_poly(pc),a1
 lea native_poly(pc),a0
 move.l a0,2(a1)
 move.l custom2(pc),d0
 cmp.l #1,d0
 beq.w .done
 cmp.l #3,d0
 beq.w .done
 move.l perf_game(pc),a0
 adda.l #RASTER_START,a0
 move.l perf_arena(pc),a1
 adda.l #RASTER_ARENA,a1
 lea perf_code(pc),a2
 move.l a1,(a2)
 move.l a1,a3
 move.w #RASTER_SIZE/4-1,d0
.copy
 move.l (a0)+,(a1)+
 dbf d0,.copy
 ; Clone the complete scanline loop, including its native return sequence.
 move.l perf_arena(pc),a4
 adda.l #RASTER_CLONES,a4
 move.l perf_arena(pc),a5
 adda.l #RASTER_TABLE,a5
 ; The 68000/68010 keep their existing loops; only 68020+ select the refinement.
 moveq #0,d6
 move.l (4).w,a0
 btst #AFB_68020,AttnFlags+1(a0)
 beq.s .cpu_selected
 moveq #RASTER_TRIM,d6
.cpu_selected
 moveq #0,d7
.clone
 move.l a4,(a5)+
 move.l a3,a0
 adda.l #RASTER_LOOP-RASTER_START,a0
 move.l a4,a1
 move.w #RASTER_LOOP_SIZE/4-1,d0
.loop_copy
 move.l (a0)+,(a1)+
 dbf d0,.loop_copy
 tst.w d6
 beq.s .addresses_done
 ; LEA can read the preceding plane directly, removing three MOVEA copies.
 lea raster_planes(pc),a0
 lea $1604a-RASTER_LOOP(a4),a1
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 lea $1605c-RASTER_LOOP(a4),a0
 moveq #($16094-$1605c)/4-1,d0
.compact
 move.l (a0)+,(a1)+
 dbf d0,.compact
 move.w #$4e71,(a1)+
 move.w #$4e71,(a1)+
 move.w #$4e71,(a1)+
 ; Empty-row branch and DBF retain their original destinations after compaction.
 sub.b #RASTER_TRIM,$16033-RASTER_LOOP(a4)
 add.w #RASTER_TRIM,$16092-RASTER_TRIM-RASTER_LOOP(a4)
.addresses_done
 ; Relocate LEA mask-table(pc),a1 in this clone.
 move.l a3,d0
 add.l #$15ea8-RASTER_START,d0
 sub.l a4,d0
 subq.l #2,d0
 move.w d0,2(a4)
 move.l a4,a1
 suba.w d6,a1
 ; Original table entries are signed branch displacements, not addresses.
 move.l a3,a0
 adda.l #$15e68-RASTER_START,a0
 move.w (a0,d7.w),d0
 ext.l d0
 add.l a3,d0
 add.l #$16080-RASTER_START,d0
 sub.l a4,d0
 sub.l #$16080-RASTER_LOOP,d0
 add.l d6,d0
 move.w d0,$16080-RASTER_LOOP(a1)
 move.w 32(a0,d7.w),d0
 ext.l d0
 add.l a3,d0
 add.l #$1608a-RASTER_START,d0
 sub.l a4,d0
 sub.l #$1608a-RASTER_LOOP,d0
 add.l d6,d0
 move.w d0,$1608a-RASTER_LOOP(a1)
 adda.w #RASTER_LOOP_SIZE,a4
 addq.w #2,d7
 cmp.w #32,d7
 bne.w .clone
 ; Replace mutable branch selection with one static-loop selection per polygon.
 lea raster_dispatch(pc),a0
 move.l a3,a1
 adda.l #$1600c-RASTER_START,a1
 move.l a1,a4
 moveq #5,d0
.dispatch
 move.l (a0)+,(a1)+
 dbf d0,.dispatch
 move.l perf_arena(pc),d0
 add.l #RASTER_TABLE,d0
 sub.l a4,d0
 subq.l #4,d0
 move.w d0,4(a4)
 sub.w d6,12(a4)
 add.w d6,22(a4)
 lea perf_span_resume(pc),a0
 move.l a0,16(a4)
 ; Span writers return here. a6 is dead until the next row rebuilds plane 3
 ; or the native epilogue restores the game's state base.
 move.w #$2c79,$1608c-RASTER_START(a3)
 move.l a0,$1608e-RASTER_START(a3)
 move.w #$4ed6,$16092-RASTER_START(a3)
 lea fast_poly(pc),a0
 move.l a3,d0
 add.l #$15ee8-RASTER_START,d0
 move.l d0,2(a0)
.done
 movem.l (sp)+,d0-d7/a0-a6
 rts

raster_planes
 lea 8000(a0),a3
 lea 8000(a3),a4
 lea 8000(a4),a6

raster_dispatch
 add.w d7,d7
 dc.w $43fa,0 ; lea color-table(pc),a1, displacement filled at installation
 movea.l (a1,d7.w),a1
 adda.w #$1608c-RASTER_LOOP,a1
 dc.w $23c9 ; move.l a1,perf_span_resume (address filled at installation)
 dc.l 0
 jmp RASTER_LOOP-$1608c(a1)

routed_poly
 ; Polygon entry overwrites NZVC before its first conditional branch; X is retained.
 dc.w $4a79 ; tst.w perf_active, address filled at installation
 dc.l 0
 beq.w native_poly
fast_poly
 dc.w $4ef9
 dc.l 0
native_poly
 ds.b 6
 dc.w $4ef9
 dc.l 0

raster_status dc.b 'PDRAST02'
perf_code dc.l 0
perf_span_resume dc.l 0
perf_native_edge dc.l 0
perf_edge dc.l 0
perf_edge_active dc.w 0
perf_scratch_failures dc.l 0
perf_register_failures dc.l 0

seed_edge
 lea perf_edge_active(pc),a0
 clr.w (a0)
 move.l custom2(pc),d0
 cmp.l #1,d0
 beq.w .done
 cmp.l #0,d0
 beq.w .done
 move.l perf_game(pc),a2
 cmp.w #200,$4660(a2)
 bne.w .done
 lea perf_native_edge(pc),a1
 move.l $12(a2),(a1)
 move.l perf_arena(pc),a0
 adda.l #EDGE_ARENA,a0
 lea perf_edge(pc),a1
 move.l a0,(a1)
 IFD VERIFY
 lea -128(a0),a1
 lea EDGE_SIZE(a0),a0
 moveq #31,d0
.guards
 move.l #PERF_GUARD,(a0)+
 move.l #PERF_GUARD,(a1)+
 dbf d0,.guards
 ENDC
 move.l perf_native_edge(pc),a0
 move.l perf_edge(pc),a1
 move.w #EDGE_SIZE/4-1,d0
.copy
 move.l (a0)+,(a1)+
 dbf d0,.copy
 move.l perf_edge(pc),$12(a2)
 lea perf_edge_active(pc),a0
 move.w #1,(a0)
.done
 rts

edge_to_native
 move.w perf_edge_active(pc),d0
 beq.s .done
 move.l perf_game(pc),a0
 move.l perf_native_edge(pc),$12(a0)
.done
 rts

edge_to_fast
 move.w perf_edge_active(pc),d0
 beq.s .done
 move.l perf_game(pc),a0
 move.l perf_edge(pc),$12(a0)
.done
 rts

restore_edge
 move.w perf_edge_active(pc),d0
 beq.w .done
 bsr edge_to_native
 IFD VERIFY
 move.l custom4(pc),d0
 beq.s .copy
 move.l perf_native_edge(pc),a0
 move.l perf_edge(pc),a1
 move.w #EDGE_SIZE/4-1,d0
.compare
 cmpm.l (a0)+,(a1)+
 dbne d0,.compare
 beq.s .copy
 lea perf_scratch_failures(pc),a0
 addq.l #1,(a0)
.copy
 ENDC
 move.l perf_edge(pc),a0
 move.l perf_native_edge(pc),a1
 move.w #EDGE_SIZE/4-1,d0
.loop
 move.l (a0)+,(a1)+
 dbf d0,.loop
 IFD VERIFY
 move.l perf_edge(pc),a0
 lea -128(a0),a0
 move.l perf_edge(pc),a1
 lea EDGE_SIZE(a1),a1
 moveq #31,d0
.guards
 cmp.l #PERF_GUARD,(a0)+
 bne.s .bad
 cmp.l #PERF_GUARD,(a1)+
 bne.s .bad
 dbf d0,.guards
 bra.s .done
.bad
 lea perf_guards(pc),a0
 addq.l #1,(a0)
 ENDC
.done
 rts
