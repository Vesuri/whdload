from pathlib import Path
import json,shutil,struct
r=Path(__file__).resolve().parents[1]
b=r/'tmp/build/render-h2';o=r/'tmp/build/render-h2-control';shutil.copytree(b,o,dirs_exist_ok=True)
m=json.loads((b/'build.json').read_text());at=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['FF1RenderColourControl'];p=o/'FerrariFormulaOne.slave';data=bytearray(p.read_bytes());assert data[at:at+2]==b'\0\1';data[at:at+2]=b'\0\0';p.write_bytes(data)
for src,dst in [('capture_render_profile.py','capture_h2_profile.py'),('test_drive_timing.py','test_h2_timing.py')]:
 s=(r/'tools'/src).read_text().replace("b=r/'tmp/build/drive-fix/FerrariFormulaOne.slave'","b=Path(os.environ['H2_BUILD'])/'FerrariFormulaOne.slave'")
 s=s.replace("report['scope']='Unmodified RC2;", "report['scope']='H2 equal-layout rendering comparison;")
 (r/'tools'/dst).write_text(s)
