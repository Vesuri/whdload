import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp'
table=json.loads((root/'native-gear-parameters/bike-table.json').read_text())
w=table['words'];top=w[0];rates=w[1:7];up=w[7:13];down=w[13:19]
results={}
for name in ['b-default-distance-dynamics','c-aux-distance-dynamics']:
 rows=json.loads((root/name/'result.json').read_text())['rows'];checked=[]
 for a,b in zip(rows,rows[1:]):
  if b['cursor']>500:break
  flags=b['flags']>>8
  assert flags&0xbd==0,hex(flags)
  speed=a['speed'];gear=a['gear'];accel=0
  if flags&2:
   if speed>=up[gear]:
    assert gear<top
    gear+=1
   if speed<down[gear]:gear-=1
   accel=rates[gear]
  else:accel=-5
  predicted=max(0,speed+accel*b['delta'])
  assert (gear,accel,predicted)==(b['gear'],b['acceleration'],b['speed']),(name,a,b,gear,accel,predicted)
  assert b['displacement']==b['speed']*b['delta']
  assert b['position']-a['position']==b['displacement']
  checked.append(b['cursor'])
 results[name]=dict(steps=len(checked),first=checked[0],last=checked[-1],all_gear_acceleration_speed_displacement_exact=True)
flat={}
for q in [1,3,4]:
 speed=gear=position=ticks=0;shifts=[]
 while ticks<400:
  delta=min(q,400-ticks);old=gear
  if speed>=up[gear] and gear<top:gear+=1
  if speed<down[gear]:gear-=1
  speed+=rates[gear]*delta;position+=speed*delta;ticks+=delta
  if gear!=old:shifts.append(dict(field=ticks,speed=speed,gear=gear))
 flat[q]=dict(speed=speed,distance=position,shifts=shifts)
out=dict(table=table,results=results,flat_road_constant_throttle_400_fields=flat)
(root/'native-gear-parameters/arithmetic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
