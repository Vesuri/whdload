from pathlib import Path
import sys,shutil,json
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_h7_legacy.py').read_text().replace('render-h7','render-h10').replace('test_h7_legacy.py','test_h10_legacy.py');exec(compile(s,str(r/'tools/build_h7_legacy.py'),'exec'))
b=r/'tmp/build/render-h10';o=r/'tmp/build/render-h10-bad-signature';shutil.copytree(b,o,dirs_exist_ok=True);m=json.loads((b/'build.json').read_text());f=m['payloads']['fine'];start=32+f['offset']+f['symbols']['FF1RenderInstallClear'];p=o/'FerrariFormulaOne.slave';v=bytearray(p.read_bytes());at=v.index(bytes.fromhex('0c7933c0'),start,start+64)+3;v[at]^=1;p.write_bytes(v)
s=(r/'tools/test_h9_fault.py').read_text().replace('h9','h10').replace('H9','H10').replace("profile.startswith('a1200')","not profile.startswith('a500')").replace('else 0x600000','else 0xa00000').replace('road_fill','clear').replace('addresses.map(0x6abc6)','addresses.map(0x6b0e4)').replace("bytes.fromhex('4eb9')+struct.pack('>I',addresses.map(0x2a130))","bytes.fromhex('33c000dff058')");(r/'tools/test_h10_fault.py').write_text(s)
