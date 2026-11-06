import json,sys,csv
from pathlib import Path
from decimal import Decimal,localcontext
from math_oracle import extended,oracle
p=Path(sys.argv[1]);rows=json.loads(p.read_text());fail=[];fpspfail=[];maxerr={};observed=set()
for r in csv.reader((Path(__file__).resolve().parents[1]/'tmp/step9/baseline-operands/profile.csv').open()):
 if r[0]=='math' and r[3]=='0':observed.add(''.join(f'{int(v):08x}' for v in r[4:7]))
for r in rows:
 dst=r['dest'];off=dst*24
 got=extended(r['native'][off:off+24]);ref=extended(r['fpsp'][off:off+24]);want=oracle(r['key'],extended(r['value']))
 def error(v):
  if want.is_nan():return Decimal(0) if v.is_nan() else Decimal('Infinity')
  if not v.is_finite():return Decimal('Infinity')
  return abs(v-want)/max(Decimal(1),abs(want))
 e=error(got);er=error(ref);maxerr[r['key']]=max(maxerr.get(r['key'],Decimal(0)),e)
 if e>Decimal('2e-15') or not r['preserved'] or not r['fpcr_equal']:fail.append(dict(key=r['key'],input=r['value'],error=str(e)))
 if er>Decimal('2e-15'):fpspfail.append(dict(key=r['key'],input=r['value'],error=str(er),observed=r['value'] in observed))
report=dict(cases=len(rows),max_relative_or_absolute_error={k:str(v) for k,v in maxerr.items()},failures=fail,fpsp_outliers=fpspfail)
(p.parent/'oracle.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert not fail;assert not any(x['observed'] for x in fpspfail)
