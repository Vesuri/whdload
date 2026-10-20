#!/usr/bin/env python3
"""Native OCS D3 construction, selective restoration and input contracts."""
from runtime_buffers import load as load_slave
import argparse,json,struct
from pathlib import Path
from ocs_clock_check import machine,SLAVE
from ocs_display_check import Native,CODE,DATA,word,long
from ocs_reconstruct import ROOT,new_output,require

def setup(build,model):
 c,sy=machine(build,model)
 c.write(SLAVE+sy['game_base'],long(CODE));c.write(SLAVE+sy['ocs_game_a4'],long(DATA+0x7ffe))
 c.write(CODE+0x793e,word(0x4e71))
 def put(n,v,size=2):c.write(SLAVE+sy[n],word(v) if size==2 else long(v))
 def call(n):
  try:c.run(SLAVE-CODE+sy[n])
  except Exception:
   print(n,hex(c.reg(18)),[hex(c.reg(i)) for i in range(1,17)]);raise
 return c,sy,put,call

def load_scene(c,sy,build):
 meta=json.loads((ROOT/'tmp/p13d2-final-on/result.json').read_text())
 raw=bytearray((ROOT/'tmp/p13d2-final-on/fire-h1.bin').read_bytes())
 for off in range(0,len(raw)-3,2):
  val=int.from_bytes(raw[off:off+4],'big')
  for old,new,size in zip(meta['hunks'],(CODE,DATA,0x150000,0x160000),(0x358c8,0xf5b8,4,0x1d94)):
   if old<=val<old+size:raw[off:off+4]=long(new+val-old);break
 c.write(DATA,bytes(raw))
 payload=c.read(SLAVE,len((build/'WingCommander.Slave').read_bytes())-36)
 c.write(0x200000,(ROOT/'tmp/p13d2-final-on/fire-fast.bin').read_bytes())
 c.write(SLAVE,payload)

def poses(build,model):
 c,sy,put,call=setup(build,model)
 try:
  load_scene(c,sy,build)
  c.write(DATA+0x3870,word(0));c.write(DATA+0xafc,word(0))
  c.write(DATA+0x8e8c,word(12));c.write(DATA+0x8cf2,word(-1));c.write(DATA+0x8c54,word(-1))
  put('ocs_clock_active',1);put('ocs_clock_hz',50,4)
  call('timing_scene_snapshot');call('timing_scene_snapshot')
  c.write(DATA+0x77fe,long(100));put('ocs_clock_state',100,4);put('ocs_prediction_cost',0,4)
  c.write(DATA+0x5292,word(0x1234))
  before=c.read(DATA,0xf5b8)
  call('timing_scene_begin');shown=c.read(DATA,0xf5b8)
  call('timing_scene_end');require(c.read(DATA,0xf5b8)==before,'pose restoration')
  # Geometry mutates additional OCS scratch outside the shared pose records.
  call('timing_scene_begin');c.run(0x290fa);call('timing_scene_end')
  changes=[hex(i) for i,(x,y) in enumerate(zip(before,c.read(DATA,0xf5b8))) if x!=y]
  require(not changes,'geometry restoration '+str(changes))
  return dict(staging_changed=shown!=before,geometry_leaks=changes)
 finally:c.close()

