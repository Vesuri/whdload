from pathlib import Path
import csv,json,collections
r=Path(__file__).resolve().parents[1]/'tmp/opt20';a=r/'exp-long-on';b=r/'project-observer-on'
without=lambda p:[x for x in csv.reader((p/'profile.csv').open()) if not (x[0]=='math' and x[2]==str(0x55e6c))]
names=['counts.json','after.png']+[f'{t}-hunk{i}.bin' for t in ['entry','start','end'] for i in range(3)]
checks={}
for first,second in [('exp-long-on','project-observer-on'),('project-operands','project-observer-off')]:
 x=r/first;y=r/second
 result={n:(x/n).read_bytes()==(y/n).read_bytes() for n in names}
 result['profile_without_added_operands']=without(x)==without(y)
 assert all(result.values()),(first,second,result)
 checks[first+' vs '+second]=result
signed=lambda x:x-2**32 if x>=2**31 else x
count=over=small=exact=0;den=collections.Counter();quot=collections.Counter();bounds=[2**31,-2**31]
for x in csv.reader((b/'profile.csv').open()):
 if x[0]!='math' or x[2]!=str(0x55e6c):continue
 n,m,d,fpcr=map(int,x[4:8]);d=d&65535;assert 17<=d<=32767
 count+=1;den[d]+=1
 for val in [signed(n),signed(m)]:
  q=abs(val)//d*(-1 if val<0 else 1);over+=not(-32768<=q<=32767);small+=-32768<=val<=32767;exact+=val%d==0
  quot[q]+=1;bounds=[min(bounds[0],val),max(bounds[1],val)]
report=dict(observer_checks=checks,points=count,divisions=count*2,numerator_range=bounds,denominator_range=[min(den),max(den)],distinct_denominators=len(den),overflow_divisions=over,word_sized_numerators=small,integer_quotients=exact,common_denominators=den.most_common(15))
(r/'project-operand-analysis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
