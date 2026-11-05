"""Audit current-source observed extreme-T cases, without claiming untested paths."""
from pathlib import Path
import json,hashlib,struct,subprocess
root=Path('tmp/prof');build=Path('tmp/build');src=Path('src');report={'passed':True,'scope':'Live observed collision/loop/jump/award matrix only; moving and turning results are separate until present. Not full-lap, arbitrary T or universal collision proof.','cases':{}}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for case in ['follow','headon','loop','jump','checkpoint','finish']:
 prefix='c4-live-' if case in ['follow','headon'] else 'c4-final-'
 manifest=json.loads((build/(prefix+case+'.json')).read_text())
 assert manifest['source_sha256']=={p.name:sha(p) for p in src.glob('*.s')}
 assert not any(manifest[k] for k in ['private_checkpoint_post','private_road_continuation','private_landing_impact','private_landing_depth','private_support_object','private_wide_pitch','private_terrain_road','private_road_pitch','private_full_pitch','private_keep_rate','private_contact_clamp'])
 for name,value in manifest['source_sha256'].items():
  if name not in ['HardDrivinVerify.s','HardDrivinPhase.s']:assert value==manifest['fixture_all_source_sha256'][name]
 for tag in ['slow','060']:
  name=prefix+case+'-'+tag;p=root/name;meta=json.loads((p/'metadata.json').read_text());m=json.loads((p/'motion.json').read_text());rows=m['rows'];steps=[r for r in rows if r['kind']=='STEP'];vbl=[r for r in rows if r['kind']=='VBL'];events=[r for r in rows if r['kind'] in ['CHECKPOINT','FINISH']];collisions=json.loads((p/'collision-objects.json').read_text())
  assert (p/'slave.slave').read_bytes()==(build/(prefix+case+'.slave')).read_bytes()
  assert len(vbl)==(180 if prefix=='c4-live-' else 450 if case in ['loop','jump'] else 130)
  assert m['profile']==('a500' if tag=='slow' else 'a4000-060-50') and m['delay']==(4 if tag=='slow' else 0)
  assert max(r['sweep_overflow'] for r in rows)==0
  intervals=sorted(set(r['interval'] for r in steps));assert max(intervals)>8 if tag=='slow' else max(intervals)<=2
  result=dict(slave_sha256=sha(p/'slave.slave'),fields=len(vbl),physics_returns=len(steps),intervals=intervals,postphysics_peak_y=max(r['y8'] for r in steps)/8,sweep_hits=max(r['sweep_hits'] for r in rows),sweep_overflow=0,events=[dict(kind=r['kind'],field=r['field'],consumed=r['consumed']) for r in events],collisions=collisions)
  crashes=[r for r in steps if r['crash']]
  result['first_crash_field']=crashes[0]['field'] if crashes else None
  if case in ['follow','headon']:
   assert len(collisions)==1 and not events and crashes[0]['crash']==25
   c=collisions[0];data=(p/'game-data.bin').read_bytes();pool=struct.unpack_from('>I',data,0x9962-0x8002)[0]
   assert c['object']==pool+96*56 and [c[k] for k in ['world_x','world_y','world_z','type','class','active']]==[20382,0,17345,1,8,255]
   before=[r for r in rows if r['kind']=='INPUT' and r['field']<=crashes[0]['field']][-1];integrated=[r for r in rows if r['kind']=='INTEGRATED' and r['field']<=crashes[0]['field']][-1]
   if tag=='slow':
    assert result['sweep_hits']==1
    sign=1 if case=='follow' else -1;target=17345*8
    assert sign*(before['z8']-target)<0 and sign*(integrated['z8']-target)>0 and sign*(crashes[0]['z8']-target)<0
    result['crossing']=dict(start_z=before['z8']/8,integrated_z=integrated['z8']/8,postcontact_z=crashes[0]['z8']/8,interval=integrated['interval'])
   else:assert result['sweep_hits']==0
  elif case=='loop':
   assert not crashes and not events and not collisions
   section=(steps[-1]['road_cursor']-steps[-1]['stunt_base'])//20;assert section>=50
   assert steps[-1]['course_next']==steps[0]['course_next']+8
   result['exit_section']=section
   result['airborne_returns']=[r['field'] for r in steps if r['mask']==0]
  elif case=='jump':
   assert crashes and crashes[0]['crash']==25 and not events and not collisions
   air=[r['field'] for r in steps if r['mask']==0];assert air and min(air)<max(air)<crashes[0]['field']
   result['airborne_returns']=[min(air),max(air)]
   result['exit_section']=(steps[-1]['road_cursor']-steps[-1]['stunt_base'])//20
   assert result['exit_section']==26
  else:
   kind='CHECKPOINT' if case=='checkpoint' else 'FINISH'
   assert len(events)==1 and events[0]['kind']==kind and not crashes and not collisions
   assert steps[-1]['checkpoint_latch']==(255 if case=='checkpoint' else 0)
   result['seeded_finish_latch']=manifest['seeded_checkpoint_latch']
  report['cases'][name]=result
