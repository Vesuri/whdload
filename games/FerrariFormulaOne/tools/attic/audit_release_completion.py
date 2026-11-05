from pathlib import Path
import json,hashlib,zipfile
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
def read(name):return json.loads((r/'manifest'/f'{name}.json').read_text())
def sha(data):return hashlib.sha256(data).hexdigest()
gates=[]
def gate(name,evidence,scope):
 for p in evidence:assert (r/p).exists(),p
 gates.append(dict(requirement=name,status='passed',evidence=evidence,scope=scope))
prod=read('production-integration');assert prod['status']=='passed' and not prod['gates_remaining'];expected=prod['slave_sha256']
for profile,row in prod['timing'].items():assert row['slave_sha256']==expected and row['status']=='passed' and row['error']==0 and row['error_percent']<1
for x in ['step5-c4-q01-validation','step5-c4-q02-validation','step5-c4-q03-validation','step5-c4-performance-closure-audit','production-coarse-identity']:assert read(x)['status']=='passed'
for opt in (0,1):
 d=read(f'release-default-c{opt}-validation');assert d['status']=='passed' and len(d['profiles'])==4 and all(v['passed'] for v in d['profiles'].values())
d=read('release-disabled-ranges');assert d['status']=='passed' and len(d['comparisons'])==24 and all(v['passed'] for v in d['comparisons'])
d=read('release-disabled-reloads');assert len(d['results'])==8
for row in d['results']:
 x=json.loads((r/row['evidence']).read_text());assert x['native_original_reference_exact'] and x['reload_patch_words_exact']==1005
 assert x['slave_sha256']==expected
 # Preserve the actual byte inventories, not just summary flags.
 p=(r/row['evidence']).parent;a=(p/'input-start.bin').read_bytes();b=(p/'reloaded-race.bin').read_bytes()
 for q in read('release-perf-ranges')['PERF_RANGE']:assert a[q['start']:q['start']+q['bytes']]==b[q['start']:q['start']+q['bytes']]
gate('Step7.1 disabled options, first loads and native reloads',['manifest/release-default-c0-validation.json','manifest/release-default-c1-validation.json','manifest/release-disabled-ranges.json','manifest/release-disabled-reloads.json'],'Both CUSTOM1 values, all four base profiles; original timing option contract preserved.')
assert prod['pal_rejection']['status']=='passed' and prod['pal_rejection']['monitor']=='0x11000' and prod['pal_rejection']['slave_sha256']==expected
gate('Step7.2 version gating',['manifest/production-integration.json'],'SPS0481 enabled; unavailable Irek retains original route, as explicitly permitted by plan. No Irek runtime claim.')
d=read('release-accelerated-enabled');assert len(d['profiles'])==4
for profile,row in d['profiles'].items():
 a=r/f'tmp/step5/c4-q03-release-census-{profile}-clock-v2-a/window.jsonl';b=r/f'tmp/step5/c4-q03-release-census-{profile}-clock-v2-b/window.jsonl';assert a.read_bytes()==b.read_bytes();assert len(a.read_text().splitlines())==1001;assert sha(a.read_bytes())==row['dma_window_sha256'];assert row['error_percent']<1
assert read('release-cache-mmu')['status']=='passed';d=read('release-exact');assert d['state']['status']==d['frame']['status']=='passed';assert len(d['state']['cases'])==9 and len(d['frame']['cases'])==10
assert read('release-final-artifact-audit')['rgb_frames_rehashed']==300
gate('Step7.3 machine, cache, MMU, video and accelerated analysis',['manifest/production-integration.json','manifest/release-accelerated-enabled.json','manifest/release-cache-mmu.json','manifest/release-exact.json','manifest/release-clock-calibration.json'],'Calibrated DMA repeats, elapsed and frame/state checks; functional040/060MMU; enabled actualNTSC rejected. No physical-hardware timing ranking.')
d=read('release-laps');assert d['status']=='passed' and len(d['results'])==3
for row in d['results']:
 v=json.loads((r/row['evidence']).read_text());assert v['status']=='passed' and v['error']==0 and v['last_lap_time']==v['lap_time_native'] and v['lap_time_after']==1
