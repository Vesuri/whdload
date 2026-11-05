#!/usr/bin/env python3
"""Acceptance of retained phase-7 emulator evidence, with explicit negative controls."""
import json
from harness import ROOT,sha
from audit_simulation import ranges,originals,validate
from check_units import check as units
from check_disabled import check as installed
from verify_state import private,compare
out=ROOT/'tmp/phase7'
names=['straight-a500','straight-a1200','slow-a500','slow-a1200','events-a500','events-a1200','crash-block','demo-a500','demo-a1200','disabled','route-a500','route-slow-a500']
report={'captures':{}}
for name in names:
 p=out/('final-'+name);meta=json.loads((p/'capture.json').read_text())
 assert sha(p/'slave.slave')==sha(ROOT/'tmp/build/verify/TestDrive.Slave'),'stale fixture build'
 units((p/'code.bin').read_bytes());installed(p)
 s=json.loads((p/'states/samples.json').read_text());assert len(s)==meta['fields']
 assert all(b['vbl']==a['vbl']+1 for a,b in zip(s,s[1:])), 'skipped field'
 if meta['options']['C5']&1:
  raw=(p/'code.bin').read_bytes();start=private(raw);at=meta['regions']['td-data']-meta['base']+0x7ffe
  assert start['active']==1 and start['visual_seed']==0x1234
  assert int.from_bytes(raw[at-25640:at-25638],'big')==0x1234,'player gameplay seed not reset'
  assert int.from_bytes(raw[at-31782:at-31778],'big')==start['epoch'],'tape epoch differs from player anchor'
 r=private((p/'end/code.bin').read_bytes());report['captures'][name]={'fields':len(s),'rng_count':r['rng_count'],'fired':r['fired'],'renderer_updates':s[-1]['frames']-s[0]['frames'],'counted_updates':s[-1]['samples']-s[0]['samples']}
 if name.startswith(('straight','slow')):
  assert all(x['period']==5 for x in s),'original five-field period changed'
  assert s[0]['mode']==0 and max(x['gear'] for x in s)>=3
  assert max(x['speed'] for x in s)>0 and s[-1]['speed']==0,'acceleration/braking tape did not run'
 if name.startswith('events') or name=='crash-block':
  assert max(x['event'] for x in s)==1
  assert s[0]['chances']==5 and min(x['chances'] for x in s)==s[-1]['chances']==4,'not one crash penalty'
  jumps=[b['samples']-a['samples'] for a,b in zip(s,s[1:])]
  assert jumps.count(240)==1,'240-unit penalty not applied exactly once'
  if name=='crash-block':
   assert r['fired']==1 and s[-1]['event']==1
   assert len({x['samples'] for x in s[-100:]})==1,'original crash no longer blocks clock'
  else:
   assert r['fired']==3 and s[-1]['event']==0 and s[-1]['gear']==0
   assert max(x['police_clock'] for x in s)>=90 and max(x['police_stop'] for x in s)==30
   assert r['recovery_started']==0,'automatic recovery did not finish'
for cpu in ['a500','a1200']:
 normal=report['captures']['straight-'+cpu];slow=report['captures']['slow-'+cpu]
 assert slow['renderer_updates']<normal['renderer_updates']
 assert slow['counted_updates']==normal['counted_updates']==259
for name,b in [('cross_cpu','straight-a1200'),('slow_a500','slow-a500')]:
 r=compare(out/'final-straight-a500',out/('final-'+b));assert r['first_difference']['clutch'] is not None and r['first_difference']['speed'] is not None
 report[name]=r
r=compare(out/'final-route-a500',out/'final-route-slow-a500');assert r['first_difference']['saved_x'] is not None,'geometry negative control did not diverge';report['geometry']=r
pa=private((out/'final-demo-a500/end/code.bin').read_bytes());pb=private((out/'final-demo-a1200/end/code.bin').read_bytes());n=min(pa['rng_count'],pb['rng_count'])
assert 0<n<=256 and pa['rng_log'][:n]==pb['rng_log'][:n]
assert {kind for kind,value in pa['rng_log'][:n]}=={1,2},'both traffic and radar draws required'
assert pa['visual_seed']!=pb['visual_seed'],'visual RNG negative control did not exercise different consumption'
report['rng']={'common_draws':n,'log':pa['rng_log'][:n],'visual_seeds':[pa['visual_seed'],pb['visual_seed']]}
reload=out/'final-reload-confirmed'
assert (reload/'unloaded-stub.bin').read_bytes()[:2]==bytes.fromhex('6100')
installed(reload);report['overlay_reload']='PASS: unloaded BSR stub, next race entry and installed ranges'
validate(ranges(),originals());report['status']='PASS';print(json.dumps(report,indent=2))
