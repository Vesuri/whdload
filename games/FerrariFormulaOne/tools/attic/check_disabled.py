from pathlib import Path
import json,struct
r=Path(__file__).resolve().parents[1];inventory=json.loads((r/'manifest/release-perf-ranges.json').read_text());results=[]
for option in (0,1):
 for profile in ('a500','a500-fast','a1200','a1200-fast'):
  for loop in (125,150,175):
   paths=[r/f'tmp/step5/release-default-c{option}-{profile}-{arm}/loop{loop}.bin' for arm in ('release','production')]
   if not all(p.exists() for p in paths):continue
   a,b=[p.read_bytes() for p in paths];bad=[]
   # Both arms retain the original timing-call patch. Its operand points into
   # distinct host allocations. Verify JSR and compare all other ledger bytes.
   assert a[0x6a304:0x6a306]==b[0x6a304:0x6a306]==bytes.fromhex('4eb9')
   for q in inventory['PERF_RANGE']:
    for at in range(q['start'],q['start']+q['bytes']):
     if 0x6a306<=at<0x6a30a:continue
     if a[at]!=b[at]:bad.append(hex(at))
   results.append(dict(custom1=option,profile=profile,loop=loop,passed=not bad,differences=bad))
report=dict(status='passed' if len(results)==24 and all(x['passed'] for x in results) else 'incomplete-or-failed',scope='Exact native engine-patch byte comparisons; original timing JSR host-pointer operand is verified separately; overlay reloads remain separate.',words=inventory['words'],comparisons=results)
(r/'manifest/release-disabled-ranges.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
