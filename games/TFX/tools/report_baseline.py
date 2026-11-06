#!/usr/bin/env python3
"""Validate and summarize the frozen baseline matrix; never turn failed cells into FPS."""
import argparse,hashlib,json,re,struct
from pathlib import Path
from baseline_matrix import START,END,VARIANTS
from replay_flight import sha

def validate(path):
 r=json.loads((path/'counts.json').read_text());m=json.loads((path/'manifest.json').read_text())
 assert r['window']==[START,END] and r['pal_fields']==END-START
 assert m['variant']==r['variant']
 assert r['variant']['executable'] in ['TFX','tfx.020','TFX.FPU','TFX.040']
 for phase in ['entry','end']:
  fields=dict(re.findall(r'(\w+)=(\w+)',(path/f'cpuinfo-{phase}.txt').read_text()))
  for key,value in r['variant']['expected_cpu'].items():assert int(fields[key])==value
 assert (path/'cpuinfo-entry.txt').read_text()==(path/'cpuinfo-end.txt').read_text(),'CPU/cache metadata changed across window'
 events=r['events'];ticks=0;swap=1;published=set();previous=None
 for e in events:
  if e['kind']=='vblank':ticks+=1
  elif e['kind']=='swap':swap+=1
  else:
   assert e['kind']=='publish';assert swap not in published;published.add(swap)
   assert e['copper']!=previous and 0<=e['copper']<0x200000;previous=e['copper']
  assert e['vblank']==ticks and e['swap']==swap
 assert ticks==END
 pubs=[e for e in events if e['kind']=='publish' and START<=e['vblank']<END]
 assert len(pubs)==r['publications'] and r['pal50_equivalent_fps']==50*len(pubs)/(END-START)
 tape=json.loads((path/'flight.tape.json').read_text())
 expected=[dict(e,vblank=next(x['vblank'] for x in events if x['kind']=='swap' and x['swap']==e['swap'])) for e in tape['flight_inputs'] if e['swap']<=swap]
 assert r['inputs']==expected
 assert sha(path/'flight.tape.json')==m['tape_sha256']
 assert sha(path/'slave.slave')==m['slave_sha256']
 image=next(path.glob('after.*g'))
 return r,m,image

def report(root):
 rows=[]
 for machine,variant in [('040',x) for x in VARIANTS]+[('020','integer'),('020','newfpu')]:
  a,b=[root/f'{machine}-{variant}-{i}' for i in (1,2)]
  if not (a/'manifest.json').exists() or not (b/'manifest.json').exists():
   unavailable=a/'unavailable.json'
   if machine=='020' and variant=='newfpu' and (a/'failure.txt').exists():
    memory=(a/'locate-fast.bin').read_bytes()
    config=(a/'debug.uae').read_text()
    # Match the rendered WHDLoad fault location, not its generic error-message table.
    if b"Prg 'TFX.020' Off $50F4C" in memory and 'cpu_model=68020\n' in config and not re.search(r'^fpu_model=(?!0$)\d+',config,re.M):
     unavailable.write_text(json.dumps({'reason':'Forced tfx.020 faults without an FPU at code offset $50F4C (FMOVE to FPCR). No flight or FPS result.','evidence':['failure.png','locate-fast.bin','debug.uae'],'game_offset':'0x50f4c'},indent=2))
   if unavailable.exists():
    assert (a/'failure.txt').exists()
    reason=json.loads(unavailable.read_text())
    rows.append(dict(machine=machine,variant=variant,status='unavailable',reason=reason,log=f'{machine}-{variant}-1.log',evidence_sha256={str(f.relative_to(root)):sha(f) for f in a.iterdir() if f.is_file()}))
   else:rows.append(dict(machine=machine,variant=variant,status='incomplete',log=f'{machine}-{variant}-1.log'))
   continue
  x,m,im=validate(a);y,n,jn=validate(b)
  for key in ['variant','slave_sha256','fpsp040_sha256','fpsp060_sha256','executable_sha256','emulator_sha256','seed_sha256','tape_sha256']:assert m[key]==n[key],key
  assert len(x['events'])==len(y['events']),f'{a}: event count repeat mismatch'
  assert x['publications']==y['publications'],f'{a}: publication total repeat mismatch'
  event_differences=[{'index':i,'run1':e,'run2':f} for i,(e,f) in enumerate(zip(x['events'],y['events'])) if e!=f]
  assert x['inputs']==y['inputs']
  assert im.read_bytes()==jn.read_bytes(),f'{a}: screenshot repeat mismatch'
  states={};raw=True
  for p in sorted(a.glob('*-hunk*.bin')):
   u=p.read_bytes();v=(b/p.name).read_bytes();assert len(u)==len(v)
   diffs=[i for i,(c,d) in enumerate(zip(u,v)) if c!=d]
   if diffs:states[p.name]={'differing_bytes':len(diffs),'offsets':[hex(i) for i in diffs]};raw=False
  rows.append(dict(machine=machine,variant=variant,status='measured',publications=x['publications'],vblanks=END-START,fps=x['pal50_equivalent_fps'],repeats=2,events_identical=not event_differences,event_differences=event_differences,screenshots_identical=True,raw_hunks_identical=raw,state_differences=states,inputs=x['inputs'],cpuinfo=(a/'cpuinfo-entry.txt').read_text(),evidence_sha256={str(p.relative_to(root)):sha(p) for folder in [a,b] for p in folder.iterdir() if p.is_file()}))
 return dict(window=[START,END],units='publications per 50 PAL vblanks; emulator A/B only',rows=rows)

def main():
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();r=report(a.root)
 (a.root/'report.json').write_text(json.dumps(r,indent=2))
 for row in r['rows']:print(row['machine'],row['variant'],row['status'],row.get('fps'),row.get('raw_hunks_identical'))
 if any(row['status']=='incomplete' for row in r['rows']):raise SystemExit(1)
if __name__=='__main__':main()
