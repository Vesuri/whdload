from pathlib import Path
import json,hashlib
from analyze_step3 import analyze
r=Path(__file__).resolve().parents[1];results=[]
for cpu,flag,cacr in [('030-50','nocache',0x2000),('030-50','dcache',0x2111),('040-25','dcache',0x80008000),('060-50','dcache',0x80008000),('060-50','branchcache',0x808000)]:
 p=r/f'tmp/step5/c4-q03-release-census-{cpu}-cache-{flag}';j=json.loads((p/'result.json').read_text());assert j['status']=='passed' and j['error']==0 and j['selection']==2 and j['survey_meta']['cacr']==cacr
 assert j['end_context'][0]-j['start_context'][0]==1000
 a=analyze(p);assert a['presented_fps_count']>=5.54
 results.append(dict(profile=cpu,option=flag,cacr=hex(cacr),fps=a['presented_fps_count'],interval_fields=a['interval_fields'],evidence=str(p.relative_to(r))))
mmu=[]
for cpu in ('040-25','060-50'):
 p=r/f'tmp/step5/c4-q03-release-smoke-{cpu}-mmu';j=json.loads((p/'result.json').read_text());log=(p/'capture.log').read_text();assert j['status']=='passed' and j['error']==0 and j['selection']==2 and j['context_after'][6]==20
 assert ('68040' if cpu.startswith('040') else '68060')+' MMU: TC=8000 enabled=1' in log
 mmu.append(dict(profile=cpu,updates=20,translation_enabled_verified=True,evidence=str(p.relative_to(r)),timing_claim=False))
(r/'manifest/release-cache-mmu.json').write_text(json.dumps(dict(status='passed',cache_demo=results,mmu_functional=mmu,scope='Unmodified production; cache performance observations and MMU-enabled 20-update functional checks. Exact-state/frame gates recorded separately; no hardware timing or MMU performance claim.'),indent=2)+'\n');print('cache and MMU checks passed')
