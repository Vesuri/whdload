from pathlib import Path
import subprocess,struct,re,hashlib
r=Path(__file__).resolve().parents[1];base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
for v in ('verify','lean'):
 prior=r/'tmp/build/step5-verify-split-module'/v;o=r/'tmp/build/step5-s2-scheduler-fix'/v;o.mkdir(parents=True,exist_ok=True)
 (o/'fine.s').write_bytes((prior/'fine.s').read_bytes());(o/'original_div.bin').write_bytes((prior/'original_div.bin').read_bytes())
 args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','fine.list','-o','fine.bin']
 if v=='verify':args+=['-DVERIFY=1']
 subprocess.run(args+['fine.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);size=len(code);listing=(o/'fine.list').read_text();boot=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16);assert size+boot<32768
 struct.pack_into('>H',code,24,size+boot);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
 h=bytearray(base[:32]);struct.pack_into('>I',h,20,len(code)//4);h[28:32]=h[20:24];(o/'fine.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
 if v=='verify':assert (o/'fine.slave').read_bytes()==(prior/'fine.slave').read_bytes()
 print(v,hashlib.sha256((o/'fine.slave').read_bytes()).hexdigest())
