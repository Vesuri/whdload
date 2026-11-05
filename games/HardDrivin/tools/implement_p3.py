from pathlib import Path
p=Path('src/HardDrivinPhase.s')
s=p.read_text();Path('tmp/phase-p3-before.s').write_text(s)
s=s.replace('move.l d0,(a0)\n lea _phase_patches','move.l d0,(a0)+\n move.l _code_start(pc),d0\n addi.l #$b904,d0\n move.l d0,(a0)\n lea _phase_patches',1)
s=s.replace('_phase_manual_ptr: dc.l 0','_phase_manual_ptr: dc.l 0\n_phase_continue_ptr: dc.l 0')
s=s.replace(' clr.w PH_ACTIVE(a0)\n movea.l',' clr.w PH_ACTIVE(a0)\n clr.w _phase_cache_valid-_phase_state(a0)\n movea.l',1)
s=s.replace('_phase_engine_call:\n move.l _drivetrain_engine(pc),-(a7)\n rts', '''; Cache only the pure B678..B904 endpoint, within one eight-field phase.
; prepare_anchor normalizes speed/RPM, derived engine speed, scalar carries and
; gear before this call. Gear ratios and native math tables are immutable.
; Key: full Q16 anchors, gear, throttle, brake, contact, skid, road, turning,
; grade-disable, engine-disable, automatic and pitch sine. PH_DT is deliberately
; not an endpoint input: off-road retention consumes it separately on every hit.
; B904 onward ALWAYS runs: phase integration, boundary-only gear selection and
; gear pointer, MPH/engine-speed publication, brake clear, final-segment audio.
; Position/spin/skid exit still run once per outer frame, outside this routine.
 dc.b 'HDENGC01'
_phase_cache_valid: dc.w 0
_phase_cache_key: dcb.b 22,0
_phase_cache_endpoint: dc.l 0
_phase_cache_hits: dc.l 0
_phase_cache_misses: dc.l 0
_phase_engine_call:
 lea _phase_cache_valid(pc),a0
 tst.w PH_PHASE(a6)
 beq .miss
 tst.w (a0)
 beq .miss
 move.l PH_ANCHOR_V(a6),d0
 cmp.l 2(a0),d0
 bne .miss
 move.l PH_ANCHOR_R(a6),d0
 cmp.l 6(a0),d0
 bne .miss
 move.w PH_GEAR(a6),d0
 cmp.w 10(a0),d0
 bne .miss
 move.b -$66e4(a4),d0
 cmp.b 12(a0),d0
 bne .miss
 move.b -$66ef(a4),d0
 cmp.b 13(a0),d0
 bne .miss
 move.b -$66f0(a4),d0
 cmp.b 14(a0),d0
 bne .miss
 move.b -$50cf(a4),d0
 cmp.b 15(a0),d0
 bne .miss
 move.b -$16b6(a4),d0
 cmp.b 16(a0),d0
 bne .miss
 move.b -$0870(a4),d0
 cmp.b 17(a0),d0
 bne .miss
 move.b -$086f(a4),d0
 cmp.b 18(a0),d0
 bne .miss
 move.b -$69fa(a4),d0
 cmp.b 19(a0),d0
 bne .miss
 move.b -$66c2(a4),d0
 cmp.b 20(a0),d0
 bne .miss
 move.w -$6bb4(a4),d0
 cmp.w 22(a0),d0
 bne .miss
 addq.l #1,28(a0)
 ; Match the native B662 stack frame so its existing gear/tail code returns
 ; normally. No automatic-path tail reads the skipped engine stack locals.
 link a5,#-20
 movem.l d4/a2-a3,-(a7)
 tst.b -$16b6(a4)
 bne.s .retained
 cmpi.b #30,-$66e4(a4)
 ble.s .retained
 bsr _time_throttle_retention
.retained:
 lea _phase_cache_endpoint(pc),a0
 move.l (a0),-$66d8(a4)
 lea _time_scalar_state(pc),a0
 move.w -$66d8(a4),SS_VELOCITY_LAST(a0)
 move.w -$66d6(a4),SS_RPM_LAST(a0)
 move.l _phase_continue_ptr(pc),-(a7)
 rts
.miss:
 addq.l #1,32(a0)
 move.w #1,(a0)+
 move.l PH_ANCHOR_V(a6),(a0)+
 move.l PH_ANCHOR_R(a6),(a0)+
 move.w PH_GEAR(a6),(a0)+
 move.b -$66e4(a4),(a0)+
 move.b -$66ef(a4),(a0)+
 move.b -$66f0(a4),(a0)+
 move.b -$50cf(a4),(a0)+
 move.b -$16b6(a4),(a0)+
 move.b -$0870(a4),(a0)+
 move.b -$086f(a4),(a0)+
 move.b -$69fa(a4),(a0)+
 move.b -$66c2(a4),(a0)+
 clr.b (a0)+
 move.w -$6bb4(a4),(a0)
 move.l _drivetrain_engine(pc),-(a7)
 rts''')
s=s.replace(' beq.s .restore\n move.w PH_DT(a2),d1',' beq.s .restore\n lea _phase_cache_endpoint(pc),a0\n move.l -$66d8(a4),(a0)\n move.w PH_DT(a2),d1',1)
p.write_text(s)
