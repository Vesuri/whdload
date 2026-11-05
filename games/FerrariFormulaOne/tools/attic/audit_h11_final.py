from pathlib import Path
import json,hashlib,collections,sys
from PIL import Image
r=Path(__file__).resolve().parents[1];read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof={};out={'status':'pending','scope':'Reduced H13-style representative acceptance; no Cartesian matrix or new release qualification.'}
def result(name,build):
 p=r/'tmp/step5'/name/'result.json';x=read(p);assert x['slave_sha256']==sha(r/'tmp/build'/build/'FerrariFormulaOne.slave'),name
 proof[name]={'result':str(p.relative_to(r)),'sha256':sha(p)};return x
b=read(r/'manifest/render-h11-build-audit.json');assert b['status']=='passed';assert sha(r/'tmp/build/render-h11-v2/FerrariFormulaOne.slave')==b['slave_sha256'];out['build']=b
out['source']=read(r/'manifest/render-h11-source-audit.json');assert out['source']['status']=='passed'
x=result('c4-q03-h11-oracle-040-40-bce-h11-v2-candidate','render-h11-v2-oracle');assert x['status']=='passed' and x['checked']==47 and x['oracle_error']==0;out['native_oracle_cases']=47
pairs=[]
for a in ['control','candidate']:
 n=f'c4-q03-drive-state-production-040-40-bce-h11-v2-state-{a}';x=result(n,'render-h11-v2-matched'+('-control' if a=='control' else ''));assert x['steps']==100 and x['context_after'][6]==100 and x['error']==0;pairs.append(r/'tmp/step5'/n)
assert (pairs[0]/'records.bin').read_bytes()==(pairs[1]/'records.bin').read_bytes();assert read(pairs[0]/'private.json')==read(pairs[1]/'private.json');out['exact_updates']=100
for scene in ['normal','solo','grid','dense']:
 pair=[]
 for a in ['control','candidate']:
  n=f'c4-q03-h5-frame-production-040-40-bce-h11-v2-{scene}-{a}';bn='render-h11-v2-'+('matched' if scene=='normal' else scene)+'-stable-frames'+('-control' if a=='control' else '');x=result(n,bn);assert x['error']==0 and len(x['frames'])==30
  for f in x['frames']:
   im=Image.open(r/'tmp/step5'/n/f"frame-{f['update']}.png").convert('RGB');assert hashlib.sha256(im.tobytes()).hexdigest()==f['pixel_sha256']
  pair.append(x['frames'])
 assert pair[0]==pair[1],scene
out['rgb_frames_each_scene']=30
x=result('c4-q03-drive-timing-040-40-bce-h11-v2-elapsed','render-h11-v2');assert x['status']=='passed' and x['simulated_seconds']==60 and x['error_percent']<=.25;out['elapsed_error_percent']=x['error_percent']
fps={}
for p,s in [('a1200-fast','normal'),('040-40-bce','grid'),('040-40-bce','dense'),('060-50-bce','grid'),('030-50-bce','grid')]:
 for a in (['candidate'] if p.startswith(('060','030')) else ['control','candidate']):
  bn='render-h11-v2'+('' if s=='normal' else '-'+s)+('-control' if a=='control' else '');x=result(f'c4-q03-h5-fps-{p}-h11-v2-{s}-{a}',bn);assert x['status']=='passed' and len(x['interval_fields'])==300 and x['error']==0 and x.get('heavy_incomplete',0)==0
  fps[p+'/'+s+'/'+a]={k:x[k] for k in ['fps','mean_ms','p95_ms','slave_sha256']}|{'histogram':dict(sorted(collections.Counter(x['interval_fields']).items()))}
 if not p.startswith(('060','030')):
  a,b=[fps[p+'/'+s+'/'+z] for z in ['control','candidate']];assert b['mean_ms']<=a['mean_ms'] and b['p95_ms']<=a['p95_ms']
out['fps']=fps
traces={}
for a in ['control','candidate']:
 p=r/f'tmp/step5/hi25-profile-040-40-bce-h11-v2-grid-{a}';x=result(p.name,'render-h11-v2-grid'+('-control' if a=='control' else ''));assert x['status']=='passed' and '--uae_blitter_cycle_exact=true' in x['extra_args'];s=read(p/'h7-safety.json');assert s['status']=='passed' and int(s['maximum_dma_address'],16)<0x200000
 traces[a]={'analysis':read(p/'hi25-analysis.json'),'safety':s,'trace_hash':read(p/'h11-trace-hash.json')}
assert traces['candidate']['analysis']['mean_after_wait_ms']<traces['control']['analysis']['mean_after_wait_ms'];out['traces']=traces;out['cpu_bus']=read(r/'tmp/step5/hi25-profile-040-40-bce-h11-v2-grid-candidate/h11-cpu-audit.json');assert out['cpu_bus']['status']=='passed'
out['prepare_overlap']=read(r/'tmp/step5/hi25-profile-040-40-bce-h11-v2-grid-candidate/h11-prepare-overlap.json');assert out['prepare_overlap']['status']=='passed'
x=result('c4-q03-h7-live-040-40-h11-v2-candidate','render-h11-v2');assert x['status']=='passed' and x['fresh_epoch_after_actual_session_change'] and x['ledger_entries']==x['ledger_restored_words'];out['lifecycle']=dict(ledger_restored_words=x['ledger_restored_words'],native_pause_tow_pit_menu_reentry='passed',ready_zero_at_native_boundaries=True)
for c in ['fault-set','fault-clear']:
 x=result('c4-q03-h11-ownership-040-40-'+c,'render-h11-v2-'+c);assert x['status']=='passed' and x['clock_ready_at_fault']==1 and x['active']==x['saved']==0;assert x['intena']&64==(64 if c=='fault-set' else 0)
out['fault_injection']='Both entry INTENA states restored after fault with a prepared clock; no DMA references private data.'
for c in [0,1]:
 p=r/f'manifest/render-h11-v2-default-c{c}-validation.json';x=read(p);assert x['status']=='passed' and x['profiles']['a1200-fast']['passed'];proof['legacy/'+str(c)]={'path':str(p.relative_to(r)),'sha256':sha(p)}
out['legacy']='020Fast bothCUSTOM1 passed; coarse payloads byte-identical'
for name,expected in [('FerrariFormulaOne_v1.02-rc2_0481_Performance.lha','cdd0357047f302f1faec3584eafba5af2bfa56720452ab1f7eb1ad806a87c68b'),('FerrariFormulaOne_v1.02-h13_0481_Performance.lha','9a09fbb8715fe5fe382de07c328cfaf284e5c4e996677c1a3edbcdcf98ad8780')]:assert sha(r/'dist'/name)==expected
out['archives_unchanged']=True;out['evidence']=proof;out['tool_sha256']={p.name:sha(p) for p in (r/'tools').glob('*h11*.py')};out['sources']={str(p.relative_to(r.parents[1])):sha(p) for p in [r.parents[1]/'Games/FerrariFormulaOne/Fine.s',r.parents[1]/'Games/FerrariFormulaOne/RenderOverlap.s',r.parents[1]/'Games/FerrariFormulaOne_FullPresentation.s']};out['status']='passed';out['next']='H6c common-scene confirmation before deciding on optional H14-H16; H12 dropped.'
checks=read(r/'manifest/render-h11-v2-checks.json');assert checks['fps']==checks['exact']=='passed';checks['status']='passed';(r/'manifest/render-h11-v2-checks.json').write_text(json.dumps(checks,indent=2)+'\n');(r/'manifest/render-h11-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('H11 accepted',out['build']['slave_sha256'])
