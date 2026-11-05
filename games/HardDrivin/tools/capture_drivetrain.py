"""Observe velocity, RPM and automatic shifts without writing game state."""
import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--delay',type=int,default=0);p.add_argument('--fields',type=int,default=360);p.add_argument('--slave',default='s4-throttle-hold22.slave');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits=[]
 for _,b in s.dump_banks('drivetrain'):
  i=b.find(b'HDSCAL01')
  if i>=0:hits.append((_+i+8))
 assert len(hits)==1;ss=hits[0]
 def mem(addr,t='short'):return f'*({t}*){addr:#x}'
 def g(off,t='short'):return mem(a4+off-65536,t)
 cols=['field','interval','velocity','velocity_carry','rpm','rpm_carry','rpm_last','rpm_gear','gear','auto','throttle','mask','road','power','rate']
 expr=['$f',mem(ss-10,'unsigned short'),g(0x9928),mem(ss),g(0x992a),mem(ss+10),mem(ss+12),mem(ss+14),g(0x9936),g(0x993e,'unsigned char'),g(0x991c,'unsigned char'),g(0x9910,'unsigned char'),g(0xe94a,'unsigned char'),'*(unsigned short*)($a5-14)','*(short*)($a5-8)']
 sites=[('ENTRY',0xb678),('FORCE',0xb8a2),('RPM',0xb904),('GEAR',0xba8a)]
 lines=[f'gdb break *{base+0x3f2:#x}']+[f'break *{base+off:#x}' for _,off in sites]+['set $f=0',f'while $f<{a.fields}','continue',f'if $pc=={base+0x3f2:#x}','set $f=$f+1','end']
 for tag,off in sites:lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr),'end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 rows=[dict(kind=k,**dict(zip(cols,map(int,v.split())))) for k,v in re.findall(r'^(ENTRY|FORCE|RPM|GEAR) ([-0-9 ]+)$',reply,re.M)]
 table=struct.unpack_from('>10h',(out/'game-data.bin').read_bytes(),0xcc2)
 (out/'drivetrain.json').write_text(json.dumps(dict(profile=a.profile,delay=a.delay,columns=cols,gear_table=list(zip(table[::2],table[1::2])),rows=rows),indent=2)+'\n');print(a.name,len(rows),'observations')
finally:s.close()
