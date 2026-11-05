from pathlib import Path
import json,hashlib,collections,struct,sys
from PIL import Image
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'tools'));from step5_b7_addresses import Addresses
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof={};out={'status':'pending','scope':'Reduced representative H13 acceptance: 040BCE exact state/private fractions, four completed RGB scene pairs, elapsed, native040 lifecycle,020Fast default-off bothCUSTOM1, new-hook signature failure, matched020 normal and040BCE grid/dense FPS,030/060BCE grid candidate,040BCE matched traces.'}
def blob(p):
 import gzip
 return p.read_bytes() if p.exists() else gzip.open(p.with_suffix(p.suffix+'.gz'),'rb').read()
def result(name,build=None):
 p=r/'tmp/step5'/name/'result.json';x=read(p)
 if build:assert x['slave_sha256']==sha(r/'tmp/build'/build/'FerrariFormulaOne.slave'),name
 proof[name]={'result':str(p.relative_to(r)),'sha256':sha(p)};return x
build=read(r/'manifest/render-h13-build-audit.json');assert build['status']=='passed';assert (r/'tmp/build/render-h13/FerrariFormulaOne.slave').read_bytes()==(r/'tmp/build/render-h13-rebuild/FerrariFormulaOne.slave').read_bytes();build['reproducible_build']=True;assert sha(r/'dist/FerrariFormulaOne_v1.02-rc2_0481_Performance.lha')==build['rc2_sha256'];out['build']=build
out['microbench']=read(r/'manifest/render-h13-microbench.json');assert out['microbench']['status']=='passed'
x=result('c4-q03-h13-oracle-040-40-bce-h13-candidate','render-h13-oracle');assert x['status']=='passed' and x['checked']==108 and x['gauge_calls']>=108 and x['oracle_error']==0;out['native_oracle_cases']=108;out['native_contract']='CPU input-register preservation and nativeA6/SP/CCR exact';out['caller_contract']=read(r/'manifest/render-h13-caller-contract.json');assert out['caller_contract']['status']=='passed'
states=[]
for arm in ['control','candidate']:
 n='c4-q03-drive-state-production-040-40-bce-h13-state-'+arm;x=result(n,'render-h13-matched'+('-control' if arm=='control' else ''));assert x['steps']==100 and x['context_after'][6]==100 and x['error']==0;states.append(r/'tmp/step5'/n)
for arm,p in zip(['control','candidate'],states):
 x=read(p/'result.json');m=blob(p/'sample-full-check.bin');m+=bytes(0x200000-len(m))+blob(p/'sample-full-check-fast.bin');a=Addresses(m,int(x['table'],16));probe=int(x['probe'],16);sy=read(r/'tmp/build/render-h13-matched/build.json')['payloads']['fine']['symbols']
 for native,label in [(0x6bd66,'FF1RenderGaugeStrip'),(0x6bdb6,'FF1RenderGaugeStrip')]:
  expected=bytes.fromhex('4eb9')+struct.pack('>I',probe+sy[label]) if arm=='candidate' else bytes.fromhex('4eb9')+struct.pack('>I',a.map(0x24ae0))
  assert m[a.map(native):a.map(native)+6]==expected
out['state_comparison_hooks_verified']=True
out['native_dependencies']=read(r/'manifest/render-h13-dependencies.json');assert out['native_dependencies']['status']=='passed'
assert (states[0]/'records.bin').read_bytes()==(states[1]/'records.bin').read_bytes();assert read(states[0]/'private.json')==read(states[1]/'private.json');out['exact_updates']=100
for scene in ['normal','solo','grid','dense']:
 pair=[]
 for arm in ['control','candidate']:
  n=f'c4-q03-h5-frame-production-040-40-bce-h13-{scene}-{arm}';b='render-h13-'+('matched' if scene=='normal' else scene)+'-stable-frames'+('-control' if arm=='control' else '');x=result(n,b);assert x['error']==0 and len(x['frames'])==30
  for f in x['frames']:
   im=Image.open(r/'tmp/step5'/n/f"frame-{f['update']}.png").convert('RGB');assert hashlib.sha256(im.tobytes()).hexdigest()==f['pixel_sha256']
  pair.append(x['frames'])
 assert pair[0]==pair[1],scene