def projectiles(build,model):
 results=[]
 for shooter in (0,1,9):
  for weapon in (*range(24,34),48):
   c,sy,put,call=setup(build,model)
   try:
    load_scene(c,sy,build)
    c.write(DATA+0x3870,word(0));c.write(DATA+0xafc,word(0))
    c.write(DATA+0x8e8c+4,bytes(118))
    for slot in (0,1,9):
     c.write(DATA+0x8e8c+slot*2,word(12));c.write(DATA+0x8cf2+slot*2,word(-1));c.write(DATA+0x8c54+slot*2,word(-1))
    for other in (1,9):
     for off in (0x8928,0x94fa,0x98d6,0xaa3e,0xad3e):c.write(DATA+off+12*other,c.read(DATA+off,12))
     c.write(DATA+0x9edc+42*other,c.read(DATA+0x9edc,42))
    c.write(DATA+0x9edc+42*shooter+2,word(weapon));c.write(DATA+0x8cd4+2*shooter,word(100))
    c.write(CODE+0x146ce,word(0x4e75))
    put('ocs_clock_active',1);call('timing_scene_snapshot');call('timing_scene_snapshot')
    entry,args=(0xbf5a,struct.pack('>hhI',shooter,400,DATA+0x8928)) if weapon==48 else (0xc1ce,struct.pack('>hh',shooter,0))
    ref=Native(ROOT/'tmp/originals/ocs/WingCommander/data/Wing.english',model=model)
    try:
     ref.write(0x200000,c.read(0x200000,0x400000));ref.write(DATA,c.read(DATA,0xf5b8))
     ref.write(CODE+0x146ce,word(0x4e75));ref.run(entry,args);c.run(entry,args)
     require(ref.read(DATA,0xf5b8)==c.read(DATA,0xf5b8),'constructor changed native state')
     require([ref.reg(i) for i in range(1,17)]==[c.reg(i) for i in range(1,17)],'constructor registers')
    finally:ref.close()
    slot=c.reg(9)&65535
    require(slot<=60,('allocation',shooter,weapon,slot))
    kind=c.get(DATA+0x8e8c+2*slot)
    require(c.get(SLAVE+sy['projectile_types']+slot*2)==kind,('certificate',weapon,slot,kind))
    saved=c.read(SLAVE,len(load_slave((build/"WingCommander.Slave").read_bytes())));data=c.read(DATA,0xf5b8)
    if weapon==24:
     for cut in ('birth','cooldown','reuse','dead','expired','model','view','jump'):
      c.write(SLAVE,saved);c.write(DATA,data);target=slot
      if cut=='birth':c.write(SLAVE+sy['projectile_types']+2*slot,word(0))
      elif cut=='cooldown':c.write(SLAVE+sy['projectile_cooldown_valid']+shooter,b'\0');target=shooter
      elif cut=='reuse':c.run(0x9780,struct.pack('>hhh',slot,24,0))
      elif cut=='expired':c.write(DATA+0x8c54+2*slot,word(0))
      elif cut=='dead':c.write(DATA+0x8e8c+2*slot,word(0))
      elif cut=='model':c.write(DATA+0x8f84+2*slot,word(25))
      elif cut=='view':c.write(DATA+0x3870,word(1))
      elif cut=='jump':c.write(DATA+0x8928,long(0x40000000));target=0
      call('timing_scene_snapshot')
      require(c.get(SLAVE+sy['timing_scene_predictable']+target,1)==0,'stale '+cut)
     c.write(SLAVE,saved);c.write(DATA,data)
    if weapon==24:
     c.run(entry,args);second=c.reg(9)&65535
     require(second!=slot and second<=60,'second mount')
     require(c.get(SLAVE+sy['projectile_types']+2*slot)==kind and c.get(SLAVE+sy['projectile_types']+2*second)==kind,'lost simultaneous birth')
     call('timing_scene_snapshot')
     require(c.get(SLAVE+sy['timing_scene_predictable']+second,1)==1,'second mount prediction')
     c.write(SLAVE,saved);c.write(DATA,data)
    muzzle=struct.unpack('>3i',c.read(DATA+0x8928+12*slot,12))
    c.run(0x7a90,struct.pack('>h',slot))
    call('timing_scene_snapshot')
    require(c.get(SLAVE+sy['timing_scene_predictable']+slot,1)==1,('birth prediction',weapon,slot,kind))
    require(c.get(SLAVE+sy['timing_scene_predictable']+shooter,1)==1,('cooldown reset',weapon))
    c.write(DATA+0x77fe,long(100));put('ocs_clock_state',100,4);put('ocs_prediction_cost',0,4)
    before=c.read(DATA,0xf5b8);samples=[]
    for debt in (0,10,20,30,40):
     c.write(SLAVE+sy['ocs_clock_state']+4,long(debt))
     call('timing_scene_begin');samples.append(c.read(DATA+0x8928+12*slot,12).hex())
     call('timing_scene_end');require(c.read(DATA,0xf5b8)==before,'spawn restoration')
    require(len(set(samples))>1 or c.read(DATA+0x94fa+12*slot,12)==bytes(12),('stationary projectile',weapon))
    path=0
    if shooter==0 and kind==8:
     from projectile_path_check import check_path
     velocity=struct.unpack('>3i',c.read(DATA+0x94fa+12*slot,12))
     require(struct.unpack('>3i',c.read(DATA+0x8928+12*slot,12))==tuple(p+v for p,v in zip(muzzle,velocity)), 'native birth step')
     path=check_path(muzzle,velocity,
       lambda:c.run(0x7a90,word(slot)),lambda:call('timing_scene_snapshot'),
       lambda hz:put('ocs_clock_hz',hz,4),
       lambda debt:c.write(SLAVE+sy['ocs_clock_state']+4,long(debt)),
       lambda:(call('timing_scene_begin'),struct.unpack('>3i',c.read(DATA+0x8928+12*slot,12)))[1],
       lambda:call('timing_scene_end'),lambda:c.read(DATA,0xf5b8))
    results.append(dict(shooter=shooter,weapon=weapon,slot=slot,kind=kind,samples=samples,muzzle_path_samples=path))
   finally:c.close()
 return results

