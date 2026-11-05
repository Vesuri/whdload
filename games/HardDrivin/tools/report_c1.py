import json,hashlib
from pathlib import Path
out={}
for name,lo,hi in [('c1-final-a',1,500),('c1-final-b',4000,4499)]:
 root=Path('tmp/prof')/name;rows=json.loads((root/'motion.json').read_text())['rows'];frames=[];before=None
 for row in rows:
  if row['kind']=='INPUT':before=row
  if row['kind']=='INTEGRATED' and before is not None:
   if lo<=before['field'] and row['field']<=hi and before['interval']:
    frames.append(dict(field=before['field'],crash=before['crash'],fallback=row['phase_frames']==before['phase_frames'],gear=before['gear'],velocity=before['velocity']))
   before=None
 driving=[x for x in frames if not x['crash']];fallback=sum(x['fallback'] for x in driving)
 out[name]=dict(window=[lo,hi],complete_frames=len(frames),crash_frames=sum(bool(x['crash']) for x in frames),driving_frames=len(driving),driving_fallbacks=fallback,driving_fallback_percent=100*fallback/len(driving),all_fallbacks=sum(x['fallback'] for x in frames),fallbacks=[x for x in frames if x['fallback']],slave_sha256=hashlib.sha256((root/'slave.slave').read_bytes()).hexdigest())
 assert out[name]['driving_fallback_percent']<2
for name in ['c1-air-full-a500','c1-air-020','c1-air-slow','c1-manual-020','c1-final-manual-a500']:
 root=Path('tmp/prof')/name;rows=json.loads((root/'motion.json').read_text())['rows'];incoming=[x for x in rows if x['kind']=='INPUT' and x['interval']]
 out[name]=dict(driving_frames=len(incoming),no_contact_frames=sum(x['mask']==0 for x in incoming),partial_contact_frames=sum(x['mask'] not in (0,15) for x in incoming),falling_frames=sum(bool(x['fall_velocity']!=0 or x['fall_carry']) for x in incoming),gear_requests=sum(bool(x.get('gear_request',0) or x.get('joystick_gear',0)) for x in incoming),gears=sorted(set(x['gear'] for x in incoming)))
 sources=['HardDrivinPhase.s','HardDrivinDrivetrain.s','HardDrivinHD.s']
report=dict(coverage=out,sources={s:hashlib.sha256((Path('src')/s).read_bytes()).hexdigest() for s in sources})
Path('tmp/c1-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(out,indent=2))