s=read('release-season-roundtrip');a,b=[(r/f).read_bytes() for f in s['files']];assert a==b and len(a)==4190 and sha(a)==s['sha256']
d=read('release-modal-clocks');assert d['status']=='passed' and len(d['rows'])==2
m=read('release-monaco');v=json.loads((r/m['source']).read_text());assert v['monaco_prestart_entry_pc']==v['monaco_prestart_checkpoint'];assert v['monaco-after-501-updates']['completed']==501 and v['monaco-tow-restored']['context']==[0]*14
assert read('release-native-ui')['f10']['status']=='passed'
gate('Step7.4 native gameplay and modal routes',['manifest/release-native-ui.json','manifest/release-monaco.json','manifest/release-modal-clocks.json','manifest/release-season-roundtrip.json','manifest/release-laps.json','manifest/step5-c4-q01-validation.json','manifest/step5-c4-q02-validation.json','manifest/step5-c4-q03-validation.json'],'F1/F3, Fiorano/Rio/Monaco, start/traffic, directed contact/recovery/fuel/wear, native laps, pit/tow/pause/session/results, saved files and F10. Human full races explicitly deferred.')
d=read('release-runtime-memory');passed=[]
for row in d['results']:
 if row['status']!='passed':continue
 v=json.loads((r/row['evidence']).read_text());assert v['status']=='passed' and v['error']==0 and v['slave_sha256']==expected;assert v['context_after'][6]-v['context_before'][6]>=20;passed.append(row['case'])
assert len(passed)==10
blob=(r/'tmp/build/production/FerrariFormulaOne.slave').read_bytes();assert sha(blob)==expected and int.from_bytes(blob[44:46],'big')==17
gate('Step7.5 API, minimum/development runtimes and memory',['manifest/release-runtime-memory.json','manifest/release-toolchain.json'],'API17, ten qualified20-update runtime/memory/MMU arrangements; expected allocation exclusions explicitly documented. Mode stays default-off. No universal minimum or all-runtime save/load claim.')
assert read('release-production-audit')['status']=='passed';audit=read('release-final-artifact-audit');assert audit['status']=='passed'
for path,digest in audit['source_hashes'].items():assert sha((repo/path).read_bytes())==digest
p=read('release-candidate');assert p['status']=='passed' and p['production_sha256']==expected;assert sha((r/p['archive']).read_bytes())==p['archive_sha256']
with zipfile.ZipFile(r/p['archive']) as z:
 for name,meta in p['files'].items():assert sha(z.read('FerrariFormulaOne-1.02-rc1/'+name))==meta['sha256']
gate('Step7.6 production audit, reproducibility and candidate',['manifest/release-production-audit.json','manifest/release-final-artifact-audit.json','manifest/release-candidate.json'],'Production bytes exclude active VERIFY/test work; independent rebuild and complete payload hashes exact. Deterministic local candidate contains no game/runtime inputs and is unpublished.')
for file in ['PERFORMANCE.md','GAME_TIME.md','open-work.md','STEP5_CAPACITY.md','PERFORMANCE_PLAN.md']:assert (r/'docs'/file).exists()
assert read('project')['release_qualification_status'].startswith('Emulator release qualification')
gate('Step7.7 reconciled reports',['manifest/project.json','docs/PERFORMANCE.md','docs/GAME_TIME.md','docs/open-work.md','docs/STEP5_CAPACITY.md','docs/PERFORMANCE_PLAN.md'],'Current status reconciled; historical evidence retained. Shared generic splash/save-cache lessons committed in AmigaXDev7bd1307.')
report={'status':'passed','objective':'Finish emulator-based Ferrari Formula One release qualification and030/040/060 performance analysis','production_sha256':expected,'requirements':gates,'deferred':['human playtesting, including complete races','real Amiga hardware testing'],'permitted_limitations':['Irek unavailable; original route retained','enabled NTSC rejected','runtime/memory scope and NoWriteCache workaround documented'],'remaining_required_emulator_work':[]}
(r/'manifest/release-completion-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('Completion audit passed:',len(gates),'Step7 requirement groups; no required emulator work remaining')
