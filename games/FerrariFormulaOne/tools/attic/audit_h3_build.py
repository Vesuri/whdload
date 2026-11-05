from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/render-h3';m=json.loads((b/'build.json').read_text());old=json.loads((r/'tmp/build/render-h2/build.json').read_text());sy=m['payloads']['fine']['symbols'];reset=json.loads((b/'fine/reset.json').read_text());spans=[(x['offset'],x['offset']+x['size']) for x in reset]
assert all(any(a<=sy[n]<z for a,z in spans) for n in ['FF1RenderRoadField','FF1RenderRoadRegisters','FF1RenderRoadCCR'])
assert not any(a<=sy['FF1RenderRoadControl']<z for a,z in spans)
assert all(m['payloads'][k]['sha256']==old['payloads'][k]['sha256'] for k in ['000','020'])
a=(b/'FerrariFormulaOne.slave').read_bytes();c=(r/'tmp/build/render-h3-control/FerrariFormulaOne.slave').read_bytes();diff=[i for i,(x,y) in enumerate(zip(a,c)) if x!=y];assert len(a)==len(c) and len(diff)==1
assert a==(r/'tmp/build/render-h3-rebuild/FerrariFormulaOne.slave').read_bytes()
out=dict(status='passed',bytes=len(a),candidate_sha256=hashlib.sha256(a).hexdigest(),control_sha256=hashlib.sha256(c).hexdigest(),equal_layout_diff=diff,unchanged_payloads=['000','020'],lifetime_workspace_reset=True,immutable_preset_excluded=True,independent_rebuild_exact=True,native_audit='tmp/h3-native.txt',ownership='CPU-only road preparation before safe beam wait; native clear/sky order preserved. Flag/clock pointer alias scopes both native passes to the back buffer, restored before completion wait. No new native patch, interrupt ownership or DMA allocation.')
(r/'manifest/render-h3-build-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
