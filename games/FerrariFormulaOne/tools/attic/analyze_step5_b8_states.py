from pathlib import Path
import json,struct
r=Path(__file__).resolve().parents[1]
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[dict(name='gear',address='0x6bf84',bytes=4),dict(name='instrument_phase',address='0x6c942',bytes=6),dict(name='instrument_rates',address='0x66c88',bytes=4),dict(name='flag_counter',address='0x66be0',bytes=2),dict(name='pit_flags',address='0xd0dc',bytes=8)]
a=r/'tmp/step5/a1200-fast-b8-v3-control-verify-fine';report=dict(blocks=blocks,profiles={})
for variant in ('verify','lean'):
 b=r/f'tmp/step5/a1200-fast-b8-v3-{variant}-fine';bad=[]
 for i in range(125,226):
  x=(a/f'loop{i}.bin').read_bytes();y=(b/f'loop{i}.bin').read_bytes()
  for block in blocks:
   p=int(block['address'],16);n=block['bytes']
   if x[p:p+n]!=y[p:p+n]:bad.append(dict(tick=i,block=block['name'],differences=[hex(v) for v in range(p,p+n) if x[v]!=y[v]][:12]))
 fractions={n:(a/(n+'.bin')).read_bytes()[:l]==(b/(n+'.bin')).read_bytes()[:l] for n,l in [('velocity_shadow',12),('position_shadow',12),('heading_shadow',12),('speed_shadow',6),('steering_shadow',18),('wear_remainders',8),('fuel_remainders',2)]}
 report['profiles'][variant]=dict(passed=not bad and all(fractions.values()),failures=bad,player_fractions=fractions)
report['status']='passed' if all(x['passed'] for x in report['profiles'].values()) else 'failed';(r/'manifest/step5-b8-v3-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(report);assert report['status']=='passed'
