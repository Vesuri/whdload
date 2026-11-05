from pathlib import Path
from functools import lru_cache
import re,json,sys
for arg in sys.argv[1:]:
 p=Path(arg);l=(p/'capture.slave.lst').read_text(encoding='latin1')
 @lru_cache(None)
 def sy(n):return int(re.search('^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
 initial=(p/'active-epoch-arena.bin').read_bytes();rebase_off=sy('RT_CLOCK')+sy('TC_REBASES');initial_rebases=int.from_bytes(initial[rebase_off:rebase_off+4],'big')
 epoch=json.loads((p/'input-events.json').read_text())['epoch'];rows=[]
 for world in range(20,81):
  a=(p/f'world-{world}/arena.bin').read_bytes();h2=(p/f'world-{world}/h2.bin').read_bytes()
  def read(off,n):return int.from_bytes(a[off:off+n],'big')
  for key,width in [('TC_FAULT',2),('TC_DROPPED',4)]: assert read(sy('RT_CLOCK')+sy(key),width)==0,(p,world,key)
  for block,pre in [('SCHEDULER','TS'),('HISTORY','TH'),('COMMANDS','CQ')]:
   assert read(sy('RT_'+block)+sy(pre+'_FAULT'),2)==0,(p,world,pre)
  for block,pre in [('HISTORY','TH'),('COMMANDS','CQ')]:
   for suffix in ('LOST','DISCARDED'):assert read(sy('RT_'+block)+sy(pre+'_'+suffix),4)==0,(p,world,pre,suffix)
  assert read(rebase_off,4)==initial_rebases,(p,world,'active rebase')
  native=int.from_bytes(h2[28:32],'big')-epoch
  rate=read(sy('RT_CLOCK')+sy('TC_RATE'),2);logical=read(sy('RT_CLOCK')+sy('TC_FIELDS'),4)
  assert logical==(world*rate+2)//3
  rows.append(dict(world=world,logical=logical,native=native,lag=native-logical))
 counts={n:read(sy('RT_FORECAST')+sy('RF_'+n),4) for n in ('ATTEMPTS','ACCEPTED','REJECTED')}
 assert counts['ATTEMPTS']==counts['ACCEPTED']+counts['REJECTED']
 report=dict(run=p.name,worlds=len(rows),rate=rate,native_span=rows[-1]['native']-rows[0]['native'],worlds_per_second=60*rate/(rows[-1]['native']-rows[0]['native']),lag_min=min(r['lag'] for r in rows),lag_max=max(r['lag'] for r in rows),forecast_counts=counts,no_sampled_faults_loss_or_active_rebases=True,activation_rebases=initial_rebases,rows=rows)
 (p/'guided-rate-audit.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='rows'})
