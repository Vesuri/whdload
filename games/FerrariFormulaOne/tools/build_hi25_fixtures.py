#!/usr/bin/env python3
# Hi25 profiling fixtures (test-only, never production builds), from the H5
# matched source: solo = fixed dense-pack pose with the seven native per-car
# draw calls counted and returned before any sprite work; grid/dense = the H5
# fixtures. Suffix -nbi adds a diagnostic BLIT-interrupt disable before every
# draw (what-if measurement only; no ownership/restore handling).
from pathlib import Path
import sys,subprocess,shutil
r=Path(__file__).resolve().parents[1]
for name in sys.argv[1:] or ['solo']:
 case,_,opt=name.partition('-')
 source=r/f'tmp/build/render-hi25-{name}-source'
 shutil.copytree(r/'tmp/build/render-h5-matched-source',source,dirs_exist_ok=True)
 fn={'solo':'step5_c4_heavy_v2_fixture.s','dense':'step5_c4_heavy_v2_fixture.s','grid':'step5_c4_start_grid_center_fixture.s'}[case]
 asm=(r/'tools'/fn).read_text();a=asm.index(' move.w C1Control');b=asm.index('.done:',a);asm=asm[:a]+asm[b:];asm=asm.replace('C1Fault','FF1ProductionFault').replace('move.w sr,','move.w ccr,').replace('.w FF1ProductionFault','.l FF1ProductionFault')
 if case=='solo':
  old=' move.l (sp)+,d0\n link a6,#-22\n movem.l d2-d5,-(sp)\n jmp $69e4c\n';assert asm.count(old)==1
  asm=asm.replace(old,' move.l (sp)+,d0\n rts\n')
 if opt=='nbi':
  assert asm.count('HeavyBegin:\n')==1;asm=asm.replace('HeavyBegin:\n','HeavyBegin:\n move.w #$0040,$dff09a\n')
 insert=''
 for dest in [96,112,128,192,208]:insert+=f' lea ${0x6a5aa+dest:x},a0\n lea (B8RenderArena+{dest}.l,pc),a1\n'+(' move.l (a0)+,(a1)+\n'*4)
 asm=asm.replace('HeavyStartDone:',insert+'HeavyStartDone:')
 p=source/'FerrariFormulaOne/Fine.s';t=p.read_text()
 for x in (' bsr.l FF1RenderInstallColourElide',' bsr.l B8Draw',' include "RenderColour.s"'):assert t.count(x)==1,x
 t=t.replace(' bsr.l FF1RenderInstallColourElide',' bsr.l HeavyInit\n bsr.l FF1RenderInstallColourElide').replace(' bsr.l B8Draw',' bsr.l HeavyBegin\n bsr.l B8Draw\n bsr.l HeavyEnd').replace(' include "RenderColour.s"',asm+'\n include "RenderColour.s"');p.write_text(t)
 p=source/'FerrariFormulaOne/reset.py';s=p.read_text();old=' if pc>=sy.get(';assert old in s
 p.write_text(s.replace(old," if sy.get('HeavyInit',1<<30)<=pc<sy.get('FF1RenderInstallColourElide',0):continue\n if pc>=sy.get(",1))
 o=r/f'tmp/build/render-hi25-{name}'
 subprocess.run([sys.executable,str(source/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne/data/racemenu'),'--out',str(o)],check=True)
 print('built',o)
