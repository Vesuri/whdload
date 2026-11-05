import argparse,json,sys,struct
from pathlib import Path
FIELD_SECONDS=142102/7093790
p=argparse.ArgumentParser();p.add_argument('names',nargs='+');p.add_argument('--start',type=int,default=280);p.add_argument('--end',type=int,default=420);args=p.parse_args();START,END=args.start,args.end;assert START<END
filename='constant-throttle.json' if (START,END)==(280,420) else f'constant-throttle-{START}-{END}.json'
for name in args.names:
 out=Path('tmp/prof')/name;d=json.loads((out/'motion.json').read_text());rows=d['rows'];vbl={r['field']:r for r in rows if r['kind']=='VBL'};steps=[r for r in rows if r['kind']=='STEP'];window=[r for r in steps if START<=r['field']<=END]
 # The menu tape can select manual neutral on a different timing/layout.
 # Never report a stationary or wrong-mode run as automatic straight driving.
 data=(out/'game-data.bin').read_bytes()
 initial_gear=struct.unpack_from('>h',data,0x9936-0x8002)[0]
 automatic=data[0x993e-0x8002]
 if initial_gear!=1 or automatic!=1 or not window or not all(r['velocity']>0 for r in window):
  failure=dict(passed=False,profile=d['profile'],reason='Automatic first-gear start and moving measurement window required',initial_gear=initial_gear,automatic=automatic)
  (out/filename).write_text(json.dumps(failure,indent=2)+'\n')
  raise AssertionError(failure)
 # Contact globals are scratch during physics; validate completed steps only.
 assert window and all(r['y8']==0 and r['z8']==200224 and r['heading']==360 and r['fall_velocity']==0 and r['mask']==15 and r['road']==255 and not r['braking'] for r in window),'window is not flat straight driving'
 throttles=sorted(set(r['throttle'] for r in window))
 if len(throttles)!=1 or throttles[0]<=0:
  failure=dict(passed=False,profile=d['profile'],fields=[START,END],reason='Throttle is not constant and positive throughout the window',throttles=throttles)
  (out/filename).write_text(json.dumps(failure,indent=2)+'\n');raise AssertionError(failure)
 assert all(r['buttons']==0 for r in window),'accelerator not released'
 assert all(a['x8']<=b['x8'] for a,b in zip(steps,steps[1:]) if START<=a['field']<=END),'nonmonotonic'
 def at(field):
  a=max((r for r in steps if r['field']<=field),key=lambda r:r['field']);b=min((r for r in steps if r['field']>=field),key=lambda r:r['field'])
  estimate=a['x8'] if a['field']==b['field'] else a['x8']+(b['x8']-a['x8'])*(field-a['field'])/(b['field']-a['field'])
  return dict(estimate=estimate,lower=a['x8'],upper=b['x8'],fields=[a['field'],b['field']])
 a,b=at(START),at(END);seconds=(END-START)*FIELD_SECONDS
 r=dict(passed=True,profile=d['profile'],custom1=d['custom1'],delay=d['delay'],fields=[START,END],seconds=seconds,throttle=throttles[0],velocity_range=[min(x['velocity'] for x in window),max(x['velocity'] for x in window)],published_distance_world=(vbl[END]['x8']-vbl[START]['x8'])/8,interpolated_distance_world=(b['estimate']-a['estimate'])/8,distance_bounds=[(b['lower']-a['upper'])/8,(b['upper']-a['lower'])/8],endpoint_brackets=[a,b],flat_straight=True)
 r['world_units_per_second']=r['interpolated_distance_world']/seconds
 (out/filename).write_text(json.dumps(r,indent=2)+'\n');print(name,json.dumps(r))
