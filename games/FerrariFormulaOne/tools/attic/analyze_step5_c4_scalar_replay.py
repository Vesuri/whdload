from pathlib import Path
import json,collections
r=Path(__file__).resolve().parents[1]
p=r/'tmp/step5/c4-boundary-p5-v3-ab-a500-candidate-scalar-replay'
j=json.loads((p/'result.json').read_text());rows=json.loads((p/'scalars.json').read_text())
bad=[];counts=collections.Counter();phases=set();settings=set();pulses=set()
signed=lambda x:(x+2**31)%2**32-2**31
for n,x in enumerate(rows):
 kind=x['kind'];counts[kind]+=1;d0=signed(x['d0']);d1=x['d1']&65535
 if kind=='FF1SpeedRatePulses200':
  old=x['before'];pulses.add(d1)
  valid=0<=old<=500*65536 and -32768<=d0<=32767 and d1<=2
  if valid:
   integer=(old>>16)+d1*(d0-(old>>16))
   expected=0 if integer<0 else 500*65536 if integer>=500 else integer*65536+(old&65535)
   # A zero-pulse call preserves the complete scalar, including its bound.
   if d1==0:expected=old
  else:expected=old
  okay=x['after']==expected and x['out_d1']==(0 if valid else 0xffffffff)
 elif kind=='FF1Wear200Delta':
  old=x['before'];valid=d0>=0 and signed(old)>=0
  expected=min(2*d0,old) if valid else x['d0']
  okay=x['after']==old and x['out_d0']==expected and x['out_d1']==(0 if valid else 0xffffffff)
 else:
  phase=x['d0']&65535;phases.add(phase);settings.add(d1)
  forbidden={0} if d1==4 else {0,1} if d1==5 else set()
  expected=sum(v not in forbidden for v in [(phase-1)%4,phase]) if phase<=3 else 0xffffffff
  okay=x['out_d0']==expected and x['out_d1']==x['d1']
 if not okay:bad.append({'record':n,'input':x,'expected':expected})
passed=j['status']=='complete' and j['updates']==100 and not bad and len(counts)==3
out={'status':'passed' if passed else 'failed','scope':'Independent replay of actual scalar-rate, continuous-loss and phase-count helper calls in 100 integrated demo updates. Does not establish event eligibility, caller subtraction or unobserved boundary cases.','counts':dict(counts),'phases':sorted(phases),'settings':sorted(settings),'eligible_pulses':sorted(pulses),'failures':bad[:20],'slave_sha256':j['slave_sha256']}
(r/'manifest/step5-c4-scalar-replay-validation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2));assert passed
