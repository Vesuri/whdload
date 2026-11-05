from pathlib import Path
root=Path('src')
p=root/'raster.s';s=p.read_text()
needle=' lea raster_buffer(pc),a0\n clr.l (a0)\n';assert needle in s;s=s.replace(needle,''' IFD P3_BACKGROUND
 move.l perf_game(pc),d0
 add.l #$32248,d0
 lea raster_bitmap_continue(pc),a0
 move.l d0,(a0)
 move.l perf_game(pc),d0
 add.l #$323a2,d0
 lea raster_bitmap_done(pc),a0
 move.l d0,(a0)
 ENDC
'''+needle,1)
needle='pl_raster:\n PL_START\n';assert needle in s;s=s.replace(needle,needle+''' IFD P3_BACKGROUND
 PL_PSS $21228,raster_bg_enter,2 ; PERF_RANGE h0:21228 8 bit=1
 PL_P $21ba8,raster_bg_exit ; PERF_RANGE h0:21ba8 6 bit=1
 PL_PSS $347b0,raster_bg_rect,34 ; PERF_RANGE h0:347b0 40 bit=1
 PL_P $32242,raster_bg_bitmap ; PERF_RANGE h0:32242 6 bit=1
 PL_P $323a6,raster_bg_bitmap_end ; PERF_RANGE h0:323a6 6 bit=1
 ENDC
''')
s=s.replace(' .copy_start:\n',' .copy_start:\n IFD P3_BACKGROUND\n bsr raster_bg_seed\n ENDC\n')
s=s.replace(' lea raster_taken(pc),a0\n move.w #1,(a0)\n rts\n',' lea raster_taken(pc),a0\n move.w #1,(a0)\n IFD P3_BACKGROUND\n IFD P3_FRAME_TWIN\n bsr raster_bg_reference\n ENDC\n ENDC\n rts\n')
s=s.replace('raster_after:\n dc.w $42e7 ; MOVE CCR,-(sp)\n movem.l d0-d2/a0-a2,-(sp)\n','raster_after:\n dc.w $42e7 ; MOVE CCR,-(sp)\n movem.l d0-d2/a0-a2,-(sp)\n IFD P3_BACKGROUND\n IFD P3_FRAME_TWIN\n bsr raster_bg_reference_end\n ENDC\n ENDC\n')
at=s.index('raster_degenerate:\n');tail=s[at:];needle=' movem.l d0-a6,-(sp)\n';assert needle in tail;tail=tail.replace(needle,needle+''' IFD P3_BACKGROUND
 move.w raster_background(pc),d0
 beq .bg_done
 bsr raster_frame_fallback
.bg_done:
 ENDC
''',1);s=s[:at]+tail
s+='\n IFD P3_BACKGROUND\n include "raster_background.s"\n ENDC\n';p.write_text(s)
p=root/'raster_frame.s';s=p.read_text();s=s.replace(' cmp.w #2,d0\n beq .done\n',' cmp.w #2,d0\n beq .done\n IFD P3_BACKGROUND\n cmp.w #1,d0\n beq .done\n ENDC\n',1)
s=s.replace(' cmp.b #4,$bfb(a4)\n bne .done\n',' cmp.b #4,$bfb(a4)\n bne .done\n cmp.b #15,$c36(a4)\n bne .done\n',1)
needle=' move.w $ce4(a4),d0\n bmi .done\n move.w $ce6(a4),d1\n';assert needle in s;s=s.replace(needle,''' IFD P3_BACKGROUND
 move.w raster_background(pc),d0
 beq .native_clip
 move.l $a(a5),a0
 move.w 4(a0),d0
 move.w 6(a0),d1
 bra .clip_ready
.native_clip:
 ENDC
 move.w $ce4(a4),d0
 move.w $ce6(a4),d1
 IFD P3_BACKGROUND
.clip_ready:
 ENDC
 tst.w d0
 bmi .done
''',1)
needle=' IFND P3_FRAME_TWIN\n adda.w raster_band_offset(pc),a0\n';assert needle in s;s=s.replace(needle,''' IFND P3_FRAME_TWIN
 IFD P3_BACKGROUND
 move.w raster_background(pc),d0
 beq .seed_plane
 adda.w #8000,a1
 bra .plane_done
.seed_plane:
 ENDC
 adda.w raster_band_offset(pc),a0
''',1)
s=s.replace(' dbra d1,.plane\n IFD P3_FRAME_TWIN\n',' IFD P3_BACKGROUND\n.plane_done:\n ENDC\n dbra d1,.plane\n IFD P3_FRAME_TWIN\n',1)
s=s.replace(' lea raster_fallback_count(pc),a0\n',' IFD P3_BACKGROUND\n bsr raster_bg_seed\n ENDC\n lea raster_fallback_count(pc),a0\n',1)
needle=' cmp.w #1,d0\n bne .fallback\n lea raster_fallback_pc(pc),a0\n';assert needle in s;s=s.replace(needle,''' cmp.w #1,d0
 bne .fallback
 IFD P3_BACKGROUND
 IFD P3_FRAME_TWIN
 move.w raster_bg_reference_active(pc),d0
 bne .owned
 ENDC
 move.w raster_background(pc),d0
 beq .unknown
 move.l 66(sp),d0
 sub.l perf_game(pc),d0
 cmp.l #$3408a,d0
 beq .owned
 cmp.l #$32186,d0
 beq .owned
 cmp.l #$32206,d0
 beq .owned
.unknown:
 ENDC
 lea raster_fallback_pc(pc),a0
''')
s=s.replace(' bsr raster_frame_fallback\n movem.l (sp)+,d0-a6\n',' bsr raster_frame_fallback\n IFD P3_BACKGROUND\n.owned:\n ENDC\n movem.l (sp)+,d0-a6\n',1);p.write_text(s)
p=Path('tools/build.sh');s=p.read_text();s=s.replace('cd "$GAME_SOURCE"','if [ "${P3_BACKGROUND:-0}" = 1 ]; then DEFINES+=(-DP3_BACKGROUND=1); fi\ncd "$GAME_SOURCE"');p.write_text(s)
