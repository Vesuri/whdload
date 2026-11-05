"""Read-only braking comparison against the one-field native-force recurrence."""
import json,re,sys
from fractions import Fraction
from pathlib import Path
from audit_forward_force import force
from dissipation_model import update

def projection(v,c):
 a=v+v//2;b=(v+(1 if c>=0 else -1))*3//2
 return a*65536+(b-a)*abs(c)*8192

def tick(v,c,p,x):
 f=force(v,0,True,False,False,True,0)
 r=update(v,f['rate'],1,c,v,f['drive'],f['drag'],f['brake'],0)
 v,c=r['value'],r['carry'];q=projection(v,c)
 return v,c,q,x+(9*q-7*p)//16

def phase_distance(eighths):
 v=(eighths+7)//8;c=eighths-v*8;p=projection(v,c);x=0;n=0;cross=None
 while v or c:
  oldv=v*8+c;oldx=x;v,c,p,x=tick(v,c,p,x);n+=1
  if cross is None and oldv>=800 and v*8+c<800:cross=Fraction(oldx)+Fraction((x-oldx)*(oldv-800),oldv-(v*8+c))
  assert n<1000
 assert cross is not None
 return Fraction(x-cross,65536*8)

phases={str(n):str(phase_distance(n)) for n in range(800,806)}
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;text=(out/'events.log').read_text();points=[];context=None;mode=None;other={}
 for tag,values in re.findall(r'^(BEFORE|AFTER|MODE POUT|POUT|YPOUT|ZPOUT) ([-0-9 ]+)$',text,re.M):
  r=list(map(int,values.split()))
  if tag=='BEFORE':context=r
  elif tag=='MODE POUT':
   assert points and 'mode' not in points[-1];points[-1]['mode']=r
  elif tag in ('YPOUT','ZPOUT'):other[tag]=r
  elif tag=='POUT':
   assert context is not None
   points.append(dict(raw=r,context=context,other=dict(other),v8=r[10]*8+r[9],x=r[1]*65536+r[4]*512+r[7],p=r[2]*65536+r[5]))
 brackets=[i for i,(a,b) in enumerate(zip(points,points[1:])) if a['v8']>=800>b['v8'] and a['context'][7]==b['context'][7]==0 and a['context'][9] and b['context'][9]]
 assert len(brackets)==1,brackets
 first=brackets[0];stop=next(i for i in range(first,len(points)) if points[i]['v8']==0)
 rows=points[first:stop+1];start=rows[0];v,c=start['raw'][10],start['raw'][9];p,x=start['p'],start['x'];steps=0;backward=[]
 for a,b in zip(rows,rows[1:]):
  r=b['raw'];ctx=b['context'];assert ctx[2:4]==[0,200224] and ctx[6]==360 and ctx[7]==0 and ctx[9] and ctx[10:12]==[15,255] and ctx[5]==0
  assert b['mode'][1:]==[0,15,0]
  assert all(b['other'][k][1]==pos and b['other'][k][4:8]==[0,0,0,0] for k,pos in [('YPOUT',0),('ZPOUT',200224)])
  for _ in range(r[8]):v,c,p,x=tick(v,c,p,x);steps+=1
  assert (v,c,p,x)==(r[10],r[9],b['p'],b['x']),(name,r,(v,c,p,x),(r[10],r[9],b['p'],b['x']))
  if b['x']<a['x']:backward.append(Fraction(a['x']-b['x'],65536*8))
 a,b=rows[:2];assert b['raw'][8]==1,'crossing is not resolved to one field'
 crossing=Fraction(a['x'])+Fraction((b['x']-a['x'])*(a['v8']-800),a['v8']-b['v8'])
 distance=Fraction(rows[-1]['x']-crossing,65536*8)
 assert 800<=a['v8']<806
 assert distance==Fraction(phases[str(a['v8'])]),(name,distance,phases)
 stationary=points[stop:];assert len(stationary)>1 and all(p['raw'][9:11]==[0,0] and p['p']==0 and p['x']==rows[-1]['x'] for p in stationary)
 result=dict(passed=True,profile=json.loads((out/'metadata.json').read_text())['layout']['profile'],matched_updates=len(rows)-1,modeled_fields=steps,crossing_velocity_eighths=[a['v8'],b['v8']],distance_world_exact=str(distance),distance_world=float(distance),one_field_sample_bounds=[float(Fraction(rows[-1]['x']-b['x'],65536*8)),float(Fraction(rows[-1]['x']-a['x'],65536*8))],phase_envelope_exact=phases,backward_fractional_updates=len(backward),max_backward_world=float(max(backward,default=0)),total_backward_world=float(sum(backward)),published_integer_backward_updates=sum(b['raw'][1]<a['raw'][1] for a,b in zip(rows,rows[1:])),elapsed_fields_from_interpolated_crossing=str(Fraction(steps)-Fraction(a['v8']-800,a['v8']-b['v8'])),stopped_exact_position_held=True,scope='Flat zero-throttle braking in optional reference, matched to one-field force recurrence and fractional position. Crossing estimate is linear within one modeled field; native force quantization creates the enumerated phase envelope. No general handling or FPS claim.')
 (out/'fine-braking.json').write_text(json.dumps(result,indent=2)+'\n');print(name,{k:v for k,v in result.items() if k not in ['scope','phase_envelope_exact']},flush=True)