# Moving traffic and turning collision captures retain the same production modules.
for prefix in ['c4-moving-v3-', 'c4-turn-']:
 for case in ['follow','headon']:
  manifest=json.loads((build/(prefix+case+'.json')).read_text())
  assert manifest['source_sha256']=={p.name:sha(p) for p in src.glob('*.s')}
  for name,value in manifest['source_sha256'].items():
   if name not in ['HardDrivinVerify.s','HardDrivinPhase.s']:assert value==manifest['fixture_all_source_sha256'][name]
  for tag in ['slow','060']:
   name=prefix+case+'-'+tag;p=root/name;m=json.loads((p/'motion.json').read_text());rows=m['rows'];steps=[r for r in rows if r['kind']=='STEP'];collisions=json.loads((p/'collision-objects.json').read_text())
   assert (p/'slave.slave').read_bytes()==(build/(prefix+case+'.slave')).read_bytes()
   assert m['profile']==('a500' if tag=='slow' else 'a4000-060-50') and m['delay']==(4 if tag=='slow' else 0)
   assert len(collisions)==1 and max(r['sweep_overflow'] for r in rows)==0
   c=collisions[0];pool=struct.unpack_from('>I',(p/'game-data.bin').read_bytes(),0x9962-0x8002)[0]
   assert c['object']==pool+96*56 and [c[k] for k in ['type','class','active']]==[1,8,255]
   crash=next(r for r in steps if r['crash']);assert crash['crash']==25
   before=[r for r in rows if r['kind']=='INPUT' and r['field']<=c['field']][-1]
   integrated=[r for r in rows if r['kind']=='INTEGRATED' and r['field']<=c['field']][-1]
   result=dict(slave_sha256=sha(p/'slave.slave'),collision=c,first_crash_field=crash['field'],contact_interval=integrated['interval'],sweep_hits=max(r['sweep_hits'] for r in rows),sweep_overflow=0,heading=integrated['heading'],turning=integrated['turning'])
   assert integrated['interval']>8 if tag=='slow' else integrated['interval']<=2
   if prefix=='c4-moving-v3-':
    seeds=[r for r in rows if r['kind']=='INPUT' and r['fixture_seeded']]
    assert rows[0]['fixture_seeded']==0 and seeds and all(r['fixture_seeded']==1 for r in rows[rows.index(seeds[0]):])
    assert abs(seeds[0]['target_z']-17345)>=20 and seeds[0]['traffic_started'] and seeds[0]['target_speed']>0
    assert before['target_speed']>0 and before['target_z']!=rows[0]['target_z']
    result.update(seed_field=seeds[0]['field'],seed_target_z=seeds[0]['target_z'],contact_target_z=before['target_z'],contact_target_speed=before['target_speed'])
    if tag=='slow' and case=='follow':assert result['sweep_hits']==1
   else:
    assert integrated['turning'] and integrated['heading']%(1440)!=(0 if case=='follow' else 720)
    if tag=='slow':assert result['sweep_hits']==1
   if tag=='060':assert result['sweep_hits']==0
   report['cases'][name]=result
report['scope']='Observed extreme-profile collision, moving-traffic, turning, loop, jump and award matrix. Not full-lap, arbitrary T or universal collision proof.'
# Auxiliary records in the frozen world are all non-solid native class64.
p=root/'c2-clock-debug-record';meta=json.loads((p/'metadata.json').read_text());regions=meta['world_regions'];offset=sum(r['size'] for r in regions[:-1]);aux=regions[-1];assert aux['name']=='aux_objects'
raw=subprocess.check_output(['zstd','-qdc',str(p/'world.bin.zst')]);stride=meta['world_snapshot_size'];classes={raw[i*stride+offset+j*56+28] for i in range(650) for j in range(aux['count'])};assert classes=={64}
report['auxiliary_audit']=dict(returns=650,objects_per_return=aux['count'],classes=sorted(classes),scope='These captured auxiliary records never meet native class8 solid eligibility; no claim about unseen modes.')
report['source_sha256']={p.name:sha(p) for p in src.glob('*.s')}
Path('tmp/c4-live-matrix-summary.json').write_text(json.dumps(report,indent=2)+'\n');print('passed',len(report['cases']),'live cases; auxiliary class audit',report['auxiliary_audit'])
