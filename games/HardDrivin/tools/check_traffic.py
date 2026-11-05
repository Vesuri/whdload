import argparse,json,os,struct,shutil
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--fields',type=int,default=8);p.add_argument('--off',action='store_true');a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=f' CUSTOM1={0 if a.off else 1}'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];banks=s.dump_banks('traffic')
 def read(addr,size):
  for b,x in banks:
   if b<=addr and addr+size<=b+len(x):return x[addr-b:addr-b+size]
  raise ValueError(hex(addr))
 count=struct.unpack('>H',read(a4+0xaf04-65536,2))[0];ptr=struct.unpack('>I',read(a4+0xaf06-65536,4))[0];route=struct.unpack('>I',read(a4+0x98e0-65536,4))[0];actors=[struct.unpack('>I',read(ptr+i*46+8,4))[0] for i in range(count)];st=None
 if not a.off:
  hits=[]
  for b,x in banks:
   i=x.find(b'HDTRAFF1')
   if i>=0:hits.append(struct.unpack_from('>II',x,i+8))
  assert len(hits)==1;st,size=hits[0];stride=46 if size==count*92 else 16;assert size in [count*16,count*92]
 names=['before','after','poses']+([] if a.off else ['state-before','state-after'])
 for name in names:(out/(name+'.bin')).write_bytes(b'')
 lines=[f'gdb break *{base+0xd40e:#x}',f'break *{base+0xd44e:#x}','set $n=0','while $n<120','continue',f'if $pc=={base+0xd40e:#x}',f'if *(unsigned char*){a4+0xaddf-65536:#x}!=0',f'append binary memory {s.rel}/before.bin {ptr:#x} {ptr+count*46:#x}']
 if st:lines+=[f'append binary memory {s.rel}/state-before.bin {st:#x} {st+count*stride:#x}']
 lines+=['end','end',f'if $pc=={base+0xd44e:#x}',f'append binary memory {s.rel}/after.bin {ptr:#x} {ptr+count*46:#x}']
 if st:lines+=[f'append binary memory {s.rel}/state-after.bin {st:#x} {st+count*stride:#x}']
 lines += [f'append binary memory {s.rel}/poses.bin {actor+8:#x} {actor+20:#x}' for actor in actors]
 lines+=['set $n=$n+1','end','end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 before=(out/'before.bin').read_bytes();after=(out/'after.bin').read_bytes();assert len(before)==len(after)==120*count*46;assert (out/'poses.bin').stat().st_size==120*count*12
 meta=dict(s.metadata,count=count,route_base=route,record_base=ptr,fields=a.fields,off=a.off,companion_stride=stride if st else None);(out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
 if st:
  sb=(out/'state-before.bin').read_bytes();sa=(out/'state-after.bin').read_bytes();errors=[];crossings=0;fractions=0
  def trunc(n,d):return abs(n)//d*(-1 if n<0 else 1)
  for i in range(120*count):
   r=before[i*46:(i+1)*46];got=after[i*46:(i+1)*46];state=sb[i*stride:(i+1)*stride];speed=struct.unpack_from('>b',r,23)[0];carry,last,old,pcarry,plast=struct.unpack_from('>hhhhh',state);phase=struct.unpack_from('>h',r,16)[0];n=8 if state[11] else a.fields;accel=r[21];target=r[22]
   if speed!=last:carry=0
   v=speed*8+carry;u=v
   if accel:
    cap=((target+accel-1)//accel)*accel*8
    if v<cap:v=min(v+accel*n,cap)
   speed=trunc(v,8);carry=v-speed*8
   if phase-plast not in [0,200,-200]:pcarry=0
   delta=(v*(8+n)-u*(8-n)+pcarry) if n else pcarry;q=trunc(delta,128) if n else 0;pcarry=delta-q*128;rawphase=phase+q;phase=rawphase
   if phase>=200:phase-=200;crossings+=1
   elif phase<0:phase+=200;crossings+=1
   expected=(speed,phase,carry,speed,u,pcarry,rawphase);actual=(struct.unpack_from('>b',got,23)[0],struct.unpack_from('>h',got,16)[0],*struct.unpack_from('>hhhhh',sa,i*stride));fractions+=carry!=0 or pcarry!=0
   if actual!=expected:errors.append(dict(update=i,expected=expected,actual=actual))
  result=dict(passed=not errors,updates=120*count,route_crossings=crossings,fractional_updates=fractions,errors=errors);(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result);assert result['passed']
 else:print(dict(reference=True,updates=120*count))
finally:s.close()
