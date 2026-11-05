import argparse,json,os,struct,shutil
from fractions import Fraction
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--fields',type=int,default=8);p.add_argument('--off',action='store_true');p.add_argument('--profile',default='a500');p.add_argument('--updates',type=int,default=120);p.add_argument('--delay',type=int,default=0);a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={0 if a.off else 1}'
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
 bounds={o:struct.unpack('>I',read(a4+o-65536,4))[0] for o in [0x98e0,0xaf26,0x9952,0xaf2a,0xaf0a,0xaf0e]}
 scalar=[]
 for b,x in banks:
  ix=x.find(b'HDSCAL01')
  if ix>=0:scalar.append(b+ix-2)
 assert len(scalar)==1
 names=['fields','before','after','poses']+([] if a.off else ['state-before','state-after'])
 for name in names:(out/(name+'.bin')).write_bytes(b'')
 lines=[f'gdb break *{base+0xd40e:#x}',f'break *{base+0xd44e:#x}','set $n=0',f'while $n<{a.updates}','continue',f'if $pc=={base+0xd40e:#x}',f'if *(unsigned char*){a4+0xaddf-65536:#x}!=0',f'append binary memory {s.rel}/before.bin {ptr:#x} {ptr+count*46:#x}']
 if st:lines += [f'append binary memory {s.rel}/state-before.bin {st:#x} {st+count*stride:#x}',f'append binary memory {s.rel}/fields.bin {scalar[0]:#x} {scalar[0]+2:#x}']
 lines+=['end','end',f'if $pc=={base+0xd44e:#x}',f'append binary memory {s.rel}/after.bin {ptr:#x} {ptr+count*46:#x}']
 if st:lines+=[f'append binary memory {s.rel}/state-after.bin {st:#x} {st+count*stride:#x}']
 lines += [f'append binary memory {s.rel}/poses.bin {actor+8:#x} {actor+20:#x}' for actor in actors]
 lines+=['set $n=$n+1','end','end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 before=(out/'before.bin').read_bytes();after=(out/'after.bin').read_bytes();assert len(before)==len(after)==a.updates*count*46;assert (out/'poses.bin').stat().st_size==a.updates*count*12
 meta=dict(s.metadata,count=count,route_base=route,record_base=ptr,fields=a.fields,off=a.off,companion_stride=stride if st else None);(out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
 if st:
  sb=(out/'state-before.bin').read_bytes();sa=(out/'state-after.bin').read_bytes();errors=[];crossings=0;fractions=0
  def trunc(n,d):return abs(n)//d*(-1 if n<0 else 1)
  ns=struct.unpack('>'+str(a.updates)+'H',(out/'fields.bin').read_bytes());wide_count=coasting=multiple=turns=0;max_cross=0
  def normalize(cur,nxt,mode,branch,direction):
   if mode:
    if nxt>=bounds[0xaf2a]:nxt=bounds[0xaf0e];mode=0
    elif nxt<bounds[0x9952]:nxt=bounds[0xaf0a];mode=0
   else:
    if nxt>=bounds[0xaf26]:nxt=bounds[0x98e0]
    if nxt<bounds[0x98e0]:nxt=bounds[0xaf26]-20
    if branch:
     if cur==bounds[0xaf0a] and direction==1:nxt=bounds[0x9952]+20;mode=branch
     if cur==bounds[0xaf0e] and direction==-1:nxt=bounds[0xaf2a]-20;mode=branch
   return nxt,mode
  for i in range(a.updates*count):
   r=before[i*46:(i+1)*46];got=after[i*46:(i+1)*46];state=sb[i*stride:(i+1)*stride];speed=struct.unpack_from('>b',r,23)[0];carry,last,old,pcarry,plast=struct.unpack_from('>hhhhh',state);micro=struct.unpack_from('>h',state,12)[0];phase=struct.unpack_from('>h',r,16)[0];n=8 if state[11] else ns[i//count];accel=r[21];target=r[22]
   assert 0<=accel<=3
   if speed!=last:carry=0
   v=speed*8+carry;u=v
   if accel:
    cap=((target+accel-1)//accel)*accel*8
    if v<cap:v=min(v+accel*n,cap)
   speed=trunc(v,8);carry=v-speed*8
   if phase-plast not in [0,200,-200]:pcarry=micro=0
   wide=n>8 or bool(micro);wide_count+=wide
   initial_phase=phase;initial_carry=6*pcarry+micro;minimum=0
   t=Fraction(-u,accel)-4 if accel else 0
   if n>8 and 0<t<n:minimum=min(0,int(Fraction(2*u*t+accel*t*t+8*accel*t,128)+Fraction(initial_carry,768)))
   turns+=minimum<0
   if n:
    if n>8 and accel and 0<v-u<accel*n:
     t=Fraction(v-u,accel);distance=u*t+Fraction(accel,2)*t*t+v*(n-t);coasting+=1
    else:distance=Fraction(n*(u+v),2)
    delta=distance/64+Fraction(v-u,16)+Fraction(6*pcarry+micro,768)
    q=int(delta);rem=(delta-q)*768;assert rem.denominator==1
    pcarry=trunc(int(rem),6);micro=int(rem)-pcarry*6
    phase+=q
   rawphase=phase;cur,nxt=struct.unpack_from('>II',r);mode=r[13];branch=r[15];direction=struct.unpack_from('>b',r,20)[0]
   if not nxt:nxt=cur+direction*20
   if not r[19]:nxt,mode=normalize(cur,nxt,mode,branch,direction)
   cross=0
   legs=[minimum,phase-initial_phase-minimum] if minimum<0 else [phase-initial_phase]
   phase=initial_phase
   for leg in legs:
    phase+=leg
    while phase>=200 or phase<0:
     if wide:nxt,mode=normalize(cur,nxt,mode,branch,direction)
     if phase>=200:phase-=200;cur=nxt;nxt+=direction*20
     else:phase+=200;nxt=cur;cur-=direction*20
     cross+=1
     if not wide:break
   crossings+=cross;max_cross=max(max_cross,cross);multiple+=cross>1
   expected=(speed,phase,carry,speed,u,pcarry,phase if wide and n else rawphase,micro,cur,nxt,mode)
   actual=(struct.unpack_from('>b',got,23)[0],struct.unpack_from('>h',got,16)[0],*struct.unpack_from('>hhhhh',sa,i*stride),struct.unpack_from('>h',sa,i*stride+12)[0],*struct.unpack_from('>II',got),got[13]);fractions+=carry!=0 or pcarry!=0 or micro!=0
   if actual!=expected:errors.append(dict(update=i,fields=n,expected=expected,actual=actual))
  result=dict(passed=not errors,updates=a.updates*count,route_crossings=crossings,max_crossings_per_update=max_cross,multiple_crossings=multiple,wide_updates=wide_count,turnaround_updates=turns,coasting_updates=coasting,fractional_updates=fractions,errors=errors);(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result);assert result['passed']
 else:print(dict(reference=True,updates=a.updates*count))
finally:s.close()
