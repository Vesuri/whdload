from pathlib import Path
import json,shutil,struct
r=Path(__file__).resolve().parents[1]
b=r/'tmp/build/render-h5';o=r/'tmp/build/render-h5-control';shutil.copytree(b,o,dirs_exist_ok=True)
m=json.loads((b/'build.json').read_text());at=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['FF1RenderBitmapControl'];p=o/'FerrariFormulaOne.slave';data=bytearray(p.read_bytes());assert data[at:at+2]==b'\0\1';data[at:at+2]=b'\0\0';p.write_bytes(data)
