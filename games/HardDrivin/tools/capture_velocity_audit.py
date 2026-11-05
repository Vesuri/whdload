import argparse,json,os,re,shutil
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--custom1',type=int,default=1);p.add_argument('--fields',type=int,default=800);p.add_argument('--dissipation',action='store_true');p.add_argument('--delay',type=int,default=0);p.add_argument('--slave',default='s4-brake-audit.slave');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits={}
 for bank,b in s.dump_banks('velocity'):
  for sig in [b'HDSCAL01',b'HDMOTN01',b'HDDISP01']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 ss=hits[b'HDSCAL01'];ms=hits[b'HDMOTN01'];ds=hits[b'HDDISP01'];sf=ss-10
 def mem(x,t='short'):return f'*({t}*){x:#x}'
 def g(x,t='short'):return mem(a4+x-65536,t)
 def event(tag,expr):return 'printf "'+tag+' '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr)
 lines=[f'gdb break *{base+0x3f2:#x}']+[f'break *{base+o:#x}' for o in [0xb8a2,0xb8aa,0xccc2,0xccd4,0xcd86]]+['set $f=-1',f'while $f<{a.fields}','continue',f'if $pc=={base+0x3f2:#x}','set $f=$f+1','end']
 fields=mem(sf,'unsigned short') if a.custom1 else '8'
 common=['$f',fields,g(0x9928),'*(short*)($a5-8)',mem(ss) if a.custom1 else '0',mem(ss+2) if a.custom1 else g(0x9928)]
 ordinary=common+['*(short*)($a5-2)','*(short*)($a5-4)','*(short*)($a5-6)','*(short*)($a5-18)',g(0x991c,'unsigned char'),g(0x9911,'unsigned char'),g(0x9936),mem(ds+26,'unsigned short') if a.custom1 else '-1','*(unsigned short*)($a5-14)',g(0xe94a,'unsigned char'),g(0xf790,'unsigned char'),g(0xaf31,'unsigned char')]
 lines += [f'if $pc=={base+0xb8a2:#x}',event('V0',ordinary),'end',f'if $pc=={base+0xb8aa:#x}',event('V1',[g(0x9928),mem(ss),mem(ss+2)]),'end']
 for off,rate,condition in [(0xccc2,'*(short*)($a5-14)','1'),(0xccd4,'5','*(unsigned char*)($a5-1)==0')]:
  lines += [f'if $pc=={base+off:#x} && ({condition})',event('F0',['$f',fields,g(0x990e),rate,mem(ms+18) if a.custom1 else '0',mem(ms+20) if a.custom1 else g(0x990e)]),'end']
 lines += [f'if $pc=={base+0xcd86:#x}',event('F1',[g(0x990e),mem(ms+18),mem(ms+20)]),'end','end','delete']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply);pending={};rows={'V':[],'F':[]}
 for line in reply.splitlines():
  match=re.fullmatch(r'([VF])([01]) ([-0-9 ]+)',line)
  if not match:continue
  kind,edge,values=match.groups();values=list(map(int,values.split()))
  if edge=='0':pending[kind]=values;continue
  old=pending.pop(kind,None)
  if old is None:continue
  field,n,v,rate,rem,last=old[:6];rem=rem if last==v else 0;num=rate*n+rem;delta=abs(num)//8*(-1 if num<0 else 1);full=v+delta;carry=num-delta*8;wrapped=(full+32768)%65536-32768
  limited=False
  if a.dissipation and kind=='V':
   from dissipation_model import update
   drag,brake,slope,drive=old[6:10]
   corrected=update(v,rate,n,rem,v,drive,drag,brake,slope)
   full=corrected['full'];carry=corrected['carry'];wrapped=corrected['value'];limited=corrected['limited']
  assert values[0]==wrapped,(kind,old,values,full)
  if a.custom1:assert values[1:]==[carry,wrapped],(kind,old,values,carry)
  rows[kind].append(dict(field=field,fields=n,old=v,rate=rate,full=full,value=wrapped,carry=carry,overflow=not -32768<=full<=32767,limited=limited,crossed_zero=v*wrapped<0,inputs=old[6:]))
 result={kind:dict(updates=len(v),limited=sum(r['limited'] for r in v),overflows=sum(r['overflow'] for r in v),zero_crossings=sum(r['crossed_zero'] for r in v),min_value=min((r['value'] for r in v),default=None),max_value=max((r['value'] for r in v),default=None),max_fields=max((r['fields'] for r in v),default=None)) for kind,v in rows.items()}
 (out/'samples.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');(out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n');print(result)
finally:s.close()
