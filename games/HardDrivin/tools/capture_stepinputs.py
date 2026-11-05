"""Controlled constant input experiment; input globals only, no dynamics injection."""
import argparse,json,os,re,shutil,subprocess,struct
from capture_demo import ROOT,command,sha
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('name');p.add_argument('--slave',default='s3-stepinput.slave');p.add_argument('--custom1',type=int,default=0);p.add_argument('--steps',type=int,default=108);p.add_argument('--world',action='store_true');p.add_argument('--delay',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);slave=ROOT/'tmp/build'/a.slave;shutil.copyfile(slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 print(a.name,flush=True);s.boot();base=s.layout['code_base'];a4=s.layout['a4'];regions=s.layout['regions'][1:];size=sum(r['size'] for r in regions)
 world=[]
 if a.world:
  banks=s.dump_banks('world-layout')
  def mem(addr,n):
   for b,x in banks:
    if b<=addr and addr+n<=b+len(x):return x[addr-b:addr-b+n]
   raise AssertionError((addr,n))
  def g(off,fmt):return struct.unpack('>'+fmt,mem(a4+off-65536,struct.calcsize('>'+fmt)))[0]
  count=g(0xaf04,'H');ptr=g(0xaf06,'I');assert 0<count<100
  world.append(dict(name='traffic',base=ptr,size=count*46,count=count,stride=46,pointer_global=0xaf06,count_global=0xaf04))
  for i in range(count):
   actor=struct.unpack('>I',mem(ptr+i*46+8,4))[0]
   world.append(dict(name='actor'+str(i),base=actor,size=44,count=1,stride=44))
  for name,po,co in [('main_objects',0x9962,0x9966),('aux_objects',0x9968,0x996c)]:
   count=g(co,'H');ptr=g(po,'I');assert 0<count<500
   world.append(dict(name=name,base=ptr,size=count*56,count=count,stride=56,pointer_global=po,count_global=co))
 for k in ['physics','controls']+(['world'] if a.world else []):(out/(k+'.bin')).write_bytes(b'')
 lines=[f'gdb break *{base+0x7c32:#x}',f'break *{base+0xcdb0:#x}',f'break *{base+0x3f2:#x}','set $s3n=0','set $s3f=0',f'while $s3n < {a.steps}','continue',f'if $pc == {base+0x3f2:#x}','set $s3f=$s3f+1','end',f'if $pc == {base+0x7c32:#x}']
 lines += [f'append binary memory {s.rel}/controls.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in regions]
 lines += ['end',f'if $pc == {base+0xcdb0:#x}','printf "S3STEP %d %d\\n",$s3n,$s3f']
 lines += [f'append binary memory {s.rel}/physics.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in regions]
 lines += [f'append binary memory {s.rel}/world.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in world]
 lines += ['set $s3n=$s3n+1','end','end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 events=[dict(step=int(i),field=int(f)) for i,f in re.findall(r'^S3STEP (\d+) (\d+)$',reply,re.M)];assert len(events)==a.steps
 meta=dict(s.metadata,snapshot_size=size,world_regions=world,world_snapshot_size=sum(r['size'] for r in world),events=events,input='Compiled input diagnostic; mode and coordinates depend on build flags. Input globals are retained at controls entry, before per-pass reassertion. No pose/velocity/clock/RNG writes.');(out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
 for k in ['physics','controls']+(['world'] if a.world else []):
  path=out/(k+'.bin');assert path.stat().st_size%(sum(r['size'] for r in world) if k=='world' else size)==0;(out/(k+'.sha256')).write_text(sha(path)+'\n');subprocess.run(['zstd','-q','-3',str(path)],check=True);path.unlink()
 print(events[-1],flush=True)
finally:s.close()
