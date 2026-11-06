"""Independent 80-digit exponential oracle and register/status preservation."""
import copy,json,sys
from pathlib import Path
from decimal import Decimal,localcontext
from math_oracle import extended

def check(rows):
 maximum=Decimal(0);fail=[];fpsp=[]
 for i,r in enumerate(rows):
  a=bytes.fromhex(r['native']);b=bytes.fromhex(r['fpsp'])
  with localcontext() as c:
   c.prec=80;x=extended(r['value']);want=x.exp();got=extended(r['native'][:24]);ref=extended(r['fpsp'][:24]);error=abs(got-want)/want;old_error=abs(ref-want)/want
  maximum=max(maximum,error)
  clean=lambda v:v[:2]+v[4:12]
  preserved=all(clean(a[j*12:(j+1)*12])==clean(b[j*12:(j+1)*12]) for j in range(1,8))
  if error>Decimal('2e-15') or not preserved or a[96:]!=b[96:]:fail.append(dict(case=i,input=str(x),error=str(error)))
  if old_error>Decimal('2e-15'):fpsp.append(dict(case=i,input=str(x),error=str(old_error)))
 return dict(cases=len(rows),maximum_relative_error=str(maximum),failures=fail,fpsp_outliers=fpsp,fpsr_equal=sum(r['fpsr_equal'] for r in rows))
p=Path(sys.argv[1]);rows=json.loads((p/'results.json').read_text());report=check(rows);assert not report['failures'],report
controls=[]
for offset in [0,12,96,100]:
 bad=copy.deepcopy(rows[:1]);data=bytearray.fromhex(bad[0]['native']);data[offset]^=1;bad[0]['native']=data.hex();controls.append(bool(check(bad)['failures']))
assert all(controls);report['negative_controls']=controls
(p/'oracle.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
