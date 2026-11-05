from pathlib import Path
import re,json,shutil,subprocess,sys,struct
r=Path(__file__).resolve().parents[1]
# Matched-state builder already owns the established startup RNG control.
s=(r/'tools/build_drive_matched.py').read_text().replace('drive-matched','render-h7-matched')
exec(compile(s,str(r/'tools/build_drive_matched.py'),'exec'))
def control(b):
 o=b.with_name(b.name+'-control');shutil.copytree(b,o,dirs_exist_ok=True);m=json.loads((b/'build.json').read_text());at=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['FF1FineBlitControl'];p=o/'FerrariFormulaOne.slave';d=bytearray(p.read_bytes());assert d[at:at+2]==b'\0\1';d[at:at+2]=b'\0\0';p.write_bytes(d)
def frames(base):
 m=json.loads((base/'build.json').read_text());info=m['payloads']['fine'];sy=info['symbols'];off=32+info['offset'];listing=(base/'fine/fine.list').read_text();data=bytearray((base/'FerrariFormulaOne.slave').read_bytes())
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
base=r/'tmp/build/render-h7';subprocess.run([sys.executable,str(r.parents[1]/'Games/FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(base)],check=True);control(base)
base=r/'tmp/build/render-h7-matched';control(base);frames(base)
# Use the existing Hi25 fixture implementation, changing only output/input roots.
s=(r/'tools/build_hi25_fixtures.py').read_text().replace('render-h5-matched-source','render-h7-matched-source').replace('render-hi25-','render-h7-')
sys.argv=['build_hi25_fixtures.py','solo','grid','dense'];exec(compile(s,str(r/'tools/build_hi25_fixtures.py'),'exec'))
for scene in ['solo','grid','dense']:
 b=r/f'tmp/build/render-h7-{scene}';control(b);frames(b)
