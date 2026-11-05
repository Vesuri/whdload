from pathlib import Path
import os,ast
r=Path(__file__).resolve().parents[1];kind=os.environ.get('C1_FIXTURE','reload')
s=(r/'tools/build_step5_c4_blit_d1_ab.py').read_text()
coarse=(r.parents[1]/'Games/FerrariFormulaOne_Coarse.s').read_text();install=(r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text()
if kind=='exit':
 body='''C1Fixture:
 move.l C1Completed(pc),d0
 cmpi.l #10,d0
 bne.b .done
 move.w #1,$66be0
.done: rts
'''
elif kind=='images':
 body='C1Fixture: rts\n'
 coarse=coarse.replace(' tst.l d0\n bne.b .behind',' tst.l d0\n ; Image fixture: draw every admitted update.',1)
elif kind=='ownership':
 body="""C1Fixture:
 move.l C1Completed(pc),d0
 cmpi.l #1,d0
 bne.w .done
 ; Activation acquired the enabled BLIT bit.
 move.w C4BlitOwned(pc),d0
 cmpi.w #64,d0
 bne.w C1Fault
 bsr.w FF1C4BlitAcquire
 move.w C4BlitOwned(pc),d0
 cmpi.w #64,d0
 bne.w C1Fault
 ; Releasing twice must restore exactly once.
 bsr.w FF1C4BlitRestore
 bsr.w FF1C4BlitRestore
 move.w $dff01c,d0
 andi.w #64,d0
 beq.w C1Fault
 move.w C4BlitOwned(pc),d0
 bne.w C1Fault
 ; An initially disabled bit must stay disabled after acquire/release.
 move.w #64,$dff09a
 bsr.w FF1C4BlitAcquire
 move.w C4BlitOwned(pc),d0
 bne.w C1Fault
 bsr.w FF1C4BlitRestore
 move.w $dff01c,d0
 andi.w #64,d0
 bne.w C1Fault
 ; Return to race ownership, including the pending-completion case.
 move.w #$8040,$dff09c
 move.w #$8040,$dff09a
 bsr.w FF1C4BlitAcquire
 move.w C4BlitOwned(pc),d0
 cmpi.w #64,d0
 bne.w C1Fault
 move.w $dff01c,d0
 andi.w #64,d0
 bne.w C1Fault
 lea C4OwnershipPassed(pc),a0
 move.l #1,(a0)
.done:
 rts
C4OwnershipPassed: dc.l 0
"""
elif kind=='fault':
 body="""C1Fixture:
 move.l C1Completed(pc),d0
 cmpi.l #10,d0
 beq.w C1Fault
 rts
"""
elif kind=='reload':
 old=ast.parse((r/'tools/build_step5_b7_reload_v3.py').read_text());patch=next(ast.literal_eval(n.value) for n in old.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='patch' for t in n.targets))
 body=ast.literal_eval(ast.parse(patch).body[0].value.args[1]).replace('FF1PresentationAfterTick:', 'C1Fixture:',1).replace('schedule_completed','C1Completed').replace(' cmpi.l #10,C1Completed(pc)',' move.l C1Completed(pc),d0\n cmpi.l #10,d0').replace(' tst.l public_reload_count(pc)',' move.l public_reload_count(pc),d0')
 body=body.replace('bsr.l','bsr.w').replace('(public_reload_count.l,pc)','public_reload_count(pc)').replace('(public_reload_old.l,pc)','public_reload_old(pc)').replace('(public_reload_size.l,pc)','public_reload_size(pc)').replace('(public_reload_hold.l,pc)','public_reload_hold(pc)')
 body+='\npublic_reload_count: dc.l 0\npublic_descriptor: dc.l 0\npublic_reload_old: dc.l 0\npublic_reload_size: dc.l 0\npublic_reload_hold: ds.l 2\n'
 install=install.replace(' move.l a4,a2',' lea public_descriptor(pc),a0\n move.l a3,(a0)\n move.l a4,a2',1).replace(' move.l 160*4(a2),(a0)',' move.l 160*4(a2),(a0)\n lea public_reload_hold(pc),a0\n bsr.w FF1PublicRelease',1)
else:raise ValueError(kind)
coarse=coarse.replace('C1Checkpoint:\n nop','C1Checkpoint:\n bsr.w C1Fixture\n nop',1)+'\n'+body
inject="(o/'FerrariFormulaOne_Coarse.s').write_text("+repr(coarse)+")\n(o/'FerrariFormulaOne_CoarseInstall.s').write_text("+repr(install)+")\n"
s=s.replace("exec(compile(s,","s=s.replace('step5-c4-blit-d1-ab','step5-c4-blit-d1-ab-"+kind+"')\ns=s.replace('base=(r/',"+repr(inject)+"+'base=(r/',1)\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
