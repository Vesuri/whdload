from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_b8_source.py').read_text().replace('step5-b8-v3-source','step5-b8-v3-tow')
fixture='''
B8TowFixture:
 cmpi.l #10,schedule_completed(pc)
 bne.b .done
 tst.w B8TowDone(pc)
 bne.b .done
 lea (B8TowDone.l,pc),a0
 move.w #1,(a0)
 jsr $69496
.done:
 rts
B8TowDone: dc.w 0
'''
extra="s=s.replace(' bsr.l B8PoseTick',' bsr.l B8TowFixture\\n bsr.l B8PoseTick',1)\ns=s.replace(' FF1UpdateWorkspace',"+repr(fixture+' FF1UpdateWorkspace')+",1)\n"
s=s.replace('exec(compile(s,',"s=s.replace(\"(o/'reset.bin').write_bytes\", "+repr(extra)+"+\"\\n(o/'reset.bin').write_bytes\",1)\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_b8_source.py'),'exec'))
