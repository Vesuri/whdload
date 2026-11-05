from pathlib import Path
import sys,shutil,json
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_h7_legacy.py').read_text().replace('render-h7','render-h13').replace('test_h7_legacy.py','test_h13_legacy.py');exec(compile(s,str(r/'tools/build_h7_legacy.py'),'exec'))
b=r/'tmp/build/render-h13';o=r/'tmp/build/render-h13-bad-signature';shutil.copytree(b,o,dirs_exist_ok=True);m=json.loads((b/'build.json').read_text());f=m['payloads']['fine'];start=32+f['offset']+f['symbols']['FF1RenderInstallGauges'];p=o/'FerrariFormulaOne.slave';v=bytearray(p.read_bytes());first=v.index(bytes.fromhex('0c794eb9'),start,start+64);at=v.index(bytes.fromhex('0c794eb9'),first+4,start+96)+3;v[at]^=1;p.write_bytes(v)
s=(r/'tools/test_h9_fault.py').read_text().replace('h9','h13').replace('H9','H13').replace("profile.startswith('a1200')","not profile.startswith('a500')").replace('else 0x600000','else 0xa00000').replace('road_fill','gauge').replace('addresses.map(0x6abc6)','addresses.map(0x6bd66)').replace("bytes.fromhex('4eb9')+struct.pack('>I',addresses.map(0x2a130))","bytes.fromhex('4eb9')+struct.pack('>I',addresses.map(0x24ae0))");(r/'tools/test_h13_fault.py').write_text(s)
