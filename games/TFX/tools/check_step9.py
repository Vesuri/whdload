"""Validate retained step-9 evidence; report every failed replay-state gate."""
import csv,json,struct,hashlib,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=root/'tmp/step9';final=p/'final';report={}
meta=json.loads((p/'fpu-sites.json').read_text());expected={s['offset']:0x4eb80000+meta['slots'][s['key']] for s in meta['sites']}
expected.update({o:0x4eb801fc+6*i for i,o in enumerate([0x50f82,0x5169e,0x516b6,0x517a4,0x517f2,0x5183c])})
code=(final/'profile/entry-hunk0.bin').read_bytes()
assert all(struct.unpack_from('>I',code,o)[0]==v for o,v in expected.items());report['live_040_sites']=len(expected)
for name in ['profile','profile-repeat']:
 r=list(csv.reader((final/name/'profile.csv').open()));counts=json.loads((final/name/'counts.json').read_text())
 exceptions=[x for x in r if x[0]=='exception'];bad=[x for x in exceptions if int(x[2]) not in (26,27,28)]
 assert not bad and counts['publications']==73
 report[name]=dict(publications=73,fpu_exceptions=0,strict_fpu=next(x for x in r if x[0]=='meta')[-1]=='1')
 assert report[name]['strict_fpu']
a=json.loads((final/'profile/counts.json').read_text());b=json.loads((final/'profile-repeat/counts.json').read_text());assert a['events']==b['events'] and a['inputs']==b['inputs']
report['timing_pair']={f:(final/'profile'/f).read_bytes()==(final/'profile-repeat'/f).read_bytes() for f in ['after.png','end-hunk0.bin','end-hunk1.bin','end-hunk2.bin']};assert report['timing_pair']['after.png']
report['controlled_images']={f'swap-{n:03d}.png':(final/'baseline-scene'/f'swap-{n:03d}.png').read_bytes()==(final/'native-scene'/f'swap-{n:03d}.png').read_bytes() for n in [1,10,30,45,57]};assert all(report['controlled_images'].values())
math=json.loads((p/'math-tests-final/oracle.json').read_text());assert not math['failures'] and not any(x['observed'] for x in math['fpsp_outliers']);report['math']=math
static=json.loads((p/'static-tests2/results.json').read_text());assert all(x['equal'] and x['fpsr_equal'] and x['fpcr_equal'] for x in static);report['static_cases']=len(static)
# Same binary/layout, CUSTOM5=1 versus 0, at the same controlled publication.
controlled=[p/'controlled-off',p/'controlled-on'];assert json.loads((controlled[0]/'segments.json').read_text())==json.loads((controlled[1]/'segments.json').read_text())
numeric=json.loads((p/'controlled-numerics.json').read_text());assert len(numeric)==20
for h in range(3):
 a,b=[bytearray((q/f'end-hunk{h}.bin').read_bytes()) for q in controlled]
 if h==0:
  for o,v in expected.items():
   original=next((bytes.fromhex(x['original']) for x in meta['sites'] if x['offset']==o),None)
   if original is None:
    original=bytes.fromhex({0x50f82:'f2001c0f',0x5169e:'f2001c0e',0x516b6:'f2001c1d',0x517a4:'f200068a',0x517f2:'f2001c0a',0x5183c:'f2001c0c'}[o])
   assert a[o:o+4]==original
   assert struct.unpack_from('>I',b,o)[0]==v
   a[o:o+4]=b[o:o+4]
  clocks=[0x4d85a,0x4d884]
 elif h==1:
  clocks=[0x10678,0x13de0]
  for item in numeric:
   o=int(item['offset'],16);x=struct.unpack_from('>d',a,o)[0];y=struct.unpack_from('>d',b,o)[0]
   assert x==item['a'] and y==item['b'] and abs(x-y)<=8e-12 and abs(x-y)/max(1,abs(x))<=3e-14
   a[o:o+8]=b[o:o+8]
 else:clocks=[]
 for o in clocks:
  assert struct.unpack_from('>I',b,o)[0]-struct.unpack_from('>I',a,o)[0]==-2
  a[o:o+4]=b[o:o+4]
 assert a==b,('unexplained controlled bytes',h)
for n in [1,10,30,45,57]:assert (controlled[0]/f'swap-{n:03d}.png').read_bytes()==(controlled[1]/f'swap-{n:03d}.png').read_bytes()
report['controlled_state']=dict(intentional_patches=245,clock_fields=4,clock_delta=-2,numeric_cells=20,max_absolute_difference=max(x['absolute_error'] for x in numeric),max_scaled_difference=max(x['scaled_error'] for x in numeric),unexplained_bytes=0)
modes=json.loads((p/'modes/results.json').read_text());assert all(x['equal'] and x['fpsr_equal'] and x['fpcr_equal'] for x in modes);report['mode_cases']=len(modes)
reg=json.loads((final/'regression/summary.json').read_text());report['regression']=reg
# 040/030 clock/cadence divergence is retained, never waived by this checker.
assert reg['020']['screenshots_identical'] and reg['060']['screenshots_identical']
# On 060 the original 040 emulation list and 060-specific sites stay byte-identical.
a=(root/'tmp/step8/final-regression/060-1/swap-001-hunk0.bin').read_bytes();b=(final/'regression/060-1/swap-001-hunk0.bin').read_bytes()
assert all(a[o:o+4]==b[o:o+4] for o in expected);report['060_fpu_sites_unchanged']=True
assert (root/'tmp/build/release/TFX.Slave').read_bytes()==(final/'profile/slave.slave').read_bytes()
for f in ['fpsp040','fpsp060']:assert (root/'tmp/build'/f).read_bytes()==(root/'tmp/step8/final-window'/f).read_bytes()
(p/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='math'},indent=2))
