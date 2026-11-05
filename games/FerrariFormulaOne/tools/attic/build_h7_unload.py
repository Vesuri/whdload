from pathlib import Path
import shutil,subprocess,sys
r=Path(__file__).resolve().parents[1];games=r.parents[1]/'Games'
for bit in [0,64]:
 case='unload-'+str(bit);source=r/f'tmp/build/render-h7-{case}-source';source.mkdir(exist_ok=True)
 for p in games.glob('FerrariFormulaOne_*.s'):shutil.copy2(p,source/p.name)
 shutil.copytree(games/'FerrariFormulaOne',source/'FerrariFormulaOne',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 code='''
H7UnloadTest:
 bsr.l FF1FineBlitRestore
 move.w #64,$dff09a
'''+(' move.w #$8040,$dff09a\n' if bit else '')+'''
 bsr.l FF1FineBlitAcquire
H7UnloadStart:
 move.l public_table(pc),a0
 move.l (a0),d0
 lsl.l #2,d0
 addi.l #4+$35c,d0
 move.l d0,a0
 move.l H7Descriptor(pc),a4
 jsr (a0)
H7UnloadDone:
 bra.b H7UnloadDone
H7Descriptor: dc.l 0
'''
 p=source/'FerrariFormulaOne/Fine.s';s=p.read_text().replace('FF1PresentationAfterTick:\n','FF1PresentationAfterTick:\n bsr.l H7UnloadTest\n').replace(' include "RenderBlit.s"',' include "RenderBlit.s"\n'+code).replace(' move.l a4,a2',' lea (H7Descriptor.l,pc),a0\n move.l a3,(a0)\n move.l a4,a2');p.write_text(s)
 subprocess.run([sys.executable,str(source/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(r/f'tmp/build/render-h7-{case}')],check=True)
s=(r/'tools/test_h7_ownership.py').read_text();a=s.index(" if 'H7OwnershipPassed' in sy:");z=s.index(" report['status']='passed'",a)
s=s[:a]+'''
 cmd('delete');cmd(f'break *{probe+sy["H7UnloadStart"]}');assert 'Breakpoint' in cmd('continue')
 entry=val('*(unsigned short*)0xdff01c');saved=val(f'*(unsigned short*){probe+sy["FF1FineBlitSaved"]}')
 assert not entry&64 and saved==int(variant.split('-')[-1])
 memory=dump('before-unload');ledger=probe+sy['public_patch_context'];data,capacity,used=struct.unpack_from('>III',memory,ledger+8)
 expected={}
 for i in range(0,used,6):
  address,word=struct.unpack_from('>IH',memory,data+i);expected.setdefault(address,word)
 cmd('delete');cmd(f'break *{probe+sy["public_unload_jump"]}');assert 'Breakpoint' in cmd('continue')
 memory=dump('restored-before-free');assert memory[ledger:ledger+24]==bytes(24)
 for address,word in expected.items():assert struct.unpack_from('>H',memory,address)[0]==word,hex(address)
 assert val(f'*(unsigned int*){probe+sy["FF1FineBlitActive"]}')==0
 assert val('*(unsigned short*)0xdff01c')==entry|saved
 cmd('delete');cmd(f'break *{probe+sy["H7UnloadDone"]}');assert 'Breakpoint' in cmd('continue')
 assert val('$pc')==probe+sy['H7UnloadDone']
 report.update(ledger_words_restored=len(expected),entry_intena=entry,saved_blit=saved,after_intena=val('*(unsigned short*)0xdff01c'),native_unload_returned=True)
'''+s[z:];s=s.replace("kind='h7-ownership'","kind='h7-unload'");(r/'tools/test_h7_unload.py').write_text(s)
