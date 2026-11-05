"""Exhaust all signed word rates at the short-interval bounds and extreme carries."""
from pathlib import Path
exec(Path('tools/check_p4_first.py').read_text().split('try:\n',1)[0])
count=0
try:
 for rate in range(-32768,32768):
  for n in [1,8]:
   for carry in [-7,7]:
    a=run(0,'_time_scale_word',[rate,n,carry]);b=run(1,'_time_scale_word',[rate,n,carry]);assert all(a[2][k]==b[2][k] for k in range(16) if k!=6),(rate,n,carry)
    numerator=rate*n+carry;quotient=abs(numerator)//8*(-1 if numerator<0 else 1);remainder=numerator-quotient*8
    assert (b[2][8],b[2][10])==(quotient&0xffffffff,remainder&0xffffffff),(rate,n,carry)
    count+=1
 report=dict(passed=True,actual_68000_old_new_cases=count,signed_word_rates=65536,intervals=[1,8],carries=[-7,7],independent_model='truncation toward zero with signed eighth remainder')
 Path('tmp/p4-scale-words-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
