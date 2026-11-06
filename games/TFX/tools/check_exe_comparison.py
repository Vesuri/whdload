"""Final executable-policy coverage and frozen-input checks; no emulator launch."""
import json,hashlib,struct,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];r=root/'tmp/exe-compare'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=sha(r/'auto.slave');meta=read(root/'tmp/step9/fpu-sites.json')
base=['auto','auto-original','integer','fpu','newfpu','beta','fps','fps-original','uncapped','oneframe','both','both-original','no-fpu-fixes','integer-projection']
rows={}
for folder,cpus,fpu,labels in [('selection',['040','030','060','020'],True,base),('selection-no-fpu',['020'],False,[n for n in base if n not in ['fpu','newfpu','beta','integer-projection']]),('selection-68881',['020'],True,['auto','auto-original'])]:
 for cpu in cpus:
  for name in labels:
   d=r/folder/(cpu+'-'+name);a=read(d/'audit.json');v=a['variant']
   assert a['passed'] and a['publications']==3
   assert sha(d/'slave.slave')==expected==read(d/'launch.json')['slave_sha256']
   for n in ['fpsp040','fpsp060']:assert sha(d/n)==sha(root/'tmp/game/TFX_v2.1_AGA/TFXAGA/data'/n)
   if v['custom3']==0:assert v['executable']==('tfx.020' if fpu else 'TFX')
   if v['executable']=='tfx.020':
    assert read(d/'renderer-audit.json')['passed']
    bases=read(d/'segments.json');enabled=not bool(v['custom4']&4)
    assert all(a>=0x40000000 if enabled else a<0x200000 for a in bases[1:])
    code=(d/'code.bin').read_bytes()
    if cpu=='040':
     for x in meta['sites']:
      want=bytes.fromhex(x['original']) if v.get('custom5',0) else (0x4eb80000+meta['slots'][x['key']]).to_bytes(4,'big')
      assert code[x['offset']:x['offset']+4]==want,(name,x)
   if cpu in ['040','060']:assert '\nfpu_no_unimplemented=true\n' in (d/'debug.uae').read_text()
   assert (d/'flight.png').stat().st_size>0
   rows[folder+'/'+cpu+'-'+name]=v['executable']
assert len(rows)==68,len(rows)
startup=[]
for folder,cpus in [('startup',['040','030','060','020']),('startup-no-fpu',['020'])]:
 for cpu in cpus:
  for name in ['intro','menu','configuration','action-intro']:
   d=r/folder/(cpu+'-'+name);assert read(d/'capture.json')['captured'];assert sha(d/'slave.slave')==expected
   for n in ['fpsp040','fpsp060']:assert sha(d/n)==sha(root/'tmp/game/TFX_v2.1_AGA/TFXAGA/data'/n)
   for delay in [0,250,500]:assert (d/f'startup-{delay}.png').stat().st_size>0
   startup.append(folder+'/'+d.name)
for cpu in ['020','030','060']:
 p=r/f'native-{cpu}-project';assert read(p/'oracle.json')['cases']==275
 g=read(r/f'native-{cpu}-gouraud/results.json');assert g['passed']==g['streams']==18 and g['rows']==2496 and g['model_passed']==18 and all(g['negative_controls_rejected'].values())
assert sha(root/'tmp/build/release/TFX.Slave')==expected
report=dict(passed=True,flight_cases=len(rows),startup_cases=len(startup),rows=rows,startup=startup,slave_sha256=expected,visual_review=read(r/'visual-review.json'))
assert report['visual_review']['passed']
(r/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k not in ['rows','startup','visual_review']})
