"""Check complete step-13 boot coverage, frozen builds and CPU/FPU gates."""
import json,hashlib,struct,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=root/'tmp/step13'
read=lambda x:json.loads(x.read_text())
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
expected_slave=sha(p/'candidate.slave');baseline_slave=sha(p/'baseline.slave')
meta=read(root/'tmp/step9/fpu-sites.json')
static={s['offset']:0x4eb80000+meta['slots'][s['key']] for s in meta['sites']}
hot=dict(zip([0x50f82,0x5169e,0x516b6,0x517a4,0x517f2,0x5183c],[0x1fc,0x202,0x208,0x20e,0x214,0x21a]))
report={'baseline':{},'candidate':{},'startup':{},'unsupported':{}}
for cpu in ['040','020','030','060']:
 b=p/('baseline' if cpu in ['040','020'] else 'baseline-'+cpu)
 for label in ['auto','auto-original']:
  d=b/(cpu+'-'+label);a=read(d/'audit.json');assert a['passed'] and a['publications']==3
  assert sha(d/'slave.slave')==baseline_slave
  report['baseline'][d.name]=a['variant']['executable']
 labels=['auto','auto-original','integer']+([] if cpu=='020' else ['fpu','newfpu','beta'])+['fps','fps-original','uncapped','oneframe','both','both-original','no-fpu-fixes']
 for label in labels:
  d=p/('candidate-'+cpu)/(cpu+'-'+label);a=read(d/'audit.json');assert a['passed'] and a['publications']==3
  assert sha(d/'slave.slave')==expected_slave
  launch=read(d/'launch.json');assert launch['slave_sha256']==expected_slave
  if cpu in ['040','060']:assert '\nfpu_no_unimplemented=true\n' in (d/'debug.uae').read_text()
  for name in ['fpsp040','fpsp060']:assert sha(d/name)==sha(p/'baseline-inputs'/name)
  v=a['variant'];c= (d/'code.bin').read_bytes()
  if v['executable']=='tfx.020' and cpu=='040':
   if not v.get('custom5',0):
    for off,op in static.items():assert struct.unpack_from('>I',c,off)[0]==op
    for off,slot in hot.items():assert struct.unpack_from('>I',c,off)[0]==0x4eb80000+slot
   else:
    for site in meta['sites']:assert c[site['offset']:site['offset']+4]==bytes.fromhex(site['original'])
   report['candidate'][d.name]={'executable':v['executable'],'native_fpu':not bool(v.get('custom5',0)),'passed':True}
  else:report['candidate'][d.name]={'executable':v['executable'],'passed':True}
  if label=='newfpu' and cpu=='060':
   old=(root/'tmp/step10/final/gate-060-114/code.bin').read_bytes()
   assert all(c[o:o+4]==old[o:o+4] for o in list(static)+list(hot))
   report['060_fpu_sites_unchanged']=len(static)+len(hot)
 for label in ['intro','menu','configuration','action-intro']:
  d=p/('startup-'+cpu)/(cpu+'-'+label);assert read(d/'capture.json')['captured']
  assert sha(d/'slave.slave')==expected_slave
  for delay in [0,250,500]:assert (d/f'startup-{delay}.png').stat().st_size>0
  report['startup'][d.name]='captured; see visual review'
assert len(report['candidate'])==49 and len(report['baseline'])==8 and len(report['startup'])==16
assert report['candidate']['040-auto']['executable']=='tfx.020'
for cpu in ['020','030','060']:
 for label in ['auto','auto-original']:
  key=cpu+'-'+label;assert report['candidate'][key]['executable']==report['baseline'][key]
assert sha(root/'tmp/build/release/TFX.Slave')==expected_slave
report['visual_review']=read(p/'visual-review.json')
assert report['visual_review']['passed']
report['unsupported']=read(p/'no-fpu/verified-results.json')
assert all(not x['supported'] for x in report['unsupported'].values()) and len(report['unsupported'])==3
report['passed']=True;(p/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':True,'flight_boots':49,'startup_cases':16,'baseline_cases':8,'unsupported_no_fpu':3,'unchanged_060_fpu_sites':report['060_fpu_sites_unchanged']},indent=2))
