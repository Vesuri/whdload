import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-attract.slave');p.add_argument('--native',action='store_true');p.add_argument('--original',action='store_true');p.add_argument('--pause',action='store_true');p.add_argument('--delay',type=int,default=0);p.add_argument('--cycle',type=int,default=1);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10844,a.delay);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4']
 for _ in range(a.cycle-1):command(f'gdb break *{base+0x10844:#x}\ncontinue\ndelete')
 images=s.dump_banks('attract');hits={}
 def read(addr,n):
  for bank,b in images:
   if bank<=addr and addr+n<=bank+len(b):return b[addr-bank:addr-bank+n]
  raise ValueError(hex(addr))
 def val(addr,fmt):return struct.unpack('>'+fmt,read(addr,struct.calcsize('>'+fmt)))[0]
 def gv(o,fmt):return val(a4+o-65536,fmt)
 for bank,b in images:
  for sig in [b'HDATTR01',b'HDRPLAY1']+([b'HDATKEY1'] if a.pause else []):
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 assert a.original or len(hits)==(3 if a.pause else 2);at=hits.get(b'HDATTR01',0);rp=hits.get(b'HDRPLAY1',0)
 initial=dict(current=gv(0x94dc,'I'),next=gv(0x94d8,'I'),phase=gv(0x94d4,'B')*8,alternate=gv(0x94d6,'B'),fork=gv(0x94d7,'B'),heading=gv(0x9946,'h'))
 page=gv(0x9584,'B')
 limits=dict(main_start=gv(0x98e0,'I'),main_end=gv(0xaf26,'I'),alt_start=gv(0x9952,'I'),alt_end=gv(0xaf2a,'I'),alt_exit=gv(0xaf0e,'I'));(out/'initial.json').write_text(json.dumps(dict(initial=initial,limits=limits),indent=2))
 def mem(addr,t='unsigned int'):return f'*({t}*){addr:#x}'
 def g(o,t='unsigned short'):return mem(a4+o-65536,t)
 offsets=[0xd8fe,0x1088c,0x10898];lines=[f'gdb break *{base+offsets[0]:#x}']+[f'break *{base+x:#x}' for x in offsets[1:]]+['set $done=0','while $done==0','continue']
 expr=[mem(rp),mem(at),mem(at+4),mem(at+8),mem(at+12,'unsigned short'),mem(at+14,'unsigned char'),g(0x94dc,'unsigned int'),g(0x94d8,'unsigned int'),g(0x94d4,'unsigned char'),g(0x94d6,'unsigned char'),g(0x94d7,'unsigned char'),'0']+[g(o,'short') for o in [0x94bc,0x94be,0x94c0,0x94c8,0x94ca,0x94cc,0x98ea,0x98ec,0x98ee,0x9944,0x9946,0x9948]]
 if a.original:expr=['0']*6+expr[6:11]+['0']+expr[12:]
 lines += [f'if $pc=={base+0xd8fe:#x}','printf "POSE '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr),'end']
 for tag,off in [('DRAW',0x1088c),('EXIT',0x10898)]:
  ex=[mem(rp),mem(at),mem(at+4),'*(unsigned short*)($a5-2)',g(0xfb54,'short')]
  if a.original:ex=['0','0','0']+ex[3:]
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' %u %u %u %u %d\\n",'+','.join(ex)]
  if tag=='EXIT':lines+=['set $done=1']
  lines+=['end']
 lines+=['end','delete',f'break *{base+0x1089e:#x}','continue','delete']
 if not a.original:lines+=['printf "DONE %u %u %u %u\\n",'+mem(at+14,'unsigned char')+','+g(0x9584,'unsigned char')+','+mem(at+8)+','+mem(at+12,'unsigned short')]
 if a.pause:lines+=['printf "PAUSED %u\\n",'+mem(hits[b'HDATKEY1'])+'-'+mem(rp)]
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 poses=[];draws=[];exits=[]
 for line in reply.splitlines():
  m=re.fullmatch(r'(POSE|DRAW|EXIT) ((?:-?\d+ ?)+)',line)
  if m:{'POSE':poses,'DRAW':draws,'EXIT':exits}[m[1]].append(list(map(int,m[2].split())))
 if not a.original:
  done=tuple(map(int,re.search(r'^DONE (\d+) (\d+) (\d+) (\d+)$',reply,re.M).groups()))
  assert done[:2]==(0,page^255),done
  if not a.native:assert done[2:]==(8000,initial['phase']),done
 paused=int(re.search(r'^PAUSED (\d+)$',reply,re.M)[1]) if a.pause else 0
 if a.pause:assert paused==40,paused
 assert poses and len(poses)==len(draws) and len(exits)==1
 def trunc(x,n):return (abs(x)//n)*(-1 if x<0 else 1)
 def word(x):return (x+32768)%65536-32768
 def h(ptr,off):return val(ptr+off,'h')
 st=initial.copy();last=0;crossings=0;fractional=0;branches=0;multiple=0;max_cross=0
 def normalize():
  global branches
  if not st['alternate']:
   if val(st['current']+19,'B')&2:
    if not st['fork']:st['next']=limits['alt_start']+20;st['alternate']=1;branches+=1
   elif st['next']>=limits['main_end']:st['next']=limits['main_start'];st['fork']^=255
  elif st['next']>=limits['alt_end']:st['next']=limits['alt_exit'];st['alternate']=0;branches+=1
 def blend_heading(phase):
  left=h(st['current'],14);right=h(st['next'],14)
  if phase<=32:return left
  if left>360 and right<0:right=word(right+1440)
  k=phase-32
  return trunc(left*(48-k)+right*k,48)
 for ix,v in enumerate(poses):
  wall,start,age,rage,phase,active,cur,nxt,nativephase,alt,fork,held,*geom=v
  if a.native:continue
  expected_age=min(age,8000);st['phase']+=expected_age-last;last=expected_age
  frame_cross=0
  while st['phase']>=80:
   normalize();st['heading']=blend_heading(72);st['current']=st['next'];st['next']+=20;st['phase']-=80;crossings+=1;frame_cross+=1
  multiple+=frame_cross>1;max_cross=max(max_cross,frame_cross)
  normalize()
  assert (rage,phase,active,cur,nxt,nativephase,alt,fork,held)==(expected_age,st['phase'],255,st['current'],st['next'],st['phase']//8,st['alternate'],st['fork'],0),(ix,v,st)
  delta=geom[:3];origin=geom[3:6];actual=geom[6:]
  xyz=[word(b+trunc(d*phase,80)) for d,b in zip(delta,origin)]
  pitch=trunc(h(cur,12)*(80-phase)+h(nxt,12)*phase,80);roll=trunc(h(cur,16)*(80-phase)+h(nxt,16)*phase,80)
  expected=xyz+[pitch,blend_heading(phase),roll]
  assert actual==expected,(ix,actual,expected,v)
  fractional+=phase%8!=0
 for ix,d in enumerate(draws):
  wall,start,age,count,scroll=d
  if a.native:assert count==ix and scroll==199-ix,d
  else:assert count==min(1000,age//8) and scroll==200-min(age,8000)//8,d
 exit=exits[0];elapsed=exit[0]-exit[1]
 if a.native:assert len(draws)==1000 and exit[3]==1000
 else:assert elapsed>=8000 and draws[-1][2]<8000 and exit[3]==1000
 def route_pointer(ptr):
  for name in ['main','alt']:
   if limits[name+'_start']<=ptr<limits[name+'_end']:return [name,ptr-limits[name+'_start']]
  raise AssertionError(hex(ptr))
 normalized=[dict(route=[route_pointer(v[6]),route_pointer(v[7]),*v[8:11]],geometry=v[12:],scroll=d[4]) for v,d in zip(poses,draws)]
 (out/'poses.json').write_text(json.dumps(normalized)+'\n')
 result=dict(passed=True,profile=a.profile,native=a.native,cycle=a.cycle,page=page,frames=len(draws),pause_fields=paused,elapsed_fields=elapsed,last_draw_age=draws[-1][2],route_crossings=crossings,multiple_crossing_frames=multiple,max_crossings_per_frame=max_cross,branch_transitions=branches,fractional_poses=fractional)
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
