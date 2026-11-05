from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1]
report={'scope':'100 traced adapted updates driven by live PAL elapsed time, drawing omitted. Trace overhead is included; not a production capacity or full scheduler/presentation acceptance.','profiles':{}}
sha=hashlib.sha256((r/'tmp/build/step5-elapsed/fine.slave').read_bytes()).hexdigest()
for profile in ('a1200','a1200-fast'):
 p=r/'tmp/step5'/(profile+'-elapsed-fine')
 result=json.loads((p/'result.json').read_text())
 assert result['status']=='complete' and result['slave_sha256']==sha
 context=(p/'schedule_context.bin').read_bytes();records=(p/'schedule_records.bin').read_bytes()
 fields,hi,lo,chi,clo,interval,ticks=struct.unpack_from('>7I',context)
 phase,step=struct.unpack_from('>HH',context,28)
 rebases,rhi,rlo,paused,phi,plo=struct.unpack_from('>6I',context,32)
 elapsed=(hi<<32)|lo;consumed=(chi<<32)|clo
 failures=[];cost=[];pulses=[];previous=0
 for i in range(100):
  begin,end,bhi,blo,ehi,elo,serial,pulse=struct.unpack_from('>8I',records,i*32)
  before=(bhi<<32)|blo;after=(ehi<<32)|elo
  expected_before=begin*710510-i*709379
  # VBL can occur between field snapshot and the later pending snapshot.
  expected_after=end*710510-(i+1)*709379
  if begin<previous or end<begin or before<709379 or not 0<=expected_before-before<=710510 or not 0<=after-expected_after<=710510 or serial!=126+i or pulse!=int((i+1)%5==0):
   failures.append(dict(index=i,record=[begin,end,before,after,serial,pulse],expected_before=expected_before,expected_after=expected_after))
  cost.append(end-begin);pulses.append(pulse);previous=end
 coherent=elapsed==fields*710510 and consumed==100*709379 and interval==709379 and ticks==100 and phase==0 and step==20 and (rebases,rhi,rlo,paused,phi,plo)==(0,0,0,0,0,0) and result['probe']['schedule_completed']==100
 seconds=elapsed/35468950
 report['profiles'][profile]={'passed':coherent and not failures,'failures':failures,'context_coherent':coherent,'completed_updates':ticks,'native_pulses':sum(pulses),'elapsed_seconds':seconds,'simulated_seconds':consumed/35468950,'outstanding_seconds':(elapsed-consumed)/35468950,'simulation_to_elapsed_ratio':(consumed/elapsed),'mean_traced_update_ms':sum(cost)*710510/35468950*1000/100,'max_traced_update_fields':max(cost),'fields':fields,'slave_sha256':sha}
 print(profile,json.dumps(report['profiles'][profile]),flush=True)
report['status']='passed' if all(x['passed'] for x in report['profiles'].values()) else 'failed'
(r/'manifest/step5-elapsed-validation.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['status']=='passed'
