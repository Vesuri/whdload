import argparse,json,os,re,shutil
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-gameover.slave');p.add_argument('--native',action='store_true');p.add_argument('--pause',action='store_true');p.add_argument('--args',default='CUSTOM1=1');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10f62);s.env['WHD_ARGS']+=' '+a.args
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits={}
 for bank,b in s.dump_banks('timeline'):
  for sig in [b'HDTMLIN1',b'HDRPLAY1',b'HDPRES01']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 assert len(hits)==3;tl=hits[b'HDTMLIN1'];rp=hits[b'HDRPLAY1'];pres=hits[b'HDPRES01']
 def mem(addr,t='unsigned int'):return f'*({t}*){addr:#x}'
 lines=[f'gdb break *{base+0x10f72:#x}',f'break *{base+0x10ff0:#x}',f'break *{base+0x10ff4:#x}',f'break *{base+0x3f2:#x}',f'break *{base+0x10246:#x}',f'break *{base+0x1024e:#x}','set $done=0','set $paused=0','while $done==0','continue',f'if $pc=={base+0x3f2:#x}',f'if {mem(rp+18,"unsigned char")}!=0','set $paused=$paused+1','printf "PAUSE %u\\n",'+mem(rp),'end','end']
 for tag,off in [('OI',0x10246),('OO',0x1024e)]:
  expr=[mem(rp),mem(tl+8),mem(pres,'unsigned short'),mem(pres+2,'unsigned short'),mem(a4-0x50ce,'unsigned char')]
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' %u %u %u %u %u\\n",'+','.join(expr),'end']
 for tag,off in [('FRAME',0x10f72),('END',0x10ff0),('EXIT',0x10ff4)]:
  expr=[mem(rp),mem(tl),mem(tl+4),mem(tl+12,'unsigned char'),'*(unsigned short*)($a5-2)']
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' %u %u %u %u %u\\n",'+','.join(expr)]
  if tag=='EXIT':lines+=['set $done=1']
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 events=[]
 for line in reply.splitlines():
  m=re.fullmatch(r'(FRAME|END|EXIT) (\d+) (\d+) (\d+) (\d+) (\d+)',line)
  if m:events.append([m[1],*map(int,m.groups()[1:])])
 overlay=[];before=None
 for m in re.finditer(r'^(OI|OO) (\d+) (\d+) (\d+) (\d+) (\d+)$',reply,re.M):
  tag=m[1];v=list(map(int,m.groups()[1:]))
  if tag=='OI':before=v;continue
  assert before is not None
  wall,last,rem,prev,count=before
  due=8 if a.native else min(65535,v[1]-last)
  expected=max(0,(rem if prev==count else count*8)-due)
  assert v[2:]==[expected,(expected+7)//8,(expected+7)//8],(before,v,due)
  overlay.append([before,v]);before=None
 pauses=[int(m[1]) for m in re.finditer(r'^PAUSE (\d+)$',reply,re.M)]
 if a.pause:assert len(pauses)==40 and len(set(pauses))==1,pauses
 else:assert not pauses
 frames=[v for v in events if v[0]=='FRAME'];ends=[v for v in events if v[0]=='END'];exits=[v for v in events if v[0]=='EXIT'];assert len(exits)==1 and len(frames)==len(ends)>0
 for i,(fr,en) in enumerate(zip(frames,ends)):
  assert fr[4]==255
  for v in (fr,en):
   if not a.native:assert v[3]<=v[1]-v[2] and v[5]==(35 if v[3]>=280 else min(20,v[3]//2)),v
  if a.native:assert fr[5]==i and en[5]==i+1
  else:assert (en[3]>=280)==(i==len(ends)-1),en
 assert exits[0][4]==0
 if a.native:assert len(frames)==35
 r=dict(passed=True,profile=a.profile,native=a.native,frames=len(frames),pause_fields=len(pauses),overlay_updates=len(overlay),elapsed_fields=exits[0][1]-exits[0][2],last_frame_start_fields=frames[-1][1]-frames[-1][2],target_fields=None if a.native else 280,events=events);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='events'})
finally:s.close()
