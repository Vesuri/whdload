from pathlib import Path
import os,sys,subprocess,json,struct,shutil,re
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_drive_matched.py').read_text().replace('drive-matched','render-h3-matched')
exec(compile(s,str(r/'tools/build_drive_matched.py'),'exec'))
def control(b):
 o=b.with_name(b.name+'-control');shutil.copytree(b,o,dirs_exist_ok=True);m=json.loads((b/'build.json').read_text());at=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['FF1RenderRoadControl'];p=o/'FerrariFormulaOne.slave';d=bytearray(p.read_bytes());assert d[at:at+2]==b'\0\1';d[at:at+2]=b'\0\0';p.write_bytes(d)
def frames(base):
 m=json.loads((base/'build.json').read_text());info=m['payloads']['fine'];sy=info['symbols'];offset=info['offset'];listing=(base/'fine/fine.list').read_text();data=bytearray((base/'FerrariFormulaOne.slave').read_bytes());off=32+offset
 rows=[int(x[1],16) for x in re.finditer(r'^00:([0-9A-F]{8}) 66[0-9A-F]{2}\s+\d+:\s+bne.b .done',listing,re.M) if sy['FF1PresentationAfterTick']<=int(x[1],16)<sy['B8DrawEnabled']];assert len(rows)==1;data[off+rows[0]:off+rows[0]+2]=bytes.fromhex('4e71')
 anchor=late=None
 for line in listing.splitlines():
  x=re.match(r'^00:([0-9A-F]{8})\s+[0-9A-F]+\s+\d+:\s+(.*)',line)
  if not x:continue
  pc=int(x[1],16)
  if not sy['B8PrepareRenderCopies']<=pc<sy['B8PublishProjection']:continue
  if 'lea (schedule_context.l,pc),a0' in x[2]:anchor=pc
  if x[2].strip()=='moveq #100,d6':late=pc
 assert anchor and late;data[off+anchor:off+anchor+4]=bytes.fromhex('6000')+struct.pack('>h',late-anchor-2)
 o=base.with_name(base.name+'-frames');shutil.copytree(base,o,dirs_exist_ok=True);(o/'FerrariFormulaOne.slave').write_bytes(data);control(o)
base=r/'tmp/build/render-h3-matched';control(base);frames(base)
for case,fn in [('grid','step5_c4_start_grid_center_fixture.s'),('dense','step5_c4_heavy_v2_fixture.s')]:
 source=r/f'tmp/build/render-h3-{case}-source';shutil.copytree(r/'tmp/build/render-h3-matched-source',source,dirs_exist_ok=True)
 asm=(r/'tools'/fn).read_text();a=asm.index(' move.w C1Control');b=asm.index('.done:',a);asm=asm[:a]+asm[b:];asm=asm.replace('C1Fault','FF1ProductionFault').replace('move.w sr,','move.w ccr,').replace('.w FF1ProductionFault','.l FF1ProductionFault')
 insert=''
 for dest in [96,112,128,192,208]:insert+=f' lea ${0x6a5aa+dest:x},a0\n lea (B8RenderArena+{dest}.l,pc),a1\n'+(' move.l (a0)+,(a1)+\n'*4)
 asm=asm.replace('HeavyStartDone:',insert+'HeavyStartDone:')
 p=source/'FerrariFormulaOne/Fine.s';t=p.read_text().replace(' bsr.l FF1RenderInstallColourElide',' bsr.l HeavyInit\n bsr.l FF1RenderInstallColourElide').replace(' bsr.l B8Draw',' bsr.l HeavyBegin\n bsr.l B8Draw\n bsr.l HeavyEnd').replace(' include "RenderColour.s"',asm+'\n include "RenderColour.s"');p.write_text(t)
 # Fixture state is initialized once, never used for lifecycle tests. Exclude
 # its hand-copied declarations from the production reset-table parser.
 p=source/'FerrariFormulaOne/reset.py';p.write_text(p.read_text().replace(' if pc>=sy.get('," if sy.get('HeavyInit',1<<30)<=pc<sy.get('FF1RenderInstallColourElide',0):continue\n if pc>=sy.get("))
 o=r/f'tmp/build/render-h3-{case}';subprocess.run([sys.executable,str(source/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(o)],check=True);control(o);frames(o)
