import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-replay-playback.slave');p.add_argument('--native',action='store_true');p.add_argument('--pause',action='store_true');p.add_argument('--audio',action='store_true');p.add_argument('--delay',type=int,default=0);p.add_argument('--overlay',action='store_true');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10bb0,a.delay);s.env['WHD_ARGS']+=' CUSTOM1=1'
def signed(x):return x-65536 if x>=32768 else x
def blend(left,right,f):
 if f==0:return left
 if f==8:return right
 result=[]
 for i,(x,y) in enumerate(zip(left,right)):
  if i<7:kind=['u','u','s','a','a','a','p'][i]
  else:kind=['u','s','u','a','a','a'][(i-7)%6]
  if kind=='p':v=(((x&4095)*(8-f)+(y&4095)*f)//8)|(x&0xf000)
  elif kind=='a':
   x=signed(x);y=signed(y);d=y-x
   if d>720:d-=1440
   if d< -720:d+=1440
   v=x+d*f//8
   if v>720:v-=1440
   if v< -720:v+=1440
  else:
   if kind=='s':x=signed(x);y=signed(y)
   v=(x*(8-f)+y*f)//8
  result.append(v&65535)
 return tuple(result)
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits={};images=s.dump_banks('replay')
 for bank,b in images:
  for sig in [b'HDRPLAY1',b'HDRPMAT1']+([b'HDRAUD01'] if a.audio else [])+([b'HDRPOM01'] if a.overlay else []):
   i=b.find(sig)
   if i>=0:
    assert sig not in hits;hits[sig]=bank+i+8
    if sig==b'HDRPMAT1':math=b[i+8:i+8+1422]
    if sig==b'HDRPOM01':overlay_math=b[i+8:i+8+144]
 assert len(hits)==2+int(a.overlay)+int(a.audio)
 if a.overlay:
  cases=[(100,100),(100,101),(100,107),(100,108),(100,111),(100,420),(100,421),(0xfffffffc,3),(100,70100)]
  for i,(before,now) in enumerate(cases):
   elapsed=8 if a.native else min((now-before)&0xffffffff,65535)
   remaining=max(0,320-elapsed)
   expected=(elapsed,now,(remaining+7)//8,remaining,8 if a.native else 0)
   got=struct.unpack_from('>IIHHI',overlay_math,i*16)
   assert got==expected,(i,got,expected)
 left=[65535,0,-32768,719,-719,0,0x8fff];right=[0,65535,32767,-719,719,720,0x0123]
 angles=[(719,-719),(-719,719),(720,-720),(-720,720),(0,720),(720,0),(0,-720),(-720,0),(1439,1),(1,1439),(100,-100),(-100,100)]
 for i,(x,y) in enumerate(angles):
  left += [65535 if i%2 else 0,-32768 if i%2 else 32767,i*5000,x,x,x];right += [0 if i%2 else 65535,32767 if i%2 else -32768,65535-i*5000,y,y,y]
 left=tuple(x&65535 for x in left);right=tuple(x&65535 for x in right)
 for f in range(9):assert struct.unpack_from('>79H',math,f*158)==blend(left,right,f),f
 state=hits[b'HDRPLAY1'];frame=state+32;ringbase=a4-0x4e6e
 for bank,b in images:
  if bank<=ringbase and ringbase+14220<=bank+len(b):ring=b[ringbase-bank:ringbase-bank+14220]
 assert len(ring)==14220
 (out/'frames.bin').write_bytes(b'');(out/'states.bin').write_bytes(b'')
 lines=[f'gdb break *{base+0x10bbe:#x}',f'break *{base+0x10e68:#x}',f'break *{base+0xa36:#x}',f'break *{base+0x10dd8:#x}','set $rng=0','set $n=0','set $done=0','while $done==0 && $n<1000','continue',f'if $pc=={base+0xa36:#x}','set $rng=$rng+1','end',f'if $pc=={base+0x10dd8:#x}',f'printf "EFFECT %d %d %u\\n",*(short*){state+20:#x},*(short*){state+22:#x},*(unsigned int*)($a5-8)','end',f'if $pc=={base+0x10bbe:#x}',f'append binary memory {s.rel}/states.bin {state:#x} {state+20:#x}',f'append binary memory {s.rel}/frames.bin {frame:#x} {frame+158:#x}','set $n=$n+1','end',f'if $pc=={base+0x10e68:#x}','set $done=1','end','end',f'dump binary memory {s.rel}/exit.bin {state:#x} {state+20:#x}','printf "END %d %d\\n",$n,$done','printf "RNG %d\\n",$rng','delete']
 # Retain three visible replay frames for the requested A500/020 visual inspection.
 at=lines.index('set $n=$n+1')+1
 snapshots=[]
 for shot in [1,10,30]:
  snapshots += [f'if $n=={shot}',f'set $front=*(unsigned int*){a4-0x6a0e:#x}',f'set $pal=*(unsigned int*){a4-0x7036:#x}',f'dump binary memory {s.rel}/view-{shot}.bin $front $front+32000',f'dump binary memory {s.rel}/palette-{shot}.bin $pal $pal+32','end']
 lines[at:at]=snapshots
 if a.audio:
  audio=hits[b'HDRAUD01']
  lines.insert(1,f'break *{base+0x8ae:#x}')
  at=lines.index('continue')+1
  lines[at:at]=[f'if $pc=={base+0x8ae:#x}',f'printf "SOUND %u %d\\n",*(unsigned short*)($sp+4),*(short*){audio:#x}','end']
 if a.pause:
  lines.insert(1,f'break *{base+0x3f2:#x}')
  at=lines.index('set $n=0');lines[at:at]=['set $paused=0']
  at=lines.index('continue')+1;lines[at:at]=[f'if $pc=={base+0x3f2:#x}',f'if *(unsigned char*){state+18:#x} != 0','set $paused=$paused+1',f'printf "PAUSED %u\\n",*(unsigned int*){state:#x}','end','end']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply);n,done=map(int,re.search(r'END (\d+) (\d+)',reply).groups());assert done and n
 raw=(out/'states.bin').read_bytes();frames=(out/'frames.bin').read_bytes();assert len(raw)==n*20 and len(frames)==n*158
 fractional=0;ages=[]
 for i in range(n):
  wall,start,age,oldest,count,pad=struct.unpack_from('>4I2H',raw,i*20);idx=age//8;f=age%8;assert idx<count
  if not a.native:assert wall>=start+age
  else:assert age==i*8
  first=((oldest-ringbase)//158+idx)%90;second=(first+1)%90 if idx+1<count else first
  expected=blend(struct.unpack_from('>79H',ring,first*158),struct.unpack_from('>79H',ring,second*158),f)
  got=struct.unpack_from('>79H',frames,i*158);assert got==expected,(i,[j for j in range(79) if got[j]!=expected[j]])
  ages.append(age);fractional+=bool(f)
 wall,start,age,oldest,count,pad=struct.unpack('>4I2H',(out/'exit.bin').read_bytes());assert age>=count*8,(age,count)
 assert age-count*8 < age-ages[-1] or age==count*8
 rng=int(re.search(r'RNG (\d+)',reply).group(1));assert rng==2*min(count,26),(rng,count)
 effects=re.findall(r'EFFECT (-?\d+) (-?\d+) (\d+)',reply)
 for last,target,ptr in effects:
  last,target,ptr=map(int,(last,target,ptr));assert last==target and 0<=target<26
  index=target//3;index=index if index<=5 else 10-index
  assert ptr==a4-0x5160+index*16
 assert effects
 paused=list(map(int,re.findall(r'PAUSED (\d+)',reply)))
 if a.pause:assert 38<=len(paused)<=40 and len(set(paused))==1,paused
 end_images=s.dump_banks('end')
 def readmem(addr,n):
  for bank,b in end_images:
   if bank<=addr and addr+n<=bank+len(b):return b[addr-bank:addr-bank+n]
  raise AssertionError(hex(addr))
 if a.audio:
  last,pad,requests=struct.unpack('>HHI',readmem(audio,8))
  sounds=[(int(x),int(y)) for x,y in re.findall(r'SOUND (\d+) (-?\d+)',reply)]
  expected=[i for i in range(count) if ring[(((oldest-ringbase)//158+i)%90)*158+12]&128]
  actual=[i for sound,i in sounds if sound==4]
  assert actual==expected,(actual,expected)
  assert last==count-1 and requests==len(expected),(last,count,requests)
  (out/'audio-check.json').write_text(json.dumps(dict(passed=True,history_skid_records=expected,skid_requests=actual,other_requests=[x for x in sounds if x[0]!=4]),indent=2)+'\n')
 front=struct.unpack('>I',readmem(a4-0x6a0e,4))[0];palette=struct.unpack('>I',readmem(a4-0x7036,4))[0]
 planes=readmem(front,32000);colors=struct.unpack('>16H',readmem(palette,32))
 from PIL import Image
 im=Image.new('RGB',(320,200));pixels=im.load()
 for y in range(200):
  for x in range(320):
   index=sum(((planes[k*8000+y*40+x//8]>>(7-x%8))&1)<<k for k in range(4));c=colors[index];pixels[x,y]=tuple(((c>>shift)&15)*17 for shift in [8,4,0])
 im.resize((640,400),Image.Resampling.NEAREST).save(out/'replay-end.png')
 for shot in [1,10,30]:
  if not (out/f'view-{shot}.bin').exists():continue
  planes=(out/f'view-{shot}.bin').read_bytes();colors=struct.unpack('>16H',(out/f'palette-{shot}.bin').read_bytes())
  for y in range(200):
   for x in range(320):
    index=sum(((planes[k*8000+y*40+x//8]>>(7-x%8))&1)<<k for k in range(4));c=colors[index];pixels[x,y]=tuple(((c>>shift)&15)*17 for shift in [8,4,0])
  im.resize((640,400),Image.Resampling.NEAREST).save(out/f'replay-{shot}.png')
 r=dict(passed=True,private_overlay_cases=9 if a.overlay else 0,private_record_cases=9,private_words=711,paused_fields=len(paused),rng_calls=rng,effect_frames=len(effects),frames=n,fractional_frames=fractional,history_entries=count,target_fields=count*8,exit_age=age,overshoot_fields=age-count*8,ages=ages);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');(out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n');print({k:v for k,v in r.items() if k!='ages'})
finally:s.close()
