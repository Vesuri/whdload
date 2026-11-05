from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/render-h5';a=b/'FerrariFormulaOne.slave';other=r/'tmp/build/render-h5-rebuild/FerrariFormulaOne.slave';assert a.read_bytes()==other.read_bytes();m=json.loads((b/'build.json').read_text());sy=m['payloads']['fine']['symbols'];at=32+m['payloads']['fine']['offset']+sy['FF1RenderBitmapControl'];c=r/'tmp/build/render-h5-control/FerrariFormulaOne.slave';assert [i for i,(x,y) in enumerate(zip(a.read_bytes(),c.read_bytes())) if x!=y]==[at+1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=dict(status='passed',bytes=a.stat().st_size,slave_sha256=sha(a),candidate=str(a),independent_rebuild=str(other),independent_rebuild_sha256=sha(other),control=str(c),control_sha256=sha(c),one_byte_ab_offset=at+1,control_contract='Both arms validate entry signature; control skips hook installation entirely. Native path retains original entry, with no per-call H5 dispatch overhead.',coarse_payloads_unchanged=True)
for kind in ['000','020']:assert (b/kind/'fine.bin').read_bytes()==(r/'tmp/build/render-h4'/kind/'fine.bin').read_bytes()
(r/'manifest/render-h5-build-audit.json').write_text(json.dumps(out,indent=2)+'\n')
o=b.with_name('render-h5-bad-signature');shutil.copytree(b,o,dirs_exist_ok=True);at=32+m['payloads']['fine']['offset']+sy['FF1RenderInstallBitmap'];p=o/'FerrariFormulaOne.slave';d=bytearray(p.read_bytes());assert d[at:at+4]==bytes.fromhex('0c794a79');d[at+3]^=1;p.write_bytes(d)
print(out)