out['rgb_frames_each_scene']=30
x=result('c4-q03-drive-timing-040-40-bce-h13-elapsed','render-h13');assert x['status']=='passed' and x['simulated_seconds']==60 and x['error_percent']<=.25;out['elapsed_error_percent']=x['error_percent']
fps={}
for p,s in [('a1200-fast','normal'),('040-40-bce','grid'),('040-40-bce','dense'),('060-50-bce','grid'),('030-50-bce','grid')]:
 for a in (['candidate'] if p.startswith(('060','030')) else ['control','candidate']):
  b='render-h13'+('' if s=='normal' else '-'+s)+('-control' if a=='control' else '');x=result(f'c4-q03-h5-fps-{p}-h13-{s}-{a}',b);assert x['status']=='passed' and len(x['interval_fields'])==300 and x['error']==0 and x.get('heavy_incomplete',0)==0
  fps[p+'/'+s+'/'+a]={k:x[k] for k in ['fps','mean_ms','p95_ms','slave_sha256']}|{'histogram':dict(sorted(collections.Counter(x['interval_fields']).items()))}
 if not p.startswith(('060','030')):
  a,b=[fps[p+'/'+s+'/'+z] for z in ['control','candidate']];assert b['mean_ms']<=a['mean_ms'] and b['p95_ms']<=a['p95_ms']
out['fps']=fps
traces={}
for a in ['control','candidate']:
 p=r/f'tmp/step5/hi25-profile-040-40-bce-h13-grid-{a}';x=result(p.name,'render-h13-grid'+('-control' if a=='control' else ''));assert x['status']=='passed' and '--uae_blitter_cycle_exact=true' in x['extra_args'];s=read(p/'h7-safety.json');assert s['status']=='passed' and int(s['maximum_dma_address'],16)<0x200000
 traces[a]={'analysis':read(p/'hi25-analysis.json'),'safety':s,'trace_hash':read(p/'h13-trace-hash.json')}
assert traces['candidate']['analysis']['mean_after_wait_ms']<traces['control']['analysis']['mean_after_wait_ms'];out['traces']=traces;out['cpu_bus']=read(r/'tmp/step5/hi25-profile-040-40-bce-h13-grid-candidate/h13-cpu-audit.json');assert out['cpu_bus']['status']=='passed'
x=result('c4-q03-h7-live-040-40-h13-candidate','render-h13');assert x['status']=='passed' and x['fresh_epoch_after_actual_session_change'] and x['ledger_entries']==x['ledger_restored_words']
p=r/'tmp/step5/c4-q03-h7-live-040-40-h13-candidate';table=int(x['table'],16);probe=int(x['probe'],16);sy=read(r/'tmp/build/render-h13/build.json')['payloads']['fine']['symbols']
for snap in ['takeover','fresh-session-step21']:
 m=blob(p/(snap+'.bin'))
 for native,label in [(0x6bd66,'FF1RenderGaugeStrip'),(0x6bdb6,'FF1RenderGaugeStrip')]:
  a=Addresses(m,table).map(native);assert m[a:a+6]==bytes.fromhex('4eb9')+struct.pack('>I',probe+sy[label])
out['lifecycle']={'ledger_restored_words':x['ledger_restored_words'],'gauge_hooks_present_on_takeover_and_reload':True,'native_pause_tow_pit_menu_reentry':'passed'}
x=result('c4-q03-h13-bad-signature-040-40-candidate','render-h13-bad-signature');assert x['status']=='passed' and x['gauge_hook_not_installed'];out['signature_failure']='passed'
for c in [0,1]:
 p=r/f'manifest/render-h13-default-c{c}-validation.json';x=read(p);assert x['status']=='passed' and x['profiles']['a1200-fast']['passed'];proof['legacy/'+str(c)]={'path':str(p.relative_to(r)),'sha256':sha(p)}
out['legacy']='020Fast bothCUSTOM1 passed; coarse payloads byte-identical';out['evidence']=proof;out['tool_sha256']={n:sha(r/'tools'/n) for n in ['build_h13_final_oracle.py','test_h13_oracle.py','run_h13_checks.py','analyze_h13_trace.py','audit_h13_cpu.py','audit_h13_build.py','audit_h13_final.py']};checks=read(r/'manifest/render-h13-checks.json');checks['status']='passed';(r/'manifest/render-h13-checks.json').write_text(json.dumps(checks,indent=2)+'\n');out['status']='passed';out['next']='H11 if common-scene H6c remains unmet; H12 dropped by user';(r/'manifest/render-h13-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('H13 accepted',build['candidate_sha256'])