def geometry(build,model):
 c,sy,put,call=setup(build,model)
 try:
  load_scene(c,sy,build);before=c.read(DATA,0xf5b8)
  c.run(0x290fa);full=c.read(DATA,0xf5b8)
  c.write(DATA,before);put('ocs_input_geometry',1);c.run(0x290fa);filtered=c.read(DATA,0xf5b8)
  # Shared selective records cover native projection outputs, including OCS's
  # separate previous-range words. Compare every collidable/action slot.
  c.write(DATA,full);call('timing_scene_save_active');full_saved=c.read(SLAVE+sy['timing_scene_saved'],7680)
  c.write(DATA,filtered);call('timing_scene_save_active');partial_saved=c.read(SLAVE+sy['timing_scene_saved'],7680)
  checked=[]
  for slot in range(61):
   if int.from_bytes(before[0x8e8c+2*slot:0x8e8e+2*slot],'big')>3:
    require(full_saved[120*slot:120*(slot+1)]==partial_saved[120*slot:120*(slot+1)],'input geometry changed gameplay slot')
    checked.append(slot)
  require(checked and full!=filtered,'missing geometry filter contrast')
  return checked
 finally:c.close()

def player_rate(build,model,hz):
 rows=[]
 for fast in (0,1,2):
  c,sy,put,call=setup(build,model)
  try:
   load_scene(c,sy,build);put('ocs_clock_active',1);put('ocs_prediction_fast',fast);put('ocs_clock_hz',hz,4)
   c.write(DATA+0x3870,word(0));c.write(DATA+0xafc,word(0));c.write(DATA+0x8e8c,word(12));c.write(DATA+0x8cf2,word(-1));c.write(DATA+0x8c54,word(-1))
   before=c.read(DATA,0xf5b8)
   for tick in range(10):
    for field in range(hz//10):
     # Native nine-byte joystick ABI, hold then release left, with fire held.
     sample=long(100+tick*(hz//10)+field+1)+bytes((tick<5,0,0,0,0,0,0,0,0,0))+bytes(128)+word(0)
     if fast==2:put('ocs_acceleration_valid',0)
     c.write(SLAVE+sy['ocs_input_sample'],sample);call('ocs_prediction_field')
    # Native committed controller updates the ramp once per world interval.
    c.run(0x183e4);c.run(0x73e)
    pos=c.read(DATA+0x8928,12);put('timing_in_world',1)
    c.run(0x7a90,word(0));put('timing_in_world',0)
    require(c.read(DATA+0x8928,12)==pos,'double player translation')
   data=c.read(DATA,0xf5b8)
   rows.append(dict(position=data[0x8928:0x8934].hex(),velocity=data[0x94fa:0x9506].hex(),basis=data[0x98d6:0x98e2].hex()))
   require(data[0x8928:0x8934]!=before[0x8928:0x8934],'no field motion')
  finally:c.close()
 require(rows[0]==rows[1]==rows[2],'render/cache policy changed authoritative player')
 return rows

def player(build,model):
 return {str(hz):player_rate(build,model,hz) for hz in (50,60)}

def fractions(build,model):
 c,sy,put,call=setup(build,model)
 try:
  count=0
  for hz in (50,60):
   for value in (-2147483648,-32769,-32768,-1,0,1,32767,32768,2147483647):
    for rem in (-hz+1,0,hz-1):
     c.write(0x180000,long(rem))
     c.run(SLAVE-CODE+sy['translation_fraction'],registers={9:value&0xffffffff,16:hz,1:0x180000})
     total=value*10+rem;quot=abs(total)//hz*(-1 if total<0 else 1);remainder=total-quot*hz
     require(c.reg(9)==quot&0xffffffff and c.get(0x180000,4)==remainder&0xffffffff,'fraction boundary')
     count+=1
  return count
 finally:c.close()

def inputs(build,model):
 c,sy,put,call=setup(build,model)
 try:
  put('ocs_clock_active',1);put('ocs_clock_state',100,4)
  # Native providers are explicit device stubs here, retaining their argument ABI.
  def pad():
   sp=c.reg(8);dest=c.get(sp+6,4);c.write(dest,bytes((1,0,0,0,1,0,1,1,0)));c.return_call()
  def keys():
   dest=c.get(c.reg(8)+4,4);c.write(dest,bytes(range(128)));c.return_call()
  c.intercept(CODE+0x33f24,pad);c.intercept(CODE+0x34606,keys)
  c.write(DATA+0x780a,word(23));c.write(DATA+0x77fe,long(101));call('ocs_input_record')
  require(c.get(SLAVE+sy['ocs_input_head'])==1,'input publish')
  call('ocs_input_take');require(c.reg(9)==1,'input consume')
  sample=c.read(SLAVE+sy['ocs_input_sample'],144)
  require(sample[:4]==long(101) and sample[4:13]==bytes((1,0,0,0,1,0,1,1,0)) and sample[14:142]==bytes(range(128)) and sample[142:]==word(23),'input ABI')
  call('ocs_input_take');require(c.reg(9)==0,'duplicate sample')
  # A gap retains the previous held state but cannot replay pulses.
  c.write(DATA+0x77fe,long(104));call('ocs_input_record');put('ocs_clock_state',101,4)
  call('ocs_input_take');require(c.get(SLAVE+sy['ocs_input_sample'],4)==102 and c.get(SLAVE+sy['ocs_input_sample']+10)==0,'input gap')
  require(c.get(SLAVE+sy['ocs_input_tail'])==1,'future input consumed early')
  # Real native keyboard FIFO: replay exposes only the captured producer.
  c.write(DATA+0x7804,long(0));c.write(DATA+0x7808,word(62));c.write(DATA+0x780a,word(1))
  c.write(CODE+0x34568+62,bytes((65,66)));c.write(CODE+0x34568,bytes((67,)))
  put('ocs_input_replay',1);c.write(SLAVE+sy['ocs_input_sample']+142,word(0))
  popped=[]
  for _ in range(3):call('ocs_input_command');popped.append(c.reg(9)&65535)
  require(popped==[65,66,65535] and c.get(DATA+0x7808)==0,'command replay boundary')
  c.write(SLAVE+sy['ocs_input_sample']+142,word(1));call('ocs_input_command');require(c.reg(9)==67,'lost command')
  call('ocs_input_command');require(c.reg(9)&65535==65535,'duplicate command')
  # Full producer must not overwrite unread records.
  put('ocs_input_head',0);put('ocs_input_tail',1);prior=c.read(SLAVE+sy['ocs_input_ring'],9216)
  call('ocs_input_record');require(prior==c.read(SLAVE+sy['ocs_input_ring'],9216) and c.get(SLAVE+sy['ocs_input_overflows'],4)==1,'ring overwrite')
  call('ocs_prediction_rebase');require(c.get(SLAVE+sy['ocs_input_tail'])==0 and c.get(SLAVE+sy['ocs_input_replay'])==0,'input rebase')
  for hz in (50,60):
   put('ocs_clock_hz',hz,4)
   for pending in (0,1):
    put('ocs_pending',pending);put('ocs_prediction_cost',2,4);put('ocs_clock_state',100,4);c.write(DATA+0x77fe,long(100))
    c.write(SLAVE+sy['ocs_clock_state']+4,long(hz-10));call('release_predict')
    require(c.reg(15)<=hz+20 and c.get(SLAVE+sy['release_render_time'],4)==103+pending,'forecast bound')
  return dict(record_abi=True,once=True,gap=True,overflow=True,rebase=True,publication_bound=True)
 finally:c.close()

def main():
 p=argparse.ArgumentParser();p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 results={str(m):dict(poses=poses(a.build,m),projectiles=projectiles(a.build,m),inputs=inputs(a.build,m),player=player(a.build,m),fractions=fractions(a.build,m),geometry=geometry(a.build,m)) for m in (1,2)}
 (out/'report.json').write_text(json.dumps(dict(passed=True,models=results,build_sha256=json.loads((a.build/'build.json').read_text())['sha256']),indent=2)+'\n');print('D3 pose and constructor checks pass')
if __name__=='__main__':main()
