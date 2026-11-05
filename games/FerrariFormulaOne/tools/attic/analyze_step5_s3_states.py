from pathlib import Path
import json,hashlib,struct
r=Path(__file__).resolve().parents[1]
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[dict(name='gear_transition',address='0x6bf84',bytes=4)]
extra=[dict(name='flag_counter',address='0x66be0',bytes=2),dict(name='instrument_phases',address='0x6c942',bytes=6),dict(name='instrument_rates',address='0x66c88',bytes=4)]
report={'scope':'Unchanged S2 semantic blocks plus explicit instrument phase/rate blocks for drawing-count independence. Actual native component rendering, not full road presentation.','profiles':{}}
for profile in ('a1200','a1200-fast'):
 pairs=[('verify',0),('verify',1),('verify',3),('lean',0)]
 paths=[r/'tmp/step5'/f'{profile}-s3-v3-{v}-p{p}-fine' for v,p in pairs]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 assert all(x['status']=='complete' for x in results)
 for (v,p),x in zip(pairs,results):assert x['slave_sha256']==hashlib.sha256((r/f'tmp/build/step5-s3/{v}-p{p}/fine.slave').read_bytes()).hexdigest()
 differences={};s2diffs={}
 for tick in (125,150,175,225):
  data=[(p/f'loop{tick}.bin').read_bytes() for p in paths]
  def diffs(a,b,inventory):return [x['name'] for x in inventory if a[int(x['address'],16):int(x['address'],16)+x['bytes']]!=b[int(x['address'],16):int(x['address'],16)+x['bytes']]]
  differences[tick]={str(pairs[i]):diffs(data[0],data[i],blocks+extra) for i in range(1,4)}
  s2=(r/'tmp/step5'/f'{profile}-verify-split-v4-verify-fine'/f'loop{tick}.bin').read_bytes()
  s2diffs[tick]=diffs(s2,data[0],blocks)
 contexts=('velocity_shadow','speed_shadow','position_shadow','heading_shadow','steering_shadow','wear_remainders','fuel_remainders')
 cd={str(pairs[i]):[n for n in contexts if (paths[0]/(n+'.bin')).read_bytes()!=(paths[i]/(n+'.bin')).read_bytes()] for i in range(1,4)}
 timers={}
 for pair,path in zip(pairs,paths):
  c=(path/'schedule_context.bin').read_bytes()
  fields,hi,lo,chi,clo,interval,ticks=struct.unpack_from('>7I',c)
  phase,step=struct.unpack_from('>HH',c,28)
  timers[str(pair)]=((hi<<32)|lo)==fields*710510 and ((chi<<32)|clo)==100*709379 and interval==709379 and ticks==100 and phase==0 and step==20 and c[32:]==bytes(24)
 lean_stats={n:v for n,v in results[3]['probe'].items() if n not in ('schedule_completed','ticks','error') and not n.endswith('_installed') and n!='installed' and v!=0}
 passed=all(timers.values()) and not lean_stats and not any(s2diffs.values()) and not any(d for t in differences.values() for d in t.values()) and not any(cd.values())
 report['profiles'][profile]=dict(passed=passed,presentation_differences=differences,s2_differences=s2diffs,context_differences=cd,elapsed_contexts_coherent=timers,nonzero_lean_stats=lean_stats)
 print(profile,report['profiles'][profile])
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-s3-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
