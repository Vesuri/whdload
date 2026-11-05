from pathlib import Path
import subprocess,struct,re,hashlib
r=Path(__file__).resolve().parents[1];base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
for variant in ('verify','lean'):
 o=r/'tmp/build/step5-b5-v5'/variant;o.mkdir(parents=True,exist_ok=True)
 s=(r/f'tmp/build/step5-s3/{variant}-p0/fine.s').read_text().replace(' bsr.w FF1InstallPresentation',' bsr.w FF1InstallPresentation\n bsr.w FF1InstallOpponents')
 s=s.replace('bsr.w FF1InstallPresentation','bsr.l FF1InstallPresentation').replace('bsr.w FF1InstallOpponents','bsr.l FF1InstallOpponents')
 (o/'fine.s').write_text(s);(o/'original_div.bin').write_bytes((r/f'tmp/build/step5-s3/{variant}-p0/original_div.bin').read_bytes())
 args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1','-DFF1_HELPERS_020=1','-L','fine.list','-o','fine.bin']
 if variant=='verify':args+=['-DVERIFY=1']
 subprocess.run(args+['fine.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);size=len(code);listing=(o/'fine.list').read_text();entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16);assert size+entry<32768
 struct.pack_into('>H',code,24,size+entry);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
 h=bytearray(base[:32]);struct.pack_into('>I',h,20,len(code)//4);h[28:32]=h[20:24];(o/'fine.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
 print(variant,hashlib.sha256((o/'fine.slave').read_bytes()).hexdigest())
