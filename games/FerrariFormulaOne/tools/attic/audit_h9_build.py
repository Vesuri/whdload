from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/render-h9';c=r/'tmp/build/render-h9-control';old=r/'tmp/build/render-h7';sha=lambda v:hashlib.sha256(v).hexdigest()
x=(b/'FerrariFormulaOne.slave').read_bytes();y=(c/'FerrariFormulaOne.slave').read_bytes();m=json.loads((b/'build.json').read_text());o=json.loads((old/'build.json').read_text());base=(old/'FerrariFormulaOne.slave').read_bytes();f=m['payloads']['fine'];sy=f['symbols'];diff=[i for i,(a,z) in enumerate(zip(x,y)) if a!=z]
assert len(x)==len(y) and diff==[32+f['offset']+sy['FF1RenderFillControl']+1]
unchanged=[]
for k in ['000','020']:
 p=m['payloads'][k];q=o['payloads'][k];v=x[32+p['offset']:32+p['offset']+p['bytes']];assert v==base[32+q['offset']:32+q['offset']+q['bytes']];unchanged.append(dict(kind=k,sha256=sha(v)))
reset=json.loads((b/'fine/reset.json').read_text());assert not any(z['offset']<=sy['FF1RenderFillControl']<z['offset']+z['size'] for z in reset)
rc=sha((r/'dist/FerrariFormulaOne_v1.02-rc2_0481_Performance.lha').read_bytes());assert rc=='cdd0357047f302f1faec3584eafba5af2bfa56720452ab1f7eb1ad806a87c68b'
report=dict(status='passed',candidate_sha256=sha(x),candidate_bytes=len(x),control_sha256=sha(y),only_difference=diff,unchanged_payloads=unchanged,immutable_control_excluded_from_reset=True,new_workspace_bytes=0,rc2_sha256=rc)
(r/'manifest/render-h9-build-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
