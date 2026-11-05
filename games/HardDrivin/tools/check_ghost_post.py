import argparse,ast,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session,re_register
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a1200-020');p.add_argument('--slave',default='s4-ghost-post.slave');p.add_argument('--pause',action='store_true');p.add_argument('--delay',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
# Shared independent rational pose model, without starting its capture driver.
model=ast.parse((ROOT/'tools/check_ghost_playback.py').read_text());scope={'struct':struct};exec(compile(ast.Module(body=[n for n in model.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'pose-model','exec'),scope);pose=scope['pose'];signed=scope['signed'];trunc=scope['trunc']
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x1111c,a.delay);s.env['WHD_ARGS']+=' CUSTOM1=1';s.env['SERVE_WAIT']='600'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];a5=re_register(command('gdb info registers a5'),'a5');images=s.dump_banks('ghost-post');hits={}
 for bank,b in images:
  for sig in [b'HDGHPOST',b'HDRPLAY1',b'HDPRES01']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 def read(addr,n):
  for bank,b in images:
   if bank<=addr and addr+n<=bank+len(b):return b[addr-bank:addr-bank+n]
  raise ValueError(hex(addr))
 def u32(addr):return struct.unpack('>I',read(addr,4))[0]
 def ga(o):return a4+o-65536
 def mem(addr,t='unsigned int'):return f'*({t}*){addr:#x}'
 def g(o,t='unsigned short'):return mem(ga(o),t)
 pg=hits[b'HDGHPOST'];rp=hits[b'HDRPLAY1'];pr=hits[b'HDPRES01'];arenas=[u32(ga(o)) for o in [0x9644,0x9640]];actors=[u32(ga(o)) for o in [0x997a,0x997e]];histories=[read(x,3600) for x in arenas];saved=[u32(a5-4),u32(a5-8)]
 for name,b in zip(['player','opponent'],histories):(out/(name+'-history.bin')).write_bytes(b)
 (out/'post-inputs.json').write_text(json.dumps(dict(arenas=arenas,actors=actors,saved=saved,a5=a5),indent=2)+'\n')
 # Frame: wall, start, age, delta, duration, starts, phases, active/first/sources,
 # both cursors, both public phases, both actor poses, overlay and its field state.
 frame=[mem(rp)]+[mem(pg+i) for i in [0,4,12,16,20,24]]+[mem(pg+i,'unsigned short') for i in [28,30]]+[mem(pg+i,'unsigned char') for i in [32,33,34]]+[g(o,'unsigned int') for o in [0xe924,0xe928]]+[g(o,'unsigned char') for o in [0xe922,0xe92c]]+[mem(actor+i,'unsigned short') for actor in actors for i in [8,10,12,14,16,18]]+[g(0xaf32,'unsigned char'),mem(pr,'unsigned short'),mem(pr+2,'unsigned short'),mem(pg+36)]
 pitch=[mem(pg+4),mem(pg+12),mem(pg+33,'unsigned char'),mem(a5-20,'unsigned short'),mem(a5-22,'unsigned short'),g(0x9602)]
 end=[mem(rp),mem(pg),mem(pg+4),mem(pg+16),mem(pg+32,'unsigned char')]+[g(o,'unsigned int') for o in [0xe924,0xe928]]+[g(o,'unsigned char') for o in [0xe922,0xe92c]]
 lines=[f'gdb break *{base+0x11152:#x}',f'break *{base+0x111a0:#x}',f'break *{base+0x111b6:#x}',f'break *{base+0x1126e:#x}','set $done=0','while $done==0','continue']
 if a.pause:
  lines.insert(4,f'break *{base+0x3f2:#x}')
  lines += [f'if $pc=={base+0x3f2:#x}',f'if {mem(rp+18,"unsigned char")} != 0','printf "PAUSE %u\\n",'+mem(rp),'end','end']
 for tag,off,expr in [('F',0x11152,frame),('B',0x111a0,pitch),('A',0x111b6,pitch),('E',0x1126e,end)]:
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%u']*len(expr))+'\\n",'+','.join(expr)]
  if tag=='E':lines+=['set $done=1']
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 events=[(m[1],list(map(int,m[2].split()))) for m in re.finditer(r'^([FBAE]) ((?:\d+ ?)+)$',reply,re.M)];frames=[];fractional=0;first=True;previous_age=0;pending=None;ending=None
 for tag,v in events:
  if tag=='F':
   wall,start,age,delta,duration,player,opponent,pp,op,active,isfirst,sources,pc,oc,phasep,phaseo=v[:16]
   assert active==255 and age<duration and age<=wall-start and delta==age-previous_age
   assert bool(isfirst)==first and sources==3,(tag,v)
   assert duration==max(0,min((saved[0]-12-player)*4-pp,(saved[1]-12-opponent)*4-op))
   for j,(cursor,initial,phase,published) in enumerate(zip([pc,oc],[player,opponent],[pp,op],[phasep,phaseo])):
    absolute=(initial-arenas[j])*4+phase+age
    assert cursor==arenas[j]+absolute//48*12 and published==(absolute%48)//8
    expected=pose(histories[j],absolute);assert v[16+j*6:22+j*6]==expected,(len(frames),j,absolute,v[16+j*6:22+j*6],expected)
   previous_age=age;fractional+=(age+pp)%8!=0 or (age+op)%8!=0;frames.append(v)
  elif tag=='B':pending=v
  elif tag=='A':
   assert pending is not None;age,delta,isfirst,dist,prev,pitch_before=pending;expected=pitch_before
   if isfirst or delta:expected=(800-trunc(signed(dist-prev)*48,8 if isfirst else delta))&65535
   assert v[:2]==[age,delta] and v[2]==0 and v[3:5]==[dist,prev] and v[5]==expected,(pending,v,expected)
   pending=None;first=False
  else:ending=v
 assert frames and pending is None and ending is not None
 wall,start,age,duration,active,pc,oc,pp,op=ending;assert age==duration and active==0 and [pc,oc]==saved
 assert wall-start>=duration and frames[0][2]==0
 firstrow=frames[0]
 assert [pp,op]==[((firstrow[7]+duration)%48)//8,((firstrow[8]+duration)%48)//8]
 pauses=[int(m[1]) for m in re.finditer(r'^PAUSE (\d+)$',reply,re.M)]
 if a.pause:assert len(pauses)==40 and len(set(pauses))==1,pauses
 else:assert not pauses
 result=dict(passed=True,pause_fields=len(pauses),profile=a.profile,frames=len(frames),duration_fields=duration,elapsed_fields=wall-start,last_pose_age=frames[-1][2],fractional_pose_frames=fractional,pitch_checks=len(frames),phase_sources=firstrow[11],initial_phases=firstrow[7:9],restored_cursors=True)
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
