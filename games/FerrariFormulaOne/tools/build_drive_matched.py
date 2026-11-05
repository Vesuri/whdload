from pathlib import Path
import shutil,os,subprocess,sys
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'tools'));from ff1layout import legacy;g=legacy();o=r/'tmp/build/drive-matched-source';o.mkdir(exist_ok=True)
for p in g.glob('FerrariFormulaOne_*.s'):shutil.copy2(p,o/p.name)
shutil.copytree(g/'FerrariFormulaOne',o/'FerrariFormulaOne',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
old=(r/'tmp/build/step5-b8-v3/lean/fine.s').read_text();rng=old[old.index('s2_rng_control:'):old.index('FF1PresentationAfterTick:')]
p=o/'FerrariFormulaOne_Coarse.s';s=p.read_text().replace(' IFD FF1_PRODUCTION\n move.w C1Active',' IFD NEVER_DEFINED\n move.w C1Active').replace(' IFND FF1_PRODUCTION\n lea s2_rng_done',' IFD FF1_PRODUCTION\n lea s2_rng_done');p.write_text(s)
p=o/'FerrariFormulaOne_CoarseInstall.s';s=p.read_text().replace(' IFND FF1_PRODUCTION\n move.w #$4eb9,$6a304',' IFD FF1_PRODUCTION\n move.w #$4eb9,$6a304');p.write_text(s)
p=o/'FerrariFormulaOne/Coarse.s';s=p.read_text().replace(' include "FerrariFormulaOne_Coarse.s"',rng.replace(' move.w ccr,-(sp)',' C1SaveFlags')+'\n include "FerrariFormulaOne_Coarse.s"')
# Macro is declared by Coarse.s, so the diagnostic RNG copy must follow it.
a=s.index('s2_rng_control:');z=s.index(' include "FerrariFormulaOne_Coarse.s"',a);stub=s[a:z];s=s[:a]+s[z:];s=s.replace('public_table: dc.l 0',stub+'\npublic_table: dc.l 0');p.write_text(s)
p=o/'FerrariFormulaOne/Fine.s';s=p.read_text().replace(' tst.w schedule_context+FF1T_STEP_MS(pc)\n bne.w finish',' lea (ticks.l,pc),a0\n addq.l #1,(a0)\n cmpi.l #126,(a0)\n bne.w finish').replace(' addq.l #1,(a0)\n lea (barrier.l,pc),a0',' move.w #$4eb9,$6a304\n lea s2_rng_control(pc),a1\n move.l a1,$6a306\n addq.l #1,(a0)\n lea (barrier.l,pc),a0').replace('FF1PresentationAfterTick:',rng+'\nFF1PresentationAfterTick:');p.write_text(s)
subprocess.run([sys.executable,str(o/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne/data/racemenu'),'--out',str(r/'tmp/build/drive-matched')],check=True)
