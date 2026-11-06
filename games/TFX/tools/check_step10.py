"""Validate retained step-10 exit evidence; never turn replay failures into waivers."""
import json,csv,struct,hashlib
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1];p=root/'tmp/step10';f=p/'final';report={}
read=lambda path:json.loads(path.read_text())
status=read(f/'run-status.json');assert all(v==0 for k,v in status.items() if k!='regression')
report['run_status']=status
for cpu,c4 in [('040',114),('040',118),('030',114),('060',114)]:assert read(f/f'gate-{cpu}-{c4}/audit.json')['passed']
report['cpu_option_gates']=4
# Full original vs native comparisons, independent non-empty pixel oracles.
for name,count in [('fills-test4',436),('lines-candidate2',592),('boxes-final',259),('final/fills',180)]:
 rows=read(p/name/'results.json');assert len(rows)==count
 field='different_longs'
 assert all(x[field]==0 for x in rows)
 if 'fills' in name:assert all(x['left_difference']==x['right_difference']==0 for x in rows)
 report[name+'_cases']=count
for name in ['fills-test4','final/fills']:
 oracle=read(p/name/'oracle.json');assert all(x['original_equal'] and x['native_equal'] and x['changed_bytes']>0 for x in oracle)
assert read(p/'boxes-final/oracle.json')==dict(original=True,native=True)
assert sum(bool(x['different_longs']) for x in read(p/'lines-before/results.json'))==113
assert sum(bool(x['different_longs']) for x in read(p/'boxes-before/results.json'))==60
rows=read(f/'options/results.json');assert len(rows)==41 and all(x['equal'] for x in rows);report['option_cases']=41
report['images']={}
for n in [1,10,30,45,57]:
 a=f/'scene'/f'swap-{n:03d}.png';b=f/'original-scene'/a.name
 assert a.read_bytes()==b.read_bytes()
 report['images'][n]=True
planes=read(p/'final-plane-comparison.json');assert all(x['planes_equal'] and x['rgb_equal'] for x in planes.values())
report['profiles']={}
for name in ['baseline','fills-profile','fills-profile-repeat','original-flat-profile']+[f'final/{mode}-{suffix}' for mode in ['default','uncapped','oneframe'] for suffix in ['profile','repeat']]:
 q=p/name;counts=read(q/'counts.json');rows=list(csv.reader((q/'profile.csv').open()))
 assert next(x for x in rows if x[0]=='meta')[-1]=='1'
 bad=[x for x in rows if x[0]=='exception' and int(x[2]) not in (26,27,28)];assert not bad
 report['profiles'][name]=dict(publications=counts['publications'],fpu_exceptions=0,window=counts['window'])
 assert counts['window']==[2,252]
report['timing_pairs']={}
for mode,limit in [('default',0x7002),('uncapped',0x7000),('oneframe',0x7001)]:
 a=f/(mode+'-profile');b=f/(mode+'-repeat');ca,cb=read(a/'counts.json'),read(b/'counts.json')
 assert ca['publications']==cb['publications']
 code=(a/'entry-hunk0.bin').read_bytes();assert struct.unpack_from('>H',code,0x1abfe)[0]==limit
 assert code[0x6c4f2:0x6c4f4]==bytes.fromhex('23df') # retained faster flat routine
 base=read(a/'segments.json')[0];assert struct.unpack_from('>I',code,0x6c4f4)[0]==base+0x6c4c0
 meta=read(root/'tmp/step9/fpu-sites.json')
 for site in meta['sites']:assert struct.unpack_from('>I',code,site['offset'])[0]==0x4eb80000+meta['slots'][site['key']]
 for i,o in enumerate([0x50f82,0x5169e,0x516b6,0x517a4,0x517f2,0x5183c]):assert struct.unpack_from('>I',code,o)[0]==0x4eb801fc+6*i
 for o in [0x4f840,0x4f9f8,0x4de00,0x500dc,0x4dba0,0x4dbc8]:assert code[o:o+2]==bytes.fromhex('4ef9')
 if mode=='uncapped':
  for o in [0x1830,0x1850,0x1ec38,0x1fec4]:assert code[o:o+2]==bytes.fromhex('4eb9')
 report['timing_pairs'][mode]=dict(events_equal=ca['events']==cb['events'],inputs_equal=ca['inputs']==cb['inputs'],image_equal=(a/'after.png').read_bytes()==(b/'after.png').read_bytes(),hunks_equal=[(a/f'end-hunk{i}.bin').read_bytes()==(b/f'end-hunk{i}.bin').read_bytes() for i in range(3)])
# Explain retained option-state differences without labelling raw state equal.
state=read(f/'timing-state-differences.json');report['timing_state_details']=state
for mode in ['uncapped','oneframe']:
 a=(f/(mode+'-profile')/'end-hunk0.bin').read_bytes();b=(f/(mode+'-repeat')/'end-hunk0.bin').read_bytes()
 if mode=='uncapped':
  assert struct.unpack_from('>H',a,0x4d77c)[0]==struct.unpack_from('>H',b,0x4d77c)[0]==0
  assert all(0x4d7c8<=int(o,16)<0x4d7d2 for o in state[mode][0]['other_changed_bytes'])
 else:assert not any(row['other_changed_bytes'] for row in state[mode])
reg=read(f/'regression/summary.json');report['regression']=reg
assert all(reg[cpu]['screenshots_identical'] for cpu in ['020','030','060'])
# Other CPUs retain unported fills and limits; low-page 060 FPU calls are unchanged.
for cpu in ['030','060']:
 code=(f/f'regression/{cpu}-1/swap-001-hunk0.bin').read_bytes()
 for off,raw in [(0x4f840,'45ef0004280d'),(0x4f9f8,'9efc001848e7'),(0x1830,'302cf45c48c0'),(0x1850,'302cf45c48c0'),(0x1ec38,'102cf45a5300'),(0x1abfe,'7002')]:assert code[off:off+len(raw)//2]==bytes.fromhex(raw)
 if cpu=='060':
  old=(root/'tmp/step9/final/regression/060-1/swap-001-hunk0.bin').read_bytes();meta=read(root/'tmp/step9/fpu-sites.json');sites=[x['offset'] for x in meta['sites']]+[0x50f82,0x5169e,0x516b6,0x517a4,0x517f2,0x5183c]
  assert all(code[o:o+4]==old[o:o+4] for o in sites)
report['060_fpu_sites_unchanged']=True
original=read(p/'baseline/launch.json')['executable_sha256'];assert hashlib.sha256((root/'tmp/game/TFX_v2.1_AGA/TFXAGA/data/tfx.020').read_bytes()).hexdigest()==original
report['pristine_game_unchanged']=True
assert (root/'tmp/build/release/TFX.Slave').read_bytes()==(f/'default-profile/slave.slave').read_bytes()
for name in ['fpsp040','fpsp060']:assert (root/'tmp/build'/name).read_bytes()==(p/'baseline'/name).read_bytes()
(p/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
