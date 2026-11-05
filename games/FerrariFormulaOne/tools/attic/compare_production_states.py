from pathlib import Path
import json,sys
r=Path(__file__).resolve().parents[1];profile=sys.argv[1]
a=r/f'tmp/step5/c4-q03-production-state-accepted-{profile}-candidate';b=r/f'tmp/step5/c4-q03-production-state-production-{profile}-candidate'
blocks=json.loads((a/'blocks.json').read_text());assert blocks==json.loads((b/'blocks.json').read_text());x=(a/'records.bin').read_bytes();y=(b/'records.bin').read_bytes();width=sum(v['bytes'] for v in blocks);assert len(x)==len(y)==100*width
bad=[]
for tick in range(100):
 off=tick*width
 for block in blocks:
  n=block['bytes']
  if x[off:off+n]!=y[off:off+n]:bad.append({'step':tick+1,'block':block['name'],'differences':[hex(int(block['address'],16)+i) for i in range(n) if x[off+i]!=y[off+i]][:16]})
  off+=n
private=json.loads((a/'private.json').read_text())==json.loads((b/'private.json').read_text())
report={'status':'passed' if not bad and private else 'failed','profile':profile,'steps':100,'blocks':len(blocks),'exact_private_fractions':private,'failures':bad,'arms':[json.loads((p/'result.json').read_text())['slave_sha256'] for p in [a,b]]}
(r/f'manifest/production-state-{profile}.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],profile,len(bad),'mismatches',bad[:2]);assert report['status']=='passed'
