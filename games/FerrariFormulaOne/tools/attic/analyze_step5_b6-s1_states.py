from pathlib import Path
import json,os
r=Path(__file__).resolve().parents[1];ver='s1';blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[dict(name='gear',address='0x6bf84',bytes=4),dict(name='instrument_phase',address='0x6c942',bytes=6),dict(name='instrument_rates',address='0x66c88',bytes=4),dict(name='flag_counter',address='0x66be0',bytes=2)]
report={'profiles':{},'scope':'B5 versus B6 VERIFY and lean: 101 native semantic checkpoints, unchanged exact-state inventory; complete player fractional state. Native opponents and compact player state remain exact.'}
for profile in ('a1200-fast','a1200'):
 a=r/f'tmp/step5/{profile}-b5-v5-matrix-verify-fine'
 for variant in ('verify','lean'):
  b=r/f'tmp/step5/{profile}-b6-{ver}-matrix-{variant}-fine'
  if not (b/'result.json').exists() or json.loads((b/'result.json').read_text())['status']!='complete':continue
  bad=[]
  for i in range(125,226):
   x=(a/f'loop{i}.bin').read_bytes();y=(b/f'loop{i}.bin').read_bytes()
   for block in blocks:
    p=int(block['address'],16);n=block['bytes']
    if x[p:p+n]!=y[p:p+n]:bad.append((i,block['name']))
  fractions={}
  for n,l in [('velocity_shadow',12),('position_shadow',12),('heading_shadow',12),('speed_shadow',6),('steering_shadow',18),('wear_remainders',8),('fuel_remainders',2)]:
   fractions[n]=(a/(n+'.bin')).read_bytes()[:l]==(b/(n+'.bin')).read_bytes()[:l]
  result=dict(passed=not bad and all(fractions.values()),failures=bad,player_fractions=fractions)
  report['profiles'][profile+'-'+variant]=result;print(profile,variant,result)
report['status']='passed' if len(report['profiles'])==4 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/f'manifest/step5-b6-{ver}-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
