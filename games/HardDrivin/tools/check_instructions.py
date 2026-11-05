import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session,re_register
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a1200-020');p.add_argument('--slave',default='s4-instructions-hold.slave');p.add_argument('--pause',action='store_true');p.add_argument('--native',action='store_true');p.add_argument('--delay',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x114b2,a.delay);s.env['WHD_ARGS']+=' CUSTOM1=1';s.env['SERVE_WAIT']='600'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];a5=re_register(command('gdb info registers a5'),'a5');images=s.dump_banks('instruction');hits={}
 for bank,b in images:
  for sig in [b'HDINSTR1',b'HDRPLAY1']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 def m(addr,t='unsigned short'):return f'*({t}*){addr:#x}'
 def g(off,t='unsigned short'):return m(a4+off-65536,t)
 rp=hits[b'HDRPLAY1'];ins=hits.get(b'HDINSTR1');fields=[m(rp,'unsigned int'),m(a5-2)]+[g(o) for o in [0x98f6,0x98f8,0x98fa,0x994c,0x994a]]+[m(a5-i) for i in [12,14,16]]+[g(0xadde,'unsigned char'),g(0xadd7,'unsigned char'),g(0x9604,'unsigned char')]+[g(o,'unsigned int') for o in [0x98fc,0x9900,0x9904]]
 if ins:fields += [m(ins,'unsigned int'),m(ins+4,'unsigned int'),m(ins+9,'unsigned char')]
 points=[('S',0x114ca),('B',0x1157a),('C',0x1159c),('E',0x115f0)];lines=['gdb break *'+hex(base+points[0][1])]+['break *'+hex(base+o) for _,o in points[1:]]+['set $done=0','while $done==0','continue']
 if a.pause:
  lines.insert(4,f'break *{base+0x3f2:#x}')
  lines += [f'if $pc=={base+0x3f2:#x}',f'if {m(rp+18,"unsigned char")} != 0','printf "PAUSE %u\\n",'+m(rp,'unsigned int'),'end','end']
 for tag,off in points:
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%u']*len(fields))+'\\n",'+','.join(fields)]
  if tag=='E':lines+=['set $done=1']
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply);events=[(x,list(map(int,y.split()))) for x,y in re.findall(r'^([SBCE]) ((?:\d+ ?)+)$',reply,re.M)];(out/'events.json').write_text(json.dumps(events)+'\n')
 scroll=[v for t,v in events if t=='S'];camera=[v for t,v in events if t=='C'];beg=next(v for t,v in events if t=='B');end=events[-1][1];assert events[-1][0]=='E' and scroll and camera
 def signed(x):return x-65536 if x&32768 else x
 def trunc(n,d):return (abs(n)//d)*(-1 if n<0 else 1)
 for i,v in enumerate(scroll):
  age=i*8 if a.native else v[17]
  assert v[1]==18+min(age,232)*3//8,(i,v)
 for i,v in enumerate(camera):
  age=i*8 if a.native else v[17];n=min(age+8,56)
  expected=[(beg[2+j]-trunc(signed(beg[7+j])*n,8))&65535 for j in range(3)]+[(beg[5]+n//8)&65535,(beg[6]-2*n)&65535]
  assert v[2:7]==expected,(i,v,expected)
 expected=[(beg[2+j]-7*signed(beg[7+j]))&65535 for j in range(3)]+[(beg[5]+7)&65535,(beg[6]-112)&65535]
 assert end[2:7]==expected,(end,expected)
 assert end[13:16]==[expected[0]*8,(signed(expected[1])*8)&0xffffffff,expected[2]*8]
 if not a.native:assert end[0]-end[16]>=56 and end[18]==0
 pauses=[int(x) for x in re.findall(r'^PAUSE (\d+)$',reply,re.M)]
 if a.pause:assert len(pauses)==40 and len(set(pauses))==1,pauses
 result=dict(pause_fields=len(pauses),passed=True,profile=a.profile,scroll_frames=len(scroll),camera_frames=len(camera),camera_fields=end[0]-camera[0][0],last_scroll=scroll[-1][1],native=a.native,menu_modes=sorted(set(tuple(v[10:13]) for v in camera)))
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.close()
