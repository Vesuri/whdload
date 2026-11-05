from pathlib import Path
import sys,re,json
r=Path(__file__).resolve().parents[1];kind=sys.argv[1] if len(sys.argv)>1 else 'position'
old=(r/f'tools/build_step5_native_{kind}_writers.py').read_text()
ns={};snippet=old[old.index("extra='''writer_fixture:"):old.index('asm+=extra')];exec(snippet,ns);a=ns['extra']
a=re.sub(r' lea start\(pc\),a2\n.*? jsr \$20\(a2\)\n','',a,flags=re.S)
a=re.sub(r'(d[0-7])\.l\)',r'\1.w)',a)
if kind=='position':
 endpoints=[0x663fa,0x68c18,0x6895e,0x688e8,0x68920,0x68ac0,0x68b2c]
 blocks=[('$6a61a',32),('$227ca',16),('position_shadow',96),('saved_position',48)]
 cases=[dict(car=c,operation=op) for c in range(8) for op in ('snapshot','restore','init_x_111','init_z_222','init_x_333','init_x_444','zero_z')];record=192
else:
 endpoints=[0x68996,0x689a6,0x68b9e,0x68bb2,0x6e96e]
 blocks=[('$6f13c',32),('velocity_shadow',96)]
 cases=[dict(car=c,operation=op) for c in range(8) for op in ('zero_x_a','zero_z','zero_x_b','set_z200','zero_both')];record=132
blocks=[(f'${p:x}',6) for p in endpoints]+blocks
save=' movem.l d0-d7/a0-a6,-(sp)\n lea QWriterSaved(pc),a1\n'
restore=' lea QWriterSaved(pc),a1\n'
for i,(addr,n) in enumerate(blocks):
 lea=' lea '+addr+('' if addr.startswith('$') else '(pc)')+',a0\n'
 save+=lea+f' move.w #{n//2-1},d0\n.qsave{i}: move.w (a0)+,(a1)+\n dbra d0,.qsave{i}\n'
 restore+=lea+f' move.w #{n//2-1},d0\n.qrestore{i}: move.w (a1)+,(a0)+\n dbra d0,.qrestore{i}\n'
a=a.replace('writer_fixture:\n','writer_fixture:\n'+save,1).replace('writer_complete:\n bra.b writer_complete','writer_complete:\n'+restore+' movem.l (sp)+,d0-d7/a0-a6\n rts')
a+='QWriterSaved: ds.b '+str(sum(n for _,n in blocks))+'\n'
(r/f'tools/step5_c4_q02_{kind}.s').write_text(a)
(r/f'manifest/step5-c4-q02-{kind}-cases.json').write_text(json.dumps(dict(cases=cases,record_size=record),indent=2)+'\n')
s=(r/'tools/build_step5_c4_divide_frame_r3g_ab.py').read_text().replace('step5-c4-divide-frame-r3g-v1-ab',f'step5-c4-q02-{kind}')
inject="import shutil\nshutil.copy(r/'tools/step5_c4_q02_"+kind+".s',o/'qwriter.s')\np=o/'FerrariFormulaOne_CoarseInstall.s'\np.write_text((r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text().replace(' bsr.w FF1TimeInit',' bsr.w FF1TimeInit\\n bsr.w writer_fixture'))\n"
s=s.replace('exec(compile(s,',"s=s.replace('base=(r/',"+repr(inject)+"+'base=(r/',1)\ns=s.replace('public_bindings:', ' include \"qwriter.s\"\\npublic_bindings:')\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
