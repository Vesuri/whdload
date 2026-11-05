from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_c4_colour_r2_ab.py').read_text()
asm=(r/'tools/step5_c4_heavy_v2_fixture.s').read_text()
coarse=(r.parents[1]/'Games/FerrariFormulaOne_Coarse.s').read_text()
coarse=coarse.replace(' bsr.w B8Draw',' bsr.w HeavyBegin\n bsr.w B8Draw\n bsr.w HeavyEnd',1)+'\n'+asm
install=(r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text()
install=install.replace('C1Activate:\n movem.l d0-d7/a0-a6,-(sp)','C1Activate:\n movem.l d0-d7/a0-a6,-(sp)\n bsr.w HeavyInit',1)
coarse=coarse.replace(' tst.l d0\n bne.b .behind',' tst.l d0\n ; Draw every update for deterministic image comparison.',1)
inject="(o/'FerrariFormulaOne_Coarse.s').write_text("+repr(coarse)+")\n(o/'FerrariFormulaOne_CoarseInstall.s').write_text("+repr(install)+")\n"
s=s.replace("exec(compile(s,","s=s.replace('step5-c4-colour-r2-v2-ab','step5-c4-colour-r2-v2-heavy-v2-images')\ns=s.replace('base=(r/',"+repr(inject)+"+'base=(r/',1)\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
