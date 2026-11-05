"""Compare culled intermediate preparation to native preparation at identical state."""
import argparse,json,os,re,shutil,struct
from pathlib import Path
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--pairs',type=int,default=100);p.add_argument('--existing',action='store_true');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name
if not a.existing:
 out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-scene-twin.slave',out/'slave.slave')
listing=out/'slave.lst'
if not a.existing:shutil.copyfile(ROOT/'tmp/build/s4-scene-twin.lst',listing)
symbols={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (_[A-Za-z][A-Za-z0-9_]*)(?:\s|$)',listing.read_text(errors='replace'),re.M)}
s=Session(out,'a500',out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 if a.existing:s.layout=json.loads((out/'metadata.json').read_text())['layout']
 else:s.boot()
 slave=s.layout['published']-symbols['_code_start'];a4=s.layout['a4'];before=slave+symbols['_scene_twin_before'];after=slave+symbols['_scene_twin_after']
 banks=[(0,0x80000),(0xc00000,0x180000)];size=sum(n for _,n in banks)
 if not a.existing:
  for phase in ['before','after']:(out/(phase+'.bin')).write_bytes(b'')
  lines=[f'gdb break *{before:#x}',f'break *{after:#x}','set $pairs=0',f'while $pairs<{a.pairs}','continue',f'if $pc=={before:#x}']
  for phase in ['before','after']:
   for base,n in banks:lines.append(f'append binary memory {s.rel}/{phase}.bin {base:#x} {base+n:#x}')
   if phase=='before':lines+=['else','set $pairs=$pairs+1']
  lines+=['end','end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 raw=[(out/(p+'.bin')).read_bytes() for p in ['before','after']];assert all(len(x)==a.pairs*size for x in raw)
 def mem(blob,addr,n):
  offset=0
  for base,length in banks:
   if base<=addr and addr+n<=base+length:return blob[offset+addr-base:offset+addr-base+n]
   offset+=length
  raise AssertionError(('outside banks',hex(addr),n))
 def word(b,addr):return struct.unpack('>H',mem(b,addr,2))[0]
 def long(b,addr):return struct.unpack('>I',mem(b,addr,4))[0]
 objects=near=vertices=crashes=0
 for i in range(a.pairs):
  x,y=[v[i*size:(i+1)*size] for v in raw]
  # Scene-contact flags feed terrain/vehicle physics and obstacle collision.
  for off in [0xe94a,0xe94b,0xe960]:
   addr=a4+off-0x10000;assert mem(x,addr,1)==mem(y,addr,1),(i,hex(off))
  # Player state, start/score inputs and replay write pointer must not change.
  for off,n in [(0x98f0,0x66),(0x9788,4),(0xadd4,12),(0xe91e,4)]:
   addr=a4+off-0x10000;assert mem(x,addr,n)==mem(y,addr,n),(i,hex(off))
  crashes+=bool(mem(x,a4-0x69fa,1)[0])
  for ptr_off,count_off in [(0x9962,0x9966),(0x9968,0x996c)]:
   ptr=long(x,a4+ptr_off-0x10000);count=word(x,a4+count_off-0x10000)
   assert 0<count<500
   assert ptr==long(y,a4+ptr_off-0x10000) and count==word(y,a4+count_off-0x10000)
   for j in range(count):
    obj=ptr+j*56;old=mem(x,obj,44);new=mem(y,obj,44)
    assert old==new,(i,j,hex(ptr_off),[(k,old[k],new[k]) for k in range(44) if old[k]!=new[k]])
    objects+=1
    if old[29] and old[34] and (ptr_off==0x9968 or old[30]):
     n=(word(x,obj+20)+old[22])*6
     assert 0<=n<20000
     l=mem(x,long(x,obj+44),n);r=mem(y,long(y,obj+44),n)
     assert l==r,(i,j,'near vertices');near+=1;vertices+=n//6
 counts=struct.unpack('>II',mem(raw[1][-size:],slave+symbols['_scene_counts'],8));assert sum(counts)>0
 result=dict(passed=True,pairs=a.pairs,objects=objects,near_objects=near,near_vertices=vertices,crash_pairs=crashes,culled_auxiliary=counts[0],culled_main=counts[1]);(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.close()
