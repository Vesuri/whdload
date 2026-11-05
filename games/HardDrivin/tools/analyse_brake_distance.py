import json,re

def analyse(out,reply,a):
 cols=['field','x8','y8','z8','velocity','fall_velocity','heading','throttle','buttons','braking','mask','road','latched','interval','consumed']
 rows=[dict(kind=k,**dict(zip(cols,map(int,v.split())))) for k,v in re.findall(r'^(BEFORE|AFTER) ([-0-9 ]+)$',reply,re.M)]
 before=[r for r in rows if r['kind']=='BEFORE'];after=[r for r in rows if r['kind']=='AFTER'];assert before and after
 braking=[r for r in before if r['braking']];assert braking,'brake input never consumed'
 start=braking[0];stops=[r for r in after if r['latched'] and r['velocity']==0];assert len(stops)>=2,'did not stop twice within window';stop=stops[0]
 assert all(r['y8']==0 and r['z8']==start['z8'] and r['heading']==360 and r['mask']==15 and r['road']==255 and r['fall_velocity']==0 for r in rows if start['field']<=r['field']<=stop['field']),'not a flat straight stop'
 result=dict(profile=a.profile,custom1=a.custom1,delay=a.delay,actual_brake_speed=start['velocity'],brake_field=start['field'],stop_field=stop['field'],distance_world=(stop['x8']-start['x8'])/8,elapsed_fields=stop['field']-start['field'],stopped=True,flat_straight=True,rows=rows)
 # Common descending speed100 is below the throttle rundown. Require zero
 # throttle throughout the comparison so residual engine force cannot confound it.
 moving=[r for r in after if r['field']>=start['field']]
 target=100
 brackets=[(u,v) for u,v in zip(moving,moving[1:]) if u['velocity']>=target and v['velocity']<target]
 assert brackets,'common descending speed not crossed'
 u,v=brackets[0];assert u['x8']<=v['x8']<=stop['x8']
 assert all(r['throttle']==0 for r in rows if u['field']<=r['field']<=stop['field']),'engine force not excluded'
 fraction=(u['velocity']-target)/(u['velocity']-v['velocity'])
 x_est=u['x8']+fraction*(v['x8']-u['x8'])
 result['from_speed_100']=dict(distance_world_estimate=(stop['x8']-x_est)/8,distance_world_bounds=[(stop['x8']-v['x8'])/8,(stop['x8']-u['x8'])/8],bracket_fields=[u['field'],v['field']],bracket_speeds=[u['velocity'],v['velocity']],zero_throttle=True)
 (out/'braking.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='rows'})
