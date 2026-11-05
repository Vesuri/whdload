"""Compare observed collector dependencies across same-world completed frames."""
from pathlib import Path
import json,collections
root=Path(__file__).resolve().parents[1]
reads=json.loads((root/'tmp/c/homing-forecast-player-reads-candidates-only.json').read_text())['reports']
needed=collections.defaultdict(set)
for row in reads:
 for part in row['shared_read_ranges']:
  if part['source']=='external':continue
  start=int(part['offset'],16);needed[part['source']].update(range(start,start+part['length']))
reports=[]
for name in ('hellfire-frames-pal-020','hellfire-frames-pal-060'):
 folder=root/'tmp/c'/name;frames=json.loads((folder/'frames.json').read_text());pairs=[]
 for before,after in zip(frames,frames[1:]):
  if before['world']!=after['world']:continue
  changes=[]
  for hunk,offsets in needed.items():
   a=(folder/f"frame-{before['frame']:03d}"/(hunk+'.bin')).read_bytes();b=(folder/f"frame-{after['frame']:03d}"/(hunk+'.bin')).read_bytes()
   changes.extend(dict(hunk=hunk,offset=hex(off),before=a[off],after=b[off]) for off in sorted(offsets) if a[off]!=b[off])
  pairs.append(dict(world=before['world'],before=before['frame'],after=after['frame'],changes=changes))
 reports.append(dict(run=name,pairs=pairs,checked_hunk_bytes=sum(map(len,needed.values())),external_pointed_records='not captured per frame; not certified'))
report=dict(reports=reports);(root/'tmp/c/forecast-frame-dependency-audit.json').write_text(json.dumps(report,indent=2)+'\n')
for r in reports:print(dict(run=r['run'],pairs=len(r['pairs']),changed_pairs=sum(bool(p['changes']) for p in r['pairs']),changed_bytes=sorted(set((x['hunk'],x['offset']) for p in r['pairs'] for x in p['changes']))))
