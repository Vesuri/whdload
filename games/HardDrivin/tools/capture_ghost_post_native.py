import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session,re_register
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x1111c);s.env['WHD_ARGS']+=' CUSTOM1=1';s.env['SERVE_WAIT']='600'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];a5=re_register(command('gdb info registers a5'),'a5');images=s.dump_banks('post-native')
 def read(addr,n):
  for bank,b in images:
   if bank<=addr and addr+n<=bank+len(b):return b[addr-bank:addr-bank+n]
  raise ValueError(hex(addr))
 def u32(addr):return struct.unpack('>I',read(addr,4))[0]
 def ga(o):return a4+o-65536
 def mem(addr,t='unsigned int'):return f'*({t}*){addr:#x}'
 def g(o,t='unsigned short'):return mem(ga(o),t)
 arenas=[u32(ga(o)) for o in [0x9644,0x9640]];actors=[u32(ga(o)) for o in [0x997a,0x997e]];saved=[u32(a5-4),u32(a5-8)]
 expr=[g(o,'unsigned int')+f'-{arena}' for o,arena in zip([0xe924,0xe928],arenas)]+[g(o,'unsigned char') for o in [0xe922,0xe92c]]+[mem(actor+i,'unsigned short') for actor in actors for i in [8,10,12,14,16,18]]+[mem(a5-20,'unsigned short'),mem(a5-22,'unsigned short'),g(0x9602),g(0xaf32,'unsigned char')]
 lines=[f'gdb break *{base+0x11152:#x}',f'break *{base+0x111b6:#x}',f'break *{base+0x1126e:#x}','set $done=0','while $done==0','continue']
 for tag,off in [('F',0x11152),('P',0x111b6),('E',0x1126e)]:
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%u']*len(expr))+'\\n",'+','.join(expr)]
  if tag=='E':lines+=['set $done=1']
  lines+=['end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply);events=[(m[1],list(map(int,m[2].split()))) for m in re.finditer(r'^([FPE]) ((?:\d+ ?)+)$',reply,re.M)];assert events and events[-1][0]=='E';(out/'post-events.json').write_text(json.dumps(events)+'\n');print(dict(frames=sum(t=='F' for t,v in events),saved_offsets=[x-y for x,y in zip(saved,arenas)],final=events[-1]))
finally:s.close()
