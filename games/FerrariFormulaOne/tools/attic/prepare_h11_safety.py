from pathlib import Path
import sys,shutil,subprocess
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_h7_legacy.py').read_text().replace('render-h7','render-h11-v2').replace('test_h7_legacy.py','test_h11_legacy.py');exec(compile(s,str(r/'tools/build_h7_legacy.py'),'exec'))
# Keep the prior compressed-capture-safe comparison implementation.
s=(r/'tools/test_h13_legacy.py').read_text().replace('h13','h11-v2');(r/'tools/test_h11_legacy.py').write_text(s)
for case in ['fault-set','fault-clear']:
 src=r/f'tmp/build/render-h11-v2-{case}-source';shutil.copytree(r/'tmp/build/render-h11-v2-matched-source',src,dirs_exist_ok=True)
 p=src/'FerrariFormulaOne_FullPresentation.s';s=p.read_text().replace(' bsr.l FF1RenderPrepareClock\n',' bsr.l FF1RenderPrepareClock\n bsr.l H11InjectFault\n');p.write_text(s)
 body='''
H11InjectFault:
 tst.w FF1RenderClockReady(pc)
 beq.b .done
 bsr.l FF1FineBlitRestore
 move.w #64,$dff09a
'''+(' move.w #$8040,$dff09a\n' if case=='fault-set' else '')+''' bsr.l FF1FineBlitAcquire
 bra.l FF1ProductionFault
.done:
 rts
'''
 p=src/'FerrariFormulaOne/Fine.s';s=p.read_text().replace(' include "RenderOverlap.s"',body+'\n include "RenderOverlap.s"');p.write_text(s)
 out=r/f'tmp/build/render-h11-v2-{case}';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(out)],check=True)
s=(r/'tools/test_h7_ownership.py').read_text().replace("kind='h7-ownership'","kind='h11-ownership'").replace(" report['status']='passed'", " report['clock_ready_at_fault']=val(f'*(unsigned short*){probe+sy[\"FF1RenderClockReady\"]}');assert report['clock_ready_at_fault']==1\n report['status']='passed'");(r/'tools/test_h11_fault.py').write_text(s)
s=(r/'tools/test_h7_live.py').read_text().replace("  v['intena']=", "  v['clock_ready']=struct.unpack_from('>H',m,probe+sy['FF1RenderClockReady'])[0];assert v['clock_ready']==0\n  v['intena']=");(r/'tools/test_h11_live.py').write_text(s)
s=(r/'tools/run_h7_live.py').read_text().replace('test_h7_live.py','test_h11_live.py');(r/'tools/run_h11_live.py').write_text(s)
