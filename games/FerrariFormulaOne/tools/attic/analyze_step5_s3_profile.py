from pathlib import Path
import json,sys,collections,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1]
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[dict(name='gear_transition',address='0x6bf84',bytes=4)]
report={'scope':'Matched corrected-S2 lean versus S3 lean p0, same all-car diagnostic and startup control, unwarped complete updates. Native render entries and blitter busy-spin audited from the full instruction trace.','profiles':{}}
for p in ('a1200','a1200-fast'):
 dirs=[r/'tmp/step5'/(f'{p}-s3-profile-s2' if v=='s2' else f'{p}-s3-v3-profile-s3') for v in ('s2','s3')]
 if not all((d/'classified.json').exists() for d in dirs):continue
 prof=[json.loads((d/'profile.json').read_text()) for d in dirs];pc=[json.loads((d/'percar.json').read_text()) for d in dirs];cl=[json.loads((d/'classified.json').read_text()) for d in dirs]
 n=prof[0]['complete_updates'];assert n==prof[1]['complete_updates']
 assert all(a['per_update_cycles']==b['per_update_totals'] for a,b in zip(prof,pc))
 assert all(abs(sum(c['totals'].values())-a['mean_cycles'])<.001 for c,a in zip(cl,prof))
 data=[(d/'start.bin').read_bytes() for d in dirs]
 diffs=[x['name'] for x in blocks if data[0][int(x['address'],16):int(x['address'],16)+x['bytes']]!=data[1][int(x['address'],16):int(x['address'],16)+x['bytes']]]
 audits=[]
 for d in dirs:
  trace=barto.load(d/'detail.bin');loops=[];cur=None
  memory=(d/'end.bin').read_bytes();vector=struct.unpack_from('>I',memory,0x243c8)[0]-228
  wait_target=None;after_vector=False
  for f in trace.fields:
   for addr,cost,regs in trace.instructions(f):
    if after_vector and addr not in (None,0x7fffffff):
     wait_target=addr;break
    if addr==vector:after_vector=True
   if wait_target is not None:break
  assert wait_target is not None and wait_target>0x80000,wait_target
  for f in trace.fields:
   for addr,cost,regs in trace.instructions(f):
    if addr==0x65174:
     if cur is not None:loops.append(cur)
     cur=collections.Counter()
    if cur is None or addr is None:continue
    if addr==0x24ae0:cur['native_blit_calls']+=1
    if addr==0x23946:cur['clock_glyph_calls']+=1
    if addr==0x6c0d0:cur['instrument_calls']+=1
    if 0x6bcce<=addr<0x6be6a or 0x6bf2c<=addr<0x6bf60:cur['boost_drawing_cycles']+=cost
    if wait_target+0x10<=addr<wait_target+0x32:cur['WaitBlit_busy_spin_cycles']+=cost
  total=collections.Counter()
  for q in loops[:n]:total.update(q)
  audits.append(dict(total))
  print(d.name,'WaitBlit target',hex(wait_target),flush=True)
 before,after=[a['mean_cycles'] for a in prof]
 report['profiles'][p]=dict(passed=not diffs and not any(audits[1].values()),start_state_mismatches=diffs,complete_updates=n,s2_cycles=before,s3_cycles=after,saving_cycles=before-after,saving_percent=100*(before-after)/before,s3_ms=after/14187.58,s2_render_audit=audits[0],s3_render_audit=audits[1],s2_segments=pc[0]['segments'],s3_segments=pc[1]['segments'])
 print(p,{k:v for k,v in report['profiles'][p].items() if not k.endswith('segments')},flush=True)
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-s3-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n')
