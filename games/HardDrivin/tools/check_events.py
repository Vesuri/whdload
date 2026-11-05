import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-events-live.slave');p.add_argument('--wide',action='store_true');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits={}
 for bank,b in s.dump_banks('events'):
  for sig in [b'HDEVENT1',b'HDDISP01',b'HDTIME01',b'HDEVMAT1']+([b'HDEVPH01'] if a.wide else []):
   i=b.find(sig)
   if i>=0:
    assert sig not in hits;hits[sig]=bank+i+8
    if sig==b'HDEVMAT1':math=b[i+8:i+8+(1536 if a.wide else 864)]
    if sig==b'HDEVPH01':phase=b[i+8:i+8+108]
 expected=[]
 for fields in (list(range(9))+[9,15,16,255,32768,65528,65535] if a.wide else range(9)):
  for carry in range(8):
   due,rest=divmod(carry+fields,8);due2,rest2=divmod(rest+fields,8);expected += [due,rest,0,rest,due2,rest2]
 assert struct.unpack('>'+str(len(expected))+'H',math)==tuple(expected)
 if a.wide:assert struct.unpack('>54H',phase)==tuple(min(7,p+n) for p in range(1,7) for n in [0,1,2,5,6,7,8,8191,8192])
 assert len(hits)==(5 if a.wide else 4);es=hits[b'HDEVENT1'];ds=hits[b'HDDISP01'];ts=hits[b'HDTIME01']
 def mem(addr,typ='unsigned short'):return f'*({typ}*){addr:#x}'
 def g(offset,typ='unsigned short'):return mem(a4+offset-65536,typ)
 lines=[f'gdb break *{base+0xdb1e:#x}',f'break *{base+0xdb32:#x}',f'break *{base+0xdb40:#x}',f'break *{base+0xdb4a:#x}',f'break *{base+0x10f28:#x}',f'break *{base+0x2c14:#x}','set $n=0','while $n<350','continue',f'if $pc=={base+0x10f28:#x}','set $n=$n+1','end']
 for tag,off,slot,val in [('SI',0xdb1e,es,g(0x9788,'unsigned int')),('SO',0xdb32,es,g(0x9788,'unsigned int')),('PI',0xdb40,es+4,g(0xadde,'unsigned char')),('PO',0xdb4a,es+4,g(0xadde,'unsigned char'))]:
  expr=[mem(ds+8,'unsigned int'),mem(ts+20,'unsigned int'),mem(ds+24,'unsigned char'),mem(slot),mem(slot+2,'unsigned char'),val]
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' %u %u %u %u %u %u\\n",'+','.join(expr),'end']
 lines += [f'if $pc=={base+0x2c14:#x}','printf "BCD\\n"','end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply);pending={};counts={'S':0,'P':0};duplicates=0;duecounts={'S':0,'P':0};fractional=0;native_calls=0;total_native_calls=0;multiple=0
 for line in reply.splitlines():
  if line=='BCD':
   if 'S' in pending:native_calls+=1
   continue
  m=re.match(r'([SP])([IO]) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$',line)
  if not m:continue
  kind,direction,*values=m.groups();step,T,active,carry,charged,value=map(int,values)
  if direction=='I':
   pending[kind]=(step,T,active,carry,charged,value)
   if kind=='S':native_calls=0
   continue
  before=pending.pop(kind,None)
  if before is None:continue
  st,t,act,oldcarry,oldcharged,oldvalue=before
  assert step==st
  if not act:continue
  n=t//8192;due=0;rest=oldcarry
  if not oldcharged:due,rest=divmod(oldcarry+n,8)
  assert (carry,charged)==(rest,255),(kind,before,(carry,charged))
  if kind=='P':assert value==min(7,oldvalue+due),(before,value,due)
  else:
   assert native_calls==due,(before,native_calls,due)
   total_native_calls+=native_calls;multiple+=due>1
   if not due:assert value==oldvalue,(before,value)
  counts[kind]+=1;duplicates+=bool(oldcharged);duecounts[kind]+=due;fractional+=n<8
 assert counts['S'] and counts['P'] and fractional
 r=dict(passed=True,private_cadence_cases=128 if a.wide else 72,private_phase_cases=54 if a.wide else 0,native_score_calls=total_native_calls,multiple_score_visits=multiple,live_score_visits=counts['S'],live_start_visits=counts['P'],score_events=duecounts['S'],phase_events=duecounts['P'],duplicate_visits=duplicates,fractional_visits=fractional);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');(out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n');print(r)
finally:s.close()
