from pathlib import Path
import shutil,json,struct
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/render-h2';o=r/'tmp/build/render-h2-bad-signature';shutil.copytree(b,o,dirs_exist_ok=True);m=json.loads((b/'build.json').read_text());a=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['FF1RenderColourSignature'];p=o/'FerrariFormulaOne.slave';data=bytearray(p.read_bytes());assert data[a:a+2]==bytes.fromhex('0100');data[a+1]=1;p.write_bytes(data)
s=(r/'tools/test_production_fault.py').read_text().replace('production-fault','h2-bad-signature').replace('tmp/build/h2-bad-signature','tmp/build/render-h2-bad-signature').replace('zero-sized patch ledger exits through WHDLoad error instead of a diagnostic spin or silent loop fallback','corrupted immutable H2 signature exits through WHDLoad error before installing the colour hook')
(r/'tools/test_h2_fault.py').write_text(s)
