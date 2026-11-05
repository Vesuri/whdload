# S0 startup-only A/B on the retained all-car CCR benchmark. This is NOT
# activation of the selected production path: Plan B and coarse await S2/S3.
from pathlib import Path
import struct,subprocess,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-selection-elapsed';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();code=bytearray(base[32:-4]);size=len(code)
asm=(r/'tmp/build/step5-elapsed-ccr/fine.s').read_text()
selection=(r/'tmp/build/step5-selection/fine.s').read_text().split('selection_boot:',1)[1]
body,buffers=asm.split('velocity_records: ds.b 64000',1)
asm=body+'selection_boot:'+selection+'\nvelocity_records: ds.b 64000'+buffers
(o/'fine.s').write_text(asm);(o/'original_div.bin').write_bytes((r/'tmp/build/step5-elapsed-ccr/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
listing=(o/'fine.list').read_text();boot=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16)
assert size+boot<65536
struct.pack_into('>H',code,24,size+boot)
pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);struct.pack_into('>I',header,20,len(code)//4);header[28:32]=header[20:24]
(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
control=bytearray((o/'fine.slave').read_bytes());control[56:58]=base[56:58];(o/'control.slave').write_bytes(control)
print('Built selection startup A/B for the retained CCR benchmark')
