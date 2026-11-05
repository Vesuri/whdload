import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-ghost-play.slave');p.add_argument('--visits',type=int,default=180);p.add_argument('--delay',type=int,default=0);p.add_argument('--until-finish',action='store_true');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x11664,a.delay);s.env['WHD_ARGS']+=' CUSTOM1=1'
def signed(x):return (x+32768)%65536-32768
def trunc(x,d):return (-1 if x<0 else 1)*(abs(x)//d)
def pose(records,position):
 index,phase=divmod(position,48);left=struct.unpack_from('>6H',records,index*12);right=struct.unpack_from('>6H',records,min(298,index+1)*12);values=[]
 for j,(x,y) in enumerate(zip(left,right)):
  if j<2:z=(x*(48-phase)+y*phase)//48
  elif j==2:z=trunc(signed(x)*(48-phase),48)+trunc(signed(y)*phase,48)
  else:
   x=signed(x);y=signed(y)
   if j==3 and abs(x-y)>720:x+=1440 if x<0 else -1440
   z=trunc(x*(48-phase)+y*phase,48)
  values.append(z&65535)
 return [values[i] for i in [0,2,1,4,3,5]]
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];images=s.dump_banks('ghost-play');hits={}
 for bank,b in images:
  for sig in [b'HDGHPLY1',b'HDDISP01',b'HDSCAL01']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 def read(addr,n):
  for bank,b in images:
   if bank<=addr and addr+n<=bank+len(b):return b[addr-bank:addr-bank+n]
  raise ValueError(hex(addr))
 def gaddr(o):return a4+o-65536
 def mem(addr,t='unsigned int'):return f'*({t}*){addr:#x}'
 def g(o,t='unsigned short'):return mem(gaddr(o),t)
 arena=struct.unpack('>I',read(gaddr(0x9640),4))[0];actor=struct.unpack('>I',read(gaddr(0x997e),4))[0];records=read(arena,3600);(out/'history.bin').write_bytes(records);finish=struct.unpack('>3H',read(gaddr(0xaf20),6));gp=hits[b'HDGHPLY1'];ds=hits[b'HDDISP01'];scalar=hits[b'HDSCAL01']-10
 expr=[mem(ds+8),mem(scalar,'unsigned short'),g(0xadde,'unsigned char'),g(0xe928,'unsigned int')+f'-{arena}',g(0xe92c,'unsigned char')]+[g(o,'unsigned char') for o in [0x979c,0x95ed,0xe92d,0xaf32,0xe92e,0xe92f]]+[mem(gp+i) for i in [0,4,8,12]]+[mem(gp+16,'unsigned char'),mem(gp+17,'unsigned char'),mem(gp+20)]+[mem(actor+i,'unsigned short') for i in [8,10,12,14,16,18]]
 lines=[f'gdb break *{base+0x8c84:#x}',f'break *{base+0x116b0:#x}',f'break *{base+0x118a4:#x}','set $n=0','set $done=0',f'while $n<{a.visits} && $done==0','continue',f'if $pc=={base+0x118a4:#x}','set $done=1','end']
 for tag,off in [('I',0x8c84),('O',0x116b0)]:
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%u']*len(expr))+'\\n",'+','.join(expr)]
  if tag=='O':
   lines+=['set $n=$n+1']
   if a.until_finish:lines += [f'if {g(0xe92d,"unsigned char")} != 0','set $done=2','end']
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 events=[(m[1],list(map(int,m[2].split()))) for m in re.finditer(r'^([IO]) ((?:\d+ ?)+)$',reply,re.M)];assert len(events)%2==0
 position=0;rendered=0;checks=0;eligible=0;fractional=0;extra=0;finish_hits=0
 def hit(p):
  # Preserve the native ABS.W edge at -32768 as well as strict thresholds.
  d=[signed(abs(signed(x-y))) for x,y in zip(p[:3],finish)]
  return all(x<lim for x,lim in zip(d,[200,40,200]))
 for ix in range(0,len(events),2):
  (ti,b),(to,v)=events[ix:ix+2];assert(ti,to)==('I','O');step,n,gate=b[:3]
  if gate<4:
   assert b[3:]==v[3:],(ix,b,v);continue
  eligible+=1;expected=pose(records,position);assert v[18:]==expected,(ix,position,v[18:],expected)
  finished=bool(b[5]);nc=0
  for q in range((rendered//8+1)*8,position,8):
   if finished:break
   nc+=1;finished=hit(pose(records,q))
  nc+=1;finished=finished or hit(expected);checks+=nc;extra+=nc-1
  if finished and not b[5]:
   finish_hits+=1;assert v[5:11]==[255,0,255,60,7,0],(ix,b,v)
  else:assert v[5:11]==b[5:11],(ix,b,v)
  rendered=position;fractional+=position%8!=0;position=min(298*48,position+n)
  assert v[3:5]==[position//48*12,(position%48)//8],(ix,b,v,position)
  assert v[11:]==[position,rendered,step,arena+position//48*12,(position%48)//8,255,checks]+expected,(ix,b,v,position,rendered,checks)
 result=dict(passed=True,profile=a.profile,visits=len(events)//2,eligible_visits=eligible,position_fields=position,fractional_poses=fractional,extra_finish_checks=extra,finish_events=finish_hits)
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
