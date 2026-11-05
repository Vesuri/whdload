"""Read-only capture/model of every fixed-field recording transaction."""
import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-record-math');p.add_argument('--existing',action='store_true');p.add_argument('--wide',action='store_true');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name
if not a.existing:
 out.mkdir(exist_ok=False)
 for ext in ['slave','lst']:shutil.copyfile(ROOT/'tmp/build'/(a.slave+'.'+ext),out/('slave.'+ext))
symbols={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (_[A-Za-z][A-Za-z0-9_]*)(?:\s|$)',(out/'slave.lst').read_text(errors='replace'),re.M)}
s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
pending=0
def words(b):return struct.unpack('>79H',b)
def signed(x):return x-65536 if x>=32768 else x
def blend(left,right,num,den):
 if num==den:return right
 result=[]
 for i,(x,y) in enumerate(zip(left,right)):
  kind=('uusaaap'[i] if i<7 else 'usuaaa'[(i-7)%6])
  if kind=='p':v=(((x&4095)*(den-num)+(y&4095)*num)//den)|(x&0xf000)
  elif kind=='a':
   x=signed(x);y=signed(y);d=y-x
   if d>720:d-=1440
   if d< -720:d+=1440
   v=x+d*num//den
   if v>720:v-=1440
   if v< -720:v+=1440
  else:
   if kind=='s':x=signed(x);y=signed(y)
   v=(x*(den-num)+y*num)//den
  result.append(v&65535)
 return tuple(result)
try:
 if a.existing:s.layout=json.loads((out/'metadata.json').read_text())['layout']
 else:s.boot()
 base=s.layout['code_base'];a4=s.layout['a4'];slave=s.layout['published']-symbols['_code_start'];rr=slave+symbols['_record_state'];data=next(r for r in s.layout['regions'] if r['name']=='data');ds=slave+symbols['_dispatch_state'];sf=slave+symbols['_time_scalar_fields'];size=348+2+4+data['size']+144
 if '_record_pending' in symbols:
  reply=command(f'gdb x/wx {slave+symbols["_record_pending"]:#x}')
  pending=int(re.findall(r':\s*(0x[0-9a-f]+)',reply)[-1],16)
 if not a.existing:
  if pending:(out/'pending.bin').write_bytes(b'')
  if '_record_previous_ptr' in symbols:(out/'pointers.bin').write_bytes(b'')
  if '_record_math_results' in symbols:command(f'gdb dump binary memory {s.rel}/math.bin {slave+symbols["_record_math_results"]:#x} {slave+symbols["_record_math_results"]+5688:#x}')
  if '_record_wrap_results' in symbols:command(f'gdb dump binary memory {s.rel}/wrap.bin {slave+symbols["_record_wrap_results"]:#x} {slave+symbols["_record_wrap_results"]+14260:#x}')
  if a.wide and '_record_wide_results' in symbols:command(f'gdb dump binary memory {s.rel}/wide.bin {slave+symbols["_record_wide_results"]:#x} {slave+symbols["_record_wide_results"]+3792:#x}')
  for n in (['left','right'] if '_record_math_results' in symbols else []):command(f'gdb dump binary memory {s.rel}/{n}.bin {slave+symbols["_replay_math_"+n]:#x} {slave+symbols["_replay_math_"+n]+158:#x}')
  (out/'samples.bin').write_bytes(b'')
  lines=[f'gdb break *{base+0xdb16:#x}',f'break *{base+0x10bb0:#x}',f'break *{base+0x89b4:#x}','set $n=0','set $done=0','set $rewinds=0','while $done==0 && $n<300','continue',f'if $pc=={base+0x89b4:#x}','set $rewinds=$rewinds+1','end',f'if $pc=={base+0xdb16:#x}']
  for start,length in [(rr,348),(sf,2),(ds+8,4),(data['base'],data['size'])]:lines.append(f'append binary memory {s.rel}/samples.bin {start:#x} {start+length:#x}')
  if pending:lines.append(f'append binary memory {s.rel}/pending.bin {pending:#x} {pending+29476:#x}')
  if '_record_previous_ptr' in symbols:
   ptr=slave+symbols['_record_previous_ptr'];lines.append(f'append binary memory {s.rel}/pointers.bin {ptr:#x} {ptr+8:#x}')
  lines+=['set $j=0','while $j<12',f'set $obj=*(unsigned int*)(*(unsigned int*){a4-0x50fa:#x}+46*$j+8)',f'append binary memory {s.rel}/samples.bin $obj+8 $obj+20','set $j=$j+1','end','set $n=$n+1','end',f'if $pc=={base+0x10bb0:#x}','set $done=1','end','end','printf "END %d %d %d\\n",$n,$done,$rewinds','delete']
  (out/'events.log').write_text(command('\n'.join(lines)))
  command(f'gdb dump binary memory {s.rel}/resolved.bin {a4-0x4e6e:#x} {a4-0x16e2:#x}')
 k=0
 if '_record_math_results' in symbols:
  left,right=[words((out/(n+'.bin')).read_bytes()) for n in ['left','right']];math=(out/'math.bin').read_bytes()
  for den in range(1,9):
   for num in range(1,den+1):
    assert words(math[k*158:(k+1)*158])==blend(left,right,num,den),('math',num,den);k+=1
  if a.wide:
   wide=(out/'wide.bin').read_bytes();pairs=[(num,den) for den in [9,15,16,255,32768,65535] for num in [1,den//2,den-1,den]]
   for j,(num,den) in enumerate(pairs):assert words(wide[j*158:(j+1)*158])==blend(left,right,num,den),('wide',num,den)
 if '_record_wrap_results' in symbols:
  wrap=(out/'wrap.bin').read_bytes();wb=slave+symbols['_record_wrap_ring'];wr=bytearray(14220)
  for j,num in enumerate(range(1,729,8)):
   pos=((88+j)%90)*158;wr[pos:pos+158]=struct.pack('>79H',*blend(left,right,num,728))
  assert wrap[36:36+14220]==wr,'private wrap ring'
  assert struct.unpack_from('>I',wrap,12)[0]==91
  assert struct.unpack_from('>H',wrap,20)[0]==7
  assert struct.unpack_from('>I',wrap,32)[0]==wb+89*158
  assert struct.unpack_from('>I',wrap,36+14220)[0]==wb+89*158
 n,done,rewinds=map(int,re.search(r'END (\d+) (\d+) (\d+)',(out/'events.log').read_text()).groups());assert done and n
 raw=(out/'samples.bin').read_bytes();assert len(raw)==size*n
 def off(g):return a4+g-0x10000-data['base']
 initial=(out/'game-data.bin').read_bytes();ring=bytearray(initial[off(0xb192):off(0xe91e)]);write=struct.unpack_from('>I',initial,off(0xe91e))[0];ringbase=a4-0x4e6e
 phase=age=emitted=replaced=0;last_stamp=None;current=(0,)*79;fractional=duplicates=gaps=multiple=0;maximum=0;multi_replacements=0
 for i in range(n):
  b=raw[i*size:(i+1)*size];stamp,rwrite,rage,remit,rreplace,rphase,rbefore,rfields,rprev,valid,new,first,pad=struct.unpack_from('>5I4H4B',b);fields,steps=struct.unpack_from('>HI',b,348);g=b[354:354+data['size']];traffic=b[-144:]
  def word(glo):return struct.unpack_from('>H',g,off(glo))[0]
  pose=[word(glo) for glo in [0x98f0,0x98f4,0x98f2,0x9944,0x9946,0x9948]]+[word(0x9602)|(0x8000 if g[off(0xaf31)] else 0)]
  for j in range(12):
   t=struct.unpack_from('>6H',traffic,j*12);pose.extend([t[0],t[1],t[2],t[4],t[3],t[5]])
  current_offset=struct.unpack_from('>I',(out/'pointers.bin').read_bytes(),i*8+4)[0]-rr if '_record_previous_ptr' in symbols else 190
  assert words(b[current_offset:current_offset+158])==tuple(pose),('native capture',i)
  unique=last_stamp!=steps
  if unique:
   first_sample=last_stamp is None;interval=previous_fields if last_stamp is not None and steps==last_stamp+1 else 0
   gaps+=int(last_stamp is not None and steps!=last_stamp+1);before=phase;write_at=write;previous=current;previous_fields=fields;age+=interval;last_stamp=steps
  else:duplicates+=1
  current=tuple(pose);phase=(before+interval)%8;samples=[]
  if first_sample:samples=[current]
  else:
   for num in range(8-before,interval+1,8):
    samples.append(blend(previous,current,num,interval));fractional+=num!=interval
  multiple+=len(samples)>1;maximum=max(maximum,len(samples));multi_replacements+=not unique and len(samples)>1
  at=write_at
  for sample in samples:
   offset=at-ringbase;ring[offset:offset+158]=struct.pack('>79H',*sample);at=ringbase+(offset+158)%14220
   if unique:emitted+=1
   else:replaced+=1
  write=at
  expected=(steps,write_at,age,emitted,replaced,phase,before,interval,previous_fields,255,255 if unique else 0,255 if first_sample else 0,0)
  actual=struct.unpack_from('>5I4H4B',b);assert actual==expected,('state',i,actual,expected)
  actual_ring=bytearray(g[off(0xb192):off(0xe91e)])
  if pending:
   pend=(out/'pending.bin').read_bytes()[i*29476:(i+1)*29476]
   for slot in range(90):
    pair,num,den=struct.unpack_from('>IHH',pend,slot*8)
    if pair:
     pos=pair-pending;l=words(pend[pos:pos+158]);r=words(pend[pos+158:pos+316])
     actual_ring[slot*158:(slot+1)*158]=struct.pack('>79H',*blend(l,r,num,den))
  assert actual_ring==ring,('logical ring',i)
  assert struct.unpack_from('>I',g,off(0xe91e))[0]==write,('pointer',i)
 assert (out/'resolved.bin').read_bytes()==ring,'resolved native ring at playback entry'
 result=dict(passed=True,deferred=bool(pending),resolved_native_ring_exact=True,transactions=n,private_wrap_samples=91 if '_record_wrap_results' in symbols else 0,multiple_transactions=multiple,max_samples_per_transaction=maximum,multiple_replacements=multi_replacements,wide_private_records=24 if a.wide else 0,private_records=k,private_words=k*79,rewinds=rewinds,duplicates=duplicates,replacements=replaced,gaps=gaps,fractional_samples=fractional,emitted=emitted,age_fields=age)
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.close()
