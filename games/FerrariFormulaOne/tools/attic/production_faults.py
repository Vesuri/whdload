from pathlib import Path
p=Path('Games/FerrariFormulaOne/ProductionFault.s');p.write_text('''; Leave WHDLoad cleanly if a production invariant or immutable signature fails.
; Diagnostic builds retain their breakpoint loops for the local harness.
FF1ProductionFault:
 lea start(pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 adda.l #FF1_HOST_ABORT,a2
 jmp (a2)
''')
for n,at in [('Coarse.s','selection_path:'),('Fine.s',' include "FerrariFormulaOne_Math.s"')]:
 p=Path('Games/FerrariFormulaOne')/n;s=p.read_text();s=s.replace(at,' include "ProductionFault.s"\n'+at,1);p.write_text(s)
p=Path('Games/FerrariFormulaOne/ProductionHost.s');s=p.read_text()+'''
FF1PerformanceAbort:
 pea .message(pc)
 pea (TDREASON_FAILMSG).w
 bra.w EXIT
.message:
 dc.b "Performance mode could not safely initialise or continue.",0
 even
''';p.write_text(s)
p=Path('Games/FerrariFormulaOne/build.py');s=p.read_text().replace("f'FF1_HOST_RESLOAD={hs[\"_resload\"]}'","f'FF1_HOST_RESLOAD={hs[\"_resload\"]}',f'FF1_HOST_ABORT={hs[\"FF1PerformanceAbort\"]}'");s=s.replace("assert a.game.stat().st_size==199368,'SPS 0481 racemenu required'","assert hashlib.sha256(a.game.read_bytes()).hexdigest()=='66ebd0939954329148e87c051fc041420d8f1ab4c2ad73ece7351b87ef9c889e','Verified SPS 0481 racemenu required'");p.write_text(s)
p=Path('Games/FerrariFormulaOne_Coarse.s');s=p.read_text().replace('.stop: bra.b .stop',' IFD FF1_PRODUCTION\n bra.w FF1ProductionFault\n ELSE\n.stop: bra.b .stop\n ENDC');p.write_text(s)
p=Path('Games/FerrariFormulaOne_UpdateHooks.s');s=p.read_text().replace('velocity_stop:\n bra.b velocity_stop','velocity_stop:\n IFD FF1_PRODUCTION\n bra.w FF1ProductionFault\n ELSE\n bra.b velocity_stop\n ENDC');p.write_text(s)
p=Path('Games/FerrariFormulaOne_Coarse200Motion.s');s=p.read_text().replace('velocity_stop:\n IFD FF1_C4_BLIT_GUARD','velocity_stop:\n IFD FF1_PRODUCTION\n bra.w C1Fault\n ELSE\n IFD FF1_C4_BLIT_GUARD').replace('velocity_initialized: dc.w 0',' ENDC\nvelocity_initialized: dc.w 0');p.write_text(s)
p=Path('Games/FerrariFormulaOne/Fine.s');s=p.read_text().replace(' move.l #1,(a0)\ndone:', ' move.l #1,(a0)\n bra.w FF1ProductionFault\ndone:').replace(' move.l #2,(a1)\n rts',' move.l #2,(a1)\n bra.w FF1ProductionFault').replace(' move.l d0,(a0)\n bra.b .coarse',' move.l d0,(a0)\n bra.l FF1ProductionFault');s=s.replace(' bsr.w FF1FinePauseInstall',' bsr.l FF1FinePauseInstall');s=s.replace(' bsr.w schedule_install',' tst.l error(pc)\n bne.l FF1ProductionFault\n bsr.w schedule_install');p.write_text(s)
p=Path('Games/FerrariFormulaOne_PublicLifecycle.s');s=p.read_text().replace('public_rollback:\n','public_rollback:\n');s=s.replace(' bsr.w public_reset\n lea (selection_path.l,pc),a0',' bsr.w public_reset\n IFD FF1_PRODUCTION\n bra.l FF1ProductionFault\n ENDC\n lea (selection_path.l,pc),a0')
for name in ['public_race_returns','public_fallbacks','public_unloads']:
 old=f' lea ({name}.l,pc),a0\n addq.l #1,(a0)';s=s.replace(old,' IFND FF1_PRODUCTION\n'+old+'\n ENDC')
p.write_text(s)
