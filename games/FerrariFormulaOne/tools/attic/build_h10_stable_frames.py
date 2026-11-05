from pathlib import Path
import shutil,subprocess,sys
r=Path(__file__).resolve().parents[1]
# Retain all existing fixed-update/endpoint fixture patches. Observe a complete
# scanout while the CPU waits after drawing; do not change palette or pixels.
helpers=(r/'tools/prepare_h10.py').read_text();helpers=helpers[helpers.index('def control('):helpers.index("base=r/'tmp/build/render-h10';")]
import re,json,struct
exec(helpers)
for scene in ['matched','solo','grid','dense']:
 src=r/f'tmp/build/render-h10-{scene}-source';dst=r/f'tmp/build/render-h10-{scene}-stable-source'
 shutil.copytree(src,dst,dirs_exist_ok=True)
 p=dst/'FerrariFormulaOne/Fine.s';s=p.read_text();assert s.count(' bsr.l B8Draw\n')==1
 s=s.replace(' bsr.l B8Draw\n',' bsr.l B8Draw\n bsr.l H7FrameHold\n')
 s+='''\n; Test-only scanout hold, entered at the completed-draw capture breakpoint.\n; Three complete PAL fields leave two captured fields free of CPU palette writes.\nH7FrameHold:\n move.w ccr,-(sp)\n move.l d0,-(sp)\n moveq #2,d0\n.edge:\n btst #0,$dff005\n beq.b .edge\n.wrap:\n btst #0,$dff005\n bne.b .wrap\n dbra d0,.edge\n move.l (sp)+,d0\n move.w (sp)+,ccr\n rts\n'''
 p.write_text(s)
 out=r/f'tmp/build/render-h10-{scene}-stable'
 subprocess.run([sys.executable,str(dst/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(out)],check=True)
 frames(out)
