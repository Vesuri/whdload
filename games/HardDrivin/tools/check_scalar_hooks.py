"""Check actual game call operands and results against an independent rate model."""
import argparse,json,os,re,shutil
from capture_demo import ROOT,command
from capture_session import Session
from check_disabled import check
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--fields',type=int,default=1);p.add_argument('--slave',default='s4-scalars-eighth.slave');p.add_argument('--require-down',action='store_true');p.add_argument('--steps',type=int,default=120);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits=[]
 for bank,b in s.dump_banks('scalars'):
  i=b.find(b'HDSCAL01')
  if i>=0:hits.append(bank+i+8)
 assert len(hits)==1;st=hits[0]
 sites=[('v',0xb8a2,0xb8aa,0x9928,'*(short*)($a5-8)',0,2,'short','short'),('u',0x7d36,0x7d40,0x991c,'2',4,8,'signed char','long'),('d',0x7d50,0x7d58,0x991c,'-2',4,8,'signed char','long'),('n',0xb704,0xb72a,0x992a,'*(short*)($a5-12)',10,12,'short','short'),('r',0xb8d2,0xb8ec,0x992a,'(short)$d4',10,12,'short','short')]
 addresses=[base+x for _,start,end,*_ in sites for x in [start,end]]+[base+0xcdb0]
 lines=['gdb break *'+hex(addresses[0])]+['break *'+hex(x) for x in addresses[1:]]+['set $n=0',f'while $n < {a.steps}','continue',f'if $pc == {base+0xcdb0:#x}','set $n=$n+1','end']
 for name,start,end,g,inc,carry,last,typ,ctyp in sites:
  addr=a4+g-65536
  lines += [f'if $pc == {base+start:#x}',f'printf "IN {name} %d %d %d %d %d %d\\n",*({typ}*){addr:#x},{inc},*({ctyp}*){st+carry:#x},*({typ}*){st+last:#x},*(short*){a4+0x9936-65536:#x},*(short*){st+14:#x}','end',f'if $pc == {base+end:#x}',f'printf "OUT {name} %d %d\\n",*({typ}*){addr:#x},*({ctyp}*){st+carry:#x}','end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 pending={};counts={k:0 for k,*_ in sites};errors=[]
 def trunc(n):return abs(n)//8*(-1 if n<0 else 1)
 for line in reply.splitlines():
  if line.startswith('IN '):
   _,k,*vals=line.split();v,raw,carry,last,gear,lastgear=map(int,vals)
   if v!=last or (k in 'nr' and gear!=lastgear):carry=0
   rate=(450 if raw>0 else -450 if raw<0 else 0) if k in 'nr' else raw
   scale=8192 if k in 'ud' else 1;den=65536 if k in 'ud' else 8
   n=rate*a.fields*scale+carry;q=abs(n)//den*(-1 if n<0 else 1);rem=n-q*den
   if k in 'nr' and ((raw>=0 and raw<=q) or (raw<0 and raw>=q)):q=raw;rem=0
   value=v+q
   if k in 'ud':
    value=(value+128)%256-128
    if (value<=0 and rem<0) or (value>=100 and rem>0):rem=0
   else:
    value=(value+32768)%65536-32768
    if k in 'nr' and value>=6500:rem=0
   pending[k]=(value,rem,line)
  elif line.startswith('OUT '):
   _,k,v,c=line.split();got=(int(v),int(c));assert k in pending,(line,pending)
   exp= pending.pop(k)
   if got!=exp[:2]:errors.append(dict(entry=exp[2],expected=exp[:2],actual=got))
   counts[k]+=1
 r=dict(passed=not errors and (not a.require_down or counts['d']>0),counts=counts,errors=errors,fields=a.fields,ranges=check(out,['VERIFY_DRIVE','VERIFY_STEPINPUT','CUSTOM1','VERIFY_TIME_SCALARS']));assert r['ranges']['passed'];(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='ranges'});assert r['passed']
finally:s.close()
