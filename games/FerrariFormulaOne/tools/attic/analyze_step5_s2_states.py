from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1]
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear_display_transition','address':'0x6bf84','bytes':4}]
report={'scope':'S2 VERIFY vs lean, common step-1 startup RNG/saved-random/countdown control. Exact semantic blocks at matched native loops; no mask relaxation. 100 all-car adapted updates, drawing omitted.','profiles':{}}
for p in ('a1200','a1200-fast'):
 dirs=[r/'tmp/step5'/(p+'-verify-split-v4-'+v+'-fine') for v in ('verify','lean')]
 results=[json.loads((d/'result.json').read_text()) for d in dirs]
 assert all(x['status']=='complete' for x in results)
 for v,x in zip(('verify','lean'),results):assert x['slave_sha256']==hashlib.sha256((r/'tmp/build/step5-verify-split-module'/v/'fine.slave').read_bytes()).hexdigest()
 differences={}
 for t in (125,150,175,225):
  a,b=[(d/f'loop{t}.bin').read_bytes() for d in dirs]
  differences[t]=[x['name'] for x in blocks if a[int(x['address'],16):int(x['address'],16)+x['bytes']]!=b[int(x['address'],16):int(x['address'],16)+x['bytes']]]
 contexts=('velocity_shadow','speed_shadow','position_shadow','heading_shadow','steering_shadow','wear_remainders','fuel_remainders')
 context_diffs=[n for n in contexts if (dirs[0]/(n+'.bin')).read_bytes()!=(dirs[1]/(n+'.bin')).read_bytes()]
 c=(dirs[1]/'schedule_context.bin').read_bytes();fields,hi,lo,chi,clo,interval,ticks=struct.unpack_from('>7I',c);phase,step=struct.unpack_from('>HH',c,28)
 coherent=((hi<<32)|lo)==fields*710510 and ((chi<<32)|clo)==100*709379 and interval==709379 and ticks==100 and phase==0 and step==20 and c[32:]==bytes(24)
 nonzero_stats={n:v for n,v in results[1]['probe'].items() if n not in ('schedule_completed','ticks','error') and not n.endswith('_installed') and n!='installed' and v!=0}
 passed=not any(differences.values()) and not context_diffs and coherent and not nonzero_stats and results[1]['probe']['error']==0 and results[1]['probe']['schedule_completed']==100
 report['profiles'][p]={'passed':passed,'matched_loops':differences,'context_mismatches':context_diffs,'lean_timer_coherent':coherent,'completed_updates':ticks,'simulated_seconds':((chi<<32)|clo)/35468950,'nonzero_lean_stats':nonzero_stats,'verify_sha256':results[0]['slave_sha256'],'lean_sha256':results[1]['slave_sha256']}
 print(p,report['profiles'][p])
report['status']='passed' if all(x['passed'] for x in report['profiles'].values()) else 'failed'
(r/'manifest/step5-s2-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['status']=='passed'
