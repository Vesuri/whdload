from pathlib import Path
import json,hashlib,collections,struct,sys
from PIL import Image
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'tools'));from step5_b7_addresses import Addresses
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof={};out={'status':'pending','scope':'Reduced representative H9 acceptance: 020Fast exact state/private fractions, four completed RGB scene pairs, elapsed, native040 lifecycle,020Fast default-off bothCUSTOM1, new-hook signature failure, matched020 normal/dense and040BCE grid/dense FPS,060BCE grid candidate,040BCE matched traces.'}
def result(name,build=None):
 p=r/'tmp/step5'/name/'result.json';x=read(p)
 if build:assert x['slave_sha256']==sha(r/'tmp/build'/build/'FerrariFormulaOne.slave'),name
 proof[name]={'result':str(p.relative_to(r)),'sha256':sha(p)};return x
build=read(r/'manifest/render-h9-build-audit.json');assert build['status']=='passed';assert (r/'tmp/build/render-h9/FerrariFormulaOne.slave').read_bytes()==(r/'tmp/build/render-h9-rebuild/FerrariFormulaOne.slave').read_bytes();build['reproducible_build']=True;assert sha(r/'dist/FerrariFormulaOne_v1.02-rc2_0481_Performance.lha')==build['rc2_sha256'];out['build']=build
model=read(r/'manifest/render-h9-model.json');assert model['status']=='passed' and model['directed_cases']==450 and len(model['captured'])==16
for x in model['captured']:assert sha(r/x['path'])==x['sha256']
out['model']=model;out['callers']=read(r/'manifest/render-h9-callers.json');assert out['callers']['status']=='passed'
states=[]
for arm in ['control','candidate']:
 n='c4-q03-drive-state-production-a1200-fast-h9-state-'+arm;x=result(n,'render-h9-matched'+('-control' if arm=='control' else ''));assert x['steps']==100 and x['context_after'][6]==100 and x['error']==0;states.append(r/'tmp/step5'/n)
assert (states[0]/'records.bin').read_bytes()==(states[1]/'records.bin').read_bytes();assert read(states[0]/'private.json')==read(states[1]/'private.json');out['exact_updates']=100
for scene in ['normal','solo','grid','dense']:
 pair=[]
 for arm in ['control','candidate']:
  n=f'c4-q03-h5-frame-production-a1200-fast-h9-{scene}-{arm}';b='render-h9-'+('matched' if scene=='normal' else scene)+'-stable-frames'+('-control' if arm=='control' else '');x=result(n,b);assert x['error']==0 and len(x['frames'])==30
  for f in x['frames']:
   im=Image.open(r/'tmp/step5'/n/f"frame-{f['update']}.png").convert('RGB');assert hashlib.sha256(im.tobytes()).hexdigest()==f['pixel_sha256']
  pair.append(x['frames'])
 assert pair[0]==pair[1],scene
out['rgb_frames_each_scene']=30
x=result('c4-q03-drive-timing-a1200-fast-h9-elapsed','render-h9');assert x['status']=='passed' and x['simulated_seconds']==60 and x['error_percent']<=.25;out['elapsed_error_percent']=x['error_percent']
fps={}
for p,s in [('a1200-fast','normal'),('a1200-fast','dense'),('040-40-bce','grid'),('040-40-bce','dense'),('060-50-bce','grid')]:
 for a in (['candidate'] if p.startswith('060') else ['control','candidate']):
  b='render-h9'+('' if s=='normal' else '-'+s)+('-control' if a=='control' else '');x=result(f'c4-q03-h5-fps-{p}-h9-{s}-{a}',b);assert x['status']=='passed' and len(x['interval_fields'])==300 and x['error']==0 and x.get('heavy_incomplete',0)==0
  fps[p+'/'+s+'/'+a]={k:x[k] for k in ['fps','mean_ms','p95_ms','slave_sha256']}|{'histogram':dict(sorted(collections.Counter(x['interval_fields']).items()))}
 if not p.startswith('060'):
  a,b=[fps[p+'/'+s+'/'+z] for z in ['control','candidate']];assert b['mean_ms']<=a['mean_ms'] and b['p95_ms']<=a['p95_ms']
out['fps']=fps
traces={}
for a in ['control','candidate']:
 p=r/f'tmp/step5/hi25-profile-040-40-bce-h9-grid-{a}';x=result(p.name,'render-h9-grid'+('-control' if a=='control' else ''));assert x['status']=='passed' and '--uae_blitter_cycle_exact=true' in x['extra_args'];s=read(p/'h7-safety.json');assert s['status']=='passed' and s['maximum_dma_address']=='0x59fb0'
 traces[a]={'analysis':read(p/'hi25-analysis.json'),'safety':s,'trace_hash':read(p/'h9-trace-hash.json')}
assert traces['candidate']['analysis']['mean_after_wait_ms']<traces['control']['analysis']['mean_after_wait_ms'];out['traces']=traces
x=result('c4-q03-h7-live-040-40-h9-candidate','render-h9');assert x['status']=='passed' and x['fresh_epoch_after_actual_session_change'] and x['ledger_entries']==x['ledger_restored_words']
p=r/'tmp/step5/c4-q03-h7-live-040-40-h9-candidate';m=(p/'takeover.bin').read_bytes();table=int(x['table'],16);probe=int(x['probe'],16);a=Addresses(m,table).map(0x6abc6);sy=read(r/'tmp/build/render-h9/build.json')['payloads']['fine']['symbols'];assert m[a:a+6]==bytes.fromhex('4ef9')+struct.pack('>I',probe+sy['FF1RenderFill']);m=(p/'fresh-session-step21.bin').read_bytes();a=Addresses(m,table).map(0x6abc6);assert m[a:a+6]==bytes.fromhex('4ef9')+struct.pack('>I',probe+sy['FF1RenderFill']);out['lifecycle']={'ledger_restored_words':x['ledger_restored_words'],'fill_hook_present_on_takeover_and_reload':True,'native_pause_tow_pit_menu_reentry':'passed'}
x=result('c4-q03-h9-bad-signature-a1200-fast-candidate','render-h9-bad-signature');assert x['status']=='passed' and x['road_fill_hook_not_installed'];out['signature_failure']='passed'
for c in [0,1]:
 p=r/f'manifest/render-h9-default-c{c}-validation.json';x=read(p);assert x['status']=='passed' and x['profiles']['a1200-fast']['passed'];proof['legacy/'+str(c)]={'path':str(p.relative_to(r)),'sha256':sha(p)}
out['legacy']='020Fast bothCUSTOM1 passed; coarse payloads byte-identical';out['evidence']=proof;out['tool_sha256']={n:sha(r/'tools'/n) for n in ['test_h9_model.py','capture_h9_planes.py','run_h9_checks.py','analyze_h9_trace.py','audit_h9_build.py','audit_h9_final.py']};checks=read(r/'manifest/render-h9-checks.json');checks['status']='passed';(r/'manifest/render-h9-checks.json').write_text(json.dumps(checks,indent=2)+'\n');out['status']='passed';out['next']='H10; H6c 25FPS target not yet met; H12 still needs explicit approval';(r/'manifest/render-h9-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('H9 accepted',build['candidate_sha256'])
