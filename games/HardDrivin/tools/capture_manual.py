import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-manual.slave');p.add_argument('--steps',type=int,default=108);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits={}
 for bank,b in s.dump_banks('manual-start'):
  for sig in [b'HDDRIVE1',b'HDSCAL01',b'HDMANIN1']:
   i=b.find(sig)
   if i>=0:assert sig not in hits;hits[sig]=bank+i+8
 assert len(hits)==3;dt=hits[b'HDDRIVE1'];ss=hits[b'HDSCAL01'];fixture=hits[b'HDMANIN1']
 def mem(addr,t='short'):return f'*({t}*){addr:#x}'
 def g(off,t='short'):return mem(a4+off-65536,t)
 cols=['field','controls','active','fields','remaining','outer','gear','rpm','auto','request','joystick','velocity','rpm_carry','rpm_last','rpm_gear','throttle','mask','skid']
 expr=['$f',mem(fixture),mem(dt+6),mem(dt),mem(dt+2),mem(dt+12,'unsigned int'),g(0x9936),g(0x992a),g(0x993e,'unsigned char'),g(0x991d,'unsigned char'),g(0x95ff,'unsigned char'),g(0x9928),mem(ss+10),mem(ss+12),mem(ss+14),g(0x991c,'unsigned char'),g(0x9910,'unsigned char'),g(0xaf31,'unsigned char')]
 sites=[('ENTER',0xb678),('MANUAL',0xb9ba),('SHIFT',0xba00),('AFTER',0xba8a)]
 lines=[f'gdb break *{base+0x3f2:#x}',f'break *{base+0xcdb0:#x}']+[f'break *{base+off:#x}' for _,off in sites]+['set $f=0','set $n=0',f'while $n<{a.steps}','continue',f'if $pc=={base+0x3f2:#x}','set $f=$f+1','end',f'if $pc=={base+0xcdb0:#x}','set $n=$n+1','end']
 for tag,off in sites:lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr),'end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 rows=[dict(kind=k,**dict(zip(cols,map(int,v.split())))) for k,v in re.findall(r'^(ENTER|MANUAL|SHIFT|AFTER) ([-0-9 ]+)$',reply,re.M)]
 assert rows and all(r['auto']==0 for r in rows)
 (out/'manual.json').write_text(json.dumps(dict(profile=a.profile,steps=a.steps,rows=rows),indent=2)+'\n');print(a.name,len(rows),'manual observations')
finally:s.close()
