from pathlib import Path
import shutil,subprocess,sys
r=Path(__file__).resolve().parents[1];games=r.parents[1]/'Games'
body='''
H7OwnershipTest:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 tst.l H7OwnershipPassed(pc)
 bne.w .done
 move.w FF1FineBlitSaved(pc),d7
 bsr.l FF1FineBlitRestore
 moveq #0,d6
.case:
 move.w #$0040,$dff09a
 tst.w d6
 beq.b .clear
 move.w #$8040,$dff09a
.clear:
 move.w $dff01c,d5
 move.w #$1f,ccr
 bsr.l FF1FineBlitAcquire
 move.w ccr,d0
 cmpi.w #$1f,d0
 bne.w H7OwnershipFail
 cmpi.w #1,FF1FineBlitActive(pc)
 bne.w H7OwnershipFail
 cmp.w FF1FineBlitSaved(pc),d6
 bne.w H7OwnershipFail
 move.w $dff01c,d0
 andi.w #64,d0
 bne.w H7OwnershipFail
 ; Re-enable while owned, including a pending completion. Reacquire must
 ; clear it without replacing the epoch's original bit.
 move.w #$8040,$dff09c
 move.w #$8040,$dff09a
 bsr.l FF1FineBlitAcquire
 bsr.l FF1FineBlitAcquire
 cmp.w FF1FineBlitSaved(pc),d6
 bne.w H7OwnershipFail
 move.w $dff01c,d0
 andi.w #64,d0
 bne.w H7OwnershipFail
 move.w #$1f,ccr
 bsr.l FF1FineBlitRestore
 move.w ccr,d0
 cmpi.w #$1f,d0
 bne.w H7OwnershipFail
 bsr.l FF1FineBlitRestore
 tst.l FF1FineBlitActive(pc)
 bne.w H7OwnershipFail
 move.w $dff01c,d0
 cmp.w d5,d0
 bne.w H7OwnershipFail
 tst.w d6
 bne.b .passed
 moveq #64,d6
 bra.w .case
.passed:
 move.w #64,$dff09a
 tst.w d7
 beq.b .return
 move.w #$8040,$dff09a
.return:
 bsr.l FF1FineBlitAcquire
 lea H7OwnershipPassed(pc),a0
 move.l #1,(a0)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts
H7OwnershipFail:
 bra.l FF1ProductionFault
H7OwnershipPassed: dc.l 0
'''
for case in ['ownership','fault-set','fault-clear','schedule-fault','velocity-fault']:
 source=r/f'tmp/build/render-h7-{case}-source';source.mkdir(exist_ok=True)
 for p in games.glob('FerrariFormulaOne_*.s'):shutil.copy2(p,source/p.name)
 shutil.copytree(games/'FerrariFormulaOne',source/'FerrariFormulaOne',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 p=source/'FerrariFormulaOne/Fine.s';s=p.read_text()
 if case=='ownership':code=body
 else:
  target={'schedule-fault':'schedule_bad','velocity-fault':'velocity_fault'}.get(case,'FF1ProductionFault')
  code='H7OwnershipTest:\n bsr.l FF1FineBlitRestore\n move.w #64,$dff09a\n'+(' move.w #$8040,$dff09a\n' if case!='fault-clear' else '')+' bsr.l FF1FineBlitAcquire\n bra.l '+target+'\n'
 s=s.replace('FF1PresentationAfterTick:\n','FF1PresentationAfterTick:\n bsr.l H7OwnershipTest\n').replace(' include "RenderBlit.s"',' include "RenderBlit.s"\n'+code);p.write_text(s)
 out=r/f'tmp/build/render-h7-{case}';subprocess.run([sys.executable,str(source/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(out)],check=True)
