"""Validate retained step-4 evidence; no emulator or source mutation."""
from pathlib import Path
import sys,json,hashlib,struct,runpy
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'tools'))
ns=runpy.run_path(str(r/'tools/analyze_step4.py'))
from compare_step2 import FIELDS
from overlay_map import decode
m=json.loads((r/'manifest/step4-measurements.json').read_text());world=ns['world'];clock=ns['clock'];field=ns['field']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p):return json.loads(p.read_text())
def raw(n,label):return (r/'tmp/step4'/n/(label+'.bin')).read_bytes()
def census(n,count):
 rows=[json.loads(x) for x in (r/'tmp/step4'/n/'window.jsonl').read_text().splitlines()]
 assert rows[0]['meta'] and rows[0]['vblank_hz']==ns['hz'] and rows[0]['cycle_exact']==1
 assert len(rows)==count+1 and [x['field'] for x in rows[1:]]==list(range(count))
 assert all(x['cycles']==142102*256//rows[0]['cpucycleunit'] for x in rows[1:])
 return rows[0]
source=r.parents[1]/'Games/FerrariFormulaOne_WHD.s';release=r/'tmp/build/release/FerrariFormulaOne.slave';emulator=r/'tmp/step3/fs-uae'
assert sha(source)=='88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'
assert sha(release)=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
assert sha(emulator)=='2caccbb397100340227d41f98a489562cadab71a2e4a45878c6c6acfeb364fbb'
assert len(m['runs'])==21 and len(m['comparisons'])==12
for name,checks in m['comparisons'].items():
 assert len(checks)==(5 if 'contact3' in name else 4)
 assert not any(checks.values()),(name,checks)
# Normal and slowed drawing also preserve the original mixed state/render block.
for p in ('a500','a1200','a1200-fast'):
 for aa,bb in (('c0','c1'),('control-v2','slow-v2')):
  for tick in (125,150,175,225):
   a=raw(p+'-'+aa,f'loop{tick}');b=raw(p+'-'+bb,f'loop{tick}')
   assert all(a[i:i+z]==b[i:i+z] for _,i,z in FIELDS),(p,aa,bb,tick)
 for c in (0,1):assert raw(f'{p}-c{c}','anchor')==(r/f'tmp/step3/{p}-c{c}-a/anchor.bin').read_bytes()
# Comparator sensitivity and the independently observed rejected omission.
a=raw('a500-control-v2','loop225');b=bytearray(a);b[0x2275b]^=1
assert world(a)!=world(b)
assert world(a)!=world(raw('a500-control-v2','loop150'))
assert world(raw('a500-control','loop225'))!=world(raw('a500-logic','loop225'))
checks={'state_comparisons':12,'matched_checkpoints':sum(map(len,m['comparisons'].values())),'full_baseline_anchor_matches':6,'comparator_mutation_later_tick_and_rejected_omission':True,'normal_and_slow_original_projection_block_matches':True}
runs={}
for n,x in m['runs'].items():
 p=r/'tmp/step4'/n;v=js(p/'result.json');launch=js(p/'launch.json')
 assert v['status']=='complete' and v['warp_after']==v['warp_end']=='warp=0' and v['warp_before']=='warp=1'
 assert v['emulator_sha256']==sha(emulator)
 assert v['demo']==v['end_state']['demo']==1
 assert x['calendar_tenths']==x['session_tenths']==100
 assert launch['slave_sha256']==sha(Path(launch['SLAVE']))
 profile=next(q for q in ('a1200-fast','a1200','a500') if n.startswith(q+'-'))
 expected=js(r/'manifest/step3-profiles.json')[profile]
 assert all(launch[k]==value for k,value in expected.items()),(n,launch,expected)
 if 'contact3' in n:
  assert v['contact_car']==0
  log=(p/'capture.log').read_text();assert '0x0006988c' in log
  b=raw(n,'contact');seg=struct.unpack_from('>H',b,0x32fca)[0];lat=struct.unpack_from('>h',b,0x32fc2)[0];width=struct.unpack_from('>h',b,0x1c914+2*seg)[0]
  assert lat==-width-80,(n,lat,width)
 runs[n]={'status':'passed','protocol':'completed loops 125 to 225, 100 native ticks','legacy_metadata_note':'requested_fields/observer in early result.json are unused inherited defaults, not an observed 1000-field window','field_count':x['field_count'],'mean_ms_per_tick':x['ms_per_update']}
fixtures={}
for folder,names in (('step4-v2',('control','slow','logic')),('step4-contact-v3',('control','logic'))):
 paths=[r/'tmp/build'/folder/(n+'.slave') for n in names];base=paths[0].read_bytes()
 assert all(len(p.read_bytes())==len(base) and sum(a!=b for a,b in zip(base,p.read_bytes()))==1 for p in paths[1:])
 fixtures[folder]={'bytes':len(base),'only_one_mode_byte_differs':True,'sha256':{p.name:sha(p) for p in paths}}
modal={}
for p in ('a500','a1200-fast'):
 n=p+'-menu-clock';start=raw(n,'anchor');end=raw(n,'end');v=js(r/'tmp/step4'/n/'result.json')
 assert v['status']=='complete' and v['warp_after']==v['warp_end']=='warp=0'
 meta=census(n,600)
 modal[n]={'protocol':'startup loading/countdown transition, not steady menu pacing','fields':600,'seconds':600/ns['hz'],'calendar_tenths':clock(end,0x226c0)-clock(start,0x226c0),'session_tenths':clock(end,0x226ca)-clock(start,0x226ca),'start_overlay':[g['identity'] for g in decode(start)['groups']],'end_overlay':[g['identity'] for g in decode(end)['groups']],'meta':meta}
 assert modal[n]['calendar_tenths']==modal[n]['session_tenths']==(0 if p=='a500' else 17)
 n=p+'-pause-fixture';start=raw(n,'pause_start');end=raw(n,'pause_end');resume=raw(n,'resumed_loop');v=js(r/'tmp/step4'/n/'result.json')
 assert v['status']=='complete' and v['warp_after']==v['warp_end']=='warp=0' and v['pause_pc']==0x6542c
 meta=census(n,100);assert (field(end)-field(start))%65536==100
 assert world(start)==world(end)
 assert clock(resume,0x226c0)-clock(end,0x226c0)==clock(resume,0x226ca)-clock(end,0x226ca)==1
 assert v['end_state']=={'demo':0,'mode':3}
 launch=js(r/'tmp/step4'/n/'launch.json');assert launch['slave_sha256']==sha(r/'tmp/build/step4-pause/pause.slave')
 modal[n]={'protocol':'new balanced key-consumer ESC fixture, native takeover/pause/resume; physical keyboard delivery not validated','fields':100,'seconds':100/ns['hz'],'all_semantic_blocks_frozen':True,'resume_calendar_and_session_tenths':1,'meta':meta}
for n in list(runs)+list(modal):
 p=r/'tmp/step4'/n
 target=runs[n] if n in runs else modal[n]
 target['sha256']={f.name:sha(f) for f in sorted(p.iterdir()) if f.is_file()}
equal_fields={}
for p in ('a500','a1200','a1200-fast'):
 for c in (0,1):
  n=f'{p}-c{c}-a';d=r/'tmp/step3'/n;a=(d/'anchor.bin').read_bytes();b=(d/'end.bin').read_bytes()
  equal_fields[n]={'fields':1000,'seconds':1000/ns['hz'],'calendar_tenths':clock(b,0x226c0)-clock(a,0x226c0),'session_tenths':clock(b,0x226ca)-clock(a,0x226ca),'sha256':{f:sha(d/f) for f in ('anchor.bin','end.bin','window.jsonl','result.json','launch.json')}}
artifacts=[source,release,emulator,r/'manifest/step4-measurements.json',r/'manifest/step4-static-audit.json',r/'manifest/step4-clock-refs.json',r/'manifest/step3-profiles.json']
artifacts+=list((r/'tools').glob('*step4*.py'))
artifacts+=list((r/'tmp/step4').glob('*.dis'))
for folder in ('step4-v2','step4-contact-v3','step4-pause'):artifacts+=list((r/'tmp/build'/folder).glob('*'))
for f in ('GAME_TIME.md','PERFORMANCE_PLAN.md','profiling.md','open-work.md'):artifacts.append(r/'docs'/f)
artifacts.append(r/'manifest/project.json')
rejected={p.name:js(p/'result.json') for p in (r/'tmp/step4').iterdir() if p.is_dir() and p.name not in runs and p.name not in modal and (p/'result.json').exists()}
out={'status':'complete within documented step-4 analysis scope','scope':{'profiles':['68000','68020','68020+Fast'],'deferred':['030','040','060'],'ordinary_workload':'automatic no-input demo','extra_checks':'synthetic native wall contact and ESC-consumer pause','static_only':'ordinary menu six-field gate, garage/repair, tow, transport, results and save/load clock boundaries','unvalidated':'physical keyboard delivery, full season, real hardware, Irek, NTSC, a shipping scheduler'},'gates':checks,'fixtures':fixtures,'runs':runs,'modal':modal,'equal_field_evidence_from_step3':equal_fields,'excluded_runs':rejected,'artifacts':{str(p.relative_to(r)) if p.is_relative_to(r) else str(p):sha(p) for p in sorted(set(artifacts))}}
(r/'manifest/step4-validation.json').write_text(json.dumps(out,indent=2)+'\n')
print('STEP 4 PASS:',checks)
print('Modal measurements:',{n:{k:v for k,v in x.items() if k not in ('sha256','meta')} for n,x in modal.items()})
